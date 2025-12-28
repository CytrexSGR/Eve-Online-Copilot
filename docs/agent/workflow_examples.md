# EVE Co-Pilot Agent - Common Workflow Examples

This document provides proven workflow patterns for the Agent Runtime to use when orchestrating multi-tool operations.

**Purpose:** Help the LLM understand optimal tool usage patterns and common EVE Online analytical workflows.

**Last Updated:** 2025-12-28

---

## Market Analysis Workflows

### Q: "What's profitable to manufacture in Jita?"

**Workflow:**
1. `get_manufacturing_opportunities(region_id=10000002)`
   - Returns top 50 profitable items based on pre-calculated data
2. For top 5 candidates: `get_market_stats(type_id=X, region_id=10000002)`
   - Get current buy/sell prices and daily volumes
3. `calculate_production_cost(type_id=X)`
   - Calculate material costs and blueprint requirements
4. Calculate profit margins: `(sell_price - cost) / cost`
5. Rank by ISK/hour based on build time

**Expected Tools:** 6-8 tool calls, all READ_ONLY
**L1 Behavior:** Auto-execute
**Typical Duration:** 3-5 seconds

---

### Q: "Compare arbitrage opportunities for Hobgoblin II across all hubs"

**Workflow:**
1. `search_item(q="Hobgoblin II")`
   - Get type_id (2454)
2. `get_market_stats(type_id=2454, region_id=X)` for each major hub:
   - Jita (10000002), Amarr (10000043), Dodixie (10000032), Rens (10000030), Hek (10000042)
3. `calculate_arbitrage(type_id=2454)`
   - Automated multi-region arbitrage calculation
4. For best opportunities: `calculate_route(from_system, to_system)`
   - Get jump distance and safety rating
5. Calculate profit per jump: `profit / (jumps + 1)`

**Expected Tools:** 8-10 tool calls, all READ_ONLY
**L1 Behavior:** Auto-execute
**Typical Duration:** 4-6 seconds

---

## War Room Intelligence Workflows

### Q: "Where are battles happening and what materials are needed?"

**Workflow:**
1. `get_war_summary()`
   - Get overview of hot regions and current conflicts
2. `get_combat_losses(region_id=X)` for top 3 active regions
   - Get detailed ship destruction data
3. `get_top_destroyed_ships()`
   - Identify most commonly destroyed ships galaxy-wide
4. `get_material_requirements(type_ids=[ship_type_ids])`
   - Calculate materials needed to build those ship types
5. `get_regional_comparison(type_ids=[material_type_ids], regions=[hot_regions])`
   - Find best prices for required materials in war zones

**Expected Tools:** 8-12 tool calls, all READ_ONLY
**L1 Behavior:** Auto-execute
**Typical Duration:** 5-8 seconds

**Strategic Insight:**
- Higher destruction rates = higher material demand
- Suggest stockpiling common materials near war zones
- Identify profitable production opportunities

---

### Q: "What's the danger level of the route from Jita to Amarr?"

**Workflow:**
1. `search_systems(q="Jita")` and `search_systems(q="Amarr")`
   - Get system IDs if needed
2. `calculate_route(from_system="Jita", to_system="Amarr")`
   - Get jump sequence
3. `get_system_danger_score(system_id=X)` for each system in route
   - Based on recent killmail data
4. `get_safe_route(from_system="Jita", to_system="Amarr")`
   - Alternative safer route if available
5. Compare: shortest route vs. safest route (jumps, danger, time)

**Expected Tools:** 6-8 tool calls, all READ_ONLY
**L1 Behavior:** Auto-execute
**Typical Duration:** 3-4 seconds

---

## Production Planning Workflows

### Q: "Create shopping list for building 10 Caracals in Jita"

**Workflow:**
1. `search_item(q="Caracal")`
   - Get type_id for Caracal (621)
2. `get_production_chain(type_id=621, quantity=10)`
   - Get complete material tree (recursive, includes components)
3. `create_shopping_list(name="10 Caracals - Jita")` **[WRITE_LOW_RISK]**
   - Create new shopping list
4. `add_shopping_items(list_id=X, items=[{type_id, quantity}, ...])`  **[WRITE_LOW_RISK]**
   - Add all materials to list
5. `get_regional_comparison(type_ids=[material_ids], regions=[10000002])`
   - Get Jita prices for all materials
6. `calculate_shopping_route(list_id=X, hub_system="Jita")`
   - Optimize purchase route within trade hub

**Expected Tools:** 8-10 tool calls, includes WRITE_LOW_RISK
**L1 Behavior:** **Propose plan, wait for approval**
**Typical Duration:** 2 seconds planning + 4-6 seconds execution (after approval)

---

### Q: "What's the most profitable T1 frigate to build with my current skills?"

**Workflow:**
1. `get_character_skills(character_id=X)`
   - Get current skill levels
