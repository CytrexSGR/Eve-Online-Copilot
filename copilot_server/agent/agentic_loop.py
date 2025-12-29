"""
Agentic Streaming Loop
Executes multi-turn tool-calling workflow with streaming.
"""

import logging
import json
from typing import List, Dict, Any, AsyncIterator, Optional
from ..llm.anthropic_client import AnthropicClient
from ..mcp.client import MCPClient
from ..models.user_settings import UserSettings
from ..governance.authorization import AuthorizationChecker
from .tool_extractor import ToolCallExtractor

logger = logging.getLogger(__name__)


class AgenticStreamingLoop:
    """
    Executes agentic loop with streaming and tool execution.

    Flow:
    1. Stream LLM response
    2. Extract tool calls from stream
    3. Execute tools (with authorization)
    4. Feed results back to LLM
    5. Repeat until final answer
    6. Stream events to client
    """

    def __init__(
        self,
        llm_client: AnthropicClient,
        mcp_client: MCPClient,
        user_settings: UserSettings,
        max_iterations: int = 5
    ):
        self.llm = llm_client
        self.mcp = mcp_client
        self.settings = user_settings
        self.max_iterations = max_iterations
        self.auth_checker = AuthorizationChecker(user_settings)

    async def execute(
        self,
        messages: List[Dict[str, Any]],
        system: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Execute agentic loop with streaming.

        Args:
            messages: Conversation history
            system: System prompt
            session_id: Session ID for events

        Yields:
            Stream events: text chunks, tool calls, results, errors
        """
        iteration = 0
        current_messages = messages.copy()
        tools = self.mcp.get_tools()
        claude_tools = self.llm.build_tool_schema(tools) if tools else []

        # Detect LLM provider
        provider = "anthropic"
        if hasattr(self.llm, "client") and "openai" in str(type(self.llm.client)).lower():
            provider = "openai"
        logger.info(f"Detected LLM provider: {provider}")

        while iteration < self.max_iterations:
            iteration += 1
            logger.info(f"Agentic loop iteration {iteration}/{self.max_iterations}")

            # Yield thinking event
            yield {
                "type": "thinking",
                "iteration": iteration
            }

            # Stream LLM response
            extractor = ToolCallExtractor()
            assistant_content_blocks = []

            async for chunk in self.llm._stream_response({
                "model": self.llm.model,
                "messages": current_messages,
                "system": system or "",
                "max_tokens": 4096,
                "tools": claude_tools,
                "stream": True
            }):
                # Process chunk for tool extraction with provider info
                extractor.process_chunk(chunk, provider=provider)

                # Yield text chunks to client
                if chunk.get("type") == "content_block_delta":
                    delta = chunk.get("delta", {})
                    if delta.get("type") == "text_delta":
                        text = delta.get("text", "")
                        yield {
                            "type": "text",
                            "text": text
                        }

                # Build assistant content blocks for next turn
                if chunk.get("type") == "content_block_start":
                    content_block = chunk.get("content_block", {})
                    assistant_content_blocks.append({
                        "type": content_block.get("type"),
                        "id": content_block.get("id"),
                        "name": content_block.get("name"),
                        "partial_text": "",
                        "partial_json": ""
                    })
                elif chunk.get("type") == "content_block_delta":
                    index = chunk.get("index", 0)
                    if index < len(assistant_content_blocks):
                        delta = chunk.get("delta", {})
                        if delta.get("type") == "text_delta":
                            assistant_content_blocks[index]["partial_text"] += delta.get("text", "")
                        elif delta.get("type") == "input_json_delta":
                            assistant_content_blocks[index]["partial_json"] += delta.get("partial_json", "")

            # Check if tools were called
            tool_calls = extractor.get_tool_calls()

            if not tool_calls:
                # No tool calls - final answer reached
                logger.info("No tool calls detected - final answer reached")
                yield {"type": "done"}
                return

            # Execute tool calls
            logger.info(f"Executing {len(tool_calls)} tool calls")

            # Build assistant message for conversation
            assistant_message_content = self._build_assistant_content(assistant_content_blocks)
            current_messages.append({
                "role": "assistant",
                "content": assistant_message_content
            })

            # Execute tools and build tool results
            tool_results = []

            for tool_call in tool_calls:
                tool_name = tool_call["name"]
                tool_input = tool_call["input"]
                tool_id = tool_call["id"]

                # Yield tool_call_started event
                yield {
                    "type": "tool_call_started",
                    "tool": tool_name,
                    "arguments": tool_input
                }

                # Check authorization
                allowed, denial_reason = self.auth_checker.check_authorization(
                    tool_name,
                    tool_input
                )

                if not allowed:
                    logger.warning(f"Tool '{tool_name}' blocked: {denial_reason}")

                    # Yield authorization denied event
                    yield {
                        "type": "authorization_denied",
                        "tool": tool_name,
                        "reason": denial_reason
                    }

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": f"Authorization Error: {denial_reason}",
                        "is_error": True
                    })
                    continue

                # Execute tool
                logger.info(f"Executing tool: {tool_name}")
                result = self.mcp.call_tool(tool_name, tool_input)

                # Yield tool_call_completed event
                yield {
                    "type": "tool_call_completed",
                    "tool": tool_name,
                    "result": result
                }

                # Format for LLM
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "content": self._format_tool_result(result)
                })

            # Add tool results to conversation
            current_messages.append({
                "role": "user",
                "content": tool_results
            })

        # Max iterations reached
        logger.warning(f"Max iterations ({self.max_iterations}) reached")
        yield {
            "type": "error",
            "error": "Maximum iterations reached without final answer"
        }

    def _build_assistant_content(self, content_blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Build assistant content blocks for conversation."""
        result = []

        for block in content_blocks:
            if block["type"] == "text":
                result.append({
                    "type": "text",
                    "text": block["partial_text"]
                })
            elif block["type"] == "tool_use":
                result.append({
                    "type": "tool_use",
                    "id": block["id"],
                    "name": block["name"],
                    "input": json.loads(block["partial_json"])
                })

        return result

    def _format_tool_result(self, result: Dict[str, Any]) -> str:
        """Format tool result for LLM."""
        if "error" in result:
            return f"Error: {result['error']}"

        if "content" in result:
            # Extract text from content blocks
            texts = []
            for block in result["content"]:
                if block.get("type") == "text":
                    texts.append(block.get("text", ""))
            return "\n".join(texts) if texts else str(result)

        return str(result)
