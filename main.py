#!/usr/bin/env python3
"""
EVE Co-Pilot MCP Server
FastAPI-based REST API for EVE Online production and trading analysis
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import uvicorn

from config import SERVER_HOST, SERVER_PORT, REGIONS, ESI_SCOPES
from services import calculate_production_cost, find_arbitrage
from database import get_item_info, get_item_by_name, get_group_by_name, get_material_composition
from esi_client import esi_client
from auth import eve_auth
from character import character_api
from production_simulator import production_simulator

# Import routers
from routers.shopping import router as shopping_router
from routers.hunter import router as hunter_router
from routers.mcp import router as mcp_router
from routers.mining import router as mining_router
from routers.war import router as war_router

# FastAPI App
app = FastAPI(
    title="EVE Co-Pilot API",
    description="MCP Server for EVE Online production cost calculation, arbitrage finding, and character management",
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

# Register routers
app.include_router(shopping_router)
app.include_router(hunter_router)
app.include_router(mcp_router)
app.include_router(mining_router)
app.include_router(war_router)


# Request Models
class ProductionCostRequest(BaseModel):
    type_id: int
    me_level: int = 0
    te_level: int = 0
    region_id: int = REGIONS["the_forge"]
    use_buy_orders: bool = False


class ArbitrageRequest(BaseModel):
    group_name: Optional[str] = None
    group_id: Optional[int] = None
    source_region: int = REGIONS["the_forge"]
    target_region: int = REGIONS["domain"]
    min_margin_percent: float = 5.0
    limit: int = 5


# ============================================================
# Core API Endpoints
# ============================================================

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


# ============================================================
# Authentication Endpoints
# ============================================================

@app.get("/api/auth/login")
async def auth_login(redirect: bool = False):
    """Start OAuth2 authentication flow"""
    result = eve_auth.get_auth_url()
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    if redirect:
        return RedirectResponse(url=result["auth_url"])
    return result


@app.get("/api/auth/callback")
async def auth_callback(
    code: str = Query(..., description="Authorization code from EVE SSO"),
    state: str = Query(..., description="State parameter for CSRF protection")
):
    """OAuth2 callback endpoint"""
    result = eve_auth.handle_callback(code, state)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result)
    return result


@app.get("/api/auth/characters")
async def auth_characters():
    """Get list of authenticated characters"""
    characters = eve_auth.get_authenticated_characters()
    return {"authenticated_characters": len(characters), "characters": characters}


@app.post("/api/auth/refresh/{character_id}")
async def auth_refresh(character_id: int):
    """Manually refresh token for a character"""
    result = eve_auth.refresh_token(character_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.delete("/api/auth/character/{character_id}")
async def auth_remove_character(character_id: int):
    """Remove authentication for a character"""
    result = eve_auth.remove_character(character_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@app.get("/api/auth/scopes")
async def auth_scopes():
    """Get required ESI scopes"""
    return {"required_scopes": ESI_SCOPES}


# ============================================================
# Character Data Endpoints
# ============================================================

@app.get("/api/character/{character_id}/wallet")
async def character_wallet(character_id: int):
    """Get character's wallet balance"""
    result = character_api.get_wallet_balance(character_id)
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.get("/api/character/{character_id}/assets")
async def character_assets(
    character_id: int,
    location_id: Optional[int] = Query(None)
):
    """Get character's assets"""
    result = character_api.get_assets(character_id, location_id)
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.get("/api/character/{character_id}/skills")
async def character_skills(character_id: int):
    """Get character's skills"""
    result = character_api.get_skills(character_id)
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.get("/api/character/{character_id}/skillqueue")
async def character_skillqueue(character_id: int):
    """Get character's skill queue"""
    result = character_api.get_skill_queue(character_id)
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.get("/api/character/{character_id}/orders")
async def character_orders(character_id: int):
    """Get character's active market orders"""
    result = character_api.get_market_orders(character_id)
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.get("/api/character/{character_id}/industry")
async def character_industry(character_id: int, include_completed: bool = Query(False)):
    """Get character's industry jobs"""
    result = character_api.get_industry_jobs(character_id, include_completed)
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.get("/api/character/{character_id}/blueprints")
async def character_blueprints(character_id: int):
    """Get character's blueprints"""
    result = character_api.get_blueprints(character_id)
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.get("/api/character/{character_id}/info")
async def character_info(character_id: int):
    """Get public character information"""
    result = character_api.get_character_info(character_id)
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# ============================================================
# Corporation Endpoints
# ============================================================

