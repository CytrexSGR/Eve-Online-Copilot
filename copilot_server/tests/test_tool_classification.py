# copilot_server/tests/test_tool_classification.py

import pytest
from copilot_server.governance.tool_classification import (
    RiskLevel,
    get_tool_risk_level,
    classify_all_tools,
    TOOL_RISK_LEVELS
)


def test_read_only_tools_are_green():
    """Read-only tools should be classified as READ_ONLY."""
    assert get_tool_risk_level("search_item") == RiskLevel.READ_ONLY
    assert get_tool_risk_level("get_market_stats") == RiskLevel.READ_ONLY
    assert get_tool_risk_level("get_war_summary") == RiskLevel.READ_ONLY


def test_write_low_risk_tools_are_yellow():
    """Low-risk write tools should be classified as WRITE_LOW_RISK."""
    assert get_tool_risk_level("create_shopping_list") == RiskLevel.WRITE_LOW_RISK
    assert get_tool_risk_level("create_bookmark") == RiskLevel.WRITE_LOW_RISK
    assert get_tool_risk_level("mark_item_purchased") == RiskLevel.WRITE_LOW_RISK


def test_write_high_risk_tools_are_orange():
    """High-risk write tools should be classified as WRITE_HIGH_RISK."""
    assert get_tool_risk_level("delete_shopping_list") == RiskLevel.WRITE_HIGH_RISK
    assert get_tool_risk_level("delete_bookmark") == RiskLevel.WRITE_HIGH_RISK


def test_all_115_tools_classified():
    """All MCP tools must have risk classification."""
    classification = classify_all_tools()
    assert len(classification) == 115

    # Verify all tools are classified
    for tool_name, risk_level in classification.items():
        assert isinstance(risk_level, RiskLevel)


def test_no_critical_tools_yet():
    """CRITICAL tools not implemented yet."""
    classification = classify_all_tools()
    critical_tools = [
        name for name, level in classification.items()
        if level == RiskLevel.CRITICAL
    ]
    assert len(critical_tools) == 0
