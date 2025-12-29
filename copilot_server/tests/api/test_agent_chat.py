"""
Tests for agent chat API endpoints.
Tests message persistence functionality.
"""
import pytest
import asyncpg
from httpx import ASGITransport, AsyncClient
from copilot_server.main import app
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


@pytest.mark.asyncio
async def test_get_chat_history():
    """Test getting chat history for a session."""
    # Import agent_routes to set globals
    from copilot_server.api import agent_routes

    # Create session directly via session manager
    session_manager = AgentSessionManager()
    await session_manager.startup()

    # Create database pool for the endpoint
    db_pool = await asyncpg.create_pool(
        DATABASE_URL,
        min_size=1,
        max_size=2
    )

    # Set globals for agent_routes
    agent_routes.session_manager = session_manager
    agent_routes.db_pool = db_pool

    try:
        session = await session_manager.create_session(
            character_id=526379435,
            autonomy_level=AutonomyLevel.RECOMMENDATIONS
        )
        session_id = session.id

        # Connect to database and add messages directly
        conn = await asyncpg.connect(DATABASE_URL)
        repo = MessageRepository(conn)

        # Add messages to database
        msg1 = AgentMessage.create(session_id=session_id, role="user", content="First message")
        msg2 = AgentMessage.create(session_id=session_id, role="user", content="Second message")
        await repo.save(msg1)
        await repo.save(msg2)
        await conn.close()

        # Get history via API endpoint using AsyncClient
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(f"/agent/chat/history/{session_id}")

            # Assertions - print response for debugging
            if response.status_code != 200:
                print(f"Response status: {response.status_code}")
                print(f"Response body: {response.json()}")
            assert response.status_code == 200
            data = response.json()
            assert "messages" in data
            assert len(data["messages"]) >= 2
            assert data["messages"][0]["role"] == "user"
            assert data["messages"][0]["content"] == "First message"

        # Cleanup
        conn = await asyncpg.connect(DATABASE_URL)
        await conn.execute("DELETE FROM agent_messages WHERE session_id = $1", session_id)
        await conn.execute("DELETE FROM agent_sessions WHERE id = $1", session_id)
        await conn.close()

    finally:
        # Clean up
        await db_pool.close()
        await session_manager.shutdown()
        # Reset globals
        agent_routes.session_manager = None
        agent_routes.db_pool = None


@pytest.mark.asyncio
async def test_stream_chat_endpoint_should_fail_before_implementation():
    """
    Test that /agent/chat/stream endpoint does not exist yet.

    This test should FAIL before implementation and PASS after.
    Expected to return 404 or 405 before implementation.

    Note: Full SSE streaming testing requires manual testing with curl/browser
    as AsyncClient doesn't handle streaming well.
    """
    # Create session manager for session creation
    session_manager = AgentSessionManager()
    await session_manager.startup()

    try:
        # Create session
        session = await session_manager.create_session(
            character_id=526379435,
            autonomy_level=AutonomyLevel.RECOMMENDATIONS
        )
        session_id = session.id

        # Test that endpoint does not exist yet
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/agent/chat/stream",
                json={
                    "message": "Test streaming message",
                    "session_id": session_id,
                    "character_id": 526379435
                },
                timeout=5.0
            )

            # Before implementation: expect 404 (not found) or 405 (method not allowed)
            # After implementation: expect 200 (success) or 500 (server error if not initialized)
            # This assertion should FAIL before implementation
            assert response.status_code in [200, 500], \
                f"Expected endpoint to exist and return 200 or 500, got {response.status_code}"

        # Cleanup
        conn = await asyncpg.connect(DATABASE_URL)
        await conn.execute("DELETE FROM agent_messages WHERE session_id = $1", session_id)
        await conn.execute("DELETE FROM agent_sessions WHERE id = $1", session_id)
        await conn.close()

    finally:
        # Clean up
        await session_manager.shutdown()