2. `get_manufacturing_opportunities(region_id=10000002, category="Ship")`
   - Get profitable ship manufacturing data
3. Filter results by character skills:
   - For each opportunity: `get_skills_for_item(type_id=X)`
   - Compare with character skills, keep only buildable
4. For top 5 buildable frigates: `get_market_stats(type_id=X, region_id=10000002)`
   - Get current market data
5. Rank by profit margin and build time

**Expected Tools:** 10-15 tool calls, all READ_ONLY
**L1 Behavior:** Auto-execute
**Typical Duration:** 6-10 seconds

---

## Character & Skill Workflows

### Q: "What skills do I need for building Tech 2 drones?"

**Workflow:**
1. `search_item(q="Tech 2 drone", group="Drone")`
   - Get drone type_ids (e.g., Hobgoblin II, Warrior II)
2. For each T2 drone: `get_skills_for_item(type_id=X)`
   - Get required production skills (typically Industry 5, various drone skills)
3. `get_character_skills(character_id=Y)`
   - Get player's current skills
4. Compare: identify skill gaps
   - Missing skills
   - Skills that need training (current level < required level)
5. `get_skill_recommendations(character_id=Y, goal="Tech 2 Drone Production")`
   - Get optimized training queue

**Expected Tools:** 6-9 tool calls, all READ_ONLY
**L1 Behavior:** Auto-execute
**Typical Duration:** 4-6 seconds

**Training Plan Output:**
- List missing skills in priority order
- Show training time for each
- Total time to goal
- Recommend skill books to purchase

---

## Shopping & Logistics Workflows

### Q: "Find cheapest region to buy 1M Tritanium and route from there to Jita"

**Workflow:**
1. `search_item(q="Tritanium")`
   - Get type_id (34)
2. `get_regional_comparison(type_ids=[34], quantity=1000000)`
   - Compare prices across all major hubs
3. Identify cheapest region (e.g., Amarr)
4. `calculate_route(from_system="Amarr", to_system="Jita")`
   - Get jump count and route safety
5. `calculate_cargo_volume(items=[{type_id: 34, quantity: 1000000}])`
   - Calculate m³ required
6. `get_transport_options(volume=X, value=Y)`
   - Suggest ship types (Tayra, Badger, DST)
7. Calculate total cost: `material_cost + (jumps * risk_factor * value * 0.01)`

**Expected Tools:** 7-9 tool calls, all READ_ONLY
**L1 Behavior:** Auto-execute
**Typical Duration:** 4-5 seconds

---

### Q: "Export my shopping list 'Gila Production' to EVE format"

**Workflow:**
1. `get_shopping_lists()`
   - Get all user shopping lists
2. Filter by name: "Gila Production"
3. `export_shopping_list(list_id=X, format="eve")`
   - Generate EVE Online compatible format (copy-paste into game)
4. Return formatted text:
   ```
   Tritanium    2,450,000
   Pyerite      890,000
   Mexallon     345,000
   ...
   ```

**Expected Tools:** 3-4 tool calls, all READ_ONLY
**L1 Behavior:** Auto-execute
**Typical Duration:** 1-2 seconds

---

## Bookmark Management Workflows

### Q: "Bookmark all ships I'm currently researching for production"

**Workflow:**
1. `get_character_industry(character_id=X)`
   - Get active manufacturing and research jobs
2. Extract unique ship type_ids from jobs
3. For each ship: `create_bookmark(type_id=X, notes="Production target")`  **[WRITE_LOW_RISK]**
   - Create individual bookmarks
4. `create_bookmark_list(name="Production Pipeline")`  **[WRITE_LOW_RISK]**
   - Create list to organize bookmarks
5. `add_to_bookmark_list(list_id=X, bookmark_ids=[...])`  **[WRITE_LOW_RISK]**
   - Add all ship bookmarks to list

**Expected Tools:** 8-12 tool calls, includes WRITE_LOW_RISK
**L1 Behavior:** **Propose plan, wait for approval**
**Typical Duration:** 2 seconds planning + 3-4 seconds execution

---

## Mining Workflows

### Q: "Where can I mine Veldspar closest to Jita?"

**Workflow:**
1. `search_item(q="Veldspar")`
   - Get ore type_id (typically 1230)
2. `find_mineral_ore(mineral_name="Tritanium")`
   - Veldspar is primary Tritanium source
3. `get_ore_locations(ore_type_id=1230, proximity_to="Jita", max_distance=10)`
   - Find asteroid belts within 10 jumps
4. `calculate_route(from_system="Jita", to_system=X)` for each location
   - Get exact jump counts
5. `get_system_danger_score(system_id=X)` for each location
   - Check safety (important for miners)
6. Rank by: `(ore_richness * safety_score) / jump_distance`

**Expected Tools:** 8-10 tool calls, all READ_ONLY
**L1 Behavior:** Auto-execute
**Typical Duration:** 4-6 seconds

---

## Dashboard & Overview Workflows

