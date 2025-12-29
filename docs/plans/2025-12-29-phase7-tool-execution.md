# Phase 7: Agent Runtime Tool Execution & Agentic Loop

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Enable Agent Runtime to execute MCP tools in response to user queries, creating a full agentic loop where the LLM can request data from EVE Online database and provide informed answers.

**Architecture:** Extend existing SSE streaming infrastructure to detect tool calls from LLM stream, execute tools via ToolOrchestrator, handle plan approval for high-risk operations (L2/L3 autonomy), stream intermediate results and final answers back to user, broadcast events via WebSocket for real-time status updates.

**Tech Stack:** FastAPI, AsyncIO, Anthropic Streaming API, OpenAI Streaming API, ToolOrchestrator (existing), EventBus (existing), PostgreSQL, SSE (Server-Sent Events)

---

## Prerequisites

- Phase 6 completed: Backend Chat Integration, SSE Streaming, WebSocket Events, Message Persistence
- Existing: ToolOrchestrator with governance (L0-L3), 115 MCP Tools, Authorization middleware
- System supports both Anthropic Claude and OpenAI GPT-4.1-nano

---

## Task 1: Streaming Tool Call Detection

**Goal:** Extract tool calls from LLM streaming responses (both Anthropic and OpenAI)

**Files:**
- Modify: `copilot_server/agent/streaming.py:63-108`
- Create: `copilot_server/agent/tool_extractor.py`
- Test: `copilot_server/tests/test_tool_extractor.py`

**Step 1: Write failing test for tool call extraction**

Create `copilot_server/tests/test_tool_extractor.py`:

```python
import pytest
from copilot_server.agent.tool_extractor import ToolCallExtractor

def test_extract_tool_call_from_anthropic_stream():
    """Test extracting tool_use blocks from Anthropic streaming chunks."""
    extractor = ToolCallExtractor()

    # Simulate Anthropic streaming events
    chunks = [
        {"type": "content_block_start", "index": 0, "content_block": {"type": "tool_use", "id": "toolu_123", "name": "get_market_price"}},
        {"type": "content_block_delta", "index": 0, "delta": {"type": "input_json_delta", "partial_json": '{"type'}},
        {"type": "content_block_delta", "index": 0, "delta": {"type": "input_json_delta", "partial_json": '_id": 34'}},
        {"type": "content_block_delta", "index": 0, "delta": {"type": "input_json_delta", "partial_json": '}'}},
        {"type": "content_block_stop", "index": 0}
    ]

    for chunk in chunks:
        extractor.process_chunk(chunk)

    tool_calls = extractor.get_tool_calls()

    assert len(tool_calls) == 1
    assert tool_calls[0]["id"] == "toolu_123"
    assert tool_calls[0]["name"] == "get_market_price"
    assert tool_calls[0]["input"] == {"type_id": 34}

def test_extract_mixed_text_and_tool_calls():
    """Test extracting both text and tool calls from same response."""
    extractor = ToolCallExtractor()

    chunks = [
        {"type": "content_block_start", "index": 0, "content_block": {"type": "text"}},
        {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "Let me check"}},
        {"type": "content_block_stop", "index": 0},
        {"type": "content_block_start", "index": 1, "content_block": {"type": "tool_use", "id": "toolu_456", "name": "search_items"}},
        {"type": "content_block_delta", "index": 1, "delta": {"type": "input_json_delta", "partial_json": '{"query": "Tritanium"}'}},
        {"type": "content_block_stop", "index": 1}
    ]

    for chunk in chunks:
        extractor.process_chunk(chunk)

    tool_calls = extractor.get_tool_calls()
    text_chunks = extractor.get_text_chunks()

    assert len(tool_calls) == 1
    assert len(text_chunks) == 1
    assert text_chunks[0] == "Let me check"
```

**Step 2: Run test to verify it fails**

```bash
pytest copilot_server/tests/test_tool_extractor.py -v
```

Expected: FAIL with "No module named 'copilot_server.agent.tool_extractor'"

**Step 3: Implement ToolCallExtractor**

Create `copilot_server/agent/tool_extractor.py`:

```python
"""
Tool Call Extraction from LLM Streams
Handles Anthropic and OpenAI streaming formats.
"""

import json
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class ToolCallExtractor:
    """Extracts tool calls from streaming LLM responses."""

    def __init__(self):
        self.current_blocks: Dict[int, Dict[str, Any]] = {}
        self.completed_tool_calls: List[Dict[str, Any]] = []
        self.text_chunks: List[str] = []

    def process_chunk(self, chunk: Dict[str, Any]) -> None:
        """
        Process a single streaming chunk.

        Args:
            chunk: Streaming event from LLM
        """
        chunk_type = chunk.get("type")

        if chunk_type == "content_block_start":
            # New content block starting
            index = chunk.get("index", 0)
            content_block = chunk.get("content_block", {})

            self.current_blocks[index] = {
                "type": content_block.get("type"),
                "id": content_block.get("id"),
                "name": content_block.get("name"),
                "partial_json": ""
            }

        elif chunk_type == "content_block_delta":
            # Accumulate content
            index = chunk.get("index", 0)
            delta = chunk.get("delta", {})
            delta_type = delta.get("type")

            if index in self.current_blocks:
                block = self.current_blocks[index]

                if delta_type == "text_delta":
                    # Text content
                    text = delta.get("text", "")
                    self.text_chunks.append(text)

                elif delta_type == "input_json_delta":
                    # Tool input JSON (partial)
                    block["partial_json"] += delta.get("partial_json", "")

        elif chunk_type == "content_block_stop":
            # Content block complete
            index = chunk.get("index", 0)

            if index in self.current_blocks:
                block = self.current_blocks[index]

                if block["type"] == "tool_use":
                    # Parse complete JSON
                    try:
                        tool_input = json.loads(block["partial_json"])

                        self.completed_tool_calls.append({
                            "id": block["id"],
                            "name": block["name"],
                            "input": tool_input
                        })

                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse tool input JSON: {e}")
                        logger.error(f"Partial JSON: {block['partial_json']}")

                # Remove from current blocks
                del self.current_blocks[index]

    def get_tool_calls(self) -> List[Dict[str, Any]]:
        """Get all completed tool calls."""
        return self.completed_tool_calls

    def get_text_chunks(self) -> List[str]:
        """Get all text chunks."""
        return self.text_chunks

    def has_tool_calls(self) -> bool:
        """Check if any tool calls were detected."""
        return len(self.completed_tool_calls) > 0

    def reset(self) -> None:
        """Reset extractor for new response."""
        self.current_blocks.clear()
        self.completed_tool_calls.clear()
        self.text_chunks.clear()
```

**Step 4: Run test to verify it passes**

```bash
pytest copilot_server/tests/test_tool_extractor.py -v
```

Expected: PASS (2/2 tests)

**Step 5: Commit**

```bash
git add copilot_server/agent/tool_extractor.py copilot_server/tests/test_tool_extractor.py
git commit -m "feat: add ToolCallExtractor for streaming tool detection

- Extracts tool_use blocks from Anthropic streaming
- Accumulates partial JSON from input_json_delta events
- Separates text chunks from tool calls
- Tested with mixed content streams"
```

---

## Task 2: Agentic Streaming Loop

**Goal:** Create streaming function that executes tools and continues conversation until final answer

**Files:**
- Create: `copilot_server/agent/agentic_loop.py`
- Test: `copilot_server/tests/test_agentic_loop.py`

**Step 1: Write failing test for agentic loop**

Create `copilot_server/tests/test_agentic_loop.py`:

