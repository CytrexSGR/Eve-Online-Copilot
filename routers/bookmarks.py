"""
Bookmarks router - Bookmark management endpoints.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from bookmark_service import bookmark_service
from schemas import BookmarkCreate, BookmarkUpdate, BookmarkListCreate

router = APIRouter(prefix="/api/bookmarks", tags=["Bookmarks"])


@router.post("")
async def create_bookmark(request: BookmarkCreate):
    """Create a new bookmark"""
    return bookmark_service.create_bookmark(
        type_id=request.type_id, item_name=request.item_name,
        character_id=request.character_id, corporation_id=request.corporation_id,
        notes=request.notes, tags=request.tags, priority=request.priority
    )


@router.get("")
async def get_bookmarks(
    character_id: Optional[int] = Query(None),
    corporation_id: Optional[int] = Query(None),
    list_id: Optional[int] = Query(None)
):
    """Get bookmarks with optional filters"""
    return bookmark_service.get_bookmarks(character_id, corporation_id, list_id)


@router.get("/check/{type_id}")
async def check_bookmark(
    type_id: int,
    character_id: Optional[int] = Query(None),
    corporation_id: Optional[int] = Query(None)
):
    """Check if item is bookmarked"""
    bookmark = bookmark_service.get_bookmark_by_type(type_id, character_id, corporation_id)
    return {"is_bookmarked": bookmark is not None, "bookmark": bookmark}


@router.patch("/{bookmark_id}")
async def update_bookmark(bookmark_id: int, request: BookmarkUpdate):
    """Update a bookmark"""
    result = bookmark_service.update_bookmark(
        bookmark_id=bookmark_id, notes=request.notes,
        tags=request.tags, priority=request.priority
    )
    if not result:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    return result


@router.delete("/{bookmark_id}")
async def delete_bookmark(bookmark_id: int):
    """Delete a bookmark"""
    if not bookmark_service.delete_bookmark(bookmark_id):
        raise HTTPException(status_code=404, detail="Bookmark not found")
    return {"status": "deleted"}


@router.post("/lists")
async def create_bookmark_list(request: BookmarkListCreate):
    """Create a bookmark list"""
    return bookmark_service.create_list(
        name=request.name, description=request.description,
        character_id=request.character_id, corporation_id=request.corporation_id,
        is_shared=request.is_shared
    )


@router.get("/lists")
async def get_bookmark_lists(
    character_id: Optional[int] = Query(None),
    corporation_id: Optional[int] = Query(None)
):
    """Get bookmark lists"""
    return bookmark_service.get_lists(character_id, corporation_id)


@router.post("/lists/{list_id}/items/{bookmark_id}")
async def add_to_list(list_id: int, bookmark_id: int, position: int = Query(0)):
    """Add bookmark to list"""
    if not bookmark_service.add_to_list(list_id, bookmark_id, position):
        raise HTTPException(status_code=400, detail="Could not add to list")
    return {"status": "added"}


@router.delete("/lists/{list_id}/items/{bookmark_id}")
async def remove_from_list(list_id: int, bookmark_id: int):
    """Remove bookmark from list"""
    if not bookmark_service.remove_from_list(list_id, bookmark_id):
        raise HTTPException(status_code=404, detail="Item not in list")
    return {"status": "removed"}
