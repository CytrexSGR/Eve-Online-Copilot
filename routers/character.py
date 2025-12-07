"""
Character router - Character and Corporation data endpoints.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from character import character_api

router = APIRouter(prefix="/api/character", tags=["Character"])


@router.get("/{character_id}/wallet")
async def character_wallet(character_id: int):
    """Get character's wallet balance"""
    result = character_api.get_wallet_balance(character_id)
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/{character_id}/assets")
async def character_assets(
    character_id: int,
    location_id: Optional[int] = Query(None)
):
    """Get character's assets"""
    result = character_api.get_assets(character_id, location_id)
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/{character_id}/skills")
async def character_skills(character_id: int):
    """Get character's skills"""
    result = character_api.get_skills(character_id)
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/{character_id}/skillqueue")
async def character_skillqueue(character_id: int):
    """Get character's skill queue"""
    result = character_api.get_skill_queue(character_id)
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/{character_id}/orders")
async def character_orders(character_id: int):
    """Get character's active market orders"""
    result = character_api.get_market_orders(character_id)
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/{character_id}/industry")
async def character_industry(character_id: int, include_completed: bool = Query(False)):
    """Get character's industry jobs"""
    result = character_api.get_industry_jobs(character_id, include_completed)
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/{character_id}/blueprints")
async def character_blueprints(character_id: int):
    """Get character's blueprints"""
    result = character_api.get_blueprints(character_id)
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/{character_id}/info")
async def character_info(character_id: int):
    """Get public character information"""
    result = character_api.get_character_info(character_id)
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/{character_id}/corporation/wallet")
async def corporation_wallet(character_id: int):
    """Get corporation wallet balances"""
    result = character_api.get_corporation_wallets(character_id)
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/{character_id}/corporation/info")
async def corporation_info(character_id: int):
    """Get corporation info for a character"""
    corp_id = character_api.get_corporation_id(character_id)
    if not corp_id:
        raise HTTPException(status_code=404, detail="Corporation not found")
    result = character_api.get_corporation_info(corp_id)
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/{character_id}/corporation/journal/{division}")
async def corporation_journal(character_id: int, division: int = 1):
    """Get corporation wallet journal for a specific division (1-7)"""
    result = character_api.get_corporation_wallet_journal(character_id, division)
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result
