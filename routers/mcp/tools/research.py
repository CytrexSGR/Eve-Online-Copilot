"""
Research MCP Tools
Skill requirements and recommendations.
"""

from typing import Dict, Any, List
from ..handlers import api_proxy


# Tool Definitions
TOOLS: List[Dict[str, Any]] = [
    {
        "name": "get_skills_for_item",
        "description": "Get required skills for using an item. Returns skill prerequisites with levels needed.",
        "parameters": [
            {
                "name": "type_id",
                "type": "integer",
                "required": True,
                "description": "Item type ID"
            }
        ]
    },
    {
        "name": "get_skill_recommendations",
        "description": "Get skill training recommendations for character. Suggests useful skills based on character's current skills and common gameplay paths.",
        "parameters": [
            {
                "name": "character_id",
                "type": "integer",
                "required": True,
                "description": "Character ID"
            },
            {
                "name": "focus",
                "type": "string",
                "required": False,
                "description": "Focus area (combat, industry, trade, exploration)",
                "enum": ["combat", "industry", "trade", "exploration"]
            }
        ]
    }
]


# Tool Handlers
def handle_get_skills_for_item(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get skills for item."""
    type_id = args.get("type_id")
    return api_proxy.get(f"/api/research/skills-for-item/{type_id}")


def handle_get_skill_recommendations(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get skill recommendations."""
    character_id = args.get("character_id")
    focus = args.get("focus")
    params = {"focus": focus} if focus else None
    return api_proxy.get(f"/api/research/recommendations/{character_id}", params=params)


# Handler mapping
HANDLERS = {
    "get_skills_for_item": handle_get_skills_for_item,
    "get_skill_recommendations": handle_get_skill_recommendations
}
