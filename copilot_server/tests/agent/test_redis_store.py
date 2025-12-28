import pytest
import redis.asyncio as redis
from copilot_server.agent.redis_store import RedisSessionStore
from copilot_server.agent.models import AgentSession, SessionStatus
from copilot_server.models.user_settings import AutonomyLevel

@pytest.fixture
async def redis_store():
    """Create RedisSessionStore for testing."""
    store = RedisSessionStore(
        redis_url="redis://localhost:6379",
        ttl_seconds=3600
    )
    await store.connect()
    yield store
    await store.disconnect()

    # Cleanup test data
    r = await redis.from_url("redis://localhost:6379")
    await r.flushdb()
    await r.aclose()

@pytest.mark.asyncio
async def test_save_and_load_session(redis_store):
    """Test saving and loading session from Redis."""
    session = AgentSession(
        id="sess-test-123",
        character_id=1117367444,
        autonomy_level=AutonomyLevel.RECOMMENDATIONS,
        status=SessionStatus.IDLE
    )

    # Save
    await redis_store.save(session)

    # Load
    loaded = await redis_store.load("sess-test-123")

    assert loaded is not None
    assert loaded.id == session.id
    assert loaded.character_id == session.character_id
    assert loaded.status == session.status

@pytest.mark.asyncio
async def test_load_nonexistent_session(redis_store):
    """Test loading non-existent session returns None."""
    loaded = await redis_store.load("sess-nonexistent")
    assert loaded is None

@pytest.mark.asyncio
async def test_delete_session(redis_store):
    """Test deleting session from Redis."""
    session = AgentSession(
        id="sess-test-456",
        character_id=1117367444
    )

    await redis_store.save(session)
    assert await redis_store.exists("sess-test-456") is True

    await redis_store.delete("sess-test-456")
    assert await redis_store.exists("sess-test-456") is False
