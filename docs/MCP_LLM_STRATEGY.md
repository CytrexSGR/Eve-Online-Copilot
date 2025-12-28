# EVE Co-Pilot: MCP-LLM Integration Strategy

**Status:** Analysis & Roadmap
**Date:** 2025-12-28
**Version:** 2.0

---

## Executive Summary

**Die entscheidende Erkenntnis:** Ihr habt bereits 80% einer produktionsreifen AI-Platform gebaut.

Mit **115 MCP-Tools** + **ToolOrchestrator** + **AnthropicClient** + **WebSocket** habt ihr die kritische Infrastruktur.

**Was fehlt:** Nicht Technologie, sondern **Orchestrierung-Patterns** und **Use-Case-Fokus**.

---

## 1. IST-Analyse: Was bereits existiert ✅

### 1.1 MCP-Ebene (Backend)

```
routers/mcp/
├── tools/          # 115 Tools in 13 Kategorien
│   ├── market.py           (12 Tools)
│   ├── production.py       (14 Tools)
│   ├── war_room.py         (16 Tools)
│   ├── shopping.py         (25 Tools)
│   ├── character.py        (12 Tools)
│   └── ...
├── handlers/       # API Proxy
└── __init__.py     # Router mit 4 Endpoints
```

**Bewertung:** ✅ Production-ready, vollständig dokumentiert

### 1.2 AI-Copilot-Server

```
copilot_server/
├── llm/
│   ├── anthropic_client.py     # Claude API Integration
│   └── conversation_manager.py # Conversation Memory
├── mcp/
│   ├── client.py              # MCP Tool Calls
│   └── orchestrator.py        # Agentic Workflows ⭐
├── websocket/                 # Real-time Communication
├── audio/                     # STT/TTS
└── main.py                    # FastAPI Server
```

**Bewertung:** ✅ Infrastruktur komplett, Orchestrator implementiert

### 1.3 Vorhandene Capabilities

| Komponente | Status | Details |
|------------|--------|---------|
| **Tool Discovery** | ✅ | `/mcp/tools/list` |
| **Tool Execution** | ✅ | `MCPClient.call_tool()` |
| **LLM Integration** | ✅ | `AnthropicClient` mit Tool-Support |
| **Agentic Loop** | ✅ | `ToolOrchestrator.execute_workflow()` |
| **Conversation Memory** | ✅ | `ConversationManager` |
| **WebSocket** | ✅ | Real-time Communication |
| **Audio Pipeline** | ✅ | Whisper (STT) + TTS |
| **Session Management** | ✅ | Multi-User Support |

---

## 2. SOLL-Analyse: Konkrete Gaps

### 2.1 Orchestrierung-Patterns (CRITICAL)

**Problem:** Der aktuelle `ToolOrchestrator` ist ein **generischer Loop**.

**Was fehlt:**
- ❌ Domänenspezifische Workflows (z.B. "Market Analysis", "Production Planning")
- ❌ Tool-Chaining Templates
- ❌ Kontextuelle Tool-Auswahl
- ❌ Fehler-Recovery-Strategien
- ❌ Zwischenergebnis-Validierung

**Impact:** Hoch - LLM muss jedes Mal von Grund auf planen

### 2.2 Meta-Tools (HIGH PRIORITY)

**Problem:** 115 einzelne Tools = kognitive Überlast für LLM.

**Lösung:** Abstraktionsschicht mit Composite-Tools.

**Beispiele:**

```python
# Statt: 5 separate Tool-Calls
search_item → get_market_prices → calculate_production_cost →
compare_regions → calculate_arbitrage

# Wird: 1 Meta-Tool
analyze_item_profitability(type_id, strategy="arbitrage")
  → Führt intern 5-Tool-Workflow aus
  → Gibt strukturiertes Ergebnis
```

**Impact:** Mittel-Hoch - Reduziert Token-Kosten und Latenz drastisch

### 2.3 Kontextuelle System-Prompts (MEDIUM)

**Problem:** Generischer System-Prompt für alle Use-Cases.

**Lösung:** Dynamische Prompts basierend auf:
- User-Rolle (Trader, Producer, FC)
- Aktueller Task (Market Analysis, War Intel, Shopping)
- Verfügbare Tools (relevante Subset laden)

