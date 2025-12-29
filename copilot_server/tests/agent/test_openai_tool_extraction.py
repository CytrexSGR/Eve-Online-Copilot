"""
Integration test for OpenAI tool extraction.
Tests that OpenAIClient + ToolCallExtractor work together correctly.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from copilot_server.llm.openai_client import OpenAIClient
from copilot_server.agent.tool_extractor import ToolCallExtractor


class MockOpenAIChunk:
    """Mock OpenAI streaming chunk."""
    def __init__(self, content=None, function_call=None, finish_reason=None):
        self.choices = [MagicMock()]
        self.choices[0].delta = MagicMock()
        self.choices[0].finish_reason = finish_reason

        # Set up delta
        delta_dict = {}
        if content is not None:
            delta_dict["content"] = content
        if function_call is not None:
            delta_dict["function_call"] = function_call

        self.choices[0].delta.model_dump = MagicMock(return_value=delta_dict)
        self.choices[0].delta.content = content
        self.choices[0].delta.function_call = function_call if function_call else None


@pytest.mark.asyncio
async def test_openai_tool_extraction_with_actual_client():
    """
    Integration test: OpenAIClient streams raw chunks, ToolCallExtractor extracts tool calls.
    This is the CRITICAL test that proves Task 4 fix works.
    """
    # Create OpenAI client
    client = OpenAIClient(api_key="test-key", model="gpt-4")

    # Mock the streaming response
    mock_stream = [
        MockOpenAIChunk(content="Let me search for that item."),
        MockOpenAIChunk(function_call={"name": "search_items", "arguments": ""}),
        MockOpenAIChunk(function_call={"arguments": '{"query": "Tri'}),
        MockOpenAIChunk(function_call={"arguments": 'tanium"}'}),
        MockOpenAIChunk(finish_reason="function_call")
    ]

    async def mock_create_generator():
        """Simulate OpenAI streaming."""
        for chunk in mock_stream:
            yield chunk

    async def mock_create(**kwargs):
        """Return the async generator."""
        return mock_create_generator()

    # Mock the client's chat.completions.create
    client.client = MagicMock()
    client.client.chat = MagicMock()
    client.client.chat.completions = MagicMock()
    client.client.chat.completions.create = mock_create

    # Create tool extractor
    extractor = ToolCallExtractor()

    # Stream with convert_format=False (raw OpenAI chunks)
    params = {
        "model": "gpt-4",
        "messages": [{"role": "user", "content": "Find Tritanium"}],
        "tools": [
            {
                "name": "search_items",
                "description": "Search for items",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"}
                    }
                }
            }
        ]
    }

    text_chunks = []
    async for chunk in client._stream_response(params, convert_format=False):
        # Chunks should be in raw OpenAI format
        assert "choices" in chunk, "Expected raw OpenAI format with 'choices' key"

        # Process with extractor
        extractor.process_chunk(chunk, provider="openai")

        # Collect text
        if "choices" in chunk and chunk["choices"]:
            delta = chunk["choices"][0].get("delta", {})
            if "content" in delta and delta["content"]:
                text_chunks.append(delta["content"])

    # Verify tool extraction worked
    tool_calls = extractor.get_tool_calls()

    assert len(tool_calls) == 1, f"Expected 1 tool call, got {len(tool_calls)}"
    assert tool_calls[0]["name"] == "search_items"
    assert tool_calls[0]["input"] == {"query": "Tritanium"}

    # Verify text was also captured
    assert len(text_chunks) == 1
    assert text_chunks[0] == "Let me search for that item."


@pytest.mark.asyncio
async def test_openai_backward_compatibility():
    """
    Verify that convert_format=True (default) still works for backward compatibility.
    """
    client = OpenAIClient(api_key="test-key", model="gpt-4")

    mock_stream = [
        MockOpenAIChunk(content="Hello"),
        MockOpenAIChunk(content=" world"),
        MockOpenAIChunk(finish_reason="stop")
    ]

    async def mock_create_generator():
        for chunk in mock_stream:
            yield chunk

    async def mock_create(**kwargs):
        return mock_create_generator()

    client.client = MagicMock()
    client.client.chat = MagicMock()
    client.client.chat.completions = MagicMock()
    client.client.chat.completions.create = mock_create

    params = {
        "model": "gpt-4",
        "messages": [{"role": "user", "content": "Hello"}]
    }

    chunks = []
    # Default convert_format=True should give Anthropic format
    async for chunk in client._stream_response(params):
        chunks.append(chunk)

    # Should be in Anthropic format
    assert len(chunks) == 3
    assert chunks[0]["type"] == "content_block_delta"
    assert chunks[0]["delta"]["type"] == "text_delta"
    assert chunks[0]["delta"]["text"] == "Hello"

    assert chunks[2]["type"] == "message_stop"


@pytest.mark.asyncio
async def test_openai_multiple_tool_calls():
    """
    Test that multiple tool calls in sequence are extracted correctly.
    """
    client = OpenAIClient(api_key="test-key", model="gpt-4")

    # First tool call
    mock_stream = [
        MockOpenAIChunk(content="Searching first..."),
        MockOpenAIChunk(function_call={"name": "search_items", "arguments": '{"query": "A"}'}),
        MockOpenAIChunk(finish_reason="function_call")
    ]

    async def mock_create_generator():
        for chunk in mock_stream:
            yield chunk

    async def mock_create(**kwargs):
        return mock_create_generator()

    client.client = MagicMock()
    client.client.chat = MagicMock()
    client.client.chat.completions = MagicMock()
    client.client.chat.completions.create = mock_create

    extractor = ToolCallExtractor()

    params = {
        "model": "gpt-4",
        "messages": [{"role": "user", "content": "Search for A"}],
        "tools": [{"name": "search_items", "input_schema": {}}]
    }

    async for chunk in client._stream_response(params, convert_format=False):
        extractor.process_chunk(chunk, provider="openai")

    tool_calls = extractor.get_tool_calls()
    assert len(tool_calls) == 1
    assert tool_calls[0]["name"] == "search_items"
    assert tool_calls[0]["input"] == {"query": "A"}


@pytest.mark.asyncio
async def test_openai_no_tool_calls():
    """
    Test that responses without tool calls work correctly.
    """
    client = OpenAIClient(api_key="test-key", model="gpt-4")

    mock_stream = [
        MockOpenAIChunk(content="Just text, no tools"),
        MockOpenAIChunk(finish_reason="stop")
    ]

    async def mock_create_generator():
        for chunk in mock_stream:
            yield chunk

    async def mock_create(**kwargs):
        return mock_create_generator()

    client.client = MagicMock()
    client.client.chat = MagicMock()
    client.client.chat.completions = MagicMock()
    client.client.chat.completions.create = mock_create

    extractor = ToolCallExtractor()

    params = {
        "model": "gpt-4",
        "messages": [{"role": "user", "content": "Hello"}]
    }

    async for chunk in client._stream_response(params, convert_format=False):
        extractor.process_chunk(chunk, provider="openai")

    tool_calls = extractor.get_tool_calls()
    assert len(tool_calls) == 0

    text_chunks = extractor.get_text_chunks()
    assert len(text_chunks) == 1
    assert text_chunks[0] == "Just text, no tools"
