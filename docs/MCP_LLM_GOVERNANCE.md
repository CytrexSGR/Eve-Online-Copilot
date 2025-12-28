# EVE Co-Pilot: AI Agent Governance & Strategy

**Companion Document zu:** [MCP_LLM_STRATEGY.md](MCP_LLM_STRATEGY.md)

**Status:** Strategic Framework
**Date:** 2025-12-28
**Version:** 1.0

---

## Executive Summary

**Kernfrage:** Ihr baut keine Feature-Erweiterung, sondern einen **AI Operations Layer für New Eden**.

Das erfordert nicht nur Technologie, sondern **explizite Governance**:
- Wer darf was?
- Wo liegt die Entscheidungshoheit?
- Wie evaluieren wir Erfolg?
- Wann Determinismus, wann Kreativität?

**Diese Fragen sind strategisch, nicht technisch.**

---

## 1. Agenten-Governance: Autonomiegrade

### 1.1 Autonomie-Spektrum

EVE Co-Pilot operiert auf **4 Autonomie-Leveln**:

| Level | Name | Beschreibung | LLM-Rolle | User-Rolle | Beispiel |
|-------|------|--------------|-----------|------------|----------|
| **L0** | **Read-Only Analytics** | Nur Daten lesen, analysieren, präsentieren | Analyst | Entscheider | "Analysiere Markt für Tritanium" |
| **L1** | **Recommendations** | Daten + Handlungsempfehlungen, User entscheidet | Berater | Entscheider | "Top 3 Arbitrage-Chancen" |
| **L2** | **Assisted Execution** | Vorbereitung, User bestätigt kritische Schritte | Assistent | Kontrolleur | "Erstelle Shopping-Liste (User approved)" |
| **L3** | **Supervised Autonomy** | Autonome Aktionen mit Limits, User kann abbrechen | Operator | Supervisor | "Auto-Trade bis 100M ISK Budget" |

**CRITICAL:** EVE Co-Pilot MVP operiert auf **L0-L1**.

### 1.2 Tool-Kategorisierung nach Risiko

Jedes der 115 MCP-Tools wird klassifiziert:

#### **READ-ONLY (Grün)** - Autonomie L0-L3
```
get_market_stats
get_production_chains
get_war_summary
search_item
get_character_wallet
...
```
**Risiko:** Keine
**Autorisierung:** Immer erlaubt
**Logging:** Standard

#### **WRITE-LOW-RISK (Gelb)** - Autonomie L1-L2
```
create_shopping_list
add_bookmark
mark_item_purchased
update_shopping_item
...
```
**Risiko:** User-Daten ändern (reversibel)
**Autorisierung:** Session-Token required
**Logging:** Alle Änderungen
**Confirmation:** Optional (User-Setting)

#### **WRITE-HIGH-RISK (Orange)** - Autonomie L2
```
set_build_decision (build vs buy)
delete_shopping_list
delete_bookmark
...
```
**Risiko:** Datenverlust möglich
**Autorisierung:** Session-Token + Confirmation
**Logging:** Detailed mit Rollback-Info
**Confirmation:** **MANDATORY**

#### **CRITICAL (Rot)** - Autonomie L3 ONLY
```
place_market_order (FUTURE)
transfer_isk (FUTURE)
contract_item (FUTURE)
...
```
**Risiko:** ISK-Verlust, irreversibel
**Autorisierung:** Explicit User Opt-In + 2FA
**Logging:** Full Audit Trail
**Confirmation:** **ALWAYS + Budget Limit**

**Status Quo:** Aktuell nur READ-ONLY + WRITE-LOW-RISK Tools.

### 1.3 Autonomie-Konfiguration

User kann per Session seinen **Autonomie-Level** setzen:

