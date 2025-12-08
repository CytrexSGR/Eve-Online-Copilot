"""Tests for database connection management."""

import pytest
from unittest.mock import Mock, patch, MagicMock


def test_database_pool_initializes():
    """Test database pool initializes with settings."""
    from src.core.database import DatabasePool
    from src.core.config import Settings

    settings = Settings(
        db_host="localhost",
        db_name="test",
        db_user="user",
        db_password="pass",
        eve_client_id="id",
        eve_client_secret="secret",
        eve_callback_url="http://test"
    )

    with patch('src.core.database.psycopg2.pool.SimpleConnectionPool') as mock_pool:
        pool = DatabasePool(settings)
        assert pool is not None
        mock_pool.assert_called_once()


def test_database_connection_context_manager():
    """Test database connection as context manager."""
    from src.core.database import DatabasePool
    from src.core.config import Settings

    settings = Settings(
        db_host="localhost",
        db_name="test",
        db_user="user",
        db_password="pass",
        eve_client_id="id",
        eve_client_secret="secret",
        eve_callback_url="http://test"
    )

    mock_conn = MagicMock()
    mock_pool = Mock()
    mock_pool.getconn.return_value = mock_conn

    with patch('src.core.database.psycopg2.pool.SimpleConnectionPool', return_value=mock_pool):
        pool = DatabasePool(settings)

        with pool.get_connection() as conn:
            assert conn == mock_conn

        mock_pool.putconn.assert_called_once_with(mock_conn)


def test_database_query_helper():
    """Test database query helper method."""
    from src.core.database import DatabasePool
    from src.core.config import Settings

    settings = Settings(
        db_host="localhost",
        db_name="test",
        db_user="user",
        db_password="pass",
        eve_client_id="id",
        eve_client_secret="secret",
        eve_callback_url="http://test"
    )

    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [{"id": 1, "name": "test"}]
    mock_conn = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_pool = Mock()
    mock_pool.getconn.return_value = mock_conn

    with patch('src.core.database.psycopg2.pool.SimpleConnectionPool', return_value=mock_pool):
        pool = DatabasePool(settings)
        results = pool.execute_query("SELECT * FROM test")

        assert results == [{"id": 1, "name": "test"}]
        mock_cursor.execute.assert_called_once_with("SELECT * FROM test", None)
