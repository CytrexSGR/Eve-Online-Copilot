#!/usr/bin/env python3
"""
Phase 7 Integration Test with REAL MCP Server
Tests complete end-to-end flow with actual MCP tool calls.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from copilot_server.agent.agentic_loop import AgenticStreamingLoop
from copilot_server.llm.openai_client import OpenAIClient
from copilot_server.mcp.client import MCPClient
from copilot_server.models.user_settings import UserSettings, AutonomyLevel
from copilot_server.config import OPENAI_API_KEY, OPENAI_MODEL


async def test_with_real_mcp():
    """Test agentic loop with real MCP server."""
    print("\n" + "="*60)
    print("Phase 7 Integration Test - REAL MCP Server")
    print("="*60)

    # Setup
    print("\n1️⃣ Setup Components...")
    user_settings = UserSettings(
        character_id=526379435,
        autonomy_level=AutonomyLevel.SUPERVISED  # L3: Auto-execute CRITICAL tools
    )

    llm_client = OpenAIClient(api_key=OPENAI_API_KEY, model=OPENAI_MODEL)

    # Real MCP Client (connects to http://localhost:8000)
    mcp_client = MCPClient()

    # Fetch tools from MCP server
    tools = mcp_client.get_tools()
    print(f"   ✅ LLM Client: OpenAI {OPENAI_MODEL}")
    print(f"   ✅ MCP Client: Real (http://localhost:8000)")
    print(f"   ✅ MCP Tools: {len(tools)} tools loaded")
    for tool in tools:
        print(f"      - {tool['name']}: {tool['description']}")
    print(f"   ✅ Autonomy: {user_settings.autonomy_level.value}")

    # Create agentic loop
    loop = AgenticStreamingLoop(
        llm_client=llm_client,
        mcp_client=mcp_client,
        user_settings=user_settings,
        max_iterations=5
    )

    # Test message
    print("\n2️⃣ User Message:")
    message = "Navigate to https://www.eveonline.com and take a screenshot"
    print(f"   💬 '{message}'")

    # Execute agentic loop
    print("\n3️⃣ Agentic Loop Execution:")

    messages = [
        {"role": "user", "content": message}
    ]

    system_prompt = """You are a browser automation assistant. You have access to Puppeteer tools.
When asked to navigate or interact with websites, use the available tools:
- puppeteer_navigate: Navigate to a URL
- puppeteer_screenshot: Take a screenshot
- puppeteer_click: Click an element"""

    events_collected = []
    full_response = ""
    tools_executed = []

    try:
        async for event in loop.execute(
            messages=messages,
            system=system_prompt,
            session_id="test-mcp-session"
        ):
            events_collected.append(event)
            event_type = event.get("type")

            if event_type == "thinking":
                print(f"   🤔 Iteration {event.get('iteration')}")

            elif event_type == "text":
                text = event.get("text", "")
                full_response += text
                # Only print first/last chunks to keep output clean
                if len(full_response) < 50 or len(full_response) > len(full_response) - 50:
                    print(f"   💭 LLM: {text[:30]}{'...' if len(text) > 30 else ''}")

            elif event_type == "tool_call_started":
                tool = event.get("tool")
                args = event.get("arguments")
                tools_executed.append(tool)
                print(f"   🔧 Tool Starting: {tool}")
                print(f"      Args: {args}")

            elif event_type == "tool_call_completed":
                tool = event.get("tool")
                result = event.get("result", {})
                # Extract text from result
                if "content" in result and result["content"]:
                    result_text = result["content"][0].get("text", "")
                    print(f"   ✅ Tool Completed: {tool}")
                    print(f"      Result: {result_text[:60]}{'...' if len(result_text) > 60 else ''}")

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

    print(f"\n   🔧 Tools Executed: {len(tools_executed)}")
    for tool in tools_executed:
        print(f"      - {tool}")

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
        "response not empty": len(full_response) > 0,
        "tools executed": len(tools_executed) > 0
    }

    all_passed = all(checks.values())

    for check, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"   {status} {check}")

    print("\n" + "="*60)
    if all_passed:
        print("🎉 REAL MCP INTEGRATION TEST PASSED!")
    else:
        print("❌ REAL MCP INTEGRATION TEST FAILED")
    print("="*60 + "\n")

    return all_passed


if __name__ == "__main__":
    result = asyncio.run(test_with_real_mcp())
    sys.exit(0 if result else 1)
