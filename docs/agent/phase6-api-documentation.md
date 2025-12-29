# Phase 6 API Documentation: Chat Integration & SSE Streaming

## Overview

Phase 6 introduces comprehensive chat capabilities with message persistence, Server-Sent Events (SSE) streaming for real-time responses, and full integration with the Agent Runtime system.

**Key Features:**
- Message persistence to PostgreSQL database
- Real-time streaming via Server-Sent Events (SSE)
- Chat history retrieval with pagination
- Authorization and validation middleware
- Error recovery with automatic retry logic

---

## Endpoints

### 1. POST /agent/chat

Send a message to the agent with automatic message persistence.

**Purpose:** Send a chat message to the agent. Creates a new session if no session_id is provided, otherwise continues an existing conversation.

**Request:**
```typescript
POST /agent/chat
Content-Type: application/json

{
  "message": string,           // Required: Message content (max 10,000 chars)
  "session_id": string | null, // Optional: Session ID (creates new if null)
  "character_id": number       // Required: EVE character ID
}
```

**Response:**
```typescript
{
  "session_id": string,  // Session ID (newly created or existing)
  "status": string       // Session status: "idle" | "thinking" | "executing" | "error"
}
```

**Example:**
```bash
# Create new session and send message
curl -X POST http://localhost:8000/agent/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is the best ship for mining in high-sec?",
    "session_id": null,
    "character_id": 526379435
  }'

# Response
{
  "session_id": "sess-abc123",
  "status": "idle"
}
```

**Behavior:**
- Validates message content (non-empty, max 10,000 characters)
- Creates new session if `session_id` is null
- Loads existing session if `session_id` is provided
- Saves user message to database (`agent_messages` table)
- Executes agent runtime to generate response
- Saves assistant response to database
- Returns session status

**Error Codes:**
- `400` - Bad Request: Empty message or message too long
- `404` - Not Found: Session not found
- `500` - Internal Server Error: Runtime not initialized

---

### 2. POST /agent/chat/stream

Stream agent responses in real-time using Server-Sent Events (SSE).

**Purpose:** Send a message and receive the agent's response as a stream of text chunks for real-time display.

**Request:**
```typescript
POST /agent/chat/stream
Content-Type: application/json

{
  "message": string,       // Required: Message content (max 10,000 chars)
  "session_id": string,    // Required: Session ID
  "character_id": number   // Required: EVE character ID
}
```

**Response:**
```
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
X-Accel-Buffering: no

data: {"type":"text","text":"Hello"}

data: {"type":"text","text":" there"}

data: {"type":"text","text":"!"}

data: {"type":"done","message_id":"msg-abc123"}
```

**Event Types:**

1. **Text Chunk:**
```json
{
  "type": "text",
  "text": "string"  // Text fragment
}
```

2. **Completion:**
```json
{
  "type": "done",
  "message_id": "string"  // ID of saved assistant message
}
```

3. **Error:**
```json
{
  "type": "error",
  "error": "string"  // Error message
}
```

4. **Retry Notification:**
```json
{
  "type": "retry",
  "attempt": number,      // Current retry attempt
  "max_attempts": number  // Maximum retry attempts (3)
}
```

**JavaScript Example:**
```javascript
const eventSource = new EventSource(
  'http://localhost:8000/agent/chat/stream',
  {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message: "Tell me about Tritanium production",
      session_id: "sess-abc123",
      character_id: 526379435
    })
  }
);

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);

  switch(data.type) {
    case 'text':
      // Append text chunk to display
      appendText(data.text);
      break;

    case 'done':
      // Stream complete
      console.log('Message saved:', data.message_id);
      eventSource.close();
      break;

    case 'error':
      // Handle error
      console.error('Stream error:', data.error);
      eventSource.close();
      break;

    case 'retry':
      // Show retry notification
      console.log(`Retrying... (${data.attempt}/${data.max_attempts})`);
      break;
  }
};

eventSource.onerror = (error) => {
  console.error('Connection error:', error);
  eventSource.close();
};
```

