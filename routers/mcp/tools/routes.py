"""
Routes & Navigation MCP Tools
Route calculation and navigation assistance.
"""

from typing import Dict, Any, List
from ..handlers import api_proxy


# Tool Definitions
TOOLS: List[Dict[str, Any]] = [
    {
        "name": "get_trade_hubs",
        "description": "Get list of major trade hubs. Returns hub systems with region information.",
        "parameters": []
    },
    {
        "name": "get_hub_distances",
        "description": "Get distances from system to all trade hubs. Returns jump counts to major hubs.",
        "parameters": [
            {
                "name": "from_system",
                "type": "string",
                "required": True,
                "description": "Starting system name or ID"
            }
        ]
    },
    {
        "name": "calculate_system_route",
        "description": "Calculate route between two systems using A* pathfinding. Returns optimal jump route.",
        "parameters": [
            {
                "name": "from_system",
                "type": "string",
                "required": True,
                "description": "Starting system name or ID"
            },
            {
                "name": "to_system",
                "type": "string",
                "required": True,
                "description": "Destination system name or ID"
            },
            {
                "name": "avoid_lowsec",
                "type": "boolean",
                "required": False,
                "description": "Avoid low security systems (default: false)",
                "default": False
            }
        ]
    },
    {
        "name": "calculate_route_with_danger",
        "description": "Calculate route with danger scores for each system. Returns route with safety ratings.",
        "parameters": [
            {
                "name": "from_system",
                "type": "string",
                "required": True,
                "description": "Starting system"
            },
            {
                "name": "to_system",
                "type": "string",
                "required": True,
                "description": "Destination system"
            },
            {
                "name": "avoid_dangerous",
                "type": "boolean",
                "required": False,
                "description": "Avoid high-danger systems (default: false)",
                "default": False
            }
        ]
    },
    {
        "name": "get_system_region",
        "description": "Get region for solar system. Returns region ID and name for system.",
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
def handle_get_trade_hubs(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get trade hubs."""
    return api_proxy.get("/api/route/hubs")


def handle_get_hub_distances(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get hub distances."""
    from_system = args.get("from_system")
    return api_proxy.get(f"/api/route/distances/{from_system}")


def handle_calculate_system_route(args: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate route."""
    from_system = args.get("from_system")
    to_system = args.get("to_system")
    avoid_lowsec = args.get("avoid_lowsec", False)
    return api_proxy.get(
        f"/api/route/{from_system}/{to_system}",
        params={"avoid_lowsec": avoid_lowsec}
    )


def handle_calculate_route_with_danger(args: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate route with danger."""
    from_system = args.get("from_system")
    to_system = args.get("to_system")
    avoid_dangerous = args.get("avoid_dangerous", False)
    return api_proxy.get(
        f"/api/war/route/safe/{from_system}/{to_system}",
        params={"avoid_dangerous": avoid_dangerous}
    )


def handle_get_system_region(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get system region."""
    system_id = args.get("system_id")
    # Use system search to get region info
    return api_proxy.get("/api/systems/search", params={"q": str(system_id)})


# Handler mapping
HANDLERS = {
    "get_trade_hubs": handle_get_trade_hubs,
    "get_hub_distances": handle_get_hub_distances,
    "calculate_system_route": handle_calculate_system_route,
    "calculate_route_with_danger": handle_calculate_route_with_danger,
    "get_system_region": handle_get_system_region
}
