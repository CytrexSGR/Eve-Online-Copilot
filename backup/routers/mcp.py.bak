"""
MCP Protocol Router
Model Context Protocol endpoints for Claude Desktop integration
"""

from fastapi import APIRouter
from pydantic import BaseModel
from config import REGIONS
from database import get_item_info, get_item_by_name, get_group_by_name
from esi_client import esi_client
from auth import eve_auth
from character import character_api
from services import calculate_production_cost, find_arbitrage
from production_simulator import production_simulator

router = APIRouter(prefix="/mcp", tags=["MCP Protocol"])


# EVE Online Context for LLM - CRITICAL KNOWLEDGE
EVE_CONTEXT = """
# EVE ONLINE CO-PILOT SYSTEM CONTEXT

## AUTHENTICATED CHARACTERS (use these IDs directly!)
| Name     | character_id | Role                          | Corp Wallet Access |
|----------|--------------|-------------------------------|-------------------|
| Cytrex   | 1117367444   | CEO of Minimal Industries     | YES               |
| Cytricia | 110592475    | Member                        | NO                |
| Artallus | 526379435    | Member                        | NO                |

## CORPORATION
- Name: Minimal Industries
- CEO: Cytrex (character_id: 1117367444)
- Use get_corporation_wallet with character_id=1117367444 for corp finances

## TRADE HUB REGIONS (use these region_id values!)
| Region       | region_id  | Main Hub   | Notes                    |
|--------------|------------|------------|--------------------------|
| The Forge    | 10000002   | Jita 4-4   | LARGEST market, best prices |
| Domain       | 10000043   | Amarr      | Second largest           |
| Heimatar     | 10000030   | Rens       | Minmatar hub             |
| Sinq Laison  | 10000032   | Dodixie    | Gallente hub             |
| Metropolis   | 10000042   | Hek        | Smaller hub              |

## EVE ONLINE INDUSTRY BASICS

### Material Efficiency (ME) - Reduces material costs
- ME 0 = 100% materials needed (default for unresearched BPO/BPC)
- ME 10 = 90% materials needed (maximum research, saves 10%)
- Formula: materials_needed = base_quantity * (1 - ME/100)

### Time Efficiency (TE) - Reduces manufacturing time
- TE 0 = 100% time (default)
- TE 20 = 80% time (maximum research, 20% faster)
- Formula: time_needed = base_time * (1 - TE/100)

### Blueprint Types
- BPO (Blueprint Original): Can be researched, infinite runs
- BPC (Blueprint Copy): Limited runs, cannot be researched further

### Production Profitability
- profit = sell_price - production_cost
- margin_percent = (profit / production_cost) * 100
- Consider: material costs, system cost index, taxes

## COMMON ITEM CATEGORIES (groupID examples)
| Category        | groupID | Examples                      |
|-----------------|---------|-------------------------------|
| Minerals        | 18      | Tritanium, Pyerite, Mexallon  |
| Combat Drones   | 100     | Hobgoblin, Hammerhead, Ogre   |
| Mining Drones   | 101     | Mining Drone I/II             |
| Frigates        | 25      | Rifter, Punisher, Merlin      |
| Cruisers        | 26      | Caracal, Thorax, Maller       |
| Battleships     | 27      | Raven, Megathron, Apocalypse  |
| Ammunition      | 83-90   | Various ammo types            |

## WORKFLOW EXAMPLES

### "Is it profitable to build X?"
1. search_item(q="item name") -> get type_id
2. get_production_cost(type_id=X, me_level=10) -> shows cost vs market price

### "Find trading opportunities"
1. search_group(q="category name") -> get group_id
2. find_arbitrage(group_id=X, min_margin_percent=10) -> profitable items

### "Check character status"
1. get_character_wallet(character_id=1117367444) -> ISK balance
2. get_character_orders(character_id=1117367444) -> active orders
3. get_character_industry(character_id=1117367444) -> running jobs

### "Check corporation finances"
1. get_corporation_wallet(character_id=1117367444) -> all 7 divisions

## MARKET DATA INTERPRETATION
- lowest_sell = cheapest sell order (buy instantly at this price)
- highest_buy = best buy order (sell instantly at this price)
- spread = lowest_sell - highest_buy (profit potential for market making)
- volume = trading activity indicator
"""

