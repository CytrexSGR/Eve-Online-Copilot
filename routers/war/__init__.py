"""
War Room Router Package.

This package provides API endpoints for combat intelligence and analysis.
It splits the monolithic war router into focused modules.

Routers:
- battles: Active battles, battle details, telegram alerts
- systems: System kills, ship classes, danger scores
- analysis: Combat analysis, doctrines, conflicts, demand
- live: Real-time zkillboard data, pilot intelligence
- fw_sov: Faction Warfare and sovereignty campaigns
- map: Map data and safe route calculation

Usage:
    from routers.war import router

    # Add to FastAPI app
    app.include_router(router, prefix="/api/war", tags=["War Room"])
"""

from fastapi import APIRouter

from .battles import router as battles_router
from .systems import router as systems_router
from .analysis import router as analysis_router
from .live import router as live_router
from .fw_sov import router as fw_sov_router
from .map import router as map_router

# Create main router that aggregates all sub-routers
router = APIRouter()

# Include all sub-routers
router.include_router(battles_router)
router.include_router(systems_router)
router.include_router(analysis_router)
router.include_router(live_router)
router.include_router(fw_sov_router)
router.include_router(map_router)

__all__ = [
    'router',
    'battles_router',
    'systems_router',
    'analysis_router',
    'live_router',
    'fw_sov_router',
    'map_router',
]