**Impact:** Mittel - Verbessert Antwortqualität signifikant

### 2.4 Tool-Result-Caching (MEDIUM)

**Problem:** Identische Tool-Calls werden wiederholt.

**Beispiel:**
```
User: "Analyse Tritanium"
  → get_market_prices(Tritanium, Jita)
User: "Now Pyerite"
  → get_market_prices(Pyerite, Jita)
User: "Compare both"
  → get_market_prices(Tritanium, Jita) ← REDUNDANT
  → get_market_prices(Pyerite, Jita) ← REDUNDANT
```

**Lösung:** Session-basierter Cache (TTL: 5-10 Min).

**Impact:** Mittel - Spart API-Calls + Kosten

### 2.5 Structured Output Enforcement (LOW)

**Problem:** LLM-Antworten sind unstrukturiert.

**Lösung:** JSON-Mode oder Output-Schema erzwingen.

```python
response_format = {
    "summary": str,
    "recommendations": List[Dict],
    "data_sources": List[str],
    "confidence": float,
    "next_actions": List[str]
}
```

**Impact:** Niedrig-Mittel - Verbessert UX, nicht Kern-Funktionalität

---

## 3. Konkrete Implementierungsvorschläge

### 3.1 Workflow Templates (PHASE 1 - Critical)

**Ziel:** Vordefinierte Multi-Tool-Workflows für häufige Tasks.

#### Implementierung:

