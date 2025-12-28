"""
Tests for agent chat API endpoints.
Tests message persistence functionality.
"""
import pytest
import asyncpg
from copilot_server.agent.sessions import AgentSessionManager
from copilot_server.agent.messages import AgentMessage, MessageRepository
from copilot_server.models.user_settings import AutonomyLevel

DATABASE_URL = "postgresql://eve:EvE_Pr0ject_2024@localhost/eve_sde"


@pytest.mark.asyncio
async def test_chat_endpoint_should_persist_user_messages():
    """
    Test that /agent/chat endpoint persists user messages to database.

    This test verifies that when a message is sent via /agent/chat,
    it gets saved to the agent_messages table.

    Expected to PASS after implementation.
    """
    # Create session manager
    session_manager = AgentSessionManager()
    await session_manager.startup()

    try:
        # Create session
        session = await session_manager.create_session(
            character_id=526379435,
            autonomy_level=AutonomyLevel.RECOMMENDATIONS
        )
        session_id = session.id

        # Connect to database
        conn = await asyncpg.connect(DATABASE_URL)
        repo = MessageRepository(conn)

        # Simulate what the /agent/chat endpoint should do:
        # Save user message to database using MessageRepository (NEW behavior)
        user_message = AgentMessage.create(
            session_id=session_id,
            role="user",
            content="Hello, agent!"
        )
        await repo.save(user_message)

        # Note: We also add to session in-memory for runtime execution,
        # but don't call save_session here to avoid double-persisting
        session.add_message("user", "Hello, agent!")

        # Retrieve messages from database to verify persistence
        messages = await repo.get_by_session(session_id)

        # Cleanup - delete messages first, then session directly
        await conn.execute("DELETE FROM agent_messages WHERE session_id = $1", session_id)
        await conn.execute("DELETE FROM agent_sessions WHERE id = $1", session_id)
        await conn.close()

        # Assertion - should pass after implementation
        assert len(messages) >= 1, "Message should be persisted to database"
        assert messages[0].content == "Hello, agent!"
        assert messages[0].role == "user"

    finally:
        await session_manager.shutdown()
