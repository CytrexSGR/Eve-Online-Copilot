"""
Bookmark MCP Tools
Bookmark and bookmark list management.
"""

from typing import Dict, Any, List
from ..handlers import api_proxy


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
    data = {
        "type_id": args.get("type_id"),
        "notes": args.get("notes", "")
    }
    return api_proxy.post("/api/bookmarks", data=data)


def handle_list_bookmarks(args: Dict[str, Any]) -> Dict[str, Any]:
    """List bookmarks."""
    return api_proxy.get("/api/bookmarks")


def handle_check_bookmark(args: Dict[str, Any]) -> Dict[str, Any]:
    """Check bookmark."""
    type_id = args.get("type_id")
    return api_proxy.get(f"/api/bookmarks/check/{type_id}")


def handle_update_bookmark(args: Dict[str, Any]) -> Dict[str, Any]:
    """Update bookmark."""
    bookmark_id = args.get("bookmark_id")
    data = {"notes": args.get("notes")}
    return api_proxy.patch(f"/api/bookmarks/{bookmark_id}", data=data)


def handle_delete_bookmark(args: Dict[str, Any]) -> Dict[str, Any]:
    """Delete bookmark."""
    bookmark_id = args.get("bookmark_id")
    return api_proxy.delete(f"/api/bookmarks/{bookmark_id}")


def handle_create_bookmark_list(args: Dict[str, Any]) -> Dict[str, Any]:
    """Create bookmark list."""
    data = {
        "name": args.get("name"),
        "description": args.get("description", "")
    }
    return api_proxy.post("/api/bookmarks/lists", data=data)


def handle_list_bookmark_lists(args: Dict[str, Any]) -> Dict[str, Any]:
    """List bookmark lists."""
    return api_proxy.get("/api/bookmarks/lists")


def handle_add_to_bookmark_list(args: Dict[str, Any]) -> Dict[str, Any]:
    """Add to bookmark list."""
    list_id = args.get("list_id")
    bookmark_id = args.get("bookmark_id")
    return api_proxy.post(f"/api/bookmarks/lists/{list_id}/items/{bookmark_id}")


def handle_remove_from_bookmark_list(args: Dict[str, Any]) -> Dict[str, Any]:
    """Remove from bookmark list."""
    list_id = args.get("list_id")
    bookmark_id = args.get("bookmark_id")
    return api_proxy.delete(f"/api/bookmarks/lists/{list_id}/items/{bookmark_id}")


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
