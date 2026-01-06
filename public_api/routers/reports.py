"""
Reports API Router
Serves cached combat intelligence reports from Redis
"""

from fastapi import APIRouter, HTTPException
from typing import Dict
import redis
from services.zkillboard import zkill_live_service

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/battle-24h")
async def get_battle_report() -> Dict:
    """
    24-Hour Battle Report by Region

    Returns comprehensive combat statistics for the last 24 hours,
    organized by region with top systems, ships, and destroyed items.

    Cache: 10 minutes
    """
    try:
        report = zkill_live_service.get_24h_battle_report()
        return report
    except redis.RedisError as e:
        raise HTTPException(
            status_code=503,
            detail="Redis connection error. Reports temporarily unavailable."
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Failed to generate battle report"
        )


@router.get("/war-profiteering")
async def get_war_profiteering() -> Dict:
    """
    War Profiteering Daily Digest

    Identifies market opportunities based on destroyed items in combat.
    Shows items with highest market value destroyed in last 24 hours.

    Cache: 1 hour (refreshed daily at 06:00 UTC)
    """
    try:
        report = zkill_live_service.get_war_profiteering_report(limit=20)
        return report
    except redis.RedisError as e:
        raise HTTPException(
            status_code=503,
            detail="Redis connection error. Reports temporarily unavailable."
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Failed to generate war profiteering report"
        )


@router.get("/alliance-wars")
async def get_alliance_wars() -> Dict:
    """
    Alliance War Tracker

    Tracks active alliance conflicts with kill/death ratios and ISK efficiency.
    Shows top 5 most active alliance wars in last 24 hours.

    Cache: 30 minutes
    """
    try:
        report = await zkill_live_service.get_alliance_war_tracker(limit=5)
        return report
    except redis.RedisError as e:
        raise HTTPException(
            status_code=503,
            detail="Redis connection error. Reports temporarily unavailable."
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Failed to generate alliance wars report"
        )


@router.get("/trade-routes")
async def get_trade_routes() -> Dict:
    """
    Trade Route Danger Map

    Analyzes danger levels along major HighSec trade routes between hubs.
    Shows danger scores per system based on recent kills and gate camps.

    Cache: 1 hour (refreshed daily at 08:00 UTC)
    """
    try:
        report = zkill_live_service.get_trade_route_danger_map()
        return report
    except redis.RedisError as e:
        raise HTTPException(
            status_code=503,
            detail="Redis connection error. Reports temporarily unavailable."
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Failed to generate trade routes report"
        )
