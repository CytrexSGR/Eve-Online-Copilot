"""
Agent API Routes
REST endpoints for agent runtime.
"""

import asyncio
import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import asyncpg

from ..agent.sessions import AgentSessionManager
from ..agent.runtime import AgentRuntime
from ..agent.models import SessionStatus, PlanStatus
from ..agent.events import AgentEvent
from ..agent.messages import AgentMessage, MessageRepository
from ..models.user_settings import get_default_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["agent"])

# Global instances (initialized in main.py)
session_manager: Optional[AgentSessionManager] = None
runtime: Optional[AgentRuntime] = None
db_pool: Optional[asyncpg.Pool] = None


class ChatRequest(BaseModel):
    """Chat request."""
    message: str
    session_id: Optional[str] = None
    character_id: int


class ChatResponse(BaseModel):
    """Chat response."""
    session_id: str
    status: str


class ExecuteRequest(BaseModel):
    """Request to execute pending plan."""
    session_id: str
    plan_id: str


class RejectRequest(BaseModel):
    """Request to reject pending plan."""
    session_id: str
    plan_id: str


class ChatHistoryResponse(BaseModel):
    """Chat history response."""
    session_id: str
    messages: List[Dict[str, Any]]
    message_count: int


@router.post("/chat", response_model=ChatResponse)
async def agent_chat(request: ChatRequest):
    """
    Send message to agent.

    Creates new session if session_id is None, otherwise continues existing.
    Persists all messages to database.
    """
    if not session_manager or not runtime or not db_pool:
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

    # Save user message to database
    async with db_pool.acquire() as conn:
        repo = MessageRepository(conn)
        user_message = AgentMessage.create(
            session_id=session.id,
            role="user",
            content=request.message
        )
        await repo.save(user_message)

    # Add user message to session
    session.add_message("user", request.message)
    await session_manager.save_session(session)

    # Execute runtime (async, don't await in Phase 1)
    # Phase 2 will add background task execution
    try:
        response = await runtime.execute(session)

        # Save assistant response to database if available
        if response and "content" in response:
            async with db_pool.acquire() as conn:
                repo = MessageRepository(conn)

                # Extract text from content blocks
                text_content = ""
                for block in response["content"]:
                    if block.get("type") == "text":
                        text_content += block.get("text", "")

                assistant_message = AgentMessage.create(
                    session_id=session.id,
                    role="assistant",
                    content=text_content,
                    content_blocks=response["content"]
                )

                # Add token usage if available
                if "usage" in response:
                    assistant_message.token_usage = response["usage"]

                await repo.save(assistant_message)

    except Exception as e:
        logger.error(f"Runtime execution failed: {e}")
        session.status = SessionStatus.ERROR
        await session_manager.save_session(session)

    return ChatResponse(
        session_id=session.id,
        status=session.status.value
    )


@router.get("/chat/history/{session_id}", response_model=ChatHistoryResponse)
async def get_chat_history(session_id: str, limit: int = 100):
    """
    Get chat history for a session.

    Args:
        session_id: Session ID
        limit: Max messages to return (default 100)

    Returns:
        Chat history with messages
    """
    if not db_pool:
        raise HTTPException(status_code=500, detail="Database not initialized")

    # Verify session exists
    session = await session_manager.load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Get messages from database
    async with db_pool.acquire() as conn:
        repo = MessageRepository(conn)
        messages = await repo.get_by_session(session_id, limit)

    # Convert to dict format
    message_dicts = [
        {
            "id": msg.id,
            "role": msg.role,
            "content": msg.content,
            "content_blocks": msg.content_blocks,
            "created_at": msg.created_at.isoformat(),
            "token_usage": msg.token_usage
        }
        for msg in messages
    ]

    return ChatHistoryResponse(
        session_id=session_id,
        messages=message_dicts,
        message_count=len(message_dicts)
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


@router.post("/execute")
async def execute_plan(request: ExecuteRequest):
    """
    Approve and execute pending plan.

    Args:
        request: Execute request with session and plan IDs

    Returns:
        Execution status
    """
    if not session_manager or not runtime:
        raise HTTPException(status_code=500, detail="Agent runtime not initialized")

    # Load session
    session = await session_manager.load_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Load plan
    plan = await session_manager.plan_repo.load_plan(request.plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    # Verify plan belongs to session
    if plan.session_id != session.id:
        raise HTTPException(status_code=400, detail="Plan does not belong to session")

    # Mark plan as approved
    plan.status = PlanStatus.APPROVED
    plan.approved_at = datetime.now()
    await session_manager.plan_repo.save_plan(plan)

    # Update session status
    session.status = SessionStatus.EXECUTING
    session.context["current_plan_id"] = plan.id
    if "pending_plan_id" in session.context:
        del session.context["pending_plan_id"]
    await session_manager.save_session(session)

    # Execute plan (async, don't wait)
    asyncio.create_task(runtime._execute_plan(session, plan))

    return {
        "status": "executing",
        "session_id": session.id,
        "plan_id": plan.id,
        "message": "Plan approved and executing"
    }


@router.post("/reject")
async def reject_plan(request: RejectRequest):
    """
    Reject pending plan.

    Args:
        request: Reject request with session and plan IDs

    Returns:
        Rejection status
    """
    if not session_manager:
        raise HTTPException(status_code=500, detail="Session manager not initialized")

    # Load session
    session = await session_manager.load_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Load plan
    plan = await session_manager.plan_repo.load_plan(request.plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    # Mark plan as rejected
    plan.status = PlanStatus.REJECTED
    await session_manager.plan_repo.save_plan(plan)

    # Return session to idle
    session.status = SessionStatus.IDLE
    if "pending_plan_id" in session.context:
        del session.context["pending_plan_id"]
    await session_manager.save_session(session)

    return {
        "status": "idle",
        "session_id": session.id,
        "plan_id": plan.id,
        "message": "Plan rejected"
    }


@router.websocket("/stream/{session_id}")
async def websocket_stream(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time event streaming.

    Args:
        websocket: WebSocket connection
        session_id: Session ID to stream events for
    """
    # Accept connection
    await websocket.accept()
    logger.info(f"WebSocket connected for session: {session_id}")

    # Verify session exists
    session = await session_manager.load_session(session_id)
    if not session:
        logger.warning(f"WebSocket connection rejected - session not found: {session_id}")
        await websocket.close(code=1008, reason="Session not found")
        return

    # Event handler to send events to WebSocket
    async def send_event(event: AgentEvent):
        """Send event to WebSocket client."""
        try:
            event_dict = event.to_dict()
            await websocket.send_json(event_dict)
        except WebSocketDisconnect:
            logger.warning(
                f"WebSocket disconnected while sending event for session {session_id}",
                exc_info=True
            )
            # Unsubscribe on disconnect
            session_manager.event_bus.unsubscribe(session_id, send_event)
        except Exception as e:
            logger.error(
                f"Error sending event to WebSocket for session {session_id}: {e}",
                exc_info=True
            )

    # Subscribe to session events
    session_manager.event_bus.subscribe(session_id, send_event)
    logger.info(f"WebSocket subscribed to events for session: {session_id}")

    try:
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Receive messages (for heartbeat or control commands)
                data = await websocket.receive_text()

                # Handle ping/pong for keepalive
                if data == "ping":
                    await websocket.send_text("pong")
                    logger.debug(f"WebSocket ping/pong for session: {session_id}")

            except WebSocketDisconnect:
                break

    finally:
        # Unsubscribe when connection closes
        session_manager.event_bus.unsubscribe(session_id, send_event)
        logger.info(f"WebSocket disconnected for session: {session_id}")
