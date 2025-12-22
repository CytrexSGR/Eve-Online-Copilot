"""
Dashboard MCP Tools
Dashboard overview and portfolio analysis.
"""

from typing import Dict, Any, List
from ..handlers import api_proxy


# Tool Definitions
TOOLS: List[Dict[str, Any]] = [
    {
        "name": "get_market_opportunities",
        "description": "Get market opportunities overview from dashboard. Returns profitable manufacturing opportunities with ROI and profit margins.",
        "parameters": [
            {
                "name": "category",
                "type": "string",
                "required": False,
                "description": "Filter by category (ships, modules, etc.)"
            }
        ]
    },
    {
        "name": "get_opportunities_by_category",
        "description": "Get opportunities filtered by specific category. Returns category-specific manufacturing opportunities.",
        "parameters": [
            {
                "name": "category",
                "type": "string",
                "required": True,
                "description": "Category name (e.g., 'Ship', 'Module', 'Ammunition')"
            }
        ]
    },
    {
        "name": "get_characters_summary",
        "description": "Get summary of all authenticated characters. Returns wallet balances, active jobs, and key metrics for all characters.",
        "parameters": []
    },
    {
        "name": "get_portfolio_analysis",
        "description": "Get portfolio analysis across all characters. Returns combined assets, wallets, market orders, and net worth.",
        "parameters": []
    },
    {
        "name": "get_active_projects",
        "description": "Get active production projects across all characters. Returns ongoing manufacturing, research, and industry jobs.",
        "parameters": []
    }
]


# Tool Handlers
def handle_get_market_opportunities(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get market opportunities."""
    category = args.get("category")
    params = {"category": category} if category else None
    return api_proxy.get("/api/dashboard/opportunities", params=params)


def handle_get_opportunities_by_category(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get opportunities by category."""
    category = args.get("category")
    return api_proxy.get(f"/api/dashboard/opportunities/{category}")


def handle_get_characters_summary(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get characters summary."""
    return api_proxy.get("/api/dashboard/characters/summary")


def handle_get_portfolio_analysis(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get portfolio analysis."""
    return api_proxy.get("/api/dashboard/characters/portfolio")


def handle_get_active_projects(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get active projects."""
    return api_proxy.get("/api/dashboard/projects")


# Handler mapping
HANDLERS = {
    "get_market_opportunities": handle_get_market_opportunities,
    "get_opportunities_by_category": handle_get_opportunities_by_category,
    "get_characters_summary": handle_get_characters_summary,
    "get_portfolio_analysis": handle_get_portfolio_analysis,
    "get_active_projects": handle_get_active_projects
}
