"""Tests for Bookmark Service following TDD approach."""

import pytest
from datetime import datetime
from unittest.mock import Mock

from src.services.bookmark.models import (
    Bookmark, BookmarkCreate, BookmarkUpdate, BookmarkWithPosition,
    BookmarkList, BookmarkListCreate
)
from src.services.bookmark.repository import BookmarkRepository
from src.core.exceptions import NotFoundError

# Service will be imported once implemented
try:
    from src.services.bookmark.service import BookmarkService
except ImportError:
    BookmarkService = None


@pytest.fixture
def mock_repository():
    """Create a mock BookmarkRepository."""
    return Mock()


@pytest.fixture
def bookmark_service(mock_repository):
    """Create BookmarkService with mock repository."""
    if BookmarkService is None:
        pytest.skip("BookmarkService not implemented yet")
    return BookmarkService(repository=mock_repository)


class TestCreateBookmark:
    """Tests for create_bookmark method."""

    def test_create_bookmark_success(self, bookmark_service, mock_repository):
        """Test successful bookmark creation."""
        bookmark_data = BookmarkCreate(
            type_id=648,
            item_name="Tritanium",
            character_id=123,
            notes="Important material",
            tags=["manufacturing", "minerals"],
            priority=5
        )

        mock_repository.create.return_value = {
            "id": 1,
            "type_id": 648,
            "item_name": "Tritanium",
            "character_id": 123,
            "corporation_id": None,
            "notes": "Important material",
            "tags": ["manufacturing", "minerals"],
            "priority": 5,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }

        result = bookmark_service.create_bookmark(bookmark_data)

        assert isinstance(result, Bookmark)
        assert result.id == 1
        assert result.type_id == 648
        assert result.item_name == "Tritanium"
        mock_repository.create.assert_called_once_with(bookmark_data)


class TestGetBookmark:
    """Tests for get_bookmark method."""

    def test_get_bookmark_success(self, bookmark_service, mock_repository):
        """Test getting bookmark by ID."""
        mock_repository.get_by_id.return_value = {
            "id": 1,
            "type_id": 648,
            "item_name": "Tritanium",
            "character_id": 123,
            "corporation_id": None,
            "notes": "Test",
            "tags": [],
            "priority": 0,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }

        result = bookmark_service.get_bookmark(1)

        assert isinstance(result, Bookmark)
        assert result.id == 1
        assert result.type_id == 648
        mock_repository.get_by_id.assert_called_once_with(1)

    def test_get_bookmark_not_found(self, bookmark_service, mock_repository):
        """Test getting non-existent bookmark raises NotFoundError."""
        mock_repository.get_by_id.return_value = None

        with pytest.raises(NotFoundError) as exc_info:
            bookmark_service.get_bookmark(999)

        assert exc_info.value.resource == "Bookmark"
        assert exc_info.value.resource_id == 999


