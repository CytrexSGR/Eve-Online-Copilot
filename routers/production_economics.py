"""
Production Economics Router

API endpoints for production cost analysis, profitability, and opportunities.
"""

from fastapi import APIRouter, HTTPException, Query
from services.production.economics_service import ProductionEconomicsService

router = APIRouter(prefix="/api/production", tags=["production-economics"])
service = ProductionEconomicsService()


@router.get("/economics/opportunities")
async def find_production_opportunities(
    region_id: int = Query(10000002, description="Region ID"),
    min_roi: float = Query(0, description="Minimum ROI percentage"),
    min_profit: float = Query(0, description="Minimum profit in ISK"),
    limit: int = Query(50, ge=1, le=500, description="Max results")
):
    """
    Find profitable manufacturing opportunities

    Args:
        region_id: Region to search in
        min_roi: Minimum ROI percentage
        min_profit: Minimum profit threshold
        limit: Maximum results to return

    Returns:
        List of profitable items sorted by ROI
    """
    result = service.find_opportunities(
        region_id=region_id,
        min_roi=min_roi,
        min_profit=min_profit,
        limit=limit
    )

    return result


@router.get("/economics/{type_id}")
async def get_production_economics(
    type_id: int,
    region_id: int = Query(10000002, description="Region ID (default: The Forge)"),
    me: int = Query(0, ge=0, le=10, description="Material Efficiency (0-10)"),
    te: int = Query(0, ge=0, le=20, description="Time Efficiency (0-20)")
):
    """
    Get complete production economics analysis for an item

    Args:
        type_id: Item type ID
        region_id: Region ID for pricing
        me: Material Efficiency level
        te: Time Efficiency level

    Returns:
        Economics data with costs, market prices, profit, and ROI
    """
    result = service.get_economics(type_id, region_id, me=me, te=te)

    if 'error' in result:
        raise HTTPException(status_code=404, detail=result['error'])

    return result


@router.get("/economics/{type_id}/regions")
async def compare_regions(type_id: int):
    """
    Compare production profitability across multiple regions

    Args:
        type_id: Item type ID

    Returns:
        Multi-region comparison with best region
    """
    result = service.compare_regions(type_id)

    if not result.get('regions'):
        raise HTTPException(
            status_code=404,
            detail="No economics data found for this item in any region"
        )

    return result
