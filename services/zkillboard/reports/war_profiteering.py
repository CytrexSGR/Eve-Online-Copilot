"""
War Profiteering Report - Market opportunities from combat.

Analyzes destroyed items and calculates market opportunity scores
based on quantity destroyed and current market prices.
"""

import json
from typing import Dict

from src.database import get_db_connection
from .base import REPORT_CACHE_TTL


class WarProfiteeringMixin:
    """Mixin providing war profiteering report methods."""

    def get_war_profiteering_report(self, limit: int = 20) -> Dict:
        """
        Generate war profiteering report with market opportunities.

        Analyzes destroyed items and calculates market opportunity scores
        based on quantity destroyed and current market prices.

        Args:
            limit: Number of items to return

        Returns:
            Dict with top destroyed items and their market opportunity scores
        """
        # Check cache first
        cache_key = f"report:war_profiteering:{limit}"
        try:
            cached = self.redis_client.get(cache_key)
            if cached:
                print(f"[CACHE HIT] Returning cached war profiteering report")
                return json.loads(cached)
        except Exception:
            pass

        # Get destroyed items from Redis
        items = []
        for key in self.redis_client.scan_iter("kill:item:*:destroyed"):
            parts = key.split(":")
            if len(parts) == 4:
                item_type_id = int(parts[2])
                quantity = int(self.redis_client.get(key) or 0)

                if quantity > 0:  # Only items with actual destruction
                    items.append({
                        "item_type_id": item_type_id,
                        "quantity_destroyed": quantity
                    })

        if not items:
            return {"items": [], "total_items": 0, "total_opportunity_value": 0}

        # Batch query for all items with price fallback logic
        item_data = []
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Create temporary table with destroyed items for efficient JOIN
                item_ids = [item['item_type_id'] for item in items]
                quantities = {item['item_type_id']: item['quantity_destroyed'] for item in items}

                # Batch query with price fallback: Jita → Adjusted → Base
                cur.execute(
                    '''SELECT
                        t."typeID",
                        t."typeName",
                        t."groupID",
                        g."categoryID",
                        COALESCE(mp.lowest_sell, mpc.adjusted_price, t."basePrice"::double precision, 0) as final_price
                       FROM "invTypes" t
                       JOIN "invGroups" g ON t."groupID" = g."groupID"
                       LEFT JOIN market_prices mp ON t."typeID" = mp.type_id AND mp.region_id = 10000002
                       LEFT JOIN market_prices_cache mpc ON t."typeID" = mpc.type_id
                       WHERE t."typeID" = ANY(%s)''',
                    (item_ids,)
                )

                for row in cur.fetchall():
                    item_id = row[0]
                    item_name = row[1]
                    group_id = row[2]
                    category_id = row[3]
                    market_price = float(row[4]) if row[4] else 0
                    quantity = quantities[item_id]

                    # Exclude raw materials, ore, ice, PI materials
                    # Category 4 = Material, 25 = Asteroid, 43 = Planetary Commodities
                    if category_id in (4, 25, 43):
                        continue

                    # Skip items without valid market price
                    if market_price <= 0:
                        continue

                    # Calculate opportunity score
                    opportunity_value = quantity * market_price

                    item_data.append({
                        "item_type_id": item_id,
                        "item_name": item_name,
                        "group_id": group_id,
                        "quantity_destroyed": quantity,
                        "market_price": market_price,
                        "opportunity_value": opportunity_value
                    })

        # Sort by opportunity value (highest opportunity first)
        item_data.sort(key=lambda x: x['opportunity_value'], reverse=True)

        # Calculate totals
        total_opportunity = sum(item['opportunity_value'] for item in item_data[:limit])

        result = {
            "items": item_data[:limit],
            "total_items": len(item_data),
            "total_opportunity_value": total_opportunity,
            "period": "24h"
        }

        # Cache for 7 hours
        try:
            self.redis_client.setex(cache_key, REPORT_CACHE_TTL, json.dumps(result))
            print(f"[CACHE] Cached war profiteering report for {REPORT_CACHE_TTL}s")
        except Exception:
            pass

        return result
