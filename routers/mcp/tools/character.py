"""
Character MCP Tools
Character and corporation data access via EVE SSO.
"""

from typing import Dict, Any, List
from ..handlers import api_proxy


# Tool Definitions
TOOLS: List[Dict[str, Any]] = [
    {
        "name": "get_authenticated_characters",
        "description": "Get list of authenticated characters with tokens. Returns character IDs and names for characters logged in via EVE SSO.",
        "parameters": []
    },
    {
        "name": "get_character_wallet",
        "description": "Get character wallet balance. Returns current ISK balance.",
        "parameters": [
            {
                "name": "character_id",
                "type": "integer",
                "required": True,
                "description": "Character ID"
            }
        ]
    },
    {
        "name": "get_character_assets",
        "description": "Get character assets/inventory. Returns items owned by character with locations and quantities.",
        "parameters": [
            {
                "name": "character_id",
                "type": "integer",
                "required": True,
                "description": "Character ID"
            }
        ]
    },
    {
        "name": "get_character_skills",
        "description": "Get character skills and levels. Returns trained skills with levels and SP.",
        "parameters": [
            {
                "name": "character_id",
                "type": "integer",
                "required": True,
                "description": "Character ID"
            }
        ]
    },
    {
        "name": "get_character_skillqueue",
        "description": "Get character skill training queue. Returns currently training skills with completion times.",
        "parameters": [
            {
                "name": "character_id",
                "type": "integer",
                "required": True,
                "description": "Character ID"
            }
        ]
    },
    {
        "name": "get_character_orders",
        "description": "Get character active market orders. Returns buy/sell orders with prices and locations.",
        "parameters": [
            {
                "name": "character_id",
                "type": "integer",
                "required": True,
                "description": "Character ID"
            }
        ]
    },
    {
        "name": "get_character_industry",
        "description": "Get character industry jobs. Returns active manufacturing, research, and reaction jobs.",
        "parameters": [
            {
                "name": "character_id",
                "type": "integer",
                "required": True,
                "description": "Character ID"
            }
        ]
    },
    {
        "name": "get_character_blueprints",
        "description": "Get character owned blueprints. Returns blueprints with ME/TE levels and run counts.",
        "parameters": [
            {
                "name": "character_id",
                "type": "integer",
                "required": True,
                "description": "Character ID"
            }
        ]
    },
    {
        "name": "get_character_info",
        "description": "Get character public information. Returns character name, corporation, alliance, security status.",
        "parameters": [
            {
                "name": "character_id",
                "type": "integer",
                "required": True,
                "description": "Character ID"
            }
        ]
    },
    {
        "name": "get_character_portrait",
        "description": "Get character portrait image URL. Returns URL to character portrait image.",
        "parameters": [
            {
                "name": "character_id",
                "type": "integer",
                "required": True,
                "description": "Character ID"
            }
        ]
    },
    {
        "name": "get_corporation_wallet",
        "description": "Get corporation wallet balance for specific division. Requires corp roles.",
        "parameters": [
            {
                "name": "character_id",
                "type": "integer",
                "required": True,
                "description": "Character ID with corp access"
            },
            {
                "name": "division",
                "type": "integer",
                "required": False,
                "description": "Wallet division (1-7, default: 1)",
                "default": 1
            }
        ]
    },
    {
        "name": "get_corporation_info",
        "description": "Get corporation information. Returns corp details, member count, tax rate.",
        "parameters": [
            {
                "name": "character_id",
                "type": "integer",
                "required": True,
                "description": "Character ID in corporation"
            }
        ]
    }
]


# Tool Handlers
def handle_get_authenticated_characters(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get authenticated characters."""
    return api_proxy.get("/api/auth/characters")


def handle_get_character_wallet(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get character wallet."""
    character_id = args.get("character_id")
    return api_proxy.get(f"/api/character/{character_id}/wallet")


def handle_get_character_assets(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get character assets."""
    character_id = args.get("character_id")
    return api_proxy.get(f"/api/character/{character_id}/assets")


def handle_get_character_skills(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get character skills."""
    character_id = args.get("character_id")
    return api_proxy.get(f"/api/character/{character_id}/skills")


def handle_get_character_skillqueue(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get skill queue."""
    character_id = args.get("character_id")
    return api_proxy.get(f"/api/character/{character_id}/skillqueue")


def handle_get_character_orders(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get market orders."""
    character_id = args.get("character_id")
    return api_proxy.get(f"/api/character/{character_id}/orders")


def handle_get_character_industry(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get industry jobs."""
    character_id = args.get("character_id")
    return api_proxy.get(f"/api/character/{character_id}/industry")


def handle_get_character_blueprints(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get blueprints."""
    character_id = args.get("character_id")
    return api_proxy.get(f"/api/character/{character_id}/blueprints")


def handle_get_character_info(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get character info."""
    character_id = args.get("character_id")
    return api_proxy.get(f"/api/character/{character_id}/info")


def handle_get_character_portrait(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get character portrait."""
    character_id = args.get("character_id")
    return api_proxy.get(f"/api/character/{character_id}/portrait")


def handle_get_corporation_wallet(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get corp wallet."""
    character_id = args.get("character_id")
    division = args.get("division", 1)
    return api_proxy.get(f"/api/character/{character_id}/corporation/wallet", params={"division": division})


def handle_get_corporation_info(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get corp info."""
    character_id = args.get("character_id")
    return api_proxy.get(f"/api/character/{character_id}/corporation/info")


# Handler mapping
HANDLERS = {
    "get_authenticated_characters": handle_get_authenticated_characters,
    "get_character_wallet": handle_get_character_wallet,
    "get_character_assets": handle_get_character_assets,
    "get_character_skills": handle_get_character_skills,
    "get_character_skillqueue": handle_get_character_skillqueue,
    "get_character_orders": handle_get_character_orders,
    "get_character_industry": handle_get_character_industry,
    "get_character_blueprints": handle_get_character_blueprints,
    "get_character_info": handle_get_character_info,
    "get_character_portrait": handle_get_character_portrait,
    "get_corporation_wallet": handle_get_corporation_wallet,
    "get_corporation_info": handle_get_corporation_info
}
