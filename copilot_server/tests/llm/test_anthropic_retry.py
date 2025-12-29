"""
Tests for Anthropic Client Retry Logic
Tests retry behavior with exponential backoff using tenacity.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import anthropic
from copilot_server.llm.anthropic_client import AnthropicClient


@pytest.mark.asyncio
async def test_chat_retries_on_api_error():
    """Test that chat method retries on APIError."""
    client = AnthropicClient(api_key="test-key")

    # Mock the Anthropic client to fail twice then succeed
    call_count = 0

    def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            # Create a proper APIError with required arguments
            mock_request = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 500
            raise anthropic.APIConnectionError(message="Connection failed", request=mock_request)
        # Return successful response
        mock_response = MagicMock()
        mock_response.id = "msg-123"
        mock_response.model = "claude-3-sonnet-20240229"
        mock_response.role = "assistant"
        mock_response.content = [MagicMock(type="text", text="Success!")]
        mock_response.stop_reason = "end_turn"
        mock_response.usage = MagicMock(input_tokens=10, output_tokens=20)
        return mock_response

    with patch.object(client.client.messages, 'create', side_effect=side_effect):
        result = await client.chat([{"role": "user", "content": "Test"}])

        # Should succeed after retries
        assert result["content"][0]["text"] == "Success!"
        assert call_count == 3  # Failed twice, succeeded on third


@pytest.mark.asyncio
async def test_chat_retries_on_rate_limit_error():
    """Test that chat method retries on RateLimitError."""
    client = AnthropicClient(api_key="test-key")

    call_count = 0

    def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            # Create proper RateLimitError
            mock_response = MagicMock()
            mock_response.status_code = 429
            raise anthropic.RateLimitError(
                message="Rate limit exceeded",
                response=mock_response,
                body={"error": {"message": "Rate limit exceeded"}}
            )
        # Return successful response
        mock_response = MagicMock()
        mock_response.id = "msg-456"
        mock_response.model = "claude-3-sonnet-20240229"
        mock_response.role = "assistant"
        mock_response.content = [MagicMock(type="text", text="Rate limit recovered")]
        mock_response.stop_reason = "end_turn"
        mock_response.usage = MagicMock(input_tokens=15, output_tokens=25)
        return mock_response

    with patch.object(client.client.messages, 'create', side_effect=side_effect):
        result = await client.chat([{"role": "user", "content": "Test"}])

        # Should succeed after retry
        assert result["content"][0]["text"] == "Rate limit recovered"
        assert call_count == 2  # Failed once, succeeded on second


@pytest.mark.asyncio
async def test_chat_max_retries_exceeded():
    """Test that chat fails after max retries."""
    client = AnthropicClient(api_key="test-key")

    # Always fail with APIConnectionError
    def always_fail(*args, **kwargs):
        mock_request = MagicMock()
        raise anthropic.APIConnectionError(message="Persistent error", request=mock_request)

    with patch.object(
        client.client.messages,
        'create',
        side_effect=always_fail
    ):
        result = await client.chat([{"role": "user", "content": "Test"}])

        # Should return error after max retries
        assert "error" in result
        assert "error" in result["error"].lower()


@pytest.mark.asyncio
async def test_chat_exponential_backoff():
    """Test that retry uses exponential backoff."""
    client = AnthropicClient(api_key="test-key")

    import time
    call_times = []

    def side_effect(*args, **kwargs):
        call_times.append(time.time())
        if len(call_times) < 3:
            mock_request = MagicMock()
            raise anthropic.APIConnectionError(message="Temporary error", request=mock_request)
        # Return successful response
        mock_response = MagicMock()
        mock_response.id = "msg-789"
        mock_response.model = "claude-3-sonnet-20240229"
        mock_response.role = "assistant"
        mock_response.content = [MagicMock(type="text", text="Success after backoff")]
        mock_response.stop_reason = "end_turn"
        mock_response.usage = MagicMock(input_tokens=20, output_tokens=30)
        return mock_response

    with patch.object(client.client.messages, 'create', side_effect=side_effect):
        result = await client.chat([{"role": "user", "content": "Test"}])

        # Should succeed
        assert result["content"][0]["text"] == "Success after backoff"

        # Check that we have exponential delays
        assert len(call_times) == 3

        # Delays should be approximately 2^0=1s, 2^1=2s
        # We use wait_exponential(multiplier=1, min=2, max=10)
        # So: 2^0=1, 2^1=2 seconds minimum
        if len(call_times) >= 3:
            delay1 = call_times[1] - call_times[0]
            delay2 = call_times[2] - call_times[1]

            # First retry should be ~2 seconds (2^1 = 2)
            assert delay1 >= 1.8, f"First delay too short: {delay1}"

            # Second retry should be longer than first
            assert delay2 >= delay1, f"Delays not exponential: {delay1} vs {delay2}"


@pytest.mark.asyncio
async def test_chat_logs_retry_attempts(caplog):
    """Test that retry attempts are logged."""
    import logging
    caplog.set_level(logging.WARNING)

    client = AnthropicClient(api_key="test-key")

    call_count = 0

    def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            mock_request = MagicMock()
            raise anthropic.APIConnectionError(message="Temporary error", request=mock_request)
        mock_response = MagicMock()
        mock_response.id = "msg-log"
        mock_response.model = "claude-3-sonnet-20240229"
        mock_response.role = "assistant"
        mock_response.content = [MagicMock(type="text", text="Logged retry")]
        mock_response.stop_reason = "end_turn"
        mock_response.usage = MagicMock(input_tokens=10, output_tokens=10)
        return mock_response

    with patch.object(client.client.messages, 'create', side_effect=side_effect):
        result = await client.chat([{"role": "user", "content": "Test"}])

        # Check that result is successful
        assert result["content"][0]["text"] == "Logged retry"

        # Verify retry was logged (tenacity's before_sleep logs warnings)
        assert any("Retrying" in record.message for record in caplog.records), \
            "Retry attempt should be logged"


@pytest.mark.asyncio
async def test_streaming_retries_on_error():
    """Test that streaming retries on connection errors."""
    client = AnthropicClient(api_key="test-key")

    call_count = 0

    class MockStream:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def __iter__(self):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Connection lost")

            # Successful stream
            yield MagicMock(
                type='content_block_delta',
                delta=MagicMock(type='text_delta', text='Hello')
            )
            yield MagicMock(type='message_stop')

    with patch.object(client.client.messages, 'stream', return_value=MockStream()):
        chunks = []
        async for chunk in client._stream_response({"model": "test"}):
            chunks.append(chunk)

        # Should get successful chunks after retry
        assert len(chunks) >= 1
        # Note: Current implementation may not retry streaming,
        # this test will help us implement that feature
