"""
Routes & Navigation MCP Tools
Route calculation and navigation assistance.
"""

from typing import Dict, Any, List
from ..handlers import api_proxy
from route_service import route_service, TRADE_HUB_SYSTEMS


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
    try:
        # Call route_service directly instead of HTTP request
        result = {}
        for name, sys_id in TRADE_HUB_SYSTEMS.items():
            sys_info = route_service.get_system_by_name(name) or {}
            result[name] = {
                'system_id': sys_id,
                'system_name': sys_info.get('system_name', name.capitalize()),
                'security': sys_info.get('security', 0)
            }

        return {"content": [{"type": "text", "text": str(result)}]}
    except Exception as e:
        return {"error": f"Failed to get trade hubs: {str(e)}", "isError": True}


def handle_get_hub_distances(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get hub distances."""
    try:
        from_system = args.get("from_system")
        # Call route_service directly instead of HTTP request
        distances = route_service.get_hub_distances(from_system)
        return {"content": [{"type": "text", "text": str(distances)}]}
    except Exception as e:
        return {"error": f"Failed to get hub distances: {str(e)}", "isError": True}


def handle_calculate_system_route(args: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate route."""
    try:
        from_system = args.get("from_system")
        to_system = args.get("to_system")
        avoid_lowsec = args.get("avoid_lowsec", False)

        # Call route_service directly instead of HTTP request
        from_sys = route_service.get_system_by_name(from_system)
        to_sys = route_service.get_system_by_name(to_system)

        if not from_sys:
            return {"error": f"System not found: {from_system}", "isError": True}
        if not to_sys:
            return {"error": f"System not found: {to_system}", "isError": True}

        route = route_service.find_route(
            from_sys['system_id'], to_sys['system_id'],
            avoid_lowsec=avoid_lowsec, avoid_nullsec=True
        )

        if not route:
            return {"error": "No route found", "isError": True}

        travel_time = route_service.calculate_travel_time(route)
        result = {
            "from": from_sys, "to": to_sys,
            "route": route, "travel_time": travel_time,
            "highsec_only": avoid_lowsec,
            "waypoints": [r['system_name'] for r in route]
        }

        return {"content": [{"type": "text", "text": str(result)}]}
    except Exception as e:
        return {"error": f"Failed to calculate route: {str(e)}", "isError": True}


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