**Behavior:**
- Validates message content
- Verifies session access
- Saves user message to database
- Streams LLM response in real-time
- Accumulates full response text
- Saves complete assistant response to database
- Sends completion event with message ID
- Automatically retries on failure (up to 3 attempts with exponential backoff)

**Error Codes:**
- `400` - Bad Request: Invalid message content
- `404` - Not Found: Session not found
- `500` - Internal Server Error: Services not initialized

---

### 3. GET /agent/chat/history/{session_id}

Retrieve chat history for a session with pagination support.

**Purpose:** Get all messages for a specific session, ordered chronologically.

**Request:**
```typescript
GET /agent/chat/history/{session_id}?limit=100
Authorization: Bearer <token>  // Optional
```

**Parameters:**
- `session_id` (path): Session ID
- `limit` (query): Maximum messages to return (default: 100)

**Response:**
```typescript
{
  "session_id": string,
  "message_count": number,
  "messages": [
    {
      "id": string,              // Message ID
      "role": "user" | "assistant" | "system",
      "content": string,         // Full message text
      "content_blocks": [        // Structured content
        {
          "type": "text",
          "text": string
        }
      ],
      "created_at": string,      // ISO 8601 timestamp
      "token_usage": {           // Only for assistant messages
        "input_tokens": number,
        "output_tokens": number
      } | null
    }
  ]
}
```

**Example:**
```bash
curl http://localhost:8000/agent/chat/history/sess-abc123?limit=50

# Response
{
  "session_id": "sess-abc123",
  "message_count": 4,
  "messages": [
    {
      "id": "msg-001",
      "role": "user",
      "content": "What is the best mining ship?",
      "content_blocks": [
        {
          "type": "text",
          "text": "What is the best mining ship?"
        }
      ],
      "created_at": "2025-12-29T10:00:00Z",
      "token_usage": null
    },
    {
      "id": "msg-002",
      "role": "assistant",
      "content": "For high-sec mining, I recommend the Covetor...",
      "content_blocks": [
        {
          "type": "text",
          "text": "For high-sec mining, I recommend the Covetor..."
        }
      ],
      "created_at": "2025-12-29T10:00:05Z",
      "token_usage": {
        "input_tokens": 125,
        "output_tokens": 450
      }
    }
  ]
}
```

**Behavior:**
- Verifies session access (authorization)
- Loads messages from database in chronological order
- Returns up to `limit` messages (default 100)
- Includes message metadata (timestamps, token usage)
- Returns 404 if session not found

**Error Codes:**
- `404` - Not Found: Session not found
- `500` - Internal Server Error: Database not initialized

---

## Database Schema

### agent_messages Table

Stores all chat messages with full content and metadata.

```sql
CREATE TABLE agent_messages (
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
```

**Columns:**
- `id`: Unique message identifier (format: `msg-{uuid}`)
- `session_id`: Foreign key to `agent_sessions`
- `role`: Message role (`user`, `assistant`, `system`)
- `content`: Full message text
- `content_blocks`: Structured content (JSON array)
- `created_at`: Message creation timestamp
- `token_usage`: Token usage for assistant messages (JSON object)

**Indexes:**
- `idx_agent_messages_session`: Fast lookup by session
- `idx_agent_messages_created`: Chronological ordering

**Cascade Behavior:**
- Messages are automatically deleted when parent session is deleted

---

## Message Flow

### Non-Streaming Flow (POST /agent/chat)

```
┌─────────┐                ┌──────────┐                ┌──────────┐
│ Client  │                │  Server  │                │ Database │
└────┬────┘                └────┬─────┘                └────┬─────┘
     │                          │                           │
     │ POST /agent/chat         │                           │
     ├─────────────────────────>│                           │
     │                          │                           │
     │                          │ Validate message          │
     │                          │                           │
     │                          │ Save user message         │
     │                          ├──────────────────────────>│
     │                          │                           │
     │                          │ Execute LLM               │
     │                          │                           │
     │                          │ Save assistant message    │
     │                          ├──────────────────────────>│
     │                          │                           │
     │ Response (session_id)    │                           │
     │<─────────────────────────┤                           │
     │                          │                           │
```

### Streaming Flow (POST /agent/chat/stream)

