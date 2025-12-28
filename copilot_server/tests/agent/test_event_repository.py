import pytest
import asyncpg
from copilot_server.agent.event_repository import EventRepository
from copilot_server.agent.events import AgentEvent, AgentEventType

DATABASE_URL = "postgresql://eve:EvE_Pr0ject_2024@localhost/eve_sde"


@pytest.fixture
async def event_repo():
    """Create event repository."""
    repo = EventRepository(DATABASE_URL)
    await repo.connect()
    yield repo
    await repo.disconnect()


@pytest.fixture
async def test_sessions():
    """Create test sessions and plans in database."""
    conn = await asyncpg.connect(DATABASE_URL)

    # Insert test sessions
    # AutonomyLevel: READ_ONLY=0, RECOMMENDATIONS=1, ASSISTED=2, SUPERVISED=3
    sessions = [
        ("sess-test-save", 123, 1, "{}"),  # RECOMMENDATIONS
        ("sess-test-load", 123, 2, "{}"),  # ASSISTED
        ("sess-test-plan", 123, 2, "{}")   # ASSISTED
    ]

    for session_id, char_id, autonomy, context in sessions:
        await conn.execute("""
            INSERT INTO agent_sessions (id, character_id, autonomy_level, context, status, created_at, updated_at)
            VALUES ($1, $2, $3, $4::jsonb, 'active', NOW(), NOW())
            ON CONFLICT (id) DO NOTHING
        """, session_id, char_id, autonomy, context)

    # Insert test plans
    plans = [
        ("plan-test", "sess-test-save", "Test plan", "{}"),
        ("plan-test-load", "sess-test-plan", "Test plan for loading", "{}")
    ]

    for plan_id, session_id, purpose, plan_data in plans:
        await conn.execute("""
            INSERT INTO agent_plans (id, session_id, purpose, plan_data, status, created_at)
            VALUES ($1, $2, $3, $4::jsonb, 'pending', NOW())
            ON CONFLICT (id) DO NOTHING
        """, plan_id, session_id, purpose, plan_data)

    yield

    # Cleanup events, plans, and sessions
    await conn.execute("DELETE FROM agent_events WHERE session_id LIKE 'sess-test%'")
    await conn.execute("DELETE FROM agent_plans WHERE session_id LIKE 'sess-test%'")
    await conn.execute("DELETE FROM agent_sessions WHERE id LIKE 'sess-test%'")
    await conn.close()


@pytest.fixture
async def cleanup_events(test_sessions):
    """Clean up test events (depends on test_sessions)."""
    yield


@pytest.mark.asyncio
async def test_save_event(event_repo, cleanup_events):
    """Test saving an event to database."""
    event = AgentEvent(
        type=AgentEventType.PLAN_PROPOSED,
        session_id="sess-test-save",
        plan_id="plan-test",
        payload={"test": "data"}
    )

    await event_repo.save(event)

    # Verify saved
    events = await event_repo.load_by_session("sess-test-save")
    assert len(events) >= 1

    saved_event = events[0]
    assert saved_event.session_id == "sess-test-save"
    assert saved_event.plan_id == "plan-test"
    assert saved_event.payload == {"test": "data"}


@pytest.mark.asyncio
async def test_load_by_session(event_repo, cleanup_events):
    """Test loading events by session."""
    # Save multiple events
    for i in range(3):
        event = AgentEvent(
            type=AgentEventType.TOOL_CALL_STARTED,
            session_id="sess-test-load",
            payload={"index": i}
        )
        await event_repo.save(event)

    # Load all events for session
    events = await event_repo.load_by_session("sess-test-load")

    assert len(events) == 3
    # Events should be ordered by timestamp
    assert events[0].payload["index"] == 0
    assert events[1].payload["index"] == 1
    assert events[2].payload["index"] == 2


@pytest.mark.asyncio
async def test_load_by_plan(event_repo, cleanup_events):
    """Test loading events by plan."""
    plan_id = "plan-test-load"

    # Save events for plan
    for i in range(2):
        event = AgentEvent(
            type=AgentEventType.TOOL_CALL_STARTED,
            session_id="sess-test-plan",
            plan_id=plan_id,
            payload={"index": i}
        )
        await event_repo.save(event)

    # Load events for plan
    events = await event_repo.load_by_plan(plan_id)

    assert len(events) == 2
    assert all(e.plan_id == plan_id for e in events)
