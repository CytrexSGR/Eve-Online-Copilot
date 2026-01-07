"""
zKillboard Live Service - Real-time Killmail Processing

Integrates with zKillboard RedisQ for live killmail streaming.
Provides real-time combat intelligence and hotspot detection.

Features:
- RedisQ pull-based killmail streaming
- Redis hot storage (24h TTL)
- Hotspot detection (kill spikes)
- Fitting analysis for war profiteering
- Discord/Telegram alert integration
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict, deque
import aiohttp
import redis
from dataclasses import dataclass, asdict

from src.database import get_db_connection
from config import DISCORD_WEBHOOK_URL, WAR_DISCORD_ENABLED
from src.telegram_service import telegram_service


# Redis Configuration
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 0
REDIS_TTL = 86400  # 24 hours

# zKillboard Configuration
ZKILL_API_URL = "https://zkillboard.com/api/kills/"
ZKILL_USER_AGENT = "EVE-CoPilot/1.0 (Live Combat Intelligence)"
ZKILL_REQUEST_TIMEOUT = 10  # seconds
ZKILL_POLL_INTERVAL = 10  # Poll every 10 seconds

# ESI Configuration
ESI_KILLMAIL_URL = "https://esi.evetech.net/latest/killmails/{killmail_id}/{hash}/"
ESI_USER_AGENT = "EVE-CoPilot/1.0"

# Hotspot Detection Configuration
HOTSPOT_WINDOW_SECONDS = 300  # 5 minutes
HOTSPOT_THRESHOLD_KILLS = 5   # 5+ kills in 5min = hotspot
HOTSPOT_ALERT_COOLDOWN = 600  # 10 minutes between alerts for same system


@dataclass
class LiveKillmail:
    """Structured killmail data"""
    killmail_id: int
    killmail_time: str
    solar_system_id: int
    region_id: int
    ship_type_id: int
    ship_value: float
    victim_character_id: Optional[int]
    victim_corporation_id: Optional[int]
    victim_alliance_id: Optional[int]
    attacker_count: int
    is_solo: bool
    is_npc: bool
    destroyed_items: List[Dict]  # Items that were destroyed (market demand)
    dropped_items: List[Dict]    # Items that dropped (no market demand)
    attacker_corporations: List[int]  # Corp IDs of attackers
    attacker_alliances: List[int]     # Alliance IDs of attackers


class ZKillboardLiveService:
    """Service for processing live killmail data from zKillboard RedisQ"""

    def __init__(self):
        self.redis_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            decode_responses=True
        )
        self.session: Optional[aiohttp.ClientSession] = None
        self.running = False

        # Track processed killmail IDs to avoid duplicates
        self.processed_kills: set = set()

        # In-memory hotspot tracking (system_id -> deque of timestamps)
        self.kill_timestamps: Dict[int, deque] = defaultdict(lambda: deque(maxlen=100))

        # Track when alerts were last sent per system (system_id -> timestamp)
        self.last_alert_sent: Dict[int, float] = {}

        # System -> Region mapping cache
        self.system_region_map: Dict[int, int] = {}
        self._load_system_region_map()

    def _load_system_region_map(self):
        """Load solar_system_id -> region_id mapping from DB"""
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT solar_system_id, region_id FROM system_region_map")
                self.system_region_map = {row[0]: row[1] for row in cur.fetchall()}

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                headers={"User-Agent": ZKILL_USER_AGENT}
            )
        return self.session

    async def fetch_recent_kills(self) -> List[Dict]:
        """
        Fetch recent killmails from zkillboard API.

        Returns list of zkillboard kill entries (killmail_id + hash).
        Full killmail data must be fetched from ESI.
        """
        session = await self._get_session()

        try:
            async with session.get(
                ZKILL_API_URL,
                headers={"User-Agent": ZKILL_USER_AGENT},
                timeout=aiohttp.ClientTimeout(total=ZKILL_REQUEST_TIMEOUT)
            ) as response:
                if response.status == 200:
                    kills = await response.json()
                    return kills if isinstance(kills, list) else []

                return []

        except Exception as e:
            print(f"Error fetching from zkillboard API: {e}")
            return []

    async def fetch_killmail_from_esi(self, killmail_id: int, hash_str: str) -> Optional[Dict]:
        """
        Fetch full killmail data from ESI.

        Args:
            killmail_id: Killmail ID
            hash_str: zkillboard hash for this killmail

        Returns:
            Full killmail dict or None if failed
        """
        session = await self._get_session()
        url = ESI_KILLMAIL_URL.format(killmail_id=killmail_id, hash=hash_str)

        try:
            async with session.get(
                url,
                headers={"User-Agent": ESI_USER_AGENT},
                timeout=aiohttp.ClientTimeout(total=ZKILL_REQUEST_TIMEOUT)
            ) as response:
                if response.status == 200:
                    return await response.json()

                return None

        except Exception as e:
            print(f"Error fetching killmail {killmail_id} from ESI: {e}")
            return None

    def parse_killmail(self, killmail: Dict, zkb: Dict) -> Optional[LiveKillmail]:
        """
        Parse ESI killmail + zkillboard data into structured LiveKillmail.

        Args:
            killmail: ESI killmail dict
            zkb: zkillboard metadata dict

        Returns:
            LiveKillmail object or None if invalid
        """
        try:

            # Extract core data
            killmail_id = killmail.get("killmail_id")
            solar_system_id = killmail.get("solar_system_id")
            killmail_time = killmail.get("killmail_time")

            if not all([killmail_id, solar_system_id, killmail_time]):
                return None

            # Get region from our mapping
            region_id = self.system_region_map.get(solar_system_id)
            if not region_id:
                # Skip wormhole systems and unknown systems
                return None

            # Victim data
            victim = killmail.get("victim", {})
            ship_type_id = victim.get("ship_type_id")

            if not ship_type_id:
                return None

            # Attacker analysis
            attackers = killmail.get("attackers", [])
            attacker_count = len(attackers)
            is_solo = attacker_count == 1
            is_npc = zkb.get("npc", False)

            # Extract attacker corps and alliances
            attacker_corporations = []
            attacker_alliances = []
            for attacker in attackers:
                corp_id = attacker.get("corporation_id")
                if corp_id:
                    attacker_corporations.append(corp_id)
                alliance_id = attacker.get("alliance_id")
                if alliance_id:
                    attacker_alliances.append(alliance_id)

            # Item segregation: destroyed vs dropped
            items = victim.get("items", [])
            destroyed_items = []
            dropped_items = []

            for item in items:
                item_type_id = item.get("item_type_id")
                qty_destroyed = item.get("quantity_destroyed", 0)
                qty_dropped = item.get("quantity_dropped", 0)

                if item_type_id:
                    if qty_destroyed > 0:
                        destroyed_items.append({
                            "item_type_id": item_type_id,
                            "quantity": qty_destroyed
                        })
                    if qty_dropped > 0:
                        dropped_items.append({
                            "item_type_id": item_type_id,
                            "quantity": qty_dropped
                        })

            return LiveKillmail(
                killmail_id=killmail_id,
                killmail_time=killmail_time,
                solar_system_id=solar_system_id,
                region_id=region_id,
                ship_type_id=ship_type_id,
                ship_value=zkb.get("totalValue", 0.0),
                victim_character_id=victim.get("character_id"),
                victim_corporation_id=victim.get("corporation_id"),
                victim_alliance_id=victim.get("alliance_id"),
                attacker_count=attacker_count,
                is_solo=is_solo,
                is_npc=is_npc,
                destroyed_items=destroyed_items,
                dropped_items=dropped_items,
                attacker_corporations=attacker_corporations,
                attacker_alliances=attacker_alliances
            )

        except Exception as e:
            print(f"Error parsing killmail: {e}")
            return None

    def store_persistent_kill(self, kill: LiveKillmail, zkb_data: Dict, esi_killmail: Dict):
        """
        Store killmail permanently in PostgreSQL.

        Writes to:
        - killmails table (core data)
        - killmail_items table (destroyed/dropped items)
        - killmail_attackers table (attacker details)

        Args:
            kill: Parsed killmail data
            zkb_data: zkillboard metadata (points, npc, awox flags)
            esi_killmail: Full ESI killmail data (for attacker details)
        """
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # Determine if victim ship is a capital
                    is_capital = self._is_capital_ship(kill.ship_type_id)

                    # Find final blow attacker
                    final_blow_char_id = None
                    final_blow_corp_id = None
                    final_blow_alliance_id = None
                    attackers = esi_killmail.get("attackers", [])
                    for attacker in attackers:
                        if attacker.get("final_blow", False):
                            final_blow_char_id = attacker.get("character_id")
                            final_blow_corp_id = attacker.get("corporation_id")
                            final_blow_alliance_id = attacker.get("alliance_id")
                            break

                    # 1. Insert main killmail record
                    cur.execute("""
                        INSERT INTO killmails (
                            killmail_id, killmail_time, solar_system_id, region_id,
                            ship_type_id, ship_value,
                            victim_character_id, victim_corporation_id, victim_alliance_id,
                            attacker_count,
                            final_blow_character_id, final_blow_corporation_id, final_blow_alliance_id,
                            is_solo, is_npc, is_capital,
                            zkb_points, zkb_npc, zkb_awox,
                            processed_at
                        ) VALUES (
                            %s, %s, %s, %s,
                            %s, %s,
                            %s, %s, %s,
                            %s,
                            %s, %s, %s,
                            %s, %s, %s,
                            %s, %s, %s,
                            CURRENT_TIMESTAMP
                        )
                        ON CONFLICT (killmail_id) DO NOTHING
                    """, (
                        kill.killmail_id,
                        kill.killmail_time,
                        kill.solar_system_id,
                        kill.region_id,
                        kill.ship_type_id,
                        int(kill.ship_value),
                        kill.victim_character_id,
                        kill.victim_corporation_id,
                        kill.victim_alliance_id,
                        kill.attacker_count,
                        final_blow_char_id,
                        final_blow_corp_id,
                        final_blow_alliance_id,
                        kill.is_solo,
                        kill.is_npc,
                        is_capital,
                        zkb_data.get("points"),
                        zkb_data.get("npc", False),
                        zkb_data.get("awox", False)
                    ))

                    # 2. Insert destroyed items
                    for item in kill.destroyed_items:
                        cur.execute("""
                            INSERT INTO killmail_items (
                                killmail_id, item_type_id, quantity, was_destroyed
                            ) VALUES (%s, %s, %s, %s)
                        """, (
                            kill.killmail_id,
                            item['item_type_id'],
                            item['quantity'],
                            True
                        ))

                    # 3. Insert dropped items
                    for item in kill.dropped_items:
                        cur.execute("""
                            INSERT INTO killmail_items (
                                killmail_id, item_type_id, quantity, was_destroyed
                            ) VALUES (%s, %s, %s, %s)
                        """, (
                            kill.killmail_id,
                            item['item_type_id'],
                            item['quantity'],
                            False
                        ))

                    # 4. Insert attacker details
                    for attacker in attackers:
                        cur.execute("""
                            INSERT INTO killmail_attackers (
                                killmail_id,
                                character_id,
                                corporation_id,
                                alliance_id,
                                ship_type_id,
                                weapon_type_id,
                                damage_done,
                                is_final_blow
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            kill.killmail_id,
                            attacker.get("character_id"),
                            attacker.get("corporation_id"),
                            attacker.get("alliance_id"),
                            attacker.get("ship_type_id"),
                            attacker.get("weapon_type_id"),
                            attacker.get("damage_done", 0),
                            attacker.get("final_blow", False)
                        ))

                    conn.commit()

        except Exception as e:
            print(f"Error storing killmail {kill.killmail_id} to PostgreSQL: {e}")

    def _is_capital_ship(self, ship_type_id: int) -> bool:
        """
        Check if a ship is a capital ship.

        Capital ship groups: Titan, Supercarrier, Carrier, Dreadnought, Force Auxiliary, Rorqual
        """
        capital_groups = [30, 659, 547, 485, 1538, 941]  # Group IDs for capital ships
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        'SELECT "groupID" FROM "invTypes" WHERE "typeID" = %s',
                        (ship_type_id,)
                    )
                    result = cur.fetchone()
                    if result:
                        group_id = result[0]
                        return group_id in capital_groups
        except Exception:
            pass
        return False

    def _update_existing_battle(self, kill: LiveKillmail) -> Optional[int]:
        """
        Update an existing active battle (if one exists) without creating a new one.

        This is used for kills that don't trigger hotspot detection but occur
        in systems with active battles.

        Args:
            kill: LiveKillmail to add to existing battle

        Returns:
            battle_id if battle was updated, None if no active battle exists
        """
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # Check for active battle
                    cur.execute("""
                        SELECT battle_id
                        FROM battles
                        WHERE solar_system_id = %s
                          AND status = 'active'
                          AND last_kill_at > NOW() - INTERVAL '30 minutes'
                        ORDER BY battle_id DESC
                        LIMIT 1
                    """, (kill.solar_system_id,))

                    result = cur.fetchone()

                    if result:
                        battle_id = result[0]
                        is_capital = self._is_capital_ship(kill.ship_type_id)

                        cur.execute("""
                            UPDATE battles
                            SET last_kill_at = CURRENT_TIMESTAMP,
                                total_kills = total_kills + 1,
                                total_isk_destroyed = total_isk_destroyed + %s,
                                capital_kills = capital_kills + %s
                            WHERE battle_id = %s
                        """, (
                            int(kill.ship_value),
                            1 if is_capital else 0,
                            battle_id
                        ))

                        conn.commit()
                        return battle_id

                    return None

        except Exception as e:
            print(f"Error updating existing battle: {e}")
            return None

    def create_or_update_battle(self, kill: LiveKillmail) -> Optional[int]:
        """
        Create a new battle or update existing battle in a system.

        A battle is a sustained combat engagement in a single system.
        Battles are created when hotspots are detected and updated with each kill.

        Args:
            kill: LiveKillmail that triggered the battle detection

        Returns:
            battle_id if battle was created/updated, None otherwise
        """
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # Check if there's an active battle in this system
                    # Battle is considered active if last kill was within 30 minutes
                    cur.execute("""
                        SELECT battle_id, total_kills, total_isk_destroyed, capital_kills
                        FROM battles
                        WHERE solar_system_id = %s
                          AND status = 'active'
                          AND last_kill_at > NOW() - INTERVAL '30 minutes'
                        ORDER BY battle_id DESC
                        LIMIT 1
                    """, (kill.solar_system_id,))

                    result = cur.fetchone()

                    if result:
                        # Update existing battle
                        battle_id, total_kills, total_isk, capital_kills = result
                        is_capital = self._is_capital_ship(kill.ship_type_id)

                        print(f"[BATTLE] Updating battle {battle_id} in system {kill.solar_system_id} (was {total_kills} kills)")

                        cur.execute("""
                            UPDATE battles
                            SET last_kill_at = CURRENT_TIMESTAMP,
                                total_kills = total_kills + 1,
                                total_isk_destroyed = total_isk_destroyed + %s,
                                capital_kills = capital_kills + %s
                            WHERE battle_id = %s
                        """, (
                            int(kill.ship_value),
                            1 if is_capital else 0,
                            battle_id
                        ))

                        conn.commit()
                        new_kill_count = total_kills + 1
                        print(f"[BATTLE] Battle {battle_id} updated to {new_kill_count} kills")

                        # Check if milestone reached
                        asyncio.create_task(self.check_and_send_milestone_alert(battle_id, new_kill_count, kill.solar_system_id))

                        return battle_id
                    else:
                        # Create new battle
                        is_capital = self._is_capital_ship(kill.ship_type_id)

                        print(f"[BATTLE] Creating new battle in system {kill.solar_system_id}")

                        cur.execute("""
                            INSERT INTO battles (
                                solar_system_id,
                                region_id,
                                started_at,
                                last_kill_at,
                                total_kills,
                                total_isk_destroyed,
                                capital_kills,
                                status
                            ) VALUES (
                                %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, %s, %s, %s, 'active'
                            )
                            RETURNING battle_id
                        """, (
                            kill.solar_system_id,
                            kill.region_id,
                            1,
                            int(kill.ship_value),
                            1 if is_capital else 0
                        ))

                        battle_id = cur.fetchone()[0]
                        conn.commit()
                        print(f"[BATTLE] Battle {battle_id} created in system {kill.solar_system_id}")

                        # Send initial battle alert
                        asyncio.create_task(self.send_initial_battle_alert(battle_id, kill.solar_system_id))

                        return battle_id

        except Exception as e:
            print(f"Error creating/updating battle: {e}")
            return None

    async def send_initial_battle_alert(self, battle_id: int, system_id: int):
        """
        Send initial "New Battle" alert when battle starts.

        Args:
            battle_id: Battle ID
            system_id: Solar system ID
        """
        try:
            # Get battle and system info
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT
                            b.total_kills,
                            b.total_isk_destroyed,
                            ms."solarSystemName",
                            mr."regionName",
                            ms.security,
                            b.initial_alert_sent
                        FROM battles b
                        JOIN "mapSolarSystems" ms ON ms."solarSystemID" = b.solar_system_id
                        JOIN "mapRegions" mr ON mr."regionID" = ms."regionID"
                        WHERE b.battle_id = %s
                    """, (battle_id,))

                    row = cur.fetchone()
                    if not row or row[5]:  # Skip if alert already sent
                        return

                    kills, isk_destroyed, system_name, region_name, security, _ = row

                    # Create initial alert message
                    alert_msg = f"""⚠️ **NEW BATTLE DETECTED**

