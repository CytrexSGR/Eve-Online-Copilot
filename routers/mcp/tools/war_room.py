"""
War Room MCP Tools
Combat intelligence, sovereignty, faction warfare, and market demand analysis.
"""

from typing import Dict, Any, List
from ..handlers import api_proxy
from killmail_service import killmail_service
from sovereignty_service import sovereignty_service
from fw_service import fw_service
from war_analyzer import war_analyzer
from route_service import route_service


# Tool Definitions
TOOLS: List[Dict[str, Any]] = [
    {
        "name": "get_war_losses",
        "description": "Get combat ship/item losses for a region over recent days. Returns top destroyed ships with quantities and ISK value. Use region_id 10000002 for Jita/The Forge.",
        "parameters": [
            {
                "name": "region_id",
                "type": "integer",
                "required": True,
                "description": "Region ID (10000002=The Forge, 10000043=Domain, etc.)"
            },
            {
                "name": "days",
                "type": "integer",
                "required": False,
                "description": "Days to look back (1-30, default: 7)",
                "default": 7
            },
            {
                "name": "type",
                "type": "string",
                "required": False,
                "description": "Filter by type: 'ships', 'items', or 'all'",
                "default": "all",
                "enum": ["all", "ships", "items"]
            }
        ]
    },
    {
        "name": "get_war_demand",
        "description": "Analyze combat demand and identify market gaps where ship/module losses exceed available market supply. Shows production opportunities from combat losses.",
        "parameters": [
            {
                "name": "region_id",
                "type": "integer",
                "required": True,
                "description": "Region ID for demand analysis"
            },
            {
                "name": "days",
                "type": "integer",
                "required": False,
                "description": "Days for analysis (default: 7)",
                "default": 7
            },
            {
                "name": "min_gap",
                "type": "integer",
                "required": False,
                "description": "Minimum gap threshold (default: 10)",
                "default": 10
            }
        ]
    },
    {
        "name": "get_war_heatmap",
        "description": "Get galaxy-wide combat heatmap showing killmail activity by region. Returns regions sorted by combat intensity for identifying hotspots.",
        "parameters": [
            {
                "name": "days",
                "type": "integer",
                "required": False,
                "description": "Days for heatmap (default: 7)",
                "default": 7
            },
            {
                "name": "min_kills",
                "type": "integer",
                "required": False,
                "description": "Minimum kills to include region (default: 5)",
                "default": 5
            }
        ]
    },
    {
        "name": "get_war_campaigns",
        "description": "Get active sovereignty campaigns and timers. Returns upcoming sov battles with structure types, attackers/defenders, and timer information.",
        "parameters": [
            {
                "name": "region_id",
                "type": "integer",
                "required": False,
                "description": "Filter by region (default: all regions)"
            }
        ]
    },
    {
        "name": "update_war_campaigns",
        "description": "Manually trigger update of sovereignty campaign data from ESI. Use when you need fresh sov timer information.",
        "parameters": []
    },
    {
        "name": "get_war_fw_hotspots",
        "description": "Get Faction Warfare hotspots showing active FW systems with recent activity. Returns systems by faction with occupation status.",
        "parameters": [
            {
                "name": "faction",
                "type": "string",
                "required": False,
                "description": "Filter by faction (caldari, gallente, amarr, minmatar)",
                "enum": ["caldari", "gallente", "amarr", "minmatar"]
            }
        ]
    },
    {
        "name": "get_war_fw_vulnerable",
        "description": "Get vulnerable Faction Warfare systems close to flipping. Returns systems with high contested percentage that may flip soon.",
        "parameters": [
            {
                "name": "min_contested",
                "type": "integer",
                "required": False,
                "description": "Minimum contested percentage (default: 50)",
                "default": 50
            }
        ]
    },
    {
        "name": "update_war_fw",
        "description": "Manually trigger update of Faction Warfare status from ESI. Use for fresh FW system information.",
        "parameters": []
    },
    {
        "name": "get_war_doctrines",
        "description": "Detect fleet doctrines from combat loss patterns. Analyzes recent losses to identify common fleet compositions and ship combinations.",
        "parameters": [
            {
                "name": "region_id",
                "type": "integer",
                "required": True,
                "description": "Region ID for doctrine detection"
            },
            {
                "name": "days",
                "type": "integer",
                "required": False,
                "description": "Days to analyze (default: 7)",
                "default": 7
            },
            {
                "name": "min_fleet_size",
                "type": "integer",
                "required": False,
                "description": "Minimum fleet size to detect (default: 10)",
                "default": 10
            }
        ]
    },
    {
        "name": "get_war_conflicts",
        "description": "Get active alliance conflicts and wars. Returns ongoing wars between alliances with combat statistics.",
        "parameters": [
            {
                "name": "alliance_id",
                "type": "integer",
                "required": False,
                "description": "Filter by specific alliance"
            }
        ]
    },
    {
        "name": "get_system_danger",
        "description": "Get danger score for a solar system based on recent combat activity. Returns 0-100 danger rating with recent kill statistics.",
        "parameters": [
            {
                "name": "system_id",
                "type": "integer",
                "required": True,
                "description": "Solar system ID"
            },
            {
                "name": "hours",
                "type": "integer",
                "required": False,
                "description": "Hours to analyze (default: 24)",
                "default": 24
            }
        ]
    },
    {
        "name": "get_war_summary",
        "description": "Get regional combat summary with overview statistics. Returns total kills, ISK destroyed, top ships, and active combatants for region.",
        "parameters": [
            {
                "name": "region_id",
                "type": "integer",
                "required": True,
                "description": "Region ID for summary"
            },
            {
                "name": "days",
                "type": "integer",
                "required": False,
                "description": "Days for summary (default: 7)",
                "default": 7
            }
        ]
    },
    {
        "name": "get_war_top_ships",
        "description": "Get most destroyed ships galaxy-wide. Returns top ships by kill count across all regions for identifying popular combat ships.",
        "parameters": [
            {
                "name": "days",
                "type": "integer",
                "required": False,
                "description": "Days to analyze (default: 7)",
                "default": 7
            },
            {
                "name": "limit",
                "type": "integer",
                "required": False,
                "description": "Number of top ships to return (default: 50)",
                "default": 50
            }
        ]
    },
    {
        "name": "get_safe_route",
        "description": "Calculate route between systems with danger scores. Returns route with per-system danger ratings based on recent combat activity.",
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
                "name": "avoid_dangerous",
                "type": "boolean",
                "required": False,
                "description": "Avoid high-danger systems (default: false)",
                "default": False
            }
        ]
    },
    {
        "name": "get_item_combat_stats",
        "description": "Get combat statistics for an item showing usage in PvP. Returns kill/loss statistics with fit popularity and combat effectiveness data.",
        "parameters": [
            {
                "name": "type_id",
                "type": "integer",
                "required": True,
                "description": "Item type ID"
            },
            {
                "name": "days",
                "type": "integer",
                "required": False,
                "description": "Days to analyze (default: 30)",
                "default": 30
            }
        ]
    },
    {
        "name": "get_war_alerts",
        "description": "Get war room alerts for significant combat events, sov timers, and high-value kills. Returns recent notable events requiring attention.",
        "parameters": [
            {
                "name": "region_id",
                "type": "integer",
                "required": False,
                "description": "Filter by region (default: all)"
            },
            {
                "name": "hours",
                "type": "integer",
                "required": False,
                "description": "Hours to look back (default: 6)",
                "default": 6
            }
        ]
    }
]


