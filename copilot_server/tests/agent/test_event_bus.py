import pytest
import asyncio
from copilot_server.agent.event_bus import EventBus
from copilot_server.agent.events import AgentEvent, AgentEventType


@pytest.fixture
def event_bus():
    """Create event bus for testing."""
    return EventBus()


@pytest.mark.asyncio
async def test_subscribe_and_emit(event_bus):
    """Test subscribing to events and receiving them."""
    received_events = []

    async def handler(event: AgentEvent):
        received_events.append(event)

    # Subscribe to session
    event_bus.subscribe("sess-test", handler)

    # Emit event
    event = AgentEvent(
        type=AgentEventType.PLAN_PROPOSED,
        session_id="sess-test",
        payload={"test": "data"}
    )
    await event_bus.emit(event)

    # Wait for async delivery
    await asyncio.sleep(0.1)

    assert len(received_events) == 1
    assert received_events[0].session_id == "sess-test"


@pytest.mark.asyncio
async def test_unsubscribe(event_bus):
    """Test unsubscribing from events."""
    received_events = []

    async def handler(event: AgentEvent):
        received_events.append(event)

    # Subscribe
    event_bus.subscribe("sess-test", handler)

    # Emit first event
    event1 = AgentEvent(
        type=AgentEventType.PLAN_PROPOSED,
        session_id="sess-test"
    )
    await event_bus.emit(event1)
    await asyncio.sleep(0.1)

    # Unsubscribe
    event_bus.unsubscribe("sess-test", handler)

    # Emit second event (should not be received)
    event2 = AgentEvent(
        type=AgentEventType.TOOL_CALL_STARTED,
        session_id="sess-test"
    )
    await event_bus.emit(event2)
    await asyncio.sleep(0.1)

    # Only first event received
    assert len(received_events) == 1


@pytest.mark.asyncio
async def test_multiple_subscribers(event_bus):
    """Test multiple subscribers to same session."""
    received_1 = []
    received_2 = []

    async def handler1(event: AgentEvent):
        received_1.append(event)

    async def handler2(event: AgentEvent):
        received_2.append(event)

    event_bus.subscribe("sess-test", handler1)
    event_bus.subscribe("sess-test", handler2)

    event = AgentEvent(
        type=AgentEventType.PLAN_PROPOSED,
        session_id="sess-test"
    )
    await event_bus.emit(event)
    await asyncio.sleep(0.1)

    assert len(received_1) == 1
    assert len(received_2) == 1


@pytest.mark.asyncio
async def test_session_isolation(event_bus):
    """Test that events are isolated by session."""
    received_1 = []
    received_2 = []

    async def handler1(event: AgentEvent):
        received_1.append(event)

    async def handler2(event: AgentEvent):
        received_2.append(event)

    event_bus.subscribe("sess-1", handler1)
    event_bus.subscribe("sess-2", handler2)

    # Emit to session 1
    event1 = AgentEvent(
        type=AgentEventType.PLAN_PROPOSED,
        session_id="sess-1"
    )
    await event_bus.emit(event1)
    await asyncio.sleep(0.1)

    # Only handler1 should receive
    assert len(received_1) == 1
    assert len(received_2) == 0
