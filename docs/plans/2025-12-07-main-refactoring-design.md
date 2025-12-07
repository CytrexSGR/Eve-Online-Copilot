# Design: main.py Refactoring

**Date:** 2025-12-07
**Status:** Approved

---

## Overview

Split `main.py` (871 lines) into modular routers and a shared schemas module.

## Goals

- Reduce `main.py` to ~50 lines (app setup only)
- Each resource gets its own router
- All Pydantic models in central `schemas.py`
- Maintain 100% API compatibility (no endpoint changes)

## New File Structure

```
eve_copilot/
├── main.py              # Slim: App, CORS, Router imports (~50 lines)
├── schemas.py           # All Pydantic Request/Response Models (~80 lines)
├── routers/
│   ├── __init__.py      # Updated with new router exports
│   ├── auth.py          # NEW: /api/auth/* (6 endpoints)
│   ├── character.py     # NEW: /api/character/* (11 endpoints)
│   ├── bookmarks.py     # NEW: /api/bookmarks/* (8 endpoints)
│   ├── production.py    # NEW: /api/production/* (2 endpoints)
│   ├── market.py        # NEW: /api/market/*, /api/trade/* (4 endpoints)
│   ├── items.py         # NEW: /api/items/*, /api/groups/*, /api/materials/*, /api/regions (7 endpoints)
│   ├── shopping.py      # Existing
│   ├── hunter.py        # Existing
│   ├── mcp.py           # Existing
│   ├── mining.py        # Existing
│   └── war.py           # Existing
```

## Router Details

| Router | Prefix | Endpoints | Imports From |
|--------|--------|-----------|--------------|
| `auth.py` | `/api/auth` | login, callback, characters, refresh, remove, scopes | `auth.eve_auth` |
| `character.py` | `/api/character` | wallet, assets, skills, skillqueue, orders, industry, blueprints, info, corp/* | `character.character_api` |
| `bookmarks.py` | `/api/bookmarks` | create, get, check, update, delete, lists CRUD | `bookmark_service` |
| `production.py` | `/api/production` | cost (POST + GET) | `services.calculate_production_cost` |
| `market.py` | `/api/market`, `/api/trade` | stats, arbitrage (POST + GET) | `services.find_arbitrage`, `esi_client` |
| `items.py` | `/api/items`, `/api/groups`, `/api/materials`, `/api/regions` | search, info, composition, volumes | `database.*` |

## schemas.py Content

```python
from pydantic import BaseModel
from typing import Optional, List
from config import REGIONS

# Production
class ProductionCostRequest(BaseModel):
    type_id: int
    me_level: int = 0
    te_level: int = 0
    region_id: int = REGIONS["the_forge"]
    use_buy_orders: bool = False

# Trade
class ArbitrageRequest(BaseModel):
    group_name: Optional[str] = None
    group_id: Optional[int] = None
    source_region: int = REGIONS["the_forge"]
    target_region: int = REGIONS["domain"]
    min_margin_percent: float = 5.0
    limit: int = 5

# Bookmarks
class BookmarkCreate(BaseModel):
    type_id: int
    name: str
    notes: Optional[str] = None
    priority: int = 0
    tags: Optional[List[str]] = None

class BookmarkUpdate(BaseModel):
    name: Optional[str] = None
    notes: Optional[str] = None
    priority: Optional[int] = None
    tags: Optional[List[str]] = None

class BookmarkListCreate(BaseModel):
    name: str
    description: Optional[str] = None
    color: Optional[str] = "#3b82f6"
```

## main.py After Refactoring

```python
#!/usr/bin/env python3
"""EVE Co-Pilot API - FastAPI Application"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import auth, character, bookmarks, production, market, items
from routers import shopping, hunter, mcp, mining, war

app = FastAPI(
    title="EVE Co-Pilot API",
    description="REST API for EVE Online production and trading analysis",
    version="1.2.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all routers
app.include_router(auth.router)
app.include_router(character.router)
app.include_router(bookmarks.router)
app.include_router(production.router)
app.include_router(market.router)
app.include_router(items.router)
app.include_router(shopping.router)
app.include_router(hunter.router)
app.include_router(mcp.router)
app.include_router(mining.router)
app.include_router(war.router)

@app.get("/")
async def root():
    """API health check"""
    return {"name": "EVE Co-Pilot API", "version": "1.2.0", "status": "online"}

if __name__ == "__main__":
    import uvicorn
    from config import SERVER_HOST, SERVER_PORT
    uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT)
```

## Implementation Steps

1. Create `schemas.py` with all Pydantic models
2. Create `routers/auth.py`
3. Create `routers/character.py`
4. Create `routers/bookmarks.py`
5. Create `routers/production.py`
6. Create `routers/market.py`
7. Create `routers/items.py`
8. Update `routers/__init__.py`
9. Rewrite `main.py` (slim version)
10. Test all endpoints
11. Commit & push

## Verification

After refactoring:
- `curl http://localhost:8000/` returns health check
- `curl http://localhost:8000/docs` shows all endpoints
- All existing API calls continue to work
