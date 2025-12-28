import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from copilot_server.agent.runtime import AgentRuntime
from copilot_server.agent.models import AgentSession, SessionStatus, Plan, PlanStatus
from copilot_server.models.user_settings import AutonomyLevel, RiskLevel


@pytest.fixture
def mock_llm():
    """Mock LLM client."""
    llm = MagicMock()
    llm.chat = AsyncMock()
    return llm


@pytest.fixture
def mock_orchestrator():
    """Mock orchestrator."""
    orch = MagicMock()
    orch.mcp = MagicMock()
    # Default to empty tools, tests can override this
    orch.mcp.get_tools = MagicMock(return_value=[])
    orch.mcp.call_tool = MagicMock(return_value={"result": "success"})
    return orch


@pytest.fixture
def mock_session_manager():
    """Mock session manager."""
    mgr = MagicMock()
    mgr.save_session = AsyncMock()
    mgr.plan_repo = MagicMock()
    mgr.plan_repo.save_plan = AsyncMock()
    return mgr


def create_runtime(mock_llm, mock_orchestrator, mock_session_manager):
    """Create runtime with mocks - not a fixture because we need to configure mocks first."""
    return AgentRuntime(
        session_manager=mock_session_manager,
        llm_client=mock_llm,
        orchestrator=mock_orchestrator
    )


@pytest.mark.asyncio
async def test_single_tool_executes_directly(mock_llm, mock_orchestrator, mock_session_manager):
    """Single tool call executes directly without plan detection."""
    runtime = create_runtime(mock_llm, mock_orchestrator, mock_session_manager)

    session = AgentSession(
        id="sess-test",
        character_id=123,
        autonomy_level=AutonomyLevel.RECOMMENDATIONS
    )
    session.add_message("user", "What's the price of Tritanium?")

    # Mock LLM response: single tool
    mock_llm.chat.return_value = {
        "content": [
            {"type": "text", "text": "Let me check."},
            {"type": "tool_use", "id": "call1", "name": "get_market_stats", "input": {"type_id": 34}}
        ],
        "stop_reason": "tool_use"
    }

    # Second call: return answer
    mock_llm.chat.side_effect = [
        mock_llm.chat.return_value,
        {"content": [{"type": "text", "text": "Tritanium costs 5.2 ISK."}], "stop_reason": "end_turn"}
    ]

    await runtime.execute(session)

    # Should execute directly, no plan created
    assert session.status == SessionStatus.COMPLETED
    assert "pending_plan" not in session.context


@pytest.mark.asyncio
async def test_multi_tool_creates_plan_l1_read_only(mock_llm, mock_orchestrator, mock_session_manager):
    """L1 with READ_ONLY plan auto-executes."""
    # Configure orchestrator to return READ_ONLY risk levels BEFORE creating runtime
    mock_orchestrator.mcp.get_tools.return_value = [
        {"name": "get_war_summary", "metadata": {"risk_level": "READ_ONLY"}},
        {"name": "get_combat_losses", "metadata": {"risk_level": "READ_ONLY"}},
        {"name": "get_top_destroyed_ships", "metadata": {"risk_level": "READ_ONLY"}}
    ]

    # Create runtime after configuring the mock
    runtime = create_runtime(mock_llm, mock_orchestrator, mock_session_manager)

    session = AgentSession(
        id="sess-test",
        character_id=123,
        autonomy_level=AutonomyLevel.RECOMMENDATIONS
    )
    session.add_message("user", "Analyze war zones.")

    # Mock LLM response: 3 READ_ONLY tools
    mock_llm.chat.return_value = {
        "content": [
            {"type": "text", "text": "I'll analyze war zones."},
            {"type": "tool_use", "id": "call1", "name": "get_war_summary", "input": {}},
            {"type": "tool_use", "id": "call2", "name": "get_combat_losses", "input": {"region_id": 10000002}},
            {"type": "tool_use", "id": "call3", "name": "get_top_destroyed_ships", "input": {}}
        ],
        "stop_reason": "tool_use"
    }

    await runtime.execute(session)

    # Should auto-execute
    assert session.status == SessionStatus.COMPLETED
    assert mock_session_manager.plan_repo.save_plan.called


@pytest.mark.asyncio
async def test_multi_tool_waits_approval_l1_write(mock_llm, mock_orchestrator, mock_session_manager):
    """L1 with WRITE_LOW_RISK plan waits for approval."""
    # Configure orchestrator to return WRITE_LOW_RISK risk levels BEFORE creating runtime
    mock_orchestrator.mcp.get_tools.return_value = [
        {"name": "get_production_chain", "metadata": {"risk_level": "READ_ONLY"}},
        {"name": "create_shopping_list", "metadata": {"risk_level": "WRITE_LOW_RISK"}},
        {"name": "add_shopping_items", "metadata": {"risk_level": "WRITE_LOW_RISK"}}
    ]

    # Create runtime after configuring the mock
    runtime = create_runtime(mock_llm, mock_orchestrator, mock_session_manager)

    session = AgentSession(
        id="sess-test",
        character_id=123,
        autonomy_level=AutonomyLevel.RECOMMENDATIONS
    )
    session.add_message("user", "Create shopping list for 10 Caracals.")

    # Mock LLM response: 3 tools with WRITE_LOW_RISK
    mock_llm.chat.return_value = {
        "content": [
            {"type": "text", "text": "I'll create a shopping list."},
            {"type": "tool_use", "id": "call1", "name": "get_production_chain", "input": {}},
            {"type": "tool_use", "id": "call2", "name": "create_shopping_list", "input": {}},
            {"type": "tool_use", "id": "call3", "name": "add_shopping_items", "input": {}}
        ],
        "stop_reason": "tool_use"
    }

    await runtime.execute(session)

    # Should wait for approval
    assert session.status == SessionStatus.WAITING_APPROVAL
    assert session.context.get("pending_plan_id") is not None
