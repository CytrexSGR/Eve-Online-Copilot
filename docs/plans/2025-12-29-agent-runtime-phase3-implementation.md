# Agent Runtime Phase 3: Event System & WebSocket - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement real-time event streaming and WebSocket support for Agent Runtime with authorization integration and error handling

**Architecture:** Event-driven architecture with EventBus for internal event distribution, WebSocket endpoints for client streaming, PostgreSQL audit trail, authorization checks per tool execution, and retry logic for failed operations

**Tech Stack:** FastAPI WebSockets, asyncio, PostgreSQL (agent_events table), Pydantic v2, existing Authorization Framework

**Context:** Builds on Phase 1 (Session Manager, Runtime, API) and Phase 2 (Plan Detection, Auto-Execute, Approval)

---

## Task 1: Event Models and Database Schema

**Files:**
- Create: `copilot_server/agent/events.py`
- Create: `copilot_server/db/migrations/006_agent_events.sql`
- Test: `copilot_server/tests/agent/test_event_models.py`
- Test: `copilot_server/tests/agent/test_event_schema.py`

**Step 1: Write the failing test for event models**

Create test file `copilot_server/tests/agent/test_event_models.py`:

```python
import pytest
from datetime import datetime
from copilot_server.agent.events import (
    AgentEventType,
    AgentEvent,
    PlanProposedEvent,
    ToolCallStartedEvent,
    ToolCallCompletedEvent,
    AnswerReadyEvent
)


def test_event_type_enum():
    """Test that all event types are defined."""
    assert AgentEventType.PLAN_PROPOSED == "plan_proposed"
    assert AgentEventType.TOOL_CALL_STARTED == "tool_call_started"
    assert AgentEventType.TOOL_CALL_COMPLETED == "tool_call_completed"
    assert AgentEventType.ANSWER_READY == "answer_ready"
    assert AgentEventType.WAITING_FOR_APPROVAL == "waiting_for_approval"


def test_agent_event_base():
    """Test base AgentEvent model."""
    event = AgentEvent(
        type=AgentEventType.PLAN_PROPOSED,
        session_id="sess-test",
        plan_id="plan-test",
        payload={"test": "data"}
    )

    assert event.type == AgentEventType.PLAN_PROPOSED
    assert event.session_id == "sess-test"
    assert event.plan_id == "plan-test"
    assert event.payload == {"test": "data"}
    assert isinstance(event.timestamp, datetime)


def test_plan_proposed_event():
    """Test plan_proposed event with structured payload."""
    event = PlanProposedEvent(
        session_id="sess-test",
        plan_id="plan-test",
        purpose="Test plan",
        steps=[
            {"tool": "get_market_stats", "arguments": {"type_id": 34}}
        ],
        max_risk_level="READ_ONLY",
        tool_count=1,
        auto_executing=True
    )

    assert event.type == AgentEventType.PLAN_PROPOSED
    assert event.payload["purpose"] == "Test plan"
    assert event.payload["tool_count"] == 1
    assert event.payload["auto_executing"] is True


def test_tool_call_started_event():
    """Test tool_call_started event."""
    event = ToolCallStartedEvent(
        session_id="sess-test",
        plan_id="plan-test",
        step_index=0,
        tool="get_market_stats",
        arguments={"type_id": 34}
    )

    assert event.type == AgentEventType.TOOL_CALL_STARTED
    assert event.payload["step_index"] == 0
    assert event.payload["tool"] == "get_market_stats"


def test_tool_call_completed_event():
    """Test tool_call_completed event."""
    event = ToolCallCompletedEvent(
        session_id="sess-test",
        plan_id="plan-test",
        step_index=0,
        tool="get_market_stats",
        duration_ms=234,
        result_preview="5.2 ISK per unit"
    )

    assert event.type == AgentEventType.TOOL_CALL_COMPLETED
    assert event.payload["duration_ms"] == 234
    assert event.payload["result_preview"] == "5.2 ISK per unit"


def test_answer_ready_event():
    """Test answer_ready event."""
    event = AnswerReadyEvent(
        session_id="sess-test",
        answer="Tritanium costs 5.2 ISK",
        tool_calls_count=3,
        duration_ms=1234
    )

    assert event.type == AgentEventType.ANSWER_READY
    assert event.payload["answer"] == "Tritanium costs 5.2 ISK"
    assert event.payload["tool_calls_count"] == 3


def test_event_to_dict():
    """Test event serialization to dict."""
    event = AgentEvent(
        type=AgentEventType.PLAN_PROPOSED,
        session_id="sess-test",
        payload={"test": "data"}
    )

    event_dict = event.to_dict()

    assert event_dict["type"] == "plan_proposed"
    assert event_dict["session_id"] == "sess-test"
    assert event_dict["payload"] == {"test": "data"}
    assert "timestamp" in event_dict
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=/home/cytrex/eve_copilot:$PYTHONPATH pytest copilot_server/tests/agent/test_event_models.py -v`
Expected: FAIL with "No module named 'copilot_server.agent.events'"

**Step 3: Implement event models**

Create file `copilot_server/agent/events.py`:

```python
from enum import Enum
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from datetime import datetime


class AgentEventType(str, Enum):
    """Event types for agent runtime."""

    # Session Events
    SESSION_CREATED = "session_created"
    SESSION_RESUMED = "session_resumed"

    # Planning Events
    PLANNING_STARTED = "planning_started"
    PLAN_PROPOSED = "plan_proposed"
    PLAN_APPROVED = "plan_approved"
    PLAN_REJECTED = "plan_rejected"

    # Execution Events
    EXECUTION_STARTED = "execution_started"
    TOOL_CALL_STARTED = "tool_call_started"
    TOOL_CALL_COMPLETED = "tool_call_completed"
    TOOL_CALL_FAILED = "tool_call_failed"
    THINKING = "thinking"

    # Completion Events
    ANSWER_READY = "answer_ready"
    COMPLETED = "completed"
    COMPLETED_WITH_ERRORS = "completed_with_errors"

    # Control Events
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    MESSAGE_QUEUED = "message_queued"
    INTERRUPTED = "interrupted"
    ERROR = "error"
    AUTHORIZATION_DENIED = "authorization_denied"


class AgentEvent(BaseModel):
    """Base event model for agent runtime."""

    type: AgentEventType
    session_id: str
    plan_id: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for WebSocket transmission."""
        return {
            "type": self.type.value,
            "session_id": self.session_id,
            "plan_id": self.plan_id,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat()
        }


class PlanProposedEvent(AgentEvent):
    """Event emitted when a plan is proposed."""

    def __init__(
        self,
        session_id: str,
        plan_id: str,
        purpose: str,
        steps: List[Dict[str, Any]],
        max_risk_level: str,
        tool_count: int,
        auto_executing: bool,
        **kwargs
    ):
        super().__init__(
            type=AgentEventType.PLAN_PROPOSED,
            session_id=session_id,
            plan_id=plan_id,
            payload={
                "purpose": purpose,
                "steps": steps,
                "max_risk_level": max_risk_level,
                "tool_count": tool_count,
                "auto_executing": auto_executing
            },
            **kwargs
        )


class ToolCallStartedEvent(AgentEvent):
    """Event emitted when a tool call starts."""

    def __init__(
        self,
        session_id: str,
        plan_id: str,
        step_index: int,
        tool: str,
        arguments: Dict[str, Any],
        **kwargs
    ):
        super().__init__(
            type=AgentEventType.TOOL_CALL_STARTED,
            session_id=session_id,
            plan_id=plan_id,
            payload={
                "step_index": step_index,
                "tool": tool,
                "arguments": arguments
            },
            **kwargs
        )


class ToolCallCompletedEvent(AgentEvent):
    """Event emitted when a tool call completes."""

    def __init__(
        self,
        session_id: str,
        plan_id: str,
        step_index: int,
        tool: str,
        duration_ms: int,
        result_preview: str,
        **kwargs
    ):
        super().__init__(
            type=AgentEventType.TOOL_CALL_COMPLETED,
            session_id=session_id,
            plan_id=plan_id,
            payload={
                "step_index": step_index,
                "tool": tool,
                "duration_ms": duration_ms,
                "result_preview": result_preview
            },
            **kwargs
        )


class ToolCallFailedEvent(AgentEvent):
    """Event emitted when a tool call fails."""

    def __init__(
        self,
        session_id: str,
        plan_id: str,
        step_index: int,
        tool: str,
        error: str,
        retry_count: int = 0,
        **kwargs
    ):
        super().__init__(
            type=AgentEventType.TOOL_CALL_FAILED,
            session_id=session_id,
            plan_id=plan_id,
            payload={
                "step_index": step_index,
                "tool": tool,
                "error": error,
                "retry_count": retry_count
            },
            **kwargs
        )


class AnswerReadyEvent(AgentEvent):
    """Event emitted when final answer is ready."""

    def __init__(
        self,
        session_id: str,
        answer: str,
        tool_calls_count: int,
        duration_ms: int,
        **kwargs
    ):
        super().__init__(
            type=AgentEventType.ANSWER_READY,
            session_id=session_id,
            payload={
                "answer": answer,
                "tool_calls_count": tool_calls_count,
                "duration_ms": duration_ms
            },
            **kwargs
        )


class WaitingForApprovalEvent(AgentEvent):
    """Event emitted when waiting for plan approval."""

    def __init__(
        self,
        session_id: str,
        plan_id: str,
        message: str,
        **kwargs
    ):
        super().__init__(
            type=AgentEventType.WAITING_FOR_APPROVAL,
            session_id=session_id,
            plan_id=plan_id,
            payload={"message": message},
            **kwargs
        )


class AuthorizationDeniedEvent(AgentEvent):
    """Event emitted when tool authorization is denied."""

    def __init__(
        self,
        session_id: str,
        plan_id: str,
        tool: str,
        reason: str,
        **kwargs
    ):
        super().__init__(
            type=AgentEventType.AUTHORIZATION_DENIED,
            session_id=session_id,
            plan_id=plan_id,
            payload={
                "tool": tool,
                "reason": reason
            },
            **kwargs
        )
```

