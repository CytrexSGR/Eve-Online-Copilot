"""
Dashboard aggregation service for EVE Co-Pilot 2.0

Aggregates opportunities from:
- Market Hunter (manufacturing)
- Arbitrage Finder (trading)
- War Analyzer (combat demand)

Sorts by user priorities: Industrie → Handel → War Room
"""

import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta
import psycopg2
from database import get_db_connection, get_item_info
from esi_client import esi_client
from config import REGIONS

logger = logging.getLogger(__name__)


# Mapping of region IDs to names for REGIONS dict
REGION_ID_TO_NAME = {v: k for k, v in REGIONS.items()}


def get_best_arbitrage_opportunities(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Calculate best arbitrage opportunities between trade hubs

    Returns top opportunities sorted by profit
    """
    # High-volume items to check for arbitrage
    popular_items = [
        645,   # Thorax
        638,   # Vexor
        11987, # Dominix
        641,   # Myrmidon
        16236  # Gila
    ]

    opportunities = []

    for type_id in popular_items:
        try:
            # Get item name
            item_info = get_item_info(type_id)
            type_name = item_info.get('typeName', 'Unknown') if item_info else 'Unknown'

            # Get prices in all trade hubs
            prices = {}
            for region_name, region_id in REGIONS.items():
                try:
                    stats = esi_client.get_market_stats(region_id, type_id)
                    if stats:
                        prices[region_id] = {
                            'name': region_name,
                            'buy': stats.get('highest_buy', 0) or 0,
                            'sell': stats.get('lowest_sell', 0) or 0
                        }
                except Exception as e:
                    logger.debug(f"Failed to get price for {type_id} in region {region_id}: {e}")
                    continue

            # Find best arbitrage
            for buy_region_id, buy_data in prices.items():
                for sell_region_id, sell_data in prices.items():
                    if buy_region_id == sell_region_id:
                        continue

                    buy_price = buy_data['sell']  # Buy at lowest sell
                    sell_price = sell_data['buy']  # Sell at highest buy

                    if buy_price > 0 and sell_price > buy_price:
                        profit = sell_price - buy_price
                        roi = (profit / buy_price) * 100

                        if profit > 1000000:  # Min 1M profit
                            opportunities.append({
                                'type_id': type_id,
                                'type_name': type_name,
                                'buy_region_id': buy_region_id,
                                'buy_region_name': buy_data['name'],
                                'sell_region_id': sell_region_id,
                                'sell_region_name': sell_data['name'],
                                'buy_price': buy_price,
                                'sell_price': sell_price,
                                'profit': profit,
                                'roi': roi
                            })

        except Exception as e:
            logger.error(f"Error calculating arbitrage for {type_id}: {e}")
            continue

    # Sort by profit and limit
    return sorted(opportunities, key=lambda x: -x['profit'])[:limit]


class DashboardService:
    """Aggregates and prioritizes opportunities for dashboard"""

    CATEGORY_PRIORITY = {
        'production': 1,
        'trade': 2,
        'war_demand': 3
    }

    def __init__(self):
        self.cache = {}
        self.cache_ttl = timedelta(minutes=5)

    def get_opportunities(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get top opportunities across all categories

        Args:
            limit: Maximum number of opportunities to return (default 10)

        Returns:
            List of opportunity dicts sorted by priority and profitability
        """
        # Check cache
        cache_key = f"opportunities_{limit}"
        if cache_key in self.cache:
            cached_time, cached_data = self.cache[cache_key]
            if datetime.now() - cached_time < self.cache_ttl:
                return cached_data

        opportunities = []

        # Aggregate from all sources
        opportunities.extend(self._get_production_opportunities())
        opportunities.extend(self._get_trade_opportunities())
        opportunities.extend(self._get_war_demand_opportunities())

        # Sort by priority and profit
        sorted_ops = self._sort_opportunities(opportunities)

        # Limit results
        result = sorted_ops[:limit]

        # Cache result
        self.cache[cache_key] = (datetime.now(), result)

        return result

    def _get_production_opportunities(self) -> List[Dict[str, Any]]:
        """Get manufacturing opportunities from Market Hunter"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT
                            product_id,
                            product_name,
                            profit,
                            roi,
                            difficulty,
                            cheapest_material_cost,
                            best_sell_price
                        FROM manufacturing_opportunities
                        WHERE profit > 1000000
                        ORDER BY profit DESC
                        LIMIT 10
                    """)

                    rows = cursor.fetchall()

                    opportunities = []
                    for row in rows:
                        opportunities.append({
                            'category': 'production',
                            'type_id': row[0],
                            'name': row[1],
                            'profit': float(row[2]) if row[2] else 0.0,
                            'roi': float(row[3]) if row[3] else 0.0,
                            'difficulty': row[4],
                            'material_cost': float(row[5]) if row[5] else 0.0,
                            'sell_price': float(row[6]) if row[6] else 0.0
                        })

                    return opportunities

        except psycopg2.Error as e:
            logger.error(f"Database error fetching production opportunities: {e}", exc_info=True)
            return []
        except Exception as e:
            logger.exception(f"Unexpected error fetching production opportunities: {e}")
            return []

    def _get_trade_opportunities(self) -> List[Dict[str, Any]]:
        """Get arbitrage opportunities"""
        try:
            arbitrage_ops = get_best_arbitrage_opportunities(limit=5)

            opportunities = []
            for arb in arbitrage_ops:
                opportunities.append({
                    'category': 'trade',
                    'type_id': arb['type_id'],
                    'name': arb.get('type_name', 'Unknown'),
                    'profit': arb['profit'],
                    'roi': arb['roi'],
                    'buy_region_id': arb['buy_region_id'],
                    'sell_region_id': arb['sell_region_id'],
                    'buy_price': arb['buy_price'],
                    'sell_price': arb['sell_price']
                })

            return opportunities

        except Exception as e:
            logger.error(f"Error fetching trade opportunities: {e}")
            return []

    def _get_war_demand_opportunities(self) -> List[Dict[str, Any]]:
        """Get combat demand opportunities from War Analyzer"""
        # Mock data for testing - will be replaced with real integration
        return [{
            'category': 'war_demand',
            'type_id': 16236,
            'name': 'Gila',
            'profit': 10000000,
            'roi': 35.0
        }]

    def _sort_opportunities(self, opportunities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Sort opportunities by:
        1. Category priority (production > trade > war_demand)
        2. Profit (descending)
        """
        return sorted(
            opportunities,
            key=lambda x: (
                self.CATEGORY_PRIORITY.get(x['category'], 999),
                -x.get('profit', 0)
            )
        )
