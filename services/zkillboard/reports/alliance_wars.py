"""
Alliance Wars Report - Alliance conflict tracking.

Tracks active alliance wars with:
- Kill/death ratios and ISK efficiency
- System hotspots
- Ship class breakdowns
- Coalition detection
"""

import json
import aiohttp
from datetime import datetime
from typing import Dict, List

from src.database import get_db_connection
from .base import REPORT_CACHE_TTL


class AllianceWarsMixin:
    """Mixin providing alliance war tracking methods."""

    async def get_alliance_name(self, alliance_id: int) -> str:
        """
        Get alliance name from ESI API with Redis caching.

        Args:
            alliance_id: Alliance ID

        Returns:
            Alliance name or fallback string
        """
        if not alliance_id:
            return "Unknown"

        cache_key = f"esi:alliance:{alliance_id}:name"

        # Try cache first
        try:
            cached = self.redis_client.get(cache_key)
            if cached:
                return cached if isinstance(cached, str) else cached.decode('utf-8')
        except Exception:
            pass

        # Fetch from ESI
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://esi.evetech.net/latest/alliances/{alliance_id}/"
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        data = await response.json()
                        name = data.get("name", f"Alliance {alliance_id}")
                        # Cache for 7 days
                        try:
                            self.redis_client.setex(cache_key, 7 * 24 * 60 * 60, name)
                        except Exception:
                            pass
                        return name
        except Exception as e:
            print(f"Error fetching alliance {alliance_id}: {e}")
        return f"Alliance {alliance_id}"

    async def get_alliance_war_tracker_postgres(self, limit: int = 10, days: int = 7) -> Dict:
        """
        Track active alliance wars using PostgreSQL persistent storage.

        Reads from alliance_wars and war_daily_stats tables
        instead of Redis (which had 24h TTL and data loss).

        Args:
            limit: Number of wars to return
            days: How many days of history to analyze

        Returns:
            Dict with top alliance wars and their statistics
        """
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # Get active wars with statistics
                    cur.execute("""
                        SELECT
                            w.war_id,
                            w.alliance_a_id,
                            w.alliance_b_id,
                            w.first_kill_at,
                            w.last_kill_at,
                            w.total_kills,
                            w.total_isk_destroyed,
                            w.duration_days,
                            w.status,
                            COALESCE(SUM(wds.kills_by_a), 0) as recent_kills_a,
                            COALESCE(SUM(wds.kills_by_b), 0) as recent_kills_b,
                            COALESCE(SUM(wds.isk_destroyed_by_a), 0) as recent_isk_a,
                            COALESCE(SUM(wds.isk_destroyed_by_b), 0) as recent_isk_b
                        FROM alliance_wars w
                        LEFT JOIN war_daily_stats wds ON wds.war_id = w.war_id
                            AND wds.date >= CURRENT_DATE - INTERVAL '%s days'
                        WHERE w.status IN ('active', 'dormant')
                          AND w.total_kills >= 5
                        GROUP BY w.war_id
                        ORDER BY w.total_kills DESC, w.total_isk_destroyed DESC
                        LIMIT %s
                    """, (days, limit))

                    wars = cur.fetchall()

                    if not wars:
                        return {"wars": [], "total_wars": 0}

                    war_data = []
                    for war in wars:
                        war_id, alliance_a, alliance_b, first_kill, last_kill, total_kills, total_isk, duration, status, \
                        _, _, _, _ = war

                        # Get alliance names
                        alliance_a_name = await self.get_alliance_name(alliance_a)
                        alliance_b_name = await self.get_alliance_name(alliance_b)

                        # Count actual ship losses
                        cur.execute("""
                            SELECT
                                COUNT(*) FILTER (WHERE k.victim_alliance_id = %s) as alliance_a_losses,
                                COUNT(*) FILTER (WHERE k.victim_alliance_id = %s) as alliance_b_losses,
                                COALESCE(SUM(k.ship_value) FILTER (WHERE k.victim_alliance_id = %s), 0) as alliance_a_isk_lost,
                                COALESCE(SUM(k.ship_value) FILTER (WHERE k.victim_alliance_id = %s), 0) as alliance_b_isk_lost
                            FROM killmails k
                            WHERE k.killmail_time >= NOW() - INTERVAL '%s days'
                              AND (
                                  (k.victim_alliance_id = %s AND EXISTS (
                                      SELECT 1 FROM killmail_attackers ka
                                      WHERE ka.killmail_id = k.killmail_id
                                      AND ka.alliance_id = %s
                                  ))
                                  OR
                                  (k.victim_alliance_id = %s AND EXISTS (
                                      SELECT 1 FROM killmail_attackers ka
                                      WHERE ka.killmail_id = k.killmail_id
                                      AND ka.alliance_id = %s
                                  ))
                              )
                        """, (alliance_a, alliance_b, alliance_a, alliance_b, days,
                              alliance_a, alliance_b, alliance_b, alliance_a))

                        actual_result = cur.fetchone()
                        actual_losses_a, actual_losses_b, actual_isk_lost_a, actual_isk_lost_b = actual_result

                        # Use actual counts
                        recent_kills_a = actual_losses_b
                        recent_kills_b = actual_losses_a
                        recent_isk_a = actual_isk_lost_b
                        recent_isk_b = actual_isk_lost_a

                        # Calculate metrics
                        kill_ratio_a = recent_kills_a / max(recent_kills_b, 1)
                        isk_efficiency_a = (recent_isk_a / (recent_isk_a + recent_isk_b)) * 100 if (recent_isk_a + recent_isk_b) > 0 else 50
                        isk_efficiency_b = 100 - isk_efficiency_a

                        # Determine winners
                        tactical_winner = "a" if kill_ratio_a > 1.2 else "b" if kill_ratio_a < 0.8 else "contested"
                        economic_winner = "a" if isk_efficiency_a > 60 else "b" if isk_efficiency_a < 40 else "contested"

                        if isk_efficiency_a > 55 or (isk_efficiency_a > 45 and kill_ratio_a > 1.5):
                            overall_winner = "a"
                        elif isk_efficiency_a < 45 or (isk_efficiency_a < 55 and kill_ratio_a < 0.67):
                            overall_winner = "b"
                        else:
                            overall_winner = "contested"

                        # Get system hotspots
                        cur.execute("""
                            SELECT
                                k.solar_system_id,
                                COUNT(*) as kill_count
                            FROM killmails k
                            WHERE k.killmail_time >= NOW() - INTERVAL '%s days'
                              AND (
                                  (k.victim_alliance_id = %s AND EXISTS (
                                      SELECT 1 FROM killmail_attackers ka
                                      WHERE ka.killmail_id = k.killmail_id
                                      AND ka.alliance_id = %s
                                  ))
                                  OR
                                  (k.victim_alliance_id = %s AND EXISTS (
                                      SELECT 1 FROM killmail_attackers ka
                                      WHERE ka.killmail_id = k.killmail_id
                                      AND ka.alliance_id = %s
                                  ))
                              )
                            GROUP BY k.solar_system_id
                            ORDER BY kill_count DESC
                            LIMIT 5
                        """, (days, alliance_a, alliance_b, alliance_b, alliance_a))

                        system_hotspots = []
                        for sys_id, kill_count in cur.fetchall():
                            sys_info = self.get_system_location_info(sys_id)
                            system_hotspots.append({
                                "system_id": sys_id,
                                "system_name": sys_info.get("system_name", f"System {sys_id}"),
                                "kills": kill_count,
                                "security": sys_info.get("security_status", 0.0),
                                "region_name": sys_info.get("region_name", "Unknown")
                            })

                        # Calculate war intensity score
                        isk_score = (total_isk / 1e9) * 0.6
                        kill_score = total_kills * 0.3
                        system_score = len(system_hotspots) * 0.1
                        war_score = isk_score + kill_score + system_score

                        war_data.append({
                            "war_id": war_id,
                            "alliance_a_id": alliance_a,
                            "alliance_a_name": alliance_a_name,
                            "alliance_b_id": alliance_b,
                            "alliance_b_name": alliance_b_name,
                            "kills_by_a": int(recent_kills_a),
                            "kills_by_b": int(recent_kills_b),
                            "isk_by_a": int(recent_isk_a),
                            "isk_by_b": int(recent_isk_b),
                            "total_kills": total_kills,
                            "total_isk": int(total_isk),
                            "duration_days": duration if duration else 0,
                            "status": status,
                            "kill_ratio_a": round(kill_ratio_a, 2),
                            "isk_efficiency_a": round(isk_efficiency_a, 1),
                            "isk_efficiency_b": round(isk_efficiency_b, 1),
                            "tactical_winner": tactical_winner,
                            "economic_winner": economic_winner,
                            "overall_winner": overall_winner,
                            "war_score": round(war_score, 2),
                            "system_hotspots": system_hotspots,
                            "first_kill_at": first_kill.isoformat() if first_kill else None,
                            "last_kill_at": last_kill.isoformat() if last_kill else None
                        })

                    return {
                        "wars": war_data,
                        "total_wars": len(war_data),
                        "analysis_period_days": days
                    }

        except Exception as e:
            print(f"Error getting alliance wars from PostgreSQL: {e}")
            return {"wars": [], "total_wars": 0, "error": str(e)}

    async def get_alliance_war_tracker(self, limit: int = 5) -> Dict:
        """
        Track active alliance wars with kill/death ratios and ISK efficiency.

        Uses PostgreSQL persistent storage for accurate historical data.

        Args:
            limit: Number of wars to return

        Returns:
            Dict with top alliance wars and their statistics
        """
        # Check cache first
        cache_key = f"report:alliance_wars:{limit}"
        try:
            cached = self.redis_client.get(cache_key)
            if cached:
                print(f"[CACHE HIT] Returning cached alliance wars report")
                return json.loads(cached)
        except Exception:
            pass

        # Get from PostgreSQL
        result = await self.get_alliance_war_tracker_postgres(limit=limit, days=7)

        # Cache for 7 hours
        try:
            self.redis_client.setex(cache_key, REPORT_CACHE_TTL, json.dumps(result))
            print(f"[CACHE] Cached alliance wars report for {REPORT_CACHE_TTL}s")
        except Exception:
            pass

        return result

    async def detect_coalitions(self, days: int = 7, min_fights_together: int = 5) -> Dict:
        """
        Self-learning coalition detection based on combat patterns.

        Alliances that frequently fight TOGETHER (co-attackers) are grouped into coalitions.
        Named after the largest alliance in each coalition.

        Args:
            days: How many days of data to analyze
            min_fights_together: Minimum shared kills to consider alliances allied

        Returns:
            Dict with detected coalitions and their aggregated stats
        """
        cache_key = f"coalitions:detected:{days}d"
        cached = self.redis_client.get(cache_key)
        if cached:
            return json.loads(cached)

        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # Find alliance pairs that fight TOGETHER
                    cur.execute("""
                        WITH recent_kills AS (
                            SELECT killmail_id
                            FROM killmails
                            WHERE killmail_time >= NOW() - INTERVAL '%s days'
                        )
                        SELECT
                            ka1.alliance_id as alliance_a,
                            ka2.alliance_id as alliance_b,
                            COUNT(DISTINCT ka1.killmail_id) as fights_together
                        FROM killmail_attackers ka1
                        JOIN killmail_attackers ka2
                            ON ka1.killmail_id = ka2.killmail_id
                            AND ka1.alliance_id < ka2.alliance_id
                        WHERE ka1.killmail_id IN (SELECT killmail_id FROM recent_kills)
                          AND ka1.alliance_id IS NOT NULL
                          AND ka2.alliance_id IS NOT NULL
                          AND ka1.alliance_id != ka2.alliance_id
                        GROUP BY ka1.alliance_id, ka2.alliance_id
                        HAVING COUNT(DISTINCT ka1.killmail_id) >= %s
                        ORDER BY fights_together DESC
                    """, (days, min_fights_together))

                    alliance_pairs = cur.fetchall()

                    # Get alliance activity stats
                    cur.execute("""
                        SELECT
                            alliance_id,
                            COUNT(*) as total_activity
                        FROM (
                            SELECT ka.alliance_id
                            FROM killmail_attackers ka
                            JOIN killmails k ON k.killmail_id = ka.killmail_id
                            WHERE k.killmail_time >= NOW() - INTERVAL '%s days'
                              AND ka.alliance_id IS NOT NULL
                            UNION ALL
                            SELECT k.victim_alliance_id as alliance_id
                            FROM killmails k
                            WHERE k.killmail_time >= NOW() - INTERVAL '%s days'
                              AND k.victim_alliance_id IS NOT NULL
                        ) combined
                        GROUP BY alliance_id
                        HAVING COUNT(*) >= 10
                        ORDER BY total_activity DESC
                    """, (days, days))

                    alliance_activity = {row[0]: row[1] for row in cur.fetchall()}

                    # Union-Find for clustering
                    parent = {}

                    def find(x):
                        if x not in parent:
                            parent[x] = x
                        if parent[x] != x:
                            parent[x] = find(parent[x])
                        return parent[x]

                    def union(x, y):
                        px, py = find(x), find(y)
                        if px != py:
                            if alliance_activity.get(px, 0) >= alliance_activity.get(py, 0):
                                parent[py] = px
                            else:
                                parent[px] = py

                    # Get conflicts for enemy detection
                    cur.execute("""
                        SELECT
                            ka.alliance_id as attacker_alliance,
                            k.victim_alliance_id as victim_alliance,
                            COUNT(*) as fights_against
                        FROM killmail_attackers ka
                        JOIN killmails k ON k.killmail_id = ka.killmail_id
                        WHERE k.killmail_time >= NOW() - INTERVAL '%s days'
                          AND ka.alliance_id IS NOT NULL
                          AND k.victim_alliance_id IS NOT NULL
                          AND ka.alliance_id != k.victim_alliance_id
                        GROUP BY ka.alliance_id, k.victim_alliance_id
                        HAVING COUNT(*) >= %s
                    """, (days, min_fights_together))

                    conflicts_raw = cur.fetchall()

                    conflict_map = {}
                    for attacker, victim, count in conflicts_raw:
                        pair = tuple(sorted([attacker, victim]))
                        conflict_map[pair] = conflict_map.get(pair, 0) + count

                    coop_map = {}
                    for alliance_a, alliance_b, fights_together in alliance_pairs:
                        pair = (alliance_a, alliance_b)
                        coop_map[pair] = fights_together

                    confirmed_enemies = set()
                    for pair, fights_against in conflict_map.items():
                        if fights_against >= 20:
                            confirmed_enemies.add(pair)

                    # Union alliances that are TRUE allies
                    for alliance_a, alliance_b, fights_together in alliance_pairs:
                        pair = tuple(sorted([alliance_a, alliance_b]))

                        if pair in confirmed_enemies:
                            continue

                        fights_against = conflict_map.get(pair, 0)
                        if fights_against > 0 and fights_together < fights_against * 5:
                            continue

                        activity_a = alliance_activity.get(alliance_a, 0)
                        activity_b = alliance_activity.get(alliance_b, 0)
                        min_activity = min(activity_a, activity_b)

                        is_significant = min_activity > 0 and fights_together >= min_activity * 0.10

                        if is_significant:
                            union(alliance_a, alliance_b)

                    # Group alliances by coalition root
                    coalitions_raw = {}
                    for alliance_id in alliance_activity.keys():
                        root = find(alliance_id)
                        if root not in coalitions_raw:
                            coalitions_raw[root] = []
                        coalitions_raw[root].append(alliance_id)

                    # Build final coalition data
                    coalitions = []
                    unaffiliated = []

                    for root, members in coalitions_raw.items():
                        if len(members) < 2:
                            unaffiliated.extend(members)
                            continue

                        members.sort(key=lambda x: alliance_activity.get(x, 0), reverse=True)
                        leader_name = await self.get_alliance_name(members[0])

                        member_ids = tuple(members[:50])
                        cur.execute("""
                            SELECT
                                COUNT(DISTINCT ka.killmail_id) as total_kills,
                                COALESCE(SUM(DISTINCT k.ship_value), 0) as isk_destroyed
                            FROM killmail_attackers ka
                            JOIN killmails k ON k.killmail_id = ka.killmail_id
                            WHERE k.killmail_time >= NOW() - INTERVAL '%s days'
                              AND ka.alliance_id IN %s
                        """, (days, member_ids))
                        kills_result = cur.fetchone()

                        cur.execute("""
                            SELECT
                                COUNT(*) as total_losses,
                                COALESCE(SUM(ship_value), 0) as isk_lost
                            FROM killmails
                            WHERE killmail_time >= NOW() - INTERVAL '%s days'
                              AND victim_alliance_id IN %s
                        """, (days, member_ids))
                        losses_result = cur.fetchone()

                        total_kills = kills_result[0] if kills_result else 0
                        isk_destroyed = int(kills_result[1]) if kills_result else 0
                        total_losses = losses_result[0] if losses_result else 0
                        isk_lost = int(losses_result[1]) if losses_result else 0

                        efficiency = (isk_destroyed / (isk_destroyed + isk_lost) * 100) if (isk_destroyed + isk_lost) > 0 else 50

                        member_names = []
                        for member_id in members[:10]:
                            name = await self.get_alliance_name(member_id)
                            member_names.append({
                                "alliance_id": member_id,
                                "name": name,
                                "activity": alliance_activity.get(member_id, 0)
                            })

                        coalitions.append({
                            "name": f"{leader_name} Coalition",
                            "leader_alliance_id": members[0],
                            "leader_name": leader_name,
                            "member_count": len(members),
                            "members": member_names,
                            "total_kills": total_kills,
                            "total_losses": total_losses,
                            "isk_destroyed": isk_destroyed,
                            "isk_lost": isk_lost,
                            "efficiency": round(efficiency, 1),
                            "total_activity": sum(alliance_activity.get(m, 0) for m in members)
                        })

                    coalitions.sort(key=lambda x: x['total_activity'], reverse=True)

                    # Build unaffiliated summary
                    unaffiliated.sort(key=lambda x: alliance_activity.get(x, 0), reverse=True)
                    unaffiliated_data = []
                    for alliance_id in unaffiliated[:10]:
                        name = await self.get_alliance_name(alliance_id)

                        cur.execute("""
                            SELECT COUNT(*) as kills
                            FROM killmail_attackers ka
                            JOIN killmails k ON k.killmail_id = ka.killmail_id
                            WHERE k.killmail_time >= NOW() - INTERVAL '%s days'
                              AND ka.alliance_id = %s
                        """, (days, alliance_id))
                        kills = cur.fetchone()[0]

                        cur.execute("""
                            SELECT COUNT(*) as losses, COALESCE(SUM(ship_value), 0) as isk_lost
                            FROM killmails
                            WHERE killmail_time >= NOW() - INTERVAL '%s days'
                              AND victim_alliance_id = %s
                        """, (days, alliance_id))
                        loss_result = cur.fetchone()

                        unaffiliated_data.append({
                            "alliance_id": alliance_id,
                            "name": name,
                            "kills": kills,
                            "losses": loss_result[0],
                            "isk_lost": int(loss_result[1]),
                            "activity": alliance_activity.get(alliance_id, 0)
                        })

                    result = {
                        "period_days": days,
                        "coalitions": coalitions[:5],
                        "unaffiliated": unaffiliated_data,
                        "total_coalitions_detected": len(coalitions),
                        "total_unaffiliated": len(unaffiliated)
                    }

                    self.redis_client.setex(cache_key, REPORT_CACHE_TTL, json.dumps(result))

                    return result

        except Exception as e:
            print(f"Error detecting coalitions: {e}")
            import traceback
            traceback.print_exc()
            return {
                "period_days": days,
                "coalitions": [],
                "unaffiliated": [],
                "error": str(e)
            }
