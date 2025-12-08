"""Bookmark service domain models."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


class BookmarkCreate(BaseModel):
    """Schema for creating a bookmark."""
    type_id: int = Field(..., gt=0, description="EVE type ID (must be positive)")
    item_name: str = Field(..., min_length=1, max_length=255, description="Item name")
    character_id: Optional[int] = None
    corporation_id: Optional[int] = None
    notes: Optional[str] = None
    tags: List[str] = Field(default_factory=list, description="List of tags")
    priority: int = Field(default=0, ge=0, description="Priority (non-negative)")


class Bookmark(BaseModel):
    """Bookmark entity."""
    id: int
    type_id: int
    item_name: str
    character_id: Optional[int]
    corporation_id: Optional[int]
    notes: Optional[str]
    tags: List[str]
    priority: int
    created_at: datetime
    updated_at: datetime


class BookmarkUpdate(BaseModel):
    """Schema for updating a bookmark."""
    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    priority: Optional[int] = Field(None, ge=0, description="Priority (non-negative)")


class BookmarkListCreate(BaseModel):
    """Schema for creating a bookmark list."""
    name: str = Field(..., min_length=1, max_length=255, description="List name")
    description: Optional[str] = None
    character_id: Optional[int] = None
    corporation_id: Optional[int] = None
    is_shared: bool = Field(default=False, description="Whether list is shared")


class BookmarkList(BaseModel):
    """Bookmark list entity."""
    id: int
    name: str
    description: Optional[str]
    character_id: Optional[int]
    corporation_id: Optional[int]
    is_shared: bool
    item_count: int = 0
    created_at: datetime
    updated_at: datetime


class BookmarkWithPosition(Bookmark):
    """Bookmark with position field for list items."""
    position: int = Field(..., description="Position in list")
