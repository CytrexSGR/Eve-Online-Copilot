"""
User Settings and Autonomy Configuration
Defines user preferences for AI agent behavior.
"""

from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, ConfigDict


class RiskLevel(str, Enum):
    """
    Risk level for MCP tools.

    Levels:
        READ_ONLY: Analytics, market data, no state changes
        WRITE_LOW_RISK: Shopping lists, bookmarks, non-critical writes
        WRITE_HIGH_RISK: Market orders, contract creation
        CRITICAL: Unknown tools, requires explicit approval
    """
    READ_ONLY = "READ_ONLY"
    WRITE_LOW_RISK = "WRITE_LOW_RISK"
    WRITE_HIGH_RISK = "WRITE_HIGH_RISK"
    CRITICAL = "CRITICAL"


class AutonomyLevel(Enum):
    """
    User's preferred autonomy level for AI agent.

    Levels:
        READ_ONLY (0): Only analytics, no writes
        RECOMMENDATIONS (1): Suggest actions, user decides (DEFAULT)
        ASSISTED (2): Prepare actions, ask confirmation
        SUPERVISED (3): Auto-execute within limits (future)
    """
    READ_ONLY = 0
    RECOMMENDATIONS = 1
    ASSISTED = 2
    SUPERVISED = 3


class UserSettings(BaseModel):
    """
    User preferences for AI behavior.

    Attributes:
        character_id: EVE character ID
        autonomy_level: Preferred autonomy level (default: RECOMMENDATIONS)
        require_confirmation: Ask before WRITE_HIGH_RISK tools (default: True)
        budget_limit_isk: Max ISK for automated actions (future trading)
        allowed_regions: Restrict operations to specific regions
        blocked_tools: User-blacklisted tools
    """

    model_config = ConfigDict(use_enum_values=False)

    character_id: int
    autonomy_level: AutonomyLevel = AutonomyLevel.RECOMMENDATIONS
    require_confirmation: bool = True
    budget_limit_isk: Optional[float] = None
    allowed_regions: Optional[List[int]] = None
    blocked_tools: List[str] = Field(default_factory=list)

    @field_validator('budget_limit_isk')
    @classmethod
    def validate_budget(cls, v):
        """Ensure budget is positive if set."""
        if v is not None and v <= 0:
            raise ValueError("Budget limit must be positive")
        return v


def get_default_settings(character_id: int) -> UserSettings:
    """
    Get default safe settings for new user.

    Args:
        character_id: EVE character ID

    Returns:
        UserSettings with safe defaults (L1, confirmations enabled)
    """
    return UserSettings(
        character_id=character_id,
        autonomy_level=AutonomyLevel.RECOMMENDATIONS,
        require_confirmation=True
    )
