#!/usr/bin/env python3
"""
EVE Co-Pilot API
FastAPI-based REST API for EVE Online production and trading analysis
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import (
    auth_router,
    character_router,
    bookmarks_router,
    production_router,
    simulation_router,
    market_router,
    items_router,
    shopping_router,
    hunter_router,
    mcp_router,
    mining_router,
    war_router,
)

# FastAPI App
app = FastAPI(
    title="EVE Co-Pilot API",
    description="REST API for EVE Online production cost calculation, arbitrage finding, and character management",
    version="1.2.0"
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all routers
app.include_router(auth_router)
app.include_router(character_router)
app.include_router(bookmarks_router)
app.include_router(production_router)
app.include_router(simulation_router)
app.include_router(market_router)
app.include_router(items_router)
app.include_router(shopping_router)
app.include_router(hunter_router)
app.include_router(mcp_router)
app.include_router(mining_router)
app.include_router(war_router)


@app.get("/")
async def root():
    """API health check and info"""
    return {
        "name": "EVE Co-Pilot API",
        "version": "1.2.0",
        "status": "online",
        "endpoints": {
            "production_cost": "/api/production/cost",
            "arbitrage": "/api/trade/arbitrage",
            "market_stats": "/api/market/stats/{region_id}/{type_id}",
            "item_search": "/api/items/search",
            "group_search": "/api/groups/search",
            "auth_login": "/api/auth/login",
            "shopping": "/api/shopping/*",
            "hunter": "/api/hunter/scan",
            "mcp": "/mcp/tools/*"
        }
    }


if __name__ == "__main__":
    import uvicorn
    from config import SERVER_HOST, SERVER_PORT
    print("Starting EVE Co-Pilot API Server...")
    print(f"Server: http://{SERVER_HOST}:{SERVER_PORT}")
    print(f"Docs: http://localhost:{SERVER_PORT}/docs")
    uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT)