```python
# copilot_server/workflows/templates.py

class WorkflowTemplate:
    """Base class for workflow templates."""

    name: str
    description: str
    tools: List[str]  # Required tools

    async def execute(self, orchestrator, **kwargs) -> Dict[str, Any]:
        """Execute workflow."""
        raise NotImplementedError


class MarketAnalysisWorkflow(WorkflowTemplate):
    """Analyze item profitability across regions."""

    name = "market_analysis"
    description = "Complete market analysis for an item"
    tools = [
        "search_item",
        "get_market_stats",
        "compare_regions",
        "calculate_arbitrage"
    ]

    async def execute(self, orchestrator, item_query: str):
        # Step 1: Search item
        item_result = orchestrator.mcp.call_tool(
            "search_item",
            {"q": item_query}
        )

        if "error" in item_result:
            return item_result

        type_id = item_result["items"][0]["typeID"]

        # Step 2: Get market stats for major hubs
        hubs = [10000002, 10000043, 10000030, 10000032]  # Jita, Amarr, Rens, Dodixie
        market_data = []

        for region_id in hubs:
            stats = orchestrator.mcp.call_tool(
                "get_market_stats",
                {"region_id": region_id, "type_id": type_id}
            )
            market_data.append(stats)

        # Step 3: Calculate arbitrage
        arbitrage = orchestrator.mcp.call_tool(
            "get_arbitrage_opportunities",
            {"type_id": type_id}
        )

        # Step 4: LLM synthesizes results
        synthesis_prompt = f"""
        Analyze this market data for {item_query}:

        Market Stats: {market_data}
        Arbitrage: {arbitrage}

        Provide:
        1. Best buy location
        2. Best sell location
        3. Profit margin
        4. Risk assessment
        """

        response = await orchestrator.llm.chat(
            messages=[{"role": "user", "content": synthesis_prompt}],
            max_tokens=1000
        )

        return {
            "workflow": self.name,
            "raw_data": {
                "market_stats": market_data,
                "arbitrage": arbitrage
            },
            "analysis": response["content"][0]["text"]
        }


class ProductionPlanningWorkflow(WorkflowTemplate):
    """Plan production with material sourcing."""

    name = "production_planning"
    tools = [
        "search_item",
        "get_production_chains",
        "get_materials_required",
        "compare_regional_prices",
        "calculate_production_cost"
    ]

    async def execute(self, orchestrator, item_query: str, quantity: int = 1):
        # Step 1: Get item and production chain
        item = orchestrator.mcp.call_tool("search_item", {"q": item_query})
        type_id = item["items"][0]["typeID"]

        chain = orchestrator.mcp.call_tool(
            "get_production_chains",
            {"type_id": type_id}
        )

        # Step 2: Get all required materials
        materials = orchestrator.mcp.call_tool(
            "get_chain_materials",
            {"type_id": type_id}
        )

        # Step 3: Price comparison for materials
        material_prices = []
        for material in materials["materials"]:
            prices = orchestrator.mcp.call_tool(
                "compare_regions",
                {"type_id": material["typeID"]}
            )
            material_prices.append(prices)

        # Step 4: Calculate total production cost
        cost = orchestrator.mcp.call_tool(
            "calculate_production_cost",
            {
                "type_id": type_id,
                "quantity": quantity,
                "materials": materials
            }
        )

        # Step 5: LLM creates production plan
        plan_prompt = f"""
        Create a production plan for {quantity}x {item_query}:

        Production Chain: {chain}
        Materials Needed: {materials}
        Material Prices: {material_prices}
        Total Cost: {cost}

        Provide:
        1. Shopping list (sorted by best region)
        2. Production steps
        3. Timeline estimate
        4. Profit calculation (if market price available)
        """

        response = await orchestrator.llm.chat(
            messages=[{"role": "user", "content": plan_prompt}],
            max_tokens=2000
        )

        return {
            "workflow": self.name,
            "raw_data": {
                "chain": chain,
                "materials": materials,
                "material_prices": material_prices,
                "cost": cost
            },
            "plan": response["content"][0]["text"]
        }


class WarRoomBriefingWorkflow(WorkflowTemplate):
    """Generate combat intelligence briefing."""

    name = "war_room_briefing"
    tools = [
        "get_war_summary",
        "get_combat_hotspots",
        "get_sov_campaigns",
        "get_fw_hotspots",
        "get_top_ships_destroyed"
    ]

    async def execute(self, orchestrator, region_id: Optional[int] = None):
        # Step 1: Galaxy summary or regional focus
        if region_id:
            summary = orchestrator.mcp.call_tool(
                "get_war_losses",
                {"region_id": region_id}
            )
        else:
            summary = orchestrator.mcp.call_tool("get_war_summary", {})

        # Step 2: Combat hotspots
        hotspots = orchestrator.mcp.call_tool("get_combat_hotspots", {})

        # Step 3: Sovereignty campaigns
        sov = orchestrator.mcp.call_tool("get_sov_campaigns", {})

        # Step 4: FW activity
        fw = orchestrator.mcp.call_tool("get_fw_hotspots", {})

        # Step 5: Top destroyed ships
        top_ships = orchestrator.mcp.call_tool("get_top_ships_destroyed", {})

        # Step 6: LLM creates briefing
        briefing_prompt = f"""
        Create a War Room Intelligence Briefing:

        Combat Summary: {summary}
        Active Hotspots: {hotspots}
        Sovereignty Campaigns: {sov}
        FW Activity: {fw}
        Top Ship Losses: {top_ships}

        Format as:
        1. SITREP (Situation Report)
        2. Threat Assessment
        3. Market Opportunities (from combat losses)
        4. Recommended Actions
        """

        response = await orchestrator.llm.chat(
            messages=[{"role": "user", "content": briefing_prompt}],
            max_tokens=2500
        )

        return {
            "workflow": self.name,
            "raw_data": {
                "summary": summary,
                "hotspots": hotspots,
                "sov": sov,
                "fw": fw,
                "top_ships": top_ships
            },
            "briefing": response["content"][0]["text"]
        }


# Registry
WORKFLOW_TEMPLATES = {
    "market_analysis": MarketAnalysisWorkflow(),
    "production_planning": ProductionPlanningWorkflow(),
    "war_room_briefing": WarRoomBriefingWorkflow()
}


def get_workflow(name: str) -> Optional[WorkflowTemplate]:
    """Get workflow template by name."""
    return WORKFLOW_TEMPLATES.get(name)


def list_workflows() -> List[Dict[str, str]]:
    """List all available workflows."""
    return [
        {
            "name": wf.name,
            "description": wf.description,
            "tools": wf.tools
        }
        for wf in WORKFLOW_TEMPLATES.values()
    ]
```