# MCP Tool definitions
MCP_TOOLS = [
    {
        "name": "eve_copilot_context",
        "description": "CALL THIS FIRST in every conversation! Returns complete EVE Online context including: all character IDs (Cytrex=1117367444, Cytricia=110592475, Artallus=526379435), region IDs (Jita=10000002, Amarr=10000043), industry formulas (ME/TE), common group IDs, and workflow examples. Essential reference for all EVE operations.",
        "parameters": []
    },
    {
        "name": "search_item",
        "description": "Search EVE items by name to get typeID. Examples: 'Tritanium'->34, 'Hobgoblin'->2454. Use typeID in get_production_cost, get_market_stats.",
        "parameters": [
            {"name": "q", "type": "string", "required": True, "description": "Item name to search (e.g., 'Tritanium', 'Hobgoblin', 'Raven')"}
        ]
    },
    {
        "name": "search_group",
        "description": "Search item categories to get groupID for arbitrage. Examples: 'Minerals'->18, 'Combat Drones'->100, 'Cruisers'->26.",
        "parameters": [
            {"name": "q", "type": "string", "required": True, "description": "Category name (e.g., 'Drones', 'Minerals', 'Frigates')"}
        ]
    },
    {
        "name": "get_item_info",
        "description": "Get item details: name, groupID, volume, base price. Use after search_item to get full info.",
        "parameters": [
            {"name": "type_id", "type": "integer", "required": True, "description": "Item typeID from search_item result"}
        ]
    },
    {
        "name": "get_blueprint_info",
        "description": "Get blueprint manufacturing details: base production time, output quantity, required skills. Essential for production planning.",
        "parameters": [
            {"name": "type_id", "type": "integer", "required": True, "description": "Product typeID (the item you want to build, not the blueprint)"}
        ]
    },
    {
        "name": "simulate_build",
        "description": "FULL PRODUCTION SIMULATION with asset matching! Shows: materials needed, what you have/missing, shopping list with costs, profit/loss analysis, production time. Use character_id to check against their assets. Example: simulate_build(type_id=2454, runs=10, me=10, character_id=1117367444)",
        "parameters": [
            {"name": "type_id", "type": "integer", "required": False, "description": "Product typeID (use search_item to find)"},
            {"name": "blueprint_name", "type": "string", "required": False, "description": "Or search by name (e.g. 'Hobgoblin I')"},
            {"name": "runs", "type": "integer", "required": False, "description": "Number of production runs, default 1"},
            {"name": "me", "type": "integer", "required": False, "description": "Material Efficiency 0-10, default 0"},
            {"name": "te", "type": "integer", "required": False, "description": "Time Efficiency 0-20, default 0"},
            {"name": "character_id", "type": "integer", "required": False, "description": "Character to check assets (Cytrex=1117367444)"},
            {"name": "region_id", "type": "integer", "required": False, "description": "Region for prices (default: 10000002 Jita)"}
        ]
    },
    {
        "name": "get_production_cost",
        "description": "Calculate exact ISK material costs for producing an item, considering ME/TE levels, compared to current market price. Shows if manufacturing is profitable.",
        "parameters": [
            {"name": "type_id", "type": "integer", "required": True, "description": "The typeID of the item to produce"},
            {"name": "me_level", "type": "integer", "required": False, "description": "Material Efficiency level (0-10), default 0"},
            {"name": "te_level", "type": "integer", "required": False, "description": "Time Efficiency level (0-10), default 0"},
            {"name": "region_id", "type": "integer", "required": False, "description": "Region ID for prices (default: 10000002 = Jita)"},
            {"name": "use_buy_orders", "type": "boolean", "required": False, "description": "Use buy prices instead of sell, default false"}
        ]
    },
    {
        "name": "find_arbitrage",
        "description": "Find profitable trading opportunities between two regions. Shows items with highest profit margins.",
        "parameters": [
            {"name": "group_name", "type": "string", "required": False, "description": "Name of item group to search (e.g. 'Combat Drones')"},
            {"name": "group_id", "type": "integer", "required": False, "description": "Direct groupID to search"},
            {"name": "source_region", "type": "integer", "required": False, "description": "Region to buy from (default: 10000002 = Jita)"},
            {"name": "target_region", "type": "integer", "required": False, "description": "Region to sell in (default: 10000043 = Amarr)"},
            {"name": "min_margin_percent", "type": "number", "required": False, "description": "Minimum profit margin %, default 5.0"},
            {"name": "limit", "type": "integer", "required": False, "description": "Max results (1-50), default 5"}
        ]
    },
    {
        "name": "get_market_stats",
        "description": "Get live market statistics for an item in a region including prices, volumes, and order counts.",
        "parameters": [
            {"name": "region_id", "type": "integer", "required": True, "description": "Region ID (10000002=Jita, 10000043=Amarr)"},
            {"name": "type_id", "type": "integer", "required": True, "description": "Item typeID"}
        ]
    },
    {
        "name": "get_regions",
        "description": "Get list of known trade hub region IDs and names.",
        "parameters": []
    },
    {
        "name": "get_character_wallet",
        "description": "Get ISK wallet balance for an EVE character. Use character_id: Cytrex=1117367444, Cytricia=110592475, Artallus=526379435. Returns current ISK balance.",
        "parameters": [
            {"name": "character_id", "type": "integer", "required": True, "description": "Character ID (Cytrex=1117367444, Cytricia=110592475, Artallus=526379435)"}
        ]
    },
    {
        "name": "get_character_assets",
        "description": "Get inventory/hangar contents for an EVE character. Cytrex=1117367444, Cytricia=110592475, Artallus=526379435.",
        "parameters": [
            {"name": "character_id", "type": "integer", "required": True, "description": "Character ID (Cytrex=1117367444, Cytricia=110592475, Artallus=526379435)"},
            {"name": "location_id", "type": "integer", "required": False, "description": "Filter by station/structure ID"}
        ]
    },
    {
        "name": "get_character_skills",
        "description": "Get skill list and total skillpoints for an EVE character. Cytrex=1117367444, Cytricia=110592475, Artallus=526379435.",
        "parameters": [
            {"name": "character_id", "type": "integer", "required": True, "description": "Character ID (Cytrex=1117367444, Cytricia=110592475, Artallus=526379435)"}
        ]
    },
    {
        "name": "get_character_orders",
        "description": "Get active market sell/buy orders for an EVE character. Cytrex=1117367444, Cytricia=110592475, Artallus=526379435.",
        "parameters": [
            {"name": "character_id", "type": "integer", "required": True, "description": "Character ID (Cytrex=1117367444, Cytricia=110592475, Artallus=526379435)"}
        ]
    },
    {
        "name": "get_character_blueprints",
        "description": "Get blueprint library (BPOs and BPCs) for an EVE character. Cytrex=1117367444, Cytricia=110592475, Artallus=526379435.",
        "parameters": [
            {"name": "character_id", "type": "integer", "required": True, "description": "Character ID (Cytrex=1117367444, Cytricia=110592475, Artallus=526379435)"}
        ]
    },
    {
        "name": "get_character_industry",
        "description": "Get manufacturing/research jobs for an EVE character. Cytrex=1117367444, Cytricia=110592475, Artallus=526379435.",
        "parameters": [
            {"name": "character_id", "type": "integer", "required": True, "description": "Character ID (Cytrex=1117367444, Cytricia=110592475, Artallus=526379435)"},
            {"name": "include_completed", "type": "boolean", "required": False, "description": "Include completed jobs, default false"}
        ]
    },
    {
        "name": "get_corporation_wallet",
        "description": "Get Minimal Industries corporation wallet balances (all 7 divisions). ONLY use character_id=1117367444 (Cytrex is CEO with access).",
        "parameters": [
            {"name": "character_id", "type": "integer", "required": True, "description": "Must be 1117367444 (Cytrex - CEO with Director access)"}
        ]
    },
    {
        "name": "get_corporation_info",
        "description": "Get corporation info (name, ticker, member count) for a character's corp. Cytrex=1117367444, Cytricia=110592475, Artallus=526379435.",
        "parameters": [
            {"name": "character_id", "type": "integer", "required": True, "description": "Character ID (Cytrex=1117367444, Cytricia=110592475, Artallus=526379435)"}
        ]
    },
    {
        "name": "get_authenticated_characters",
        "description": "ALWAYS CALL THIS FIRST when user mentions a character name like Cytrex, Cytricia, or Artallus. Returns list of all authenticated EVE Online characters with their character_id numbers needed for other functions. Available characters: Cytrex (ID: 1117367444, CEO), Cytricia (ID: 110592475), Artallus (ID: 526379435).",
        "parameters": []
    }
]


