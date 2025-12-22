"""
MCP Client
Handles tool calls to EVE Co-Pilot MCP endpoints.
"""

import requests
from typing import List, Dict, Any, Optional
import logging

from ..config import EVE_COPILOT_API_URL

logger = logging.getLogger(__name__)


class MCPClient:
    """Client for calling MCP tools via EVE Co-Pilot API."""

    def __init__(self, api_url: Optional[str] = None):
        """
        Initialize MCP client.

        Args:
            api_url: Base URL for EVE Co-Pilot API
        """
        self.api_url = api_url or EVE_COPILOT_API_URL
        self.tools_cache: Optional[List[Dict[str, Any]]] = None

    def get_tools(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Get all available MCP tools.

        Args:
            force_refresh: Force refresh from API

        Returns:
            List of tool definitions
        """
        if self.tools_cache and not force_refresh:
            return self.tools_cache

        try:
            response = requests.get(
                f"{self.api_url}/mcp/tools/list",
                timeout=10
            )
            response.raise_for_status()

            data = response.json()
            self.tools_cache = data.get("tools", [])
            logger.info(f"Loaded {len(self.tools_cache)} MCP tools")
            return self.tools_cache

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch tools: {e}")
            return []

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call an MCP tool.

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            Tool execution result
        """
        try:
            response = requests.post(
                f"{self.api_url}/mcp/tools/call",
                json={"name": name, "arguments": arguments},
                timeout=60
            )
            response.raise_for_status()

            result = response.json()
            logger.info(f"Tool '{name}' executed successfully")
            return result

        except requests.exceptions.Timeout:
            logger.error(f"Tool '{name}' timed out")
            return {
                "error": f"Tool '{name}' timed out after 60 seconds",
                "isError": True
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Tool '{name}' failed: {e}")
            return {
                "error": f"Tool execution failed: {str(e)}",
                "isError": True
            }

    def get_tool_info(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific tool.

        Args:
            name: Tool name

        Returns:
            Tool definition or None
        """
        tools = self.get_tools()
        for tool in tools:
            if tool["name"] == name:
                return tool
        return None

    def search_tools(self, query: str) -> List[Dict[str, Any]]:
        """
        Search tools by name or description.

        Args:
            query: Search query

        Returns:
            Matching tools
        """
        tools = self.get_tools()
        query_lower = query.lower()

        matches = []
        for tool in tools:
            if (query_lower in tool["name"].lower() or
                query_lower in tool["description"].lower()):
                matches.append(tool)

        return matches

    def get_tools_by_category(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group tools by category (inferred from name prefix).

        Returns:
            Tools grouped by category
        """
        tools = self.get_tools()
        categories: Dict[str, List[Dict[str, Any]]] = {}

        for tool in tools:
            # Infer category from tool name prefix
            name_parts = tool["name"].split("_")
            if len(name_parts) > 1:
                category = name_parts[0]
            else:
                category = "other"

            if category not in categories:
                categories[category] = []

            categories[category].append(tool)

        return categories
