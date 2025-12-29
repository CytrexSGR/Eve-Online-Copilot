"""
Items & Materials MCP Tools
Item information, materials, volumes, and cargo calculations.
"""

from typing import Dict, Any, List
from ..handlers import api_proxy
from database import get_material_composition, get_item_info
from esi_client import esi_client
from config import REGIONS
from route_service import route_service
from cargo_service import cargo_service


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
    try:
        type_id = args.get("type_id")

        # Call database functions directly instead of HTTP request
        composition = get_material_composition(type_id)
        item = get_item_info(type_id)

        result = {
            "type_id": type_id,
            "item_name": item["typeName"] if item else f"Type {type_id}",
            "is_craftable": len(composition) > 0,
            "materials": [
                {"type_id": m["material_type_id"], "name": m["material_name"], "quantity": m["quantity"]}
                for m in composition
            ]
        }

        return {"content": [{"type": "text", "text": str(result)}]}
    except Exception as e:
        return {"error": f"Failed to get material composition: {str(e)}", "isError": True}


def handle_get_material_volumes(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get material volumes."""
    try:
        type_id = args.get("type_id")

        # Call esi_client directly instead of HTTP request
        item = get_item_info(type_id)
        volumes = {}
        for region_name, region_id in REGIONS.items():
            depth = esi_client.get_market_depth(region_id, type_id)
            volumes[region_name] = {
                "sell_volume": depth["sell_volume"],
                "lowest_sell": depth["lowest_sell_price"],
                "lowest_sell_volume": depth["lowest_sell_volume"],
                "sell_orders": depth["sell_orders"],
                "buy_volume": depth["buy_volume"],
                "highest_buy": depth["highest_buy_price"],
            }

        best_availability = max(
            [(r, v["sell_volume"]) for r, v in volumes.items()],
            key=lambda x: x[1], default=(None, 0)
        )

        result = {
            "type_id": type_id,
            "item_name": item["typeName"] if item else f"Type {type_id}",
            "volumes_by_region": volumes,
            "best_availability_region": best_availability[0],
            "best_availability_volume": best_availability[1]
        }

        return {"content": [{"type": "text", "text": str(result)}]}
    except Exception as e:
        return {"error": f"Failed to get material volumes: {str(e)}", "isError": True}


def handle_calculate_cargo_volume(args: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate cargo volume."""
    try:
        items_str = args.get("items")
        # Parse items string into list of dicts
        items = []
        for item_pair in items_str.split(","):
            type_id, quantity = item_pair.strip().split(":")
            items.append({"type_id": int(type_id), "quantity": int(quantity)})

        # Call cargo_service directly instead of HTTP request
        volume_info = cargo_service.calculate_cargo_volume(items)
        ship_recommendation = cargo_service.recommend_ship(volume_info['total_volume_m3'])

        result = {**volume_info, 'ship_recommendation': ship_recommendation}

        return {"content": [{"type": "text", "text": str(result)}]}
    except Exception as e:
        return {"error": f"Failed to calculate cargo volume: {str(e)}", "isError": True}


def handle_get_item_volume_info(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get item volume info."""
    try:
        type_id = args.get("type_id")

        # Call database directly instead of HTTP request
        item = get_item_info(type_id)
        if not item:
            return {"error": f"Item {type_id} not found", "isError": True}

        result = {
            "type_id": type_id,
            "item_name": item["typeName"],
            "volume_m3": item.get("volume", 0),
            "packaged_volume_m3": item.get("packagedVolume", item.get("volume", 0))
        }

        return {"content": [{"type": "text", "text": str(result)}]}
    except Exception as e:
        return {"error": f"Failed to get item volume info: {str(e)}", "isError": True}


def handle_search_systems(args: Dict[str, Any]) -> Dict[str, Any]:
    """Search systems."""
    try:
        query = args.get("query")

        # Try to parse as system ID first
        try:
            system_id = int(query)
            sys_info = route_service.get_system_by_id(system_id)
            if sys_info:
                return {"content": [{"type": "text", "text": str([sys_info])}]}
        except (ValueError, AttributeError):
            pass

        # Search by name using route_service
        sys_info = route_service.get_system_by_name(query)
        results = [sys_info] if sys_info else []

        return {"content": [{"type": "text", "text": str(results)}]}
    except Exception as e:
        return {"error": f"Failed to search systems: {str(e)}", "isError": True}


def handle_get_system_info(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get system info."""
    try:
        system_id = args.get("system_id")

        # Call route_service directly instead of HTTP request
        sys_info = route_service.get_system_by_id(system_id)
        if not sys_info:
            return {"error": f"System {system_id} not found", "isError": True}

        return {"content": [{"type": "text", "text": str(sys_info)}]}
    except Exception as e:
        return {"error": f"Failed to get system info: {str(e)}", "isError": True}


# Handler mapping
HANDLERS = {
    "get_material_composition": handle_get_material_composition,
    "get_material_volumes": handle_get_material_volumes,
    "calculate_cargo_volume": handle_calculate_cargo_volume,
    "get_item_volume_info": handle_get_item_volume_info,
    "search_systems": handle_search_systems,
    "get_system_info": handle_get_system_info
}