@app.get("/api/character/{character_id}/corporation/wallet")
async def corporation_wallet(character_id: int):
    """Get corporation wallet balances"""
    result = character_api.get_corporation_wallets(character_id)
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.get("/api/character/{character_id}/corporation/info")
async def corporation_info(character_id: int):
    """Get corporation info for a character"""
    corp_id = character_api.get_corporation_id(character_id)
    if not corp_id:
        raise HTTPException(status_code=404, detail="Corporation not found")
    result = character_api.get_corporation_info(corp_id)
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.get("/api/character/{character_id}/corporation/journal/{division}")
async def corporation_journal(character_id: int, division: int = 1):
    """Get corporation wallet journal for a specific division (1-7)"""
    result = character_api.get_corporation_wallet_journal(character_id, division)
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# ============================================================
# Production & Trading Endpoints
# ============================================================

@app.post("/api/production/cost")
async def api_production_cost(request: ProductionCostRequest):
    """Calculate production cost for an item"""
    result = calculate_production_cost(
        type_id=request.type_id,
        me_level=request.me_level,
        te_level=request.te_level,
        region_id=request.region_id,
        use_buy_orders=request.use_buy_orders
    )
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@app.get("/api/production/cost/{type_id}")
async def api_production_cost_get(
    type_id: int,
    me_level: int = Query(0, ge=0, le=10),
    te_level: int = Query(0, ge=0, le=10),
    region_id: int = Query(REGIONS["the_forge"]),
    use_buy_orders: bool = Query(False)
):
    """GET endpoint for production cost calculation"""
    result = calculate_production_cost(
        type_id=type_id, me_level=me_level, te_level=te_level,
        region_id=region_id, use_buy_orders=use_buy_orders
    )
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@app.post("/api/trade/arbitrage")
async def api_arbitrage(request: ArbitrageRequest):
    """Find arbitrage opportunities between two regions"""
    result = find_arbitrage(
        group_name=request.group_name,
        group_id=request.group_id,
        source_region=request.source_region,
        target_region=request.target_region,
        min_margin_percent=request.min_margin_percent,
        limit=request.limit
    )
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@app.get("/api/trade/arbitrage")
async def api_arbitrage_get(
    group_name: Optional[str] = Query(None),
    group_id: Optional[int] = Query(None),
    source_region: int = Query(REGIONS["the_forge"]),
    target_region: int = Query(REGIONS["domain"]),
    min_margin_percent: float = Query(5.0),
    limit: int = Query(5, ge=1, le=50)
):
    """GET endpoint for arbitrage search"""
    result = find_arbitrage(
        group_name=group_name, group_id=group_id,
        source_region=source_region, target_region=target_region,
        min_margin_percent=min_margin_percent, limit=limit
    )
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# ============================================================
# Market & Data Endpoints
# ============================================================

@app.get("/api/market/stats/{region_id}/{type_id}")
async def api_market_stats(region_id: int, type_id: int):
    """Get market statistics for an item in a region"""
    stats = esi_client.get_market_stats(region_id, type_id)
    if not stats.get("total_orders"):
        raise HTTPException(status_code=404, detail="No market data found")
    item = get_item_info(type_id)
    if item:
        stats["item_name"] = item["typeName"]
    return stats


@app.get("/api/items/search")
async def api_item_search(q: str = Query(..., min_length=2)):
    """Search for items by name"""
    items = get_item_by_name(q)
    return {"query": q, "results": items, "count": len(items)}


