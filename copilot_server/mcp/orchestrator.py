"""
Tool Orchestrator
Handles multi-tool workflows and intelligent tool selection.
"""

from typing import List, Dict, Any, Optional
import logging

from .client import MCPClient
from ..llm.anthropic_client import AnthropicClient

logger = logging.getLogger(__name__)


class ToolOrchestrator:
    """Orchestrates complex multi-tool workflows."""

    def __init__(self, mcp_client: MCPClient, llm_client: AnthropicClient):
        """
        Initialize orchestrator.

        Args:
            mcp_client: MCP client for tool calls
            llm_client: LLM client for reasoning
        """
        self.mcp = mcp_client
        self.llm = llm_client

    async def execute_workflow(
        self,
        messages: List[Dict[str, Any]],
        max_iterations: int = 5
    ) -> Dict[str, Any]:
        """
        Execute agentic workflow with tool calls.

        Args:
            messages: Conversation messages
            max_iterations: Maximum tool call iterations

        Returns:
            Final response with tool results
        """
        # Get available tools
        tools = self.mcp.get_tools()
        claude_tools = self.llm.build_tool_schema(tools)

        iteration = 0
        current_messages = messages.copy()
        tool_results = []

        while iteration < max_iterations:
            iteration += 1
            logger.info(f"Workflow iteration {iteration}/{max_iterations}")

            # Call Claude with tools
            response = await self.llm.chat(
                messages=current_messages,
                tools=claude_tools
            )

            if "error" in response:
                return response

            # Check if Claude wants to use tools
            has_tool_use = any(
                block.get("type") == "tool_use"
                for block in response.get("content", [])
            )

            if not has_tool_use:
                # No more tool calls - return final response
                return {
                    "response": response,
                    "tool_results": tool_results,
                    "iterations": iteration
                }

            # Execute tool calls
            tool_use_blocks = [
                block for block in response["content"]
                if block["type"] == "tool_use"
            ]

            # Add assistant message to conversation
            current_messages.append({
                "role": "assistant",
                "content": response["content"]
            })

            # Execute each tool call
            tool_result_blocks = []
            for tool_use in tool_use_blocks:
                tool_name = tool_use["name"]
                tool_input = tool_use["input"]
                tool_id = tool_use["id"]

                logger.info(f"Executing tool: {tool_name}")

                # Call tool via MCP
                result = self.mcp.call_tool(tool_name, tool_input)

                # Store result
                tool_results.append({
                    "tool": tool_name,
                    "input": tool_input,
                    "result": result,
                    "iteration": iteration
                })

                # Format for Claude
                tool_result_blocks.append({
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "content": self._format_tool_result(result)
                })

            # Add tool results to conversation
            current_messages.append({
                "role": "user",
                "content": tool_result_blocks
            })

        # Max iterations reached
        logger.warning(f"Max iterations ({max_iterations}) reached")
        return {
            "error": "Maximum tool call iterations reached",
            "tool_results": tool_results,
            "iterations": iteration
        }

    def _format_tool_result(self, result: Dict[str, Any]) -> str:
        """
        Format tool result for Claude.

        Args:
            result: Raw tool result

        Returns:
            Formatted string
        """
        if "error" in result:
            return f"Error: {result['error']}"

        if "content" in result:
            # Extract text from content blocks
            content = result["content"]
            if isinstance(content, list) and content:
                first_block = content[0]
                if isinstance(first_block, dict) and "text" in first_block:
                    return first_block["text"]

        return str(result)

    def suggest_tools(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Suggest relevant tools for a query.

        Args:
            query: User query
            top_k: Number of suggestions

        Returns:
            Suggested tools
        """
        # Simple keyword matching for now
        # TODO: Use embeddings for better matching
        matches = self.mcp.search_tools(query)
        return matches[:top_k]
