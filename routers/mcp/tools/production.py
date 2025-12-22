"""
Production MCP Tools
Production planning, cost calculation, chains, economics, and workflow management.
"""

from typing import Dict, Any, List
from ..handlers import api_proxy


# Tool Definitions
TOOLS: List[Dict[str, Any]] = [
    {
        "name": "get_production_cost",
        "description": "Calculate production cost for an item including materials, time, and facility costs. Supports ME/TE bonuses. Returns total cost, material breakdown, and profitability if market price available.",
        "parameters": [
            {
                "name": "type_id",
                "type": "integer",
                "required": True,
                "description": "Item type ID to calculate production cost for"
            },
            {
                "name": "me",
                "type": "integer",
                "required": False,
                "description": "Material Efficiency level (0-10, default: 10)",
                "default": 10
            },
            {
                "name": "te",
                "type": "integer",
                "required": False,
                "description": "Time Efficiency level (0-20, default: 0)",
                "default": 0
            },
            {
                "name": "runs",
                "type": "integer",
                "required": False,
                "description": "Number of production runs (default: 1)",
                "default": 1
            }
        ]
    },
    {
        "name": "simulate_build",
        "description": "Simulate a production build with detailed breakdown. Returns materials needed, production time, facility requirements, and cost analysis.",
        "parameters": [
            {
                "name": "type_id",
                "type": "integer",
                "required": True,
                "description": "Item type ID to simulate"
            },
            {
                "name": "quantity",
                "type": "integer",
                "required": False,
                "description": "Quantity to build (default: 1)",
                "default": 1
            },
            {
                "name": "me",
                "type": "integer",
                "required": False,
                "description": "ME level (default: 10)",
                "default": 10
            }
        ]
    },
    {
        "name": "get_blueprint_info",
        "description": "Get blueprint information including activities, materials, products, and time requirements. Returns all blueprint data from EVE SDE.",
        "parameters": [
            {
                "name": "type_id",
                "type": "integer",
                "required": True,
                "description": "Blueprint type ID"
            }
        ]
    },
    {
        "name": "get_production_chains",
        "description": "Get full production chain tree for an item showing all sub-components and raw materials recursively. Returns hierarchical breakdown of manufacturing dependencies.",
        "parameters": [
            {
                "name": "type_id",
                "type": "integer",
                "required": True,
                "description": "Item type ID to get production chain for"
            },
            {
                "name": "quantity",
                "type": "integer",
                "required": False,
                "description": "Quantity to build (default: 1)",
                "default": 1
            },
            {
                "name": "me",
                "type": "integer",
                "required": False,
                "description": "ME level (default: 10)",
                "default": 10
            }
        ]
    },
    {
        "name": "get_chain_materials",
        "description": "Get all materials needed for production chain including sub-components. Returns flattened list of all materials with quantities.",
        "parameters": [
            {
                "name": "type_id",
                "type": "integer",
                "required": True,
                "description": "Item type ID"
            },
            {
                "name": "quantity",
                "type": "integer",
                "required": False,
                "description": "Quantity (default: 1)",
                "default": 1
            }
        ]
    },
    {
        "name": "get_direct_materials",
        "description": "Get only direct materials for item production (no recursion). Returns first-level materials needed without sub-components.",
        "parameters": [
            {
                "name": "type_id",
                "type": "integer",
                "required": True,
                "description": "Item type ID"
            }
        ]
    },
    {
        "name": "get_economics_opportunities",
        "description": "Find production economic opportunities by analyzing profitable items to manufacture. Returns items with high profit margins considering current market prices.",
        "parameters": [
            {
                "name": "min_profit",
                "type": "integer",
                "required": False,
                "description": "Minimum profit margin in ISK (default: 1000000)",
                "default": 1000000
            },
            {
                "name": "category",
                "type": "string",
                "required": False,
                "description": "Item category filter (e.g., 'ships', 'modules', 'ammunition')"
            }
        ]
    },
    {
        "name": "get_economics_analysis",
        "description": "Get detailed economic analysis for item production including break-even, ROI, and market depth. Returns comprehensive profitability metrics.",
        "parameters": [
            {
                "name": "type_id",
                "type": "integer",
                "required": True,
                "description": "Item type ID to analyze"
            },
            {
                "name": "region_id",
                "type": "integer",
                "required": False,
                "description": "Region for analysis (default: Jita/10000002)",
                "default": 10000002
            }
        ]
    },
    {
        "name": "get_economics_regions",
        "description": "Compare production economics across multiple regions. Returns regional profitability comparison for item production.",
        "parameters": [
            {
                "name": "type_id",
                "type": "integer",
                "required": True,
                "description": "Item type ID"
            },
            {
                "name": "regions",
                "type": "string",
                "required": False,
                "description": "Comma-separated region IDs (default: major hubs)",
                "default": "10000002,10000043,10000030,10000032"
            }
        ]
    },
    {
        "name": "create_workflow_job",
        "description": "Create a production workflow job for tracking manufacturing progress. Returns job ID and initial status.",
        "parameters": [
            {
                "name": "type_id",
                "type": "integer",
                "required": True,
                "description": "Item being produced"
            },
            {
                "name": "quantity",
                "type": "integer",
                "required": True,
                "description": "Quantity to produce"
            },
            {
                "name": "character_id",
                "type": "integer",
                "required": True,
                "description": "Character performing production"
            },
            {
                "name": "notes",
                "type": "string",
                "required": False,
                "description": "Optional notes"
            }
        ]
    },
    {
        "name": "list_workflow_jobs",
        "description": "List production workflow jobs with filtering. Returns active/completed production jobs with status.",
        "parameters": [
            {
                "name": "character_id",
                "type": "integer",
                "required": False,
                "description": "Filter by character"
            },
            {
                "name": "status",
                "type": "string",
                "required": False,
                "description": "Filter by status (pending, in_progress, completed, cancelled)",
                "enum": ["pending", "in_progress", "completed", "cancelled"]
            }
        ]
    },
    {
        "name": "update_workflow_job",
        "description": "Update production workflow job status or details. Allows tracking progress through production stages.",
        "parameters": [
            {
                "name": "job_id",
                "type": "integer",
                "required": True,
                "description": "Job ID to update"
            },
            {
                "name": "status",
                "type": "string",
                "required": False,
                "description": "New status",
                "enum": ["pending", "in_progress", "completed", "cancelled"]
            },
            {
                "name": "notes",
                "type": "string",
                "required": False,
                "description": "Updated notes"
            }
        ]
    },
    {
        "name": "get_production_optimize",
        "description": "Get optimized production plan with regional analysis. Returns best regions for production considering material costs and selling prices.",
        "parameters": [
            {
                "name": "type_id",
                "type": "integer",
                "required": True,
                "description": "Item type ID"
            },
            {
                "name": "me",
                "type": "integer",
                "required": False,
                "description": "ME level (default: 10)",
                "default": 10
            }
        ]
    },
    {
        "name": "batch_production_cost",
        "description": "Calculate production costs for multiple items in batch. Efficient for analyzing multiple manufacturing options.",
        "parameters": [
            {
                "name": "type_ids",
                "type": "string",
                "required": True,
                "description": "Comma-separated type IDs (e.g., '34,35,36')"
            },
            {
                "name": "me",
                "type": "integer",
                "required": False,
                "description": "ME level (default: 10)",
                "default": 10
            }
        ]
    }
]


