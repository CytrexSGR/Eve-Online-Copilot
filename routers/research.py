"""
Research API Router

Provides skill analysis endpoints for EVE Online manufacturing:
- Required skills for items
- Training recommendations
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
from services.research_service import ResearchService

router = APIRouter(prefix="/api/research", tags=["research"])

research_service = ResearchService()


@router.get("/skills-for-item/{type_id}")
async def get_skills_for_item(
    type_id: int,
    character_id: Optional[int] = Query(None, description="Optional character ID to compare skills")
) -> Dict[str, Any]:
    """
    Get skills required to manufacture an item

    Args:
        type_id: Item type ID to check
        character_id: Optional character to compare skills with

    Returns:
        Dict with blueprint_id, required_skills list, and optional character comparison

    Raises:
        HTTPException: 404 if no blueprint found for this item
    """
    result = research_service.get_skills_for_item(type_id, character_id)

    # Check if blueprint was found
    if 'error' in result and result['error'] == 'No blueprint found':
        raise HTTPException(
            status_code=404,
            detail=f"No blueprint found for item type_id {type_id}"
        )

    return result


@router.get("/recommendations/{character_id}")
async def get_training_recommendations(
    character_id: int
) -> List[Dict[str, Any]]:
    """
    Get skill training recommendations for a character

    Args:
        character_id: Character ID to get recommendations for

    Returns:
        List of recommended skills with priority and reasoning
    """
    return research_service.get_skill_recommendations(character_id)