```python
import pytest
from unittest.mock import AsyncMock, Mock
from copilot_server.agent.agentic_loop import AgenticStreamingLoop
from copilot_server.models.user_settings import UserSettings, AutonomyLevel

@pytest.mark.asyncio
async def test_execute_single_tool_call():
    """Test loop that executes one tool and returns answer."""
    # Mock dependencies
    llm_client = Mock()
    llm_client._stream_response = AsyncMock()

    # First response: tool call
    llm_client._stream_response.return_value = async_gen([
        {"type": "content_block_start", "index": 0, "content_block": {"type": "text"}},
        {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "Let me check"}},
        {"type": "content_block_stop", "index": 0},
        {"type": "content_block_start", "index": 1, "content_block": {"type": "tool_use", "id": "toolu_1", "name": "get_price"}},
        {"type": "content_block_delta", "index": 1, "delta": {"type": "input_json_delta", "partial_json": '{"type_id": 34}'}},
        {"type": "content_block_stop", "index": 1},
        {"type": "message_stop"}
    ])

    mcp_client = Mock()
    mcp_client.call_tool = Mock(return_value={"content": [{"type": "text", "text": "Price: 5.50 ISK"}]})
    mcp_client.get_tools = Mock(return_value=[])

    user_settings = UserSettings(character_id=123, autonomy_level=AutonomyLevel.RECOMMENDATIONS)

    loop = AgenticStreamingLoop(llm_client, mcp_client, user_settings)

    events = []
    async for event in loop.execute([{"role": "user", "content": "What is price of Tritanium?"}]):
        events.append(event)

    # Should emit: text chunk, tool_call_started, tool_call_completed, final answer
    assert any(e["type"] == "text" for e in events)
    assert any(e["type"] == "tool_call_started" for e in events)
    assert any(e["type"] == "tool_call_completed" for e in events)

async def async_gen(items):
    """Helper to create async generator from list."""
    for item in items:
        yield item
```

**Step 2: Run test to verify it fails**

```bash
pytest copilot_server/tests/test_agentic_loop.py -v
```

Expected: FAIL with "No module named 'copilot_server.agent.agentic_loop'"

**Step 3: Implement AgenticStreamingLoop (Part 1: Structure)**

Create `copilot_server/agent/agentic_loop.py`:

```python
"""
Agentic Streaming Loop
Executes multi-turn tool-calling workflow with streaming.
"""

import logging
from typing import List, Dict, Any, AsyncIterator, Optional
from ..llm.anthropic_client import AnthropicClient
from ..mcp.client import MCPClient
from ..models.user_settings import UserSettings
from ..governance.authorization import AuthorizationChecker
from .tool_extractor import ToolCallExtractor
from .events import (
    AgentEvent,
    AgentEventType,
    ToolCallStartedEvent,
    ToolCallCompletedEvent
)

logger = logging.getLogger(__name__)


class AgenticStreamingLoop:
    """
    Executes agentic loop with streaming and tool execution.

    Flow:
    1. Stream LLM response
    2. Extract tool calls from stream
    3. Execute tools (with authorization)
    4. Feed results back to LLM
    5. Repeat until final answer
    6. Stream events to client
    """

    def __init__(
        self,
        llm_client: AnthropicClient,
        mcp_client: MCPClient,
        user_settings: UserSettings,
        max_iterations: int = 5
    ):
        self.llm = llm_client
        self.mcp = mcp_client
        self.settings = user_settings
        self.max_iterations = max_iterations
        self.auth_checker = AuthorizationChecker(user_settings)

    async def execute(
        self,
        messages: List[Dict[str, Any]],
        system: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Execute agentic loop with streaming.

        Args:
            messages: Conversation history
            system: System prompt
            session_id: Session ID for events

        Yields:
            Stream events: text chunks, tool calls, results, errors
        """
        iteration = 0
        current_messages = messages.copy()
        tools = self.mcp.get_tools()
        claude_tools = self.llm.build_tool_schema(tools) if tools else []

        while iteration < self.max_iterations:
            iteration += 1
            logger.info(f"Agentic loop iteration {iteration}/{self.max_iterations}")

            # Yield thinking event
            yield {
                "type": "thinking",
                "iteration": iteration
            }

            # Stream LLM response
            extractor = ToolCallExtractor()
            assistant_content_blocks = []

            async for chunk in self.llm._stream_response({
                "model": self.llm.model,
                "messages": current_messages,
                "system": system or "",
                "max_tokens": 4096,
                "tools": claude_tools,
                "stream": True
            }):
                # Process chunk for tool extraction
                extractor.process_chunk(chunk)

                # Yield text chunks to client
                if chunk.get("type") == "content_block_delta":
                    delta = chunk.get("delta", {})
                    if delta.get("type") == "text_delta":
                        text = delta.get("text", "")
                        yield {
                            "type": "text",
                            "text": text
                        }

                # Build assistant content blocks for next turn
                if chunk.get("type") == "content_block_start":
                    content_block = chunk.get("content_block", {})
                    assistant_content_blocks.append({
                        "type": content_block.get("type"),
                        "id": content_block.get("id"),
                        "name": content_block.get("name"),
                        "partial_text": "",
                        "partial_json": ""
                    })
                elif chunk.get("type") == "content_block_delta":
                    index = chunk.get("index", 0)
                    if index < len(assistant_content_blocks):
                        delta = chunk.get("delta", {})
                        if delta.get("type") == "text_delta":
                            assistant_content_blocks[index]["partial_text"] += delta.get("text", "")
                        elif delta.get("type") == "input_json_delta":
                            assistant_content_blocks[index]["partial_json"] += delta.get("partial_json", "")

            # Check if tools were called
            tool_calls = extractor.get_tool_calls()

            if not tool_calls:
                # No tool calls - final answer reached
                logger.info("No tool calls detected - final answer reached")
                yield {"type": "done"}
                return

            # Execute tool calls
            logger.info(f"Executing {len(tool_calls)} tool calls")

            # Build assistant message for conversation
            assistant_message_content = self._build_assistant_content(assistant_content_blocks)
            current_messages.append({
                "role": "assistant",
                "content": assistant_message_content
            })

            # Execute tools and build tool results
            tool_results = []

            for tool_call in tool_calls:
                tool_name = tool_call["name"]
                tool_input = tool_call["input"]
                tool_id = tool_call["id"]

                # Yield tool_call_started event
                yield {
                    "type": "tool_call_started",
                    "tool": tool_name,
                    "arguments": tool_input
                }

                # Check authorization
                allowed, denial_reason = self.auth_checker.check_authorization(
                    tool_name,
                    tool_input
                )

                if not allowed:
                    logger.warning(f"Tool '{tool_name}' blocked: {denial_reason}")

                    # Yield authorization denied event
                    yield {
                        "type": "authorization_denied",
                        "tool": tool_name,
                        "reason": denial_reason
                    }

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": f"Authorization Error: {denial_reason}",
                        "is_error": True
                    })
                    continue

                # Execute tool
                logger.info(f"Executing tool: {tool_name}")
                result = self.mcp.call_tool(tool_name, tool_input)

                # Yield tool_call_completed event
                yield {
                    "type": "tool_call_completed",
                    "tool": tool_name,
                    "result": result
                }

                # Format for LLM
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "content": self._format_tool_result(result)
                })

            # Add tool results to conversation
            current_messages.append({
                "role": "user",
                "content": tool_results
            })

        # Max iterations reached
        logger.warning(f"Max iterations ({self.max_iterations}) reached")
        yield {
            "type": "error",
            "error": "Maximum iterations reached without final answer"
        }

    def _build_assistant_content(self, content_blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Build assistant content blocks for conversation."""
        result = []

        for block in content_blocks:
            if block["type"] == "text":
                result.append({
                    "type": "text",
                    "text": block["partial_text"]
                })
            elif block["type"] == "tool_use":
                import json
                result.append({
                    "type": "tool_use",
                    "id": block["id"],
                    "name": block["name"],
                    "input": json.loads(block["partial_json"])
                })

        return result

    def _format_tool_result(self, result: Dict[str, Any]) -> str:
        """Format tool result for LLM."""
        if "error" in result:
            return f"Error: {result['error']}"

        if "content" in result:
            # Extract text from content blocks
            texts = []
            for block in result["content"]:
                if block.get("type") == "text":
                    texts.append(block.get("text", ""))
            return "\n".join(texts) if texts else str(result)

        return str(result)
```

