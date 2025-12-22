"""
Mining MCP Tools
Mining location finder and ore information.
"""

from typing import Dict, Any, List
from ..handlers import api_proxy


# Tool Definitions
TOOLS: List[Dict[str, Any]] = [
    {
        "name": "find_mineral_locations",
        "description": "Find where to mine specific minerals. Returns ore types and locations for mineral sourcing.",
        "parameters": [
            {
                "name": "mineral_name",
                "type": "string",
                "required": True,
                "description": "Mineral name (e.g., 'Tritanium', 'Pyerite', 'Mexallon')"
            },
            {
                "name": "from_system",
                "type": "string",
                "required": False,
                "description": "Starting system for distance calculation"
            }
        ]
    },
    {
        "name": "get_system_mining_info",
        "description": "Get mining information for solar system. Returns available asteroid belts and ore types.",
        "parameters": [
            {
                "name": "system_id",
                "type": "integer",
                "required": True,
                "description": "Solar system ID"
            }
        ]
    },
    {
        "name": "get_ore_composition",
        "description": "Get mineral composition of ore types. Returns which minerals each ore refines into with yields.",
        "parameters": [
            {
                "name": "ore_name",
                "type": "string",
                "required": False,
                "description": "Specific ore name (default: all ores)"
            }
        ]
    }
]


# Tool Handlers
def handle_find_mineral_locations(args: Dict[str, Any]) -> Dict[str, Any]:
    """Find mineral locations."""
    mineral_name = args.get("mineral_name")
    from_system = args.get("from_system")
    params = {"mineral": mineral_name}
    if from_system:
        params["from_system"] = from_system
    return api_proxy.get("/api/mining/find-mineral", params=params)


def handle_get_system_mining_info(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get system mining info."""
    system_id = args.get("system_id")
    # Use route planner with system as target
    return api_proxy.get("/api/mining/route-planner", params={"target_system": system_id})


def handle_get_ore_composition(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get ore composition."""
    ore_name = args.get("ore_name")
    params = {"ore": ore_name} if ore_name else None
    return api_proxy.get("/api/mining/ore-info", params=params)


# Handler mapping
HANDLERS = {
    "find_mineral_locations": handle_find_mineral_locations,
    "get_system_mining_info": handle_get_system_mining_info,
    "get_ore_composition": handle_get_ore_composition
}
