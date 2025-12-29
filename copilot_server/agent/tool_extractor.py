"""
Tool Call Extraction from LLM Streams
Handles Anthropic and OpenAI streaming formats.
"""

import json
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class ToolCallExtractor:
    """Extracts tool calls from streaming LLM responses (Anthropic & OpenAI)."""

    def __init__(self):
        self.current_blocks: Dict[int, Dict[str, Any]] = {}
        self.completed_tool_calls: List[Dict[str, Any]] = []
        self.text_chunks: List[str] = []

        # OpenAI-specific state
        self.openai_function_call: Optional[Dict[str, Any]] = None

    def process_chunk(self, chunk: Dict[str, Any], provider: str = "anthropic") -> None:
        """
        Process a single streaming chunk.

        Args:
            chunk: Streaming event from LLM
            provider: "anthropic" or "openai"
        """
        if provider == "openai":
            self._process_openai_chunk(chunk)
        else:
            self._process_anthropic_chunk(chunk)

    def _process_anthropic_chunk(self, chunk: Dict[str, Any]) -> None:
        """Process Anthropic streaming chunk (existing logic)."""
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

    def _process_openai_chunk(self, chunk: Dict[str, Any]) -> None:
        """Process OpenAI streaming chunk."""
        if "choices" not in chunk or not chunk["choices"]:
            return

        choice = chunk["choices"][0]
        delta = choice.get("delta", {})

        # Handle text content
        if "content" in delta and delta["content"]:
            self.text_chunks.append(delta["content"])

        # Handle function call
        if "function_call" in delta:
            func_call = delta["function_call"]

            # Skip if function_call is None or empty
            if not func_call:
                return

            # Initialize function call on first chunk
            if self.openai_function_call is None:
                self.openai_function_call = {
                    "name": func_call.get("name", ""),
                    "arguments": ""
                }

            # Accumulate name
            if "name" in func_call:
                self.openai_function_call["name"] = func_call["name"]

            # Accumulate arguments
            if "arguments" in func_call:
                self.openai_function_call["arguments"] += func_call["arguments"]

        # Finish reason indicates completion
        if choice.get("finish_reason") == "function_call":
            if self.openai_function_call:
                try:
                    args = json.loads(self.openai_function_call["arguments"])

                    self.completed_tool_calls.append({
                        "id": f"call_{len(self.completed_tool_calls)}",
                        "name": self.openai_function_call["name"],
                        "input": args
                    })

                    self.openai_function_call = None

                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse OpenAI function arguments: {e}")
                    logger.error(f"Arguments: {self.openai_function_call['arguments']}")

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
        self.openai_function_call = None