**Step 4: Run test to verify it passes**

```bash
pytest copilot_server/tests/test_agentic_loop.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add copilot_server/agent/agentic_loop.py copilot_server/tests/test_agentic_loop.py
git commit -m "feat: implement AgenticStreamingLoop for tool execution

- Streams LLM responses while extracting tool calls
- Executes tools via MCP with authorization checks
- Continues loop until final answer (max 5 iterations)
- Yields events: thinking, text, tool_call_started, tool_call_completed
- Handles authorization denials gracefully"
```

---

## Task 3: Integrate Agentic Loop into Chat Streaming Endpoint

**Goal:** Replace simple streaming with agentic loop in `/agent/chat/stream`

**Files:**
- Modify: `copilot_server/api/agent_routes.py:264-368`

**Step 1: Write integration test**

Add to `copilot_server/tests/test_agent_routes.py`:

```python
@pytest.mark.asyncio
async def test_chat_stream_with_tool_execution(test_client, mock_llm_client, mock_mcp_client):
    """Test chat streaming endpoint executes tools."""
    # Create session
    response = test_client.post("/agent/session", json={
        "character_id": 123,
        "autonomy_level": 1
    })
    session_id = response.json()["session_id"]

    # Mock LLM to request tool call
    async def mock_stream(*args, **kwargs):
        yield {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "Let me check"}}
        yield {"type": "content_block_start", "index": 1, "content_block": {"type": "tool_use", "id": "t1", "name": "get_price"}}
        yield {"type": "content_block_delta", "index": 1, "delta": {"type": "input_json_delta", "partial_json": '{"type_id": 34}'}}
        yield {"type": "content_block_stop", "index": 1}
        yield {"type": "message_stop"}

    mock_llm_client._stream_response = mock_stream
    mock_mcp_client.call_tool.return_value = {"content": [{"type": "text", "text": "5.50 ISK"}]}

    # Stream chat
    response = test_client.post("/agent/chat/stream",
        headers={"Content-Type": "application/json"},
        json={
            "session_id": session_id,
            "message": "What is price of Tritanium?",
            "character_id": 123
        }
    )

    # Verify SSE stream contains tool events
    lines = response.text.strip().split('\n\n')
    events = [json.loads(line.replace('data: ', '')) for line in lines if line.startswith('data:')]

    assert any(e["type"] == "text" for e in events)
    assert any(e["type"] == "tool_call_started" for e in events)
    assert any(e["type"] == "tool_call_completed" for e in events)
```

**Step 2: Run test to verify it fails**

```bash
pytest copilot_server/tests/test_agent_routes.py::test_chat_stream_with_tool_execution -v
```

Expected: FAIL (agentic loop not integrated yet)

**Step 3: Integrate AgenticStreamingLoop into agent_routes.py**

Modify `copilot_server/api/agent_routes.py`:

```python
# Add import at top
from ..agent.agentic_loop import AgenticStreamingLoop

# Replace stream_chat_response function (lines 264-368)
@router.post("/chat/stream")
async def stream_chat_response(
    request: ChatStreamRequest,
    authorization: Optional[str] = Header(None)
):
    """
    Stream chat response via SSE with tool execution.

    Executes agentic loop: LLM → Tools → LLM until final answer.
    Streams intermediate results and tool calls.
    """
    # Validate message content
    await validate_message_content(request.message)

    # Verify session access
    await verify_session_access(
        request.session_id,
        request.character_id,
        authorization
    )

    if not session_manager or not llm_client or not db_pool or not mcp_client:
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

    # Stream response with agentic loop
    async def event_generator():
        formatter = SSEFormatter()
        full_response = ""
        tool_calls_executed = []

        try:
            # Get conversation history
            messages = session.get_messages_for_api()

            # Get user settings
            user_settings = get_default_settings(character_id=request.character_id or -1)

            # Create agentic loop
            from ..config import SYSTEM_PROMPT
            loop = AgenticStreamingLoop(
                llm_client=llm_client,
                mcp_client=mcp_client,
                user_settings=user_settings,
                max_iterations=5
            )

            # Execute agentic loop
            async for event in loop.execute(
                messages=messages,
                system=SYSTEM_PROMPT,
                session_id=session.id
            ):
                event_type = event.get("type")

                if event_type == "text":
                    # Text chunk from LLM
                    text = event.get("text", "")
                    full_response += text
                    yield formatter.format_text_chunk(text)

                elif event_type == "thinking":
                    # Thinking indicator
                    yield formatter.format({
                        "type": "thinking",
                        "iteration": event.get("iteration")
                    })

                elif event_type == "tool_call_started":
                    # Tool execution started
                    yield formatter.format({
                        "type": "tool_call_started",
                        "tool": event.get("tool"),
                        "arguments": event.get("arguments")
                    })

                elif event_type == "tool_call_completed":
                    # Tool execution completed
                    tool_calls_executed.append({
                        "tool": event.get("tool"),
                        "result": event.get("result")
                    })
                    yield formatter.format({
                        "type": "tool_call_completed",
                        "tool": event.get("tool")
                    })

                elif event_type == "authorization_denied":
                    # Tool blocked by authorization
                    yield formatter.format({
                        "type": "authorization_denied",
                        "tool": event.get("tool"),
                        "reason": event.get("reason")
                    })

                elif event_type == "error":
                    # Error occurred
                    yield formatter.format_error(event.get("error", "Unknown error"))
                    return

                elif event_type == "done":
                    # Final answer reached
                    break

            # Save assistant response
            async with db_pool.acquire() as conn:
                repo = MessageRepository(conn)
                assistant_message = AgentMessage.create(
                    session_id=session.id,
                    role="assistant",
                    content=full_response,
                    metadata={
                        "tool_calls": tool_calls_executed
                    }
                )
                message_id = await repo.save(assistant_message)

            # Send done event with message ID
            yield formatter.format_done(message_id)

        except Exception as e:
            logger.error(f"Chat streaming error: {e}", exc_info=True)
            yield formatter.format_error(str(e))

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )
```

**Step 4: Run test to verify it passes**

```bash
pytest copilot_server/tests/test_agent_routes.py::test_chat_stream_with_tool_execution -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add copilot_server/api/agent_routes.py
git commit -m "feat: integrate AgenticStreamingLoop into chat streaming

- Replace simple LLM streaming with agentic loop
- Executes tools and continues until final answer
- Streams intermediate events: thinking, tool calls, results
- Saves tool execution metadata with assistant messages
- Handles authorization denials in stream"
```

---

## Task 4: Add OpenAI Tool Call Support

**Goal:** Extend ToolCallExtractor and AgenticLoop to handle OpenAI streaming format

**Files:**
- Modify: `copilot_server/agent/tool_extractor.py`
- Modify: `copilot_server/llm/openai_client.py`
- Test: `copilot_server/tests/test_tool_extractor.py`

**Step 1: Write failing test for OpenAI format**

Add to `copilot_server/tests/test_tool_extractor.py`:

```python
def test_extract_tool_call_from_openai_stream():
    """Test extracting function calls from OpenAI streaming chunks."""
    extractor = ToolCallExtractor()

    # OpenAI uses function_call in delta
    chunks = [
        {"choices": [{"delta": {"function_call": {"name": "get_market_price", "arguments": ""}}}]},
        {"choices": [{"delta": {"function_call": {"arguments": '{"type'}}}]},
        {"choices": [{"delta": {"function_call": {"arguments": '_id": 34}'}}}]},
        {"choices": [{"delta": {"function_call": {"arguments": '}'}}}]},
        {"choices": [{"finish_reason": "function_call"}]}
    ]

    for chunk in chunks:
        extractor.process_chunk(chunk, provider="openai")

    tool_calls = extractor.get_tool_calls()

    assert len(tool_calls) == 1
    assert tool_calls[0]["name"] == "get_market_price"
    assert tool_calls[0]["input"] == {"type_id": 34}
```