# Tool Handlers
def handle_get_war_losses(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get war losses for region."""
    region_id = args.get("region_id")
    params = {
        "days": args.get("days", 7),
        "type": args.get("type", "all")
    }
    return api_proxy.get(f"/api/war/losses/{region_id}", params=params)


def handle_get_war_demand(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get war demand analysis."""
    region_id = args.get("region_id")
    params = {
        "days": args.get("days", 7),
        "min_gap": args.get("min_gap", 10)
    }
    return api_proxy.get(f"/api/war/demand/{region_id}", params=params)


def handle_get_war_heatmap(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get combat heatmap."""
    params = {
        "days": args.get("days", 7),
        "min_kills": args.get("min_kills", 5)
    }
    return api_proxy.get("/api/war/heatmap", params=params)


def handle_get_war_campaigns(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get sov campaigns."""
    region_id = args.get("region_id")
    params = {"region_id": region_id} if region_id else None
    return api_proxy.get("/api/war/campaigns", params=params)


def handle_update_war_campaigns(args: Dict[str, Any]) -> Dict[str, Any]:
    """Update sov campaigns."""
    return api_proxy.get("/api/war/campaigns/update")


def handle_get_war_fw_hotspots(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get FW hotspots."""
    faction = args.get("faction")
    params = {"faction": faction} if faction else None
    return api_proxy.get("/api/war/fw/hotspots", params=params)


def handle_get_war_fw_vulnerable(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get vulnerable FW systems."""
    min_contested = args.get("min_contested", 50)
    return api_proxy.get("/api/war/fw/vulnerable", params={"min_contested": min_contested})


def handle_update_war_fw(args: Dict[str, Any]) -> Dict[str, Any]:
    """Update FW status."""
    return api_proxy.get("/api/war/fw/update")


def handle_get_war_doctrines(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get doctrine detection."""
    region_id = args.get("region_id")
    params = {
        "days": args.get("days", 7),
        "min_fleet_size": args.get("min_fleet_size", 10)
    }
    return api_proxy.get(f"/api/war/doctrines/{region_id}", params=params)


def handle_get_war_conflicts(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get alliance conflicts."""
    alliance_id = args.get("alliance_id")
    params = {"alliance_id": alliance_id} if alliance_id else None
    return api_proxy.get("/api/war/conflicts", params=params)


def handle_get_system_danger(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get system danger score."""
    system_id = args.get("system_id")
    hours = args.get("hours", 24)
    return api_proxy.get(f"/api/war/system/{system_id}/danger", params={"hours": hours})


def handle_get_war_summary(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get regional combat summary."""
    region_id = args.get("region_id")
    days = args.get("days", 7)
    return api_proxy.get("/api/war/summary", params={"region_id": region_id, "days": days})


def handle_get_war_top_ships(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get top destroyed ships."""
    params = {
        "days": args.get("days", 7),
        "limit": args.get("limit", 50)
    }
    return api_proxy.get("/api/war/top-ships", params=params)


def handle_get_safe_route(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get safe route with danger scores."""
    from_system = args.get("from_system")
    to_system = args.get("to_system")
    avoid_dangerous = args.get("avoid_dangerous", False)
    return api_proxy.get(
        f"/api/war/route/safe/{from_system}/{to_system}",
        params={"avoid_dangerous": avoid_dangerous}
    )


def handle_get_item_combat_stats(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get item combat statistics."""
    type_id = args.get("type_id")
    days = args.get("days", 30)
    return api_proxy.get(f"/api/war/item/{type_id}/stats", params={"days": days})


def handle_get_war_alerts(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get war room alerts."""
    params = {}
    if args.get("region_id"):
        params["region_id"] = args.get("region_id")
    if args.get("hours"):
        params["hours"] = args.get("hours")
    else:
        params["hours"] = 6
    return api_proxy.get("/api/war/alerts", params=params if params else None)


# Handler mapping
HANDLERS = {
    "get_war_losses": handle_get_war_losses,
    "get_war_demand": handle_get_war_demand,
    "get_war_heatmap": handle_get_war_heatmap,
    "get_war_campaigns": handle_get_war_campaigns,
    "update_war_campaigns": handle_update_war_campaigns,
    "get_war_fw_hotspots": handle_get_war_fw_hotspots,
    "get_war_fw_vulnerable": handle_get_war_fw_vulnerable,
    "update_war_fw": handle_update_war_fw,
    "get_war_doctrines": handle_get_war_doctrines,
    "get_war_conflicts": handle_get_war_conflicts,
    "get_system_danger": handle_get_system_danger,
    "get_war_summary": handle_get_war_summary,
    "get_war_top_ships": handle_get_war_top_ships,
    "get_safe_route": handle_get_safe_route,
    "get_item_combat_stats": handle_get_item_combat_stats,
    "get_war_alerts": handle_get_war_alerts
}
