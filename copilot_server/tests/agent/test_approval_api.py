"""
Tests for plan approval API endpoints.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI

from copilot_server.agent.models import AgentSession, Plan, PlanStep, PlanStatus, SessionStatus
from copilot_server.models.user_settings import AutonomyLevel, RiskLevel


@pytest.fixture
def mock_session_manager():
    """Mock session manager."""
    mgr = MagicMock()
    mgr.load_session = AsyncMock()
    mgr.save_session = AsyncMock()
    mgr.plan_repo = MagicMock()
    mgr.plan_repo.load_plan = AsyncMock()
    mgr.plan_repo.save_plan = AsyncMock()
    return mgr


@pytest.fixture
def mock_runtime():
    """Mock runtime."""
    runtime = MagicMock()
    runtime._execute_plan = AsyncMock()
    return runtime


@pytest.fixture
async def client():
    """Create async HTTP client with minimal app."""
    # Create minimal FastAPI app with just the agent routes
    from copilot_server.api import agent_routes

    app = FastAPI()
    app.include_router(agent_routes.router)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.mark.asyncio
async def test_execute_endpoint_approves_plan(client, mock_session_manager, mock_runtime):
    """POST /agent/execute approves and executes pending plan."""
    session = AgentSession(
        id="sess-test",
        character_id=123,
        autonomy_level=AutonomyLevel.RECOMMENDATIONS,
        status=SessionStatus.WAITING_APPROVAL
    )
    session.context["pending_plan_id"] = "plan-test"

    plan = Plan(
        id="plan-test",
        session_id="sess-test",
        purpose="Test plan",
        steps=[
            PlanStep(tool="create_shopping_list", arguments={}, risk_level=RiskLevel.WRITE_LOW_RISK)
        ],
        max_risk_level=RiskLevel.WRITE_LOW_RISK,
        status=PlanStatus.PROPOSED
    )

    mock_session_manager.load_session.return_value = session
    mock_session_manager.plan_repo.load_plan.return_value = plan

    # Patch the global instances
    with patch('copilot_server.api.agent_routes.session_manager', mock_session_manager), \
         patch('copilot_server.api.agent_routes.runtime', mock_runtime):

        response = await client.post("/agent/execute", json={
            "session_id": "sess-test",
            "plan_id": "plan-test"
        })

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "executing"
    assert data["message"] == "Plan approved and executing"

    # Verify plan was marked approved
    assert mock_session_manager.plan_repo.save_plan.called
    saved_plan = mock_session_manager.plan_repo.save_plan.call_args[0][0]
    assert saved_plan.status == PlanStatus.APPROVED

    # Verify runtime was called
    assert mock_runtime._execute_plan.called


@pytest.mark.asyncio
async def test_execute_endpoint_session_not_found(client, mock_session_manager, mock_runtime):
    """POST /agent/execute returns 404 if session doesn't exist."""
    mock_session_manager.load_session.return_value = None

    with patch('copilot_server.api.agent_routes.session_manager', mock_session_manager), \
         patch('copilot_server.api.agent_routes.runtime', mock_runtime):
        response = await client.post("/agent/execute", json={
            "session_id": "sess-nonexistent",
            "plan_id": "plan-test"
        })

    assert response.status_code == 404
    assert response.json()["detail"] == "Session not found"


@pytest.mark.asyncio
async def test_execute_endpoint_plan_not_found(client, mock_session_manager, mock_runtime):
    """POST /agent/execute returns 404 if plan doesn't exist."""
    session = AgentSession(
        id="sess-test",
        character_id=123,
        status=SessionStatus.WAITING_APPROVAL
    )

    mock_session_manager.load_session.return_value = session
    mock_session_manager.plan_repo.load_plan.return_value = None

    with patch('copilot_server.api.agent_routes.session_manager', mock_session_manager), \
         patch('copilot_server.api.agent_routes.runtime', mock_runtime):
        response = await client.post("/agent/execute", json={
            "session_id": "sess-test",
            "plan_id": "plan-nonexistent"
        })

    assert response.status_code == 404
    assert response.json()["detail"] == "Plan not found"


@pytest.mark.asyncio
async def test_reject_endpoint_rejects_plan(client, mock_session_manager):
    """POST /agent/reject rejects pending plan."""
    session = AgentSession(
        id="sess-test",
        character_id=123,
        status=SessionStatus.WAITING_APPROVAL
    )
    session.context["pending_plan_id"] = "plan-test"

    plan = Plan(
        id="plan-test",
        session_id="sess-test",
        purpose="Test plan",
        steps=[],
        max_risk_level=RiskLevel.WRITE_LOW_RISK,
        status=PlanStatus.PROPOSED
    )

    mock_session_manager.load_session.return_value = session
    mock_session_manager.plan_repo.load_plan.return_value = plan

    with patch('copilot_server.api.agent_routes.session_manager', mock_session_manager):
        response = await client.post("/agent/reject", json={
            "session_id": "sess-test",
            "plan_id": "plan-test"
        })

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "idle"
    assert data["message"] == "Plan rejected"

    # Verify plan was marked rejected
    saved_plan = mock_session_manager.plan_repo.save_plan.call_args[0][0]
    assert saved_plan.status == PlanStatus.REJECTED

    # Verify session returned to idle
    saved_session = mock_session_manager.save_session.call_args[0][0]
    assert saved_session.status == SessionStatus.IDLE
    assert "pending_plan_id" not in saved_session.context


@pytest.mark.asyncio
async def test_reject_endpoint_session_not_found(client, mock_session_manager):
    """POST /agent/reject returns 404 if session doesn't exist."""
    mock_session_manager.load_session.return_value = None

    with patch('copilot_server.api.agent_routes.session_manager', mock_session_manager):
        response = await client.post("/agent/reject", json={
            "session_id": "sess-nonexistent",
            "plan_id": "plan-test"
        })

    assert response.status_code == 404
