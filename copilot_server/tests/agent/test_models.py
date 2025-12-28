import pytest
from datetime import datetime
from copilot_server.agent.models import (
    SessionStatus,
    AgentSession,
    AgentMessage
)
from copilot_server.models.user_settings import AutonomyLevel

def test_session_status_enum():
    """Test SessionStatus enum values."""
    assert SessionStatus.IDLE == "idle"
    assert SessionStatus.PLANNING == "planning"
    assert SessionStatus.EXECUTING == "executing"
    assert SessionStatus.COMPLETED == "completed"

def test_agent_session_creation():
    """Test AgentSession model creation."""
    session = AgentSession(
        id="sess-test-123",
        character_id=1117367444,
        autonomy_level=AutonomyLevel.RECOMMENDATIONS,
        status=SessionStatus.IDLE
    )

    assert session.id == "sess-test-123"
    assert session.character_id == 1117367444
    assert session.autonomy_level == AutonomyLevel.RECOMMENDATIONS
    assert session.status == SessionStatus.IDLE
    assert session.messages == []
    assert session.queued_message is None

def test_agent_message_creation():
    """Test AgentMessage model creation."""
    msg = AgentMessage(
        session_id="sess-test-123",
        role="user",
        content="What's profitable in Jita?"
    )

    assert msg.session_id == "sess-test-123"
    assert msg.role == "user"
    assert msg.content == "What's profitable in Jita?"
    assert isinstance(msg.timestamp, datetime)