```python
# copilot_server/models/user_settings.py

from enum import Enum

class AutonomyLevel(Enum):
    """User's preferred autonomy level."""
    READ_ONLY = 0          # Only analytics, no writes
    RECOMMENDATIONS = 1    # Suggest actions, user decides
    ASSISTED = 2           # Prepare actions, ask confirmation
    SUPERVISED = 3         # Auto-execute within limits

class UserSettings(BaseModel):
    """User preferences for AI behavior."""
    character_id: int
    autonomy_level: AutonomyLevel = AutonomyLevel.RECOMMENDATIONS
    require_confirmation: bool = True  # Ask before WRITE-HIGH-RISK
    budget_limit_isk: Optional[float] = None  # For future trading
    allowed_regions: Optional[List[int]] = None
    blocked_tools: List[str] = []  # User can blacklist tools
```

**Implementation:**

```python
# copilot_server/mcp/orchestrator.py

class ToolOrchestrator:
    def __init__(self, mcp_client, llm_client, user_settings: UserSettings):
        self.mcp = mcp_client
        self.llm = llm_client
        self.settings = user_settings

    async def execute_workflow(self, messages, max_iterations=5):
        # ... existing code ...

        # Before executing tool
        if not self._is_tool_allowed(tool_name, tool_input):
            # Skip or ask confirmation
            confirmation = await self._request_user_confirmation(
                tool_name,
                tool_input
            )
            if not confirmation:
                continue  # Skip this tool

        # Execute tool
        result = self.mcp.call_tool(tool_name, tool_input)

    def _is_tool_allowed(self, tool_name: str, arguments: Dict) -> bool:
        """Check if tool execution is allowed."""

        # 1. Check user blacklist
        if tool_name in self.settings.blocked_tools:
            logger.warning(f"Tool '{tool_name}' blocked by user")
            return False

        # 2. Check tool risk level
        risk_level = TOOL_RISK_LEVELS.get(tool_name, RiskLevel.READ_ONLY)

        # 3. Check against user's autonomy level
        if risk_level == RiskLevel.READ_ONLY:
            return True

        elif risk_level == RiskLevel.WRITE_LOW_RISK:
            return self.settings.autonomy_level.value >= AutonomyLevel.RECOMMENDATIONS.value

        elif risk_level == RiskLevel.WRITE_HIGH_RISK:
            if self.settings.autonomy_level.value < AutonomyLevel.ASSISTED.value:
                return False
            # Mandatory confirmation
            return self.settings.require_confirmation

        elif risk_level == RiskLevel.CRITICAL:
            # Not implemented yet
            return False

        return False
```

---

## 2. Determinismus vs. Kreativität

### 2.1 Das Spektrum

EVE-Use-Cases haben **unterschiedliche Anforderungen**:

| Use-Case | Determinismus | Kreativität | Temperature | Reasoning |
|----------|---------------|-------------|-------------|-----------|
| **Market Price Lookup** | 🔴 MAX (100%) | Keine | 0.0 | Exact data retrieval |
| **Production Cost Calc** | 🔴 MAX (100%) | Keine | 0.0 | Deterministic math |
| **Shopping List Export** | 🔴 MAX (100%) | Keine | 0.0 | Format compliance |
| **Arbitrage Opportunities** | 🟡 HIGH (80%) | Low | 0.3 | Reproducible ranking |
| **Market Analysis** | 🟡 MEDIUM (60%) | Medium | 0.7 | Insight generation |
| **Production Planning** | 🟡 MEDIUM (60%) | Medium | 0.7 | Strategic options |
| **War Room Briefing** | 🟢 LOW (40%) | High | 1.0 | Creative synthesis |
| **Investment Suggestions** | 🟢 LOW (40%) | High | 1.0 | Exploratory ideas |

### 2.2 Strategie: Mode-Switching

**Regel:** Temperature folgt dem **kritischsten Schritt** im Workflow.

#### Beispiel: Market Analysis Workflow