@app.get("/api/items/{type_id}")
async def api_item_info(type_id: int):
    """Get item information by typeID"""
    item = get_item_info(type_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@app.get("/api/materials/{type_id}/composition")
async def api_material_composition(type_id: int):
    """Get manufacturing composition for an item"""
    composition = get_material_composition(type_id)
    item = get_item_info(type_id)
    return {
        "type_id": type_id,
        "item_name": item["typeName"] if item else f"Type {type_id}",
        "is_craftable": len(composition) > 0,
        "materials": [
            {"type_id": m["material_type_id"], "name": m["material_name"], "quantity": m["quantity"]}
            for m in composition
        ]
    }


@app.get("/api/materials/{type_id}/volumes")
async def api_material_volumes(type_id: int):
    """Get available volumes for a material across all trade hub regions"""
    item = get_item_info(type_id)
    volumes = {}
    for region_name, region_id in REGIONS.items():
        depth = esi_client.get_market_depth(region_id, type_id)
        volumes[region_name] = {
            "sell_volume": depth["sell_volume"],
            "lowest_sell": depth["lowest_sell_price"],
            "lowest_sell_volume": depth["lowest_sell_volume"],
            "sell_orders": depth["sell_orders"],
            "buy_volume": depth["buy_volume"],
            "highest_buy": depth["highest_buy_price"],
        }
    best_availability = max(
        [(r, v["sell_volume"]) for r, v in volumes.items()],
        key=lambda x: x[1], default=(None, 0)
    )
    return {
        "type_id": type_id,
        "item_name": item["typeName"] if item else f"Type {type_id}",
        "volumes_by_region": volumes,
        "best_availability_region": best_availability[0],
        "best_availability_volume": best_availability[1]
    }


@app.get("/api/groups/search")
async def api_group_search(q: str = Query(..., min_length=2)):
    """Search for item groups by name"""
    groups = get_group_by_name(q)
    return {"query": q, "results": groups, "count": len(groups)}


@app.get("/api/regions")
async def api_regions():
    """Get list of known regions"""
    return REGIONS


# ============================================================
# Bookmark Endpoints
# ============================================================

from bookmark_service import bookmark_service


class BookmarkCreate(BaseModel):
    type_id: int
    item_name: str
    character_id: Optional[int] = None
    corporation_id: Optional[int] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    priority: int = 0


class BookmarkUpdate(BaseModel):
    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    priority: Optional[int] = None


class BookmarkListCreate(BaseModel):
    name: str
    description: Optional[str] = None
    character_id: Optional[int] = None
    corporation_id: Optional[int] = None
    is_shared: bool = False


@app.post("/api/bookmarks")
async def create_bookmark(request: BookmarkCreate):
    """Create a new bookmark"""
    return bookmark_service.create_bookmark(
        type_id=request.type_id, item_name=request.item_name,
        character_id=request.character_id, corporation_id=request.corporation_id,
        notes=request.notes, tags=request.tags, priority=request.priority
    )


@app.get("/api/bookmarks")
async def get_bookmarks(
    character_id: Optional[int] = Query(None),
    corporation_id: Optional[int] = Query(None),
    list_id: Optional[int] = Query(None)
):
    """Get bookmarks with optional filters"""
    return bookmark_service.get_bookmarks(character_id, corporation_id, list_id)


@app.get("/api/bookmarks/check/{type_id}")
async def check_bookmark(
    type_id: int,
    character_id: Optional[int] = Query(None),
    corporation_id: Optional[int] = Query(None)
):
    """Check if item is bookmarked"""
    bookmark = bookmark_service.get_bookmark_by_type(type_id, character_id, corporation_id)
    return {"is_bookmarked": bookmark is not None, "bookmark": bookmark}


@app.patch("/api/bookmarks/{bookmark_id}")
async def update_bookmark(bookmark_id: int, request: BookmarkUpdate):
    """Update a bookmark"""
    result = bookmark_service.update_bookmark(
        bookmark_id=bookmark_id, notes=request.notes,
        tags=request.tags, priority=request.priority
    )
    if not result:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    return result


@app.delete("/api/bookmarks/{bookmark_id}")
async def delete_bookmark(bookmark_id: int):
    """Delete a bookmark"""
    if not bookmark_service.delete_bookmark(bookmark_id):
        raise HTTPException(status_code=404, detail="Bookmark not found")
    return {"status": "deleted"}


@app.post("/api/bookmarks/lists")
async def create_bookmark_list(request: BookmarkListCreate):
    """Create a bookmark list"""
    return bookmark_service.create_list(
        name=request.name, description=request.description,
        character_id=request.character_id, corporation_id=request.corporation_id,
        is_shared=request.is_shared
    )


@app.get("/api/bookmarks/lists")
async def get_bookmark_lists(
    character_id: Optional[int] = Query(None),
    corporation_id: Optional[int] = Query(None)
):
    """Get bookmark lists"""
    return bookmark_service.get_lists(character_id, corporation_id)


@app.post("/api/bookmarks/lists/{list_id}/items/{bookmark_id}")
async def add_to_list(list_id: int, bookmark_id: int, position: int = Query(0)):
    """Add bookmark to list"""
    if not bookmark_service.add_to_list(list_id, bookmark_id, position):
        raise HTTPException(status_code=400, detail="Could not add to list")
    return {"status": "added"}


@app.delete("/api/bookmarks/lists/{list_id}/items/{bookmark_id}")
async def remove_from_list(list_id: int, bookmark_id: int):
    """Remove bookmark from list"""
    if not bookmark_service.remove_from_list(list_id, bookmark_id):
        raise HTTPException(status_code=404, detail="Item not in list")
    return {"status": "removed"}


# ============================================================
# Route & Navigation Endpoints
# ============================================================

from route_service import route_service, TRADE_HUB_SYSTEMS


@app.get("/api/route/hubs")
async def api_get_trade_hubs():
    """Get list of known trade hub systems"""
    result = {}
    for name, sys_id in TRADE_HUB_SYSTEMS.items():
        sys_info = route_service.get_system_by_name(name) or {}
        result[name] = {
            'system_id': sys_id,
            'system_name': sys_info.get('system_name', name.capitalize()),
            'security': sys_info.get('security', 0)
        }
    return result


@app.get("/api/route/distances/{from_system}")
async def api_hub_distances(from_system: str = "isikemi"):
    """Get distances from a system to all trade hubs"""
    return route_service.get_hub_distances(from_system)


@app.get("/api/route/{from_system}/{to_system}")
async def api_calculate_route(
    from_system: str,
    to_system: str,
    highsec_only: bool = Query(True)
):
    """Calculate route between two systems using A* pathfinding"""
    from_sys = route_service.get_system_by_name(from_system)
    to_sys = route_service.get_system_by_name(to_system)

    if not from_sys:
        raise HTTPException(status_code=404, detail=f"System not found: {from_system}")
    if not to_sys:
        raise HTTPException(status_code=404, detail=f"System not found: {to_system}")

    route = route_service.find_route(
        from_sys['system_id'], to_sys['system_id'],
        avoid_lowsec=highsec_only, avoid_nullsec=True
    )
    if not route:
        raise HTTPException(status_code=404, detail=f"No route found")

    travel_time = route_service.calculate_travel_time(route)
    return {
        "from": from_sys, "to": to_sys,
        "route": route, "travel_time": travel_time,
        "highsec_only": highsec_only,
        "waypoints": [r['system_name'] for r in route]
    }


@app.get("/api/systems/search")
async def api_search_systems(q: str = Query(..., min_length=2)):
    """Search for solar systems by name"""
    results = route_service.search_systems(q, limit=10)
    return {"query": q, "results": results}


# ============================================================
# Cargo & Logistics Endpoints
# ============================================================

from cargo_service import cargo_service


class CargoCalculateRequest(BaseModel):
    items: List[dict]


@app.post("/api/cargo/calculate")
async def api_calculate_cargo(request: CargoCalculateRequest):
    """Calculate total cargo volume for a list of items"""
    volume_info = cargo_service.calculate_cargo_volume(request.items)
    ship_recommendation = cargo_service.recommend_ship(volume_info['total_volume_m3'])
    return {**volume_info, 'ship_recommendation': ship_recommendation}


@app.get("/api/cargo/item/{type_id}")
async def api_item_volume(type_id: int, quantity: int = Query(1)):
    """Get volume for a single item"""
    volume = cargo_service.get_item_volume(type_id)
    if volume is None:
        raise HTTPException(status_code=404, detail="Item not found or has no volume")
    total = volume * quantity
    return {
        'type_id': type_id, 'quantity': quantity,
        'unit_volume': volume, 'total_volume': total,
        'formatted': cargo_service._format_volume(total)
    }


# ============================================================
# Multi-Region Comparison Endpoints
# ============================================================

@app.get("/api/market/compare/{type_id}")
async def api_compare_prices(type_id: int):
    """Compare prices for an item across all trade hubs"""
    prices = esi_client.get_all_region_prices(type_id)
    item = get_item_info(type_id)
    item_name = item["typeName"] if item else f"Type {type_id}"

    best_buy = {"region": None, "price": float('inf')}
    best_sell = {"region": None, "price": 0}

    for region, data in prices.items():
        if data.get("lowest_sell") and data["lowest_sell"] < best_buy["price"]:
            best_buy = {"region": region, "price": data["lowest_sell"]}
        if data.get("highest_buy") and data["highest_buy"] > best_sell["price"]:
            best_sell = {"region": region, "price": data["highest_buy"]}

    return {
        "type_id": type_id, "item_name": item_name,
        "prices_by_region": prices,
        "best_buy_region": best_buy["region"],
        "best_buy_price": best_buy["price"] if best_buy["price"] != float('inf') else None,
        "best_sell_region": best_sell["region"],
        "best_sell_price": best_sell["price"] if best_sell["price"] > 0 else None,
    }


@app.get("/api/market/arbitrage/{type_id}")
async def api_find_arbitrage(
    type_id: int,
    min_profit: float = Query(5.0)
):
    """Find arbitrage opportunities for an item between trade hubs"""
    opportunities = esi_client.find_arbitrage_opportunities(type_id, min_profit)
    item = get_item_info(type_id)
    item_name = item["typeName"] if item else f"Type {type_id}"
    return {
        "type_id": type_id, "item_name": item_name,
        "min_profit_percent": min_profit,
        "opportunities": opportunities,
        "opportunity_count": len(opportunities),
    }


@app.get("/api/production/optimize/{type_id}")
async def api_optimize_production(type_id: int, me: int = Query(10, ge=0, le=10)):
    """Find optimal regions for production using cached regional prices"""
    from database import get_db_connection

    REGION_ID_TO_NAME = {
        10000002: 'the_forge', 10000043: 'domain',
        10000030: 'heimatar', 10000032: 'sinq_laison', 10000042: 'metropolis',
    }

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Get materials
            cur.execute("""
                SELECT m."materialTypeID", t."typeName", m.quantity
                FROM "invTypeMaterials" m
                JOIN "invTypes" t ON m."materialTypeID" = t."typeID"
                WHERE m."typeID" = %s
            """, (type_id,))
            materials = cur.fetchall()

            if not materials:
                raise HTTPException(status_code=404, detail="No blueprint found for this item")

            cur.execute('SELECT "typeName" FROM "invTypes" WHERE "typeID" = %s', (type_id,))
            item_row = cur.fetchone()
            item_name = item_row[0] if item_row else f"Type {type_id}"

            # Get all prices
            material_type_ids = [m[0] for m in materials]
            all_type_ids = material_type_ids + [type_id]

            cur.execute("""
                SELECT type_id, region_id, lowest_sell, highest_buy, sell_volume, buy_volume
                FROM market_prices WHERE type_id = ANY(%s)
            """, (all_type_ids,))

            all_prices = {}
            for row in cur.fetchall():
                tid, region_id, lowest_sell, highest_buy, sell_vol, buy_vol = row
                region_name = REGION_ID_TO_NAME.get(region_id)
                if not region_name:
                    continue
                if tid not in all_prices:
                    all_prices[tid] = {}
                all_prices[tid][region_name] = {
                    'lowest_sell': float(lowest_sell) if lowest_sell else None,
                    'highest_buy': float(highest_buy) if highest_buy else None,
                    'sell_volume': sell_vol or 0,
                    'buy_volume': buy_vol or 0,
                }

    me_factor = 1 - (me / 100)
    material_details = []

    for mat_id, mat_name, base_qty in materials:
        adjusted_qty = max(1, int(base_qty * me_factor))
        mat_prices = all_prices.get(mat_id, {})
        material_details.append({
            "type_id": mat_id, "name": mat_name,
            "base_quantity": base_qty, "adjusted_quantity": adjusted_qty,
            "prices_by_region": {r: d.get("lowest_sell") for r, d in mat_prices.items()},
            "volumes_by_region": {r: d.get("sell_volume", 0) for r, d in mat_prices.items()}
        })

    region_totals = {}
    for region in REGIONS.keys():
        total = sum(
            (mat["prices_by_region"].get(region) or 0) * mat["adjusted_quantity"]
            for mat in material_details
        )
        region_totals[region] = total if total > 0 else None

    valid_regions = [(r, c) for r, c in region_totals.items() if c]
    best_region = min(valid_regions, key=lambda x: x[1], default=(None, None)) if valid_regions else (None, None)

    product_prices_raw = all_prices.get(type_id, {})
    product_prices = {
        r: {"lowest_sell": d.get("lowest_sell"), "highest_buy": d.get("highest_buy")}
        for r, d in product_prices_raw.items()
    }
    best_sell = max(
        [(r, p.get("lowest_sell", 0) or 0) for r, p in product_prices.items()],
        key=lambda x: x[1], default=("the_forge", 0)
    )

    return {
        "type_id": type_id, "item_name": item_name, "me_level": me,
        "materials": material_details,
        "production_cost_by_region": region_totals,
        "cheapest_production_region": best_region[0],
        "cheapest_production_cost": best_region[1],
        "product_prices": product_prices,
        "best_sell_region": best_sell[0],
        "best_sell_price": best_sell[1]
    }


@app.post("/api/cache/clear")
async def api_clear_cache():
    """Clear the ESI price cache"""
    esi_client.clear_cache()
    return {"status": "cache cleared"}


# ============================================================
# Production Simulation Endpoints
# ============================================================

class SimulationRequest(BaseModel):
    blueprint_name: Optional[str] = None
    type_id: Optional[int] = None
    runs: int = 1
    me: int = 0
    te: int = 0
    character_id: Optional[int] = None
    region_id: int = REGIONS["the_forge"]


@app.post("/api/simulation/build")
async def api_simulate_build(request: SimulationRequest):
    """Simulate a production run with asset matching and profitability analysis"""
    type_id = request.type_id
    if not type_id and request.blueprint_name:
        items = get_item_by_name(request.blueprint_name)
        if items:
            for item in items:
                if item["typeName"].lower() == request.blueprint_name.lower():
                    type_id = item["typeID"]
                    break
            if not type_id:
                type_id = items[0]["typeID"]

    if not type_id:
        raise HTTPException(status_code=400, detail="Could not find item.")

    character_assets = None
    if request.character_id:
        assets_result = character_api.get_assets(request.character_id)
        if isinstance(assets_result, dict) and "error" not in assets_result:
            character_assets = assets_result.get("assets", [])

    result = production_simulator.simulate_build(
        type_id=type_id, runs=request.runs, me=request.me, te=request.te,
        character_assets=character_assets, region_id=request.region_id
    )
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@app.get("/api/simulation/build/{type_id}")
async def api_simulate_build_get(
    type_id: int,
    runs: int = Query(1, ge=1, le=1000),
    me: int = Query(0, ge=0, le=10),
    te: int = Query(0, ge=0, le=20),
    character_id: Optional[int] = Query(None),
    region_id: int = Query(REGIONS["the_forge"])
):
    """GET endpoint for production simulation"""
    character_assets = None
    if character_id:
        assets_result = character_api.get_assets(character_id)
        if isinstance(assets_result, dict) and "error" not in assets_result:
            character_assets = assets_result.get("assets", [])

    result = production_simulator.simulate_build(
        type_id=type_id, runs=runs, me=me, te=te,
        character_assets=character_assets, region_id=region_id
    )
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


if __name__ == "__main__":
    print("Starting EVE Co-Pilot MCP Server...")
    print(f"Server: http://{SERVER_HOST}:{SERVER_PORT}")
    print(f"Docs: http://localhost:{SERVER_PORT}/docs")
    uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT)
