# copilot_server/governance/authorization.py

"""
Authorization Middleware
Server-side enforcement of tool access policies.
"""

from typing import Dict, Any, Tuple
import logging

from .tool_classification import RiskLevel, get_tool_risk_level
from ..models.user_settings import UserSettings, AutonomyLevel

logger = logging.getLogger(__name__)


class AuthorizationChecker:
    """
    Checks if user is authorized to execute a tool.

    Authorization Rules:
        - L0 (READ_ONLY): Only READ_ONLY tools
        - L1 (RECOMMENDATIONS): READ_ONLY + WRITE_LOW_RISK
        - L2 (ASSISTED): L1 + WRITE_HIGH_RISK (with confirmation)
        - L3 (SUPERVISED): L2 + CRITICAL (future, with budget limits)

    User-blacklisted tools are ALWAYS blocked.
    """

    def __init__(self, user_settings: UserSettings):
        """
        Initialize authorization checker.

        Args:
            user_settings: User's autonomy preferences
        """
        self.settings = user_settings

    def is_tool_allowed(self, tool_name: str, arguments: Dict[str, Any]) -> bool:
        """
        Quick check if tool is allowed (bool only).

        Args:
            tool_name: Name of MCP tool
            arguments: Tool arguments

        Returns:
            True if allowed, False otherwise
        """
        allowed, _ = self.check_authorization(tool_name, arguments)
        return allowed

    def check_authorization(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """
        Full authorization check with denial reason.

        Args:
            tool_name: Name of MCP tool
            arguments: Tool arguments

        Returns:
            Tuple of (allowed: bool, reason: str)
            - If allowed: (True, "")
            - If denied: (False, "Reason for denial")
        """
        # 1. Check user blacklist
        if tool_name in self.settings.blocked_tools:
            logger.warning(
                f"Tool '{tool_name}' blocked by user {self.settings.character_id}"
            )
            return (False, f"Tool '{tool_name}' is in your blacklist")

        # 2. Get tool risk level
        try:
            risk_level = get_tool_risk_level(tool_name)
        except ValueError as e:
            logger.error(f"Unknown tool '{tool_name}': {e}")
            return (False, f"Unknown tool: {tool_name}")

        # 3. Check against user's autonomy level
        user_level = self.settings.autonomy_level

        if risk_level == RiskLevel.READ_ONLY:
            # Always allowed
            return (True, "")

        elif risk_level == RiskLevel.WRITE_LOW_RISK:
            if user_level.value >= AutonomyLevel.RECOMMENDATIONS.value:
                return (True, "")
            else:
                return (
                    False,
                    f"Tool requires autonomy level RECOMMENDATIONS (L1) or higher. "
                    f"Current level: {user_level.name}"
                )

        elif risk_level == RiskLevel.WRITE_HIGH_RISK:
            if user_level.value >= AutonomyLevel.ASSISTED.value:
                # L2+ allowed (confirmation handled separately)
                return (True, "")
            else:
                return (
                    False,
                    f"Tool requires autonomy level ASSISTED (L2) or higher. "
                    f"Current level: {user_level.name}"
                )

        elif risk_level == RiskLevel.CRITICAL:
            # Not implemented yet
            return (
                False,
                f"CRITICAL tools not yet supported. "
                f"Tool '{tool_name}' will be available in future update."
            )

        # Should not reach here
        return (False, f"Unknown risk level for tool '{tool_name}'")
