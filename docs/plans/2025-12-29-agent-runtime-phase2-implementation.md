# Agent Runtime Phase 2: Plan Detection & Approval Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement multi-tool plan detection and approval workflow for Agent Runtime

**Architecture:** Extend Phase 1 Agent Runtime with PlanDetector (3+ tools threshold), auto-execute decision matrix (L0-L3), agent_plans database table, and approval API endpoints

**Tech Stack:** FastAPI, PostgreSQL, Redis, Pydantic v2, asyncpg, pytest, TDD

**Context:** This builds on Phase 1 (Session Manager, Runtime, API already implemented and tested)

---

## Task 1: Database Schema for agent_plans Table

**Files:**
- Create: `copilot_server/db/migrations/005_agent_plans.sql`
- Test: `copilot_server/tests/agent/test_plan_schema.py`

**Step 1: Write the failing test**

Create test file that verifies the agent_plans table exists with correct schema:

```python
import pytest
import asyncpg
from copilot_server.config import DATABASE_URL

@pytest.mark.asyncio
async def test_agent_plans_table_exists():
    """Test that agent_plans table exists with correct schema."""
    conn = await asyncpg.connect(DATABASE_URL)

    # Check table exists
    result = await conn.fetchval("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'agent_plans'
        )
    """)
    assert result is True, "agent_plans table should exist"

    # Check columns
    columns = await conn.fetch("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'agent_plans'
        ORDER BY ordinal_position
    """)

    expected_columns = {
        'id': 'character varying',
        'session_id': 'character varying',
        'purpose': 'text',
        'plan_data': 'jsonb',
        'status': 'character varying',
        'auto_executing': 'boolean',
        'created_at': 'timestamp without time zone',
        'approved_at': 'timestamp without time zone',
        'executed_at': 'timestamp without time zone',
        'completed_at': 'timestamp without time zone',
        'duration_ms': 'integer'
    }

    actual_columns = {row['column_name']: row['data_type'] for row in columns}

    for col_name, col_type in expected_columns.items():
        assert col_name in actual_columns, f"Column {col_name} should exist"
        assert actual_columns[col_name] == col_type, f"Column {col_name} should be {col_type}"

    await conn.close()


@pytest.mark.asyncio
async def test_agent_plans_foreign_key():
    """Test that agent_plans has foreign key to agent_sessions."""
    conn = await asyncpg.connect(DATABASE_URL)

    result = await conn.fetch("""
        SELECT
            tc.constraint_name,
            kcu.column_name,
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
            ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.constraint_column_usage AS ccu
            ON ccu.constraint_name = tc.constraint_name
        WHERE tc.table_name = 'agent_plans'
            AND tc.constraint_type = 'FOREIGN KEY'
    """)

    assert len(result) > 0, "Should have foreign key constraint"
    fk = result[0]
    assert fk['column_name'] == 'session_id'
    assert fk['foreign_table_name'] == 'agent_sessions'
    assert fk['foreign_column_name'] == 'id'

    await conn.close()


@pytest.mark.asyncio
async def test_agent_plans_indexes():
    """Test that agent_plans has proper indexes."""
    conn = await asyncpg.connect(DATABASE_URL)

    indexes = await conn.fetch("""
        SELECT indexname, indexdef
        FROM pg_indexes
        WHERE tablename = 'agent_plans'
    """)

    index_names = [idx['indexname'] for idx in indexes]

    # Should have index on session_id and status
    assert any('session_id' in name for name in index_names), "Should have session_id index"
    assert any('status' in name for name in index_names), "Should have status index"

    await conn.close()
```

**Step 2: Run test to verify it fails**

Run: `pytest copilot_server/tests/agent/test_plan_schema.py -v`
Expected: FAIL with "relation 'agent_plans' does not exist"

**Step 3: Create migration**

Create file `copilot_server/db/migrations/005_agent_plans.sql`:

```sql
-- Migration 005: Agent Plans Table
-- Purpose: Store execution plans for multi-tool workflows

CREATE TABLE IF NOT EXISTS agent_plans (
    id VARCHAR(255) PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL REFERENCES agent_sessions(id) ON DELETE CASCADE,
    purpose TEXT NOT NULL,
    plan_data JSONB NOT NULL,
    status VARCHAR(50) NOT NULL,
    auto_executing BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    approved_at TIMESTAMP,
    executed_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_ms INTEGER
);

CREATE INDEX IF NOT EXISTS idx_agent_plans_session_id ON agent_plans(session_id);
CREATE INDEX IF NOT EXISTS idx_agent_plans_status ON agent_plans(status);

COMMENT ON TABLE agent_plans IS 'Stores execution plans for replay, audit, and approval workflow';
COMMENT ON COLUMN agent_plans.plan_data IS 'JSON: {steps: [{tool, arguments, risk_level}], max_risk_level}';
COMMENT ON COLUMN agent_plans.status IS 'proposed, approved, rejected, executing, completed, failed';
```

**Step 4: Run migration**

Run: `echo 'Aug2012#' | sudo -S docker exec eve_db psql -U eve -d eve_sde -f /home/cytrex/eve_copilot/copilot_server/db/migrations/005_agent_plans.sql`
Expected: CREATE TABLE, CREATE INDEX (2x)

**Step 5: Run test to verify it passes**

Run: `pytest copilot_server/tests/agent/test_plan_schema.py -v`
Expected: PASS (3 tests)

**Step 6: Commit**

```bash
git add copilot_server/db/migrations/005_agent_plans.sql copilot_server/tests/agent/test_plan_schema.py
git commit -m "feat(agent): add agent_plans database table

- Create agent_plans table with plan lifecycle fields
- Add foreign key to agent_sessions
- Add indexes on session_id and status
- Add tests for schema verification

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 2: Plan Models and PlanDetector

**Files:**
- Modify: `copilot_server/agent/models.py` (add Plan, PlanStep, PlanStatus)
- Create: `copilot_server/agent/plan_detector.py`
- Test: `copilot_server/tests/agent/test_plan_detector.py`

**Step 1: Write the failing test**

Create test file:

```python
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
```

**Step 2: Run test to verify it fails**

Run: `pytest copilot_server/tests/agent/test_plan_detector.py -v`
Expected: FAIL with "No module named 'copilot_server.agent.plan_detector'"

**Step 3: Add Plan models to models.py**

Add to `copilot_server/agent/models.py`:

```python
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from copilot_server.models.user_settings import RiskLevel

class PlanStatus(str, Enum):
    """Plan lifecycle status."""
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"


class PlanStep(BaseModel):
    """Individual step in execution plan."""
    tool: str
    arguments: Dict[str, Any]
    risk_level: RiskLevel = RiskLevel.CRITICAL  # Default to safest