```python
class MarketAnalysisWorkflow(WorkflowTemplate):

    async def execute(self, orchestrator, item_query: str):
        # STEP 1: Search Item - DETERMINISTIC
        # Temperature: 0.0 (exact match)
        item = await orchestrator.llm.chat(
            messages=[{
                "role": "user",
                "content": f"Find the EVE item with ID for: {item_query}"
            }],
            tools=[get_tool("search_item")],
            temperature=0.0  # Exact match
        )

        # STEP 2: Get Market Data - DETERMINISTIC
        # No LLM needed - direct tool call
        market_data = orchestrator.mcp.call_tool("get_market_stats", {...})

        # STEP 3: Calculate Arbitrage - DETERMINISTIC
        # No LLM needed - direct tool call
        arbitrage = orchestrator.mcp.call_tool("calculate_arbitrage", {...})

        # STEP 4: Synthesize Analysis - CREATIVE
        # Temperature: 0.7 (insights, recommendations)
        analysis = await orchestrator.llm.chat(
            messages=[{
                "role": "user",
                "content": f"""
                Analyze this market data:
                {market_data}
                {arbitrage}

                Provide:
                1. Best buy/sell locations
                2. Profit margin analysis
                3. Risk assessment
                4. Strategic recommendations
                """
            }],
            temperature=0.7  # Creative insights
        )

        return analysis
```

**Prinzip:**
- **Daten-Retrieval:** Temperature 0.0
- **Berechnungen:** Keine LLM (direkte Tools)
- **Interpretation:** Temperature 0.7-1.0

### 2.3 Output-Constraints für Determinismus

Wenn **Reproduzierbarkeit** kritisch ist:

```python
# copilot_server/llm/output_schemas.py

MARKET_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "best_buy_location": {
            "type": "object",
            "properties": {
                "region_id": {"type": "integer"},
                "region_name": {"type": "string"},
                "price": {"type": "number"}
            },
            "required": ["region_id", "region_name", "price"]
        },
        "best_sell_location": {
            "type": "object",
            "properties": {
                "region_id": {"type": "integer"},
                "region_name": {"type": "string"},
                "price": {"type": "number"}
            },
            "required": ["region_id", "region_name", "price"]
        },
        "profit_margin_percent": {"type": "number"},
        "risk_level": {"enum": ["low", "medium", "high"]},
        "recommendations": {
            "type": "array",
            "items": {"type": "string"}
        }
    },
    "required": ["best_buy_location", "best_sell_location", "profit_margin_percent"]
}

# Usage
response = await llm.chat(
    messages=messages,
    response_format={"type": "json_schema", "schema": MARKET_ANALYSIS_SCHEMA},
    temperature=0.3  # Low temp + schema = max reproducibility
)
```

---

## 3. Verantwortung der Logik: LLM vs. Server

### 3.1 Das Grundprinzip

**Hard Rule:**

> **Kritische Geschäftslogik liegt IMMER im Server-Code, niemals im LLM.**

**Warum?**
- LLMs sind nicht-deterministisch
- Prompt-Injection-Risiko
- Keine formale Verifikation möglich
- Updates ändern Verhalten

### 3.2 Decision Matrix

| Entscheidungstyp | Verantwortung | Begründung | Beispiel |
|------------------|---------------|------------|----------|
| **Datenvalidierung** | 🔴 SERVER | Sicherheitskritisch | Input Sanitization |
| **Berechtigungsprüfung** | 🔴 SERVER | Sicherheitskritisch | Tool Authorization |
| **Preisberechnungen** | 🔴 SERVER | Finanziell kritisch | Production Cost |
| **Budget-Limits** | 🔴 SERVER | Finanziell kritisch | Max Trade Amount |
| **Tool-Auswahl** | 🟡 LLM + SERVER | LLM schlägt vor, Server prüft | Workflow Planning |
| **Parameter-Extraktion** | 🟡 LLM + SERVER | LLM extrahiert, Server validiert | "Jita" → region_id |
| **Interpretation** | 🟢 LLM | Keine Kritikalität | "Is this profitable?" |
| **Empfehlungen** | 🟢 LLM | Keine Kritikalität | "Consider hauling" |
| **Zusammenfassungen** | 🟢 LLM | Keine Kritikalität | War Room Briefing |

### 3.3 Beispiel: Budget-Limit (FALSCH vs. RICHTIG)

#### ❌ FALSCH: Logik im Prompt

```python
# NEVER DO THIS
system_prompt = f"""
You are EVE Co-Pilot.
IMPORTANT: Never suggest trades over {user_budget} ISK.
"""

response = await llm.chat(messages, system=system_prompt)
# ❌ LLM könnte Limit ignorieren oder falsch interpretieren
```

