#!/usr/bin/env python3
"""
Simple MCP Server for testing Phase 7 integration.
Provides Chrome DevTools-like tools.
"""

from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict, Any, List
import uvicorn

app = FastAPI(title="Test MCP Server")


class ToolCallRequest(BaseModel):
    name: str
    arguments: Dict[str, Any]


# Mock Chrome DevTools tools
TOOLS = [
    {
        "name": "puppeteer_navigate",
        "description": "Navigate browser to a URL",
        "parameters": [
            {
                "name": "url",
                "type": "string",
                "description": "URL to navigate to",
                "required": True
            }
        ]
    },
    {
        "name": "puppeteer_screenshot",
        "description": "Take a screenshot of the current page",
        "parameters": [
            {
                "name": "path",
                "type": "string",
                "description": "Path to save screenshot",
                "required": False
            }
        ]
    },
    {
        "name": "puppeteer_click",
        "description": "Click an element on the page",
        "parameters": [
            {
                "name": "selector",
                "type": "string",
                "description": "CSS selector of element to click",
                "required": True
            }
        ]
    }
]


@app.get("/mcp/tools/list")
def list_tools():
    """Return available MCP tools."""
    return {"tools": TOOLS}


@app.post("/mcp/tools/call")
def call_tool(request: ToolCallRequest):
    """Execute an MCP tool."""
    print(f"\n🔧 MCP Tool Called: {request.name}")
    print(f"   Arguments: {request.arguments}")

    # Mock responses for different tools
    if request.name == "puppeteer_navigate":
        url = request.arguments.get("url", "")
        return {
            "content": [{
                "type": "text",
                "text": f"Successfully navigated to {url}"
            }]
        }

    elif request.name == "puppeteer_screenshot":
        path = request.arguments.get("path", "/tmp/screenshot.png")
        return {
            "content": [{
                "type": "text",
                "text": f"Screenshot saved to {path}"
            }]
        }

    elif request.name == "puppeteer_click":
        selector = request.arguments.get("selector", "")
        return {
            "content": [{
                "type": "text",
                "text": f"Clicked element: {selector}"
            }]
        }

    # Default response
    return {
        "content": [{
            "type": "text",
            "text": f"Tool {request.name} executed successfully"
        }]
    }


if __name__ == "__main__":
    print("\n" + "="*60)
    print("Test MCP Server Starting")
    print("="*60)
    print("Listening on: http://localhost:8000")
    print("Tools endpoint: http://localhost:8000/mcp/tools/list")
    print("="*60 + "\n")

    uvicorn.run(app, host="0.0.0.0", port=8000)