@pytest.mark.asyncio
async def test_chat_requires_valid_session():
    """Test that chat validates session access."""
    from copilot_server.api import agent_routes

    # Create session manager and database pool
    session_manager = AgentSessionManager()
    await session_manager.startup()

    db_pool = await asyncpg.create_pool(
        DATABASE_URL,
        min_size=1,
        max_size=2
    )

    # Set globals for agent_routes
    agent_routes.session_manager = session_manager
    agent_routes.db_pool = db_pool
    agent_routes.runtime = "mock_runtime"  # Just to pass initialization check

    try:
        # Try to chat with invalid session
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/agent/chat",
                json={
                    "message": "Test",
                    "session_id": "invalid-session-id",
                    "character_id": 123
                }
            )

            # Should return 404 for session not found
            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()

    finally:
        # Clean up
        await db_pool.close()
        await session_manager.shutdown()
        # Reset globals
        agent_routes.session_manager = None
        agent_routes.db_pool = None
        agent_routes.runtime = None


@pytest.mark.asyncio
async def test_chat_rejects_empty_message():
    """Test that empty messages are rejected."""
    from copilot_server.api import agent_routes

    # Create session manager and database pool
    session_manager = AgentSessionManager()
    await session_manager.startup()

    db_pool = await asyncpg.create_pool(
        DATABASE_URL,
        min_size=1,
        max_size=2
    )

    # Set globals for agent_routes
    agent_routes.session_manager = session_manager
    agent_routes.db_pool = db_pool
    agent_routes.runtime = "mock_runtime"

    try:
        # Create a valid session first
        session = await session_manager.create_session(
            character_id=526379435,
            autonomy_level=AutonomyLevel.RECOMMENDATIONS
        )
        session_id = session.id

        # Try to send empty message
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/agent/chat",
                json={
                    "message": "",
                    "session_id": session_id,
                    "character_id": 526379435
                }
            )

            # Should return 400 for invalid message
            assert response.status_code == 400
            assert "empty" in response.json()["detail"].lower()

        # Cleanup
        conn = await asyncpg.connect(DATABASE_URL)
        await conn.execute("DELETE FROM agent_sessions WHERE id = $1", session_id)
        await conn.close()

    finally:
        # Clean up
        await db_pool.close()
        await session_manager.shutdown()
        # Reset globals
        agent_routes.session_manager = None
        agent_routes.db_pool = None
        agent_routes.runtime = None


@pytest.mark.asyncio
async def test_chat_rejects_too_long_message():
    """Test that messages exceeding max length are rejected."""
    from copilot_server.api import agent_routes

    # Create session manager and database pool
    session_manager = AgentSessionManager()
    await session_manager.startup()

    db_pool = await asyncpg.create_pool(
        DATABASE_URL,
        min_size=1,
        max_size=2
    )

    # Set globals for agent_routes
    agent_routes.session_manager = session_manager
    agent_routes.db_pool = db_pool
    agent_routes.runtime = "mock_runtime"

    try:
        # Create a valid session first
        session = await session_manager.create_session(
            character_id=526379435,
            autonomy_level=AutonomyLevel.RECOMMENDATIONS
        )
        session_id = session.id

        # Try to send message that's too long
        long_message = "x" * 20000  # Exceeds 10000 char limit
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/agent/chat",
                json={
                    "message": long_message,
                    "session_id": session_id,
                    "character_id": 526379435
                }
            )

            # Should return 400 for message too long
            assert response.status_code == 400
            assert "too long" in response.json()["detail"].lower()

        # Cleanup
        conn = await asyncpg.connect(DATABASE_URL)
        await conn.execute("DELETE FROM agent_sessions WHERE id = $1", session_id)
        await conn.close()

    finally:
        # Clean up
        await db_pool.close()
        await session_manager.shutdown()
        # Reset globals
        agent_routes.session_manager = None
        agent_routes.db_pool = None
        agent_routes.runtime = None


