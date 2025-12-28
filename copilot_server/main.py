#!/usr/bin/env python3
"""
EVE Co-Pilot AI Server
Main FastAPI application for AI Copilot with WebSocket and Audio support.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uuid
import logging

from .config import (
    COPILOT_HOST,
    COPILOT_PORT,
    DATABASE_URL,
    validate_config
)
import asyncpg
from .llm import AnthropicClient, ConversationManager
from .mcp import MCPClient, ToolOrchestrator
from .websocket import ConnectionManager, SessionManager
from .audio import AudioTranscriber, TextToSpeech
from .models.user_settings import get_default_settings
from .api import agent_routes
from .agent.sessions import AgentSessionManager
from .agent.runtime import AgentRuntime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI App
app = FastAPI(
    title="EVE Co-Pilot AI Server",
    description="AI-powered copilot server with LLM, WebSocket, and Audio capabilities",
    version="2.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
llm_client = AnthropicClient()
mcp_client = MCPClient()
# Note: orchestrator now requires user_settings, created per-request
conv_manager = ConversationManager()
conn_manager = ConnectionManager()
session_manager = SessionManager()
audio_transcriber = AudioTranscriber()
tts = TextToSpeech()

# Agent Runtime components (initialized on startup)
agent_session_manager: Optional[AgentSessionManager] = None
agent_runtime: Optional[AgentRuntime] = None


# Request/Response Models
class ChatRequest(BaseModel):
    """Chat message request."""
    message: str
    session_id: Optional[str] = None
    character_id: Optional[int] = None
    region_id: int = 10000002


class ChatResponse(BaseModel):
    """Chat message response."""
    response: str
    session_id: str
    tool_calls: List[Dict[str, Any]] = []


class SessionCreate(BaseModel):
    """Session creation request."""
    character_id: Optional[int] = None
    region_id: int = 10000002


# Startup/Shutdown
@app.on_event("startup")
async def startup():
    """Application startup."""
    global agent_session_manager, agent_runtime

    logger.info("Starting EVE Co-Pilot AI Server...")

    # Validate configuration
    warnings = validate_config()
    for warning in warnings:
        logger.warning(warning)

    # Load MCP tools
    tools = mcp_client.get_tools()
    logger.info(f"Loaded {len(tools)} MCP tools")

    # Initialize Agent Runtime
    try:
        agent_session_manager = AgentSessionManager()
        await agent_session_manager.startup()

        # Get user settings for orchestrator (use default for now)
        user_settings = get_default_settings(character_id=-1)

        # Create orchestrator for agent runtime
        orchestrator = ToolOrchestrator(mcp_client, llm_client, user_settings)

        # Create agent runtime
        agent_runtime = AgentRuntime(
            session_manager=agent_session_manager,
            llm_client=llm_client,
            orchestrator=orchestrator
        )

        # Set globals for routes
        agent_routes.session_manager = agent_session_manager
        agent_routes.runtime = agent_runtime

        logger.info("Agent Runtime initialized")
    except Exception as e:
        logger.error(f"Failed to initialize Agent Runtime: {e}")
        logger.warning("Agent Runtime endpoints will not be available")

    # Initialize database pool for agent routes
    try:
        agent_routes.db_pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=2,
            max_size=10
        )
        logger.info("Database pool initialized for agent routes")
    except Exception as e:
        logger.error(f"Failed to initialize database pool: {e}")

    logger.info(f"Server ready on http://{COPILOT_HOST}:{COPILOT_PORT}")


@app.on_event("shutdown")
async def shutdown():
    """Application shutdown."""
    global agent_session_manager

    logger.info("Shutting down EVE Co-Pilot AI Server...")

    # Shutdown Agent Runtime
    if agent_session_manager:
        try:
            await agent_session_manager.shutdown()
            logger.info("Agent Runtime shutdown complete")
        except Exception as e:
            logger.error(f"Error shutting down Agent Runtime: {e}")

    logger.info("Server stopped")


# Root endpoint
@app.get("/")
async def root():
    """API info."""
    return {
        "name": "EVE Co-Pilot AI Server",
        "version": "2.0.0",
        "status": "online",
        "endpoints": {
            "chat": "POST /copilot/chat",
            "websocket": "WS /copilot/ws/{session_id}",
            "sessions": "GET /copilot/sessions",
            "audio_transcribe": "POST /copilot/audio/transcribe",
            "audio_synthesize": "POST /copilot/audio/synthesize"
        }
    }


# Chat endpoint (REST)
@app.post("/copilot/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Send chat message and get response.

    Args:
        request: Chat request with message and context

    Returns:
        AI response with tool calls
    """
    try:
        # Get or create conversation
        if request.session_id:
            conv = conv_manager.get_conversation(request.session_id)
            if not conv:
                conv = conv_manager.create_conversation(
                    character_id=request.character_id,
                    region_id=request.region_id
                )
        else:
            conv = conv_manager.create_conversation(
                character_id=request.character_id,
                region_id=request.region_id
            )

        # Add user message
        conv.add_message("user", request.message)

        # Get messages for API
        messages = conv.get_messages_for_api()

        # Get user settings (default for now, will load from DB later)
        user_settings = get_default_settings(
            character_id=request.character_id or -1  # -1 = unauthenticated marker
        )

        # Create orchestrator with user settings
        orchestrator = ToolOrchestrator(mcp_client, llm_client, user_settings)

        # Execute workflow with tools
        result = await orchestrator.execute_workflow(messages)

        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])

        # Extract response text
        response_content = result["response"]["content"]
        response_text = ""
        for block in response_content:
            if block["type"] == "text":
                response_text += block["text"]

        # Add assistant response to conversation
        conv.add_message("assistant", response_content)

        return ChatResponse(
            response=response_text,
            session_id=conv.session_id,
            tool_calls=result.get("tool_results", [])
        )

    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# WebSocket endpoint
