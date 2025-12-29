"""
Production MCP Tools
Production planning, cost calculation, chains, economics, and workflow management.
"""

from typing import Dict, Any, List
from ..handlers import api_proxy
from production_simulator import production_simulator
from services.production.chain_service import ProductionChainService
from services.production.economics_service import ProductionEconomicsService
from services.production.workflow_service import ProductionWorkflowService

# Create service instances
chain_service = ProductionChainService()
economics_service = ProductionEconomicsService()
workflow_service = ProductionWorkflowService()


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
    try:
        type_id = args.get("type_id")
        me = args.get("me", 10)
        te = args.get("te", 0)
        runs = args.get("runs", 1)

        # Call production_simulator directly instead of HTTP request
        result = production_simulator.calculate_financials(
            product_type_id=type_id,
            runs=runs,
            me=me,
            te=te
        )

        return {"content": [{"type": "text", "text": str(result)}]}
    except Exception as e:
        return {"error": f"Failed to calculate production cost: {str(e)}", "isError": True}


def handle_simulate_build(args: Dict[str, Any]) -> Dict[str, Any]:
    """Simulate production build."""
    try:
        type_id = args.get("type_id")
        quantity = args.get("quantity", 1)
        me = args.get("me", 10)

        # Call production_simulator directly instead of HTTP request
        result = production_simulator.simulate_build(
            type_id=type_id,
            quantity=quantity,
            me=me
        )

        return {"content": [{"type": "text", "text": str(result)}]}
    except Exception as e:
        return {"error": f"Failed to simulate build: {str(e)}", "isError": True}


def handle_get_blueprint_info(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get blueprint information."""
    try:
        type_id = args.get("type_id")

        # Call production_simulator directly instead of HTTP request
        bom = production_simulator.get_bom_with_names(type_id, runs=1, me=0)

        result = {
            "type_id": type_id,
            "materials": bom,
            "total_materials": len(bom)
        }

        return {"content": [{"type": "text", "text": str(result)}]}
    except Exception as e:
        return {"error": f"Failed to get blueprint info: {str(e)}", "isError": True}


def handle_get_production_chains(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get production chain tree."""
    try:
        type_id = args.get("type_id")
        quantity = args.get("quantity", 1)
        me = args.get("me", 10)

        # Call chain_service directly instead of HTTP request
        result = chain_service.get_chain_tree(type_id, format='tree')

        return {"content": [{"type": "text", "text": str(result)}]}
    except Exception as e:
        return {"error": f"Failed to get production chains: {str(e)}", "isError": True}


def handle_get_chain_materials(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get all chain materials."""
    try:
        type_id = args.get("type_id")
        quantity = args.get("quantity", 1)

        # Call chain_service directly instead of HTTP request
        result = chain_service.get_materials_list(type_id=type_id, quantity=quantity)

        return {"content": [{"type": "text", "text": str(result)}]}
    except Exception as e:
        return {"error": f"Failed to get chain materials: {str(e)}", "isError": True}


def handle_get_direct_materials(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get direct materials only."""
    try:
        type_id = args.get("type_id")

        # Call chain_service directly instead of HTTP request
        result = chain_service.get_direct_dependencies(type_id)

        return {"content": [{"type": "text", "text": str(result)}]}
    except Exception as e:
        return {"error": f"Failed to get direct materials: {str(e)}", "isError": True}


def handle_get_economics_opportunities(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get economic opportunities."""
    try:
        min_profit = args.get("min_profit", 1000000)
        category = args.get("category")

        # Call economics_service directly instead of HTTP request
        result = economics_service.find_opportunities(
            min_profit=min_profit,
            category=category
        )

        return {"content": [{"type": "text", "text": str(result)}]}
    except Exception as e:
        return {"error": f"Failed to get economic opportunities: {str(e)}", "isError": True}


def handle_get_economics_analysis(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get economics analysis for item."""
    try:
        type_id = args.get("type_id")
        region_id = args.get("region_id", 10000002)

        # Call economics_service directly instead of HTTP request
        result = economics_service.get_economics(
            type_id=type_id,
            region_id=region_id
        )

        return {"content": [{"type": "text", "text": str(result)}]}
    except Exception as e:
        return {"error": f"Failed to get economics analysis: {str(e)}", "isError": True}


def handle_get_economics_regions(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get regional economics comparison."""
    try:
        type_id = args.get("type_id")
        regions = args.get("regions", "10000002,10000043,10000030,10000032")

        # Call economics_service directly instead of HTTP request
        result = economics_service.compare_regions(type_id)

        return {"content": [{"type": "text", "text": str(result)}]}
    except Exception as e:
        return {"error": f"Failed to get regional economics: {str(e)}", "isError": True}


def handle_create_workflow_job(args: Dict[str, Any]) -> Dict[str, Any]:
    """Create workflow job."""
    try:
        type_id = args.get("type_id")
        quantity = args.get("quantity")
        character_id = args.get("character_id")
        notes = args.get("notes", "")

        # Call workflow_service directly instead of HTTP request
        result = workflow_service.create_job(
            type_id=type_id,
            quantity=quantity,
            character_id=character_id,
            notes=notes
        )

        return {"content": [{"type": "text", "text": str(result)}]}
    except Exception as e:
        return {"error": f"Failed to create workflow job: {str(e)}", "isError": True}


def handle_list_workflow_jobs(args: Dict[str, Any]) -> Dict[str, Any]:
    """List workflow jobs."""
    try:
        character_id = args.get("character_id")
        status = args.get("status")

        # Call workflow_service directly instead of HTTP request
        result = workflow_service.get_jobs(
            character_id=character_id,
            status=status
        )

        return {"content": [{"type": "text", "text": str(result)}]}
    except Exception as e:
        return {"error": f"Failed to list workflow jobs: {str(e)}", "isError": True}


def handle_update_workflow_job(args: Dict[str, Any]) -> Dict[str, Any]:
    """Update workflow job."""
    try:
        job_id = args.get("job_id")
        status = args.get("status")
        notes = args.get("notes")

        # Call workflow_service directly instead of HTTP request
        result = workflow_service.update_job(
            job_id=job_id,
            status=status,
            notes=notes
        )

        return {"content": [{"type": "text", "text": str(result)}]}
    except Exception as e:
        return {"error": f"Failed to update workflow job: {str(e)}", "isError": True}


def handle_get_production_optimize(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get optimized production plan."""
    try:
        type_id = args.get("type_id")
        me = args.get("me", 10)

        # Call production_simulator directly instead of HTTP request
        result = production_simulator.quick_profit_check(
            type_id=type_id,
            runs=1,
            me=me
        )

        return {"content": [{"type": "text", "text": str(result)}]}
    except Exception as e:
        return {"error": f"Failed to optimize production: {str(e)}", "isError": True}


def handle_batch_production_cost(args: Dict[str, Any]) -> Dict[str, Any]:
    """Batch production cost calculation."""
    try:
        type_ids_str = args.get("type_ids")
        me = args.get("me", 10)

        # Parse type IDs
        type_ids = [int(tid.strip()) for tid in type_ids_str.split(",")]

        # Call production_simulator for each type_id
        results = []
        for type_id in type_ids:
            try:
                cost = production_simulator.calculate_financials(
                    product_type_id=type_id,
                    runs=1,
                    me=me
                )
                results.append(cost)
            except Exception as e:
                results.append({"type_id": type_id, "error": str(e)})

        return {"content": [{"type": "text", "text": str(results)}]}
    except Exception as e:
        return {"error": f"Failed to batch calculate costs: {str(e)}", "isError": True}


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
