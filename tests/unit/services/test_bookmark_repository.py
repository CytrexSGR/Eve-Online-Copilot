"""Tests for bookmark repository."""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock, call, ANY

from src.services.bookmark.repository import BookmarkRepository
from src.services.bookmark.models import BookmarkCreate, BookmarkListCreate
from src.core.exceptions import EVECopilotError


@pytest.fixture
def mock_db_pool():
    """Create mock database pool."""
    return Mock()


@pytest.fixture
def repository(mock_db_pool):
    """Create repository with mocked database."""
    return BookmarkRepository(mock_db_pool)


@pytest.fixture
def mock_cursor():
    """Create mock cursor."""
    cursor = MagicMock()
    cursor.fetchone = Mock()
    cursor.fetchall = Mock()
    cursor.rowcount = 1
    return cursor


@pytest.fixture
def mock_connection(mock_cursor):
    """Create mock connection with cursor."""
    conn = MagicMock()
    conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
    conn.cursor.return_value.__exit__ = Mock(return_value=False)
    return conn


class TestBookmarkCreate:
    """Test creating bookmarks."""

    def test_create_bookmark_success(self, repository, mock_db_pool, mock_connection, mock_cursor):
        """Test successfully creating a bookmark."""
        mock_db_pool.get_connection.return_value.__enter__ = Mock(return_value=mock_connection)
        mock_db_pool.get_connection.return_value.__exit__ = Mock(return_value=False)

        mock_cursor.fetchone.return_value = {
            "id": 1,
            "type_id": 648,
            "item_name": "Badger",
            "character_id": 123,
            "corporation_id": None,
            "notes": "Test bookmark",
            "tags": ["mining"],
            "priority": 5,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }

        data = BookmarkCreate(
            type_id=648,
            item_name="Badger",
            character_id=123,
            notes="Test bookmark",
            tags=["mining"],
            priority=5
        )
        result = repository.create(data)

        assert result["id"] == 1
        assert result["type_id"] == 648
        assert result["item_name"] == "Badger"
        mock_cursor.execute.assert_called_once()
        mock_connection.commit.assert_called_once()

    def test_create_bookmark_with_defaults(self, repository, mock_db_pool, mock_connection, mock_cursor):
        """Test creating bookmark with default values."""
        mock_db_pool.get_connection.return_value.__enter__ = Mock(return_value=mock_connection)
        mock_db_pool.get_connection.return_value.__exit__ = Mock(return_value=False)

        mock_cursor.fetchone.return_value = {
            "id": 1,
            "type_id": 648,
            "item_name": "Badger",
            "character_id": None,
            "corporation_id": None,
            "notes": None,
            "tags": [],
            "priority": 0,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }

        data = BookmarkCreate(type_id=648, item_name="Badger")
        result = repository.create(data)

        assert result["tags"] == []
        assert result["priority"] == 0

    def test_create_bookmark_database_error(self, repository, mock_db_pool, mock_connection):
        """Test handling database error during create."""
        mock_db_pool.get_connection.return_value.__enter__ = Mock(return_value=mock_connection)
        mock_db_pool.get_connection.return_value.__exit__ = Mock(return_value=False)
        mock_connection.cursor.return_value.__enter__.side_effect = Exception("Database error")

        data = BookmarkCreate(type_id=648, item_name="Badger")
        with pytest.raises(EVECopilotError) as exc_info:
            repository.create(data)
        assert "Failed to create bookmark" in str(exc_info.value)


class TestBookmarkGetById:
    """Test getting bookmark by ID."""

    def test_get_by_id_found(self, repository, mock_db_pool, mock_connection, mock_cursor):
        """Test getting existing bookmark by ID."""
        mock_db_pool.get_connection.return_value.__enter__ = Mock(return_value=mock_connection)
        mock_db_pool.get_connection.return_value.__exit__ = Mock(return_value=False)

        mock_cursor.fetchone.return_value = {
            "id": 1,
            "type_id": 648,
            "item_name": "Badger",
            "character_id": 123,
            "corporation_id": None,
            "notes": "Test",
            "tags": ["mining"],
            "priority": 5,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }

        result = repository.get_by_id(1)

        assert result is not None
        assert result["id"] == 1
        assert result["item_name"] == "Badger"
        mock_cursor.execute.assert_called_once()

    def test_get_by_id_not_found(self, repository, mock_db_pool, mock_connection, mock_cursor):
        """Test getting non-existent bookmark."""
        mock_db_pool.get_connection.return_value.__enter__ = Mock(return_value=mock_connection)
        mock_db_pool.get_connection.return_value.__exit__ = Mock(return_value=False)
        mock_cursor.fetchone.return_value = None

        result = repository.get_by_id(999)

        assert result is None


