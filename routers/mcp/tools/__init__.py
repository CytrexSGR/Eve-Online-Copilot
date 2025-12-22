"""
MCP Tools Registry
Centralized registry of all MCP tool definitions and handlers.
"""

from typing import Dict, List, Any, Callable

# Import all tool modules
from . import context
from . import market
from . import production
from . import war_room
from . import shopping
from . import character
from . import dashboard
from . import research
from . import bookmarks
from . import items
from . import routes
from . import mining
from . import hunter


# Combine all tools
ALL_TOOLS: List[Dict[str, Any]] = []
ALL_TOOLS.extend(context.TOOLS)
ALL_TOOLS.extend(market.TOOLS)
ALL_TOOLS.extend(production.TOOLS)
ALL_TOOLS.extend(war_room.TOOLS)
ALL_TOOLS.extend(shopping.TOOLS)
ALL_TOOLS.extend(character.TOOLS)
ALL_TOOLS.extend(dashboard.TOOLS)
ALL_TOOLS.extend(research.TOOLS)
ALL_TOOLS.extend(bookmarks.TOOLS)
ALL_TOOLS.extend(items.TOOLS)
ALL_TOOLS.extend(routes.TOOLS)
ALL_TOOLS.extend(mining.TOOLS)
ALL_TOOLS.extend(hunter.TOOLS)


# Combine all handlers
ALL_HANDLERS: Dict[str, Callable] = {}
ALL_HANDLERS.update(context.HANDLERS)
ALL_HANDLERS.update(market.HANDLERS)
ALL_HANDLERS.update(production.HANDLERS)
ALL_HANDLERS.update(war_room.HANDLERS)
ALL_HANDLERS.update(shopping.HANDLERS)
ALL_HANDLERS.update(character.HANDLERS)
ALL_HANDLERS.update(dashboard.HANDLERS)
ALL_HANDLERS.update(research.HANDLERS)
ALL_HANDLERS.update(bookmarks.HANDLERS)
ALL_HANDLERS.update(items.HANDLERS)
ALL_HANDLERS.update(routes.HANDLERS)
ALL_HANDLERS.update(mining.HANDLERS)
ALL_HANDLERS.update(hunter.HANDLERS)


def get_tool_by_name(name: str) -> Dict[str, Any]:
    """Get tool definition by name."""
    for tool in ALL_TOOLS:
        if tool["name"] == name:
            return tool
    return None


def get_handler_by_name(name: str) -> Callable:
    """Get handler function by tool name."""
    return ALL_HANDLERS.get(name)


# Tool counts by category
TOOL_COUNTS = {
    "context": len(context.TOOLS),
    "market": len(market.TOOLS),
    "production": len(production.TOOLS),
    "war_room": len(war_room.TOOLS),
    "shopping": len(shopping.TOOLS),
    "character": len(character.TOOLS),
    "dashboard": len(dashboard.TOOLS),
    "research": len(research.TOOLS),
    "bookmarks": len(bookmarks.TOOLS),
    "items": len(items.TOOLS),
    "routes": len(routes.TOOLS),
    "mining": len(mining.TOOLS),
    "hunter": len(hunter.TOOLS),
    "total": len(ALL_TOOLS)
}


__all__ = [
    "ALL_TOOLS",
    "ALL_HANDLERS",
    "get_tool_by_name",
    "get_handler_by_name",
    "TOOL_COUNTS"
]
