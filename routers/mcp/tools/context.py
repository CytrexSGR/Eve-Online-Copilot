"""
Context & Utility MCP Tools
Provides system context and reference information.
"""

from typing import Dict, Any, List
from ..handlers import api_proxy
from config import REGIONS
from src.auth import eve_auth


# Tool Definitions
TOOLS: List[Dict[str, Any]] = [
    {
        "name": "get_regions",
        "description": "Get list of all EVE Online regions with their IDs. Useful for region-based queries. Returns region names and IDs for all known space regions.",
        "parameters": [
            {
                "name": "include_wh",
                "type": "boolean",
                "required": False,
                "description": "Include wormhole regions (default: false)",
                "default": False
            }
        ]
    },
    {
        "name": "eve_copilot_context",
        "description": "Get EVE Co-Pilot system context and capabilities. Returns information about available features, authenticated characters, system status, and usage tips. Use this when user asks 'what can you do' or needs system overview.",
        "parameters": []
    }
]


# Tool Handlers
def handle_get_regions(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get all EVE Online regions."""
    try:
        include_wh = args.get("include_wh", False)

        # Use REGIONS constant directly instead of HTTP request
        result = dict(REGIONS)

        return {"content": [{"type": "text", "text": str(result)}]}
    except Exception as e:
        return {"error": f"Failed to get regions: {str(e)}", "isError": True}


def handle_eve_copilot_context(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get EVE Co-Pilot system context."""
    try:
        # Call auth module directly instead of HTTP request
        characters = eve_auth.get_authenticated_characters()

        context = {
            "system": "EVE Co-Pilot",
            "version": "2.0.0",
            "capabilities": [
                "Market Analysis & Arbitrage Finding",
                "Production Planning & Cost Calculation",
                "Shopping List Management with Regional Comparison",
                "War Room - Combat Intelligence & Demand Analysis",
                "Character & Corporation Management",
                "Research & Skill Planning",
                "Route Calculation & Navigation",
                "Mining Location Finder",
                "Bookmark Management"
            ],
            "mcp_tools": 97,
            "authenticated_characters": characters,
            "features": {
                "dashboard": "Market opportunities, portfolio analysis, active projects",
                "production": "Full production chains, economics analysis, workflow management",
                "war_room": "Combat losses, doctrines, sovereignty, faction warfare",
                "shopping": "Wizard-guided shopping, regional comparison, cargo calculator",
                "market": "Enhanced arbitrage with routing, multi-region comparison"
            },
            "tips": [
                "Use get_regions to see available regions for market queries",
                "War Room tools require region_id (e.g., 10000002 for Jita/The Forge)",
                "Shopping wizard guides you through creating optimized shopping lists",
                "Production chains show full material breakdown from raw materials"
            ]
        }

        return {"content": [{"type": "text", "text": str(context)}]}

    except Exception as e:
        return {"error": f"Failed to get context: {str(e)}", "isError": True}


# Handler mapping
HANDLERS = {
    "get_regions": handle_get_regions,
    "eve_copilot_context": handle_eve_copilot_context
}