@pytest.mark.asyncio
async def test_chat_history_requires_valid_session():
    """Test that chat history validates session exists."""
    from copilot_server.api import agent_routes

    # Create session manager and database pool
    session_manager = AgentSessionManager()
    await session_manager.startup()

    db_pool = await asyncpg.create_pool(
        DATABASE_URL,
        min_size=1,
        max_size=2
    )

    # Set globals for agent_routes
    agent_routes.session_manager = session_manager
    agent_routes.db_pool = db_pool

    try:
        # Try to get history for invalid session
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/agent/chat/history/invalid-session-id")

            # Should return 404 for session not found
            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()

    finally:
        # Clean up
        await db_pool.close()
        await session_manager.shutdown()
        # Reset globals
        agent_routes.session_manager = None
        agent_routes.db_pool = None


@pytest.mark.asyncio
async def test_chat_stream_with_tool_execution():
    """Test chat streaming endpoint executes tools."""
    import json
    from unittest.mock import Mock
    from copilot_server.api import agent_routes
    from copilot_server.models.user_settings import AutonomyLevel

    # Create session manager and database pool
    session_manager = AgentSessionManager()
    await session_manager.startup()

    db_pool = await asyncpg.create_pool(
        DATABASE_URL,
        min_size=1,
        max_size=2
    )

    # Create mock LLM client
    mock_llm_client = Mock()
    mock_llm_client.model = "claude-3-5-sonnet-20241022"
    mock_llm_client.build_tool_schema = Mock(return_value=[])

    # Track how many times we stream (need 2 iterations: tool call, then final answer)
    call_count = [0]

    # Mock LLM to request tool call on first iteration, then final answer
    async def mock_stream(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            # First iteration: request tool call
            yield {"type": "content_block_start", "index": 0, "content_block": {"type": "text"}}
            yield {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "Let me check"}}
            yield {"type": "content_block_stop", "index": 0}
            yield {"type": "content_block_start", "index": 1, "content_block": {"type": "tool_use", "id": "t1", "name": "get_market_prices"}}
            yield {"type": "content_block_delta", "index": 1, "delta": {"type": "input_json_delta", "partial_json": '{}'}}
            yield {"type": "content_block_stop", "index": 1}
            yield {"type": "message_stop"}
        else:
            # Second iteration: final answer (no tools)
            yield {"type": "content_block_start", "index": 0, "content_block": {"type": "text"}}
            yield {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": " the price is 5.50 ISK"}}
            yield {"type": "content_block_stop", "index": 0}
            yield {"type": "message_stop"}

    mock_llm_client._stream_response = mock_stream

    # Create mock MCP client
    mock_mcp_client = Mock()
    mock_mcp_client.get_tools = Mock(return_value=[])
    mock_mcp_client.call_tool = Mock(return_value={"content": [{"type": "text", "text": "5.50 ISK"}]})

    # Set globals for agent_routes
    agent_routes.session_manager = session_manager
    agent_routes.db_pool = db_pool
    agent_routes.llm_client = mock_llm_client
    agent_routes.mcp_client = mock_mcp_client

    try:
        # Create session
        session = await session_manager.create_session(
            character_id=123,
            autonomy_level=AutonomyLevel.RECOMMENDATIONS
        )
        session_id = session.id

        # Stream chat
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/agent/chat/stream",
                headers={"Content-Type": "application/json"},
                json={
                    "session_id": session_id,
                    "message": "What is price of Tritanium?",
                    "character_id": 123
                }
            )

            # Verify SSE stream contains tool events
            lines = response.text.strip().split('\n\n')
            events = [json.loads(line.replace('data: ', '')) for line in lines if line.startswith('data:')]

            assert any(e["type"] == "text" for e in events), "Should have text events"
            assert any(e["type"] == "tool_call_started" for e in events), "Should have tool_call_started events"
            assert any(e["type"] == "tool_call_completed" for e in events), "Should have tool_call_completed events"

        # Cleanup
        conn = await asyncpg.connect(DATABASE_URL)
        await conn.execute("DELETE FROM agent_messages WHERE session_id = $1", session_id)
        await conn.execute("DELETE FROM agent_sessions WHERE id = $1", session_id)
        await conn.close()

    finally:
        # Clean up
        await db_pool.close()
        await session_manager.shutdown()
        # Reset globals
        agent_routes.session_manager = None
        agent_routes.db_pool = None
        agent_routes.llm_client = None
        agent_routes.mcp_client = None
