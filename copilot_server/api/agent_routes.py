"""
Agent API Routes
REST endpoints for agent runtime.
"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from ..agent.sessions import AgentSessionManager
from ..agent.runtime import AgentRuntime
from ..agent.models import SessionStatus
from ..models.user_settings import get_default_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["agent"])

# Global instances (initialized in main.py)
session_manager: Optional[AgentSessionManager] = None
runtime: Optional[AgentRuntime] = None


class ChatRequest(BaseModel):
    """Chat request."""
    message: str
    session_id: Optional[str] = None
    character_id: int


class ChatResponse(BaseModel):
    """Chat response."""
    session_id: str
    status: str


@router.post("/chat", response_model=ChatResponse)
async def agent_chat(request: ChatRequest):
    """
    Send message to agent.

    Creates new session if session_id is None, otherwise continues existing.
    """
    if not session_manager or not runtime:
        raise HTTPException(status_code=500, detail="Agent runtime not initialized")

    # Load or create session
    if request.session_id:
        session = await session_manager.load_session(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
    else:
        # Get user settings
        user_settings = get_default_settings(character_id=request.character_id or -1)

        # Create new session
        session = await session_manager.create_session(
            character_id=request.character_id,
            autonomy_level=user_settings.autonomy_level
        )

    # Add user message
    session.add_message("user", request.message)
    await session_manager.save_session(session)

    # Execute runtime (async, don't await in Phase 1)
    # Phase 2 will add background task execution
    try:
        await runtime.execute(session)
    except Exception as e:
        logger.error(f"Runtime execution failed: {e}")
        session.status = SessionStatus.ERROR
        await session_manager.save_session(session)

    return ChatResponse(
        session_id=session.id,
        status=session.status.value
    )


@router.get("/session/{session_id}")
async def get_session(session_id: str):
    """Get session state."""
    if not session_manager:
        raise HTTPException(status_code=500, detail="Session manager not initialized")

    session = await session_manager.load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "id": session.id,
        "character_id": session.character_id,
        "autonomy_level": session.autonomy_level.value,
        "status": session.status.value,
        "created_at": session.created_at.isoformat(),
        "updated_at": session.updated_at.isoformat(),
        "messages": [
            {
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat()
            }
            for msg in session.messages
        ]
    }


@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """Delete session."""
    if not session_manager:
        raise HTTPException(status_code=500, detail="Session manager not initialized")

    session = await session_manager.load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    await session_manager.delete_session(session_id)

    return {"message": "Session deleted", "session_id": session_id}
