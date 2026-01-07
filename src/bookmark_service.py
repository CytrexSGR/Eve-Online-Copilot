"""Bookmark Service for EVE Co-Pilot"""

from src.database import get_db_connection
from psycopg2.extras import RealDictCursor
from typing import Optional, List
from datetime import datetime


class BookmarkService:

    def create_bookmark(
        self,
        type_id: int,
        item_name: str,
        character_id: Optional[int] = None,
        corporation_id: Optional[int] = None,
        notes: Optional[str] = None,
        tags: Optional[List[str]] = None,
        priority: int = 0
    ) -> dict:
        """Create a new bookmark"""
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute('''
                    INSERT INTO bookmarks
                        (type_id, item_name, character_id, corporation_id, notes, tags, priority)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING *
                ''', (type_id, item_name, character_id, corporation_id, notes, tags or [], priority))
                conn.commit()
                return dict(cur.fetchone())

    def get_bookmarks(
        self,
        character_id: Optional[int] = None,
        corporation_id: Optional[int] = None,
        list_id: Optional[int] = None
    ) -> List[dict]:
        """Get bookmarks filtered by character/corp/list"""
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if list_id:
                    cur.execute('''
                        SELECT b.*, bli.position
                        FROM bookmarks b
                        JOIN bookmark_list_items bli ON b.id = bli.bookmark_id
                        WHERE bli.list_id = %s
                        ORDER BY bli.position, b.created_at DESC
                    ''', (list_id,))
                else:
                    where_clauses = []
                    params = []

                    if character_id:
                        where_clauses.append("character_id = %s")
                        params.append(character_id)
                    if corporation_id:
                        where_clauses.append("corporation_id = %s")
                        params.append(corporation_id)

                    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

                    cur.execute(f'''
                        SELECT * FROM bookmarks
                        WHERE {where_sql}
                        ORDER BY priority DESC, created_at DESC
                    ''', params)

                return [dict(row) for row in cur.fetchall()]

    def delete_bookmark(self, bookmark_id: int) -> bool:
        """Delete a bookmark"""
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('DELETE FROM bookmarks WHERE id = %s', (bookmark_id,))
                conn.commit()
                return cur.rowcount > 0

    def update_bookmark(
        self,
        bookmark_id: int,
        notes: Optional[str] = None,
        tags: Optional[List[str]] = None,
        priority: Optional[int] = None
    ) -> dict:
        """Update bookmark fields"""
        updates = []
        params = []

        if notes is not None:
            updates.append("notes = %s")
            params.append(notes)
        if tags is not None:
            updates.append("tags = %s")
            params.append(tags)
        if priority is not None:
            updates.append("priority = %s")
            params.append(priority)

        updates.append("updated_at = %s")
        params.append(datetime.now())
        params.append(bookmark_id)

        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(f'''
                    UPDATE bookmarks
                    SET {", ".join(updates)}
                    WHERE id = %s
                    RETURNING *
                ''', params)
                conn.commit()
                result = cur.fetchone()
                return dict(result) if result else None

    def is_bookmarked(self, type_id: int, character_id: Optional[int] = None, corporation_id: Optional[int] = None) -> bool:
        """Check if an item is bookmarked"""
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                where_clauses = ["type_id = %s"]
                params = [type_id]

                if character_id:
                    where_clauses.append("character_id = %s")
                    params.append(character_id)
                if corporation_id:
                    where_clauses.append("corporation_id = %s")
                    params.append(corporation_id)

                cur.execute(f'''
                    SELECT COUNT(*) FROM bookmarks
                    WHERE {" AND ".join(where_clauses)}
                ''', params)
                return cur.fetchone()[0] > 0

    def get_bookmark_by_type(self, type_id: int, character_id: Optional[int] = None, corporation_id: Optional[int] = None) -> Optional[dict]:
        """Get bookmark for a specific item"""
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                where_clauses = ["type_id = %s"]
                params = [type_id]

                if character_id:
                    where_clauses.append("character_id = %s")
                    params.append(character_id)
                if corporation_id:
                    where_clauses.append("corporation_id = %s")
                    params.append(corporation_id)

                cur.execute(f'''
                    SELECT * FROM bookmarks
                    WHERE {" AND ".join(where_clauses)}
                    LIMIT 1
                ''', params)
                result = cur.fetchone()
                return dict(result) if result else None

    # Bookmark Lists
    def create_list(
        self,
        name: str,
        description: Optional[str] = None,
        character_id: Optional[int] = None,
        corporation_id: Optional[int] = None,
        is_shared: bool = False
    ) -> dict:
        """Create a bookmark list"""
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute('''
                    INSERT INTO bookmark_lists (name, description, character_id, corporation_id, is_shared)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING *
                ''', (name, description, character_id, corporation_id, is_shared))
                conn.commit()
                return dict(cur.fetchone())

    def get_lists(
        self,
        character_id: Optional[int] = None,
        corporation_id: Optional[int] = None
    ) -> List[dict]:
        """Get bookmark lists"""
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                where_clauses = []
                params = []

                if character_id:
                    where_clauses.append("(character_id = %s OR is_shared = TRUE)")
                    params.append(character_id)
                if corporation_id:
                    where_clauses.append("corporation_id = %s")
                    params.append(corporation_id)

                where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

                cur.execute(f'''
                    SELECT bl.*,
                           (SELECT COUNT(*) FROM bookmark_list_items WHERE list_id = bl.id) as item_count
                    FROM bookmark_lists bl
                    WHERE {where_sql}
                    ORDER BY bl.name
                ''', params)
                return [dict(row) for row in cur.fetchall()]

    def add_to_list(self, list_id: int, bookmark_id: int, position: int = 0) -> bool:
        """Add bookmark to list"""
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    INSERT INTO bookmark_list_items (list_id, bookmark_id, position)
                    VALUES (%s, %s, %s)
                    ON CONFLICT DO NOTHING
                ''', (list_id, bookmark_id, position))
                conn.commit()
                return cur.rowcount > 0

    def remove_from_list(self, list_id: int, bookmark_id: int) -> bool:
        """Remove bookmark from list"""
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    DELETE FROM bookmark_list_items
                    WHERE list_id = %s AND bookmark_id = %s
                ''', (list_id, bookmark_id))
                conn.commit()
                return cur.rowcount > 0


bookmark_service = BookmarkService()