**Step 2: Run test to verify it fails**

```bash
pytest copilot_server/tests/test_tool_extractor.py::test_extract_tool_call_from_openai_stream -v
```

Expected: FAIL (OpenAI format not supported)

**Step 3: Extend ToolCallExtractor for OpenAI**

Modify `copilot_server/agent/tool_extractor.py`:

```python
class ToolCallExtractor:
    """Extracts tool calls from streaming LLM responses (Anthropic & OpenAI)."""

    def __init__(self):
        self.current_blocks: Dict[int, Dict[str, Any]] = {}
        self.completed_tool_calls: List[Dict[str, Any]] = []
        self.text_chunks: List[str] = []

        # OpenAI-specific state
        self.openai_function_call: Optional[Dict[str, Any]] = None

    def process_chunk(self, chunk: Dict[str, Any], provider: str = "anthropic") -> None:
        """
        Process a single streaming chunk.

        Args:
            chunk: Streaming event from LLM
            provider: "anthropic" or "openai"
        """
        if provider == "openai":
            self._process_openai_chunk(chunk)
        else:
            self._process_anthropic_chunk(chunk)

    def _process_anthropic_chunk(self, chunk: Dict[str, Any]) -> None:
        """Process Anthropic streaming chunk (existing logic)."""
        chunk_type = chunk.get("type")

        if chunk_type == "content_block_start":
            # ... (existing code)

        elif chunk_type == "content_block_delta":
            # ... (existing code)

        elif chunk_type == "content_block_stop":
            # ... (existing code)

    def _process_openai_chunk(self, chunk: Dict[str, Any]) -> None:
        """Process OpenAI streaming chunk."""
        if "choices" not in chunk or not chunk["choices"]:
            return

        choice = chunk["choices"][0]
        delta = choice.get("delta", {})

        # Handle text content
        if "content" in delta and delta["content"]:
            self.text_chunks.append(delta["content"])

        # Handle function call
        if "function_call" in delta:
            func_call = delta["function_call"]

            # Initialize function call on first chunk
            if self.openai_function_call is None:
                self.openai_function_call = {
                    "name": func_call.get("name", ""),
                    "arguments": ""
                }

            # Accumulate name
            if "name" in func_call:
                self.openai_function_call["name"] = func_call["name"]

            # Accumulate arguments
            if "arguments" in func_call:
                self.openai_function_call["arguments"] += func_call["arguments"]

        # Finish reason indicates completion
        if choice.get("finish_reason") == "function_call":
            if self.openai_function_call:
                try:
                    args = json.loads(self.openai_function_call["arguments"])

                    self.completed_tool_calls.append({
                        "id": f"call_{len(self.completed_tool_calls)}",
                        "name": self.openai_function_call["name"],
                        "input": args
                    })

                    self.openai_function_call = None

                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse OpenAI function arguments: {e}")
```

**Step 4: Update AgenticStreamingLoop to detect provider**

Modify `copilot_server/agent/agentic_loop.py`:

```python
# In execute() method, detect provider:

# Detect LLM provider
provider = "anthropic"
if hasattr(self.llm, "client") and "openai" in str(type(self.llm.client)).lower():
    provider = "openai"

# Process chunks with provider info
async for chunk in self.llm._stream_response({...}):
    extractor.process_chunk(chunk, provider=provider)
    # ... rest of processing
```

**Step 5: Run test to verify it passes**

```bash
pytest copilot_server/tests/test_tool_extractor.py -v
```

Expected: PASS (all tests including OpenAI)

**Step 6: Commit**

```bash
git add copilot_server/agent/tool_extractor.py copilot_server/agent/agentic_loop.py copilot_server/tests/test_tool_extractor.py
git commit -m "feat: add OpenAI streaming tool call support

- Extend ToolCallExtractor to handle OpenAI function_call format
- Accumulate function arguments from streaming deltas
- Auto-detect provider in AgenticStreamingLoop
- Support both Anthropic and OpenAI in same codebase"
```

---

## Task 5: Event Broadcasting via WebSocket

**Goal:** Broadcast tool execution events to WebSocket clients for real-time UI updates

**Files:**
- Modify: `copilot_server/agent/agentic_loop.py`
- Modify: `copilot_server/api/agent_routes.py` (chat streaming)

**Step 1: Write test for event broadcasting**

Add to `copilot_server/tests/test_agentic_loop.py`:

```python
@pytest.mark.asyncio
async def test_broadcast_events_to_websocket(mock_event_bus):
    """Test that agentic loop broadcasts events to WebSocket."""
    llm_client = Mock()
    llm_client._stream_response = AsyncMock(return_value=async_gen([
        {"type": "content_block_start", "index": 0, "content_block": {"type": "tool_use", "id": "t1", "name": "get_price"}},
        {"type": "content_block_delta", "index": 0, "delta": {"type": "input_json_delta", "partial_json": '{"type_id": 34}'}},
        {"type": "content_block_stop", "index": 0},
        {"type": "message_stop"}
    ]))

    mcp_client = Mock()
    mcp_client.call_tool = Mock(return_value={"content": [{"type": "text", "text": "5.50 ISK"}]})
    mcp_client.get_tools = Mock(return_value=[])

    user_settings = UserSettings(character_id=123, autonomy_level=AutonomyLevel.RECOMMENDATIONS)

    loop = AgenticStreamingLoop(llm_client, mcp_client, user_settings, event_bus=mock_event_bus)

    async for _ in loop.execute([{"role": "user", "content": "Price?"}], session_id="sess-123"):
        pass

    # Verify events were published
    published_events = mock_event_bus.get_published_events("sess-123")
    assert any(e.type == AgentEventType.TOOL_CALL_STARTED for e in published_events)
    assert any(e.type == AgentEventType.TOOL_CALL_COMPLETED for e in published_events)
```

**Step 2: Run test to verify it fails**

```bash
pytest copilot_server/tests/test_agentic_loop.py::test_broadcast_events_to_websocket -v
```

Expected: FAIL (event_bus not integrated)

**Step 3: Add EventBus to AgenticStreamingLoop**

Modify `copilot_server/agent/agentic_loop.py`:

```python
# Add to imports
from ..agent.sessions import EventBus

# Modify __init__
def __init__(
    self,
    llm_client: AnthropicClient,
    mcp_client: MCPClient,
    user_settings: UserSettings,
    max_iterations: int = 5,
    event_bus: Optional[EventBus] = None
):
    self.llm = llm_client
    self.mcp = mcp_client
    self.settings = user_settings
    self.max_iterations = max_iterations
    self.auth_checker = AuthorizationChecker(user_settings)
    self.event_bus = event_bus  # Optional EventBus for broadcasting

# In execute(), broadcast events:

# After "Yield tool_call_started event"
if self.event_bus and session_id:
    event = ToolCallStartedEvent(
        session_id=session_id,
        plan_id=None,
        step_index=0,
        tool=tool_name,
        arguments=tool_input
    )
    self.event_bus.publish(session_id, event)

# After "Yield tool_call_completed event"
if self.event_bus and session_id:
    from .events import ToolCallCompletedEvent
    event = ToolCallCompletedEvent(
        session_id=session_id,
        plan_id=None,
        step_index=0,
        tool=tool_name,
        result=result
    )
    self.event_bus.publish(session_id, event)
```

**Step 4: Pass EventBus from agent_routes**

Modify `copilot_server/api/agent_routes.py`:

```python
# In stream_chat_response, pass event_bus to loop:

loop = AgenticStreamingLoop(
    llm_client=llm_client,
    mcp_client=mcp_client,
    user_settings=user_settings,
    max_iterations=5,
    event_bus=session_manager.event_bus if session_manager else None
)
```

**Step 5: Run test to verify it passes**

```bash
pytest copilot_server/tests/test_agentic_loop.py::test_broadcast_events_to_websocket -v
```

Expected: PASS

**Step 6: Commit**