#### Integration in ToolOrchestrator:

```python
# copilot_server/mcp/orchestrator.py

from ..workflows.templates import get_workflow, list_workflows

class ToolOrchestrator:
    # ... existing code ...

    async def execute_template_workflow(
        self,
        workflow_name: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute a predefined workflow template.

        Args:
            workflow_name: Name of workflow template
            **kwargs: Workflow-specific parameters

        Returns:
            Workflow execution result
        """
        workflow = get_workflow(workflow_name)
        if not workflow:
            return {
                "error": f"Workflow '{workflow_name}' not found",
                "available": list_workflows()
            }

        logger.info(f"Executing workflow template: {workflow_name}")

        try:
            result = await workflow.execute(self, **kwargs)
            return result
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            return {
                "error": f"Workflow execution failed: {str(e)}",
                "workflow": workflow_name
            }

    async def suggest_workflow(self, user_query: str) -> Optional[str]:
        """
        Suggest appropriate workflow for user query.

        Args:
            user_query: User's natural language query

        Returns:
            Suggested workflow name or None
        """
        query_lower = user_query.lower()

        # Simple keyword matching (could be replaced with embeddings)
        if any(word in query_lower for word in ["market", "price", "arbitrage", "trade"]):
            return "market_analysis"
        elif any(word in query_lower for word in ["build", "produce", "manufacture", "materials"]):
            return "production_planning"
        elif any(word in query_lower for word in ["war", "combat", "pvp", "kills", "sov"]):
            return "war_room_briefing"

        return None
```

### 3.2 Dynamische System-Prompts (PHASE 1)

```python
# copilot_server/prompts/dynamic_prompts.py

class PromptBuilder:
    """Build context-specific system prompts."""

    BASE_PROMPT = """You are EVE Co-Pilot, an AI assistant for EVE Online players.

You have access to 115 MCP tools across 13 categories:
- Market Analysis
- Production Planning
- War Room Intelligence
- Shopping & Logistics
- Character Management
- And more...

CRITICAL RULES:
1. ALWAYS use tools when data is needed - NEVER make up numbers
2. Chain multiple tools for complex analyses
3. Cite your data sources
4. Be concise but thorough
5. Format numbers with commas (e.g., 1,000,000 ISK)
"""

    @staticmethod
    def build_prompt(
        user_role: Optional[str] = None,
        available_categories: Optional[List[str]] = None,
        character_id: Optional[int] = None,
        region_id: int = 10000002
    ) -> str:
        """
        Build context-specific system prompt.

        Args:
            user_role: User's primary role (trader, producer, fc, etc.)
            available_categories: Tool categories to focus on
            character_id: User's character ID (for personalization)
            region_id: User's current region

        Returns:
            Customized system prompt
        """
        prompt = PromptBuilder.BASE_PROMPT

        # Role-specific guidance
        if user_role == "trader":
            prompt += """

YOUR FOCUS: Market Analysis & Arbitrage
- Prioritize profit margins and trading volumes
- Always check multiple regions
- Consider transport costs and time
- Flag high-risk opportunities"""

        elif user_role == "producer":
            prompt += """

YOUR FOCUS: Production Planning & Materials
- Optimize material sourcing (build vs buy)
- Consider ME/TE levels
- Track market trends for outputs
- Suggest production chains"""

        elif user_role == "fc":  # Fleet Commander
            prompt += """

YOUR FOCUS: War Room Intelligence
- Provide tactical intel on hotspots
- Track enemy doctrines and losses
- Identify supply opportunities
- Monitor sovereignty campaigns"""

        # Available tools context
        if available_categories:
            prompt += f"""

AVAILABLE TOOL CATEGORIES: {', '.join(available_categories)}
Focus your tool usage on these categories."""

        # Personalization
        if character_id:
            prompt += f"""

USER CONTEXT:
- Character ID: {character_id}
- Primary Region: {region_id}
You can access this user's wallet, assets, and skills."""

        return prompt


# copilot_server/llm/anthropic_client.py

class AnthropicClient:
    # ... existing code ...

    async def chat_with_context(
        self,
        messages: List[Dict[str, Any]],
        user_context: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """
        Chat with contextual system prompt.

        Args:
            messages: Conversation messages
            user_context: User context (role, character_id, etc.)
            **kwargs: Additional chat parameters

        Returns:
            Claude response
        """
        from ..prompts.dynamic_prompts import PromptBuilder

        # Build dynamic system prompt
        system_prompt = PromptBuilder.build_prompt(
            user_role=user_context.get("role"),
            available_categories=user_context.get("tool_categories"),
            character_id=user_context.get("character_id"),
            region_id=user_context.get("region_id", 10000002)
        )

        return await self.chat(
            messages=messages,
            system=system_prompt,
            **kwargs
        )
```

