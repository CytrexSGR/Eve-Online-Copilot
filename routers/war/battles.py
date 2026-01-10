"""
Battle Endpoints Router.

Provides endpoints for active battles, battle details, and telegram alerts.
"""

import aiohttp
import asyncio
import redis
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Depends

from src.database import get_db_connection

router = APIRouter()

# Redis cache for ESI names (24h TTL)
ESI_NAME_TTL = 86400


@router.get("/battles/active")
async def get_active_battles(limit: int = Query(default=10, ge=1, le=1000)):
    """
    Get currently active battles with real-time statistics.

    Returns battles that are currently ongoing (status='active') with:
    - System and region information
    - Kill counts and ISK destroyed
    - Last milestone reached
    - Time since battle started
    - Telegram notification status

    Args:
        limit: Maximum number of battles to return (default: 10, max: 1000)

    Returns:
        {
            "battles": [...],
            "total_active": 5
        }
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Get active battles with system/region info including coordinates
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

                return {
                    "battles": battles,
                    "total_active": total_active
                }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch active battles: {str(e)}")


@router.get("/battle/{battle_id}/kills")
async def get_battle_kills(
    battle_id: int,
    limit: int = Query(500, ge=1, le=1000, description="Max results")
):
    """
    Get killmails for a specific battle (only within battle timeframe).

    Unlike /system/{system_id}/kills which gets all kills in a time window,
    this endpoint returns only kills that occurred during the battle period
    (between started_at and last_kill_at/ended_at).

    Args:
        battle_id: Battle ID
        limit: Maximum number of kills to return

    Returns:
        List of killmails that occurred during this battle
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Get battle timeframe
                cur.execute("""
                    SELECT solar_system_id, started_at, COALESCE(ended_at, last_kill_at) as end_time
                    FROM battles
                    WHERE battle_id = %s
                """, (battle_id,))

                battle_row = cur.fetchone()
                if not battle_row:
                    raise HTTPException(status_code=404, detail=f"Battle {battle_id} not found")

                system_id, started_at, end_time = battle_row

                # Get killmails linked to this battle (via battle_id FK)
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
                    WHERE battle_id = %s
                    ORDER BY killmail_time DESC
                    LIMIT %s
                """, (battle_id, limit))

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
            "battle_id": battle_id,
            "system_id": system_id,
            "started_at": started_at.isoformat() + "Z",
            "end_time": end_time.isoformat() + "Z"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch battle kills: {str(e)}")


@router.get("/battle/{battle_id}/ship-classes")
async def get_battle_ship_classes(
    battle_id: int,
    group_by: str = Query(default="category", pattern="^(category|role|both)$")
):
    """
    Get ship class breakdown for kills in a specific battle.

    Args:
        battle_id: Battle ID
        group_by: Grouping mode - "category", "role", or "both" (default: category)

    Returns:
        Ship class breakdown for kills during this battle
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Get battle timeframe
                cur.execute("""
                    SELECT solar_system_id, started_at, COALESCE(ended_at, last_kill_at) as end_time
                    FROM battles
                    WHERE battle_id = %s
                """, (battle_id,))

                battle_row = cur.fetchone()
                if not battle_row:
                    raise HTTPException(status_code=404, detail=f"Battle {battle_id} not found")

                system_id, started_at, end_time = battle_row

                # Get ship class breakdown using battle_id FK
                if group_by == "category":
                    cur.execute("""
                        SELECT
                            COALESCE(
                                LOWER(k.ship_category),
                                LOWER(g."groupName")
                            ) as category,
                            COUNT(*) as count
                        FROM killmails k
                        LEFT JOIN "invTypes" t ON t."typeID" = k.ship_type_id
                        LEFT JOIN "invGroups" g ON g."groupID" = t."groupID"
                        WHERE k.battle_id = %s
                        GROUP BY category
                        ORDER BY count DESC
                    """, (battle_id,))
                elif group_by == "role":
                    cur.execute("""
                        SELECT
                            COALESCE(ship_role, 'standard') as role,
                            COUNT(*) as count
                        FROM killmails
                        WHERE battle_id = %s
                        GROUP BY role
                        ORDER BY count DESC
                    """, (battle_id,))
                else:  # both
                    cur.execute("""
                        SELECT
                            COALESCE(
                                LOWER(k.ship_category),
                                LOWER(g."groupName")
                            ) || ':' || COALESCE(k.ship_role, 'standard') as combined,
                            COUNT(*) as count
                        FROM killmails k
                        LEFT JOIN "invTypes" t ON t."typeID" = k.ship_type_id
                        LEFT JOIN "invGroups" g ON g."groupID" = t."groupID"
                        WHERE k.battle_id = %s
                        GROUP BY combined
                        ORDER BY count DESC
                    """, (battle_id,))

                rows = cur.fetchall()
                breakdown = {row[0]: row[1] for row in rows}

                # Get total kills
                cur.execute("""
                    SELECT COUNT(*)
                    FROM killmails
                    WHERE battle_id = %s
                """, (battle_id,))

                total_kills = cur.fetchone()[0]

                return {
                    "battle_id": battle_id,
                    "system_id": system_id,
                    "started_at": started_at.isoformat() + "Z",
                    "end_time": end_time.isoformat() + "Z",
                    "total_kills": total_kills,
                    "group_by": group_by,
                    "breakdown": breakdown
                }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch battle ship classes: {str(e)}")


