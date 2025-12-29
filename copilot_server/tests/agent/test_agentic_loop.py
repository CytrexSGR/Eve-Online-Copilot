import pytest
from unittest.mock import AsyncMock, Mock
from copilot_server.agent.agentic_loop import AgenticStreamingLoop
from copilot_server.models.user_settings import UserSettings, AutonomyLevel


async def async_gen(items):
    """Helper to create async generator from list."""
    for item in items:
        yield item


@pytest.mark.asyncio
async def test_execute_single_tool_call():
    """Test loop that executes one tool and returns answer."""
    # Mock dependencies
    llm_client = Mock()
    llm_client.model = "claude-3-5-sonnet-20241022"
    llm_client.build_tool_schema = Mock(return_value=[])

    # First response: tool call
    async def mock_stream(*args, **kwargs):
        for event in [
            {"type": "content_block_start", "index": 0, "content_block": {"type": "text"}},
            {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "Let me check"}},
            {"type": "content_block_stop", "index": 0},
            {"type": "content_block_start", "index": 1, "content_block": {"type": "tool_use", "id": "toolu_1", "name": "get_market_prices"}},
            {"type": "content_block_delta", "index": 1, "delta": {"type": "input_json_delta", "partial_json": '{}'}},
            {"type": "content_block_stop", "index": 1},
            {"type": "message_stop"}
        ]:
            yield event

    llm_client._stream_response = mock_stream

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


@pytest.mark.asyncio
async def test_multiple_iterations():
    """Test loop handles multiple iterations correctly."""
    llm_client = Mock()
    llm_client.model = "claude-3-5-sonnet-20241022"
    llm_client.build_tool_schema = Mock(return_value=[])

    # Track how many times we stream
    call_count = [0]

    async def mock_stream(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            # First iteration: request a tool (use a known READ_ONLY tool)
            for event in [
                {"type": "content_block_start", "index": 0, "content_block": {"type": "tool_use", "id": "t1", "name": "get_market_prices"}},
                {"type": "content_block_delta", "index": 0, "delta": {"type": "input_json_delta", "partial_json": '{}'}},
                {"type": "content_block_stop", "index": 0},
                {"type": "message_stop"}
            ]:
                yield event
        else:
            # Second iteration: final answer (no tools)
            for event in [
                {"type": "content_block_start", "index": 0, "content_block": {"type": "text"}},
                {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "Done"}},
                {"type": "content_block_stop", "index": 0},
                {"type": "message_stop"}
            ]:
                yield event

    llm_client._stream_response = mock_stream

    mcp_client = Mock()
    mcp_client.call_tool = Mock(return_value={"content": [{"type": "text", "text": "Result"}]})
    mcp_client.get_tools = Mock(return_value=[])

    user_settings = UserSettings(character_id=123, autonomy_level=AutonomyLevel.RECOMMENDATIONS)

    loop = AgenticStreamingLoop(llm_client, mcp_client, user_settings)

    events = []
    async for event in loop.execute([{"role": "user", "content": "Test"}]):
        events.append(event)

    # Should have 2 thinking events (2 iterations)
    thinking_events = [e for e in events if e["type"] == "thinking"]
    assert len(thinking_events) == 2
    assert thinking_events[0]["iteration"] == 1
    assert thinking_events[1]["iteration"] == 2

    # Should have tool execution events
    assert any(e["type"] == "tool_call_started" for e in events)
    assert any(e["type"] == "tool_call_completed" for e in events)

    # Should have done event
    assert any(e["type"] == "done" for e in events)


@pytest.mark.asyncio
async def test_authorization_denial():
    """Test that unauthorized tools are blocked."""
    llm_client = Mock()
    llm_client.model = "claude-3-5-sonnet-20241022"
    llm_client.build_tool_schema = Mock(return_value=[])

    # Request a WRITE_HIGH_RISK tool at READ_ONLY level
    async def mock_stream(*args, **kwargs):
        for event in [
            {"type": "content_block_start", "index": 0, "content_block": {"type": "tool_use", "id": "t1", "name": "shopping_list_create"}},
            {"type": "content_block_delta", "index": 0, "delta": {"type": "input_json_delta", "partial_json": '{"name": "Test"}'}},
            {"type": "content_block_stop", "index": 0},
            {"type": "message_stop"}
        ]:
            yield event

    llm_client._stream_response = mock_stream

    mcp_client = Mock()
    mcp_client.call_tool = Mock(return_value={"content": [{"type": "text", "text": "Should not execute"}]})
    mcp_client.get_tools = Mock(return_value=[])

    # READ_ONLY level - should block writes
    user_settings = UserSettings(character_id=123, autonomy_level=AutonomyLevel.READ_ONLY)

    loop = AgenticStreamingLoop(llm_client, mcp_client, user_settings)

    events = []
    async for event in loop.execute([{"role": "user", "content": "Test"}]):
        events.append(event)

    # Should have authorization_denied event
    assert any(e["type"] == "authorization_denied" for e in events)

    # Tool should NOT have been called
    mcp_client.call_tool.assert_not_called()


@pytest.mark.asyncio
async def test_max_iterations_limit():
    """Test that loop stops after max iterations."""
    llm_client = Mock()
    llm_client.model = "claude-3-5-sonnet-20241022"
    llm_client.build_tool_schema = Mock(return_value=[])

    # Always request a tool (infinite loop without limit)
    async def always_tool(*args, **kwargs):
        for event in [
            {"type": "content_block_start", "index": 0, "content_block": {"type": "tool_use", "id": "t1", "name": "get_market_prices"}},
            {"type": "content_block_delta", "index": 0, "delta": {"type": "input_json_delta", "partial_json": '{}'}},
            {"type": "content_block_stop", "index": 0},
            {"type": "message_stop"}
        ]:
            yield event

    llm_client._stream_response = always_tool

    mcp_client = Mock()
    mcp_client.call_tool = Mock(return_value={"content": [{"type": "text", "text": "Result"}]})
    mcp_client.get_tools = Mock(return_value=[])

    user_settings = UserSettings(character_id=123, autonomy_level=AutonomyLevel.RECOMMENDATIONS)

    # Set max_iterations to 3
    loop = AgenticStreamingLoop(llm_client, mcp_client, user_settings, max_iterations=3)

    events = []
    async for event in loop.execute([{"role": "user", "content": "Test"}]):
        events.append(event)

    # Should have exactly 3 thinking events
    thinking_events = [e for e in events if e["type"] == "thinking"]
    assert len(thinking_events) == 3

    # Should have error event for max iterations
    assert any(e["type"] == "error" and "Maximum iterations" in e.get("error", "") for e in events)
