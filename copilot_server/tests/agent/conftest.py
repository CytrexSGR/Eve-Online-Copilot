"""
Pytest configuration for agent tests.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_llm_client():
    """Mock LLM client for testing."""
    client = AsyncMock()
    client.chat.return_value = {
        "content": [{"type": "text", "text": "Hello! How can I help?"}],
        "stop_reason": "end_turn"
    }
    return client


@pytest.fixture
def mock_orchestrator():
    """Mock orchestrator for testing."""
    orchestrator = AsyncMock()
    orchestrator.mcp = MagicMock()
    orchestrator.mcp.get_tools.return_value = []
    return orchestrator


@pytest.fixture
def mock_event_bus():
    """Mock EventBus for testing."""
    event_bus = MagicMock()
    # Track published events by session_id
    event_bus._published_events = {}

    async def publish_side_effect(session_id, event):
        """Async publish for event tracking."""
        if session_id not in event_bus._published_events:
            event_bus._published_events[session_id] = []
        event_bus._published_events[session_id].append(event)

    event_bus.publish = AsyncMock(side_effect=publish_side_effect)
    event_bus.get_published_events = lambda session_id: event_bus._published_events.get(session_id, [])

    return event_bus
