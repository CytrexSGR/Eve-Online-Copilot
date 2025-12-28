"""
Test Agent Runtime
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from copilot_server.agent.runtime import AgentRuntime
from copilot_server.agent.sessions import AgentSessionManager
from copilot_server.agent.models import AgentSession, SessionStatus
from copilot_server.models.user_settings import AutonomyLevel
from copilot_server.llm.anthropic_client import AnthropicClient
from copilot_server.mcp.orchestrator import ToolOrchestrator


@pytest.fixture
async def session_manager():
    """Create AgentSessionManager for testing."""
    manager = AgentSessionManager()
    await manager.startup()
    yield manager
    await manager.shutdown()


@pytest.fixture
def runtime(session_manager):
    """Create AgentRuntime with mocked dependencies."""
    llm_client = AsyncMock(spec=AnthropicClient)
    orchestrator = MagicMock(spec=ToolOrchestrator)

    # Mock the mcp client within orchestrator
    orchestrator.mcp = MagicMock()
    orchestrator.mcp.get_tools = MagicMock(return_value=[])
    orchestrator.mcp.call_tool = MagicMock()

    runtime = AgentRuntime(
        session_manager=session_manager,
        llm_client=llm_client,
        orchestrator=orchestrator
    )

    return runtime


@pytest.mark.asyncio
async def test_execute_simple_response(runtime, session_manager):
    """Test execution with simple text response (no tools)."""
    session = await session_manager.create_session(
        character_id=1117367444
    )
    session.add_message("user", "Hello")

    # Mock LLM response (no tool calls)
    runtime.llm_client.chat.return_value = {
        "content": [{"type": "text", "text": "Hello! How can I help?"}],
        "stop_reason": "end_turn"
    }

    await runtime.execute(session)

    # Verify session completed
    assert session.status == SessionStatus.COMPLETED
    assert len(session.messages) == 2  # user + assistant
    assert session.messages[1].role == "assistant"
    assert "Hello! How can I help?" in session.messages[1].content


@pytest.mark.asyncio
async def test_execute_single_tool_call(runtime, session_manager):
    """Test execution with single tool call."""
    session = await session_manager.create_session(
        character_id=1117367444
    )
    session.add_message("user", "What's the price of Tritanium in Jita?")

    # Mock MCP tools
    runtime.orchestrator.mcp.get_tools.return_value = [
        {
            "name": "get_market_stats",
            "description": "Get market statistics",
            "parameters": []
        }
    ]

    # Mock tool schema building
    runtime.llm_client.build_tool_schema.return_value = [
        {
            "name": "get_market_stats",
            "description": "Get market statistics",
            "input_schema": {"type": "object", "properties": {}, "required": []}
        }
    ]

    # Mock LLM response (single tool call)
    first_response = {
        "content": [
            {
                "type": "tool_use",
                "id": "tool-1",
                "name": "get_market_stats",
                "input": {"type_id": 34, "region_id": 10000002}
            }
        ],
        "stop_reason": "tool_use"
    }

    # Mock final LLM response after tool execution
    second_response = {
        "content": [{"type": "text", "text": "Tritanium in Jita: 5.50 ISK sell, 5.45 ISK buy"}],
        "stop_reason": "end_turn"
    }

    # Set up side effect for two calls
    runtime.llm_client.chat.side_effect = [first_response, second_response]

    # Mock tool execution
    runtime.orchestrator.mcp.call_tool.return_value = {
        "content": [{"text": '{"lowest_sell": 5.50, "highest_buy": 5.45}'}]
    }

    await runtime.execute(session)

    # Verify tool was called
    runtime.orchestrator.mcp.call_tool.assert_called_once()

    # Verify session completed
    assert session.status == SessionStatus.COMPLETED
