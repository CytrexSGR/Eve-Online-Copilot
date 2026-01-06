"""
zKillboard Live Service - Real-time Killmail Processing

Integrates with zKillboard RedisQ for live killmail streaming.
Provides real-time combat intelligence and hotspot detection.

Features:
- RedisQ pull-based killmail streaming
- Redis hot storage (24h TTL)
- Hotspot detection (kill spikes)
- Fitting analysis for war profiteering
- Discord alert integration
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

from database import get_db_connection
from config import DISCORD_WEBHOOK_URL, WAR_DISCORD_ENABLED


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
                dropped_items=dropped_items
            )

        except Exception as e:
            print(f"Error parsing killmail: {e}")
            return None

    def store_live_kill(self, kill: LiveKillmail):
        """
        Store killmail in Redis with 24h TTL.
        Multiple storage patterns for different query types.
        """
        timestamp = int(time.time())

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

    async def send_discord_alert(self, message: str):
        """Send alert to Discord webhook"""
        if not WAR_DISCORD_ENABLED or not DISCORD_WEBHOOK_URL:
            return

        session = await self._get_session()

        try:
            async with session.post(
                DISCORD_WEBHOOK_URL,
                json={"content": message}
            ) as response:
                if response.status != 204:
                    print(f"Discord webhook failed: {response.status}")
        except Exception as e:
            print(f"Error sending Discord alert: {e}")

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

        # Store
        self.store_live_kill(kill)

        # Detect hotspot
        hotspot = self.detect_hotspot(kill)
        if hotspot:
            # Get system name from DB
            system_name = self._get_system_name(kill.solar_system_id)

            alert_msg = (
                f"⚠️ **Combat Hotspot Detected**\n"
                f"System: **{system_name}** (ID: {kill.solar_system_id})\n"
                f"Kills: **{hotspot['kill_count']}** in {hotspot['window_seconds']//60} minutes\n"
                f"Latest: {self._get_ship_name(kill.ship_type_id)} ({kill.ship_value:,.0f} ISK)"
            )

            await self.send_discord_alert(alert_msg)

            # Store hotspot alert
            key = f"hotspot:{kill.solar_system_id}:{int(time.time())}"
            self.redis_client.setex(key, 3600, json.dumps(hotspot))  # 1h TTL

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


# Singleton instance
zkill_live_service = ZKillboardLiveService()
