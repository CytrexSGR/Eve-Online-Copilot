"""
Items & Materials MCP Tools
Item information, materials, volumes, and cargo calculations.
"""

from typing import Dict, Any, List
from ..handlers import api_proxy


# Tool Definitions
TOOLS: List[Dict[str, Any]] = [
    {
        "name": "get_material_composition",
        "description": "Get material composition for item production. Returns materials needed from blueprint.",
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
        "name": "get_material_volumes",
        "description": "Get material availability across regions. Returns where materials can be sourced with volumes.",
        "parameters": [
            {
                "name": "type_id",
                "type": "integer",
                "required": True,
                "description": "Material type ID"
            }
        ]
    },
    {
        "name": "calculate_cargo_volume",
        "description": "Calculate total cargo volume for items. Returns volume calculations and ship recommendations.",
        "parameters": [
            {
                "name": "items",
                "type": "string",
                "required": True,
                "description": "Comma-separated type_id:quantity pairs (e.g., '34:1000,35:500')"
            }
        ]
    },
    {
        "name": "get_item_volume_info",
        "description": "Get volume information for single item. Returns packaged/assembled volumes.",
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
        "name": "search_systems",
        "description": "Search solar systems by name. Returns matching systems with IDs and security status.",
        "parameters": [
            {
                "name": "query",
                "type": "string",
                "required": True,
                "description": "System name search query"
            }
        ]
    },
    {
        "name": "get_system_info",
        "description": "Get solar system information. Returns system details, security, region, and connections.",
        "parameters": [
            {
                "name": "system_id",
                "type": "integer",
                "required": True,
                "description": "Solar system ID"
            }
        ]
    }
]


# Tool Handlers
def handle_get_material_composition(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get material composition."""
    type_id = args.get("type_id")
    return api_proxy.get(f"/api/materials/{type_id}/composition")


def handle_get_material_volumes(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get material volumes."""
    type_id = args.get("type_id")
    return api_proxy.get(f"/api/materials/{type_id}/volumes")


def handle_calculate_cargo_volume(args: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate cargo volume."""
    items_str = args.get("items")
    # Parse items string into list of dicts
    items = []
    for item_pair in items_str.split(","):
        type_id, quantity = item_pair.strip().split(":")
        items.append({"type_id": int(type_id), "quantity": int(quantity)})

    data = {"items": items}
    return api_proxy.post("/api/cargo/calculate", data=data)


def handle_get_item_volume_info(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get item volume info."""
    type_id = args.get("type_id")
    return api_proxy.get(f"/api/cargo/item/{type_id}")


def handle_search_systems(args: Dict[str, Any]) -> Dict[str, Any]:
    """Search systems."""
    query = args.get("query")
    return api_proxy.get("/api/systems/search", params={"q": query})


def handle_get_system_info(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get system info."""
    system_id = args.get("system_id")
    # This might not have a dedicated endpoint, use search with ID
    return api_proxy.get("/api/systems/search", params={"q": str(system_id)})


# Handler mapping
HANDLERS = {
    "get_material_composition": handle_get_material_composition,
    "get_material_volumes": handle_get_material_volumes,
    "calculate_cargo_volume": handle_calculate_cargo_volume,
    "get_item_volume_info": handle_get_item_volume_info,
    "search_systems": handle_search_systems,
    "get_system_info": handle_get_system_info
}
