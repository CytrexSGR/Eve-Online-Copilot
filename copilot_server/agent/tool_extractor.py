"""
Tool Call Extraction from LLM Streams
Handles Anthropic and OpenAI streaming formats.
"""

import json
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class ToolCallExtractor:
    """Extracts tool calls from streaming LLM responses."""

    def __init__(self):
        self.current_blocks: Dict[int, Dict[str, Any]] = {}
        self.completed_tool_calls: List[Dict[str, Any]] = []
        self.text_chunks: List[str] = []

    def process_chunk(self, chunk: Dict[str, Any]) -> None:
        """
        Process a single streaming chunk.

        Args:
            chunk: Streaming event from LLM
        """
        chunk_type = chunk.get("type")

        if chunk_type == "content_block_start":
            # New content block starting
            index = chunk.get("index", 0)
            content_block = chunk.get("content_block", {})

            self.current_blocks[index] = {
                "type": content_block.get("type"),
                "id": content_block.get("id"),
                "name": content_block.get("name"),
                "partial_json": ""
            }

        elif chunk_type == "content_block_delta":
            # Accumulate content
            index = chunk.get("index", 0)
            delta = chunk.get("delta", {})
            delta_type = delta.get("type")

            if index in self.current_blocks:
                block = self.current_blocks[index]

                if delta_type == "text_delta":
                    # Text content
                    text = delta.get("text", "")
                    self.text_chunks.append(text)

                elif delta_type == "input_json_delta":
                    # Tool input JSON (partial)
                    block["partial_json"] += delta.get("partial_json", "")

        elif chunk_type == "content_block_stop":
            # Content block complete
            index = chunk.get("index", 0)

            if index in self.current_blocks:
                block = self.current_blocks[index]

                if block["type"] == "tool_use":
                    # Parse complete JSON
                    try:
                        tool_input = json.loads(block["partial_json"])

                        self.completed_tool_calls.append({
                            "id": block["id"],
                            "name": block["name"],
                            "input": tool_input
                        })

                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse tool input JSON: {e}")
                        logger.error(f"Partial JSON: {block['partial_json']}")

                # Remove from current blocks
                del self.current_blocks[index]

    def get_tool_calls(self) -> List[Dict[str, Any]]:
        """Get all completed tool calls."""
        return self.completed_tool_calls

    def get_text_chunks(self) -> List[str]:
        """Get all text chunks."""
        return self.text_chunks

    def has_tool_calls(self) -> bool:
        """Check if any tool calls were detected."""
        return len(self.completed_tool_calls) > 0

    def reset(self) -> None:
        """Reset extractor for new response."""
        self.current_blocks.clear()
        self.completed_tool_calls.clear()
        self.text_chunks.clear()
