import pytest
from copilot_server.agent.auto_execute import should_auto_execute
from copilot_server.agent.models import Plan, PlanStep
from copilot_server.models.user_settings import AutonomyLevel, RiskLevel


def test_l0_never_auto_executes():
    """L0 (READ_ONLY) never auto-executes, always requires approval."""
    plan = Plan(
        session_id="sess-test",
        purpose="Test",
        steps=[
            PlanStep(tool="get_market_stats", arguments={}, risk_level=RiskLevel.READ_ONLY),
            PlanStep(tool="get_war_summary", arguments={}, risk_level=RiskLevel.READ_ONLY),
            PlanStep(tool="search_item", arguments={}, risk_level=RiskLevel.READ_ONLY)
        ],
        max_risk_level=RiskLevel.READ_ONLY
    )

    result = should_auto_execute(plan, AutonomyLevel.READ_ONLY)
    assert result is False


def test_l1_auto_executes_read_only():
    """L1 (RECOMMENDATIONS) auto-executes pure READ_ONLY workflows."""
    plan = Plan(
        session_id="sess-test",
        purpose="Market analysis",
        steps=[
            PlanStep(tool="get_market_stats", arguments={}, risk_level=RiskLevel.READ_ONLY),
            PlanStep(tool="get_war_summary", arguments={}, risk_level=RiskLevel.READ_ONLY),
            PlanStep(tool="calculate_arbitrage", arguments={}, risk_level=RiskLevel.READ_ONLY)
        ],
        max_risk_level=RiskLevel.READ_ONLY
    )

    result = should_auto_execute(plan, AutonomyLevel.RECOMMENDATIONS)
    assert result is True


def test_l1_requires_approval_for_writes():
    """L1 requires approval for any WRITE operations."""
    plan = Plan(
        session_id="sess-test",
        purpose="Create shopping list",
        steps=[
            PlanStep(tool="get_production_chain", arguments={}, risk_level=RiskLevel.READ_ONLY),
            PlanStep(tool="create_shopping_list", arguments={}, risk_level=RiskLevel.WRITE_LOW_RISK),
            PlanStep(tool="add_shopping_items", arguments={}, risk_level=RiskLevel.WRITE_LOW_RISK)
        ],
        max_risk_level=RiskLevel.WRITE_LOW_RISK
    )

    result = should_auto_execute(plan, AutonomyLevel.RECOMMENDATIONS)
    assert result is False


def test_l2_auto_executes_low_risk_writes():
    """L2 (ASSISTED) auto-executes READ_ONLY and WRITE_LOW_RISK."""
    plan = Plan(
        session_id="sess-test",
        purpose="Create shopping list",
        steps=[
            PlanStep(tool="get_production_chain", arguments={}, risk_level=RiskLevel.READ_ONLY),
            PlanStep(tool="create_shopping_list", arguments={}, risk_level=RiskLevel.WRITE_LOW_RISK),
            PlanStep(tool="add_shopping_items", arguments={}, risk_level=RiskLevel.WRITE_LOW_RISK)
        ],
        max_risk_level=RiskLevel.WRITE_LOW_RISK
    )

    result = should_auto_execute(plan, AutonomyLevel.ASSISTED)
    assert result is True


def test_l2_requires_approval_for_high_risk():
    """L2 requires approval for WRITE_HIGH_RISK operations."""
    plan = Plan(
        session_id="sess-test",
        purpose="Delete bookmarks",
        steps=[
            PlanStep(tool="get_bookmarks", arguments={}, risk_level=RiskLevel.READ_ONLY),
            PlanStep(tool="delete_bookmark", arguments={}, risk_level=RiskLevel.WRITE_HIGH_RISK),
            PlanStep(tool="delete_bookmark", arguments={}, risk_level=RiskLevel.WRITE_HIGH_RISK)
        ],
        max_risk_level=RiskLevel.WRITE_HIGH_RISK
    )

    result = should_auto_execute(plan, AutonomyLevel.ASSISTED)
    assert result is False


def test_l2_blocks_critical_operations():
    """L2 blocks CRITICAL operations."""
    plan = Plan(
        session_id="sess-test",
        purpose="Unknown operations",
        steps=[
            PlanStep(tool="unknown_tool", arguments={}, risk_level=RiskLevel.CRITICAL),
            PlanStep(tool="another_unknown", arguments={}, risk_level=RiskLevel.CRITICAL)
        ],
        max_risk_level=RiskLevel.CRITICAL
    )

    result = should_auto_execute(plan, AutonomyLevel.ASSISTED)
    assert result is False


def test_l3_auto_executes_everything():
    """L3 (SUPERVISED) auto-executes all operations (future feature)."""
    plan_critical = Plan(
        session_id="sess-test",
        purpose="High-risk operations",
        steps=[
            PlanStep(tool="dangerous_operation", arguments={}, risk_level=RiskLevel.CRITICAL),
            PlanStep(tool="another_dangerous", arguments={}, risk_level=RiskLevel.CRITICAL)
        ],
        max_risk_level=RiskLevel.CRITICAL
    )

    result = should_auto_execute(plan_critical, AutonomyLevel.SUPERVISED)
    assert result is True
