"""Tests for bookmark models."""

import pytest
from datetime import datetime
from pydantic import ValidationError

from src.services.bookmark.models import (
    BookmarkCreate,
    Bookmark,
    BookmarkUpdate,
    BookmarkListCreate,
    BookmarkList,
    BookmarkWithPosition
)


class TestBookmarkCreate:
    """Test BookmarkCreate model."""

    def test_valid_bookmark_create(self):
        """Test creating valid bookmark."""
        data = BookmarkCreate(
            type_id=648,
            item_name="Badger",
            character_id=123,
            notes="Test bookmark",
            tags=["mining", "hauler"],
            priority=5
        )
        assert data.type_id == 648
        assert data.item_name == "Badger"
        assert data.character_id == 123
        assert data.notes == "Test bookmark"
        assert data.tags == ["mining", "hauler"]
        assert data.priority == 5

    def test_bookmark_create_with_corporation(self):
        """Test creating bookmark with corporation ID."""
        data = BookmarkCreate(
            type_id=648,
            item_name="Badger",
            corporation_id=456
        )
        assert data.type_id == 648
        assert data.corporation_id == 456
        assert data.character_id is None

    def test_bookmark_create_minimal(self):
        """Test creating bookmark with minimal required fields."""
        data = BookmarkCreate(
            type_id=648,
            item_name="Badger"
        )
        assert data.type_id == 648
        assert data.item_name == "Badger"
        assert data.character_id is None
        assert data.corporation_id is None
        assert data.notes is None
        assert data.tags == []
        assert data.priority == 0

    def test_bookmark_create_invalid_type_id_zero(self):
        """Test type_id must be greater than 0."""
        with pytest.raises(ValidationError) as exc_info:
            BookmarkCreate(type_id=0, item_name="Test")
        assert "type_id" in str(exc_info.value)

    def test_bookmark_create_invalid_type_id_negative(self):
        """Test type_id must be positive."""
        with pytest.raises(ValidationError) as exc_info:
            BookmarkCreate(type_id=-1, item_name="Test")
        assert "type_id" in str(exc_info.value)

    def test_bookmark_create_invalid_priority_negative(self):
        """Test priority must be non-negative."""
        with pytest.raises(ValidationError) as exc_info:
            BookmarkCreate(type_id=648, item_name="Test", priority=-1)
        assert "priority" in str(exc_info.value)

    def test_bookmark_create_empty_item_name(self):
        """Test item_name cannot be empty."""
        with pytest.raises(ValidationError) as exc_info:
            BookmarkCreate(type_id=648, item_name="")
        assert "item_name" in str(exc_info.value)

    def test_bookmark_create_tags_default_empty_list(self):
        """Test tags defaults to empty list."""
        data = BookmarkCreate(type_id=648, item_name="Test")
        assert data.tags == []
        assert isinstance(data.tags, list)


class TestBookmark:
    """Test Bookmark model."""

    def test_valid_bookmark(self):
        """Test creating valid bookmark entity."""
        now = datetime.now()
        data = Bookmark(
            id=1,
            type_id=648,
            item_name="Badger",
            character_id=123,
            corporation_id=None,
            notes="Test bookmark",
            tags=["mining", "hauler"],
            priority=5,
            created_at=now,
            updated_at=now
        )
        assert data.id == 1
        assert data.type_id == 648
        assert data.item_name == "Badger"
        assert data.character_id == 123
        assert data.created_at == now
        assert data.updated_at == now


class TestBookmarkUpdate:
    """Test BookmarkUpdate model."""

    def test_bookmark_update_all_fields(self):
        """Test updating all allowed fields."""
        data = BookmarkUpdate(
            notes="Updated notes",
            tags=["new", "tags"],
            priority=10
        )
        assert data.notes == "Updated notes"
        assert data.tags == ["new", "tags"]
        assert data.priority == 10

    def test_bookmark_update_partial(self):
        """Test updating only some fields."""
        data = BookmarkUpdate(notes="Only notes")
        assert data.notes == "Only notes"
        assert data.tags is None
        assert data.priority is None

    def test_bookmark_update_empty(self):
        """Test creating empty update object."""
        data = BookmarkUpdate()
        assert data.notes is None
        assert data.tags is None
        assert data.priority is None

    def test_bookmark_update_invalid_priority_negative(self):
        """Test priority must be non-negative."""
        with pytest.raises(ValidationError) as exc_info:
            BookmarkUpdate(priority=-1)
        assert "priority" in str(exc_info.value)


class TestBookmarkListCreate:
    """Test BookmarkListCreate model."""

    def test_valid_bookmark_list_create(self):
        """Test creating valid bookmark list."""
        data = BookmarkListCreate(
            name="My Fleet Bookmarks",
            description="Bookmarks for fleet ops",
            character_id=123,
            is_shared=True
        )
        assert data.name == "My Fleet Bookmarks"
        assert data.description == "Bookmarks for fleet ops"
        assert data.character_id == 123
        assert data.is_shared is True

    def test_bookmark_list_create_minimal(self):
        """Test creating bookmark list with minimal fields."""
        data = BookmarkListCreate(name="Test List")
        assert data.name == "Test List"
        assert data.description is None
        assert data.character_id is None
        assert data.corporation_id is None
        assert data.is_shared is False

    def test_bookmark_list_create_empty_name(self):
        """Test name cannot be empty."""
        with pytest.raises(ValidationError) as exc_info:
            BookmarkListCreate(name="")
        assert "name" in str(exc_info.value)


class TestBookmarkList:
    """Test BookmarkList model."""

    def test_valid_bookmark_list(self):
        """Test creating valid bookmark list entity."""
        now = datetime.now()
        data = BookmarkList(
            id=1,
            name="My Fleet Bookmarks",
            description="Bookmarks for fleet ops",
            character_id=123,
            corporation_id=None,
            is_shared=True,
            item_count=5,
            created_at=now,
            updated_at=now
        )
        assert data.id == 1
        assert data.name == "My Fleet Bookmarks"
        assert data.item_count == 5
        assert data.created_at == now


class TestBookmarkWithPosition:
    """Test BookmarkWithPosition model."""

    def test_bookmark_with_position(self):
        """Test bookmark with position field."""
        now = datetime.now()
        data = BookmarkWithPosition(
            id=1,
            type_id=648,
            item_name="Badger",
            character_id=123,
            corporation_id=None,
            notes="Test bookmark",
            tags=["mining"],
            priority=5,
            created_at=now,
            updated_at=now,
            position=10
        )
        assert data.id == 1
        assert data.position == 10
        assert data.item_name == "Badger"

    def test_bookmark_with_position_zero(self):
        """Test position can be zero."""
        now = datetime.now()
        data = BookmarkWithPosition(
            id=1,
            type_id=648,
            item_name="Badger",
            character_id=None,
            corporation_id=None,
            notes=None,
            tags=[],
            priority=0,
            created_at=now,
            updated_at=now,
            position=0
        )
        assert data.position == 0
