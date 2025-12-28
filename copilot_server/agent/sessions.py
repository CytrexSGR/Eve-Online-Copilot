"""
Agent Session Manager
Manages session lifecycle with hybrid Redis + PostgreSQL storage.
"""

import logging
from typing import Optional
from datetime import datetime

from .models import AgentSession, SessionStatus
from .redis_store import RedisSessionStore
from .pg_repository import PostgresSessionRepository
from ..models.user_settings import AutonomyLevel

logger = logging.getLogger(__name__)


class AgentSessionManager:
    """
    Manages agent sessions with hybrid storage.

    - Redis: Fast ephemeral cache (24h TTL)
    - PostgreSQL: Persistent audit trail
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        pg_database: str = "eve_sde",
        pg_user: str = "eve",
        pg_password: str = "EvE_Pr0ject_2024",
        pg_host: str = "localhost"
    ):
        """
        Initialize session manager.

        Args:
            redis_url: Redis connection URL
            pg_database: PostgreSQL database name
            pg_user: PostgreSQL user
            pg_password: PostgreSQL password
            pg_host: PostgreSQL host
        """
        self.redis = RedisSessionStore(redis_url=redis_url, ttl_seconds=86400)
        self.postgres = PostgresSessionRepository(
            database=pg_database,
            user=pg_user,
            password=pg_password,
            host=pg_host
        )

    async def startup(self) -> None:
        """Connect to storage backends."""
        await self.redis.connect()
        await self.postgres.connect()
        logger.info("AgentSessionManager started")

    async def shutdown(self) -> None:
        """Disconnect from storage backends."""
        await self.redis.disconnect()
        await self.postgres.disconnect()
        logger.info("AgentSessionManager stopped")

    async def create_session(
        self,
        character_id: int,
        autonomy_level: AutonomyLevel = AutonomyLevel.RECOMMENDATIONS
    ) -> AgentSession:
        """
        Create new agent session.

        Args:
            character_id: EVE character ID
            autonomy_level: User's autonomy level (L0-L3)

        Returns:
            New AgentSession
        """
        session = AgentSession(
            character_id=character_id,
            autonomy_level=autonomy_level,
            status=SessionStatus.IDLE
        )

        # Save to both stores
        await self.save_session(session)

        logger.info(f"Created session {session.id} for character {character_id}")
        return session

    async def load_session(self, session_id: str) -> Optional[AgentSession]:
        """
        Load session (tries Redis first, then PostgreSQL).

        Args:
            session_id: Session ID

        Returns:
            AgentSession if found, None otherwise
        """
        # Try Redis first (fast)
        session = await self.redis.load(session_id)

        if session is not None:
            logger.debug(f"Session {session_id} loaded from Redis cache")
            return session

        # Fallback to PostgreSQL
        session = await self.postgres.load_session(session_id)

        if session is not None:
            # Restore to Redis cache
            await self.redis.save(session)
            logger.debug(f"Session {session_id} loaded from PostgreSQL, restored to cache")
            return session

        logger.debug(f"Session {session_id} not found")
        return None

    async def save_session(self, session: AgentSession) -> None:
        """
        Save session to both Redis and PostgreSQL.

        Args:
            session: AgentSession to save
        """
        session.updated_at = datetime.now()
        session.last_activity = datetime.now()

        # Save to both stores
        await self.redis.save(session)
        await self.postgres.save_session(session)

        # Save messages to PostgreSQL
        for message in session.messages:
            await self.postgres.save_message(message)

        logger.debug(f"Saved session {session.id}")

    async def delete_session(self, session_id: str) -> None:
        """
        Delete session from Redis, archive in PostgreSQL.

        Args:
            session_id: Session ID
        """
        # Remove from Redis
        await self.redis.delete(session_id)

        # Mark as archived in PostgreSQL (keep for audit)
        session = await self.postgres.load_session(session_id)
        if session:
            session.archived = True
            await self.postgres.save_session(session)

        logger.info(f"Deleted session {session_id}")
