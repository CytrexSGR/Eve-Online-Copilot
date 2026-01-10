"""
Shopping List Wizard Operations.

Provides step-based wizard workflow for material calculation and comparison.
"""

import math
from typing import Optional, List

from psycopg2.extras import RealDictCursor

from src.database import get_db_connection


# Region ID to name mapping
REGION_ID_TO_NAME = {
    10000002: 'the_forge',
    10000043: 'domain',
    10000030: 'heimatar',
    10000032: 'sinq_laison',
    10000042: 'metropolis',
}


class ShoppingWizardMixin:
    """Mixin providing wizard workflow operations for shopping lists."""

    def calculate_materials_for_wizard(
        self,
        product_type_id: int,
        runs: int = 1,
        me_level: int = 10,
        decisions: dict = None
    ) -> Optional[dict]:
        """
        Calculate materials for a product with build/buy decisions.
        Used by the new step-based shopping wizard.

        Args:
            product_type_id: Type ID of the product to build
            runs: Number of blueprint runs
            me_level: Material Efficiency level (0-10)
            decisions: Dict of {type_id: 'buy'|'build'} for sub-components

        Returns:
            {
                'product': {...},
                'sub_components': [...],  # List with decisions
                'shopping_list': [...],   # Flattened list of items to buy
                'totals': {...}           # Cost totals by category
            }
        """
        if decisions is None:
            decisions = {}

        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Get product info
                cur.execute('''
                    SELECT "typeID" as type_id, "typeName" as type_name, "volume"
                    FROM "invTypes"
                    WHERE "typeID" = %s
                ''', (product_type_id,))
                product_info = cur.fetchone()

                if not product_info:
                    return None

                # Get blueprint/formula info
                cur.execute('''
                    SELECT bp."typeID" as blueprint_type_id,
                           bp."quantity" as output_per_run,
                           bp."activityID" as activity_id
                    FROM "industryActivityProducts" bp
                    WHERE bp."productTypeID" = %s AND bp."activityID" IN (1, 11)
                    LIMIT 1
                ''', (product_type_id,))
                blueprint_info = cur.fetchone()

                if not blueprint_info:
                    return None

                blueprint_type_id = blueprint_info['blueprint_type_id']
                output_per_run = blueprint_info['output_per_run'] or 1
                activity_id = blueprint_info['activity_id']

                # Get materials from industryActivityMaterials
                cur.execute('''
                    SELECT
                        m."materialTypeID" as type_id,
                        t."typeName" as item_name,
                        m."quantity" as base_quantity,
                        t."volume" as volume
                    FROM "industryActivityMaterials" m
                    JOIN "invTypes" t ON m."materialTypeID" = t."typeID"
                    WHERE m."typeID" = %s AND m."activityID" = %s
                    ORDER BY t."typeName"
                ''', (blueprint_type_id, activity_id))
                raw_materials = cur.fetchall()

                # Separate into materials and sub-components
                materials = []
                sub_components = []

                for mat in raw_materials:
                    mat_type_id = mat['type_id']

                    # Check if this material can be built
                    cur.execute('''
                        SELECT bp."typeID"
                        FROM "industryActivityProducts" bp
                        WHERE bp."productTypeID" = %s AND bp."activityID" IN (1, 11)
                        LIMIT 1
                    ''', (mat_type_id,))
                    has_blueprint = cur.fetchone() is not None

                    # Calculate quantity (ME only applies to raw materials)
                    calculated_qty = self._calculate_material_quantity(
                        mat['base_quantity'], runs, me_level, apply_me=(not has_blueprint)
                    )

                    material_data = {
                        'type_id': mat_type_id,
                        'item_name': mat['item_name'],
                        'quantity': calculated_qty,
                        'base_quantity': mat['base_quantity'],
                        'volume': float(mat['volume']) if mat['volume'] else 0,
                        'has_blueprint': has_blueprint
                    }

                    if has_blueprint:
                        # Get decision for this sub-component
                        decision = decisions.get(str(mat_type_id), 'buy')
                        material_data['decision'] = decision
                        sub_components.append(material_data)
                    else:
                        materials.append(material_data)

                # Build the shopping list based on decisions
                shopping_list = []
                aggregated = {}  # type_id -> aggregated item

                def add_to_shopping_list(item, category):
                    """Add item to shopping list, aggregating duplicates"""
                    tid = item['type_id']
                    if tid in aggregated:
                        aggregated[tid]['quantity'] += item['quantity']
                    else:
                        aggregated[tid] = {
                            'type_id': tid,
                            'item_name': item['item_name'],
                            'quantity': item['quantity'],
                            'volume': item.get('volume', 0),
                            'category': category
                        }

                # Add raw materials from main product
                for mat in materials:
                    add_to_shopping_list(mat, 'material')

                # Process sub-components based on decisions
                for sub in sub_components:
                    decision = sub.get('decision', 'buy')
                    if decision == 'buy':
                        add_to_shopping_list(sub, 'sub_component')
                    else:
                        # Build: recursively get materials for this sub-component
                        sub_mats = self._get_build_materials(
                            cur, sub['type_id'], sub['quantity'], me_level
                        )
                        for sm in sub_mats:
                            add_to_shopping_list(sm, 'material')

                # Convert aggregated dict to list
                shopping_list = list(aggregated.values())

                # Get prices for all items
                all_type_ids = [item['type_id'] for item in shopping_list]
                if all_type_ids:
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

                    # Add prices to shopping list
                    for item in shopping_list:
                        prices = price_map.get(item['type_id'], {})
                        best_region, best_price = self._get_best_price(prices)
                        item['jita_sell'] = prices.get('the_forge')
                        item['best_price'] = best_price
                        item['best_region'] = best_region
                        item['total_cost'] = (best_price or 0) * item['quantity']

                # Calculate totals
                sub_component_total = sum(
                    item['total_cost'] for item in shopping_list
                    if item['category'] == 'sub_component'
                )
                material_total = sum(
                    item['total_cost'] for item in shopping_list
                    if item['category'] == 'material'
                )

                return {
                    'product': {
                        'type_id': product_type_id,
                        'name': product_info['type_name'],
                        'runs': runs,
                        'me_level': me_level,
                        'output_per_run': output_per_run,
                        'total_output': runs * output_per_run
                    },
                    'sub_components': sub_components,
                    'shopping_list': shopping_list,
                    'totals': {
                        'sub_components': sub_component_total,
                        'raw_materials': material_total,
                        'grand_total': sub_component_total + material_total
                    }
                }

    def _get_build_materials(
        self,
        cur,
        type_id: int,
        quantity: int,
        me_level: int = 10
    ) -> List[dict]:
        """
        Get materials needed to build a sub-component.
        Recursively resolves nested buildable items (all set to 'buy').
        """
        # Get blueprint info
        cur.execute('''
            SELECT bp."typeID" as blueprint_type_id,
                   bp."quantity" as output_per_run,
                   bp."activityID" as activity_id
            FROM "industryActivityProducts" bp
            WHERE bp."productTypeID" = %s AND bp."activityID" IN (1, 11)
            LIMIT 1
        ''', (type_id,))
        bp_info = cur.fetchone()

        if not bp_info:
            return []

        # Calculate runs needed
        output_per_run = bp_info['output_per_run'] or 1
        runs_needed = math.ceil(quantity / output_per_run)

        # Get materials
        cur.execute('''
            SELECT
                m."materialTypeID" as type_id,
                t."typeName" as item_name,
                m."quantity" as base_quantity,
                t."volume" as volume
            FROM "industryActivityMaterials" m
            JOIN "invTypes" t ON m."materialTypeID" = t."typeID"
            WHERE m."typeID" = %s AND m."activityID" = %s
        ''', (bp_info['blueprint_type_id'], bp_info['activity_id']))
        raw_mats = cur.fetchall()

        result = []
        for mat in raw_mats:
            mat_type_id = mat['type_id']

            # Check if buildable (but we treat as buy for simplicity)
            cur.execute('''
                SELECT bp."typeID"
                FROM "industryActivityProducts" bp
                WHERE bp."productTypeID" = %s AND bp."activityID" IN (1, 11)
                LIMIT 1
            ''', (mat_type_id,))
            has_blueprint = cur.fetchone() is not None

            # Calculate quantity with ME
            calc_qty = self._calculate_material_quantity(
                mat['base_quantity'], runs_needed, me_level, apply_me=(not has_blueprint)
            )

            result.append({
                'type_id': mat_type_id,
                'item_name': mat['item_name'],
                'quantity': calc_qty,
                'volume': float(mat['volume']) if mat['volume'] else 0
            })

        return result
