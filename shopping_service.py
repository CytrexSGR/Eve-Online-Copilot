"""
Shopping List Service for EVE Co-Pilot
Manages shopping lists with items, prices, and purchase tracking
"""

from database import get_db_connection
from psycopg2.extras import RealDictCursor
from typing import Optional, List
from datetime import datetime
import math


class ShoppingService:

    def create_list(
        self,
        name: str,
        character_id: Optional[int] = None,
        corporation_id: Optional[int] = None,
        notes: Optional[str] = None
    ) -> dict:
        """Create a new shopping list"""
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute('''
                    INSERT INTO shopping_lists (name, character_id, corporation_id, notes)
                    VALUES (%s, %s, %s, %s)
                    RETURNING *
                ''', (name, character_id, corporation_id, notes))
                conn.commit()
                return dict(cur.fetchone())

    def get_lists(
        self,
        character_id: Optional[int] = None,
        corporation_id: Optional[int] = None,
        status: Optional[str] = None
    ) -> List[dict]:
        """Get shopping lists with optional filters"""
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                where_clauses = []
                params = []

                if character_id:
                    where_clauses.append("character_id = %s")
                    params.append(character_id)
                if corporation_id:
                    where_clauses.append("corporation_id = %s")
                    params.append(corporation_id)
                if status:
                    where_clauses.append("status = %s")
                    params.append(status)

                where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

                cur.execute(f'''
                    SELECT sl.*,
                           (SELECT COUNT(*) FROM shopping_list_items WHERE list_id = sl.id) as item_count,
                           (SELECT COUNT(*) FROM shopping_list_items WHERE list_id = sl.id AND is_purchased) as purchased_count
                    FROM shopping_lists sl
                    WHERE {where_sql}
                    ORDER BY sl.created_at DESC
                ''', params)
                return [dict(row) for row in cur.fetchall()]

    def get_list(self, list_id: int) -> Optional[dict]:
        """Get a single shopping list by ID"""
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute('SELECT * FROM shopping_lists WHERE id = %s', (list_id,))
                result = cur.fetchone()
                return dict(result) if result else None

    def get_list_with_items(self, list_id: int) -> Optional[dict]:
        """Get shopping list with all items in hierarchical structure"""
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute('SELECT * FROM shopping_lists WHERE id = %s', (list_id,))
                shopping_list = cur.fetchone()

                if not shopping_list:
                    return None

                # Get all items for this list
                # activityID 1 = Manufacturing, 11 = Reactions
                cur.execute('''
                    SELECT sli.*,
                           COALESCE(bp."quantity", 1) as output_per_run
                    FROM shopping_list_items sli
                    LEFT JOIN "industryActivityProducts" bp
                        ON bp."productTypeID" = sli.type_id AND bp."activityID" IN (1, 11)
                    WHERE sli.list_id = %s
                    ORDER BY sli.is_purchased, sli.is_product DESC, sli.item_name
                ''', (list_id,))
                all_items = [dict(item) for item in cur.fetchall()]

                # Build item map for hierarchy
                item_map = {item['id']: item for item in all_items}

                # Separate into products (top-level) and standalone items
                products = []
                standalone_items = []
                flat_items = []  # Legacy flat list for backward compatibility

                for item in all_items:
                    flat_items.append(item)

                    if item['parent_item_id'] is None:
                        if item['is_product']:
                            # Get materials for this product
                            item['materials'] = [
                                i for i in all_items
                                if i['parent_item_id'] == item['id'] and not i['is_product']
                            ]
                            item['sub_products'] = []
                            # Get sub-products (recursive would be better but keeping simple)
                            for sub in all_items:
                                if sub['parent_item_id'] == item['id'] and sub['is_product']:
                                    sub['materials'] = [
                                        i for i in all_items
                                        if i['parent_item_id'] == sub['id'] and not i['is_product']
                                    ]
                                    sub['sub_products'] = []
                                    item['sub_products'].append(sub)

                            item['materials_calculated'] = len(item['materials']) > 0 or len(item['sub_products']) > 0
                            products.append(item)
                        else:
                            standalone_items.append(item)

                result = dict(shopping_list)
                result['items'] = flat_items  # Backward compatibility
                result['products'] = products
                result['standalone_items'] = standalone_items
                return result

    def update_list(
        self,
        list_id: int,
        name: Optional[str] = None,
        status: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Optional[dict]:
        """Update shopping list"""
        updates = []
        params = []

        if name is not None:
            updates.append("name = %s")
            params.append(name)
        if status is not None:
            updates.append("status = %s")
            params.append(status)
        if notes is not None:
            updates.append("notes = %s")
            params.append(notes)

        if not updates:
            return self.get_list(list_id)

        updates.append("updated_at = %s")
        params.append(datetime.now())
        params.append(list_id)

        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(f'''
                    UPDATE shopping_lists
                    SET {", ".join(updates)}
                    WHERE id = %s
                    RETURNING *
                ''', params)
                conn.commit()
                result = cur.fetchone()
                return dict(result) if result else None

    def delete_list(self, list_id: int) -> bool:
        """Delete a shopping list"""
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('DELETE FROM shopping_lists WHERE id = %s', (list_id,))
                conn.commit()
                return cur.rowcount > 0

    # ============================================================
    # Shopping List Items
    # ============================================================

    def add_item(
        self,
        list_id: int,
        type_id: int,
        item_name: str,
        quantity: int,
        target_region: Optional[str] = None,
        target_price: Optional[float] = None,
        notes: Optional[str] = None
    ) -> dict:
        """Add item to shopping list"""
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Check if item has a blueprint or reaction formula (= is a product)
                # activityID 1 = Manufacturing, 11 = Reactions
                cur.execute('''
                    SELECT bp."typeID"
                    FROM "industryActivityProducts" bp
                    WHERE bp."productTypeID" = %s AND bp."activityID" IN (1, 11)
                    LIMIT 1
                ''', (type_id,))
                has_blueprint = cur.fetchone() is not None

                # Get volume from SDE
                cur.execute('SELECT "volume" FROM "invTypes" WHERE "typeID" = %s', (type_id,))
                volume_row = cur.fetchone()
                volume_per_unit = float(volume_row['volume']) if volume_row and volume_row['volume'] else None

                # Check if item already exists in list
                cur.execute('''
                    SELECT id, quantity FROM shopping_list_items
                    WHERE list_id = %s AND type_id = %s AND target_region = %s AND NOT is_purchased
                ''', (list_id, type_id, target_region))
                existing = cur.fetchone()

                if existing:
                    # Update quantity
                    new_quantity = existing['quantity'] + quantity
                    cur.execute('''
                        UPDATE shopping_list_items
                        SET quantity = %s, target_price = COALESCE(%s, target_price)
                        WHERE id = %s
                        RETURNING *
                    ''', (new_quantity, target_price, existing['id']))
                else:
                    # Insert new item - mark as product if has blueprint
                    cur.execute('''
                        INSERT INTO shopping_list_items
                            (list_id, type_id, item_name, quantity, target_region, target_price, notes,
                             is_product, runs, volume_per_unit, total_volume)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING *
                    ''', (list_id, type_id, item_name, quantity, target_region, target_price, notes,
                          has_blueprint, quantity if has_blueprint else 1,
                          volume_per_unit, volume_per_unit * quantity if volume_per_unit else None))

                conn.commit()
                self._update_list_totals(list_id)
                return dict(cur.fetchone())

    def update_item(
        self,
        item_id: int,
        quantity: Optional[int] = None,
        target_region: Optional[str] = None,
        target_price: Optional[float] = None,
        notes: Optional[str] = None
    ) -> Optional[dict]:
        """Update a shopping list item"""
        updates = []
        params = []

        if quantity is not None:
            updates.append("quantity = %s")
            params.append(quantity)
        if target_region is not None:
            updates.append("target_region = %s")
            params.append(target_region)
        if target_price is not None:
            updates.append("target_price = %s")
            params.append(target_price)
        if notes is not None:
            updates.append("notes = %s")
            params.append(notes)

        if not updates:
            return None

        params.append(item_id)

        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(f'''
                    UPDATE shopping_list_items
                    SET {", ".join(updates)}
                    WHERE id = %s
                    RETURNING *
                ''', params)
                conn.commit()
                result = cur.fetchone()
                if result:
                    self._update_list_totals(result['list_id'])
                return dict(result) if result else None

    def remove_item(self, item_id: int) -> bool:
        """Remove item from shopping list"""
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Get list_id before deleting
                cur.execute('SELECT list_id FROM shopping_list_items WHERE id = %s', (item_id,))
                row = cur.fetchone()
                if not row:
                    return False

                list_id = row['list_id']
                cur.execute('DELETE FROM shopping_list_items WHERE id = %s', (item_id,))
                conn.commit()
                self._update_list_totals(list_id)
                return cur.rowcount > 0

    def mark_purchased(
        self,
        item_id: int,
        actual_price: Optional[float] = None
    ) -> Optional[dict]:
        """Mark item as purchased"""
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute('''
                    UPDATE shopping_list_items
                    SET is_purchased = TRUE, purchased_at = %s, actual_price = COALESCE(%s, target_price)
                    WHERE id = %s
                    RETURNING *
                ''', (datetime.now(), actual_price, item_id))
                conn.commit()
                result = cur.fetchone()
                if result:
                    self._update_list_totals(result['list_id'])
                return dict(result) if result else None

    def unmark_purchased(self, item_id: int) -> Optional[dict]:
        """Unmark item as purchased"""
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute('''
                    UPDATE shopping_list_items
                    SET is_purchased = FALSE, purchased_at = NULL, actual_price = NULL
                    WHERE id = %s
                    RETURNING *
                ''', (item_id,))
                conn.commit()
                result = cur.fetchone()
                if result:
                    self._update_list_totals(result['list_id'])
                return dict(result) if result else None

    def _update_list_totals(self, list_id: int):
        """Update list total cost and volume"""
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    UPDATE shopping_lists
                    SET total_cost = (
                        SELECT COALESCE(SUM(COALESCE(actual_price, target_price) * quantity), 0)
                        FROM shopping_list_items WHERE list_id = %s
                    ),
                    updated_at = %s
                    WHERE id = %s
                ''', (list_id, datetime.now(), list_id))
                conn.commit()

    # ============================================================
    # Volume Calculation Methods
    # ============================================================

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
                # Get item and its volume from SDE
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

    # ============================================================
    # Bulk Operations
    # ============================================================

    def add_materials_from_production(
        self,
        list_id: int,
        type_id: int,
        me_level: int = 10,
        runs: int = 1
    ) -> List[dict]:
        """Add all materials for producing an item to the shopping list"""
        from database import get_db_connection

        # Region ID to name mapping
        REGION_ID_TO_NAME = {
            10000002: 'the_forge',
            10000043: 'domain',
            10000030: 'heimatar',
            10000032: 'sinq_laison',
            10000042: 'metropolis',
        }

        # Get materials and their cached prices in a single query
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Get materials for this product
                cur.execute("""
                    SELECT m."materialTypeID" as type_id, t."typeName" as name, m.quantity
                    FROM "invTypeMaterials" m
                    JOIN "invTypes" t ON m."materialTypeID" = t."typeID"
                    WHERE m."typeID" = %s
                """, (type_id,))
                materials = cur.fetchall()

                if not materials:
                    return []

                # Get all material type IDs
                material_ids = [m['type_id'] for m in materials]

                # Get cached prices for all materials at once
                cur.execute("""
                    SELECT type_id, region_id, lowest_sell
                    FROM market_prices
                    WHERE type_id = ANY(%s) AND lowest_sell IS NOT NULL
                """, (material_ids,))

                # Build price map: {type_id: {region_name: lowest_sell}}
                price_map = {}
                for row in cur.fetchall():
                    tid = row['type_id']
                    region_name = REGION_ID_TO_NAME.get(row['region_id'])
                    if not region_name:
                        continue
                    if tid not in price_map:
                        price_map[tid] = {}
                    price_map[tid][region_name] = float(row['lowest_sell'])

        me_factor = 1 - (me_level / 100)
        added_items = []

        for mat in materials:
            adjusted_qty = max(1, int(mat['quantity'] * me_factor * runs))

            # Get best price from cached data
            prices = price_map.get(mat['type_id'], {})
            best_region = None
            best_price = float('inf')

            for region, price in prices.items():
                if price and price < best_price:
                    best_price = price
                    best_region = region

            item = self.add_item(
                list_id=list_id,
                type_id=mat['type_id'],
                item_name=mat['name'],
                quantity=adjusted_qty,
                target_region=best_region,
                target_price=best_price if best_price != float('inf') else None
            )
            added_items.append(item)

        return added_items

    def export_multibuy(self, list_id: int, region: Optional[str] = None) -> str:
        """Export shopping list in EVE Multibuy format"""
        list_data = self.get_list_with_items(list_id)
        if not list_data:
            return ""

        lines = []
        for item in list_data['items']:
            if item['is_purchased']:
                continue
            if region and item['target_region'] != region:
                continue
            lines.append(f"{item['item_name']} {item['quantity']}")

        return "\n".join(lines)

    def get_by_region(self, list_id: int) -> dict:
        """Get shopping list items grouped by region"""
        list_data = self.get_list_with_items(list_id)
        if not list_data:
            return {}

        by_region = {}
        for item in list_data['items']:
            region = item['target_region'] or 'unassigned'
            if region not in by_region:
                by_region[region] = {
                    'items': [],
                    'total_cost': 0,
                    'item_count': 0
                }
            by_region[region]['items'].append(item)
            by_region[region]['item_count'] += 1
            if item['target_price']:
                by_region[region]['total_cost'] += item['target_price'] * item['quantity']

        return by_region

    # ============================================================
    # Material Calculation Methods
    # ============================================================

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
        Calculate materials for a product item.
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

                # Get blueprint/formula type ID for this product
                # activityID 1 = Manufacturing, 11 = Reactions
                cur.execute('''
                    SELECT bp."typeID" as blueprint_type_id, bp."quantity" as output_per_run, bp."activityID" as activity_id
                    FROM "industryActivityProducts" bp
                    WHERE bp."productTypeID" = %s AND bp."activityID" IN (1, 11)
                    LIMIT 1
                ''', (type_id,))
                blueprint_info = cur.fetchone()

                if not blueprint_info:
                    return None

                blueprint_type_id = blueprint_info['blueprint_type_id']
                output_per_run = blueprint_info['output_per_run'] or 1
                activity_id = blueprint_info['activity_id']  # 1 for manufacturing, 11 for reactions

                # Get materials from industryActivityMaterials
                # Use the same activityID as the blueprint/formula
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

                # Calculate quantities and check for sub-products
                materials = []
                sub_products = []

                for mat in raw_materials:
                    mat_type_id = mat['type_id']

                    # Check if this material has a blueprint or reaction formula (= is a sub-product)
                    # activityID 1 = Manufacturing, 11 = Reactions
                    cur.execute('''
                        SELECT bp."typeID"
                        FROM "industryActivityProducts" bp
                        WHERE bp."productTypeID" = %s AND bp."activityID" IN (1, 11)
                        LIMIT 1
                    ''', (mat_type_id,))
                    has_blueprint = cur.fetchone() is not None

                    # EVE Online rule: ME only applies to raw materials, NOT to sub-products
                    # Sub-products (Capital Components, T2 parts, etc.) require exact quantities
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
        # Region mapping for price lookup
        REGION_ID_TO_NAME = {
            10000002: 'the_forge',
            10000043: 'domain',
            10000030: 'heimatar',
            10000032: 'sinq_laison',
            10000042: 'metropolis',
        }

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
                        # Add as material (is_product=False)
                        cur.execute('''
                            INSERT INTO shopping_list_items
                                (list_id, type_id, item_name, quantity, target_region, target_price,
                                 is_product, parent_item_id, build_decision, volume_per_unit, total_volume)
                            VALUES (%s, %s, %s, %s, %s, %s, FALSE, %s, 'buy', %s, %s)
                            RETURNING *
                        ''', (
                            list_id, sp_type_id, sp['item_name'], sp['quantity'],
                            best_region, best_price, parent_item_id, volume, volume * sp['quantity']
                        ))
                        added_materials.append(dict(cur.fetchone()))

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


shopping_service = ShoppingService()
