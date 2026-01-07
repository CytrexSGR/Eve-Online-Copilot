"""
zKillboard Live Service - Backwards Compatibility Wrapper

This module is deprecated. All functionality has been moved to:
- services.zkillboard.live_service
- services.zkillboard.reports_service

For backwards compatibility, we re-export all symbols here.
"""

from services.zkillboard import (
    ZKillboardLiveService,
    ZKillboardReportsService,
    CombinedZKillboardService,
    LiveKillmail,
    zkill_live_service,
    REDIS_HOST,
    REDIS_PORT,
    REDIS_DB,
    REDIS_TTL,
    HOTSPOT_WINDOW_SECONDS,
    HOTSPOT_THRESHOLD_KILLS,
    HOTSPOT_ALERT_COOLDOWN,
    BATTLE_REPORT_CACHE_TTL
)


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
