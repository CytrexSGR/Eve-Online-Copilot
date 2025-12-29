"""Tests for Context Window Manager."""

import pytest
from copilot_server.agent.context_manager import ContextWindowManager


def test_truncate_below_limit():
    """Test that messages below limit are not truncated."""
    manager = ContextWindowManager(max_messages=10)

    messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
    ]

    result = manager.truncate(messages)

    assert len(result) == 2
    assert result == messages


def test_truncate_at_limit():
    """Test truncation when exactly at limit."""
    manager = ContextWindowManager(max_messages=2)

    messages = [
        {"role": "user", "content": "Message 1"},
        {"role": "assistant", "content": "Response 1"},
    ]

    result = manager.truncate(messages)

    assert len(result) == 2
    assert result == messages


def test_truncate_over_limit():
    """Test truncation when over limit (keeps most recent)."""
    manager = ContextWindowManager(max_messages=3)

    messages = [
        {"role": "user", "content": "Oldest"},
        {"role": "assistant", "content": "Old response"},
        {"role": "user", "content": "Middle"},
        {"role": "assistant", "content": "Middle response"},
        {"role": "user", "content": "Newest"},
    ]

    result = manager.truncate(messages)

    # Should keep last 3 messages
    assert len(result) == 3
    assert result[0]["content"] == "Middle"
    assert result[1]["content"] == "Middle response"
    assert result[2]["content"] == "Newest"


def test_truncate_empty_messages():
    """Test handling of empty message list."""
    manager = ContextWindowManager(max_messages=10)

    result = manager.truncate([])

    assert result == []


def test_estimate_tokens_simple():
    """Test token estimation for simple text messages."""
    manager = ContextWindowManager()

    messages = [
        {"role": "user", "content": "Hello" * 100},  # 500 chars ≈ 125 tokens
    ]

    tokens = manager.estimate_tokens(messages)

    # Should be roughly 125 tokens (500 / 4)
    assert 100 < tokens < 150


def test_estimate_tokens_complex():
    """Test token estimation for complex content blocks."""
    manager = ContextWindowManager()

    messages = [
        {
            "role": "assistant",
            "content": [
                {"type": "text", "text": "Hello" * 50},  # 250 chars
                {
                    "type": "tool_use",
                    "name": "test_tool",
                    "input": {"arg": "value" * 20}  # ~100 chars
                }
            ]
        }
    ]

    tokens = manager.estimate_tokens(messages)

    # Should be roughly 87 tokens ((250 + 100) / 4)
    assert 70 < tokens < 110


def test_should_truncate():
    """Test truncation detection."""
    manager = ContextWindowManager(max_messages=5)

    # Below limit
    assert not manager.should_truncate([{"role": "user", "content": "test"}] * 3)

    # At limit
    assert not manager.should_truncate([{"role": "user", "content": "test"}] * 5)

    # Over limit
    assert manager.should_truncate([{"role": "user", "content": "test"}] * 6)


def test_context_summary():
    """Test context summary generation."""
    manager = ContextWindowManager(max_messages=3)

    messages = [
        {"role": "user", "content": "Message 1"},
        {"role": "assistant", "content": "Response 1"},
        {"role": "user", "content": "Message 2"},
        {"role": "assistant", "content": "Response 2"},
    ]

    summary = manager.get_context_summary(messages)

    assert summary["total_messages"] == 4
    assert summary["max_messages"] == 3
    assert summary["needs_truncation"] is True
    assert summary["messages_over_limit"] == 1
    assert "estimated_tokens" in summary


def test_large_conversation():
    """Test truncation with large conversation."""
    manager = ContextWindowManager(max_messages=10)

    # Create 50-message conversation
    messages = []
    for i in range(25):
        messages.append({"role": "user", "content": f"Question {i}"})
        messages.append({"role": "assistant", "content": f"Answer {i}"})

    result = manager.truncate(messages)

    # Should keep only last 10
    assert len(result) == 10
    # Should keep most recent (question 20 onwards)
    assert "Question 20" in result[0]["content"]
    assert "Answer 24" in result[-1]["content"]


def test_custom_max_messages():
    """Test custom max_messages setting."""
    manager = ContextWindowManager(max_messages=50)

    messages = [{"role": "user", "content": f"Msg {i}"} for i in range(30)]

    result = manager.truncate(messages)

    # Should not truncate (30 < 50)
    assert len(result) == 30