#### ✅ RICHTIG: Logik im Server

```python
# Server enforces limits
async def execute_workflow(self, messages):
    response = await self.llm.chat(messages, tools=claude_tools)

    # Extract tool calls
    for tool_use in response["content"]:
        if tool_use["type"] == "tool_use":
            tool_name = tool_use["name"]
            tool_input = tool_use["input"]

            # SERVER validates critical parameters
            if tool_name == "place_market_order":  # Future
                order_value = tool_input.get("quantity") * tool_input.get("price")

                if order_value > self.settings.budget_limit_isk:
                    # HARD BLOCK - Server rejects
                    return {
                        "error": f"Order value {order_value:,.0f} ISK exceeds budget limit {self.settings.budget_limit_isk:,.0f} ISK",
                        "blocked_by": "server_policy"
                    }

            # Execute tool
            result = self.mcp.call_tool(tool_name, tool_input)
```

### 3.4 Hybride Entscheidungen: LLM + Server

**Use-Case:** Tool-Parameter-Extraktion

```python
# LLM extrahiert semantisch
User: "What's the price of Tritanium in Jita?"

# LLM reasoning:
# - Item: "Tritanium" → needs search
# - Location: "Jita" → region_id required

# LLM schlägt vor:
tool_use = {
    "name": "get_market_stats",
    "input": {
        "item_name": "Tritanium",  # Semantisch
        "region_name": "Jita"       # Semantisch
    }
}

# SERVER übersetzt & validiert:
def _resolve_tool_parameters(self, tool_name, raw_input):
    if tool_name == "get_market_stats":
        # Resolve item name → type_id
        if "item_name" in raw_input:
            item = self.mcp.call_tool("search_item", {"q": raw_input["item_name"]})
            type_id = item["items"][0]["typeID"]
        else:
            type_id = raw_input.get("type_id")

        # Resolve region name → region_id
        if "region_name" in raw_input:
            region_id = REGION_NAME_TO_ID.get(raw_input["region_name"])
            if not region_id:
                raise ValueError(f"Unknown region: {raw_input['region_name']}")
        else:
            region_id = raw_input.get("region_id")

        # SERVER führt aus mit validierten IDs
        return self.mcp.call_tool(tool_name, {
            "type_id": type_id,
            "region_id": region_id
        })
```

**Prinzip:**
- LLM: Semantisches Reasoning
- Server: Formale Validierung & Execution

---

## 4. Evaluation & Feedback-Loop

### 4.1 Was messen wir?

#### **A) Technical Metrics** (Automatisch)

| Metric | Ziel | Messung | Alert bei |
|--------|------|---------|-----------|
| **Response Time** | < 3s | Per Request | > 5s |
| **Tool Success Rate** | > 98% | Per Tool Call | < 95% |
| **Cache Hit Rate** | > 60% | Per Session | < 40% |
| **Token Usage** | < 5k/query | Per Request | > 10k |
| **Error Rate** | < 2% | Per Workflow | > 5% |

#### **B) Business Metrics** (User-Feedback)

| Metric | Messung | Methode |
|--------|---------|---------|
| **Recommendation Accuracy** | "War Empfehlung profitabel?" | Post-Trade Feedback |
| **Briefing Relevance** | "War Briefing nützlich?" | Thumbs Up/Down |
| **Time Saved** | "Schneller als manuell?" | Survey |
| **Trust Score** | "Würdest du folgen?" | After Recommendation |

#### **C) Quality Metrics** (Sampling)

| Metric | Messung | Frequenz |
|--------|---------|----------|
| **Hallucination Rate** | Fact-Check Sample | 10% random |
| **Instruction Following** | Output matches Schema? | All structured outputs |
| **Reasoning Quality** | Human Expert Review | Weekly Sample |

### 4.2 Feedback-Integration

