"""
System Endpoints Router.

Provides endpoints for system-level combat data.
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Depends

from src.database import get_db_connection
from src.zkillboard_live_service import zkill_live_service
from src.services.warroom.analyzer import WarAnalyzer
from src.core.exceptions import EVECopilotError
from .dependencies import get_war_analyzer

router = APIRouter()


@router.get("/system/{system_id}/kills")
async def get_system_kills(
    system_id: int,
    limit: int = Query(500, ge=1, le=1000, description="Max results"),
    hours: int = Query(24, ge=1, le=168, description="Hours to look back")
):
    """
    Get recent killmails for a system from database (historical data).

    Unlike /live/kills which uses RedisQ stream, this endpoint queries
    the killmails table for reliable historical data.

    Args:
        system_id: Solar system ID
        limit: Maximum number of kills to return
        hours: How many hours back to search

    Returns:
        List of killmails with full details
    """
    try:
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        killmail_id,
                        killmail_time,
                        solar_system_id,
                        ship_type_id,
                        ship_value,
                        victim_character_id,
                        victim_corporation_id,
                        victim_alliance_id,
                        attacker_count,
                        is_solo,
                        is_npc
                    FROM killmails
                    WHERE solar_system_id = %s
                      AND killmail_time >= %s
                    ORDER BY killmail_time DESC
                    LIMIT %s
                """, (system_id, cutoff_time, limit))

                rows = cur.fetchall()

                kills = []
                for row in rows:
                    kills.append({
                        "killmail_id": row[0],
                        "killmail_time": row[1].isoformat() + "Z",
                        "solar_system_id": row[2],
                        "ship_type_id": row[3],
                        "ship_value": row[4] or 0,
                        "victim_character_id": row[5],
                        "victim_corporation_id": row[6],
                        "victim_alliance_id": row[7],
                        "attacker_count": row[8] or 1,
                        "is_solo": row[9] or False,
                        "is_npc": row[10] or False
                    })

        return {
            "kills": kills,
            "count": len(kills),
            "system_id": system_id,
            "hours": hours
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch system kills: {str(e)}")


@router.get("/system/{system_id}/ship-classes")
async def get_system_ship_classes(
    system_id: int,
    hours: int = Query(default=24, ge=1, le=168),
    group_by: str = Query(default="category", pattern="^(category|role|both)$")
):
    """
    Get ship class breakdown for kills in a system using official EVE classification.

    Analyzes recent killmails with official EVE ship categories and roles.
    Useful for battle analysis, doctrine detection, and fleet composition insights.

    Args:
        system_id: Solar system ID
        hours: Hours to look back (default: 24, max: 168/7 days)
        group_by: Grouping mode - "category", "role", or "both" (default: category)

    Returns:
        Ship class breakdown with counts
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                if group_by == "category":
                    cur.execute("""
                        SELECT
                            ship_category,
                            COUNT(*) as count
                        FROM killmails
                        WHERE solar_system_id = %s
                            AND killmail_time >= NOW() - INTERVAL '%s hours'
                            AND ship_category IS NOT NULL
                        GROUP BY ship_category
                        ORDER BY count DESC
                    """, (system_id, hours))
                elif group_by == "role":
                    cur.execute("""
                        SELECT
                            ship_role,
                            COUNT(*) as count
                        FROM killmails
                        WHERE solar_system_id = %s
                            AND killmail_time >= NOW() - INTERVAL '%s hours'
                            AND ship_role IS NOT NULL
                        GROUP BY ship_role
                        ORDER BY count DESC
                    """, (system_id, hours))
                else:  # both
                    cur.execute("""
                        SELECT
                            ship_category || ':' || ship_role as ship_class,
                            COUNT(*) as count
                        FROM killmails
                        WHERE solar_system_id = %s
                            AND killmail_time >= NOW() - INTERVAL '%s hours'
                            AND ship_category IS NOT NULL
                            AND ship_role IS NOT NULL
                        GROUP BY ship_category, ship_role
                        ORDER BY count DESC
                    """, (system_id, hours))

                rows = cur.fetchall()

                breakdown = {}
                total_kills = 0
                for key, count in rows:
                    breakdown[key] = count
                    total_kills += count

                return {
                    "system_id": system_id,
                    "hours": hours,
                    "total_kills": total_kills,
                    "group_by": group_by,
                    "breakdown": breakdown
                }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get ship class breakdown: {str(e)}")


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
