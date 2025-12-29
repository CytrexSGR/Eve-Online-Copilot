"""
Bookmark MCP Tools
Bookmark and bookmark list management.
"""

from typing import Dict, Any, List
from ..handlers import api_proxy
from bookmark_service import bookmark_service


# Tool Definitions
TOOLS: List[Dict[str, Any]] = [
    {
        "name": "create_bookmark",
        "description": "Create a bookmark for an item. Save items for quick access later.",
        "parameters": [
            {
                "name": "type_id",
                "type": "integer",
                "required": True,
                "description": "Item type ID to bookmark"
            },
            {
                "name": "notes",
                "type": "string",
                "required": False,
                "description": "Optional notes"
            }
        ]
    },
    {
        "name": "list_bookmarks",
        "description": "Get all bookmarks. Returns saved items with notes and creation dates.",
        "parameters": []
    },
    {
        "name": "check_bookmark",
        "description": "Check if item is bookmarked. Returns bookmark status for specific item.",
        "parameters": [
            {
                "name": "type_id",
                "type": "integer",
                "required": True,
                "description": "Item type ID"
            }
        ]
    },
    {
        "name": "update_bookmark",
        "description": "Update bookmark notes. Modify notes for existing bookmark.",
        "parameters": [
            {
                "name": "bookmark_id",
                "type": "integer",
                "required": True,
                "description": "Bookmark ID"
            },
            {
                "name": "notes",
                "type": "string",
                "required": True,
                "description": "New notes"
            }
        ]
    },
    {
        "name": "delete_bookmark",
        "description": "Delete a bookmark. Remove item from bookmarks.",
        "parameters": [
            {
                "name": "bookmark_id",
                "type": "integer",
                "required": True,
                "description": "Bookmark ID to delete"
            }
        ]
    },
    {
        "name": "create_bookmark_list",
        "description": "Create a bookmark list/folder. Organize bookmarks into collections.",
        "parameters": [
            {
                "name": "name",
                "type": "string",
                "required": True,
                "description": "List name"
            },
            {
                "name": "description",
                "type": "string",
                "required": False,
                "description": "Optional description"
            }
        ]
    },
    {
        "name": "list_bookmark_lists",
        "description": "Get all bookmark lists. Returns bookmark folders/collections.",
        "parameters": []
    },
    {
        "name": "add_to_bookmark_list",
        "description": "Add bookmark to a list. Organize bookmark into specific collection.",
        "parameters": [
            {
                "name": "list_id",
                "type": "integer",
                "required": True,
                "description": "Bookmark list ID"
            },
            {
                "name": "bookmark_id",
                "type": "integer",
                "required": True,
                "description": "Bookmark ID to add"
            }
        ]
    },
    {
        "name": "remove_from_bookmark_list",
        "description": "Remove bookmark from list. Unorganize bookmark from collection.",
        "parameters": [
            {
                "name": "list_id",
                "type": "integer",
                "required": True,
                "description": "Bookmark list ID"
            },
            {
                "name": "bookmark_id",
                "type": "integer",
                "required": True,
                "description": "Bookmark ID to remove"
            }
        ]
    }
]


# Tool Handlers
def handle_create_bookmark(args: Dict[str, Any]) -> Dict[str, Any]:
    """Create bookmark."""
    try:
        type_id = args.get("type_id")
        notes = args.get("notes", "")

        # Call bookmark_service directly instead of HTTP request
        result = bookmark_service.create_bookmark(type_id=type_id, notes=notes)

        return {"content": [{"type": "text", "text": str(result)}]}
    except Exception as e:
        return {"error": f"Failed to create bookmark: {str(e)}", "isError": True}


def handle_list_bookmarks(args: Dict[str, Any]) -> Dict[str, Any]:
    """List bookmarks."""
    try:
        # Call bookmark_service directly instead of HTTP request
        result = bookmark_service.get_all_bookmarks()

        return {"content": [{"type": "text", "text": str(result)}]}
    except Exception as e:
        return {"error": f"Failed to list bookmarks: {str(e)}", "isError": True}


