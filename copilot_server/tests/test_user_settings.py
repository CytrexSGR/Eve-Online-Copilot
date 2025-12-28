# copilot_server/tests/test_user_settings.py

import pytest
from copilot_server.models.user_settings import (
    AutonomyLevel,
    UserSettings,
    get_default_settings
)


def test_autonomy_level_enum():
    """Test autonomy level values."""
    assert AutonomyLevel.READ_ONLY.value == 0
    assert AutonomyLevel.RECOMMENDATIONS.value == 1
    assert AutonomyLevel.ASSISTED.value == 2
    assert AutonomyLevel.SUPERVISED.value == 3


def test_default_user_settings():
    """Default settings should be safe (L1 with confirmations)."""
    settings = get_default_settings(character_id=12345)

    assert settings.character_id == 12345
    assert settings.autonomy_level == AutonomyLevel.RECOMMENDATIONS
    assert settings.require_confirmation is True
    assert settings.budget_limit_isk is None
    assert settings.allowed_regions is None
    assert settings.blocked_tools == []


def test_user_can_increase_autonomy():
    """User can opt-in to higher autonomy."""
    settings = UserSettings(
        character_id=12345,
        autonomy_level=AutonomyLevel.ASSISTED,
        require_confirmation=False
    )

    assert settings.autonomy_level == AutonomyLevel.ASSISTED
    assert settings.require_confirmation is False


def test_user_can_block_tools():
    """User can blacklist specific tools."""
    settings = UserSettings(
        character_id=12345,
        blocked_tools=["delete_shopping_list", "delete_bookmark"]
    )

    assert "delete_shopping_list" in settings.blocked_tools
    assert len(settings.blocked_tools) == 2


def test_budget_limit_validation():
    """Budget limit must be positive."""
    with pytest.raises(ValueError, match="Budget limit must be positive"):
        UserSettings(
            character_id=12345,
            budget_limit_isk=-1000000
        )
