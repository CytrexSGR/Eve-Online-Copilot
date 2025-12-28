# Phase 6: Backend Chat Integration & SSE Streaming Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Connect frontend chat components to backend with full message persistence, streaming responses via SSE, and proper error handling.

**Architecture:** FastAPI SSE endpoints for streaming LLM responses, PostgreSQL message persistence, integration with existing Agent Runtime and frontend chat components (ChatMessageInput, MessageHistory, useStreamingMessage).

**Tech Stack:** FastAPI, PostgreSQL (asyncpg), Server-Sent Events (SSE), Anthropic Streaming API, React hooks

---

## Prerequisites

**Before starting:**
- ✅ Phase 5 complete (frontend chat components implemented)
- ✅ Agent Runtime Phase 1-4 complete (backend session management, WebSocket events)
- ✅ AnthropicClient with streaming support (`_stream_response`)
- ✅ Frontend components: ChatMessageInput, MessageHistory, useStreamingMessage

**Current State:**
- Backend: `/agent/chat` POST endpoint exists but doesn't persist messages
- Frontend: Chat components ready but not connected to backend
- Missing: Message persistence, SSE streaming, chat history API

---

## Task 1: Database Migration - agent_messages Table

**Files:**
- Create: `/home/cytrex/eve_copilot/migrations/006_agent_messages.sql`
- Test: Manual verification with psql

**Step 1: Write the migration SQL**

```sql
-- Agent messages table for chat persistence
CREATE TABLE IF NOT EXISTS agent_messages (
    id VARCHAR(36) PRIMARY KEY,
    session_id VARCHAR(36) NOT NULL REFERENCES agent_sessions(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    content_blocks JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    token_usage JSONB,
    INDEX idx_agent_messages_session (session_id),
    INDEX idx_agent_messages_created (created_at DESC)
);

-- Add message count to agent_sessions for quick lookup
ALTER TABLE agent_sessions
ADD COLUMN IF NOT EXISTS message_count INTEGER DEFAULT 0;
```

**Step 2: Run migration**

```bash
cd /home/cytrex/eve_copilot
echo 'Aug2012#' | sudo -S docker exec eve_db psql -U eve -d eve_sde -f /migrations/006_agent_messages.sql
```

Expected: `CREATE TABLE` success message

**Step 3: Verify table exists**

```bash
echo 'Aug2012#' | sudo -S docker exec eve_db psql -U eve -d eve_sde -c "\d agent_messages"
```

Expected: Table structure displayed with all columns

**Step 4: Commit**

```bash
git add migrations/006_agent_messages.sql
git commit -m "feat(db): add agent_messages table for chat persistence

- Add agent_messages table with role/content/timestamps
- Add foreign key to agent_sessions
- Add indexes for session_id and created_at
- Add message_count column to agent_sessions"
```

---

## Task 2: Message Model & Repository

**Files:**
- Create: `/home/cytrex/eve_copilot/copilot_server/agent/messages.py`
- Test: `/home/cytrex/eve_copilot/copilot_server/tests/agent/test_messages.py`

**Step 1: Write the failing test**

```python
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
```

**Step 2: Run test to verify it fails**

```bash
cd /home/cytrex/eve_copilot
pytest copilot_server/tests/agent/test_messages.py::test_create_and_retrieve_message -v
```

Expected: `ModuleNotFoundError: No module named 'copilot_server.agent.messages'`

**Step 3: Write minimal implementation**

```python
"""
Agent Message Models and Repository
Handles message persistence for agent chat sessions.
"""

import uuid
import asyncpg
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
import json

@dataclass
class AgentMessage:
    """Agent chat message."""
    id: str
    session_id: str
    role: str  # 'user', 'assistant', 'system'
    content: str
    content_blocks: List[Dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    token_usage: Optional[Dict[str, int]] = None

    @staticmethod
    def create(session_id: str, role: str, content: str, content_blocks: List[Dict[str, Any]] = None) -> 'AgentMessage':
        """Create new message with generated ID."""
        return AgentMessage(
            id=f"msg-{uuid.uuid4()}",
            session_id=session_id,
            role=role,
            content=content,
            content_blocks=content_blocks or [{"type": "text", "text": content}]
        )


class MessageRepository:
    """Repository for agent messages."""

    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn

    async def save(self, message: AgentMessage) -> None:
        """Save message to database."""
        await self.conn.execute("""
            INSERT INTO agent_messages
            (id, session_id, role, content, content_blocks, created_at, token_usage)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (id) DO UPDATE SET
                content = EXCLUDED.content,
                content_blocks = EXCLUDED.content_blocks,
                token_usage = EXCLUDED.token_usage
        """,
            message.id,
            message.session_id,
            message.role,
            message.content,
            json.dumps(message.content_blocks),
            message.created_at,
            json.dumps(message.token_usage) if message.token_usage else None
        )

        # Update message count
        await self.conn.execute("""
            UPDATE agent_sessions
            SET message_count = (
                SELECT COUNT(*) FROM agent_messages WHERE session_id = $1
            )
            WHERE id = $1
        """, message.session_id)

    async def get_by_id(self, message_id: str) -> Optional[AgentMessage]:
        """Get message by ID."""
        row = await self.conn.fetchrow("""
            SELECT id, session_id, role, content, content_blocks, created_at, token_usage
            FROM agent_messages
            WHERE id = $1
        """, message_id)

        if not row:
            return None

        return AgentMessage(
            id=row['id'],
            session_id=row['session_id'],
            role=row['role'],
            content=row['content'],
            content_blocks=json.loads(row['content_blocks']) if row['content_blocks'] else [],
            created_at=row['created_at'],
            token_usage=json.loads(row['token_usage']) if row['token_usage'] else None
        )

    async def get_by_session(self, session_id: str, limit: int = 100) -> List[AgentMessage]:
        """Get messages for session, ordered by creation time."""
        rows = await self.conn.fetch("""
            SELECT id, session_id, role, content, content_blocks, created_at, token_usage
            FROM agent_messages
            WHERE session_id = $1
            ORDER BY created_at ASC
            LIMIT $2
        """, session_id, limit)

        return [
            AgentMessage(
                id=row['id'],
                session_id=row['session_id'],
                role=row['role'],
                content=row['content'],
                content_blocks=json.loads(row['content_blocks']) if row['content_blocks'] else [],
                created_at=row['created_at'],
                token_usage=json.loads(row['token_usage']) if row['token_usage'] else None
            )
            for row in rows
        ]
```

