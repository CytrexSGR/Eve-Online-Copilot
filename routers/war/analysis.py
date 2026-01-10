"""
Analysis Endpoints Router.

Provides endpoints for combat analysis, doctrines, conflicts, and demand.
"""

from fastapi import APIRouter, HTTPException, Query, Depends

from src.killmail_service import killmail_service as legacy_killmail_service
from src.services.warroom.analyzer import WarAnalyzer
from src.services.warroom.repository import WarRoomRepository
from src.core.exceptions import EVECopilotError
from .dependencies import get_war_analyzer, get_war_room_repository

router = APIRouter()


@router.get("/losses/{region_id}")
async def get_losses(
    region_id: int,
    days: int = Query(7, ge=1, le=30),
    type: str = Query("all", pattern="^(all|ships|items)$")
):
    """Get combat losses for a region (legacy service)"""
    try:
        if type == "ships":
            return {"ships": legacy_killmail_service.get_ship_losses(region_id, days)}
        elif type == "items":
            return {"items": legacy_killmail_service.get_item_losses(region_id, days)}
        else:
            return {
                "ships": legacy_killmail_service.get_ship_losses(region_id, days),
                "items": legacy_killmail_service.get_item_losses(region_id, days)
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/demand/{region_id}")
async def get_demand(
    region_id: int,
    days: int = Query(7, ge=1, le=30),
    analyzer: WarAnalyzer = Depends(get_war_analyzer)
):
    """Full demand analysis for a region using refactored service"""
    try:
        result = analyzer.analyze_demand(region_id, days)
        return result.model_dump()
    except EVECopilotError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/heatmap")
async def get_heatmap(
    days: int = Query(7, ge=1, le=30),
    min_kills: int = Query(5, ge=1),
    analyzer: WarAnalyzer = Depends(get_war_analyzer)
):
    """Get heatmap data for galaxy visualization using refactored service"""
    try:
        systems = analyzer.get_heatmap_data(days, min_kills)
        return {"systems": [s.model_dump() for s in systems]}
    except EVECopilotError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/doctrines/{region_id}")
async def get_doctrines(
    region_id: int,
    days: int = Query(7, ge=1, le=30),
    analyzer: WarAnalyzer = Depends(get_war_analyzer)
):
    """Detect fleet doctrines from loss patterns using refactored service"""
    try:
        doctrines = analyzer.detect_doctrines(region_id, days)
        return {"doctrines": [d.model_dump() for d in doctrines]}
    except EVECopilotError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conflicts")
async def get_conflicts(
    days: int = Query(7, ge=1, le=30),
    top: int = Query(20, ge=1, le=100),
    analyzer: WarAnalyzer = Depends(get_war_analyzer)
):
    """Get top alliance conflicts using refactored service"""
    try:
        conflicts = analyzer.get_alliance_conflicts(days, top)
        return {"conflicts": [c.model_dump() for c in conflicts]}
    except EVECopilotError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_regional_summary(
    days: int = Query(7, ge=1, le=30),
    analyzer: WarAnalyzer = Depends(get_war_analyzer)
):
    """Get summary of combat activity per region using refactored service"""
    try:
        summary = analyzer.get_regional_summary(days)
        return {"regions": summary}
    except EVECopilotError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/top-ships")
async def get_top_ships(
    days: int = Query(7, ge=1, le=30),
    limit: int = Query(20, ge=1, le=100),
    analyzer: WarAnalyzer = Depends(get_war_analyzer)
):
    """Get most destroyed ships across all regions using refactored service"""
    try:
        ships = analyzer.get_top_ships_galaxy(days, limit)
        return {"ships": [s.model_dump(by_alias=False) for s in ships]}
    except EVECopilotError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/item/{type_id}/stats")
async def get_item_combat_stats(
    type_id: int,
    days: int = Query(7, ge=1, le=30),
    analyzer: WarAnalyzer = Depends(get_war_analyzer)
):
    """Get combat stats for a specific item using refactored service"""
    try:
        stats = analyzer.get_item_combat_stats(type_id, days)
        return stats
    except EVECopilotError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts")
async def get_war_alerts(
    limit: int = Query(5, ge=1, le=50),
    repository: WarRoomRepository = Depends(get_war_room_repository)
):
    """
    Get recent high-priority war events from combat losses.

    Returns alerts for high-value ship kills (>1B ISK) from the last 24 hours.
    Alerts are prioritized as:
    - high: >5B ISK
    - medium: >1B ISK

    Args:
        limit: Maximum number of alerts to return (default: 5)

    Returns:
        List of alert objects with priority, message, timestamp, and value
    """
    try:
        with repository.db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT
                        csl.ship_type_id as type_id,
                        t."typeName",
                        csl.date,
                        csl.total_value_destroyed,
                        csl.region_id,
                        r."regionName",
                        csl.solar_system_id,
                        ms."solarSystemName"
                    FROM combat_ship_losses csl
                    JOIN "invTypes" t ON csl.ship_type_id = t."typeID"
                    JOIN "mapRegions" r ON csl.region_id = r."regionID"
                    LEFT JOIN "mapSolarSystems" ms ON csl.solar_system_id = ms."solarSystemID"
                    WHERE csl.total_value_destroyed > 1000000000
                        AND csl.date >= CURRENT_DATE - INTERVAL '1 day'
                    ORDER BY csl.date DESC, csl.total_value_destroyed DESC
                    LIMIT %s
                """, (limit,))

                rows = cursor.fetchall()

                alerts = []
                for row in rows:
                    type_id, type_name, kill_date, value, region_id, region_name, system_id, system_name = row

                    priority = "high" if value > 5_000_000_000 else "medium"
                    location = system_name if system_name else region_name
                    message = f"High-value {type_name} destroyed in {location}"
                    timestamp = kill_date.isoformat() + "T00:00:00Z"

                    alerts.append({
                        "priority": priority,
                        "message": message,
                        "timestamp": timestamp,
                        "value": float(value)
                    })

                return alerts

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch war alerts: {str(e)}")