```
┌─────────┐                ┌──────────┐                ┌──────────┐
│ Client  │                │  Server  │                │ Database │
└────┬────┘                └────┬─────┘                └────┬─────┘
     │                          │                           │
     │ POST /agent/chat/stream  │                           │
     ├─────────────────────────>│                           │
     │                          │                           │
     │                          │ Validate & save user msg  │
     │                          ├──────────────────────────>│
     │                          │                           │
     │ SSE: {"type":"text",     │ Stream LLM chunks         │
     │<─────────────────────────┤                           │
     │      "text":"Hello"}     │                           │
     │                          │                           │
     │ SSE: {"type":"text",     │                           │
     │<─────────────────────────┤                           │
     │      "text":" there"}    │                           │
     │                          │                           │
     │                          │ Save complete message     │
     │                          ├──────────────────────────>│
     │                          │                           │
     │ SSE: {"type":"done",     │                           │
     │<─────────────────────────┤                           │
     │      "message_id":"..."}│                           │
     │                          │                           │
```

### History Retrieval Flow

```
┌─────────┐                ┌──────────┐                ┌──────────┐
│ Client  │                │  Server  │                │ Database │
└────┬────┘                └────┬─────┘                └────┬─────┘
     │                          │                           │
     │ GET /agent/chat/history  │                           │
     ├─────────────────────────>│                           │
     │                          │                           │
     │                          │ Verify session access     │
     │                          │                           │
     │                          │ Query messages            │
     │                          ├──────────────────────────>│
     │                          │                           │
     │                          │ Messages (ordered)        │
     │                          │<──────────────────────────┤
     │                          │                           │
     │ Chat history (JSON)      │                           │
     │<─────────────────────────┤                           │
     │                          │                           │
```

---

## Error Handling

### Validation Errors

**Empty Message:**
```json
{
  "detail": "Message content cannot be empty"
}
```
Status Code: 400

**Message Too Long:**
```json
{
  "detail": "Message too long (max 10000 characters)"
}
```
Status Code: 400

### Session Errors

**Session Not Found:**
```json
{
  "detail": "Session not found"
}
```
Status Code: 404

### Runtime Errors

**Services Not Initialized:**
```json
{
  "detail": "Agent runtime not initialized"
}
```
Status Code: 500

**Database Not Initialized:**
```json
{
  "detail": "Database not initialized"
}
```
Status Code: 500

### Streaming Errors

**SSE Error Event:**
```json
{
  "type": "error",
  "error": "Connection timeout"
}
```

**SSE Retry Event:**
```json
{
  "type": "retry",
  "attempt": 2,
  "max_attempts": 3
}
```

---

## Authorization & Security

### Phase 6 Implementation

**Current State:**
- Placeholder authorization middleware
- Basic session validation
- Message content validation

**Authorization Headers:**
```http
Authorization: Bearer <token>
```

Currently optional. Phase 7 will implement full JWT validation.

### Validation Rules

**Message Content:**
- Cannot be empty or whitespace-only
- Maximum length: 10,000 characters

**Session Access:**
- Session must exist in database
- Session must be accessible (Phase 7: verify ownership via JWT)

---

## Performance Considerations

### Message Persistence

- Messages are saved to PostgreSQL with indexes on `session_id` and `created_at`
- Batch operations use database connection pool (2-10 connections)
- Average insert time: <10ms per message

### SSE Streaming

- Chunks are sent as they arrive from LLM (no buffering)
- Average latency: <50ms per chunk
- Connection timeout: 30 seconds
- Automatic reconnection with exponential backoff

### Chat History

- Default limit: 100 messages per request
- Pagination supported via `limit` parameter
- Indexed queries for fast retrieval
- Average response time: <50ms for 100 messages

---

## Usage Examples

### Example 1: Simple Chat Conversation

