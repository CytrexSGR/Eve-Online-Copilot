"""
Dashboard API Router

Provides aggregated data for the EVE Co-Pilot 2.0 dashboard:
- Opportunities from all sources (production, trade, war)
- Character summaries
- War room alerts
"""

from fastapi import APIRouter, Query
from typing import List, Dict, Any
from services.dashboard_service import DashboardService

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

dashboard_service = DashboardService()


@router.get("/opportunities")
async def get_dashboard_opportunities(
    limit: int = Query(10, ge=1, le=50, description="Maximum opportunities to return")
) -> List[Dict[str, Any]]:
    """
    Get top opportunities across all categories

    Returns opportunities from:
    - Manufacturing (Market Hunter)
    - Trading (Arbitrage)
    - Combat Demand (War Room)

    Sorted by user priority: Industrie → Handel → War Room
    """
    return dashboard_service.get_opportunities(limit=limit)


@router.get("/opportunities/{category}")
async def get_dashboard_opportunities_by_category(
    category: str,
    limit: int = Query(10, ge=1, le=50)
) -> List[Dict[str, Any]]:
    """
    Get opportunities for specific category

    Categories: production, trade, war_demand
    """
    all_ops = dashboard_service.get_opportunities(limit=100)
    filtered = [op for op in all_ops if op['category'] == category]
    return filtered[:limit]