### 3.3 Tool-Result-Caching (PHASE 2)

```python
# copilot_server/mcp/cache.py

from typing import Dict, Any, Optional
import time
import hashlib
import json

class ToolResultCache:
    """Session-based cache for tool results."""

    def __init__(self, ttl: int = 600):  # 10 minutes default
        """
        Initialize cache.

        Args:
            ttl: Time-to-live in seconds
        """
        self.ttl = ttl
        self.cache: Dict[str, Dict[str, Any]] = {}

    def _generate_key(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Generate cache key from tool call."""
        # Sort arguments for consistent hashing
        sorted_args = json.dumps(arguments, sort_keys=True)
        key_string = f"{tool_name}:{sorted_args}"
        return hashlib.sha256(key_string.encode()).hexdigest()

    def get(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached result if available and not expired.

        Args:
            tool_name: Tool name
            arguments: Tool arguments

        Returns:
            Cached result or None
        """
        key = self._generate_key(tool_name, arguments)

        if key in self.cache:
            entry = self.cache[key]
            if time.time() - entry["timestamp"] < self.ttl:
                return entry["result"]
            else:
                # Expired - remove
                del self.cache[key]

        return None

    def set(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        result: Dict[str, Any]
    ):
        """
        Cache a tool result.

        Args:
            tool_name: Tool name
            arguments: Tool arguments
            result: Tool result
        """
        key = self._generate_key(tool_name, arguments)
        self.cache[key] = {
            "result": result,
            "timestamp": time.time()
        }

    def clear(self):
        """Clear all cached results."""
        self.cache.clear()

    def cleanup_expired(self):
        """Remove expired cache entries."""
        current_time = time.time()
        expired_keys = [
            key for key, entry in self.cache.items()
            if current_time - entry["timestamp"] >= self.ttl
        ]
        for key in expired_keys:
            del self.cache[key]


# copilot_server/mcp/client.py

class MCPClient:
    def __init__(self, api_url: Optional[str] = None, enable_cache: bool = True):
        self.api_url = api_url or EVE_COPILOT_API_URL
        self.tools_cache: Optional[List[Dict[str, Any]]] = None

        # Tool result cache
        self.enable_cache = enable_cache
        self.result_cache = ToolResultCache(ttl=600) if enable_cache else None

    def call_tool(
        self,
        name: str,
        arguments: Dict[str, Any],
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """Call tool with optional caching."""

        # Check cache first
        if use_cache and self.enable_cache:
            cached = self.result_cache.get(name, arguments)
            if cached:
                logger.info(f"Tool '{name}' - cache hit")
                return cached

        # Execute tool
        result = self._execute_tool(name, arguments)

        # Cache result (only if successful)
        if use_cache and self.enable_cache and "error" not in result:
            self.result_cache.set(name, arguments, result)

        return result

    def _execute_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tool via API (existing implementation)."""
        try:
            response = requests.post(
                f"{self.api_url}/mcp/tools/call",
                json={"name": name, "arguments": arguments},
                timeout=60
            )
            response.raise_for_status()
            result = response.json()
            logger.info(f"Tool '{name}' executed successfully")
            return result
        except Exception as e:
            logger.error(f"Tool '{name}' failed: {e}")
            return {"error": str(e), "isError": True}
```

---

## 4. Priorisierte Roadmap

### PHASE 1: Foundation (Week 1-2) - CRITICAL

**Ziel:** Produktionsreife Workflows für 3 Kern-Use-Cases

