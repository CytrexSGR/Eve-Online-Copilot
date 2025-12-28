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
