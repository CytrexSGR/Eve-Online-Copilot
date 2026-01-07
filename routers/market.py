"""
Market router - Market stats, arbitrage, and price comparison endpoints.
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional

from config import REGIONS
from src.core.config import get_settings
from src.core.database import DatabasePool
from src.core.exceptions import NotFoundError, ExternalAPIError, EVECopilotError
from src.services.market.service import MarketService
from src.services.market.repository import MarketRepository
from src.esi_client import esi_client  # Use the legacy ESI client instance
from src.legacy_services import find_arbitrage
from src.database import get_item_info
from src.schemas import ArbitrageRequest
from src.route_service import route_service, TRADE_HUB_SYSTEMS
from src.cargo_service import cargo_service

router = APIRouter(tags=["Market"])

# Mapping of region names to their trade hub system IDs (case-insensitive)
REGION_TO_HUB_SYSTEM = {
    "the_forge": TRADE_HUB_SYSTEMS['jita'],
    "The Forge": TRADE_HUB_SYSTEMS['jita'],
    "domain": TRADE_HUB_SYSTEMS['amarr'],
    "Domain": TRADE_HUB_SYSTEMS['amarr'],
    "heimatar": TRADE_HUB_SYSTEMS['rens'],
    "Heimatar": TRADE_HUB_SYSTEMS['rens'],
    "sinq_laison": TRADE_HUB_SYSTEMS['dodixie'],
    "Sinq Laison": TRADE_HUB_SYSTEMS['dodixie'],
    "metropolis": TRADE_HUB_SYSTEMS['hek'],
    "Metropolis": TRADE_HUB_SYSTEMS['hek'],
}

# Ship cargo capacities for calculations
SHIP_CAPACITIES = {
    'industrial': 5000,
    'blockade_runner': 10000,
    'deep_space_transport': 60000,
    'freighter': 1000000,
}


def get_market_service() -> MarketService:
    """Dependency injection for MarketService."""
    settings = get_settings()
    db = DatabasePool(settings)
    from src.integrations.esi.client import ESIClient
    esi = ESIClient(settings)  # New ESI client needs settings
    repository = MarketRepository(db)
    return MarketService(esi, repository)


@router.get("/api/market/stats/{region_id}/{type_id}")
async def api_market_stats(
    region_id: int,
    type_id: int
):
    """Get market statistics for an item in a region"""
    try:
        stats = esi_client.get_market_stats(region_id, type_id)
        if not stats.get("total_orders"):
            raise HTTPException(status_code=404, detail="No market data found")
        item = get_item_info(type_id)
        if item:
            stats["item_name"] = item["typeName"]
        return stats
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ExternalAPIError as e:
        raise HTTPException(status_code=502, detail=f"ESI API error: {e}")
    except EVECopilotError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/market/compare/{type_id}")
async def api_compare_prices(
    type_id: int
):
    """Compare prices for an item across all trade hubs"""
    try:
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
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ExternalAPIError as e:
        raise HTTPException(status_code=502, detail=f"ESI API error: {e}")
    except EVECopilotError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/market/arbitrage/{type_id}")
async def api_find_arbitrage(
    type_id: int,
    min_profit: float = Query(5.0)
):
    """Find arbitrage opportunities for an item between trade hubs"""
    try:
        opportunities = esi_client.find_arbitrage_opportunities(type_id, min_profit)
        item = get_item_info(type_id)
        item_name = item["typeName"] if item else f"Type {type_id}"
        return {
            "type_id": type_id, "item_name": item_name,
            "min_profit_percent": min_profit,
            "opportunities": opportunities,
            "opportunity_count": len(opportunities),
        }
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ExternalAPIError as e:
        raise HTTPException(status_code=502, detail=f"ESI API error: {e}")
    except EVECopilotError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/arbitrage/enhanced/{type_id}")
async def api_enhanced_arbitrage(
    type_id: int,
    min_profit: float = Query(5.0),
    ship_type: str = Query("industrial"),
    broker_fee_percent: float = Query(3.0),
    sales_tax_percent: float = Query(8.0)
):
    """
    Enhanced arbitrage with route planning, cargo calculations, and profitability analysis.

    Integrates RouteService and CargoService for comprehensive trading information.
    """
    try:
        # Get basic arbitrage opportunities
        opportunities = esi_client.find_arbitrage_opportunities(type_id, min_profit)
        item = get_item_info(type_id)
        item_name = item["typeName"] if item else f"Type {type_id}"

        # Get item volume for cargo calculations
        item_volume = cargo_service.get_item_volume(type_id)

        if item_volume is None:
            item_volume = 0

        # Get ship capacity
        ship_capacity = SHIP_CAPACITIES.get(ship_type, 5000)

        # Enhance each opportunity with route and cargo data
        enhanced_opportunities = []
        for opp in opportunities:
            buy_region = opp.get("buy_region")
            sell_region = opp.get("sell_region")

            # Calculate route if both regions are trade hubs
            route_data = None
            if buy_region in REGION_TO_HUB_SYSTEM and sell_region in REGION_TO_HUB_SYSTEM:
                from_system = REGION_TO_HUB_SYSTEM[buy_region]
                to_system = REGION_TO_HUB_SYSTEM[sell_region]

                route = route_service.find_route(from_system, to_system, avoid_lowsec=True)

                if route:
                    # Calculate route safety
                    has_lowsec = any(sys.get('security', 1.0) < 0.45 for sys in route)
                    has_nullsec = any(sys.get('security', 1.0) < 0.0 for sys in route)

                    if has_nullsec:
                        safety = "dangerous"
                    elif has_lowsec:
                        safety = "caution"
                    else:
                        safety = "safe"

                    # Estimate trip time (2 minutes per jump)
                    trip_time_minutes = len(route) * 2

                    route_data = {
                        "jumps": len(route),
                        "safety": safety,
                        "time_minutes": trip_time_minutes,
                        "has_lowsec": has_lowsec,
                        "has_nullsec": has_nullsec,
                    }

            # Calculate cargo data
            cargo_data = None
            if item_volume > 0:
                units_per_trip = int(ship_capacity / item_volume)
                profit_per_unit = opp.get("profit_per_unit", 0)

                if units_per_trip > 0:
                    gross_profit_per_trip = units_per_trip * profit_per_unit
                    isk_per_m3 = profit_per_unit / item_volume if item_volume > 0 else 0

                    cargo_data = {
                        "unit_volume": round(item_volume, 2),
                        "units_per_trip": units_per_trip,
                        "gross_profit_per_trip": round(gross_profit_per_trip, 2),
                        "isk_per_m3": round(isk_per_m3, 2),
                        "ship_type": ship_type,
                        "ship_capacity": ship_capacity,
                        "fill_percent": round((units_per_trip * item_volume / ship_capacity) * 100, 1),
                    }

            # Calculate profitability with fees and taxes
            profitability_data = None
            if cargo_data:
                buy_price = opp.get("buy_price", 0)
                sell_price = opp.get("sell_price", 0)
                units = cargo_data["units_per_trip"]

                # Calculate fees and taxes
                broker_fee_buy = (buy_price * units) * (broker_fee_percent / 100)
                broker_fee_sell = (sell_price * units) * (broker_fee_percent / 100)
                sales_tax = (sell_price * units) * (sales_tax_percent / 100)

                total_fees = broker_fee_buy + broker_fee_sell + sales_tax

                gross_profit = cargo_data["gross_profit_per_trip"]
                net_profit = gross_profit - total_fees

                # Calculate profit per hour if we have route data
                profit_per_hour = None
                if route_data and route_data["time_minutes"] > 0:
                    # Account for round trip time
                    total_trip_time = route_data["time_minutes"] * 2  # Round trip
                    profit_per_hour = (net_profit / total_trip_time) * 60

                profitability_data = {
                    "gross_profit": round(gross_profit, 2),
                    "broker_fees": round(broker_fee_buy + broker_fee_sell, 2),
                    "sales_tax": round(sales_tax, 2),
                    "total_fees": round(total_fees, 2),
                    "net_profit": round(net_profit, 2),
                    "roi_percent": round((net_profit / (buy_price * units)) * 100, 2) if buy_price > 0 else 0,
                    "profit_per_hour": round(profit_per_hour, 2) if profit_per_hour else None,
                }

            # Add enhanced data to opportunity
            enhanced_opp = {**opp}
            if route_data:
                enhanced_opp["route"] = route_data
            if cargo_data:
                enhanced_opp["cargo"] = cargo_data
            if profitability_data:
                enhanced_opp["profitability"] = profitability_data

            enhanced_opportunities.append(enhanced_opp)

        # Sort by ISK per m³ if available, otherwise by profit percent
        enhanced_opportunities.sort(
            key=lambda x: x.get("cargo", {}).get("isk_per_m3", 0) or x.get("profit_percent", 0),
            reverse=True
        )

        return {
            "type_id": type_id,
            "item_name": item_name,
            "item_volume": round(item_volume, 2) if item_volume else None,
            "min_profit_percent": min_profit,
            "ship_type": ship_type,
            "ship_capacity": ship_capacity,
            "opportunities": enhanced_opportunities,
            "opportunity_count": len(enhanced_opportunities),
        }
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ExternalAPIError as e:
        raise HTTPException(status_code=502, detail=f"ESI API error: {e}")
    except EVECopilotError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Enhanced arbitrage failed: {str(e)}")


@router.post("/api/trade/arbitrage")
async def api_arbitrage(request: ArbitrageRequest):
    """Find arbitrage opportunities between two regions"""
    try:
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
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except EVECopilotError as e:
        raise HTTPException(status_code=500, detail=str(e))


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
    try:
        result = find_arbitrage(
            group_name=group_name, group_id=group_id,
            source_region=source_region, target_region=target_region,
            min_margin_percent=min_margin_percent, limit=limit
        )
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except EVECopilotError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/cache/clear")
async def api_clear_cache(
    service: MarketService = Depends(get_market_service)
):
    """Clear the market price cache"""
    try:
        # Clear memory cache
        service._memory_cache.clear()
        service._cache_loaded = False
        return {"status": "cache cleared"}
    except EVECopilotError as e:
        raise HTTPException(status_code=500, detail=str(e))
