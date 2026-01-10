"""
zkillboard Reports Package.

This package provides analytical reports based on killmail data.
It splits the monolithic ZKillboardReportsService into focused modules.

Reports available:
- PilotIntelligence: 24h battle report with global/regional stats
- WarProfiteering: Market opportunities from destroyed items
- AllianceWars: Alliance conflict tracking with kill ratios
- TradeRoutes: Trade route danger analysis
- WarEconomy: Fleet doctrines and regional demand

Usage:
    from services.zkillboard.reports import ZKillboardReportsService

    # Creates the facade service with all report methods
    service = ZKillboardReportsService(redis_client, session)
    report = service.build_pilot_intelligence_report()
"""

# Re-export constants for backwards compatibility
from .base import (
    SHIP_CATEGORIES,
    CAPITAL_GROUPS,
    INDUSTRIAL_GROUPS,
    REPORT_CACHE_TTL,
    ReportsBase
)

# Import mixins
from .kill_analysis import KillAnalysisMixin
from .pilot_intelligence import PilotIntelligenceMixin
from .war_profiteering import WarProfiteeringMixin
from .trade_routes import TradeRoutesMixin
from .war_economy import WarEconomyMixin
from .alliance_wars import AllianceWarsMixin

# Import the original service for backwards compatibility
# This will be replaced with the composed class once all modules are complete
from ..reports_service import ZKillboardReportsService

__all__ = [
    'ZKillboardReportsService',
    'SHIP_CATEGORIES',
    'CAPITAL_GROUPS',
    'INDUSTRIAL_GROUPS',
    'REPORT_CACHE_TTL',
    'ReportsBase',
    'KillAnalysisMixin',
    'PilotIntelligenceMixin',
    'WarProfiteeringMixin',
    'TradeRoutesMixin',
    'WarEconomyMixin',
    'AllianceWarsMixin',
]
