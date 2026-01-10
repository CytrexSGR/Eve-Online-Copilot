"""
War API Router for Public Frontend
Serves live battle data for the public combat intelligence dashboard
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict
import redis
import json
from src.database import get_db_connection

# Cache configuration
BATTLE_CACHE_TTL = 60  # 1 minute cache for live data

# Redis client
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

router = APIRouter(prefix="/api/war", tags=["war"])


@router.get("/battles/active")
async def get_active_battles(limit: int = Query(default=10, ge=1, le=1000)) -> Dict:
    """
    Get currently active battles with real-time statistics.

    Cache: 1 minute (live data needs frequent updates)
    """
    try:
        # Check cache first
        cache_key = f"endpoint:battles_active:{limit}"
        try:
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Get active battles with system/region info
                cur.execute("""
                    SELECT
                        b.battle_id,
                        b.solar_system_id,
                        ms."solarSystemName",
                        mr."regionName",
                        ms.security,
                        b.total_kills,
                        b.total_isk_destroyed,
                        b.last_milestone_notified,
                        b.started_at,
                        b.last_kill_at,
                        b.telegram_message_id,
                        EXTRACT(EPOCH FROM (b.last_kill_at - b.started_at)) / 60 as duration_minutes,
                        ms.x,
                        ms.z
                    FROM battles b
                    JOIN "mapSolarSystems" ms ON ms."solarSystemID" = b.solar_system_id
                    JOIN "mapRegions" mr ON mr."regionID" = ms."regionID"
                    WHERE b.status = 'active'
                    ORDER BY b.total_kills DESC, b.total_isk_destroyed DESC
                    LIMIT %s
                """, (limit,))

                rows = cur.fetchall()

                # Get total count
                cur.execute("SELECT COUNT(*) FROM battles WHERE status = 'active'")
                total_active = cur.fetchone()[0]

                battles = []
                for row in rows:
                    (battle_id, system_id, system_name, region_name, security,
                     total_kills, total_isk, last_milestone, started_at, last_kill_at,
                     telegram_message_id, duration_minutes, x, z) = row

                    # Determine intensity
                    if total_kills >= 100 or total_isk >= 50_000_000_000:
                        intensity = "extreme"
                    elif total_kills >= 50 or total_isk >= 20_000_000_000:
                        intensity = "high"
                    elif total_kills >= 10:
                        intensity = "moderate"
                    else:
                        intensity = "low"

                    battles.append({
                        "battle_id": battle_id,
                        "system_id": system_id,
                        "system_name": system_name,
                        "region_name": region_name,
                        "security": float(security) if security else 0.0,
                        "total_kills": total_kills,
                        "total_isk_destroyed": int(total_isk),
                        "last_milestone": last_milestone or 0,
                        "started_at": started_at.isoformat() + "Z" if started_at else None,
                        "last_kill_at": last_kill_at.isoformat() + "Z" if last_kill_at else None,
                        "duration_minutes": int(duration_minutes) if duration_minutes else 0,
                        "telegram_sent": telegram_message_id is not None,
                        "intensity": intensity,
                        "x": float(x),
                        "z": float(z)
                    })

                result = {
                    "battles": battles,
                    "total_active": total_active
                }

                # Cache the result
                try:
                    redis_client.setex(cache_key, BATTLE_CACHE_TTL, json.dumps(result))
                except Exception:
                    pass

                return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch active battles: {str(e)}")


@router.get("/telegram/recent")
async def get_recent_telegram_alerts(limit: int = Query(default=5, ge=1, le=20)) -> Dict:
    """
    Get recent Telegram alerts sent for battles.

    Cache: 1 minute
    """
    try:
        # Check cache first
        cache_key = f"endpoint:telegram_recent:{limit}"
        try:
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Get recent battles with Telegram messages
                cur.execute("""
                    SELECT
                        b.battle_id,
                        ms."solarSystemName",
                        mr."regionName",
                        ms.security,
                        b.total_kills,
                        b.total_isk_destroyed,
                        b.last_milestone_notified,
                        b.telegram_message_id,
                        b.initial_alert_sent,
                        b.last_kill_at,
                        b.status
                    FROM battles b
                    JOIN "mapSolarSystems" ms ON ms."solarSystemID" = b.solar_system_id
                    JOIN "mapRegions" mr ON mr."regionID" = ms."regionID"
                    WHERE b.telegram_message_id IS NOT NULL
                    ORDER BY b.last_kill_at DESC
                    LIMIT %s
                """, (limit,))

                rows = cur.fetchall()

                alerts = []
                for row in rows:
                    (battle_id, system_name, region_name, security,
                     total_kills, total_isk, milestone, telegram_id,
                     initial_sent, last_kill_at, status) = row

                    # Determine alert type
                    if milestone and milestone > 0:
                        alert_type = "milestone"
                    elif initial_sent:
                        alert_type = "initial"
                    else:
                        alert_type = "update"

                    alerts.append({
                        "battle_id": battle_id,
                        "system_name": system_name,
                        "region_name": region_name,
                        "security": float(security) if security else 0.0,
                        "alert_type": alert_type,
                        "milestone": milestone or 0,
                        "total_kills": total_kills,
                        "total_isk_destroyed": int(total_isk),
                        "telegram_message_id": telegram_id,
                        "sent_at": last_kill_at.isoformat() + "Z" if last_kill_at else None,
                        "status": status
                    })

                result = {
                    "alerts": alerts,
                    "total": len(alerts)
                }

                # Cache the result
                try:
                    redis_client.setex(cache_key, BATTLE_CACHE_TTL, json.dumps(result))
                except Exception:
                    pass

                return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch telegram alerts: {str(e)}")
