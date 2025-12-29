"""
API Middleware
Authorization and validation for agent endpoints.
"""

from fastapi import HTTPException, Header
from typing import Optional
import logging

logger = logging.getLogger(__name__)


async def verify_session_access(
    session_id: str,
    character_id: Optional[int] = None,
    authorization: Optional[str] = Header(None)
) -> bool:
    """
    Verify user has access to session.

    For now, this is a placeholder. In production:
    - Verify JWT token in Authorization header
    - Check character_id matches token
    - Verify session belongs to character

    Args:
        session_id: Session to access
        character_id: Character requesting access
        authorization: Authorization header

    Returns:
        True if authorized

    Raises:
        HTTPException: If not authorized
    """
    # Phase 6: Basic validation only
    # Phase 7+: Add full JWT validation

    if not session_id:
        raise HTTPException(status_code=400, detail="Session ID required")

    # TODO Phase 7: Validate JWT token
    # TODO Phase 7: Verify character_id from token
    # TODO Phase 7: Check session ownership

    return True


async def validate_message_content(content: str) -> None:
    """
    Validate message content.

    Args:
        content: Message content

    Raises:
        HTTPException: If content invalid
    """
    if not content or not content.strip():
        raise HTTPException(status_code=400, detail="Message content cannot be empty")

    if len(content) > 10000:
        raise HTTPException(status_code=400, detail="Message too long (max 10000 characters)")
