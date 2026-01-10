"""
Base utilities for zkillboard reports.

Provides shared functionality used by all report types:
- Ship classification
- System information lookups
- Database/Redis access patterns
"""

import json
from datetime import datetime
from typing import Dict, List, Optional
import redis
import aiohttp

from src.database import get_db_connection


# Cache Configuration - All reports generated every 6h by cron, TTL 7h for buffer
REPORT_CACHE_TTL = 7 * 3600  # 7 hours (regenerated every 6h by cron)


# Ship type categories based on groupID from invTypes table
SHIP_CATEGORIES = {
    # Capital Ships
    'titan': [30],
    'supercarrier': [659],
    'carrier': [547],
    'dreadnought': [485],
    'fax': [1538],
    # Subcaps
    'battleship': [27],
    'battlecruiser': [419],
    'cruiser': [26],
    'destroyer': [420],
    'frigate': [25],
    # Special
    'interdictor': [541],
    'heavy_interdictor': [894],
    'logistics': [832],
    'command_ship': [540],
    'strategic_cruiser': [963],
    'tactical_destroyer': [1305],
    'stealth_bomber': [830],
    'force_recon': [833],
    'combat_recon': [906],
    'assault_frigate': [324],
    'heavy_assault_cruiser': [358],
    'industrial': [28, 380, 1202],
    'mining': [463, 543],
    'hauler': [513, 902],
    'shuttle': [31],
    'capsule': [29],
}

# Capital ship group IDs
CAPITAL_GROUPS = [30, 659, 547, 485, 1538, 883, 902]

# Industrial ship group IDs
INDUSTRIAL_GROUPS = [28, 380, 1202, 513, 883, 902, 463, 543, 941]


class ReportsBase:
    """Base class with shared utilities for all report types."""

    def __init__(self, redis_client: redis.Redis, session: Optional[aiohttp.ClientSession] = None):
        """
        Initialize the reports base.

        Args:
            redis_client: Redis client for data access
            session: Optional aiohttp session for API calls
        """
        self.redis_client = redis_client
        self.session = session
        self._system_cache: Dict[int, Dict] = {}
        self._ship_cache: Dict[int, Dict] = {}

    def get_system_security(self, system_id: int) -> float:
        """Get security status for a system."""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        'SELECT security FROM "mapSolarSystems" WHERE "solarSystemID" = %s',
                        (system_id,)
                    )
                    result = cur.fetchone()
                    return round(result[0], 1) if result else 0.0
        except Exception:
            return 0.0

    def get_ship_class(self, ship_type_id: int) -> Optional[str]:
        """Get ship class (frigate, cruiser, etc.) for a ship type ID."""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute('''
                        SELECT g."groupID", g."groupName", c."categoryName"
                        FROM "invTypes" t
                        JOIN "invGroups" g ON t."groupID" = g."groupID"
                        JOIN "invCategories" c ON g."categoryID" = c."categoryID"
                        WHERE t."typeID" = %s
                    ''', (ship_type_id,))
                    result = cur.fetchone()

                    if not result:
                        return None

                    group_id, group_name, category_name = result

                    # Check against known categories
                    for ship_class, group_ids in SHIP_CATEGORIES.items():
                        if group_id in group_ids:
                            return ship_class

                    # Fallback based on category
                    if category_name == 'Ship':
                        return 'other'
                    elif category_name == 'Structure':
                        return 'structure'
                    elif category_name == 'Deployable':
                        return 'deployable'

                    return 'other'
        except Exception:
            return None

    def get_system_location_info(self, system_id: int, cache: Dict = None) -> Dict:
        """Get location info for a system (name, region, security)."""
        if cache and system_id in cache:
            return cache[system_id]

        if system_id in self._system_cache:
            return self._system_cache[system_id]

        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute('''
                        SELECT s."solarSystemName", r."regionName", s.security
                        FROM "mapSolarSystems" s
                        JOIN "mapRegions" r ON s."regionID" = r."regionID"
                        WHERE s."solarSystemID" = %s
                    ''', (system_id,))
                    result = cur.fetchone()

                    if result:
                        info = {
                            'system_name': result[0],
                            'region_name': result[1],
                            'security': round(result[2], 1)
                        }
                        self._system_cache[system_id] = info
                        if cache is not None:
                            cache[system_id] = info
                        return info

        except Exception:
            pass

        return {'system_name': f'System {system_id}', 'region_name': 'Unknown', 'security': 0.0}

    def get_system_locations_batch(self, system_ids: List[int]) -> Dict[int, Dict]:
        """Batch lookup of system location info."""
        if not system_ids:
            return {}

        # Filter already cached
        uncached = [sid for sid in system_ids if sid not in self._system_cache]

        if uncached:
            try:
                with get_db_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute('''
                            SELECT s."solarSystemID", s."solarSystemName", r."regionName", s.security
                            FROM "mapSolarSystems" s
                            JOIN "mapRegions" r ON s."regionID" = r."regionID"
                            WHERE s."solarSystemID" = ANY(%s)
                        ''', (uncached,))

                        for row in cur.fetchall():
                            self._system_cache[row[0]] = {
                                'system_name': row[1],
                                'region_name': row[2],
                                'security': round(row[3], 1)
                            }
            except Exception:
                pass

        return {sid: self._system_cache.get(sid, {
            'system_name': f'System {sid}',
            'region_name': 'Unknown',
            'security': 0.0
        }) for sid in system_ids}

    def get_ship_info_batch(self, ship_type_ids: List[int]) -> Dict[int, Dict]:
        """Batch lookup of ship info (name, group, class)."""
        if not ship_type_ids:
            return {}

        uncached = [sid for sid in ship_type_ids if sid not in self._ship_cache]

        if uncached:
            try:
                with get_db_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute('''
                            SELECT t."typeID", t."typeName", g."groupID", g."groupName"
                            FROM "invTypes" t
                            JOIN "invGroups" g ON t."groupID" = g."groupID"
                            WHERE t."typeID" = ANY(%s)
                        ''', (uncached,))

                        for row in cur.fetchall():
                            self._ship_cache[row[0]] = {
                                'ship_name': row[1],
                                'group_id': row[2],
                                'group_name': row[3],
                                'ship_class': self.get_ship_category(row[2])
                            }
            except Exception:
                pass

        return {sid: self._ship_cache.get(sid, {
            'ship_name': f'Unknown ({sid})',
            'group_id': 0,
            'group_name': 'Unknown',
            'ship_class': 'other'
        }) for sid in ship_type_ids}

    def get_ship_category(self, group_id: int) -> str:
        """Map group ID to ship category."""
        for category, group_ids in SHIP_CATEGORIES.items():
            if group_id in group_ids:
                return category
        return 'other'

    def is_capital_ship(self, group_id: int) -> bool:
        """Check if a group ID is a capital ship."""
        return group_id in CAPITAL_GROUPS

    def is_industrial_ship(self, group_id: int) -> bool:
        """Check if a group ID is an industrial ship."""
        return group_id in INDUSTRIAL_GROUPS
