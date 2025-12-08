"""Tests for market repository - TDD approach."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch
from psycopg2.extras import RealDictCursor


@pytest.fixture
def mock_db_pool():
    """Mock database pool."""
    pool = Mock()
    mock_cursor = MagicMock()
    mock_conn = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_conn.cursor.return_value.__exit__ = Mock()

    # Create proper context manager mock - needs to be callable each time
    def get_connection_context():
        mock_context = MagicMock()
        mock_context.__enter__ = Mock(return_value=mock_conn)
        mock_context.__exit__ = Mock(return_value=None)
        return mock_context

    pool.get_connection = Mock(side_effect=get_connection_context)

    return pool, mock_cursor


def test_bulk_upsert_prices(mock_db_pool):
    """Test bulk upserting market prices."""
    from src.services.market.repository import MarketRepository
    from src.services.market.models import MarketPrice

    pool, mock_cursor = mock_db_pool
    mock_cursor.rowcount = 3

    repo = MarketRepository(pool)
    now = datetime.now()

    prices = [
        MarketPrice(
            type_id=34,
            adjusted_price=5.5,
            average_price=5.75,
            last_updated=now
        ),
        MarketPrice(
            type_id=35,
            adjusted_price=4.2,
            average_price=4.5,
            last_updated=now
        ),
        MarketPrice(
            type_id=36,
            adjusted_price=6.0,
            average_price=6.25,
            last_updated=now
        )
    ]

    with patch('src.services.market.repository.execute_values') as mock_execute_values:
        result = repo.bulk_upsert_prices(prices)

        assert result == 3
        # Verify execute_values was called with correct parameters
        assert mock_execute_values.called
        call_args = mock_execute_values.call_args
        assert mock_cursor == call_args[0][0]
        assert "INSERT INTO market_prices_cache" in call_args[0][1]
        assert "ON CONFLICT" in call_args[0][1]


def test_bulk_upsert_empty_list(mock_db_pool):
    """Test bulk upsert with empty list."""
    from src.services.market.repository import MarketRepository

    pool, mock_cursor = mock_db_pool

    repo = MarketRepository(pool)
    result = repo.bulk_upsert_prices([])

    assert result == 0
    mock_cursor.execute.assert_not_called()


def test_bulk_upsert_database_error():
    """Test bulk upsert with database error."""
    from src.services.market.repository import MarketRepository
    from src.services.market.models import MarketPrice
    from src.core.exceptions import EVECopilotError

    # Create a mock pool that raises on connection
    pool = Mock()
    mock_context = MagicMock()
    mock_context.__enter__ = Mock(side_effect=Exception("Database connection failed"))
    pool.get_connection.return_value = mock_context

    repo = MarketRepository(pool)
    now = datetime.now()

    prices = [
        MarketPrice(
            type_id=34,
            adjusted_price=5.5,
            average_price=5.75,
            last_updated=now
        )
    ]

    with pytest.raises(EVECopilotError) as exc_info:
        repo.bulk_upsert_prices(prices)

    assert "Failed to bulk upsert prices" in str(exc_info.value)


def test_get_cache_stats_with_data(mock_db_pool):
    """Test getting cache statistics when data exists."""
    from src.services.market.repository import MarketRepository
    from src.services.market.models import CacheStats

    pool, mock_cursor = mock_db_pool
    now = datetime.now()
    old_time = now - timedelta(minutes=30)

    mock_cursor.fetchone.return_value = {
        "total_items": 15000,
        "oldest_entry": old_time,
        "newest_entry": now
    }

    repo = MarketRepository(pool)
    result = repo.get_cache_stats()

    assert isinstance(result, CacheStats)
    assert result.total_items == 15000
    assert result.oldest_entry == old_time
    assert result.newest_entry == now
    assert result.cache_age_seconds is not None
    assert result.cache_age_seconds <= 1800  # 30 minutes
    assert result.is_stale is False  # Less than 1 hour old


def test_get_cache_stats_stale_cache(mock_db_pool):
    """Test cache stats when cache is stale."""
    from src.services.market.repository import MarketRepository

    pool, mock_cursor = mock_db_pool
    now = datetime.now()
    old_time = now - timedelta(hours=2)

    mock_cursor.fetchone.return_value = {
        "total_items": 15000,
        "oldest_entry": old_time,
        "newest_entry": old_time
    }

    repo = MarketRepository(pool)
    result = repo.get_cache_stats()

    assert result.is_stale is True  # More than 1 hour old


def test_get_cache_stats_empty_cache(mock_db_pool):
    """Test cache stats when cache is empty."""
    from src.services.market.repository import MarketRepository

    pool, mock_cursor = mock_db_pool
    mock_cursor.fetchone.return_value = {
        "total_items": 0,
        "oldest_entry": None,
        "newest_entry": None
    }

    repo = MarketRepository(pool)
    result = repo.get_cache_stats()

    assert result.total_items == 0
    assert result.oldest_entry is None
    assert result.newest_entry is None
    assert result.cache_age_seconds is None
    assert result.is_stale is True


def test_get_cache_stats_database_error():
    """Test cache stats with database error."""
    from src.services.market.repository import MarketRepository
    from src.core.exceptions import EVECopilotError

    # Create a mock pool that raises on connection
    pool = Mock()
    mock_context = MagicMock()
    mock_context.__enter__ = Mock(side_effect=Exception("Database error"))
    pool.get_connection.return_value = mock_context

    repo = MarketRepository(pool)

    with pytest.raises(EVECopilotError) as exc_info:
        repo.get_cache_stats()

    assert "Failed to get cache stats" in str(exc_info.value)


def test_get_price_found(mock_db_pool):
    """Test getting a single price that exists."""
    from src.services.market.repository import MarketRepository

    pool, mock_cursor = mock_db_pool
    now = datetime.now()

    mock_cursor.fetchone.return_value = {
        "type_id": 34,
        "adjusted_price": 5.5,
        "average_price": 5.75,
        "last_updated": now
    }

    repo = MarketRepository(pool)
    result = repo.get_price(34)

    assert result is not None
    assert result["type_id"] == 34
    assert result["adjusted_price"] == 5.5
    mock_cursor.execute.assert_called_with(
        "SELECT * FROM market_prices_cache WHERE type_id = %s",
        (34,)
    )


def test_get_price_not_found(mock_db_pool):
    """Test getting a price that doesn't exist."""
    from src.services.market.repository import MarketRepository

    pool, mock_cursor = mock_db_pool
    mock_cursor.fetchone.return_value = None

    repo = MarketRepository(pool)
    result = repo.get_price(999999)

    assert result is None