class TestBookmarkGetAll:
    """Test getting all bookmarks."""

    def test_get_all_without_filters(self, repository, mock_db_pool, mock_connection, mock_cursor):
        """Test getting all bookmarks without filters."""
        mock_db_pool.get_connection.return_value.__enter__ = Mock(return_value=mock_connection)
        mock_db_pool.get_connection.return_value.__exit__ = Mock(return_value=False)

        mock_cursor.fetchall.return_value = [
            {"id": 1, "type_id": 648, "item_name": "Badger", "priority": 5},
            {"id": 2, "type_id": 649, "item_name": "Bestower", "priority": 3}
        ]

        result = repository.get_all()

        assert len(result) == 2
        assert result[0]["item_name"] == "Badger"

    def test_get_all_with_character_filter(self, repository, mock_db_pool, mock_connection, mock_cursor):
        """Test getting bookmarks filtered by character."""
        mock_db_pool.get_connection.return_value.__enter__ = Mock(return_value=mock_connection)
        mock_db_pool.get_connection.return_value.__exit__ = Mock(return_value=False)

        mock_cursor.fetchall.return_value = [
            {"id": 1, "character_id": 123, "item_name": "Badger"}
        ]

        result = repository.get_all(character_id=123)

        assert len(result) == 1
        assert result[0]["character_id"] == 123

    def test_get_all_with_corporation_filter(self, repository, mock_db_pool, mock_connection, mock_cursor):
        """Test getting bookmarks filtered by corporation."""
        mock_db_pool.get_connection.return_value.__enter__ = Mock(return_value=mock_connection)
        mock_db_pool.get_connection.return_value.__exit__ = Mock(return_value=False)

        mock_cursor.fetchall.return_value = [
            {"id": 1, "corporation_id": 456, "item_name": "Badger"}
        ]

        result = repository.get_all(corporation_id=456)

        assert len(result) == 1


class TestBookmarkGetByListId:
    """Test getting bookmarks by list ID."""

    def test_get_by_list_id(self, repository, mock_db_pool, mock_connection, mock_cursor):
        """Test getting bookmarks in a list with position."""
        mock_db_pool.get_connection.return_value.__enter__ = Mock(return_value=mock_connection)
        mock_db_pool.get_connection.return_value.__exit__ = Mock(return_value=False)

        mock_cursor.fetchall.return_value = [
            {"id": 1, "item_name": "Badger", "position": 0},
            {"id": 2, "item_name": "Bestower", "position": 1}
        ]

        result = repository.get_by_list_id(1)

        assert len(result) == 2
        assert result[0]["position"] == 0
        assert result[1]["position"] == 1

    def test_get_by_list_id_empty(self, repository, mock_db_pool, mock_connection, mock_cursor):
        """Test getting bookmarks from empty list."""
        mock_db_pool.get_connection.return_value.__enter__ = Mock(return_value=mock_connection)
        mock_db_pool.get_connection.return_value.__exit__ = Mock(return_value=False)
        mock_cursor.fetchall.return_value = []

        result = repository.get_by_list_id(1)

        assert len(result) == 0


class TestBookmarkGetByType:
    """Test getting bookmark by type ID."""

    def test_get_by_type_found(self, repository, mock_db_pool, mock_connection, mock_cursor):
        """Test finding bookmark by type ID."""
        mock_db_pool.get_connection.return_value.__enter__ = Mock(return_value=mock_connection)
        mock_db_pool.get_connection.return_value.__exit__ = Mock(return_value=False)

        mock_cursor.fetchone.return_value = {
            "id": 1,
            "type_id": 648,
            "item_name": "Badger",
            "character_id": 123
        }

        result = repository.get_by_type(648, character_id=123)

        assert result is not None
        assert result["type_id"] == 648

    def test_get_by_type_not_found(self, repository, mock_db_pool, mock_connection, mock_cursor):
        """Test type not found."""
        mock_db_pool.get_connection.return_value.__enter__ = Mock(return_value=mock_connection)
        mock_db_pool.get_connection.return_value.__exit__ = Mock(return_value=False)
        mock_cursor.fetchone.return_value = None

        result = repository.get_by_type(999)

        assert result is None


