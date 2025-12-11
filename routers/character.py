"""
Character router - Character and Corporation data endpoints.
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional

from src.core.config import get_settings
from src.core.database import DatabasePool
from src.core.exceptions import NotFoundError, ExternalAPIError, AuthenticationError, EVECopilotError
from src.services.character.service import CharacterService
from src.services.auth.service import AuthService
from src.services.auth.repository import AuthRepository
from src.integrations.esi.client import ESIClient

router = APIRouter(prefix="/api/character", tags=["Character"])


def get_character_service() -> CharacterService:
    """Dependency injection for CharacterService."""
    settings = get_settings()
    db = DatabasePool(settings)
    esi_client = ESIClient()

    # Initialize AuthService for token management
    auth_repository = AuthRepository()
    auth_service = AuthService(auth_repository, esi_client, settings)

    return CharacterService(esi_client, auth_service, db)


@router.get("/{character_id}/wallet")
async def character_wallet(
    character_id: int,
    service: CharacterService = Depends(get_character_service)
):
    """Get character's wallet balance"""
    try:
        result = service.get_wallet_balance(character_id)
        return result.model_dump()
    except AuthenticationError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ExternalAPIError as e:
        raise HTTPException(status_code=502, detail=f"ESI API error: {e}")
    except EVECopilotError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{character_id}/assets")
async def character_assets(
    character_id: int,
    location_id: Optional[int] = Query(None),
    service: CharacterService = Depends(get_character_service)
):
    """Get character's assets"""
    try:
        result = service.get_assets(character_id, location_id)
        return result.model_dump()
    except AuthenticationError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ExternalAPIError as e:
        raise HTTPException(status_code=502, detail=f"ESI API error: {e}")
    except EVECopilotError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{character_id}/skills")
async def character_skills(
    character_id: int,
    service: CharacterService = Depends(get_character_service)
):
    """Get character's skills"""
    try:
        result = service.get_skills(character_id)
        return result.model_dump()
    except AuthenticationError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ExternalAPIError as e:
        raise HTTPException(status_code=502, detail=f"ESI API error: {e}")
    except EVECopilotError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{character_id}/skillqueue")
async def character_skillqueue(
    character_id: int,
    service: CharacterService = Depends(get_character_service)
):
    """Get character's skill queue"""
    try:
        result = service.get_skill_queue(character_id)
        return result.model_dump()
    except AuthenticationError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ExternalAPIError as e:
        raise HTTPException(status_code=502, detail=f"ESI API error: {e}")
    except EVECopilotError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{character_id}/orders")
async def character_orders(
    character_id: int,
    service: CharacterService = Depends(get_character_service)
):
    """Get character's active market orders"""
    try:
        result = service.get_market_orders(character_id)
        return result.model_dump()
    except AuthenticationError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ExternalAPIError as e:
        raise HTTPException(status_code=502, detail=f"ESI API error: {e}")
    except EVECopilotError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{character_id}/industry")
async def character_industry(
    character_id: int,
    include_completed: bool = Query(False),
    service: CharacterService = Depends(get_character_service)
):
    """Get character's industry jobs"""
    try:
        result = service.get_industry_jobs(character_id, include_completed)
        return result.model_dump()
    except AuthenticationError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ExternalAPIError as e:
        raise HTTPException(status_code=502, detail=f"ESI API error: {e}")
    except EVECopilotError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{character_id}/blueprints")
async def character_blueprints(
    character_id: int,
    service: CharacterService = Depends(get_character_service)
):
    """Get character's blueprints"""
    try:
        result = service.get_blueprints(character_id)
        return result.model_dump()
    except AuthenticationError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ExternalAPIError as e:
        raise HTTPException(status_code=502, detail=f"ESI API error: {e}")
    except EVECopilotError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{character_id}/info")
async def character_info(
    character_id: int,
    service: CharacterService = Depends(get_character_service)
):
    """Get public character information"""
    try:
        result = service.get_character_info(character_id)
        return result.model_dump()
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ExternalAPIError as e:
        raise HTTPException(status_code=502, detail=f"ESI API error: {e}")
    except EVECopilotError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{character_id}/corporation/wallet")
async def corporation_wallet(
    character_id: int,
    service: CharacterService = Depends(get_character_service)
):
    """Get corporation wallet balances"""
    try:
        result = service.get_corporation_wallets(character_id)
        return result.model_dump()
    except AuthenticationError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ExternalAPIError as e:
        raise HTTPException(status_code=502, detail=f"ESI API error: {e}")
    except EVECopilotError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{character_id}/corporation/info")
async def corporation_info(
    character_id: int,
    service: CharacterService = Depends(get_character_service)
):
    """Get corporation info for a character"""
    try:
        corp_id = service.get_corporation_id(character_id)
        if not corp_id:
            raise HTTPException(status_code=404, detail="Corporation not found")
        result = service.get_corporation_info(corp_id)
        return result.model_dump()
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ExternalAPIError as e:
        raise HTTPException(status_code=502, detail=f"ESI API error: {e}")
    except EVECopilotError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{character_id}/corporation/journal/{division}")
async def corporation_journal(
    character_id: int,
    division: int = 1,
    service: CharacterService = Depends(get_character_service)
):
    """Get corporation wallet journal for a specific division (1-7)"""
    try:
        result = service.get_corporation_wallet_journal(character_id, division)
        return result
    except AuthenticationError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ExternalAPIError as e:
        raise HTTPException(status_code=502, detail=f"ESI API error: {e}")
    except EVECopilotError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{character_id}/portrait")
async def character_portrait(
    character_id: int,
    service: CharacterService = Depends(get_character_service)
):
    """
    Get character portrait URL (px256x256) with 24h caching.

    This endpoint proxies ESI's character portrait endpoint and caches
    results for 24 hours to reduce API calls. If the character is not found
    or an error occurs, a default avatar URL is returned.

    Args:
        character_id: EVE Online character ID

    Returns:
        dict: {"url": "https://images.evetech.net/characters/{id}/portrait?size=256"}
    """
    try:
        result = service.get_character_portrait(character_id)
        return result
    except ExternalAPIError as e:
        # Return default avatar on any ESI error
        return {"url": "https://images.evetech.net/characters/1/portrait?size=256"}
    except EVECopilotError as e:
        # Return default avatar on any error
        return {"url": "https://images.evetech.net/characters/1/portrait?size=256"}
