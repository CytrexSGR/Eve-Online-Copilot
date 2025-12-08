"""Tests for shopping repository."""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock


@pytest.fixture
def mock_db_pool():
    """Mock database pool."""
    pool = Mock()
    mock_cursor = MagicMock()
    mock_conn = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_conn.cursor.return_value.__exit__ = Mock()

    # Create proper context manager mock
    mock_context = MagicMock()
    mock_context.__enter__ = Mock(return_value=mock_conn)
    mock_context.__exit__ = Mock(return_value=None)
    pool.get_connection.return_value = mock_context

    return pool, mock_cursor


def test_create_shopping_list(mock_db_pool):
    """Test creating a shopping list."""
    from src.services.shopping.repository import ShoppingRepository
    from src.services.shopping.models import ShoppingListCreate

    pool, mock_cursor = mock_db_pool
    mock_cursor.fetchone.return_value = {
        "id": 1,
        "name": "Test List",
        "character_id": 123,
        "corporation_id": None,
        "status": "active",
        "notes": "Test notes",
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }

    repo = ShoppingRepository(pool)
    list_data = ShoppingListCreate(
        name="Test List",
        character_id=123,
        notes="Test notes"
    )

    result = repo.create(list_data)

    assert result["id"] == 1
    assert result["name"] == "Test List"
    mock_cursor.execute.assert_called_once()


def test_get_shopping_list_by_id(mock_db_pool):
    """Test getting shopping list by ID."""
    from src.services.shopping.repository import ShoppingRepository

    pool, mock_cursor = mock_db_pool
    mock_cursor.fetchone.return_value = {
        "id": 1,
        "name": "Test List",
        "status": "active"
    }

    repo = ShoppingRepository(pool)
    result = repo.get_by_id(1)

    assert result is not None
    assert result["id"] == 1
    mock_cursor.execute.assert_called_with(
        "SELECT * FROM shopping_lists WHERE id = %s",
        (1,)
    )


def test_get_shopping_list_not_found(mock_db_pool):
    """Test getting non-existent shopping list."""
    from src.services.shopping.repository import ShoppingRepository

    pool, mock_cursor = mock_db_pool
    mock_cursor.fetchone.return_value = None

    repo = ShoppingRepository(pool)
    result = repo.get_by_id(999)

    assert result is None


def test_list_shopping_lists_with_filters(mock_db_pool):
    """Test listing shopping lists with filters."""
    from src.services.shopping.repository import ShoppingRepository

    pool, mock_cursor = mock_db_pool
    mock_cursor.fetchall.return_value = [
        {"id": 1, "name": "List 1", "character_id": 123},
        {"id": 2, "name": "List 2", "character_id": 123}
    ]

    repo = ShoppingRepository(pool)
    results = repo.list_by_character(character_id=123)

    assert len(results) == 2
    assert results[0]["id"] == 1


def test_add_item_to_list(mock_db_pool):
    """Test adding item to shopping list."""
    from src.services.shopping.repository import ShoppingRepository
    from src.services.shopping.models import ShoppingItemCreate

    pool, mock_cursor = mock_db_pool
    mock_cursor.fetchone.return_value = {
        "id": 1,
        "list_id": 1,
        "type_id": 34,
        "item_name": "Tritanium",
        "quantity": 1000
    }

    repo = ShoppingRepository(pool)
    item_data = ShoppingItemCreate(
        type_id=34,
        item_name="Tritanium",
        quantity=1000
    )

    result = repo.add_item(list_id=1, item_data=item_data)

    assert result["id"] == 1
    assert result["type_id"] == 34
