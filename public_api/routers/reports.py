"""
Reports API Router
Serves pre-generated combat intelligence reports from PostgreSQL.
Reports are generated every 6 hours by cron job.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict
from services.stored_reports_service import get_report, get_report_status

router = APIRouter(prefix="/api/reports", tags=["reports"])


def get_stored_report_or_error(report_type: str) -> Dict:
    """Get a stored report or raise HTTPException if not available."""
    report = get_report(report_type)
    if report is None:
        raise HTTPException(
            status_code=503,
            detail=f"Report '{report_type}' not yet generated. Please wait for the next cron cycle."
        )
    return report


@router.get("/battle-24h")
async def get_battle_report() -> Dict:
    """
    24-Hour Battle Report - Pilot Intelligence

    Returns actionable combat intelligence from pilot perspective:
    - Hot zones (top systems by activity)
    - Capital kills summary
    - High-value individual kills with gank detection
    - Danger zones for haulers
    - Ship type breakdown
    - Hourly activity timeline

    Pre-generated every 6 hours.
    """
    return get_stored_report_or_error('pilot_intelligence')


@router.get("/war-profiteering")
async def get_war_profiteering(limit: int = Query(default=20, ge=5, le=50)) -> Dict:
    """
    War Profiteering Daily Digest

    Identifies market opportunities based on destroyed items in combat.
    Shows items with highest market value destroyed in last 24 hours.

    Pre-generated every 6 hours.
    """
    return get_stored_report_or_error('war_profiteering')


@router.get("/alliance-wars")
async def get_alliance_wars() -> Dict:
    """
    Alliance War Tracker

    Tracks active alliance conflicts with kill/death ratios and ISK efficiency.
    Shows top 5 most active alliance wars in last 24 hours.
    Includes auto-detected coalitions based on combat patterns.

    Pre-generated every 6 hours.
    """
    return get_stored_report_or_error('alliance_wars')


@router.get("/alliance-wars/analysis")
async def get_alliance_wars_analysis() -> Dict:
    """
    AI-Powered Alliance Wars Analysis

    Returns an LLM-generated strategic analysis of the current alliance warfare situation.
    Includes a summary and key insights based on the last 24 hours of combat data.

    Pre-generated every 6 hours.
    """
    return get_stored_report_or_error('alliance_wars_analysis')


@router.get("/trade-routes")
async def get_trade_routes(
    limit: int = Query(default=5, ge=1, le=20),
    include_systems: bool = Query(default=True)
) -> Dict:
    """
    Trade Route Danger Map

    Analyzes danger levels along major HighSec trade routes between hubs.
    Shows danger scores per system based on recent kills and gate camps.

    Pre-generated every 6 hours.
    """
    report = get_stored_report_or_error('trade_routes')

    # Apply limit and include_systems filtering
    if report and 'routes' in report:
        routes = report['routes'][:limit]
        if not include_systems:
            # Remove systems array from each route
            for route in routes:
                route.pop('systems', None)
        report = {**report, 'routes': routes}

    return report


@router.get("/war-economy")
async def get_war_economy(limit: int = Query(default=10, ge=5, le=20)) -> Dict:
    """
    War Economy Intelligence Report

    Combines combat data with market intelligence to show:
    - Regional Demand: Where combat is happening → where market demand rises
    - Hot Items: Top destroyed items with market prices
    - Fleet Compositions: Ship class breakdown by region (doctrine detection)
    - Market Opportunities: Items with highest demand from combat

    Pre-generated every 6 hours.
    """
    return get_stored_report_or_error('war_economy')


@router.get("/war-economy/analysis")
async def get_war_economy_analysis_endpoint() -> Dict:
    """
    AI-Powered War Economy Analysis

    Returns an LLM-generated analysis of war economy trends and trading opportunities.
    Includes a summary, insights, recommendations, doctrine alerts, and risk warnings.

    Pre-generated every 6 hours.
    """
    return get_stored_report_or_error('war_economy_analysis')


@router.get("/strategic-briefing")
async def get_strategic_briefing() -> Dict:
    """
    Strategic Intelligence Briefing

    AI-powered strategic analysis of the current state of New Eden.
    Provides executive-level intelligence for alliance leaders and FCs.

    Includes:
    - Power balance assessment
    - Territorial control analysis
    - Capital fleet status
    - Momentum indicators
    - Escalation risk zones
    - Gate camp / chokepoint activity

    Pre-generated every 6 hours.
    """
    return get_stored_report_or_error('strategic_briefing')


@router.get("/status")
async def get_reports_status() -> Dict:
    """
    Reports Generation Status

    Shows when each report was last generated and if any are stale.
    """
    return {
        "reports": get_report_status(),
        "generation_interval": "6 hours"
    }
