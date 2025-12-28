import pytest
from copilot_server.agent.streaming import SSEFormatter, stream_llm_response


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


@pytest.mark.asyncio
async def test_stream_llm_response():
    """Test stream_llm_response with mock client."""

    # Mock LLM client
    class MockLLMClient:
        def __init__(self):
            self.model = "claude-3-sonnet-20240229"

        async def _stream_response(self, params):
            """Mock streaming response."""
            # Yield text chunks
            yield {
                "type": "content_block_delta",
                "delta": {
                    "type": "text_delta",
                    "text": "Hello "
                }
            }
            yield {
                "type": "content_block_delta",
                "delta": {
                    "type": "text_delta",
                    "text": "world!"
                }
            }
            # Yield completion event
            yield {"type": "message_stop"}

    # Create mock client
    client = MockLLMClient()

    # Stream response
    chunks = []
    async for chunk in stream_llm_response(
        client,
        messages=[{"role": "user", "content": "test"}],
        tools=[],
        system="test system"
    ):
        chunks.append(chunk)

    # Verify chunks
    assert len(chunks) == 3
    assert chunks[0] == {"type": "text", "text": "Hello "}
    assert chunks[1] == {"type": "text", "text": "world!"}
    assert chunks[2] == {"type": "done"}


@pytest.mark.asyncio
async def test_stream_llm_response_error():
    """Test stream_llm_response error handling."""

    # Mock LLM client that raises error
    class MockErrorClient:
        def __init__(self):
            self.model = "claude-3-sonnet-20240229"

        async def _stream_response(self, params):
            """Mock streaming response with error."""
            # Make this an async generator that raises
            if False:
                yield  # Make it a generator
            raise Exception("API connection failed")

    # Create mock client
    client = MockErrorClient()

    # Stream response
    chunks = []
    async for chunk in stream_llm_response(
        client,
        messages=[{"role": "user", "content": "test"}],
        tools=[],
        system="test system"
    ):
        chunks.append(chunk)

    # Verify error chunk
    assert len(chunks) == 1
    assert chunks[0]["type"] == "error"
    assert "API connection failed" in chunks[0]["error"]
