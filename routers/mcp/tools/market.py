"""
Market MCP Tools
Market analysis, arbitrage, and price comparison tools.
"""

from typing import Dict, Any, List
from ..handlers import api_proxy
from esi_client import esi_client
from database import get_item_info


# Tool Definitions
TOOLS: List[Dict[str, Any]] = [
    {
        "name": "search_item",
        "description": "Search for EVE Online items by name. Returns matching items with type_id and name. Use this to find item IDs before other operations. Example: search 'Tritanium' to get type_id 34.",
        "parameters": [
            {
                "name": "query",
                "type": "string",
                "required": True,
                "description": "Item name search query (e.g., 'Tritanium', 'Raven', 'Capital Shield Booster')"
            }
        ]
    },
    {
        "name": "get_item_info",
        "description": "Get detailed information about an item including name, group, volume, and market availability. Returns item metadata from EVE SDE.",
        "parameters": [
            {
                "name": "type_id",
                "type": "integer",
                "required": True,
                "description": "Item type ID (use search_item to find)"
            }
        ]
    },
    {
        "name": "get_market_stats",
        "description": "Get current market statistics for an item in a specific region. Returns lowest sell, highest buy, volume, and spread. Use region_id 10000002 for Jita.",
        "parameters": [
            {
                "name": "region_id",
                "type": "integer",
                "required": True,
                "description": "Region ID (10000002=Jita/The Forge, 10000043=Amarr/Domain, 10000030=Rens/Heimatar, 10000032=Dodixie/Sinq Laison)"
            },
            {
                "name": "type_id",
                "type": "integer",
                "required": True,
                "description": "Item type ID"
            }
        ]
    },
    {
        "name": "compare_region_prices",
        "description": "Compare market prices for an item across multiple regions. Returns best buy/sell prices, spreads, and regional differences. Useful for finding best trading locations.",
        "parameters": [
            {
                "name": "type_id",
                "type": "integer",
                "required": True,
                "description": "Item type ID to compare"
            },
            {
                "name": "regions",
                "type": "string",
                "required": False,
                "description": "Comma-separated region IDs (default: major trade hubs)",
                "default": "10000002,10000043,10000030,10000032"
            }
        ]
    },
    {
        "name": "find_arbitrage",
        "description": "Find arbitrage opportunities for an item (buy low in one region, sell high in another). Returns profitable trade routes with profit margins and volumes.",
        "parameters": [
            {
                "name": "type_id",
                "type": "integer",
                "required": True,
                "description": "Item type ID"
            },
            {
                "name": "min_profit",
                "type": "integer",
                "required": False,
                "description": "Minimum profit per item in ISK (default: 100000)",
                "default": 100000
            }
        ]
    },
    {
        "name": "enhanced_arbitrage_with_routing",
        "description": "Enhanced arbitrage finder with route calculation and cargo optimization. Returns arbitrage opportunities with jump counts, route danger scores, and recommended transport ships.",
        "parameters": [
            {
                "name": "type_id",
                "type": "integer",
                "required": True,
                "description": "Item type ID"
            },
            {
                "name": "max_jumps",
                "type": "integer",
                "required": False,
                "description": "Maximum jumps for route (default: 20)",
                "default": 20
            },
            {
                "name": "min_profit",
                "type": "integer",
                "required": False,
                "description": "Minimum profit per item (default: 100000)",
                "default": 100000
            }
        ]
    },
    {
        "name": "submit_custom_arbitrage",
        "description": "Submit custom arbitrage calculation between specific regions. Allows manual specification of buy/sell regions for arbitrage analysis.",
        "parameters": [
            {
                "name": "type_id",
                "type": "integer",
                "required": True,
                "description": "Item type ID"
            },
            {
                "name": "buy_region_id",
                "type": "integer",
                "required": True,
                "description": "Region to buy from"
            },
            {
                "name": "sell_region_id",
                "type": "integer",
                "required": True,
                "description": "Region to sell to"
            },
            {
                "name": "quantity",
                "type": "integer",
                "required": False,
                "description": "Quantity to trade (default: 1000)",
                "default": 1000
            }
        ]
    },
    {
        "name": "get_saved_arbitrage",
        "description": "Get previously calculated arbitrage results. Returns saved arbitrage opportunities from recent calculations.",
        "parameters": []
    },
    {
        "name": "clear_market_cache",
        "description": "Clear the market price cache to force fresh data retrieval. Use when market data seems stale or after major market events.",
        "parameters": [
            {
                "name": "region_id",
                "type": "integer",
                "required": False,
                "description": "Specific region to clear (default: all regions)"
            }
        ]
    },
    {
        "name": "get_market_orders",
        "description": "Get active market orders for an item in a region with detailed order information. Returns buy/sell orders with prices, volumes, and locations.",
        "parameters": [
            {
                "name": "type_id",
                "type": "integer",
                "required": True,
                "description": "Item type ID"
            },
            {
                "name": "region_id",
                "type": "integer",
                "required": False,
                "description": "Region ID (default: Jita/10000002)",
                "default": 10000002
            }
        ]
    },
    {
        "name": "search_item_groups",
        "description": "Search for item groups/categories by name. Returns market groups with IDs for filtering items by category.",
        "parameters": [
            {
                "name": "query",
                "type": "string",
                "required": True,
                "description": "Group name search query (e.g., 'Ship', 'Module', 'Ore')"
            }
        ]
    },
    {
        "name": "get_all_regions",
        "description": "Get comprehensive list of all regions including wormhole space. Returns full region data with names, IDs, and classifications.",
        "parameters": [
            {
                "name": "include_wh",
                "type": "boolean",
                "required": False,
                "description": "Include wormhole regions (default: false)",
                "default": False
            }
        ]
    }
]