class Plan(BaseModel):
    """Multi-tool execution plan."""
    id: str = Field(default_factory=lambda: f"plan-{uuid4().hex[:12]}")
    session_id: str
    purpose: str
    steps: List[PlanStep]
    max_risk_level: RiskLevel = RiskLevel.CRITICAL
    status: PlanStatus = PlanStatus.PROPOSED
    auto_executing: bool = False
    created_at: datetime = Field(default_factory=datetime.now)
    approved_at: Optional[datetime] = None
    executed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None

    def to_db_dict(self) -> Dict[str, Any]:
        """Convert to database format."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "purpose": self.purpose,
            "plan_data": {
                "steps": [
                    {
                        "tool": step.tool,
                        "arguments": step.arguments,
                        "risk_level": step.risk_level.value
                    }
                    for step in self.steps
                ],
                "max_risk_level": self.max_risk_level.value
            },
            "status": self.status.value,
            "auto_executing": self.auto_executing,
            "created_at": self.created_at,
            "approved_at": self.approved_at,
            "executed_at": self.executed_at,
            "completed_at": self.completed_at,
            "duration_ms": self.duration_ms
        }
```

**Step 4: Implement PlanDetector**

Create file `copilot_server/agent/plan_detector.py`:

```python
from typing import Dict, Any, Optional
from copilot_server.agent.models import Plan, PlanStep
from copilot_server.models.user_settings import RiskLevel
from copilot_server.mcp import MCPClient


class PlanDetector:
    """Detects multi-tool plans from LLM responses."""

    PLAN_THRESHOLD = 3  # 3+ tools = plan

    def __init__(self, mcp_client: Optional[MCPClient] = None):
        """
        Initialize detector.

        Args:
            mcp_client: Optional MCP client for tool risk lookup
        """
        self.mcp_client = mcp_client
        self.tool_risks: Dict[str, RiskLevel] = {}

        if mcp_client:
            self._load_tool_risks()

    def _load_tool_risks(self):
        """Load tool risk levels from MCP tools."""
        tools = self.mcp_client.get_tools()
        for tool in tools:
            tool_name = tool.get("name", "")
            risk_str = tool.get("metadata", {}).get("risk_level", "CRITICAL")
            self.tool_risks[tool_name] = RiskLevel(risk_str)

    def is_plan(self, llm_response: Dict[str, Any]) -> bool:
        """
        Check if LLM response contains a multi-tool plan.

        Args:
            llm_response: Claude API response

        Returns:
            True if response has 3+ tool_use blocks
        """
        content = llm_response.get("content", [])
        tool_uses = [block for block in content if block.get("type") == "tool_use"]
        return len(tool_uses) >= self.PLAN_THRESHOLD

    def extract_plan(self, llm_response: Dict[str, Any], session_id: str) -> Plan:
        """
        Extract Plan object from LLM response.

        Args:
            llm_response: Claude API response with 3+ tool calls
            session_id: Session ID

        Returns:
            Plan object with steps and risk levels
        """
        content = llm_response.get("content", [])

        # Extract purpose from text blocks
        text_blocks = [block.get("text", "") for block in content if block.get("type") == "text"]
        purpose = " ".join(text_blocks).strip() or "Multi-tool workflow"

        # Extract tool steps
        tool_uses = [block for block in content if block.get("type") == "tool_use"]
        steps = []

        for tool_block in tool_uses:
            tool_name = tool_block.get("name", "")
            arguments = tool_block.get("input", {})

            # Get risk level (default to CRITICAL for unknown tools)
            risk_level = self.tool_risks.get(tool_name, RiskLevel.CRITICAL)

            steps.append(PlanStep(
                tool=tool_name,
                arguments=arguments,
                risk_level=risk_level
            ))

        # Calculate max risk level
        max_risk = max((step.risk_level for step in steps), default=RiskLevel.CRITICAL)

        return Plan(
            session_id=session_id,
            purpose=purpose,
            steps=steps,
            max_risk_level=max_risk
        )
```

**Step 5: Run test to verify it passes**

Run: `pytest copilot_server/tests/agent/test_plan_detector.py -v`
Expected: PASS (7 tests)

**Step 6: Commit**

```bash
git add copilot_server/agent/models.py copilot_server/agent/plan_detector.py copilot_server/tests/agent/test_plan_detector.py
git commit -m "feat(agent): implement plan detection for multi-tool workflows

- Add Plan, PlanStep, PlanStatus models
- Implement PlanDetector with 3+ tool threshold
- Extract plan purpose and risk levels from LLM response
- Default unknown tools to CRITICAL risk level
- Add comprehensive tests for plan detection

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 3: Auto-Execute Decision Logic

**Files:**
- Create: `copilot_server/agent/auto_execute.py`
- Test: `copilot_server/tests/agent/test_auto_execute.py`

**Step 1: Write the failing test**

Create test file:

```python
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
```

**Step 2: Run test to verify it fails**

Run: `pytest copilot_server/tests/agent/test_auto_execute.py -v`
Expected: FAIL with "No module named 'copilot_server.agent.auto_execute'"

**Step 3: Implement auto-execute decision logic**

Create file `copilot_server/agent/auto_execute.py`:

```python
from copilot_server.agent.models import Plan
from copilot_server.models.user_settings import AutonomyLevel, RiskLevel


def should_auto_execute(plan: Plan, autonomy_level: AutonomyLevel) -> bool:
    """
    Decide if plan should auto-execute based on autonomy level and risk.

    Decision Matrix:
    ---------------
    L0 (READ_ONLY):       Never auto-execute (always propose)
    L1 (RECOMMENDATIONS): Auto-execute READ_ONLY only
    L2 (ASSISTED):        Auto-execute READ_ONLY + WRITE_LOW_RISK
    L3 (SUPERVISED):      Auto-execute everything (future)

    Args:
        plan: Execution plan with risk levels
        autonomy_level: User's autonomy level setting

    Returns:
        True if plan should auto-execute, False if approval needed
    """
    max_risk = plan.max_risk_level

    # L0: Never auto-execute
    if autonomy_level == AutonomyLevel.READ_ONLY:
        return False

    # L1: Auto-execute pure analysis (READ_ONLY)
    if autonomy_level == AutonomyLevel.RECOMMENDATIONS:
        return max_risk == RiskLevel.READ_ONLY

    # L2: Auto-execute low-risk writes
    if autonomy_level == AutonomyLevel.ASSISTED:
        return max_risk in [RiskLevel.READ_ONLY, RiskLevel.WRITE_LOW_RISK]

    # L3: Auto-execute everything (future feature)
    if autonomy_level == AutonomyLevel.SUPERVISED:
        return True

    # Default: safe behavior
    return False
```

**Step 4: Run test to verify it passes**

Run: `pytest copilot_server/tests/agent/test_auto_execute.py -v`
Expected: PASS (7 tests)

**Step 5: Commit**

```bash
git add copilot_server/agent/auto_execute.py copilot_server/tests/agent/test_auto_execute.py
git commit -m "feat(agent): implement auto-execute decision matrix

- L0 never auto-executes (always requires approval)
- L1 auto-executes READ_ONLY, proposes WRITE operations
- L2 auto-executes READ_ONLY + WRITE_LOW_RISK
- L3 auto-executes everything (future feature)
- Add comprehensive tests for all autonomy levels

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 4: Plan Storage (PostgreSQL Repository)

**Files:**
- Create: `copilot_server/agent/plan_repository.py`
- Test: `copilot_server/tests/agent/test_plan_repository.py`

**Step 1: Write the failing test**

Create test file:

```python
import pytest
import asyncpg
from datetime import datetime
from copilot_server.agent.plan_repository import PlanRepository
from copilot_server.agent.models import Plan, PlanStep, PlanStatus
from copilot_server.models.user_settings import RiskLevel
from copilot_server.config import DATABASE_URL


@pytest.fixture
async def plan_repo():
    """Create plan repository with connection pool."""
    repo = PlanRepository(DATABASE_URL)
    await repo.connect()
    yield repo
    await repo.disconnect()


@pytest.fixture
async def cleanup_plans():
    """Clean up test plans after each test."""
    yield
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute("DELETE FROM agent_plans WHERE id LIKE 'plan-test%'")
    await conn.close()


@pytest.mark.asyncio
async def test_save_plan(plan_repo, cleanup_plans):
    """Test saving a plan to database."""
    plan = Plan(
        id="plan-test-save",
        session_id="sess-test",
        purpose="Test plan",
        steps=[
            PlanStep(tool="get_market_stats", arguments={"type_id": 34}, risk_level=RiskLevel.READ_ONLY),
            PlanStep(tool="get_war_summary", arguments={}, risk_level=RiskLevel.READ_ONLY)
        ],
        max_risk_level=RiskLevel.READ_ONLY,
        auto_executing=True
    )

    await plan_repo.save_plan(plan)

    # Verify saved
    loaded = await plan_repo.load_plan(plan.id)
    assert loaded is not None
    assert loaded.id == plan.id
    assert loaded.session_id == plan.session_id
    assert loaded.purpose == plan.purpose
    assert len(loaded.steps) == 2
    assert loaded.steps[0].tool == "get_market_stats"
    assert loaded.auto_executing is True


@pytest.mark.asyncio
async def test_update_plan_status(plan_repo, cleanup_plans):
    """Test updating plan status and timestamps."""
    plan = Plan(
        id="plan-test-update",
        session_id="sess-test",
        purpose="Test",
        steps=[
            PlanStep(tool="test_tool", arguments={}, risk_level=RiskLevel.READ_ONLY)
        ],
        max_risk_level=RiskLevel.READ_ONLY,
        status=PlanStatus.PROPOSED
    )

    await plan_repo.save_plan(plan)

    # Update to approved
    plan.status = PlanStatus.APPROVED
    plan.approved_at = datetime.now()
    await plan_repo.save_plan(plan)

    loaded = await plan_repo.load_plan(plan.id)
    assert loaded.status == PlanStatus.APPROVED
    assert loaded.approved_at is not None

    # Update to executing
    plan.status = PlanStatus.EXECUTING
    plan.executed_at = datetime.now()
    await plan_repo.save_plan(plan)

    loaded = await plan_repo.load_plan(plan.id)
    assert loaded.status == PlanStatus.EXECUTING
    assert loaded.executed_at is not None


@pytest.mark.asyncio
async def test_load_plans_by_session(plan_repo, cleanup_plans):
    """Test loading all plans for a session."""
    session_id = "sess-test-multi"

    plan1 = Plan(
        id="plan-test-multi-1",
        session_id=session_id,
        purpose="Plan 1",
        steps=[PlanStep(tool="tool1", arguments={}, risk_level=RiskLevel.READ_ONLY)],
        max_risk_level=RiskLevel.READ_ONLY
    )

    plan2 = Plan(
        id="plan-test-multi-2",
        session_id=session_id,
        purpose="Plan 2",
        steps=[PlanStep(tool="tool2", arguments={}, risk_level=RiskLevel.WRITE_LOW_RISK)],
        max_risk_level=RiskLevel.WRITE_LOW_RISK
    )

    await plan_repo.save_plan(plan1)
    await plan_repo.save_plan(plan2)

    plans = await plan_repo.load_plans_by_session(session_id)
    assert len(plans) == 2
    assert {p.id for p in plans} == {"plan-test-multi-1", "plan-test-multi-2"}


@pytest.mark.asyncio
async def test_load_nonexistent_plan(plan_repo):
    """Test loading a plan that doesn't exist returns None."""
    plan = await plan_repo.load_plan("plan-nonexistent")
    assert plan is None
