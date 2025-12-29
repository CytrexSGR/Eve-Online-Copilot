# Phase 6 Usage Examples: Chat Integration & SSE Streaming

This document provides practical, copy-paste ready examples for using the Phase 6 chat endpoints.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Basic Chat (Non-Streaming)](#basic-chat-non-streaming)
3. [Real-Time Streaming (SSE)](#real-time-streaming-sse)
4. [Chat History](#chat-history)
5. [Error Handling](#error-handling)
6. [React Integration](#react-integration)
7. [Python Integration](#python-integration)
8. [Complete Applications](#complete-applications)

---

## Quick Start

### Prerequisites

```bash
# Ensure backend is running
cd /home/cytrex/eve_copilot
uvicorn main:app --reload

# Backend should be at http://localhost:8000
```

### Test Endpoints

```bash
# Health check
curl http://localhost:8000/docs

# Create session
curl -X POST http://localhost:8000/agent/session \
  -H "Content-Type: application/json" \
  -d '{"character_id":526379435,"autonomy_level":"RECOMMENDATIONS"}'
```

---

## Basic Chat (Non-Streaming)

### Example 1: Start New Conversation

```bash
curl -X POST http://localhost:8000/agent/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is the most profitable T1 frigate to manufacture?",
    "session_id": null,
    "character_id": 526379435
  }'
```

**Response:**
```json
{
  "session_id": "sess-a1b2c3d4",
  "status": "idle"
}
```

### Example 2: Continue Existing Conversation

```bash
SESSION_ID="sess-a1b2c3d4"

curl -X POST http://localhost:8000/agent/chat \
  -H "Content-Type: application/json" \
  -d "{
    \"message\": \"Where should I sell it?\",
    \"session_id\": \"$SESSION_ID\",
    \"character_id\": 526379435
  }"
```

### Example 3: Multi-Turn Conversation

```bash
#!/bin/bash
# save as: chat_demo.sh

# Start conversation
RESPONSE=$(curl -s -X POST http://localhost:8000/agent/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello! I want to start manufacturing.","session_id":null,"character_id":526379435}')

SESSION_ID=$(echo $RESPONSE | jq -r '.session_id')
echo "Created session: $SESSION_ID"

# Ask follow-up questions
curl -s -X POST http://localhost:8000/agent/chat \
  -H "Content-Type: application/json" \
  -d "{\"message\":\"What skills do I need?\",\"session_id\":\"$SESSION_ID\",\"character_id\":526379435}" | jq

curl -s -X POST http://localhost:8000/agent/chat \
  -H "Content-Type: application/json" \
  -d "{\"message\":\"How much ISK to start?\",\"session_id\":\"$SESSION_ID\",\"character_id\":526379435}" | jq

# Get chat history
curl -s "http://localhost:8000/agent/chat/history/$SESSION_ID" | jq
```

---

## Real-Time Streaming (SSE)

### Example 4: Stream with curl

```bash
# Stream response in real-time
curl -N -X POST http://localhost:8000/agent/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Explain the best mining strategy for a new player",
    "session_id": "sess-a1b2c3d4",
    "character_id": 526379435
  }'
```

**Output:**
```
data: {"type":"text","text":"For"}

data: {"type":"text","text":" new"}

data: {"type":"text","text":" players"}

data: {"type":"text","text":", I"}

data: {"type":"text","text":" recommend"}

...

data: {"type":"done","message_id":"msg-xyz789"}
```

### Example 5: JavaScript EventSource

```javascript
// stream_chat.js
function streamChat(message, sessionId) {
  const url = 'http://localhost:8000/agent/chat/stream';

  // Create request body
  const body = JSON.stringify({
    message: message,
    session_id: sessionId,
    character_id: 526379435
  });

  // Note: Standard EventSource doesn't support POST
  // Use fetch with streaming instead
  fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body
  }).then(response => {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    function readChunk() {
      reader.read().then(({ done, value }) => {
        if (done) {
          console.log('Stream complete');
          return;
        }

        // Decode chunk
        const chunk = decoder.decode(value, { stream: true });

        // Parse SSE events (data: {...}\n\n)
        const events = chunk.split('\n\n');

        events.forEach(event => {
          if (event.startsWith('data: ')) {
            const json = event.substring(6);
            const data = JSON.parse(json);

            switch(data.type) {
              case 'text':
                process.stdout.write(data.text);
                break;

              case 'done':
                console.log('\n\nMessage ID:', data.message_id);
                break;

              case 'error':
                console.error('\nError:', data.error);
                break;

              case 'retry':
                console.log(`\nRetrying (${data.attempt}/${data.max_attempts})...`);
                break;
            }
          }
        });

        // Read next chunk
        readChunk();
      });
    }

    readChunk();
  }).catch(error => {
    console.error('Fetch error:', error);
  });
}

// Usage
streamChat(
  'What are the best minerals to mine?',
  'sess-a1b2c3d4'
);
```

### Example 6: Python Streaming Client

```python
# stream_client.py
import requests
import json
import sseclient  # pip install sseclient-py

def stream_chat(message: str, session_id: str, character_id: int = 526379435):
    """Stream chat response and print in real-time."""
    url = 'http://localhost:8000/agent/chat/stream'

    response = requests.post(
        url,
        json={
            'message': message,
            'session_id': session_id,
            'character_id': character_id
        },
        stream=True,
        headers={'Accept': 'text/event-stream'}
    )

    client = sseclient.SSEClient(response)

    full_text = ""

    for event in client.events():
        data = json.loads(event.data)

        if data['type'] == 'text':
            text = data['text']
            full_text += text
            print(text, end='', flush=True)

        elif data['type'] == 'done':
            print(f"\n\nMessage saved: {data['message_id']}")
            break

        elif data['type'] == 'error':
            print(f"\n\nError: {data['error']}")
            break

        elif data['type'] == 'retry':
            print(f"\nRetrying ({data['attempt']}/{data['max_attempts']})...")

    return full_text


# Usage
if __name__ == '__main__':
    session_id = 'sess-a1b2c3d4'
    message = 'What is the best way to make ISK as a new player?'

    response = stream_chat(message, session_id)
    print(f"\nFull response length: {len(response)} characters")
```

---

## Chat History

### Example 7: Get Recent Messages

```bash
# Get last 10 messages
curl "http://localhost:8000/agent/chat/history/sess-a1b2c3d4?limit=10" | jq
```

**Response:**
```json
{
  "session_id": "sess-a1b2c3d4",
  "message_count": 10,
  "messages": [
    {
      "id": "msg-001",
      "role": "user",
      "content": "Hello! I want to start manufacturing.",
      "content_blocks": [{"type": "text", "text": "Hello! I want to start manufacturing."}],
      "created_at": "2025-12-29T10:00:00Z",
      "token_usage": null
    },
    {
      "id": "msg-002",
      "role": "assistant",
      "content": "Great! Manufacturing in EVE Online...",
      "content_blocks": [{"type": "text", "text": "Great! Manufacturing..."}],
      "created_at": "2025-12-29T10:00:05Z",
      "token_usage": {
        "input_tokens": 125,
        "output_tokens": 650
      }
    }
  ]
}
```

### Example 8: Format Chat History

```python
# format_history.py
import requests
from datetime import datetime

def display_chat_history(session_id: str, limit: int = 50):
    """Fetch and display chat history in readable format."""
    url = f'http://localhost:8000/agent/chat/history/{session_id}'

    response = requests.get(url, params={'limit': limit})
    data = response.json()

    print(f"\n{'='*80}")
    print(f"Chat History - Session: {data['session_id']}")
    print(f"Total Messages: {data['message_count']}")
    print(f"{'='*80}\n")

    for msg in data['messages']:
        # Parse timestamp
        timestamp = datetime.fromisoformat(msg['created_at'].replace('Z', '+00:00'))

        # Format role
        role_display = {
            'user': '👤 USER',
            'assistant': '🤖 AGENT',
            'system': '⚙️  SYSTEM'
        }[msg['role']]

        # Print message
        print(f"[{timestamp:%Y-%m-%d %H:%M:%S}] {role_display}")
        print(f"  {msg['content']}\n")

        # Show token usage for assistant messages
        if msg['token_usage']:
            tokens = msg['token_usage']
            total = tokens['input_tokens'] + tokens['output_tokens']
            print(f"  💬 Tokens: {tokens['input_tokens']} in + {tokens['output_tokens']} out = {total} total\n")

        print(f"{'-'*80}\n")


# Usage
if __name__ == '__main__':
    display_chat_history('sess-a1b2c3d4', limit=20)
```

### Example 9: Export Chat to Text File

```python
# export_chat.py
import requests
from datetime import datetime

def export_chat_to_file(session_id: str, filename: str = 'chat_export.txt'):
    """Export chat history to text file."""
    response = requests.get(f'http://localhost:8000/agent/chat/history/{session_id}')
    data = response.json()

    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"EVE Co-Pilot Chat Export\n")
        f.write(f"Session ID: {data['session_id']}\n")
        f.write(f"Exported: {datetime.now():%Y-%m-%d %H:%M:%S}\n")
        f.write(f"Total Messages: {data['message_count']}\n")
        f.write(f"\n{'='*80}\n\n")

        for msg in data['messages']:
            timestamp = datetime.fromisoformat(msg['created_at'].replace('Z', '+00:00'))
            role = msg['role'].upper()

            f.write(f"[{timestamp:%Y-%m-%d %H:%M:%S}] {role}:\n")
            f.write(f"{msg['content']}\n\n")

            if msg['token_usage']:
                tokens = msg['token_usage']
                f.write(f"Tokens: {tokens['input_tokens']} in, {tokens['output_tokens']} out\n\n")

            f.write(f"{'-'*80}\n\n")

    print(f"Chat exported to {filename}")


# Usage
export_chat_to_file('sess-a1b2c3d4', 'my_chat.txt')
```

---

## Error Handling

### Example 10: Handle Empty Messages

```python
import requests

try:
    response = requests.post('http://localhost:8000/agent/chat', json={
        'message': '',  # Invalid: empty message
        'session_id': 'sess-123',
        'character_id': 526379435
    })
    response.raise_for_status()

except requests.exceptions.HTTPError as e:
    if e.response.status_code == 400:
        print(f"Validation error: {e.response.json()['detail']}")
        # Output: "Message content cannot be empty"
```

### Example 11: Handle Invalid Session

```python
import requests

try:
    response = requests.post('http://localhost:8000/agent/chat', json={
        'message': 'Hello',
        'session_id': 'invalid-session-id',
        'character_id': 526379435
    })
    response.raise_for_status()

except requests.exceptions.HTTPError as e:
    if e.response.status_code == 404:
        print(f"Session error: {e.response.json()['detail']}")
        # Output: "Session not found"
```

### Example 12: Retry on Stream Failure

```javascript
// stream_with_retry.js
async function streamChatWithRetry(message, sessionId, maxRetries = 3) {
  let attempt = 0;

  while (attempt < maxRetries) {
    try {
      await streamChat(message, sessionId);
      return; // Success
    } catch (error) {
      attempt++;
      console.error(`Attempt ${attempt} failed:`, error);

      if (attempt < maxRetries) {
        const delay = Math.pow(2, attempt) * 1000; // Exponential backoff
        console.log(`Retrying in ${delay}ms...`);
        await new Promise(resolve => setTimeout(resolve, delay));
      } else {
        console.error('Max retries exceeded');
        throw error;
      }
    }
  }
}
```

---

## React Integration

### Example 13: Chat Component with Hooks

```typescript
// ChatComponent.tsx
import { useState, useCallback } from 'react';
import axios from 'axios';

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
}

export function ChatComponent({ sessionId }: { sessionId: string }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [streaming, setStreaming] = useState(false);

  const sendMessage = useCallback(async (message: string) => {
    if (!message.trim()) return;

    // Add user message
    setMessages(prev => [...prev, {
      id: `temp-${Date.now()}`,
      role: 'user',
      content: message,
      timestamp: new Date().toISOString()
    }]);

    setInput('');
    setStreaming(true);

    // Add streaming placeholder
    const streamingMsgId = `streaming-${Date.now()}`;
    setMessages(prev => [...prev, {
      id: streamingMsgId,
      role: 'assistant',
      content: '',
      timestamp: new Date().toISOString()
    }]);

    try {
      const response = await fetch('http://localhost:8000/agent/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message,
          session_id: sessionId,
          character_id: 526379435
        })
      });

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      while (reader) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const events = chunk.split('\n\n');

        for (const event of events) {
          if (event.startsWith('data: ')) {
            const data = JSON.parse(event.substring(6));

            if (data.type === 'text') {
              setMessages(prev => {
                const updated = [...prev];
                const msg = updated.find(m => m.id === streamingMsgId);
                if (msg) msg.content += data.text;
                return updated;
              });
            } else if (data.type === 'done') {
              setMessages(prev => {
                const updated = [...prev];
                const msg = updated.find(m => m.id === streamingMsgId);
                if (msg) msg.id = data.message_id;
                return updated;
              });
            }
          }
        }
      }
    } catch (error) {
      console.error('Streaming error:', error);
    } finally {
      setStreaming(false);
    }
  }, [sessionId]);

  return (
    <div className="chat-container">
      <div className="messages">
        {messages.map(msg => (
          <div key={msg.id} className={`message ${msg.role}`}>
            <div className="role">{msg.role}</div>
            <div className="content">{msg.content}</div>
          </div>
        ))}
      </div>

      <div className="input-area">
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyPress={e => e.key === 'Enter' && sendMessage(input)}
          disabled={streaming}
          placeholder="Type a message..."
        />
        <button onClick={() => sendMessage(input)} disabled={streaming}>
          {streaming ? 'Sending...' : 'Send'}
        </button>
      </div>
    </div>
  );
}
```

### Example 14: Load History on Mount

```typescript
// ChatWithHistory.tsx
import { useState, useEffect } from 'react';
import axios from 'axios';

export function ChatWithHistory({ sessionId }: { sessionId: string }) {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Load chat history
    async function loadHistory() {
      try {
        const response = await axios.get(
          `http://localhost:8000/agent/chat/history/${sessionId}`,
          { params: { limit: 100 } }
        );

        setMessages(response.data.messages.map(msg => ({
          id: msg.id,
          role: msg.role,
          content: msg.content,
          timestamp: msg.created_at
        })));
      } catch (error) {
        console.error('Failed to load history:', error);
      } finally {
        setLoading(false);
      }
    }

    loadHistory();
  }, [sessionId]);

  if (loading) {
    return <div>Loading chat history...</div>;
  }

  return (
    <div className="chat-history">
      {messages.map(msg => (
        <div key={msg.id} className={`message ${msg.role}`}>
          <span className="timestamp">
            {new Date(msg.timestamp).toLocaleTimeString()}
          </span>
          <span className="role">{msg.role}:</span>
          <span className="content">{msg.content}</span>
        </div>
      ))}
    </div>
  );
}
```

---

## Python Integration

### Example 15: Python Chat Client Class

```python
# chat_client.py
import requests
from typing import Optional, List, Dict, Callable
import json

class AgentChatClient:
    """Python client for EVE Co-Pilot Agent Chat API."""

    def __init__(self, base_url: str = 'http://localhost:8000'):
        self.base_url = base_url
        self.character_id = 526379435

    def send_message(
        self,
        message: str,
        session_id: Optional[str] = None
    ) -> Dict:
        """Send message to agent (non-streaming)."""
        response = requests.post(
            f'{self.base_url}/agent/chat',
            json={
                'message': message,
                'session_id': session_id,
                'character_id': self.character_id
            }
        )
        response.raise_for_status()
        return response.json()

    def stream_message(
        self,
        message: str,
        session_id: str,
        on_chunk: Callable[[str], None],
        on_done: Callable[[str], None],
        on_error: Callable[[str], None]
    ):
        """Send message and stream response."""
        import sseclient

        response = requests.post(
            f'{self.base_url}/agent/chat/stream',
            json={
                'message': message,
                'session_id': session_id,
                'character_id': self.character_id
            },
            stream=True,
            headers={'Accept': 'text/event-stream'}
        )

        client = sseclient.SSEClient(response)

        for event in client.events():
            data = json.loads(event.data)

            if data['type'] == 'text':
                on_chunk(data['text'])
            elif data['type'] == 'done':
                on_done(data['message_id'])
                break
            elif data['type'] == 'error':
                on_error(data['error'])
                break

    def get_history(
        self,
        session_id: str,
        limit: int = 100
    ) -> List[Dict]:
        """Get chat history for session."""
        response = requests.get(
            f'{self.base_url}/agent/chat/history/{session_id}',
            params={'limit': limit}
        )
        response.raise_for_status()
        return response.json()['messages']


# Usage
if __name__ == '__main__':
    client = AgentChatClient()

    # Send message
    result = client.send_message('Hello agent!')
    session_id = result['session_id']
    print(f"Session: {session_id}")

    # Stream message
    print("\nStreaming response:")
    client.stream_message(
        'What is Tritanium used for?',
        session_id,
        on_chunk=lambda text: print(text, end='', flush=True),
        on_done=lambda msg_id: print(f"\n\nSaved: {msg_id}"),
        on_error=lambda err: print(f"\n\nError: {err}")
    )

    # Get history
    print("\n\nChat history:")
    messages = client.get_history(session_id)
    for msg in messages:
        print(f"{msg['role']}: {msg['content'][:50]}...")
```

---

## Complete Applications

### Example 16: CLI Chat Application

```python
# cli_chat.py
#!/usr/bin/env python3
"""
Interactive CLI chat application for EVE Co-Pilot Agent.
"""

import requests
import json
import sys
from datetime import datetime

BASE_URL = 'http://localhost:8000'
CHARACTER_ID = 526379435

def create_session():
    """Create new agent session."""
    response = requests.post(f'{BASE_URL}/agent/session', json={
        'character_id': CHARACTER_ID,
        'autonomy_level': 'RECOMMENDATIONS'
    })
    return response.json()['session_id']

def send_message(session_id: str, message: str):
    """Send message and get response."""
    response = requests.post(f'{BASE_URL}/agent/chat', json={
        'message': message,
        'session_id': session_id,
        'character_id': CHARACTER_ID
    })
    return response.json()

def display_history(session_id: str):
    """Display recent chat history."""
    response = requests.get(f'{BASE_URL}/agent/chat/history/{session_id}', params={'limit': 10})
    data = response.json()

    print("\n--- Recent Messages ---")
    for msg in data['messages'][-5:]:  # Last 5 messages
        role = msg['role'].upper()
        content = msg['content'][:100] + ('...' if len(msg['content']) > 100 else '')
        print(f"{role}: {content}")
    print()

def main():
    """Main CLI loop."""
    print("EVE Co-Pilot Agent - Interactive Chat")
    print("=" * 50)

    # Create session
    session_id = create_session()
    print(f"Session created: {session_id}\n")

    print("Commands:")
    print("  /history - Show recent messages")
    print("  /quit    - Exit chat")
    print("  /help    - Show this help")
    print()

    while True:
        try:
            # Get user input
            user_input = input("You: ").strip()

            if not user_input:
                continue

            # Handle commands
            if user_input == '/quit':
                print("Goodbye!")
                break
            elif user_input == '/history':
                display_history(session_id)
                continue
            elif user_input == '/help':
                print("\nCommands:")
                print("  /history - Show recent messages")
                print("  /quit    - Exit chat")
                print("  /help    - Show this help")
                print()
                continue

            # Send message
            result = send_message(session_id, user_input)

            # Get latest message from history
            history = requests.get(f'{BASE_URL}/agent/chat/history/{session_id}').json()
            if history['messages']:
                last_msg = history['messages'][-1]
                if last_msg['role'] == 'assistant':
                    print(f"\nAgent: {last_msg['content']}\n")

        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}\n")

if __name__ == '__main__':
    main()
```

**Run it:**
```bash
chmod +x cli_chat.py
./cli_chat.py
```

---

## Related Documentation

- [Phase 6 API Documentation](phase6-api-documentation.md)
- [Phase 6 Completion Report](phase6-completion.md)
- [Agent Runtime Design](../plans/2025-12-28-agent-runtime-design.md)
