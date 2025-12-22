"""
WebSocket Connection Handler
Manages WebSocket connections and message routing.
"""

from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List, Set
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages active WebSocket connections."""

    def __init__(self):
        """Initialize connection manager."""
        self.active_connections: Dict[str, WebSocket] = {}
        self.session_connections: Dict[str, Set[str]] = {}  # session_id -> {client_ids}
        logger.info("ConnectionManager initialized")

    async def connect(self, websocket: WebSocket, client_id: str, session_id: str):
        """
        Accept new WebSocket connection.

        Args:
            websocket: WebSocket connection
            client_id: Unique client identifier
            session_id: Session identifier
        """
        await websocket.accept()
        self.active_connections[client_id] = websocket

        # Track session mapping
        if session_id not in self.session_connections:
            self.session_connections[session_id] = set()
        self.session_connections[session_id].add(client_id)

        logger.info(f"Client {client_id} connected to session {session_id}")

    def disconnect(self, client_id: str, session_id: str):
        """
        Handle client disconnect.

        Args:
            client_id: Client identifier
            session_id: Session identifier
        """
        if client_id in self.active_connections:
            del self.active_connections[client_id]

        if session_id in self.session_connections:
            self.session_connections[session_id].discard(client_id)
            if not self.session_connections[session_id]:
                del self.session_connections[session_id]

        logger.info(f"Client {client_id} disconnected from session {session_id}")

    async def send_personal_message(self, message: Dict, client_id: str):
        """
        Send message to specific client.

        Args:
            message: Message to send
            client_id: Target client ID
        """
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Failed to send message to {client_id}: {e}")

    async def broadcast_to_session(self, message: Dict, session_id: str):
        """
        Broadcast message to all clients in a session.

        Args:
            message: Message to broadcast
            session_id: Target session ID
        """
        if session_id in self.session_connections:
            client_ids = self.session_connections[session_id].copy()
            for client_id in client_ids:
                await self.send_personal_message(message, client_id)

    async def handle_message(
        self,
        websocket: WebSocket,
        client_id: str,
        session_id: str,
        message_handler
    ):
        """
        Handle incoming WebSocket messages.

        Args:
            websocket: WebSocket connection
            client_id: Client identifier
            session_id: Session identifier
            message_handler: Async function to process messages
        """
        try:
            while True:
                # Receive message
                data = await websocket.receive_text()

                try:
                    message = json.loads(data)
                except json.JSONDecodeError:
                    await self.send_personal_message(
                        {
                            "type": "error",
                            "error": "Invalid JSON",
                            "timestamp": datetime.utcnow().isoformat()
                        },
                        client_id
                    )
                    continue

                # Process message
                try:
                    await message_handler(message, client_id, session_id)
                except Exception as e:
                    logger.error(f"Message handler error: {e}")
                    await self.send_personal_message(
                        {
                            "type": "error",
                            "error": str(e),
                            "timestamp": datetime.utcnow().isoformat()
                        },
                        client_id
                    )

        except WebSocketDisconnect:
            self.disconnect(client_id, session_id)
        except Exception as e:
            logger.error(f"WebSocket error for {client_id}: {e}")
            self.disconnect(client_id, session_id)

    def get_active_sessions(self) -> List[Dict]:
        """
        Get list of active sessions.

        Returns:
            List of session info
        """
        sessions = []
        for session_id, client_ids in self.session_connections.items():
            sessions.append({
                "session_id": session_id,
                "client_count": len(client_ids),
                "clients": list(client_ids)
            })
        return sessions