```python
# copilot_server/feedback/collector.py

class FeedbackCollector:
    """Collect and store user feedback on AI outputs."""

    async def record_feedback(
        self,
        session_id: str,
        workflow_name: str,
        user_rating: int,  # 1-5
        feedback_text: Optional[str] = None,
        outcome: Optional[str] = None  # "profitable", "loss", "neutral"
    ):
        """
        Record user feedback on AI recommendation.

        Args:
            session_id: Session ID
            workflow_name: Which workflow was executed
            user_rating: 1-5 stars
            feedback_text: Optional free text
            outcome: Actual outcome (if applicable)
        """
        # Store in database
        feedback_entry = {
            "session_id": session_id,
            "workflow": workflow_name,
            "timestamp": time.time(),
            "rating": user_rating,
            "feedback": feedback_text,
            "outcome": outcome
        }

        await self._store_feedback(feedback_entry)

        # Trigger analysis if negative
        if user_rating <= 2:
            await self._analyze_failure(session_id, workflow_name)

    async def _analyze_failure(self, session_id, workflow_name):
        """Analyze what went wrong in low-rated interaction."""

        # Get conversation history
        conv = await self.session_manager.get_conversation(session_id)

        # Get tool calls made
        tool_calls = [msg for msg in conv if "tool_use" in msg]

        # Log for human review
        logger.warning(f"Low rating for {workflow_name}: {session_id}")
        logger.warning(f"Tool calls: {tool_calls}")

        # Future: Feed into fine-tuning dataset
```

### 4.3 Continuous Improvement Loop

```
┌─────────────────────────────────────────────────────┐
│                User Interaction                      │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│          AI Agent (Workflow Execution)               │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│              User Feedback (Rating)                  │
└──────────────────────┬──────────────────────────────┘
                       │
           ┌───────────┴──────────┐
           ▼                      ▼
┌──────────────────┐    ┌─────────────────────┐
│  Automated       │    │  Human Review       │
│  Analysis        │    │  (Low Ratings)      │
└────────┬─────────┘    └──────────┬──────────┘
         │                         │
         └───────────┬─────────────┘
                     ▼
         ┌────────────────────────┐
         │  Improvement Actions:  │
         │  - Prompt Tuning       │
         │  - Tool Adjustments    │
         │  - Workflow Refinement │
         │  - Fine-Tuning Data    │
         └────────────────────────┘
```

**Konkret:**

**Week 1-4:** Sammeln von Feedback
**Month 2:** Erste Analyse-Session
- Top 10 Failures reviewen
- Patterns identifizieren
- Prompts/Workflows anpassen

**Month 3+:** Systematische Optimierung
- A/B-Testing von Prompts
- Fine-Tuning mit Production-Data
- Kontinuierliche Iteration

---

## 5. Abbruch- & Fallback-Logik

### 5.1 Abbruchbedingungen

**Der Agent bricht ab bei:**

| Bedingung | Aktion | User-Nachricht |
|-----------|--------|----------------|
| **Max Iterations (5)** | Stopp | "Workflow zu komplex, manuelle Übernahme erforderlich" |
| **Tool Error Rate > 50%** | Stopp | "Technisches Problem, bitte später versuchen" |
| **Unauthorized Tool** | Stopp | "Aktion erfordert höhere Berechtigung" |
| **Budget Limit** | Stopp | "Vorgeschlagene Aktion überschreitet Budget" |
| **User Abort** | Sofort | "Abgebrochen durch User" |
| **Timeout (60s)** | Stopp | "Anfrage dauert zu lange, Timeout" |

**Implementation:**

```python
class ToolOrchestrator:

    async def execute_workflow(self, messages, max_iterations=5):
        iteration = 0
        tool_errors = 0
        total_tools = 0

        while iteration < max_iterations:
            iteration += 1

            # Call LLM
            response = await self.llm.chat(messages, tools=claude_tools)

            # Execute tools
            for tool_use in response["content"]:
                if tool_use["type"] == "tool_use":
                    total_tools += 1

                    # Check authorization
                    if not self._is_tool_allowed(tool_use["name"], tool_use["input"]):
                        return {
                            "error": "Unauthorized tool access",
                            "aborted_at": "authorization_check",
                            "tool": tool_use["name"]
                        }

                    # Execute
                    result = self.mcp.call_tool(tool_use["name"], tool_use["input"])

                    # Track errors
                    if "error" in result:
                        tool_errors += 1

                    # ABORT: Error rate too high
                    if total_tools > 2 and (tool_errors / total_tools) > 0.5:
                        return {
                            "error": "Too many tool failures",
                            "aborted_at": f"iteration_{iteration}",
                            "error_rate": tool_errors / total_tools
                        }

        # Max iterations reached
        return {
            "error": "Maximum iterations reached",
            "aborted_at": f"iteration_{max_iterations}",
            "message": "Workflow too complex for autonomous execution"
        }
```

