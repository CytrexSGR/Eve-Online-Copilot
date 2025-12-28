import pytest
import asyncpg
from datetime import datetime
from copilot_server.agent.plan_repository import PlanRepository
from copilot_server.agent.models import Plan, PlanStep, PlanStatus
from copilot_server.models.user_settings import RiskLevel

DATABASE_URL = "postgresql://eve:EvE_Pr0ject_2024@localhost/eve_sde"


@pytest.fixture
async def plan_repo():
    """Create plan repository with connection pool."""
    repo = PlanRepository(DATABASE_URL)
    await repo.connect()
    yield repo
    await repo.disconnect()


@pytest.fixture
async def cleanup_plans():
    """Clean up test plans and sessions after each test."""
    yield
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute("DELETE FROM agent_plans WHERE id LIKE 'plan-test%'")
    await conn.execute("DELETE FROM agent_sessions WHERE id LIKE 'sess-test%'")
    await conn.close()


@pytest.fixture
async def test_session():
    """Create test session in database."""
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute("""
        INSERT INTO agent_sessions (id, character_id, autonomy_level, status, created_at, updated_at, last_activity, archived)
        VALUES ($1, $2, $3, $4, NOW(), NOW(), NOW(), $5)
        ON CONFLICT (id) DO NOTHING
    """, "sess-test", 123, 1, "idle", False)  # autonomy_level=1 (RECOMMENDATIONS)

    await conn.execute("""
        INSERT INTO agent_sessions (id, character_id, autonomy_level, status, created_at, updated_at, last_activity, archived)
        VALUES ($1, $2, $3, $4, NOW(), NOW(), NOW(), $5)
        ON CONFLICT (id) DO NOTHING
    """, "sess-test-multi", 123, 1, "idle", False)  # autonomy_level=1 (RECOMMENDATIONS)

    await conn.close()
    yield
    # Cleanup handled by cleanup_plans fixture


@pytest.mark.asyncio
async def test_save_plan(plan_repo, test_session, cleanup_plans):
    """Test saving a plan to database."""
    plan = Plan(
        id="plan-test-save",
        session_id="sess-test",
        purpose="Test plan",
        steps=[
            PlanStep(tool="get_market_stats", arguments={"type_id": 34}, risk_level=RiskLevel.READ_ONLY),
            PlanStep(tool="get_war_summary", arguments={}, risk_level=RiskLevel.READ_ONLY)
        ],
        max_risk_level=RiskLevel.READ_ONLY,
        auto_executing=True
    )

    await plan_repo.save_plan(plan)

    # Verify saved
    loaded = await plan_repo.load_plan(plan.id)
    assert loaded is not None
    assert loaded.id == plan.id
    assert loaded.session_id == plan.session_id
    assert loaded.purpose == plan.purpose
    assert len(loaded.steps) == 2
    assert loaded.steps[0].tool == "get_market_stats"
    assert loaded.auto_executing is True


@pytest.mark.asyncio
async def test_update_plan_status(plan_repo, test_session, cleanup_plans):
    """Test updating plan status and timestamps."""
    plan = Plan(
        id="plan-test-update",
        session_id="sess-test",
        purpose="Test",
        steps=[
            PlanStep(tool="test_tool", arguments={}, risk_level=RiskLevel.READ_ONLY)
        ],
        max_risk_level=RiskLevel.READ_ONLY,
        status=PlanStatus.PROPOSED
    )

    await plan_repo.save_plan(plan)

    # Update to approved
    plan.status = PlanStatus.APPROVED
    plan.approved_at = datetime.now()
    await plan_repo.save_plan(plan)

    loaded = await plan_repo.load_plan(plan.id)
    assert loaded.status == PlanStatus.APPROVED
    assert loaded.approved_at is not None

    # Update to executing
    plan.status = PlanStatus.EXECUTING
    plan.executed_at = datetime.now()
    await plan_repo.save_plan(plan)

    loaded = await plan_repo.load_plan(plan.id)
    assert loaded.status == PlanStatus.EXECUTING
    assert loaded.executed_at is not None


@pytest.mark.asyncio
async def test_load_plans_by_session(plan_repo, test_session, cleanup_plans):
    """Test loading all plans for a session."""
    session_id = "sess-test-multi"

    plan1 = Plan(
        id="plan-test-multi-1",
        session_id=session_id,
        purpose="Plan 1",
        steps=[PlanStep(tool="tool1", arguments={}, risk_level=RiskLevel.READ_ONLY)],
        max_risk_level=RiskLevel.READ_ONLY
    )

    plan2 = Plan(
        id="plan-test-multi-2",
        session_id=session_id,
        purpose="Plan 2",
        steps=[PlanStep(tool="tool2", arguments={}, risk_level=RiskLevel.WRITE_LOW_RISK)],
        max_risk_level=RiskLevel.WRITE_LOW_RISK
    )

    await plan_repo.save_plan(plan1)
    await plan_repo.save_plan(plan2)

    plans = await plan_repo.load_plans_by_session(session_id)
    assert len(plans) == 2
    assert {p.id for p in plans} == {"plan-test-multi-1", "plan-test-multi-2"}


@pytest.mark.asyncio
async def test_load_nonexistent_plan(plan_repo):
    """Test loading a plan that doesn't exist returns None."""
    plan = await plan_repo.load_plan("plan-nonexistent")
    assert plan is None
