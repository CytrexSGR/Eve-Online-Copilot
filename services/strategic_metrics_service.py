"""
Strategic Metrics Service
Provides strategic-level intelligence data for LLM analysis.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from decimal import Decimal
import redis
import requests
import json

# Redis connection for caching
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# ESI API base URL
ESI_BASE_URL = "https://esi.evetech.net/latest"

# Cache TTL for alliance/corp names (7 days)
NAME_CACHE_TTL = 7 * 24 * 60 * 60


def get_alliance_name(alliance_id: int) -> str:
    """
    Get alliance name from ESI API with Redis caching.

    Args:
        alliance_id: The alliance ID

    Returns:
        Alliance name or fallback string
    """
    if not alliance_id:
        return "Unknown"

    cache_key = f"esi:alliance:{alliance_id}:name"

    # Try cache first
    try:
        cached = redis_client.get(cache_key)
        if cached:
            return cached
    except redis.RedisError:
        pass

    # Fetch from ESI
    try:
        response = requests.get(
            f"{ESI_BASE_URL}/alliances/{alliance_id}/",
            timeout=5,
            headers={"Accept": "application/json"}
        )
        if response.status_code == 200:
            data = response.json()
            name = data.get("name", f"Alliance {alliance_id}")
            # Cache the result
            try:
                redis_client.setex(cache_key, NAME_CACHE_TTL, name)
            except redis.RedisError:
                pass
            return name
    except Exception as e:
        print(f"Error fetching alliance {alliance_id}: {e}")

    return f"Alliance {alliance_id}"


def get_corporation_name(corp_id: int) -> str:
    """
    Get corporation name from ESI API with Redis caching.

    Args:
        corp_id: The corporation ID

    Returns:
        Corporation name or fallback string
    """
    if not corp_id:
        return "Unknown"

    cache_key = f"esi:corporation:{corp_id}:name"

    # Try cache first
    try:
        cached = redis_client.get(cache_key)
        if cached:
            return cached
    except redis.RedisError:
        pass

    # Fetch from ESI
    try:
        response = requests.get(
            f"{ESI_BASE_URL}/corporations/{corp_id}/",
            timeout=5,
            headers={"Accept": "application/json"}
        )
        if response.status_code == 200:
            data = response.json()
            name = data.get("name", f"Corp {corp_id}")
            # Cache the result
            try:
                redis_client.setex(cache_key, NAME_CACHE_TTL, name)
            except redis.RedisError:
                pass
            return name
    except Exception as e:
        print(f"Error fetching corporation {corp_id}: {e}")

    return f"Corp {corp_id}"


def batch_resolve_alliance_names(alliance_ids: List[int]) -> Dict[int, str]:
    """
    Resolve multiple alliance names efficiently.
    Uses cache where available, fetches missing from ESI.

    Args:
        alliance_ids: List of alliance IDs to resolve

    Returns:
        Dict mapping alliance_id to name
    """
    result = {}
    ids_to_fetch = []

    # Check cache first
    for aid in alliance_ids:
        if not aid:
            continue
        cache_key = f"esi:alliance:{aid}:name"
        try:
            cached = redis_client.get(cache_key)
            if cached:
                result[aid] = cached
            else:
                ids_to_fetch.append(aid)
        except redis.RedisError:
            ids_to_fetch.append(aid)

    # Fetch missing from ESI (one by one, ESI doesn't have batch endpoint for names)
    for aid in ids_to_fetch:
        result[aid] = get_alliance_name(aid)

    return result


def convert_decimals(obj: Any) -> Any:
    """Recursively convert Decimal values to float for JSON serialization."""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: convert_decimals(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimals(item) for item in obj]
    return obj

# Database connection settings
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "eve_sde",
    "user": "eve",
    "password": "EvE_Pr0ject_2024"
}


def get_db_connection():
    """Get a database connection with RealDictCursor."""
    return psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)


def get_strategic_metrics() -> Dict:
    """
    Gather all strategic metrics for the homepage briefing.
    Returns current period data + comparison period for trend analysis.
    """
    metrics = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "power_balance": get_power_balance_metrics(),
        "territorial": get_territorial_metrics(),
        "capital_status": get_capital_fleet_metrics(),
        "momentum": get_momentum_indicators(),
        "chokepoints": get_chokepoint_control(),
        "escalation": get_escalation_indicators(),
        "high_value_losses": get_high_value_losses(),
    }
    # Convert all Decimals to floats for JSON serialization
    return convert_decimals(metrics)


def get_power_balance_metrics() -> Dict:
    """
    Coalition ISK balance - who can sustain the war longer?
    Compares 24h vs previous 24h and 7-day trends.
    """
    conn = get_db_connection()
    cur = conn.cursor()

    # Get top alliances by activity with ISK destroyed vs lost
    cur.execute("""
        WITH alliance_kills AS (
            -- ISK destroyed by alliance (as attacker)
            SELECT
                ka.alliance_id,
                COUNT(DISTINCT k.killmail_id) as kills,
                SUM(k.ship_value) as isk_destroyed
            FROM killmail_attackers ka
            JOIN killmails k ON ka.killmail_id = k.killmail_id
            WHERE k.killmail_time >= NOW() - INTERVAL '24 hours'
            AND ka.alliance_id IS NOT NULL
            GROUP BY ka.alliance_id
        ),
        alliance_losses AS (
            -- ISK lost by alliance (as victim)
            SELECT
                victim_alliance_id as alliance_id,
                COUNT(*) as losses,
                SUM(ship_value) as isk_lost
            FROM killmails
            WHERE killmail_time >= NOW() - INTERVAL '24 hours'
            AND victim_alliance_id IS NOT NULL
            GROUP BY victim_alliance_id
        ),
        previous_kills AS (
            SELECT
                ka.alliance_id,
                COUNT(DISTINCT k.killmail_id) as kills,
                SUM(k.ship_value) as isk_destroyed
            FROM killmail_attackers ka
            JOIN killmails k ON ka.killmail_id = k.killmail_id
            WHERE k.killmail_time >= NOW() - INTERVAL '48 hours'
            AND k.killmail_time < NOW() - INTERVAL '24 hours'
            AND ka.alliance_id IS NOT NULL
            GROUP BY ka.alliance_id
        ),
        previous_losses AS (
            SELECT
                victim_alliance_id as alliance_id,
                COUNT(*) as losses,
                SUM(ship_value) as isk_lost
            FROM killmails
            WHERE killmail_time >= NOW() - INTERVAL '48 hours'
            AND killmail_time < NOW() - INTERVAL '24 hours'
            AND victim_alliance_id IS NOT NULL
            GROUP BY victim_alliance_id
        )
        SELECT
            COALESCE(ak.alliance_id, al.alliance_id) as alliance_id,
            'Alliance ' || COALESCE(ak.alliance_id, al.alliance_id)::text as alliance_name,
            COALESCE(ak.kills, 0) as kills_24h,
            COALESCE(al.losses, 0) as losses_24h,
            COALESCE(ak.isk_destroyed, 0) as isk_destroyed_24h,
            COALESCE(al.isk_lost, 0) as isk_lost_24h,
            COALESCE(pk.kills, 0) as kills_prev_24h,
            COALESCE(pl.losses, 0) as losses_prev_24h,
            COALESCE(pk.isk_destroyed, 0) as isk_destroyed_prev_24h,
            COALESCE(pl.isk_lost, 0) as isk_lost_prev_24h,
            CASE
                WHEN COALESCE(ak.isk_destroyed, 0) + COALESCE(al.isk_lost, 0) > 0
                THEN ROUND(COALESCE(ak.isk_destroyed, 0)::numeric /
                     (COALESCE(ak.isk_destroyed, 0) + COALESCE(al.isk_lost, 0)) * 100, 1)
                ELSE 0
            END as efficiency_24h
        FROM alliance_kills ak
        FULL OUTER JOIN alliance_losses al ON ak.alliance_id = al.alliance_id
        LEFT JOIN previous_kills pk ON COALESCE(ak.alliance_id, al.alliance_id) = pk.alliance_id
        LEFT JOIN previous_losses pl ON COALESCE(ak.alliance_id, al.alliance_id) = pl.alliance_id
        WHERE COALESCE(ak.kills, 0) + COALESCE(al.losses, 0) >= 10
        ORDER BY COALESCE(ak.kills, 0) + COALESCE(al.losses, 0) DESC
        LIMIT 15
    """)

    alliances = cur.fetchall()
    cur.close()
    conn.close()

    # Batch resolve alliance names from ESI
    alliance_ids = [a['alliance_id'] for a in alliances if a['alliance_id']]
    name_map = batch_resolve_alliance_names(alliance_ids)

    # Calculate net ISK and trends
    results = []
    for a in alliances:
        net_isk_24h = (a['isk_destroyed_24h'] or 0) - (a['isk_lost_24h'] or 0)
        net_isk_prev = (a['isk_destroyed_prev_24h'] or 0) - (a['isk_lost_prev_24h'] or 0)
        alliance_id = a['alliance_id']

        results.append({
            "alliance_id": alliance_id,
            "alliance_name": name_map.get(alliance_id, f"Alliance {alliance_id}"),
            "kills_24h": a['kills_24h'],
            "losses_24h": a['losses_24h'],
            "isk_destroyed_24h": a['isk_destroyed_24h'],
            "isk_lost_24h": a['isk_lost_24h'],
            "net_isk_24h": net_isk_24h,
            "efficiency_24h": float(a['efficiency_24h'] or 0),
            "kills_change": a['kills_24h'] - (a['kills_prev_24h'] or 0),
            "isk_trend": net_isk_24h - net_isk_prev,
        })

    return {
        "top_alliances": results,
        "period": "24h",
        "comparison": "previous 24h"
    }


def get_territorial_metrics() -> Dict:
    """
    Regional control - where are groups fighting (home vs away)?
    Identify who is on offensive vs defensive.
    """
    conn = get_db_connection()
    cur = conn.cursor()

    # Top regions by activity
    cur.execute("""
        WITH current_period AS (
            SELECT
                region_id,
                COUNT(*) as kills,
                SUM(ship_value) as isk_destroyed,
                COUNT(*) FILTER (WHERE is_capital) as capital_kills
            FROM killmails
            WHERE killmail_time >= NOW() - INTERVAL '24 hours'
            AND region_id IS NOT NULL
            GROUP BY region_id
        ),
        previous_period AS (
            SELECT
                region_id,
                COUNT(*) as kills,
                SUM(ship_value) as isk_destroyed
            FROM killmails
            WHERE killmail_time >= NOW() - INTERVAL '48 hours'
            AND killmail_time < NOW() - INTERVAL '24 hours'
            AND region_id IS NOT NULL
            GROUP BY region_id
        )
        SELECT
            c.region_id,
            COALESCE(r."regionName", 'Unknown') as region_name,
            c.kills as kills_24h,
            c.isk_destroyed as isk_destroyed_24h,
            c.capital_kills,
            COALESCE(p.kills, 0) as kills_prev_24h,
            COALESCE(p.isk_destroyed, 0) as isk_destroyed_prev_24h,
            c.kills - COALESCE(p.kills, 0) as kills_change
        FROM current_period c
        LEFT JOIN previous_period p ON c.region_id = p.region_id
        LEFT JOIN "mapRegions" r ON c.region_id = r."regionID"
        ORDER BY c.kills DESC
        LIMIT 15
    """)

    regions = cur.fetchall()

    # Identify hotspot shifts
    cur.execute("""
        WITH current_top AS (
            SELECT region_id, COUNT(*) as kills,
                   ROW_NUMBER() OVER (ORDER BY COUNT(*) DESC) as rank_now
            FROM killmails
            WHERE killmail_time >= NOW() - INTERVAL '24 hours'
            AND region_id IS NOT NULL
            GROUP BY region_id
        ),
        previous_top AS (
            SELECT region_id, COUNT(*) as kills,
                   ROW_NUMBER() OVER (ORDER BY COUNT(*) DESC) as rank_prev
            FROM killmails
            WHERE killmail_time >= NOW() - INTERVAL '48 hours'
            AND killmail_time < NOW() - INTERVAL '24 hours'
            AND region_id IS NOT NULL
            GROUP BY region_id
        )
        SELECT
            c.region_id,
            COALESCE(r."regionName", 'Unknown') as region_name,
            c.rank_now,
            COALESCE(p.rank_prev, 99) as rank_prev,
            COALESCE(p.rank_prev, 99) - c.rank_now as rank_change
        FROM current_top c
        LEFT JOIN previous_top p ON c.region_id = p.region_id
        LEFT JOIN "mapRegions" r ON c.region_id = r."regionID"
        WHERE c.rank_now <= 10
        ORDER BY c.rank_now
    """)

    hotspot_shifts = cur.fetchall()

    cur.close()
    conn.close()

    return {
        "top_regions": [dict(r) for r in regions],
        "hotspot_shifts": [dict(h) for h in hotspot_shifts],
        "period": "24h"
    }


def get_capital_fleet_metrics() -> Dict:
    """
    Capital ship status - who is burning reserves?
    Compare to 7-day and 30-day averages.
    """
    conn = get_db_connection()
    cur = conn.cursor()

    # Capital losses by type (24h vs averages)
    cur.execute("""
        WITH daily_capitals AS (
            SELECT
                ship_category,
                DATE(killmail_time) as kill_date,
                COUNT(*) as count,
                SUM(ship_value) as isk_value
            FROM killmails
            WHERE is_capital = true
            AND killmail_time >= NOW() - INTERVAL '30 days'
            GROUP BY ship_category, DATE(killmail_time)
        ),
        today_capitals AS (
            SELECT
                ship_category,
                COUNT(*) as count_24h,
                SUM(ship_value) as isk_24h
            FROM killmails
            WHERE is_capital = true
            AND killmail_time >= NOW() - INTERVAL '24 hours'
            GROUP BY ship_category
        ),
        avg_7d AS (
            SELECT
                ship_category,
                ROUND(AVG(count), 1) as avg_daily_7d,
                ROUND(AVG(isk_value), 0) as avg_isk_7d
            FROM daily_capitals
            WHERE kill_date >= CURRENT_DATE - INTERVAL '7 days'
            GROUP BY ship_category
        ),
        avg_30d AS (
            SELECT
                ship_category,
                ROUND(AVG(count), 1) as avg_daily_30d,
                ROUND(AVG(isk_value), 0) as avg_isk_30d
            FROM daily_capitals
            GROUP BY ship_category
        )
        SELECT
            COALESCE(t.ship_category, a7.ship_category, a30.ship_category) as ship_category,
            COALESCE(t.count_24h, 0) as count_24h,
            COALESCE(t.isk_24h, 0) as isk_24h,
            COALESCE(a7.avg_daily_7d, 0) as avg_daily_7d,
            COALESCE(a30.avg_daily_30d, 0) as avg_daily_30d,
            CASE
                WHEN COALESCE(a7.avg_daily_7d, 0) > 0
                THEN ROUND((COALESCE(t.count_24h, 0) - a7.avg_daily_7d) / a7.avg_daily_7d * 100, 1)
                ELSE 0
            END as change_vs_7d_avg
        FROM today_capitals t
        FULL OUTER JOIN avg_7d a7 ON t.ship_category = a7.ship_category
        FULL OUTER JOIN avg_30d a30 ON COALESCE(t.ship_category, a7.ship_category) = a30.ship_category
        WHERE COALESCE(t.ship_category, a7.ship_category, a30.ship_category) IN
              ('Titan', 'Supercarrier', 'Dreadnought', 'Carrier', 'Force Auxiliary')
        ORDER BY COALESCE(t.isk_24h, 0) DESC
    """)

    capital_stats = cur.fetchall()

    # Top alliances losing capitals
    cur.execute("""
        SELECT
            victim_alliance_id,
            'Alliance ' || victim_alliance_id::text as alliance_name,
            COUNT(*) as capital_losses,
            SUM(ship_value) as isk_lost,
            COUNT(*) FILTER (WHERE ship_category = 'Titan') as titans,
            COUNT(*) FILTER (WHERE ship_category = 'Supercarrier') as supers,
            COUNT(*) FILTER (WHERE ship_category = 'Dreadnought') as dreads
        FROM killmails k
        WHERE is_capital = true
        AND killmail_time >= NOW() - INTERVAL '24 hours'
        AND victim_alliance_id IS NOT NULL
        GROUP BY victim_alliance_id
        ORDER BY isk_lost DESC
        LIMIT 10
    """)

    capital_losers = cur.fetchall()

    cur.close()
    conn.close()

    # Resolve alliance names for capital losers
    loser_alliance_ids = [l['victim_alliance_id'] for l in capital_losers if l['victim_alliance_id']]
    loser_name_map = batch_resolve_alliance_names(loser_alliance_ids)

    top_losers = []
    for l in capital_losers:
        alliance_id = l['victim_alliance_id']
        loser_data = dict(l)
        loser_data['alliance_name'] = loser_name_map.get(alliance_id, f"Alliance {alliance_id}")
        top_losers.append(loser_data)

    return {
        "by_category": [dict(c) for c in capital_stats],
        "top_losers": top_losers,
        "period": "24h",
        "comparison": "7d and 30d averages"
    }


def get_momentum_indicators() -> Dict:
    """
    Efficiency trends over 7 days - who is gaining/losing momentum?
    """
    conn = get_db_connection()
    cur = conn.cursor()

    # Daily efficiency for top alliances over 7 days
    cur.execute("""
        WITH daily_stats AS (
            SELECT
                DATE(k.killmail_time) as kill_date,
                ka.alliance_id,
                COUNT(DISTINCT k.killmail_id) as kills,
                SUM(k.ship_value) as isk_destroyed
            FROM killmail_attackers ka
            JOIN killmails k ON ka.killmail_id = k.killmail_id
            WHERE k.killmail_time >= NOW() - INTERVAL '7 days'
            AND ka.alliance_id IS NOT NULL
            GROUP BY DATE(k.killmail_time), ka.alliance_id
        ),
        daily_losses AS (
            SELECT
                DATE(killmail_time) as kill_date,
                victim_alliance_id as alliance_id,
                COUNT(*) as losses,
                SUM(ship_value) as isk_lost
            FROM killmails
            WHERE killmail_time >= NOW() - INTERVAL '7 days'
            AND victim_alliance_id IS NOT NULL
            GROUP BY DATE(killmail_time), victim_alliance_id
        ),
        active_alliances AS (
            SELECT alliance_id FROM daily_stats
            GROUP BY alliance_id
            HAVING SUM(kills) >= 50
        )
        SELECT
            ds.alliance_id,
            'Alliance ' || ds.alliance_id::text as alliance_name,
            ds.kill_date,
            COALESCE(ds.kills, 0) as kills,
            COALESCE(dl.losses, 0) as losses,
            COALESCE(ds.isk_destroyed, 0) as isk_destroyed,
            COALESCE(dl.isk_lost, 0) as isk_lost,
            CASE
                WHEN COALESCE(ds.isk_destroyed, 0) + COALESCE(dl.isk_lost, 0) > 0
                THEN ROUND(COALESCE(ds.isk_destroyed, 0)::numeric /
                     (COALESCE(ds.isk_destroyed, 0) + COALESCE(dl.isk_lost, 0)) * 100, 1)
                ELSE 0
            END as efficiency
        FROM daily_stats ds
        JOIN active_alliances aa ON ds.alliance_id = aa.alliance_id
        LEFT JOIN daily_losses dl ON ds.alliance_id = dl.alliance_id AND ds.kill_date = dl.kill_date
        ORDER BY ds.alliance_id, ds.kill_date
    """)

    daily_data = cur.fetchall()
    cur.close()
    conn.close()

    # Batch resolve alliance names
    unique_alliance_ids = list(set(row['alliance_id'] for row in daily_data if row['alliance_id']))
    name_map = batch_resolve_alliance_names(unique_alliance_ids)

    # Calculate trends per alliance
    alliance_trends = {}
    for row in daily_data:
        aid = row['alliance_id']
        if aid not in alliance_trends:
            alliance_trends[aid] = {
                "alliance_id": aid,
                "alliance_name": name_map.get(aid, f"Alliance {aid}"),
                "daily_efficiency": []
            }
        alliance_trends[aid]["daily_efficiency"].append({
            "date": row['kill_date'].isoformat(),
            "efficiency": float(row['efficiency'] or 0)
        })

    # Calculate 7-day trend (linear regression approximation)
    results = []
    for aid, data in alliance_trends.items():
        efficiencies = [d['efficiency'] for d in data['daily_efficiency']]
        if len(efficiencies) >= 3:
            # Simple trend: compare first half to second half
            first_half = sum(efficiencies[:len(efficiencies)//2]) / max(len(efficiencies)//2, 1)
            second_half = sum(efficiencies[len(efficiencies)//2:]) / max(len(efficiencies) - len(efficiencies)//2, 1)
            trend = second_half - first_half

            results.append({
                "alliance_id": aid,
                "alliance_name": data['alliance_name'],
                "current_efficiency": efficiencies[-1] if efficiencies else 0,
                "trend_7d": round(trend, 1),
                "momentum": "gaining" if trend > 3 else "losing" if trend < -3 else "stable"
            })

    # Sort by absolute trend
    results.sort(key=lambda x: abs(x['trend_7d']), reverse=True)

    return {
        "alliance_momentum": results[:15],
        "period": "7 days"
    }


def get_chokepoint_control() -> Dict:
    """
    Gate camp and chokepoint activity - who controls logistics routes?
    """
    conn = get_db_connection()
    cur = conn.cursor()

    # Systems with high industrial/hauler kills (gate camp indicators)
    cur.execute("""
        WITH camp_systems AS (
            SELECT
                solar_system_id,
                COUNT(*) as total_kills,
                COUNT(*) FILTER (WHERE ship_category IN ('Industrial', 'Hauler', 'Freighter')) as hauler_kills,
                COUNT(*) FILTER (WHERE ship_category = 'Capsule') as pod_kills,
                SUM(ship_value) as isk_destroyed
            FROM killmails
            WHERE killmail_time >= NOW() - INTERVAL '24 hours'
            GROUP BY solar_system_id
            HAVING COUNT(*) FILTER (WHERE ship_category IN ('Industrial', 'Hauler', 'Freighter', 'Capsule')) >= 3
        ),
        previous_camps AS (
            SELECT
                solar_system_id,
                COUNT(*) FILTER (WHERE ship_category IN ('Industrial', 'Hauler', 'Freighter')) as hauler_kills_prev
            FROM killmails
            WHERE killmail_time >= NOW() - INTERVAL '48 hours'
            AND killmail_time < NOW() - INTERVAL '24 hours'
            GROUP BY solar_system_id
        )
        SELECT
            c.solar_system_id,
            COALESCE(s."solarSystemName", 'Unknown') as system_name,
            COALESCE(r."regionName", 'Unknown') as region_name,
            s."security" as security_status,
            c.total_kills,
            c.hauler_kills,
            c.pod_kills,
            c.isk_destroyed,
            COALESCE(p.hauler_kills_prev, 0) as hauler_kills_prev,
            c.hauler_kills - COALESCE(p.hauler_kills_prev, 0) as hauler_change
        FROM camp_systems c
        LEFT JOIN previous_camps p ON c.solar_system_id = p.solar_system_id
        LEFT JOIN "mapSolarSystems" s ON c.solar_system_id = s."solarSystemID"
        LEFT JOIN "mapRegions" r ON s."regionID" = r."regionID"
        ORDER BY c.hauler_kills DESC, c.total_kills DESC
        LIMIT 15
    """)

    gate_camps = cur.fetchall()

    cur.close()
    conn.close()

    return {
        "active_camps": [dict(g) for g in gate_camps],
        "period": "24h"
    }


def get_escalation_indicators() -> Dict:
    """
    Supercap/Titan deployments - where might escalation happen?
    """
    conn = get_db_connection()
    cur = conn.cursor()

    # Regions with supercap activity
    cur.execute("""
        SELECT
            region_id,
            COALESCE(r."regionName", 'Unknown') as region_name,
            COUNT(*) FILTER (WHERE ship_category = 'Titan') as titan_kills,
            COUNT(*) FILTER (WHERE ship_category = 'Supercarrier') as super_kills,
            COUNT(*) FILTER (WHERE ship_category IN ('Dreadnought', 'Carrier', 'Force Auxiliary')) as other_caps,
            SUM(ship_value) as total_isk
        FROM killmails k
        LEFT JOIN "mapRegions" r ON k.region_id = r."regionID"
        WHERE killmail_time >= NOW() - INTERVAL '24 hours'
        AND is_capital = true
        AND region_id IS NOT NULL
        GROUP BY region_id, r."regionName"
        HAVING COUNT(*) >= 3
        ORDER BY COUNT(*) FILTER (WHERE ship_category IN ('Titan', 'Supercarrier')) DESC,
                 COUNT(*) DESC
        LIMIT 10
    """)

    escalation_zones = cur.fetchall()

    # Active large battles (potential escalation points)
    cur.execute("""
        SELECT
            b.battle_id,
            b.solar_system_id,
            COALESCE(s."solarSystemName", 'Unknown') as system_name,
            COALESCE(r."regionName", 'Unknown') as region_name,
            b.total_kills,
            b.total_isk_destroyed,
            b.capital_kills,
            b.started_at,
            EXTRACT(EPOCH FROM (NOW() - b.started_at))/60 as duration_minutes
        FROM battles b
        LEFT JOIN "mapSolarSystems" s ON b.solar_system_id = s."solarSystemID"
        LEFT JOIN "mapRegions" r ON s."regionID" = r."regionID"
        WHERE b.status = 'active'
        AND b.total_kills >= 20
        ORDER BY b.capital_kills DESC, b.total_isk_destroyed DESC
        LIMIT 5
    """)

    active_battles = cur.fetchall()

    cur.close()
    conn.close()

    return {
        "escalation_zones": [dict(e) for e in escalation_zones],
        "active_large_battles": [dict(b) for b in active_battles],
        "period": "24h"
    }


def get_high_value_losses() -> Dict:
    """
    Top kills by ISK value - notable losses.
    """
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            k.killmail_id,
            k.ship_value,
            k.ship_type_id,
            COALESCE(t."typeName", 'Unknown') as ship_name,
            k.victim_alliance_id,
            CASE WHEN k.victim_alliance_id IS NOT NULL
                 THEN 'Alliance ' || k.victim_alliance_id::text
                 ELSE 'Unknown'
            END as victim_alliance,
            k.solar_system_id,
            COALESCE(s."solarSystemName", 'Unknown') as system_name,
            COALESCE(r."regionName", 'Unknown') as region_name,
            k.killmail_time
        FROM killmails k
        LEFT JOIN "invTypes" t ON k.ship_type_id = t."typeID"
        LEFT JOIN "mapSolarSystems" s ON k.solar_system_id = s."solarSystemID"
        LEFT JOIN "mapRegions" r ON s."regionID" = r."regionID"
        WHERE k.killmail_time >= NOW() - INTERVAL '24 hours'
        AND k.ship_value >= 1000000000  -- 1B+ ISK
        ORDER BY k.ship_value DESC
        LIMIT 10
    """)

    high_value = cur.fetchall()

    cur.close()
    conn.close()

    # Resolve alliance names for victims
    victim_alliance_ids = [h['victim_alliance_id'] for h in high_value if h['victim_alliance_id']]
    victim_name_map = batch_resolve_alliance_names(victim_alliance_ids)

    top_losses = []
    for h in high_value:
        loss_data = dict(h)
        alliance_id = h['victim_alliance_id']
        if alliance_id:
            loss_data['victim_alliance'] = victim_name_map.get(alliance_id, f"Alliance {alliance_id}")
        top_losses.append(loss_data)

    return {
        "top_losses": top_losses,
        "period": "24h"
    }


