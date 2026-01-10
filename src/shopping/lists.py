"""
Shopping List CRUD Operations.

Provides create, read, update, delete operations for shopping lists.
"""

from datetime import datetime
from typing import Optional, List

from psycopg2.extras import RealDictCursor

from src.database import get_db_connection


class ShoppingListMixin:
    """Mixin providing shopping list CRUD operations."""

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

                # Helper function to recursively build product tree
                def build_product_tree(parent_id: int, all_items: list) -> tuple:
                    """Recursively build materials and sub_products for a given parent"""
                    materials = []
                    sub_products = []

                    for item in all_items:
                        if item['parent_item_id'] == parent_id:
                            if item['is_product']:
                                # This is a sub-product - recursively get its children
                                item['materials'], item['sub_products'] = build_product_tree(item['id'], all_items)
                                item['materials_calculated'] = len(item['materials']) > 0 or len(item['sub_products']) > 0
                                sub_products.append(item)
                            else:
                                # This is a raw material
                                materials.append(item)

                    return materials, sub_products

                # Separate into products (top-level) and standalone items
                products = []
                standalone_items = []
                flat_items = []  # Legacy flat list for backward compatibility

                for item in all_items:
                    flat_items.append(item)

                    if item['parent_item_id'] is None:
                        if item['is_product']:
                            # Recursively build the entire tree
                            item['materials'], item['sub_products'] = build_product_tree(item['id'], all_items)
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
