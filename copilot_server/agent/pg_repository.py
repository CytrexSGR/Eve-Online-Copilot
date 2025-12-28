"""
PostgreSQL Session Repository
Provides persistent storage for agent sessions and audit trail.
"""

import json
import logging
from typing import Optional, List
import asyncpg

from .models import AgentSession, AgentMessage, SessionStatus
from ..models.user_settings import AutonomyLevel

logger = logging.getLogger(__name__)


class PostgresSessionRepository:
    """PostgreSQL-backed session repository."""

    def __init__(self, database: str, user: str, password: str, host: str = "localhost"):
        """
        Initialize PostgreSQL repository.

        Args:
            database: Database name
            user: Database user
            password: Database password
            host: Database host
        """
        self.database = database
        self.user = user
        self.password = password
        self.host = host
        self._pool: Optional[asyncpg.Pool] = None

    async def connect(self) -> None:
        """Create connection pool."""
        self._pool = await asyncpg.create_pool(
            database=self.database,
            user=self.user,
            password=self.password,
            host=self.host,
            min_size=2,
            max_size=10
        )
        logger.info(f"Connected to PostgreSQL at {self.host}/{self.database}")

    async def disconnect(self) -> None:
        """Close connection pool."""
        if self._pool:
            await self._pool.close()
            logger.info("Disconnected from PostgreSQL")

    async def save_session(self, session: AgentSession) -> None:
        """
        Save or update session in PostgreSQL.

        Args:
            session: AgentSession to save
        """
        if not self._pool:
            raise RuntimeError("PostgreSQL not connected. Call connect() first.")

        async with self._pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO agent_sessions (
                    id, character_id, autonomy_level, status,
                    created_at, updated_at, last_activity, archived, context
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9::jsonb)
                ON CONFLICT (id) DO UPDATE SET
                    status = EXCLUDED.status,
                    updated_at = EXCLUDED.updated_at,
                    last_activity = EXCLUDED.last_activity,
                    context = EXCLUDED.context
            """,
                session.id,
                session.character_id,
                session.autonomy_level.value,
                session.status.value,
                session.created_at,
                session.updated_at,
                session.last_activity,
                session.archived,
                json.dumps(session.context)
            )

        logger.debug(f"Saved session {session.id} to PostgreSQL")

    async def load_session(self, session_id: str) -> Optional[AgentSession]:
        """
        Load session from PostgreSQL.

        Args:
            session_id: Session ID

        Returns:
            AgentSession if found, None otherwise
        """
        if not self._pool:
            raise RuntimeError("PostgreSQL not connected. Call connect() first.")

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM agent_sessions WHERE id = $1 AND archived = FALSE",
                session_id
            )

        if row is None:
            logger.debug(f"Session {session_id} not found in PostgreSQL")
            return None

        # Build AgentSession from row
        # Parse context if it's a string, otherwise use directly
        context = row['context']
        if isinstance(context, str):
            context = json.loads(context) if context else {}
        elif context is None:
            context = {}

        session = AgentSession(
            id=row['id'],
            character_id=row['character_id'],
            autonomy_level=AutonomyLevel(row['autonomy_level']),
            status=SessionStatus(row['status']),
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            last_activity=row['last_activity'],
            archived=row['archived'],
            context=context
        )

        # Load messages
        messages = await self.load_messages(session_id)
        session.messages = messages

        logger.debug(f"Loaded session {session_id} from PostgreSQL")
        return session

    async def save_message(self, message: AgentMessage) -> None:
        """
        Save message to PostgreSQL.

        Args:
            message: AgentMessage to save
        """
        if not self._pool:
            raise RuntimeError("PostgreSQL not connected. Call connect() first.")

        async with self._pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO agent_messages (session_id, role, content, timestamp)
                VALUES ($1, $2, $3, $4)
            """,
                message.session_id,
                message.role,
                message.content,
                message.timestamp
            )

        logger.debug(f"Saved message to session {message.session_id}")

    async def load_messages(self, session_id: str) -> List[AgentMessage]:
        """
        Load all messages for a session.

        Args:
            session_id: Session ID

        Returns:
            List of AgentMessage objects
        """
        if not self._pool:
            raise RuntimeError("PostgreSQL not connected. Call connect() first.")

        async with self._pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM agent_messages
                WHERE session_id = $1
                ORDER BY timestamp ASC
            """, session_id)

        messages = [
            AgentMessage(
                session_id=row['session_id'],
                role=row['role'],
                content=row['content'],
                timestamp=row['timestamp']
            )
            for row in rows
        ]

        return messages