class TestBookmarkIsBookmarked:
    """Test checking if item is bookmarked."""

    def test_is_bookmarked_true(self, repository, mock_db_pool, mock_connection, mock_cursor):
        """Test item is bookmarked."""
        mock_db_pool.get_connection.return_value.__enter__ = Mock(return_value=mock_connection)
        mock_db_pool.get_connection.return_value.__exit__ = Mock(return_value=False)
        mock_cursor.fetchone.return_value = (1,)

        result = repository.is_bookmarked(648, character_id=123)

        assert result is True

    def test_is_bookmarked_false(self, repository, mock_db_pool, mock_connection, mock_cursor):
        """Test item is not bookmarked."""
        mock_db_pool.get_connection.return_value.__enter__ = Mock(return_value=mock_connection)
        mock_db_pool.get_connection.return_value.__exit__ = Mock(return_value=False)
        mock_cursor.fetchone.return_value = (0,)

        result = repository.is_bookmarked(999)

        assert result is False


class TestBookmarkUpdate:
    """Test updating bookmarks."""

    def test_update_bookmark_success(self, repository, mock_db_pool, mock_connection, mock_cursor):
        """Test successfully updating bookmark."""
        mock_db_pool.get_connection.return_value.__enter__ = Mock(return_value=mock_connection)
        mock_db_pool.get_connection.return_value.__exit__ = Mock(return_value=False)

        updated_time = datetime.now()
        mock_cursor.fetchone.return_value = {
            "id": 1,
            "type_id": 648,
            "item_name": "Badger",
            "notes": "Updated notes",
            "tags": ["new", "tags"],
            "priority": 10,
            "updated_at": updated_time
        }

        updates = {"notes": "Updated notes", "tags": ["new", "tags"], "priority": 10}
        result = repository.update(1, updates)

        assert result is not None
        assert result["notes"] == "Updated notes"
        assert result["priority"] == 10
        mock_connection.commit.assert_called_once()

    def test_update_bookmark_empty_updates(self, repository, mock_db_pool, mock_connection, mock_cursor):
        """Test updating with empty updates returns current state."""
        mock_db_pool.get_connection.return_value.__enter__ = Mock(return_value=mock_connection)
        mock_db_pool.get_connection.return_value.__exit__ = Mock(return_value=False)

        mock_cursor.fetchone.return_value = {
            "id": 1,
            "type_id": 648,
            "item_name": "Badger"
        }

        result = repository.update(1, {})

        assert result is not None
        assert result["id"] == 1

    def test_update_bookmark_invalid_field(self, repository):
        """Test updating with invalid field raises ValueError."""
        updates = {"invalid_field": "value"}

        with pytest.raises(ValueError) as exc_info:
            repository.update(1, updates)
        assert "Cannot update field: invalid_field" in str(exc_info.value)

    def test_update_bookmark_whitelist_protection(self, repository):
        """Test field whitelist prevents SQL injection."""
        # Try to inject malicious field
        updates = {"notes": "OK", "id": 999, "character_id": 999}

        with pytest.raises(ValueError):
            repository.update(1, updates)

    def test_update_bookmark_not_found(self, repository, mock_db_pool, mock_connection, mock_cursor):
        """Test updating non-existent bookmark."""
        mock_db_pool.get_connection.return_value.__enter__ = Mock(return_value=mock_connection)
        mock_db_pool.get_connection.return_value.__exit__ = Mock(return_value=False)
        mock_cursor.fetchone.return_value = None

        result = repository.update(999, {"notes": "Test"})

        assert result is None


class TestBookmarkDelete:
    """Test deleting bookmarks."""

    def test_delete_bookmark_success(self, repository, mock_db_pool, mock_connection, mock_cursor):
        """Test successfully deleting bookmark."""
        mock_db_pool.get_connection.return_value.__enter__ = Mock(return_value=mock_connection)
        mock_db_pool.get_connection.return_value.__exit__ = Mock(return_value=False)
        mock_cursor.rowcount = 1

        result = repository.delete(1)

        assert result is True
        mock_connection.commit.assert_called_once()

    def test_delete_bookmark_not_found(self, repository, mock_db_pool, mock_connection, mock_cursor):
        """Test deleting non-existent bookmark."""
        mock_db_pool.get_connection.return_value.__enter__ = Mock(return_value=mock_connection)
        mock_db_pool.get_connection.return_value.__exit__ = Mock(return_value=False)
        mock_cursor.rowcount = 0

        result = repository.delete(999)

        assert result is False


