import asyncio
from typing import Callable, Any, Tuple, Type
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    """Configuration for retry logic."""
    max_retries: int = 3
    base_delay_ms: int = 1000  # 1 second
    max_delay_ms: int = 10000  # 10 seconds
    retryable_exceptions: Tuple[Type[Exception], ...] = (TimeoutError, ConnectionError)


async def execute_with_retry(
    func: Callable,
    tool_name: str,
    arguments: dict,
    config: RetryConfig = None
) -> Any:
    """
    Execute function with exponential backoff retry.

    Args:
        func: Async function to execute
        tool_name: Tool name (for logging)
        arguments: Tool arguments (for logging)
        config: Retry configuration

    Returns:
        Function result

    Raises:
        Exception: If max retries exceeded
    """
    if config is None:
        config = RetryConfig()

    last_exception = None

    for attempt in range(config.max_retries + 1):
        try:
            # Execute function
            if asyncio.iscoroutinefunction(func):
                result = await func()
            else:
                result = func()

            # Success
            if attempt > 0:
                logger.info(f"Tool {tool_name} succeeded after {attempt} retries")
            return result

        except config.retryable_exceptions as e:
            last_exception = e

            # Max retries exceeded
            if attempt >= config.max_retries:
                logger.error(
                    f"Tool {tool_name} failed after {config.max_retries} retries: {e}"
                )
                raise

            # Calculate exponential backoff delay
            delay_ms = min(
                config.base_delay_ms * (2 ** attempt),
                config.max_delay_ms
            )

            logger.warning(
                f"Tool {tool_name} failed (attempt {attempt + 1}/{config.max_retries + 1}): {e}. "
                f"Retrying in {delay_ms}ms..."
            )

            # Wait before retry
            await asyncio.sleep(delay_ms / 1000)

        except Exception as e:
            # Non-retryable exception, fail immediately
            logger.error(f"Tool {tool_name} failed with non-retryable error: {e}")
            raise

    # Should never reach here, but just in case
    raise last_exception
