"""
Redis Cache Operations.

Provides Redis storage and hotspot detection for real-time killmail data.
"""

import json
import time
from dataclasses import asdict
from typing import Dict, List, Optional, TYPE_CHECKING

from .models import REDIS_TTL, HOTSPOT_WINDOW_SECONDS, HOTSPOT_THRESHOLD_KILLS

if TYPE_CHECKING:
    from .models import LiveKillmail


class RedisCacheMixin:
    """Mixin providing Redis cache operations for ZKillboardLiveService."""

    def store_live_kill(self, kill: 'LiveKillmail', zkb_data: Optional[Dict] = None, esi_killmail: Optional[Dict] = None) -> Optional[int]:
        """
        Store killmail in Redis with 24h TTL AND PostgreSQL permanently.
        Multiple storage patterns for different query types.

        Args:
            kill: Parsed killmail data
            zkb_data: Optional zkillboard metadata for PostgreSQL storage
            esi_killmail: Optional full ESI killmail data for detailed attacker storage

        Returns:
            battle_id if kill was stored and part of a battle
            0 if kill was stored but not part of a battle
            None if kill was duplicate or failed to store
        """
        timestamp = int(time.time())

        # PERSISTENT STORAGE: Write to PostgreSQL with atomic battle assignment
        if not zkb_data or not esi_killmail:
            print(f"[WARNING] Killmail {kill.killmail_id} missing zkb_data or esi_killmail - skipping")
            return None

        # store_persistent_kill returns:
        # - battle_id (>0) if associated with battle
        # - 0 if stored but no battle
        # - None if duplicate
        result = self.store_persistent_kill(kill, zkb_data, esi_killmail)

        if result is None:
            # Duplicate - already exists in database
            return None

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

        # Cache kill in state manager for fast retrieval
        self.state_manager.cache_kill(kill.killmail_id, asdict(kill))

        # Add to system timeline in state manager
        self.state_manager.add_to_system_timeline(
            kill.solar_system_id,
            kill.killmail_id,
            timestamp
        )

        # Return battle_id (or 0 if not part of battle)
        return result

    def detect_hotspot(self, kill: 'LiveKillmail') -> Optional[Dict]:
        """
        Detect if this kill indicates a hotspot (combat spike).

        Uses Redis-based state manager for persistence across restarts.

        Returns:
            Hotspot info dict or None if not a hotspot
        """
        system_id = kill.solar_system_id
        now = time.time()

        # Add timestamp to Redis and get hotspot info
        # This is atomic and survives service restarts
        hotspot_info = self.state_manager.add_kill_timestamp(system_id, now)

        if hotspot_info.is_hotspot:
            return {
                "solar_system_id": system_id,
                "region_id": kill.region_id,
                "kill_count": hotspot_info.kill_count,
                "window_seconds": hotspot_info.window_seconds,
                "timestamp": now,
                "latest_ship": kill.ship_type_id,
                "latest_value": kill.ship_value
            }

        return None

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

    def store_live_hotspot(self, kill: 'LiveKillmail', hotspot: Dict):
        """
        Store hotspot data for live visualization.

        Args:
            kill: LiveKillmail that triggered the hotspot
            hotspot: Hotspot detection result
        """
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
