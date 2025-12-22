"""
MCP Router Module
Model Context Protocol implementation for EVE Co-Pilot.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
import traceback

from .tools import ALL_TOOLS, ALL_HANDLERS, get_handler_by_name, TOOL_COUNTS

# Create router
router = APIRouter(prefix="/mcp", tags=["MCP"])


# Request/Response Models
class ToolCallRequest(BaseModel):
    """Request model for MCP tool calls."""
    name: str
    arguments: Dict[str, Any] = {}


class ToolListResponse(BaseModel):
    """Response model for tool listing."""
    tools: List[Dict[str, Any]]
    count: int
    categories: Dict[str, int]


# Routes
@router.get("/tools/list", response_model=ToolListResponse)
async def list_tools():
    """
    List all available MCP tools.

    Returns:
        List of tool definitions with metadata
    """
    return {
        "tools": ALL_TOOLS,
        "count": len(ALL_TOOLS),
        "categories": TOOL_COUNTS
    }


@router.post("/tools/call")
async def call_tool(request: ToolCallRequest):
    """
    Execute an MCP tool.

    Args:
        request: Tool call request with name and arguments

    Returns:
        Tool execution result in MCP format
    """
    tool_name = request.name
    args = request.arguments

    # Get handler
    handler = get_handler_by_name(tool_name)
    if not handler:
        raise HTTPException(
            status_code=404,
            detail=f"Tool '{tool_name}' not found. Use /mcp/tools/list to see available tools."
        )

    # Execute handler
    try:
        result = handler(args)
        return result
    except Exception as e:
        error_msg = f"Tool execution failed: {str(e)}\n{traceback.format_exc()}"
        return {
            "error": error_msg,
            "isError": True
        }


@router.get("/tools/{tool_name}")
async def get_tool_info(tool_name: str):
    """
    Get information about a specific tool.

    Args:
        tool_name: Name of the tool

    Returns:
        Tool definition
    """
    from .tools import get_tool_by_name

    tool = get_tool_by_name(tool_name)
    if not tool:
        raise HTTPException(
            status_code=404,
            detail=f"Tool '{tool_name}' not found"
        )

    return tool


@router.get("/health")
async def health_check():
    """MCP server health check."""
    return {
        "status": "healthy",
        "total_tools": len(ALL_TOOLS),
        "categories": TOOL_COUNTS
    }


__all__ = ["router"]
