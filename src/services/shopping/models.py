"""Shopping service domain models."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class ShoppingListCreate(BaseModel):
    """Schema for creating a shopping list."""
    name: str = Field(..., min_length=1, max_length=255)
    character_id: Optional[int] = None
    corporation_id: Optional[int] = None
    notes: Optional[str] = None


class ShoppingListUpdate(BaseModel):
    """Schema for updating a shopping list."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    status: Optional[str] = None
    notes: Optional[str] = None


class ShoppingList(BaseModel):
    """Shopping list entity."""
    id: int
    name: str
    character_id: Optional[int]
    corporation_id: Optional[int]
    status: str = "active"
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    item_count: int = 0
    purchased_count: int = 0


class ShoppingItemCreate(BaseModel):
    """Schema for creating a shopping list item."""
    type_id: int
    item_name: str
    quantity: int = Field(..., gt=0)
    parent_item_id: Optional[int] = None
    is_product: bool = False


class ShoppingItem(BaseModel):
    """Shopping list item entity."""
    id: int
    list_id: int
    type_id: int
    item_name: str
    quantity: int
    parent_item_id: Optional[int]
    is_product: bool
    is_purchased: bool
    purchase_price: Optional[float]
    purchase_location: Optional[str]
    created_at: datetime
