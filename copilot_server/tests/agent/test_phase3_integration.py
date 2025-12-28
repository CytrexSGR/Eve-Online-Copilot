"""
Integration tests for Agent Runtime Phase 3.
Tests event streaming, authorization, and retry logic with real AgentSessionManager.
"""

import pytest
import asyncio
import asyncpg
from copilot_server.agent.sessions import AgentSessionManager
from copilot_server.agent.runtime import AgentRuntime
from copilot_server.agent.authorization import AuthorizationChecker
from copilot_server.agent.models import AgentSession, Plan, PlanStep
from copilot_server.agent.events import AgentEventType
from copilot_server.models.user_settings import AutonomyLevel, RiskLevel, get_default_settings
from copilot_server.agent.retry_logic import RetryConfig
from unittest.mock import MagicMock, AsyncMock

DATABASE_URL = "postgresql://eve:EvE_Pr0ject_2024@localhost/eve_sde"


@pytest.fixture
async def session_manager():
    """Create real session manager."""
    mgr = AgentSessionManager(
        redis_url="redis://localhost:6379",
        pg_database="eve_sde",
        pg_user="eve",
        pg_password="EvE_Pr0ject_2024"
    )
    await mgr.startup()
    yield mgr
    await mgr.shutdown()


@pytest.fixture
async def cleanup_test_data():
    """Clean up test data after test."""
    yield
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute("DELETE FROM agent_events WHERE session_id LIKE 'sess-phase3%'")
    await conn.execute("DELETE FROM agent_sessions WHERE id LIKE 'sess-phase3%'")
    await conn.execute("DELETE FROM agent_plans WHERE id LIKE 'plan-phase3%'")
    await conn.close()


@pytest.mark.asyncio
async def test_end_to_end_event_streaming(session_manager, cleanup_test_data):
    """
    Test complete event streaming workflow:
    1. Create session
    2. Subscribe to events via EventBus
    3. Execute plan
    4. Verify all events emitted
    5. Verify events saved to database
    """
    # Track received events
    received_events = []

    async def event_handler(event):
        received_events.append(event)

    # Create session
    user_settings = get_default_settings(character_id=123)
    user_settings.autonomy_level = AutonomyLevel.ASSISTED

    session = await session_manager.create_session(
        character_id=123,
        autonomy_level=user_settings.autonomy_level
    )
    session.id = "sess-phase3-streaming"  # Override for cleanup

    # Subscribe to events
    session_manager.event_bus.subscribe(session.id, event_handler)

    # Mock LLM and orchestrator
    mock_llm = MagicMock()
    mock_llm.chat = AsyncMock()
    mock_llm.build_tool_schema = MagicMock(return_value=[])

    mock_mcp = MagicMock()
    mock_mcp.get_tools = MagicMock(return_value=[
        {"name": "get_market_stats", "metadata": {"risk_level": "READ_ONLY"}},
        {"name": "get_war_summary", "metadata": {"risk_level": "READ_ONLY"}},
        {"name": "search_item", "metadata": {"risk_level": "READ_ONLY"}}
    ])
    mock_mcp.call_tool = MagicMock(return_value={"result": "data"})

    mock_orchestrator = MagicMock()
    mock_orchestrator.mcp = mock_mcp

    # Create runtime
    runtime = AgentRuntime(
        session_manager=session_manager,
        llm_client=mock_llm,
        orchestrator=mock_orchestrator
    )

    # Add message
    session.add_message("user", "Analyze market data")
    await session_manager.save_session(session)

    # Mock LLM response: 3 READ_ONLY tools
    mock_llm.chat.return_value = {
        "content": [
            {"type": "text", "text": "I'll analyze market data."},
            {"type": "tool_use", "id": "call1", "name": "get_market_stats", "input": {}},
            {"type": "tool_use", "id": "call2", "name": "get_war_summary", "input": {}},
            {"type": "tool_use", "id": "call3", "name": "search_item", "input": {}}
        ],
        "stop_reason": "tool_use"
    }

    # Second call: return answer
    mock_llm.chat.side_effect = [
        mock_llm.chat.return_value,
        {"content": [{"type": "text", "text": "Analysis complete."}], "stop_reason": "end_turn"}
    ]

    # Execute
    await runtime.execute(session)

    # Wait for async event delivery
    await asyncio.sleep(0.2)

    # Verify events received
    assert len(received_events) >= 3, f"Expected at least 3 events, got {len(received_events)}"

    event_types = [e.type for e in received_events]
    assert AgentEventType.PLAN_PROPOSED in event_types, "PLAN_PROPOSED event not found"
    assert AgentEventType.TOOL_CALL_STARTED in event_types, "TOOL_CALL_STARTED event not found"
    assert AgentEventType.TOOL_CALL_COMPLETED in event_types, "TOOL_CALL_COMPLETED event not found"

    # Verify events saved to database
    saved_events = await session_manager.event_repo.load_by_session(session.id)
    assert len(saved_events) >= 3, f"Expected at least 3 saved events, got {len(saved_events)}"

    # Verify event types are correct
    saved_event_types = [e.type for e in saved_events]
    assert AgentEventType.PLAN_PROPOSED in saved_event_types
    assert AgentEventType.TOOL_CALL_STARTED in saved_event_types
    assert AgentEventType.TOOL_CALL_COMPLETED in saved_event_types


