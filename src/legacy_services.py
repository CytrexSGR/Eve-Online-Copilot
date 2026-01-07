"""
EVE Co-Pilot Business Logic Services
Core functions for production cost calculation and arbitrage finding
"""

from src.database import (
    get_item_info,
    get_blueprint_materials,
    get_blueprint_info,
    get_items_by_group,
    get_group_by_name
)
from src.esi_client import esi_client
from config import REGIONS


def calculate_production_cost(
    type_id: int,
    me_level: int = 0,
    te_level: int = 0,
    region_id: int = REGIONS["the_forge"],
    use_buy_orders: bool = False
) -> dict:
    """
    Calculate production cost for an item

    Args:
        type_id: The typeID of the item to produce
        me_level: Material Efficiency level (0-10)
        te_level: Time Efficiency level (0-10)
        region_id: Region to fetch prices from
        use_buy_orders: If True, use buy order prices; if False, use sell order prices

    Returns:
        Dictionary with production cost breakdown
    """
    # Get item info
    item = get_item_info(type_id)
    if not item:
        return {"error": f"Item with typeID {type_id} not found"}

    # Get blueprint info
    blueprint = get_blueprint_info(type_id)
    if not blueprint:
        return {"error": f"No blueprint found for {item['typeName']}"}

    # Get materials
    materials = get_blueprint_materials(type_id)
    if not materials:
        return {"error": f"No materials found for {item['typeName']}"}

    # ME bonus calculation (reduces material by 1% per level)
    me_bonus = 1 - (me_level * 0.01)

    # TE bonus calculation (reduces time by 2% per level)
    te_bonus = 1 - (te_level * 0.02)

    # Calculate material costs
    material_breakdown = []
    total_material_cost = 0

    for mat in materials:
        mat_type_id = mat['type_id']
        base_quantity = mat['quantity']

        # Apply ME bonus (minimum 1 unit)
        adjusted_quantity = max(1, int(base_quantity * me_bonus + 0.99))  # Round up

        # Get price from ESI
        if use_buy_orders:
            price = esi_client.get_highest_buy_price(region_id, mat_type_id)
        else:
            price = esi_client.get_lowest_sell_price(region_id, mat_type_id)

        if price is None:
            price = 0  # No market data available

        mat_cost = adjusted_quantity * price

        material_breakdown.append({
            "type_id": mat_type_id,
            "name": mat['material_name'],
            "base_quantity": base_quantity,
            "adjusted_quantity": adjusted_quantity,
            "unit_price": price,
            "total_cost": mat_cost
        })

        total_material_cost += mat_cost

    # Calculate build time
    base_time = blueprint.get('base_time', 0)
    adjusted_time = int(base_time * te_bonus)

    # Get current sell price for profit calculation
    sell_price = esi_client.get_lowest_sell_price(region_id, type_id)
    output_quantity = blueprint.get('output_quantity', 1)

    result = {
        "item": {
            "type_id": type_id,
            "name": item['typeName'],
            "output_quantity": output_quantity
        },
        "blueprint": {
            "type_id": blueprint['blueprint_id'],
            "name": blueprint['blueprint_name']
        },
        "settings": {
            "me_level": me_level,
            "te_level": te_level,
            "region_id": region_id,
            "price_source": "buy_orders" if use_buy_orders else "sell_orders"
        },
        "materials": material_breakdown,
        "summary": {
            "total_material_cost": total_material_cost,
            "cost_per_unit": total_material_cost / output_quantity if output_quantity > 0 else total_material_cost,
            "base_build_time_seconds": base_time,
            "adjusted_build_time_seconds": adjusted_time,
            "build_time_formatted": format_time(adjusted_time)
        }
    }

    # Add profit analysis if sell price is available
    if sell_price:
        total_sell_value = sell_price * output_quantity
        profit = total_sell_value - total_material_cost
        profit_margin = (profit / total_material_cost * 100) if total_material_cost > 0 else 0

        result["profit_analysis"] = {
            "current_sell_price": sell_price,
            "total_sell_value": total_sell_value,
            "profit": profit,
            "profit_margin_percent": profit_margin,
            "profitable": profit > 0
        }

    return result


def find_arbitrage(
    group_name: str = None,
    group_id: int = None,
    source_region: int = REGIONS["the_forge"],
    target_region: int = REGIONS["domain"],
    min_margin_percent: float = 5.0,
    limit: int = 5
) -> dict:
    """
    Find arbitrage opportunities between two regions

    Args:
        group_name: Name of the item group to search
        group_id: Direct groupID to search
        source_region: Region to buy from (default: The Forge/Jita)
        target_region: Region to sell in (default: Domain/Amarr)
        min_margin_percent: Minimum profit margin to consider
        limit: Maximum number of results

    Returns:
        Dictionary with arbitrage opportunities
    """
    # Find group if name provided
    if group_name and not group_id:
        groups = get_group_by_name(group_name)
        if not groups:
            return {"error": f"No group found matching '{group_name}'"}
        # Use first match
        group_id = groups[0]['groupID']
        group_info = groups[0]
    elif group_id:
        group_info = {"groupID": group_id, "groupName": "Unknown"}
    else:
        return {"error": "Either group_name or group_id must be provided"}

    # Get items in group
    items = get_items_by_group(group_id)
    if not items:
        return {"error": f"No items found in group {group_id}"}

    opportunities = []

    for item in items:
        type_id = item['typeID']

        # Get prices in both regions
        source_sell = esi_client.get_lowest_sell_price(source_region, type_id)
        target_sell = esi_client.get_lowest_sell_price(target_region, type_id)

        if source_sell is None or target_sell is None:
            continue

        if source_sell <= 0:
            continue

        # Calculate arbitrage margin
        margin = target_sell - source_sell
        margin_percent = (margin / source_sell) * 100

        if margin_percent >= min_margin_percent:
            opportunities.append({
                "type_id": type_id,
                "name": item['typeName'],
                "volume": item.get('volume', 0),
                "source_price": source_sell,
                "target_price": target_sell,
                "margin_isk": margin,
                "margin_percent": margin_percent,
                "isk_per_m3": margin / item['volume'] if item.get('volume', 0) > 0 else 0
            })

    # Sort by margin percentage and limit results
    opportunities.sort(key=lambda x: x['margin_percent'], reverse=True)
    top_opportunities = opportunities[:limit]

    return {
        "group": {
            "id": group_id,
            "name": group_info.get('groupName', 'Unknown'),
            "category": group_info.get('categoryName', 'Unknown')
        },
        "regions": {
            "source": source_region,
            "target": target_region
        },
        "parameters": {
            "min_margin_percent": min_margin_percent,
            "limit": limit
        },
        "total_items_checked": len(items),
        "opportunities_found": len(opportunities),
        "top_opportunities": top_opportunities
    }


def format_time(seconds: int) -> str:
    """Format seconds into human-readable time"""
    if seconds <= 0:
        return "0s"

    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0:
        parts.append(f"{secs}s")

    return " ".join(parts)