```bash
git add copilot_server/agent/agentic_loop.py copilot_server/api/agent_routes.py copilot_server/tests/test_agentic_loop.py
git commit -m "feat: broadcast tool execution events via WebSocket

- Add EventBus integration to AgenticStreamingLoop
- Publish TOOL_CALL_STARTED and TOOL_CALL_COMPLETED events
- WebSocket clients receive real-time tool execution updates
- Events shown in Agent Dashboard Event Stream"
```

---

## Task 6: Plan Approval Flow for High-Risk Tools

**Goal:** Require user approval for L2/L3 autonomy tool calls before execution

**Files:**
- Modify: `copilot_server/agent/agentic_loop.py`
- Create: `copilot_server/agent/approval_manager.py`
- Test: `copilot_server/tests/test_approval_manager.py`

**Step 1: Write test for approval manager**

Create `copilot_server/tests/test_approval_manager.py`:

```python
import pytest
from copilot_server.agent.approval_manager import ApprovalManager
from copilot_server.agent.models import Plan, PlanStep
from copilot_server.models.user_settings import RiskLevel, AutonomyLevel

def test_requires_approval_for_high_risk():
    """Test that high-risk tools require approval at L1 autonomy."""
    manager = ApprovalManager(autonomy_level=AutonomyLevel.RECOMMENDATIONS)

    # L2 (MODERATE) requires approval at L1
    assert manager.requires_approval("market_order_create", {}, RiskLevel.MODERATE) == True

    # L0 (READ_ONLY) auto-executes at L1
    assert manager.requires_approval("market_price_get", {}, RiskLevel.READ_ONLY) == False

def test_auto_execute_at_assisted_level():
    """Test that L2 tools auto-execute at ASSISTED autonomy."""
    manager = ApprovalManager(autonomy_level=AutonomyLevel.ASSISTED)

    # L2 auto-executes at ASSISTED
    assert manager.requires_approval("market_order_create", {}, RiskLevel.MODERATE) == False

    # L3 still requires approval
    assert manager.requires_approval("wallet_transfer", {}, RiskLevel.CRITICAL) == True
```

**Step 2: Run test to verify it fails**

```bash
pytest copilot_server/tests/test_approval_manager.py -v
```

Expected: FAIL with "No module named 'copilot_server.agent.approval_manager'"

**Step 3: Implement ApprovalManager**

Create `copilot_server/agent/approval_manager.py`:

```python
"""
Approval Manager
Determines if tool execution requires user approval based on autonomy level.
"""

from typing import Dict, Any, Optional
from ..models.user_settings import AutonomyLevel, RiskLevel


class ApprovalManager:
    """Manages approval requirements for tool execution."""

    # Autonomy level to max auto-executable risk level mapping
    AUTO_EXECUTE_THRESHOLDS = {
        AutonomyLevel.READ_ONLY: RiskLevel.READ_ONLY,  # L0: Only READ_ONLY
        AutonomyLevel.RECOMMENDATIONS: RiskLevel.LOW,   # L1: READ_ONLY + LOW
        AutonomyLevel.ASSISTED: RiskLevel.MODERATE,     # L2: READ_ONLY + LOW + MODERATE
        AutonomyLevel.SUPERVISED: RiskLevel.CRITICAL    # L3: All (not implemented)
    }

    def __init__(self, autonomy_level: AutonomyLevel):
        """
        Initialize approval manager.

        Args:
            autonomy_level: User's autonomy level
        """
        self.autonomy_level = autonomy_level
        self.threshold = self.AUTO_EXECUTE_THRESHOLDS[autonomy_level]

    def requires_approval(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        risk_level: RiskLevel
    ) -> bool:
        """
        Check if tool execution requires approval.

        Args:
            tool_name: Name of tool
            arguments: Tool arguments
            risk_level: Tool's risk level

        Returns:
            True if approval required, False if auto-executable
        """
        # Risk levels are ordered: READ_ONLY < LOW < MODERATE < CRITICAL
        # Auto-execute if risk <= threshold
        risk_order = [RiskLevel.READ_ONLY, RiskLevel.LOW, RiskLevel.MODERATE, RiskLevel.CRITICAL]

        tool_risk_index = risk_order.index(risk_level)
        threshold_index = risk_order.index(self.threshold)

        # Requires approval if risk exceeds threshold
        return tool_risk_index > threshold_index

    def create_approval_plan(
        self,
        session_id: str,
        tool_calls: list,
        purpose: str
    ) -> Optional[Any]:
        """
        Create a plan requiring approval.

        Args:
            session_id: Session ID
            tool_calls: List of tool calls
            purpose: Purpose of plan

        Returns:
            Plan object or None
        """
        from .models import Plan, PlanStep

        steps = []
        max_risk = RiskLevel.READ_ONLY

        for tc in tool_calls:
            step = PlanStep(
                tool=tc["name"],
                arguments=tc["input"],
                risk_level=tc.get("risk_level", RiskLevel.MODERATE)
            )
            steps.append(step)

            # Track highest risk
            if step.risk_level.value > max_risk.value:
                max_risk = step.risk_level

        plan = Plan(
            session_id=session_id,
            purpose=purpose,
            steps=steps,
            max_risk_level=max_risk,
            auto_executing=False  # Requires approval
        )

        return plan
```

**Step 4: Run test to verify it passes**

```bash
pytest copilot_server/tests/test_approval_manager.py -v
```

Expected: PASS

**Step 5: Integrate into AgenticStreamingLoop**

Modify `copilot_server/agent/agentic_loop.py`:

```python
# Add import
from .approval_manager import ApprovalManager

# In __init__, create approval manager
def __init__(self, ...):
    # ... existing code
    self.approval_manager = ApprovalManager(user_settings.autonomy_level)

# In execute(), check approval before tool execution:

# After extracting tool calls:
tool_calls_needing_approval = []
tool_calls_auto_execute = []

for tool_call in tool_calls:
    tool_name = tool_call["name"]
    tool_input = tool_call["input"]

    # Get risk level from tool metadata (assume MODERATE if unknown)
    risk_level = self._get_tool_risk_level(tool_name)

    if self.approval_manager.requires_approval(tool_name, tool_input, risk_level):
        tool_calls_needing_approval.append({
            **tool_call,
            "risk_level": risk_level
        })
    else:
        tool_calls_auto_execute.append(tool_call)

# If approval needed, create plan and wait
if tool_calls_needing_approval:
    logger.info(f"{len(tool_calls_needing_approval)} tools require approval")

    # Create plan
    plan = self.approval_manager.create_approval_plan(
        session_id=session_id,
        tool_calls=tool_calls_needing_approval,
        purpose=f"Execute {len(tool_calls_needing_approval)} tools"
    )

    # Yield WAITING_FOR_APPROVAL event
    yield {
        "type": "waiting_for_approval",
        "plan_id": plan.id,
        "plan": plan.to_db_dict()
    }

    # Broadcast event
    if self.event_bus and session_id:
        from .events import AgentEvent, AgentEventType
        event = AgentEvent(
            type=AgentEventType.WAITING_FOR_APPROVAL,
            session_id=session_id,
            plan_id=plan.id,
            payload={
                "purpose": plan.purpose,
                "tool_count": len(plan.steps)
            }
        )
        self.event_bus.publish(session_id, event)

    # Stop execution - user must approve via /agent/execute endpoint
    return

# Execute auto-approved tools
tool_calls = tool_calls_auto_execute
```

**Step 6: Add helper method to get tool risk level**

```python
def _get_tool_risk_level(self, tool_name: str) -> RiskLevel:
    """Get risk level for tool (from metadata or defaults)."""
    # Get tool info from MCP
    tools = self.mcp.get_tools()

    for tool in tools:
        if tool.get("name") == tool_name:
            # Check for risk_level in tool metadata
            if "risk_level" in tool:
                return RiskLevel(tool["risk_level"])

    # Default mapping based on tool name patterns
    if any(x in tool_name.lower() for x in ["create", "delete", "update", "transfer"]):
        return RiskLevel.MODERATE
    elif any(x in tool_name.lower() for x in ["get", "list", "search", "find"]):
        return RiskLevel.READ_ONLY

    # Default to MODERATE for safety
    return RiskLevel.MODERATE
```

