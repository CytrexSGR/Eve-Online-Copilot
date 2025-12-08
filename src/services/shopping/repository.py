"""Shopping repository - data access layer."""

from typing import Dict, List, Optional, Any
from psycopg2.extras import RealDictCursor

from src.core.database import DatabasePool
from src.core.exceptions import EVECopilotError
from src.services.shopping.models import ShoppingListCreate, ShoppingItemCreate


class ShoppingRepository:
    """Data access for shopping lists."""

    def __init__(self, db_pool: DatabasePool):
        """Initialize repository with database pool."""
        self.db = db_pool

    def create(self, list_data: ShoppingListCreate) -> Dict[str, Any]:
        """Create a new shopping list."""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        """
                        INSERT INTO shopping_lists (name, character_id, corporation_id, notes)
                        VALUES (%s, %s, %s, %s)
                        RETURNING *
                        """,
                        (
                            list_data.name,
                            list_data.character_id,
                            list_data.corporation_id,
                            list_data.notes
                        )
                    )
                    conn.commit()
                    result = cur.fetchone()
                    if result is None:
                        raise EVECopilotError("Failed to create shopping list: No result returned")
                    return dict(result)
        except EVECopilotError:
            raise
        except Exception as e:
            raise EVECopilotError(f"Failed to create shopping list: {str(e)}")

    def get_by_id(self, list_id: int) -> Optional[Dict[str, Any]]:
        """Get shopping list by ID."""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        "SELECT * FROM shopping_lists WHERE id = %s",
                        (list_id,)
                    )
                    result = cur.fetchone()
                    return dict(result) if result else None
        except Exception as e:
            raise EVECopilotError(f"Failed to get shopping list by ID: {str(e)}")

    def list_by_character(
        self,
        character_id: int,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List shopping lists for a character."""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    query = """
                        SELECT sl.*,
                               (SELECT COUNT(*) FROM shopping_list_items WHERE list_id = sl.id) as item_count,
                               (SELECT COUNT(*) FROM shopping_list_items
                                WHERE list_id = sl.id AND is_purchased) as purchased_count
                        FROM shopping_lists sl
                        WHERE character_id = %s
                    """
                    params = [character_id]

                    if status:
                        query += " AND status = %s"
                        params.append(status)

                    query += " ORDER BY created_at DESC"

                    cur.execute(query, params)
                    return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            raise EVECopilotError(f"Failed to list shopping lists by character: {str(e)}")

    def add_item(
        self,
        list_id: int,
        item_data: ShoppingItemCreate
    ) -> Dict[str, Any]:
        """Add item to shopping list."""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        """
                        INSERT INTO shopping_list_items
                        (list_id, type_id, item_name, quantity, parent_item_id, is_product)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        RETURNING *
                        """,
                        (
                            list_id,
                            item_data.type_id,
                            item_data.item_name,
                            item_data.quantity,
                            item_data.parent_item_id,
                            item_data.is_product
                        )
                    )
                    conn.commit()
                    result = cur.fetchone()
                    if result is None:
                        raise EVECopilotError("Failed to add shopping list item: No result returned")
                    return dict(result)
        except EVECopilotError:
            raise
        except Exception as e:
            raise EVECopilotError(f"Failed to add shopping list item: {str(e)}")

    def update(self, list_id: int, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update shopping list."""
        if not updates:
            return self.get_by_id(list_id)

        # Whitelist allowed fields to prevent SQL injection
        ALLOWED_FIELDS = {"name", "status", "notes"}
        for key in updates.keys():
            if key not in ALLOWED_FIELDS:
                raise ValueError(f"Cannot update field: {key}")

        try:
            set_clauses = ", ".join(f"{key} = %s" for key in updates.keys())
            query = f"UPDATE shopping_lists SET {set_clauses} WHERE id = %s RETURNING *"

            with self.db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(query, (*updates.values(), list_id))
                    conn.commit()
                    result = cur.fetchone()
                    return dict(result) if result else None
        except ValueError:
            raise
        except Exception as e:
            raise EVECopilotError(f"Failed to update shopping list: {str(e)}")

    def delete(self, list_id: int) -> bool:
        """Delete shopping list."""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("DELETE FROM shopping_lists WHERE id = %s", (list_id,))
                    conn.commit()
                    return cur.rowcount > 0
        except Exception as e:
            raise EVECopilotError(f"Failed to delete shopping list: {str(e)}")
