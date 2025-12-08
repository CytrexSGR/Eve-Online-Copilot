"""Shopping service - business logic layer."""

from typing import List, Optional, Any

from src.services.shopping.repository import ShoppingRepository
from src.services.shopping.models import (
    ShoppingList,
    ShoppingListCreate,
    ShoppingListUpdate,
    ShoppingItem,
    ShoppingItemCreate
)
from src.core.exceptions import NotFoundError


class ShoppingService:
    """Business logic for shopping lists."""

    def __init__(
        self,
        repository: ShoppingRepository,
        market_service: Any  # Will be typed properly later
    ):
        """Initialize service with dependencies."""
        self.repo = repository
        self.market = market_service

    def create_list(self, list_data: ShoppingListCreate) -> ShoppingList:
        """Create a new shopping list."""
        result = self.repo.create(list_data)
        return ShoppingList(**result, item_count=0, purchased_count=0)

    def get_list(self, list_id: int) -> ShoppingList:
        """Get shopping list by ID."""
        result = self.repo.get_by_id(list_id)
        if not result:
            raise NotFoundError("Shopping list", list_id)
        return ShoppingList(**result)

    def list_by_character(
        self,
        character_id: int,
        status: Optional[str] = None
    ) -> List[ShoppingList]:
        """List shopping lists for a character."""
        results = self.repo.list_by_character(character_id, status)
        return [ShoppingList(**r) for r in results]

    def add_item(
        self,
        list_id: int,
        item_data: ShoppingItemCreate
    ) -> ShoppingItem:
        """Add item to shopping list."""
        # Verify list exists
        if not self.repo.get_by_id(list_id):
            raise NotFoundError("Shopping list", list_id)

        result = self.repo.add_item(list_id, item_data)
        return ShoppingItem(**result)

    def update_list(
        self,
        list_id: int,
        updates: ShoppingListUpdate
    ) -> ShoppingList:
        """Update shopping list."""
        if not self.repo.get_by_id(list_id):
            raise NotFoundError("Shopping list", list_id)

        update_data = updates.model_dump(exclude_unset=True)
        result = self.repo.update(list_id, update_data)
        return ShoppingList(**result)

    def delete_list(self, list_id: int) -> bool:
        """Delete shopping list."""
        if not self.repo.get_by_id(list_id):
            raise NotFoundError("Shopping list", list_id)

        return self.repo.delete(list_id)
