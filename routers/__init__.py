# Routers package

from .auth import router as auth_router
from .character import router as character_router
from .bookmarks import router as bookmarks_router
from .production import router as production_router, simulation_router
from .production_chains import router as production_chains_router
from .production_economics import router as production_economics_router
from .production_workflow import router as production_workflow_router
from .market import router as market_router
from .items import router as items_router
from .shopping import router as shopping_router
from .hunter import router as hunter_router
from .mcp import router as mcp_router
from .mining import router as mining_router
from .war import router as war_router
from .dashboard import router as dashboard_router
from .research import router as research_router

__all__ = [
    'auth_router',
    'character_router',
    'bookmarks_router',
    'production_router',
    'simulation_router',
    'production_chains_router',
    'production_economics_router',
    'production_workflow_router',
    'market_router',
    'items_router',
    'shopping_router',
    'hunter_router',
    'mcp_router',
    'mining_router',
    'war_router',
    'dashboard_router',
    'research_router',
]
