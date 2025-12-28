import asyncpg
import json
from typing import Optional, List
from copilot_server.agent.events import AgentEvent, AgentEventType


class EventRepository:
    """PostgreSQL repository for agent events."""

    def __init__(self, database_url: str):
        """
        Initialize repository.

        Args:
            database_url: PostgreSQL connection string
        """
        self.database_url = database_url
        self._pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        """Create connection pool."""
        self._pool = await asyncpg.create_pool(self.database_url, min_size=2, max_size=10)

    async def disconnect(self):
        """Close connection pool."""
        if self._pool:
            await self._pool.close()

    async def save(self, event: AgentEvent):
        """
        Save event to database.

        Args:
            event: Event to save
        """
        if not self._pool:
            raise RuntimeError("Repository not connected. Call connect() first.")
        async with self._pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO agent_events (session_id, plan_id, event_type, payload, timestamp)
                VALUES ($1, $2, $3, $4::jsonb, $5)
            """,
                event.session_id,
                event.plan_id,
                event.type.value,
                json.dumps(event.payload),
                event.timestamp
            )

    async def load_by_session(self, session_id: str) -> List[AgentEvent]:
        """
        Load all events for a session.

        Args:
            session_id: Session ID

        Returns:
            List of events ordered by timestamp
        """
        if not self._pool:
            raise RuntimeError("Repository not connected. Call connect() first.")
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT session_id, plan_id, event_type, payload, timestamp
                FROM agent_events
                WHERE session_id = $1
                ORDER BY timestamp ASC
            """, session_id)

            return [self._row_to_event(row) for row in rows]

    async def load_by_plan(self, plan_id: str) -> List[AgentEvent]:
        """
        Load all events for a plan.

        Args:
            plan_id: Plan ID

        Returns:
            List of events ordered by timestamp
        """
        if not self._pool:
            raise RuntimeError("Repository not connected. Call connect() first.")
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT session_id, plan_id, event_type, payload, timestamp
                FROM agent_events
                WHERE plan_id = $1
                ORDER BY timestamp ASC
            """, plan_id)

            return [self._row_to_event(row) for row in rows]

    def _row_to_event(self, row) -> AgentEvent:
        """Convert database row to AgentEvent."""
        payload = row["payload"] or {}
        if isinstance(payload, str):
            payload = json.loads(payload)

        return AgentEvent(
            type=AgentEventType(row["event_type"]),
            session_id=row["session_id"],
            plan_id=row["plan_id"],
            payload=payload,
            timestamp=row["timestamp"]
        )
