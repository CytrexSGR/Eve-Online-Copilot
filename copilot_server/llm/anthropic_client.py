"""
Anthropic Claude API Client
Handles LLM interactions with Claude API.
"""

import anthropic
from typing import List, Dict, Any, Optional, AsyncIterator
import logging
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

from ..config import (
    ANTHROPIC_API_KEY,
    ANTHROPIC_MODEL,
    ANTHROPIC_MAX_TOKENS,
    SYSTEM_PROMPT
)

logger = logging.getLogger(__name__)


class AnthropicClient:
    """Client for Anthropic Claude API with MCP tool support."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize Anthropic client.

        Args:
            api_key: Anthropic API key (defaults to config)
            model: Model to use (defaults to config)
        """
        self.api_key = api_key or ANTHROPIC_API_KEY
        self.model = model or ANTHROPIC_MODEL
        self.client = anthropic.Anthropic(api_key=self.api_key)

        if not self.api_key:
            logger.warning("No Anthropic API key provided - client will not work")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((
            anthropic.APIError,
            anthropic.RateLimitError,
            anthropic.APIConnectionError,
            anthropic.APITimeoutError
        )),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )
    async def _chat_with_retry(
        self,
        params: Dict[str, Any]
    ) -> anthropic.types.Message:
        """
        Internal method to make API call with retry logic.

        Args:
            params: Request parameters

        Returns:
            Raw API response

        Raises:
            APIError: If API request fails after retries
            RateLimitError: If rate limited after retries
        """
        return self.client.messages.create(**params)

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        system: Optional[str] = None,
        max_tokens: int = ANTHROPIC_MAX_TOKENS,
        temperature: float = 1.0,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Send chat completion request to Claude.

        Args:
            messages: Conversation messages
            tools: Available MCP tools
            system: System prompt (defaults to config)
            max_tokens: Max tokens in response
            temperature: Sampling temperature
            stream: Enable streaming

        Returns:
            Response from Claude API
        """
        try:
            system_prompt = system or SYSTEM_PROMPT

            # Build request parameters
            params = {
                "model": self.model,
                "messages": messages,
                "system": system_prompt,
                "max_tokens": max_tokens,
                "temperature": temperature
            }

            # Add tools if provided
            if tools:
                params["tools"] = tools

            # Make API call
            if stream:
                return self._stream_response(params)
            else:
                response = await self._chat_with_retry(params)
                return self._parse_response(response)

        except anthropic.RateLimitError as e:
            logger.error(f"Anthropic rate limit error after retries: {e}")
            return {
                "error": f"Rate Limit Error: {str(e)}",
                "type": "rate_limit_error"
            }
        except anthropic.APIConnectionError as e:
            logger.error(f"Anthropic API connection error after retries: {e}")
            return {
                "error": f"API Connection Error: {str(e)}",
                "type": "connection_error"
            }
        except anthropic.APITimeoutError as e:
            logger.error(f"Anthropic API timeout error after retries: {e}")
            return {
                "error": f"API Timeout Error: {str(e)}",
                "type": "timeout_error"
            }
        except anthropic.APIError as e:
            logger.error(f"Anthropic API error after retries: {e}")
            return {
                "error": f"API Error: {str(e)}",
                "type": "api_error"
            }
        except Exception as e:
            logger.error(f"Unexpected error in chat: {e}")
            return {
                "error": f"Unexpected error: {str(e)}",
                "type": "error"
            }

    def _parse_response(self, response: anthropic.types.Message) -> Dict[str, Any]:
        """
        Parse Claude API response.

        Args:
            response: Raw API response

        Returns:
            Parsed response dictionary
        """
        result = {
            "id": response.id,
            "model": response.model,
            "role": response.role,
            "content": [],
            "stop_reason": response.stop_reason,
            "usage": {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens
            }
        }

        # Parse content blocks
        for block in response.content:
            if block.type == "text":
                result["content"].append({
                    "type": "text",
                    "text": block.text
                })
            elif block.type == "tool_use":
                result["content"].append({
                    "type": "tool_use",
                    "id": block.id,
                    "name": block.name,
                    "input": block.input
                })

        return result

    async def _stream_response(self, params: Dict[str, Any]) -> AsyncIterator[Dict[str, Any]]:
        """
        Stream response from Claude API.

        Args:
            params: Request parameters

        Yields:
            Response chunks in format: {"type": "content_block_delta", "delta": {...}}
        """
        try:
            with self.client.messages.stream(**params) as stream:
                for event in stream:
                    if hasattr(event, 'type'):
                        # Extract delta data for content_block_delta events
                        if event.type == 'content_block_delta' and hasattr(event, 'delta'):
                            yield {
                                "type": "content_block_delta",
                                "delta": {
                                    "type": event.delta.type,
                                    "text": getattr(event.delta, 'text', '')
                                }
                            }
                        # Pass through other event types
                        elif event.type == 'message_stop':
                            yield {"type": "message_stop"}
                        # Handle other streaming events if needed
                        elif event.type in ['message_start', 'content_block_start', 'content_block_stop']:
                            # These events are informational, can be yielded if needed
                            pass
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield {
                "type": "error",
                "error": str(e)
            }

    def count_tokens(self, text: str) -> int:
        """
        Estimate token count for text.

        Args:
            text: Text to count tokens for

        Returns:
            Estimated token count
        """
        # Rough estimation: 1 token ≈ 4 characters
        # For more accurate counting, use Anthropic's tokenizer
        return len(text) // 4

    def format_tool_result(self, tool_use_id: str, result: Any) -> Dict[str, Any]:
        """
        Format tool execution result for Claude.

        Args:
            tool_use_id: ID of the tool use block
            result: Tool execution result

        Returns:
            Formatted tool result
        """
        return {
            "type": "tool_result",
            "tool_use_id": tool_use_id,
            "content": str(result) if not isinstance(result, str) else result
        }

    def build_tool_schema(self, mcp_tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Convert MCP tool definitions to Claude tool schema.

        Args:
            mcp_tools: MCP tool definitions

        Returns:
            Claude-compatible tool schemas
        """
        claude_tools = []

        for tool in mcp_tools:
            # Build input schema
            properties = {}
            required = []

            for param in tool.get("parameters", []):
                param_name = param["name"]
                param_type = param["type"]

                # Map types
                type_mapping = {
                    "integer": "number",
                    "string": "string",
                    "boolean": "boolean",
                    "number": "number"
                }

                properties[param_name] = {
                    "type": type_mapping.get(param_type, "string"),
                    "description": param.get("description", "")
                }

                # Add enum if present
                if "enum" in param:
                    properties[param_name]["enum"] = param["enum"]

                # Track required parameters
                if param.get("required", False):
                    required.append(param_name)

            # Build Claude tool schema
            claude_tool = {
                "name": tool["name"],
                "description": tool["description"],
                "input_schema": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }

            claude_tools.append(claude_tool)

        return claude_tools
