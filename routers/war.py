"""
War Room Router
Endpoints for combat analysis and demand forecasting
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional

# Legacy services (temporary until full migration)
from killmail_service import killmail_service as legacy_killmail_service
from sovereignty_service import sovereignty_service as legacy_sovereignty_service
from fw_service import fw_service as legacy_fw_service
from war_analyzer import war_analyzer as legacy_war_analyzer
from route_service import route_service
from zkillboard_live_service import zkill_live_service
from config import REGIONS

# New refactored services
from src.core.config import get_settings, Settings
from src.core.database import DatabasePool
from src.integrations.esi.client import ESIClient
from src.services.warroom.repository import WarRoomRepository
from src.services.warroom.sovereignty import SovereigntyService
from src.services.warroom.fw import FactionWarfareService
from src.services.warroom.analyzer import WarAnalyzer
from src.core.exceptions import NotFoundError, EVECopilotError, ESIError, ExternalAPIError

router = APIRouter(prefix="/api/war", tags=["War Room"])


# ============================================================
# Dependency Injection Functions
# ============================================================

def get_war_room_repository(settings: Settings = Depends(get_settings)) -> WarRoomRepository:
    """
    Dependency injection for WarRoomRepository.

    Creates shared repository instance for War Room services.
    """
    db_pool = DatabasePool(settings)
    return WarRoomRepository(db_pool)


def get_sovereignty_service(
    repository: WarRoomRepository = Depends(get_war_room_repository)
) -> SovereigntyService:
    """
    Dependency injection for SovereigntyService.

    Requires ESI client and War Room repository.
    """
    esi_client = ESIClient()
    return SovereigntyService(repository, esi_client)


def get_faction_warfare_service(
    repository: WarRoomRepository = Depends(get_war_room_repository)
) -> FactionWarfareService:
    """
    Dependency injection for FactionWarfareService.

    Requires ESI client and War Room repository.
    """
    esi_client = ESIClient()
    return FactionWarfareService(repository, esi_client)


def get_war_analyzer(
    repository: WarRoomRepository = Depends(get_war_room_repository)
) -> WarAnalyzer:
    """
    Dependency injection for WarAnalyzer.

    Requires only War Room repository.
    """
    return WarAnalyzer(repository)


# ============================================================
# Combat Loss Endpoints
# ============================================================

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
        # Use get_fw_hotspots with 90% threshold to find vulnerable systems
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


# ============================================================
# Doctrine and Conflict Analysis Endpoints
# ============================================================

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


@router.get("/system/{system_id}/danger")
async def get_system_danger(
    system_id: int,
    days: int = Query(1, ge=1, le=7),
    analyzer: WarAnalyzer = Depends(get_war_analyzer)
):
    """Get danger score for a solar system using refactored service"""
    try:
        danger = analyzer.get_system_danger_score(system_id, days)
        return danger.model_dump()
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


# ============================================================
# Route and Item Analysis Endpoints (Legacy)
# ============================================================

@router.get("/route/safe/{from_system}/{to_system}")
async def get_safe_route(
    from_system: int,
    to_system: int,
    avoid_lowsec: bool = Query(True),
    avoid_nullsec: bool = Query(True)
):
    """Get route with danger analysis (legacy service)"""
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
    days: int = Query(7, ge=1, le=30),
    analyzer: WarAnalyzer = Depends(get_war_analyzer)
):
    """Get combat stats for a specific item using refactored service"""
    try:
        stats = analyzer.get_item_combat_stats(type_id, days)
        return stats
    except EVECopilotError as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# War Room Alerts Endpoint
# ============================================================

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
                # Query high-value kills from last 24 hours
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

                    # Determine priority based on value
                    priority = "high" if value > 5_000_000_000 else "medium"

                    # Create alert message
                    location = system_name if system_name else region_name
                    message = f"High-value {type_name} destroyed in {location}"

                    # Convert date to ISO format timestamp
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


# ============================================================
# zKillboard Live Endpoints (Real-time Combat Intelligence)
# ============================================================

@router.get("/live/kills")
async def get_live_kills(
    system_id: Optional[int] = Query(None, description="Filter by solar system ID"),
    region_id: Optional[int] = Query(None, description="Filter by region ID"),
    limit: int = Query(50, ge=1, le=200, description="Max results")
):
    """
    Get recent killmails from live zKillboard stream (last 24h).

    Real-time combat intelligence from RedisQ. Data is updated continuously
    by the background listener service.

    Args:
        system_id: Filter kills to specific system
        region_id: Filter kills to specific region
        limit: Maximum number of kills to return

    Returns:
        List of recent killmails with full details
    """
    try:
        if not system_id and not region_id:
            return {
                "error": "Must specify either system_id or region_id",
                "example": "/api/war/live/kills?region_id=10000002&limit=50"
            }

        kills = zkill_live_service.get_recent_kills(
            system_id=system_id,
            region_id=region_id,
            limit=limit
        )

        return {
            "kills": kills,
            "count": len(kills),
            "filter": {
                "system_id": system_id,
                "region_id": region_id
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/live/hotspots")
async def get_live_hotspots():
    """
    Get active combat hotspots (last hour).

    Hotspot = 5+ kills in 5 minutes in same system.
    Indicates active combat, gate camps, or fleet battles.

    Returns:
        List of active hotspots with kill counts and locations
    """
    try:
        hotspots = zkill_live_service.get_active_hotspots()

        return {
            "hotspots": hotspots,
            "count": len(hotspots),
            "threshold": "5 kills in 5 minutes"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/live/demand/top")
async def get_top_destroyed_items(
    limit: int = Query(20, ge=1, le=100)
):
    """
    Get most destroyed items in last 24h.

    Identifies high-demand items for war profiteering.
    Items are sorted by quantity destroyed (descending).

    Args:
        limit: Maximum number of items to return

    Returns:
        List of items with destruction counts
    """
    try:
        items = zkill_live_service.get_top_destroyed_items(limit)

        return {
            "items": items,
            "count": len(items),
            "window": "24 hours"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/live/demand/{item_type_id}")
async def get_live_item_demand(
    item_type_id: int
):
    """
    Get destroyed quantity for an item (last 24h).

    Only counts DESTROYED items (not dropped), as these create market demand.
    Useful for war profiteering and market speculation.

    Args:
        item_type_id: EVE item type ID

    Returns:
        Total quantity destroyed in last 24h
    """
    try:
        quantity = zkill_live_service.get_item_demand(item_type_id)

        return {
            "item_type_id": item_type_id,
            "quantity_destroyed_24h": quantity,
            "note": "Only destroyed items counted (not dropped)"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/live/stats")
async def get_live_stats():
    """
    Get zKillboard live service statistics.

    Returns:
        Service status and statistics
    """
    try:
        stats = zkill_live_service.get_stats()

        return stats

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/live/report/24h")
async def get_24h_battle_report():
    """
    Get comprehensive 24h battle report by region.

    Returns detailed statistics for each region including:
    - Total kills and ISK destroyed
    - Top 3 most active systems
    - Top 3 most destroyed ship types
    - Average kill value

    Also includes global summary with most active and expensive regions.

    Example response:
    {
        "period": "24h",
        "global": {
            "total_kills": 1523,
            "total_isk_destroyed": 45678900000.0,
            "most_active_region": "The Forge",
            "most_expensive_region": "Delve"
        },
        "regions": [
            {
                "region_id": 10000002,
                "region_name": "The Forge",
                "kills": 234,
                "total_isk_destroyed": 8900000000.0,
                "avg_kill_value": 38034188.03,
                "top_systems": [
                    {"system_id": 30002187, "system_name": "Jita", "kills": 45},
                    ...
                ],
                "top_ships": [
                    {"ship_type_id": 670, "ship_name": "Capsule", "losses": 12},
                    ...
                ]
            },
            ...
        ]
    }
    """
    try:
        report = zkill_live_service.get_24h_battle_report()

        return report

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pilot-intelligence")
async def get_pilot_intelligence_report():
    """
    Get comprehensive pilot intelligence battle report with all 4 combat layers.

    Includes:
    - Hot Zones: Systems with highest kill activity (5+ kills in 5 minutes)
    - Capital Kills: Capital ship losses (Titans, Supercarriers, Carriers, Dreadnoughts, FAX)
    - High-Value Kills: Expensive ship losses (100M+ ISK)
    - Danger Zones: Areas with industrial/hauler losses
    - Global Statistics: Total kills, ISK destroyed, peak activity hour

    Data is cached for 10 minutes for performance.

    Response:
    {
        "global": {
            "total_kills": 2500,
            "total_isk_destroyed": 500000000000.0,
            "peak_hour_utc": 18
        },
        "hot_zones": [
            {
                "system_id": 30002187,
                "system_name": "Jita",
                "region_name": "The Forge",
                "kills": 45,
                "kill_rate": 0.5,
                "total_value": 2500000000.0
            },
            ...
        ],
        "capital_kills": {
            "titans": {"count": 2, "kills": [...]},
            "supercarriers": {"count": 1, "kills": [...]},
            ...
        },
        "high_value_kills": [...],
        "danger_zones": [...]
    }
    """
    try:
        report = zkill_live_service.build_pilot_intelligence_report()
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to build pilot intelligence report: {str(e)}")


@router.get("/live-hotspots")
async def get_live_hotspots():
    """
    Get all currently active combat hotspots for real-time 3D map visualization.

    Returns hotspots detected in the last 5 minutes with age calculation.
    Used by BattleMapPreview component for live pulsing visualization.

    Response:
    {
        "hotspots": [
            {
                "system_id": 30002187,
                "system_name": "Jita",
                "region_id": 10000002,
                "kill_count": 12,
                "timestamp": 1735939200.0,
                "age_seconds": 45,
                "latest_ship": 670,
                "latest_value": 5000000.0,
                "danger_level": "HIGH"
            },
            ...
        ],
        "count": 5,
        "last_updated": "2025-01-06T20:00:00Z"
    }
    """
    try:
        import time
        import json
        from datetime import datetime

        hotspots = []
        current_time = time.time()

        # Scan Redis for all live_hotspot:* keys
        redis_client = zkill_live_service.redis_client
        hotspot_keys = list(redis_client.scan_iter("live_hotspot:*"))

        for key in hotspot_keys:
            data = redis_client.get(key)
            if data:
                hotspot = json.loads(data)

                # Calculate age in seconds
                hotspot_time = hotspot.get("timestamp", current_time)
                age_seconds = int(current_time - hotspot_time)
                hotspot["age_seconds"] = age_seconds

                # Only include hotspots less than 5 minutes old
                if age_seconds < 300:
                    hotspots.append(hotspot)

        return {
            "hotspots": hotspots,
            "count": len(hotspots),
            "last_updated": datetime.utcnow().isoformat() + "Z"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch live hotspots: {str(e)}")
