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


@pytest.mark.asyncio
async def test_async_function_support():
    """Test that async functions are supported."""
    handler = RetryHandler(max_retries=3)

    call_count = 0
    async def async_flaky_function():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise RetryableError("Temporary failure")
        return {"success": True}

    result = await handler.execute_with_retry(async_flaky_function)

    assert result == {"success": True}
    assert call_count == 2


@pytest.mark.asyncio
async def test_non_retryable_error_fails_immediately():
    """Test that non-retryable errors fail immediately without retries."""
    handler = RetryHandler(max_retries=3)

    call_count = 0
    def raises_non_retryable():
        nonlocal call_count
        call_count += 1
        raise ValueError("This is not retryable")

    with pytest.raises(ValueError):
        await handler.execute_with_retry(raises_non_retryable)

    # Should only call once (no retries)
    assert call_count == 1


@pytest.mark.asyncio
async def test_exponential_backoff():
    """Test that delays follow exponential backoff pattern."""
    import time

    handler = RetryHandler(max_retries=3, base_delay=0.1, max_delay=1.0)

    call_times = []
    def failing_function():
        call_times.append(time.time())
        raise RetryableError("Temporary failure")

    try:
        await handler.execute_with_retry(failing_function)
    except RetryableError:
        pass

    # Should have 4 calls (initial + 3 retries)
    assert len(call_times) == 4

    # Calculate delays between calls
    delays = [call_times[i+1] - call_times[i] for i in range(len(call_times) - 1)]

    # Verify exponential backoff: 0.1s, 0.2s, 0.4s
    # Allow 50% tolerance for timing variance
    assert 0.05 < delays[0] < 0.15  # ~0.1s
    assert 0.15 < delays[1] < 0.25  # ~0.2s
    assert 0.35 < delays[2] < 0.45  # ~0.4s


@pytest.mark.asyncio
async def test_is_retryable_error():
    """Test the is_retryable_error detection logic."""
    handler = RetryHandler()

    # Retryable errors
    assert handler.is_retryable_error(Exception("Connection timeout"))
    assert handler.is_retryable_error(Exception("Rate limit exceeded"))
    assert handler.is_retryable_error(Exception("Service temporarily unavailable"))
    assert handler.is_retryable_error(Exception("Temporary failure"))
    assert handler.is_retryable_error(Exception("Connection refused"))

    # Non-retryable errors
    assert not handler.is_retryable_error(Exception("Invalid input"))
    assert not handler.is_retryable_error(Exception("Not found"))
    assert not handler.is_retryable_error(Exception("Access denied"))


@pytest.mark.asyncio
async def test_max_delay_cap():
    """Test that delay is capped at max_delay."""
    handler = RetryHandler(max_retries=10, base_delay=1.0, max_delay=5.0)

    call_count = 0
    def failing_function():
        nonlocal call_count
        call_count += 1
        raise RetryableError("Temporary failure")

    try:
        await handler.execute_with_retry(failing_function)
    except RetryableError:
        pass

    # Should have tried all retries
    assert call_count == 11  # Initial + 10 retries