| Task | Effort | Impact | Files |
|------|--------|--------|-------|
| Workflow Templates implementieren | 2d | 🔴 CRITICAL | `workflows/templates.py` |
| Dynamische System-Prompts | 1d | 🔴 CRITICAL | `prompts/dynamic_prompts.py` |
| Integration in Orchestrator | 1d | 🔴 CRITICAL | `mcp/orchestrator.py` |
| Testing & Validation | 1d | HIGH | `tests/test_workflows.py` |

**Deliverables:**
- ✅ 3 funktionierende Workflows (Market, Production, War Room)
- ✅ Rollenbasierte Prompts
- ✅ API-Endpoints für Workflow-Ausführung

### PHASE 2: Optimization (Week 3-4) - HIGH

| Task | Effort | Impact | Files |
|------|--------|--------|-------|
| Tool-Result-Caching | 1d | HIGH | `mcp/cache.py` |
| Fehler-Recovery | 1d | MEDIUM | `mcp/orchestrator.py` |
| Token-Usage-Tracking | 0.5d | MEDIUM | `llm/usage_tracker.py` |
| Performance-Monitoring | 0.5d | MEDIUM | `utils/metrics.py` |

**Deliverables:**
- ✅ 50% weniger redundante API-Calls
- ✅ Automatisches Error-Recovery
- ✅ Cost-Tracking Dashboard

### PHASE 3: Scale (Month 2) - MEDIUM

| Task | Effort | Impact | Files |
|------|--------|--------|-------|
| Meta-Tools (Composite) | 3d | MEDIUM | `routers/mcp/tools/meta.py` |
| Structured Output Enforcement | 1d | LOW-MEDIUM | `llm/output_schemas.py` |
| Multi-LLM Support | 2d | LOW | `llm/openai_client.py` |
| Embeddings-based Tool Search | 2d | LOW | `mcp/tool_search.py` |

**Deliverables:**
- ✅ 5 Meta-Tools für häufige Workflows
- ✅ JSON-formatierte Antworten
- ✅ OpenAI als Fallback

### PHASE 4: Advanced (Month 3+) - LOW

| Task | Effort | Impact | Files |
|------|--------|--------|-------|
| Agent Swarms | 5d | FUTURE | `agents/swarm.py` |
| Proactive Alerts | 2d | FUTURE | `agents/alert_agent.py` |
| Learning from Feedback | 3d | FUTURE | `ml/feedback_loop.py` |

---

## 5. Success Metrics

### Technical KPIs

| Metric | Baseline | Target (3 Months) |
|--------|----------|-------------------|
| Average Response Time | 8-12s | < 3s |
| Tool Calls per Query | 5-8 | 2-3 (via Meta-Tools) |
| Cache Hit Rate | 0% | > 60% |
| Token Cost per Query | ~15k tokens | < 5k tokens |
| Error Rate | ~10% | < 2% |

### Business KPIs

| Metric | Target |
|--------|--------|
| Daily Active Workflows | 100+ executions |
| User Satisfaction | > 4.5/5 |
| Time Saved vs Manual | > 80% |
| Market Opportunity Hit Rate | > 70% profitable |

---

## 6. Quick Wins (This Week)

### Immediate Actions (No Code)

1. **Define 3 Priority Use-Cases**
   - Talk to power users
   - Identify pain points
   - Map to workflows

2. **Test Current Orchestrator**
   ```bash
   # Test agentic loop
   curl -X POST http://localhost:8001/chat \
     -H "Content-Type: application/json" \
     -d '{
       "message": "Find me the most profitable T1 item to build in Jita",
       "session_id": "test-session"
     }'
   ```

3. **Measure Baseline**
   - Token usage
   - Response times
   - Tool call patterns

### Quick Code Improvements (1-2 hours)

**Add Workflow Suggestion to Chat Endpoint:**

```python
# copilot_server/main.py

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """Chat with AI Copilot."""
    # ... existing code ...

    # NEW: Suggest workflow
    suggested_workflow = await orchestrator.suggest_workflow(request.message)

    if suggested_workflow:
        logger.info(f"Suggested workflow: {suggested_workflow}")

        # Execute workflow template
        result = await orchestrator.execute_template_workflow(
            workflow_name=suggested_workflow,
            # Extract parameters from message (simple version)
        )

        return ChatResponse(
            response=result.get("analysis") or result.get("plan") or result.get("briefing"),
            session_id=session_id,
            tool_calls=result.get("raw_data", {})
        )

    # Fallback to generic agentic loop
    # ... existing code ...
```

