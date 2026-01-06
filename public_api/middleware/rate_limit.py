"""
Rate limiting middleware
100 requests per minute per IP address
"""

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded


# Initialize limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100/minute"],
    storage_uri="memory://",  # In-memory storage
)


# Custom rate limit error response
async def rate_limit_handler(request, exc):
    return {
        "error": "Rate limit exceeded",
        "detail": "Maximum 100 requests per minute allowed",
        "retry_after": exc.detail
    }