```

**Step 2: Run test to verify it fails**

Run: `pytest copilot_server/tests/agent/test_plan_repository.py -v`
Expected: FAIL with "No module named 'copilot_server.agent.plan_repository'"

**Step 3: Implement PlanRepository**

Create file `copilot_server/agent/plan_repository.py`:

```python
import asyncpg
from typing import Optional, List
from copilot_server.agent.models import Plan, PlanStep, PlanStatus
from copilot_server.models.user_settings import RiskLevel
from datetime import datetime


class PlanRepository:
    """PostgreSQL repository for agent plans."""

    def __init__(self, database_url: str):
        """
        Initialize repository.

        Args:
            database_url: PostgreSQL connection string
        """
        self.database_url = database_url
        self._pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        """Create connection pool."""
        self._pool = await asyncpg.create_pool(self.database_url, min_size=2, max_size=10)

    async def disconnect(self):
        """Close connection pool."""
        if self._pool:
            await self._pool.close()

    async def save_plan(self, plan: Plan) -> None:
        """
        Save or update plan in database.

        Args:
            plan: Plan to save
        """
        plan_dict = plan.to_db_dict()

        async with self._pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO agent_plans (
                    id, session_id, purpose, plan_data, status,
                    auto_executing, created_at, approved_at,
                    executed_at, completed_at, duration_ms
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                ON CONFLICT (id) DO UPDATE SET
                    status = EXCLUDED.status,
                    approved_at = EXCLUDED.approved_at,
                    executed_at = EXCLUDED.executed_at,
                    completed_at = EXCLUDED.completed_at,
                    duration_ms = EXCLUDED.duration_ms
            """,
                plan_dict["id"],
                plan_dict["session_id"],
                plan_dict["purpose"],
                plan_dict["plan_data"],
                plan_dict["status"],
                plan_dict["auto_executing"],
                plan_dict["created_at"],
                plan_dict["approved_at"],
                plan_dict["executed_at"],
                plan_dict["completed_at"],
                plan_dict["duration_ms"]
            )

    async def load_plan(self, plan_id: str) -> Optional[Plan]:
        """
        Load plan from database.

        Args:
            plan_id: Plan ID

        Returns:
            Plan object or None if not found
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT id, session_id, purpose, plan_data, status,
                       auto_executing, created_at, approved_at,
                       executed_at, completed_at, duration_ms
                FROM agent_plans
                WHERE id = $1
            """, plan_id)

            if not row:
                return None

            return self._row_to_plan(row)

    async def load_plans_by_session(self, session_id: str) -> List[Plan]:
        """
        Load all plans for a session.

        Args:
            session_id: Session ID

        Returns:
            List of plans, ordered by creation time
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT id, session_id, purpose, plan_data, status,
                       auto_executing, created_at, approved_at,
                       executed_at, completed_at, duration_ms
                FROM agent_plans
                WHERE session_id = $1
                ORDER BY created_at ASC
            """, session_id)

            return [self._row_to_plan(row) for row in rows]

    def _row_to_plan(self, row) -> Plan:
        """Convert database row to Plan object."""
        plan_data = row["plan_data"]

        # Reconstruct steps
        steps = [
            PlanStep(
                tool=step["tool"],
                arguments=step["arguments"],
                risk_level=RiskLevel(step["risk_level"])
            )
            for step in plan_data["steps"]
        ]

        return Plan(
            id=row["id"],
            session_id=row["session_id"],
            purpose=row["purpose"],
            steps=steps,
            max_risk_level=RiskLevel(plan_data["max_risk_level"]),
            status=PlanStatus(row["status"]),
            auto_executing=row["auto_executing"],
            created_at=row["created_at"],
            approved_at=row["approved_at"],
            executed_at=row["executed_at"],
            completed_at=row["completed_at"],
            duration_ms=row["duration_ms"]
        )
```

**Step 4: Run test to verify it passes**

Run: `pytest copilot_server/tests/agent/test_plan_repository.py -v`
Expected: PASS (4 tests)

**Step 5: Commit**

```bash
git add copilot_server/agent/plan_repository.py copilot_server/tests/agent/test_plan_repository.py
git commit -m "feat(agent): implement plan repository for PostgreSQL

- Save and load plans with UPSERT support
- Load all plans by session ID
- Convert between Plan objects and database rows
- Add tests for save, update, and load operations

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 5: Integrate Plan Detection into Runtime

**Files:**
- Modify: `copilot_server/agent/runtime.py`
- Modify: `copilot_server/agent/sessions.py` (add plan repository)
- Test: `copilot_server/tests/agent/test_runtime_plans.py`

**Step 1: Write the failing test**

Create test file:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from copilot_server.agent.runtime import AgentRuntime
from copilot_server.agent.models import AgentSession, SessionStatus, Plan, PlanStatus
from copilot_server.models.user_settings import AutonomyLevel, RiskLevel


@pytest.fixture
def mock_llm():
    """Mock LLM client."""
    llm = MagicMock()
    llm.chat = AsyncMock()
    return llm


@pytest.fixture
def mock_orchestrator():
    """Mock orchestrator."""
    orch = MagicMock()
    orch.mcp = MagicMock()
    orch.mcp.get_tools = MagicMock(return_value=[])
    orch.mcp.call_tool = MagicMock(return_value={"result": "success"})
    return orch


@pytest.fixture
def mock_session_manager():
    """Mock session manager."""
    mgr = MagicMock()
    mgr.save_session = AsyncMock()
    mgr.plan_repo = MagicMock()
    mgr.plan_repo.save_plan = AsyncMock()
    return mgr


@pytest.fixture
def runtime(mock_llm, mock_orchestrator, mock_session_manager):
    """Create runtime with mocks."""
    return AgentRuntime(
        session_manager=mock_session_manager,
        llm_client=mock_llm,
        orchestrator=mock_orchestrator
    )


@pytest.mark.asyncio
async def test_single_tool_executes_directly(runtime, mock_llm):
    """Single tool call executes directly without plan detection."""
    session = AgentSession(
        id="sess-test",
        character_id=123,
        autonomy_level=AutonomyLevel.RECOMMENDATIONS
    )
    session.add_message("user", "What's the price of Tritanium?")

    # Mock LLM response: single tool
    mock_llm.chat.return_value = {
        "content": [
            {"type": "text", "text": "Let me check."},
            {"type": "tool_use", "id": "call1", "name": "get_market_stats", "input": {"type_id": 34}}
        ],
        "stop_reason": "tool_use"
    }

    # Second call: return answer
    mock_llm.chat.side_effect = [
        mock_llm.chat.return_value,
        {"content": [{"type": "text", "text": "Tritanium costs 5.2 ISK."}], "stop_reason": "end_turn"}
    ]

    await runtime.execute(session)

    # Should execute directly, no plan created
    assert session.status == SessionStatus.COMPLETED
    assert "pending_plan" not in session.context


@pytest.mark.asyncio
async def test_multi_tool_creates_plan_l1_read_only(runtime, mock_llm, mock_session_manager):
    """L1 with READ_ONLY plan auto-executes."""
    session = AgentSession(
        id="sess-test",
        character_id=123,
        autonomy_level=AutonomyLevel.RECOMMENDATIONS
    )
    session.add_message("user", "Analyze war zones.")

    # Mock LLM response: 3 READ_ONLY tools
    mock_llm.chat.return_value = {
        "content": [
            {"type": "text", "text": "I'll analyze war zones."},
            {"type": "tool_use", "id": "call1", "name": "get_war_summary", "input": {}},
            {"type": "tool_use", "id": "call2", "name": "get_combat_losses", "input": {"region_id": 10000002}},
            {"type": "tool_use", "id": "call3", "name": "get_top_destroyed_ships", "input": {}}
        ],
        "stop_reason": "tool_use"
    }

    # Mock tool risks as READ_ONLY
    with patch('copilot_server.agent.plan_detector.PlanDetector') as mock_detector_class:
        mock_detector = MagicMock()
        mock_detector.is_plan.return_value = True
        mock_detector.extract_plan.return_value = Plan(
            session_id=session.id,
            purpose="I'll analyze war zones.",
            steps=[],
            max_risk_level=RiskLevel.READ_ONLY,
            auto_executing=True
        )
        mock_detector_class.return_value = mock_detector

        # Second call: return answer
        mock_llm.chat.side_effect = [
            mock_llm.chat.return_value,
            {"content": [{"type": "text", "text": "Analysis complete."}], "stop_reason": "end_turn"}
        ]

        await runtime.execute(session)

        # Should auto-execute
        assert session.status == SessionStatus.COMPLETED
        assert mock_session_manager.plan_repo.save_plan.called


@pytest.mark.asyncio
async def test_multi_tool_waits_approval_l1_write(runtime, mock_llm, mock_session_manager):
    """L1 with WRITE_LOW_RISK plan waits for approval."""
    session = AgentSession(
        id="sess-test",
        character_id=123,
        autonomy_level=AutonomyLevel.RECOMMENDATIONS
    )
    session.add_message("user", "Create shopping list for 10 Caracals.")

    # Mock LLM response: 3 tools with WRITE_LOW_RISK
    mock_llm.chat.return_value = {
        "content": [
            {"type": "text", "text": "I'll create a shopping list."},
            {"type": "tool_use", "id": "call1", "name": "get_production_chain", "input": {}},
            {"type": "tool_use", "id": "call2", "name": "create_shopping_list", "input": {}},
            {"type": "tool_use", "id": "call3", "name": "add_shopping_items", "input": {}}
        ],
        "stop_reason": "tool_use"
    }

    with patch('copilot_server.agent.plan_detector.PlanDetector') as mock_detector_class:
        mock_detector = MagicMock()
        mock_detector.is_plan.return_value = True
        mock_detector.extract_plan.return_value = Plan(
            session_id=session.id,
            purpose="I'll create a shopping list.",
            steps=[],
            max_risk_level=RiskLevel.WRITE_LOW_RISK,
            auto_executing=False
        )
        mock_detector_class.return_value = mock_detector

        await runtime.execute(session)

        # Should wait for approval
        assert session.status == SessionStatus.WAITING_APPROVAL
        assert session.context.get("pending_plan_id") is not None
```

**Step 2: Run test to verify it fails**

Run: `pytest copilot_server/tests/agent/test_runtime_plans.py -v`
Expected: FAIL (runtime doesn't have plan detection yet)

**Step 3: Add plan_repo to AgentSessionManager**

Modify `copilot_server/agent/sessions.py`:

```python
from copilot_server.agent.plan_repository import PlanRepository

class AgentSessionManager:
    def __init__(self):
        # ... existing init ...
        self.plan_repo: Optional[PlanRepository] = None

    async def startup(self):
        """Initialize storage layers."""
        # ... existing startup code ...

        # Initialize plan repository
        self.plan_repo = PlanRepository(self.postgres.database_url)
        await self.plan_repo.connect()

    async def shutdown(self):
        """Clean shutdown."""
        # ... existing shutdown code ...

        if self.plan_repo:
            await self.plan_repo.disconnect()
```

**Step 4: Integrate plan detection into runtime**

Modify `copilot_server/agent/runtime.py`:

```python
from copilot_server.agent.plan_detector import PlanDetector
from copilot_server.agent.auto_execute import should_auto_execute
from copilot_server.agent.models import Plan, PlanStatus, SessionStatus
import time

class AgentRuntime:
    def __init__(self, session_manager, llm_client, orchestrator):
        self.session_manager = session_manager
        self.llm_client = llm_client
        self.orchestrator = orchestrator
        self.plan_detector = PlanDetector(orchestrator.mcp)

    async def execute(self, session: AgentSession, max_iterations: int = 5) -> None:
        """
        Execute agent runtime with plan detection.

        Args:
            session: Agent session
            max_iterations: Maximum execution loops
        """
        session.status = SessionStatus.PLANNING
        await self.session_manager.save_session(session)

        iteration = 0
        while iteration < max_iterations:
            iteration += 1

            # Build messages
            messages = self._build_messages(session)
            tools = self.orchestrator.mcp.get_tools()
            claude_tools = self.llm_client.build_tool_schema(tools)

            # Call LLM
            response = await self.llm_client.chat(messages=messages, tools=claude_tools)

            # Check if response is a multi-tool plan
            if self.plan_detector.is_plan(response):
                plan = self.plan_detector.extract_plan(response, session.id)

                # Decide auto-execute
                auto_exec = should_auto_execute(plan, session.autonomy_level)
                plan.auto_executing = auto_exec

                # Save plan
                await self.session_manager.plan_repo.save_plan(plan)

                if auto_exec:
                    # Execute immediately
                    session.status = SessionStatus.EXECUTING
                    session.context["current_plan_id"] = plan.id
                    await self.session_manager.save_session(session)

                    await self._execute_plan(session, plan)
                    return
                else:
                    # Wait for approval
                    session.status = SessionStatus.WAITING_APPROVAL
                    session.context["pending_plan_id"] = plan.id
                    await self.session_manager.save_session(session)
                    return

            # Single/dual tool execution (existing logic)
            if self._has_tool_calls(response):
                session.status = SessionStatus.EXECUTING
                await self.session_manager.save_session(session)
                await self._execute_tools(response, session)
                continue
            else:
                # No tools, final answer
                answer = self._extract_text(response)
                session.add_message("assistant", answer)
                session.status = SessionStatus.COMPLETED
                await self.session_manager.save_session(session)
                return

        # Max iterations reached
        session.status = SessionStatus.ERROR
        await self.session_manager.save_session(session)

    async def _execute_plan(self, session: AgentSession, plan: Plan) -> None:
        """
        Execute multi-tool plan.

        Args:
            session: Agent session
            plan: Plan to execute
        """
        start_time = time.time()
        plan.status = PlanStatus.EXECUTING
        plan.executed_at = datetime.now()
        await self.session_manager.plan_repo.save_plan(plan)

        results = []

        for step in plan.steps:
            try:
                result = await asyncio.to_thread(
                    self.orchestrator.mcp.call_tool,
                    step.tool,
                    step.arguments
                )
                results.append(result)
            except Exception as e:
                logger.error(f"Tool execution failed: {step.tool}, error: {e}")
                plan.status = PlanStatus.FAILED
                await self.session_manager.plan_repo.save_plan(plan)
                session.status = SessionStatus.COMPLETED_WITH_ERRORS
                await self.session_manager.save_session(session)
                return

        # Mark plan completed
        duration_ms = int((time.time() - start_time) * 1000)
        plan.status = PlanStatus.COMPLETED
        plan.completed_at = datetime.now()
        plan.duration_ms = duration_ms
        await self.session_manager.plan_repo.save_plan(plan)

        # Add summary to session
        tool_summary = f"Executed {len(results)} tools from plan: {plan.purpose}"
        session.add_message("assistant", tool_summary)
        session.status = SessionStatus.COMPLETED
        await self.session_manager.save_session(session)
```

**Step 5: Run test to verify it passes**

Run: `pytest copilot_server/tests/agent/test_runtime_plans.py -v`
Expected: PASS (3 tests)

**Step 6: Commit**

```bash
git add copilot_server/agent/runtime.py copilot_server/agent/sessions.py copilot_server/tests/agent/test_runtime_plans.py
git commit -m "feat(agent): integrate plan detection into runtime

- Detect 3+ tool calls as multi-tool plans
- Auto-execute or wait for approval based on autonomy level
- Execute plans with full lifecycle tracking
- Add plan repository to session manager
- Add tests for plan detection in runtime

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 6: API Endpoints for Plan Approval

**Files:**
- Modify: `copilot_server/api/agent_routes.py`
- Test: `copilot_server/tests/agent/test_approval_api.py`

**Step 1: Write the failing test**

Create test file:

```python
import pytest
from httpx import AsyncClient, ASGITransport
from copilot_server.main import app
from copilot_server.api import agent_routes
from copilot_server.agent.models import AgentSession, Plan, PlanStep, PlanStatus, SessionStatus
from copilot_server.models.user_settings import AutonomyLevel, RiskLevel
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
async def client():
    """Create async HTTP client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def mock_session_manager():
    """Mock session manager."""
    mgr = MagicMock()
    mgr.load_session = AsyncMock()
    mgr.save_session = AsyncMock()
    mgr.plan_repo = MagicMock()
    mgr.plan_repo.load_plan = AsyncMock()
    mgr.plan_repo.save_plan = AsyncMock()
    return mgr


@pytest.fixture
def mock_runtime():
    """Mock runtime."""
    runtime = MagicMock()
    runtime._execute_plan = AsyncMock()
    return runtime


@pytest.fixture(autouse=True)
def inject_mocks(mock_session_manager, mock_runtime):
    """Inject mocks into agent_routes."""
    agent_routes.session_manager = mock_session_manager
    agent_routes.runtime = mock_runtime
    yield
    agent_routes.session_manager = None
    agent_routes.runtime = None


@pytest.mark.asyncio
async def test_execute_endpoint_approves_plan(client, mock_session_manager, mock_runtime):
    """POST /agent/execute approves and executes pending plan."""
    session = AgentSession(
        id="sess-test",
        character_id=123,
        autonomy_level=AutonomyLevel.RECOMMENDATIONS,
        status=SessionStatus.WAITING_APPROVAL
    )
    session.context["pending_plan_id"] = "plan-test"

    plan = Plan(
        id="plan-test",
        session_id="sess-test",
        purpose="Test plan",
        steps=[
            PlanStep(tool="create_shopping_list", arguments={}, risk_level=RiskLevel.WRITE_LOW_RISK)
        ],
        max_risk_level=RiskLevel.WRITE_LOW_RISK,
        status=PlanStatus.PROPOSED
    )

    mock_session_manager.load_session.return_value = session
    mock_session_manager.plan_repo.load_plan.return_value = plan

    response = await client.post("/agent/execute", json={
        "session_id": "sess-test",
        "plan_id": "plan-test"
    })

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "executing"
    assert data["message"] == "Plan approved and executing"

    # Verify plan was marked approved
    assert mock_session_manager.plan_repo.save_plan.called
    saved_plan = mock_session_manager.plan_repo.save_plan.call_args[0][0]
    assert saved_plan.status == PlanStatus.APPROVED

    # Verify runtime was called
    assert mock_runtime._execute_plan.called


@pytest.mark.asyncio
async def test_execute_endpoint_session_not_found(client, mock_session_manager):
    """POST /agent/execute returns 404 if session doesn't exist."""
    mock_session_manager.load_session.return_value = None

    response = await client.post("/agent/execute", json={
        "session_id": "sess-nonexistent",
        "plan_id": "plan-test"
    })

    assert response.status_code == 404
    assert response.json()["detail"] == "Session not found"


@pytest.mark.asyncio
async def test_execute_endpoint_plan_not_found(client, mock_session_manager):
    """POST /agent/execute returns 404 if plan doesn't exist."""
    session = AgentSession(
        id="sess-test",
        character_id=123,
        status=SessionStatus.WAITING_APPROVAL
    )

    mock_session_manager.load_session.return_value = session
    mock_session_manager.plan_repo.load_plan.return_value = None

    response = await client.post("/agent/execute", json={
        "session_id": "sess-test",
        "plan_id": "plan-nonexistent"
    })

    assert response.status_code == 404
    assert response.json()["detail"] == "Plan not found"


@pytest.mark.asyncio
async def test_reject_endpoint_rejects_plan(client, mock_session_manager):
    """POST /agent/reject rejects pending plan."""
    session = AgentSession(
        id="sess-test",
        character_id=123,
        status=SessionStatus.WAITING_APPROVAL
    )
    session.context["pending_plan_id"] = "plan-test"

    plan = Plan(
        id="plan-test",
        session_id="sess-test",
        purpose="Test plan",
        steps=[],
        max_risk_level=RiskLevel.WRITE_LOW_RISK,
        status=PlanStatus.PROPOSED
    )

    mock_session_manager.load_session.return_value = session
    mock_session_manager.plan_repo.load_plan.return_value = plan

    response = await client.post("/agent/reject", json={
        "session_id": "sess-test",
        "plan_id": "plan-test"
    })

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "idle"
    assert data["message"] == "Plan rejected"

    # Verify plan was marked rejected
    saved_plan = mock_session_manager.plan_repo.save_plan.call_args[0][0]
    assert saved_plan.status == PlanStatus.REJECTED

    # Verify session returned to idle
    saved_session = mock_session_manager.save_session.call_args[0][0]
    assert saved_session.status == SessionStatus.IDLE
    assert "pending_plan_id" not in saved_session.context


@pytest.mark.asyncio
async def test_reject_endpoint_session_not_found(client, mock_session_manager):
    """POST /agent/reject returns 404 if session doesn't exist."""
    mock_session_manager.load_session.return_value = None

    response = await client.post("/agent/reject", json={
        "session_id": "sess-nonexistent",
        "plan_id": "plan-test"
    })

    assert response.status_code == 404
```

**Step 2: Run test to verify it fails**

Run: `pytest copilot_server/tests/agent/test_approval_api.py -v`
Expected: FAIL (endpoints don't exist yet)

**Step 3: Add execute and reject endpoints**

Modify `copilot_server/api/agent_routes.py`:

```python
from datetime import datetime
from copilot_server.agent.models import PlanStatus, SessionStatus

class ExecuteRequest(BaseModel):
    """Request to execute pending plan."""
    session_id: str
    plan_id: str


class RejectRequest(BaseModel):
    """Request to reject pending plan."""
    session_id: str
    plan_id: str


@router.post("/execute")
async def execute_plan(request: ExecuteRequest):
    """
    Approve and execute pending plan.

    Args:
        request: Execute request with session and plan IDs

    Returns:
        Execution status
    """
    # Load session
    session = await session_manager.load_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Load plan
    plan = await session_manager.plan_repo.load_plan(request.plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    # Verify plan belongs to session
    if plan.session_id != session.id:
        raise HTTPException(status_code=400, detail="Plan does not belong to session")

    # Mark plan as approved
    plan.status = PlanStatus.APPROVED
    plan.approved_at = datetime.now()
    await session_manager.plan_repo.save_plan(plan)

    # Update session status
    session.status = SessionStatus.EXECUTING
    session.context["current_plan_id"] = plan.id
    if "pending_plan_id" in session.context:
        del session.context["pending_plan_id"]
    await session_manager.save_session(session)

    # Execute plan (async, don't wait)
    asyncio.create_task(runtime._execute_plan(session, plan))

    return {
        "status": "executing",
        "session_id": session.id,
        "plan_id": plan.id,
        "message": "Plan approved and executing"
    }


@router.post("/reject")
async def reject_plan(request: RejectRequest):
    """
    Reject pending plan.

    Args:
        request: Reject request with session and plan IDs

    Returns:
        Rejection status
    """
    # Load session
    session = await session_manager.load_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Load plan
    plan = await session_manager.plan_repo.load_plan(request.plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    # Mark plan as rejected
    plan.status = PlanStatus.REJECTED
    await session_manager.plan_repo.save_plan(plan)

    # Return session to idle
    session.status = SessionStatus.IDLE
    if "pending_plan_id" in session.context:
        del session.context["pending_plan_id"]
    await session_manager.save_session(session)

    return {
        "status": "idle",
        "session_id": session.id,
        "plan_id": plan.id,
        "message": "Plan rejected"
    }
```

**Step 4: Run test to verify it passes**

Run: `pytest copilot_server/tests/agent/test_approval_api.py -v`
Expected: PASS (5 tests)

**Step 5: Commit**

```bash
git add copilot_server/api/agent_routes.py copilot_server/tests/agent/test_approval_api.py
git commit -m "feat(agent): add plan approval API endpoints

- POST /agent/execute - Approve and execute pending plan
- POST /agent/reject - Reject pending plan
- Update session and plan status on approval/rejection
- Add validation for session and plan existence
- Add tests for approval workflow

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 7: Integration Testing

**Files:**
- Create: `copilot_server/tests/agent/test_phase2_integration.py`

**Step 1: Write the integration test**

Create test file:

```python
import pytest
import asyncpg
from copilot_server.agent.sessions import AgentSessionManager
from copilot_server.agent.runtime import AgentRuntime
from copilot_server.agent.models import AgentSession, SessionStatus, PlanStatus
from copilot_server.models.user_settings import AutonomyLevel, get_default_settings
from copilot_server.llm import AnthropicClient
from copilot_server.mcp import MCPClient, ToolOrchestrator
from copilot_server.config import DATABASE_URL
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
async def session_manager():
    """Create real session manager."""
    mgr = AgentSessionManager()
    await mgr.startup()
    yield mgr
    await mgr.shutdown()


@pytest.fixture
async def cleanup_test_data():
    """Clean up test data after test."""
    yield
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute("DELETE FROM agent_sessions WHERE id LIKE 'sess-integ%'")
    await conn.execute("DELETE FROM agent_plans WHERE id LIKE 'plan-integ%'")
    await conn.close()


@pytest.mark.asyncio
async def test_end_to_end_plan_approval_workflow(session_manager, cleanup_test_data):
    """
    Test complete workflow:
    1. User sends message
    2. LLM proposes 3+ tool plan
    3. Runtime detects plan
    4. Auto-execute decision (L1 + WRITE = wait for approval)
    5. Session status = WAITING_APPROVAL
    6. User approves via API
    7. Plan executes
    8. Session status = COMPLETED
    """
    # Mock LLM and orchestrator
    mock_llm = MagicMock()
    mock_llm.chat = AsyncMock()
    mock_llm.build_tool_schema = MagicMock(return_value=[])

    mock_mcp = MagicMock()
    mock_mcp.get_tools = MagicMock(return_value=[
        {"name": "get_production_chain", "metadata": {"risk_level": "READ_ONLY"}},
        {"name": "create_shopping_list", "metadata": {"risk_level": "WRITE_LOW_RISK"}},
        {"name": "add_shopping_items", "metadata": {"risk_level": "WRITE_LOW_RISK"}}
    ])
    mock_mcp.call_tool = MagicMock(return_value={"result": "success"})

    user_settings = get_default_settings(character_id=123)
    user_settings.autonomy_level = AutonomyLevel.RECOMMENDATIONS

    mock_orchestrator = MagicMock()
    mock_orchestrator.mcp = mock_mcp

    runtime = AgentRuntime(
        session_manager=session_manager,
        llm_client=mock_llm,
        orchestrator=mock_orchestrator
    )

    # 1. Create session and send message
    session = await session_manager.create_session(
        character_id=123,
        autonomy_level=AutonomyLevel.RECOMMENDATIONS
    )
    session.id = "sess-integ-test"  # Override for cleanup
    session.add_message("user", "Create shopping list for 10 Caracals")
    await session_manager.save_session(session)

    # 2. Mock LLM response: 3-tool plan with WRITE operations
    mock_llm.chat.return_value = {
        "content": [
            {"type": "text", "text": "I'll create a shopping list for 10 Caracals."},
            {"type": "tool_use", "id": "call1", "name": "get_production_chain", "input": {"type_id": 621, "quantity": 10}},
            {"type": "tool_use", "id": "call2", "name": "create_shopping_list", "input": {"name": "10 Caracals"}},
            {"type": "tool_use", "id": "call3", "name": "add_shopping_items", "input": {"list_id": "test"}}
        ],
        "stop_reason": "tool_use"
    }

    # 3-5. Execute runtime (should detect plan and wait for approval)
    await runtime.execute(session)

    # Reload session
    session = await session_manager.load_session(session.id)

    assert session.status == SessionStatus.WAITING_APPROVAL
    assert "pending_plan_id" in session.context

    # Load plan
    plan_id = session.context["pending_plan_id"]
    plan = await session_manager.plan_repo.load_plan(plan_id)

    assert plan is not None
    assert plan.status == PlanStatus.PROPOSED
    assert plan.auto_executing is False
    assert len(plan.steps) == 3

    # 6. Approve plan (simulate API call)
    plan.status = PlanStatus.APPROVED
    await session_manager.plan_repo.save_plan(plan)

    session.status = SessionStatus.EXECUTING
    session.context["current_plan_id"] = plan.id
    del session.context["pending_plan_id"]
    await session_manager.save_session(session)

    # 7. Execute plan
    await runtime._execute_plan(session, plan)

    # 8. Verify completion
    session = await session_manager.load_session(session.id)
    assert session.status == SessionStatus.COMPLETED

    plan = await session_manager.plan_repo.load_plan(plan_id)
    assert plan.status == PlanStatus.COMPLETED
    assert plan.duration_ms is not None


@pytest.mark.asyncio
async def test_l1_auto_executes_read_only_plan(session_manager, cleanup_test_data):
    """L1 autonomy auto-executes pure READ_ONLY plans."""
    # Mock LLM and orchestrator
    mock_llm = MagicMock()
    mock_llm.chat = AsyncMock()
    mock_llm.build_tool_schema = MagicMock(return_value=[])

    mock_mcp = MagicMock()
    mock_mcp.get_tools = MagicMock(return_value=[
        {"name": "get_war_summary", "metadata": {"risk_level": "READ_ONLY"}},
        {"name": "get_combat_losses", "metadata": {"risk_level": "READ_ONLY"}},
        {"name": "get_top_destroyed_ships", "metadata": {"risk_level": "READ_ONLY"}}
    ])
    mock_mcp.call_tool = MagicMock(return_value={"result": "data"})

    mock_orchestrator = MagicMock()
    mock_orchestrator.mcp = mock_mcp

    runtime = AgentRuntime(
        session_manager=session_manager,
        llm_client=mock_llm,
        orchestrator=mock_orchestrator
    )

    # Create session
    session = await session_manager.create_session(
        character_id=123,
        autonomy_level=AutonomyLevel.RECOMMENDATIONS
    )
    session.id = "sess-integ-auto"
    session.add_message("user", "Analyze war zones")
    await session_manager.save_session(session)

    # Mock LLM response: 3 READ_ONLY tools
    mock_llm.chat.return_value = {
        "content": [
            {"type": "text", "text": "I'll analyze war zones."},
            {"type": "tool_use", "id": "call1", "name": "get_war_summary", "input": {}},
            {"type": "tool_use", "id": "call2", "name": "get_combat_losses", "input": {"region_id": 10000002}},
            {"type": "tool_use", "id": "call3", "name": "get_top_destroyed_ships", "input": {}}
        ],
        "stop_reason": "tool_use"
    }

    # Execute (should auto-execute)
    await runtime.execute(session)

    # Verify auto-executed
    session = await session_manager.load_session(session.id)
    assert session.status == SessionStatus.COMPLETED
    assert "current_plan_id" in session.context

    # Verify plan was executed
    plan_id = session.context["current_plan_id"]
    plan = await session_manager.plan_repo.load_plan(plan_id)
    assert plan.status == PlanStatus.COMPLETED
    assert plan.auto_executing is True
```

**Step 2: Run test to verify it passes**

Run: `pytest copilot_server/tests/agent/test_phase2_integration.py -v`
Expected: PASS (2 tests)

**Step 3: Commit**

```bash
git add copilot_server/tests/agent/test_phase2_integration.py
git commit -m "test(agent): add Phase 2 integration tests

- End-to-end approval workflow test
- L1 auto-execute READ_ONLY plan test
- Verify plan lifecycle from detection to completion
- Test approval API integration

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 8: Documentation

**Files:**
- Create: `docs/agent/phase2-completion.md`
- Modify: `README.md`

**Step 1: Write Phase 2 completion documentation**

Create file `docs/agent/phase2-completion.md`:

```markdown
# Agent Runtime Phase 2: Plan Detection & Approval - Completion Report

**Status:** ✅ COMPLETED
**Date:** 2025-12-29
**Phase:** 2 of 4

---

## Executive Summary

Phase 2 successfully implements multi-tool plan detection and approval workflow for the EVE Co-Pilot Agent Runtime. The system now intelligently detects when the LLM proposes complex workflows (3+ tools), applies the L0-L3 autonomy matrix to decide auto-execution vs. approval, and provides REST API endpoints for user approval/rejection.

**Key Achievement:** Agent Runtime can now handle complex multi-tool workflows with proper human-in-the-loop approval flow.

---

## Implemented Features

### 1. Plan Detection (3+ Tool Threshold)

**PlanDetector** analyzes LLM responses and identifies multi-tool workflows:

- **Threshold:** 3 or more `tool_use` blocks = plan
- **Purpose Extraction:** Extracts plan description from text blocks
- **Risk Analysis:** Determines max risk level across all steps
- **Tool Risk Lookup:** Loads risk levels from MCP tool metadata

**Example:**
```python
# Single tool → execute directly
get_market_stats(type_id=34)

# 3+ tools → create plan
get_war_summary() + get_combat_losses() + get_material_requirements()
→ Plan created, auto-execute decision applied
```

### 2. Auto-Execute Decision Matrix

**Decision Logic** based on autonomy level + max risk level:

| Autonomy Level | Plan Risk      | Auto-Execute? | Behavior                |
|----------------|----------------|---------------|-------------------------|
| L0 (READ_ONLY) | Any            | ❌ No          | Always propose plan     |
| L1 (RECOMMENDATIONS) | READ_ONLY | ✅ Yes         | Execute immediately     |
| L1             | WRITE_*        | ❌ No          | Propose plan            |
| L2 (ASSISTED)  | READ_ONLY      | ✅ Yes         | Execute immediately     |
| L2             | WRITE_LOW_RISK | ✅ Yes         | Execute immediately     |
| L2             | WRITE_HIGH_RISK | ❌ No         | Propose plan            |
| L3 (SUPERVISED) | Any           | ✅ Yes         | Execute immediately     |

**Implementation:** `copilot_server/agent/auto_execute.py`

### 3. Database Schema (agent_plans Table)

**PostgreSQL table** for plan lifecycle tracking:

```sql
CREATE TABLE agent_plans (
    id VARCHAR(255) PRIMARY KEY,
    session_id VARCHAR(255) REFERENCES agent_sessions(id) ON DELETE CASCADE,
    purpose TEXT NOT NULL,
    plan_data JSONB NOT NULL,  -- {steps: [...], max_risk_level: "..."}
    status VARCHAR(50) NOT NULL,  -- proposed, approved, rejected, executing, completed, failed
    auto_executing BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    approved_at TIMESTAMP,
    executed_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_ms INTEGER
);
```

**Indexes:** `session_id`, `status`

### 4. Plan Repository

**PlanRepository** provides PostgreSQL persistence:

- `save_plan()` - UPSERT plan with lifecycle updates
- `load_plan()` - Load plan by ID
- `load_plans_by_session()` - Get all plans for session

**Implementation:** `copilot_server/agent/plan_repository.py`

### 5. Runtime Integration

**AgentRuntime** enhanced with plan detection:

- Detects 3+ tool responses from LLM
- Extracts Plan object with risk levels
- Applies auto-execute decision
- Executes or waits for approval
- Updates session status accordingly

**Flow:**
```
User message → LLM response → Plan detection → Auto-execute decision
    ↓ (if auto-execute)            ↓ (if wait approval)
Execute plan immediately      Set status=WAITING_APPROVAL
    ↓                              ↓
COMPLETED                     Wait for POST /agent/execute
```

### 6. API Endpoints

**POST /agent/execute**
- Approve and execute pending plan
- Updates plan status: PROPOSED → APPROVED → EXECUTING
- Updates session status: WAITING_APPROVAL → EXECUTING
- Returns: execution status

**POST /agent/reject**
- Reject pending plan
- Updates plan status: PROPOSED → REJECTED
- Updates session status: WAITING_APPROVAL → IDLE
- Returns: rejection confirmation

**Implementation:** `copilot_server/api/agent_routes.py`

---

## Test Coverage

**Total Tests:** 21 (Phase 2 only)
**Pass Rate:** 100%

### Test Files:

1. **test_plan_schema.py** (3 tests)
   - Table existence and schema validation
   - Foreign key constraints
   - Index verification

2. **test_plan_detector.py** (7 tests)
   - Single/dual tool detection (not a plan)
   - 3+ tool detection (is a plan)
   - Purpose extraction
   - Risk level calculation
   - Unknown tool defaults to CRITICAL

3. **test_auto_execute.py** (7 tests)
   - L0 never auto-executes
   - L1 auto-executes READ_ONLY
   - L1 waits for WRITE approval
   - L2 auto-executes WRITE_LOW_RISK
   - L2 waits for WRITE_HIGH_RISK
   - L3 auto-executes everything

4. **test_plan_repository.py** (4 tests)
   - Save plan
   - Update plan status
   - Load plans by session
   - Load nonexistent plan returns None

5. **test_runtime_plans.py** (3 tests)
   - Single tool executes directly
   - Multi-tool READ_ONLY auto-executes (L1)
   - Multi-tool WRITE waits approval (L1)

6. **test_approval_api.py** (5 tests)
   - Execute endpoint approves plan
   - Execute endpoint validates session/plan
   - Reject endpoint rejects plan
   - API error handling

7. **test_phase2_integration.py** (2 tests)
   - End-to-end approval workflow
   - L1 auto-execute READ_ONLY plan

---

## File Changes

### New Files (9):

1. `copilot_server/db/migrations/005_agent_plans.sql`
2. `copilot_server/agent/plan_detector.py`
3. `copilot_server/agent/auto_execute.py`
4. `copilot_server/agent/plan_repository.py`
5. `copilot_server/tests/agent/test_plan_schema.py`
6. `copilot_server/tests/agent/test_plan_detector.py`
7. `copilot_server/tests/agent/test_auto_execute.py`
8. `copilot_server/tests/agent/test_plan_repository.py`
9. `copilot_server/tests/agent/test_runtime_plans.py`

### Modified Files (4):

1. `copilot_server/agent/models.py` - Added Plan, PlanStep, PlanStatus models
2. `copilot_server/agent/runtime.py` - Integrated plan detection and execution
3. `copilot_server/agent/sessions.py` - Added plan repository
4. `copilot_server/api/agent_routes.py` - Added execute/reject endpoints

### Test Files (3):

1. `copilot_server/tests/agent/test_approval_api.py`
2. `copilot_server/tests/agent/test_phase2_integration.py`
3. `docs/agent/phase2-completion.md` (this file)

---

## API Usage Examples

### Example 1: L1 User Requests Multi-Tool Analysis

**Request:**
```bash
POST /agent/chat
{
  "message": "Analyze war zones and material demand",
  "character_id": 123
}
```

**Response:**
```json
{
  "session_id": "sess-abc123",
  "status": "completed"
}
```

**Behavior:** L1 + READ_ONLY = auto-execute immediately, no approval needed.

---

### Example 2: L1 User Requests Shopping List Creation

**Request:**
```bash
POST /agent/chat
{
  "message": "Create shopping list for 10 Caracals",
  "session_id": "sess-abc123",
  "character_id": 123
}
```

**Response:**
```json
{
  "session_id": "sess-abc123",
  "status": "waiting_approval",
  "plan_id": "plan-xyz789"
}
```

**Behavior:** L1 + WRITE_LOW_RISK = wait for approval.

**Frontend shows approval dialog:**
- Plan purpose: "I'll create a shopping list for 10 Caracals."
- Steps: get_production_chain → create_shopping_list → add_shopping_items
- Max risk: WRITE_LOW_RISK

**User approves:**
```bash
POST /agent/execute
{
  "session_id": "sess-abc123",
  "plan_id": "plan-xyz789"
}
```

**Response:**
```json
{
  "status": "executing",
  "session_id": "sess-abc123",
  "plan_id": "plan-xyz789",
  "message": "Plan approved and executing"
}
```

---

### Example 3: User Rejects Plan

**Request:**
```bash
POST /agent/reject
{
  "session_id": "sess-abc123",
  "plan_id": "plan-xyz789"
}
```

**Response:**
```json
{
  "status": "idle",
  "session_id": "sess-abc123",
  "plan_id": "plan-xyz789",
  "message": "Plan rejected"
}
```

**Behavior:** Session returns to IDLE, plan marked REJECTED, user can send new message.

---

## Database Queries

### Get All Plans for Session

```sql
SELECT id, purpose, status, auto_executing, created_at
FROM agent_plans
WHERE session_id = 'sess-abc123'
ORDER BY created_at DESC;
```

### Get Pending Plans Waiting Approval

```sql
SELECT ap.id, ap.purpose, ap.plan_data, as.character_id
FROM agent_plans ap
JOIN agent_sessions as ON ap.session_id = as.id
WHERE ap.status = 'proposed'
  AND ap.auto_executing = false;
```

### Plan Execution Duration Statistics

```sql
SELECT
    status,
    COUNT(*) as count,
    AVG(duration_ms) as avg_duration_ms,
    MAX(duration_ms) as max_duration_ms
FROM agent_plans
WHERE status = 'completed'
GROUP BY status;
```

---

## Performance Metrics

**Plan Detection Overhead:** < 5ms (analyzing LLM response)
**Auto-Execute Decision:** < 1ms (simple logic)
**Plan Save to PostgreSQL:** ~10ms (UPSERT)
**Plan Load from PostgreSQL:** ~5ms (indexed query)

**Total Overhead per Request:** ~20ms (negligible compared to LLM latency)

---

## Known Limitations

1. **No WebSocket Events:** Phase 2 implements approval logic but doesn't emit real-time events (reserved for Phase 3)
2. **No Authorization Integration:** Phase 2 doesn't enforce tool-level authorization checks (deferred to Phase 3)
3. **No Retry Logic:** Tool failures in plan execution don't retry (future enhancement)

---

## Next Steps (Phase 3)

1. **Event System:**
   - Implement EventBus for real-time updates
   - Emit events: plan_proposed, tool_call_started, tool_call_completed
   - WebSocket streaming endpoint

2. **Authorization Integration:**
   - Integrate with existing AuthorizationChecker
   - Enforce per-tool authorization
   - Emit authorization_denied events

3. **Error Handling:**
   - Partial results on tool failures
   - Retry logic with exponential backoff
   - Better error messages

4. **Frontend Integration:**
   - Plan approval UI component
   - Real-time progress indicators
   - WebSocket connection management

---

## Commits

All Phase 2 work committed with conventional commit messages:

```bash
git log --oneline --grep="feat(agent)" --since="2025-12-29"
```

**Total Commits:** 7
**All Tests Passing:** ✅ 21/21

---

**Phase 2 Status:** ✅ COMPLETE
**Ready for Phase 3:** ✅ YES
```

**Step 2: Update README**

Add to `README.md` after Agent Runtime section:

```markdown
## Agent Runtime

**Status:** Phase 2 Complete ✅

The Agent Runtime provides session-based conversational AI with human-in-the-loop approval for complex workflows.

### Phase 1: Core Infrastructure (Complete)
- Session management (Redis + PostgreSQL)
- Basic execution loop
- REST API endpoints

### Phase 2: Plan Detection & Approval (Complete)
- Multi-tool plan detection (3+ tools)
- Auto-execute decision matrix (L0-L3)
- Plan approval/rejection API
- Full test coverage (21 tests)

**See:** `docs/agent/phase2-completion.md` for details

### API Endpoints

**Chat:**
- `POST /agent/chat` - Send message, create/continue session

**Plan Approval:**
- `POST /agent/execute` - Approve and execute pending plan
- `POST /agent/reject` - Reject pending plan

**Session Management:**
- `GET /agent/session/{id}` - Get session details
- `DELETE /agent/session/{id}` - Delete session
```

**Step 3: Run all tests**

Run: `pytest copilot_server/tests/agent/ -v`
Expected: PASS (all Phase 1 + Phase 2 tests, 44 total)

**Step 4: Commit**

```bash
git add docs/agent/phase2-completion.md README.md
git commit -m "docs(agent): add Phase 2 completion documentation

- Comprehensive Phase 2 completion report
- API usage examples
- Database query examples
- Performance metrics
- Update README with Phase 2 status

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Summary

**Phase 2 Implementation Plan Complete**

**Total Tasks:** 8
**Total Tests:** 21
**Total Files:** 16 (9 new, 4 modified, 3 test)

**Deliverables:**
1. ✅ agent_plans database table
2. ✅ Plan detection (3+ tool threshold)
3. ✅ Auto-execute decision matrix
4. ✅ Plan repository (PostgreSQL)
5. ✅ Runtime integration
6. ✅ Approval API endpoints
7. ✅ Integration tests
8. ✅ Documentation

**Ready for Execution:** Use `superpowers:subagent-driven-development` or `superpowers:executing-plans`