### 5.2 Fallback-Strategien

```python
class ToolOrchestrator:

    async def execute_workflow_with_fallback(self, messages, max_iterations=5):
        """Execute workflow with automatic fallback."""

        try:
            # Primary: Agentic workflow
            result = await self.execute_workflow(messages, max_iterations)

            if "error" in result:
                # Fallback: Direct tool execution (no reasoning)
                logger.warning("Workflow failed, attempting direct execution")
                return await self._fallback_direct_execution(messages)

            return result

        except Exception as e:
            logger.error(f"Workflow exception: {e}")
            # Fallback: Static response
            return await self._fallback_static_response(messages)

    async def _fallback_direct_execution(self, messages):
        """
        Fallback: Try to extract tool call from last message directly.
        No multi-step reasoning, just single tool.
        """
        last_message = messages[-1]["content"]

        # Simple keyword matching
        if "price" in last_message.lower() or "market" in last_message.lower():
            # Try market query
            return await self._execute_simple_market_query(last_message)

        elif "build" in last_message.lower() or "produce" in last_message.lower():
            # Try production query
            return await self._execute_simple_production_query(last_message)

        # Can't determine - escalate to human
        return {
            "error": "Unable to process request",
            "fallback": "direct_execution_failed",
            "suggestion": "Please rephrase your question more specifically"
        }

    async def _fallback_static_response(self, messages):
        """
        Final fallback: Static response template.
        """
        return {
            "response": "I'm experiencing technical difficulties. Please try one of these:\n\n"
                       "1. Rephrase your question\n"
                       "2. Use the Web UI directly\n"
                       "3. Contact support\n\n"
                       "I've logged this issue for review.",
            "fallback": "static_response",
            "error_logged": True
        }
```

### 5.3 Graceful Degradation

**Prinzip:** Lieber **reduzierte Funktionalität** als **totaler Ausfall**.

```
Full Agentic Workflow (L3)
    ↓ (falls Fehler)
Template Workflow (L2)
    ↓ (falls Fehler)
Direct Tool Call (L1)
    ↓ (falls Fehler)
Static Helpful Response (L0)
```

---

## 6. Strategische Implikationen

### 6.1 Plattform-Claim

**Früher:**
> "EVE Co-Pilot ist ein API-Hub für EVE-Daten"

**Jetzt:**
> "EVE Co-Pilot ist ein **AI Operations Layer für New Eden**"

**Das bedeutet:**
- LLM ist nicht Add-on, sondern **zentraler Betriebsmodus**
- User erwarten **Intelligenz**, nicht nur Daten
- Verantwortung für **AI-Qualität** liegt bei uns

### 6.2 Konsequenzen

#### **A) Produktpositionierung**

| Dimension | Alte Position | Neue Position |
|-----------|---------------|---------------|
| **Value Prop** | "Schneller Zugriff auf Daten" | "Intelligente Entscheidungsunterstützung" |
| **Zielgruppe** | Power-User mit API-Kenntnissen | Alle EVE-Spieler |
| **Differentiator** | API-Vollständigkeit | AI-Qualität |
| **Messgröße** | API-Calls | Profitable Empfehlungen |

#### **B) Entwicklungsfokus**

**Nicht mehr:**
- Mehr API-Endpoints
- Schnellere Responses
- Mehr Features

**Sondern:**
- Bessere AI-Reasoning
- Zuverlässigere Empfehlungen
- Trust & Safety

#### **C) Support & Documentation**

**Neuer Support-Bedarf:**
- "Warum hat der Agent das vorgeschlagen?"
- "Kann ich dem vertrauen?"
- "Wie stelle ich Autonomie-Level ein?"

