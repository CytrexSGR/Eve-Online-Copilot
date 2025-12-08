"""Bookmark repository - data access layer."""

from typing import Dict, List, Optional, Any
from psycopg2.extras import RealDictCursor

from src.core.database import DatabasePool
from src.core.exceptions import EVECopilotError
from src.services.bookmark.models import BookmarkCreate, BookmarkListCreate


class BookmarkRepository:
    """Data access for bookmarks and bookmark lists."""

    # Whitelist of allowed fields for update to prevent SQL injection
    ALLOWED_UPDATE_FIELDS = {"notes", "tags", "priority"}

    def __init__(self, db: DatabasePool):
        """Initialize repository with database pool."""
        self.db = db

    def create(self, data: BookmarkCreate) -> Dict[str, Any]:
        """Create a new bookmark."""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        """
                        INSERT INTO bookmarks
                            (type_id, item_name, character_id, corporation_id, notes, tags, priority)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        RETURNING *
                        """,
                        (
                            data.type_id,
                            data.item_name,
                            data.character_id,
                            data.corporation_id,
                            data.notes,
                            data.tags,
                            data.priority
                        )
                    )
                    conn.commit()
                    result = cur.fetchone()
                    if result is None:
                        raise EVECopilotError("Failed to create bookmark: No result returned")
                    return dict(result)
        except EVECopilotError:
            raise
        except Exception as e:
            raise EVECopilotError(f"Failed to create bookmark: {str(e)}")

    def get_by_id(self, bookmark_id: int) -> Optional[Dict[str, Any]]:
        """Get bookmark by ID."""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        "SELECT * FROM bookmarks WHERE id = %s",
                        (bookmark_id,)
                    )
                    result = cur.fetchone()
                    return dict(result) if result else None
        except Exception as e:
            raise EVECopilotError(f"Failed to get bookmark by ID: {str(e)}")

    def get_all(
        self,
        character_id: Optional[int] = None,
        corporation_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get bookmarks filtered by character and/or corporation."""
        try:
            where_clauses = []
            params = []

            if character_id is not None:
                where_clauses.append("character_id = %s")
                params.append(character_id)
            if corporation_id is not None:
                where_clauses.append("corporation_id = %s")
                params.append(corporation_id)

            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

            with self.db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        f"""
                        SELECT * FROM bookmarks
                        WHERE {where_sql}
                        ORDER BY priority DESC, created_at DESC
                        """,
                        params
                    )
                    return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            raise EVECopilotError(f"Failed to get bookmarks: {str(e)}")

    def get_by_list_id(self, list_id: int) -> List[Dict[str, Any]]:
        """Get bookmarks in a specific list (with position)."""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        """
                        SELECT b.*, bli.position
                        FROM bookmarks b
                        JOIN bookmark_list_items bli ON b.id = bli.bookmark_id
                        WHERE bli.list_id = %s
                        ORDER BY bli.position, b.created_at DESC
                        """,
                        (list_id,)
                    )
                    return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            raise EVECopilotError(f"Failed to get bookmarks by list ID: {str(e)}")

    def get_by_type(
        self,
        type_id: int,
        character_id: Optional[int] = None,
        corporation_id: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Find bookmark by type_id."""
        try:
            where_clauses = ["type_id = %s"]
            params = [type_id]

            if character_id is not None:
                where_clauses.append("character_id = %s")
                params.append(character_id)
            if corporation_id is not None:
                where_clauses.append("corporation_id = %s")
                params.append(corporation_id)

            with self.db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        f"""
                        SELECT * FROM bookmarks
                        WHERE {" AND ".join(where_clauses)}
                        LIMIT 1
                        """,
                        params
                    )
                    result = cur.fetchone()
                    return dict(result) if result else None
        except Exception as e:
            raise EVECopilotError(f"Failed to get bookmark by type: {str(e)}")

    def is_bookmarked(
        self,
        type_id: int,
        character_id: Optional[int] = None,
        corporation_id: Optional[int] = None
    ) -> bool:
        """Check if an item is bookmarked."""
        try:
            where_clauses = ["type_id = %s"]
            params = [type_id]

            if character_id is not None:
                where_clauses.append("character_id = %s")
                params.append(character_id)
            if corporation_id is not None:
                where_clauses.append("corporation_id = %s")
                params.append(corporation_id)

            with self.db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        f"""
                        SELECT COUNT(*) FROM bookmarks
                        WHERE {" AND ".join(where_clauses)}
                        """,
                        params
                    )
                    count = cur.fetchone()[0]
                    return count > 0
        except Exception as e:
            raise EVECopilotError(f"Failed to check if bookmarked: {str(e)}")

    def update(self, bookmark_id: int, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update bookmark with field whitelist."""
        if not updates:
            return self.get_by_id(bookmark_id)

        # Whitelist validation to prevent SQL injection
        for key in updates.keys():
            if key not in self.ALLOWED_UPDATE_FIELDS:
                raise ValueError(f"Cannot update field: {key}")

        try:
            set_clauses = ", ".join(f"{key} = %s" for key in updates.keys())
            query = f"UPDATE bookmarks SET {set_clauses}, updated_at = NOW() WHERE id = %s RETURNING *"

            with self.db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(query, (*updates.values(), bookmark_id))
                    conn.commit()
                    result = cur.fetchone()
                    return dict(result) if result else None
        except ValueError:
            raise
        except Exception as e:
            raise EVECopilotError(f"Failed to update bookmark: {str(e)}")

    def delete(self, bookmark_id: int) -> bool:
        """Delete bookmark."""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("DELETE FROM bookmarks WHERE id = %s", (bookmark_id,))
                    conn.commit()
                    return cur.rowcount > 0
        except Exception as e:
            raise EVECopilotError(f"Failed to delete bookmark: {str(e)}")

    def create_list(self, data: BookmarkListCreate) -> Dict[str, Any]:
        """Create a bookmark list."""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        """
                        INSERT INTO bookmark_lists
                            (name, description, character_id, corporation_id, is_shared)
                        VALUES (%s, %s, %s, %s, %s)
                        RETURNING *
                        """,
                        (
                            data.name,
                            data.description,
                            data.character_id,
                            data.corporation_id,
                            data.is_shared
                        )
                    )
                    conn.commit()
                    result = cur.fetchone()
                    if result is None:
                        raise EVECopilotError("Failed to create bookmark list: No result returned")
                    return dict(result)
        except EVECopilotError:
            raise
        except Exception as e:
            raise EVECopilotError(f"Failed to create bookmark list: {str(e)}")

    def get_lists(
        self,
        character_id: Optional[int] = None,
        corporation_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get bookmark lists with item_count."""
        try:
            where_clauses = []
            params = []

            if character_id is not None:
                where_clauses.append("(character_id = %s OR is_shared = TRUE)")
                params.append(character_id)
            if corporation_id is not None:
                where_clauses.append("corporation_id = %s")
                params.append(corporation_id)

            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

            with self.db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        f"""
                        SELECT bl.*,
                               (SELECT COUNT(*) FROM bookmark_list_items WHERE list_id = bl.id) as item_count
                        FROM bookmark_lists bl
                        WHERE {where_sql}
                        ORDER BY bl.name
                        """,
                        params
                    )
                    return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            raise EVECopilotError(f"Failed to get bookmark lists: {str(e)}")

    def add_to_list(self, list_id: int, bookmark_id: int, position: int) -> bool:
        """Add bookmark to list."""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        """
                        INSERT INTO bookmark_list_items (list_id, bookmark_id, position)
                        VALUES (%s, %s, %s)
                        ON CONFLICT DO NOTHING
                        """,
                        (list_id, bookmark_id, position)
                    )
                    conn.commit()
                    return cur.rowcount > 0
        except Exception as e:
            raise EVECopilotError(f"Failed to add bookmark to list: {str(e)}")

    def remove_from_list(self, list_id: int, bookmark_id: int) -> bool:
        """Remove bookmark from list."""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        """
                        DELETE FROM bookmark_list_items
                        WHERE list_id = %s AND bookmark_id = %s
                        """,
                        (list_id, bookmark_id)
                    )
                    conn.commit()
                    return cur.rowcount > 0
        except Exception as e:
            raise EVECopilotError(f"Failed to remove bookmark from list: {str(e)}")
