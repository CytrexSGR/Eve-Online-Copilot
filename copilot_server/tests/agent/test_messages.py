import pytest
import asyncpg
from datetime import datetime
from copilot_server.agent.messages import AgentMessage, MessageRepository

DATABASE_URL = "postgresql://eve:EvE_Pr0ject_2024@localhost/eve_sde"

@pytest.fixture
async def db_connection():
    """Provide database connection for tests."""
    conn = await asyncpg.connect(DATABASE_URL)
    yield conn
    await conn.close()

@pytest.fixture
async def message_repo(db_connection):
    """Provide MessageRepository for tests."""
    return MessageRepository(db_connection)

@pytest.fixture
async def test_session(db_connection):
    """Create test session for messages."""
    session_id = "sess-test-123"
    await db_connection.execute("""
        INSERT INTO agent_sessions (id, character_id, autonomy_level, status, message_count)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (id) DO NOTHING
    """, session_id, 526379435, 1, "idle", 0)
    yield session_id
    await db_connection.execute("DELETE FROM agent_messages WHERE session_id = $1", session_id)
    await db_connection.execute("DELETE FROM agent_sessions WHERE id = $1", session_id)

@pytest.fixture
async def test_session_multi(db_connection):
    """Create test session for multiple message tests."""
    session_id = "sess-test-456"
    await db_connection.execute("""
        INSERT INTO agent_sessions (id, character_id, autonomy_level, status, message_count)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (id) DO NOTHING
    """, session_id, 526379435, 1, "idle", 0)
    yield session_id
    await db_connection.execute("DELETE FROM agent_messages WHERE session_id = $1", session_id)
    await db_connection.execute("DELETE FROM agent_sessions WHERE id = $1", session_id)

@pytest.mark.asyncio
async def test_create_and_retrieve_message(message_repo, test_session):
    """Test creating and retrieving a message."""
    # Create message
    message = AgentMessage(
        id="msg-test-123",
        session_id=test_session,
        role="user",
        content="Test message",
        content_blocks=[{"type": "text", "text": "Test message"}]
    )

    await message_repo.save(message)

    # Retrieve message
    retrieved = await message_repo.get_by_id("msg-test-123")

    assert retrieved is not None
    assert retrieved.id == "msg-test-123"
    assert retrieved.role == "user"
    assert retrieved.content == "Test message"


@pytest.mark.asyncio
async def test_get_messages_by_session(message_repo, test_session_multi):
    """Test retrieving all messages for a session."""
    # Create multiple messages
    msg1 = AgentMessage.create(test_session_multi, "user", "Message 1")
    msg2 = AgentMessage.create(test_session_multi, "assistant", "Message 2")
    msg3 = AgentMessage.create(test_session_multi, "user", "Message 3")

    await message_repo.save(msg1)
    await message_repo.save(msg2)
    await message_repo.save(msg3)

    # Retrieve all messages
    messages = await message_repo.get_by_session(test_session_multi)

    assert len(messages) == 3
    assert messages[0].content == "Message 1"
    assert messages[1].content == "Message 2"
    assert messages[2].content == "Message 3"
