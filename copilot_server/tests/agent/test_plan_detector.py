import pytest
from copilot_server.agent.plan_detector import PlanDetector
from copilot_server.agent.models import Plan, PlanStatus
from copilot_server.models.user_settings import RiskLevel


@pytest.fixture
def detector():
    return PlanDetector()


def test_single_tool_not_plan(detector):
    """Single tool call is not considered a plan."""
    llm_response = {
        "content": [
            {"type": "text", "text": "Let me check that."},
            {"type": "tool_use", "id": "call1", "name": "get_market_stats", "input": {}}
        ]
    }

    is_plan = detector.is_plan(llm_response)
    assert is_plan is False


def test_two_tools_not_plan(detector):
    """Two tool calls don't meet 3+ threshold."""
    llm_response = {
        "content": [
            {"type": "tool_use", "id": "call1", "name": "search_item", "input": {}},
            {"type": "tool_use", "id": "call2", "name": "get_market_stats", "input": {}}
        ]
    }

    is_plan = detector.is_plan(llm_response)
    assert is_plan is False


def test_three_tools_is_plan(detector):
    """Three or more tools = plan."""
    llm_response = {
        "content": [
            {"type": "tool_use", "id": "call1", "name": "get_war_summary", "input": {}},
            {"type": "tool_use", "id": "call2", "name": "get_combat_losses", "input": {"region_id": 10000002}},
            {"type": "tool_use", "id": "call3", "name": "get_material_requirements", "input": {}}
        ]
    }

    is_plan = detector.is_plan(llm_response)
    assert is_plan is True


def test_extract_plan_purpose(detector):
    """Extract plan purpose from text content."""
    llm_response = {
        "content": [
            {"type": "text", "text": "I'll analyze war zones and material demand."},
            {"type": "tool_use", "id": "call1", "name": "get_war_summary", "input": {}},
            {"type": "tool_use", "id": "call2", "name": "get_combat_losses", "input": {}},
            {"type": "tool_use", "id": "call3", "name": "get_top_destroyed_ships", "input": {}}
        ]
    }

    plan = detector.extract_plan(llm_response, session_id="sess-test")

    assert plan.purpose == "I'll analyze war zones and material demand."
    assert len(plan.steps) == 3
    assert plan.steps[0].tool == "get_war_summary"
    assert plan.steps[1].tool == "get_combat_losses"
    assert plan.steps[2].tool == "get_top_destroyed_ships"


def test_extract_plan_with_risk_levels(detector):
    """Extract plan and determine max risk level."""
    llm_response = {
        "content": [
            {"type": "text", "text": "Creating shopping list."},
            {"type": "tool_use", "id": "call1", "name": "get_production_chain", "input": {}},
            {"type": "tool_use", "id": "call2", "name": "create_shopping_list", "input": {}},
            {"type": "tool_use", "id": "call3", "name": "add_shopping_items", "input": {}}
        ]
    }

    # Mock tool risk levels
    detector.tool_risks = {
        "get_production_chain": RiskLevel.READ_ONLY,
        "create_shopping_list": RiskLevel.WRITE_LOW_RISK,
        "add_shopping_items": RiskLevel.WRITE_LOW_RISK
    }

    plan = detector.extract_plan(llm_response, session_id="sess-test")

    assert plan.max_risk_level == RiskLevel.WRITE_LOW_RISK
    assert plan.steps[0].risk_level == RiskLevel.READ_ONLY
    assert plan.steps[1].risk_level == RiskLevel.WRITE_LOW_RISK


def test_extract_plan_defaults_unknown_risk(detector):
    """Unknown tools default to CRITICAL risk level."""
    llm_response = {
        "content": [
            {"type": "text", "text": "Testing."},
            {"type": "tool_use", "id": "call1", "name": "unknown_tool_1", "input": {}},
            {"type": "tool_use", "id": "call2", "name": "unknown_tool_2", "input": {}},
            {"type": "tool_use", "id": "call3", "name": "unknown_tool_3", "input": {}}
        ]
    }

    plan = detector.extract_plan(llm_response, session_id="sess-test")

    # Unknown tools should default to CRITICAL
    assert plan.max_risk_level == RiskLevel.CRITICAL
    assert all(step.risk_level == RiskLevel.CRITICAL for step in plan.steps)