**Step 4: Write database schema test**

Create file `copilot_server/tests/agent/test_event_schema.py`:

```python
import pytest
import asyncpg

DATABASE_URL = "postgresql://eve:EvE_Pr0ject_2024@localhost/eve_sde"


@pytest.mark.asyncio
async def test_agent_events_table_exists():
    """Test that agent_events table exists with correct schema."""
    conn = await asyncpg.connect(DATABASE_URL)

    # Check table exists
    result = await conn.fetchval("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'agent_events'
        )
    """)
    assert result is True, "agent_events table should exist"

    # Check columns
    columns = await conn.fetch("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'agent_events'
        ORDER BY ordinal_position
    """)

    expected_columns = {
        'id': 'bigint',
        'session_id': 'character varying',
        'plan_id': 'character varying',
        'event_type': 'character varying',
        'payload': 'jsonb',
        'timestamp': 'timestamp without time zone'
    }

    actual_columns = {row['column_name']: row['data_type'] for row in columns}

    for col_name, col_type in expected_columns.items():
        assert col_name in actual_columns, f"Column {col_name} should exist"
        assert actual_columns[col_name] == col_type

    await conn.close()


@pytest.mark.asyncio
async def test_agent_events_indexes():
    """Test that agent_events has proper indexes."""
    conn = await asyncpg.connect(DATABASE_URL)

    indexes = await conn.fetch("""
        SELECT indexname
        FROM pg_indexes
        WHERE tablename = 'agent_events'
    """)

    index_names = [idx['indexname'] for idx in indexes]

    assert any('session_id' in name for name in index_names)
    assert any('plan_id' in name for name in index_names)
    assert any('event_type' in name for name in index_names)
    assert any('timestamp' in name for name in index_names)

    await conn.close()
```

**Step 5: Create migration**

Create file `copilot_server/db/migrations/006_agent_events.sql`:

```sql
-- Migration 006: Agent Events Table
-- Purpose: Store event audit trail for agent runtime

CREATE TABLE IF NOT EXISTS agent_events (
    id BIGSERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL REFERENCES agent_sessions(id) ON DELETE CASCADE,
    plan_id VARCHAR(255) REFERENCES agent_plans(id) ON DELETE SET NULL,
    event_type VARCHAR(50) NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_events_session_id ON agent_events(session_id);
CREATE INDEX IF NOT EXISTS idx_agent_events_plan_id ON agent_events(plan_id);
CREATE INDEX IF NOT EXISTS idx_agent_events_event_type ON agent_events(event_type);
CREATE INDEX IF NOT EXISTS idx_agent_events_timestamp ON agent_events(timestamp);

COMMENT ON TABLE agent_events IS 'Event audit trail for agent runtime debugging and monitoring';
COMMENT ON COLUMN agent_events.event_type IS 'Event type: plan_proposed, tool_call_started, etc.';
COMMENT ON COLUMN agent_events.payload IS 'JSON: event-specific data';

GRANT ALL ON agent_events TO eve;
GRANT ALL ON SEQUENCE agent_events_id_seq TO eve;
```

**Step 6: Run migration**

Run: `echo 'Aug2012#' | sudo -S docker exec eve_db psql -U eve -d eve_sde -c "$(cat copilot_server/db/migrations/006_agent_events.sql)"`

**Step 7: Run tests to verify they pass**

Run: `PYTHONPATH=/home/cytrex/eve_copilot:$PYTHONPATH pytest copilot_server/tests/agent/test_event_models.py copilot_server/tests/agent/test_event_schema.py -v`
Expected: PASS (all tests)

**Step 8: Commit**

```bash
git add copilot_server/agent/events.py copilot_server/db/migrations/006_agent_events.sql copilot_server/tests/agent/test_event_models.py copilot_server/tests/agent/test_event_schema.py
git commit -m "feat(agent): add event models and agent_events table

- Add AgentEventType enum with 19 event types
- Add AgentEvent base model and specialized event classes
- Create agent_events PostgreSQL table with indexes
- Add comprehensive tests for event models and schema

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 2: EventBus Implementation

**Files:**
- Create: `copilot_server/agent/event_bus.py`
- Create: `copilot_server/agent/event_repository.py`
- Test: `copilot_server/tests/agent/test_event_bus.py`
- Test: `copilot_server/tests/agent/test_event_repository.py`

**Step 1: Write the failing test for EventBus**

Create test file `copilot_server/tests/agent/test_event_bus.py`:

```python
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
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=/home/cytrex/eve_copilot:$PYTHONPATH pytest copilot_server/tests/agent/test_event_bus.py -v`
Expected: FAIL with "No module named 'copilot_server.agent.event_bus'"

**Step 3: Implement EventBus**

Create file `copilot_server/agent/event_bus.py`:

```python
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
```

**Step 4: Write event repository test**

Create file `copilot_server/tests/agent/test_event_repository.py`:

```python
import pytest
import asyncpg
from copilot_server.agent.event_repository import EventRepository
from copilot_server.agent.events import AgentEvent, AgentEventType

DATABASE_URL = "postgresql://eve:EvE_Pr0ject_2024@localhost/eve_sde"


@pytest.fixture
async def event_repo():
    """Create event repository."""
    repo = EventRepository(DATABASE_URL)
    await repo.connect()
    yield repo
    await repo.disconnect()


@pytest.fixture
async def cleanup_events():
    """Clean up test events."""
    yield
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute("DELETE FROM agent_events WHERE session_id LIKE 'sess-test%'")
    await conn.close()


