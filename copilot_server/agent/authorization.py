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
