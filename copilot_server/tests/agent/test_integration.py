"""
Integration tests for Agent Runtime Phase 1.
Tests full stack: API → Runtime → Session Manager → Storage.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from fastapi import FastAPI
from unittest.mock import AsyncMock

from copilot_server.api import agent_routes
from copilot_server.agent.sessions import AgentSessionManager
from copilot_server.agent.runtime import AgentRuntime


@pytest.fixture
async def session_manager():
    """Set up session manager for testing."""
    manager = AgentSessionManager(
        redis_url="redis://localhost:6379",
        pg_database="eve_sde",
        pg_user="eve",
        pg_password="EvE_Pr0ject_2024"
    )
    await manager.startup()
    yield manager
    await manager.shutdown()


@pytest.fixture
def mock_runtime(session_manager):
    """Set up mocked agent runtime for testing."""
    # Mock LLM and orchestrator
    llm_client = AsyncMock()
    llm_client.chat.return_value = {
        "content": [{"type": "text", "text": "Hello! How can I help?"}],
        "stop_reason": "end_turn"
    }

    orchestrator = AsyncMock()
    orchestrator.mcp = AsyncMock()
    orchestrator.mcp.get_tools.return_value = []
    llm_client.build_tool_schema.return_value = []

    # Create runtime with actual session manager
    return AgentRuntime(
        session_manager=session_manager,
        llm_client=llm_client,
        orchestrator=orchestrator
    )


@pytest.fixture
def test_app(session_manager, mock_runtime):
    """Create test app with agent routes."""
    # Set globals
    agent_routes.session_manager = session_manager
    agent_routes.runtime = mock_runtime

    app = FastAPI()
    app.include_router(agent_routes.router)
    return app


@pytest.mark.asyncio
async def test_full_session_lifecycle(test_app):
    """Test complete session lifecycle from creation to deletion."""
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        # 1. Create session with first message
        response1 = await client.post("/agent/chat", json={
            "message": "Hello, what can you do?",
            "session_id": None,
            "character_id": 1117367444
        })

        assert response1.status_code == 200
        session_id = response1.json()["session_id"]
        assert session_id.startswith("sess-")

        # 2. Continue conversation
        response2 = await client.post("/agent/chat", json={
            "message": "Tell me about market analysis",
            "session_id": session_id,
            "character_id": 1117367444
        })

        assert response2.status_code == 200
        assert response2.json()["session_id"] == session_id

        # 3. Get session state
        response3 = await client.get(f"/agent/session/{session_id}")

        assert response3.status_code == 200
        session_data = response3.json()
        assert len(session_data["messages"]) >= 2  # At least 2 user messages

        # 4. Delete session
        response4 = await client.delete(f"/agent/session/{session_id}")

        assert response4.status_code == 200

        # 5. Verify deleted
        response5 = await client.get(f"/agent/session/{session_id}")
        assert response5.status_code == 404


@pytest.mark.asyncio
async def test_multiple_concurrent_sessions(test_app):
    """Test multiple sessions can exist independently."""
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        # Create session 1
        response1 = await client.post("/agent/chat", json={
            "message": "Session 1 message",
            "session_id": None,
            "character_id": 1117367444
        })
        session1_id = response1.json()["session_id"]

        # Create session 2
        response2 = await client.post("/agent/chat", json={
            "message": "Session 2 message",
            "session_id": None,
            "character_id": 526379435
        })
        session2_id = response2.json()["session_id"]

        # Verify different sessions
        assert session1_id != session2_id

        # Get session 1
        response3 = await client.get(f"/agent/session/{session1_id}")
        assert response3.json()["character_id"] == 1117367444

        # Get session 2
        response4 = await client.get(f"/agent/session/{session2_id}")
        assert response4.json()["character_id"] == 526379435

        # Cleanup
        await client.delete(f"/agent/session/{session1_id}")
        await client.delete(f"/agent/session/{session2_id}")
