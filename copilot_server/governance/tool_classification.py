"""
Tool Risk Classification
Classifies all 115 MCP tools by risk level for authorization.
"""

from enum import Enum
from typing import Dict


class RiskLevel(Enum):
    """Risk levels for MCP tools."""
    READ_ONLY = "read_only"              # Green - No state changes
    WRITE_LOW_RISK = "write_low_risk"    # Yellow - User data, reversible
    WRITE_HIGH_RISK = "write_high_risk"  # Orange - Data loss possible
    CRITICAL = "critical"                 # Red - ISK/irreversible (future)


# Tool Risk Classification Registry
TOOL_RISK_LEVELS: Dict[str, RiskLevel] = {
    # CONTEXT (2 tools) - READ_ONLY
    "eve_copilot_context": RiskLevel.READ_ONLY,
    "get_available_tools": RiskLevel.READ_ONLY,

    # MARKET (12 tools) - READ_ONLY
    "get_market_stats": RiskLevel.READ_ONLY,
    "compare_regions": RiskLevel.READ_ONLY,
    "get_arbitrage_opportunities": RiskLevel.READ_ONLY,
    "get_enhanced_arbitrage": RiskLevel.READ_ONLY,
    "calculate_custom_arbitrage": RiskLevel.READ_ONLY,
    "get_saved_arbitrage": RiskLevel.READ_ONLY,
    "clear_market_cache": RiskLevel.WRITE_LOW_RISK,  # Cache clear is low risk
    "get_market_orders": RiskLevel.READ_ONLY,
    "get_market_history": RiskLevel.READ_ONLY,
    "get_market_types": RiskLevel.READ_ONLY,
    "get_market_groups": RiskLevel.READ_ONLY,
    "get_market_prices": RiskLevel.READ_ONLY,

    # PRODUCTION (14 tools) - READ_ONLY
    "get_production_cost": RiskLevel.READ_ONLY,
    "optimize_production": RiskLevel.READ_ONLY,
    "simulate_production": RiskLevel.READ_ONLY,
    "get_production_chains": RiskLevel.READ_ONLY,
    "get_chain_materials": RiskLevel.READ_ONLY,
    "get_direct_materials": RiskLevel.READ_ONLY,
    "get_production_economics": RiskLevel.READ_ONLY,
    "get_economic_opportunities": RiskLevel.READ_ONLY,
    "get_regional_economics": RiskLevel.READ_ONLY,
    "create_production_job": RiskLevel.WRITE_LOW_RISK,
    "list_production_jobs": RiskLevel.READ_ONLY,
    "update_production_job": RiskLevel.WRITE_LOW_RISK,
    "get_production_job": RiskLevel.READ_ONLY,
    "delete_production_job": RiskLevel.WRITE_HIGH_RISK,

    # WAR_ROOM (16 tools) - READ_ONLY
    "get_war_losses": RiskLevel.READ_ONLY,
    "get_war_demand": RiskLevel.READ_ONLY,
    "get_combat_hotspots": RiskLevel.READ_ONLY,
    "get_sov_campaigns": RiskLevel.READ_ONLY,
    "update_sov_campaigns": RiskLevel.WRITE_LOW_RISK,  # Triggers data refresh
    "get_fw_hotspots": RiskLevel.READ_ONLY,
    "get_fw_vulnerable": RiskLevel.READ_ONLY,
    "update_fw_status": RiskLevel.WRITE_LOW_RISK,  # Triggers data refresh
    "get_war_doctrines": RiskLevel.READ_ONLY,
    "get_alliance_conflicts": RiskLevel.READ_ONLY,
    "get_system_danger": RiskLevel.READ_ONLY,
    "get_war_summary": RiskLevel.READ_ONLY,
    "get_top_ships_destroyed": RiskLevel.READ_ONLY,
    "get_safe_route": RiskLevel.READ_ONLY,
    "get_item_combat_stats": RiskLevel.READ_ONLY,
    "get_war_alerts": RiskLevel.READ_ONLY,

    # SHOPPING (25 tools) - MIXED
    "create_shopping_list": RiskLevel.WRITE_LOW_RISK,
    "list_shopping_lists": RiskLevel.READ_ONLY,
    "get_shopping_list": RiskLevel.READ_ONLY,
    "update_shopping_list": RiskLevel.WRITE_LOW_RISK,
    "delete_shopping_list": RiskLevel.WRITE_HIGH_RISK,
    "add_shopping_item": RiskLevel.WRITE_LOW_RISK,
    "update_shopping_item": RiskLevel.WRITE_LOW_RISK,
    "delete_shopping_item": RiskLevel.WRITE_HIGH_RISK,
    "mark_item_purchased": RiskLevel.WRITE_LOW_RISK,
    "unmark_item_purchased": RiskLevel.WRITE_LOW_RISK,
    "set_purchase_region": RiskLevel.WRITE_LOW_RISK,
    "update_item_runs": RiskLevel.WRITE_LOW_RISK,
    "set_build_decision": RiskLevel.WRITE_LOW_RISK,
    "calculate_item_materials": RiskLevel.READ_ONLY,
    "apply_materials_to_list": RiskLevel.WRITE_LOW_RISK,
    "get_item_with_materials": RiskLevel.READ_ONLY,
    "add_production_to_list": RiskLevel.WRITE_LOW_RISK,
    "export_shopping_list": RiskLevel.READ_ONLY,
    "get_list_by_region": RiskLevel.READ_ONLY,
    "get_regional_comparison": RiskLevel.READ_ONLY,
    "get_cargo_summary": RiskLevel.READ_ONLY,
    "get_transport_options": RiskLevel.READ_ONLY,
    "calculate_shopping_route": RiskLevel.READ_ONLY,
    "wizard_calculate_materials": RiskLevel.READ_ONLY,
    "wizard_compare_regions": RiskLevel.READ_ONLY,

    # CHARACTER (12 tools) - READ_ONLY (ESI data)
    "get_character_wallet": RiskLevel.READ_ONLY,
    "get_character_assets": RiskLevel.READ_ONLY,
    "get_character_skills": RiskLevel.READ_ONLY,
    "get_character_skillqueue": RiskLevel.READ_ONLY,
    "get_character_orders": RiskLevel.READ_ONLY,
    "get_character_industry": RiskLevel.READ_ONLY,
    "get_character_blueprints": RiskLevel.READ_ONLY,
    "get_character_info": RiskLevel.READ_ONLY,
    "get_character_portrait": RiskLevel.READ_ONLY,
    "get_corporation_wallet": RiskLevel.READ_ONLY,
    "get_corporation_info": RiskLevel.READ_ONLY,
    "get_corporation_journal": RiskLevel.READ_ONLY,

    # DASHBOARD (5 tools) - READ_ONLY
    "get_market_opportunities": RiskLevel.READ_ONLY,
    "get_opportunities_by_category": RiskLevel.READ_ONLY,
    "get_characters_summary": RiskLevel.READ_ONLY,
    "get_characters_portfolio": RiskLevel.READ_ONLY,
    "get_active_projects": RiskLevel.READ_ONLY,

    # RESEARCH (2 tools) - READ_ONLY
    "get_skills_for_item": RiskLevel.READ_ONLY,
    "get_skill_recommendations": RiskLevel.READ_ONLY,

    # BOOKMARKS (9 tools) - MIXED
    "create_bookmark": RiskLevel.WRITE_LOW_RISK,
    "list_bookmarks": RiskLevel.READ_ONLY,
    "check_bookmark": RiskLevel.READ_ONLY,
    "update_bookmark": RiskLevel.WRITE_LOW_RISK,
    "delete_bookmark": RiskLevel.WRITE_HIGH_RISK,
    "create_bookmark_list": RiskLevel.WRITE_LOW_RISK,
    "get_bookmark_lists": RiskLevel.READ_ONLY,
    "add_to_bookmark_list": RiskLevel.WRITE_LOW_RISK,
    "remove_from_bookmark_list": RiskLevel.WRITE_LOW_RISK,

    # ITEMS (6 tools) - READ_ONLY
    "search_item": RiskLevel.READ_ONLY,
    "get_item_info": RiskLevel.READ_ONLY,
    "search_group": RiskLevel.READ_ONLY,
    "get_material_composition": RiskLevel.READ_ONLY,
    "get_material_volumes": RiskLevel.READ_ONLY,
    "get_item_volume": RiskLevel.READ_ONLY,

    # ROUTES (5 tools) - READ_ONLY
    "get_trade_hubs": RiskLevel.READ_ONLY,
    "get_hub_distances": RiskLevel.READ_ONLY,
    "calculate_route": RiskLevel.READ_ONLY,
    "search_systems": RiskLevel.READ_ONLY,
    "calculate_cargo": RiskLevel.READ_ONLY,

    # MINING (3 tools) - READ_ONLY
    "find_mineral_locations": RiskLevel.READ_ONLY,
    "plan_mining_route": RiskLevel.READ_ONLY,
    "get_ore_info": RiskLevel.READ_ONLY,

    # HUNTER (4 tools) - READ_ONLY
    "get_hunter_categories": RiskLevel.READ_ONLY,
    "get_market_tree": RiskLevel.READ_ONLY,
    "scan_opportunities": RiskLevel.READ_ONLY,
    "get_cached_opportunities": RiskLevel.READ_ONLY,
}


def get_tool_risk_level(tool_name: str) -> RiskLevel:
    """
    Get risk level for a specific tool.

    Args:
        tool_name: Name of the MCP tool

    Returns:
        RiskLevel enum

    Raises:
        ValueError: If tool not found in classification
    """
    if tool_name not in TOOL_RISK_LEVELS:
        raise ValueError(f"Tool '{tool_name}' not classified. Add to TOOL_RISK_LEVELS.")

    return TOOL_RISK_LEVELS[tool_name]


def classify_all_tools() -> Dict[str, RiskLevel]:
    """
    Get risk classification for all tools.

    Returns:
        Dictionary mapping tool names to risk levels
    """
    return TOOL_RISK_LEVELS.copy()


def get_tools_by_risk_level(risk_level: RiskLevel) -> list[str]:
    """
    Get all tools at a specific risk level.

    Args:
        risk_level: Risk level to filter by

    Returns:
        List of tool names
    """
    return [
        name for name, level in TOOL_RISK_LEVELS.items()
        if level == risk_level
    ]
