"""
Dashboard MCP Tools
Dashboard overview and portfolio analysis.
"""

from typing import Dict, Any, List
from ..handlers import api_proxy
from services.dashboard_service import DashboardService
from services.portfolio_service import PortfolioService

# Create service instances
dashboard_service = DashboardService()
portfolio_service = PortfolioService()


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
    try:
        category = args.get("category")

        # Call dashboard_service directly instead of HTTP request
        opportunities = dashboard_service.get_opportunities(limit=20)

        # Filter by category if specified
        if category:
            opportunities = [opp for opp in opportunities if opp.get("category") == category]

        return {"content": [{"type": "text", "text": str(opportunities)}]}
    except Exception as e:
        return {"error": f"Failed to get market opportunities: {str(e)}", "isError": True}


def handle_get_opportunities_by_category(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get opportunities by category."""
    try:
        category = args.get("category")

        # Call dashboard_service directly instead of HTTP request
        opportunities = dashboard_service.get_opportunities(limit=50)
        filtered = [opp for opp in opportunities if opp.get("category") == category]

        return {"content": [{"type": "text", "text": str(filtered)}]}
    except Exception as e:
        return {"error": f"Failed to get opportunities by category: {str(e)}", "isError": True}


def handle_get_characters_summary(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get characters summary."""
    try:
        from auth import eve_auth

        # Get authenticated character IDs
        characters = eve_auth.get_authenticated_characters()
        character_ids = [char["character_id"] for char in characters]

        # Call portfolio_service directly instead of HTTP request
        summaries = portfolio_service.get_character_summaries(character_ids)

        return {"content": [{"type": "text", "text": str(summaries)}]}
    except Exception as e:
        return {"error": f"Failed to get characters summary: {str(e)}", "isError": True}


def handle_get_portfolio_analysis(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get portfolio analysis."""
    try:
        from auth import eve_auth

        # Get authenticated character IDs
        characters = eve_auth.get_authenticated_characters()
        character_ids = [char["character_id"] for char in characters]

        # Call portfolio_service directly instead of HTTP request
        total_value = portfolio_service.get_total_portfolio_value(character_ids)
        summaries = portfolio_service.get_character_summaries(character_ids)

        result = {
            "total_portfolio_value": total_value,
            "characters": summaries
        }

        return {"content": [{"type": "text", "text": str(result)}]}
    except Exception as e:
        return {"error": f"Failed to get portfolio analysis: {str(e)}", "isError": True}


def handle_get_active_projects(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get active projects."""
    try:
        from auth import eve_auth
        from character import character_api

        # Get authenticated character IDs
        characters = eve_auth.get_authenticated_characters()

        # Collect active industry jobs from all characters
        projects = []
        for char in characters:
            char_id = char["character_id"]
            jobs = character_api.get_industry_jobs(char_id, include_completed=False)
            if isinstance(jobs, dict) and "jobs" in jobs:
                projects.extend(jobs["jobs"])

        result = {
            "total_projects": len(projects),
            "projects": projects
        }

        return {"content": [{"type": "text", "text": str(result)}]}
    except Exception as e:
        return {"error": f"Failed to get active projects: {str(e)}", "isError": True}


# Handler mapping
HANDLERS = {
    "get_market_opportunities": handle_get_market_opportunities,
    "get_opportunities_by_category": handle_get_opportunities_by_category,
    "get_characters_summary": handle_get_characters_summary,
    "get_portfolio_analysis": handle_get_portfolio_analysis,
    "get_active_projects": handle_get_active_projects
}