class MCPToolCallRequest(BaseModel):
    name: str
    arguments: dict = {}


@router.get("/tools/list")
async def mcp_tools_list():
    """List all available MCP tools"""
    return {"tools": MCP_TOOLS}


@router.post("/tools/call")
async def mcp_tools_call(request: MCPToolCallRequest):
    """Execute an MCP tool call"""
    import json

    name = request.name
    args = request.arguments

    try:
        result = None

        # Route tool calls to appropriate handlers
        if name == "eve_copilot_context":
            result = {"context": EVE_CONTEXT, "hint": "Use the IDs and workflows above for all operations"}

        elif name == "search_item":
            items = get_item_by_name(args.get("q", ""))
            result = {"query": args.get("q"), "results": items, "count": len(items)}

        elif name == "search_group":
            groups = get_group_by_name(args.get("q", ""))
            result = {"query": args.get("q"), "results": groups, "count": len(groups)}

        elif name == "get_item_info":
            item = get_item_info(args.get("type_id"))
            result = item if item else {"error": "Item not found"}

        elif name == "get_blueprint_info":
            from database import get_blueprint_info as db_get_blueprint_info
            bp_info = db_get_blueprint_info(args.get("type_id"))
            if bp_info:
                base_time = bp_info.get("base_time", 0)
                hours = base_time // 3600
                minutes = (base_time % 3600) // 60
                bp_info["base_time_formatted"] = f"{hours}h {minutes}m"
                result = bp_info
            else:
                result = {"error": "Blueprint not found for this item"}

        elif name == "simulate_build":
            type_id = args.get("type_id")
            if not type_id and args.get("blueprint_name"):
                items = get_item_by_name(args.get("blueprint_name"))
                if items:
                    for item in items:
                        if item["typeName"].lower() == args.get("blueprint_name").lower():
                            type_id = item["typeID"]
                            break
                    if not type_id:
                        type_id = items[0]["typeID"]

            if not type_id:
                result = {"error": "Could not find item. Provide type_id or valid blueprint_name."}
            else:
                character_assets = None
                if args.get("character_id"):
                    assets_result = character_api.get_assets(args.get("character_id"))
                    if isinstance(assets_result, dict) and "error" not in assets_result:
                        character_assets = assets_result.get("assets", [])

                result = production_simulator.simulate_build(
                    type_id=type_id,
                    runs=args.get("runs", 1),
                    me=args.get("me", 0),
                    te=args.get("te", 0),
                    character_assets=character_assets,
                    region_id=args.get("region_id", REGIONS["the_forge"])
                )

        elif name == "get_production_cost":
            result = calculate_production_cost(
                type_id=args.get("type_id"),
                me_level=args.get("me_level", 0),
                te_level=args.get("te_level", 0),
                region_id=args.get("region_id", REGIONS["the_forge"]),
                use_buy_orders=args.get("use_buy_orders", False)
            )

        elif name == "find_arbitrage":
            result = find_arbitrage(
                group_name=args.get("group_name"),
                group_id=args.get("group_id"),
                source_region=args.get("source_region", REGIONS["the_forge"]),
                target_region=args.get("target_region", REGIONS["domain"]),
                min_margin_percent=args.get("min_margin_percent", 5.0),
                limit=args.get("limit", 5)
            )

        elif name == "get_market_stats":
            stats = esi_client.get_market_stats(args.get("region_id"), args.get("type_id"))
            item = get_item_info(args.get("type_id"))
            if item:
                stats["item_name"] = item["typeName"]
            result = stats

        elif name == "get_regions":
            result = REGIONS

        elif name == "get_character_wallet":
            result = character_api.get_wallet_balance(args.get("character_id"))

        elif name == "get_character_assets":
            result = character_api.get_assets(args.get("character_id"), args.get("location_id"))

        elif name == "get_character_skills":
            result = character_api.get_skills(args.get("character_id"))

        elif name == "get_character_orders":
            result = character_api.get_market_orders(args.get("character_id"))

        elif name == "get_character_blueprints":
            result = character_api.get_blueprints(args.get("character_id"))

        elif name == "get_character_industry":
            result = character_api.get_industry_jobs(
                args.get("character_id"),
                args.get("include_completed", False)
            )

        elif name == "get_corporation_wallet":
            result = character_api.get_corporation_wallets(args.get("character_id"))

        elif name == "get_corporation_info":
            char_id = args.get("character_id")
            corp_id = character_api.get_corporation_id(char_id)
            if corp_id:
                result = character_api.get_corporation_info(corp_id)
            else:
                result = {"error": "Corporation not found"}

        elif name == "get_authenticated_characters":
            characters = eve_auth.get_authenticated_characters()
            result = {"authenticated_characters": len(characters), "characters": characters}

        else:
            return {
                "content": [{"type": "text", "text": f"Unknown tool: {name}"}],
                "isError": True
            }

        # Format response for MCP
        return {
            "content": [{"type": "text", "text": json.dumps(result, indent=2, default=str)}],
            "isError": False
        }

    except Exception as e:
        return {
            "content": [{"type": "text", "text": f"Error: {str(e)}"}],
            "isError": True
        }
