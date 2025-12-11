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
from services.portfolio_service import PortfolioService

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

dashboard_service = DashboardService()
portfolio_service = PortfolioService()


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


@router.get("/characters/summary")
async def get_dashboard_character_summaries() -> List[Dict[str, Any]]:
    """
    Get summary for all configured characters

    Returns:
    - Character name
    - ISK balance
    - Current location
    - Active industry jobs
    - Skill queue status
    """
    # Get character IDs from config or database
    character_ids = [526379435, 1117367444, 110592475]  # Artallus, Cytrex, Cytricia

    return portfolio_service.get_character_summaries(character_ids)


@router.get("/characters/portfolio")
async def get_dashboard_portfolio() -> Dict[str, Any]:
    """
    Get aggregated portfolio data across all characters

    Returns:
    - Total ISK
    - Total asset value
    - Character count
    """
    character_ids = [526379435, 1117367444, 110592475]

    total_isk = portfolio_service.get_total_portfolio_value(character_ids)

    return {
        'total_isk': total_isk,
        'character_count': len(character_ids),
        'characters': character_ids
    }