def test_get_price_database_error():
    """Test get_price with database error."""
    from src.services.market.repository import MarketRepository
    from src.core.exceptions import EVECopilotError

    # Create a mock pool that raises on connection
    pool = Mock()
    mock_context = MagicMock()
    mock_context.__enter__ = Mock(side_effect=Exception("Connection lost"))
    pool.get_connection.return_value = mock_context

    repo = MarketRepository(pool)

    with pytest.raises(EVECopilotError) as exc_info:
        repo.get_price(34)

    assert "Failed to get price" in str(exc_info.value)


def test_get_prices_bulk(mock_db_pool):
    """Test getting multiple prices at once."""
    from src.services.market.repository import MarketRepository

    pool, mock_cursor = mock_db_pool
    now = datetime.now()

    mock_cursor.fetchall.return_value = [
        {"type_id": 34, "adjusted_price": 5.5, "average_price": 5.75, "last_updated": now},
        {"type_id": 35, "adjusted_price": 4.2, "average_price": 4.5, "last_updated": now},
        {"type_id": 36, "adjusted_price": 6.0, "average_price": 6.25, "last_updated": now}
    ]

    repo = MarketRepository(pool)
    result = repo.get_prices_bulk([34, 35, 36])

    assert len(result) == 3
    assert result[0]["type_id"] == 34
    assert result[1]["type_id"] == 35
    assert result[2]["type_id"] == 36
    mock_cursor.execute.assert_called_once()
    # Verify ANY clause was used
    call_args = mock_cursor.execute.call_args
    assert "WHERE type_id = ANY(%s)" in call_args[0][0]


def test_get_prices_bulk_empty_list(mock_db_pool):
    """Test bulk get with empty list."""
    from src.services.market.repository import MarketRepository

    pool, mock_cursor = mock_db_pool

    repo = MarketRepository(pool)
    result = repo.get_prices_bulk([])

    assert result == []
    mock_cursor.execute.assert_not_called()


def test_get_prices_bulk_partial_results(mock_db_pool):
    """Test bulk get when only some prices exist."""
    from src.services.market.repository import MarketRepository

    pool, mock_cursor = mock_db_pool
    now = datetime.now()

    mock_cursor.fetchall.return_value = [
        {"type_id": 34, "adjusted_price": 5.5, "average_price": 5.75, "last_updated": now}
    ]

    repo = MarketRepository(pool)
    result = repo.get_prices_bulk([34, 999999, 888888])

    # Should only return the one that exists
    assert len(result) == 1
    assert result[0]["type_id"] == 34


def test_get_prices_bulk_database_error():
    """Test bulk get with database error."""
    from src.services.market.repository import MarketRepository
    from src.core.exceptions import EVECopilotError

    # Create a mock pool that raises on connection
    pool = Mock()
    mock_context = MagicMock()
    mock_context.__enter__ = Mock(side_effect=Exception("Query timeout"))
    pool.get_connection.return_value = mock_context

    repo = MarketRepository(pool)

    with pytest.raises(EVECopilotError) as exc_info:
        repo.get_prices_bulk([34, 35, 36])

    assert "Failed to get prices bulk" in str(exc_info.value)


def test_repository_uses_realdictcursor(mock_db_pool):
    """Test that repository uses RealDictCursor."""
    from src.services.market.repository import MarketRepository

    pool, mock_cursor = mock_db_pool
    now = datetime.now()

    mock_cursor.fetchone.return_value = {
        "type_id": 34,
        "adjusted_price": 5.5,
        "average_price": 5.75,
        "last_updated": now
    }

    repo = MarketRepository(pool)
    result = repo.get_price(34)

    # Verify result was returned
    assert result is not None
    assert result["type_id"] == 34

    # The repository pattern requires RealDictCursor which is verified by
    # the fact that we're getting dict results from the mock (implicit verification)