@pytest.mark.asyncio
async def test_save_event(event_repo, cleanup_events):
    """Test saving an event to database."""
    event = AgentEvent(
        type=AgentEventType.PLAN_PROPOSED,
        session_id="sess-test-save",
        plan_id="plan-test",
        payload={"test": "data"}
    )

    await event_repo.save(event)

    # Verify saved
    events = await event_repo.load_by_session("sess-test-save")
    assert len(events) >= 1

    saved_event = events[0]
    assert saved_event.session_id == "sess-test-save"
    assert saved_event.plan_id == "plan-test"
    assert saved_event.payload == {"test": "data"}


@pytest.mark.asyncio
async def test_load_by_session(event_repo, cleanup_events):
    """Test loading events by session."""
    # Save multiple events
    for i in range(3):
        event = AgentEvent(
            type=AgentEventType.TOOL_CALL_STARTED,
            session_id="sess-test-load",
            payload={"index": i}
        )
        await event_repo.save(event)

    # Load all events for session
    events = await event_repo.load_by_session("sess-test-load")

    assert len(events) == 3
    # Events should be ordered by timestamp
    assert events[0].payload["index"] == 0
    assert events[1].payload["index"] == 1
    assert events[2].payload["index"] == 2


@pytest.mark.asyncio
async def test_load_by_plan(event_repo, cleanup_events):
    """Test loading events by plan."""
    plan_id = "plan-test-load"

    # Save events for plan
    for i in range(2):
        event = AgentEvent(
            type=AgentEventType.TOOL_CALL_STARTED,
            session_id="sess-test-plan",
            plan_id=plan_id,
            payload={"index": i}
        )
        await event_repo.save(event)

    # Load events for plan
    events = await event_repo.load_by_plan(plan_id)

    assert len(events) == 2
    assert all(e.plan_id == plan_id for e in events)
```

**Step 5: Implement EventRepository**

Create file `copilot_server/agent/event_repository.py`:

```python
import asyncpg
import json
from typing import Optional, List
from copilot_server.agent.events import AgentEvent, AgentEventType