def get_global_summary() -> Dict:
    """
    Quick global stats for context.
    """
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            COUNT(*) as total_kills_24h,
            SUM(ship_value) as total_isk_24h,
            COUNT(*) FILTER (WHERE is_capital) as capital_kills_24h,
            COUNT(DISTINCT region_id) as active_regions,
            COUNT(DISTINCT victim_alliance_id) FILTER (WHERE victim_alliance_id IS NOT NULL) as alliances_involved
        FROM killmails
        WHERE killmail_time >= NOW() - INTERVAL '24 hours'
    """)

    current = cur.fetchone()

    cur.execute("""
        SELECT
            COUNT(*) as total_kills_prev,
            SUM(ship_value) as total_isk_prev
        FROM killmails
        WHERE killmail_time >= NOW() - INTERVAL '48 hours'
        AND killmail_time < NOW() - INTERVAL '24 hours'
    """)

    previous = cur.fetchone()

    cur.close()
    conn.close()

    # Handle None values and Decimals
    total_kills_24h = int(current['total_kills_24h'] or 0)
    total_isk_24h = float(current['total_isk_24h'] or 0)
    total_kills_prev = int(previous['total_kills_prev'] or 0)
    total_isk_prev = float(previous['total_isk_prev'] or 0)

    kills_change = ((total_kills_24h - total_kills_prev) /
                    max(total_kills_prev, 1) * 100) if total_kills_prev else 0

    return {
        "total_kills_24h": total_kills_24h,
        "total_isk_24h": total_isk_24h,
        "capital_kills_24h": int(current['capital_kills_24h'] or 0),
        "active_regions": int(current['active_regions'] or 0),
        "alliances_involved": int(current['alliances_involved'] or 0),
        "kills_change_percent": round(kills_change, 1),
        "isk_change_percent": round(
            ((total_isk_24h - total_isk_prev) /
             max(total_isk_prev, 1) * 100) if total_isk_prev else 0, 1
        )
    }
