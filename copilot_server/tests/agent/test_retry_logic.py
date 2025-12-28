import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
from copilot_server.agent.retry_logic import execute_with_retry, RetryConfig


@pytest.mark.asyncio
async def test_execute_with_retry_success_first_try():
    """Test successful execution on first try."""
    mock_func = AsyncMock(return_value={"result": "success"})

    result = await execute_with_retry(mock_func, "test_tool", {})

    assert result == {"result": "success"}
    assert mock_func.call_count == 1


@pytest.mark.asyncio
async def test_execute_with_retry_success_after_retries():
    """Test successful execution after retries."""
    call_count = 0

    async def failing_func():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ConnectionError("Temporary error")
        return {"result": "success"}

    config = RetryConfig(max_retries=3, base_delay_ms=10)
    result = await execute_with_retry(failing_func, "test_tool", {}, config=config)

    assert result == {"result": "success"}
    assert call_count == 3


@pytest.mark.asyncio
async def test_execute_with_retry_max_retries_exceeded():
    """Test that max retries is respected."""
    async def always_fails():
        raise TimeoutError("API timeout")

    config = RetryConfig(max_retries=2, base_delay_ms=10)

    with pytest.raises(TimeoutError):
        await execute_with_retry(always_fails, "test_tool", {}, config=config)


@pytest.mark.asyncio
async def test_execute_with_retry_exponential_backoff():
    """Test exponential backoff delay."""
    call_times = []

    async def failing_func():
        call_times.append(asyncio.get_event_loop().time())
        raise ConnectionError("Temporary error")

    config = RetryConfig(max_retries=3, base_delay_ms=100)

    try:
        await execute_with_retry(failing_func, "test_tool", {}, config=config)
    except ConnectionError:
        pass

    # Verify delays increase exponentially
    assert len(call_times) == 4  # Initial + 3 retries

    # Check delays (approximately 100ms, 200ms, 400ms)
    # Allow some tolerance for timing
    delay1 = (call_times[1] - call_times[0]) * 1000
    delay2 = (call_times[2] - call_times[1]) * 1000
    delay3 = (call_times[3] - call_times[2]) * 1000

    assert 80 < delay1 < 120  # ~100ms
    assert 180 < delay2 < 220  # ~200ms
    assert 380 < delay3 < 420  # ~400ms


def test_retry_config_defaults():
    """Test RetryConfig default values."""
    config = RetryConfig()

    assert config.max_retries == 3
    assert config.base_delay_ms == 1000
    assert config.max_delay_ms == 10000
    assert config.retryable_exceptions == (TimeoutError, ConnectionError)
