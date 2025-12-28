"""
PostgreSQL repository for agent plans.
"""

import asyncpg
import json
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
                VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7, $8, $9, $10, $11)
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
                json.dumps(plan_dict["plan_data"]),
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

        # Parse JSON if it's a string
        if isinstance(plan_data, str):
            plan_data = json.loads(plan_data)

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
