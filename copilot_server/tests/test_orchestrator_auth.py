# copilot_server/tests/test_orchestrator_auth.py

import pytest
from unittest.mock import Mock, AsyncMock, patch
import sys

# Mock anthropic before importing
sys.modules['anthropic'] = Mock()

from copilot_server.models.user_settings import UserSettings, AutonomyLevel
from copilot_server.mcp.orchestrator import ToolOrchestrator


@pytest.fixture
def mock_mcp():
    """Mock MCP client."""
    client = Mock()
    client.get_tools = Mock(return_value=[
        {"name": "search_item", "description": "Search items"},
        {"name": "create_shopping_list", "description": "Create list"}
    ])
    client.call_tool = Mock(return_value={"result": "success"})
    return client


@pytest.fixture
def mock_llm():
    """Mock LLM client."""
    client = Mock()
    client.build_tool_schema = Mock(return_value=[])
    return client


@pytest.fixture
def l0_user_settings():
    """READ_ONLY user settings."""
    return UserSettings(
        character_id=12345,
        autonomy_level=AutonomyLevel.READ_ONLY
    )


@pytest.fixture
def l1_user_settings():
    """RECOMMENDATIONS user settings."""
    return UserSettings(
        character_id=12345,
        autonomy_level=AutonomyLevel.RECOMMENDATIONS
    )


@pytest.fixture
def l2_user_settings():
    """ASSISTED user settings."""
    return UserSettings(
        character_id=12345,
        autonomy_level=AutonomyLevel.ASSISTED,
        require_confirmation=False
    )


def test_orchestrator_requires_user_settings(mock_mcp, mock_llm):
    """Orchestrator must be initialized with user settings."""
    with pytest.raises(TypeError):
        # Missing user_settings parameter
        ToolOrchestrator(mock_mcp, mock_llm)


def test_orchestrator_accepts_user_settings(mock_mcp, mock_llm, l1_user_settings):
    """Orchestrator accepts user settings parameter."""
    orchestrator = ToolOrchestrator(mock_mcp, mock_llm, l1_user_settings)

    assert orchestrator.settings == l1_user_settings
    assert orchestrator.auth_checker is not None


def test_orchestrator_blocks_unauthorized_tools(mock_mcp, mock_llm, l0_user_settings):
    """Orchestrator blocks tools user is not authorized to use."""
    orchestrator = ToolOrchestrator(mock_mcp, mock_llm, l0_user_settings)

    # L0 user cannot create shopping lists
    allowed = orchestrator._is_tool_allowed("create_shopping_list", {})

    assert allowed is False


def test_orchestrator_allows_authorized_tools(mock_mcp, mock_llm, l0_user_settings):
    """Orchestrator allows tools user is authorized to use."""
    orchestrator = ToolOrchestrator(mock_mcp, mock_llm, l0_user_settings)

    # L0 user can search items
    allowed = orchestrator._is_tool_allowed("search_item", {})

    assert allowed is True


@pytest.mark.asyncio
async def test_orchestrator_skips_unauthorized_in_workflow(mock_mcp, mock_llm, l0_user_settings):
    """Orchestrator skips unauthorized tools during workflow execution."""

    # Mock LLM response with unauthorized tool call
    mock_llm.chat = AsyncMock(return_value={
        "content": [
            {"type": "tool_use", "id": "1", "name": "create_shopping_list", "input": {}}
        ],
        "stop_reason": "tool_use"
    })

    orchestrator = ToolOrchestrator(mock_mcp, mock_llm, l0_user_settings)

    result = await orchestrator.execute_workflow(
        messages=[{"role": "user", "content": "Create a shopping list"}],
        max_iterations=1
    )

    # Should have error about authorization in tool results
    assert "tool_results" in result
    assert len(result["tool_results"]) > 0

    tool_result = result["tool_results"][0]
    assert "error" in tool_result or "blocked_by" in tool_result

    # MCP tool should NOT have been called
    mock_mcp.call_tool.assert_not_called()


@pytest.mark.asyncio
async def test_orchestrator_executes_authorized_tools(mock_mcp, mock_llm, l1_user_settings):
    """Orchestrator executes authorized tools during workflow."""

    # Mock LLM response with authorized tool call
    mock_llm.chat = AsyncMock(return_value={
        "content": [
            {"type": "tool_use", "id": "1", "name": "search_item", "input": {"query": "Tritanium"}}
        ],
        "stop_reason": "tool_use"
    })

    orchestrator = ToolOrchestrator(mock_mcp, mock_llm, l1_user_settings)

    result = await orchestrator.execute_workflow(
        messages=[{"role": "user", "content": "Search for Tritanium"}],
        max_iterations=1
    )

    # MCP tool should have been called
    mock_mcp.call_tool.assert_called_once_with("search_item", {"query": "Tritanium"})

    # Should have successful tool result
    assert "tool_results" in result
    assert len(result["tool_results"]) > 0

    tool_result = result["tool_results"][0]
    assert "result" in tool_result
    assert tool_result.get("blocked_by") != "authorization"


@pytest.mark.asyncio
async def test_orchestrator_returns_denial_reason_to_llm(mock_mcp, mock_llm, l0_user_settings):
    """Orchestrator returns helpful denial message to LLM."""

    # Mock LLM to make tool call, then check response
    responses = [
        {
            "content": [
                {"type": "tool_use", "id": "1", "name": "create_shopping_list", "input": {}}
            ],
            "stop_reason": "tool_use"
        },
        {
            "content": [
                {"type": "text", "text": "I cannot create shopping lists with your current autonomy level."}
            ],
            "stop_reason": "end_turn"
        }
    ]

    mock_llm.chat = AsyncMock(side_effect=responses)

    orchestrator = ToolOrchestrator(mock_mcp, mock_llm, l0_user_settings)

    result = await orchestrator.execute_workflow(
        messages=[{"role": "user", "content": "Create a shopping list"}],
        max_iterations=2
    )

    # Check that LLM was called twice (initial + after auth error)
    assert mock_llm.chat.call_count == 2

    # Check that second call received authorization error
    second_call_args = mock_llm.chat.call_args_list[1][1]
    messages = second_call_args["messages"]

    # Last message should be tool result with error
    last_message = messages[-1]
    assert last_message["role"] == "user"

    tool_result_block = last_message["content"][0]
    assert tool_result_block["type"] == "tool_result"
    assert "Authorization Error" in tool_result_block["content"]
