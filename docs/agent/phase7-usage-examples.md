# Phase 7: Usage Examples & Real-World Scenarios

**Date:** 2025-12-29

This document provides practical examples of using the Phase 7 Agent Runtime with real-world EVE Online queries, demonstrating the agentic loop, tool execution, and various scenarios.

## Table of Contents

1. [Simple Queries](#simple-queries)
2. [Multi-Tool Workflows](#multi-tool-workflows)
3. [Authorization Scenarios](#authorization-scenarios)
4. [Error Handling](#error-handling)
5. [Complex Queries](#complex-queries)
6. [Testing Scenarios](#testing-scenarios)

---

## Simple Queries

### Example 1: Market Price Lookup

**Query:** "What is the current sell price of Tritanium in Jita?"

**Autonomy Level:** L1 (RECOMMENDATIONS)

**Agent Flow:**
```
1. LLM analyzes query
2. Recognizes need for market data
3. Calls get_market_stats tool:
   - type_id: 34 (Tritanium)
   - region_id: 10000002 (The Forge/Jita)
4. Tool executes in 159ms
5. Returns: {"lowest_sell": 3.95, "highest_buy": 3.80}
6. LLM synthesizes answer
```

**SSE Event Stream:**
```
data: {"type":"thinking","iteration":1}

data: {"type":"text","text":"Let me check the current market price for Tritanium in Jita."}

data: {"type":"tool_call_started","tool":"get_market_stats","arguments":{"type_id":34,"region_id":10000002}}

data: {"type":"tool_call_completed","tool":"get_market_stats"}

data: {"type":"text","text":" The current lowest sell price for Tritanium in Jita is approximately 3.95 ISK."}

data: {"type":"done","message_id":"msg-abc123"}
```

**Final Answer:**
> "Let me check the current market price for Tritanium in Jita. The current lowest sell price for Tritanium in Jita is approximately 3.95 ISK."

**Performance:**
- Tool execution: 159ms
- LLM processing: ~800ms
- Total time: ~2 seconds

---

### Example 2: Item Search

**Query:** "Find items related to shield boosting"

**Autonomy Level:** L1 (RECOMMENDATIONS)

**Agent Flow:**
```
1. LLM recognizes search intent
2. Calls search_item tool:
   - query: "shield booster"
   - limit: 10
3. Tool returns list of shield booster modules
4. LLM formats results
```

**Tool Call:**
```json
{
  "tool": "search_item",
  "arguments": {
    "query": "shield booster",
    "limit": 10
  }
}
```

**Tool Result:**
```json
[
  {"type_id": 3841, "name": "Small Shield Booster I", "group": "Shield Boosters"},
  {"type_id": 3843, "name": "Medium Shield Booster I", "group": "Shield Boosters"},
  {"type_id": 3849, "name": "Large Shield Booster I", "group": "Shield Boosters"},
  {"type_id": 5739, "name": "X-Large Shield Booster I", "group": "Shield Boosters"}
]
```

**Final Answer:**
> "I found several shield boosting modules: Small Shield Booster I, Medium Shield Booster I, Large Shield Booster I, and X-Large Shield Booster I. There are also faction and tech 2 variants available."

---

## Multi-Tool Workflows

### Example 3: Multi-Region Price Comparison

**Query:** "Compare Tritanium prices across all major trade hubs and tell me where it's cheapest to buy."

**Autonomy Level:** L1 (RECOMMENDATIONS)

**Agent Flow (2 iterations):**

**Iteration 1:**
```
1. LLM identifies need for hub information
2. Calls get_trade_hubs tool
3. Returns: {Jita, Amarr, Dodixie, Rens, Hek}
```

**Iteration 2:**
```
1. LLM needs price for each hub
2. Calls get_market_stats 5 times (one per hub):
   - Jita (The Forge): 3.95 ISK
   - Amarr (Domain): 4.10 ISK
   - Dodixie (Sinq Laison): 4.05 ISK
   - Rens (Heimatar): 4.20 ISK
   - Hek (Metropolis): 4.15 ISK
3. LLM compares prices and identifies cheapest
```

**Tool Calls:**
```json
// Iteration 1
{"tool": "get_trade_hubs", "arguments": {}}

// Iteration 2 (5 parallel calls)
{"tool": "get_market_stats", "arguments": {"type_id": 34, "region_id": 10000002}}
{"tool": "get_market_stats", "arguments": {"type_id": 34, "region_id": 10000043}}
{"tool": "get_market_stats", "arguments": {"type_id": 34, "region_id": 10000032}}
{"tool": "get_market_stats", "arguments": {"type_id": 34, "region_id": 10000030}}
{"tool": "get_market_stats", "arguments": {"type_id": 34, "region_id": 10000042}}
```

**Final Answer:**
> "I've checked Tritanium prices across all major trade hubs:
> - Jita: 3.95 ISK (cheapest)
> - Dodixie: 4.05 ISK
> - Amarr: 4.10 ISK
> - Hek: 4.15 ISK
> - Rens: 4.20 ISK
>
> Jita has the lowest price at 3.95 ISK per unit."

**Performance:**
- Total tools: 6 (1 hub lookup + 5 price checks)
- Tool execution: ~200ms each = 1.2 seconds total
- LLM processing: 2 iterations × 800ms = 1.6 seconds
- Total time: ~3 seconds

---

### Example 4: Production Chain Analysis

**Query:** "What materials do I need to build a Stabber cruiser?"

**Autonomy Level:** L2 (ASSISTED)

**Agent Flow (3 iterations):**

**Iteration 1:**
```
1. Search for "Stabber"
2. Identify type_id: 622
```

**Iteration 2:**
```
1. Get production materials for Stabber
2. Returns list of components:
   - Tritanium: 250,000
   - Pyerite: 100,000
   - Mexallon: 25,000
   - Isogen: 6,000
   - Nocxium: 1,500
   - Megacyte: 200
```

**Iteration 3:**
```
1. Get current market prices for materials
2. Calculate total cost
3. Return formatted breakdown
```

**Final Answer:**
> "To build a Stabber cruiser, you need:
>
> **Minerals:**
> - Tritanium: 250,000 units (~988k ISK)
> - Pyerite: 100,000 units (~800k ISK)
> - Mexallon: 25,000 units (~500k ISK)
> - Isogen: 6,000 units (~72k ISK)
> - Nocxium: 1,500 units (~60k ISK)
> - Megacyte: 200 units (~8k ISK)
>
> **Total Material Cost:** ~2.4M ISK (Jita buy prices)"

---

## Authorization Scenarios

### Example 5: Authorization Denial (READ_ONLY)

**Query:** "Create a market order to sell 1000 Tritanium at 5 ISK each"

**Autonomy Level:** L0 (READ_ONLY)

**Agent Flow:**
```
1. LLM identifies need for market_order_create tool
2. AuthorizationChecker evaluates:
   - Tool: market_order_create (MODERATE - L2)
   - User autonomy: READ_ONLY (L0)
   - Decision: DENIED (L2 > L0)
3. Tool blocked with error message
4. LLM receives error in tool result
5. Explains limitation to user
```

**SSE Event Stream:**
```
data: {"type":"thinking","iteration":1}

data: {"type":"authorization_denied","tool":"market_order_create","reason":"MODERATE operations not allowed at READ_ONLY autonomy level"}

data: {"type":"text","text":"I cannot create market orders with your current autonomy level (READ_ONLY). This operation requires at least ASSISTED (L2) autonomy. You can view market data and get recommendations, but I cannot execute trades."}

data: {"type":"done","message_id":"msg-xyz789"}
```

**Final Answer:**
> "I cannot create market orders with your current autonomy level (READ_ONLY). This operation requires at least ASSISTED (L2) autonomy. You can view market data and get recommendations, but I cannot execute trades."

---

### Example 6: Plan Approval Required (RECOMMENDATIONS)

**Query:** "Add Stabber to my shopping list"

**Autonomy Level:** L1 (RECOMMENDATIONS)

**Agent Flow:**
```
1. LLM wants to call shopping_list_add_item (MODERATE - L2)
2. ApprovalManager evaluates:
   - Tool risk: MODERATE (L2)
   - User autonomy: RECOMMENDATIONS (L1)
   - Decision: REQUIRES_APPROVAL (L2 > L1)
3. Creates Plan with 1 step
4. Emits waiting_for_approval event
5. Execution pauses
```

**SSE Event Stream:**
```
data: {"type":"thinking","iteration":1}

data: {"type":"waiting_for_approval","plan_id":"plan-123","purpose":"Add Stabber to shopping list"}

data: {"type":"text","text":"I've prepared a plan to add Stabber to your shopping list. This requires your approval since it will modify game data. Please review and approve the plan."}

data: {"type":"done","message_id":"msg-approval"}
```

**Plan Object:**
```json
{
  "id": "plan-123",
  "session_id": "sess-456",
  "purpose": "Add Stabber to shopping list",
  "steps": [
    {
      "tool": "shopping_list_add_item",
      "arguments": {
        "list_id": "default",
        "type_id": 622,
        "quantity": 1
      },
      "risk_level": "MODERATE"
    }
  ],
  "max_risk_level": "MODERATE",
  "status": "pending_approval"
}
```

**User Action:** Approve via UI or API:
```bash
curl -X POST http://localhost:8001/agent/execute \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "sess-456",
    "plan_id": "plan-123",
    "character_id": 526379435
  }'
```

**After Approval:**
```
1. Plan executes
2. Tool shopping_list_add_item runs
3. Stabber added to list
4. Agent confirms completion
```

---

### Example 7: Auto-Execute at ASSISTED Level

**Query:** "Add Stabber to my shopping list"

**Autonomy Level:** L2 (ASSISTED)

**Agent Flow:**
```
1. LLM wants to call shopping_list_add_item (MODERATE - L2)
2. ApprovalManager evaluates:
   - Tool risk: MODERATE (L2)
   - User autonomy: ASSISTED (L2)
   - Decision: AUTO_EXECUTE (L2 == L2)
3. Tool executes immediately
4. No approval needed
```

**SSE Event Stream:**
```
data: {"type":"thinking","iteration":1}

data: {"type":"tool_call_started","tool":"shopping_list_add_item","arguments":{"list_id":"default","type_id":622,"quantity":1}}

data: {"type":"tool_call_completed","tool":"shopping_list_add_item"}

data: {"type":"text","text":"I've added Stabber to your shopping list."}

data: {"type":"done","message_id":"msg-auto"}
```

**Final Answer:**
> "I've added Stabber to your shopping list."

**Note:** Same query, different autonomy level = different behavior

---

## Error Handling

### Example 8: Retry on Transient Error

**Query:** "What's the production cost for a Stabber?"

**Scenario:** ESI API temporarily slow/unavailable

**Agent Flow:**
```
1. LLM calls get_production_cost tool
2. Attempt 1: Timeout (ESI slow)
   - RetryHandler catches timeout
   - Waits 1 second
3. Attempt 2: Timeout again
   - RetryHandler catches timeout
   - Waits 2 seconds (exponential backoff)
4. Attempt 3: SUCCESS
   - Returns production cost data
5. LLM formats answer
```

**Internal Logs:**
```
[2025-12-29 10:15:32] INFO: Executing tool: get_production_cost
[2025-12-29 10:15:33] WARNING: Attempt 1/4 failed: Request timeout. Retrying in 1.0s...
[2025-12-29 10:15:35] WARNING: Attempt 2/4 failed: Request timeout. Retrying in 2.0s...
[2025-12-29 10:15:38] INFO: Retry succeeded on attempt 3
```

**SSE Event Stream:** (No error events - handled internally)
```
data: {"type":"thinking","iteration":1}

data: {"type":"tool_call_started","tool":"get_production_cost","arguments":{"type_id":622}}

[3-second delay with internal retries]

data: {"type":"tool_call_completed","tool":"get_production_cost"}

data: {"type":"text","text":"The production cost for a Stabber is approximately 2.4M ISK..."}

data: {"type":"done","message_id":"msg-retry"}
```

**User Experience:** Seamless - no indication of retries

---

### Example 9: Permanent Error (Non-Retryable)

**Query:** "What's the price of item ID 999999999?"

**Scenario:** Invalid item ID (doesn't exist in database)

**Agent Flow:**
```
1. LLM calls get_item_info with invalid ID
2. Tool executes, returns error
3. RetryHandler recognizes non-retryable error
4. Returns error to LLM immediately (no retries)
5. LLM informs user
```

**SSE Event Stream:**
```
data: {"type":"thinking","iteration":1}

data: {"type":"tool_call_started","tool":"get_item_info","arguments":{"type_id":999999999}}

data: {"type":"tool_call_failed","tool":"get_item_info","error":"Item not found","retries_exhausted":false}

data: {"type":"text","text":"I couldn't find an item with ID 999999999. It doesn't exist in the EVE Online database. Could you provide a valid item name or ID?"}

data: {"type":"done","message_id":"msg-error"}
```

**Final Answer:**
> "I couldn't find an item with ID 999999999. It doesn't exist in the EVE Online database. Could you provide a valid item name or ID?"

---

### Example 10: All Retries Exhausted

**Query:** "Get market stats for Tritanium"

**Scenario:** ESI completely down

**Agent Flow:**
```
1. LLM calls get_market_stats
2. Attempt 1: Timeout - wait 1s
3. Attempt 2: Timeout - wait 2s
4. Attempt 3: Timeout - wait 4s
5. Attempt 4: Timeout - GIVE UP
6. Return error to LLM with retry context
```

**SSE Event Stream:**
```
data: {"type":"thinking","iteration":1}

data: {"type":"tool_call_started","tool":"get_market_stats","arguments":{"type_id":34,"region_id":10000002}}

[~7 seconds of retries]

data: {"type":"tool_call_failed","tool":"get_market_stats","error":"Request timeout after multiple attempts","retries_exhausted":true}

data: {"type":"text","text":"I'm having trouble connecting to the market data service. It appears to be temporarily unavailable. Please try again in a few minutes."}

data: {"type":"done","message_id":"msg-exhausted"}
```

**Final Answer:**
> "I'm having trouble connecting to the market data service. It appears to be temporarily unavailable. Please try again in a few minutes."

---

## Complex Queries

### Example 11: Multi-Step Analysis

**Query:** "Find profitable manufacturing opportunities in Jita right now"

**Autonomy Level:** L2 (ASSISTED)

**Agent Flow (4 iterations, 12 tools):**

**Iteration 1:** Get market opportunities
```
Tool: get_manufacturing_opportunities
Args: {region_id: 10000002, min_roi: 15, limit: 5}
Result: [
  {type_id: 648, profit: 500000, roi: 25%},
  {type_id: 649, profit: 450000, roi: 22%},
  {type_id: 650, profit: 400000, roi: 18%}
]
```

**Iteration 2:** Get item names
```
Tools: get_item_info (3 calls)
- 648 → "Scorpion"
- 649 → "Raven"
- 650 → "Typhoon"
```

**Iteration 3:** Get production costs
```
Tools: get_production_cost (3 calls)
- Scorpion: 2M ISK materials
- Raven: 2.05M ISK materials
- Typhoon: 2.2M ISK materials
```

**Iteration 4:** Get market prices
```
Tools: get_market_stats (3 calls)
- Scorpion: 2.5M sell price
- Raven: 2.5M sell price
- Typhoon: 2.6M sell price
```

**Final Answer:**
> "I found 3 profitable manufacturing opportunities in Jita right now:
>
> 1. **Scorpion Battleship** - Most Profitable
>    - Material Cost: 2.0M ISK
>    - Market Price: 2.5M ISK
>    - Profit: 500k ISK (25% ROI)
>
> 2. **Raven Battleship**
>    - Material Cost: 2.05M ISK
>    - Market Price: 2.5M ISK
>    - Profit: 450k ISK (22% ROI)
>
> 3. **Typhoon Battleship**
>    - Material Cost: 2.2M ISK
>    - Market Price: 2.6M ISK
>    - Profit: 400k ISK (18% ROI)
>
> I recommend starting with Scorpion for the highest ROI."

**Performance:**
- Total tools: 12 (1 scan + 3 names + 3 costs + 3 prices)
- Iterations: 4 (within 5-iteration limit)
- Total time: ~4-5 seconds

---

### Example 12: Combat Intelligence Query

**Query:** "Which ships are getting destroyed most in Venal right now and what's the demand for their replacement parts?"

**Autonomy Level:** L2 (ASSISTED)

**Agent Flow (3 iterations, 8 tools):**

**Iteration 1:** Get region info and recent losses
```
Tool: search_region
Args: {query: "Venal"}
Result: {region_id: 10000015}

Tool: get_combat_losses
Args: {region_id: 10000015, days: 7}
Result: [
  {type_id: 587, count: 150},  # Rifter
  {type_id: 588, count: 120},  # Merlin
  {type_id: 589, count: 100}   # Tristan
]
```

**Iteration 2:** Get ship names and common fittings
```
Tools: get_item_info (3 calls)
+ get_common_modules (3 calls)
```

**Iteration 3:** Analyze market demand
```
Tools: get_war_demand_analysis
Args: {region_id: 10000015}
Result: Market gaps for ship modules
```

**Final Answer:**
> "In Venal over the past week, the most destroyed ships are:
>
> 1. **Rifter** - 150 destroyed
> 2. **Merlin** - 120 destroyed
> 3. **Tristan** - 100 destroyed
>
> **Market Demand Analysis:**
> - Light Missile Launchers: High demand (used on Rifter/Merlin)
> - Small Shield Boosters: Moderate demand
> - Warp Disruptors: High demand (PvP fitting)
>
> These modules show strong arbitrage potential in Venal due to combat activity."

---

## Testing Scenarios

### Test 1: Read-Only Tool (Auto-Execute)

**Setup:**
```json
{
  "session_id": "test-session-1",
  "autonomy_level": 1,
  "query": "Search for shield boosters"
}
```

**Expected Behavior:**
- ✅ Tool executes immediately (no approval)
- ✅ search_item is READ_ONLY (L0)
- ✅ Returns results within 2 seconds
- ✅ No authorization_denied events

**Verification:**
```bash
curl -X POST http://localhost:8001/agent/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"session_id":"test-session-1","message":"Search for shield boosters","character_id":526379435}' | grep -E "tool_call_started|authorization_denied"
```

---

### Test 2: Moderate Tool (Requires Approval at L1)

**Setup:**
```json
{
  "session_id": "test-session-2",
  "autonomy_level": 1,
  "query": "Add Stabber to my shopping list"
}
```

**Expected Behavior:**
- ✅ Tool does NOT execute automatically
- ✅ waiting_for_approval event emitted
- ✅ Plan created with shopping_list_add_item step
- ✅ User must approve via /agent/execute

**Verification:**
```bash
# Should see waiting_for_approval event
curl -X POST http://localhost:8001/agent/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"session_id":"test-session-2","message":"Add Stabber to my shopping list","character_id":526379435}' | grep "waiting_for_approval"
```

---

### Test 3: Error Recovery (Retry Logic)

**Setup:** Simulate ESI timeout

**Expected Behavior:**
- ✅ Tool retries 3 times
- ✅ Exponential backoff (1s, 2s, 4s)
- ✅ If successful, no error shown to user
- ✅ If all fail, tool_call_failed event emitted

**Verification:**
```python
# Mock ESI to fail twice, succeed third time
def test_retry_recovery():
    call_count = 0

    def flaky_esi_call():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise RetryableError("Timeout")
        return {"lowest_sell": 3.95}

    # Should succeed after 2 retries
    result = retry_handler.execute_with_retry(flaky_esi_call)
    assert result == {"lowest_sell": 3.95}
    assert call_count == 3
```

---

### Test 4: Authorization Block (L0 autonomy)

**Setup:**
```json
{
  "session_id": "test-session-4",
  "autonomy_level": 0,
  "query": "Create a market sell order for 1000 Tritanium"
}
```

**Expected Behavior:**
- ✅ Tool blocked immediately
- ✅ authorization_denied event emitted
- ✅ Clear error message to user
- ✅ LLM explains limitation

**Verification:**
```bash
curl -X POST http://localhost:8001/agent/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"session_id":"test-session-4","message":"Create a market sell order","character_id":526379435}' | grep "authorization_denied"
```

---

### Test 5: Multi-Tool Query (Complex)

**Setup:**
```json
{
  "session_id": "test-session-5",
  "autonomy_level": 2,
  "query": "Compare Tritanium prices across all trade hubs"
}
```

**Expected Behavior:**
- ✅ Multiple tool calls (6+)
- ✅ Multiple iterations (2-3)
- ✅ All tools execute successfully
- ✅ Final answer includes all hubs
- ✅ Completes within 5 seconds

**Verification:**
```bash
# Count tool_call_started events
curl -X POST http://localhost:8001/agent/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"session_id":"test-session-5","message":"Compare Tritanium prices across all trade hubs","character_id":526379435}' | grep -c "tool_call_started"

# Should be >= 6 (1 hub lookup + 5 price checks)
```

---

## Best Practices

### 1. Choose Appropriate Autonomy Level

**READ_ONLY (L0):** For exploration, learning, price checking
```json
{"autonomy_level": 0}
```

**RECOMMENDATIONS (L1):** For decision support, analysis, recommendations
```json
{"autonomy_level": 1}
```

**ASSISTED (L2):** For semi-autonomous operations, shopping, planning
```json
{"autonomy_level": 2}
```

### 2. Handle Streaming Events

**Good Practice:**
```javascript
const eventSource = new EventSource('/agent/chat/stream');

eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);

    switch (data.type) {
        case 'text':
            appendToChat(data.text);
            break;
        case 'tool_call_started':
            showToolIndicator(data.tool);
            break;
        case 'tool_call_completed':
            hideToolIndicator();
            break;
        case 'error':
            showError(data.error);
            break;
    }
};
```

### 3. Provide Clear Queries

**Bad Query:** "prices"
**Good Query:** "What is the current sell price of Tritanium in Jita?"

**Bad Query:** "ships"
**Good Query:** "Which battleships are most profitable to manufacture in Jita?"

### 4. Monitor Performance

```javascript
const startTime = Date.now();

eventSource.addEventListener('done', () => {
    const duration = Date.now() - startTime;
    console.log(`Query completed in ${duration}ms`);
});
```

---

## Conclusion

Phase 7 enables natural language interaction with EVE Online data and operations. The agentic loop handles complex multi-step queries autonomously while respecting user-defined limits.

**Key Patterns:**
- Simple queries: 1 iteration, 1 tool, ~2 seconds
- Multi-tool queries: 2-3 iterations, 5-10 tools, ~4 seconds
- Authorization: Automatic for allowed tools, approval for risky ones
- Errors: Automatic retry for transient issues, clear messages for permanent ones

**Next Steps:**
- Experiment with different autonomy levels
- Test complex multi-step queries
- Monitor tool execution performance
- Provide feedback on tool results

---

**Related Documentation:**
- [Phase 7 Tool Execution](phase7-tool-execution.md) - Technical details
- [Phase 7 Browser Testing Report](phase7-browser-testing-report.md) - Real-world testing
- [Phase 6 API Documentation](phase6-api-documentation.md) - Foundation

**Last Updated:** 2025-12-29
