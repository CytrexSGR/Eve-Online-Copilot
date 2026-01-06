"""
zKillboard Services - Modularized Service Layer

Provides:
- Live killmail streaming and hotspot detection
- Combat intelligence reports

Components:
- ZKillboardLiveService: Real-time kill processing and alerts
- ZKillboardReportsService: Analytical reports

For backwards compatibility, a combined service instance is exported.
"""

from .live_service import (
    ZKillboardLiveService,
    LiveKillmail,
    REDIS_HOST,
    REDIS_PORT,
    REDIS_DB,
    REDIS_TTL,
    HOTSPOT_WINDOW_SECONDS,
    HOTSPOT_THRESHOLD_KILLS,
    HOTSPOT_ALERT_COOLDOWN
)
from .reports_service import ZKillboardReportsService, BATTLE_REPORT_CACHE_TTL


class CombinedZKillboardService(ZKillboardLiveService):
    """
    Combined service class providing both live streaming and reports.

    For backwards compatibility with existing code.
    """

    def __init__(self):
        super().__init__()
        # Initialize reports service with same redis client and session
        self._reports_service = ZKillboardReportsService(
            redis_client=self.redis_client,
            session=self.session
        )

    # Delegate report methods to reports service

    def get_war_profiteering_report(self, limit: int = 20):
        """Generate war profiteering report"""
        return self._reports_service.get_war_profiteering_report(limit=limit)

    async def get_alliance_war_tracker(self, limit: int = 5):
        """Track active alliance wars"""
        # Ensure reports service has the latest session
        self._reports_service.session = await self._get_session()
        return await self._reports_service.get_alliance_war_tracker(limit=limit)

    def get_trade_route_danger_map(self):
        """Analyze danger levels on trade routes"""
        return self._reports_service.get_trade_route_danger_map()

    def get_24h_battle_report(self):
        """Generate 24h battle report"""
        return self._reports_service.get_24h_battle_report()


# Singleton instance for backwards compatibility
zkill_live_service = CombinedZKillboardService()


__all__ = [
    'ZKillboardLiveService',
    'ZKillboardReportsService',
    'CombinedZKillboardService',
    'LiveKillmail',
    'zkill_live_service',
    'REDIS_HOST',
    'REDIS_PORT',
    'REDIS_DB',
    'REDIS_TTL',
    'HOTSPOT_WINDOW_SECONDS',
    'HOTSPOT_THRESHOLD_KILLS',
    'HOTSPOT_ALERT_COOLDOWN',
    'BATTLE_REPORT_CACHE_TTL'
]
