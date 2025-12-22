"""
Hunter MCP Tools
Market opportunity hunting and scanning.
"""

from typing import Dict, Any, List
from ..handlers import api_proxy


# Tool Definitions
TOOLS: List[Dict[str, Any]] = [
    {
        "name": "get_hunter_categories",
        "description": "Get available item categories for market hunting. Returns categories that can be scanned for opportunities.",
        "parameters": []
    },
    {
        "name": "get_market_tree",
        "description": "Get market group hierarchy tree. Returns full market category structure for filtering.",
        "parameters": []
    },
    {
        "name": "scan_market_opportunities",
        "description": "Scan for profitable manufacturing opportunities. Returns items with high profit margins and ROI.",
        "parameters": [
            {
                "name": "category",
                "type": "string",
                "required": False,
                "description": "Filter by category"
            },
            {
                "name": "min_roi",
                "type": "number",
                "required": False,
                "description": "Minimum ROI percentage (default: 15)",
                "default": 15
            },
            {
                "name": "min_profit",
                "type": "integer",
                "required": False,
                "description": "Minimum profit in ISK (default: 500000)",
                "default": 500000
            }
        ]
    },
    {
        "name": "get_precalculated_opportunities",
        "description": "Get pre-calculated market opportunities from cron job. Returns cached profitable manufacturing items updated every 5 minutes.",
        "parameters": [
            {
                "name": "limit",
                "type": "integer",
                "required": False,
                "description": "Number of results (default: 20)",
                "default": 20
            }
        ]
    }
]


# Tool Handlers
def handle_get_hunter_categories(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get hunter categories."""
    return api_proxy.get("/api/hunter/categories")


def handle_get_market_tree(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get market tree."""
    return api_proxy.get("/api/hunter/market-tree")


def handle_scan_market_opportunities(args: Dict[str, Any]) -> Dict[str, Any]:
    """Scan market opportunities."""
    params = {
        "min_roi": args.get("min_roi", 15),
        "min_profit": args.get("min_profit", 500000)
    }
    if args.get("category"):
        params["category"] = args.get("category")
    return api_proxy.get("/api/hunter/scan", params=params)


def handle_get_precalculated_opportunities(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get precalculated opportunities."""
    limit = args.get("limit", 20)
    return api_proxy.get("/api/hunter/opportunities", params={"limit": limit})


# Handler mapping
HANDLERS = {
    "get_hunter_categories": handle_get_hunter_categories,
    "get_market_tree": handle_get_market_tree,
    "scan_market_opportunities": handle_scan_market_opportunities,
    "get_precalculated_opportunities": handle_get_precalculated_opportunities
}
