"""
Production Economics Updater

Updates production_economics table with material costs, market prices, and production times.
Runs periodically (e.g., every 30 minutes) to keep economics data fresh.

Usage:
    python3 -m jobs.production_economics_updater --region=10000002 --limit=100
    python3 -m jobs.production_economics_updater --all  # Update all items with chains
"""

import sys
import argparse
from typing import Dict, Optional
from database import get_db_connection
from services.production.economics_repository import ProductionEconomicsRepository
from services.production.chain_repository import ProductionChainRepository


class ProductionEconomicsUpdater:
    """Updates economics data for production items"""

    def __init__(self):
        self.economics_repo = ProductionEconomicsRepository()
        self.chain_repo = ProductionChainRepository()

    def update_item_economics(
        self,
        type_id: int,
        region_id: int
    ) -> bool:
        """
        Calculate and update economics for a single item

        Args:
            type_id: Item type ID
            region_id: Region ID

        Returns:
            True if successful
        """
        try:
            # Calculate material cost from production chains
            material_cost = self._calculate_material_cost(type_id, region_id)

            if material_cost is None:
                print(f"  No chain data for item {type_id}")
                return False

            # Get base job cost (simplified, using 2% of material cost)
            base_job_cost = material_cost * 0.02

            # Get market prices
            market_sell, market_buy = self._get_market_prices(type_id, region_id)

            # Get production time from SDE
            production_time = self._get_production_time(type_id)

            # Upsert to database
            self.economics_repo.upsert(
                type_id=type_id,
                region_id=region_id,
                material_cost=material_cost,
                base_job_cost=base_job_cost,
                market_sell_price=market_sell,
                market_buy_price=market_buy,
                base_production_time=production_time,
                market_volume_daily=0
            )

            return True

        except Exception as e:
            print(f"Error updating economics for {type_id}: {e}")
            return False

    def update_batch(
        self,
        region_id: int,
        limit: Optional[int] = None
    ) -> tuple:
        """
        Update economics for multiple items

        Args:
            region_id: Region ID
            limit: Max items to process (None for all)

        Returns:
            Tuple of (success_count, fail_count)
        """
        # Get items with production chains
        items = self._get_items_with_chains(limit)

        print(f"Updating economics for {len(items)} items in region {region_id}...")

        success_count = 0
        fail_count = 0

        for i, item_type_id in enumerate(items, 1):
            if i % 100 == 0:
                print(f"Progress: {i}/{len(items)} items processed")

            if self.update_item_economics(item_type_id, region_id):
                success_count += 1
            else:
                fail_count += 1

        print(f"\nUpdate completed:")
        print(f"  Success: {success_count}")
        print(f"  Failed: {fail_count}")

        return success_count, fail_count

    def _calculate_material_cost(
        self,
        type_id: int,
        region_id: int
    ) -> Optional[float]:
        """
        Calculate total material cost from production chains

        Args:
            type_id: Item type ID
            region_id: Region for pricing

        Returns:
            Total material cost or None
        """
        # Get raw materials from chains
        materials = self.chain_repo.get_full_chain(type_id)

        if not materials:
            return None

        total_cost = 0.0

        for material in materials:
            material_id = material['material_type_id']
            quantity = material['base_quantity']

            # Get price from market_prices_cache
            price = self._get_material_price(material_id, region_id)

            if price:
                total_cost += quantity * price
            else:
                # Use fallback estimate if no market price
                total_cost += quantity * 10  # 10 ISK per unit fallback

        return total_cost

    def _get_material_price(
        self,
        material_id: int,
        region_id: int
    ) -> Optional[float]:
        """Get material price from market_prices_cache or market_prices"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # Try market_prices_cache first (global adjusted prices)
                    cursor.execute("""
                        SELECT adjusted_price
                        FROM market_prices_cache
                        WHERE type_id = %s
                        LIMIT 1
                    """, (material_id,))

                    row = cursor.fetchone()
                    if row and row[0]:
                        return float(row[0])

                    # Fallback to regional market prices
                    cursor.execute("""
                        SELECT lowest_sell
                        FROM market_prices
                        WHERE type_id = %s AND region_id = %s
                        LIMIT 1
                    """, (material_id, region_id))

                    row = cursor.fetchone()
                    if row and row[0]:
                        return float(row[0])

                    return None

        except Exception as e:
            print(f"Error getting material price: {e}")
            return None

    def _get_market_prices(
        self,
        type_id: int,
        region_id: int
    ) -> tuple:
        """Get market sell and buy prices"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT lowest_sell, highest_buy
                        FROM market_prices
                        WHERE type_id = %s AND region_id = %s
                    """, (type_id, region_id))

                    row = cursor.fetchone()
                    if row:
                        return (
                            float(row[0]) if row[0] else None,
                            float(row[1]) if row[1] else None
                        )

                    return None, None

        except Exception as e:
            print(f"Error getting market prices: {e}")
            return None, None

    def _get_production_time(self, type_id: int) -> int:
        """Get base production time from SDE"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT ia.time
                        FROM "industryActivity" ia
                        JOIN "industryActivityProducts" iap ON ia."typeID" = iap."typeID"
                        WHERE iap."productTypeID" = %s
                        AND ia."activityID" = 1
                        LIMIT 1
                    """, (type_id,))

                    row = cursor.fetchone()
                    return int(row[0]) if row else 3600  # Default 1 hour

        except Exception as e:
            print(f"Error getting production time: {e}")
            return 3600

    def _get_items_with_chains(self, limit: Optional[int]) -> list:
        """Get list of items that have production chains"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    query = """
                        SELECT DISTINCT item_type_id
                        FROM production_chains
                        ORDER BY item_type_id
                    """

                    if limit:
                        query += f" LIMIT {limit}"

                    cursor.execute(query)
                    rows = cursor.fetchall()
                    return [row[0] for row in rows]

        except Exception as e:
            print(f"Error getting items: {e}")
            return []


def main():
    parser = argparse.ArgumentParser(description='Update production economics data')
    parser.add_argument('--region', type=int, default=10000002, help='Region ID (default: The Forge)')
    parser.add_argument('--limit', type=int, help='Max items to process')
    parser.add_argument('--all', action='store_true', help='Process all items')
    parser.add_argument('--item', type=int, help='Single item to update')

    args = parser.parse_args()

    updater = ProductionEconomicsUpdater()

    if args.item:
        print(f"Updating economics for item {args.item} in region {args.region}...")
        success = updater.update_item_economics(args.item, args.region)
        sys.exit(0 if success else 1)

    elif args.all:
        success_count, fail_count = updater.update_batch(args.region, limit=None)
        sys.exit(0 if fail_count == 0 else 1)

    else:
        limit = args.limit if args.limit else 100
        success_count, fail_count = updater.update_batch(args.region, limit=limit)
        sys.exit(0 if fail_count == 0 else 1)


if __name__ == '__main__':
    main()
