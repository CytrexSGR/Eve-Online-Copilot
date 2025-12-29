import pytest
from copilot_server.agent.tool_extractor import ToolCallExtractor

def test_extract_tool_call_from_anthropic_stream():
    """Test extracting tool_use blocks from Anthropic streaming chunks."""
    extractor = ToolCallExtractor()

    # Simulate Anthropic streaming events
    chunks = [
        {"type": "content_block_start", "index": 0, "content_block": {"type": "tool_use", "id": "toolu_123", "name": "get_market_price"}},
        {"type": "content_block_delta", "index": 0, "delta": {"type": "input_json_delta", "partial_json": '{"type'}},
        {"type": "content_block_delta", "index": 0, "delta": {"type": "input_json_delta", "partial_json": '_id": 34'}},
        {"type": "content_block_delta", "index": 0, "delta": {"type": "input_json_delta", "partial_json": '}'}},
        {"type": "content_block_stop", "index": 0}
    ]

    for chunk in chunks:
        extractor.process_chunk(chunk)

    tool_calls = extractor.get_tool_calls()

    assert len(tool_calls) == 1
    assert tool_calls[0]["id"] == "toolu_123"
    assert tool_calls[0]["name"] == "get_market_price"
    assert tool_calls[0]["input"] == {"type_id": 34}

def test_extract_mixed_text_and_tool_calls():
    """Test extracting both text and tool calls from same response."""
    extractor = ToolCallExtractor()

    chunks = [
        {"type": "content_block_start", "index": 0, "content_block": {"type": "text"}},
        {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "Let me check"}},
        {"type": "content_block_stop", "index": 0},
        {"type": "content_block_start", "index": 1, "content_block": {"type": "tool_use", "id": "toolu_456", "name": "search_items"}},
        {"type": "content_block_delta", "index": 1, "delta": {"type": "input_json_delta", "partial_json": '{"query": "Tritanium"}'}},
        {"type": "content_block_stop", "index": 1}
    ]

    for chunk in chunks:
        extractor.process_chunk(chunk)

    tool_calls = extractor.get_tool_calls()
    text_chunks = extractor.get_text_chunks()

    assert len(tool_calls) == 1
    assert len(text_chunks) == 1
    assert text_chunks[0] == "Let me check"

def test_extract_tool_call_from_openai_stream():
    """Test extracting function calls from OpenAI streaming chunks."""
    extractor = ToolCallExtractor()

    # OpenAI uses function_call in delta
    chunks = [
        {"choices": [{"delta": {"function_call": {"name": "get_market_price", "arguments": ""}}}]},
        {"choices": [{"delta": {"function_call": {"arguments": '{"type'}}}]},
        {"choices": [{"delta": {"function_call": {"arguments": '_id": 34'}}}]},
        {"choices": [{"delta": {"function_call": {"arguments": '}'}}}]},
        {"choices": [{"finish_reason": "function_call"}]}
    ]

    for chunk in chunks:
        extractor.process_chunk(chunk, provider="openai")

    tool_calls = extractor.get_tool_calls()

    assert len(tool_calls) == 1
    assert tool_calls[0]["name"] == "get_market_price"
    assert tool_calls[0]["input"] == {"type_id": 34}