**Step 7: Commit**

```bash
git add copilot_server/agent/approval_manager.py copilot_server/agent/agentic_loop.py copilot_server/tests/test_approval_manager.py
git commit -m "feat: add plan approval flow for high-risk tools

- Create ApprovalManager to determine approval requirements
- Auto-execute tools within autonomy threshold
- Create Plan for tools exceeding threshold
- Emit WAITING_FOR_APPROVAL event and pause execution
- User must approve via /agent/execute endpoint"
```

---

## Task 7: Error Handling & Retry Logic

**Goal:** Handle tool execution failures gracefully with retry and error recovery

**Files:**
- Modify: `copilot_server/agent/agentic_loop.py`
- Create: `copilot_server/agent/retry_handler.py`
- Test: `copilot_server/tests/test_retry_handler.py`

**Step 1: Write test for retry handler**

Create `copilot_server/tests/test_retry_handler.py`:

```python
import pytest
from unittest.mock import Mock
from copilot_server.agent.retry_handler import RetryHandler, RetryableError

@pytest.mark.asyncio
async def test_retry_on_transient_error():
    """Test that transient errors are retried."""
    handler = RetryHandler(max_retries=3)

    # Mock function that fails twice then succeeds
    call_count = 0
    def flaky_function():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise RetryableError("Temporary failure")
        return {"success": True}

    result = await handler.execute_with_retry(flaky_function)

    assert result == {"success": True}
    assert call_count == 3  # Failed twice, succeeded on 3rd

@pytest.mark.asyncio
async def test_give_up_after_max_retries():
    """Test that execution fails after max retries."""
    handler = RetryHandler(max_retries=2)

    def always_fails():
        raise RetryableError("Permanent failure")

    with pytest.raises(RetryableError):
        await handler.execute_with_retry(always_fails)
```

**Step 2: Run test to verify it fails**

```bash
pytest copilot_server/tests/test_retry_handler.py -v
```

