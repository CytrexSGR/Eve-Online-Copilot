import pytest
import asyncpg
from copilot_server.agent.pg_repository import PostgresSessionRepository
from copilot_server.agent.models import AgentSession, AgentMessage, SessionStatus
from copilot_server.models.user_settings import AutonomyLevel

@pytest.fixture
async def pg_repo():
    """Create PostgresSessionRepository for testing."""
    repo = PostgresSessionRepository(
        database="eve_sde",
        user="eve",
        password="EvE_Pr0ject_2024",
        host="localhost"
    )
    await repo.connect()
    yield repo
    await repo.disconnect()

    # Cleanup test data
    conn = await asyncpg.connect(
        database="eve_sde",
        user="eve",
        password="EvE_Pr0ject_2024",
        host="localhost"
    )
    await conn.execute("DELETE FROM agent_sessions WHERE id LIKE 'sess-test-%'")
    await conn.close()

@pytest.mark.asyncio
async def test_save_session_to_postgres(pg_repo):
    """Test saving session to PostgreSQL."""
    session = AgentSession(
        id="sess-test-789",
        character_id=1117367444,
        autonomy_level=AutonomyLevel.RECOMMENDATIONS,
        status=SessionStatus.IDLE
    )

    await pg_repo.save_session(session)

    # Verify in database
    conn = await asyncpg.connect(
        database="eve_sde",
        user="eve",
        password="EvE_Pr0ject_2024",
        host="localhost"
    )
    result = await conn.fetchrow(
        "SELECT * FROM agent_sessions WHERE id = $1",
        session.id
    )
    await conn.close()

    assert result is not None
    assert result['character_id'] == 1117367444
    assert result['status'] == 'idle'

@pytest.mark.asyncio
async def test_load_session_from_postgres(pg_repo):
    """Test loading session from PostgreSQL."""
    session = AgentSession(
        id="sess-test-101",
        character_id=1117367444
    )

    await pg_repo.save_session(session)
    loaded = await pg_repo.load_session("sess-test-101")

    assert loaded is not None
    assert loaded.id == session.id
    assert loaded.character_id == session.character_id

@pytest.mark.asyncio
async def test_save_message_to_postgres(pg_repo):
    """Test saving message to PostgreSQL."""
    session = AgentSession(
        id="sess-test-202",
        character_id=1117367444
    )
    await pg_repo.save_session(session)

    message = AgentMessage(
        session_id="sess-test-202",
        role="user",
        content="What's profitable?"
    )

    await pg_repo.save_message(message)

    # Verify in database
    conn = await asyncpg.connect(
        database="eve_sde",
        user="eve",
        password="EvE_Pr0ject_2024",
        host="localhost"
    )
    result = await conn.fetchrow(
        "SELECT * FROM agent_messages WHERE session_id = $1",
        session.id
    )
    await conn.close()

    assert result is not None
    assert result['role'] == 'user'
    assert result['content'] == "What's profitable?"