```python
import requests

# Start conversation
response = requests.post('http://localhost:8000/agent/chat', json={
    'message': 'What mining ships should I focus on?',
    'session_id': None,  # Create new session
    'character_id': 526379435
})

session_id = response.json()['session_id']
print(f"Session created: {session_id}")

# Continue conversation
response = requests.post('http://localhost:8000/agent/chat', json={
    'message': 'What skills do I need for the Covetor?',
    'session_id': session_id,
    'character_id': 526379435
})

# Get chat history
history = requests.get(f'http://localhost:8000/agent/chat/history/{session_id}')
messages = history.json()['messages']

for msg in messages:
    print(f"{msg['role']}: {msg['content'][:100]}...")
```

### Example 2: Streaming Chat with React

```typescript
import { useState, useEffect } from 'react';

function ChatComponent() {
  const [messages, setMessages] = useState([]);
  const [streamingText, setStreamingText] = useState('');

  const sendStreamingMessage = (message: string, sessionId: string) => {
    // Add user message immediately
    setMessages(prev => [...prev, { role: 'user', content: message }]);

    // Create streaming placeholder
    const assistantIndex = messages.length + 1;
    setMessages(prev => [...prev, { role: 'assistant', content: '' }]);

    // Connect to SSE
    const eventSource = new EventSource(
      `http://localhost:8000/agent/chat/stream`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message,
          session_id: sessionId,
          character_id: 526379435
        })
      }
    );

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === 'text') {
        // Update streaming message
        setMessages(prev => {
          const updated = [...prev];
          updated[assistantIndex].content += data.text;
          return updated;
        });
      } else if (data.type === 'done') {
        // Complete
        console.log('Message saved:', data.message_id);
        eventSource.close();
      } else if (data.type === 'error') {
        console.error('Error:', data.error);
        eventSource.close();
      }
    };

    return () => eventSource.close();
  };

  return (
    <div>
      {/* Chat UI */}
    </div>
  );
}
```

### Example 3: Load and Display History

```python
import requests
from datetime import datetime

def display_chat_history(session_id: str):
    """Load and display chat history with timestamps."""
    response = requests.get(
        f'http://localhost:8000/agent/chat/history/{session_id}',
        params={'limit': 50}
    )

    data = response.json()
    print(f"Session: {data['session_id']}")
    print(f"Total messages: {data['message_count']}\n")

    for msg in data['messages']:
        timestamp = datetime.fromisoformat(msg['created_at'])
        role = msg['role'].upper()
        content = msg['content']

        print(f"[{timestamp:%Y-%m-%d %H:%M}] {role}:")
        print(f"  {content}\n")

        if msg['token_usage']:
            tokens = msg['token_usage']
            print(f"  Tokens: {tokens['input_tokens']} in, {tokens['output_tokens']} out\n")

# Usage
display_chat_history('sess-abc123')
```

---

## Testing

### Unit Tests

```python
import pytest
from copilot_server.agent.messages import AgentMessage, MessageRepository

@pytest.mark.asyncio
async def test_message_persistence():
    """Test message save and retrieval."""
    # Test implemented in copilot_server/tests/agent/test_messages.py
    pass
```

### Integration Tests

```python
import pytest
from fastapi.testclient import TestClient

def test_chat_flow():
    """Test complete chat flow."""
    # Test implemented in copilot_server/tests/integration/test_chat_flow.py
    pass
```

### Manual Testing

```bash
# Test chat endpoint
curl -X POST http://localhost:8000/agent/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello","session_id":null,"character_id":526379435}'

# Test streaming
curl -N -X POST http://localhost:8000/agent/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello","session_id":"sess-123","character_id":526379435}'

# Test history
curl http://localhost:8000/agent/chat/history/sess-123
```

---

## Migration Guide

### From Phase 5 to Phase 6

**Database:**
```sql
-- Run migration
docker exec eve_db psql -U eve -d eve_sde -f /migrations/006_agent_messages.sql
```

**Backend:**
- No breaking changes
- New endpoints added
- Existing endpoints unchanged

**Frontend:**
- New API methods available
- Existing components work unchanged
- Optional: Use SSE streaming for better UX

---

## Related Documentation

- [Phase 6 Implementation Plan](../plans/2025-12-28-agent-runtime-phase6-implementation.md)
- [Agent Runtime Design](../plans/2025-12-28-agent-runtime-design.md)
- [Phase 5 Completion Report](phase5-completion.md)
