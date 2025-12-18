"""
Production Chains Router

API endpoints for production chain queries and material lists.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from services.production.chain_service import ProductionChainService

router = APIRouter(prefix="/api/production", tags=["production-chains"])
service = ProductionChainService()


@router.get("/chains/{type_id}")
async def get_production_chain(
    type_id: int,
    format: str = Query('tree', regex='^(tree|flat)$')
):
    """
    Get complete production chain for an item

    Args:
        type_id: Item type ID
        format: Output format - 'tree' for hierarchical, 'flat' for simple list

    Returns:
        Production chain in requested format
    """
    result = service.get_chain_tree(type_id, format=format)

    if 'error' in result:
        raise HTTPException(status_code=404, detail=result['error'])

    return result


@router.get("/chains/{type_id}/materials")
async def get_materials_list(
    type_id: int,
    me: int = Query(0, ge=0, le=10, description="Material Efficiency (0-10)"),
    runs: int = Query(1, ge=1, description="Number of production runs")
):
    """
    Get flattened material list with ME adjustments

    Args:
        type_id: Item type ID
        me: Material Efficiency level (0-10)
        runs: Number of production runs

    Returns:
        List of materials with base and adjusted quantities
    """
    result = service.get_materials_list(type_id, me=me, runs=runs)

    if 'error' in result:
        raise HTTPException(status_code=404, detail=result['error'])

    return result


@router.get("/chains/{type_id}/direct")
async def get_direct_dependencies(type_id: int):
    """
    Get only direct material dependencies (1 level)

    Args:
        type_id: Item type ID

    Returns:
        List of direct material requirements
    """
    result = service.get_direct_dependencies(type_id)

    if 'error' in result:
        raise HTTPException(status_code=404, detail=result['error'])

    return result
