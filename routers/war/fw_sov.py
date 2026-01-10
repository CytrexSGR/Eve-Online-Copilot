"""
Faction Warfare and Sovereignty Endpoints Router.

Provides endpoints for FW hotspots and sovereignty campaigns.
"""

from fastapi import APIRouter, HTTPException, Query, Depends

from src.services.warroom.sovereignty import SovereigntyService
from src.services.warroom.fw import FactionWarfareService
from src.core.exceptions import EVECopilotError, ESIError
from .dependencies import get_sovereignty_service, get_faction_warfare_service

router = APIRouter()


# ============================================================
# Sovereignty Campaign Endpoints
# ============================================================

@router.get("/campaigns")
async def get_campaigns(
    hours: int = Query(48, ge=1, le=168),
    service: SovereigntyService = Depends(get_sovereignty_service)
):
    """Get upcoming sovereignty battles using refactored service"""
    try:
        campaigns = service.get_upcoming_battles(hours)
        return {"campaigns": [c.model_dump() for c in campaigns]}
    except ESIError as e:
        raise HTTPException(status_code=502, detail=f"ESI API error: {str(e)}")
    except EVECopilotError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/campaigns/update")
async def update_campaigns(
    service: SovereigntyService = Depends(get_sovereignty_service)
):
    """Manually trigger campaign update from ESI using refactored service"""
    try:
        count = service.update_campaigns()
        return {
            "status": "success",
            "campaigns_updated": count,
            "message": f"Successfully updated {count} campaigns"
        }
    except ESIError as e:
        raise HTTPException(status_code=502, detail=f"ESI API error: {str(e)}")
    except EVECopilotError as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Faction Warfare Endpoints
# ============================================================

@router.get("/fw/hotspots")
async def get_fw_hotspots(
    min_contested: float = Query(50.0, ge=0, le=100),
    service: FactionWarfareService = Depends(get_faction_warfare_service)
):
    """Get Faction Warfare hotspots using refactored service"""
    try:
        hotspots = service.get_fw_hotspots(min_contested)
        return {"hotspots": [h.model_dump(by_alias=False) for h in hotspots]}
    except ESIError as e:
        raise HTTPException(status_code=502, detail=f"ESI API error: {str(e)}")
    except EVECopilotError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fw/vulnerable")
async def get_fw_vulnerable(
    service: FactionWarfareService = Depends(get_faction_warfare_service)
):
    """Get FW systems close to flipping (>90% contested) using refactored service"""
    try:
        vulnerable = service.get_fw_hotspots(min_progress=90.0)
        return {"vulnerable": [v.model_dump(by_alias=False) for v in vulnerable]}
    except ESIError as e:
        raise HTTPException(status_code=502, detail=f"ESI API error: {str(e)}")
    except EVECopilotError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fw/update")
async def update_fw_status(
    service: FactionWarfareService = Depends(get_faction_warfare_service)
):
    """Manually trigger FW status update from ESI using refactored service"""
    try:
        count = service.update_fw_systems()
        return {
            "status": "success",
            "systems_updated": count,
            "message": f"Successfully updated {count} FW systems"
        }
    except ESIError as e:
        raise HTTPException(status_code=502, detail=f"ESI API error: {str(e)}")
    except EVECopilotError as e:
        raise HTTPException(status_code=500, detail=str(e))
