"""
Redis State Manager for zkillboard Live Service

Manages all persistent state in Redis instead of in-memory:
- Processed kills (deduplication)
- Kill timestamps per system (hotspot detection)
- Alert cooldowns (deduplication)
- Queue position (recovery after restart)

All state survives service restarts!
"""

import json
import time
from datetime import datetime, date
from typing import Optional, Set, Dict, List
import redis
from dataclasses import dataclass


# Redis Configuration
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 0

# TTL Configuration
TTL_PROCESSED_KILLS = 259200  # 3 days (covers RedisQ 3h memory + safety margin)
TTL_KILL_TIMESTAMPS = 600     # 10 minutes (hotspot window is 5 min)
TTL_ALERT_COOLDOWN = 600      # 10 minutes
TTL_QUEUE_POSITION = 14400    # 4 hours (RedisQ remembers 3h)
TTL_KILL_CACHE = 86400        # 24 hours

# Hotspot Configuration
HOTSPOT_WINDOW_SECONDS = 300  # 5 minutes
HOTSPOT_THRESHOLD_KILLS = 5   # 5+ kills = hotspot


@dataclass
class HotspotInfo:
    """Hotspot detection result"""
    system_id: int
    kill_count: int
    window_seconds: int
    is_hotspot: bool
    timestamp: float


