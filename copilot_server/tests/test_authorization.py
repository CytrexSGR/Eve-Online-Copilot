# copilot_server/tests/test_authorization.py

import pytest
from copilot_server.governance.authorization import AuthorizationChecker
from copilot_server.governance.tool_classification import RiskLevel
from copilot_server.models.user_settings import UserSettings, AutonomyLevel


@pytest.fixture
def l0_user():
    """User with READ_ONLY autonomy."""
    return UserSettings(
        character_id=12345,
        autonomy_level=AutonomyLevel.READ_ONLY
    )


@pytest.fixture
def l1_user():
    """User with RECOMMENDATIONS autonomy (default)."""
    return UserSettings(
        character_id=12345,
        autonomy_level=AutonomyLevel.RECOMMENDATIONS
    )


@pytest.fixture
def l2_user():
    """User with ASSISTED autonomy."""
    return UserSettings(
        character_id=12345,
        autonomy_level=AutonomyLevel.ASSISTED,
        require_confirmation=False
    )


def test_read_only_user_can_use_read_tools(l0_user):
    """L0 user can use READ_ONLY tools."""
    checker = AuthorizationChecker(l0_user)

    assert checker.is_tool_allowed("search_item", {}) is True
    assert checker.is_tool_allowed("get_market_stats", {}) is True


def test_read_only_user_cannot_write(l0_user):
    """L0 user cannot use any WRITE tools."""
    checker = AuthorizationChecker(l0_user)

    assert checker.is_tool_allowed("create_shopping_list", {}) is False
    assert checker.is_tool_allowed("delete_bookmark", {}) is False


def test_l1_user_can_write_low_risk(l1_user):
    """L1 user can use WRITE_LOW_RISK tools."""
    checker = AuthorizationChecker(l1_user)

    assert checker.is_tool_allowed("create_shopping_list", {}) is True
    assert checker.is_tool_allowed("mark_item_purchased", {}) is True


def test_l1_user_blocked_from_high_risk(l1_user):
    """L1 user blocked from WRITE_HIGH_RISK without L2."""
    checker = AuthorizationChecker(l1_user)

    assert checker.is_tool_allowed("delete_shopping_list", {}) is False
    assert checker.is_tool_allowed("delete_bookmark", {}) is False


def test_l2_user_can_write_high_risk(l2_user):
    """L2 user can use WRITE_HIGH_RISK tools."""
    checker = AuthorizationChecker(l2_user)

    assert checker.is_tool_allowed("delete_shopping_list", {}) is True


def test_blacklisted_tools_always_blocked():
    """User-blacklisted tools always blocked."""
    settings = UserSettings(
        character_id=12345,
        autonomy_level=AutonomyLevel.ASSISTED,
        blocked_tools=["search_item"]
    )
    checker = AuthorizationChecker(settings)

    # Even READ_ONLY tool blocked if user blacklisted it
    assert checker.is_tool_allowed("search_item", {}) is False


def test_get_denial_reason():
    """Authorization checker provides helpful denial reasons."""
    settings = UserSettings(
        character_id=12345,
        autonomy_level=AutonomyLevel.READ_ONLY
    )
    checker = AuthorizationChecker(settings)

    allowed, reason = checker.check_authorization("create_shopping_list", {})

    assert allowed is False
    assert "autonomy level" in reason.lower()
    assert "RECOMMENDATIONS" in reason  # Suggests required level