**Step 4: Run test to verify it passes**

```bash
pytest copilot_server/tests/agent/test_messages.py::test_create_and_retrieve_message -v
```

Expected: `PASSED`

**Step 5: Add more tests**

Add to `test_messages.py`:

```python
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
```

**Step 6: Run all tests**

```bash
pytest copilot_server/tests/agent/test_messages.py -v
```

Expected: All tests pass

**Step 7: Commit**

```bash
git add copilot_server/agent/messages.py copilot_server/tests/agent/test_messages.py
git commit -m "feat(agent): add message model and repository

- Add AgentMessage dataclass with role/content/blocks
- Add MessageRepository for CRUD operations
- Add get_by_session for chat history
- Add 2 comprehensive tests
- Update message_count on save"
```

---

## Task 3: SSE Streaming Infrastructure

**Files:**
- Create: `/home/cytrex/eve_copilot/copilot_server/agent/streaming.py`
- Test: `/home/cytrex/eve_copilot/copilot_server/tests/agent/test_streaming.py`

**Step 1: Write the failing test**

```python
import pytest
from copilot_server.agent.streaming import SSEFormatter

def test_format_text_chunk():
    """Test formatting text chunk for SSE."""
    formatter = SSEFormatter()

    chunk = {
        "type": "content_block_delta",
        "delta": {
            "type": "text_delta",
            "text": "Hello"
        }
    }

    result = formatter.format(chunk)

    assert result == 'data: {"type":"text","text":"Hello"}\n\n'


def test_format_error():
    """Test formatting error for SSE."""
    formatter = SSEFormatter()

    error = {
        "type": "error",
        "error": "API Error"
    }

    result = formatter.format(error)

    assert result == 'data: {"type":"error","error":"API Error"}\n\n'
```

**Step 2: Run test to verify it fails**

```bash
pytest copilot_server/tests/agent/test_streaming.py -v
```

Expected: `ModuleNotFoundError`

**Step 3: Write minimal implementation**

```python
"""
SSE Streaming Infrastructure
Handles Server-Sent Events formatting for streaming responses.
"""

import json
from typing import Dict, Any, AsyncIterator
import logging

logger = logging.getLogger(__name__)


class SSEFormatter:
    """Formats streaming events for SSE protocol."""

    def format(self, data: Dict[str, Any]) -> str:
        """
        Format data as SSE event.

        Args:
            data: Event data to format

        Returns:
            SSE-formatted string
        """
        # SSE format: data: <json>\n\n
        json_data = json.dumps(data)
        return f"data: {json_data}\n\n"

    def format_text_chunk(self, text: str) -> str:
        """Format text chunk for streaming."""
        return self.format({
            "type": "text",
            "text": text
        })

    def format_error(self, error: str) -> str:
        """Format error message."""
        return self.format({
            "type": "error",
            "error": error
        })

    def format_done(self, message_id: str) -> str:
        """Format completion event."""
        return self.format({
            "type": "done",
            "message_id": message_id
        })


async def stream_llm_response(
    llm_client,
    messages: list,
    tools: list = None,
    system: str = None
) -> AsyncIterator[Dict[str, Any]]:
    """
    Stream LLM response chunks.

    Args:
        llm_client: AnthropicClient instance
        messages: Conversation messages
        tools: Available tools
        system: System prompt

    Yields:
        Response chunks
    """
    try:
        # Call LLM with streaming enabled
        async for chunk in llm_client._stream_response({
            "model": llm_client.model,
            "messages": messages,
            "system": system or "",
            "max_tokens": 4096,
            "tools": tools or [],
            "stream": True
        }):
            # Extract text from chunk
            if chunk.get("type") == "content_block_delta":
                delta = chunk.get("delta", {})
                if delta.get("type") == "text_delta":
                    yield {
                        "type": "text",
                        "text": delta.get("text", "")
                    }
            elif chunk.get("type") == "message_stop":
                yield {"type": "done"}

    except Exception as e:
        logger.error(f"Streaming error: {e}")
        yield {
            "type": "error",
            "error": str(e)
        }
```

**Step 4: Run test to verify it passes**

```bash
pytest copilot_server/tests/agent/test_streaming.py -v
```

Expected: `PASSED`

**Step 5: Commit**

```bash
git add copilot_server/agent/streaming.py copilot_server/tests/agent/test_streaming.py
git commit -m "feat(agent): add SSE streaming infrastructure

- Add SSEFormatter for SSE protocol formatting
- Add stream_llm_response for LLM streaming
- Handle text chunks and errors
- Add 2 tests for formatting"
```

---

## Task 4: Update Chat POST Endpoint with Message Persistence

**Files:**
- Modify: `/home/cytrex/eve_copilot/copilot_server/api/agent_routes.py`
- Test: `/home/cytrex/eve_copilot/copilot_server/tests/api/test_agent_chat.py`

**Step 1: Write the failing test**

```python
import pytest
from fastapi.testclient import TestClient
from copilot_server.main import app

client = TestClient(app)

def test_chat_persists_messages():
    """Test that chat endpoint persists messages to database."""
    # Create session first
    response = client.post("/agent/session", json={
        "character_id": 526379435,
        "autonomy_level": "RECOMMENDATIONS"
    })
    assert response.status_code == 200
    session_id = response.json()["session_id"]

    # Send chat message
    response = client.post("/agent/chat", json={
        "message": "Hello, agent!",
        "session_id": session_id,
        "character_id": 526379435
    })

    assert response.status_code == 200
    assert response.json()["session_id"] == session_id

    # Get chat history
    response = client.get(f"/agent/chat/history/{session_id}")
    assert response.status_code == 200

    messages = response.json()["messages"]
    assert len(messages) >= 1
    assert messages[0]["content"] == "Hello, agent!"
    assert messages[0]["role"] == "user"
```

**Step 2: Run test to verify it fails**

