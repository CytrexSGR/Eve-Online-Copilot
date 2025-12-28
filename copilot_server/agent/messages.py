"""
Agent Message Models and Repository
Handles message persistence for agent chat sessions.
"""

import uuid
import asyncpg
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
import json

@dataclass
class AgentMessage:
    """Agent chat message."""
    id: str
    session_id: str
    role: str  # 'user', 'assistant', 'system'
    content: str
    content_blocks: List[Dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    token_usage: Optional[Dict[str, int]] = None

    @staticmethod
    def create(session_id: str, role: str, content: str, content_blocks: List[Dict[str, Any]] = None) -> 'AgentMessage':
        """Create new message with generated ID."""
        return AgentMessage(
            id=f"msg-{uuid.uuid4().hex[:12]}",
            session_id=session_id,
            role=role,
            content=content,
            content_blocks=content_blocks or [{"type": "text", "text": content}]
        )


class MessageRepository:
    """Repository for agent messages."""

    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn

    async def save(self, message: AgentMessage) -> None:
        """Save message to database."""
        await self.conn.execute("""
            INSERT INTO agent_messages
            (id, session_id, role, content, content_blocks, created_at, token_usage)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (id) DO UPDATE SET
                content = EXCLUDED.content,
                content_blocks = EXCLUDED.content_blocks,
                token_usage = EXCLUDED.token_usage
        """,
            message.id,
            message.session_id,
            message.role,
            message.content,
            json.dumps(message.content_blocks),
            message.created_at,
            json.dumps(message.token_usage) if message.token_usage else None
        )

        # Update message count
        await self.conn.execute("""
            UPDATE agent_sessions
            SET message_count = (
                SELECT COUNT(*) FROM agent_messages WHERE session_id = $1
            )
            WHERE id = $1
        """, message.session_id)

    async def get_by_id(self, message_id: str) -> Optional[AgentMessage]:
        """Get message by ID."""
        row = await self.conn.fetchrow("""
            SELECT id, session_id, role, content, content_blocks, created_at, token_usage
            FROM agent_messages
            WHERE id = $1
        """, message_id)

        if not row:
            return None

        return AgentMessage(
            id=row['id'],
            session_id=row['session_id'],
            role=row['role'],
            content=row['content'],
            content_blocks=json.loads(row['content_blocks']) if row['content_blocks'] else [],
            created_at=row['created_at'],
            token_usage=json.loads(row['token_usage']) if row['token_usage'] else None
        )

    async def get_by_session(self, session_id: str, limit: int = 100) -> List[AgentMessage]:
        """Get messages for session, ordered by creation time."""
        rows = await self.conn.fetch("""
            SELECT id, session_id, role, content, content_blocks, created_at, token_usage
            FROM agent_messages
            WHERE session_id = $1
            ORDER BY created_at ASC
            LIMIT $2
        """, session_id, limit)

        return [
            AgentMessage(
                id=row['id'],
                session_id=row['session_id'],
                role=row['role'],
                content=row['content'],
                content_blocks=json.loads(row['content_blocks']) if row['content_blocks'] else [],
                created_at=row['created_at'],
                token_usage=json.loads(row['token_usage']) if row['token_usage'] else None
            )
            for row in rows
        ]
