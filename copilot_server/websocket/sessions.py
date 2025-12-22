"""
Session Management
Handles user sessions and state.
"""

from typing import Dict, Optional
from datetime import datetime
import uuid
import logging

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages user sessions."""

    def __init__(self):
        """Initialize session manager."""
        self.sessions: Dict[str, Dict] = {}

    def create_session(
        self,
        character_id: Optional[int] = None,
        region_id: int = 10000002
    ) -> str:
        """
        Create new session.

        Args:
            character_id: Active character ID
            region_id: Active region ID

        Returns:
            Session ID
        """
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = {
            "session_id": session_id,
            "character_id": character_id,
            "region_id": region_id,
            "created_at": datetime.utcnow(),
            "last_activity": datetime.utcnow(),
            "metadata": {}
        }

        logger.info(f"Created session: {session_id}")
        return session_id

    def get_session(self, session_id: str) -> Optional[Dict]:
        """
        Get session data.

        Args:
            session_id: Session identifier

        Returns:
            Session data or None
        """
        return self.sessions.get(session_id)

    def update_activity(self, session_id: str):
        """
        Update session last activity.

        Args:
            session_id: Session identifier
        """
        if session_id in self.sessions:
            self.sessions[session_id]["last_activity"] = datetime.utcnow()

    def set_character(self, session_id: str, character_id: int):
        """
        Set active character for session.

        Args:
            session_id: Session identifier
            character_id: Character ID
        """
        if session_id in self.sessions:
            self.sessions[session_id]["character_id"] = character_id
            self.update_activity(session_id)

    def set_region(self, session_id: str, region_id: int):
        """
        Set active region for session.

        Args:
            session_id: Session identifier
            region_id: Region ID
        """
        if session_id in self.sessions:
            self.sessions[session_id]["region_id"] = region_id
            self.update_activity(session_id)

    def delete_session(self, session_id: str) -> bool:
        """
        Delete session.

        Args:
            session_id: Session to delete

        Returns:
            True if deleted
        """
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"Deleted session: {session_id}")
            return True
        return False

    def cleanup_inactive(self, max_age_hours: int = 24) -> int:
        """
        Clean up inactive sessions.

        Args:
            max_age_hours: Maximum age in hours

        Returns:
            Number of sessions deleted
        """
        now = datetime.utcnow()
        to_delete = []

        for session_id, session in self.sessions.items():
            age_hours = (now - session["last_activity"]).total_seconds() / 3600
            if age_hours > max_age_hours:
                to_delete.append(session_id)

        for session_id in to_delete:
            del self.sessions[session_id]

        if to_delete:
            logger.info(f"Cleaned up {len(to_delete)} inactive sessions")

        return len(to_delete)