@app.websocket("/copilot/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket connection for real-time chat.

    Args:
        websocket: WebSocket connection
        session_id: Session identifier
    """
    client_id = str(uuid.uuid4())

    # Connect
    await conn_manager.connect(websocket, client_id, session_id)

    # Get or create conversation
    conv = conv_manager.get_conversation(session_id)
    if not conv:
        conv = conv_manager.create_conversation()
        logger.info(f"Created new conversation for session {session_id}")

    async def handle_ws_message(message: Dict, client_id: str, session_id: str):
        """Handle incoming WebSocket messages."""
        msg_type = message.get("type")

        if msg_type == "chat":
            # Chat message
            user_message = message.get("message", "")
            conv.add_message("user", user_message)

            # Send typing indicator
            await conn_manager.send_personal_message(
                {"type": "typing", "is_typing": True},
                client_id
            )

            # Get user settings
            user_settings = get_default_settings(
                character_id=conv.character_id or -1  # -1 = unauthenticated marker
            )

            # Create orchestrator with user settings
            ws_orchestrator = ToolOrchestrator(mcp_client, llm_client, user_settings)

            # Execute workflow
            messages = conv.get_messages_for_api()
            result = await ws_orchestrator.execute_workflow(messages)

            # Send response
            if "error" in result:
                await conn_manager.send_personal_message(
                    {"type": "error", "error": result["error"]},
                    client_id
                )
            else:
                response_content = result["response"]["content"]
                response_text = ""
                for block in response_content:
                    if block["type"] == "text":
                        response_text += block["text"]

                conv.add_message("assistant", response_content)

                await conn_manager.send_personal_message(
                    {
                        "type": "message",
                        "message": response_text,
                        "tool_calls": result.get("tool_results", [])
                    },
                    client_id
                )

        elif msg_type == "set_character":
            # Set character context
            character_id = message.get("character_id")
            conv.set_character(character_id)
            await conn_manager.send_personal_message(
                {"type": "context_updated", "character_id": character_id},
                client_id
            )

        elif msg_type == "set_region":
            # Set region context
            region_id = message.get("region_id")
            conv.set_region(region_id)
            await conn_manager.send_personal_message(
                {"type": "context_updated", "region_id": region_id},
                client_id
            )

    # Handle messages
    await conn_manager.handle_message(websocket, client_id, session_id, handle_ws_message)


# Session management
@app.post("/copilot/sessions")
async def create_session(request: SessionCreate):
    """Create new session."""
    session_id = session_manager.create_session(
        character_id=request.character_id,
        region_id=request.region_id
    )

    # Create conversation
    conv = conv_manager.create_conversation(
        character_id=request.character_id,
        region_id=request.region_id
    )

    return {
        "session_id": session_id,
        "conversation_id": conv.session_id
    }


@app.get("/copilot/sessions")
async def list_sessions():
    """List active sessions."""
    return {
        "sessions": session_manager.sessions,
        "ws_sessions": conn_manager.get_active_sessions(),
        "conversations": conv_manager.list_conversations()
    }


@app.get("/copilot/sessions/{session_id}")
async def get_session(session_id: str):
    """Get session details."""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


# Audio endpoints
@app.post("/copilot/audio/transcribe")
async def transcribe_audio(audio: UploadFile = File(...)):
    """
    Transcribe audio to text.

    Args:
        audio: Audio file

    Returns:
        Transcription result
    """
    try:
        audio_data = await audio.read()
        result = await audio_transcriber.transcribe(audio_data)
        return result
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class TTSRequest(BaseModel):
    """TTS request."""
    text: str
    voice: Optional[str] = None


@app.post("/copilot/audio/synthesize")
async def synthesize_speech(request: TTSRequest):
    """
    Synthesize text to speech.

    Args:
        request: TTS request

    Returns:
        Audio data
    """
    try:
        audio_data = await tts.synthesize(request.text, voice=request.voice)
        return {
            "audio": audio_data.hex(),  # Return as hex string
            "format": "mp3"
        }
    except Exception as e:
        logger.error(f"TTS error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# MCP tools proxy
@app.get("/copilot/tools")
async def list_tools():
    """List available MCP tools."""
    tools = mcp_client.get_tools()
    return {
        "tools": tools,
        "count": len(tools)
    }


@app.get("/copilot/tools/{tool_name}")
async def get_tool(tool_name: str):
    """Get tool information."""
    tool = mcp_client.get_tool_info(tool_name)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    return tool


# Include agent routes
app.include_router(agent_routes.router)


# Health check
@app.get("/health")
async def health():
    """Health check."""
    return {
        "status": "healthy",
        "llm": "configured" if llm_client.api_key else "missing_key",
        "mcp_tools": len(mcp_client.get_tools()),
        "active_sessions": len(session_manager.sessions),
        "active_ws": len(conn_manager.active_connections)
    }


if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting server on {COPILOT_HOST}:{COPILOT_PORT}")
    uvicorn.run(app, host=COPILOT_HOST, port=COPILOT_PORT)
