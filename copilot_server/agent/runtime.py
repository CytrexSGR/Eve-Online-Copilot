"""
Agent Runtime
Executes agent workflows with LLM and tool orchestration.
"""

import asyncio
import logging
import time
from typing import List, Dict, Any
from datetime import datetime

from .models import AgentSession, SessionStatus, Plan, PlanStatus
from .sessions import AgentSessionManager
from .plan_detector import PlanDetector
from .auto_execute import should_auto_execute
from ..llm.anthropic_client import AnthropicClient
from ..mcp.orchestrator import ToolOrchestrator

logger = logging.getLogger(__name__)


class AgentRuntime:
    """
    Agent execution runtime.

    Phase 2: Multi-tool plan detection with approval workflow.
    """

    def __init__(
        self,
        session_manager: AgentSessionManager,
        llm_client: AnthropicClient,
        orchestrator: ToolOrchestrator
    ):
        """
        Initialize runtime.

        Args:
            session_manager: Session manager
            llm_client: LLM client
            orchestrator: Tool orchestrator
        """
        self.session_manager = session_manager
        self.llm_client = llm_client
        self.orchestrator = orchestrator
        self.plan_detector = PlanDetector(orchestrator.mcp)

    async def execute(self, session: AgentSession, max_iterations: int = 5) -> None:
        """
        Execute agent workflow with plan detection.

        Phase 2: Detects multi-tool plans and applies auto-execute decision.

        Args:
            session: AgentSession to execute
            max_iterations: Maximum tool iterations
        """
        session.status = SessionStatus.PLANNING
        await self.session_manager.save_session(session)

        iteration = 0

        while iteration < max_iterations:
            iteration += 1
            logger.info(f"Runtime iteration {iteration}/{max_iterations} for session {session.id}")

            # Build messages for LLM
            messages = self._build_messages(session)

            # Get available tools
            tools = self.orchestrator.mcp.get_tools()
            claude_tools = self.llm_client.build_tool_schema(tools)

            # Call LLM
            response = await self.llm_client.chat(
                messages=messages,
                tools=claude_tools
            )

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

                # Execute tools and get results
                tool_results = await self._execute_tools(response, session)

                # Tool results are added to messages automatically
                # This will trigger another LLM call in next iteration
                continue
            else:
                # Final answer, no tools
                answer = self._extract_text(response)
                session.add_message("assistant", answer)
                session.status = SessionStatus.COMPLETED
                await self.session_manager.save_session(session)

                logger.info(f"Session {session.id} completed")
                return

        # Max iterations reached
        session.status = SessionStatus.ERROR
        session.add_message("assistant", "Maximum iterations reached. Please try again.")
        await self.session_manager.save_session(session)
        logger.warning(f"Session {session.id} reached max iterations")

    def _build_messages(self, session: AgentSession) -> List[Dict[str, Any]]:
        """Build messages array for LLM."""
        messages = []

        for msg in session.messages:
            messages.append({
                "role": msg.role,
                "content": msg.content
            })

        return messages

    def _has_tool_calls(self, response: Dict[str, Any]) -> bool:
        """Check if LLM response contains tool calls."""
        content = response.get("content", [])

        for block in content:
            if block.get("type") == "tool_use":
                return True

        return False

    def _extract_text(self, response: Dict[str, Any]) -> str:
        """Extract text from LLM response."""
        content = response.get("content", [])

        texts = []
        for block in content:
            if block.get("type") == "text":
                texts.append(block.get("text", ""))

        return "\n".join(texts)

    async def _execute_tools(
        self,
        response: Dict[str, Any],
        session: AgentSession
    ) -> List[Dict[str, Any]]:
        """
        Execute tools from LLM response.

        Phase 1: Execute all tools directly (no plan detection).

        Args:
            response: LLM response with tool calls
            session: Current session

        Returns:
            Tool results
        """
        content = response.get("content", [])
        results = []

        for block in content:
            if block.get("type") == "tool_use":
                tool_name = block.get("name")
                tool_input = block.get("input", {})
                tool_id = block.get("id")

                logger.info(f"Executing tool: {tool_name}")

                try:
                    # Execute via orchestrator (async-safe call)
                    result = await asyncio.to_thread(
                        self.orchestrator.mcp.call_tool,
                        tool_name,
                        tool_input
                    )

                    results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": str(result)
                    })

                except Exception as e:
                    logger.error(f"Tool execution failed: {e}")
                    results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": f"Error: {str(e)}",
                        "is_error": True
                    })

        # Add tool results to session messages
        # Phase 1: Use simplified approach for message format
        if results:
            tool_summary = f"Executed {len(results)} tools"
            session.add_message("assistant", tool_summary)

        return results

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
