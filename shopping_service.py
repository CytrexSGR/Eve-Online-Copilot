"""
Shopping List Service for EVE Co-Pilot
Manages shopping lists with items, prices, and purchase tracking
"""

from database import get_db_connection
from psycopg2.extras import RealDictCursor
from typing import Optional, List
from datetime import datetime


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
        """Get shopping list with all items"""
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute('SELECT * FROM shopping_lists WHERE id = %s', (list_id,))
                shopping_list = cur.fetchone()

                if not shopping_list:
                    return None

                cur.execute('''
                    SELECT * FROM shopping_list_items
                    WHERE list_id = %s
                    ORDER BY is_purchased, target_region, item_name
                ''', (list_id,))
                items = cur.fetchall()

                result = dict(shopping_list)
                result['items'] = [dict(item) for item in items]
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
                    # Insert new item
                    cur.execute('''
                        INSERT INTO shopping_list_items
                            (list_id, type_id, item_name, quantity, target_region, target_price, notes)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        RETURNING *
                    ''', (list_id, type_id, item_name, quantity, target_region, target_price, notes))

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
                        is_product = TRUE,
                        updated_at = NOW()
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
                # Get products
                cur.execute('''
                    SELECT type_id, item_name, runs, total_volume
                    FROM shopping_list_items
                    WHERE list_id = %s AND is_product = TRUE
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


shopping_service = ShoppingService()