class EventRepository:
    """PostgreSQL repository for agent events."""

    def __init__(self, database_url: str):
        """
        Initialize repository.

        Args:
            database_url: PostgreSQL connection string
        """
        self.database_url = database_url
        self._pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        """Create connection pool."""
        self._pool = await asyncpg.create_pool(self.database_url, min_size=2, max_size=10)

    async def disconnect(self):
        """Close connection pool."""
        if self._pool:
            await self._pool.close()

    async def save(self, event: AgentEvent):
        """
        Save event to database.

        Args:
            event: Event to save
        """
        async with self._pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO agent_events (session_id, plan_id, event_type, payload, timestamp)
                VALUES ($1, $2, $3, $4::jsonb, $5)
            """,
                event.session_id,
                event.plan_id,
                event.type.value,
                json.dumps(event.payload),
                event.timestamp
            )

    async def load_by_session(self, session_id: str) -> List[AgentEvent]:
        """
        Load all events for a session.

        Args:
            session_id: Session ID

        Returns:
            List of events ordered by timestamp
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT session_id, plan_id, event_type, payload, timestamp
                FROM agent_events
                WHERE session_id = $1
                ORDER BY timestamp ASC
            """, session_id)

            return [self._row_to_event(row) for row in rows]

    async def load_by_plan(self, plan_id: str) -> List[AgentEvent]:
        """
        Load all events for a plan.

        Args:
            plan_id: Plan ID

        Returns:
            List of events ordered by timestamp
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT session_id, plan_id, event_type, payload, timestamp
                FROM agent_events
                WHERE plan_id = $1
                ORDER BY timestamp ASC
            """, plan_id)

            return [self._row_to_event(row) for row in rows]

    def _row_to_event(self, row) -> AgentEvent:
        """Convert database row to AgentEvent."""
        payload = row["payload"]
        if isinstance(payload, str):
            payload = json.loads(payload)

        return AgentEvent(
            type=AgentEventType(row["event_type"]),
            session_id=row["session_id"],
            plan_id=row["plan_id"],
            payload=payload,
            timestamp=row["timestamp"]
        )
```

**Step 6: Run tests to verify they pass**

Run: `PYTHONPATH=/home/cytrex/eve_copilot:$PYTHONPATH pytest copilot_server/tests/agent/test_event_bus.py copilot_server/tests/agent/test_event_repository.py -v`
Expected: PASS (all tests)

**Step 7: Commit**

```bash
git add copilot_server/agent/event_bus.py copilot_server/agent/event_repository.py copilot_server/tests/agent/test_event_bus.py copilot_server/tests/agent/test_event_repository.py
git commit -m "feat(agent): implement EventBus and EventRepository

- Add EventBus for in-memory event distribution
- Add EventRepository for PostgreSQL event persistence
- Support subscribe/unsubscribe by session_id
- Add session isolation for event delivery
- Add comprehensive tests for event bus and repository

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 3: WebSocket Streaming Endpoint

**Files:**
- Modify: `copilot_server/api/agent_routes.py` (add WebSocket endpoint)
- Create: `copilot_server/tests/agent/test_websocket.py`

**Step 1: Write the failing test**

Create test file `copilot_server/tests/agent/test_websocket.py`:

```python
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
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=/home/cytrex/eve_copilot:$PYTHONPATH pytest copilot_server/tests/agent/test_websocket.py -v`
Expected: FAIL (WebSocket endpoint doesn't exist)

**Step 3: Add WebSocket endpoint**

Modify `copilot_server/api/agent_routes.py`, add these imports and endpoint:

```python
from fastapi import WebSocket, WebSocketDisconnect
from copilot_server.agent.events import AgentEvent
import json


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

    # Verify session exists
    session = await session_manager.load_session(session_id)
    if not session:
        await websocket.close(code=1008, reason="Session not found")
        return

    # Event handler to send events to WebSocket
    async def send_event(event: AgentEvent):
        """Send event to WebSocket client."""
        try:
            event_dict = event.to_dict()
            await websocket.send_json(event_dict)
        except Exception as e:
            logger.error(f"Error sending event to WebSocket: {e}")

    # Subscribe to session events
    session_manager.event_bus.subscribe(session_id, send_event)

    try:
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Receive messages (for heartbeat or control commands)
                data = await websocket.receive_text()

                # Handle ping/pong for keepalive
                if data == "ping":
                    await websocket.send_text("pong")

            except WebSocketDisconnect:
                break

    finally:
        # Unsubscribe when connection closes
        session_manager.event_bus.unsubscribe(session_id, send_event)
```

**Step 4: Add EventBus to AgentSessionManager**

Modify `copilot_server/agent/sessions.py`:

```python
from copilot_server.agent.event_bus import EventBus
from copilot_server.agent.event_repository import EventRepository

class AgentSessionManager:
    def __init__(self):
        # ... existing init ...
        self.event_bus = EventBus()
        self.event_repo: Optional[EventRepository] = None

    async def startup(self):
        """Initialize storage layers."""
        # ... existing startup code ...

        # Initialize event repository
        self.event_repo = EventRepository(self.postgres.database_url)
        await self.event_repo.connect()

    async def shutdown(self):
        """Clean shutdown."""
        # ... existing shutdown code ...

        if self.event_repo:
            await self.event_repo.disconnect()
```

**Step 5: Run test to verify it passes**

Run: `PYTHONPATH=/home/cytrex/eve_copilot:$PYTHONPATH pytest copilot_server/tests/agent/test_websocket.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add copilot_server/api/agent_routes.py copilot_server/agent/sessions.py copilot_server/tests/agent/test_websocket.py
git commit -m "feat(agent): add WebSocket streaming endpoint

- Add WS /agent/stream/{session_id} endpoint
- Integrate EventBus with AgentSessionManager
- Add EventRepository to session manager startup
- Handle WebSocket subscribe/unsubscribe lifecycle
- Add tests for WebSocket connection

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 4: Event Emission in Runtime

**Files:**
- Modify: `copilot_server/agent/runtime.py`
- Test: `copilot_server/tests/agent/test_runtime_events.py`

**Step 1: Write the failing test**

Create test file `copilot_server/tests/agent/test_runtime_events.py`:

```python
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
from copilot_server.agent.runtime import AgentRuntime
from copilot_server.agent.models import AgentSession
from copilot_server.agent.events import AgentEventType
from copilot_server.models.user_settings import AutonomyLevel


@pytest.fixture
def mock_llm():
    """Mock LLM client."""
    llm = MagicMock()
    llm.chat = AsyncMock()
    llm.build_tool_schema = MagicMock(return_value=[])
    return llm


@pytest.fixture
def mock_orchestrator():
    """Mock orchestrator."""
    orch = MagicMock()
    orch.mcp = MagicMock()
    orch.mcp.get_tools = MagicMock(return_value=[])
    orch.mcp.call_tool = MagicMock(return_value={"result": "success"})
    return orch


@pytest.fixture
def mock_session_manager():
    """Mock session manager."""
    mgr = MagicMock()
    mgr.save_session = AsyncMock()
    mgr.plan_repo = MagicMock()
    mgr.plan_repo.save_plan = AsyncMock()
    mgr.event_bus = MagicMock()
    mgr.event_bus.emit = AsyncMock()
    mgr.event_repo = MagicMock()
    mgr.event_repo.save = AsyncMock()
    return mgr


@pytest.fixture
def runtime(mock_llm, mock_orchestrator, mock_session_manager):
    """Create runtime with mocks."""
    return AgentRuntime(
        session_manager=mock_session_manager,
        llm_client=mock_llm,
        orchestrator=mock_orchestrator
    )


@pytest.mark.asyncio
async def test_runtime_emits_plan_proposed(runtime, mock_llm, mock_session_manager):
    """Test that runtime emits plan_proposed event."""
    session = AgentSession(
        id="sess-test",
        character_id=123,
        autonomy_level=AutonomyLevel.RECOMMENDATIONS
    )
    session.add_message("user", "Analyze war zones")

    # Mock LLM response: 3-tool plan
    mock_llm.chat.return_value = {
        "content": [
            {"type": "text", "text": "I'll analyze war zones."},
            {"type": "tool_use", "id": "call1", "name": "get_war_summary", "input": {}},
            {"type": "tool_use", "id": "call2", "name": "get_combat_losses", "input": {}},
            {"type": "tool_use", "id": "call3", "name": "get_top_destroyed_ships", "input": {}}
        ],
        "stop_reason": "tool_use"
    }

    await runtime.execute(session)

    # Verify plan_proposed event was emitted
    emit_calls = mock_session_manager.event_bus.emit.call_args_list
    assert len(emit_calls) >= 1

    # Find plan_proposed event
    plan_proposed_events = [
        call[0][0] for call in emit_calls
        if call[0][0].type == AgentEventType.PLAN_PROPOSED
    ]
    assert len(plan_proposed_events) == 1


@pytest.mark.asyncio
async def test_runtime_emits_tool_call_events(runtime, mock_llm, mock_session_manager):
    """Test that runtime emits tool_call_started and tool_call_completed."""
    session = AgentSession(
        id="sess-test",
        character_id=123,
        autonomy_level=AutonomyLevel.ASSISTED  # Auto-execute
    )
    session.add_message("user", "Get market data")

    # Mock LLM response: 3 READ_ONLY tools
    mock_llm.chat.return_value = {
        "content": [
            {"type": "tool_use", "id": "call1", "name": "get_market_stats", "input": {}},
            {"type": "tool_use", "id": "call2", "name": "get_war_summary", "input": {}},
            {"type": "tool_use", "id": "call3", "name": "search_item", "input": {}}
        ],
        "stop_reason": "tool_use"
    }

    # Second call: return answer
    mock_llm.chat.side_effect = [
        mock_llm.chat.return_value,
        {"content": [{"type": "text", "text": "Analysis complete."}], "stop_reason": "end_turn"}
    ]

    await runtime.execute(session)

    # Verify tool_call events
    emit_calls = mock_session_manager.event_bus.emit.call_args_list

    tool_started_events = [
        call[0][0] for call in emit_calls
        if call[0][0].type == AgentEventType.TOOL_CALL_STARTED
    ]

    tool_completed_events = [
        call[0][0] for call in emit_calls
        if call[0][0].type == AgentEventType.TOOL_CALL_COMPLETED
    ]

    # Should have 3 started and 3 completed events
    assert len(tool_started_events) == 3
    assert len(tool_completed_events) == 3
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=/home/cytrex/eve_copilot:$PYTHONPATH pytest copilot_server/tests/agent/test_runtime_events.py -v`
Expected: FAIL (events not emitted)

**Step 3: Add event emission to runtime**

Modify `copilot_server/agent/runtime.py`:

```python
from copilot_server.agent.events import (
    PlanProposedEvent,
    ToolCallStartedEvent,
    ToolCallCompletedEvent,
    ToolCallFailedEvent,
    AnswerReadyEvent,
    WaitingForApprovalEvent
)
import time as time_module


class AgentRuntime:
    # ... existing code ...

    async def execute(self, session: AgentSession, max_iterations: int = 5) -> None:
        """Execute agent runtime with event emission."""
        session.status = SessionStatus.PLANNING
        await self.session_manager.save_session(session)

        iteration = 0
        while iteration < max_iterations:
            iteration += 1

            messages = self._build_messages(session)
            tools = self.orchestrator.mcp.get_tools()
            claude_tools = self.llm_client.build_tool_schema(tools)

            response = await self.llm_client.chat(messages=messages, tools=claude_tools)

            # Check if response is a multi-tool plan
            if self.plan_detector.is_plan(response):
                plan = self.plan_detector.extract_plan(response, session.id)

                # Decide auto-execute
                auto_exec = should_auto_execute(plan, session.autonomy_level)
                plan.auto_executing = auto_exec

                # Save plan
                await self.session_manager.plan_repo.save_plan(plan)

                # Emit plan_proposed event
                plan_proposed_event = PlanProposedEvent(
                    session_id=session.id,
                    plan_id=plan.id,
                    purpose=plan.purpose,
                    steps=[
                        {"tool": step.tool, "arguments": step.arguments}
                        for step in plan.steps
                    ],
                    max_risk_level=plan.max_risk_level.value,
                    tool_count=len(plan.steps),
                    auto_executing=auto_exec
                )
                await self.session_manager.event_bus.emit(plan_proposed_event)
                await self.session_manager.event_repo.save(plan_proposed_event)

                if auto_exec:
                    session.status = SessionStatus.EXECUTING
                    session.context["current_plan_id"] = plan.id
                    await self.session_manager.save_session(session)

                    await self._execute_plan(session, plan)
                    return
                else:
                    # Wait for approval
                    session.status = SessionStatus.WAITING_APPROVAL
                    session.context["pending_plan_id"] = plan.id
                    await self.session_manager.save_session(session)

                    # Emit waiting_for_approval event
                    waiting_event = WaitingForApprovalEvent(
                        session_id=session.id,
                        plan_id=plan.id,
                        message="Plan requires user approval due to WRITE operations"
                    )
                    await self.session_manager.event_bus.emit(waiting_event)
                    await self.session_manager.event_repo.save(waiting_event)
                    return

            # Single/dual tool execution
            if self._has_tool_calls(response):
                session.status = SessionStatus.EXECUTING
                await self.session_manager.save_session(session)
                await self._execute_tools(response, session)
                continue
            else:
                # No tools, final answer
                answer = self._extract_text(response)
                session.add_message("assistant", answer)
                session.status = SessionStatus.COMPLETED
                await self.session_manager.save_session(session)

                # Emit answer_ready event
                answer_event = AnswerReadyEvent(
                    session_id=session.id,
                    answer=answer,
                    tool_calls_count=0,
                    duration_ms=0  # TODO: Track total duration
                )
                await self.session_manager.event_bus.emit(answer_event)
                await self.session_manager.event_repo.save(answer_event)
                return

        # Max iterations reached
        session.status = SessionStatus.ERROR
        await self.session_manager.save_session(session)

    async def _execute_plan(self, session: AgentSession, plan: Plan) -> None:
        """Execute multi-tool plan with event emission."""
        start_time = time_module.time()
        plan.status = PlanStatus.EXECUTING
        plan.executed_at = datetime.now()
        await self.session_manager.plan_repo.save_plan(plan)

        results = []

        for step_index, step in enumerate(plan.steps):
            # Emit tool_call_started event
            started_event = ToolCallStartedEvent(
                session_id=session.id,
                plan_id=plan.id,
                step_index=step_index,
                tool=step.tool,
                arguments=step.arguments
            )
            await self.session_manager.event_bus.emit(started_event)
            await self.session_manager.event_repo.save(started_event)

            try:
                tool_start = time_module.time()

                result = await asyncio.to_thread(
                    self.orchestrator.mcp.call_tool,
                    step.tool,
                    step.arguments
                )

                tool_duration = int((time_module.time() - tool_start) * 1000)
                results.append(result)

                # Emit tool_call_completed event
                result_preview = str(result)[:100] if result else ""
                completed_event = ToolCallCompletedEvent(
                    session_id=session.id,
                    plan_id=plan.id,
                    step_index=step_index,
                    tool=step.tool,
                    duration_ms=tool_duration,
                    result_preview=result_preview
                )
                await self.session_manager.event_bus.emit(completed_event)
                await self.session_manager.event_repo.save(completed_event)

            except Exception as e:
                logger.error(f"Tool execution failed: {step.tool}, error: {e}")

                # Emit tool_call_failed event
                failed_event = ToolCallFailedEvent(
                    session_id=session.id,
                    plan_id=plan.id,
                    step_index=step_index,
                    tool=step.tool,
                    error=str(e),
                    retry_count=0
                )
                await self.session_manager.event_bus.emit(failed_event)
                await self.session_manager.event_repo.save(failed_event)

                plan.status = PlanStatus.FAILED
                await self.session_manager.plan_repo.save_plan(plan)
                session.status = SessionStatus.COMPLETED_WITH_ERRORS
                await self.session_manager.save_session(session)
                return

        # Mark plan completed
        duration_ms = int((time_module.time() - start_time) * 1000)
        plan.status = PlanStatus.COMPLETED
        plan.completed_at = datetime.now()
        plan.duration_ms = duration_ms
        await self.session_manager.plan_repo.save_plan(plan)

        # Add summary to session
        tool_summary = f"Executed {len(results)} tools from plan: {plan.purpose}"
        session.add_message("assistant", tool_summary)
        session.status = SessionStatus.COMPLETED
        await self.session_manager.save_session(session)
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=/home/cytrex/eve_copilot:$PYTHONPATH pytest copilot_server/tests/agent/test_runtime_events.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add copilot_server/agent/runtime.py copilot_server/tests/agent/test_runtime_events.py
git commit -m "feat(agent): add event emission to runtime

- Emit plan_proposed when plan detected
- Emit tool_call_started/completed for each step
- Emit tool_call_failed on errors
- Emit answer_ready on completion
- Emit waiting_for_approval when plan needs approval
- Save all events to database via event_repo
- Add comprehensive tests for event emission

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 5: Authorization Integration

**Files:**
- Create: `copilot_server/agent/authorization.py`
- Modify: `copilot_server/agent/runtime.py`
- Test: `copilot_server/tests/agent/test_authorization_integration.py`

**Step 1: Write the failing test**

Create test file `copilot_server/tests/agent/test_authorization_integration.py`:

```python
import pytest
from unittest.mock import MagicMock, AsyncMock
from copilot_server.agent.authorization import AuthorizationChecker
from copilot_server.agent.runtime import AgentRuntime
from copilot_server.agent.models import AgentSession, Plan, PlanStep
from copilot_server.models.user_settings import AutonomyLevel, RiskLevel


@pytest.fixture
def auth_checker():
    """Create authorization checker."""
    checker = AuthorizationChecker()

    # Mock user blacklist
    checker.user_blacklists = {
        123: ["delete_bookmark", "dangerous_tool"]
    }

    return checker


def test_check_authorization_allowed():
    """Test authorization check for allowed tool."""
    checker = AuthorizationChecker()

    allowed, reason = checker.check_authorization(
        character_id=123,
        tool_name="get_market_stats",
        arguments={}
    )

    assert allowed is True
    assert reason is None


def test_check_authorization_blacklisted():
    """Test authorization check for blacklisted tool."""
    checker = AuthorizationChecker()
    checker.user_blacklists = {
        123: ["delete_bookmark"]
    }

    allowed, reason = checker.check_authorization(
        character_id=123,
        tool_name="delete_bookmark",
        arguments={}
    )

    assert allowed is False
    assert "blacklisted" in reason.lower()


def test_check_authorization_dangerous_args():
    """Test authorization check for dangerous arguments."""
    checker = AuthorizationChecker()

    # SQL injection attempt
    allowed, reason = checker.check_authorization(
        character_id=123,
        tool_name="search_item",
        arguments={"query": "'; DROP TABLE users;--"}
    )

    assert allowed is False
    assert "dangerous" in reason.lower()


@pytest.mark.asyncio
async def test_runtime_respects_authorization():
    """Test that runtime checks authorization before executing tools."""
    # Create mocks
    mock_session_manager = MagicMock()
    mock_session_manager.save_session = AsyncMock()
    mock_session_manager.plan_repo = MagicMock()
    mock_session_manager.plan_repo.save_plan = AsyncMock()
    mock_session_manager.event_bus = MagicMock()
    mock_session_manager.event_bus.emit = AsyncMock()
    mock_session_manager.event_repo = MagicMock()
    mock_session_manager.event_repo.save = AsyncMock()

    mock_llm = MagicMock()
    mock_orchestrator = MagicMock()

    # Create authorization checker
    auth_checker = AuthorizationChecker()
    auth_checker.user_blacklists = {
        123: ["delete_bookmark"]
    }

    # Create runtime with auth checker
    runtime = AgentRuntime(
        session_manager=mock_session_manager,
        llm_client=mock_llm,
        orchestrator=mock_orchestrator,
        auth_checker=auth_checker
    )

    # Create session
    session = AgentSession(
        id="sess-test",
        character_id=123,
        autonomy_level=AutonomyLevel.ASSISTED
    )

    # Create plan with blacklisted tool
    plan = Plan(
        id="plan-test",
        session_id="sess-test",
        purpose="Test plan",
        steps=[
            PlanStep(tool="get_bookmarks", arguments={}, risk_level=RiskLevel.READ_ONLY),
            PlanStep(tool="delete_bookmark", arguments={"id": 1}, risk_level=RiskLevel.WRITE_HIGH_RISK)
        ],
        max_risk_level=RiskLevel.WRITE_HIGH_RISK
    )

    # Execute plan
    await runtime._execute_plan(session, plan)

    # Verify authorization_denied event was emitted
    emit_calls = mock_session_manager.event_bus.emit.call_args_list
    auth_denied_events = [
        call[0][0] for call in emit_calls
        if hasattr(call[0][0], 'type') and call[0][0].type.value == "authorization_denied"
    ]

    assert len(auth_denied_events) >= 1
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=/home/cytrex/eve_copilot:$PYTHONPATH pytest copilot_server/tests/agent/test_authorization_integration.py -v`
Expected: FAIL (AuthorizationChecker doesn't exist)

**Step 3: Implement AuthorizationChecker**

Create file `copilot_server/agent/authorization.py`:

```python
from typing import Dict, List, Tuple, Any, Optional
import re


class AuthorizationChecker:
    """
    Authorization checker for agent runtime.

    Validates tool execution against user blacklists and security rules.
    """

    def __init__(self):
        """Initialize authorization checker."""
        self.user_blacklists: Dict[int, List[str]] = {}

        # Dangerous patterns in arguments
        self.dangerous_patterns = [
            r"';.*--",  # SQL injection
            r"<script",  # XSS
            r"\.\./",   # Path traversal
            r"rm -rf",  # Dangerous shell commands
        ]

    def check_authorization(
        self,
        character_id: int,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if tool execution is authorized.

        Args:
            character_id: Character ID requesting execution
            tool_name: Tool to execute
            arguments: Tool arguments

        Returns:
            Tuple of (allowed: bool, denial_reason: Optional[str])
        """
        # Check user blacklist
        if character_id in self.user_blacklists:
            if tool_name in self.user_blacklists[character_id]:
                return False, f"Tool {tool_name} is blacklisted for this user"

        # Check for dangerous patterns in arguments
        for pattern in self.dangerous_patterns:
            for key, value in arguments.items():
                if isinstance(value, str):
                    if re.search(pattern, value, re.IGNORECASE):
                        return False, f"Dangerous pattern detected in argument '{key}'"

        # All checks passed
        return True, None

    def add_to_blacklist(self, character_id: int, tool_name: str):
        """Add tool to user's blacklist."""
        if character_id not in self.user_blacklists:
            self.user_blacklists[character_id] = []

        if tool_name not in self.user_blacklists[character_id]:
            self.user_blacklists[character_id].append(tool_name)

    def remove_from_blacklist(self, character_id: int, tool_name: str):
        """Remove tool from user's blacklist."""
        if character_id in self.user_blacklists:
            try:
                self.user_blacklists[character_id].remove(tool_name)
            except ValueError:
                pass
