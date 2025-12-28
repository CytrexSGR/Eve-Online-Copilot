"""
Redis Session Store
Provides fast ephemeral storage for agent sessions.
"""

import json
import logging
from typing import Optional
import redis.asyncio as redis

from .models import AgentSession

logger = logging.getLogger(__name__)


class RedisSessionStore:
    """Redis-backed session storage."""

    def __init__(self, redis_url: str = "redis://localhost:6379", ttl_seconds: int = 86400):
        """
        Initialize Redis store.

        Args:
            redis_url: Redis connection URL
            ttl_seconds: Session TTL in seconds (default: 24 hours)
        """
        self.redis_url = redis_url
        self.ttl_seconds = ttl_seconds
        self._redis: Optional[redis.Redis] = None

    async def connect(self) -> None:
        """Connect to Redis."""
        self._redis = await redis.from_url(self.redis_url, decode_responses=True)
        logger.info(f"Connected to Redis at {self.redis_url}")

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._redis:
            await self._redis.aclose()
            logger.info("Disconnected from Redis")

    def _key(self, session_id: str) -> str:
        """Get Redis key for session."""
        return f"agent:session:{session_id}"

    async def save(self, session: AgentSession) -> None:
        """
        Save session to Redis with TTL.

        Args:
            session: AgentSession to save
        """
        if not self._redis:
            raise RuntimeError("Redis not connected. Call connect() first.")

        key = self._key(session.id)
        data = session.model_dump_json()

        await self._redis.setex(key, self.ttl_seconds, data)
        logger.debug(f"Saved session {session.id} to Redis (TTL: {self.ttl_seconds}s)")

    async def load(self, session_id: str) -> Optional[AgentSession]:
        """
        Load session from Redis.

        Args:
            session_id: Session ID

        Returns:
            AgentSession if found, None otherwise
        """
        if not self._redis:
            raise RuntimeError("Redis not connected. Call connect() first.")

        key = self._key(session_id)
        data = await self._redis.get(key)

        if data is None:
            logger.debug(f"Session {session_id} not found in Redis")
            return None

        session = AgentSession.model_validate_json(data)
        logger.debug(f"Loaded session {session_id} from Redis")
        return session

    async def delete(self, session_id: str) -> None:
        """
        Delete session from Redis.

        Args:
            session_id: Session ID
        """
        if not self._redis:
            raise RuntimeError("Redis not connected. Call connect() first.")

        key = self._key(session_id)
        await self._redis.delete(key)
        logger.debug(f"Deleted session {session_id} from Redis")

    async def exists(self, session_id: str) -> bool:
        """
        Check if session exists in Redis.

        Args:
            session_id: Session ID

        Returns:
            True if exists, False otherwise
        """
        if not self._redis:
            raise RuntimeError("Redis not connected. Call connect() first.")

        key = self._key(session_id)
        result = await self._redis.exists(key)
        return result > 0
