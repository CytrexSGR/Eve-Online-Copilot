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
    from unittest.mock import MagicMock

    # Mock LLM and orchestrator
    llm_client = AsyncMock()
    llm_client.chat.return_value = {
        "content": [{"type": "text", "text": "Hello! How can I help?"}],
        "stop_reason": "end_turn"
    }

    orchestrator = MagicMock()
    orchestrator.mcp = MagicMock()
    orchestrator.mcp.get_tools = MagicMock(return_value=[])
    llm_client.build_tool_schema = MagicMock(return_value=[])

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
async def test_agent_chat_creates_session(test_app):
    """Test POST /agent/chat creates new session."""
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        response = await client.post("/agent/chat", json={
            "message": "Hello",
            "session_id": None,
            "character_id": 1117367444
        })

        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert data["session_id"].startswith("sess-")
        assert data["status"] in ["idle", "planning", "executing", "completed"]


@pytest.mark.asyncio
async def test_agent_chat_continues_session(test_app):
    """Test POST /agent/chat continues existing session."""
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        # Create session
        response1 = await client.post("/agent/chat", json={
            "message": "Hello",
            "session_id": None,
            "character_id": 1117367444
        })
        session_id = response1.json()["session_id"]

        # Continue session
        response2 = await client.post("/agent/chat", json={
            "message": "What's next?",
            "session_id": session_id,
            "character_id": 1117367444
        })

        assert response2.status_code == 200
        assert response2.json()["session_id"] == session_id


@pytest.mark.asyncio
async def test_get_session(test_app):
    """Test GET /agent/session/{id}."""
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        # Create session
        response1 = await client.post("/agent/chat", json={
            "message": "Hello",
            "session_id": None,
            "character_id": 1117367444
        })
        session_id = response1.json()["session_id"]

        # Get session
        response2 = await client.get(f"/agent/session/{session_id}")

        assert response2.status_code == 200
        data = response2.json()
        assert data["id"] == session_id
        assert data["character_id"] == 1117367444


@pytest.mark.asyncio
async def test_delete_session(test_app):
    """Test DELETE /agent/session/{id}."""
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        # Create session
        response1 = await client.post("/agent/chat", json={
            "message": "Hello",
            "session_id": None,
            "character_id": 1117367444
        })
        session_id = response1.json()["session_id"]

        # Delete session
        response2 = await client.delete(f"/agent/session/{session_id}")

        assert response2.status_code == 200

        # Verify deleted
        response3 = await client.get(f"/agent/session/{session_id}")
        assert response3.status_code == 404
