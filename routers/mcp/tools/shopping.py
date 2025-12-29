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
    try:
        result = shopping_service.get_lists()
        return {"content": [{"type": "text", "text": str(result)}]}
    except Exception as e:
        return {"error": f"Failed to list shopping lists: {str(e)}", "isError": True}


def handle_create_shopping_list(args: Dict[str, Any]) -> Dict[str, Any]:
    """Create shopping list."""
    try:
        name = args.get("name")
        description = args.get("description", "")
        result = shopping_service.create_list(name=name, description=description)
        return {"content": [{"type": "text", "text": str(result)}]}
    except Exception as e:
        return {"error": f"Failed to create shopping list: {str(e)}", "isError": True}


def handle_get_shopping_list(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get shopping list details."""
    try:
        list_id = args.get("list_id")
        result = shopping_service.get_list_with_items(list_id)
        return {"content": [{"type": "text", "text": str(result)}]}
    except Exception as e:
        return {"error": f"Failed to get shopping list: {str(e)}", "isError": True}


def handle_update_shopping_list(args: Dict[str, Any]) -> Dict[str, Any]:
    """Update shopping list."""
    try:
        list_id = args.get("list_id")
        name = args.get("name")
        description = args.get("description")
        result = shopping_service.update_list(list_id=list_id, name=name, description=description)
        return {"content": [{"type": "text", "text": str(result)}]}
    except Exception as e:
        return {"error": f"Failed to update shopping list: {str(e)}", "isError": True}


def handle_delete_shopping_list(args: Dict[str, Any]) -> Dict[str, Any]:
    """Delete shopping list."""
    try:
        list_id = args.get("list_id")
        success = shopping_service.delete_list(list_id)
        return {"content": [{"type": "text", "text": str({"deleted": success, "list_id": list_id})}]}
    except Exception as e:
        return {"error": f"Failed to delete shopping list: {str(e)}", "isError": True}


def handle_add_shopping_item(args: Dict[str, Any]) -> Dict[str, Any]:
    """Add item to shopping list."""
    try:
        list_id = args.get("list_id")
        type_id = args.get("type_id")
        quantity = args.get("quantity")
        notes = args.get("notes", "")
        result = shopping_service.add_item(list_id=list_id, type_id=type_id, quantity=quantity, notes=notes)
        return {"content": [{"type": "text", "text": str(result)}]}
    except Exception as e:
        return {"error": f"Failed to add shopping item: {str(e)}", "isError": True}


def handle_update_shopping_item(args: Dict[str, Any]) -> Dict[str, Any]:
    """Update shopping item."""
    try:
        item_id = args.get("item_id")
        quantity = args.get("quantity")
        notes = args.get("notes")
        result = shopping_service.update_item(item_id=item_id, quantity=quantity, notes=notes)
        return {"content": [{"type": "text", "text": str(result)}]}
    except Exception as e:
        return {"error": f"Failed to update shopping item: {str(e)}", "isError": True}


def handle_delete_shopping_item(args: Dict[str, Any]) -> Dict[str, Any]:
    """Delete shopping item."""
    try:
        item_id = args.get("item_id")
        success = shopping_service.remove_item(item_id)
        return {"content": [{"type": "text", "text": str({"deleted": success, "item_id": item_id})}]}
    except Exception as e:
        return {"error": f"Failed to delete shopping item: {str(e)}", "isError": True}


def handle_mark_item_purchased(args: Dict[str, Any]) -> Dict[str, Any]:
    """Mark item as purchased."""
    try:
        item_id = args.get("item_id")
        result = shopping_service.mark_purchased(item_id=item_id)
        return {"content": [{"type": "text", "text": str(result)}]}
    except Exception as e:
        return {"error": f"Failed to mark item purchased: {str(e)}", "isError": True}


def handle_unmark_item_purchased(args: Dict[str, Any]) -> Dict[str, Any]:
    """Unmark item as purchased."""
    try:
        item_id = args.get("item_id")
        result = shopping_service.unmark_purchased(item_id)
        return {"content": [{"type": "text", "text": str(result)}]}
    except Exception as e:
        return {"error": f"Failed to unmark item purchased: {str(e)}", "isError": True}


def handle_set_purchase_region(args: Dict[str, Any]) -> Dict[str, Any]:
    """Set purchase region."""
    try:
        item_id = args.get("item_id")
        region_id = args.get("region_id")
        result = shopping_service.update_item(item_id=item_id, region_id=region_id)
        return {"content": [{"type": "text", "text": str(result)}]}
    except Exception as e:
        return {"error": f"Failed to set purchase region: {str(e)}", "isError": True}


def handle_update_item_runs(args: Dict[str, Any]) -> Dict[str, Any]:
    """Update item runs."""
    try:
        item_id = args.get("item_id")
        runs = args.get("runs")
        result = shopping_service.update_item_runs(item_id=item_id, runs=runs)
        return {"content": [{"type": "text", "text": str(result)}]}
    except Exception as e:
        return {"error": f"Failed to update item runs: {str(e)}", "isError": True}


def handle_set_build_decision(args: Dict[str, Any]) -> Dict[str, Any]:
    """Set build decision."""
    try:
        item_id = args.get("item_id")
        build = args.get("build")
        result = shopping_service.update_build_decision(item_id=item_id, build_instead_of_buy=build)
        return {"content": [{"type": "text", "text": str(result)}]}
    except Exception as e:
        return {"error": f"Failed to set build decision: {str(e)}", "isError": True}


def handle_calculate_item_materials(args: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate materials for item."""
    try:
        item_id = args.get("item_id")
        result = shopping_service.calculate_materials(item_id)
        return {"content": [{"type": "text", "text": str(result)}]}
    except Exception as e:
        return {"error": f"Failed to calculate materials: {str(e)}", "isError": True}


def handle_apply_materials_to_list(args: Dict[str, Any]) -> Dict[str, Any]:
    """Apply materials to list."""
    try:
        item_id = args.get("item_id")
        result = shopping_service.apply_materials(item_id=item_id)
        return {"content": [{"type": "text", "text": str(result)}]}
    except Exception as e:
        return {"error": f"Failed to apply materials: {str(e)}", "isError": True}


def handle_get_item_with_materials(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get item with materials."""
    try:
        item_id = args.get("item_id")
        result = shopping_service.get_product_with_materials(item_id)
        return {"content": [{"type": "text", "text": str(result)}]}
    except Exception as e:
        return {"error": f"Failed to get item with materials: {str(e)}", "isError": True}


def handle_add_production_to_list(args: Dict[str, Any]) -> Dict[str, Any]:
    """Add production to list."""
    try:
        list_id = args.get("list_id")
        type_id = args.get("type_id")
        runs = args.get("runs", 1)
        me = args.get("me", 10)
        result = shopping_service.add_materials_from_production(list_id=list_id, type_id=type_id, runs=runs, me_level=me)
        return {"content": [{"type": "text", "text": str(result)}]}
    except Exception as e:
        return {"error": f"Failed to add production to list: {str(e)}", "isError": True}


def handle_export_shopping_list(args: Dict[str, Any]) -> Dict[str, Any]:
    """Export shopping list."""
    try:
        list_id = args.get("list_id")
        result = shopping_service.export_multibuy(list_id)
        return {"content": [{"type": "text", "text": str(result)}]}
    except Exception as e:
        return {"error": f"Failed to export shopping list: {str(e)}", "isError": True}


def handle_get_list_by_region(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get list grouped by region."""
    try:
        list_id = args.get("list_id")
        result = shopping_service.get_by_region(list_id)
        return {"content": [{"type": "text", "text": str(result)}]}
    except Exception as e:
        return {"error": f"Failed to get list by region: {str(e)}", "isError": True}


def handle_get_regional_comparison(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get regional price comparison."""
    try:
        list_id = args.get("list_id")
        regions = args.get("regions", "10000002,10000043,10000030,10000032")
        result = shopping_service.compare_regions(list_id=list_id, regions=regions)
        return {"content": [{"type": "text", "text": str(result)}]}
    except Exception as e:
        return {"error": f"Failed to get regional comparison: {str(e)}", "isError": True}


def handle_get_cargo_summary(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get cargo summary."""
    try:
        list_id = args.get("list_id")
        result = shopping_service.get_cargo_summary(list_id)
        return {"content": [{"type": "text", "text": str(result)}]}
    except Exception as e:
        return {"error": f"Failed to get cargo summary: {str(e)}", "isError": True}


def handle_get_transport_options(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get transport options."""
    try:
        list_id = args.get("list_id")
        security = args.get("security", "highsec")

        # Get cargo summary first
        cargo = shopping_service.get_cargo_summary(list_id)
        volume = cargo.get("total_volume", 0)

        # Calculate transport options based on volume and security
        from cargo_service import cargo_service
        result = cargo_service.get_transport_options(volume=volume, security=security)

        return {"content": [{"type": "text", "text": str(result)}]}
    except Exception as e:
        return {"error": f"Failed to get transport options: {str(e)}", "isError": True}


def handle_calculate_shopping_route(args: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate shopping route."""
    try:
        list_id = args.get("list_id")
        start_system = args.get("start_system")

        # Get shopping list regions
        items_by_region = shopping_service.get_by_region(list_id)

        # Calculate optimal route through regions
        from route_service import route_service
        result = route_service.calculate_shopping_route(
            start_system=start_system,
            items_by_region=items_by_region
        )

        return {"content": [{"type": "text", "text": str(result)}]}
    except Exception as e:
        return {"error": f"Failed to calculate shopping route: {str(e)}", "isError": True}


def handle_wizard_calculate_materials(args: Dict[str, Any]) -> Dict[str, Any]:
    """Wizard: calculate materials."""
    try:
        type_id = args.get("type_id")
        quantity = args.get("quantity", 1)
        me = args.get("me", 10)

        # Calculate materials for production
        result = shopping_service.get_product_with_materials(
            type_id=type_id,
            quantity=quantity,
            me_level=me
        )

        return {"content": [{"type": "text", "text": str(result)}]}
    except Exception as e:
        return {"error": f"Failed to calculate materials: {str(e)}", "isError": True}


def handle_wizard_compare_regions(args: Dict[str, Any]) -> Dict[str, Any]:
    """Wizard: compare regions."""
    try:
        materials_str = args.get("materials")
        regions = args.get("regions", "10000002,10000043,10000030,10000032")

        # Parse material type IDs
        material_ids = [int(m.strip()) for m in materials_str.split(",")]

        # Use market service for multi-region comparison
        from market_service import market_service
        result = market_service.compare_regions_for_materials(
            material_type_ids=material_ids,
            regions=regions
        )

        return {"content": [{"type": "text", "text": str(result)}]}
    except Exception as e:
        return {"error": f"Failed to compare regions: {str(e)}", "isError": True}


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
