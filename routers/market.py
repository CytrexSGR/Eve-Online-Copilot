"""
Market router - Market stats, arbitrage, and price comparison endpoints.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from config import REGIONS
from services import find_arbitrage
from database import get_item_info
from esi_client import esi_client
from schemas import ArbitrageRequest

router = APIRouter(tags=["Market"])


@router.get("/api/market/stats/{region_id}/{type_id}")
async def api_market_stats(region_id: int, type_id: int):
    """Get market statistics for an item in a region"""
    stats = esi_client.get_market_stats(region_id, type_id)
    if not stats.get("total_orders"):
        raise HTTPException(status_code=404, detail="No market data found")
    item = get_item_info(type_id)
    if item:
        stats["item_name"] = item["typeName"]
    return stats


@router.get("/api/market/compare/{type_id}")
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


@router.get("/api/market/arbitrage/{type_id}")
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


@router.post("/api/trade/arbitrage")
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


@router.get("/api/trade/arbitrage")
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


@router.post("/api/cache/clear")
async def api_clear_cache():
    """Clear the ESI price cache"""
    esi_client.clear_cache()
    return {"status": "cache cleared"}