# Tool Handlers
def handle_search_item(args: Dict[str, Any]) -> Dict[str, Any]:
    """Search for items by name."""
    try:
        query = args.get("query")

        # Call database function directly instead of HTTP request
        from database import search_items_by_name
        results = search_items_by_name(query, limit=10)

        return {"content": [{"type": "text", "text": str(results)}]}
    except Exception as e:
        return {"error": f"Failed to search items: {str(e)}", "isError": True}


def handle_get_item_info(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get item details."""
    try:
        type_id = args.get("type_id")

        # Call database function directly
        item = get_item_info(type_id)
        if not item:
            return {"error": f"Item {type_id} not found", "isError": True}

        return {"content": [{"type": "text", "text": str(item)}]}
    except Exception as e:
        return {"error": f"Failed to get item info: {str(e)}", "isError": True}


def handle_get_market_stats(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get market statistics for item in region."""
    try:
        region_id = args.get("region_id")
        type_id = args.get("type_id")

        # Call service directly instead of HTTP request to avoid circular dependency
        stats = esi_client.get_market_stats(region_id, type_id)
        if not stats.get("total_orders"):
            return {"error": "No market data found", "isError": True}

        # Add item name
        item = get_item_info(type_id)
        if item:
            stats["item_name"] = item["typeName"]

        return {"content": [{"type": "text", "text": str(stats)}]}
    except Exception as e:
        return {"error": f"Failed to get market stats: {str(e)}", "isError": True}


def handle_compare_region_prices(args: Dict[str, Any]) -> Dict[str, Any]:
    """Compare prices across regions."""
    try:
        type_id = args.get("type_id")

        # Call esi_client directly instead of HTTP request
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

        result = {
            "type_id": type_id, "item_name": item_name,
            "prices_by_region": prices,
            "best_buy_region": best_buy["region"],
            "best_buy_price": best_buy["price"] if best_buy["price"] != float('inf') else None,
            "best_sell_region": best_sell["region"],
            "best_sell_price": best_sell["price"] if best_sell["price"] > 0 else None,
        }

        return {"content": [{"type": "text", "text": str(result)}]}
    except Exception as e:
        return {"error": f"Failed to compare region prices: {str(e)}", "isError": True}


def handle_find_arbitrage(args: Dict[str, Any]) -> Dict[str, Any]:
    """Find arbitrage opportunities."""
    type_id = args.get("type_id")
    min_profit = args.get("min_profit", 100000)
    return api_proxy.get(f"/api/market/arbitrage/{type_id}", params={"min_profit": min_profit})


def handle_enhanced_arbitrage_with_routing(args: Dict[str, Any]) -> Dict[str, Any]:
    """Enhanced arbitrage with routing."""
    type_id = args.get("type_id")
    params = {
        "max_jumps": args.get("max_jumps", 20),
        "min_profit": args.get("min_profit", 100000)
    }
    return api_proxy.get(f"/api/arbitrage/enhanced/{type_id}", params=params)


def handle_submit_custom_arbitrage(args: Dict[str, Any]) -> Dict[str, Any]:
    """Submit custom arbitrage calculation."""
    data = {
        "type_id": args.get("type_id"),
        "buy_region_id": args.get("buy_region_id"),
        "sell_region_id": args.get("sell_region_id"),
        "quantity": args.get("quantity", 1000)
    }
    return api_proxy.post("/api/trade/arbitrage", data=data)


def handle_get_saved_arbitrage(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get saved arbitrage results."""
    return api_proxy.get("/api/trade/arbitrage")


def handle_clear_market_cache(args: Dict[str, Any]) -> Dict[str, Any]:
    """Clear market cache."""
    region_id = args.get("region_id")
    params = {"region_id": region_id} if region_id else None
    return api_proxy.post("/api/cache/clear", params=params)


def handle_get_market_orders(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get market orders for item."""
    type_id = args.get("type_id")
    region_id = args.get("region_id", 10000002)
    return api_proxy.get(f"/api/shopping/orders/{type_id}", params={"region_id": region_id})


def handle_search_item_groups(args: Dict[str, Any]) -> Dict[str, Any]:
    """Search item groups."""
    query = args.get("query")
    return api_proxy.get("/api/groups/search", params={"q": query})


def handle_get_all_regions(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get all regions."""
    include_wh = args.get("include_wh", False)
    return api_proxy.get("/api/regions", params={"include_wh": include_wh})


# Handler mapping
HANDLERS = {
    "search_item": handle_search_item,
    "get_item_info": handle_get_item_info,
    "get_market_stats": handle_get_market_stats,
    "compare_region_prices": handle_compare_region_prices,
    "find_arbitrage": handle_find_arbitrage,
    "enhanced_arbitrage_with_routing": handle_enhanced_arbitrage_with_routing,
    "submit_custom_arbitrage": handle_submit_custom_arbitrage,
    "get_saved_arbitrage": handle_get_saved_arbitrage,
    "clear_market_cache": handle_clear_market_cache,
    "get_market_orders": handle_get_market_orders,
    "search_item_groups": handle_search_item_groups,
    "get_all_regions": handle_get_all_regions
}
