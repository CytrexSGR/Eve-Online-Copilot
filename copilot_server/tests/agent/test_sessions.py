# copilot_server/tests/agent/test_sessions.py

import pytest
from copilot_server.agent.sessions import AgentSessionManager
from copilot_server.agent.models import AgentSession, SessionStatus
from copilot_server.models.user_settings import AutonomyLevel

@pytest.fixture
async def session_manager():
    """Create AgentSessionManager for testing."""
    manager = AgentSessionManager(
        redis_url="redis://localhost:6379",
        pg_database="eve_sde",
        pg_user="eve",
        pg_password="EvE_Pr0ject_2024"
    )
    await manager.startup()
    yield manager
    await manager.shutdown()

@pytest.mark.asyncio
async def test_create_session(session_manager):
    """Test creating new session."""
    session = await session_manager.create_session(
        character_id=1117367444,
        autonomy_level=AutonomyLevel.RECOMMENDATIONS
    )

    assert session.id.startswith("sess-")
    assert session.character_id == 1117367444
    assert session.status == SessionStatus.IDLE

@pytest.mark.asyncio
async def test_load_session_from_cache(session_manager):
    """Test loading session from Redis cache."""
    session = await session_manager.create_session(
        character_id=1117367444
    )

    # Load from cache (should hit Redis)
    loaded = await session_manager.load_session(session.id)

    assert loaded is not None
    assert loaded.id == session.id

@pytest.mark.asyncio
async def test_save_and_load_session(session_manager):
    """Test save/load round-trip."""
    session = await session_manager.create_session(
        character_id=1117367444
    )

    # Modify session
    session.add_message("user", "What's profitable?")
    session.status = SessionStatus.PLANNING

    # Save
    await session_manager.save_session(session)

    # Load
    loaded = await session_manager.load_session(session.id)

    assert loaded.status == SessionStatus.PLANNING
    assert len(loaded.messages) == 1
    assert loaded.messages[0].content == "What's profitable?"

@pytest.mark.asyncio
async def test_delete_session(session_manager):
    """Test deleting session."""
    session = await session_manager.create_session(
        character_id=1117367444
    )

    await session_manager.delete_session(session.id)

    loaded = await session_manager.load_session(session.id)
    assert loaded is None
