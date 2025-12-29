"""
OpenAI API Client
Handles LLM interactions with OpenAI API (compatible with Anthropic interface).
"""

from openai import OpenAI, AsyncOpenAI
from typing import List, Dict, Any, Optional, AsyncIterator
import logging
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

logger = logging.getLogger(__name__)


class OpenAIClient:
    """Client for OpenAI API with streaming support."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4-turbo-preview"):
        """
        Initialize OpenAI client.

        Args:
            api_key: OpenAI API key
            model: Model to use (default: gpt-4-turbo-preview)
        """
        self.api_key = api_key
        self.model = model
        self.client = AsyncOpenAI(api_key=self.api_key) if api_key else None

        if not self.api_key:
            logger.warning("No OpenAI API key provided - client will not work")

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        system: Optional[str] = None,
        max_tokens: int = 4096
    ) -> Dict[str, Any]:
        """
        Send chat request to OpenAI.

        Args:
            messages: List of message dicts with role and content
            tools: Optional list of tool definitions
            system: Optional system prompt
            max_tokens: Maximum tokens to generate

        Returns:
            Response dict with content and usage
        """
        if not self.client:
            raise ValueError("OpenAI client not initialized - missing API key")

        # Add system message if provided
        if system:
            messages = [{"role": "system", "content": system}] + messages

        params = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens
        }

        # Add tools if provided (convert from Anthropic format to OpenAI format)
        if tools:
            params["tools"] = self._convert_tools(tools)

        try:
            response = await self.client.chat.completions.create(**params)

            # Convert OpenAI response to Anthropic-compatible format
            return {
                "content": [
                    {
                        "type": "text",
                        "text": response.choices[0].message.content or ""
                    }
                ],
                "usage": {
                    "input_tokens": response.usage.prompt_tokens,
                    "output_tokens": response.usage.completion_tokens
                }
            }
        except Exception as e:
            logger.error(f"Unexpected error in chat: {e}")
            raise

    async def _stream_response(
        self,
        params: Dict[str, Any]
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Stream chat response from OpenAI.

        Args:
            params: Request parameters

        Yields:
            Event dicts compatible with Anthropic format
        """
        if not self.client:
            raise ValueError("OpenAI client not initialized - missing API key")

        try:
            # Ensure stream=True is set (don't duplicate if already in params)
            stream_params = {**params, "stream": True}

            stream = await self.client.chat.completions.create(**stream_params)

            async for chunk in stream:
                delta = chunk.choices[0].delta

                # Yield text delta events (Anthropic-compatible format)
                if delta.content:
                    yield {
                        "type": "content_block_delta",
                        "delta": {
                            "type": "text_delta",
                            "text": delta.content
                        }
                    }

                # Yield done event when finished
                if chunk.choices[0].finish_reason:
                    yield {
                        "type": "message_stop"
                    }

        except Exception as e:
            logger.error(f"Stream error: {e}")
            raise

    def _convert_tools(self, anthropic_tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Convert Anthropic tool format to OpenAI function format.

        Args:
            anthropic_tools: Tools in Anthropic format

        Returns:
            Tools in OpenAI format
        """
        openai_tools = []
        for tool in anthropic_tools:
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": tool.get("name"),
                    "description": tool.get("description"),
                    "parameters": tool.get("input_schema", {})
                }
            })
        return openai_tools
