"""
Shopping List Material Calculation Operations.

Provides material calculation, application, and product hierarchy management.
"""

import math
from typing import Optional, List

from psycopg2.extras import RealDictCursor

from src.database import get_db_connection
from services.production.chain_service import ProductionChainService


# Region mapping for price lookup
REGION_ID_TO_NAME = {
    10000002: 'the_forge',
    10000043: 'domain',
    10000030: 'heimatar',
    10000032: 'sinq_laison',
    10000042: 'metropolis',
}


class ShoppingMaterialsMixin:
    """Mixin providing material calculation operations for shopping lists."""

    def _calculate_material_quantity(self, base_quantity: int, runs: int, me_level: int, apply_me: bool = True) -> int:
        """
        Calculate material quantity using EVE Online ME formula.

        Args:
            base_quantity: Base quantity from blueprint
            runs: Number of blueprint runs
            me_level: Material Efficiency level (0-10)
            apply_me: Whether to apply ME reduction. False for sub-products/components,
                      True for raw materials (minerals, PI, etc.)

        EVE Online rules:
        - ME reduces raw material costs (minerals, etc.)
        - ME does NOT reduce the number of sub-products needed (Capital Components, T2 parts)
        """
        if apply_me:
            me_modifier = 1 - (me_level / 100)
            return math.ceil(base_quantity * runs * me_modifier)
        else:
            # Sub-products: no ME reduction, just multiply by runs
            return base_quantity * runs

    def calculate_materials(self, item_id: int) -> Optional[dict]:
        """
        Calculate materials for a product item using new Production Chains API.
        Returns materials and sub-products (items that can also be built).
        """
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Get product item details
                cur.execute('''
                    SELECT id, list_id, type_id, item_name, runs, me_level, is_product
                    FROM shopping_list_items
                    WHERE id = %s
                ''', (item_id,))
                product = cur.fetchone()

                if not product or not product['is_product']:
                    return None

                type_id = product['type_id']
                runs = product['runs'] or 1
                me_level = product['me_level'] or 10

                # Get blueprint output info for total_output calculation
                cur.execute('''
                    SELECT bp."quantity" as output_per_run
                    FROM "industryActivityProducts" bp
                    WHERE bp."productTypeID" = %s AND bp."activityID" IN (1, 11)
                    LIMIT 1
                ''', (type_id,))
                blueprint_info = cur.fetchone()

                if not blueprint_info:
                    return None

                output_per_run = blueprint_info['output_per_run'] or 1

                # Use Production Chains API to get materials
                chain_service = ProductionChainService()
                materials_data = chain_service.get_materials_list(type_id, me=me_level, runs=runs)

                if not materials_data or 'materials' not in materials_data:
                    return None

                # Separate materials from sub-products
                materials = []
                sub_products = []

                for mat in materials_data['materials']:
                    mat_type_id = mat['type_id']

                    # Check if this material has a blueprint (is a sub-product)
                    cur.execute('''
                        SELECT bp."typeID"
                        FROM "industryActivityProducts" bp
                        WHERE bp."productTypeID" = %s AND bp."activityID" IN (1, 11)
                        LIMIT 1
                    ''', (mat_type_id,))
                    has_blueprint = cur.fetchone() is not None

                    # Get volume info
                    cur.execute('''
                        SELECT "volume" FROM "invTypes" WHERE "typeID" = %s
                    ''', (mat_type_id,))
                    volume_result = cur.fetchone()
                    volume = float(volume_result['volume']) if volume_result and volume_result['volume'] else 0

                    material_data = {
                        'type_id': mat_type_id,
                        'item_name': mat['name'],
                        'quantity': mat['adjusted_quantity'],
                        'base_quantity': mat['base_quantity'],
                        'volume': volume,
                        'has_blueprint': has_blueprint
                    }

                    if has_blueprint:
                        material_data['default_decision'] = 'buy'
                        sub_products.append(material_data)
                    else:
                        materials.append(material_data)

                return {
                    'product': {
                        'id': product['id'],
                        'type_id': type_id,
                        'item_name': product['item_name'],
                        'runs': runs,
                        'me_level': me_level,
                        'output_per_run': output_per_run,
                        'total_output': runs * output_per_run
                    },
                    'materials': materials,
                    'sub_products': sub_products
                }

    def apply_materials(
        self,
        parent_item_id: int,
        materials: List[dict],
        sub_product_decisions: List[dict]
    ) -> dict:
        """
        Apply calculated materials to shopping list.
        - Deletes existing child materials
        - Adds new materials with parent_item_id
        - For sub-products marked 'build': adds as product and recursively calculates
        """
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Get parent item details
                cur.execute('''
                    SELECT list_id, type_id, item_name FROM shopping_list_items WHERE id = %s
                ''', (parent_item_id,))
                parent = cur.fetchone()

                if not parent:
                    return {'error': 'Parent item not found'}

                list_id = parent['list_id']

                # Delete existing child materials for this parent
                cur.execute('''
                    DELETE FROM shopping_list_items
                    WHERE parent_item_id = %s
                ''', (parent_item_id,))
                deleted_count = cur.rowcount

                # Build decision map: {type_id: 'buy' | 'build'}
                decision_map = {d['type_id']: d['decision'] for d in sub_product_decisions}

                # Get prices for all material types
                all_type_ids = [m['type_id'] for m in materials]
                all_type_ids.extend([sp['type_id'] for sp in sub_product_decisions])

                cur.execute('''
                    SELECT type_id, region_id, lowest_sell
                    FROM market_prices
                    WHERE type_id = ANY(%s) AND lowest_sell IS NOT NULL
                ''', (all_type_ids,))

                price_map = {}
                for row in cur.fetchall():
                    tid = row['type_id']
                    region_name = REGION_ID_TO_NAME.get(row['region_id'])
                    if region_name:
                        if tid not in price_map:
                            price_map[tid] = {}
                        price_map[tid][region_name] = float(row['lowest_sell'])

                added_materials = []
                added_sub_products = []

                # Add regular materials
                for mat in materials:
                    prices = price_map.get(mat['type_id'], {})
                    best_region, best_price = self._get_best_price(prices)

                    # Get volume
                    cur.execute('SELECT "volume" FROM "invTypes" WHERE "typeID" = %s', (mat['type_id'],))
                    vol_row = cur.fetchone()
                    volume = float(vol_row['volume']) if vol_row and vol_row['volume'] else 0

                    cur.execute('''
                        INSERT INTO shopping_list_items
                            (list_id, type_id, item_name, quantity, target_region, target_price,
                             is_product, parent_item_id, volume_per_unit, total_volume)
                        VALUES (%s, %s, %s, %s, %s, %s, FALSE, %s, %s, %s)
                        RETURNING *
                    ''', (
                        list_id, mat['type_id'], mat['item_name'], mat['quantity'],
                        best_region, best_price, parent_item_id, volume, volume * mat['quantity']
                    ))
                    added_materials.append(dict(cur.fetchone()))

                # Handle sub-products based on decision
                for sp in sub_product_decisions:
                    decision = sp.get('decision', 'buy')
                    sp_type_id = sp['type_id']

                    prices = price_map.get(sp_type_id, {})
                    best_region, best_price = self._get_best_price(prices)

                    # Get volume
                    cur.execute('SELECT "volume" FROM "invTypes" WHERE "typeID" = %s', (sp_type_id,))
                    vol_row = cur.fetchone()
                    volume = float(vol_row['volume']) if vol_row and vol_row['volume'] else 0

                    if decision == 'build':
                        # Add as product (is_product=True) with default ME=10
                        cur.execute('''
                            INSERT INTO shopping_list_items
                                (list_id, type_id, item_name, quantity, target_region, target_price,
                                 is_product, runs, me_level, parent_item_id, build_decision,
                                 volume_per_unit, total_volume)
                            VALUES (%s, %s, %s, %s, %s, %s, TRUE, %s, 10, %s, 'build', %s, %s)
                            RETURNING *
                        ''', (
                            list_id, sp_type_id, sp['item_name'], sp['quantity'],
                            best_region, best_price, sp['quantity'], parent_item_id,
                            volume, volume * sp['quantity']
                        ))
                        sub_product = dict(cur.fetchone())
                        added_sub_products.append(sub_product)

                        # Recursively calculate materials for this sub-product
                        conn.commit()  # Commit to make the new item visible
                        sub_materials = self.calculate_materials(sub_product['id'])
                        if sub_materials and (sub_materials['materials'] or sub_materials['sub_products']):
                            # Auto-apply sub-product materials (all as 'buy')
                            sub_decisions = [
                                {'type_id': m['type_id'], 'item_name': m['item_name'],
                                 'quantity': m['quantity'], 'decision': 'buy'}
                                for m in sub_materials.get('sub_products', [])
                            ]
                            self.apply_materials(
                                sub_product['id'],
                                sub_materials['materials'],
                                sub_decisions
                            )
                    else:
                        # decision == 'buy'
                        # Still add as product (is_product=True) so it can be toggled to 'build' later
                        cur.execute('''
                            INSERT INTO shopping_list_items
                                (list_id, type_id, item_name, quantity, target_region, target_price,
                                 is_product, parent_item_id, build_decision, runs, me_level,
                                 volume_per_unit, total_volume)
                            VALUES (%s, %s, %s, %s, %s, %s, TRUE, %s, 'buy', %s, 10, %s, %s)
                            RETURNING *
                        ''', (
                            list_id, sp_type_id, sp['item_name'], sp['quantity'],
                            best_region, best_price, parent_item_id, sp['quantity'],
                            volume, volume * sp['quantity']
                        ))
                        added_sub_products.append(dict(cur.fetchone()))

                conn.commit()
                self._update_list_totals(list_id)

                return {
                    'parent_id': parent_item_id,
                    'deleted_count': deleted_count,
                    'added_materials': len(added_materials),
                    'added_sub_products': len(added_sub_products),
                    'materials': added_materials,
                    'sub_products': added_sub_products
                }

    def _get_best_price(self, prices: dict) -> tuple:
        """Get best (lowest) price and region from price map"""
        best_region = None
        best_price = None
        for region, price in prices.items():
            if price and (best_price is None or price < best_price):
                best_price = price
                best_region = region
        return best_region, best_price

    def get_product_with_materials(self, item_id: int) -> Optional[dict]:
        """Get a product item with its materials hierarchy"""
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Get the product
                cur.execute('''
                    SELECT * FROM shopping_list_items WHERE id = %s
                ''', (item_id,))
                product = cur.fetchone()

                if not product:
                    return None

                result = dict(product)

                # Get child materials
                cur.execute('''
                    SELECT * FROM shopping_list_items
                    WHERE parent_item_id = %s
                    ORDER BY is_product DESC, item_name
                ''', (item_id,))
                children = [dict(row) for row in cur.fetchall()]

                # Separate materials and sub-products
                result['materials'] = [c for c in children if not c['is_product']]
                result['sub_products'] = []

                # Recursively get sub-product materials
                for child in children:
                    if child['is_product']:
                        sub_with_materials = self.get_product_with_materials(child['id'])
                        if sub_with_materials:
                            result['sub_products'].append(sub_with_materials)

                result['materials_calculated'] = len(children) > 0

                return result
