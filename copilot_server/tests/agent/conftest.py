"""
Pytest configuration for agent tests.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_llm_client():
    """Mock LLM client for testing."""
    client = AsyncMock()
    client.chat.return_value = {
        "content": [{"type": "text", "text": "Hello! How can I help?"}],
        "stop_reason": "end_turn"
    }
    return client


@pytest.fixture
def mock_orchestrator():
    """Mock orchestrator for testing."""
    orchestrator = AsyncMock()
    orchestrator.mcp = MagicMock()
    orchestrator.mcp.get_tools.return_value = []
    return orchestrator
