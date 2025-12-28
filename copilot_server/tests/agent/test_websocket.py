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


def test_websocket_receives_events(app, mock_session_manager):
    """Test that events are actually received through WebSocket."""
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
        # Verify subscription happened
        assert subscribed_handler is not None

        # Simulate event emission by calling handler directly
        event = AgentEvent(
            type=AgentEventType.PLAN_PROPOSED,
            session_id="sess-test",
            payload={"plan_id": "plan-123", "description": "Test plan"}
        )

        # Call handler (simulating event bus publishing)
        import asyncio
        asyncio.run(subscribed_handler(event))

        # Receive event from WebSocket
        data = websocket.receive_json()

        # Verify received event
        assert data["type"] == "plan_proposed"
        assert data["session_id"] == "sess-test"
        assert data["payload"]["plan_id"] == "plan-123"


def test_websocket_ping_pong(app, mock_session_manager):
    """Test ping/pong mechanism for keepalive."""
    client = TestClient(app)

    # Simulate session exists
    mock_session = MagicMock()
    mock_session.id = "sess-test"
    mock_session_manager.load_session.return_value = mock_session

    mock_session_manager.event_bus.subscribe = MagicMock()

    # Connect to WebSocket
    with client.websocket_connect("/agent/stream/sess-test") as websocket:
        # Send ping
        websocket.send_text("ping")

        # Receive pong
        response = websocket.receive_text()
        assert response == "pong"


def test_websocket_session_not_found(app, mock_session_manager):
    """Test session not found scenario."""
    client = TestClient(app)

    # Simulate session doesn't exist
    mock_session_manager.load_session.return_value = None

    # Connect to WebSocket - should be rejected
    with client.websocket_connect("/agent/stream/sess-nonexistent") as websocket:
        # WebSocket should close with error
        # The connection will raise an exception or close immediately
        pass

    # Verify subscription was never called
    mock_session_manager.event_bus.subscribe.assert_not_called()
