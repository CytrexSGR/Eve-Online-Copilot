"""
Character MCP Tools
Character and corporation data access via EVE SSO.
"""

from typing import Dict, Any, List
from ..handlers import api_proxy
from character import character_api
from auth import eve_auth


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
    try:
        # Call auth module directly instead of HTTP request
        characters = eve_auth.get_authenticated_characters()
        return {"content": [{"type": "text", "text": str(characters)}]}
    except Exception as e:
        return {"error": f"Failed to get authenticated characters: {str(e)}", "isError": True}


def handle_get_character_wallet(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get character wallet."""
    try:
        character_id = args.get("character_id")
        # Call character_api directly instead of HTTP request
        result = character_api.get_wallet_balance(character_id)
        return {"content": [{"type": "text", "text": str(result)}]}
    except Exception as e:
        return {"error": f"Failed to get wallet: {str(e)}", "isError": True}


def handle_get_character_assets(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get character assets."""
    try:
        character_id = args.get("character_id")
        # Call character_api directly instead of HTTP request
        result = character_api.get_assets(character_id)
        return {"content": [{"type": "text", "text": str(result)}]}
    except Exception as e:
        return {"error": f"Failed to get assets: {str(e)}", "isError": True}


def handle_get_character_skills(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get character skills."""
    try:
        character_id = args.get("character_id")
        # Call character_api directly instead of HTTP request
        result = character_api.get_skills(character_id)
        return {"content": [{"type": "text", "text": str(result)}]}
    except Exception as e:
        return {"error": f"Failed to get skills: {str(e)}", "isError": True}


def handle_get_character_skillqueue(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get skill queue."""
    try:
        character_id = args.get("character_id")
        # Call character_api directly instead of HTTP request
        result = character_api.get_skill_queue(character_id)
        return {"content": [{"type": "text", "text": str(result)}]}
    except Exception as e:
        return {"error": f"Failed to get skill queue: {str(e)}", "isError": True}


def handle_get_character_orders(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get market orders."""
    try:
        character_id = args.get("character_id")
        # Call character_api directly instead of HTTP request
        result = character_api.get_market_orders(character_id)
        return {"content": [{"type": "text", "text": str(result)}]}
    except Exception as e:
        return {"error": f"Failed to get market orders: {str(e)}", "isError": True}


def handle_get_character_industry(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get industry jobs."""
    try:
        character_id = args.get("character_id")
        # Call character_api directly instead of HTTP request
        result = character_api.get_industry_jobs(character_id)
        return {"content": [{"type": "text", "text": str(result)}]}
    except Exception as e:
        return {"error": f"Failed to get industry jobs: {str(e)}", "isError": True}


def handle_get_character_blueprints(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get blueprints."""
    try:
        character_id = args.get("character_id")
        # Call character_api directly instead of HTTP request
        result = character_api.get_blueprints(character_id)
        return {"content": [{"type": "text", "text": str(result)}]}
    except Exception as e:
        return {"error": f"Failed to get blueprints: {str(e)}", "isError": True}


def handle_get_character_info(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get character info."""
    try:
        character_id = args.get("character_id")
        # Call character_api directly instead of HTTP request
        result = character_api.get_character_info(character_id)
        return {"content": [{"type": "text", "text": str(result)}]}
    except Exception as e:
        return {"error": f"Failed to get character info: {str(e)}", "isError": True}


def handle_get_character_portrait(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get character portrait."""
    try:
        character_id = args.get("character_id")
        # Return EVE image server URL directly
        portrait_url = f"https://images.evetech.net/characters/{character_id}/portrait?size=256"
        result = {
            "character_id": character_id,
            "portrait_url": portrait_url,
            "sizes_available": [32, 64, 128, 256, 512, 1024]
        }
        return {"content": [{"type": "text", "text": str(result)}]}
    except Exception as e:
        return {"error": f"Failed to get character portrait: {str(e)}", "isError": True}


def handle_get_corporation_wallet(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get corp wallet."""
    try:
        character_id = args.get("character_id")
        division = args.get("division", 1)
        # Call character_api directly instead of HTTP request
        result = character_api.get_corporation_wallets(character_id)

        # Filter to specific division if requested
        if isinstance(result, dict) and "wallets" in result:
            wallets = result.get("wallets", [])
            division_wallet = next((w for w in wallets if w.get("division") == division), None)
            if division_wallet:
                result = division_wallet

        return {"content": [{"type": "text", "text": str(result)}]}
    except Exception as e:
        return {"error": f"Failed to get corporation wallet: {str(e)}", "isError": True}


def handle_get_corporation_info(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get corp info."""
    try:
        character_id = args.get("character_id")
        # Get corporation ID from character first
        corp_id = character_api.get_corporation_id(character_id)
        if not corp_id:
            return {"error": "Failed to get corporation ID", "isError": True}

        # Call character_api directly instead of HTTP request
        result = character_api.get_corporation_info(corp_id)
        return {"content": [{"type": "text", "text": str(result)}]}
    except Exception as e:
        return {"error": f"Failed to get corporation info: {str(e)}", "isError": True}


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