Expected: FAIL (module doesn't exist)

**Step 3: Implement RetryHandler**

Create `copilot_server/agent/retry_handler.py`:

```python
"""
Retry Handler
Handles transient failures with exponential backoff.
"""

import asyncio
import logging
from typing import Callable, Any
from functools import wraps

logger = logging.getLogger(__name__)


class RetryableError(Exception):
    """Error that should be retried."""
    pass


class RetryHandler:
    """Handles retry logic with exponential backoff."""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0
    ):
        """
        Initialize retry handler.

        Args:
            max_retries: Maximum retry attempts
            base_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay

    async def execute_with_retry(
        self,
        func: Callable[[], Any],
        *args,
        **kwargs
    ) -> Any:
        """
        Execute function with retry on failure.

        Args:
            func: Function to execute
            *args, **kwargs: Function arguments

        Returns:
            Function result

        Raises:
            Last exception if all retries exhausted
        """
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                # Execute function
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)

                # Success
                if attempt > 0:
                    logger.info(f"Retry succeeded on attempt {attempt + 1}")

                return result

            except RetryableError as e:
                last_exception = e

                if attempt < self.max_retries:
                    # Calculate delay with exponential backoff
                    delay = min(self.base_delay * (2 ** attempt), self.max_delay)

                    logger.warning(
                        f"Attempt {attempt + 1}/{self.max_retries + 1} failed: {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )

                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"All {self.max_retries + 1} attempts failed. Giving up."
                    )
                    raise

            except Exception as e:
                # Non-retryable error - fail immediately
                logger.error(f"Non-retryable error: {e}")
                raise

        # Should never reach here, but just in case
        if last_exception:
            raise last_exception

    @staticmethod
    def is_retryable_error(error: Exception) -> bool:
        """
        Check if error is retryable.

        Args:
            error: Exception to check

        Returns:
            True if should retry
        """
        # Retry on specific error types
        retryable_patterns = [
            "timeout",
            "connection",
            "rate limit",
            "temporary",
            "unavailable"
        ]

        error_msg = str(error).lower()
        return any(pattern in error_msg for pattern in retryable_patterns)
```

**Step 4: Run test to verify it passes**

```bash
pytest copilot_server/tests/test_retry_handler.py -v
```

Expected: PASS

**Step 5: Integrate retry into AgenticStreamingLoop**

Modify `copilot_server/agent/agentic_loop.py`:

```python
# Add import
from .retry_handler import RetryHandler, RetryableError

# In __init__
def __init__(self, ...):
    # ... existing code
    self.retry_handler = RetryHandler(max_retries=3)

# Wrap tool execution in retry:

# Execute tool (with retry)
logger.info(f"Executing tool: {tool_name}")

try:
    async def execute_tool():
        result = self.mcp.call_tool(tool_name, tool_input)

        # Check if result indicates retryable error
        if "error" in result and self.retry_handler.is_retryable_error(
            Exception(result["error"])
        ):
            raise RetryableError(result["error"])

        return result

    result = await self.retry_handler.execute_with_retry(execute_tool)

except RetryableError as e:
    # All retries exhausted
    logger.error(f"Tool {tool_name} failed after retries: {e}")

    # Yield error event
    yield {
        "type": "tool_call_failed",
        "tool": tool_name,
        "error": str(e),
        "retries_exhausted": True
    }

    # Add error to tool results
    tool_results.append({
        "type": "tool_result",
        "tool_use_id": tool_id,
        "content": f"Tool execution failed after {self.retry_handler.max_retries} retries: {e}",
        "is_error": True
    })

    continue

except Exception as e:
    # Non-retryable error
    logger.error(f"Tool {tool_name} failed with non-retryable error: {e}")

    yield {
        "type": "tool_call_failed",
        "tool": tool_name,
        "error": str(e),
        "retries_exhausted": False
    }

    tool_results.append({
        "type": "tool_result",
        "tool_use_id": tool_id,
        "content": f"Tool execution error: {e}",
        "is_error": True
    })

    continue
```

**Step 6: Commit**

```bash
git add copilot_server/agent/retry_handler.py copilot_server/agent/agentic_loop.py copilot_server/tests/test_retry_handler.py
git commit -m "feat: add retry logic for tool execution failures

- Implement RetryHandler with exponential backoff
- Retry transient errors (timeout, connection, rate limit)
- Fail fast on non-retryable errors
- Emit tool_call_failed events with retry status
- LLM receives error in tool results and can adapt"
```

---

## Task 8: Frontend Event Handling

**Goal:** Update frontend to display tool execution events in real-time

**Files:**
- Modify: `frontend/src/components/agent/EventStreamDisplay.tsx`
- Modify: `frontend/src/types/agent-events.ts`

**Step 1: Add new event types**

Modify `frontend/src/types/agent-events.ts`:

```typescript
export enum AgentEventType {
  // ... existing types
  TOOL_CALL_STARTED = "tool_call_started",
  TOOL_CALL_COMPLETED = "tool_call_completed",
  TOOL_CALL_FAILED = "tool_call_failed",
  THINKING = "thinking",
  WAITING_FOR_APPROVAL = "waiting_for_approval",
  AUTHORIZATION_DENIED = "authorization_denied",
}

export interface ToolCallStartedEvent extends AgentEvent {
  type: AgentEventType.TOOL_CALL_STARTED;
  payload: {
    tool: string;
    arguments: Record<string, any>;
  };
}

export interface ToolCallCompletedEvent extends AgentEvent {
  type: AgentEventType.TOOL_CALL_COMPLETED;
  payload: {
    tool: string;
    result?: any;
  };
}

export interface ToolCallFailedEvent extends AgentEvent {
  type: AgentEventType.TOOL_CALL_FAILED;
  payload: {
    tool: string;
    error: string;
    retries_exhausted?: boolean;
  };
}
```

**Step 2: Update EventStreamDisplay component**

Modify `frontend/src/components/agent/EventStreamDisplay.tsx`:

```tsx
// Add rendering for new event types

function renderEventDetails(event: AgentEvent): JSX.Element {
  switch (event.type) {
    case AgentEventType.TOOL_CALL_STARTED:
      return (
        <div className="text-blue-400">
          <span className="font-semibold">🔧 Tool: {event.payload.tool}</span>
          <pre className="text-xs mt-1 text-gray-400">
            {JSON.stringify(event.payload.arguments, null, 2)}
          </pre>
        </div>
      );

    case AgentEventType.TOOL_CALL_COMPLETED:
      return (
        <div className="text-green-400">
          <span className="font-semibold">✅ {event.payload.tool} completed</span>
        </div>
      );

    case AgentEventType.TOOL_CALL_FAILED:
      return (
        <div className="text-red-400">
          <span className="font-semibold">❌ {event.payload.tool} failed</span>
          <p className="text-xs mt-1">{event.payload.error}</p>
          {event.payload.retries_exhausted && (
            <p className="text-xs mt-1 text-red-300">All retries exhausted</p>
          )}
        </div>
      );

    case AgentEventType.THINKING:
      return (
        <div className="text-gray-400">
          <span className="font-semibold">🤔 Thinking...</span>
        </div>
      );

    case AgentEventType.WAITING_FOR_APPROVAL:
      return (
        <div className="text-yellow-400">
          <span className="font-semibold">⏸️ Waiting for approval</span>
          <p className="text-xs mt-1">{event.payload.purpose}</p>
        </div>
      );

    case AgentEventType.AUTHORIZATION_DENIED:
      return (
        <div className="text-orange-400">
          <span className="font-semibold">🚫 Authorization denied</span>
          <p className="text-xs mt-1">Tool: {event.payload.tool}</p>
          <p className="text-xs text-gray-400">{event.payload.reason}</p>
        </div>
      );

    // ... existing cases
  }
}
```

**Step 3: Test frontend**

```bash
cd frontend
npm run dev
```

Manually test:
1. Create agent session
2. Ask question that requires tool call
3. Verify events appear in Event Stream panel
4. Check tool_call_started, tool_call_completed events display correctly

**Step 4: Commit**

```bash
git add frontend/src/types/agent-events.ts frontend/src/components/agent/EventStreamDisplay.tsx
git commit -m "feat: add frontend display for tool execution events

- Add new event types: TOOL_CALL_STARTED, TOOL_CALL_COMPLETED, etc.
- Render tool name and arguments in EventStreamDisplay
- Show success/failure status with appropriate colors
- Display retry status and authorization denials
- Real-time updates as agent executes tools"
```

---

## Task 9: Integration Testing

**Goal:** Test complete end-to-end flow with real EVE Online data

**Files:**
- Create: `copilot_server/tests/integration/test_phase7_e2e.py`

**Step 1: Write end-to-end test**

Create `copilot_server/tests/integration/test_phase7_e2e.py`:

```python
import pytest
from httpx import AsyncClient
from copilot_server.main import app

@pytest.mark.asyncio
@pytest.mark.integration
async def test_e2e_tool_execution_flow():
    """
    Test complete flow:
    1. Create session
    2. Send message requiring tool call
    3. Agent executes tool
    4. Agent returns answer with data
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 1. Create session
        response = await client.post("/agent/session", json={
            "character_id": 526379435,
            "autonomy_level": 1  # RECOMMENDATIONS
        })
        assert response.status_code == 200
        session_id = response.json()["session_id"]

        # 2. Ask question requiring market data
        response = await client.post("/agent/chat/stream", json={
            "session_id": session_id,
            "message": "What is the current sell price of Tritanium in Jita?",
            "character_id": 526379435
        })

        # 3. Verify SSE stream
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream"

        # Parse SSE events
        events = []
        for line in response.text.split('\n'):
            if line.startswith('data: '):
                import json
                event = json.loads(line[6:])
                events.append(event)

        # 4. Verify workflow
        # Should see: text, tool_call_started, tool_call_completed, text, done
        event_types = [e["type"] for e in events]

        assert "thinking" in event_types
        assert "tool_call_started" in event_types
        assert "tool_call_completed" in event_types
        assert "text" in event_types
        assert "done" in event_types

        # 5. Verify tool was called
        tool_events = [e for e in events if e["type"] == "tool_call_started"]
        assert len(tool_events) > 0

        # Should call market tool
        tool_names = [e.get("tool") for e in tool_events]
        assert any("market" in t.lower() or "price" in t.lower() for t in tool_names if t)

        # 6. Verify final answer contains data
        text_chunks = [e.get("text", "") for e in events if e["type"] == "text"]
        full_response = "".join(text_chunks)

        # Should contain ISK or numeric price
        assert "ISK" in full_response or any(char.isdigit() for char in full_response)

@pytest.mark.asyncio
@pytest.mark.integration
async def test_authorization_denial_flow():
    """Test that high-risk tools are blocked at L1 autonomy."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Create READ_ONLY session
        response = await client.post("/agent/session", json={
            "character_id": 526379435,
            "autonomy_level": 0  # READ_ONLY
        })
        session_id = response.json()["session_id"]

        # Try to trigger write operation
        response = await client.post("/agent/chat/stream", json={
            "session_id": session_id,
            "message": "Create a market order to sell 1000 Tritanium",
            "character_id": 526379435
        })

        events = []
        for line in response.text.split('\n'):
            if line.startswith('data: '):
                import json
                events.append(json.loads(line[6:]))

        event_types = [e["type"] for e in events]

        # Should block tool execution
        assert "authorization_denied" in event_types or "waiting_for_approval" in event_types
```

**Step 2: Run integration tests**

```bash
pytest copilot_server/tests/integration/test_phase7_e2e.py -v -m integration
```

Expected: PASS (full flow works)

**Step 3: Commit**

```bash
git add copilot_server/tests/integration/test_phase7_e2e.py
git commit -m "test: add Phase 7 end-to-end integration tests

- Test complete tool execution workflow
- Verify agent calls MCP tools and returns data
- Test authorization denial flow
- Validate SSE streaming events
- Confirm real EVE Online data integration"
```

---

## Task 10: Documentation & Completion

**Goal:** Document Phase 7 features and create usage examples

**Files:**
- Create: `docs/agent/phase7-tool-execution.md`
- Create: `docs/agent/phase7-usage-examples.md`
- Update: `CLAUDE.md`

**Step 1: Write feature documentation**

Create `docs/agent/phase7-tool-execution.md`:

```markdown
# Phase 7: Tool Execution & Agentic Loop

## Overview

Phase 7 enables the Agent Runtime to execute MCP tools in response to user queries, creating a full agentic loop where the LLM can access EVE Online data and provide informed answers.

## Features

### 1. Tool Call Detection
- Extracts tool calls from streaming LLM responses
- Supports both Anthropic Claude and OpenAI GPT formats
- Handles mixed text and tool call content

### 2. Agentic Streaming Loop
- Multi-turn workflow: LLM → Tools → LLM until final answer
- Streams intermediate results in real-time
- Maximum 5 iterations to prevent infinite loops
- Broadcasts events via WebSocket

### 3. Authorization & Governance
- Respects user autonomy levels (L0-L3)
- Auto-executes tools within threshold
- Requires approval for high-risk operations
- Blocks unauthorized tools with clear errors

### 4. Error Handling
- Retries transient failures with exponential backoff
- Distinguishes retryable vs non-retryable errors
- Provides error context to LLM for adaptation
- Broadcasts failure events to frontend

### 5. Real-Time Updates
- WebSocket events for tool execution
- EventStreamDisplay shows progress
- Tool arguments and results visible
- Approval prompts in UI (Phase 7.5)

## Architecture

```
User Query → SSE Stream → AgenticLoop
                ↓
          Extract Tools
                ↓
          Check Auth → Requires Approval? → Wait for User
                ↓ No
          Execute Tool (with retry)
                ↓
          Feed Result to LLM
                ↓
          More Tools? → Yes (loop)
                ↓ No
          Final Answer → Stream to User
```

## API Changes

### POST /agent/chat/stream

**Request:** (unchanged)
```json
{
  "session_id": "sess-xxx",
  "message": "What is the price of Tritanium?",
  "character_id": 123
}
```

**Response:** SSE Stream with new event types:
```
data: {"type":"thinking","iteration":1}

data: {"type":"text","text":"Let me check the market"}

data: {"type":"tool_call_started","tool":"market_price_get","arguments":{"type_id":34}}

data: {"type":"tool_call_completed","tool":"market_price_get"}

data: {"type":"text","text":"Tritanium is selling for 5.50 ISK"}

data: {"type":"done","message_id":"msg-xxx"}
```

## Event Types

| Event Type | Description |
|------------|-------------|
| `thinking` | Agent is processing (iteration N) |
| `tool_call_started` | Tool execution begins |
| `tool_call_completed` | Tool executed successfully |
| `tool_call_failed` | Tool execution failed (with retry status) |
| `authorization_denied` | Tool blocked by authorization |
| `waiting_for_approval` | High-risk tools require user approval |

## Autonomy Levels

| Level | Auto-Execute | Requires Approval |
|-------|--------------|-------------------|
| L0 (READ_ONLY) | READ_ONLY tools | LOW, MODERATE, CRITICAL |
| L1 (RECOMMENDATIONS) | READ_ONLY + LOW | MODERATE, CRITICAL |
| L2 (ASSISTED) | READ_ONLY + LOW + MODERATE | CRITICAL |
| L3 (SUPERVISED) | All (not implemented) | None |

## Testing

Run unit tests:
```bash
pytest copilot_server/tests/test_tool_extractor.py -v
pytest copilot_server/tests/test_agentic_loop.py -v
pytest copilot_server/tests/test_retry_handler.py -v
```

Run integration tests:
```bash
pytest copilot_server/tests/integration/test_phase7_e2e.py -v -m integration
```

## Limitations

- Plan approval UI not implemented (Phase 7.5)
- No streaming during tool execution (results shown after completion)
- Max 5 iterations (configurable)
- Tool risk levels hardcoded (should come from MCP metadata)

## Next Steps (Phase 7.5)

- Add PlanApprovalCard interactive approval
- Stream tool execution progress (e.g., "Fetching 1000 market orders...")
- Tool result caching to avoid redundant calls
- Multi-session tool coordination
```

**Step 2: Write usage examples**

Create `docs/agent/phase7-usage-examples.md`:

```markdown
# Phase 7 Usage Examples

## Example 1: Simple Market Query

**User:** "What is the price of Tritanium in Jita?"

**Agent Flow:**
1. LLM recognizes need for market data
2. Calls `market_price_get` tool with `type_id=34, region_id=10000002`
3. Receives price: `{"lowest_sell": 5.50}`
4. Responds: "Tritanium is currently selling for 5.50 ISK in Jita"

**SSE Events:**
```
thinking → text("Let me check") → tool_call_started →
tool_call_completed → text("5.50 ISK") → done
```

## Example 2: Multi-Tool Workflow

**User:** "Which ships were destroyed most in Jita last week?"

**Agent Flow:**
1. Calls `war_losses_get` tool (Jita, last 7 days)
2. Receives: `[{type_id: 587, count: 150}, {type_id: 588, count: 120}]`
3. Calls `item_name_get` tools for type IDs 587, 588
4. Receives: `["Rifter", "Merlin"]`
5. Responds with formatted answer

**Iterations:** 2 (first for losses, second for names)

## Example 3: Authorization Denial

**User:** "Transfer 100M ISK to character XYZ"

**Autonomy Level:** L1 (RECOMMENDATIONS)

**Agent Flow:**
1. LLM wants to call `wallet_transfer` (L3 CRITICAL)
2. AuthorizationChecker blocks: "L3 operations not allowed at L1"
3. LLM receives error in tool result
4. Responds: "I cannot transfer ISK at your current autonomy level"

**SSE Events:**
```
thinking → authorization_denied → text("I cannot transfer...") → done
```

## Example 4: Plan Approval Required

**User:** "Buy 1000 Tritanium at market price"

**Autonomy Level:** L1 (RECOMMENDATIONS)

**Agent Flow:**
1. LLM wants to call `market_order_create` (L2 MODERATE)
2. ApprovalManager: Exceeds L1 threshold
3. Creates Plan with 1 step
4. Emits `waiting_for_approval` event
5. Execution pauses

**User:** (clicks "Approve" in PlanApprovalCard)

**Continuation:**
6. POST /agent/execute with plan_id
7. Plan executes
8. Agent responds with order confirmation

## Example 5: Retry on Failure

**User:** "Get production cost for Stabber"

**Agent Flow:**
1. Calls `production_cost_get` tool
2. **Attempt 1:** Timeout (ESI slow)
3. **Attempt 2:** Retry after 1s → Timeout again
4. **Attempt 3:** Retry after 2s → Success!
5. Returns cost data

**SSE Events:**
```
thinking → tool_call_started → (internal retries) →
tool_call_completed → text("Production cost: 5.2M ISK") → done
```

## Example 6: Complex Multi-Step Query

**User:** "Find profitable manufacturing opportunities in Jita"

**Agent Flow:**
1. **Iteration 1:** Calls `hunter_scan` for opportunities
2. Receives: `[{type_id: 648, profit: 500000}, {type_id: 649, profit: 450000}]`
3. **Iteration 2:** Calls `item_name_get` for IDs
4. **Iteration 3:** Calls `production_cost_get` for details
5. **Iteration 4:** Synthesizes and ranks by ROI
6. Returns formatted recommendation

**Total Tools:** 7 (1 scan + 2 names + 2 costs + analysis)
**Iterations:** 4

## Testing Scenarios

### Test 1: Read-Only Tool (Auto-Execute)
```bash
# Autonomy: L1
# Query: "Search for Tritanium"
# Expected: Auto-executes, no approval needed
```

### Test 2: Moderate Tool (Requires Approval)
```bash
# Autonomy: L1
# Query: "Create shopping list"
# Expected: Waits for approval, shows PlanApprovalCard
```

### Test 3: Error Recovery
```bash
# Autonomy: L2
# Simulate: ESI timeout
# Expected: Retries 3x, then shows error to user
```

### Test 4: Authorization Block
```bash
# Autonomy: L0 (READ_ONLY)
# Query: "Update bookmark"
# Expected: Blocked, clear error message
```
```

**Step 3: Update CLAUDE.md**

Add to `CLAUDE.md`:

```markdown
### Agent Runtime (Phase 7: Tool Execution) ✅
- `POST /agent/session` - Create agent session
- `POST /agent/chat/stream` - Stream chat with tool execution
- `WS /agent/stream/{session_id}` - Real-time event stream

**Phase 7 Features:**
- ✅ Tool call detection from LLM streaming responses
- ✅ Agentic loop: LLM → Tools → LLM until final answer
- ✅ Authorization checks before tool execution
- ✅ Plan approval flow for high-risk operations
- ✅ Retry logic with exponential backoff
- ✅ Event broadcasting via WebSocket
- ✅ Support for both Anthropic and OpenAI

**Documentation:**
- [Phase 7 Tool Execution](docs/agent/phase7-tool-execution.md)
- [Phase 7 Usage Examples](docs/agent/phase7-usage-examples.md)
```

**Step 4: Commit**

```bash
git add docs/agent/phase7-tool-execution.md docs/agent/phase7-usage-examples.md CLAUDE.md
git commit -m "docs: add Phase 7 documentation and usage examples

- Comprehensive feature documentation
- Real-world usage examples
- Testing scenarios
- Architecture diagrams
- API reference updates
- Update CLAUDE.md with Phase 7 status"
```

---

## Execution Handoff

Plan complete and saved to `docs/plans/2025-12-29-phase7-tool-execution.md`.

**Two execution options:**

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

**Which approach?**
