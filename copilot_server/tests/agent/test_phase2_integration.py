"""
Integration tests for Agent Runtime Phase 2.
Tests end-to-end plan detection, auto-execute decision, and approval workflow.
"""

import pytest
import asyncpg
from copilot_server.agent.sessions import AgentSessionManager
from copilot_server.agent.runtime import AgentRuntime
from copilot_server.agent.models import AgentSession, SessionStatus, PlanStatus
from copilot_server.models.user_settings import AutonomyLevel, get_default_settings
from unittest.mock import AsyncMock, MagicMock

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
    await conn.execute("DELETE FROM agent_sessions WHERE id LIKE 'sess-integ%'")
    await conn.execute("DELETE FROM agent_plans WHERE id LIKE 'plan-integ%'")
    await conn.close()


@pytest.mark.asyncio
async def test_end_to_end_plan_approval_workflow(session_manager, cleanup_test_data):
    """
    Test complete workflow:
    1. User sends message
    2. LLM proposes 3+ tool plan
    3. Runtime detects plan
    4. Auto-execute decision (L1 + WRITE = wait for approval)
    5. Session status = WAITING_APPROVAL
    6. User approves via API
    7. Plan executes
    8. Session status = COMPLETED
    """
    # Mock LLM and orchestrator
    mock_llm = MagicMock()
    mock_llm.chat = AsyncMock()
    mock_llm.build_tool_schema = MagicMock(return_value=[])

    mock_mcp = MagicMock()
    mock_mcp.get_tools = MagicMock(return_value=[
        {"name": "get_production_chain", "metadata": {"risk_level": "READ_ONLY"}},
        {"name": "create_shopping_list", "metadata": {"risk_level": "WRITE_LOW_RISK"}},
        {"name": "add_shopping_items", "metadata": {"risk_level": "WRITE_LOW_RISK"}}
    ])
    mock_mcp.call_tool = MagicMock(return_value={"result": "success"})

    mock_orchestrator = MagicMock()
    mock_orchestrator.mcp = mock_mcp

    runtime = AgentRuntime(
        session_manager=session_manager,
        llm_client=mock_llm,
        orchestrator=mock_orchestrator
    )

    # 1. Create session and send message
    session = await session_manager.create_session(
        character_id=123,
        autonomy_level=AutonomyLevel.RECOMMENDATIONS
    )
    session.id = "sess-integ-test"  # Override for cleanup
    session.add_message("user", "Create shopping list for 10 Caracals")
    await session_manager.save_session(session)

    # 2. Mock LLM response: 3-tool plan with WRITE operations
    mock_llm.chat.return_value = {
        "content": [
            {"type": "text", "text": "I'll create a shopping list for 10 Caracals."},
            {"type": "tool_use", "id": "call1", "name": "get_production_chain", "input": {"type_id": 621, "quantity": 10}},
            {"type": "tool_use", "id": "call2", "name": "create_shopping_list", "input": {"name": "10 Caracals"}},
            {"type": "tool_use", "id": "call3", "name": "add_shopping_items", "input": {"list_id": "test"}}
        ],
        "stop_reason": "tool_use"
    }

    # 3-5. Execute runtime (should detect plan and wait for approval)
    await runtime.execute(session)

    # Reload session
    session = await session_manager.load_session(session.id)

    assert session.status == SessionStatus.WAITING_APPROVAL
    assert "pending_plan_id" in session.context

    # Load plan
    plan_id = session.context["pending_plan_id"]
    plan = await session_manager.plan_repo.load_plan(plan_id)

    assert plan is not None
    assert plan.status == PlanStatus.PROPOSED
    assert plan.auto_executing is False
    assert len(plan.steps) == 3

    # 6. Approve plan (simulate API call)
    plan.status = PlanStatus.APPROVED
    await session_manager.plan_repo.save_plan(plan)

    session.status = SessionStatus.EXECUTING
    session.context["current_plan_id"] = plan.id
    del session.context["pending_plan_id"]
    await session_manager.save_session(session)

    # 7. Execute plan
    await runtime._execute_plan(session, plan)

    # 8. Verify completion
    session = await session_manager.load_session(session.id)
    assert session.status == SessionStatus.COMPLETED

    plan = await session_manager.plan_repo.load_plan(plan_id)
    assert plan.status == PlanStatus.COMPLETED
    assert plan.duration_ms is not None


@pytest.mark.asyncio
async def test_l1_auto_executes_read_only_plan(session_manager, cleanup_test_data):
    """L1 autonomy auto-executes pure READ_ONLY plans."""
    # Mock LLM and orchestrator
    mock_llm = MagicMock()
    mock_llm.chat = AsyncMock()
    mock_llm.build_tool_schema = MagicMock(return_value=[])

    mock_mcp = MagicMock()
    mock_mcp.get_tools = MagicMock(return_value=[
        {"name": "get_war_summary", "metadata": {"risk_level": "READ_ONLY"}},
        {"name": "get_combat_losses", "metadata": {"risk_level": "READ_ONLY"}},
        {"name": "get_top_destroyed_ships", "metadata": {"risk_level": "READ_ONLY"}}
    ])
    mock_mcp.call_tool = MagicMock(return_value={"result": "data"})

    mock_orchestrator = MagicMock()
    mock_orchestrator.mcp = mock_mcp

    runtime = AgentRuntime(
        session_manager=session_manager,
        llm_client=mock_llm,
        orchestrator=mock_orchestrator
    )

    # Create session
    session = await session_manager.create_session(
        character_id=123,
        autonomy_level=AutonomyLevel.RECOMMENDATIONS
    )
    session.id = "sess-integ-auto"
    session.add_message("user", "Analyze war zones")
    await session_manager.save_session(session)

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

    # Execute (should auto-execute)
    await runtime.execute(session)

    # Verify auto-executed
    session = await session_manager.load_session(session.id)
    assert session.status == SessionStatus.COMPLETED
    assert "current_plan_id" in session.context

    # Verify plan was executed
    plan_id = session.context["current_plan_id"]
    plan = await session_manager.plan_repo.load_plan(plan_id)
    assert plan.status == PlanStatus.COMPLETED
    assert plan.auto_executing is True
