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


@router.get("/projects")
async def get_active_projects() -> List[Dict[str, Any]]:
    """
    Get active projects (shopping lists) with item counts and progress

    Returns:
    - id: Shopping list ID
    - name: Shopping list name
    - total_items: Total number of items in the list
    - checked_items: Number of purchased items (is_purchased=true)
    - progress: Completion percentage (0-100)
    """
    from database import get_db_connection
    from psycopg2.extras import RealDictCursor

    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Query shopping lists with item counts
            cur.execute('''
                SELECT
                    sl.id,
                    sl.name,
                    COUNT(sli.id) as total_items,
                    COUNT(sli.id) FILTER (WHERE sli.is_purchased = true) as checked_items
                FROM shopping_lists sl
                LEFT JOIN shopping_list_items sli ON sl.id = sli.list_id
                GROUP BY sl.id, sl.name
                ORDER BY sl.updated_at DESC, sl.created_at DESC
            ''')

            projects = []
            for row in cur.fetchall():
                total = int(row['total_items'])
                checked = int(row['checked_items'])

                # Calculate progress percentage
                if total > 0:
                    progress = round((checked / total) * 100, 1)
                else:
                    progress = 0.0

                projects.append({
                    'id': row['id'],
                    'name': row['name'],
                    'total_items': total,
                    'checked_items': checked,
                    'progress': progress
                })

            return projects