class RedisStateManager:
    """
    Manages all zkillboard service state in Redis.

    Features:
    - Atomic operations for thread safety
    - Daily partitioned sets for efficient cleanup
    - Pipelined operations for performance
    - Graceful degradation on Redis failures
    """

    def __init__(self, redis_host: str = REDIS_HOST, redis_port: int = REDIS_PORT, redis_db: int = REDIS_DB):
        """Initialize Redis connection"""
        self.redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5
        )
        self._verify_connection()

    def _verify_connection(self):
        """Verify Redis is accessible"""
        try:
            self.redis_client.ping()
        except redis.ConnectionError as e:
            raise RuntimeError(f"Cannot connect to Redis at {REDIS_HOST}:{REDIS_PORT}: {e}")

    # =========================================================
    # Processed Kills Deduplication
    # =========================================================

    def _get_processed_key(self, for_date: Optional[date] = None) -> str:
        """Get the Redis key for processed kills (daily partitioned)"""
        if for_date is None:
            for_date = datetime.utcnow().date()
        return f"zkill:processed:{for_date.isoformat()}"

    def is_kill_processed(self, killmail_id: int) -> bool:
        """
        Check if a killmail has already been processed.

        Uses SISMEMBER for O(1) lookup.
        Checks today AND yesterday to handle timezone edge cases.

        Args:
            killmail_id: The killmail ID to check

        Returns:
            True if already processed, False if new
        """
        try:
            today = datetime.utcnow().date()
            yesterday = date.fromordinal(today.toordinal() - 1)

            # Check both today and yesterday
            pipeline = self.redis_client.pipeline()
            pipeline.sismember(self._get_processed_key(today), str(killmail_id))
            pipeline.sismember(self._get_processed_key(yesterday), str(killmail_id))
            results = pipeline.execute()

            return any(results)
        except redis.RedisError as e:
            print(f"[WARNING] Redis error checking processed kill: {e}")
            return False  # Assume not processed on error (will be caught by DB constraint)

    def mark_kill_processed(self, killmail_id: int, source: str = "redisq") -> bool:
        """
        Mark a killmail as processed.

        Uses atomic SADD which returns 1 if new, 0 if duplicate.
        This is the PRIMARY deduplication mechanism.

        Args:
            killmail_id: The killmail ID to mark
            source: Source of the kill (redisq, backfill, manual)

        Returns:
            True if newly added (not duplicate), False if already exists
        """
        try:
            key = self._get_processed_key()
            # SADD returns 1 if added, 0 if already exists
            added = self.redis_client.sadd(key, str(killmail_id))
            self.redis_client.expire(key, TTL_PROCESSED_KILLS)
            return added == 1
        except redis.RedisError as e:
            print(f"[WARNING] Redis error marking kill processed: {e}")
            return True  # Assume success on error (DB will handle constraint)

    def get_processed_count(self, for_date: Optional[date] = None) -> int:
        """Get count of processed kills for a date"""
        try:
            return self.redis_client.scard(self._get_processed_key(for_date))
        except redis.RedisError:
            return 0

    def cleanup_old_processed(self, days_to_keep: int = 3):
        """Remove processed kill sets older than specified days"""
        today = datetime.utcnow().date()
        for i in range(days_to_keep + 1, days_to_keep + 10):
            old_date = date.fromordinal(today.toordinal() - i)
            key = self._get_processed_key(old_date)
            self.redis_client.delete(key)

    # =========================================================
    # Kill Timestamps for Hotspot Detection
    # =========================================================

    def _get_timestamps_key(self, system_id: int) -> str:
        """Get Redis key for system kill timestamps"""
        return f"zkill:timestamps:{system_id}"

    def add_kill_timestamp(self, system_id: int, timestamp: Optional[float] = None) -> HotspotInfo:
        """
        Add a kill timestamp for a system and check for hotspot.

        Uses ZSET with score = timestamp for automatic ordering.
        Atomically adds timestamp, removes old entries, counts remaining.

        Args:
            system_id: Solar system ID
            timestamp: Kill timestamp (default: now)

        Returns:
            HotspotInfo with detection result
        """
        if timestamp is None:
            timestamp = time.time()

        key = self._get_timestamps_key(system_id)
        cutoff = timestamp - HOTSPOT_WINDOW_SECONDS

        try:
            # Atomic pipeline: add, cleanup, count
            pipeline = self.redis_client.pipeline()
            pipeline.zadd(key, {str(timestamp): timestamp})
            pipeline.zremrangebyscore(key, 0, cutoff)
            pipeline.zcard(key)
            pipeline.expire(key, TTL_KILL_TIMESTAMPS)
            results = pipeline.execute()

            kill_count = results[2]
            is_hotspot = kill_count >= HOTSPOT_THRESHOLD_KILLS

            return HotspotInfo(
                system_id=system_id,
                kill_count=kill_count,
                window_seconds=HOTSPOT_WINDOW_SECONDS,
                is_hotspot=is_hotspot,
                timestamp=timestamp
            )
        except redis.RedisError as e:
            print(f"[WARNING] Redis error adding kill timestamp: {e}")
            return HotspotInfo(
                system_id=system_id,
                kill_count=0,
                window_seconds=HOTSPOT_WINDOW_SECONDS,
                is_hotspot=False,
                timestamp=timestamp
            )

    def get_recent_kill_count(self, system_id: int, window_seconds: int = HOTSPOT_WINDOW_SECONDS) -> int:
        """Get count of kills in a system within time window"""
        try:
            key = self._get_timestamps_key(system_id)
            cutoff = time.time() - window_seconds
            return self.redis_client.zcount(key, cutoff, "+inf")
        except redis.RedisError:
            return 0

    def get_active_systems(self, min_kills: int = 1) -> List[int]:
        """Get list of systems with recent kill activity"""
        try:
            # Scan for all timestamp keys
            systems = []
            for key in self.redis_client.scan_iter("zkill:timestamps:*"):
                system_id = int(key.split(":")[-1])
                count = self.get_recent_kill_count(system_id)
                if count >= min_kills:
                    systems.append(system_id)
            return systems
        except redis.RedisError:
            return []

    # =========================================================
    # Alert Cooldowns
    # =========================================================

    def _get_alert_key(self, system_id: int, alert_type: str = "hotspot") -> str:
        """Get Redis key for alert cooldown"""
        return f"zkill:alert_cooldown:{alert_type}:{system_id}"

    def can_send_alert(self, system_id: int, alert_type: str = "hotspot", cooldown_seconds: int = 600) -> bool:
        """
        Check if we can send an alert (not in cooldown).

        Args:
            system_id: Solar system ID
            alert_type: Type of alert (hotspot, milestone, etc.)
            cooldown_seconds: Cooldown period in seconds

        Returns:
            True if alert can be sent, False if in cooldown
        """
        try:
            key = self._get_alert_key(system_id, alert_type)
            # SET with NX (only if not exists) and EX (expiry)
            # Returns True if set successfully (no cooldown), False if exists (in cooldown)
            result = self.redis_client.set(key, "1", ex=cooldown_seconds, nx=True)
            return result is True
        except redis.RedisError as e:
            print(f"[WARNING] Redis error checking alert cooldown: {e}")
            return True  # Allow alert on error

    def set_alert_cooldown(self, system_id: int, alert_type: str = "hotspot", cooldown_seconds: int = 600):
        """Explicitly set an alert cooldown"""
        try:
            key = self._get_alert_key(system_id, alert_type)
            self.redis_client.setex(key, cooldown_seconds, "1")
        except redis.RedisError as e:
            print(f"[WARNING] Redis error setting alert cooldown: {e}")

    def clear_alert_cooldown(self, system_id: int, alert_type: str = "hotspot"):
        """Clear an alert cooldown (allow immediate alert)"""
        try:
            key = self._get_alert_key(system_id, alert_type)
            self.redis_client.delete(key)
        except redis.RedisError:
            pass

    # =========================================================
    # Kill Cache (for API queries)
    # =========================================================

    def _get_kill_cache_key(self, killmail_id: int) -> str:
        """Get Redis key for cached kill data"""
        return f"zkill:kill:{killmail_id}"

    def cache_kill(self, killmail_id: int, kill_data: Dict):
        """Cache kill data for fast retrieval"""
        try:
            key = self._get_kill_cache_key(killmail_id)
            self.redis_client.setex(key, TTL_KILL_CACHE, json.dumps(kill_data))
        except redis.RedisError as e:
            print(f"[WARNING] Redis error caching kill: {e}")

    def get_cached_kill(self, killmail_id: int) -> Optional[Dict]:
        """Get cached kill data"""
        try:
            key = self._get_kill_cache_key(killmail_id)
            data = self.redis_client.get(key)
            return json.loads(data) if data else None
        except (redis.RedisError, json.JSONDecodeError):
            return None

    # =========================================================
    # System Timeline (for API queries)
    # =========================================================

    def _get_system_timeline_key(self, system_id: int) -> str:
        """Get Redis key for system kill timeline"""
        return f"zkill:system_timeline:{system_id}"

    def add_to_system_timeline(self, system_id: int, killmail_id: int, timestamp: float):
        """Add a kill to system timeline"""
        try:
            key = self._get_system_timeline_key(system_id)
            self.redis_client.zadd(key, {str(killmail_id): timestamp})
            self.redis_client.expire(key, TTL_KILL_CACHE)
        except redis.RedisError as e:
            print(f"[WARNING] Redis error adding to timeline: {e}")

    def get_system_timeline(self, system_id: int, limit: int = 50) -> List[int]:
        """Get recent kill IDs from system timeline"""
        try:
            key = self._get_system_timeline_key(system_id)
            kill_ids = self.redis_client.zrevrange(key, 0, limit - 1)
            return [int(kid) for kid in kill_ids]
        except redis.RedisError:
            return []

    # =========================================================
    # Queue Position (for RedisQ recovery)
    # =========================================================

    def _get_queue_key(self) -> str:
        """Get Redis key for queue position"""
        return "zkill:queue_position"

    def save_queue_position(self, position_data: Dict):
        """Save queue position for recovery after restart"""
        try:
            key = self._get_queue_key()
            self.redis_client.setex(key, TTL_QUEUE_POSITION, json.dumps(position_data))
        except redis.RedisError as e:
            print(f"[WARNING] Redis error saving queue position: {e}")

    def get_queue_position(self) -> Optional[Dict]:
        """Get saved queue position"""
        try:
            key = self._get_queue_key()
            data = self.redis_client.get(key)
            return json.loads(data) if data else None
        except (redis.RedisError, json.JSONDecodeError):
            return None

    # =========================================================
    # Statistics and Monitoring
    # =========================================================

    def get_stats(self) -> Dict:
        """Get service statistics"""
        today = datetime.utcnow().date()
        try:
            return {
                "processed_today": self.get_processed_count(today),
                "processed_yesterday": self.get_processed_count(date.fromordinal(today.toordinal() - 1)),
                "active_systems": len(self.get_active_systems()),
                "redis_connected": self.redis_client.ping(),
                "timestamp": datetime.utcnow().isoformat()
            }
        except redis.RedisError as e:
            return {
                "error": str(e),
                "redis_connected": False,
                "timestamp": datetime.utcnow().isoformat()
            }

    def health_check(self) -> bool:
        """Check if Redis is healthy"""
        try:
            return self.redis_client.ping()
        except redis.RedisError:
            return False


# Singleton instance
state_manager = RedisStateManager()
