import pytest
import asyncpg
from datetime import datetime
from copilot_server.agent.messages import AgentMessage, MessageRepository

DATABASE_URL = "postgresql://eve:EvE_Pr0ject_2024@localhost/eve_sde"

@pytest.mark.asyncio
async def test_create_and_retrieve_message():
    """Test creating and retrieving a message."""
    conn = await asyncpg.connect(DATABASE_URL)
    repo = MessageRepository(conn)

    # Create message
    message = AgentMessage(
        id="msg-test-123",
        session_id="sess-test-123",
        role="user",
        content="Test message",
        content_blocks=[{"type": "text", "text": "Test message"}]
    )

    await repo.save(message)

    # Retrieve message
    retrieved = await repo.get_by_id("msg-test-123")

    assert retrieved is not None
    assert retrieved.id == "msg-test-123"
    assert retrieved.role == "user"
    assert retrieved.content == "Test message"

    # Cleanup
    await conn.execute("DELETE FROM agent_messages WHERE id = 'msg-test-123'")
    await conn.close()


@pytest.mark.asyncio
async def test_get_messages_by_session():
    """Test retrieving all messages for a session."""
    conn = await asyncpg.connect(DATABASE_URL)
    repo = MessageRepository(conn)

    # Create multiple messages
    msg1 = AgentMessage.create("sess-test-456", "user", "Message 1")
    msg2 = AgentMessage.create("sess-test-456", "assistant", "Message 2")
    msg3 = AgentMessage.create("sess-test-456", "user", "Message 3")

    await repo.save(msg1)
    await repo.save(msg2)
    await repo.save(msg3)

    # Retrieve all messages
    messages = await repo.get_by_session("sess-test-456")

    assert len(messages) == 3
    assert messages[0].content == "Message 1"
    assert messages[1].content == "Message 2"
    assert messages[2].content == "Message 3"

    # Cleanup
    await conn.execute("DELETE FROM agent_messages WHERE session_id = 'sess-test-456'")
    await conn.close()