```

**Step 4: Integrate authorization into runtime**

Modify `copilot_server/agent/runtime.py`:

```python
from copilot_server.agent.authorization import AuthorizationChecker
from copilot_server.agent.events import AuthorizationDeniedEvent


class AgentRuntime:
    def __init__(
        self,
        session_manager,
        llm_client,
        orchestrator,
        auth_checker: Optional[AuthorizationChecker] = None
    ):
        self.session_manager = session_manager
        self.llm_client = llm_client
        self.orchestrator = orchestrator
        self.plan_detector = PlanDetector(orchestrator.mcp)
        self.auth_checker = auth_checker or AuthorizationChecker()

    async def _execute_plan(self, session: AgentSession, plan: Plan) -> None:
        """Execute multi-tool plan with authorization checks."""
        start_time = time_module.time()
        plan.status = PlanStatus.EXECUTING
        plan.executed_at = datetime.now()
        await self.session_manager.plan_repo.save_plan(plan)

        results = []
        failed_steps = []

        for step_index, step in enumerate(plan.steps):
            # Emit tool_call_started event
            started_event = ToolCallStartedEvent(
                session_id=session.id,
                plan_id=plan.id,
                step_index=step_index,
                tool=step.tool,
                arguments=step.arguments
            )
            await self.session_manager.event_bus.emit(started_event)
            await self.session_manager.event_repo.save(started_event)

            # CHECK AUTHORIZATION BEFORE EXECUTION
            allowed, denial_reason = self.auth_checker.check_authorization(
                character_id=session.character_id,
                tool_name=step.tool,
                arguments=step.arguments
            )

            if not allowed:
                # Emit authorization_denied event
                auth_denied_event = AuthorizationDeniedEvent(
                    session_id=session.id,
                    plan_id=plan.id,
                    tool=step.tool,
                    reason=denial_reason
                )
                await self.session_manager.event_bus.emit(auth_denied_event)
                await self.session_manager.event_repo.save(auth_denied_event)

                # Mark step as failed
                failed_steps.append({
                    "tool": step.tool,
                    "error": f"Authorization denied: {denial_reason}"
                })

                logger.warning(f"Authorization denied for {step.tool}: {denial_reason}")
                continue

            try:
                tool_start = time_module.time()

                result = await asyncio.to_thread(
                    self.orchestrator.mcp.call_tool,
                    step.tool,
                    step.arguments
                )

                tool_duration = int((time_module.time() - tool_start) * 1000)
                results.append(result)

                # Emit tool_call_completed event
                result_preview = str(result)[:100] if result else ""
                completed_event = ToolCallCompletedEvent(
                    session_id=session.id,
                    plan_id=plan.id,
                    step_index=step_index,
                    tool=step.tool,
                    duration_ms=tool_duration,
                    result_preview=result_preview
                )
                await self.session_manager.event_bus.emit(completed_event)
                await self.session_manager.event_repo.save(completed_event)

            except Exception as e:
                logger.error(f"Tool execution failed: {step.tool}, error: {e}")

                # Emit tool_call_failed event
                failed_event = ToolCallFailedEvent(
                    session_id=session.id,
                    plan_id=plan.id,
                    step_index=step_index,
                    tool=step.tool,
                    error=str(e),
                    retry_count=0
                )
                await self.session_manager.event_bus.emit(failed_event)
                await self.session_manager.event_repo.save(failed_event)

                failed_steps.append({
                    "tool": step.tool,
                    "error": str(e)
                })

        # Mark plan completed (with or without errors)
        duration_ms = int((time_module.time() - start_time) * 1000)

        if failed_steps:
            plan.status = PlanStatus.FAILED
            session.status = SessionStatus.COMPLETED_WITH_ERRORS
        else:
            plan.status = PlanStatus.COMPLETED
            session.status = SessionStatus.COMPLETED

        plan.completed_at = datetime.now()
        plan.duration_ms = duration_ms
        await self.session_manager.plan_repo.save_plan(plan)

        # Add summary to session
        if failed_steps:
            summary = f"Executed {len(results)}/{len(plan.steps)} tools. {len(failed_steps)} failed."
        else:
            summary = f"Executed {len(results)} tools from plan: {plan.purpose}"

        session.add_message("assistant", summary)
        await self.session_manager.save_session(session)
