#!/usr/bin/env python3
"""
Simple streaming test without tools to verify OpenAI client works.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from copilot_server.llm.openai_client import OpenAIClient
from copilot_server.config import OPENAI_API_KEY, OPENAI_MODEL


async def test_simple_stream():
    """Test basic streaming without tools."""
    print(f"\nTesting OpenAI client: {OPENAI_MODEL}")
    print(f"API Key present: {bool(OPENAI_API_KEY)}\n")

    client = OpenAIClient(api_key=OPENAI_API_KEY, model=OPENAI_MODEL)

    messages = [
        {"role": "user", "content": "Say hello in one sentence."}
    ]

    print("Streaming response:")
    try:
        async for chunk in client._stream_response(
            {
                "model": client.model,
                "messages": messages,
                "max_tokens": 100
            },
            convert_format=False
        ):
            print(f"Chunk: {chunk}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_simple_stream())
