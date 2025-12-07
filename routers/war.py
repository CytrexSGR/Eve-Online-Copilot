"""
War Room Router
Endpoints for combat analysis and demand forecasting
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from killmail_service import killmail_service
from sovereignty_service import sovereignty_service
from fw_service import fw_service
from war_analyzer import war_analyzer
from route_service import route_service
from config import REGIONS

router = APIRouter(prefix="/api/war", tags=["War Room"])


@router.get("/losses/{region_id}")
async def get_losses(
    region_id: int,
    days: int = Query(7, ge=1, le=30),
    type: str = Query("all", pattern="^(all|ships|items)$")
):
    """Get combat losses for a region"""
    try:
        if type == "ships":
            return {"ships": killmail_service.get_ship_losses(region_id, days)}
        elif type == "items":
            return {"items": killmail_service.get_item_losses(region_id, days)}
        else:
            return {
                "ships": killmail_service.get_ship_losses(region_id, days),
                "items": killmail_service.get_item_losses(region_id, days)
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/demand/{region_id}")
async def get_demand(
    region_id: int,
    days: int = Query(7, ge=1, le=30)
):
    """Full demand analysis for a region"""
    try:
        return war_analyzer.analyze_demand(region_id, days)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/heatmap")
async def get_heatmap(
    days: int = Query(7, ge=1, le=30),
    min_kills: int = Query(5, ge=1)
):
    """Get heatmap data for galaxy visualization"""
    try:
        return {"systems": war_analyzer.get_heatmap_data(days, min_kills)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/campaigns")
async def get_campaigns(
    hours: int = Query(48, ge=1, le=168)
):
    """Get upcoming sovereignty battles"""
    try:
        return {"campaigns": sovereignty_service.get_upcoming_battles(hours)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/campaigns/update")
async def update_campaigns():
    """Manually trigger campaign update from ESI"""
    try:
        result = sovereignty_service.update_campaigns()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fw/hotspots")
async def get_fw_hotspots(
    min_contested: float = Query(50.0, ge=0, le=100)
):
    """Get Faction Warfare hotspots"""
    try:
        return {"hotspots": fw_service.get_hotspots(min_contested)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fw/vulnerable")
async def get_fw_vulnerable():
    """Get FW systems close to flipping (>90% contested)"""
    try:
        return {"vulnerable": fw_service.get_vulnerable_systems()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fw/update")
async def update_fw_status():
    """Manually trigger FW status update from ESI"""
    try:
        result = fw_service.update_status()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/doctrines/{region_id}")
async def get_doctrines(
    region_id: int,
    days: int = Query(7, ge=1, le=30)
):
    """Detect fleet doctrines from loss patterns"""
    try:
        return {"doctrines": war_analyzer.detect_doctrines(region_id, days)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conflicts")
async def get_conflicts(
    days: int = Query(7, ge=1, le=30),
    top: int = Query(20, ge=1, le=100)
):
    """Get top alliance conflicts"""
    try:
        return {"conflicts": war_analyzer.get_alliance_conflicts(days, top)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/system/{system_id}/danger")
async def get_system_danger(
    system_id: int,
    days: int = Query(1, ge=1, le=7)
):
    """Get danger score for a solar system"""
    try:
        return war_analyzer.get_system_danger_score(system_id, days)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_regional_summary(
    days: int = Query(7, ge=1, le=30)
):
    """Get summary of combat activity per region"""
    try:
        return {"regions": war_analyzer.get_regional_summary(days)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/top-ships")
async def get_top_ships(
    days: int = Query(7, ge=1, le=30),
    limit: int = Query(20, ge=1, le=100)
):
    """Get most destroyed ships across all regions"""
    try:
        return {"ships": war_analyzer.get_top_ships_galaxy(days, limit)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/route/safe/{from_system}/{to_system}")
async def get_safe_route(
    from_system: int,
    to_system: int,
    avoid_lowsec: bool = Query(True),
    avoid_nullsec: bool = Query(True)
):
    """Get route with danger analysis"""
    try:
        result = route_service.get_route_with_danger(
            from_system, to_system, avoid_lowsec, avoid_nullsec
        )

        if not result:
            raise HTTPException(status_code=404, detail="No route found")

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/item/{type_id}/stats")
async def get_item_combat_stats(
    type_id: int,
    days: int = Query(7, ge=1, le=30)
):
    """Get combat stats for a specific item"""
    try:
        return war_analyzer.get_item_combat_stats(type_id, days)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