def handle_check_bookmark(args: Dict[str, Any]) -> Dict[str, Any]:
    """Check bookmark."""
    try:
        type_id = args.get("type_id")

        # Call bookmark_service directly instead of HTTP request
        is_bookmarked = bookmark_service.is_bookmarked(type_id)
        result = {"type_id": type_id, "is_bookmarked": is_bookmarked}

        if is_bookmarked:
            bookmark = bookmark_service.get_bookmark_by_type(type_id)
            result["bookmark"] = bookmark

        return {"content": [{"type": "text", "text": str(result)}]}
    except Exception as e:
        return {"error": f"Failed to check bookmark: {str(e)}", "isError": True}


def handle_update_bookmark(args: Dict[str, Any]) -> Dict[str, Any]:
    """Update bookmark."""
    try:
        bookmark_id = args.get("bookmark_id")
        notes = args.get("notes")

        # Call bookmark_service directly instead of HTTP request
        result = bookmark_service.update_bookmark(bookmark_id=bookmark_id, notes=notes)

        return {"content": [{"type": "text", "text": str(result)}]}
    except Exception as e:
        return {"error": f"Failed to update bookmark: {str(e)}", "isError": True}


def handle_delete_bookmark(args: Dict[str, Any]) -> Dict[str, Any]:
    """Delete bookmark."""
    try:
        bookmark_id = args.get("bookmark_id")

        # Call bookmark_service directly instead of HTTP request
        success = bookmark_service.delete_bookmark(bookmark_id)
        result = {"bookmark_id": bookmark_id, "deleted": success}

        return {"content": [{"type": "text", "text": str(result)}]}
    except Exception as e:
        return {"error": f"Failed to delete bookmark: {str(e)}", "isError": True}


def handle_create_bookmark_list(args: Dict[str, Any]) -> Dict[str, Any]:
    """Create bookmark list."""
    try:
        name = args.get("name")
        description = args.get("description", "")

        # Call bookmark_service directly instead of HTTP request
        result = bookmark_service.create_bookmark_list(name=name, description=description)

        return {"content": [{"type": "text", "text": str(result)}]}
    except Exception as e:
        return {"error": f"Failed to create bookmark list: {str(e)}", "isError": True}


def handle_list_bookmark_lists(args: Dict[str, Any]) -> Dict[str, Any]:
    """List bookmark lists."""
    try:
        # Call bookmark_service directly instead of HTTP request
        result = bookmark_service.get_all_bookmark_lists()

        return {"content": [{"type": "text", "text": str(result)}]}
    except Exception as e:
        return {"error": f"Failed to list bookmark lists: {str(e)}", "isError": True}


def handle_add_to_bookmark_list(args: Dict[str, Any]) -> Dict[str, Any]:
    """Add to bookmark list."""
    try:
        list_id = args.get("list_id")
        bookmark_id = args.get("bookmark_id")

        # Call bookmark_service directly instead of HTTP request
        success = bookmark_service.add_to_list(list_id=list_id, bookmark_id=bookmark_id)
        result = {"list_id": list_id, "bookmark_id": bookmark_id, "added": success}

        return {"content": [{"type": "text", "text": str(result)}]}
    except Exception as e:
        return {"error": f"Failed to add to bookmark list: {str(e)}", "isError": True}


def handle_remove_from_bookmark_list(args: Dict[str, Any]) -> Dict[str, Any]:
    """Remove from bookmark list."""
    try:
        list_id = args.get("list_id")
        bookmark_id = args.get("bookmark_id")

        # Call bookmark_service directly instead of HTTP request
        success = bookmark_service.remove_from_list(list_id=list_id, bookmark_id=bookmark_id)
        result = {"list_id": list_id, "bookmark_id": bookmark_id, "removed": success}

        return {"content": [{"type": "text", "text": str(result)}]}
    except Exception as e:
        return {"error": f"Failed to remove from bookmark list: {str(e)}", "isError": True}


# Handler mapping
HANDLERS = {
    "create_bookmark": handle_create_bookmark,
    "list_bookmarks": handle_list_bookmarks,
    "check_bookmark": handle_check_bookmark,
    "update_bookmark": handle_update_bookmark,
    "delete_bookmark": handle_delete_bookmark,
    "create_bookmark_list": handle_create_bookmark_list,
    "list_bookmark_lists": handle_list_bookmark_lists,
    "add_to_bookmark_list": handle_add_to_bookmark_list,
    "remove_from_bookmark_list": handle_remove_from_bookmark_list
}
