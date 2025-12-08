"""
Bookmarks router - Bookmark management endpoints.
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional

from src.core.config import get_settings
from src.core.database import DatabasePool
from src.core.exceptions import NotFoundError, EVECopilotError
from src.services.bookmark.service import BookmarkService
from src.services.bookmark.repository import BookmarkRepository
from src.services.bookmark.models import BookmarkCreate, BookmarkUpdate, BookmarkListCreate

router = APIRouter(prefix="/api/bookmarks", tags=["Bookmarks"])


def get_bookmark_service() -> BookmarkService:
    """Dependency injection for BookmarkService."""
    settings = get_settings()
    db = DatabasePool(settings)
    repository = BookmarkRepository(db)
    return BookmarkService(repository)


@router.post("")
async def create_bookmark(
    request: BookmarkCreate,
    service: BookmarkService = Depends(get_bookmark_service)
):
    """Create a new bookmark"""
    try:
        result = service.create_bookmark(request)
        return result.model_dump()
    except EVECopilotError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
async def get_bookmarks(
    character_id: Optional[int] = Query(None),
    corporation_id: Optional[int] = Query(None),
    list_id: Optional[int] = Query(None),
    service: BookmarkService = Depends(get_bookmark_service)
):
    """Get bookmarks with optional filters"""
    try:
        bookmarks = service.get_bookmarks(character_id, corporation_id, list_id)
        # Convert list of Bookmark/BookmarkWithPosition models to dicts
        return {"bookmarks": [bookmark.model_dump() for bookmark in bookmarks]}
    except EVECopilotError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/check/{type_id}")
async def check_bookmark(
    type_id: int,
    character_id: Optional[int] = Query(None),
    corporation_id: Optional[int] = Query(None),
    service: BookmarkService = Depends(get_bookmark_service)
):
    """Check if item is bookmarked"""
    try:
        bookmark = service.get_bookmark_by_type(type_id, character_id, corporation_id)
        return {
            "is_bookmarked": bookmark is not None,
            "bookmark": bookmark.model_dump() if bookmark else None
        }
    except EVECopilotError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{bookmark_id}")
async def update_bookmark(
    bookmark_id: int,
    request: BookmarkUpdate,
    service: BookmarkService = Depends(get_bookmark_service)
):
    """Update a bookmark"""
    try:
        result = service.update_bookmark(bookmark_id, request)
        return result.model_dump()
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except EVECopilotError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{bookmark_id}")
async def delete_bookmark(
    bookmark_id: int,
    service: BookmarkService = Depends(get_bookmark_service)
):
    """Delete a bookmark"""
    try:
        if not service.delete_bookmark(bookmark_id):
            raise HTTPException(status_code=404, detail="Bookmark not found")
        return {"status": "deleted"}
    except EVECopilotError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/lists")
async def create_bookmark_list(
    request: BookmarkListCreate,
    service: BookmarkService = Depends(get_bookmark_service)
):
    """Create a bookmark list"""
    try:
        result = service.create_list(request)
        return result.model_dump()
    except EVECopilotError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/lists")
async def get_bookmark_lists(
    character_id: Optional[int] = Query(None),
    corporation_id: Optional[int] = Query(None),
    service: BookmarkService = Depends(get_bookmark_service)
):
    """Get bookmark lists"""
    try:
        lists = service.get_lists(character_id, corporation_id)
        return {"lists": [lst.model_dump() for lst in lists]}
    except EVECopilotError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/lists/{list_id}/items/{bookmark_id}")
async def add_to_list(
    list_id: int,
    bookmark_id: int,
    position: int = Query(0),
    service: BookmarkService = Depends(get_bookmark_service)
):
    """Add bookmark to list"""
    try:
        if not service.add_to_list(list_id, bookmark_id, position):
            raise HTTPException(status_code=400, detail="Could not add to list")
        return {"status": "added"}
    except EVECopilotError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/lists/{list_id}/items/{bookmark_id}")
async def remove_from_list(
    list_id: int,
    bookmark_id: int,
    service: BookmarkService = Depends(get_bookmark_service)
):
    """Remove bookmark from list"""
    try:
        if not service.remove_from_list(list_id, bookmark_id):
            raise HTTPException(status_code=404, detail="Item not in list")
        return {"status": "removed"}
    except EVECopilotError as e:
        raise HTTPException(status_code=500, detail=str(e))
