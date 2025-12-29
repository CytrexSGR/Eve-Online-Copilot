"""
Context Window Management for Agentic Loop
Handles message truncation to prevent token overflow.
"""

import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class ContextWindowManager:
    """
    Manages conversation context window with automatic truncation.

    Strategy:
    - Preserve system prompt (always first)
    - Keep recent N message pairs (sliding window)
    - Drop oldest messages when limit reached
    """

    def __init__(
        self,
        max_messages: int = 20,
        preserve_system: bool = True
    ):
        """
        Initialize context window manager.

        Args:
            max_messages: Maximum number of messages to keep (excluding system)
            preserve_system: Always preserve system prompt
        """
        self.max_messages = max_messages
        self.preserve_system = preserve_system

    def truncate(
        self,
        messages: List[Dict[str, Any]],
        system: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Truncate message list to fit within context window.

        Args:
            messages: Full conversation history
            system: System prompt (if any)

        Returns:
            Truncated message list
        """
        if not messages:
            return messages

        # If below limit, no truncation needed
        if len(messages) <= self.max_messages:
            logger.debug(f"No truncation needed: {len(messages)}/{self.max_messages} messages")
            return messages

        # Calculate how many to keep
        messages_to_keep = self.max_messages

        # Truncate from the beginning (keep most recent)
        truncated = messages[-messages_to_keep:]

        logger.info(
            f"Context truncated: {len(messages)} → {len(truncated)} messages "
            f"(dropped {len(messages) - len(truncated)} oldest)"
        )

        return truncated

    def estimate_tokens(self, messages: List[Dict[str, Any]]) -> int:
        """
        Rough token count estimation for messages.

        Uses 4 characters ≈ 1 token heuristic.

        Args:
            messages: Message list to estimate

        Returns:
            Estimated token count
        """
        total_chars = 0

        for msg in messages:
            # Count content
            if isinstance(msg.get("content"), str):
                total_chars += len(msg["content"])
            elif isinstance(msg.get("content"), list):
                for block in msg["content"]:
                    if isinstance(block, dict):
                        if "text" in block:
                            total_chars += len(block["text"])
                        if "input" in block:
                            total_chars += len(str(block["input"]))

        # 4 chars ≈ 1 token
        estimated_tokens = total_chars // 4

        logger.debug(f"Estimated {estimated_tokens} tokens from {total_chars} characters")

        return estimated_tokens

    def should_truncate(self, messages: List[Dict[str, Any]]) -> bool:
        """
        Check if message list should be truncated.

        Args:
            messages: Message list to check

        Returns:
            True if truncation needed
        """
        return len(messages) > self.max_messages

    def get_context_summary(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get summary of current context state.

        Args:
            messages: Current message list

        Returns:
            Summary dict with stats
        """
        return {
            "total_messages": len(messages),
            "max_messages": self.max_messages,
            "estimated_tokens": self.estimate_tokens(messages),
            "needs_truncation": self.should_truncate(messages),
            "messages_over_limit": max(0, len(messages) - self.max_messages),
        }