### Q: "Show me my character's current portfolio and best opportunities"

**Workflow:**
1. `get_character_wallet(character_id=X)`
   - Current ISK balance
2. `get_character_assets(character_id=X)`
   - All assets, calculate total value
3. `get_character_orders(character_id=X)`
   - Active buy/sell orders
4. `get_character_industry(character_id=X)`
   - Manufacturing jobs in progress
5. `get_opportunities_overview(character_id=X)`
   - Personalized opportunities based on skills
6. `get_character_portfolio(character_id=X)`
   - Aggregated portfolio analysis

**Expected Tools:** 6 tool calls, all READ_ONLY
**L1 Behavior:** Auto-execute
**Typical Duration:** 3-4 seconds

**Dashboard Output:**
- Net worth: XX.X billion ISK
- Active orders: XX orders, XX.X billion in trades
- Manufacturing: XX jobs, estimated completion XX hours
- Top 5 opportunities based on skills

---

## Multi-Category Complex Workflows

### Q: "I have 500M ISK. What's the best way to make money with my skills right now?"

**Complex Multi-Step Analysis:**

**Phase 1: Assess Capabilities**
1. `get_character_skills(character_id=X)`
   - What can character do?
2. `get_character_wallet(character_id=X)`
   - Confirm available capital

**Phase 2: Explore Opportunities**
3. `get_manufacturing_opportunities(budget=500000000)`
   - Manufacturing options within budget
4. `get_opportunities_overview(character_id=X)`
   - Personalized opportunities
5. For top 3 opportunities: `get_production_chain(type_id=X)`
   - Understand material requirements

**Phase 3: Market Analysis**
6. `get_regional_comparison(type_ids=[material_ids], regions=[major_hubs])`
   - Find best material prices
7. `get_market_stats(type_id=X, region_id=10000002)` for final products
   - Verify demand exists

**Phase 4: Risk Assessment**
8. `get_war_summary()`
   - Check if war might affect supply chains
9. Calculate ROI and risk for each opportunity

**Expected Tools:** 15-20 tool calls, all READ_ONLY
**L1 Behavior:** Auto-execute
**Typical Duration:** 10-15 seconds

**Output Format:**
- Option 1: Manufacturing (Caracal Navy Issue) - ROI 23%, 2 days cycle
- Option 2: Trading (Arbitrage Tritanium) - ROI 8%, same-day
- Option 3: Research (T2 BPO copying) - ROI 45%, 14 days
- Recommendation based on risk tolerance

---

## Workflow Pattern Guidelines

### When to Combine Tools

**Good Combinations:**
- Market analysis → Production cost → Profit calculation
- War intelligence → Material requirements → Shopping lists
- Character skills → Manufacturing opportunities → Training plans
- Item search → Regional comparison → Route planning

**Avoid Anti-Patterns:**
- Don't call `get_market_stats` repeatedly for same item/region (cache results)
- Don't create shopping lists without price checks first
- Don't suggest production without checking skill requirements

### Progressive Refinement

If user's question is vague:

**Example:** "What should I do?"

**Response Strategy:**
1. Start broad: `get_opportunities_overview(character_id=X)`
2. Ask clarifying question: "I see you have good mining and manufacturing skills. Which interests you more?"
3. Narrow focus based on answer
4. Execute detailed analysis workflow

**Don't:** Execute 50 tools speculatively. Let user guide focus.

---

## Tool Execution Best Practices

### Ordering Tools

**Correct Order:**
1. Gather context (character data, market data)
2. Analyze/calculate
3. Make recommendations
4. Execute writes (after approval)

**Example (Shopping List Creation):**
```
✓ search_item → get_production_chain → get_regional_comparison → create_shopping_list → add_items
✗ create_shopping_list → search_item → add_items (wrong: list created before knowing what to add)
```

### Handling Failures

If tool fails mid-workflow:
1. Log failure
2. Continue with remaining tools if possible
3. Provide partial results
4. Explain what couldn't be completed

**Example:**
"ESI API timeout prevented fetching Amarr prices, but here are Jita and Dodixie prices..."

---

## Workflow Complexity Matrix

| Workflow Type | Tool Count | READ/WRITE | Auto-Execute (L1) | Duration |
|---------------|------------|------------|-------------------|----------|
| Simple Query | 1-2 | READ_ONLY | ✅ Yes | < 1s |
| Analysis | 3-8 | READ_ONLY | ✅ Yes | 2-6s |
| Complex Analysis | 9-20 | READ_ONLY | ✅ Yes | 6-15s |
| Simple Write | 3-5 | WRITE_LOW | ❌ Propose | 2-4s |
| Complex Write | 6-12 | WRITE_LOW/HIGH | ❌ Propose | 4-10s |

---

**End of Workflow Examples**

**Usage Note:** This document should be loaded dynamically by Agent Runtime when processing complex multi-tool queries to provide LLM with proven patterns.