📍 **Location:** {system_name} ({security:.1f}) - {region_name}
🆕 **Status:** Battle just started
💀 **Current:** {kills} kills, {isk_destroyed / 1_000_000:.1f}M ISK

⚔️ Combat has begun - monitoring engagement"""

                    # Send to Telegram
                    message_id = await telegram_service.send_alert(alert_msg)
                    if message_id:
                        # Update battle with message_id
                        cur.execute("""
                            UPDATE battles
                            SET telegram_message_id = %s,
                                initial_alert_sent = TRUE,
                                last_milestone_notified = 0
                            WHERE battle_id = %s
                        """, (message_id, battle_id))
                        conn.commit()
                        print(f"[ALERT] Initial battle alert sent for battle {battle_id} (message_id: {message_id})")

        except Exception as e:
            print(f"Error sending initial battle alert: {e}")

    async def check_and_send_milestone_alert(self, battle_id: int, current_kills: int, system_id: int):
        """
        Check if battle reached a milestone and send alert if needed.

        Milestones: 10, 25, 50, 100 kills

        Args:
            battle_id: Battle ID
            current_kills: Current total kill count
            system_id: Solar system ID
        """
        try:
            # Define milestones
            MILESTONES = [10, 25, 50, 100, 200, 500]

            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT
                            last_milestone_notified,
                            telegram_message_id,
                            total_isk_destroyed
                        FROM battles
                        WHERE battle_id = %s
                    """, (battle_id,))

                    row = cur.fetchone()
                    if not row:
                        return

                    last_milestone, message_id, total_isk = row

                    # Find next milestone to notify
                    next_milestone = None
                    for milestone in MILESTONES:
                        if current_kills >= milestone and milestone > last_milestone:
                            next_milestone = milestone
                            break

                    if not next_milestone:
                        return  # No milestone reached

                    # Get system info
                    cur.execute("""
                        SELECT ms."solarSystemName", mr."regionName", ms.security
                        FROM "mapSolarSystems" ms
                        JOIN "mapRegions" mr ON mr."regionID" = ms."regionID"
                        WHERE ms."solarSystemID" = %s
                    """, (system_id,))

                    sys_row = cur.fetchone()
                    if not sys_row:
                        return

                    system_name, region_name, security = sys_row

                    # Get involved parties
                    involved = await self.get_involved_parties(system_id, limit=3)

                    # Create milestone alert message
                    isk_b = total_isk / 1_000_000_000
                    alert_msg = f"""📊 **BATTLE UPDATE - Milestone Reached**

📍 **Location:** {system_name} ({security:.1f}) - {region_name}
🎯 **Milestone:** {next_milestone} KILLS REACHED
💀 **Battle Totals:** {current_kills} kills, {isk_b:.1f}B ISK"""

                    # Add involved parties
                    if involved['attackers']['alliances']:
                        alert_msg += "\n\n**⚔️ Attacking Forces:**"
                        for alliance in involved['attackers']['alliances'][:3]:
                            alert_msg += f"\n   • {alliance['name']} ({alliance['kills']} kills)"

                    if involved['victims']['alliances']:
                        alert_msg += "\n\n**💀 Primary Victims:**"
                        for alliance in involved['victims']['alliances'][:3]:
                            alert_msg += f"\n   • {alliance['name']} ({alliance['kills']} losses)"

                    alert_msg += "\n\n🔥 Battle ongoing - use caution"

                    # Send or update message
                    if message_id:
                        # Edit existing message
                        success = await telegram_service.edit_message(message_id, alert_msg)
                        if success:
                            print(f"[ALERT] Milestone alert updated for battle {battle_id} ({next_milestone} kills)")
                    else:
                        # Send new message (fallback)
                        message_id = await telegram_service.send_alert(alert_msg)
                        if message_id:
                            print(f"[ALERT] Milestone alert sent for battle {battle_id} ({next_milestone} kills)")

                    # Update milestone tracking
                    if message_id:
                        cur.execute("""
                            UPDATE battles
                            SET last_milestone_notified = %s,
                                telegram_message_id = %s
                            WHERE battle_id = %s
                        """, (next_milestone, message_id, battle_id))
                        conn.commit()

        except Exception as e:
            print(f"Error checking milestone alert: {e}")

    async def send_battle_ended_alert(self, battle_id: int, system_id: int, final_stats: Dict):
        """
        Send final alert when battle ends.

        Args:
            battle_id: Battle ID
            system_id: Solar system ID
            final_stats: Dict with total_kills, total_isk, duration_minutes
        """
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT
                            telegram_message_id,
                            ms."solarSystemName",
                            mr."regionName",
                            ms.security
                        FROM battles b
                        JOIN "mapSolarSystems" ms ON ms."solarSystemID" = b.solar_system_id
                        JOIN "mapRegions" mr ON mr."regionID" = ms."regionID"
                        WHERE b.battle_id = %s
                    """, (battle_id,))

                    row = cur.fetchone()
                    if not row:
                        return

                    message_id, system_name, region_name, security = row

                    # Create final alert message
                    isk_b = final_stats.get('total_isk', 0) / 1_000_000_000
                    duration = final_stats.get('duration_minutes', 0)
                    alert_msg = f"""✅ **BATTLE ENDED**

