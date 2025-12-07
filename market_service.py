"""
EVE Co-Pilot Market Service Module
Handles global market price caching and bulk operations
"""

import requests
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from psycopg2.extras import execute_values
from database import get_db_connection
from config import ESI_BASE_URL, ESI_USER_AGENT


class MarketService:
    """Service for caching and retrieving global market prices"""

    def __init__(self):
        self.base_url = ESI_BASE_URL
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": ESI_USER_AGENT,
            "Accept": "application/json"
        })
        self._memory_cache: Dict[int, float] = {}
        self._cache_loaded = False

    def update_global_prices(self) -> Dict:
        """
        Fetch all market prices from ESI in a single API call and cache them.

        This endpoint returns ~15,000+ items with adjusted_price and average_price.
        Uses bulk upsert for performance.

        Returns:
            Dict with update statistics
        """
        url = f"{self.base_url}/markets/prices/"

        try:
            response = self.session.get(
                url,
                params={"datasource": "tranquility"},
                timeout=60
            )

            if response.status_code != 200:
                return {
                    "error": f"ESI request failed with status {response.status_code}",
                    "details": response.text
                }

            prices = response.json()

            if not prices:
                return {"error": "No price data received from ESI"}

            # Prepare data for bulk insert
            now = datetime.now()
            values = []
            for item in prices:
                type_id = item.get("type_id")
                if type_id:
                    values.append((
                        type_id,
                        item.get("adjusted_price", 0) or 0,
                        item.get("average_price", 0) or 0,
                        now
                    ))

            # Bulk upsert into database
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # Use ON CONFLICT for upsert
                    execute_values(
                        cur,
                        """
                        INSERT INTO market_prices_cache (type_id, adjusted_price, average_price, last_updated)
                        VALUES %s
                        ON CONFLICT (type_id)
                        DO UPDATE SET
                            adjusted_price = EXCLUDED.adjusted_price,
                            average_price = EXCLUDED.average_price,
                            last_updated = EXCLUDED.last_updated
                        """,
                        values,
                        page_size=1000
                    )
                    conn.commit()

            # Invalidate memory cache
            self._memory_cache.clear()
            self._cache_loaded = False

            return {
                "success": True,
                "items_updated": len(values),
                "timestamp": now.isoformat(),
                "message": f"Updated {len(values):,} market prices in cache"
            }

        except requests.RequestException as e:
            return {"error": f"Network error: {str(e)}"}
        except Exception as e:
            return {"error": f"Cache update failed: {str(e)}"}

    def get_cache_stats(self) -> Dict:
        """Get statistics about the price cache"""
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        COUNT(*) as total_items,
                        MIN(last_updated) as oldest_entry,
                        MAX(last_updated) as newest_entry
                    FROM market_prices_cache
                """)
                row = cur.fetchone()

                if row and row[0] > 0:
                    age = datetime.now() - row[2] if row[2] else None
                    return {
                        "total_items": row[0],
                        "oldest_entry": row[1].isoformat() if row[1] else None,
                        "newest_entry": row[2].isoformat() if row[2] else None,
                        "cache_age_seconds": age.total_seconds() if age else None,
                        "is_stale": age.total_seconds() > 3600 if age else True  # Stale if > 1 hour
                    }

                return {
                    "total_items": 0,
                    "is_stale": True,
                    "message": "Cache is empty - run update_global_prices()"
                }

    def load_prices_to_memory(self) -> int:
        """
        Load all cached prices into memory for ultra-fast lookups.
        Returns number of prices loaded.
        """
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT type_id, adjusted_price
                    FROM market_prices_cache
                    WHERE adjusted_price > 0
                """)

                self._memory_cache.clear()
                for row in cur.fetchall():
                    self._memory_cache[row[0]] = row[1]

                self._cache_loaded = True
                return len(self._memory_cache)

    def get_cached_price(self, type_id: int) -> Optional[float]:
        """
        Get adjusted_price from cache.
        Uses memory cache if loaded, otherwise queries DB.
        """
        if self._cache_loaded and self._memory_cache:
            return self._memory_cache.get(type_id)

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT adjusted_price
                    FROM market_prices_cache
                    WHERE type_id = %s
                """, (type_id,))
                row = cur.fetchone()
                return row[0] if row else None

    def get_cached_prices_bulk(self, type_ids: List[int]) -> Dict[int, float]:
        """
        Get multiple prices at once - much faster than individual lookups.
        Returns dict {type_id: adjusted_price}
        """
        if not type_ids:
            return {}

        if self._cache_loaded and self._memory_cache:
            return {tid: self._memory_cache.get(tid, 0) for tid in type_ids}

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT type_id, adjusted_price
                    FROM market_prices_cache
                    WHERE type_id = ANY(%s)
                """, (list(type_ids),))

                return {row[0]: row[1] or 0 for row in cur.fetchall()}

    def calculate_material_cost(self, bom: Dict[int, int]) -> float:
        """
        Calculate total material cost from cached prices.

        Args:
            bom: Dict of {material_type_id: quantity}

        Returns:
            Total cost based on adjusted_price
        """
        if not bom:
            return 0

        prices = self.get_cached_prices_bulk(list(bom.keys()))
        total = 0

        for type_id, quantity in bom.items():
            price = prices.get(type_id, 0)
            total += price * quantity

        return total

    def ensure_cache_fresh(self, max_age_seconds: int = 3600) -> Dict:
        """
        Ensure cache is fresh, update if stale.

        Args:
            max_age_seconds: Maximum age before cache is considered stale (default 1 hour)

        Returns:
            Cache stats or update result
        """
        stats = self.get_cache_stats()

        if stats.get("total_items", 0) == 0:
            # Cache empty, need to update
            return self.update_global_prices()

        age = stats.get("cache_age_seconds")
        if age is None or age > max_age_seconds:
            # Cache stale, need to update
            return self.update_global_prices()

        return {
            "success": True,
            "cached": True,
            "message": f"Cache is fresh ({int(age)}s old)",
            **stats
        }


# Global market service instance
market_service = MarketService()
