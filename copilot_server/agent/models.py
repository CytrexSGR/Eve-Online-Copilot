"""
Agent Runtime Data Models
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, ConfigDict

from ..models.user_settings import AutonomyLevel


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
