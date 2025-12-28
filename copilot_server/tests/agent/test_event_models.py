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