@pytest.mark.asyncio
async def test_authorization_blocks_blacklisted_tool(session_manager, cleanup_test_data):
    """Test that authorization blocks blacklisted tools."""
    # Create runtime with auth checker
    auth_checker = AuthorizationChecker()
    auth_checker.add_to_blacklist(123, "delete_bookmark")

    mock_llm = MagicMock()
    mock_orchestrator = MagicMock()
    mock_orchestrator.mcp = MagicMock()

    runtime = AgentRuntime(
        session_manager=session_manager,
        llm_client=mock_llm,
        orchestrator=mock_orchestrator,
        auth_checker=auth_checker
    )

    # Create session
    session = await session_manager.create_session(
        character_id=123,
        autonomy_level=AutonomyLevel.ASSISTED
    )
    session.id = "sess-phase3-auth"  # Override for cleanup
    await session_manager.save_session(session)  # Save with overridden ID

    # Track events
    received_events = []

    async def event_handler(event):
        received_events.append(event)

    session_manager.event_bus.subscribe(session.id, event_handler)

    # Create plan with blacklisted tool
    plan = Plan(
        session_id=session.id,
        purpose="Test blacklist",
        steps=[
            PlanStep(tool="get_bookmarks", arguments={}, risk_level=RiskLevel.READ_ONLY),
            PlanStep(tool="delete_bookmark", arguments={"id": 1}, risk_level=RiskLevel.WRITE_HIGH_RISK)
        ],
        max_risk_level=RiskLevel.WRITE_HIGH_RISK
    )
    plan.id = "plan-phase3-auth"  # Override for cleanup

    await session_manager.plan_repo.save_plan(plan)

    # Execute plan
    await runtime._execute_plan(session, plan)

    # Wait for events
    await asyncio.sleep(0.2)

    # Verify authorization_denied event
    auth_denied_events = [
        e for e in received_events
        if e.type == AgentEventType.AUTHORIZATION_DENIED
    ]

    assert len(auth_denied_events) == 1, f"Expected 1 AUTHORIZATION_DENIED event, got {len(auth_denied_events)}"
    assert "delete_bookmark" in auth_denied_events[0].payload["tool"]

    # Verify event was saved to database
    saved_events = await session_manager.event_repo.load_by_session(session.id)
    saved_auth_denied = [e for e in saved_events if e.type == AgentEventType.AUTHORIZATION_DENIED]
    assert len(saved_auth_denied) == 1, "AUTHORIZATION_DENIED event should be saved to database"


@pytest.mark.asyncio
async def test_retry_logic_recovers_from_failures(session_manager, cleanup_test_data):
    """Test that retry logic recovers from transient failures."""
    # Create runtime with fast retry config
    retry_config = RetryConfig(
        max_retries=2,
        base_delay_ms=50
    )

    mock_llm = MagicMock()

    # Mock orchestrator with failing then succeeding tool
    call_count = 0

    def flaky_tool(tool_name, args):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ConnectionError("Temporary network error")
        return {"result": "success"}

    mock_mcp = MagicMock()
    mock_mcp.call_tool = flaky_tool

    mock_orchestrator = MagicMock()
    mock_orchestrator.mcp = mock_mcp

    runtime = AgentRuntime(
        session_manager=session_manager,
        llm_client=mock_llm,
        orchestrator=mock_orchestrator,
        retry_config=retry_config
    )

    # Create session and plan
    session = await session_manager.create_session(
        character_id=123,
        autonomy_level=AutonomyLevel.ASSISTED
    )
    session.id = "sess-phase3-retry"  # Override for cleanup
    await session_manager.save_session(session)  # Save with overridden ID

    plan = Plan(
        session_id=session.id,
        purpose="Test retry",
        steps=[
            PlanStep(tool="test_tool", arguments={}, risk_level=RiskLevel.READ_ONLY)
        ],
        max_risk_level=RiskLevel.READ_ONLY
    )
    plan.id = "plan-phase3-retry"  # Override for cleanup

    await session_manager.plan_repo.save_plan(plan)

    # Execute plan
    await runtime._execute_plan(session, plan)

    # Verify tool was called 3 times (2 failures + 1 success)
    assert call_count == 3, f"Expected 3 tool calls (2 failures + 1 success), got {call_count}"

    # Verify plan completed successfully
    reloaded_plan = await session_manager.plan_repo.load_plan(plan.id)
    assert reloaded_plan.status.value == "completed", f"Expected plan status 'completed', got '{reloaded_plan.status.value}'"

    # Verify events were emitted for retries
    saved_events = await session_manager.event_repo.load_by_session(session.id)

    # Should have: tool_call_started, tool_call_completed (after retries succeeded)
    event_types = [e.type for e in saved_events]
    assert AgentEventType.TOOL_CALL_STARTED in event_types
    assert AgentEventType.TOOL_CALL_COMPLETED in event_types