@router.get("/battle/{battle_id}/participants")
async def get_battle_participants(battle_id: int):
    """
    Get detailed participant breakdown for a battle.

    Shows alliances and corporations involved on each side,
    with kill/loss counts and ISK destroyed. Names are resolved from ESI.

    Args:
        battle_id: Battle ID

    Returns:
        Attackers and defenders with statistics and names
    """
    redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

    try:
        # Helper functions to fetch names from ESI with Redis caching
        async def get_alliance_name(session: aiohttp.ClientSession, alliance_id: int) -> str:
            cache_key = f"esi:alliance:{alliance_id}:name"
            cached = redis_client.get(cache_key)
            if cached:
                return cached
            try:
                url = f"https://esi.evetech.net/latest/alliances/{alliance_id}/"
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        data = await response.json()
                        name = data.get("name", f"Alliance {alliance_id}")
                        redis_client.setex(cache_key, ESI_NAME_TTL, name)
                        return name
            except:
                pass
            return f"Alliance {alliance_id}"

        async def get_corporation_name(session: aiohttp.ClientSession, corp_id: int) -> str:
            cache_key = f"esi:corporation:{corp_id}:name"
            cached = redis_client.get(cache_key)
            if cached:
                return cached
            try:
                url = f"https://esi.evetech.net/latest/corporations/{corp_id}/"
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        data = await response.json()
                        name = data.get("name", f"Corporation {corp_id}")
                        redis_client.setex(cache_key, ESI_NAME_TTL, name)
                        return name
            except:
                pass
            return f"Corporation {corp_id}"

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Verify battle exists
                cur.execute("SELECT solar_system_id FROM battles WHERE battle_id = %s", (battle_id,))
                if not cur.fetchone():
                    raise HTTPException(status_code=404, detail=f"Battle {battle_id} not found")

                # Get attacker alliances
                cur.execute("""
                    SELECT
                        k.final_blow_alliance_id as alliance_id,
                        COUNT(*) as kills,
                        COUNT(DISTINCT k.final_blow_corporation_id) as corps_involved
                    FROM killmails k
                    WHERE k.battle_id = %s
                      AND k.final_blow_alliance_id IS NOT NULL
                    GROUP BY k.final_blow_alliance_id
                    ORDER BY kills DESC
                """, (battle_id,))
                attacker_alliances_raw = cur.fetchall()

                # Get attacker corporations
                cur.execute("""
                    SELECT
                        k.final_blow_corporation_id as corp_id,
                        k.final_blow_alliance_id as alliance_id,
                        COUNT(*) as kills
                    FROM killmails k
                    WHERE k.battle_id = %s
                      AND k.final_blow_corporation_id IS NOT NULL
                    GROUP BY k.final_blow_corporation_id, k.final_blow_alliance_id
                    ORDER BY kills DESC
                    LIMIT 20
                """, (battle_id,))
                attacker_corps_raw = cur.fetchall()

                # Get victim alliances
                cur.execute("""
                    SELECT
                        k.victim_alliance_id as alliance_id,
                        COUNT(*) as losses,
                        SUM(k.ship_value) as isk_lost,
                        COUNT(DISTINCT k.victim_corporation_id) as corps_involved
                    FROM killmails k
                    WHERE k.battle_id = %s
                      AND k.victim_alliance_id IS NOT NULL
                    GROUP BY k.victim_alliance_id
                    ORDER BY losses DESC
                """, (battle_id,))
                victim_alliances_raw = cur.fetchall()

                # Get victim corporations
                cur.execute("""
                    SELECT
                        k.victim_corporation_id as corp_id,
                        k.victim_alliance_id as alliance_id,
                        COUNT(*) as losses,
                        SUM(k.ship_value) as isk_lost
                    FROM killmails k
                    WHERE k.battle_id = %s
                      AND k.victim_corporation_id IS NOT NULL
                    GROUP BY k.victim_corporation_id, k.victim_alliance_id
                    ORDER BY losses DESC
                    LIMIT 20
                """, (battle_id,))
                victim_corps_raw = cur.fetchall()

        # Collect all unique IDs to fetch names for
        alliance_ids = set()
        corp_ids = set()

        for row in attacker_alliances_raw:
            if row[0]:
                alliance_ids.add(row[0])
        for row in victim_alliances_raw:
            if row[0]:
                alliance_ids.add(row[0])
        for row in attacker_corps_raw:
            if row[0]:
                corp_ids.add(row[0])
        for row in victim_corps_raw:
            if row[0]:
                corp_ids.add(row[0])

        # Fetch all names concurrently
        alliance_names = {}
        corp_names = {}

        async with aiohttp.ClientSession() as session:
            alliance_tasks = {aid: get_alliance_name(session, aid) for aid in alliance_ids}
            alliance_results = await asyncio.gather(*alliance_tasks.values())
            alliance_names = dict(zip(alliance_tasks.keys(), alliance_results))

            corp_tasks = {cid: get_corporation_name(session, cid) for cid in corp_ids}
            corp_results = await asyncio.gather(*corp_tasks.values())
            corp_names = dict(zip(corp_tasks.keys(), corp_results))

        # Build response with names
        attacker_alliances = []
        for row in attacker_alliances_raw:
            attacker_alliances.append({
                "alliance_id": row[0],
                "alliance_name": alliance_names.get(row[0], f"Alliance {row[0]}"),
                "kills": row[1],
                "corps_involved": row[2]
            })

        attacker_corps = []
        for row in attacker_corps_raw:
            attacker_corps.append({
                "corporation_id": row[0],
                "corporation_name": corp_names.get(row[0], f"Corporation {row[0]}"),
                "alliance_id": row[1],
                "kills": row[2]
            })

        victim_alliances = []
        for row in victim_alliances_raw:
            victim_alliances.append({
                "alliance_id": row[0],
                "alliance_name": alliance_names.get(row[0], f"Alliance {row[0]}"),
                "losses": row[1],
                "isk_lost": row[2] or 0,
                "corps_involved": row[3]
            })

        victim_corps = []
        for row in victim_corps_raw:
            victim_corps.append({
                "corporation_id": row[0],
                "corporation_name": corp_names.get(row[0], f"Corporation {row[0]}"),
                "alliance_id": row[1],
                "losses": row[2],
                "isk_lost": row[3] or 0
            })

        return {
            "battle_id": battle_id,
            "attackers": {
                "alliances": attacker_alliances,
                "corporations": attacker_corps,
                "total_alliances": len(attacker_alliances),
                "total_kills": sum(a["kills"] for a in attacker_alliances)
            },
            "defenders": {
                "alliances": victim_alliances,
                "corporations": victim_corps,
                "total_alliances": len(victim_alliances),
                "total_losses": sum(v["losses"] for v in victim_alliances),
                "total_isk_lost": sum(v["isk_lost"] for v in victim_alliances)
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch battle participants: {str(e)}")


@router.get("/telegram/recent")
async def get_recent_telegram_alerts(limit: int = Query(default=5, ge=1, le=20)):
    """
    Get recent Telegram alerts sent for battles.

    Returns the last N battles that had Telegram notifications sent,
    showing what alerts were sent to the Telegram channel.

    Args:
        limit: Maximum number of alerts to return (default: 5, max: 20)

    Returns:
        {
            "alerts": [...],
            "total": 5
        }
    """
    try:
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
                     total_kills, total_isk, last_milestone, telegram_message_id,
                     initial_alert_sent, sent_at, status) = row

                    # Determine alert type
                    if status == 'ended':
                        alert_type = "ended"
                    elif last_milestone >= 500:
                        alert_type = "milestone"
                    elif last_milestone >= 10:
                        alert_type = "milestone"
                    elif initial_alert_sent:
                        alert_type = "new_battle"
                    else:
                        alert_type = "unknown"

                    alerts.append({
                        "battle_id": battle_id,
                        "system_name": system_name,
                        "region_name": region_name,
                        "security": float(security) if security else 0.0,
                        "alert_type": alert_type,
                        "milestone": last_milestone or 0,
                        "total_kills": total_kills,
                        "total_isk_destroyed": int(total_isk),
                        "telegram_message_id": telegram_message_id,
                        "sent_at": sent_at.isoformat() + "Z" if sent_at else None,
                        "status": status
                    })

                return {
                    "alerts": alerts,
                    "total": len(alerts)
                }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch telegram alerts: {str(e)}")
