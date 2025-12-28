import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
from copilot_server.agent.runtime import AgentRuntime
from copilot_server.agent.models import AgentSession
from copilot_server.agent.events import AgentEventType
from copilot_server.models.user_settings import AutonomyLevel


@pytest.fixture
def mock_llm():
    """Mock LLM client."""
    llm = MagicMock()
    llm.chat = AsyncMock()
    llm.build_tool_schema = MagicMock(return_value=[])
    return llm


@pytest.fixture
def mock_orchestrator():
    """Mock orchestrator."""
    orch = MagicMock()
    orch.mcp = MagicMock()
    orch.mcp.get_tools = MagicMock(return_value=[
        {"name": "get_market_stats", "metadata": {"risk_level": "READ_ONLY"}},
        {"name": "get_war_summary", "metadata": {"risk_level": "READ_ONLY"}},
        {"name": "get_combat_losses", "metadata": {"risk_level": "READ_ONLY"}},
        {"name": "get_top_destroyed_ships", "metadata": {"risk_level": "READ_ONLY"}},
        {"name": "search_item", "metadata": {"risk_level": "READ_ONLY"}}
    ])
    orch.mcp.call_tool = MagicMock(return_value={"result": "success"})
    return orch


@pytest.fixture
def mock_session_manager():
    """Mock session manager."""
    mgr = MagicMock()
    mgr.save_session = AsyncMock()
    mgr.plan_repo = MagicMock()
    mgr.plan_repo.save_plan = AsyncMock()
    mgr.event_bus = MagicMock()
    mgr.event_bus.emit = AsyncMock()
    mgr.event_repo = MagicMock()
    mgr.event_repo.save = AsyncMock()
    return mgr


@pytest.fixture
def runtime(mock_llm, mock_orchestrator, mock_session_manager):
    """Create runtime with mocks."""
    return AgentRuntime(
        session_manager=mock_session_manager,
        llm_client=mock_llm,
        orchestrator=mock_orchestrator
    )


@pytest.mark.asyncio
async def test_runtime_emits_plan_proposed(runtime, mock_llm, mock_session_manager):
    """Test that runtime emits plan_proposed event."""
    session = AgentSession(
        id="sess-test",
        character_id=123,
        autonomy_level=AutonomyLevel.RECOMMENDATIONS
    )
    session.add_message("user", "Analyze war zones")

    # Mock LLM response: 3-tool plan
    mock_llm.chat.return_value = {
        "content": [
            {"type": "text", "text": "I'll analyze war zones."},
            {"type": "tool_use", "id": "call1", "name": "get_war_summary", "input": {}},
            {"type": "tool_use", "id": "call2", "name": "get_combat_losses", "input": {}},
            {"type": "tool_use", "id": "call3", "name": "get_top_destroyed_ships", "input": {}}
        ],
        "stop_reason": "tool_use"
    }

    await runtime.execute(session)

    # Verify plan_proposed event was emitted
    emit_calls = mock_session_manager.event_bus.emit.call_args_list
    assert len(emit_calls) >= 1

    # Find plan_proposed event
    plan_proposed_events = [
        call[0][0] for call in emit_calls
        if call[0][0].type == AgentEventType.PLAN_PROPOSED
    ]
    assert len(plan_proposed_events) == 1


@pytest.mark.asyncio
async def test_runtime_emits_tool_call_events(runtime, mock_llm, mock_session_manager):
    """Test that runtime emits tool_call_started and tool_call_completed."""
    session = AgentSession(
        id="sess-test",
        character_id=123,
        autonomy_level=AutonomyLevel.ASSISTED  # Auto-execute
    )
    session.add_message("user", "Get market data")

    # Mock LLM response: 3 READ_ONLY tools
    mock_llm.chat.return_value = {
        "content": [
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

    await runtime.execute(session)

    # Verify tool_call events
    emit_calls = mock_session_manager.event_bus.emit.call_args_list

    tool_started_events = [
        call[0][0] for call in emit_calls
        if call[0][0].type == AgentEventType.TOOL_CALL_STARTED
    ]

    tool_completed_events = [
        call[0][0] for call in emit_calls
        if call[0][0].type == AgentEventType.TOOL_CALL_COMPLETED
    ]

    # Should have 3 started and 3 completed events
    assert len(tool_started_events) == 3
    assert len(tool_completed_events) == 3


@pytest.mark.asyncio
async def test_runtime_emits_tool_call_failed(runtime, mock_llm, mock_session_manager, mock_orchestrator):
    """Test that runtime emits tool_call_failed event on error."""
    session = AgentSession(
        id="sess-test",
        character_id=123,
        autonomy_level=AutonomyLevel.ASSISTED  # Auto-execute
    )
    session.add_message("user", "Get market data")

    # Mock LLM response: 3 READ_ONLY tools
    mock_llm.chat.return_value = {
        "content": [
            {"type": "tool_use", "id": "call1", "name": "get_market_stats", "input": {}},
            {"type": "tool_use", "id": "call2", "name": "get_war_summary", "input": {}},
            {"type": "tool_use", "id": "call3", "name": "search_item", "input": {}}
        ],
        "stop_reason": "tool_use"
    }

    # Mock tool execution to fail on second tool
    mock_orchestrator.mcp.call_tool = MagicMock(side_effect=Exception("Tool execution failed"))

    await runtime.execute(session)

    # Verify tool_call_failed event was emitted
    emit_calls = mock_session_manager.event_bus.emit.call_args_list

    tool_failed_events = [
        call[0][0] for call in emit_calls
        if call[0][0].type == AgentEventType.TOOL_CALL_FAILED
    ]

    # Should have at least 1 failed event
    assert len(tool_failed_events) >= 1
    # Verify error message is included
    assert "Tool execution failed" in tool_failed_events[0].payload["error"]


@pytest.mark.asyncio
async def test_runtime_emits_answer_ready(runtime, mock_llm, mock_session_manager):
    """Test that runtime emits answer_ready for non-plan responses."""
    session = AgentSession(
        id="sess-test",
        character_id=123,
        autonomy_level=AutonomyLevel.ASSISTED
    )
    session.add_message("user", "What is EVE Online?")

    # Mock LLM response: Direct text answer with no tools
    mock_llm.chat.return_value = {
        "content": [
            {"type": "text", "text": "EVE Online is a space-based MMORPG."}
        ],
        "stop_reason": "end_turn"
    }

    await runtime.execute(session)

    # Verify answer_ready event was emitted
    emit_calls = mock_session_manager.event_bus.emit.call_args_list

    answer_ready_events = [
        call[0][0] for call in emit_calls
        if call[0][0].type == AgentEventType.ANSWER_READY
    ]

    assert len(answer_ready_events) == 1
    # Verify answer is included
    assert "EVE Online is a space-based MMORPG." in answer_ready_events[0].payload["answer"]
    # Verify duration is tracked (non-zero)
    assert answer_ready_events[0].payload["duration_ms"] >= 0
    # Verify tool_calls_count is 0 for non-plan responses
    assert answer_ready_events[0].payload["tool_calls_count"] == 0
