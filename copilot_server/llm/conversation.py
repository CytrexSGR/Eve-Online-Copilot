"""
Conversation Management
Handles conversation history, context, and memory.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
import logging

from ..config import MAX_CONVERSATION_HISTORY, CONTEXT_WINDOW_TOKENS

logger = logging.getLogger(__name__)


class Conversation:
    """Represents a single conversation with context and history."""

    def __init__(
        self,
        session_id: Optional[str] = None,
        character_id: Optional[int] = None,
        region_id: int = 10000002  # Default: Jita
    ):
        """
        Initialize conversation.

        Args:
            session_id: Unique session identifier
            character_id: Active EVE character ID
            region_id: Active region ID (default: Jita)
        """
        self.session_id = session_id or str(uuid.uuid4())
        self.character_id = character_id
        self.region_id = region_id
        self.messages: List[Dict[str, Any]] = []
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.metadata: Dict[str, Any] = {}

    def add_message(
        self,
        role: str,
        content: Any,
        tool_calls: Optional[List[Dict[str, Any]]] = None
    ) -> None:
        """
        Add message to conversation.

        Args:
            role: Message role (user, assistant, tool)
            content: Message content
            tool_calls: Tool calls made in this message
        """
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        }

        if tool_calls:
            message["tool_calls"] = tool_calls

        self.messages.append(message)
        self.updated_at = datetime.utcnow()

        # Trim history if too long
        if len(self.messages) > MAX_CONVERSATION_HISTORY:
            # Keep system messages and most recent messages
            system_messages = [m for m in self.messages if m.get("role") == "system"]
            recent_messages = self.messages[-MAX_CONVERSATION_HISTORY:]
            self.messages = system_messages + recent_messages

    def get_messages_for_api(self) -> List[Dict[str, Any]]:
        """
        Get messages formatted for Claude API.

        Returns:
            Messages in Claude format
        """
        # Filter out system role messages (those go in system parameter)
        api_messages = []

        for msg in self.messages:
            if msg["role"] in ["user", "assistant"]:
                api_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })

        return api_messages

    def set_character(self, character_id: int) -> None:
        """Set active character."""
        self.character_id = character_id
        self.updated_at = datetime.utcnow()

    def set_region(self, region_id: int) -> None:
        """Set active region."""
        self.region_id = region_id
        self.updated_at = datetime.utcnow()

    def get_context_summary(self) -> str:
        """
        Get summary of current context.

        Returns:
            Context summary string
        """
        context_parts = []

        if self.character_id:
            context_parts.append(f"Character ID: {self.character_id}")

        context_parts.append(f"Region ID: {self.region_id}")
        context_parts.append(f"Messages: {len(self.messages)}")
        context_parts.append(f"Session: {self.session_id[:8]}")

        return " | ".join(context_parts)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "session_id": self.session_id,
            "character_id": self.character_id,
            "region_id": self.region_id,
            "messages": self.messages,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Conversation":
        """Create conversation from dictionary."""
        conv = cls(
            session_id=data["session_id"],
            character_id=data.get("character_id"),
            region_id=data.get("region_id", 10000002)
        )
        conv.messages = data.get("messages", [])
        conv.created_at = datetime.fromisoformat(data["created_at"])
        conv.updated_at = datetime.fromisoformat(data["updated_at"])
        conv.metadata = data.get("metadata", {})
        return conv


class ConversationManager:
    """Manages multiple conversations with persistence."""

    def __init__(self):
        """Initialize conversation manager."""
        self.conversations: Dict[str, Conversation] = {}
        logger.info("ConversationManager initialized")

    def create_conversation(
        self,
        character_id: Optional[int] = None,
        region_id: int = 10000002
    ) -> Conversation:
        """
        Create new conversation.

        Args:
            character_id: Active character ID
            region_id: Active region ID

        Returns:
            New conversation instance
        """
        conv = Conversation(
            character_id=character_id,
            region_id=region_id
        )
        self.conversations[conv.session_id] = conv
        logger.info(f"Created conversation: {conv.session_id}")
        return conv

    def get_conversation(self, session_id: str) -> Optional[Conversation]:
        """
        Get conversation by session ID.

        Args:
            session_id: Session identifier

        Returns:
            Conversation instance or None
        """
        return self.conversations.get(session_id)

    def list_conversations(self) -> List[Dict[str, Any]]:
        """
        List all conversations with metadata.

        Returns:
            List of conversation summaries
        """
        summaries = []
        for conv in self.conversations.values():
            summaries.append({
                "session_id": conv.session_id,
                "character_id": conv.character_id,
                "region_id": conv.region_id,
                "message_count": len(conv.messages),
                "created_at": conv.created_at.isoformat(),
                "updated_at": conv.updated_at.isoformat()
            })
        return summaries

    def delete_conversation(self, session_id: str) -> bool:
        """
        Delete conversation.

        Args:
            session_id: Session to delete

        Returns:
            True if deleted, False if not found
        """
        if session_id in self.conversations:
            del self.conversations[session_id]
            logger.info(f"Deleted conversation: {session_id}")
            return True
        return False

    def cleanup_old_conversations(self, max_age_hours: int = 24) -> int:
        """
        Clean up old inactive conversations.

        Args:
            max_age_hours: Maximum age in hours

        Returns:
            Number of conversations deleted
        """
        now = datetime.utcnow()
        to_delete = []

        for session_id, conv in self.conversations.items():
            age_hours = (now - conv.updated_at).total_seconds() / 3600
            if age_hours > max_age_hours:
                to_delete.append(session_id)

        for session_id in to_delete:
            del self.conversations[session_id]

        if to_delete:
            logger.info(f"Cleaned up {len(to_delete)} old conversations")

        return len(to_delete)