---

## 7. Architektur-Diagramm

```
┌─────────────────────────────────────────────────────────────┐
│                         User Interface                       │
│  (Frontend Chat / Claude Desktop / Discord Bot)              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    Copilot Server (Port 8001)                │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │             ToolOrchestrator                          │   │
│  │                                                        │   │
│  │  ┌─────────────────┐    ┌──────────────────────┐    │   │
│  │  │ Workflow        │    │  AnthropicClient     │    │   │
│  │  │ Templates       │◄───┤  (Claude API)        │    │   │
│  │  └────────┬────────┘    └──────────┬───────────┘    │   │
│  │           │                         │                 │   │
│  │           ▼                         ▼                 │   │
│  │  ┌─────────────────┐    ┌──────────────────────┐    │   │
│  │  │ MCPClient       │    │  ConversationMgr     │    │   │
│  │  │ + Cache         │    │  + SessionMgr        │    │   │
│  │  └────────┬────────┘    └──────────────────────┘    │   │
│  └───────────┼──────────────────────────────────────────┘   │
└──────────────┼──────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────┐
│              Backend API (Port 8000)                         │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │           MCP Router (/mcp/*)                         │   │
│  │                                                        │   │
│  │  ┌──────────────────────────────────────────────┐    │   │
│  │  │           115 MCP Tools                       │    │   │
│  │  │  13 Categories × 1-25 Tools                   │    │   │
│  │  │                                               │    │   │
│  │  │  market | production | war_room | shopping   │    │   │
│  │  │  character | dashboard | research | ...      │    │   │
│  │  └──────────────────┬───────────────────────────┘    │   │
│  └─────────────────────┼────────────────────────────────┘   │
│                        │                                     │
│  ┌─────────────────────▼────────────────────────────────┐   │
│  │         Business Logic Services                       │   │
│  │  market_service | production_simulator |              │   │
│  │  killmail_service | shopping_service | ...            │   │
│  └─────────────────────┬────────────────────────────────┘   │
└────────────────────────┼────────────────────────────────────┘
                         │
                         ▼
               ┌─────────────────────┐
               │   PostgreSQL        │
               │   (EVE SDE + App)   │
               └─────────────────────┘
```

---

## 8. Fazit & Empfehlung

### Was ihr habt
✅ Eine **domänenspezifische MCP-Plattform** für EVE Online
✅ **115 produktionsreife Tools** mit klarer Struktur
✅ **Agentic Infrastructure** (Orchestrator, LLM, WebSocket)
✅ **80% einer AI-Platform** bereits implementiert

### Was fehlt
❌ **Use-Case-Fokussierung** - zu generisch
❌ **Workflow-Templates** - jede Query ist Neuplanung
❌ **Optimierung** - Caching, Error-Recovery

### Nächster Schritt
**Nicht mehr Technologie bauen, sondern Use-Cases produktifizieren.**

**Konkret:**
1. **Diese Woche:** Workflow-Templates für 3 Use-Cases (Market, Production, War Room)
2. **Nächste Woche:** Dynamische Prompts + Caching
3. **In 2 Wochen:** Erste produktive Nutzer

---

## 9. Anhang

### Code-Beispiele

Siehe:
- `workflows/templates.py` - Workflow-Implementierungen
- `prompts/dynamic_prompts.py` - Kontextuelle Prompts
- `mcp/cache.py` - Result-Caching

### Referenzen

- [PHASE1_COMPLETE.md](PHASE1_COMPLETE.md) - MCP Tool Expansion
- [ARCHITECTURE.md](../ARCHITECTURE.md) - System Architecture
- [Anthropic Agents Cookbook](https://docs.anthropic.com/en/docs/build-with-claude/agents)

---

**Next Review:** 2025-01-04
**Owner:** Development Team
**Status:** 🟢 Ready for Implementation
