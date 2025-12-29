"""
Integration tests for complete chat flow.
Tests the full stack: API -> Database -> LLM -> SSE.
"""

import pytest
import asyncio
from httpx import ASGITransport, AsyncClient
from copilot_server.main import app
from copilot_server.agent.sessions import AgentSessionManager
from copilot_server.agent.runtime import AgentRuntime
from copilot_server.models.user_settings import AutonomyLevel
from copilot_server.api import agent_routes
import asyncpg

DATABASE_URL = "postgresql://eve:EvE_Pr0ject_2024@localhost/eve_sde"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_complete_chat_flow():
    """Test complete chat flow from session creation to message retrieval."""
    # Setup
    session_manager = AgentSessionManager()
    await session_manager.startup()

    db_pool = await asyncpg.create_pool(
        DATABASE_URL,
        min_size=1,
        max_size=2
    )

    # Create runtime (mock for now)
    from unittest.mock import AsyncMock
    runtime = AsyncMock()
    runtime.execute = AsyncMock(return_value={
        "content": [{"type": "text", "text": "I can help with market analysis!"}],
        "usage": {"input_tokens": 10, "output_tokens": 20}
    })

    # Set globals
    agent_routes.session_manager = session_manager
    agent_routes.db_pool = db_pool
    agent_routes.runtime = runtime

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Step 1: Create session by sending first message without session_id
            response = await client.post("/agent/chat", json={
                "message": "What can you help me with?",
                "character_id": 526379435
            })
            assert response.status_code == 200
            session_id = response.json()["session_id"]

            # Step 2: Send second message with session_id
            response = await client.post("/agent/chat", json={
                "message": "Tell me about market analysis",
                "session_id": session_id,
                "character_id": 526379435
            })
            assert response.status_code == 200

            # Step 3: Get chat history
            response = await client.get(f"/agent/chat/history/{session_id}")
            assert response.status_code == 200

            history = response.json()
            assert history["message_count"] >= 2
            assert len(history["messages"]) >= 2

            # Verify message order and content
            messages = history["messages"]
            assert messages[0]["role"] == "user"
            assert "help me" in messages[0]["content"].lower()
            # Note: assistant response depends on runtime being called

            # Step 4: Verify persistence in session
            response = await client.get(f"/agent/session/{session_id}")
            assert response.status_code == 200
            session_data = response.json()
            assert len(session_data["messages"]) >= 2

            # Cleanup
            conn = await asyncpg.connect(DATABASE_URL)
            await conn.execute("DELETE FROM agent_messages WHERE session_id = $1", session_id)
            await conn.execute("DELETE FROM agent_sessions WHERE id = $1", session_id)
            await conn.close()

    finally:
        # Cleanup
        await db_pool.close()
        await session_manager.shutdown()
        agent_routes.session_manager = None
        agent_routes.db_pool = None
        agent_routes.runtime = None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_message_persistence_in_database():
    """Test that messages are actually persisted in database."""
    # Setup
    session_manager = AgentSessionManager()
    await session_manager.startup()

    db_pool = await asyncpg.create_pool(
        DATABASE_URL,
        min_size=1,
        max_size=2
    )

    # Create mock runtime
    from unittest.mock import AsyncMock
    runtime = AsyncMock()
    runtime.execute = AsyncMock(return_value={
        "content": [{"type": "text", "text": "Response"}],
        "usage": {"input_tokens": 5, "output_tokens": 10}
    })

    # Set globals
    agent_routes.session_manager = session_manager
    agent_routes.db_pool = db_pool
    agent_routes.runtime = runtime

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Create session and send message (session created automatically)
            response = await client.post("/agent/chat", json={
                "message": "Database persistence test",
                "character_id": 526379435
            })
            assert response.status_code == 200
            session_id = response.json()["session_id"]

            # Verify in database directly
            conn = await asyncpg.connect(DATABASE_URL)

            messages = await conn.fetch("""
                SELECT * FROM agent_messages
                WHERE session_id = $1
                ORDER BY created_at ASC
            """, session_id)

            assert len(messages) >= 1
            assert messages[0]['role'] == 'user'
            assert messages[0]['content'] == 'Database persistence test'

            # Cleanup
            await conn.execute("DELETE FROM agent_messages WHERE session_id = $1", session_id)
            await conn.execute("DELETE FROM agent_sessions WHERE id = $1", session_id)
            await conn.close()

    finally:
        # Cleanup
        await db_pool.close()
        await session_manager.shutdown()
        agent_routes.session_manager = None
        agent_routes.db_pool = None
        agent_routes.runtime = None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_chat_validation():
    """Test validation in chat endpoints."""
    # Setup
    session_manager = AgentSessionManager()
    await session_manager.startup()

    db_pool = await asyncpg.create_pool(
        DATABASE_URL,
        min_size=1,
        max_size=2
    )

    # Create mock runtime
    from unittest.mock import AsyncMock
    runtime = AsyncMock()

    # Set globals
    agent_routes.session_manager = session_manager
    agent_routes.db_pool = db_pool
    agent_routes.runtime = runtime

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Create session by sending first message
            response = await client.post("/agent/chat", json={
                "message": "Initial message",
                "character_id": 526379435
            })
            assert response.status_code == 200
            session_id = response.json()["session_id"]

            # Test empty message
            response = await client.post("/agent/chat", json={
                "message": "",
                "session_id": session_id,
                "character_id": 526379435
            })
            assert response.status_code == 400

            # Test invalid session
            response = await client.post("/agent/chat", json={
                "message": "Test",
                "session_id": "invalid-session-id",
                "character_id": 526379435
            })
            assert response.status_code == 404

            # Test message too long
            long_message = "x" * 20000
            response = await client.post("/agent/chat", json={
                "message": long_message,
                "session_id": session_id,
                "character_id": 526379435
            })
            assert response.status_code == 400

            # Cleanup
            conn = await asyncpg.connect(DATABASE_URL)
            await conn.execute("DELETE FROM agent_sessions WHERE id = $1", session_id)
            await conn.close()

    finally:
        # Cleanup
        await db_pool.close()
        await session_manager.shutdown()
        agent_routes.session_manager = None
        agent_routes.db_pool = None
        agent_routes.runtime = None
