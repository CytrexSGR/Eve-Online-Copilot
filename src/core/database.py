"""Database connection pool management."""

from contextlib import contextmanager
from typing import Any, Dict, List, Optional

import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor

from src.core.config import Settings


class DatabasePool:
    """Manages PostgreSQL connection pool."""

    def __init__(self, settings: Settings, min_conn: int = 1, max_conn: int = 20):
        """Initialize connection pool."""
        self.settings = settings
        self.pool = psycopg2.pool.SimpleConnectionPool(
            min_conn,
            max_conn,
            host=settings.db_host,
            port=settings.db_port,
            database=settings.db_name,
            user=settings.db_user,
            password=settings.db_password
        )

    @contextmanager
    def get_connection(self):
        """Get a connection from the pool as context manager."""
        conn = self.pool.getconn()
        try:
            yield conn
        finally:
            self.pool.putconn(conn)

    def execute_query(
        self,
        query: str,
        params: Optional[tuple] = None,
        fetch: bool = True
    ) -> List[Dict[str, Any]]:
        """Execute a query and return results as list of dicts."""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params)
                if fetch:
                    return [dict(row) for row in cur.fetchall()]
                return []

    def close(self):
        """Close all connections in the pool."""
        if self.pool:
            self.pool.closeall()


# Global pool instance (initialized on app startup)
_db_pool: Optional[DatabasePool] = None


def init_database_pool(settings: Settings) -> DatabasePool:
    """Initialize global database pool."""
    global _db_pool
    _db_pool = DatabasePool(settings)
    return _db_pool


def get_database_pool() -> DatabasePool:
    """Get global database pool instance."""
    if _db_pool is None:
        raise RuntimeError("Database pool not initialized. Call init_database_pool first.")
    return _db_pool
