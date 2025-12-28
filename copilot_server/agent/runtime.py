"""
Agent Runtime
Executes agent workflows with LLM and tool orchestration.
"""

import logging
from typing import List, Dict, Any

from .models import AgentSession, SessionStatus
from .sessions import AgentSessionManager
from ..llm.anthropic_client import AnthropicClient
from ..mcp.orchestrator import ToolOrchestrator

logger = logging.getLogger(__name__)


class AgentRuntime:
    """
    Agent execution runtime.

    Phase 1: Basic execution loop with single-tool support.
    No multi-tool plan detection yet.
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

    async def execute(self, session: AgentSession, max_iterations: int = 5) -> None:
        """
        Execute agent workflow.

        Phase 1: Simple execution loop without plan detection.

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

            # Check if LLM wants to use tools
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
                    # Execute via orchestrator (synchronous call)
                    result = self.orchestrator.call_tool(tool_name, tool_input)

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
        # Format results as a tool result message
        if results:
            # Build content for assistant message (tool use blocks)
            assistant_content = [block for block in content if block.get("type") == "tool_use"]

            # Add assistant message with tool use
            if assistant_content:
                session.add_message("assistant", str(assistant_content))

            # Add user message with tool results
            session.add_message("user", str(results))

        return results
