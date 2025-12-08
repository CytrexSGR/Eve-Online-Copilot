"""Tests for shopping service business logic."""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime


@pytest.fixture
def mock_repository():
    """Mock shopping repository."""
    return Mock()


@pytest.fixture
def mock_market_service():
    """Mock market service."""
    return Mock()


def test_create_shopping_list(mock_repository):
    """Test creating shopping list."""
    from src.services.shopping.service import ShoppingService
    from src.services.shopping.models import ShoppingListCreate, ShoppingList

    mock_repository.create.return_value = {
        "id": 1,
        "name": "Test List",
        "character_id": 123,
        "corporation_id": None,
        "status": "active",
        "notes": None,
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }

    service = ShoppingService(mock_repository, Mock())
    list_data = ShoppingListCreate(name="Test List", character_id=123)

    result = service.create_list(list_data)

    assert isinstance(result, ShoppingList)
    assert result.id == 1
    assert result.name == "Test List"
    mock_repository.create.assert_called_once_with(list_data)


def test_get_shopping_list_success(mock_repository):
    """Test getting existing shopping list."""
    from src.services.shopping.service import ShoppingService
    from src.services.shopping.models import ShoppingList

    mock_repository.get_by_id.return_value = {
        "id": 1,
        "name": "Test List",
        "character_id": 123,
        "corporation_id": None,
        "status": "active",
        "notes": None,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "item_count": 0,
        "purchased_count": 0
    }

    service = ShoppingService(mock_repository, Mock())
    result = service.get_list(1)

    assert isinstance(result, ShoppingList)
    assert result.id == 1


def test_get_shopping_list_not_found(mock_repository):
    """Test getting non-existent shopping list raises error."""
    from src.services.shopping.service import ShoppingService
    from src.core.exceptions import NotFoundError

    mock_repository.get_by_id.return_value = None

    service = ShoppingService(mock_repository, Mock())

    with pytest.raises(NotFoundError) as exc_info:
        service.get_list(999)

    assert exc_info.value.resource == "Shopping list"
    assert exc_info.value.resource_id == 999


def test_add_item_to_list(mock_repository):
    """Test adding item to shopping list."""
    from src.services.shopping.service import ShoppingService
    from src.services.shopping.models import ShoppingItemCreate, ShoppingItem

    mock_repository.get_by_id.return_value = {"id": 1}
    mock_repository.add_item.return_value = {
        "id": 1,
        "list_id": 1,
        "type_id": 34,
        "item_name": "Tritanium",
        "quantity": 1000,
        "parent_item_id": None,
        "is_product": False,
        "is_purchased": False,
        "purchase_price": None,
        "purchase_location": None,
        "created_at": datetime.now()
    }

    service = ShoppingService(mock_repository, Mock())
    item_data = ShoppingItemCreate(
        type_id=34,
        item_name="Tritanium",
        quantity=1000
    )

    result = service.add_item(list_id=1, item_data=item_data)

    assert isinstance(result, ShoppingItem)
    assert result.type_id == 34
    mock_repository.add_item.assert_called_once_with(1, item_data)


def test_add_item_to_nonexistent_list(mock_repository):
    """Test adding item to non-existent list raises error."""
    from src.services.shopping.service import ShoppingService
    from src.services.shopping.models import ShoppingItemCreate
    from src.core.exceptions import NotFoundError

    mock_repository.get_by_id.return_value = None

    service = ShoppingService(mock_repository, Mock())
    item_data = ShoppingItemCreate(
        type_id=34,
        item_name="Tritanium",
        quantity=1000
    )

    with pytest.raises(NotFoundError):
        service.add_item(list_id=999, item_data=item_data)


def test_list_by_character(mock_repository):
    """Test listing character shopping lists."""
    from src.services.shopping.service import ShoppingService
    from src.services.shopping.models import ShoppingList

    mock_repository.list_by_character.return_value = [
        {
            "id": 1,
            "name": "List 1",
            "character_id": 123,
            "corporation_id": None,
            "status": "active",
            "notes": None,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "item_count": 5,
            "purchased_count": 2
        },
        {
            "id": 2,
            "name": "List 2",
            "character_id": 123,
            "corporation_id": None,
            "status": "active",
            "notes": None,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "item_count": 3,
            "purchased_count": 0
        }
    ]

    service = ShoppingService(mock_repository, Mock())
    results = service.list_by_character(character_id=123)

    assert len(results) == 2
    assert all(isinstance(r, ShoppingList) for r in results)
    assert results[0].id == 1
    mock_repository.list_by_character.assert_called_once_with(123, None)


def test_update_list(mock_repository):
    """Test updating shopping list."""
    from src.services.shopping.service import ShoppingService
    from src.services.shopping.models import ShoppingList, ShoppingListUpdate

    mock_repository.get_by_id.return_value = {"id": 1, "name": "Test"}
    mock_repository.update.return_value = {
        "id": 1,
        "name": "Updated",
        "character_id": 123,
        "corporation_id": None,
        "status": "active",
        "notes": "Updated notes",
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "item_count": 0,
        "purchased_count": 0
    }

    service = ShoppingService(mock_repository, Mock())
    update = ShoppingListUpdate(name="Updated", notes="Updated notes")
    result = service.update_list(1, update)

    assert isinstance(result, ShoppingList)
    assert result.name == "Updated"
    mock_repository.update.assert_called_once()


def test_delete_list(mock_repository):
    """Test deleting shopping list."""
    from src.services.shopping.service import ShoppingService

    mock_repository.get_by_id.return_value = {"id": 1}
    mock_repository.delete.return_value = True

    service = ShoppingService(mock_repository, Mock())
    result = service.delete_list(1)

    assert result is True
    mock_repository.get_by_id.assert_called_once_with(1)
    mock_repository.delete.assert_called_once_with(1)
