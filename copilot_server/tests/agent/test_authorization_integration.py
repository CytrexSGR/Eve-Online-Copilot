import pytest
from unittest.mock import MagicMock, AsyncMock
from copilot_server.agent.authorization import AuthorizationChecker
from copilot_server.agent.runtime import AgentRuntime
from copilot_server.agent.models import AgentSession, Plan, PlanStep
from copilot_server.models.user_settings import AutonomyLevel, RiskLevel


@pytest.fixture
def auth_checker():
    """Create authorization checker."""
    checker = AuthorizationChecker()

    # Mock user blacklist
    checker.user_blacklists = {
        123: ["delete_bookmark", "dangerous_tool"]
    }

    return checker


def test_check_authorization_allowed():
    """Test authorization check for allowed tool."""
    checker = AuthorizationChecker()

    allowed, reason = checker.check_authorization(
        character_id=123,
        tool_name="get_market_stats",
        arguments={}
    )

    assert allowed is True
    assert reason is None


def test_check_authorization_blacklisted():
    """Test authorization check for blacklisted tool."""
    checker = AuthorizationChecker()
    checker.user_blacklists = {
        123: ["delete_bookmark"]
    }

    allowed, reason = checker.check_authorization(
        character_id=123,
        tool_name="delete_bookmark",
        arguments={}
    )

    assert allowed is False
    assert "blacklisted" in reason.lower()


def test_check_authorization_dangerous_args():
    """Test authorization check for dangerous arguments."""
    checker = AuthorizationChecker()

    # SQL injection attempt
    allowed, reason = checker.check_authorization(
        character_id=123,
        tool_name="search_item",
        arguments={"query": "'; DROP TABLE users;--"}
    )

    assert allowed is False
    assert "dangerous" in reason.lower()


@pytest.mark.asyncio
async def test_runtime_respects_authorization():
    """Test that runtime checks authorization before executing tools."""
    # Create mocks
    mock_session_manager = MagicMock()
    mock_session_manager.save_session = AsyncMock()
    mock_session_manager.plan_repo = MagicMock()
    mock_session_manager.plan_repo.save_plan = AsyncMock()
    mock_session_manager.event_bus = MagicMock()
    mock_session_manager.event_bus.emit = AsyncMock()
    mock_session_manager.event_repo = MagicMock()
    mock_session_manager.event_repo.save = AsyncMock()

    mock_llm = MagicMock()
    mock_orchestrator = MagicMock()

    # Create authorization checker
    auth_checker = AuthorizationChecker()
    auth_checker.user_blacklists = {
        123: ["delete_bookmark"]
    }

    # Create runtime with auth checker
    runtime = AgentRuntime(
        session_manager=mock_session_manager,
        llm_client=mock_llm,
        orchestrator=mock_orchestrator,
        auth_checker=auth_checker
    )

    # Create session
    session = AgentSession(
        id="sess-test",
        character_id=123,
        autonomy_level=AutonomyLevel.ASSISTED
    )

    # Create plan with blacklisted tool
    plan = Plan(
        id="plan-test",
        session_id="sess-test",
        purpose="Test plan",
        steps=[
            PlanStep(tool="get_bookmarks", arguments={}, risk_level=RiskLevel.READ_ONLY),
            PlanStep(tool="delete_bookmark", arguments={"id": 1}, risk_level=RiskLevel.WRITE_HIGH_RISK)
        ],
        max_risk_level=RiskLevel.WRITE_HIGH_RISK
    )

    # Execute plan
    await runtime._execute_plan(session, plan)

    # Verify authorization_denied event was emitted
    emit_calls = mock_session_manager.event_bus.emit.call_args_list
    auth_denied_events = [
        call[0][0] for call in emit_calls
        if hasattr(call[0][0], 'type') and call[0][0].type.value == "authorization_denied"
    ]

    assert len(auth_denied_events) >= 1
