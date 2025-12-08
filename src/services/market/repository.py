"""Market repository - data access layer."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from psycopg2.extras import RealDictCursor, execute_values

from src.core.database import DatabasePool
from src.core.exceptions import EVECopilotError
from src.services.market.models import MarketPrice, CacheStats


class MarketRepository:
    """Data access for market prices."""

    def __init__(self, db_pool: DatabasePool):
        """Initialize repository with database pool."""
        self.db = db_pool

    def bulk_upsert_prices(self, prices: List[MarketPrice]) -> int:
        """
        Bulk upsert market prices using ON CONFLICT.

        Args:
            prices: List of MarketPrice objects to upsert

        Returns:
            Number of rows affected

        Raises:
            EVECopilotError: If database operation fails
        """
        if not prices:
            return 0

        try:
            # Prepare values for bulk insert
            values = [
                (
                    price.type_id,
                    price.adjusted_price,
                    price.average_price,
                    price.last_updated
                )
                for price in prices
            ]

            with self.db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
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
                    return cur.rowcount
        except EVECopilotError:
            raise
        except Exception as e:
            raise EVECopilotError(f"Failed to bulk upsert prices: {str(e)}")

    def get_cache_stats(self) -> CacheStats:
        """
        Get statistics about the price cache.

        Returns:
            CacheStats object with cache statistics

        Raises:
            EVECopilotError: If database operation fails
        """
        try:
            with self.db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT
                            COUNT(*) as total_items,
                            MIN(last_updated) as oldest_entry,
                            MAX(last_updated) as newest_entry
                        FROM market_prices_cache
                    """)
                    row = cur.fetchone()

                    if row and row["total_items"] > 0:
                        total_items = row["total_items"]
                        oldest_entry = row["oldest_entry"]
                        newest_entry = row["newest_entry"]

                        # Calculate cache age
                        cache_age_seconds = None
                        is_stale = True

                        if newest_entry:
                            age = datetime.now() - newest_entry
                            cache_age_seconds = age.total_seconds()
                            is_stale = cache_age_seconds > 3600  # Stale if > 1 hour

                        return CacheStats(
                            total_items=total_items,
                            oldest_entry=oldest_entry,
                            newest_entry=newest_entry,
                            cache_age_seconds=cache_age_seconds,
                            is_stale=is_stale
                        )

                    # Cache is empty
                    return CacheStats(
                        total_items=0,
                        oldest_entry=None,
                        newest_entry=None,
                        cache_age_seconds=None,
                        is_stale=True
                    )
        except EVECopilotError:
            raise
        except Exception as e:
            raise EVECopilotError(f"Failed to get cache stats: {str(e)}")

    def get_price(self, type_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a single price by type_id.

        Args:
            type_id: EVE type ID to lookup

        Returns:
            Price data as dict or None if not found

        Raises:
            EVECopilotError: If database operation fails
        """
        try:
            with self.db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        "SELECT * FROM market_prices_cache WHERE type_id = %s",
                        (type_id,)
                    )
                    result = cur.fetchone()
                    return dict(result) if result else None
        except EVECopilotError:
            raise
        except Exception as e:
            raise EVECopilotError(f"Failed to get price for type_id {type_id}: {str(e)}")

    def get_prices_bulk(self, type_ids: List[int]) -> List[Dict[str, Any]]:
        """
        Get multiple prices at once using ANY clause.

        Args:
            type_ids: List of type IDs to fetch (empty list fetches all)

        Returns:
            List of price dicts (may be less than requested if some don't exist)

        Raises:
            EVECopilotError: If database operation fails
        """
        try:
            with self.db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # If empty list, fetch all prices
                    if not type_ids:
                        cur.execute(
                            """
                            SELECT *
                            FROM market_prices_cache
                            WHERE adjusted_price > 0
                            """
                        )
                    else:
                        cur.execute(
                            """
                            SELECT *
                            FROM market_prices_cache
                            WHERE type_id = ANY(%s)
                            """,
                            (list(type_ids),)
                        )
                    return [dict(row) for row in cur.fetchall()]
        except EVECopilotError:
            raise
        except Exception as e:
            raise EVECopilotError(f"Failed to get prices bulk: {str(e)}")
