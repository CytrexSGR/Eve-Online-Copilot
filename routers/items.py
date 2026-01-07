"""
Items router - Item search, groups, materials, regions, routes, cargo, and systems endpoints.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional

from config import REGIONS
from src.database import get_item_info, get_item_by_name, get_group_by_name, get_material_composition
from src.esi_client import esi_client
from src.route_service import route_service, TRADE_HUB_SYSTEMS
from src.cargo_service import cargo_service
from src.schemas import CargoCalculateRequest

router = APIRouter(tags=["Items & Catalog"])


# ============================================================
# Items & Groups
# ============================================================

@router.get("/api/items/search")
async def api_item_search(
    q: str = Query("", min_length=0),
    group_id: Optional[int] = Query(None),
    market_group_id: Optional[int] = Query(None)
):
    """Search for items by name, optionally filtered by inventory group or market group"""
    # Require either a search query or a group filter
    if not q and not group_id and not market_group_id:
        raise HTTPException(status_code=422, detail="Either 'q' (min 2 chars), 'group_id', or 'market_group_id' must be provided")
    if q and len(q) < 2 and not group_id and not market_group_id:
        raise HTTPException(status_code=422, detail="Search query must be at least 2 characters")

    items = get_item_by_name(q, group_id=group_id, market_group_id=market_group_id)
    return {"query": q, "results": items, "count": len(items)}


@router.get("/api/items/{type_id}")
async def api_item_info(type_id: int):
    """Get item information by typeID"""
    item = get_item_info(type_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.get("/api/groups/search")
async def api_group_search(q: str = Query(..., min_length=2)):
    """Search for item groups by name"""
    groups = get_group_by_name(q)
    return {"query": q, "results": groups, "count": len(groups)}


@router.get("/api/regions")
async def api_regions():
    """Get list of known regions"""
    return REGIONS


# ============================================================
# Materials
# ============================================================

@router.get("/api/materials/{type_id}/composition")
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


@router.get("/api/materials/{type_id}/volumes")
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


# ============================================================
# Routes & Navigation
# ============================================================

@router.get("/api/route/hubs")
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


@router.get("/api/route/distances/{from_system}")
async def api_hub_distances(from_system: str = "isikemi"):
    """Get distances from a system to all trade hubs"""
    return route_service.get_hub_distances(from_system)


@router.get("/api/route/{from_system}/{to_system}")
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


@router.get("/api/systems/search")
async def api_search_systems(q: str = Query(..., min_length=2)):
    """Search for solar systems by name"""
    results = route_service.search_systems(q, limit=10)
    return {"query": q, "results": results}


# ============================================================
# Cargo & Logistics
# ============================================================

@router.post("/api/cargo/calculate")
async def api_calculate_cargo(request: CargoCalculateRequest):
    """Calculate total cargo volume for a list of items"""
    volume_info = cargo_service.calculate_cargo_volume(request.items)
    ship_recommendation = cargo_service.recommend_ship(volume_info['total_volume_m3'])
    return {**volume_info, 'ship_recommendation': ship_recommendation}


@router.get("/api/cargo/item/{type_id}")
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
