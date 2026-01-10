"""
Statistics and Analysis Module.

Provides query methods, danger level calculation, and gate camp detection.
"""

import json
from datetime import datetime
from typing import Dict, List, Tuple, Optional

import aiohttp

from src.database import get_db_connection


class StatisticsMixin:
    """Mixin providing statistics and analysis methods for ZKillboardLiveService."""

    def get_top_expensive_ships(self, system_id: int, limit: int = 5) -> List[Dict]:
        """
        Get top N most expensive ships destroyed in a system.

        Args:
            system_id: Solar system ID
            limit: Number of ships to return

        Returns:
            List of {ship_type_id, ship_name, value} dicts
        """
        # Get recent kills from Redis
        kill_ids = self.redis_client.zrevrange(
            f"kill:system:{system_id}:timeline",
            0,
            50
        )

        kills = []
        for kill_id in kill_ids[:20]:  # Check last 20
            kill_data = self.redis_client.get(f"kill:id:{kill_id}")
            if kill_data:
                kill = json.loads(kill_data)
                kills.append(kill)

        # Sort by value
        kills_sorted = sorted(kills, key=lambda x: x['ship_value'], reverse=True)[:limit]

        # Get ship names from DB
        result = []
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                for kill in kills_sorted:
                    cur.execute(
                        'SELECT "typeName" FROM "invTypes" WHERE "typeID" = %s',
                        (kill['ship_type_id'],)
                    )
                    row = cur.fetchone()
                    ship_name = row[0] if row else f"Ship {kill['ship_type_id']}"

                    result.append({
                        'ship_type_id': kill['ship_type_id'],
                        'ship_name': ship_name,
                        'value': kill['ship_value']
                    })

        return result

    def calculate_danger_level(self, security: float, kill_count: int, kill_rate: float, isk_destroyed: float) -> Tuple[str, int]:
        """
        Calculate intelligent danger level based on multiple factors.

        Args:
            security: System security status
            kill_count: Number of kills in window
            kill_rate: Kills per minute
            isk_destroyed: Total ISK destroyed

        Returns:
            Tuple of (level_emoji, score) where:
            - level_emoji: "🟢 LOW", "🟡 MEDIUM", "🟠 HIGH", "🔴 EXTREME"
            - score: 0-12 points
        """
        # Factor 1: Security Status (0-2 points)
        if security >= 0.5:
            sec_score = 2
        elif security > 0:
            sec_score = 1
        else:
            sec_score = 0

        # Factor 2: Kill Count (0-3 points)
        if kill_count >= 10:
            kc_score = 3
        elif kill_count >= 7:
            kc_score = 2
        elif kill_count >= 5:
            kc_score = 1
        else:
            kc_score = 0

        # Factor 3: Kill Rate (0-3 points)
        if kill_rate >= 2.0:
            kr_score = 3
        elif kill_rate >= 1.5:
            kr_score = 2
        elif kill_rate >= 1.0:
            kr_score = 1
        else:
            kr_score = 0

        # Factor 4: ISK Value (0-3 points)
        if isk_destroyed >= 50_000_000:
            isk_score = 3
        elif isk_destroyed >= 20_000_000:
            isk_score = 2
        elif isk_destroyed >= 10_000_000:
            isk_score = 1
        else:
            isk_score = 0

        # Total score
        total_score = sec_score + kc_score + kr_score + isk_score

        # Map to danger level
        if total_score >= 10:
            return "🔴 EXTREME", total_score
        elif total_score >= 7:
            return "🟠 HIGH", total_score
        elif total_score >= 4:
            return "🟡 MEDIUM", total_score
        else:
            return "🟢 LOW", total_score

    def detect_gate_camp(self, system_id: int) -> Tuple[bool, float, List[str]]:
        """
        Detect if kills in a system indicate a gate camp.

        Args:
            system_id: Solar system ID

        Returns:
            Tuple of (is_camp, confidence, indicators)
        """
        # Get recent kills
        kill_ids = self.redis_client.zrevrange(
            f"kill:system:{system_id}:timeline",
            0,
            50
        )

        kills = []
        for kill_id in kill_ids[:20]:
            kill_data = self.redis_client.get(f"kill:id:{kill_id}")
            if kill_data:
                kills.append(json.loads(kill_data))

        if len(kills) < 3:
            return False, 0.0, []

        score = 0
        max_score = 4
        indicators = []

        # Indicator 1: Attacker Pattern
        avg_attackers = sum(k['attacker_count'] for k in kills) / len(kills)
        if avg_attackers >= 5:
            score += 1
            indicators.append("Multi-attacker pattern")
        elif avg_attackers >= 2:
            score += 0.5
            indicators.append("Small gang")

        # Indicator 2: Ship Types (check for Interdictors)
        ship_types = {}
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                for kill in kills:
                    cur.execute(
                        'SELECT g."groupName" FROM "invTypes" t '
                        'JOIN "invGroups" g ON t."groupID" = g."groupID" '
                        'WHERE t."typeID" = %s',
                        (kill['ship_type_id'],)
                    )
                    row = cur.fetchone()
                    if row:
                        group = row[0]
                        ship_types[group] = ship_types.get(group, 0) + 1

        interdictors = ship_types.get("Interdictor", 0)
        if interdictors >= 2:
            score += 1
            indicators.append(f"{interdictors}x Interdictors (Bubble camp)")
        elif ship_types.get("Frigate", 0) >= 5:
            score += 0.5
            indicators.append("Multiple frigates")

        # Indicator 3: Kill Frequency
        kill_times = []
        for kill in kills:
            try:
                dt = datetime.fromisoformat(kill['killmail_time'].replace('Z', '+00:00'))
                kill_times.append(dt.timestamp())
            except:
                pass

        if len(kill_times) >= 2:
            kill_times.sort()
            intervals = [kill_times[i+1] - kill_times[i] for i in range(len(kill_times)-1)]
            avg_interval = sum(intervals) / len(intervals)

            if avg_interval <= 180:  # <= 3 minutes
                score += 1
                indicators.append(f"Regular kills every {avg_interval/60:.1f}min")
            elif avg_interval <= 600:  # <= 10 minutes
                score += 0.5

        # Indicator 4: Victim Diversity
        unique_corps = len(set(k['victim_corporation_id'] for k in kills if k['victim_corporation_id']))
        if unique_corps >= 8:
            score += 1
            indicators.append("Diverse victims (random traffic)")
        elif unique_corps >= 4:
            score += 0.5
            indicators.append("Multiple victims")

        confidence = (score / max_score) * 100
        is_camp = score >= 2.0  # 50%+ confidence

        return is_camp, confidence, indicators

    async def get_involved_parties(self, system_id: int, limit: int = 5) -> Dict:
        """
        Get involved corporations and alliances from ongoing battle or recent kills.

        If an active battle exists in this system, returns cumulative battle statistics.
        Otherwise, falls back to recent Redis kills.

        Args:
            system_id: Solar system ID
            limit: Max parties to return per side

        Returns:
            Dict with attacker/victim corps and alliances with names
        """
        # Check for active battle in this system
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT battle_id
                        FROM battles
                        WHERE solar_system_id = %s
                          AND status = 'active'
                          AND last_kill_at > NOW() - INTERVAL '30 minutes'
                        ORDER BY battle_id DESC
                        LIMIT 1
                    """, (system_id,))

                    battle_row = cur.fetchone()
                    if battle_row:
                        battle_id = battle_row[0]

                        # Get cumulative battle statistics from battle_participants
                        # Attackers: entities with kills > 0
                        cur.execute("""
                            SELECT
                                alliance_id,
                                SUM(kills) as total_kills
                            FROM battle_participants
                            WHERE battle_id = %s
                              AND alliance_id IS NOT NULL
                              AND kills > 0
                            GROUP BY alliance_id
                            ORDER BY total_kills DESC
                            LIMIT %s
                        """, (battle_id, limit))

                        attacker_alliances = [(row[0], row[1]) for row in cur.fetchall()]

                        # Victims: entities with losses > 0
                        cur.execute("""
                            SELECT
                                alliance_id,
                                SUM(losses) as total_losses
                            FROM battle_participants
                            WHERE battle_id = %s
                              AND alliance_id IS NOT NULL
                              AND losses > 0
                            GROUP BY alliance_id
                            ORDER BY total_losses DESC
                            LIMIT %s
                        """, (battle_id, limit))

                        victim_alliances = [(row[0], row[1]) for row in cur.fetchall()]

                        # Get corps if alliances are limited
                        cur.execute("""
                            SELECT
                                corporation_id,
                                SUM(kills) as total_kills
                            FROM battle_participants
                            WHERE battle_id = %s
                              AND corporation_id IS NOT NULL
                              AND alliance_id IS NULL
                              AND kills > 0
                            GROUP BY corporation_id
                            ORDER BY total_kills DESC
                            LIMIT %s
                        """, (battle_id, limit))

                        attacker_corps = [(row[0], row[1]) for row in cur.fetchall()]

                        cur.execute("""
                            SELECT
                                corporation_id,
                                SUM(losses) as total_losses
                            FROM battle_participants
                            WHERE battle_id = %s
                              AND corporation_id IS NOT NULL
                              AND alliance_id IS NULL
                              AND losses > 0
                            GROUP BY corporation_id
                            ORDER BY total_losses DESC
                            LIMIT %s
                        """, (battle_id, limit))

                        victim_corps = [(row[0], row[1]) for row in cur.fetchall()]

                        # Use cumulative battle data
                        top_attacker_corps = attacker_corps
                        top_attacker_alliances = attacker_alliances
                        top_victim_corps = victim_corps
                        top_victim_alliances = victim_alliances

                    else:
                        # No active battle, fall back to Redis
                        raise ValueError("No active battle")
        except:
            # Fall back to Redis-based aggregation
            kill_ids = self.redis_client.zrevrange(
                f"kill:system:{system_id}:timeline",
                0,
                50
            )

            kills = []
            for kill_id in kill_ids[:20]:
                kill_data = self.redis_client.get(f"kill:id:{kill_id}")
                if kill_data:
                    kills.append(json.loads(kill_data))

            if not kills:
                return {"attackers": {"corps": [], "alliances": []}, "victims": {"corps": [], "alliances": []}}

            # Aggregate attacker corps and alliances
            attacker_corps = {}
            attacker_alliances = {}
            victim_corps = {}
            victim_alliances = {}

            for kill in kills:
                # Count attacker corps
                for corp_id in kill.get('attacker_corporations', []):
                    attacker_corps[corp_id] = attacker_corps.get(corp_id, 0) + 1

                # Count attacker alliances
                for alliance_id in kill.get('attacker_alliances', []):
                    attacker_alliances[alliance_id] = attacker_alliances.get(alliance_id, 0) + 1

                # Count victim corp
                victim_corp = kill.get('victim_corporation_id')
                if victim_corp:
                    victim_corps[victim_corp] = victim_corps.get(victim_corp, 0) + 1

                # Count victim alliance
                victim_alliance = kill.get('victim_alliance_id')
                if victim_alliance:
                    victim_alliances[victim_alliance] = victim_alliances.get(victim_alliance, 0) + 1

            # Get top corps/alliances by count
            top_attacker_corps = sorted(attacker_corps.items(), key=lambda x: x[1], reverse=True)[:limit]
            top_attacker_alliances = sorted(attacker_alliances.items(), key=lambda x: x[1], reverse=True)[:limit]
            top_victim_corps = sorted(victim_corps.items(), key=lambda x: x[1], reverse=True)[:limit]
            top_victim_alliances = sorted(victim_alliances.items(), key=lambda x: x[1], reverse=True)[:limit]

        # Fetch names from ESI
        session = await self._get_session()

        async def get_corp_name(corp_id: int) -> str:
            try:
                url = f"https://esi.evetech.net/latest/corporations/{corp_id}/"
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("name", f"Corp {corp_id}")
            except:
                pass
            return f"Corp {corp_id}"

        async def get_alliance_name(alliance_id: int) -> str:
            try:
                url = f"https://esi.evetech.net/latest/alliances/{alliance_id}/"
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("name", f"Alliance {alliance_id}")
            except:
                pass
            return f"Alliance {alliance_id}"

        # Fetch all names concurrently
        attacker_corps_with_names = []
        for corp_id, count in top_attacker_corps:
            name = await get_corp_name(corp_id)
            attacker_corps_with_names.append({"id": corp_id, "name": name, "kills": count})

        attacker_alliances_with_names = []
        for alliance_id, count in top_attacker_alliances:
            name = await get_alliance_name(alliance_id)
            attacker_alliances_with_names.append({"id": alliance_id, "name": name, "kills": count})

        victim_corps_with_names = []
        for corp_id, count in top_victim_corps:
            name = await get_corp_name(corp_id)
            victim_corps_with_names.append({"id": corp_id, "name": name, "kills": count})

        victim_alliances_with_names = []
        for alliance_id, count in top_victim_alliances:
            name = await get_alliance_name(alliance_id)
            victim_alliances_with_names.append({"id": alliance_id, "name": name, "kills": count})

        return {
            "attackers": {
                "corps": attacker_corps_with_names,
                "alliances": attacker_alliances_with_names
            },
            "victims": {
                "corps": victim_corps_with_names,
                "alliances": victim_alliances_with_names
            }
        }

    async def create_enhanced_alert(self, hotspot: Dict):
        """
        Create enhanced Discord alert with:
        - Intelligent danger level
        - Top 5 expensive ships
        - Gate camp detection
        - Compact emoji formatting
        """
        system_id = hotspot['solar_system_id']
        region_id = hotspot['region_id']
        kill_count = hotspot['kill_count']
        window_minutes = hotspot['window_seconds'] // 60

        # Get system info from DB
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    'SELECT ms."solarSystemName", mr."regionName", ms.security '
                    'FROM "mapSolarSystems" ms '
                    'JOIN "mapRegions" mr ON ms."regionID" = mr."regionID" '
                    'WHERE ms."solarSystemID" = %s',
                    (system_id,)
                )
                result = cur.fetchone()
                if not result:
                    return None

                system_name, region_name, security = result

        # Get top 5 expensive ships
        top_ships = self.get_top_expensive_ships(system_id, limit=5)

        # Calculate totals
        total_value = sum(ship['value'] for ship in top_ships)
        avg_value = total_value / len(top_ships) if top_ships else 0
        kill_rate = kill_count / window_minutes

        # Calculate intelligent danger level
        danger_level, danger_score = self.calculate_danger_level(
            security, kill_count, kill_rate, total_value
        )

        # Detect gate camp
        is_camp, camp_confidence, camp_indicators = self.detect_gate_camp(system_id)

        # Get involved parties
        involved = await self.get_involved_parties(system_id, limit=3)

        # Check for active battle to show cumulative stats
        battle_info = None
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT battle_id, total_kills, total_isk_destroyed
                        FROM battles
                        WHERE solar_system_id = %s
                          AND status = 'active'
                          AND last_kill_at > NOW() - INTERVAL '30 minutes'
                        ORDER BY battle_id DESC
                        LIMIT 1
                    """, (system_id,))
                    row = cur.fetchone()
                    if row:
                        battle_info = {
                            'battle_id': row[0],
                            'total_kills': row[1],
                            'total_isk': row[2]
                        }
        except:
            pass

        # Build alert message
        activity_line = f"{kill_count} kills in {window_minutes} minutes"
        if battle_info:
            battle_isk_b = battle_info['total_isk'] / 1_000_000_000
            activity_line += f" (Battle: {battle_info['total_kills']} kills, {battle_isk_b:.1f}B ISK)"

        alert = f"""⚠️ **Combat Hotspot Detected**

📍 **Location:** {system_name} ({security:.1f}) - {region_name}
🔥 **Activity:** {activity_line}
💰 **Total Value:** {total_value/1_000_000:.1f}M ISK (avg {avg_value/1_000_000:.1f}M/kill)
🎯 **Danger Level:** {danger_level} ({danger_score}/12 pts)
"""

        # Add gate camp detection
        if is_camp:
            pattern_desc = "Bubble Camp" if any("Interdictor" in ind for ind in camp_indicators) else "Gate Camp"
            alert += f"🚨 **Pattern:** {pattern_desc} ({camp_confidence:.0f}% confidence)\n"
            if camp_indicators:
                alert += f"   Evidence: {', '.join(camp_indicators[:2])}\n"

        # Add involved parties
        if involved['attackers']['alliances'] or involved['attackers']['corps']:
            alert += "\n**⚔️ Attacking Forces:**\n"
            if involved['attackers']['alliances']:
                for alliance in involved['attackers']['alliances']:
                    alert += f"   • {alliance['name']} ({alliance['kills']} kills)\n"
            # Show corps if no alliances or to supplement alliance data
            if involved['attackers']['corps'] and not involved['attackers']['alliances']:
                for corp in involved['attackers']['corps'][:3]:
                    alert += f"   • {corp['name']} ({corp['kills']} kills)\n"

        if involved['victims']['alliances'] or involved['victims']['corps']:
            alert += "\n**💀 Primary Victims:**\n"
            if involved['victims']['alliances']:
                for alliance in involved['victims']['alliances'][:3]:
                    alert += f"   • {alliance['name']} ({alliance['kills']} losses)\n"
            # Show corps if no alliances or to supplement alliance data
            if involved['victims']['corps'] and not involved['victims']['alliances']:
                for corp in involved['victims']['corps'][:3]:
                    alert += f"   • {corp['name']} ({corp['kills']} losses)\n"

        # Add top 5 ships
        if top_ships:
            alert += "\n**💀 Top 5 Most Expensive Losses:**\n"
            for i, ship in enumerate(top_ships, 1):
                alert += f"`{i}.` {ship['ship_name']:25} - **{ship['value']/1_000_000:>6.1f}M** ISK\n"

        # Add recommendation
        if danger_score >= 10:
            recommendation = "🛑 AVOID"
        elif danger_score >= 7:
            recommendation = "⚠️ HIGH ALERT"
        elif security < 0.5:
            recommendation = "⚠️ USE CAUTION"
        else:
            recommendation = "✅ MONITOR"

        alert += f"\n{recommendation} - Active combat zone"

        return alert
