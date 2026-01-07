"""
Production router - Manufacturing cost and simulation endpoints.
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional

from config import REGIONS
from src.core.config import get_settings
from src.core.database import DatabasePool
from src.core.exceptions import NotFoundError, EVECopilotError
from src.services.production.service import ProductionService
from src.services.production.repository import ProductionRepository
from src.services.market.service import MarketService
from src.services.market.repository import MarketRepository
from src.integrations.esi.client import ESIClient
from src.services.character.service import CharacterService
from src.services.auth.service import AuthService
from src.services.auth.repository import AuthRepository
from src.legacy_services import calculate_production_cost
from src.database import get_db_connection, get_item_by_name
from src.schemas import ProductionCostRequest, SimulationRequest

router = APIRouter(tags=["Production"])

# Separate router for simulation endpoints (different prefix)
simulation_router = APIRouter(prefix="/api/simulation", tags=["Simulation"])

REGION_ID_TO_NAME = {
    10000002: 'the_forge', 10000043: 'domain',
    10000030: 'heimatar', 10000032: 'sinq_laison', 10000042: 'metropolis',
}


def get_production_service(region_id: int = REGIONS["the_forge"]) -> ProductionService:
    """Dependency injection for ProductionService."""
    settings = get_settings()
    db = DatabasePool(settings)

    # Initialize MarketService
    esi_client = ESIClient(settings)
    market_repository = MarketRepository(db)
    market_service = MarketService(esi_client, market_repository)

    # Initialize ProductionService
    production_repository = ProductionRepository(db)
    return ProductionService(production_repository, market_service, region_id)


def get_character_service() -> CharacterService:
    """Dependency injection for CharacterService."""
    settings = get_settings()
    db = DatabasePool(settings)
    esi_client = ESIClient(settings)

    # Initialize AuthService for token management
    auth_repository = AuthRepository()
    auth_service = AuthService(auth_repository, esi_client, settings)

    return CharacterService(esi_client, auth_service, db)


@router.post("/api/production/cost")
async def api_production_cost(request: ProductionCostRequest):
    """Calculate production cost for an item"""
    try:
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
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except EVECopilotError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/production/cost/{type_id}")
async def api_production_cost_get(
    type_id: int,
    me_level: int = Query(0, ge=0, le=10),
    te_level: int = Query(0, ge=0, le=10),
    region_id: int = Query(REGIONS["the_forge"]),
    use_buy_orders: bool = Query(False)
):
    """GET endpoint for production cost calculation"""
    try:
        result = calculate_production_cost(
            type_id=type_id, me_level=me_level, te_level=te_level,
            region_id=region_id, use_buy_orders=use_buy_orders
        )
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except EVECopilotError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/production/optimize/{type_id}")
async def api_optimize_production(
    type_id: int,
    me: int = Query(10, ge=0, le=10)
):
    """Find optimal regions for production using cached regional prices"""
    try:
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
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except EVECopilotError as e:
        raise HTTPException(status_code=500, detail=str(e))


@simulation_router.post("/build")
async def api_simulate_build(
    request: SimulationRequest,
    production_service: ProductionService = Depends(get_production_service),
    character_service: CharacterService = Depends(get_character_service)
):
    """Simulate a production run with asset matching and profitability analysis"""
    try:
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
            try:
                assets_result = character_service.get_assets(request.character_id)
                # Convert AssetList model to list of dicts for compatibility
                character_assets = [
                    {"type_id": asset.type_id, "quantity": asset.quantity}
                    for asset in assets_result.assets
                ]
            except Exception:
                # If asset fetching fails, continue without assets
                character_assets = None

        result = production_service.simulate_build(
            type_id=type_id, runs=request.runs, me=request.me, te=request.te,
            character_assets=character_assets, region_id=request.region_id
        )

        # Convert Pydantic model to dict for response
        return result.model_dump()

    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except EVECopilotError as e:
        raise HTTPException(status_code=500, detail=str(e))


@simulation_router.get("/build/{type_id}")
async def api_simulate_build_get(
    type_id: int,
    runs: int = Query(1, ge=1, le=1000),
    me: int = Query(0, ge=0, le=10),
    te: int = Query(0, ge=0, le=20),
    character_id: Optional[int] = Query(None),
    region_id: int = Query(REGIONS["the_forge"]),
    production_service: ProductionService = Depends(get_production_service),
    character_service: CharacterService = Depends(get_character_service)
):
    """GET endpoint for production simulation"""
    try:
        character_assets = None
        if character_id:
            try:
                assets_result = character_service.get_assets(character_id)
                # Convert AssetList model to list of dicts for compatibility
                character_assets = [
                    {"type_id": asset.type_id, "quantity": asset.quantity}
                    for asset in assets_result.assets
                ]
            except Exception:
                # If asset fetching fails, continue without assets
                character_assets = None

        result = production_service.simulate_build(
            type_id=type_id, runs=runs, me=me, te=te,
            character_assets=character_assets, region_id=region_id
        )

        # Convert Pydantic model to dict for response
        return result.model_dump()

    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except EVECopilotError as e:
        raise HTTPException(status_code=500, detail=str(e))
