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
            func: Function to execute (can be sync or async)
            *args, **kwargs: Function arguments

        Returns:
            Function result

        Raises:
            Last exception if all retries exhausted
        """
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                # Execute function - check if it's a coroutine
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
