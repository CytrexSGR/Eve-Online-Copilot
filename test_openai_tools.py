#!/usr/bin/env python3
"""
Test OpenAI streaming with tools to verify function calling works.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from copilot_server.llm.openai_client import OpenAIClient
from copilot_server.config import OPENAI_API_KEY, OPENAI_MODEL


async def test_with_tools():
    """Test streaming with tools."""
    print(f"\nTesting OpenAI client with tools: {OPENAI_MODEL}\n")

    client = OpenAIClient(api_key=OPENAI_API_KEY, model=OPENAI_MODEL)

    # Simple tool
    tools = [{
        "name": "get_price",
        "description": "Get the price of an item",
        "input_schema": {
            "type": "object",
            "properties": {
                "item": {"type": "string", "description": "Item name"}
            },
            "required": ["item"]
        }
    }]

    # Convert to OpenAI format
    openai_tools = client.build_tool_schema(tools)
    print(f"Tools: {openai_tools}\n")

    messages = [
        {"role": "user", "content": "What is the price of Tritanium? Use the get_price tool."}
    ]

    print("Streaming response:")
    try:
        async for chunk in client._stream_response(
            {
                "model": client.model,
                "messages": messages,
                "max_tokens": 100,
                "tools": openai_tools
            },
            convert_format=False
        ):
            print(f"Chunk: {chunk}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_with_tools())
