"""
Tests for Approval Manager
Validates approval logic based on autonomy level and risk level.
"""

import pytest
from copilot_server.agent.approval_manager import ApprovalManager
from copilot_server.models.user_settings import RiskLevel, AutonomyLevel


def test_requires_approval_for_high_risk():
    """Test that high-risk tools require approval at L1 autonomy."""
    manager = ApprovalManager(autonomy_level=AutonomyLevel.RECOMMENDATIONS)

    # WRITE_HIGH_RISK requires approval at L1 (RECOMMENDATIONS)
    assert manager.requires_approval("delete_shopping_list", {}, RiskLevel.WRITE_HIGH_RISK) == True

    # READ_ONLY auto-executes at L1
    assert manager.requires_approval("get_market_stats", {}, RiskLevel.READ_ONLY) == False

    # WRITE_LOW_RISK auto-executes at L1
    assert manager.requires_approval("create_shopping_list", {}, RiskLevel.WRITE_LOW_RISK) == False


def test_auto_execute_at_assisted_level():
    """Test that WRITE_HIGH_RISK tools auto-execute at ASSISTED autonomy."""
    manager = ApprovalManager(autonomy_level=AutonomyLevel.ASSISTED)

    # WRITE_HIGH_RISK auto-executes at ASSISTED
    assert manager.requires_approval("delete_shopping_list", {}, RiskLevel.WRITE_HIGH_RISK) == False

    # CRITICAL still requires approval
    assert manager.requires_approval("unknown_tool", {}, RiskLevel.CRITICAL) == True


def test_read_only_autonomy():
    """Test that only READ_ONLY tools auto-execute at READ_ONLY autonomy."""
    manager = ApprovalManager(autonomy_level=AutonomyLevel.READ_ONLY)

    # READ_ONLY auto-executes
    assert manager.requires_approval("get_market_stats", {}, RiskLevel.READ_ONLY) == False

    # All write operations require approval
    assert manager.requires_approval("create_shopping_list", {}, RiskLevel.WRITE_LOW_RISK) == True
    assert manager.requires_approval("delete_shopping_list", {}, RiskLevel.WRITE_HIGH_RISK) == True
    assert manager.requires_approval("unknown_tool", {}, RiskLevel.CRITICAL) == True


def test_supervised_autonomy():
    """Test that all tools auto-execute at SUPERVISED autonomy (future)."""
    manager = ApprovalManager(autonomy_level=AutonomyLevel.SUPERVISED)

    # All risk levels auto-execute
    assert manager.requires_approval("get_market_stats", {}, RiskLevel.READ_ONLY) == False
    assert manager.requires_approval("create_shopping_list", {}, RiskLevel.WRITE_LOW_RISK) == False
    assert manager.requires_approval("delete_shopping_list", {}, RiskLevel.WRITE_HIGH_RISK) == False
    assert manager.requires_approval("unknown_tool", {}, RiskLevel.CRITICAL) == False


def test_threshold_mapping():
    """Test that autonomy level to threshold mapping is correct."""
    # READ_ONLY: Only READ_ONLY
    manager = ApprovalManager(autonomy_level=AutonomyLevel.READ_ONLY)
    assert manager.threshold == RiskLevel.READ_ONLY

    # RECOMMENDATIONS: READ_ONLY + WRITE_LOW_RISK
    manager = ApprovalManager(autonomy_level=AutonomyLevel.RECOMMENDATIONS)
    assert manager.threshold == RiskLevel.WRITE_LOW_RISK

    # ASSISTED: READ_ONLY + WRITE_LOW_RISK + WRITE_HIGH_RISK
    manager = ApprovalManager(autonomy_level=AutonomyLevel.ASSISTED)
    assert manager.threshold == RiskLevel.WRITE_HIGH_RISK

    # SUPERVISED: All (including CRITICAL)
    manager = ApprovalManager(autonomy_level=AutonomyLevel.SUPERVISED)
    assert manager.threshold == RiskLevel.CRITICAL


def test_risk_ordering():
    """Test that risk levels are correctly ordered."""
    manager = ApprovalManager(autonomy_level=AutonomyLevel.RECOMMENDATIONS)

    # Define expected order
    risk_order = [
        RiskLevel.READ_ONLY,
        RiskLevel.WRITE_LOW_RISK,
        RiskLevel.WRITE_HIGH_RISK,
        RiskLevel.CRITICAL
    ]

    # Test ordering
    for i in range(len(risk_order) - 1):
        lower_risk = risk_order[i]
        higher_risk = risk_order[i + 1]

        # Lower risk should be allowed at higher thresholds
        manager_higher = ApprovalManager(autonomy_level=AutonomyLevel.ASSISTED)
        assert manager_higher.requires_approval("test_tool", {}, lower_risk) == False
