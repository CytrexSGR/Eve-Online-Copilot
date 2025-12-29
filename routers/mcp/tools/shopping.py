"""
Shopping MCP Tools
Shopping list management, regional comparison, cargo calculation, and wizard.
"""

from typing import Dict, Any, List
from ..handlers import api_proxy
from shopping_service import shopping_service


# Tool Definitions
TOOLS: List[Dict[str, Any]] = [
    {
        "name": "list_shopping_lists",
        "description": "Get all shopping lists. Returns list metadata with item counts and total values.",
        "parameters": []
    },
    {
        "name": "create_shopping_list",
        "description": "Create a new shopping list. Returns new list ID and initial state.",
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
        "name": "get_shopping_list",
        "description": "Get shopping list details with all items. Returns complete list with items, prices, and purchase status.",
        "parameters": [
            {
                "name": "list_id",
                "type": "integer",
                "required": True,
                "description": "Shopping list ID"
            }
        ]
    },
    {
        "name": "update_shopping_list",
        "description": "Update shopping list metadata (name, description). Modifies list properties without affecting items.",
        "parameters": [
            {
                "name": "list_id",
                "type": "integer",
                "required": True,
                "description": "List ID to update"
            },
            {
                "name": "name",
                "type": "string",
                "required": False,
                "description": "New name"
            },
            {
                "name": "description",
                "type": "string",
                "required": False,
                "description": "New description"
            }
        ]
    },
    {
        "name": "delete_shopping_list",
        "description": "Delete a shopping list and all its items. Permanent deletion.",
        "parameters": [
            {
                "name": "list_id",
                "type": "integer",
                "required": True,
                "description": "List ID to delete"
            }
        ]
    },
    {
        "name": "add_shopping_item",
        "description": "Add item to shopping list. Supports manual quantity or blueprint-based material calculation.",
        "parameters": [
            {
                "name": "list_id",
                "type": "integer",
                "required": True,
                "description": "List ID"
            },
            {
                "name": "type_id",
                "type": "integer",
                "required": True,
                "description": "Item type ID"
            },
            {
                "name": "quantity",
                "type": "integer",
                "required": True,
                "description": "Quantity needed"
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
        "name": "update_shopping_item",
        "description": "Update shopping list item details. Modify quantity, notes, or other properties.",
        "parameters": [
            {
                "name": "item_id",
                "type": "integer",
                "required": True,
                "description": "Item ID to update"
            },
            {
                "name": "quantity",
                "type": "integer",
                "required": False,
                "description": "New quantity"
            },
            {
                "name": "notes",
                "type": "string",
                "required": False,
                "description": "New notes"
            }
        ]
    },
    {
        "name": "delete_shopping_item",
        "description": "Remove item from shopping list.",
        "parameters": [
            {
                "name": "item_id",
                "type": "integer",
                "required": True,
                "description": "Item ID to delete"
            }
        ]
    },
    {
        "name": "mark_item_purchased",
        "description": "Mark shopping list item as purchased. Tracks shopping progress.",
        "parameters": [
            {
                "name": "item_id",
                "type": "integer",
                "required": True,
                "description": "Item ID to mark purchased"
            }
        ]
    },
    {
        "name": "unmark_item_purchased",
        "description": "Unmark item as purchased (mark as needed again).",
        "parameters": [
            {
                "name": "item_id",
                "type": "integer",
                "required": True,
                "description": "Item ID to unmark"
            }
        ]
    },
    {
        "name": "set_purchase_region",
        "description": "Set preferred purchase region for shopping list item. Locks item to specific region for price calculations.",
        "parameters": [
            {
                "name": "item_id",
                "type": "integer",
                "required": True,
                "description": "Item ID"
            },
            {
                "name": "region_id",
                "type": "integer",
                "required": True,
                "description": "Region to purchase from"
            }
        ]
    },
    {
        "name": "update_item_runs",
        "description": "Update blueprint runs for item in shopping list. Recalculates material needs based on runs.",
        "parameters": [
            {
                "name": "item_id",
                "type": "integer",
                "required": True,
                "description": "Item ID"
            },
            {
                "name": "runs",
                "type": "integer",
                "required": True,
                "description": "Number of blueprint runs"
            }
        ]
    },
    {
        "name": "set_build_decision",
        "description": "Set build/buy decision for item. Marks whether to build from blueprint or buy from market.",
        "parameters": [
            {
                "name": "item_id",
                "type": "integer",
                "required": True,
                "description": "Item ID"
            },
            {
                "name": "build",
                "type": "boolean",
                "required": True,
                "description": "True to build, False to buy"
            }
        ]
    },
    {
        "name": "calculate_item_materials",
        "description": "Calculate materials needed for item production. Returns material breakdown without adding to list.",
        "parameters": [
            {
                "name": "item_id",
                "type": "integer",
                "required": True,
                "description": "Item ID in shopping list"
            }
        ]
    },
    {
        "name": "apply_materials_to_list",
        "description": "Apply calculated materials to shopping list. Adds all required materials as separate items.",
        "parameters": [
            {
                "name": "item_id",
                "type": "integer",
                "required": True,
                "description": "Item ID"
            }
        ]
    },
    {
        "name": "get_item_with_materials",
        "description": "Get shopping list item with material breakdown. Shows item plus all required materials.",
        "parameters": [
            {
                "name": "item_id",
                "type": "integer",
                "required": True,
                "description": "Item ID"
            }
        ]
    },
    {
        "name": "add_production_to_list",
        "description": "Add production item with materials to shopping list. Automatically calculates and adds all materials needed.",
        "parameters": [
            {
                "name": "list_id",
                "type": "integer",
                "required": True,
                "description": "Shopping list ID"
            },
            {
                "name": "type_id",
                "type": "integer",
                "required": True,
                "description": "Item to produce"
            },
            {
                "name": "runs",
                "type": "integer",
                "required": False,
                "description": "Blueprint runs (default: 1)",
                "default": 1
            },
            {
                "name": "me",
                "type": "integer",
                "required": False,
                "description": "Material efficiency (default: 10)",
                "default": 10
            }
        ]
    },
    {
        "name": "export_shopping_list",
        "description": "Export shopping list to EVE Online format. Returns text formatted for pasting into EVE client.",
        "parameters": [
            {
                "name": "list_id",
                "type": "integer",
                "required": True,
                "description": "List ID to export"
            }
        ]
    },
    {
        "name": "get_list_by_region",
        "description": "Group shopping list items by purchase region. Shows regional breakdown for multi-region shopping.",
        "parameters": [
            {
                "name": "list_id",
                "type": "integer",
                "required": True,
                "description": "List ID"
            }
        ]
    },
    {
        "name": "get_regional_comparison",
        "description": "Compare shopping list total cost across regions. Returns price comparison to find cheapest region.",
        "parameters": [
            {
                "name": "list_id",
                "type": "integer",
                "required": True,
                "description": "List ID"
            },
            {
                "name": "regions",
                "type": "string",
                "required": False,
                "description": "Comma-separated region IDs (default: major hubs)",
                "default": "10000002,10000043,10000030,10000032"
            }
        ]
    },
    {
        "name": "get_cargo_summary",
        "description": "Calculate cargo requirements for shopping list. Returns total volume, recommended ships, and trip calculations.",
        "parameters": [
            {
                "name": "list_id",
                "type": "integer",
                "required": True,
                "description": "List ID"
            }
        ]
    },
    {
        "name": "get_transport_options",
        "description": "Get transport ship recommendations for shopping list. Suggests appropriate haulers based on volume and value.",
        "parameters": [
            {
                "name": "list_id",
                "type": "integer",
                "required": True,
                "description": "List ID"
            },
            {
                "name": "security",
                "type": "string",
                "required": False,
                "description": "Security status (highsec, lowsec, nullsec)",
                "enum": ["highsec", "lowsec", "nullsec"],
                "default": "highsec"
            }
        ]
    },
    {
        "name": "calculate_shopping_route",
        "description": "Calculate optimal shopping route through multiple regions. Returns ordered route visiting all purchase locations.",
        "parameters": [
            {
                "name": "list_id",
                "type": "integer",
                "required": True,
                "description": "List ID"
            },
            {
                "name": "start_system",
                "type": "string",
                "required": True,
                "description": "Starting system name or ID"
            }
        ]
    },
    {
        "name": "wizard_calculate_materials",
        "description": "Shopping wizard step 1: Calculate materials for production. Returns material breakdown with build/buy recommendations.",
        "parameters": [
            {
                "name": "type_id",
                "type": "integer",
                "required": True,
                "description": "Item to build"
            },
            {
                "name": "quantity",
                "type": "integer",
                "required": False,
                "description": "Quantity (default: 1)",
                "default": 1
            },
            {
                "name": "me",
                "type": "integer",
                "required": False,
                "description": "ME level (default: 10)",
                "default": 10
            }
        ]
    },
    {
        "name": "wizard_compare_regions",
        "description": "Shopping wizard step 2: Compare regional prices for materials. Returns best regions to purchase from.",
        "parameters": [
            {
                "name": "materials",
                "type": "string",
                "required": True,
                "description": "Comma-separated material type_ids from wizard step 1"
            },
            {
                "name": "regions",
                "type": "string",
                "required": False,
                "description": "Regions to compare (default: major hubs)",
                "default": "10000002,10000043,10000030,10000032"
            }
        ]
    }
]


# Tool Handlers
def handle_list_shopping_lists(args: Dict[str, Any]) -> Dict[str, Any]:
    """List all shopping lists."""
    return api_proxy.get("/api/shopping/lists")


def handle_create_shopping_list(args: Dict[str, Any]) -> Dict[str, Any]:
    """Create shopping list."""
    data = {
        "name": args.get("name"),
        "description": args.get("description", "")
    }
    return api_proxy.post("/api/shopping/lists", data=data)


def handle_get_shopping_list(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get shopping list details."""
    list_id = args.get("list_id")
    return api_proxy.get(f"/api/shopping/lists/{list_id}")


def handle_update_shopping_list(args: Dict[str, Any]) -> Dict[str, Any]:
    """Update shopping list."""
    list_id = args.get("list_id")
    data = {}
    if args.get("name"):
        data["name"] = args.get("name")
    if args.get("description"):
        data["description"] = args.get("description")
    return api_proxy.patch(f"/api/shopping/lists/{list_id}", data=data)


def handle_delete_shopping_list(args: Dict[str, Any]) -> Dict[str, Any]:
    """Delete shopping list."""
    list_id = args.get("list_id")
    return api_proxy.delete(f"/api/shopping/lists/{list_id}")


def handle_add_shopping_item(args: Dict[str, Any]) -> Dict[str, Any]:
    """Add item to shopping list."""
    list_id = args.get("list_id")
    data = {
        "type_id": args.get("type_id"),
        "quantity": args.get("quantity"),
        "notes": args.get("notes", "")
    }
    return api_proxy.post(f"/api/shopping/lists/{list_id}/items", data=data)


def handle_update_shopping_item(args: Dict[str, Any]) -> Dict[str, Any]:
    """Update shopping item."""
    item_id = args.get("item_id")
    data = {}
    if args.get("quantity"):
        data["quantity"] = args.get("quantity")
    if args.get("notes"):
        data["notes"] = args.get("notes")
    return api_proxy.patch(f"/api/shopping/items/{item_id}", data=data)


def handle_delete_shopping_item(args: Dict[str, Any]) -> Dict[str, Any]:
    """Delete shopping item."""
    item_id = args.get("item_id")
    return api_proxy.delete(f"/api/shopping/items/{item_id}")


def handle_mark_item_purchased(args: Dict[str, Any]) -> Dict[str, Any]:
    """Mark item as purchased."""
    item_id = args.get("item_id")
    return api_proxy.post(f"/api/shopping/items/{item_id}/purchased")


def handle_unmark_item_purchased(args: Dict[str, Any]) -> Dict[str, Any]:
    """Unmark item as purchased."""
    item_id = args.get("item_id")
    return api_proxy.delete(f"/api/shopping/items/{item_id}/purchased")


def handle_set_purchase_region(args: Dict[str, Any]) -> Dict[str, Any]:
    """Set purchase region."""
    item_id = args.get("item_id")
    data = {"region_id": args.get("region_id")}
    return api_proxy.patch(f"/api/shopping/items/{item_id}/region", data=data)


def handle_update_item_runs(args: Dict[str, Any]) -> Dict[str, Any]:
    """Update item runs."""
    item_id = args.get("item_id")
    data = {"runs": args.get("runs")}
    return api_proxy.patch(f"/api/shopping/items/{item_id}/runs", data=data)


def handle_set_build_decision(args: Dict[str, Any]) -> Dict[str, Any]:
    """Set build decision."""
    item_id = args.get("item_id")
    data = {"build": args.get("build")}
    return api_proxy.patch(f"/api/shopping/items/{item_id}/build-decision", data=data)


def handle_calculate_item_materials(args: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate materials for item."""
    item_id = args.get("item_id")
    return api_proxy.post(f"/api/shopping/items/{item_id}/calculate-materials")


def handle_apply_materials_to_list(args: Dict[str, Any]) -> Dict[str, Any]:
    """Apply materials to list."""
    item_id = args.get("item_id")
    return api_proxy.post(f"/api/shopping/items/{item_id}/apply-materials")


def handle_get_item_with_materials(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get item with materials."""
    item_id = args.get("item_id")
    return api_proxy.get(f"/api/shopping/items/{item_id}/with-materials")


def handle_add_production_to_list(args: Dict[str, Any]) -> Dict[str, Any]:
    """Add production to list."""
    list_id = args.get("list_id")
    type_id = args.get("type_id")
    params = {
        "runs": args.get("runs", 1),
        "me": args.get("me", 10)
    }
    return api_proxy.post(f"/api/shopping/lists/{list_id}/add-production/{type_id}", params=params)


def handle_export_shopping_list(args: Dict[str, Any]) -> Dict[str, Any]:
    """Export shopping list."""
    list_id = args.get("list_id")
    return api_proxy.get(f"/api/shopping/lists/{list_id}/export")


def handle_get_list_by_region(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get list grouped by region."""
    list_id = args.get("list_id")
    return api_proxy.get(f"/api/shopping/lists/{list_id}/by-region")


def handle_get_regional_comparison(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get regional price comparison."""
    list_id = args.get("list_id")
    regions = args.get("regions", "10000002,10000043,10000030,10000032")
    return api_proxy.get(f"/api/shopping/lists/{list_id}/regional-comparison", params={"regions": regions})


def handle_get_cargo_summary(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get cargo summary."""
    list_id = args.get("list_id")
    return api_proxy.get(f"/api/shopping/lists/{list_id}/cargo-summary")


def handle_get_transport_options(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get transport options."""
    list_id = args.get("list_id")
    security = args.get("security", "highsec")
    return api_proxy.get(f"/api/shopping/lists/{list_id}/transport-options", params={"security": security})


def handle_calculate_shopping_route(args: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate shopping route."""
    list_id = args.get("list_id")
    start_system = args.get("start_system")
    return api_proxy.get("/api/shopping/route", params={"list_id": list_id, "start_system": start_system})


def handle_wizard_calculate_materials(args: Dict[str, Any]) -> Dict[str, Any]:
    """Wizard: calculate materials."""
    data = {
        "type_id": args.get("type_id"),
        "quantity": args.get("quantity", 1),
        "me": args.get("me", 10)
    }
    return api_proxy.post("/api/shopping/wizard/calculate-materials", data=data)


def handle_wizard_compare_regions(args: Dict[str, Any]) -> Dict[str, Any]:
    """Wizard: compare regions."""
    materials = args.get("materials").split(",")
    regions = args.get("regions", "10000002,10000043,10000030,10000032")
    data = {
        "materials": [int(m.strip()) for m in materials],
        "regions": [int(r.strip()) for r in regions.split(",")]
    }
    return api_proxy.post("/api/shopping/wizard/compare-regions", data=data)


# Handler mapping
HANDLERS = {
    "list_shopping_lists": handle_list_shopping_lists,
    "create_shopping_list": handle_create_shopping_list,
    "get_shopping_list": handle_get_shopping_list,
    "update_shopping_list": handle_update_shopping_list,
    "delete_shopping_list": handle_delete_shopping_list,
    "add_shopping_item": handle_add_shopping_item,
    "update_shopping_item": handle_update_shopping_item,
    "delete_shopping_item": handle_delete_shopping_item,
    "mark_item_purchased": handle_mark_item_purchased,
    "unmark_item_purchased": handle_unmark_item_purchased,
    "set_purchase_region": handle_set_purchase_region,
    "update_item_runs": handle_update_item_runs,
    "set_build_decision": handle_set_build_decision,
    "calculate_item_materials": handle_calculate_item_materials,
    "apply_materials_to_list": handle_apply_materials_to_list,
    "get_item_with_materials": handle_get_item_with_materials,
    "add_production_to_list": handle_add_production_to_list,
    "export_shopping_list": handle_export_shopping_list,
    "get_list_by_region": handle_get_list_by_region,
    "get_regional_comparison": handle_get_regional_comparison,
    "get_cargo_summary": handle_get_cargo_summary,
    "get_transport_options": handle_get_transport_options,
    "calculate_shopping_route": handle_calculate_shopping_route,
    "wizard_calculate_materials": handle_wizard_calculate_materials,
    "wizard_compare_regions": handle_wizard_compare_regions
}
