"""
Shopping List Item Operations.

Provides CRUD operations for individual items within shopping lists.
"""

from datetime import datetime
from typing import Optional

from psycopg2.extras import RealDictCursor

from src.database import get_db_connection


class ShoppingItemMixin:
    """Mixin providing shopping list item operations."""

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