# Tool Handlers
def handle_get_production_cost(args: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate production cost."""
    type_id = args.get("type_id")
    params = {
        "me": args.get("me", 10),
        "te": args.get("te", 0),
        "runs": args.get("runs", 1)
    }
    return api_proxy.get(f"/api/production/cost/{type_id}", params=params)


def handle_simulate_build(args: Dict[str, Any]) -> Dict[str, Any]:
    """Simulate production build."""
    data = {
        "type_id": args.get("type_id"),
        "quantity": args.get("quantity", 1),
        "me": args.get("me", 10)
    }
    # Try GET first (if endpoint exists), otherwise POST
    type_id = args.get("type_id")
    return api_proxy.get(f"/api/simulation/build/{type_id}", params={"quantity": data["quantity"], "me": data["me"]})


def handle_get_blueprint_info(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get blueprint information."""
    type_id = args.get("type_id")
    # This would need a dedicated endpoint or use production cost endpoint
    return api_proxy.get(f"/api/production/cost/{type_id}")


def handle_get_production_chains(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get production chain tree."""
    type_id = args.get("type_id")
    params = {
        "quantity": args.get("quantity", 1),
        "me": args.get("me", 10)
    }
    return api_proxy.get(f"/api/production/chains/{type_id}", params=params)


def handle_get_chain_materials(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get all chain materials."""
    type_id = args.get("type_id")
    params = {"quantity": args.get("quantity", 1)}
    return api_proxy.get(f"/api/production/chains/{type_id}/materials", params=params)


def handle_get_direct_materials(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get direct materials only."""
    type_id = args.get("type_id")
    return api_proxy.get(f"/api/production/chains/{type_id}/direct")


def handle_get_economics_opportunities(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get economic opportunities."""
    params = {
        "min_profit": args.get("min_profit", 1000000)
    }
    if args.get("category"):
        params["category"] = args.get("category")
    return api_proxy.get("/api/production/economics/opportunities", params=params)


def handle_get_economics_analysis(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get economics analysis for item."""
    type_id = args.get("type_id")
    region_id = args.get("region_id", 10000002)
    return api_proxy.get(f"/api/production/economics/{type_id}", params={"region_id": region_id})


def handle_get_economics_regions(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get regional economics comparison."""
    type_id = args.get("type_id")
    regions = args.get("regions", "10000002,10000043,10000030,10000032")
    return api_proxy.get(f"/api/production/economics/{type_id}/regions", params={"regions": regions})


def handle_create_workflow_job(args: Dict[str, Any]) -> Dict[str, Any]:
    """Create workflow job."""
    data = {
        "type_id": args.get("type_id"),
        "quantity": args.get("quantity"),
        "character_id": args.get("character_id"),
        "notes": args.get("notes", "")
    }
    return api_proxy.post("/api/production/workflow/jobs", data=data)


def handle_list_workflow_jobs(args: Dict[str, Any]) -> Dict[str, Any]:
    """List workflow jobs."""
    params = {}
    if args.get("character_id"):
        params["character_id"] = args.get("character_id")
    if args.get("status"):
        params["status"] = args.get("status")
    return api_proxy.get("/api/production/workflow/jobs", params=params if params else None)


def handle_update_workflow_job(args: Dict[str, Any]) -> Dict[str, Any]:
    """Update workflow job."""
    job_id = args.get("job_id")
    data = {}
    if args.get("status"):
        data["status"] = args.get("status")
    if args.get("notes"):
        data["notes"] = args.get("notes")
    return api_proxy.patch(f"/api/production/workflow/jobs/{job_id}", data=data)


def handle_get_production_optimize(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get optimized production plan."""
    type_id = args.get("type_id")
    me = args.get("me", 10)
    return api_proxy.get(f"/api/production/optimize/{type_id}", params={"me": me})


def handle_batch_production_cost(args: Dict[str, Any]) -> Dict[str, Any]:
    """Batch production cost calculation."""
    type_ids = args.get("type_ids").split(",")
    data = {
        "type_ids": [int(tid.strip()) for tid in type_ids],
        "me": args.get("me", 10)
    }
    return api_proxy.post("/api/production/cost", data=data)


# Handler mapping
HANDLERS = {
    "get_production_cost": handle_get_production_cost,
    "simulate_build": handle_simulate_build,
    "get_blueprint_info": handle_get_blueprint_info,
    "get_production_chains": handle_get_production_chains,
    "get_chain_materials": handle_get_chain_materials,
    "get_direct_materials": handle_get_direct_materials,
    "get_economics_opportunities": handle_get_economics_opportunities,
    "get_economics_analysis": handle_get_economics_analysis,
    "get_economics_regions": handle_get_economics_regions,
    "create_workflow_job": handle_create_workflow_job,
    "list_workflow_jobs": handle_list_workflow_jobs,
    "update_workflow_job": handle_update_workflow_job,
    "get_production_optimize": handle_get_production_optimize,
    "batch_production_cost": handle_batch_production_cost
}