📍 **Location:** {system_name} ({security:.1f}) - {region_name}
⏱️ **Duration:** {duration} minutes
💀 **Final Count:** {final_stats.get('total_kills', 0)} kills
💰 **Total Destroyed:** {isk_b:.1f}B ISK

🏁 Combat has ceased"""

                    # Get top alliances involved
                    involved = await self.get_involved_parties(system_id, limit=2)
                    if involved['attackers']['alliances']:
                        alert_msg += "\n\n**Top Attackers:**"
                        for alliance in involved['attackers']['alliances'][:2]:
                            alert_msg += f"\n   • {alliance['name']} ({alliance['kills']} kills)"

                    # Edit existing message or send new
                    if message_id:
                        success = await telegram_service.edit_message(message_id, alert_msg)
                        if success:
                            print(f"[ALERT] Battle ended alert sent for battle {battle_id}")
                    else:
                        # Fallback: send new message
                        message_id = await telegram_service.send_alert(alert_msg)
                        if message_id:
                            print(f"[ALERT] Battle ended alert sent (new) for battle {battle_id}")

        except Exception as e:
            print(f"Error sending battle ended alert: {e}")

    def update_battle_participants(self, battle_id: int, kill: LiveKillmail):
        """
        Update battle participants (alliances and corps involved).

        Tracks kills and losses for each alliance/corp in a battle.

        Args:
            battle_id: Battle ID to update
            kill: LiveKillmail with victim and attacker data
        """
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # Update victim alliance/corp (losses)
                    if kill.victim_alliance_id:
                        cur.execute("""
                            INSERT INTO battle_participants (
                                battle_id, alliance_id, corporation_id,
                                kills, losses, isk_destroyed, isk_lost
                            ) VALUES (
                                %s, %s, %s, 0, 1, 0, %s
                            )
                            ON CONFLICT (battle_id, alliance_id, corporation_id)
                            DO UPDATE SET
                                losses = battle_participants.losses + 1,
                                isk_lost = battle_participants.isk_lost + %s
                        """, (
                            battle_id,
                            kill.victim_alliance_id,
                            kill.victim_corporation_id,
                            int(kill.ship_value),
                            int(kill.ship_value)
                        ))

                    # Update attacker alliances/corps (kills)
                    attacker_alliances = set(kill.attacker_alliances)
                    for alliance_id in attacker_alliances:
                        if alliance_id:
                            cur.execute("""
                                INSERT INTO battle_participants (
                                    battle_id, alliance_id, corporation_id,
                                    kills, losses, isk_destroyed, isk_lost
                                ) VALUES (
                                    %s, %s, NULL, 1, 0, %s, 0
                                )
                                ON CONFLICT (battle_id, alliance_id, corporation_id)
                                DO UPDATE SET
                                    kills = battle_participants.kills + 1,
                                    isk_destroyed = battle_participants.isk_destroyed + %s
                            """, (
                                battle_id,
                                alliance_id,
                                int(kill.ship_value),
                                int(kill.ship_value)
                            ))

                    conn.commit()

        except Exception as e:
            print(f"Error updating battle participants: {e}")

    def track_alliance_war(self, kill: LiveKillmail):
        """
        Track alliance wars based on kill data.

        Creates or updates alliance_wars records when alliances fight each other.
        Also updates daily statistics for trend analysis.

        Args:
            kill: LiveKillmail with victim and attacker alliance data
        """
        if not kill.victim_alliance_id:
            return  # No alliance war if victim has no alliance

        victim_alliance = kill.victim_alliance_id
        attacker_alliances = set(kill.attacker_alliances)

        # Remove None values and victim alliance from attackers
        attacker_alliances.discard(None)
        attacker_alliances.discard(victim_alliance)

        if not attacker_alliances:
            return  # No opposing alliances

        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    for attacker_alliance in attacker_alliances:
                        # Ensure consistent ordering (smaller ID first)
                        alliance_a = min(victim_alliance, attacker_alliance)
                        alliance_b = max(victim_alliance, attacker_alliance)

                        # Determine who killed whom
                        if victim_alliance == alliance_a:
                            # Alliance A was victim, B killed
                            kills_by_a = 0
                            kills_by_b = 1
                        else:
                            # Alliance B was victim, A killed
                            kills_by_a = 1
                            kills_by_b = 0

                        # Create or update war record
                        cur.execute("""
                            INSERT INTO alliance_wars (
                                alliance_a_id,
                                alliance_b_id,
                                first_kill_at,
                                last_kill_at,
                                total_kills,
                                total_isk_destroyed,
                                status
                            ) VALUES (
                                %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 1, %s, 'active'
                            )
                            ON CONFLICT (alliance_a_id, alliance_b_id)
                            DO UPDATE SET
                                last_kill_at = CURRENT_TIMESTAMP,
                                total_kills = alliance_wars.total_kills + 1,
                                total_isk_destroyed = alliance_wars.total_isk_destroyed + %s,
                                status = 'active'
                            RETURNING war_id
                        """, (
                            alliance_a,
                            alliance_b,
                            int(kill.ship_value),
                            int(kill.ship_value)
                        ))

                        war_id = cur.fetchone()[0]

                        # Update daily stats
                        cur.execute("""
                            INSERT INTO war_daily_stats (
                                war_id,
                                date,
                                kills_by_a,
                                isk_destroyed_by_a,
                                kills_by_b,
                                isk_destroyed_by_b,
                                active_systems
                            ) VALUES (
                                %s, CURRENT_DATE, %s, %s, %s, %s, 1
                            )
                            ON CONFLICT (war_id, date)
                            DO UPDATE SET
                                kills_by_a = war_daily_stats.kills_by_a + %s,
                                isk_destroyed_by_a = war_daily_stats.isk_destroyed_by_a + %s,
                                kills_by_b = war_daily_stats.kills_by_b + %s,
                                isk_destroyed_by_b = war_daily_stats.isk_destroyed_by_b + %s
                        """, (
                            war_id,
                            kills_by_a,
                            int(kill.ship_value) if kills_by_a > 0 else 0,
                            kills_by_b,
                            int(kill.ship_value) if kills_by_b > 0 else 0,
                            kills_by_a,
                            int(kill.ship_value) if kills_by_a > 0 else 0,
                            kills_by_b,
                            int(kill.ship_value) if kills_by_b > 0 else 0
                        ))

                    conn.commit()

        except Exception as e:
            print(f"Error tracking alliance war: {e}")

    def finalize_dormant_wars(self):
        """
        Mark wars as dormant if no activity for 7+ days.
        Mark wars as ended if no activity for 30+ days.
        """
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # Mark as dormant: no kills in 7 days
                    cur.execute("""
                        UPDATE alliance_wars
                        SET status = 'dormant'
                        WHERE status = 'active'
                          AND last_kill_at < NOW() - INTERVAL '7 days'
                        RETURNING war_id, alliance_a_id, alliance_b_id
                    """)

                    dormant = cur.fetchall()
                    if dormant:
                        for war_id, alliance_a, alliance_b in dormant:
                            print(f"[WAR] War {war_id} ({alliance_a} vs {alliance_b}) marked dormant")

                    # Mark as ended: no kills in 30 days
                    cur.execute("""
                        UPDATE alliance_wars
                        SET status = 'ended'
                        WHERE status = 'dormant'
                          AND last_kill_at < NOW() - INTERVAL '30 days'
                        RETURNING war_id, alliance_a_id, alliance_b_id
                    """)

                    ended = cur.fetchall()
                    if ended:
                        for war_id, alliance_a, alliance_b in ended:
                            print(f"[WAR] War {war_id} ({alliance_a} vs {alliance_b}) ended")

                    conn.commit()

        except Exception as e:
            print(f"Error finalizing wars: {e}")

    def store_live_kill(self, kill: LiveKillmail, zkb_data: Optional[Dict] = None, esi_killmail: Optional[Dict] = None):
        """
        Store killmail in Redis with 24h TTL AND PostgreSQL permanently.
        Multiple storage patterns for different query types.

        Args:
            kill: Parsed killmail data
            zkb_data: Optional zkillboard metadata for PostgreSQL storage
            esi_killmail: Optional full ESI killmail data for detailed attacker storage
        """
        timestamp = int(time.time())

        # PERSISTENT STORAGE: Write to PostgreSQL
        if zkb_data and esi_killmail:
            self.store_persistent_kill(kill, zkb_data, esi_killmail)

        # TEMPORARY STORAGE: Redis for real-time queries
        # 1. Store full killmail by ID
        key_by_id = f"kill:id:{kill.killmail_id}"
        self.redis_client.setex(
            key_by_id,
            REDIS_TTL,
            json.dumps(asdict(kill))
        )

        # 2. Add to system timeline (sorted set by timestamp)
        key_system_timeline = f"kill:system:{kill.solar_system_id}:timeline"
        self.redis_client.zadd(
            key_system_timeline,
            {kill.killmail_id: timestamp}
        )
        self.redis_client.expire(key_system_timeline, REDIS_TTL)

        # 3. Add to region timeline
        key_region_timeline = f"kill:region:{kill.region_id}:timeline"
        self.redis_client.zadd(
            key_region_timeline,
            {kill.killmail_id: timestamp}
        )
        self.redis_client.expire(key_region_timeline, REDIS_TTL)

        # 4. Track ship type losses
        key_ship_losses = f"kill:ship:{kill.ship_type_id}:count"
        self.redis_client.incr(key_ship_losses)
        self.redis_client.expire(key_ship_losses, REDIS_TTL)

        # 5. Track destroyed items (market demand)
        for item in kill.destroyed_items:
            key_item_demand = f"kill:item:{item['item_type_id']}:destroyed"
            self.redis_client.incrby(key_item_demand, item['quantity'])
            self.redis_client.expire(key_item_demand, REDIS_TTL)

    def detect_hotspot(self, kill: LiveKillmail) -> Optional[Dict]:
        """
        Detect if this kill indicates a hotspot (combat spike).

        Returns:
            Hotspot info dict or None
        """
        system_id = kill.solar_system_id
        now = time.time()

        # Add current kill timestamp
        self.kill_timestamps[system_id].append(now)

        # Count kills in last 5 minutes
        cutoff = now - HOTSPOT_WINDOW_SECONDS
        recent_kills = [ts for ts in self.kill_timestamps[system_id] if ts >= cutoff]

        if len(recent_kills) >= HOTSPOT_THRESHOLD_KILLS:
            return {
                "solar_system_id": system_id,
                "region_id": kill.region_id,
                "kill_count": len(recent_kills),
                "window_seconds": HOTSPOT_WINDOW_SECONDS,
                "timestamp": now,
                "latest_ship": kill.ship_type_id,
                "latest_value": kill.ship_value
            }

        return None

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
        from datetime import datetime
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

    def finalize_inactive_battles(self):
        """
        Mark battles as ended if they've been inactive for 30+ minutes.

        A battle is considered inactive if no kills have occurred in the system
        for 30 minutes.
        """
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # Find active battles with no recent kills
                    cur.execute("""
                        UPDATE battles
                        SET status = 'ended',
                            ended_at = last_kill_at + INTERVAL '30 minutes',
                            duration_minutes = EXTRACT(EPOCH FROM (last_kill_at - started_at)) / 60
                        WHERE status = 'active'
                          AND last_kill_at < NOW() - INTERVAL '30 minutes'
                        RETURNING battle_id, solar_system_id, total_kills, total_isk_destroyed, duration_minutes
                    """)

                    finalized = cur.fetchall()
                    conn.commit()

                    if finalized:
                        for battle_id, system_id, kills, isk, duration in finalized:
                            print(f"[BATTLE] Battle {battle_id} in system {system_id} ended: {kills} kills, {isk/1_000_000:.1f}M ISK, {duration:.0f} min")

                            # Send final battle alert
                            final_stats = {
                                'total_kills': kills,
                                'total_isk': isk,
                                'duration_minutes': int(duration or 0)
                            }
                            asyncio.create_task(self.send_battle_ended_alert(battle_id, system_id, final_stats))

        except Exception as e:
            print(f"Error finalizing battles: {e}")

    async def finalize_inactive_hotspots(self):
        """
        Check for inactive hotspots and mark them as FINAL.

        Runs periodically to finalize hotspot alerts that haven't been updated in 10+ minutes.
        Also finalizes inactive battles and dormant wars.
        """
        now = time.time()

        # Finalize inactive battles in PostgreSQL
        self.finalize_inactive_battles()

        # Finalize dormant/ended alliance wars
        self.finalize_dormant_wars()

        # Scan for active alert messages
        for key in self.redis_client.scan_iter("hotspot_alert:*"):
            alert_data_str = self.redis_client.get(key)
            if not alert_data_str:
                continue

            alert_data = json.loads(alert_data_str)
            last_update = alert_data.get("last_update", 0)
            message_id = alert_data.get("message_id")
            system_id = alert_data.get("system_id")
            kill_count = alert_data.get("kill_count", 0)

            # If last update was more than 10 minutes ago, finalize it
            time_since_update = now - last_update
            if time_since_update >= 600:  # 10 minutes
                # Get latest hotspot data
                hotspot = self.detect_hotspot_by_system(system_id)
                if hotspot:
                    alert_msg = await self.create_enhanced_alert(hotspot)
                    if alert_msg:
                        # Add FINAL marker
                        final_msg = f"{alert_msg}\n\n✅ **FINAL REPORT** - Hotspot ended"

                        # Edit message one last time
                        success = await telegram_service.edit_message(message_id, final_msg)
                        if success:
                            print(f"Hotspot finalized for system {system_id} (duration: {time_since_update/60:.1f}min)")

                # Delete the alert tracking (don't send more updates)
                self.redis_client.delete(key)

    def detect_hotspot_by_system(self, system_id: int) -> Optional[Dict]:
        """Get hotspot data for a specific system from in-memory tracking."""
        now = time.time()
        cutoff = now - HOTSPOT_WINDOW_SECONDS

        if system_id in self.kill_timestamps:
            recent_kills = [ts for ts in self.kill_timestamps[system_id] if ts >= cutoff]
            if len(recent_kills) >= HOTSPOT_THRESHOLD_KILLS:
                # Get latest kill data for this system
                kill_ids = self.redis_client.zrevrange(
                    f"kill:system:{system_id}:timeline",
                    0,
                    0
                )
                if kill_ids:
                    kill_data = self.redis_client.get(f"kill:id:{kill_ids[0]}")
                    if kill_data:
                        kill = json.loads(kill_data)
                        return {
                            "solar_system_id": system_id,
                            "region_id": kill.get("region_id"),
                            "kill_count": len(recent_kills),
                            "window_seconds": HOTSPOT_WINDOW_SECONDS,
                            "timestamp": now,
                            "latest_ship": kill.get("ship_type_id"),
                            "latest_value": kill.get("ship_value", 0)
                        }
        return None

    async def process_live_kill(self, zkb_entry: Dict):
        """
        Process a single killmail from zkillboard API.

        Pipeline:
        1. Check if already processed
        2. Fetch full data from ESI
        3. Parse killmail
        4. Store in Redis
        5. Detect hotspots
        6. Send alerts if needed
        """
        killmail_id = zkb_entry.get("killmail_id")
        hash_str = zkb_entry.get("zkb", {}).get("hash")

        if not killmail_id or not hash_str:
            return

        # Skip if already processed
        if killmail_id in self.processed_kills:
            return

        # Fetch full killmail from ESI
        killmail = await self.fetch_killmail_from_esi(killmail_id, hash_str)
        if not killmail:
            return

        # Parse
        kill = self.parse_killmail(killmail, zkb_entry.get("zkb", {}))
        if not kill:
            return

        # Mark as processed
        self.processed_kills.add(killmail_id)

        # Keep processed set bounded (last 1000)
        if len(self.processed_kills) > 1000:
            self.processed_kills = set(list(self.processed_kills)[-1000:])

        # Store (both Redis and PostgreSQL)
        self.store_live_kill(
            kill,
            zkb_data=zkb_entry.get("zkb", {}),
            esi_killmail=killmail
        )

        # BATTLE TRACKING: Track all kills in active combat zones
        # Step 1: Check if hotspot detected (5+ kills in 5 min) - creates new battles
        hotspot = self.detect_hotspot(kill)

        # Step 2: Always check if there's an active battle in this system
        # This ensures all kills during a battle are counted, not just hotspot triggers
        battle_id = self.create_or_update_battle(kill) if hotspot else self._update_existing_battle(kill)
        if battle_id:
            self.update_battle_participants(battle_id, kill)

        # ALLIANCE WAR TRACKING: Track long-term conflicts between alliances
        self.track_alliance_war(kill)

        # =====================================================
        # OLD HOTSPOT ALERT SYSTEM - DISABLED
        # Now using milestone-based battle alerts instead
        # =====================================================
        # Detect hotspot for Redis storage (used by live map visualization)
        if hotspot:
            system_id = kill.solar_system_id
            now = time.time()

            # Store hotspot data for analytics (kept for compatibility)
            key = f"hotspot:{system_id}:{int(now)}"
            self.redis_client.setex(key, 3600, json.dumps(hotspot))  # 1h TTL

            # Calculate simplified danger score for live visualization
            # Based on kill count: 5-7 = LOW, 8-10 = MEDIUM, 11+ = HIGH
            kill_count = hotspot.get("kill_count", 0)
            if kill_count >= 11:
                simple_danger = "HIGH"
            elif kill_count >= 8:
                simple_danger = "MEDIUM"
            else:
                simple_danger = "LOW"

            # Store live hotspot for real-time map visualization (5-minute TTL)
            live_hotspot_data = {
                "system_id": system_id,
                "region_id": hotspot.get("region_id"),
                "kill_count": kill_count,
                "timestamp": hotspot.get("timestamp"),
                "latest_ship": hotspot.get("latest_ship"),
                "latest_value": hotspot.get("latest_value"),
                "system_name": self._get_system_name(system_id),
                "danger_level": simple_danger,
                "age_seconds": 0  # Age will be calculated by API endpoint
            }
            live_key = f"live_hotspot:{system_id}"
            self.redis_client.setex(live_key, 300, json.dumps(live_hotspot_data))  # 5-minute TTL
            print(f"Stored live hotspot for system {system_id} (TTL: 300s, danger: {simple_danger})")

    def _get_system_name(self, system_id: int) -> str:
        """Get system name from DB"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT solarSystemName FROM mapSolarSystems WHERE solarSystemID = %s",
                        (system_id,)
                    )
                    result = cur.fetchone()
                    return result[0] if result else f"System {system_id}"
        except Exception:
            return f"System {system_id}"

    def _get_ship_name(self, type_id: int) -> str:
        """Get ship name from DB"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT typeName FROM invTypes WHERE typeID = %s",
                        (type_id,)
                    )
                    result = cur.fetchone()
                    return result[0] if result else f"Ship {type_id}"
        except Exception:
            return f"Ship {type_id}"

    async def finalize_hotspots_loop(self, verbose: bool = False):
        """
        Background task that periodically checks and finalizes inactive hotspots.

        Runs every 5 minutes.
        """
        if verbose:
            print("Starting hotspot finalizer background task...")

        while self.running:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                if verbose:
                    print("[Finalizer] Checking for inactive hotspots...")
                # DISABLED: Old hotspot finalization - now using milestone-based battle alerts
                # await self.finalize_inactive_hotspots()
            except Exception as e:
                print(f"Error in hotspot finalizer: {e}")

    async def listen_zkillboard(self, verbose: bool = False):
        """
        Main loop: continuously poll zkillboard API and process new kills.

        This is a long-running async function that should be run in background.
        """
        self.running = True

        if verbose:
            print("Starting zKillboard API poller...")
            print(f"Poll interval: {ZKILL_POLL_INTERVAL}s")
            print(f"Hotspot detection: {HOTSPOT_THRESHOLD_KILLS} kills in {HOTSPOT_WINDOW_SECONDS}s")

        kill_count = 0
        poll_count = 0

        # Start background hotspot finalizer task
        finalizer_task = asyncio.create_task(self.finalize_hotspots_loop(verbose))

        try:
            while self.running:
                poll_count += 1

                if verbose and poll_count % 10 == 1:
                    print(f"\n[Poll #{poll_count}] Fetching recent kills...")

                # Fetch recent kills from zkillboard
                zkb_kills = await self.fetch_recent_kills()

                if verbose:
                    print(f"  Found {len(zkb_kills)} kills")

                # Process each kill
                for zkb_entry in zkb_kills:
                    await self.process_live_kill(zkb_entry)
                    kill_count += 1

                if verbose and kill_count > 0:
                    print(f"  Processed {kill_count} total killmails")

                # Wait before next poll
                await asyncio.sleep(ZKILL_POLL_INTERVAL)

        except KeyboardInterrupt:
            if verbose:
                print(f"\nStopping listener. Processed {kill_count} kills total.")
        finally:
            if self.session and not self.session.closed:
                await self.session.close()

    def stop(self):
        """Stop the listener"""
        self.running = False

    # Query Methods for API

    def get_recent_kills(
        self,
        system_id: Optional[int] = None,
        region_id: Optional[int] = None,
        limit: int = 50
    ) -> List[Dict]:
        """
        Get recent kills from Redis.

        Args:
            system_id: Filter by system
            region_id: Filter by region
            limit: Max results

        Returns:
            List of killmail dicts
        """
        if system_id:
            key = f"kill:system:{system_id}:timeline"
        elif region_id:
            key = f"kill:region:{region_id}:timeline"
        else:
            # Return empty if no filter
            return []

        # Get most recent kill IDs
        kill_ids = self.redis_client.zrevrange(key, 0, limit - 1)

        # Fetch full killmails
        kills = []
        for kill_id in kill_ids:
            key_data = f"kill:id:{kill_id}"
            data = self.redis_client.get(key_data)
            if data:
                kills.append(json.loads(data))

        return kills

    def get_active_hotspots(self) -> List[Dict]:
        """
        Get all active hotspots (last hour).

        Returns:
            List of hotspot dicts
        """
        hotspots = []

        # Scan for hotspot keys
        for key in self.redis_client.scan_iter("hotspot:*"):
            data = self.redis_client.get(key)
            if data:
                hotspots.append(json.loads(data))

        # Sort by timestamp descending
        hotspots.sort(key=lambda x: x['timestamp'], reverse=True)

        return hotspots

    def get_item_demand(self, item_type_id: int) -> int:
        """
        Get destroyed quantity for an item (24h window).

        Args:
            item_type_id: Item type ID

        Returns:
            Total quantity destroyed in last 24h
        """
        key = f"kill:item:{item_type_id}:destroyed"
        value = self.redis_client.get(key)
        return int(value) if value else 0

    def get_top_destroyed_items(self, limit: int = 20) -> List[Dict]:
        """
        Get most destroyed items in last 24h.

        Returns:
            List of {item_type_id, quantity_destroyed}
        """
        items = []

        for key in self.redis_client.scan_iter("kill:item:*:destroyed"):
            # Extract item_type_id from key
            parts = key.split(":")
            if len(parts) == 4:
                item_type_id = int(parts[2])
                quantity = int(self.redis_client.get(key) or 0)

                items.append({
                    "item_type_id": item_type_id,
                    "quantity_destroyed": quantity
                })

        # Sort by quantity descending
        items.sort(key=lambda x: x['quantity_destroyed'], reverse=True)

        return items[:limit]

    def get_stats(self) -> Dict:
        """Get service statistics"""
        total_kills = len(list(self.redis_client.scan_iter("kill:id:*")))
        total_hotspots = len(list(self.redis_client.scan_iter("hotspot:*")))

        return {
            "total_kills_24h": total_kills,
            "active_hotspots": total_hotspots,
            "redis_connected": self.redis_client.ping(),
            "running": self.running
        }
