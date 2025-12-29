"""
Approval Manager
Determines if tool execution requires user approval based on autonomy level.
"""

from typing import Dict, Any, Optional, List, Union
from ..models.user_settings import AutonomyLevel, RiskLevel as UserRiskLevel
from ..governance.tool_classification import RiskLevel as ToolRiskLevel


class ApprovalManager:
    """Manages approval requirements for tool execution."""

    # Autonomy level to max auto-executable risk level mapping (using UserRiskLevel)
    AUTO_EXECUTE_THRESHOLDS = {
        AutonomyLevel.READ_ONLY: UserRiskLevel.READ_ONLY,           # L0: Only READ_ONLY
        AutonomyLevel.RECOMMENDATIONS: UserRiskLevel.WRITE_LOW_RISK, # L1: READ_ONLY + WRITE_LOW_RISK
        AutonomyLevel.ASSISTED: UserRiskLevel.WRITE_HIGH_RISK,      # L2: READ_ONLY + WRITE_LOW_RISK + WRITE_HIGH_RISK
        AutonomyLevel.SUPERVISED: UserRiskLevel.CRITICAL            # L3: All (including CRITICAL)
    }

    # Risk level ordering (lowest to highest) using UserRiskLevel
    RISK_ORDER = [
        UserRiskLevel.READ_ONLY,
        UserRiskLevel.WRITE_LOW_RISK,
        UserRiskLevel.WRITE_HIGH_RISK,
        UserRiskLevel.CRITICAL
    ]

    # Mapping from tool_classification.RiskLevel to user_settings.RiskLevel
    RISK_LEVEL_MAPPING = {
        ToolRiskLevel.READ_ONLY: UserRiskLevel.READ_ONLY,
        ToolRiskLevel.WRITE_LOW_RISK: UserRiskLevel.WRITE_LOW_RISK,
        ToolRiskLevel.WRITE_HIGH_RISK: UserRiskLevel.WRITE_HIGH_RISK,
        ToolRiskLevel.CRITICAL: UserRiskLevel.CRITICAL
    }

    def __init__(self, autonomy_level: AutonomyLevel):
        """
        Initialize approval manager.

        Args:
            autonomy_level: User's autonomy level
        """
        self.autonomy_level = autonomy_level
        self.threshold = self.AUTO_EXECUTE_THRESHOLDS[autonomy_level]

    def _normalize_risk_level(self, risk_level: Union[UserRiskLevel, ToolRiskLevel]) -> UserRiskLevel:
        """
        Normalize risk level to UserRiskLevel.

        Args:
            risk_level: Risk level (either UserRiskLevel or ToolRiskLevel)

        Returns:
            Normalized UserRiskLevel
        """
        if isinstance(risk_level, UserRiskLevel):
            return risk_level
        elif isinstance(risk_level, ToolRiskLevel):
            return self.RISK_LEVEL_MAPPING[risk_level]
        else:
            # If it's neither, try to match by value
            if hasattr(risk_level, 'value'):
                # Try to find matching UserRiskLevel by value
                for user_rl in UserRiskLevel:
                    if user_rl.value == risk_level.value:
                        return user_rl
            raise ValueError(f"Cannot normalize risk level: {risk_level}")

    def requires_approval(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        risk_level: Union[UserRiskLevel, ToolRiskLevel]
    ) -> bool:
        """
        Check if tool execution requires approval.

        Args:
            tool_name: Name of tool
            arguments: Tool arguments
            risk_level: Tool's risk level (either UserRiskLevel or ToolRiskLevel)

        Returns:
            True if approval required, False if auto-executable
        """
        # Normalize risk level to UserRiskLevel
        normalized_risk = self._normalize_risk_level(risk_level)

        # Risk levels are ordered: READ_ONLY < WRITE_LOW_RISK < WRITE_HIGH_RISK < CRITICAL
        # Auto-execute if risk <= threshold
        tool_risk_index = self.RISK_ORDER.index(normalized_risk)
        threshold_index = self.RISK_ORDER.index(self.threshold)

        # Requires approval if risk exceeds threshold
        return tool_risk_index > threshold_index

    def create_approval_plan(
        self,
        session_id: str,
        tool_calls: List[Dict[str, Any]],
        purpose: str
    ) -> Optional[Dict[str, Any]]:
        """
        Create a plan requiring approval.

        Args:
            session_id: Session ID
            tool_calls: List of tool calls (each with 'name', 'input', 'id', 'risk_level')
            purpose: Purpose of plan

        Returns:
            Plan dictionary or None
        """
        from .models import Plan, PlanStep

        steps = []
        max_risk = UserRiskLevel.READ_ONLY

        for tc in tool_calls:
            # Normalize risk level
            raw_risk = tc.get("risk_level", UserRiskLevel.WRITE_HIGH_RISK)
            normalized_risk = self._normalize_risk_level(raw_risk)

            step = PlanStep(
                tool=tc["name"],
                arguments=tc["input"],
                risk_level=normalized_risk
            )
            steps.append(step)

            # Track highest risk
            if self.RISK_ORDER.index(step.risk_level) > self.RISK_ORDER.index(max_risk):
                max_risk = step.risk_level

        plan = Plan(
            session_id=session_id,
            purpose=purpose,
            steps=steps,
            max_risk_level=max_risk,
            auto_executing=False
        )

        return plan

    def get_risk_summary(self, tool_calls: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get risk summary for a list of tool calls.

        Args:
            tool_calls: List of tool calls with risk_level

        Returns:
            Dictionary with risk summary
        """
        risk_counts = {
            UserRiskLevel.READ_ONLY: 0,
            UserRiskLevel.WRITE_LOW_RISK: 0,
            UserRiskLevel.WRITE_HIGH_RISK: 0,
            UserRiskLevel.CRITICAL: 0
        }

        max_risk = UserRiskLevel.READ_ONLY

        for tc in tool_calls:
            # Normalize risk level
            raw_risk = tc.get("risk_level", UserRiskLevel.WRITE_HIGH_RISK)
            normalized_risk = self._normalize_risk_level(raw_risk)
            risk_counts[normalized_risk] += 1

            # Track highest risk
            if self.RISK_ORDER.index(normalized_risk) > self.RISK_ORDER.index(max_risk):
                max_risk = normalized_risk

        return {
            "max_risk_level": max_risk,
            "risk_counts": {k.value: v for k, v in risk_counts.items() if v > 0},
            "total_tools": len(tool_calls),
            "requires_approval": self.requires_approval("", {}, max_risk)
        }
