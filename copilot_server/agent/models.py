"""
Agent Runtime Data Models
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, ConfigDict

from ..models.user_settings import AutonomyLevel, RiskLevel


class PlanStatus(str, Enum):
    """Plan lifecycle status."""
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"


class PlanStep(BaseModel):
    """Individual step in execution plan."""
    model_config = ConfigDict(use_enum_values=False)

    tool: str
    arguments: Dict[str, Any]
    risk_level: RiskLevel = RiskLevel.CRITICAL  # Default to safest


class Plan(BaseModel):
    """Multi-tool execution plan."""
    model_config = ConfigDict(use_enum_values=False)

    id: str = Field(default_factory=lambda: f"plan-{uuid4().hex[:12]}")
    session_id: str
    purpose: str
    steps: List[PlanStep]
    max_risk_level: RiskLevel = RiskLevel.CRITICAL
    status: PlanStatus = PlanStatus.PROPOSED
    auto_executing: bool = False
    created_at: datetime = Field(default_factory=datetime.now)
    approved_at: Optional[datetime] = None
    executed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None

    def to_db_dict(self) -> Dict[str, Any]:
        """Convert to database format."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "purpose": self.purpose,
            "plan_data": {
                "steps": [
                    {
                        "tool": step.tool,
                        "arguments": step.arguments,
                        "risk_level": step.risk_level.value
                    }
                    for step in self.steps
                ],
                "max_risk_level": self.max_risk_level.value
            },
            "status": self.status.value,
            "auto_executing": self.auto_executing,
            "created_at": self.created_at,
            "approved_at": self.approved_at,
            "executed_at": self.executed_at,
            "completed_at": self.completed_at,
            "duration_ms": self.duration_ms
        }


class SessionStatus(str, Enum):
    """Agent session status."""
    IDLE = "idle"
    PLANNING = "planning"
    EXECUTING = "executing"
    EXECUTING_QUEUED = "executing_queued"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    COMPLETED_WITH_ERRORS = "completed_with_errors"
    ERROR = "error"
    INTERRUPTED = "interrupted"


class AgentMessage(BaseModel):
    """Conversation message."""
    model_config = ConfigDict(use_enum_values=False)

    session_id: str
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)


class AgentSession(BaseModel):
    """Agent session state."""
    model_config = ConfigDict(use_enum_values=False)

    id: str = Field(default_factory=lambda: f"sess-{uuid4().hex[:12]}")
    character_id: int
    autonomy_level: AutonomyLevel = AutonomyLevel.RECOMMENDATIONS
    status: SessionStatus = SessionStatus.IDLE
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    last_activity: datetime = Field(default_factory=datetime.now)
    archived: bool = False

    # Runtime state
    messages: List[AgentMessage] = Field(default_factory=list)
    queued_message: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)

    def add_message(self, role: str, content: str) -> AgentMessage:
        """Add message to conversation."""
        msg = AgentMessage(
            session_id=self.id,
            role=role,
            content=content
        )
        self.messages.append(msg)
        self.last_activity = datetime.now()
        self.updated_at = datetime.now()
        return msg

    def get_messages_for_api(self) -> List[Dict[str, Any]]:
        """
        Convert session messages to Anthropic API format.

        Returns:
            List of message dicts with role and content
        """
        return [
            {
                "role": msg.role,
                "content": msg.content
            }
            for msg in self.messages
        ]
