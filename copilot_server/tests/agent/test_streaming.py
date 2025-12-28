import pytest
from copilot_server.agent.streaming import SSEFormatter

def test_format_text_chunk():
    """Test formatting text chunk for SSE."""
    formatter = SSEFormatter()

    chunk = {
        "type": "content_block_delta",
        "delta": {
            "type": "text_delta",
            "text": "Hello"
        }
    }

    result = formatter.format(chunk)

    assert result == 'data: {"type":"text","text":"Hello"}\n\n'


def test_format_error():
    """Test formatting error for SSE."""
    formatter = SSEFormatter()

    error = {
        "type": "error",
        "error": "API Error"
    }

    result = formatter.format(error)

    assert result == 'data: {"type":"error","error":"API Error"}\n\n'
