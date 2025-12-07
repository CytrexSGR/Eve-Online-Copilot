"""
Shopping List Router
Endpoints for managing shopping lists and items
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from database import get_db_connection
from psycopg2.extras import RealDictCursor
from shopping_service import shopping_service
from route_service import route_service
from transport_service import transport_service

router = APIRouter(prefix="/api/shopping", tags=["Shopping"])


# Request Models
class ShoppingListCreate(BaseModel):
    name: str
    character_id: Optional[int] = None
    corporation_id: Optional[int] = None
    notes: Optional[str] = None


class ShoppingListUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class ShoppingItemCreate(BaseModel):
    type_id: int
    item_name: str
    quantity: int
    target_region: Optional[str] = None
    target_price: Optional[float] = None
    notes: Optional[str] = None


class ShoppingItemUpdate(BaseModel):
    quantity: Optional[int] = None
    target_region: Optional[str] = None
    target_price: Optional[float] = None
    notes: Optional[str] = None


class ItemRunsUpdate(BaseModel):
    runs: int
    me_level: int = 10


class BuildDecisionUpdate(BaseModel):
    decision: str  # 'buy' or 'build'


class SubProductDecision(BaseModel):
    type_id: int
    item_name: str
    quantity: int
    decision: str  # 'buy' or 'build'


class ApplyMaterialsRequest(BaseModel):
    materials: List[dict]
    sub_product_decisions: List[SubProductDecision]


class CalculateMaterialsRequest(BaseModel):
    product_type_id: int
    runs: int = 1
    me_level: int = 10
    decisions: Optional[dict] = None  # {type_id_str: 'buy'|'build'}


class CompareRegionsRequest(BaseModel):
    items: List[dict]  # [{type_id: int, quantity: int}]


# Shopping List Endpoints
@router.post("/lists")
async def create_shopping_list(request: ShoppingListCreate):
    """Create a new shopping list"""
    return shopping_service.create_list(
        name=request.name,
        character_id=request.character_id,
        corporation_id=request.corporation_id,
        notes=request.notes
    )


@router.get("/lists")
async def get_shopping_lists(
    character_id: Optional[int] = Query(None),
    corporation_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None)
):
    """Get shopping lists with optional filters"""
    return shopping_service.get_lists(character_id, corporation_id, status)


@router.get("/lists/{list_id}")
async def get_shopping_list(list_id: int):
    """Get shopping list with all items"""
    result = shopping_service.get_list_with_items(list_id)
    if not result:
        raise HTTPException(status_code=404, detail="Shopping list not found")
    return result


@router.patch("/lists/{list_id}")
async def update_shopping_list(list_id: int, request: ShoppingListUpdate):
    """Update a shopping list"""
    result = shopping_service.update_list(
        list_id=list_id,
        name=request.name,
        status=request.status,
        notes=request.notes
    )
    if not result:
        raise HTTPException(status_code=404, detail="Shopping list not found")
    return result


@router.delete("/lists/{list_id}")
async def delete_shopping_list(list_id: int):
    """Delete a shopping list"""
    if not shopping_service.delete_list(list_id):
        raise HTTPException(status_code=404, detail="Shopping list not found")
    return {"status": "deleted"}


# Shopping Item Endpoints
@router.post("/lists/{list_id}/items")
async def add_shopping_item(list_id: int, request: ShoppingItemCreate):
    """Add item to shopping list"""
    return shopping_service.add_item(
        list_id=list_id,
        type_id=request.type_id,
        item_name=request.item_name,
        quantity=request.quantity,
        target_region=request.target_region,
        target_price=request.target_price,
        notes=request.notes
    )


@router.patch("/items/{item_id}")
async def update_shopping_item(item_id: int, request: ShoppingItemUpdate):
    """Update a shopping list item"""
    result = shopping_service.update_item(
        item_id=item_id,
        quantity=request.quantity,
        target_region=request.target_region,
        target_price=request.target_price,
        notes=request.notes
    )
    if not result:
        raise HTTPException(status_code=404, detail="Item not found")
    return result


@router.delete("/items/{item_id}")
async def remove_shopping_item(item_id: int):
    """Remove item from shopping list"""
    if not shopping_service.remove_item(item_id):
        raise HTTPException(status_code=404, detail="Item not found")
    return {"status": "removed"}


@router.post("/items/{item_id}/purchased")
async def mark_item_purchased(item_id: int, actual_price: Optional[float] = Query(None)):
    """Mark item as purchased"""
    result = shopping_service.mark_purchased(item_id, actual_price)
    if not result:
        raise HTTPException(status_code=404, detail="Item not found")
    return result


@router.delete("/items/{item_id}/purchased")
async def unmark_item_purchased(item_id: int):
    """Unmark item as purchased"""
    result = shopping_service.unmark_purchased(item_id)
    if not result:
        raise HTTPException(status_code=404, detail="Item not found")
    return result


@router.patch("/items/{item_id}/region")
async def update_item_region(item_id: int, region: str, price: Optional[float] = Query(None)):
    """Update the target region and price for a shopping list item"""
    result = shopping_service.update_item(
        item_id=item_id,
        target_region=region,
        target_price=price
    )
    if not result:
        raise HTTPException(status_code=404, detail="Item not found")
    return result


# Export and Grouping
@router.get("/lists/{list_id}/export")
async def export_shopping_list(list_id: int, region: Optional[str] = Query(None)):
    """Export shopping list in EVE Multibuy format"""
    result = shopping_service.export_multibuy(list_id, region)
    return {"format": "multibuy", "content": result}


@router.get("/lists/{list_id}/by-region")
async def get_shopping_by_region(list_id: int):
    """Get shopping list items grouped by region"""
    return shopping_service.get_by_region(list_id)


@router.post("/lists/{list_id}/add-production/{type_id}")
async def add_production_materials(
    list_id: int,
    type_id: int,
    me: int = Query(10, ge=0, le=10),
    runs: int = Query(1, ge=1, le=1000)
):
    """Add all materials for producing an item to the shopping list"""
    items = shopping_service.add_materials_from_production(list_id, type_id, me, runs)
    if not items:
        raise HTTPException(status_code=404, detail="No blueprint found for this item")
    return {"added_items": len(items), "items": items}


# Regional Comparison
@router.get("/lists/{list_id}/regional-comparison")
async def get_regional_comparison(list_id: int, home_system: str = Query('isikemi')):
    """
    Get shopping list items with prices from all regions for comparison.

    Returns each item with prices, volumes, and totals from all trade hubs,
    allowing users to see where each item is cheapest and select preferred regions.
    Also includes route distances from home system.
    """
    REGION_ID_TO_NAME = {
        10000002: 'the_forge',
        10000043: 'domain',
        10000030: 'heimatar',
        10000032: 'sinq_laison',
        10000042: 'metropolis',
    }

    REGION_DISPLAY_NAMES = {
        'the_forge': 'Jita',
        'domain': 'Amarr',
        'heimatar': 'Rens',
        'sinq_laison': 'Dodixie',
        'metropolis': 'Hek',
    }

    REGION_TO_HUB = {
        'the_forge': 'jita',
        'domain': 'amarr',
        'heimatar': 'rens',
        'sinq_laison': 'dodixie',
        'metropolis': 'hek',
    }

    # Get shopping list with items
    list_data = shopping_service.get_list_with_items(list_id)
    if not list_data:
        raise HTTPException(status_code=404, detail="Shopping list not found")

    # Aggregate items by type_id (combine materials from all products)
    # Only include items that need to be purchased (not products themselves)
    aggregated_items = {}

    def add_to_aggregated(item_data):
        """Helper to add item to aggregated dict"""
        tid = item_data['type_id']
        if tid not in aggregated_items:
            aggregated_items[tid] = {
                'type_id': tid,
                'item_name': item_data['item_name'],
                'quantity': 0,
                'target_region': item_data.get('target_region'),
                'target_price': item_data.get('target_price')
            }
        aggregated_items[tid]['quantity'] += item_data['quantity']

    def process_sub_products_recursive(sub_products):
        """Recursively process sub-products and their materials"""
        for sub in sub_products:
            # If sub-product mode is 'buy', add the sub-product itself to buy list
            if sub.get('mode') == 'buy':
                if not sub.get('is_purchased'):
                    add_to_aggregated(sub)
            # If sub-product mode is 'build', process its materials
            elif sub.get('mode') == 'build':
                # Process direct materials
                for mat in sub.get('materials', []):
                    if not mat.get('is_purchased'):
                        add_to_aggregated(mat)
                # Recursively process nested sub-products
                if sub.get('sub_products'):
                    process_sub_products_recursive(sub.get('sub_products', []))

    # Process standalone items (items not attached to any product)
    for item in list_data.get('standalone_items', []):
        if not item.get('is_purchased'):
            add_to_aggregated(item)

    # Process materials from products (these are what we actually need to buy)
    for product in list_data.get('products', []):
        # Process direct materials of the product
        for mat in product.get('materials', []):
            if not mat.get('is_purchased'):
                add_to_aggregated(mat)

        # Process sub-products recursively
        if product.get('sub_products'):
            process_sub_products_recursive(product.get('sub_products', []))

    items_to_compare = list(aggregated_items.values())

    if not items_to_compare:
        return {
            "list": list_data,
            "items": [],
            "region_totals": {},
            "cheapest_route": []
        }

    # Get all type_ids from the aggregated list
    type_ids = [item['type_id'] for item in items_to_compare]

    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Fetch all regional prices for these items
            cur.execute("""
                SELECT type_id, region_id, lowest_sell, sell_volume
                FROM market_prices
                WHERE type_id = ANY(%s) AND lowest_sell IS NOT NULL
            """, (type_ids,))

            # Build price map
            price_map = {}
            for row in cur.fetchall():
                tid = row['type_id']
                region_name = REGION_ID_TO_NAME.get(row['region_id'])
                if not region_name:
                    continue
                if tid not in price_map:
                    price_map[tid] = {}
                price_map[tid][region_name] = {
                    'price': float(row['lowest_sell']),
                    'volume': row['sell_volume'] or 0
                }

    # Build enriched items with regional data
    enriched_items = []
    region_totals = {r: 0 for r in REGION_ID_TO_NAME.values()}

    for item in items_to_compare:
        type_id = item['type_id']
        quantity = item['quantity']
        prices = price_map.get(type_id, {})

        region_data = {}
        cheapest_region = None
        cheapest_price = float('inf')

        for region in REGION_ID_TO_NAME.values():
            data = prices.get(region, {})
            unit_price = data.get('price')
            volume = data.get('volume', 0)

            if unit_price:
                total = unit_price * quantity
                region_data[region] = {
                    'unit_price': unit_price,
                    'total': total,
                    'volume': volume,
                    'has_stock': volume >= quantity
                }
                region_totals[region] += total

                if unit_price < cheapest_price:
                    cheapest_price = unit_price
                    cheapest_region = region
            else:
                region_data[region] = {
                    'unit_price': None,
                    'total': None,
                    'volume': 0,
                    'has_stock': False
                }

        enriched_items.append({
            'id': item['type_id'],  # Use type_id as id for aggregated items
            'type_id': type_id,
            'item_name': item['item_name'],
            'quantity': quantity,
            'current_region': item.get('target_region'),
            'current_price': item.get('target_price'),
            'regions': region_data,
            'cheapest_region': cheapest_region,
            'cheapest_price': cheapest_price if cheapest_price != float('inf') else None
        })

    # Find optimal route
    optimal_regions = {}
    for item in enriched_items:
        if item['cheapest_region']:
            if item['cheapest_region'] not in optimal_regions:
                optimal_regions[item['cheapest_region']] = []
            optimal_regions[item['cheapest_region']].append({
                'item_name': item['item_name'],
                'quantity': item['quantity'],
                'price': item['cheapest_price'],
                'total': item['cheapest_price'] * item['quantity'] if item['cheapest_price'] else 0
            })

    optimal_total = sum(
        item['cheapest_price'] * item['quantity']
        for item in enriched_items
        if item['cheapest_price']
    )

    # Get route distances from home system
    hub_distances = route_service.get_hub_distances(home_system)
    route_info = {}
    if 'distances' in hub_distances:
        for region in REGION_ID_TO_NAME.values():
            hub_name = REGION_TO_HUB.get(region)
            if hub_name and hub_name in hub_distances['distances']:
                route_info[region] = hub_distances['distances'][hub_name]

    return {
        "list": {
            "id": list_data['id'],
            "name": list_data['name'],
            "status": list_data['status'],
        },
        "items": enriched_items,
        "region_totals": {
            region: {
                'total': total,
                'display_name': REGION_DISPLAY_NAMES[region],
                'jumps': route_info.get(region, {}).get('jumps'),
                'travel_time': route_info.get(region, {}).get('time'),
            }
            for region, total in region_totals.items()
        },
        "optimal_route": {
            "regions": optimal_regions,
            "total_cost": optimal_total,
            "savings_vs_single_region": {
                region: total - optimal_total
                for region, total in region_totals.items()
                if total > 0
            }
        },
        "home_system": home_system,
    }


@router.get("/route")
async def calculate_shopping_route(
    regions: str = Query(..., description="Comma-separated region keys (e.g., 'the_forge,domain')"),
    home_system: str = Query('isikemi', description="Starting system"),
    include_systems: bool = Query(True, description="Include system names for each leg"),
    return_home: bool = Query(True, description="Include return trip to home system")
):
    """
    Calculate optimal travel route through multiple trade hubs.
    Returns the best order to visit hubs to minimize total jumps.
    Optionally includes full system list for each leg and return trip.
    """
    region_list = [r.strip() for r in regions.split(',') if r.strip()]

    if not region_list:
        return {"error": "No regions specified", "total_jumps": 0, "route": []}

    result = route_service.calculate_multi_hub_route(
        home_system, region_list,
        include_systems=include_systems,
        return_home=return_home
    )
    return result


# Order Details Endpoint
@router.get("/orders/{type_id}")
async def get_order_snapshots(
    type_id: int,
    region: str = Query(None, description="Region key (e.g., 'the_forge')"),
):
    """
    Get top order snapshots for an item.
    Returns top 10 sell and buy orders per region.
    """
    REGION_NAME_TO_ID = {
        'the_forge': 10000002,
        'domain': 10000043,
        'heimatar': 10000030,
        'sinq_laison': 10000032,
        'metropolis': 10000042,
    }

    REGION_DISPLAY_NAMES = {
        'the_forge': 'Jita',
        'domain': 'Amarr',
        'heimatar': 'Rens',
        'sinq_laison': 'Dodixie',
        'metropolis': 'Hek',
    }

    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if region:
                region_id = REGION_NAME_TO_ID.get(region)
                if not region_id:
                    raise HTTPException(status_code=400, detail=f"Unknown region: {region}")
                cur.execute("""
                    SELECT type_id, region_id, is_buy_order, price, volume_remain, location_id, issued, rank, updated_at
                    FROM market_order_snapshots
                    WHERE type_id = %s AND region_id = %s
                    ORDER BY is_buy_order, rank
                """, (type_id, region_id))
            else:
                cur.execute("""
                    SELECT type_id, region_id, is_buy_order, price, volume_remain, location_id, issued, rank, updated_at
                    FROM market_order_snapshots
                    WHERE type_id = %s
                    ORDER BY region_id, is_buy_order, rank
                """, (type_id,))

            rows = cur.fetchall()

            # Group by region
            result = {}
            for row in rows:
                rid = row['region_id']
                region_key = next((k for k, v in REGION_NAME_TO_ID.items() if v == rid), str(rid))

                if region_key not in result:
                    result[region_key] = {
                        'display_name': REGION_DISPLAY_NAMES.get(region_key, region_key),
                        'sells': [],
                        'buys': [],
                        'updated_at': None
                    }

                order = {
                    'rank': row['rank'],
                    'price': float(row['price']),
                    'volume': row['volume_remain'],
                    'location_id': row['location_id'],
                    'issued': row['issued'].isoformat() if row['issued'] else None,
                }

                if row['is_buy_order']:
                    result[region_key]['buys'].append(order)
                else:
                    result[region_key]['sells'].append(order)

                if row['updated_at']:
                    result[region_key]['updated_at'] = row['updated_at'].isoformat()

            return {
                'type_id': type_id,
                'regions': result
            }


@router.get("/lists/{list_id}/cargo-summary")
async def get_cargo_summary(list_id: int):
    """Get cargo volume summary for a shopping list"""
    summary = shopping_service.get_cargo_summary(list_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Shopping list not found")
    return summary


@router.get("/lists/{list_id}/transport-options")
async def get_transport_options(
    list_id: int,
    safe_only: bool = Query(True, description="Only show safe (highsec) routes")
):
    """Get transport options for a shopping list"""
    options = transport_service.get_transport_options(list_id, safe_only)
    return options


@router.patch("/items/{item_id}/runs")
async def update_item_runs(item_id: int, request: ItemRunsUpdate):
    """Update runs and ME level for a product item"""
    result = shopping_service.update_item_runs(item_id, request.runs, request.me_level)
    if not result:
        raise HTTPException(status_code=404, detail="Item not found")
    return result


@router.patch("/items/{item_id}/build-decision")
async def update_build_decision(item_id: int, request: BuildDecisionUpdate):
    """Update build decision (buy/build) for a product item"""
    if request.decision not in ('buy', 'build'):
        raise HTTPException(status_code=400, detail="Decision must be 'buy' or 'build'")
    result = shopping_service.update_build_decision(item_id, request.decision)
    if not result:
        raise HTTPException(status_code=404, detail="Item not found")
    return result


# ============================================================
# Material Calculation Endpoints
# ============================================================

@router.post("/items/{item_id}/calculate-materials")
async def calculate_materials(item_id: int):
    """
    Calculate materials for a product item.
    Returns materials and sub-products (items that can also be built).
    User must decide 'buy' or 'build' for sub-products before applying.
    """
    result = shopping_service.calculate_materials(item_id)
    if not result:
        raise HTTPException(status_code=404, detail="Item not found or not a product")
    return result


@router.post("/items/{item_id}/apply-materials")
async def apply_materials(item_id: int, request: ApplyMaterialsRequest):
    """
    Apply calculated materials to shopping list.
    - Deletes existing child materials
    - Adds new materials with parent_item_id
    - For sub-products marked 'build': recursively calculate their materials
    """
    result = shopping_service.apply_materials(
        parent_item_id=item_id,
        materials=request.materials,
        sub_product_decisions=[sp.model_dump() for sp in request.sub_product_decisions]
    )
    if 'error' in result:
        raise HTTPException(status_code=404, detail=result['error'])
    return result


@router.get("/items/{item_id}/with-materials")
async def get_item_with_materials(item_id: int):
    """
    Get a product item with its full materials hierarchy.
    Includes nested sub-products and their materials.
    """
    result = shopping_service.get_product_with_materials(item_id)
    if not result:
        raise HTTPException(status_code=404, detail="Item not found")
    return result


# ============================================================
# Wizard API Endpoints (Step-based Workflow)
# ============================================================

@router.post("/wizard/calculate-materials")
async def wizard_calculate_materials(request: CalculateMaterialsRequest):
    """
    Calculate materials for a product with build/buy decisions.
    Used by the step-based shopping wizard.

    Returns:
    - product: Product info with runs, ME, output
    - sub_components: List of buildable sub-components with decisions
    - shopping_list: Flattened list of items to buy (aggregated)
    - totals: Cost totals by category
    """
    result = shopping_service.calculate_materials_for_wizard(
        product_type_id=request.product_type_id,
        runs=request.runs,
        me_level=request.me_level,
        decisions=request.decisions or {}
    )
    if not result:
        raise HTTPException(status_code=404, detail="Product not found or has no blueprint")
    return result


@router.post("/wizard/compare-regions")
async def wizard_compare_regions(request: CompareRegionsRequest, home_system: str = Query('isikemi')):
    """
    Compare prices across all trade hub regions for a list of items.
    Returns optimal route with savings calculation.
    """
    REGION_ID_TO_NAME = {
        10000002: 'the_forge',
        10000043: 'domain',
        10000030: 'heimatar',
        10000032: 'sinq_laison',
        10000042: 'metropolis',
    }

    REGION_DISPLAY_NAMES = {
        'the_forge': 'Jita',
        'domain': 'Amarr',
        'heimatar': 'Rens',
        'sinq_laison': 'Dodixie',
        'metropolis': 'Hek',
    }

    REGION_TO_HUB = {
        'the_forge': 'jita',
        'domain': 'amarr',
        'heimatar': 'rens',
        'sinq_laison': 'dodixie',
        'metropolis': 'hek',
    }

    if not request.items:
        return {
            "comparison": [],
            "optimal_route": {"stops": [], "total": 0, "jita_only_total": 0, "savings": 0, "savings_percent": 0}
        }

    type_ids = [item['type_id'] for item in request.items]
    quantity_map = {item['type_id']: item['quantity'] for item in request.items}

    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Get item names
            cur.execute('''
                SELECT "typeID", "typeName"
                FROM "invTypes"
                WHERE "typeID" = ANY(%s)
            ''', (type_ids,))
            name_map = {row['typeID']: row['typeName'] for row in cur.fetchall()}

            # Get prices from all regions
            cur.execute('''
                SELECT type_id, region_id, lowest_sell, sell_volume
                FROM market_prices
                WHERE type_id = ANY(%s) AND lowest_sell IS NOT NULL
            ''', (type_ids,))

            price_map = {}
            for row in cur.fetchall():
                tid = row['type_id']
                region_name = REGION_ID_TO_NAME.get(row['region_id'])
                if not region_name:
                    continue
                if tid not in price_map:
                    price_map[tid] = {}
                price_map[tid][region_name] = {
                    'price': float(row['lowest_sell']),
                    'volume': row['sell_volume'] or 0
                }

    # Build comparison list
    comparison = []
    optimal_regions = {}  # region -> [items]
    jita_total = 0

    for item in request.items:
        tid = item['type_id']
        qty = item['quantity']
        prices = price_map.get(tid, {})

        region_prices = {}
        best_region = None
        best_price = float('inf')

        for region in REGION_ID_TO_NAME.values():
            data = prices.get(region, {})
            unit_price = data.get('price')
            if unit_price:
                total = unit_price * qty
                region_prices[region] = {
                    'price': unit_price,
                    'total': total,
                    'volume': data.get('volume', 0)
                }
                if unit_price < best_price:
                    best_price = unit_price
                    best_region = region

        # Track Jita total
        jita_price = prices.get('the_forge', {}).get('price')
        if jita_price:
            jita_total += jita_price * qty

        comparison.append({
            'type_id': tid,
            'name': name_map.get(tid, f'Unknown ({tid})'),
            'quantity': qty,
            'prices': region_prices,
            'best_region': best_region,
            'best_price': best_price if best_price != float('inf') else None
        })

        # Group by best region for optimal route
        if best_region:
            if best_region not in optimal_regions:
                optimal_regions[best_region] = []
            optimal_regions[best_region].append({
                'type_id': tid,
                'name': name_map.get(tid, f'Unknown ({tid})'),
                'quantity': qty,
                'price': best_price,
                'total': best_price * qty
            })

    # Calculate optimal route
    optimal_total = sum(
        item['best_price'] * item['quantity']
        for item in comparison
        if item['best_price']
    )

    # Get route distances
    hub_distances = route_service.get_hub_distances(home_system)
    route_info = {}
    if 'distances' in hub_distances:
        for region in REGION_ID_TO_NAME.values():
            hub_name = REGION_TO_HUB.get(region)
            if hub_name and hub_name in hub_distances['distances']:
                route_info[region] = hub_distances['distances'][hub_name]

    # Build stops list
    stops = []
    for region, items in optimal_regions.items():
        subtotal = sum(item['total'] for item in items)
        stops.append({
            'region': region,
            'display_name': REGION_DISPLAY_NAMES.get(region, region),
            'items': items,
            'item_count': len(items),
            'subtotal': subtotal,
            'jumps': route_info.get(region, {}).get('jumps'),
            'travel_time': route_info.get(region, {}).get('time')
        })

    # Sort stops by subtotal (largest first)
    stops.sort(key=lambda x: x['subtotal'], reverse=True)

    savings = jita_total - optimal_total if jita_total > 0 else 0
    savings_percent = (savings / jita_total * 100) if jita_total > 0 else 0

    return {
        'comparison': comparison,
        'optimal_route': {
            'stops': stops,
            'total': optimal_total,
            'jita_only_total': jita_total,
            'savings': savings,
            'savings_percent': round(savings_percent, 1)
        },
        'home_system': home_system
    }