class TestGetBookmarks:
    """Tests for get_bookmarks method."""

    def test_get_bookmarks_all(self, bookmark_service, mock_repository):
        """Test getting all bookmarks without filters."""
        mock_repository.get_all.return_value = [
            {
                "id": 1,
                "type_id": 648,
                "item_name": "Tritanium",
                "character_id": None,
                "corporation_id": None,
                "notes": None,
                "tags": [],
                "priority": 0,
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
        ]

        result = bookmark_service.get_bookmarks()

        assert len(result) == 1
        assert all(isinstance(b, Bookmark) for b in result)
        mock_repository.get_all.assert_called_once_with(None, None)

    def test_get_bookmarks_by_list_id(self, bookmark_service, mock_repository):
        """Test getting bookmarks by list ID returns BookmarkWithPosition."""
        mock_repository.get_by_list_id.return_value = [
            {
                "id": 1,
                "type_id": 648,
                "item_name": "Tritanium",
                "character_id": 123,
                "corporation_id": None,
                "notes": None,
                "tags": [],
                "priority": 0,
                "position": 1,
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
        ]

        result = bookmark_service.get_bookmarks(list_id=1)

        assert len(result) == 1
        assert all(isinstance(b, BookmarkWithPosition) for b in result)
        assert result[0].position == 1
        mock_repository.get_by_list_id.assert_called_once_with(1)


class TestUpdateBookmark:
    """Tests for update_bookmark method."""

    def test_update_bookmark_success(self, bookmark_service, mock_repository):
        """Test updating bookmark successfully."""
        update_data = BookmarkUpdate(
            notes="Updated notes",
            tags=["new", "tags"],
            priority=10
        )

        mock_repository.update.return_value = {
            "id": 1,
            "type_id": 648,
            "item_name": "Tritanium",
            "character_id": 123,
            "corporation_id": None,
            "notes": "Updated notes",
            "tags": ["new", "tags"],
            "priority": 10,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }

        result = bookmark_service.update_bookmark(1, update_data)

        assert isinstance(result, Bookmark)
        assert result.notes == "Updated notes"
        assert result.priority == 10
        mock_repository.update.assert_called_once()

    def test_update_bookmark_not_found(self, bookmark_service, mock_repository):
        """Test updating non-existent bookmark raises NotFoundError."""
        update_data = BookmarkUpdate(notes="Test")
        mock_repository.update.return_value = None

        with pytest.raises(NotFoundError) as exc_info:
            bookmark_service.update_bookmark(999, update_data)

        assert exc_info.value.resource == "Bookmark"
        assert exc_info.value.resource_id == 999


class TestDeleteBookmark:
    """Tests for delete_bookmark method."""

    def test_delete_bookmark_success(self, bookmark_service, mock_repository):
        """Test deleting bookmark successfully."""
        mock_repository.delete.return_value = True

        result = bookmark_service.delete_bookmark(1)

        assert result is True
        mock_repository.delete.assert_called_once_with(1)


class TestGetBookmarkByType:
    """Tests for get_bookmark_by_type method."""

    def test_get_bookmark_by_type_found(self, bookmark_service, mock_repository):
        """Test finding bookmark by type_id."""
        mock_repository.get_by_type.return_value = {
            "id": 1,
            "type_id": 648,
            "item_name": "Tritanium",
            "character_id": 123,
            "corporation_id": None,
            "notes": None,
            "tags": [],
            "priority": 0,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }

        result = bookmark_service.get_bookmark_by_type(648, character_id=123)

        assert isinstance(result, Bookmark)
        assert result.type_id == 648
        mock_repository.get_by_type.assert_called_once_with(648, 123, None)


class TestIsBookmarked:
    """Tests for is_bookmarked method."""

    def test_is_bookmarked_true(self, bookmark_service, mock_repository):
        """Test checking if item is bookmarked returns True."""
        mock_repository.is_bookmarked.return_value = True

        result = bookmark_service.is_bookmarked(648, character_id=123)

        assert result is True
        mock_repository.is_bookmarked.assert_called_once_with(648, 123, None)


class TestCreateList:
    """Tests for create_list method."""

    def test_create_list_success(self, bookmark_service, mock_repository):
        """Test creating bookmark list successfully."""
        list_data = BookmarkListCreate(
            name="My Minerals",
            description="Important minerals",
            character_id=123,
            is_shared=False
        )

        mock_repository.create_list.return_value = {
            "id": 1,
            "name": "My Minerals",
            "description": "Important minerals",
            "character_id": 123,
            "corporation_id": None,
            "is_shared": False,
            "item_count": 0,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }

        result = bookmark_service.create_list(list_data)

        assert isinstance(result, BookmarkList)
        assert result.name == "My Minerals"
        mock_repository.create_list.assert_called_once_with(list_data)


class TestGetLists:
    """Tests for get_lists method."""

    def test_get_lists_all(self, bookmark_service, mock_repository):
        """Test getting all bookmark lists."""
        mock_repository.get_lists.return_value = [
            {
                "id": 1,
                "name": "List 1",
                "description": None,
                "character_id": None,
                "corporation_id": None,
                "is_shared": True,
                "item_count": 5,
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
        ]

        result = bookmark_service.get_lists()

        assert len(result) == 1
        assert all(isinstance(lst, BookmarkList) for lst in result)
        mock_repository.get_lists.assert_called_once_with(None, None)


class TestAddToList:
    """Tests for add_to_list method."""

    def test_add_to_list_success(self, bookmark_service, mock_repository):
        """Test adding bookmark to list successfully."""
        mock_repository.add_to_list.return_value = True

        result = bookmark_service.add_to_list(list_id=1, bookmark_id=5, position=10)

        assert result is True
        mock_repository.add_to_list.assert_called_once_with(1, 5, 10)


class TestRemoveFromList:
    """Tests for remove_from_list method."""

    def test_remove_from_list_success(self, bookmark_service, mock_repository):
        """Test removing bookmark from list successfully."""
        mock_repository.remove_from_list.return_value = True

        result = bookmark_service.remove_from_list(list_id=1, bookmark_id=5)

        assert result is True
        mock_repository.remove_from_list.assert_called_once_with(1, 5)
