# Phase 1: MCP Tool Expansion - Quick Start Guide

**Goal:** Expand from 17 to 118 MCP tools (complete API coverage)

---

## 📊 Current Status

- **Implemented:** 17 tools (14%)
- **Missing:** 101 tools (86%)
- **Target:** 118 tools (100%)

### Existing Tools
✅ Market: search_item, get_item_info, get_market_stats, find_arbitrage (4)
✅ Production: get_production_cost, simulate_build, get_blueprint_info (3)
✅ Character: wallet, assets, skills, orders, blueprints, industry (6)
✅ Corporation: corp_wallet, corp_info (2)
✅ Auth: get_authenticated_characters (1)
✅ Utility: get_regions, eve_copilot_context (2)

### Missing Tool Categories

**War Room (16 tools) - PRIORITY 1**
```python
# Missing tools:
- get_war_losses
- get_war_demand
- get_war_heatmap
- get_war_campaigns
- update_war_campaigns
- get_war_fw_hotspots
- get_war_fw_vulnerable
- update_war_fw
- get_war_doctrines
- get_war_conflicts
- get_system_danger
- get_war_summary
- get_war_top_ships
- get_safe_route
- get_item_combat_stats
- get_war_alerts
```

**Shopping (26 tools) - PRIORITY 2**
```python
# Missing tools:
- list_shopping_lists
- create_shopping_list
- get_shopping_list
- update_shopping_list
- delete_shopping_list
- add_shopping_item
- update_shopping_item
- delete_shopping_item
- mark_item_purchased
- unmark_item_purchased
- set_purchase_region
- update_item_runs
- set_build_decision
- calculate_item_materials
- apply_materials_to_list
- get_item_with_materials
- add_production_to_list
- export_shopping_list
- get_list_by_region
- get_regional_comparison
- get_cargo_summary
- get_transport_options
- calculate_shopping_route
- get_market_orders
- wizard_calculate_materials
- wizard_compare_regions
```

**Dashboard (5 tools) - PRIORITY 3**
```python
- get_market_opportunities
- get_opportunities_by_category
- get_characters_summary
- get_portfolio_analysis
- get_active_projects
```

**Production (9 additional tools) - PRIORITY 4**
```python
- get_production_chains
- get_chain_materials
- get_direct_materials
- get_economics_opportunities
- get_economics_analysis
- get_economics_regions
- create_workflow_job
- list_workflow_jobs
- update_workflow_job
```

**Bookmarks (9 tools) - PRIORITY 5**
```python
- create_bookmark
- list_bookmarks
- check_bookmark
- update_bookmark
- delete_bookmark
- create_bookmark_list
- list_bookmark_lists
- add_to_bookmark_list
- remove_from_bookmark_list
```

**Research (2 tools) - PRIORITY 6**
```python
- get_skills_for_item
- get_skill_recommendations
```

**Market (5 additional tools) - PRIORITY 7**
```python
- compare_region_prices
- enhanced_arbitrage_with_routing
- submit_custom_arbitrage
- get_saved_arbitrage
- clear_market_cache
```

**Items & Materials (6 tools) - PRIORITY 8**
```python
- search_item_groups
- get_all_regions
- get_material_composition
- get_material_volumes
- calculate_cargo_volume
- get_item_volume_info
```

**Mining (3 tools) - PRIORITY 9**
```python
- find_mineral_locations
- get_system_mining_info
- get_ore_composition
```

**Routes (5 tools) - PRIORITY 10**
```python
- get_trade_hubs
- get_hub_distances
- calculate_system_route
- search_systems
- calculate_route_with_danger
```

---

## 🚀 Implementation Strategy

### Step 1: Tool Definition Template

Create a standardized template for all tools:

```python
{
    "name": "tool_name",
    "description": "Clear description with example. Must mention what the tool does and when to use it.",
    "parameters": [
        {
            "name": "param_name",
            "type": "integer|string|boolean|number",
            "required": True|False,
            "description": "Parameter description with example values",
            "default": "default_value (if not required)",
            "enum": ["value1", "value2"] # if applicable
        }
    ]
}
```

### Step 2: Tool Implementation Pattern

