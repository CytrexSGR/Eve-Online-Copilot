# Agent Runtime Architecture Design

**Created:** 2025-12-28
**Status:** Design Complete
**Type:** Architecture Design Document

---

## Executive Summary

This document describes the Agent Runtime architecture for EVE Co-Pilot - a session-based, event-driven execution layer that enables conversational AI interactions with Human-in-the-Loop control. The runtime sits between the user and the existing MCP/ToolOrchestrator infrastructure, providing intelligent auto-execution for read-only operations and approval-based workflows for write operations.

**Goal:** Build a conversational AI agent that can analyze EVE Online data, propose multi-tool workflows, and execute them with appropriate user oversight based on autonomy levels.

**Architecture:** Event-driven runtime with hybrid storage (Redis for live state, PostgreSQL for persistence), WebSocket streaming, and native integration with existing Governance Framework (L0-L3 autonomy levels).

**Tech Stack:**
- FastAPI (existing)
- Redis (new - session state)
- PostgreSQL (existing - extended schema)
- WebSocket (existing - extended)
- Anthropic Claude API (existing)
- MCP Client + ToolOrchestrator (existing)

---

## Table of Contents

1. [Problem Statement](#1-problem-statement)
2. [System Architecture](#2-system-architecture)
3. [Core Components](#3-core-components)
4. [Session Lifecycle](#4-session-lifecycle)
5. [Execution Logic](#5-execution-logic)
6. [Event System](#6-event-system)
7. [API Endpoints](#7-api-endpoints)
8. [Database Schema](#8-database-schema)
9. [Tool Knowledge Strategy](#9-tool-knowledge-strategy)
10. [Error Handling](#10-error-handling)
11. [Security & Authorization](#11-security--authorization)
12. [Implementation Phases](#12-implementation-phases)

---

## 1. Problem Statement

### Current State

EVE Co-Pilot has:
- ✅ 115 MCP tools across 13 categories
- ✅ ToolOrchestrator for multi-tool workflows
- ✅ Governance Framework (L0-L3 autonomy levels)
- ✅ Authorization middleware
- ✅ WebSocket infrastructure

### What's Missing

❌ **Session Management:** Conversations are stateless, no continuation
❌ **Human-in-the-Loop:** Agent executes all tools automatically without approval
❌ **Observability:** Users can't see what agent is doing in real-time
❌ **Plan Proposals:** No way to preview multi-tool workflows before execution

### User Stories

**As a user with L1 (RECOMMENDATIONS) autonomy:**
- I want the agent to analyze data automatically (READ_ONLY tools)
- I want to approve plans before write operations execute
- I want to see live progress when agent is working
- I want to refine plans before execution

**Example Interaction:**

```
User: "Where are battles happening and what materials are needed?"

Agent: [AUTO-EXECUTES - all READ_ONLY tools]
       Live stream shows:
       ✓ get_war_summary
       ✓ get_combat_losses (Region: The Forge)
       ✓ get_top_destroyed_ships
       ✓ get_material_requirements

Agent: "Major battles in Vale of the Silent (147 kills/hour).
       Top destroyed: Caracal (23), Osprey (18), Griffin (12).
       Materials needed: 2.4M Tritanium, 890K Pyerite..."

User: "Create shopping list for those materials in Jita"

Agent: [PROPOSES PLAN - contains WRITE_LOW_RISK]
       Plan: Create shopping list
       Steps:
       1. search_item (Tritanium, Pyerite, ...)
       2. create_shopping_list (name: "Vale Battle Materials")
       3. add_shopping_items (2.4M Tritanium, ...)
       4. get_regional_comparison (best prices)

       Execute this plan? [Yes] [No] [Refine]

User: [Clicks Yes]

Agent: [EXECUTES]
       ✓ Created list "Vale Battle Materials"
       ✓ Added 12 items
       ✓ Total cost: 847M ISK (Jita best for 9/12 items)
```

---

## 2. System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         User / UI                            │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   Agent API Layer                            │
│  POST /agent/chat        WS /agent/stream/{session_id}      │
│  POST /agent/execute     DELETE /agent/session/{id}         │
│  POST /agent/interrupt   POST /agent/reject                 │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              Agent Session Manager                           │
│  - Session CRUD                                             │
│  - State persistence (Redis + PostgreSQL)                   │
│  - Message queue (1 message)                                │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   Agent Runtime                              │
│  - Execution loop (async)                                   │
│  - Plan detection (multi-tool responses)                    │
│  - Auto-execute decision logic                              │
│  - Event emission                                           │
└───────────────────────────┬─────────────────────────────────┘
                            │
                ┌───────────┴───────────┐
                ▼                       ▼
┌───────────────────────┐   ┌──────────────────────┐
│  Authorization        │   │  Event Bus           │
│  Checker (L0-L3)      │   │  (WebSocket)         │
└───────┬───────────────┘   └──────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│              ToolOrchestrator (existing)                     │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                 MCP Client → 115 Tools                       │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow: Auto-Execute Scenario (READ_ONLY)

```
1. User → POST /agent/chat "What's profitable in Jita?"
2. SessionManager → Load/Create session
3. Runtime → Call LLM with 115 tools
4. LLM → Returns 3 tool_use blocks:
   - get_manufacturing_opportunities
   - get_market_stats
   - calculate_arbitrage
5. Runtime → Detect multi-tool plan
6. Runtime → Check risk levels: ALL READ_ONLY
7. Runtime → Decision: AUTO-EXECUTE (L1 allows)
8. EventBus → Emit plan_proposed (auto_executing: true)
9. Runtime → Execute tools sequentially via ToolOrchestrator
10. EventBus → Emit tool_call_started, tool_call_completed for each
11. Runtime → Call LLM with tool results
12. LLM → Synthesizes answer
13. Runtime → Session status = completed
14. EventBus → Emit answer_ready, completed
15. User receives final answer
```

### Data Flow: Plan-Approval Scenario (WRITE)

```
1. User → POST /agent/chat "Create shopping list for Hobgoblin II"
2. SessionManager → Load session
3. Runtime → Call LLM
4. LLM → Returns 4 tool_use blocks:
   - search_item
   - create_shopping_list (WRITE_LOW_RISK)
   - add_shopping_items (WRITE_LOW_RISK)
   - get_regional_comparison
5. Runtime → Detect plan, check risk: WRITE_LOW_RISK present
6. Runtime → Decision: WAIT FOR APPROVAL (L1 requires it)
7. SessionManager → Save pending_plan
8. Session → status = waiting_approval
9. EventBus → Emit plan_proposed (auto_executing: false)
10. WAIT for user action
11. User → POST /agent/execute
12. Runtime → Resume, execute plan
13. EventBus → Stream tool_call events
14. Runtime → Complete, emit answer_ready
```

---

## 3. Core Components

### 3.1 Agent Session Manager

**Responsibilities:**
- Create, load, update, delete sessions
- Persist to Redis (live) and PostgreSQL (audit)
- Manage message queue (1 message max)
- Enforce TTL (24h inactivity → auto-cleanup)
- Thread-safe operations (no concurrent execution per session)

**Key Methods:**

```python
class AgentSessionManager:
    async def create_session(
        self,
        character_id: int,
        autonomy_level: AutonomyLevel
    ) -> AgentSession

    async def load_session(self, session_id: str) -> AgentSession

    async def save_session(self, session: AgentSession) -> None

    async def delete_session(self, session_id: str) -> None

    async def queue_message(
        self,
        session_id: str,
        message: str
    ) -> None  # Overwrites existing queued message

    async def get_queued_message(
        self,
        session_id: str
    ) -> Optional[str]

    async def cleanup_expired_sessions(self) -> int
```

### 3.2 Agent Runtime

**Responsibilities:**
- Execute main async loop
- Call LLM with tools
- Detect multi-tool plans (3+ tool_use blocks)
- Decide auto-execute vs. wait-for-approval
- Orchestrate tool execution
- Emit events to WebSocket
- Handle errors and partial results

**Key Methods:**

```python
class AgentRuntime:
    def __init__(
        self,
        session_manager: AgentSessionManager,
        llm_client: AnthropicClient,
        orchestrator: ToolOrchestrator,
        event_bus: EventBus
    )

    async def execute(self, session: AgentSession) -> None:
        """Main execution loop."""

    async def _should_auto_execute(
        self,
        plan: Plan,
        autonomy_level: AutonomyLevel
    ) -> bool:
        """Decision logic for auto-execution."""

    async def _execute_plan(
        self,
        session: AgentSession,
        plan: Plan
    ) -> None:
        """Execute all plan steps with events."""

    async def _propose_plan(
        self,
        session: AgentSession,
        plan: Plan
    ) -> None:
        """Save plan and emit proposal event."""
```

### 3.3 Event Bus

**Responsibilities:**
- Pub/Sub per session
- WebSocket broadcasting
- Optional persistence to PostgreSQL
- Event filtering and routing

**Key Methods:**

```python
class EventBus:
    async def emit(
        self,
        session_id: str,
        event: AgentEvent
    ) -> None

    async def subscribe(
        self,
        session_id: str,
        websocket: WebSocket
    ) -> None

    async def unsubscribe(
        self,
        session_id: str,
        websocket: WebSocket
    ) -> None
```

### 3.4 Plan Detector

**Responsibilities:**
- Analyze LLM response
- Extract tool_use blocks
- Determine if it's a "plan" (3+ tools)
- Calculate max risk level
- Build Plan object

**Key Methods:**

```python
class PlanDetector:
    def detect_plan(
        self,
        llm_response: Dict[str, Any]
    ) -> Optional[Plan]:
        """Returns Plan if 3+ tool_use blocks, else None."""

    def calculate_max_risk(
        self,
        tools: List[str]
    ) -> RiskLevel:
        """Uses existing tool_classification."""
```

---

## 4. Session Lifecycle

### 4.1 Session States

```python
class SessionStatus(Enum):
    IDLE = "idle"                      # Created, no activity
    PLANNING = "planning"              # LLM is thinking
    EXECUTING = "executing"            # Tools running
    EXECUTING_QUEUED = "executing_queued"  # Tools running + message queued
    WAITING_APPROVAL = "waiting_approval"  # Plan proposed, awaiting user
    COMPLETED = "completed"            # Finished successfully
    COMPLETED_WITH_ERRORS = "completed_with_errors"  # Partial success
    ERROR = "error"                    # Unrecoverable error
    INTERRUPTED = "interrupted"        # User stopped execution
```

### 4.2 Session Creation

```python
# Explicit session creation
POST /agent/chat
{
  "message": "What's profitable?",
  "session_id": null,  # Creates new session
  "character_id": 1117367444
}

→ Creates session with:
  - id: UUID
  - character_id: 1117367444
  - autonomy_level: L1 (from user_settings)
  - status: planning
  - messages: [user message]
  - created_at: now
```

### 4.3 Session Continuation

```python
# Continue existing session
POST /agent/chat
{
  "message": "And in Amarr?",
  "session_id": "sess-abc123",
  "character_id": 1117367444
}

→ Appends to session.messages
→ Maintains context from previous exchanges
```

### 4.4 Session Cleanup

**Auto-Cleanup:**
- TTL: 24 hours of inactivity
- Background job runs every 1 hour
- Redis: Expire keys automatically
- PostgreSQL: Keep for audit (no deletion)

**Explicit Cleanup:**
```python
DELETE /agent/session/{session_id}
→ Removes from Redis
→ Marks as "archived" in PostgreSQL
```

### 4.5 Message Queueing

**Scenario:** User sends new message while session is `executing`

```python
Current state: session.status = "executing"

User → POST /agent/chat {"message": "And in Dodixie?", "session_id": "sess-abc123"}

Action:
1. Check session.status → executing
2. Overwrite session.queued_message = "And in Dodixie?"
3. Update session.status = "executing_queued"
4. Emit MESSAGE_QUEUED event
5. Return 202 Accepted

When current execution completes:
1. Check session.queued_message → not null
2. Process queued message
3. Clear session.queued_message
```

---

## 5. Execution Logic

### 5.1 Auto-Execute Decision Matrix

```python
def should_auto_execute(plan: Plan, autonomy_level: AutonomyLevel) -> bool:
    """
    Decides if plan should auto-execute based on risk and autonomy level.
    """
    max_risk = max(get_risk_level(tool) for tool in plan.tools)

    if autonomy_level == AutonomyLevel.READ_ONLY:  # L0
        return False  # Never auto-execute

    if autonomy_level == AutonomyLevel.RECOMMENDATIONS:  # L1
        if max_risk == RiskLevel.READ_ONLY:
            return True   # Auto-execute pure analysis
        else:
            return False  # Wait for approval on writes

    if autonomy_level == AutonomyLevel.ASSISTED:  # L2
        if max_risk in [RiskLevel.READ_ONLY, RiskLevel.WRITE_LOW_RISK]:
            return True   # Auto-execute low-risk writes
        else:
            return False  # Wait for high-risk writes

    if autonomy_level == AutonomyLevel.SUPERVISED:  # L3
        return True  # Auto-execute everything (future)

    return False  # Default: safe
```

**Decision Table:**

| Autonomy Level | Plan Max Risk | Auto-Execute? | Behavior |
|----------------|---------------|---------------|----------|
| L0 (READ_ONLY) | Any | ❌ No | Always propose plan |
| L1 (RECOMMENDATIONS) | READ_ONLY | ✅ Yes | Execute immediately |
| L1 | WRITE_LOW_RISK | ❌ No | Propose plan |
| L1 | WRITE_HIGH_RISK | ❌ No | Propose plan |
| L2 (ASSISTED) | READ_ONLY | ✅ Yes | Execute immediately |
| L2 | WRITE_LOW_RISK | ✅ Yes | Execute immediately |
| L2 | WRITE_HIGH_RISK | ❌ No | Propose plan |
| L3 (SUPERVISED) | Any | ✅ Yes | Execute immediately |

### 5.2 Plan Detection Logic

**When is response considered a "plan"?**

```python
def is_plan(llm_response: Dict) -> bool:
    """
    A response is a plan if it contains 3+ tool_use blocks.
    """
    tool_uses = [
        block for block in llm_response.get("content", [])
        if block.get("type") == "tool_use"
    ]
    return len(tool_uses) >= 3
```

**Examples:**

```python
# NOT a plan (single tool)
{
  "content": [
    {"type": "tool_use", "name": "get_market_stats", ...}
  ]
}
→ Execute directly, no plan

# NOT a plan (2 tools, threshold not met)
{
  "content": [
    {"type": "tool_use", "name": "search_item", ...},
    {"type": "tool_use", "name": "get_market_stats", ...}
  ]
}
→ Execute directly, no plan

# IS a plan (3+ tools)
{
  "content": [
    {"type": "tool_use", "name": "get_war_summary", ...},
    {"type": "tool_use", "name": "get_combat_losses", ...},
    {"type": "tool_use", "name": "get_material_requirements", ...}
  ]
}
→ Create Plan object, decide auto-execute
```

### 5.3 Execution Loop Pseudocode

```python
async def execute(session: AgentSession):
    """Main execution loop."""

    while session.status in ["planning", "executing"]:
        # Build prompt
        messages = build_messages(session)

        # Call LLM
        response = await llm.chat(messages=messages, tools=get_tools())

        # Analyze response
        if has_tool_calls(response):
            # Detect if plan
            plan = plan_detector.detect_plan(response)

            if plan:
                # Multi-tool workflow
                if should_auto_execute(plan, session.autonomy_level):
                    # Auto-execute
                    await event_bus.emit(session.id, PlanProposed(
                        plan=plan,
                        auto_executing=True
                    ))
                    await execute_plan(session, plan)
                else:
                    # Propose and wait
                    await propose_plan(session, plan)
                    session.status = "waiting_approval"
                    return  # Exit loop, wait for user
            else:
                # Single/dual tool, execute directly
                await execute_tools_directly(session, response.tool_uses)
        else:
            # Final answer, no tools
            session.answer = response.content
            session.status = "completed"
            await event_bus.emit(session.id, AnswerReady(answer=session.answer))
            return
```

---

## 6. Event System

### 6.1 Event Types

```python
class AgentEventType(Enum):
    # Session Events
    SESSION_CREATED = "session_created"
    SESSION_RESUMED = "session_resumed"

    # Planning Events
    PLANNING_STARTED = "planning_started"
    PLAN_PROPOSED = "plan_proposed"
    PLAN_APPROVED = "plan_approved"
    PLAN_REJECTED = "plan_rejected"
    PLAN_REFINED = "plan_refined"

    # Execution Events
    EXECUTION_STARTED = "execution_started"
    TOOL_CALL_STARTED = "tool_call_started"
    TOOL_CALL_COMPLETED = "tool_call_completed"
    TOOL_CALL_FAILED = "tool_call_failed"
    THINKING = "thinking"

    # Completion Events
    ANSWER_READY = "answer_ready"
    COMPLETED = "completed"
    COMPLETED_WITH_ERRORS = "completed_with_errors"

    # Control Events
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    MESSAGE_QUEUED = "message_queued"
    INTERRUPTED = "interrupted"
    ERROR = "error"
    AUTHORIZATION_DENIED = "authorization_denied"
```

### 6.2 Event Payloads

```python
# plan_proposed
{
  "type": "plan_proposed",
  "session_id": "sess-abc123",
  "plan_id": "plan-xyz789",
  "auto_executing": true,  # or false
  "payload": {
    "purpose": "Analyze war zones and material demand",
    "steps": [
      {"tool": "get_war_summary", "arguments": {}},
      {"tool": "get_combat_losses", "arguments": {"region_id": 10000002}},
      ...
    ],
    "max_risk_level": "READ_ONLY",
    "tool_count": 5
  },
  "timestamp": "2025-12-28T10:30:00Z"
}

# tool_call_started
{
  "type": "tool_call_started",
  "session_id": "sess-abc123",
  "plan_id": "plan-xyz789",
  "payload": {
    "step_index": 0,
    "tool": "get_war_summary",
    "arguments": {}
  },
  "timestamp": "2025-12-28T10:30:05Z"
}

# tool_call_completed
{
  "type": "tool_call_completed",
  "session_id": "sess-abc123",
  "plan_id": "plan-xyz789",
  "payload": {
    "step_index": 0,
    "tool": "get_war_summary",
    "duration_ms": 234,
    "result_preview": "147 kills in Vale of the Silent..."
  },
  "timestamp": "2025-12-28T10:30:05.234Z"
}

# tool_call_failed
{
  "type": "tool_call_failed",
  "session_id": "sess-abc123",
  "plan_id": "plan-xyz789",
  "payload": {
    "step_index": 2,
    "tool": "get_material_requirements",
    "error": "ESI API timeout",
    "retry_count": 2
  },
  "timestamp": "2025-12-28T10:30:15Z"
}

# waiting_for_approval
{
  "type": "waiting_for_approval",
  "session_id": "sess-abc123",
  "plan_id": "plan-xyz789",
  "payload": {
    "message": "Plan requires user approval due to WRITE operations"
  },
  "timestamp": "2025-12-28T10:30:00Z"
}

# message_queued
{
  "type": "message_queued",
  "session_id": "sess-abc123",
  "payload": {
    "queued_message_preview": "And in Dodixie?",
    "will_process_after": "current execution completes"
  },
  "timestamp": "2025-12-28T10:30:20Z"
}

# answer_ready
{
  "type": "answer_ready",
  "session_id": "sess-abc123",
  "payload": {
    "answer": "Major battles are occurring in Vale of the Silent...",
    "tool_calls_count": 5,
    "duration_ms": 3421
  },
  "timestamp": "2025-12-28T10:30:25Z"
}
```

### 6.3 WebSocket Protocol

**Connection:**
```javascript
const ws = new WebSocket('ws://localhost:8000/agent/stream/sess-abc123');

ws.onmessage = (event) => {
  const agentEvent = JSON.parse(event.data);

  switch(agentEvent.type) {
    case 'plan_proposed':
      if (agentEvent.auto_executing) {
        showProgress(agentEvent.payload);
      } else {
        showApprovalDialog(agentEvent.payload);
      }
      break;

    case 'tool_call_started':
      updateProgress(`Running ${agentEvent.payload.tool}...`);
      break;

    case 'answer_ready':
      displayAnswer(agentEvent.payload.answer);
      break;
  }
};
```

---

## 7. API Endpoints

### 7.1 Core Endpoints

#### POST /agent/chat

**Purpose:** Send message, create/continue session

**Request:**
```json
{
  "message": "What's profitable in Jita?",
  "session_id": null,  // null = create new, or UUID to continue
  "character_id": 1117367444
}
```

**Response:**
```json
{
  "session_id": "sess-abc123",
  "status": "executing",  // or "waiting_approval"
  "plan_id": "plan-xyz789"  // if plan was created
}
```

**Behavior:**
- If `session_id` is null → create new session
- If `session_id` exists → load session, append message
- If session is `executing` → queue message (overwrite existing queue)
- Trigger runtime execution async
- Events streamed via WebSocket

---

#### POST /agent/execute

**Purpose:** Approve and execute pending plan

**Request:**
```json
{
  "session_id": "sess-abc123",
  "plan_id": "plan-xyz789"
}
```

**Response:**
```json
{
  "status": "executing",
  "message": "Plan execution started"
}
```

**Validation:**
- Session must be in `waiting_approval` status
- Plan ID must match `session.pending_plan_id`
- Idempotent: If already executing → return 409
- If already completed → return 200 with cached result

---

#### POST /agent/reject

**Purpose:** Reject proposed plan

**Request:**
```json
{
  "session_id": "sess-abc123",
  "plan_id": "plan-xyz789",
  "reason": "Too expensive"  // optional
}
```

**Response:**
```json
{
  "status": "idle",
  "message": "Plan rejected"
}
```

**Behavior:**
- Session returns to `idle` status
- Plan marked as `rejected` in database
- User can send new message to refine request

---

#### POST /agent/interrupt

**Purpose:** Stop current execution

**Request:**
```json
{
  "session_id": "sess-abc123"
}
```

**Response:**
```json
{
  "status": "interrupted",
  "message": "Execution stopped",
  "queued_message": "And in Dodixie?"  // if exists
}
```

**Behavior:**
- Gracefully stop current tool execution
- Emit `INTERRUPTED` event
- If queued message exists → process it next
- Idempotent: If not executing → return 200 (no-op)

---

#### GET /agent/session/{session_id}

**Purpose:** Get current session state

**Response:**
```json
{
  "id": "sess-abc123",
  "character_id": 1117367444,
  "autonomy_level": 1,
  "status": "waiting_approval",
  "created_at": "2025-12-28T10:00:00Z",
  "updated_at": "2025-12-28T10:30:00Z",
  "messages": [
    {"role": "user", "content": "What's profitable?"},
    {"role": "assistant", "content": "I'll analyze manufacturing opportunities..."}
  ],
  "pending_plan": {
    "plan_id": "plan-xyz789",
    "purpose": "...",
    "steps": [...]
  },
  "queued_message": null
}
```

---

#### DELETE /agent/session/{session_id}

**Purpose:** End and cleanup session

**Response:**
```json
{
  "message": "Session deleted",
  "archived": true
}
```

**Behavior:**
- Remove from Redis
- Mark as archived in PostgreSQL (keep for audit)
- Close WebSocket connections

---

#### WS /agent/stream/{session_id}

**Purpose:** Subscribe to real-time events

**Protocol:** WebSocket

**Messages:** JSON-encoded AgentEvent objects

**Example:**
```javascript
ws = new WebSocket('ws://localhost:8000/agent/stream/sess-abc123');
ws.onmessage = (event) => {
  const agentEvent = JSON.parse(event.data);
  console.log(agentEvent.type, agentEvent.payload);
};
```

---

## 8. Database Schema

### 8.1 PostgreSQL Schema

```sql
-- Agent Sessions (persistent audit trail)
CREATE TABLE agent_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    character_id INTEGER NOT NULL,
    autonomy_level INTEGER NOT NULL DEFAULT 1,  -- L0-L3
    status VARCHAR(50) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_activity TIMESTAMP NOT NULL DEFAULT NOW(),
    archived BOOLEAN DEFAULT FALSE,
    context JSONB DEFAULT '{}'::jsonb,

    INDEX idx_character_id (character_id),
    INDEX idx_status (status),
    INDEX idx_last_activity (last_activity)
);

-- Agent Plans (for replay & audit)
CREATE TABLE agent_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES agent_sessions(id) ON DELETE CASCADE,
    purpose TEXT NOT NULL,
    plan_data JSONB NOT NULL,  -- {steps: [...], max_risk_level: "..."}
    status VARCHAR(50) NOT NULL,  -- proposed, approved, rejected, executing, completed
    auto_executing BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    approved_at TIMESTAMP,
    executed_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_ms INTEGER,

    INDEX idx_session_id (session_id),
    INDEX idx_status (status)
);

-- Agent Events (for debugging & audit)
CREATE TABLE agent_events (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES agent_sessions(id) ON DELETE CASCADE,
    plan_id UUID REFERENCES agent_plans(id) ON DELETE SET NULL,
    event_type VARCHAR(50) NOT NULL,
    payload JSONB NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),

    INDEX idx_session_id (session_id),
    INDEX idx_plan_id (plan_id),
    INDEX idx_event_type (event_type),
    INDEX idx_timestamp (timestamp)
);

-- Conversation Messages (for context)
CREATE TABLE agent_messages (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES agent_sessions(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,  -- user, assistant
    content TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),

    INDEX idx_session_id (session_id)
);
```

### 8.2 Redis Schema

**Purpose:** Fast ephemeral state for live sessions

**Key Patterns:**

```python
# Session State (TTL: 24h)
Key: "agent:session:{session_id}"
Value: {
    "status": "executing",
    "current_plan_id": "plan-xyz789",
    "queued_message": null,
    "messages": [...],  # Recent conversation (last 50 messages)
    "pending_plan": {...}
}

# Session Lock (prevent concurrent execution)
Key: "agent:lock:{session_id}"
Value: "locked"
TTL: 300 seconds (5 min)

# Active Sessions Index
Key: "agent:sessions:active"
Type: Set
Members: ["sess-abc123", "sess-def456", ...]
```

**Operations:**

```python
# Load session
session_data = redis.get(f"agent:session:{session_id}")
if not session_data:
    session_data = db.query(AgentSession).filter_by(id=session_id).first()
    redis.setex(f"agent:session:{session_id}", 86400, session_data)

# Save session
redis.setex(f"agent:session:{session_id}", 86400, json.dumps(session_dict))
db.query(AgentSession).filter_by(id=session_id).update(session_dict)

# Acquire lock
acquired = redis.set(f"agent:lock:{session_id}", "locked", nx=True, ex=300)
if not acquired:
    raise SessionBusyError()
```

---

## 9. Tool Knowledge Strategy

### 9.1 Tool Categories (System Prompt)

**Included in every LLM call:**

```markdown
You have access to 115 EVE Online tools across 13 categories:

**CONTEXT (2 tools):**
- eve_copilot_context: Get session context
- get_available_tools: List all tools

**CHARACTER (8 tools):**
- get_character_wallet, get_character_assets, get_character_skills,
  get_character_skillqueue, get_character_orders, get_character_industry,
  get_character_blueprints, get_character_info

**MARKET (12 tools):**
- search_item, get_market_stats, get_market_prices, get_market_orders,
  calculate_arbitrage, get_regional_comparison, ...

**PRODUCTION (15 tools):**
- get_manufacturing_opportunities, calculate_production_cost,
  get_production_chain, get_material_requirements, ...

**WAR_ROOM (9 tools):**
- get_war_summary, get_combat_losses, get_top_destroyed_ships,
  get_material_requirements, get_sovereignty_campaigns, ...

**SHOPPING (11 tools):**
- create_shopping_list, add_shopping_items, get_shopping_lists,
  calculate_shopping_route, export_shopping_list, ...

**BOOKMARKS (6 tools):**
- create_bookmark, get_bookmarks, update_bookmark, delete_bookmark,
  create_bookmark_list, add_to_bookmark_list

**ITEMS (8 tools):**
- search_item, get_item_details, get_item_groups,
  get_material_composition, get_material_volumes, ...

**ROUTE (5 tools):**
- calculate_route, get_route_hubs, get_route_distances,
  get_safe_route, search_systems

**MINING (4 tools):**
- find_mineral_ore, plan_mining_route, get_ore_info, ...

**CARGO (3 tools):**
- calculate_cargo_volume, get_item_volume, get_transport_options

**DASHBOARD (2 tools):**
- get_opportunities_overview, get_character_portfolio

**RESEARCH (2 tools):**
- get_skills_for_item, get_skill_recommendations

**USAGE GUIDELINES:**
- For price/market questions → use MARKET tools
- For "what's profitable?" → use PRODUCTION tools
- For battle/war questions → use WAR_ROOM tools
- For multi-region analysis → combine tools from multiple categories
- When creating/modifying lists → use SHOPPING or BOOKMARKS tools
```

### 9.2 Workflow Examples (External File)

**File:** `docs/agent/workflow_examples.md`

**Loaded dynamically** when LLM needs guidance on complex queries.

**Content:**

```markdown
# Common EVE Co-Pilot Workflows

## Market Analysis

### Q: "What's profitable to manufacture in Jita?"

**Workflow:**
1. `get_manufacturing_opportunities(region_id=10000002)`
   → Returns top 50 profitable items
2. For top 5 candidates:
   `get_market_stats(type_id=X, region_id=10000002)`
   → Get current prices and volumes
3. `calculate_production_cost(type_id=X)`
   → Calculate material costs
4. Compare profit margins: (sell_price - cost) / cost
5. Return ranked list with ISK/hour estimates

**Expected Tools:** 6-8 tool calls, all READ_ONLY

---

## War Room Intelligence

### Q: "Where are battles happening and what materials are needed?"

**Workflow:**
1. `get_war_summary()`
   → Identify hot regions and systems
2. `get_combat_losses(region_id=X)` for top 3 regions
   → Get ship destruction data
3. `get_top_destroyed_ships()`
   → Most common losses
4. `get_material_requirements(type_ids=[ship_ids])`
   → Calculate materials needed to build those ships
5. `get_regional_comparison(type_ids=[material_ids])`
   → Find best prices for materials

**Expected Tools:** 8-12 tool calls, all READ_ONLY

---

## Shopping List Creation

### Q: "Create shopping list for building 10 Caracals in Jita"

**Workflow:**
1. `search_item(q="Caracal")`
   → Get type_id for Caracal
2. `get_production_chain(type_id=X, quantity=10)`
   → Get all materials needed (recursive)
3. `create_shopping_list(name="10 Caracals - Jita")`
   → Create list (WRITE_LOW_RISK)
4. For each material:
   `add_shopping_items(list_id=X, items=[...])`
   → Add to list (WRITE_LOW_RISK)
5. `get_regional_comparison(type_ids=[material_ids], regions=[Jita])`
   → Check prices
6. `calculate_shopping_route(list_id=X)`
   → Optimize purchase route

**Expected Tools:** 8-10 tool calls, includes WRITE_LOW_RISK
**L1 Behavior:** Propose plan, wait for approval

---

## Character Skill Analysis

### Q: "What skills do I need for building Tech 2 drones?"

**Workflow:**
1. `search_item(q="Tech 2 drone")`
   → Get drone type_ids
2. `get_skills_for_item(type_id=X)`
   → List required skills and levels
3. `get_character_skills(character_id=Y)`
   → Get current skills
4. Compare: identify gaps
5. `get_skill_recommendations(character_id=Y, goal="Tech 2 production")`
   → Get training plan

**Expected Tools:** 5-7 tool calls, all READ_ONLY
```

**Dynamic Loading:**

```python
# When LLM query is complex and involves multiple categories
if is_complex_query(user_message):
    relevant_workflows = load_workflow_examples(user_message)
    system_prompt += f"\n\nRELEVANT WORKFLOWS:\n{relevant_workflows}"
```

---

## 10. Error Handling

### 10.1 Tool Call Failures

**Strategy: Partial Results**

```python
async def execute_plan(session: AgentSession, plan: Plan):
    results = []
    failed_steps = []

    for step_index, step in enumerate(plan.steps):
        try:
            # Emit event
            await event_bus.emit(session.id, ToolCallStarted(
                step_index=step_index,
                tool=step.tool
            ))

            # Execute with retries
            result = await execute_with_retry(
                tool=step.tool,
                arguments=step.arguments,
                max_retries=3
            )

            results.append(result)

            await event_bus.emit(session.id, ToolCallCompleted(
                step_index=step_index,
                tool=step.tool,
                result=result
            ))

        except ToolExecutionError as e:
            # Mark as failed but continue
            failed_steps.append({
                "step_index": step_index,
                "tool": step.tool,
                "error": str(e)
            })

            await event_bus.emit(session.id, ToolCallFailed(
                step_index=step_index,
                tool=step.tool,
                error=str(e)
            ))

            # Continue with remaining steps
            continue

    # Build response with partial results
    if failed_steps:
        session.status = "completed_with_errors"
        # LLM receives: successful results + list of failed steps
        # LLM can still provide useful answer with partial data
    else:
        session.status = "completed"
```

**Retry Logic:**

```python
async def execute_with_retry(
    tool: str,
    arguments: Dict,
    max_retries: int = 3
) -> Any:
    """Execute tool with exponential backoff retry."""

    for attempt in range(max_retries):
        try:
            result = await orchestrator.execute_tool(tool, arguments)
            return result

        except (TimeoutError, ConnectionError) as e:
            if attempt < max_retries - 1:
                wait_seconds = 2 ** attempt  # 1s, 2s, 4s
                await asyncio.sleep(wait_seconds)
                continue
            else:
                raise ToolExecutionError(f"Failed after {max_retries} retries: {e}")
```

### 10.2 LLM API Failures

```python
async def execute(session: AgentSession):
    try:
        response = await llm.chat(messages=messages, tools=tools)

    except AnthropicAPIError as e:
        # Retry LLM call
        for retry in range(3):
            try:
                response = await llm.chat(messages=messages, tools=tools)
                break
            except:
                if retry == 2:
                    session.status = "error"
                    await event_bus.emit(session.id, Error(
                        error="LLM API unavailable after retries"
                    ))
                    return
                await asyncio.sleep(2 ** retry)
```

### 10.3 Session Errors

**Concurrent Execution Prevention:**

```python
async def execute_session(session_id: str):
    # Acquire lock
    lock_acquired = await redis.set(
        f"agent:lock:{session_id}",
        "locked",
        nx=True,
        ex=300  # 5 min timeout
    )

    if not lock_acquired:
        raise SessionBusyError("Session already executing")

    try:
        # Execute runtime
        await runtime.execute(session)
    finally:
        # Always release lock
        await redis.delete(f"agent:lock:{session_id}")
```

---

## 11. Security & Authorization

### 11.1 Integration with Existing Governance

**The Agent Runtime fully integrates with existing Authorization Framework:**

```python
class AgentRuntime:
    def __init__(self, ..., auth_checker: AuthorizationChecker):
        self.auth_checker = auth_checker

    async def _execute_plan(self, session: AgentSession, plan: Plan):
        for step in plan.steps:
            # Check authorization BEFORE execution
            allowed, denial_reason = self.auth_checker.check_authorization(
                tool_name=step.tool,
                arguments=step.arguments
            )

            if not allowed:
                await event_bus.emit(session.id, AuthorizationDenied(
                    tool=step.tool,
                    reason=denial_reason
                ))

                # Mark step as failed
                failed_steps.append({
                    "tool": step.tool,
                    "error": f"Authorization denied: {denial_reason}"
                })
                continue

            # Execute if authorized
            result = await orchestrator.execute_tool(step.tool, step.arguments)
```

**No changes needed to existing governance:**
- ✅ L0-L3 autonomy levels work as-is
- ✅ Tool risk classification (READ_ONLY, WRITE_LOW_RISK, etc.) reused
- ✅ AuthorizationChecker validates every tool call
- ✅ User blacklists respected

### 11.2 Additional Security Measures

**Rate Limiting:**

```python
# Per-user rate limits
@rate_limit(max_requests=100, window_seconds=3600)
async def chat_endpoint(request: ChatRequest):
    ...

# Per-session rate limits
@rate_limit(max_requests=20, window_seconds=60, key="session_id")
async def execute_endpoint(request: ExecuteRequest):
    ...
```

**Input Validation:**

```python
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000)
    session_id: Optional[UUID] = None
    character_id: int = Field(..., gt=0)

    @validator('message')
    def validate_message(cls, v):
        # Prevent injection attacks
        if any(char in v for char in ['<', '>', '{', '}']):
            raise ValueError("Invalid characters in message")
        return v
```

**Audit Logging:**

```python
# Every plan execution logged
logger.info(
    "Plan execution",
    extra={
        "session_id": session.id,
        "character_id": session.character_id,
        "plan_id": plan.id,
        "autonomy_level": session.autonomy_level,
        "auto_executing": auto_executing,
        "tool_count": len(plan.steps)
    }
)
```

---

## 12. Implementation Phases

### Phase 1: Core Infrastructure (Week 1-2)

**Goal:** Basic session management and execution loop

**Tasks:**
1. Database schema (PostgreSQL + Redis)
2. AgentSessionManager implementation
3. AgentRuntime skeleton (without plan detection)
4. Basic API endpoints: `/agent/chat`, `/agent/session/{id}`
5. Simple execution: single-tool only
6. Integration tests

**Deliverables:**
- User can send message, get response via single-tool execution
- Sessions persist across requests
- No multi-tool plans yet

---

### Phase 2: Plan Detection & Approval (Week 3)

**Goal:** Multi-tool plan detection and approval flow

**Tasks:**
1. PlanDetector implementation
2. Auto-execute decision logic
3. Plan proposal workflow
4. API endpoints: `/agent/execute`, `/agent/reject`
5. Database: agent_plans table
6. Integration with existing Authorization

**Deliverables:**
- Agent detects multi-tool workflows
- L1 users get plan proposals for WRITE operations
- L1 users auto-execute for READ_ONLY operations
- Approval flow works end-to-end

---

### Phase 3: Event System & WebSocket (Week 4)

**Goal:** Real-time progress updates

**Tasks:**
1. EventBus implementation
2. WebSocket streaming endpoint
3. Event emission in Runtime
4. Database: agent_events table
5. Event persistence (optional)

**Deliverables:**
- Users see live tool execution progress
- Events: plan_proposed, tool_call_started, tool_call_completed
- WebSocket connection stable

---

### Phase 4: Advanced Features (Week 5-6)

**Goal:** Polish and robustness

**Tasks:**
1. Message queueing
2. Interrupt functionality
3. Error handling & partial results
4. Tool knowledge strategy (workflow examples)
5. Performance optimization
6. Monitoring & observability

**Deliverables:**
- Message queue works (1 message max)
- Users can interrupt execution
- Partial results on tool failures
- LLM has better tool knowledge
- Production-ready metrics

---

### Phase 5: L2/L3 Support (Future)

**Goal:** Higher autonomy levels

**Tasks:**
1. L2 (ASSISTED): Auto-execute WRITE_LOW_RISK
2. L3 (SUPERVISED): Auto-execute everything with limits
3. Budget enforcement integration
4. Region restrictions integration

**Deliverables:**
- Full autonomy level spectrum working
- Advanced users can enable higher automation

---

## Appendix A: File Structure

```
copilot_server/
├── agent/
│   ├── __init__.py
│   ├── sessions.py          # AgentSessionManager
│   ├── runtime.py           # AgentRuntime
│   ├── events.py            # EventBus
│   ├── plan_detector.py     # PlanDetector
│   └── models.py            # AgentSession, Plan, Event schemas
│
├── api/
│   └── agent_routes.py      # FastAPI routes for /agent/*
│
├── db/
│   └── migrations/
│       └── 004_agent_runtime.sql  # Schema migration
│
├── governance/              # EXISTING
│   ├── authorization.py     # Reused
│   └── tool_classification.py  # Reused
│
├── mcp/                     # EXISTING
│   ├── orchestrator.py      # Reused
│   └── client.py            # Reused
│
└── tests/
    └── agent/
        ├── test_sessions.py
        ├── test_runtime.py
        ├── test_plan_detector.py
        └── test_integration.py

docs/
└── agent/
    └── workflow_examples.md  # Tool usage patterns
```

---

## Appendix B: Example Complete Flow

**Scenario:** User asks complex question that requires multi-tool workflow

```
1. User → POST /agent/chat
   {
     "message": "Where are battles and what materials needed?",
     "session_id": null,
     "character_id": 1117367444
   }

2. API → SessionManager.create_session()
   → Creates session (id: sess-abc123, autonomy_level: L1)

3. API → Runtime.execute(session)
   → Runs async in background
   → Returns immediately: {"session_id": "sess-abc123", "status": "planning"}

4. Runtime → Build messages from session history
   → Add system prompt with tool categories
   → Add user message

5. Runtime → LLM.chat(messages, tools=115)
   → LLM thinks: "Need war summary, combat losses, material requirements"
   → LLM returns 5 tool_use blocks

6. Runtime → PlanDetector.detect_plan(response)
   → Detects: 5 tools = plan
   → Calculates: max_risk = READ_ONLY
   → Creates Plan object

7. Runtime → should_auto_execute(plan, L1)
   → autonomy_level = L1
   → max_risk = READ_ONLY
   → Returns: TRUE (auto-execute)

8. Runtime → EventBus.emit(PlanProposed)
   → WebSocket sends to client:
   {
     "type": "plan_proposed",
     "auto_executing": true,
     "payload": {
       "purpose": "Analyze war zones and materials",
       "steps": [5 tool calls],
       "max_risk_level": "READ_ONLY"
     }
   }

9. Runtime → _execute_plan(session, plan)
   → For each step:
     a) EventBus.emit(ToolCallStarted)
     b) AuthorizationChecker.check_authorization()
     c) ToolOrchestrator.execute_tool()
     d) EventBus.emit(ToolCallCompleted)

   → WebSocket streams each event live to client

10. Runtime → All tools completed, collect results
    → Build messages with tool results
    → LLM.chat(messages_with_results)
    → LLM synthesizes answer

11. Runtime → EventBus.emit(AnswerReady)
    → WebSocket sends:
    {
      "type": "answer_ready",
      "payload": {
        "answer": "Major battles in Vale of the Silent (147 kills/hr)..."
      }
    }

12. Runtime → session.status = "completed"
    → SessionManager.save_session(session)
    → Redis + PostgreSQL updated

13. User receives answer via WebSocket
    → UI displays: Full answer + execution history
```

---

## Appendix C: Migration from Current System

**Current `/copilot/chat` endpoint:**
- Stateless
- Direct tool execution
- No approval flow
- No session persistence

**Migration Strategy:**

**Option 1: Parallel Run (Recommended)**
- Keep `/copilot/chat` as-is for simple queries
- Add `/agent/chat` for advanced features
- Users opt-in to new system
- Gradual migration

**Option 2: Replace**
- Deprecate `/copilot/chat`
- All traffic goes to `/agent/chat`
- Backward compatibility via `auto_execute_all: true` flag

**Recommendation:** Option 1 - Parallel run allows testing and gradual rollout.

---

## Appendix D: Performance Considerations

### Latency Budget

**Target Latencies:**
- Session create: < 50ms (Redis write)
- Plan detection: < 100ms (parse LLM response)
- Auto-execute decision: < 10ms (simple logic)
- Tool execution: 200-500ms each (depends on MCP tool)
- Full workflow (5 tools): 2-3 seconds

### Scalability

**Bottlenecks:**
- Redis: Can handle 100K sessions easily
- PostgreSQL: Writes can be async (event persistence)
- WebSocket: Need load balancer with sticky sessions
- LLM API: Rate limits (10K RPM for Claude)

**Mitigation:**
- Redis cluster for > 100K sessions
- Async writes to PostgreSQL
- WebSocket horizontal scaling with Redis Pub/Sub
- Queue LLM calls if rate limited

### Resource Usage

**Per Session:**
- Redis: ~10KB per session
- PostgreSQL: ~5KB per session + events
- Memory: ~1MB per active execution (runtime)

**Expected Load:**
- 1000 concurrent sessions = 10MB Redis + 1GB runtime memory
- Easily fits in single 4GB server

---

## Appendix E: Open Questions & Future Enhancements

### Open Questions

1. **Tool Result Caching:** Should we cache tool results (e.g., market_stats for 5 minutes)?
2. **Multi-User Collaboration:** Should sessions support multiple users (corp operations)?
3. **Plan Templates:** Should users save/reuse common workflows?
4. **Scheduled Plans:** Should plans execute at specific times (e.g., daily market analysis)?

### Future Enhancements

1. **Plan Library:** Users share proven workflows
2. **A/B Testing:** Test different system prompts for better plan quality
3. **Metrics Dashboard:** Track plan success rates, tool usage, latency
4. **Voice Interface:** Agent runtime works with existing audio transcription
5. **Multi-LLM Support:** Use different models for planning vs. execution

---

**End of Design Document**

---

## Next Steps

This design is ready for implementation. Recommended approach:

1. **Review this design** with team/stakeholders
2. **Create implementation plan** using `superpowers:writing-plans` skill
3. **Set up git worktree** using `superpowers:using-git-worktrees` skill
4. **Execute Phase 1** (Core Infrastructure) first
5. **Iterate based on feedback**

**Estimated Total Timeline:** 6 weeks to production-ready MVP (Phases 1-4)
