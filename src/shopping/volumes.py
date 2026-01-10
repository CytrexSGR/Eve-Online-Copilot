"""
Shopping List Volume and Cargo Operations.

Provides volume calculation, cargo summary, and build/buy decision management.
"""

import math
from typing import Optional

from psycopg2.extras import RealDictCursor

from src.database import get_db_connection


# Region ID to name mapping for price lookup
REGION_ID_TO_NAME = {
    10000002: 'the_forge',
    10000043: 'domain',
    10000030: 'heimatar',
    10000032: 'sinq_laison',
    10000042: 'metropolis',
}


class ShoppingVolumeMixin:
    """Mixin providing volume and cargo operations for shopping lists."""

    def get_item_volume(self, type_id: int) -> Optional[float]:
        """Get volume of an item from SDE"""
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute('''
                    SELECT "volume" FROM "invTypes"
                    WHERE "typeID" = %s
                ''', (type_id,))
                result = cur.fetchone()
                return float(result['volume']) if result and result['volume'] else None

    def update_item_volume(self, item_id: int) -> dict:
        """Update volume fields for an item"""
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute('''
                    UPDATE shopping_list_items sli
                    SET volume_per_unit = t."volume",
                        total_volume = sli.quantity * t."volume"
                    FROM "invTypes" t
                    WHERE sli.id = %s AND sli.type_id = t."typeID"
                    RETURNING sli.*
                ''', (item_id,))
                conn.commit()
                result = cur.fetchone()
                return dict(result) if result else None

    def update_item_runs(
        self,
        item_id: int,
        runs: int,
        me_level: int = 10
    ) -> dict:
        """Update runs and ME level for a product item"""
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute('''
                    UPDATE shopping_list_items
                    SET runs = %s,
                        me_level = %s,
                        quantity = %s,
                        is_product = TRUE
                    WHERE id = %s
                    RETURNING *
                ''', (runs, me_level, runs, item_id))
                conn.commit()
                result = cur.fetchone()
                return dict(result) if result else None

    def update_build_decision(
        self,
        item_id: int,
        decision: str
    ) -> dict:
        """
        Update build decision (buy/build) for a sub-product item.
        If decision='build': calculate and add materials as children
        If decision='buy': remove child materials
        """
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Get the item details first
                cur.execute('SELECT * FROM shopping_list_items WHERE id = %s', (item_id,))
                item = cur.fetchone()
                if not item:
                    return None

                # Update the build decision
                cur.execute('''
                    UPDATE shopping_list_items
                    SET build_decision = %s
                    WHERE id = %s
                    RETURNING *
                ''', (decision, item_id))
                updated_item = cur.fetchone()

                # Delete ALL existing children (both materials AND sub-products)
                cur.execute('''
                    DELETE FROM shopping_list_items
                    WHERE parent_item_id = %s
                ''', (item_id,))

                if decision == 'build':
                    # Calculate materials for this sub-product recursively
                    type_id = item['type_id']
                    quantity = item['quantity']
                    me_level = item['me_level'] or 10

                    # Get blueprint/formula (activityID 1 = Manufacturing, 11 = Reactions)
                    cur.execute('''
                        SELECT bp."typeID" as blueprint_type_id, bp."activityID" as activity_id
                        FROM "industryActivityProducts" bp
                        WHERE bp."productTypeID" = %s AND bp."activityID" IN (1, 11)
                        LIMIT 1
                    ''', (type_id,))
                    blueprint_info = cur.fetchone()

                    if blueprint_info:
                        blueprint_type_id = blueprint_info['blueprint_type_id']
                        activity_id = blueprint_info['activity_id']

                        # Get materials
                        cur.execute('''
                            SELECT m."materialTypeID" as type_id, t."typeName" as name, m.quantity as base_quantity
                            FROM "industryActivityMaterials" m
                            JOIN "invTypes" t ON m."materialTypeID" = t."typeID"
                            WHERE m."typeID" = %s AND m."activityID" = %s
                        ''', (blueprint_type_id, activity_id))
                        materials = cur.fetchall()

                        if materials:
                            # Get material type IDs for price lookup
                            material_ids = [m['type_id'] for m in materials]

                            # Get cached prices
                            cur.execute('''
                                SELECT type_id, region_id, lowest_sell
                                FROM market_prices
                                WHERE type_id = ANY(%s) AND lowest_sell IS NOT NULL
                            ''', (material_ids,))

                            price_map = {}
                            for row in cur.fetchall():
                                tid = row['type_id']
                                region_name = REGION_ID_TO_NAME.get(row['region_id'])
                                if region_name:
                                    if tid not in price_map:
                                        price_map[tid] = {}
                                    price_map[tid][region_name] = float(row['lowest_sell'])

                            # Calculate and insert materials/sub-products
                            me_modifier = 1 - (me_level / 100)
                            for mat in materials:
                                # Calculate quantity
                                mat_quantity = math.ceil(mat['base_quantity'] * quantity * me_modifier)

                                # Check if this material has a blueprint (= is a sub-product)
                                cur.execute('''
                                    SELECT bp."typeID"
                                    FROM "industryActivityProducts" bp
                                    WHERE bp."productTypeID" = %s AND bp."activityID" IN (1, 11)
                                    LIMIT 1
                                ''', (mat['type_id'],))
                                has_blueprint = cur.fetchone() is not None

                                # Find best price/region
                                prices = price_map.get(mat['type_id'], {})
                                best_region = None
                                best_price = None
                                for region, price in prices.items():
                                    if best_price is None or price < best_price:
                                        best_price = price
                                        best_region = region

                                # Insert as child (is_product=True if has blueprint, FALSE otherwise)
                                cur.execute('''
                                    INSERT INTO shopping_list_items
                                    (list_id, type_id, item_name, quantity, target_region, target_price,
                                     is_product, parent_item_id, build_decision, runs, me_level)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                ''', (item['list_id'], mat['type_id'], mat['name'], mat_quantity,
                                      best_region, best_price, has_blueprint, item_id,
                                      'buy' if has_blueprint else None,
                                      mat_quantity if has_blueprint else 1,
                                      10))

                conn.commit()
                return dict(updated_item) if updated_item else None

    def get_cargo_summary(self, list_id: int) -> dict:
        """Get cargo volume summary for a shopping list"""
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Get products with output_per_run from blueprint data
                cur.execute('''
                    SELECT
                        sli.type_id,
                        sli.item_name,
                        sli.runs,
                        sli.total_volume,
                        sli.me_level,
                        COALESCE(bp."quantity", 1) as output_per_run
                    FROM shopping_list_items sli
                    LEFT JOIN "industryActivityProducts" bp
                        ON bp."productTypeID" = sli.type_id AND bp."activityID" IN (1, 11)
                    WHERE sli.list_id = %s AND sli.is_product = TRUE
                ''', (list_id,))
                products = [dict(row) for row in cur.fetchall()]

                # Get materials summary
                cur.execute('''
                    SELECT
                        COUNT(*) as total_items,
                        COALESCE(SUM(total_volume), 0) as total_volume_m3,
                        target_region
                    FROM shopping_list_items
                    WHERE list_id = %s AND is_product = FALSE
                    GROUP BY target_region
                ''', (list_id,))
                by_region = [dict(row) for row in cur.fetchall()]

                # Total materials volume
                cur.execute('''
                    SELECT
                        COUNT(*) as total_items,
                        COALESCE(SUM(total_volume), 0) as total_volume_m3
                    FROM shopping_list_items
                    WHERE list_id = %s AND is_product = FALSE
                ''', (list_id,))
                totals = dict(cur.fetchone())

                return {
                    'list_id': list_id,
                    'products': products,
                    'materials': {
                        'total_items': totals['total_items'],
                        'total_volume_m3': float(totals['total_volume_m3']),
                        'volume_formatted': self._format_volume(float(totals['total_volume_m3'])),
                        'breakdown_by_region': {
                            row['target_region'] or 'unassigned': {
                                'volume_m3': float(row['total_volume_m3']),
                                'item_count': row['total_items']
                            }
                            for row in by_region
                        }
                    }
                }

    def _format_volume(self, volume: float) -> str:
        """Format volume for display"""
        if volume >= 1_000_000:
            return f"{volume / 1_000_000:.2f}M m³"
        if volume >= 1_000:
            return f"{volume / 1_000:.1f}K m³"
        return f"{volume:.0f} m³"