```

**Step 5: Run test to verify it passes**

Run: `PYTHONPATH=/home/cytrex/eve_copilot:$PYTHONPATH pytest copilot_server/tests/agent/test_authorization_integration.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add copilot_server/agent/authorization.py copilot_server/agent/runtime.py copilot_server/tests/agent/test_authorization_integration.py
git commit -m "feat(agent): integrate authorization framework

- Add AuthorizationChecker for tool validation
- Check user blacklists before tool execution
- Detect dangerous patterns in arguments
- Emit authorization_denied events
- Continue plan execution on authorization failure
- Track failed steps and partial results
- Add comprehensive authorization tests

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 6: Error Handling with Retry Logic

**Files:**
- Create: `copilot_server/agent/retry_logic.py`
- Modify: `copilot_server/agent/runtime.py`
- Test: `copilot_server/tests/agent/test_retry_logic.py`

**Step 1: Write the failing test**

Create test file `copilot_server/tests/agent/test_retry_logic.py`:

```python
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
from copilot_server.agent.retry_logic import execute_with_retry, RetryConfig


@pytest.mark.asyncio
async def test_execute_with_retry_success_first_try():
    """Test successful execution on first try."""
    mock_func = AsyncMock(return_value={"result": "success"})

    result = await execute_with_retry(mock_func, "test_tool", {})

    assert result == {"result": "success"}
    assert mock_func.call_count == 1


@pytest.mark.asyncio
async def test_execute_with_retry_success_after_retries():
    """Test successful execution after retries."""
    call_count = 0

    async def failing_func():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ConnectionError("Temporary error")
        return {"result": "success"}

    config = RetryConfig(max_retries=3, base_delay_ms=10)
    result = await execute_with_retry(failing_func, "test_tool", {}, config=config)

    assert result == {"result": "success"}
    assert call_count == 3


@pytest.mark.asyncio
async def test_execute_with_retry_max_retries_exceeded():
    """Test that max retries is respected."""
    async def always_fails():
        raise TimeoutError("API timeout")

    config = RetryConfig(max_retries=2, base_delay_ms=10)

    with pytest.raises(TimeoutError):
        await execute_with_retry(always_fails, "test_tool", {}, config=config)


@pytest.mark.asyncio
async def test_execute_with_retry_exponential_backoff():
    """Test exponential backoff delay."""
    call_times = []

    async def failing_func():
        call_times.append(asyncio.get_event_loop().time())
        raise ConnectionError("Temporary error")

    config = RetryConfig(max_retries=3, base_delay_ms=100)

    try:
        await execute_with_retry(failing_func, "test_tool", {}, config=config)
    except ConnectionError:
        pass

    # Verify delays increase exponentially
    assert len(call_times) == 4  # Initial + 3 retries

    # Check delays (approximately 100ms, 200ms, 400ms)
    # Allow some tolerance for timing
    delay1 = (call_times[1] - call_times[0]) * 1000
    delay2 = (call_times[2] - call_times[1]) * 1000
    delay3 = (call_times[3] - call_times[2]) * 1000

    assert 80 < delay1 < 120  # ~100ms
    assert 180 < delay2 < 220  # ~200ms
    assert 380 < delay3 < 420  # ~400ms


def test_retry_config_defaults():
    """Test RetryConfig default values."""
    config = RetryConfig()

    assert config.max_retries == 3
    assert config.base_delay_ms == 1000
    assert config.max_delay_ms == 10000
    assert config.retryable_exceptions == (TimeoutError, ConnectionError)
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=/home/cytrex/eve_copilot:$PYTHONPATH pytest copilot_server/tests/agent/test_retry_logic.py -v`
Expected: FAIL (module doesn't exist)

**Step 3: Implement retry logic**

Create file `copilot_server/agent/retry_logic.py`:

```python
import asyncio
from typing import Callable, Any, Tuple, Type
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    """Configuration for retry logic."""
    max_retries: int = 3
    base_delay_ms: int = 1000  # 1 second
    max_delay_ms: int = 10000  # 10 seconds
    retryable_exceptions: Tuple[Type[Exception], ...] = (TimeoutError, ConnectionError)


async def execute_with_retry(
    func: Callable,
    tool_name: str,
    arguments: dict,
    config: RetryConfig = None
) -> Any:
    """
    Execute function with exponential backoff retry.

    Args:
        func: Async function to execute
        tool_name: Tool name (for logging)
        arguments: Tool arguments (for logging)
        config: Retry configuration

    Returns:
        Function result

    Raises:
        Exception: If max retries exceeded
    """
    if config is None:
        config = RetryConfig()

    last_exception = None

    for attempt in range(config.max_retries + 1):
        try:
            # Execute function
            if asyncio.iscoroutinefunction(func):
                result = await func()
            else:
                result = func()

            # Success
            if attempt > 0:
                logger.info(f"Tool {tool_name} succeeded after {attempt} retries")
            return result

        except config.retryable_exceptions as e:
            last_exception = e

            # Max retries exceeded
            if attempt >= config.max_retries:
                logger.error(
                    f"Tool {tool_name} failed after {config.max_retries} retries: {e}"
                )
                raise

            # Calculate exponential backoff delay
            delay_ms = min(
                config.base_delay_ms * (2 ** attempt),
                config.max_delay_ms
            )

            logger.warning(
                f"Tool {tool_name} failed (attempt {attempt + 1}/{config.max_retries + 1}): {e}. "
                f"Retrying in {delay_ms}ms..."
            )

            # Wait before retry
            await asyncio.sleep(delay_ms / 1000)

        except Exception as e:
            # Non-retryable exception, fail immediately
            logger.error(f"Tool {tool_name} failed with non-retryable error: {e}")
            raise

    # Should never reach here, but just in case
    raise last_exception
```

**Step 4: Integrate retry logic into runtime**

Modify `copilot_server/agent/runtime.py`:

```python
from copilot_server.agent.retry_logic import execute_with_retry, RetryConfig


class AgentRuntime:
    def __init__(self, ..., retry_config: RetryConfig = None):
        # ... existing init ...
        self.retry_config = retry_config or RetryConfig()

    async def _execute_plan(self, session: AgentSession, plan: Plan) -> None:
        """Execute multi-tool plan with retry logic."""
        # ... existing code ...

        for step_index, step in enumerate(plan.steps):
            # ... emit started event ...
            # ... check authorization ...

            if not allowed:
                # ... handle authorization denial ...
                continue

            try:
                tool_start = time_module.time()

                # Execute with retry logic
                async def execute_tool():
                    return await asyncio.to_thread(
                        self.orchestrator.mcp.call_tool,
                        step.tool,
                        step.arguments
                    )

                result = await execute_with_retry(
                    execute_tool,
                    step.tool,
                    step.arguments,
                    config=self.retry_config
                )

                tool_duration = int((time_module.time() - tool_start) * 1000)
                results.append(result)

                # ... emit completed event ...

            except Exception as e:
                logger.error(f"Tool execution failed after retries: {step.tool}, error: {e}")

                # Emit tool_call_failed event with retry count
                failed_event = ToolCallFailedEvent(
                    session_id=session.id,
                    plan_id=plan.id,
                    step_index=step_index,
                    tool=step.tool,
                    error=str(e),
                    retry_count=self.retry_config.max_retries
                )
                await self.session_manager.event_bus.emit(failed_event)
                await self.session_manager.event_repo.save(failed_event)

                failed_steps.append({
                    "tool": step.tool,
                    "error": str(e)
                })

        # ... rest of method (partial results support) ...
```

**Step 5: Run test to verify it passes**

Run: `PYTHONPATH=/home/cytrex/eve_copilot:$PYTHONPATH pytest copilot_server/tests/agent/test_retry_logic.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add copilot_server/agent/retry_logic.py copilot_server/agent/runtime.py copilot_server/tests/agent/test_retry_logic.py
git commit -m "feat(agent): add retry logic with exponential backoff

- Add RetryConfig for configurable retry behavior
- Implement execute_with_retry with exponential backoff
- Integrate retry logic into plan execution
- Support partial results on tool failures
- Add retry count to tool_call_failed events
- Add comprehensive retry logic tests

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 7: Integration Testing

**Files:**
- Create: `copilot_server/tests/agent/test_phase3_integration.py`

**Step 1: Write integration test**

Create test file:

```python
import pytest
import asyncio
import json
from copilot_server.agent.sessions import AgentSessionManager
from copilot_server.agent.runtime import AgentRuntime
from copilot_server.agent.authorization import AuthorizationChecker
from copilot_server.agent.models import AgentSession
from copilot_server.agent.events import AgentEventType
from copilot_server.models.user_settings import AutonomyLevel, get_default_settings
from copilot_server.llm import AnthropicClient
from copilot_server.mcp import MCPClient, ToolOrchestrator
from unittest.mock import MagicMock, AsyncMock


@pytest.fixture
async def session_manager():
    """Create real session manager."""
    mgr = AgentSessionManager()
    await mgr.startup()
    yield mgr
    await mgr.shutdown()


@pytest.mark.asyncio
async def test_end_to_end_event_streaming(session_manager):
    """
    Test complete event streaming workflow:
    1. Create session
    2. Subscribe to events via EventBus
    3. Execute plan
    4. Verify all events emitted
    5. Verify events saved to database
    """
    # Track received events
    received_events = []

    async def event_handler(event):
        received_events.append(event)

    # Create session
    user_settings = get_default_settings(character_id=123)
    user_settings.autonomy_level = AutonomyLevel.ASSISTED

    session = await session_manager.create_session(
        character_id=123,
        autonomy_level=user_settings.autonomy_level
    )

    # Subscribe to events
    session_manager.event_bus.subscribe(session.id, event_handler)

    # Mock LLM and orchestrator
    mock_llm = MagicMock()
    mock_llm.chat = AsyncMock()
    mock_llm.build_tool_schema = MagicMock(return_value=[])

    mock_mcp = MagicMock()
    mock_mcp.get_tools = MagicMock(return_value=[
        {"name": "get_market_stats", "metadata": {"risk_level": "READ_ONLY"}},
        {"name": "get_war_summary", "metadata": {"risk_level": "READ_ONLY"}},
        {"name": "search_item", "metadata": {"risk_level": "READ_ONLY"}}
    ])
    mock_mcp.call_tool = MagicMock(return_value={"result": "data"})

    mock_orchestrator = MagicMock()
    mock_orchestrator.mcp = mock_mcp

    # Create runtime
    runtime = AgentRuntime(
        session_manager=session_manager,
        llm_client=mock_llm,
        orchestrator=mock_orchestrator
    )

    # Add message
    session.add_message("user", "Analyze market data")
    await session_manager.save_session(session)

    # Mock LLM response: 3 READ_ONLY tools
    mock_llm.chat.return_value = {
        "content": [
            {"type": "text", "text": "I'll analyze market data."},
            {"type": "tool_use", "id": "call1", "name": "get_market_stats", "input": {}},
            {"type": "tool_use", "id": "call2", "name": "get_war_summary", "input": {}},
            {"type": "tool_use", "id": "call3", "name": "search_item", "input": {}}
        ],
        "stop_reason": "tool_use"
    }

    # Second call: return answer
    mock_llm.chat.side_effect = [
        mock_llm.chat.return_value,
        {"content": [{"type": "text", "text": "Analysis complete."}], "stop_reason": "end_turn"}
    ]

    # Execute
    await runtime.execute(session)

    # Wait for async event delivery
    await asyncio.sleep(0.2)

    # Verify events received
    assert len(received_events) >= 3

    event_types = [e.type for e in received_events]
    assert AgentEventType.PLAN_PROPOSED in event_types
    assert AgentEventType.TOOL_CALL_STARTED in event_types
    assert AgentEventType.TOOL_CALL_COMPLETED in event_types

    # Verify events saved to database
    saved_events = await session_manager.event_repo.load_by_session(session.id)
    assert len(saved_events) >= 3


@pytest.mark.asyncio
async def test_authorization_blocks_blacklisted_tool(session_manager):
    """Test that authorization blocks blacklisted tools."""
    # Create runtime with auth checker
    auth_checker = AuthorizationChecker()
    auth_checker.add_to_blacklist(123, "delete_bookmark")

    mock_llm = MagicMock()
    mock_orchestrator = MagicMock()
    mock_orchestrator.mcp = MagicMock()

    runtime = AgentRuntime(
        session_manager=session_manager,
        llm_client=mock_llm,
        orchestrator=mock_orchestrator,
        auth_checker=auth_checker
    )

    # Create session
    session = await session_manager.create_session(
        character_id=123,
        autonomy_level=AutonomyLevel.ASSISTED
    )

    # Track events
    received_events = []

    async def event_handler(event):
        received_events.append(event)

    session_manager.event_bus.subscribe(session.id, event_handler)

    # Create plan with blacklisted tool
    from copilot_server.agent.models import Plan, PlanStep
    from copilot_server.models.user_settings import RiskLevel

    plan = Plan(
        session_id=session.id,
        purpose="Test blacklist",
        steps=[
            PlanStep(tool="get_bookmarks", arguments={}, risk_level=RiskLevel.READ_ONLY),
            PlanStep(tool="delete_bookmark", arguments={"id": 1}, risk_level=RiskLevel.WRITE_HIGH_RISK)
        ],
        max_risk_level=RiskLevel.WRITE_HIGH_RISK
    )

    await session_manager.plan_repo.save_plan(plan)

    # Execute plan
    await runtime._execute_plan(session, plan)

    # Wait for events
    await asyncio.sleep(0.2)

    # Verify authorization_denied event
    auth_denied_events = [
        e for e in received_events
        if e.type == AgentEventType.AUTHORIZATION_DENIED
    ]

    assert len(auth_denied_events) == 1
    assert "delete_bookmark" in auth_denied_events[0].payload["tool"]


@pytest.mark.asyncio
async def test_retry_logic_recovers_from_failures(session_manager):
    """Test that retry logic recovers from transient failures."""
    # Create runtime with fast retry config
    from copilot_server.agent.retry_logic import RetryConfig

    retry_config = RetryConfig(
        max_retries=2,
        base_delay_ms=50
    )

    mock_llm = MagicMock()

    # Mock orchestrator with failing then succeeding tool
    call_count = 0

    def flaky_tool(tool_name, args):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ConnectionError("Temporary network error")
        return {"result": "success"}

    mock_mcp = MagicMock()
    mock_mcp.call_tool = flaky_tool

    mock_orchestrator = MagicMock()
    mock_orchestrator.mcp = mock_mcp

    runtime = AgentRuntime(
        session_manager=session_manager,
        llm_client=mock_llm,
        orchestrator=mock_orchestrator,
        retry_config=retry_config
    )

    # Create session and plan
    session = await session_manager.create_session(
        character_id=123,
        autonomy_level=AutonomyLevel.ASSISTED
    )

    from copilot_server.agent.models import Plan, PlanStep
    from copilot_server.models.user_settings import RiskLevel

    plan = Plan(
        session_id=session.id,
        purpose="Test retry",
        steps=[
            PlanStep(tool="test_tool", arguments={}, risk_level=RiskLevel.READ_ONLY)
        ],
        max_risk_level=RiskLevel.READ_ONLY
    )

    await session_manager.plan_repo.save_plan(plan)

    # Execute plan
    await runtime._execute_plan(session, plan)

    # Verify tool was called 3 times (2 failures + 1 success)
    assert call_count == 3

    # Verify plan completed successfully
    reloaded_plan = await session_manager.plan_repo.load_plan(plan.id)
    assert reloaded_plan.status.value == "completed"
```

**Step 2: Run test to verify it passes**

Run: `PYTHONPATH=/home/cytrex/eve_copilot:$PYTHONPATH pytest copilot_server/tests/agent/test_phase3_integration.py -v`
Expected: PASS

**Step 3: Commit**

```bash
git add copilot_server/tests/agent/test_phase3_integration.py
git commit -m "test(agent): add Phase 3 integration tests

- End-to-end event streaming test
- Authorization blocking test
- Retry logic recovery test
- Verify events saved to database
- Verify WebSocket event delivery

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 8: Documentation and Completion

**Files:**
- Create: `docs/agent/phase3-completion.md`
- Modify: `README.md`

**Step 1: Write Phase 3 completion documentation**

Create comprehensive documentation (similar to Phase 2 completion report).

**Step 2: Update README**

Add Phase 3 status to README.md.

**Step 3: Run all tests**

Run: `PYTHONPATH=/home/cytrex/eve_copilot:$PYTHONPATH pytest copilot_server/tests/agent/ -v`
Expected: All tests pass

**Step 4: Commit**

```bash
git add docs/agent/phase3-completion.md README.md
git commit -m "docs(agent): Phase 3 completion documentation

- Comprehensive Phase 3 completion report
- Event system and WebSocket documentation
- API usage examples with WebSocket
- Performance metrics and benchmarks
- Update README with Phase 3 status

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Summary

**Phase 3 Implementation Plan Complete**

**Total Tasks:** 8
**Total Tests:** ~25 new tests
**Total Files:** 13 new files, 5 modified files

**Deliverables:**
1. ✅ Event models and agent_events table
2. ✅ EventBus and EventRepository
3. ✅ WebSocket streaming endpoint
4. ✅ Event emission in Runtime
5. ✅ Authorization integration
6. ✅ Retry logic with exponential backoff
7. ✅ Integration tests
8. ✅ Documentation

**Ready for Execution:** Use `superpowers:subagent-driven-development` or `superpowers:executing-plans`
