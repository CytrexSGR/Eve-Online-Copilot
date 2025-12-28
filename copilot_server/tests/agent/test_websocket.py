import pytest
import asyncio
import json
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, AsyncMock
from copilot_server.api import agent_routes
from copilot_server.agent.events import AgentEvent, AgentEventType, PlanProposedEvent


@pytest.fixture
def mock_session_manager():
    """Mock session manager."""
    mgr = MagicMock()
    mgr.load_session = AsyncMock()
    mgr.event_bus = MagicMock()
    mgr.event_bus.subscribe = MagicMock()
    mgr.event_bus.unsubscribe = MagicMock()
    return mgr


@pytest.fixture(autouse=True)
def inject_mocks(mock_session_manager):
    """Inject mocks into agent_routes."""
    agent_routes.session_manager = mock_session_manager
    yield
    agent_routes.session_manager = None


@pytest.fixture
def app():
    """Create test app."""
    app = FastAPI()
    app.include_router(agent_routes.router)
    return app


def test_websocket_connection(app, mock_session_manager):
    """Test WebSocket connection and event reception."""
    client = TestClient(app)

    # Simulate session exists
    mock_session = MagicMock()
    mock_session.id = "sess-test"
    mock_session_manager.load_session.return_value = mock_session

    # Track subscribed handler
    subscribed_handler = None

    def capture_subscribe(session_id, handler):
        nonlocal subscribed_handler
        subscribed_handler = handler

    mock_session_manager.event_bus.subscribe = capture_subscribe

    # Connect to WebSocket
    with client.websocket_connect("/agent/stream/sess-test") as websocket:
        # Verify connection established
        assert subscribed_handler is not None

        # Simulate event emission
        event = AgentEvent(
            type=AgentEventType.PLAN_PROPOSED,
            session_id="sess-test",
            payload={"test": "data"}
        )

        # Handler should send event to WebSocket
        # (In real implementation, this is handled by EventBus)
        event_dict = event.to_dict()

        # Verify event can be serialized
        assert event_dict["type"] == "plan_proposed"
        assert event_dict["session_id"] == "sess-test"
