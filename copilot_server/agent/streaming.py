"""
SSE Streaming Infrastructure
Handles Server-Sent Events formatting for streaming responses.
"""

import json
from typing import Dict, Any, AsyncIterator
import logging

logger = logging.getLogger(__name__)


class SSEFormatter:
    """Formats streaming events for SSE protocol."""

    def format(self, data: Dict[str, Any]) -> str:
        """
        Format data as SSE event.

        Args:
            data: Event data to format

        Returns:
            SSE-formatted string
        """
        # Handle content_block_delta chunks
        if data.get("type") == "content_block_delta":
            delta = data.get("delta", {})
            if delta.get("type") == "text_delta":
                simplified_data = {
                    "type": "text",
                    "text": delta.get("text", "")
                }
                json_data = json.dumps(simplified_data, separators=(',', ':'))
                return f"data: {json_data}\n\n"

        # For other types (error, etc.), format as-is
        json_data = json.dumps(data, separators=(',', ':'))
        return f"data: {json_data}\n\n"

    def format_text_chunk(self, text: str) -> str:
        """Format text chunk for streaming."""
        return self.format({
            "type": "text",
            "text": text
        })

    def format_error(self, error: str) -> str:
        """Format error message."""
        return self.format({
            "type": "error",
            "error": error
        })

    def format_done(self, message_id: str) -> str:
        """Format completion event."""
        return self.format({
            "type": "done",
            "message_id": message_id
        })


async def stream_llm_response(
    llm_client,
    messages: list,
    tools: list = None,
    system: str = None
) -> AsyncIterator[Dict[str, Any]]:
    """
    Stream LLM response chunks.

    Args:
        llm_client: AnthropicClient instance
        messages: Conversation messages
        tools: Available tools
        system: System prompt

    Yields:
        Response chunks
    """
    try:
        # Call LLM with streaming enabled
        async for chunk in llm_client._stream_response({
            "model": llm_client.model,
            "messages": messages,
            "system": system or "",
            "max_tokens": 4096,
            "tools": tools or [],
            "stream": True
        }):
            # Extract text from chunk
            if chunk.get("type") == "content_block_delta":
                delta = chunk.get("delta", {})
                if delta.get("type") == "text_delta":
                    yield {
                        "type": "text",
                        "text": delta.get("text", "")
                    }
            elif chunk.get("type") == "message_stop":
                yield {"type": "done"}

    except Exception as e:
        logger.error(f"Streaming error: {e}")
        yield {
            "type": "error",
            "error": str(e)
        }