class TestBookmarkListCreate:
    """Test creating bookmark lists."""

    def test_create_list_success(self, repository, mock_db_pool, mock_connection, mock_cursor):
        """Test successfully creating bookmark list."""
        mock_db_pool.get_connection.return_value.__enter__ = Mock(return_value=mock_connection)
        mock_db_pool.get_connection.return_value.__exit__ = Mock(return_value=False)

        mock_cursor.fetchone.return_value = {
            "id": 1,
            "name": "Fleet Bookmarks",
            "description": "Bookmarks for fleet ops",
            "character_id": 123,
            "corporation_id": None,
            "is_shared": True,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }

        data = BookmarkListCreate(
            name="Fleet Bookmarks",
            description="Bookmarks for fleet ops",
            character_id=123,
            is_shared=True
        )
        result = repository.create_list(data)

        assert result["id"] == 1
        assert result["name"] == "Fleet Bookmarks"
        assert result["is_shared"] is True
        mock_connection.commit.assert_called_once()

    def test_create_list_database_error(self, repository, mock_db_pool, mock_connection):
        """Test handling database error during list creation."""
        mock_db_pool.get_connection.return_value.__enter__ = Mock(return_value=mock_connection)
        mock_db_pool.get_connection.return_value.__exit__ = Mock(return_value=False)
        mock_connection.cursor.return_value.__enter__.side_effect = Exception("Database error")

        data = BookmarkListCreate(name="Test List")
        with pytest.raises(EVECopilotError) as exc_info:
            repository.create_list(data)
        assert "Failed to create bookmark list" in str(exc_info.value)


class TestBookmarkListGet:
    """Test getting bookmark lists."""

    def test_get_lists_without_filters(self, repository, mock_db_pool, mock_connection, mock_cursor):
        """Test getting all lists without filters."""
        mock_db_pool.get_connection.return_value.__enter__ = Mock(return_value=mock_connection)
        mock_db_pool.get_connection.return_value.__exit__ = Mock(return_value=False)

        mock_cursor.fetchall.return_value = [
            {"id": 1, "name": "List 1", "item_count": 5},
            {"id": 2, "name": "List 2", "item_count": 3}
        ]

        result = repository.get_lists()

        assert len(result) == 2
        assert result[0]["item_count"] == 5

    def test_get_lists_with_character_filter(self, repository, mock_db_pool, mock_connection, mock_cursor):
        """Test getting lists for specific character."""
        mock_db_pool.get_connection.return_value.__enter__ = Mock(return_value=mock_connection)
        mock_db_pool.get_connection.return_value.__exit__ = Mock(return_value=False)

        mock_cursor.fetchall.return_value = [
            {"id": 1, "character_id": 123, "name": "My List", "item_count": 5}
        ]

        result = repository.get_lists(character_id=123)

        assert len(result) == 1
        assert result[0]["character_id"] == 123


class TestBookmarkListOperations:
    """Test bookmark list item operations."""

    def test_add_to_list_success(self, repository, mock_db_pool, mock_connection, mock_cursor):
        """Test successfully adding bookmark to list."""
        mock_db_pool.get_connection.return_value.__enter__ = Mock(return_value=mock_connection)
        mock_db_pool.get_connection.return_value.__exit__ = Mock(return_value=False)
        mock_cursor.rowcount = 1

        result = repository.add_to_list(list_id=1, bookmark_id=1, position=0)

        assert result is True
        mock_connection.commit.assert_called_once()

    def test_add_to_list_already_exists(self, repository, mock_db_pool, mock_connection, mock_cursor):
        """Test adding bookmark that already exists in list."""
        mock_db_pool.get_connection.return_value.__enter__ = Mock(return_value=mock_connection)
        mock_db_pool.get_connection.return_value.__exit__ = Mock(return_value=False)
        mock_cursor.rowcount = 0

        result = repository.add_to_list(list_id=1, bookmark_id=1, position=0)

        assert result is False

    def test_remove_from_list_success(self, repository, mock_db_pool, mock_connection, mock_cursor):
        """Test successfully removing bookmark from list."""
        mock_db_pool.get_connection.return_value.__enter__ = Mock(return_value=mock_connection)
        mock_db_pool.get_connection.return_value.__exit__ = Mock(return_value=False)
        mock_cursor.rowcount = 1

        result = repository.remove_from_list(list_id=1, bookmark_id=1)

        assert result is True
        mock_connection.commit.assert_called_once()

    def test_remove_from_list_not_found(self, repository, mock_db_pool, mock_connection, mock_cursor):
        """Test removing bookmark that's not in list."""
        mock_db_pool.get_connection.return_value.__enter__ = Mock(return_value=mock_connection)
        mock_db_pool.get_connection.return_value.__exit__ = Mock(return_value=False)
        mock_cursor.rowcount = 0

        result = repository.remove_from_list(list_id=1, bookmark_id=999)

        assert result is False