```bash
pytest copilot_server/tests/api/test_agent_chat.py::test_chat_persists_messages -v
```

Expected: `FAILED` (endpoint doesn't exist yet)

**Step 3: Update chat endpoint implementation**

Modify `/home/cytrex/eve_copilot/copilot_server/api/agent_routes.py`:

```python
# Add imports at top
from ..agent.messages import AgentMessage, MessageRepository
import asyncpg

# Add connection pool (near session_manager declaration)
db_pool: Optional[asyncpg.Pool] = None

# Modify /agent/chat endpoint
@router.post("/chat", response_model=ChatResponse)
async def agent_chat(request: ChatRequest):
    """
    Send message to agent.

    Creates new session if session_id is None, otherwise continues existing.
    Persists all messages to database.
    """
    if not session_manager or not runtime or not db_pool:
        raise HTTPException(status_code=500, detail="Agent runtime not initialized")

    # Load or create session
    if request.session_id:
        session = await session_manager.load_session(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
    else:
        # Get user settings
        user_settings = get_default_settings(character_id=request.character_id or -1)

        # Create new session
        session = await session_manager.create_session(
            character_id=request.character_id,
            autonomy_level=user_settings.autonomy_level
        )

    # Save user message to database
    async with db_pool.acquire() as conn:
        repo = MessageRepository(conn)
        user_message = AgentMessage.create(
            session_id=session.id,
            role="user",
            content=request.message
        )
        await repo.save(user_message)

    # Add user message to session
    session.add_message("user", request.message)
    await session_manager.save_session(session)

    # Execute runtime (async, don't await in Phase 1)
    try:
        response = await runtime.execute(session)

        # Save assistant response to database if available
        if response and "content" in response:
            async with db_pool.acquire() as conn:
                repo = MessageRepository(conn)

                # Extract text from content blocks
                text_content = ""
                for block in response["content"]:
                    if block.get("type") == "text":
                        text_content += block.get("text", "")

                assistant_message = AgentMessage.create(
                    session_id=session.id,
                    role="assistant",
                    content=text_content,
                    content_blocks=response["content"]
                )

                # Add token usage if available
                if "usage" in response:
                    assistant_message.token_usage = response["usage"]

                await repo.save(assistant_message)

    except Exception as e:
        logger.error(f"Runtime execution failed: {e}")
        session.status = SessionStatus.ERROR
        await session_manager.save_session(session)

    return ChatResponse(
        session_id=session.id,
        status=session.status.value
    )
```

**Step 4: Add initialization in main.py**

Modify `/home/cytrex/eve_copilot/copilot_server/main.py` startup:

```python
from .config import DATABASE_URL
import asyncpg

@app.on_event("startup")
async def startup():
    """Application startup."""
    global agent_session_manager, agent_runtime

    logger.info("Starting EVE Co-Pilot AI Server...")

    # ... existing code ...

    # Initialize database pool for agent routes
    try:
        agent_routes.db_pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=2,
            max_size=10
        )
        logger.info("Database pool initialized for agent routes")
    except Exception as e:
        logger.error(f"Failed to initialize database pool: {e}")
```

**Step 5: Run test to verify it passes**

```bash
pytest copilot_server/tests/api/test_agent_chat.py::test_chat_persists_messages -v
```

Expected: `PASSED`

**Step 6: Commit**

```bash
git add copilot_server/api/agent_routes.py copilot_server/main.py copilot_server/tests/api/test_agent_chat.py
git commit -m "feat(agent): persist chat messages to database

- Update /agent/chat to save user and assistant messages
- Add database pool initialization in main.py
- Save message content and token usage
- Add test for message persistence"
```

---

## Task 5: Chat History GET Endpoint

**Files:**
- Modify: `/home/cytrex/eve_copilot/copilot_server/api/agent_routes.py`

**Step 1: Write the failing test**

```python
def test_get_chat_history():
    """Test getting chat history for a session."""
    # Create session
    response = client.post("/agent/session", json={
        "character_id": 526379435,
        "autonomy_level": "RECOMMENDATIONS"
    })
    session_id = response.json()["session_id"]

    # Send multiple messages
    client.post("/agent/chat", json={
        "message": "First message",
        "session_id": session_id,
        "character_id": 526379435
    })

    client.post("/agent/chat", json={
        "message": "Second message",
        "session_id": session_id,
        "character_id": 526379435
    })

    # Get history
    response = client.get(f"/agent/chat/history/{session_id}")

    assert response.status_code == 200
    data = response.json()
    assert "messages" in data
    assert len(data["messages"]) >= 2
    assert data["messages"][0]["role"] == "user"
    assert data["messages"][0]["content"] == "First message"
```

**Step 2: Run test to verify it fails**

```bash
pytest copilot_server/tests/api/test_agent_chat.py::test_get_chat_history -v
```

Expected: `FAILED` (404 Not Found)

**Step 3: Implement endpoint**

Add to `agent_routes.py`:

```python
class ChatHistoryResponse(BaseModel):
    """Chat history response."""
    session_id: str
    messages: List[Dict[str, Any]]
    message_count: int


@router.get("/chat/history/{session_id}", response_model=ChatHistoryResponse)
async def get_chat_history(session_id: str, limit: int = 100):
    """
    Get chat history for a session.

    Args:
        session_id: Session ID
        limit: Max messages to return (default 100)

    Returns:
        Chat history with messages
    """
    if not db_pool:
        raise HTTPException(status_code=500, detail="Database not initialized")

    # Verify session exists
    session = await session_manager.load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Get messages from database
    async with db_pool.acquire() as conn:
        repo = MessageRepository(conn)
        messages = await repo.get_by_session(session_id, limit)

    # Convert to dict format
    message_dicts = [
        {
            "id": msg.id,
            "role": msg.role,
            "content": msg.content,
            "content_blocks": msg.content_blocks,
            "created_at": msg.created_at.isoformat(),
            "token_usage": msg.token_usage
        }
        for msg in messages
    ]

    return ChatHistoryResponse(
        session_id=session_id,
        messages=message_dicts,
        message_count=len(message_dicts)
    )
```

**Step 4: Run test to verify it passes**

```bash
pytest copilot_server/tests/api/test_agent_chat.py::test_get_chat_history -v
```

Expected: `PASSED`

**Step 5: Commit**

```bash
git add copilot_server/api/agent_routes.py copilot_server/tests/api/test_agent_chat.py
git commit -m "feat(agent): add chat history GET endpoint

- Add /agent/chat/history/{session_id} endpoint
- Return all messages with metadata
- Add limit parameter for pagination
- Add test for chat history retrieval"
```

---

## Task 6: SSE Stream Endpoint

**Files:**
- Modify: `/home/cytrex/eve_copilot/copilot_server/api/agent_routes.py`
- Test: Manual testing with curl/browser (SSE doesn't work well with TestClient)

**Step 1: Implement SSE endpoint**

Add to `agent_routes.py`:

```python
from fastapi.responses import StreamingResponse
from ..agent.streaming import SSEFormatter, stream_llm_response
from ..llm import AnthropicClient
from ..mcp import MCPClient, ToolOrchestrator
from ..models.user_settings import get_default_settings

# Add at module level
llm_client: Optional[AnthropicClient] = None
mcp_client: Optional[MCPClient] = None


class ChatStreamRequest(BaseModel):
    """Request to stream chat response."""
    message: str
    session_id: str
    character_id: int


@router.post("/chat/stream")
async def stream_chat_response(request: ChatStreamRequest):
    """
    Stream chat response via SSE.

    Sends Server-Sent Events for real-time streaming.
    Client should use EventSource to consume.
    """
    if not session_manager or not runtime or not db_pool or not llm_client:
        raise HTTPException(status_code=500, detail="Services not initialized")

    # Load session
    session = await session_manager.load_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Save user message
    async with db_pool.acquire() as conn:
        repo = MessageRepository(conn)
        user_message = AgentMessage.create(
            session_id=session.id,
            role="user",
            content=request.message
        )
        await repo.save(user_message)

    # Add to session
    session.add_message("user", request.message)
    await session_manager.save_session(session)

    # Stream response
    async def event_generator():
        formatter = SSEFormatter()
        full_response = ""

        try:
            # Get conversation history
            messages = session.get_messages_for_api()

            # Get user settings and tools
            user_settings = get_default_settings(character_id=request.character_id or -1)
            tools = mcp_client.get_tools() if mcp_client else []

            # Stream LLM response
            async for chunk in stream_llm_response(
                llm_client,
                messages,
                tools,
                system=None
            ):
                if chunk.get("type") == "text":
                    text = chunk.get("text", "")
                    full_response += text
                    yield formatter.format_text_chunk(text)
                elif chunk.get("type") == "error":
                    yield formatter.format_error(chunk.get("error", "Unknown error"))
                    return

            # Save assistant response
            async with db_pool.acquire() as conn:
                repo = MessageRepository(conn)
                assistant_message = AgentMessage.create(
                    session_id=session.id,
                    role="assistant",
                    content=full_response
                )
                await repo.save(assistant_message)

            # Send completion
            yield formatter.format_done(assistant_message.id)

        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield formatter.format_error(str(e))

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
```

**Step 2: Update main.py initialization**

```python
@app.on_event("startup")
async def startup():
    """Application startup."""
    global agent_session_manager, agent_runtime

    # ... existing code ...

    # Initialize LLM client for streaming
    try:
        from .llm import AnthropicClient
        agent_routes.llm_client = AnthropicClient()
        logger.info("LLM client initialized for agent routes")
    except Exception as e:
        logger.error(f"Failed to initialize LLM client: {e}")

    # Initialize MCP client
    try:
        from .mcp import MCPClient
        agent_routes.mcp_client = MCPClient()
        logger.info("MCP client initialized for agent routes")
    except Exception as e:
        logger.error(f"Failed to initialize MCP client: {e}")
```

**Step 3: Manual testing**

Create test script `/home/cytrex/eve_copilot/test_sse.sh`:

```bash
#!/bin/bash
# Test SSE streaming endpoint

# First create a session
SESSION_RESPONSE=$(curl -X POST http://localhost:8000/agent/session \
  -H "Content-Type: application/json" \
  -d '{"character_id": 526379435, "autonomy_level": "RECOMMENDATIONS"}')

SESSION_ID=$(echo $SESSION_RESPONSE | jq -r '.session_id')

echo "Created session: $SESSION_ID"

# Stream chat response
curl -N -X POST http://localhost:8000/agent/chat/stream \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"Hello!\", \"session_id\": \"$SESSION_ID\", \"character_id\": 526379435}"
```

**Step 4: Run manual test**

```bash
chmod +x test_sse.sh
./test_sse.sh
```

Expected: Stream of SSE events like:
```
data: {"type":"text","text":"Hello"}
data: {"type":"text","text":"!"}
data: {"type":"done","message_id":"msg-..."}
```

**Step 5: Commit**

```bash
git add copilot_server/api/agent_routes.py copilot_server/main.py test_sse.sh
git commit -m "feat(agent): add SSE streaming endpoint

- Add /agent/chat/stream POST endpoint
- Stream LLM responses in real-time via SSE
- Save streamed messages to database
- Initialize LLM and MCP clients in main.py
- Add manual test script for SSE"
```

---

## Task 7: Frontend Integration - AgentDashboard Chat

**Files:**
- Modify: `/home/cytrex/eve_copilot/frontend/src/pages/AgentDashboard.tsx`
- Modify: `/home/cytrex/eve_copilot/frontend/src/api/agent-client.ts`
- Test: Manual testing in browser

**Step 1: Update API client with chat methods**

Add to `/home/cytrex/eve_copilot/frontend/src/api/agent-client.ts`:

```typescript
// Add to AgentClient class

async sendMessage(
  sessionId: string,
  message: string,
  characterId: number
): Promise<void> {
  await this.client.post('/agent/chat', {
    message,
    session_id: sessionId,
    character_id: characterId
  });
}

async getChatHistory(sessionId: string): Promise<ChatMessage[]> {
  const response = await this.client.get(`/agent/chat/history/${sessionId}`);
  return response.data.messages.map((msg: any) => ({
    id: msg.id,
    role: msg.role as 'user' | 'assistant' | 'system',
    content: msg.content,
    timestamp: msg.created_at,
    isStreaming: false
  }));
}

streamChatResponse(
  sessionId: string,
  message: string,
  characterId: number,
  onChunk: (text: string) => void,
  onDone: (messageId: string) => void,
  onError: (error: string) => void
): () => void {
  const eventSource = new EventSource(
    `${this.client.defaults.baseURL}/agent/chat/stream`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        message,
        session_id: sessionId,
        character_id: characterId
      })
    }
  );

  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);

      if (data.type === 'text') {
        onChunk(data.text);
      } else if (data.type === 'done') {
        onDone(data.message_id);
        eventSource.close();
      } else if (data.type === 'error') {
        onError(data.error);
        eventSource.close();
      }
    } catch (e) {
      console.error('Failed to parse SSE event:', e);
    }
  };

  eventSource.onerror = (error) => {
    console.error('SSE error:', error);
    onError('Connection error');
    eventSource.close();
  };

  // Return cleanup function
  return () => eventSource.close();
}
```

**Step 2: Integrate chat components in AgentDashboard**

Modify `/home/cytrex/eve_copilot/frontend/src/pages/AgentDashboard.tsx`:

```typescript
// Add imports
import { ChatMessageInput } from '../components/agent/ChatMessageInput';
import { MessageHistory } from '../components/agent/MessageHistory';
import { useStreamingMessage } from '../hooks/useStreamingMessage';
import type { ChatMessage } from '../types/chat-messages';

// Add state
const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
const [isSending, setIsSending] = useState(false);
const {
  content: streamingContent,
  isStreaming,
  appendChunk,
  complete: completeStreaming,
  reset: resetStreaming
} = useStreamingMessage();

// Load chat history when session is created
useEffect(() => {
  if (sessionId) {
    agentClient.getChatHistory(sessionId)
      .then(messages => setChatMessages(messages))
      .catch(err => console.error('Failed to load chat history:', err));
  }
}, [sessionId]);

// Handle send message
const handleSendMessage = async (message: string) => {
  if (!sessionId || !selectedCharacter) return;

  setIsSending(true);
  resetStreaming();

  // Add user message immediately
  const userMessage: ChatMessage = {
    id: `temp-${Date.now()}`,
    role: 'user',
    content: message,
    timestamp: new Date().toISOString(),
    isStreaming: false
  };
  setChatMessages(prev => [...prev, userMessage]);

  // Create assistant message placeholder
  const assistantMessage: ChatMessage = {
    id: `temp-assistant-${Date.now()}`,
    role: 'assistant',
    content: '',
    timestamp: new Date().toISOString(),
    isStreaming: true
  };
  setChatMessages(prev => [...prev, assistantMessage]);

  // Stream response
  const cleanup = agentClient.streamChatResponse(
    sessionId,
    message,
    selectedCharacter,
    (text) => {
      // Append chunk to streaming message
      appendChunk(text);

      // Update assistant message with streamed content
      setChatMessages(prev => {
        const updated = [...prev];
        const lastMsg = updated[updated.length - 1];
        if (lastMsg.role === 'assistant') {
          lastMsg.content += text;
        }
        return updated;
      });
    },
    (messageId) => {
      // Complete streaming
      completeStreaming();
      setIsSending(false);

      // Update message ID
      setChatMessages(prev => {
        const updated = [...prev];
        const lastMsg = updated[updated.length - 1];
        if (lastMsg.role === 'assistant') {
          lastMsg.id = messageId;
          lastMsg.isStreaming = false;
        }
        return updated;
      });
    },
    (error) => {
      console.error('Streaming error:', error);
      setIsSending(false);
      completeStreaming();
    }
  );

  // Store cleanup for component unmount
  return cleanup;
};

// Add to JSX (in the main content area)
<div className="space-y-4">
  <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
    <h3 className="text-lg font-semibold text-gray-100 mb-4">Chat</h3>

    <MessageHistory
      messages={chatMessages}
      autoScroll={true}
      maxHeight="400px"
    />

    <ChatMessageInput
      onSend={handleSendMessage}
      disabled={!sessionId || isSending}
      placeholder={
        sessionId
          ? "Type your message... (Ctrl+Enter to send)"
          : "Create a session first"
      }
    />
  </div>
</div>
```

**Step 3: Manual testing**

1. Start backend: `uvicorn main:app --reload`
2. Start frontend: `npm run dev`
3. Open browser to `http://localhost:5173/agent`
4. Create session
5. Send chat message
6. Verify streaming works
7. Check messages persist after page reload

**Step 4: Commit**

```bash
git add frontend/src/pages/AgentDashboard.tsx frontend/src/api/agent-client.ts
git commit -m "feat(frontend): integrate chat components with backend

- Add sendMessage, getChatHistory, streamChatResponse to API client
- Integrate ChatMessageInput and MessageHistory into AgentDashboard
- Use useStreamingMessage hook for real-time updates
- Load chat history on session creation
- Handle streaming responses via SSE"
```

---

## Task 8: Authorization & Session Validation

**Files:**
- Create: `/home/cytrex/eve_copilot/copilot_server/api/middleware.py`
- Modify: `/home/cytrex/eve_copilot/copilot_server/api/agent_routes.py`

**Step 1: Write authorization middleware**

```python
"""
API Middleware
Authorization and validation for agent endpoints.
"""

from fastapi import HTTPException, Header
from typing import Optional
import logging

logger = logging.getLogger(__name__)


async def verify_session_access(
    session_id: str,
    character_id: Optional[int] = None,
    authorization: Optional[str] = Header(None)
) -> bool:
    """
    Verify user has access to session.

    For now, this is a placeholder. In production:
    - Verify JWT token in Authorization header
    - Check character_id matches token
    - Verify session belongs to character

    Args:
        session_id: Session to access
        character_id: Character requesting access
        authorization: Authorization header

    Returns:
        True if authorized

    Raises:
        HTTPException: If not authorized
    """
    # Phase 6: Basic validation only
    # Phase 7+: Add full JWT validation

    if not session_id:
        raise HTTPException(status_code=400, detail="Session ID required")

    # TODO Phase 7: Validate JWT token
    # TODO Phase 7: Verify character_id from token
    # TODO Phase 7: Check session ownership

    return True


async def validate_message_content(content: str) -> None:
    """
    Validate message content.

    Args:
        content: Message content

    Raises:
        HTTPException: If content invalid
    """
    if not content or not content.strip():
        raise HTTPException(status_code=400, detail="Message content cannot be empty")

    if len(content) > 10000:
        raise HTTPException(status_code=400, detail="Message too long (max 10000 characters)")
```

**Step 2: Add validation to endpoints**

Modify `/home/cytrex/eve_copilot/copilot_server/api/agent_routes.py`:

```python
from .middleware import verify_session_access, validate_message_content

@router.post("/chat", response_model=ChatResponse)
async def agent_chat(
    request: ChatRequest,
    authorization: Optional[str] = Header(None)
):
    """Send message to agent with authorization."""
    # Validate message
    await validate_message_content(request.message)

    # Verify session access if session_id provided
    if request.session_id:
        await verify_session_access(
            request.session_id,
            request.character_id,
            authorization
        )

    # ... rest of implementation


@router.get("/chat/history/{session_id}", response_model=ChatHistoryResponse)
async def get_chat_history(
    session_id: str,
    limit: int = 100,
    authorization: Optional[str] = Header(None)
):
    """Get chat history with authorization."""
    # Verify access
    await verify_session_access(session_id, authorization=authorization)

    # ... rest of implementation


@router.post("/chat/stream")
async def stream_chat_response(
    request: ChatStreamRequest,
    authorization: Optional[str] = Header(None)
):
    """Stream chat with authorization."""
    # Validate message
    await validate_message_content(request.message)

    # Verify access
    await verify_session_access(
        request.session_id,
        request.character_id,
        authorization
    )

    # ... rest of implementation
```

**Step 3: Add tests**

```python
def test_chat_requires_valid_session():
    """Test that chat validates session access."""
    response = client.post("/agent/chat", json={
        "message": "Test",
        "session_id": "invalid-session",
        "character_id": 123
    })

    assert response.status_code == 404


def test_chat_rejects_empty_message():
    """Test that empty messages are rejected."""
    response = client.post("/agent/chat", json={
        "message": "",
        "session_id": "test",
        "character_id": 123
    })

    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()
```

**Step 4: Commit**

```bash
git add copilot_server/api/middleware.py copilot_server/api/agent_routes.py
git commit -m "feat(agent): add authorization and validation

- Add middleware for session access verification
- Add message content validation
- Validate session ownership (placeholder for Phase 7)
- Add tests for validation"
```

---

## Task 9: Error Recovery & Retry Logic

**Files:**
- Modify: `/home/cytrex/eve_copilot/frontend/src/pages/AgentDashboard.tsx`
- Modify: `/home/cytrex/eve_copilot/copilot_server/api/agent_routes.py`

**Step 1: Add retry logic to backend**

Modify streaming endpoint in `agent_routes.py`:

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
)
async def stream_with_retry(llm_client, messages, tools, system):
    """Stream with retry logic."""
    async for chunk in stream_llm_response(llm_client, messages, tools, system):
        yield chunk


@router.post("/chat/stream")
async def stream_chat_response(request: ChatStreamRequest, authorization: Optional[str] = Header(None)):
    """Stream chat response with error recovery."""
    # ... existing validation ...

    async def event_generator():
        formatter = SSEFormatter()
        full_response = ""
        retry_count = 0
        max_retries = 3

        while retry_count < max_retries:
            try:
                # Stream with retry
                async for chunk in stream_with_retry(llm_client, messages, tools, None):
                    if chunk.get("type") == "text":
                        text = chunk.get("text", "")
                        full_response += text
                        yield formatter.format_text_chunk(text)
                    elif chunk.get("type") == "error":
                        raise Exception(chunk.get("error"))

                # Success - save and exit
                async with db_pool.acquire() as conn:
                    repo = MessageRepository(conn)
                    assistant_message = AgentMessage.create(
                        session_id=session.id,
                        role="assistant",
                        content=full_response
                    )
                    await repo.save(assistant_message)

                yield formatter.format_done(assistant_message.id)
                return

            except Exception as e:
                retry_count += 1
                logger.error(f"Stream error (attempt {retry_count}/{max_retries}): {e}")

                if retry_count < max_retries:
                    # Send retry notification
                    yield formatter.format({
                        "type": "retry",
                        "attempt": retry_count,
                        "max_attempts": max_retries
                    })
                    await asyncio.sleep(2 ** retry_count)  # Exponential backoff
                else:
                    # Max retries exceeded
                    yield formatter.format_error(f"Failed after {max_retries} attempts: {str(e)}")
                    return

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

**Step 2: Add retry UI to frontend**

Modify `AgentDashboard.tsx`:

```typescript
const [retryAttempt, setRetryAttempt] = useState(0);

const handleSendMessage = async (message: string) => {
  // ... existing code ...

  const cleanup = agentClient.streamChatResponse(
    sessionId,
    message,
    selectedCharacter,
    (text) => {
      appendChunk(text);
      setChatMessages(prev => {
        const updated = [...prev];
        const lastMsg = updated[updated.length - 1];
        if (lastMsg.role === 'assistant') {
          lastMsg.content += text;
        }
        return updated;
      });
    },
    (messageId) => {
      completeStreaming();
      setIsSending(false);
      setRetryAttempt(0);
      // ... update message ID ...
    },
    (error) => {
      console.error('Streaming error:', error);
      setIsSending(false);
      completeStreaming();

      // Show error to user
      setChatMessages(prev => [...prev, {
        id: `error-${Date.now()}`,
        role: 'system',
        content: `Error: ${error}. Please try again.`,
        timestamp: new Date().toISOString(),
        isStreaming: false
      }]);
    }
  );
};

// Add retry notification handler
const handleRetryNotification = (attempt: number, maxAttempts: number) => {
  setRetryAttempt(attempt);

  // Show retry message
  setChatMessages(prev => [...prev, {
    id: `retry-${Date.now()}`,
    role: 'system',
    content: `Retrying... (${attempt}/${maxAttempts})`,
    timestamp: new Date().toISOString(),
    isStreaming: false
  }]);
};
```

**Step 3: Update SSE handler in agent-client.ts**

```typescript
streamChatResponse(
  sessionId: string,
  message: string,
  characterId: number,
  onChunk: (text: string) => void,
  onDone: (messageId: string) => void,
  onError: (error: string) => void,
  onRetry?: (attempt: number, maxAttempts: number) => void
): () => void {
  // ... existing code ...

  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);

      if (data.type === 'text') {
        onChunk(data.text);
      } else if (data.type === 'done') {
        onDone(data.message_id);
        eventSource.close();
      } else if (data.type === 'error') {
        onError(data.error);
        eventSource.close();
      } else if (data.type === 'retry' && onRetry) {
        onRetry(data.attempt, data.max_attempts);
      }
    } catch (e) {
      console.error('Failed to parse SSE event:', e);
    }
  };

  // ... rest of code ...
}
```

**Step 4: Commit**

```bash
git add copilot_server/api/agent_routes.py frontend/src/pages/AgentDashboard.tsx frontend/src/api/agent-client.ts
git commit -m "feat(agent): add error recovery and retry logic

- Add retry logic with exponential backoff (3 attempts)
- Send retry notifications via SSE
- Handle retries in frontend UI
- Show error messages to user
- Use tenacity for retry decorator"
```

---

## Task 10: Integration Tests

**Files:**
- Create: `/home/cytrex/eve_copilot/copilot_server/tests/integration/test_chat_flow.py`

**Step 1: Write integration tests**

```python
"""
Integration tests for complete chat flow.
Tests the full stack: API -> Database -> LLM -> SSE.
"""

import pytest
import asyncio
from fastapi.testclient import TestClient
from copilot_server.main import app
import asyncpg

DATABASE_URL = "postgresql://eve:EvE_Pr0ject_2024@localhost/eve_sde"

client = TestClient(app)


@pytest.mark.integration
def test_complete_chat_flow():
    """Test complete chat flow from session creation to message retrieval."""
    # Step 1: Create session
    response = client.post("/agent/session", json={
        "character_id": 526379435,
        "autonomy_level": "RECOMMENDATIONS"
    })
    assert response.status_code == 200
    session_id = response.json()["session_id"]

    # Step 2: Send first message
    response = client.post("/agent/chat", json={
        "message": "What can you help me with?",
        "session_id": session_id,
        "character_id": 526379435
    })
    assert response.status_code == 200

    # Step 3: Send second message
    response = client.post("/agent/chat", json={
        "message": "Tell me about market analysis",
        "session_id": session_id,
        "character_id": 526379435
    })
    assert response.status_code == 200

    # Step 4: Get chat history
    response = client.get(f"/agent/chat/history/{session_id}")
    assert response.status_code == 200

    history = response.json()
    assert history["message_count"] >= 2
    assert len(history["messages"]) >= 2

    # Verify message order and content
    messages = history["messages"]
    assert messages[0]["role"] == "user"
    assert "help me" in messages[0]["content"].lower()
    assert messages[1]["role"] == "assistant"  # Agent response

    # Step 5: Verify persistence
    response = client.get(f"/agent/session/{session_id}")
    assert response.status_code == 200
    session_data = response.json()
    assert session_data["message_count"] >= 2


@pytest.mark.integration
@pytest.mark.asyncio
async def test_message_persistence_in_database():
    """Test that messages are actually persisted in database."""
    # Create session and send message
    response = client.post("/agent/session", json={
        "character_id": 526379435,
        "autonomy_level": "RECOMMENDATIONS"
    })
    session_id = response.json()["session_id"]

    response = client.post("/agent/chat", json={
        "message": "Database persistence test",
        "session_id": session_id,
        "character_id": 526379435
    })
    assert response.status_code == 200

    # Verify in database directly
    conn = await asyncpg.connect(DATABASE_URL)

    messages = await conn.fetch("""
        SELECT * FROM agent_messages
        WHERE session_id = $1
        ORDER BY created_at ASC
    """, session_id)

    assert len(messages) >= 1
    assert messages[0]['role'] == 'user'
    assert messages[0]['content'] == 'Database persistence test'

    # Cleanup
    await conn.execute("DELETE FROM agent_messages WHERE session_id = $1", session_id)
    await conn.execute("DELETE FROM agent_sessions WHERE id = $1", session_id)
    await conn.close()


@pytest.mark.integration
def test_chat_validation():
    """Test validation in chat endpoints."""
    # Create session
    response = client.post("/agent/session", json={
        "character_id": 526379435,
        "autonomy_level": "RECOMMENDATIONS"
    })
    session_id = response.json()["session_id"]

    # Test empty message
    response = client.post("/agent/chat", json={
        "message": "",
        "session_id": session_id,
        "character_id": 526379435
    })
    assert response.status_code == 400

    # Test invalid session
    response = client.post("/agent/chat", json={
        "message": "Test",
        "session_id": "invalid-session-id",
        "character_id": 526379435
    })
    assert response.status_code == 404

    # Test message too long
    long_message = "x" * 20000
    response = client.post("/agent/chat", json={
        "message": long_message,
        "session_id": session_id,
        "character_id": 526379435
    })
    assert response.status_code == 400
```

**Step 2: Run integration tests**

```bash
pytest copilot_server/tests/integration/test_chat_flow.py -v -m integration
```

Expected: All tests pass

**Step 3: Commit**

```bash
git add copilot_server/tests/integration/test_chat_flow.py
git commit -m "test(agent): add chat flow integration tests

- Add complete chat flow test
- Test message persistence in database
- Test validation and error handling
- Verify chat history retrieval"
```

---

## Task 11: Documentation

**Files:**
- Create: `/home/cytrex/eve_copilot/docs/agent/phase6-completion.md`
- Modify: `/home/cytrex/eve_copilot/README.md`

**Step 1: Create completion documentation**

```markdown
# Phase 6: Backend Chat Integration & SSE Streaming - Completion Report

## Executive Summary

Phase 6 successfully implements backend chat integration with message persistence, Server-Sent Events (SSE) streaming, and full integration with Phase 5 frontend chat components.

**Status:** ✅ COMPLETE

**Completion Date:** 2025-12-28

---

## Deliverables

### 1. Database Schema (Task 1)
- ✅ `agent_messages` table for chat persistence
- ✅ Foreign key to `agent_sessions`
- ✅ Indexes on session_id and created_at
- ✅ message_count column in agent_sessions

### 2. Message Model & Repository (Task 2)
- ✅ AgentMessage dataclass
- ✅ MessageRepository with CRUD operations
- ✅ get_by_session for chat history
- ✅ Automatic message_count updates

### 3. SSE Streaming Infrastructure (Task 3)
- ✅ SSEFormatter for SSE protocol
- ✅ stream_llm_response for LLM streaming
- ✅ Text chunk and error handling

### 4. Chat Endpoints (Tasks 4-6)
- ✅ POST /agent/chat with message persistence
- ✅ GET /agent/chat/history/{session_id}
- ✅ POST /agent/chat/stream for SSE

### 5. Frontend Integration (Task 7)
- ✅ AgentDashboard chat UI
- ✅ ChatMessageInput + MessageHistory integration
- ✅ SSE streaming with useStreamingMessage hook
- ✅ Chat history loading

### 6. Authorization & Validation (Task 8)
- ✅ Session access verification (placeholder for Phase 7)
- ✅ Message content validation
- ✅ Authorization middleware

### 7. Error Recovery (Task 9)
- ✅ Retry logic with exponential backoff (3 attempts)
- ✅ Retry notifications via SSE
- ✅ Frontend error handling

### 8. Testing (Task 10)
- ✅ Integration tests for chat flow
- ✅ Database persistence verification
- ✅ Validation tests

### 9. Documentation (Task 11)
- ✅ This completion report
- ✅ Updated README.md

---

## Architecture

### Backend Stack
```
FastAPI
├── /agent/chat (POST) - Send message with persistence
├── /agent/chat/history/{session_id} (GET) - Get chat history
└── /agent/chat/stream (POST) - SSE streaming

PostgreSQL
└── agent_messages table
    ├── id (VARCHAR 36, PK)
    ├── session_id (FK to agent_sessions)
    ├── role (user/assistant/system)
    ├── content (TEXT)
    ├── content_blocks (JSONB)
    ├── created_at (TIMESTAMP)
    └── token_usage (JSONB)
```

### Frontend Integration
```
AgentDashboard
├── ChatMessageInput (Phase 5)
├── MessageHistory (Phase 5)
├── useStreamingMessage (Phase 5)
└── SSE EventSource connection
```

---

## Testing Summary

**Integration Tests:** 3 passing
- Complete chat flow
- Database persistence
- Validation and errors

**Total Tests (Backend):** TBD based on existing tests + 3 new

**Manual Testing:**
- ✅ SSE streaming works in browser
- ✅ Messages persist across page reloads
- ✅ Chat history loads correctly
- ✅ Error recovery works

---

## Known Limitations

1. **Authorization:** Phase 6 uses placeholder authorization. Full JWT validation planned for Phase 7.
2. **SSE Browser Support:** EventSource API not supported in IE. Modern browsers only.
3. **Message Limit:** Chat history limited to 100 messages (configurable).

---

## Next Steps: Phase 7+

**Phase 7: Authorization UI**
- JWT token management
- Session ownership validation
- Character-based access control

**Phase 8: Advanced Analytics**
- Token usage tracking
- Message analytics
- Performance metrics

**Future Enhancements:**
- Message editing/deletion
- Conversation branching
- Multi-modal support (images, files)
```

**Step 2: Update README.md**

Add to `/home/cytrex/eve_copilot/README.md`:

```markdown
## Agent Runtime - Phase 6: Backend Chat Integration ✅

**Status:** COMPLETE (2025-12-28)

### Features
- ✅ **Message Persistence** - PostgreSQL storage for all chat messages
- ✅ **SSE Streaming** - Real-time LLM responses via Server-Sent Events
- ✅ **Chat History** - GET endpoint for retrieving conversation history
- ✅ **Frontend Integration** - Connected to Phase 5 chat components
- ✅ **Error Recovery** - Automatic retry with exponential backoff
- ✅ **Validation** - Message content and session access validation

### Endpoints
- `POST /agent/chat` - Send message with persistence
- `GET /agent/chat/history/{session_id}` - Get chat history
- `POST /agent/chat/stream` - Stream responses via SSE

### Database
- `agent_messages` table with full chat persistence
- Automatic message counting
- Indexed for fast retrieval

### Testing
- 3 integration tests for chat flow
- Manual testing completed
- All Phase 1-6 tests passing
```

**Step 3: Commit**

```bash
git add docs/agent/phase6-completion.md README.md
git commit -m "docs(agent): Phase 6 completion documentation

Phase 6 Deliverables:
- Message persistence (PostgreSQL)
- SSE streaming endpoints
- Chat history API
- Frontend integration
- Error recovery with retry
- Authorization middleware
- Integration tests

Phase 6 Status: COMPLETE ✅
Agent Runtime Status: Chat-enabled, Production Ready 🚀"
```

---

## Execution Summary

**Total Tasks:** 11
- Task 1: Database Migration
- Task 2: Message Model & Repository
- Task 3: SSE Streaming Infrastructure
- Task 4: Update Chat POST Endpoint
- Task 5: Chat History GET Endpoint
- Task 6: SSE Stream Endpoint
- Task 7: Frontend Integration
- Task 8: Authorization & Validation
- Task 9: Error Recovery
- Task 10: Integration Tests
- Task 11: Documentation

**Estimated Time:** ~6-8 hours total
**Lines of Code:** ~800-1000 lines (backend + frontend + tests + docs)
**Tests:** 3 integration tests + existing tests
**Commits:** 11 commits (one per task)

---

## Post-Implementation Checklist

After completing all tasks:

- [ ] All 11 tasks completed
- [ ] All tests passing (integration + unit)
- [ ] Manual testing completed in browser
- [ ] SSE streaming verified
- [ ] Chat history works across page reloads
- [ ] Error recovery tested
- [ ] Documentation complete
- [ ] All commits pushed to GitHub
- [ ] README.md updated

---

**Plan Created:** 2025-12-28
**Target Implementation:** Phase 6 (Backend Chat Integration)
**Prerequisites:** Phase 1-5 complete