```python
# In routers/mcp.py

# 1. Add tool definition to MCP_TOOLS list
MCP_TOOLS.append({
    "name": "get_war_losses",
    "description": "Get combat ship losses for a region over the last N days. Returns top ships destroyed with quantities. Use region_id 10000002 for Jita.",
    "parameters": [
        {
            "name": "region_id",
            "type": "integer",
            "required": True,
            "description": "Region ID (10000002=Jita, 10000043=Amarr)"
        },
        {
            "name": "days",
            "type": "integer",
            "required": False,
            "description": "Days to look back (1-30), default 7",
            "default": 7
        },
        {
            "name": "type",
            "type": "string",
            "required": False,
            "description": "Filter by 'ships', 'items', or 'all'",
            "default": "all",
            "enum": ["all", "ships", "items"]
        }
    ]
})

# 2. Add handler in mcp_tools_call() function
elif name == "get_war_losses":
    from killmail_service import killmail_service
    region_id = args.get("region_id")
    days = args.get("days", 7)
    loss_type = args.get("type", "all")

    if loss_type == "ships":
        result = {"ships": killmail_service.get_ship_losses(region_id, days)}
    elif loss_type == "items":
        result = {"items": killmail_service.get_item_losses(region_id, days)}
    else:
        result = {
            "ships": killmail_service.get_ship_losses(region_id, days),
            "items": killmail_service.get_item_losses(region_id, days)
        }
```

### Step 3: Batch Implementation

Group tools by category and implement in batches:

1. **Day 1-2:** War Room (16 tools)
2. **Day 3-5:** Shopping (26 tools)
3. **Day 6:** Dashboard (5 tools)
4. **Day 7-8:** Production (9 tools)
5. **Day 9:** Bookmarks (9 tools)
6. **Day 10:** Research + Market + Items (13 tools)
7. **Day 11:** Mining + Routes (8 tools)
8. **Day 12-14:** Testing + Documentation

---

## 📝 Implementation Checklist

For each tool:
- [ ] Add tool definition to `MCP_TOOLS` list
- [ ] Implement handler in `mcp_tools_call()` function
- [ ] Test with curl or Python script
- [ ] Add example to documentation
- [ ] Verify error handling

### Testing Template

```bash
# Test MCP tool via API
curl -X POST http://localhost:8000/mcp/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "name": "get_war_losses",
    "arguments": {
      "region_id": 10000002,
      "days": 7,
      "type": "ships"
    }
  }' | python3 -m json.tool
```

---

## 🎯 Priority Order & Rationale

1. **War Room** - Most complex, most valuable for in-game assistance
2. **Shopping** - Core functionality for production planning
3. **Dashboard** - Quick overview, high value
4. **Production** - Advanced production features
5. **Bookmarks** - Quality of life
6. **Research** - Skill planning
7. **Market** - Additional market features
8. **Items** - Utility functions
9. **Mining** - Niche but useful
10. **Routes** - Navigation helpers

---

## 🔧 Development Workflow

### Setup
```bash
cd /home/cytrex/eve_copilot

# Create feature branch
git checkout -b feature/mcp-tool-expansion

# Make sure backend is running
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Development Loop
```bash
# 1. Edit routers/mcp.py
# 2. Save (auto-reload)
# 3. Test with curl
# 4. Repeat until tool works
# 5. Commit when category complete
```

### Commit Pattern
```bash
git add routers/mcp.py
git commit -m "feat(mcp): Add War Room tools (16 tools)

- get_war_losses
- get_war_demand
- get_war_heatmap
... (list all)

Total MCP tools: 33/118 (28%)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## 📚 Documentation Requirements

### Update `mcp_tools.json`
Add all new tools with complete metadata:

```json
{
  "tools": [
    {
      "name": "get_war_losses",
      "description": "...",
      "endpoint": "/api/war/losses/{region_id}",
      "method": "GET",
      "parameters": {...},
      "example": "/api/war/losses/10000002?days=7&type=ships"
    }
  ]
}
```

### Create `docs/MCP_TOOLS.md`

Comprehensive guide:
- Tool categorization
- Usage examples
- Best practices
- Common workflows
- Troubleshooting

---

## 🎯 Success Criteria

- [ ] All 118 endpoints have MCP tool definitions
- [ ] All tools tested and working
- [ ] Average tool execution time <500ms
- [ ] Error handling for all tools
- [ ] Complete documentation
- [ ] Example workflows documented
- [ ] Integration with existing MCP proxy working

---

## 🚀 Ready to Start?

**First Task:** Implement War Room tools (16 tools)

```bash
# Start backend if not running
cd /home/cytrex/eve_copilot
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Open in editor
# Edit: routers/mcp.py

# Start with get_war_losses (simplest War Room tool)
```

**Next:** Follow the implementation pattern above and work through the priority list!

---

**Estimated Time:** 2 weeks (1-2 hours per day)
**Difficulty:** Medium (pattern-based, repetitive)
**Reward:** Complete MCP coverage, ready for AI integration!