**Neue Dokumentation:**
- Governance-Policies
- Autonomie-Erklärung
- AI-Limitations

### 6.3 Risiken

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|--------|-------------------|--------|------------|
| **AI-Halluzination führt zu Verlust** | Medium | HIGH | Server-Side Validation + Budget Limits |
| **User verliert Vertrauen** | Medium | HIGH | Transparent Logging + Feedback Loop |
| **Prompt Injection** | Low | MEDIUM | Input Sanitization + Tool Authorization |
| **Unerwartetes AI-Verhalten** | High | LOW | Extensive Testing + Gradual Rollout |
| **Kosten-Explosion (Tokens)** | Medium | MEDIUM | Rate Limiting + Caching |

---

## 7. Governance-Checkliste für Launch

### Pre-Launch Checklist

**Bevor EVE Co-Pilot AI in Production geht:**

- [ ] **Autonomie-Level definiert** (L0-L3)
- [ ] **Tool-Risk-Classification** komplett (alle 115 Tools)
- [ ] **Server-Side Validation** für alle WRITE-Tools
- [ ] **Budget-Limits** implementiert & getestet
- [ ] **Abbruch-Logik** getestet (Max Iterations, Error Rate)
- [ ] **Fallback-Strategien** implementiert
- [ ] **User-Settings** für Autonomie-Präferenzen
- [ ] **Feedback-System** live (Rating + Outcome)
- [ ] **Logging & Audit Trail** komplett
- [ ] **Documentation** (Governance-Policies für User)

### Beta-Phase Checklist

- [ ] **50+ User** im Closed Beta
- [ ] **1000+ Workflows** ausgeführt
- [ ] **Feedback-Analyse** durchgeführt
- [ ] **Top 10 Failure-Cases** adressiert
- [ ] **Trust-Score** > 4.0/5.0
- [ ] **Error-Rate** < 5%

### Production Checklist

- [ ] **Public Launch** kommuniziert
- [ ] **Support-Team** trained auf AI-Queries
- [ ] **Monitoring-Dashboard** live
- [ ] **Incident-Response-Plan** definiert
- [ ] **Continuous Improvement Process** etabliert

---

## 8. Zusammenfassung: Die 5 Governance-Säulen

### 1. **Autonomie-Kontrolle**
User entscheidet, wie viel der Agent darf (L0-L3).

### 2. **Logik-Trennung**
Kritisches im Server, Reasoning im LLM.

### 3. **Determinismus wo nötig**
Daten & Berechnungen = Temperature 0.0, Interpretation = Temperature 0.7-1.0.

### 4. **Evaluation & Feedback**
Messen, Lernen, Verbessern - kontinuierlich.

### 5. **Safety Rails**
Abbruch bei Problemen, Fallback bei Fehlern.

---

## 9. Nächste Schritte

### Diese Woche
1. ✅ **Governance-Framework** dokumentieren (dieses Dokument)
2. ✅ **Tool-Risk-Classification** durchführen
3. ✅ **User-Settings-Modell** definieren

### Nächste Woche
1. ⏳ **Server-Side Validation** für WRITE-Tools implementieren
2. ⏳ **Abbruch-Logik** implementieren
3. ⏳ **Feedback-System** (UI + Backend)

### In 2 Wochen
1. ⏳ **Beta-Launch** mit 10 ausgewählten Usern
2. ⏳ **First Feedback-Analysis**
3. ⏳ **Iteration Based on Learnings**

---

**Fazit:**

> **Technologie ist gelöst. Governance ist die strategische Herausforderung.**

Ihr baut keine Feature-Erweiterung, sondern einen **AI Operations Layer**.

**Das erfordert:**
- Explizite Policies (nicht implizit)
- Klare Verantwortung (LLM vs. Server)
- Kontinuierliche Evaluation (Feedback-Loop)
- Safety-First-Mindset (Abbruch > Fehler)

**Wenn das steht, habt ihr eine echte Platform.**

---

**Status:** 🟡 Framework definiert, Implementation pending
**Next Review:** Nach Beta-Phase
**Owner:** Product + Engineering
