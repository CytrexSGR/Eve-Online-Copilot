#!/usr/bin/env python3
"""
Phase 7 Integration Test
Tests complete end-to-end flow with mock tools.
"""

import asyncio
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from copilot_server.agent.sessions import AgentSessionManager
from copilot_server.agent.agentic_loop import AgenticStreamingLoop
from copilot_server.llm.openai_client import OpenAIClient
from copilot_server.models.user_settings import UserSettings, AutonomyLevel
from copilot_server.config import OPENAI_API_KEY, OPENAI_MODEL


class MockMCPClient:
    """Mock MCP Client for testing."""

    def get_tools(self):
        """Return mock tools."""
        return [
            {
                "name": "get_market_prices",
                "description": "Get market prices for an item in a region",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "type_id": {"type": "integer"},
                        "region_id": {"type": "integer"}
                    },
                    "required": ["type_id"]
                }
            }
        ]

    def call_tool(self, name: str, arguments: dict):
        """Mock tool execution."""
        print(f"\n🔧 Mock Tool Called: {name}")
        print(f"   Arguments: {arguments}")

        if name == "get_market_prices":
            # Return mock market data
            return {
                "content": [{
                    "type": "text",
                    "text": f"Tritanium price in Jita: 5.50 ISK (sell), 5.45 ISK (buy)"
                }]
            }

        return {
            "content": [{
                "type": "text",
                "text": f"Mock result from {name}"
            }]
        }


async def test_complete_flow():
    """Test complete agentic flow."""
    print("\n" + "="*60)
    print("Phase 7 Integration Test - Complete Flow")
    print("="*60)

    # Setup
    print("\n1️⃣ Setup Components...")
    user_settings = UserSettings(
        character_id=526379435,
        autonomy_level=AutonomyLevel.RECOMMENDATIONS
    )

    llm_client = OpenAIClient(api_key=OPENAI_API_KEY, model=OPENAI_MODEL)
    mcp_client = MockMCPClient()

    # Create agentic loop
    loop = AgenticStreamingLoop(
        llm_client=llm_client,
        mcp_client=mcp_client,
        user_settings=user_settings,
        max_iterations=5
    )

    print("   ✅ LLM Client: OpenAI GPT")
    print("   ✅ MCP Client: Mock (1 tool)")
    print("   ✅ Autonomy: RECOMMENDATIONS (L1)")

    # Test message
    print("\n2️⃣ User Message:")
    message = "What is the current sell price of Tritanium in Jita?"
    print(f"   💬 '{message}'")

    # Execute agentic loop
    print("\n3️⃣ Agentic Loop Execution:")

    messages = [
        {"role": "user", "content": message}
    ]

    system_prompt = """You are an EVE Online assistant. You have access to market data tools.
When asked about prices, ALWAYS use the get_market_prices tool.
Tool: get_market_prices - Get market prices (type_id: 34 for Tritanium)"""

    events_collected = []
    full_response = ""

    try:
        async for event in loop.execute(
            messages=messages,
            system=system_prompt,
            session_id="test-session"
        ):
            events_collected.append(event)
            event_type = event.get("type")

            if event_type == "thinking":
                print(f"   🤔 Iteration {event.get('iteration')}")

            elif event_type == "text":
                text = event.get("text", "")
                full_response += text
                print(f"   💭 LLM: {text[:50]}{'...' if len(text) > 50 else ''}")

            elif event_type == "tool_call_started":
                tool = event.get("tool")
                args = event.get("arguments")
                print(f"   🔧 Tool Starting: {tool}")
                print(f"      Args: {args}")

            elif event_type == "tool_call_completed":
                tool = event.get("tool")
                print(f"   ✅ Tool Completed: {tool}")

            elif event_type == "tool_call_failed":
                tool = event.get("tool")
                error = event.get("error")
                print(f"   ❌ Tool Failed: {tool}")
                print(f"      Error: {error}")

            elif event_type == "done":
                print(f"   🎯 Final Answer Ready")
                break

            elif event_type == "error":
                print(f"   ⚠️ Error: {event.get('error')}")
                break

    except Exception as e:
        print(f"\n   ❌ Exception: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Results
    print("\n4️⃣ Results:")
    print(f"   📊 Total Events: {len(events_collected)}")

    event_types = {}
    for event in events_collected:
        et = event.get("type")
        event_types[et] = event_types.get(et, 0) + 1

    print(f"   📋 Event Types:")
    for et, count in event_types.items():
        print(f"      - {et}: {count}")

    print(f"\n   💬 Final Response ({len(full_response)} chars):")
    print(f"      {full_response[:200]}{'...' if len(full_response) > 200 else ''}")

    # Verify
    print("\n5️⃣ Verification:")

    checks = {
        "thinking event": "thinking" in event_types,
        "tool_call_started": "tool_call_started" in event_types,
        "tool_call_completed": "tool_call_completed" in event_types,
        "text event": "text" in event_types,
        "done event": "done" in event_types,
        "response not empty": len(full_response) > 0
    }

    all_passed = all(checks.values())

    for check, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"   {status} {check}")

    print("\n" + "="*60)
    if all_passed:
        print("🎉 INTEGRATION TEST PASSED!")
    else:
        print("❌ INTEGRATION TEST FAILED")
    print("="*60 + "\n")

    return all_passed


if __name__ == "__main__":
    result = asyncio.run(test_complete_flow())
    sys.exit(0 if result else 1)
