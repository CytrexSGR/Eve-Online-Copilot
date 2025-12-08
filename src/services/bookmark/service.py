"""Bookmark service - business logic layer."""

from typing import List, Optional

from src.services.bookmark.models import (
    Bookmark,
    BookmarkCreate,
    BookmarkUpdate,
    BookmarkWithPosition,
    BookmarkList,
    BookmarkListCreate,
)
from src.services.bookmark.repository import BookmarkRepository
from src.core.exceptions import NotFoundError


class BookmarkService:
    """Business logic for bookmark management."""

    def __init__(self, repository: BookmarkRepository):
        """Initialize service with repository dependency.

        Args:
            repository: BookmarkRepository instance for data access
        """
        self.repo = repository

    def create_bookmark(self, data: BookmarkCreate) -> Bookmark:
        """Create a new bookmark.

        Args:
            data: Bookmark creation data

        Returns:
            Created Bookmark instance
        """
        result = self.repo.create(data)
        return Bookmark(**result)

    def get_bookmark(self, bookmark_id: int) -> Bookmark:
        """Get bookmark by ID.

        Args:
            bookmark_id: ID of the bookmark

        Returns:
            Bookmark instance

        Raises:
            NotFoundError: If bookmark doesn't exist
        """
        result = self.repo.get_by_id(bookmark_id)
        if not result:
            raise NotFoundError("Bookmark", bookmark_id)
        return Bookmark(**result)

    def get_bookmarks(
        self,
        character_id: Optional[int] = None,
        corporation_id: Optional[int] = None,
        list_id: Optional[int] = None
    ) -> List[Bookmark] | List[BookmarkWithPosition]:
        """Get bookmarks filtered by character/corporation/list.

        If list_id is provided, returns BookmarkWithPosition objects with position field.
        Otherwise returns regular Bookmark objects.

        Args:
            character_id: Optional character ID filter
            corporation_id: Optional corporation ID filter
            list_id: Optional list ID to get bookmarks from a specific list

        Returns:
            List of Bookmark or BookmarkWithPosition instances
        """
        if list_id is not None:
            # Get bookmarks from specific list with position
            results = self.repo.get_by_list_id(list_id)
            return [BookmarkWithPosition(**result) for result in results]
        else:
            # Get all bookmarks with filters
            results = self.repo.get_all(character_id, corporation_id)
            return [Bookmark(**result) for result in results]

    def get_bookmark_by_type(
        self,
        type_id: int,
        character_id: Optional[int] = None,
        corporation_id: Optional[int] = None
    ) -> Optional[Bookmark]:
        """Find bookmark by type_id.

        Args:
            type_id: EVE type ID to search for
            character_id: Optional character ID filter
            corporation_id: Optional corporation ID filter

        Returns:
            Bookmark instance if found, None otherwise
        """
        result = self.repo.get_by_type(type_id, character_id, corporation_id)
        if not result:
            return None
        return Bookmark(**result)

    def is_bookmarked(
        self,
        type_id: int,
        character_id: Optional[int] = None,
        corporation_id: Optional[int] = None
    ) -> bool:
        """Check if an item type is bookmarked.

        Args:
            type_id: EVE type ID to check
            character_id: Optional character ID filter
            corporation_id: Optional corporation ID filter

        Returns:
            True if bookmarked, False otherwise
        """
        return self.repo.is_bookmarked(type_id, character_id, corporation_id)

    def update_bookmark(self, bookmark_id: int, data: BookmarkUpdate) -> Bookmark:
        """Update bookmark fields.

        Args:
            bookmark_id: ID of bookmark to update
            data: Update data with optional fields

        Returns:
            Updated Bookmark instance

        Raises:
            NotFoundError: If bookmark doesn't exist
        """
        # Convert to dict and filter out None values
        updates = data.dict(exclude_none=True)

        result = self.repo.update(bookmark_id, updates)
        if not result:
            raise NotFoundError("Bookmark", bookmark_id)
        return Bookmark(**result)

    def delete_bookmark(self, bookmark_id: int) -> bool:
        """Delete a bookmark.

        Args:
            bookmark_id: ID of bookmark to delete

        Returns:
            True if deleted, False if bookmark didn't exist
        """
        return self.repo.delete(bookmark_id)

    # Bookmark List Methods

    def create_list(self, data: BookmarkListCreate) -> BookmarkList:
        """Create a new bookmark list.

        Args:
            data: List creation data

        Returns:
            Created BookmarkList instance
        """
        result = self.repo.create_list(data)
        return BookmarkList(**result)

    def get_lists(
        self,
        character_id: Optional[int] = None,
        corporation_id: Optional[int] = None
    ) -> List[BookmarkList]:
        """Get bookmark lists filtered by character/corporation.

        Args:
            character_id: Optional character ID filter
            corporation_id: Optional corporation ID filter

        Returns:
            List of BookmarkList instances with item counts
        """
        results = self.repo.get_lists(character_id, corporation_id)
        return [BookmarkList(**result) for result in results]

    def add_to_list(self, list_id: int, bookmark_id: int, position: int) -> bool:
        """Add a bookmark to a list.

        Args:
            list_id: ID of the list
            bookmark_id: ID of the bookmark to add
            position: Position in the list

        Returns:
            True if added, False if already exists
        """
        return self.repo.add_to_list(list_id, bookmark_id, position)

    def remove_from_list(self, list_id: int, bookmark_id: int) -> bool:
        """Remove a bookmark from a list.

        Args:
            list_id: ID of the list
            bookmark_id: ID of the bookmark to remove

        Returns:
            True if removed, False if not found
        """
        return self.repo.remove_from_list(list_id, bookmark_id)
