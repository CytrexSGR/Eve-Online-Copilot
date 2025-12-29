"""
Research MCP Tools
Skill requirements and recommendations.
"""

from typing import Dict, Any, List
from ..handlers import api_proxy
from services.research_service import ResearchService

# Create service instance
research_service = ResearchService()


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
    try:
        type_id = args.get("type_id")

        # Call research_service directly instead of HTTP request
        result = research_service.get_required_skills(type_id)

        return {"content": [{"type": "text", "text": str(result)}]}
    except Exception as e:
        return {"error": f"Failed to get skills for item: {str(e)}", "isError": True}


def handle_get_skill_recommendations(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get skill recommendations."""
    try:
        character_id = args.get("character_id")
        focus = args.get("focus")

        # Call research_service directly instead of HTTP request
        result = research_service.get_recommendations(character_id, focus=focus)

        return {"content": [{"type": "text", "text": str(result)}]}
    except Exception as e:
        return {"error": f"Failed to get skill recommendations: {str(e)}", "isError": True}


# Handler mapping
HANDLERS = {
    "get_skills_for_item": handle_get_skills_for_item,
    "get_skill_recommendations": handle_get_skill_recommendations
}
