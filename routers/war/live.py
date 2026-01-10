"""
Live Endpoints Router.

Provides endpoints for real-time zKillboard data and pilot intelligence.
"""

import json
import time
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from src.zkillboard_live_service import zkill_live_service

router = APIRouter()


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
async def get_live_hotspots_from_service():
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
    """
    try:
        report = zkill_live_service.build_pilot_intelligence_report()
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to build pilot intelligence report: {str(e)}")


@router.get("/live-hotspots")
async def get_live_hotspots():
    """
    Get all currently active combat hotspots for real-time 2D map visualization.

    Returns hotspots detected in the last 5 minutes with age calculation.
    Used by BattleMapPreview component for live pulsing visualization.
    """
    try:
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
