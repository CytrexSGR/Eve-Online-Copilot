import asyncio
from typing import Dict, List, Callable, Awaitable
from copilot_server.agent.events import AgentEvent
import logging

logger = logging.getLogger(__name__)


EventHandler = Callable[[AgentEvent], Awaitable[None]]


class EventBus:
    """
    Event bus for agent runtime.

    Allows subscribing to events by session_id and emitting events
    to all subscribers.
    """

    def __init__(self):
        """Initialize event bus."""
        self._subscribers: Dict[str, List[EventHandler]] = {}

    def subscribe(self, session_id: str, handler: EventHandler):
        """
        Subscribe to events for a session.

        Args:
            session_id: Session ID to subscribe to
            handler: Async function to handle events
        """
        if session_id not in self._subscribers:
            self._subscribers[session_id] = []

        self._subscribers[session_id].append(handler)
        logger.debug(f"Subscribed to events for session {session_id}")

    def unsubscribe(self, session_id: str, handler: EventHandler):
        """
        Unsubscribe from events for a session.

        Args:
            session_id: Session ID to unsubscribe from
            handler: Handler to remove
        """
        if session_id in self._subscribers:
            try:
                self._subscribers[session_id].remove(handler)
                logger.debug(f"Unsubscribed from events for session {session_id}")

                # Clean up empty subscriber lists
                if not self._subscribers[session_id]:
                    del self._subscribers[session_id]
            except ValueError:
                pass

    async def emit(self, event: AgentEvent):
        """
        Emit an event to all subscribers for the session.

        Args:
            event: Event to emit
        """
        session_id = event.session_id

        if session_id not in self._subscribers:
            return

        # Create tasks for all subscribers
        handlers = self._subscribers[session_id].copy()
        tasks = [handler(event) for handler in handlers]

        # Execute all handlers concurrently
        if tasks:
            try:
                await asyncio.gather(*tasks, return_exceptions=True)
            except Exception as e:
                logger.error(f"Error emitting event to subscribers: {e}")
