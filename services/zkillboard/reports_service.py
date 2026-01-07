"""
zKillboard Reports Service - Combat Intelligence Reports

Provides analytical reports based on killmail data stored in Redis.

Reports:
- War Profiteering: Market opportunities from destroyed items
- Alliance War Tracker: Alliance conflicts with kill ratios
- Trade Route Danger Map: Safety analysis of trade routes
- 24h Battle Report: Regional combat statistics
"""

import json
import aiohttp
from datetime import datetime
from typing import Dict, List, Optional
import redis

from src.database import get_db_connection
from src.route_service import RouteService, TRADE_HUB_SYSTEMS


# Battle Report Configuration
BATTLE_REPORT_CACHE_TTL = 600  # 10 minutes cache

# Ship type categories based on groupID from invTypes table
SHIP_CATEGORIES = {
    'titan': [30],  # Titans
    'supercarrier': [659],  # Supercarriers
    'carrier': [547],  # Carriers
    'dreadnought': [485],  # Dreadnoughts
    'force_auxiliary': [1538],  # Force Auxiliaries
    'battleship': [27, 898, 900],  # Battleships, Black Ops, Marauders
    'battlecruiser': [419, 540],  # Battlecruisers, Command Ships
    'cruiser': [26, 358, 894, 906, 963],  # Cruisers, HACs, Recons, etc
    'destroyer': [420, 541],  # Destroyers, Interdictors
    'frigate': [25, 324, 831, 893],  # Frigates, AFs, Interceptors, etc
    'freighter': [513, 902],  # Freighters, Jump Freighters
    'industrial': [28, 463],  # Industrials, Mining Barges
    'exhumer': [543],  # Exhumers
    'capsule': [29]  # Capsules/Pods
}


class ZKillboardReportsService:
    """Service for generating analytical reports from killmail data"""

    def __init__(self, redis_client: redis.Redis, session: Optional[aiohttp.ClientSession] = None):
        """
        Initialize reports service.

        Args:
            redis_client: Redis client for data access
            session: Optional aiohttp session for ESI API calls
        """
        self.redis_client = redis_client
        self.session = session

    def get_system_security(self, system_id: int) -> float:
        """Get security status for a solar system"""
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    'SELECT security FROM "mapSolarSystems" WHERE "solarSystemID" = %s',
                    (system_id,)
                )
                result = cur.fetchone()
                return float(result[0]) if result else 0.0

    def get_ship_class(self, ship_type_id: int) -> Optional[str]:
        """
        Get ship class from ship_type_id using EVE SDE.

        Returns: 'capital', 'battleship', 'cruiser', 'frigate', 'destroyer', 'industrial', or None
        """
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    'SELECT "groupID" FROM "invTypes" WHERE "typeID" = %s',
                    (ship_type_id,)
                )
                result = cur.fetchone()
                if not result:
                    return None

                group_id = result[0]

                # Classify based on group
                if group_id in SHIP_CATEGORIES.get('titan', []) + SHIP_CATEGORIES.get('supercarrier', []) + \
                             SHIP_CATEGORIES.get('carrier', []) + SHIP_CATEGORIES.get('dreadnought', []) + \
                             SHIP_CATEGORIES.get('force_auxiliary', []):
                    return 'capital'
                elif group_id in SHIP_CATEGORIES.get('battleship', []) + SHIP_CATEGORIES.get('battlecruiser', []):
                    return 'battleship'
                elif group_id in SHIP_CATEGORIES.get('cruiser', []):
                    return 'cruiser'
                elif group_id in SHIP_CATEGORIES.get('frigate', []):
                    return 'frigate'
                elif group_id in SHIP_CATEGORIES.get('destroyer', []):
                    return 'destroyer'
                elif group_id in SHIP_CATEGORIES.get('freighter', []) + SHIP_CATEGORIES.get('industrial', []) + \
                             SHIP_CATEGORIES.get('exhumer', []):
                    return 'industrial'
                else:
                    return 'other'

    def get_system_location_info(self, system_id: int) -> Dict:
        """Get full location info for a system"""
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    '''
                    SELECT
                        s."solarSystemName",
                        s.security,
                        c."constellationName",
                        r."regionName"
                    FROM "mapSolarSystems" s
                    JOIN "mapConstellations" c ON s."constellationID" = c."constellationID"
                    JOIN "mapRegions" r ON s."regionID" = r."regionID"
                    WHERE s."solarSystemID" = %s
                    ''',
                    (system_id,)
                )
                result = cur.fetchone()
                if result:
                    return {
                        'system_name': result[0],
                        'security_status': float(result[1]),
                        'constellation_name': result[2],
                        'region_name': result[3]
                    }
                return {}

    def get_ship_category(self, group_id: int) -> str:
        """Determine ship category from group ID"""
        for category, group_ids in SHIP_CATEGORIES.items():
            if group_id in group_ids:
                return category
        return 'other'

    def is_capital_ship(self, group_id: int) -> bool:
        """Check if ship is a capital"""
        capital_categories = ['titan', 'supercarrier', 'carrier', 'dreadnought', 'force_auxiliary']
        return self.get_ship_category(group_id) in capital_categories

    def is_industrial_ship(self, group_id: int) -> bool:
        """Check if ship is industrial/hauler"""
        industrial_categories = ['freighter', 'industrial', 'exhumer']
        return self.get_ship_category(group_id) in industrial_categories

    def extract_capital_kills(self, killmails: List[Dict]) -> Dict:
        """Extract and categorize capital kills"""
        capitals = {
            'titans': {'count': 0, 'total_isk': 0, 'kills': []},
            'supercarriers': {'count': 0, 'total_isk': 0, 'kills': []},
            'carriers': {'count': 0, 'total_isk': 0, 'kills': []},
            'dreadnoughts': {'count': 0, 'total_isk': 0, 'kills': []},
            'force_auxiliaries': {'count': 0, 'total_isk': 0, 'kills': []}
        }

        # Get groupID for all unique ship_type_ids
        ship_type_ids = list(set(km.get('ship_type_id') for km in killmails if km.get('ship_type_id')))
        ship_groups = {}
        ship_names = {}

        if ship_type_ids:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # Batch lookup of groupIDs and ship names
                    cur.execute(
                        'SELECT "typeID", "groupID", "typeName" FROM "invTypes" WHERE "typeID" = ANY(%s)',
                        (ship_type_ids,)
                    )
                    for row in cur.fetchall():
                        ship_groups[row[0]] = row[1]
                        ship_names[row[0]] = row[2]

        for km in killmails:
            ship_type_id = km.get('ship_type_id')
            if not ship_type_id or ship_type_id not in ship_groups:
                continue

            group_id = ship_groups[ship_type_id]
            category = self.get_ship_category(group_id)

            if category not in ['titan', 'supercarrier', 'carrier', 'dreadnought', 'force_auxiliary']:
                continue

            # Get system info
            system_id = km.get('solar_system_id')
            system_info = self.get_system_location_info(system_id) if system_id else {}

            kill_data = {
                'killmail_id': km.get('killmail_id'),
                'ship_name': ship_names.get(ship_type_id, 'Unknown'),
                'victim': km.get('victim_character_id', 0),  # Character ID
                'isk_destroyed': float(km.get('ship_value', 0)),
                'system_name': system_info.get('system_name', 'Unknown'),
                'region_name': system_info.get('region_name', 'Unknown'),
                'security_status': system_info.get('security_status', 0.0),
                'time_utc': km.get('killmail_time', '')
            }

            # Add to appropriate category
            key = category + 's' if category != 'force_auxiliary' else 'force_auxiliaries'
            if key in capitals:
                capitals[key]['count'] += 1
                capitals[key]['total_isk'] += kill_data['isk_destroyed']
                capitals[key]['kills'].append(kill_data)

        # Sort kills by ISK value within each category
        for cat_data in capitals.values():
            cat_data['kills'].sort(key=lambda x: x['isk_destroyed'], reverse=True)

        return capitals

    def extract_high_value_kills(self, killmails: List[Dict], limit: int = 20) -> List[Dict]:
        """Extract top N highest value kills"""
        high_value = []

        # Get groupID for all unique ship_type_ids
        ship_type_ids = list(set(km.get('ship_type_id') for km in killmails if km.get('ship_type_id')))
        ship_groups = {}
        ship_names = {}

        if ship_type_ids:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        'SELECT "typeID", "groupID", "typeName" FROM "invTypes" WHERE "typeID" = ANY(%s)',
                        (ship_type_ids,)
                    )
                    for row in cur.fetchall():
                        ship_groups[row[0]] = row[1]
                        ship_names[row[0]] = row[2]

        for km in killmails:
            system_id = km.get('solar_system_id')
            system_info = self.get_system_location_info(system_id) if system_id else {}

            isk_value = float(km.get('ship_value', 0))
            security = system_info.get('security_status', 0.0)

            ship_type_id = km.get('ship_type_id', 0)
            group_id = ship_groups.get(ship_type_id, 0)

            # Gank detection: high-value kill in HighSec
            is_gank = security >= 0.5 and isk_value > 1_000_000_000  # 1B ISK threshold

            kill_data = {
                'killmail_id': km.get('killmail_id'),
                'isk_destroyed': isk_value,
                'ship_type': self.get_ship_category(group_id) if group_id else 'unknown',
                'ship_name': ship_names.get(ship_type_id, 'Unknown'),
                'victim': km.get('victim_character_id', 0),
                'system_id': system_id,
                'system_name': system_info.get('system_name', 'Unknown'),
                'region_name': system_info.get('region_name', 'Unknown'),
                'security_status': security,
                'is_gank': is_gank,
                'time_utc': km.get('killmail_time', '')
            }

            high_value.append(kill_data)

        # Sort by ISK value and take top N
        high_value.sort(key=lambda x: x['isk_destroyed'], reverse=True)

        # Add rank
        for idx, kill in enumerate(high_value[:limit], 1):
            kill['rank'] = idx

        return high_value[:limit]

    def identify_danger_zones(self, killmails: List[Dict], min_kills: int = 3) -> List[Dict]:
        """Identify systems where industrials/freighters are dying"""
        system_industrial_kills = {}

        # Get groupID for all unique ship_type_ids
        ship_type_ids = list(set(km.get('ship_type_id') for km in killmails if km.get('ship_type_id')))
        ship_groups = {}

        if ship_type_ids:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        'SELECT "typeID", "groupID" FROM "invTypes" WHERE "typeID" = ANY(%s)',
                        (ship_type_ids,)
                    )
                    for row in cur.fetchall():
                        ship_groups[row[0]] = row[1]

        for km in killmails:
            ship_type_id = km.get('ship_type_id')
            if not ship_type_id or ship_type_id not in ship_groups:
                continue

            group_id = ship_groups[ship_type_id]
            if not self.is_industrial_ship(group_id):
                continue

            system_id = km.get('solar_system_id')
            if not system_id:
                continue

            if system_id not in system_industrial_kills:
                system_info = self.get_system_location_info(system_id)
                system_industrial_kills[system_id] = {
                    'system_name': system_info.get('system_name', 'Unknown'),
                    'region_name': system_info.get('region_name', 'Unknown'),
                    'security_status': system_info.get('security_status', 0.0),
                    'industrials_killed': 0,
                    'freighters_killed': 0,
                    'total_value': 0,
                    'kills': []
                }

            isk_value = float(km.get('ship_value', 0))
            system_industrial_kills[system_id]['total_value'] += isk_value
            system_industrial_kills[system_id]['kills'].append(km)

            # Count by type
            ship_cat = self.get_ship_category(group_id)
            if ship_cat == 'freighter':
                system_industrial_kills[system_id]['freighters_killed'] += 1
            else:
                system_industrial_kills[system_id]['industrials_killed'] += 1

        # Filter systems with minimum kills and calculate warning levels
        danger_zones = []
        for sys_id, data in system_industrial_kills.items():
            total_kills = data['industrials_killed'] + data['freighters_killed']
            if total_kills < min_kills:
                continue

            # Warning level based on kills and value
            if total_kills >= 20 or data['total_value'] > 50_000_000_000:
                warning_level = 'EXTREME'
            elif total_kills >= 10 or data['total_value'] > 20_000_000_000:
                warning_level = 'HIGH'
            else:
                warning_level = 'MODERATE'

            data['warning_level'] = warning_level
            # Remove kills array (not needed in output)
            del data['kills']
            danger_zones.append(data)

        # Sort by total value
        danger_zones.sort(key=lambda x: x['total_value'], reverse=True)

        return danger_zones

    def calculate_ship_breakdown(self, killmails: List[Dict]) -> Dict:
        """Calculate kills and ISK by ship category"""
        breakdown = {}

        # Get groupID for all unique ship_type_ids
        ship_type_ids = list(set(km.get('ship_type_id') for km in killmails if km.get('ship_type_id')))
        ship_groups = {}

        if ship_type_ids:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        'SELECT "typeID", "groupID" FROM "invTypes" WHERE "typeID" = ANY(%s)',
                        (ship_type_ids,)
                    )
                    for row in cur.fetchall():
                        ship_groups[row[0]] = row[1]

        for km in killmails:
            ship_type_id = km.get('ship_type_id', 0)
            group_id = ship_groups.get(ship_type_id, 0)
            category = self.get_ship_category(group_id) if group_id else 'other'

            if category not in breakdown:
                breakdown[category] = {
                    'count': 0,
                    'total_isk': 0
                }

            breakdown[category]['count'] += 1
            breakdown[category]['total_isk'] += float(km.get('ship_value', 0))

        # Sort by ISK value
        sorted_breakdown = dict(sorted(
            breakdown.items(),
            key=lambda x: x[1]['total_isk'],
            reverse=True
        ))

        return sorted_breakdown

    def calculate_hourly_timeline(self, killmails: List[Dict]) -> List[Dict]:
        """Calculate kills and ISK per hour (UTC)"""
        hourly_data = {hour: {'hour_utc': hour, 'kills': 0, 'isk_destroyed': 0}
                       for hour in range(24)}

        for km in killmails:
            time_str = km.get('killmail_time', '')
            if not time_str:
                continue

            try:
                # Parse ISO 8601 timestamp
                dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                hour = dt.hour

                hourly_data[hour]['kills'] += 1
                hourly_data[hour]['isk_destroyed'] += float(km.get('ship_value', 0))
            except:
                continue

        # Convert to list and sort by hour
        timeline = list(hourly_data.values())
        timeline.sort(key=lambda x: x['hour_utc'])

        return timeline

    def find_peak_activity(self, timeline: List[Dict]) -> Dict:
        """Find hour with most kills"""
        if not timeline:
            return {'hour_utc': 0, 'kills_per_hour': 0, 'isk_per_hour': 0}

        peak = max(timeline, key=lambda x: x['kills'])
        return {
            'hour_utc': peak['hour_utc'],
            'kills_per_hour': peak['kills'],
            'isk_per_hour': peak['isk_destroyed']
        }

    def extract_hot_zones(self, killmails: List[Dict], limit: int = 15) -> List[Dict]:
        """Extract top N most active systems"""
        system_activity = {}

        # Get groupID and ship names for all unique ship_type_ids
        ship_type_ids = list(set(km.get('ship_type_id') for km in killmails if km.get('ship_type_id')))
        ship_names = {}

        if ship_type_ids:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        'SELECT "typeID", "typeName" FROM "invTypes" WHERE "typeID" = ANY(%s)',
                        (ship_type_ids,)
                    )
                    for row in cur.fetchall():
                        ship_names[row[0]] = row[1]

        for km in killmails:
            system_id = km.get('solar_system_id')
            if not system_id:
                continue

            if system_id not in system_activity:
                system_info = self.get_system_location_info(system_id)
                system_activity[system_id] = {
                    'system_id': system_id,
                    'system_name': system_info.get('system_name', 'Unknown'),
                    'region_name': system_info.get('region_name', 'Unknown'),
                    'constellation_name': system_info.get('constellation_name', 'Unknown'),
                    'security_status': system_info.get('security_status', 0.0),
                    'kills': 0,
                    'total_isk_destroyed': 0,
                    'ship_types': {},
                    'flags': []
                }

            system_activity[system_id]['kills'] += 1
            system_activity[system_id]['total_isk_destroyed'] += float(km.get('ship_value', 0))

            # Track ship types
            ship_type_id = km.get('ship_type_id')
            ship_name = ship_names.get(ship_type_id, 'Unknown')
            if ship_name not in system_activity[system_id]['ship_types']:
                system_activity[system_id]['ship_types'][ship_name] = 0
            system_activity[system_id]['ship_types'][ship_name] += 1

        # Determine dominant ship type and flags for each system
        for sys_data in system_activity.values():
            if sys_data['ship_types']:
                dominant = max(sys_data['ship_types'].items(), key=lambda x: x[1])
                sys_data['dominant_ship_type'] = dominant[0]
            else:
                sys_data['dominant_ship_type'] = 'Unknown'

            # Add flags
            if sys_data['kills'] >= 20:
                sys_data['flags'].append('high_activity')
            if sys_data['total_isk_destroyed'] > 10_000_000_000:  # 10B
                sys_data['flags'].append('high_value')

            # Remove ship_types dict (not needed in output)
            del sys_data['ship_types']

        # Sort by kills and take top N
        hot_zones = sorted(system_activity.values(), key=lambda x: x['kills'], reverse=True)[:limit]

        return hot_zones

    def build_pilot_intelligence_report(self) -> Dict:
        """Build complete pilot intelligence battle report"""
        # Check cache first
        cache_key = "report:pilot_intelligence:24h"
        cached_report = self.redis_client.get(cache_key)
        if cached_report:
            print(f"[CACHE HIT] Returning cached pilot intelligence report")
            return json.loads(cached_report)

        print(f"[CACHE MISS] Building pilot intelligence report from scratch...")

        # Get all killmails from Redis
        kill_ids = list(self.redis_client.scan_iter("kill:id:*"))
        print(f"[Performance] Found {len(kill_ids)} killmail keys")

        killmails = []
        for kill_id_key in kill_ids:
            kill_data = self.redis_client.get(kill_id_key)
            if kill_data:
                killmails.append(json.loads(kill_data))

        print(f"[Performance] Loaded {len(killmails)} killmails")

        if not killmails:
            return self._empty_pilot_report()

        # Calculate all intelligence sections
        timeline = self.calculate_hourly_timeline(killmails)
        peak_activity = self.find_peak_activity(timeline)
        hot_zones = self.extract_hot_zones(killmails, limit=15)
        capital_kills = self.extract_capital_kills(killmails)
        high_value_kills = self.extract_high_value_kills(killmails, limit=20)
        danger_zones = self.identify_danger_zones(killmails, min_kills=3)
        ship_breakdown = self.calculate_ship_breakdown(killmails)

        # Calculate global stats
        total_kills = len(killmails)
        total_isk = sum(float(km.get('ship_value', 0)) for km in killmails)

        # Build region summary for backwards compatibility
        region_summary = self._build_region_summary_compat(killmails)

        report = {
            'period': '24h',
            'global': {
                'total_kills': total_kills,
                'total_isk_destroyed': total_isk,
                'peak_hour_utc': peak_activity['hour_utc'],
                'peak_kills_per_hour': peak_activity['kills_per_hour']
            },
            'hot_zones': hot_zones,
            'capital_kills': capital_kills,
            'high_value_kills': high_value_kills,
            'danger_zones': danger_zones,
            'ship_breakdown': ship_breakdown,
            'timeline': timeline,
            'regions': region_summary
        }

        # Cache the report for 10 minutes (600 seconds)
        cache_key = "report:pilot_intelligence:24h"
        self.redis_client.setex(cache_key, BATTLE_REPORT_CACHE_TTL, json.dumps(report))
        print(f"[CACHE] Cached pilot intelligence report for {BATTLE_REPORT_CACHE_TTL}s")

        return report

    def _empty_pilot_report(self) -> Dict:
        """Return empty report structure"""
        return {
            'period': '24h',
            'global': {'total_kills': 0, 'total_isk_destroyed': 0, 'peak_hour_utc': 0, 'peak_kills_per_hour': 0},
            'hot_zones': [],
            'capital_kills': {
                'titans': {'count': 0, 'total_isk': 0, 'kills': []},
                'supercarriers': {'count': 0, 'total_isk': 0, 'kills': []},
                'carriers': {'count': 0, 'total_isk': 0, 'kills': []},
                'dreadnoughts': {'count': 0, 'total_isk': 0, 'kills': []},
                'force_auxiliaries': {'count': 0, 'total_isk': 0, 'kills': []}
            },
            'high_value_kills': [],
            'danger_zones': [],
            'ship_breakdown': {},
            'timeline': [{'hour_utc': h, 'kills': 0, 'isk_destroyed': 0} for h in range(24)],
            'regions': []
        }

    def _build_region_summary_compat(self, killmails: List[Dict]) -> List[Dict]:
        """Build simplified region summary for backwards compatibility"""
        # Group kills by region
        region_data = {}
        for km in killmails:
            region_id = km.get('region_id')
            if not region_id:
                continue

            if region_id not in region_data:
                region_data[region_id] = {
                    'region_id': region_id,
                    'kills': 0,
                    'total_isk_destroyed': 0
                }

            region_data[region_id]['kills'] += 1
            region_data[region_id]['total_isk_destroyed'] += float(km.get('ship_value', 0))

        # Get region names
        if region_data:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    region_ids = list(region_data.keys())
                    cur.execute(
                        'SELECT "regionID", "regionName" FROM "mapRegions" WHERE "regionID" = ANY(%s)',
                        (region_ids,)
                    )
                    for row in cur.fetchall():
                        if row[0] in region_data:
                            region_data[row[0]]['region_name'] = row[1]

        # Convert to list and sort
        regions = list(region_data.values())
        regions.sort(key=lambda x: x['kills'], reverse=True)

        return regions

    def get_war_profiteering_report(self, limit: int = 20) -> Dict:
        """
        Generate war profiteering report with market opportunities.

        Analyzes destroyed items and calculates market opportunity scores
        based on quantity destroyed and current market prices.

        Args:
            limit: Number of items to return

        Returns:
            Dict with top destroyed items and their market opportunity scores
        """
        # Get destroyed items from Redis
        items = []
        for key in self.redis_client.scan_iter("kill:item:*:destroyed"):
            parts = key.split(":")
            if len(parts) == 4:
                item_type_id = int(parts[2])
                quantity = int(self.redis_client.get(key) or 0)

                if quantity > 0:  # Only items with actual destruction
                    items.append({
                        "item_type_id": item_type_id,
                        "quantity_destroyed": quantity
                    })

        if not items:
            return {"items": [], "total_items": 0, "total_opportunity_value": 0}

        # Batch query for all items with price fallback logic
        item_data = []
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Create temporary table with destroyed items for efficient JOIN
                item_ids = [item['item_type_id'] for item in items]
                quantities = {item['item_type_id']: item['quantity_destroyed'] for item in items}

                # Batch query with price fallback: Jita → Adjusted → Base
                cur.execute(
                    '''SELECT
                        t."typeID",
                        t."typeName",
                        t."groupID",
                        g."categoryID",
                        COALESCE(mp.lowest_sell, mpc.adjusted_price, t."basePrice"::double precision, 0) as final_price
                       FROM "invTypes" t
                       JOIN "invGroups" g ON t."groupID" = g."groupID"
                       LEFT JOIN market_prices mp ON t."typeID" = mp.type_id AND mp.region_id = 10000002
                       LEFT JOIN market_prices_cache mpc ON t."typeID" = mpc.type_id
                       WHERE t."typeID" = ANY(%s)''',
                    (item_ids,)
                )

                for row in cur.fetchall():
                    item_id = row[0]
                    item_name = row[1]
                    group_id = row[2]
                    category_id = row[3]
                    market_price = float(row[4]) if row[4] else 0
                    quantity = quantities[item_id]

                    # Exclude raw materials, ore, ice, PI materials
                    # Category 4 = Material, 25 = Asteroid, 43 = Planetary Commodities
                    if category_id in (4, 25, 43):
                        continue

                    # Skip items without valid market price
                    if market_price <= 0:
                        continue

                    # Calculate opportunity score
                    opportunity_value = quantity * market_price

                    item_data.append({
                        "item_type_id": item_id,
                        "item_name": item_name,
                        "group_id": group_id,
                        "quantity_destroyed": quantity,
                        "market_price": market_price,
                        "opportunity_value": opportunity_value
                    })

        # Sort by opportunity value (highest opportunity first)
        item_data.sort(key=lambda x: x['opportunity_value'], reverse=True)

        # Calculate totals
        total_opportunity = sum(item['opportunity_value'] for item in item_data[:limit])

        return {
            "items": item_data[:limit],
            "total_items": len(item_data),
            "total_opportunity_value": total_opportunity,
            "period": "24h"
        }

    async def get_alliance_war_tracker(self, limit: int = 5) -> Dict:
        """
        Track active alliance wars with kill/death ratios and ISK efficiency.

        Identifies top alliance conflicts based on mutual kills and analyzes
        who is winning economically and numerically.

        Args:
            limit: Number of wars to return

        Returns:
            Dict with top alliance wars and their statistics
        """
        # Get all kills with alliance data
        kill_ids = list(self.redis_client.scan_iter("kill:id:*"))

        kills = []
        for kill_id_key in kill_ids[:1000]:  # Sample last 1000 kills
            kill_data = self.redis_client.get(kill_id_key)
            if kill_data:
                kill = json.loads(kill_data)
                if kill.get('victim_alliance_id') and kill.get('attacker_alliances'):
                    kills.append(kill)

        if not kills:
            return {"wars": [], "total_wars": 0}

        # Build alliance vs alliance conflict matrix
        conflicts = {}  # (alliance_a, alliance_b) -> {kills, isk, systems, ship_classes, timeline, etc}

        for kill in kills:
            victim_alliance = kill.get('victim_alliance_id')
            attacker_alliances = kill.get('attacker_alliances', [])
            ship_value = kill.get('ship_value', 0)
            ship_type_id = kill.get('ship_type_id')
            system_id = kill.get('solar_system_id')
            killmail_time = kill.get('killmail_time')

            for attacker_alliance in set(attacker_alliances):  # Unique attackers per kill
                if attacker_alliance and victim_alliance and attacker_alliance != victim_alliance:
                    # Create conflict key (sorted to ensure A vs B = B vs A)
                    alliance_pair = tuple(sorted([attacker_alliance, victim_alliance]))

                    if alliance_pair not in conflicts:
                        conflicts[alliance_pair] = {
                            "alliance_a": alliance_pair[0],
                            "alliance_b": alliance_pair[1],
                            "kills_by_a": 0,
                            "kills_by_b": 0,
                            "isk_by_a": 0,
                            "isk_by_b": 0,
                            "systems": {},  # system_id -> kill count
                            "ship_classes_a": {"capital": 0, "battleship": 0, "cruiser": 0, "frigate": 0, "destroyer": 0, "industrial": 0, "other": 0},
                            "ship_classes_b": {"capital": 0, "battleship": 0, "cruiser": 0, "frigate": 0, "destroyer": 0, "industrial": 0, "other": 0},
                            "hourly_activity": {},  # hour (0-23) -> kill count
                            "biggest_loss_a": {"ship_type_id": None, "value": 0},
                            "biggest_loss_b": {"ship_type_id": None, "value": 0},
                            "kills_timeline": []  # List of (timestamp, value) for tracking
                        }

                    # Determine who killed who
                    is_a_killed = (attacker_alliance == alliance_pair[0])

                    if is_a_killed:
                        conflicts[alliance_pair]["kills_by_a"] += 1
                        conflicts[alliance_pair]["isk_by_a"] += ship_value

                        # Track biggest loss for B (victim)
                        if ship_value > conflicts[alliance_pair]["biggest_loss_b"]["value"]:
                            conflicts[alliance_pair]["biggest_loss_b"]["value"] = ship_value
                            conflicts[alliance_pair]["biggest_loss_b"]["ship_type_id"] = ship_type_id

                        # Track ship class destroyed (B's loss)
                        ship_class = self.get_ship_class(ship_type_id)
                        if ship_class:
                            conflicts[alliance_pair]["ship_classes_b"][ship_class] += 1
                    else:
                        conflicts[alliance_pair]["kills_by_b"] += 1
                        conflicts[alliance_pair]["isk_by_b"] += ship_value

                        # Track biggest loss for A (victim)
                        if ship_value > conflicts[alliance_pair]["biggest_loss_a"]["value"]:
                            conflicts[alliance_pair]["biggest_loss_a"]["value"] = ship_value
                            conflicts[alliance_pair]["biggest_loss_a"]["ship_type_id"] = ship_type_id

                        # Track ship class destroyed (A's loss)
                        ship_class = self.get_ship_class(ship_type_id)
                        if ship_class:
                            conflicts[alliance_pair]["ship_classes_a"][ship_class] += 1

                    # Track system hotspots
                    if system_id:
                        if system_id not in conflicts[alliance_pair]["systems"]:
                            conflicts[alliance_pair]["systems"][system_id] = 0
                        conflicts[alliance_pair]["systems"][system_id] += 1

                    # Track hourly activity
                    if killmail_time:
                        try:
                            dt = datetime.fromisoformat(killmail_time.replace('Z', '+00:00'))
                            hour = dt.hour
                            if hour not in conflicts[alliance_pair]["hourly_activity"]:
                                conflicts[alliance_pair]["hourly_activity"][hour] = 0
                            conflicts[alliance_pair]["hourly_activity"][hour] += 1
                        except:
                            pass

        # Calculate metrics
        war_data = []
        for alliance_pair, data in conflicts.items():
            total_kills = data["kills_by_a"] + data["kills_by_b"]
            total_isk = data["isk_by_a"] + data["isk_by_b"]

            # Only include significant conflicts (minimum 5 mutual kills)
            if total_kills < 5:
                continue

            # Calculate ratios
            kill_ratio_a = data["kills_by_a"] / max(data["kills_by_b"], 1)

            # Calculate ISK efficiency (percentage of total ISK destroyed by alliance A)
            isk_efficiency_a = (data["isk_by_a"] / (data["isk_by_a"] + data["isk_by_b"])) * 100 if (data["isk_by_a"] + data["isk_by_b"]) > 0 else 50
            isk_efficiency_b = (data["isk_by_b"] / (data["isk_by_a"] + data["isk_by_b"])) * 100 if (data["isk_by_a"] + data["isk_by_b"]) > 0 else 50

            # Calculate war intensity score (weighted by ISK, kills, and spread)
            # ISK is normalized to billions for scoring
            isk_score = (total_isk / 1e9) * 0.6  # 60% weight on ISK destroyed
            kill_score = total_kills * 0.3       # 30% weight on kill count
            system_score = len(data["systems"]) * 0.1  # 10% weight on conflict spread
            war_score = isk_score + kill_score + system_score

            # Determine winner based on combined metrics
            # Tactical winner: more kills
            tactical_winner = "a" if kill_ratio_a > 1.2 else "b" if kill_ratio_a < 0.8 else "contested"
            # Economic winner: higher ISK efficiency
            economic_winner = "a" if isk_efficiency_a > 60 else "b" if isk_efficiency_a < 40 else "contested"

            # Overall winner: weighted combination (60% economic, 40% tactical)
            # A wins if: ISK efficiency > 55% OR (ISK efficiency > 45% AND kill ratio > 1.5)
            # B wins if: ISK efficiency < 45% OR (ISK efficiency < 55% AND kill ratio < 0.67)
            if isk_efficiency_a > 55 or (isk_efficiency_a > 45 and kill_ratio_a > 1.5):
                overall_winner = "a"
            elif isk_efficiency_a < 45 or (isk_efficiency_a < 55 and kill_ratio_a < 0.67):
                overall_winner = "b"
            else:
                overall_winner = "contested"

            # Get top 5 system hotspots (sorted by kill count)
            top_systems = sorted(data["systems"].items(), key=lambda x: x[1], reverse=True)[:5]
            system_hotspots = []
            for system_id, kill_count in top_systems:
                system_info = self.get_system_location_info(system_id)
                system_hotspots.append({
                    "system_id": system_id,
                    "system_name": system_info.get("system_name", f"System {system_id}"),
                    "kills": kill_count,
                    "security": system_info.get("security", 0.0),
                    "region_name": system_info.get("region_name", "Unknown")
                })

            # Determine peak activity hours (top 3 hours)
            if data["hourly_activity"]:
                peak_hours = sorted(data["hourly_activity"].items(), key=lambda x: x[1], reverse=True)[:3]
                peak_hours_list = [hour for hour, count in peak_hours]
            else:
                peak_hours_list = []

            # Calculate average kill value
            avg_kill_value = total_isk / total_kills if total_kills > 0 else 0

            war_data.append({
                "alliance_a_id": data["alliance_a"],
                "alliance_b_id": data["alliance_b"],
                "total_kills": total_kills,
                "kills_by_a": data["kills_by_a"],
                "kills_by_b": data["kills_by_b"],
                "isk_destroyed_by_a": data["isk_by_a"],
                "isk_destroyed_by_b": data["isk_by_b"],
                "total_isk_destroyed": total_isk,
                "kill_ratio_a": kill_ratio_a,
                "isk_efficiency_a": isk_efficiency_a,
                "isk_efficiency_b": isk_efficiency_b,
                "active_systems": len(data["systems"]),
                "war_intensity_score": war_score,
                "tactical_winner": tactical_winner,
                "economic_winner": economic_winner,
                "winner": overall_winner,
                # NEW: Ship Class Analysis
                "ship_classes_a": data["ship_classes_a"],
                "ship_classes_b": data["ship_classes_b"],
                # NEW: System Hotspots
                "system_hotspots": system_hotspots,
                # NEW: Activity Timeline
                "hourly_activity": data["hourly_activity"],
                "peak_hours": peak_hours_list,
                # NEW: Economic Metrics
                "avg_kill_value": avg_kill_value,
                "biggest_loss_a": data["biggest_loss_a"],
                "biggest_loss_b": data["biggest_loss_b"]
            })

        # Sort by war intensity score (ISK-weighted activity)
        war_data.sort(key=lambda x: x['war_intensity_score'], reverse=True)

        # Get alliance names from ESI
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession()

        for war in war_data[:limit]:
            # Get alliance A name
            try:
                url = f"https://esi.evetech.net/latest/alliances/{war['alliance_a_id']}/"
                async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=3)) as response:
                    if response.status == 200:
                        data = await response.json()
                        war['alliance_a_name'] = data.get('name', f"Alliance {war['alliance_a_id']}")
                    else:
                        war['alliance_a_name'] = f"Alliance {war['alliance_a_id']}"
            except:
                war['alliance_a_name'] = f"Alliance {war['alliance_a_id']}"

            # Get alliance B name
            try:
                url = f"https://esi.evetech.net/latest/alliances/{war['alliance_b_id']}/"
                async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=3)) as response:
                    if response.status == 200:
                        data = await response.json()
                        war['alliance_b_name'] = data.get('name', f"Alliance {war['alliance_b_id']}")
                    else:
                        war['alliance_b_name'] = f"Alliance {war['alliance_b_id']}"
            except:
                war['alliance_b_name'] = f"Alliance {war['alliance_b_id']}"

        return {
            "wars": war_data[:limit],
            "total_wars": len(war_data),
            "period": "24h"
        }

    def get_trade_route_danger_map(self) -> Dict:
        """
        Analyze danger levels along major trade routes between hubs.

        Returns routes with danger scores per system based on:
        - Kill frequency in last 24h
        - Average ship value destroyed
        - Gate camp indicators (multi-attacker kills)

        Returns:
            Dict with routes and danger analysis
        """
        route_service = RouteService()

        # Major trade routes (hub pairs)
        trade_routes = [
            ('jita', 'amarr'),
            ('jita', 'dodixie'),
            ('jita', 'rens'),
            ('amarr', 'dodixie'),
            ('amarr', 'rens'),
        ]

        # Build system danger scores from Redis data
        system_danger = {}
        system_kill_count = {}
        system_total_isk = {}
        system_gate_camps = set()

        # Get all system timelines
        system_keys = list(self.redis_client.scan_iter("kill:system:*:timeline"))

        for system_key in system_keys:
            # Extract system_id from key
            parts = system_key.split(":")
            if len(parts) < 3:
                continue
            system_id = int(parts[2])

            # Get kills for this system
            kill_ids = self.redis_client.zrevrange(system_key, 0, -1)
            if not kill_ids:
                continue

            kills = []
            for kill_id in kill_ids:
                kill_data = self.redis_client.get(f"kill:id:{kill_id}")
                if kill_data:
                    kills.append(json.loads(kill_data))

            if not kills:
                continue

            # Calculate danger metrics
            kill_count = len(kills)
            total_isk = sum(k['ship_value'] for k in kills)
            avg_isk = total_isk / kill_count if kill_count > 0 else 0

            # Detect gate camps (kills with 4+ attackers)
            gate_camp_kills = sum(1 for k in kills if k.get('attacker_count', 0) >= 4)
            gate_camp_ratio = gate_camp_kills / kill_count if kill_count > 0 else 0

            # Danger score calculation (0-100)
            # - Kill frequency: 0-40 points (1 point per kill, capped at 40)
            # - Average value: 0-30 points (1 point per 100M ISK, capped at 30)
            # - Gate camps: 0-30 points (30 points if >20% gate camps)
            danger_score = min(40, kill_count) + \
                          min(30, int(avg_isk / 100_000_000)) + \
                          (30 if gate_camp_ratio > 0.2 else 0)

            system_danger[system_id] = danger_score
            system_kill_count[system_id] = kill_count
            system_total_isk[system_id] = total_isk

            if gate_camp_ratio > 0.2:
                system_gate_camps.add(system_id)

        # Calculate routes with danger analysis
        routes_data = []

        for from_hub, to_hub in trade_routes:
            from_system_id = TRADE_HUB_SYSTEMS[from_hub]
            to_system_id = TRADE_HUB_SYSTEMS[to_hub]

            # Calculate route (HighSec only)
            route = route_service.find_route(
                from_system_id,
                to_system_id,
                avoid_lowsec=True,
                avoid_nullsec=True
            )

            if not route:
                continue

            # Analyze danger along route
            route_systems = []
            total_danger = 0
            max_danger_system = None
            max_danger_score = 0

            for system in route:
                system_id = system['system_id']
                danger = system_danger.get(system_id, 0)
                kill_count = system_kill_count.get(system_id, 0)
                total_isk = system_total_isk.get(system_id, 0)
                is_gate_camp = system_id in system_gate_camps

                total_danger += danger

                if danger > max_danger_score:
                    max_danger_score = danger
                    max_danger_system = system

                route_systems.append({
                    "system_id": system_id,
                    "system_name": system['system_name'],
                    "security": system['security'],
                    "danger_score": danger,
                    "kills_24h": kill_count,
                    "isk_destroyed_24h": total_isk,
                    "gate_camp_detected": is_gate_camp
                })

            # Classify route danger level
            avg_danger = total_danger / len(route_systems) if route_systems else 0
            if avg_danger >= 50:
                danger_level = "EXTREME"
            elif avg_danger >= 30:
                danger_level = "HIGH"
            elif avg_danger >= 15:
                danger_level = "MODERATE"
            elif avg_danger >= 5:
                danger_level = "LOW"
            else:
                danger_level = "SAFE"

            routes_data.append({
                "from_hub": from_hub.upper(),
                "to_hub": to_hub.upper(),
                "from_system_id": from_system_id,
                "to_system_id": to_system_id,
                "total_jumps": len(route_systems),
                "danger_level": danger_level,
                "avg_danger_score": round(avg_danger, 1),
                "total_danger_score": total_danger,
                "max_danger_system": {
                    "system_id": max_danger_system['system_id'],
                    "system_name": max_danger_system['system_name'],
                    "danger_score": max_danger_score
                } if max_danger_system else None,
                "systems": route_systems
            })

        # Sort by danger level
        routes_data.sort(key=lambda x: x['avg_danger_score'], reverse=True)

        return {
            "timestamp": datetime.now().isoformat(),
            "routes": routes_data,
            "total_routes": len(routes_data),
            "period": "24h",
            "danger_scale": {
                "SAFE": "0-5 avg danger",
                "LOW": "5-15 avg danger",
                "MODERATE": "15-30 avg danger",
                "HIGH": "30-50 avg danger",
                "EXTREME": "50+ avg danger"
            }
        }

    def get_24h_battle_report(self) -> Dict:
        """
        Generate comprehensive 24h battle report by region.

        Cached for 10 minutes to reduce computation load.

        Returns:
            Dict with regional stats and global summary
        """
        # Check cache first
        cache_key = "battle_report:24h:cache"
        cached = self.redis_client.get(cache_key)
        if cached:
            return json.loads(cached)

        # Generate fresh report
        # Get all region timelines
        region_keys = list(self.redis_client.scan_iter("kill:region:*:timeline"))

        regional_stats = []
        total_kills_global = 0
        total_isk_global = 0.0

        for region_key in region_keys:
            # Extract region_id from key
            parts = region_key.split(":")
            if len(parts) < 3:
                continue
            region_id = int(parts[2])

            # Get all kills for this region
            kill_ids = self.redis_client.zrevrange(region_key, 0, -1)

            if not kill_ids:
                continue

            kills = []
            for kill_id in kill_ids:
                kill_data = self.redis_client.get(f"kill:id:{kill_id}")
                if kill_data:
                    kills.append(json.loads(kill_data))

            if not kills:
                continue

            # Calculate region stats
            kill_count = len(kills)
            total_isk = sum(k['ship_value'] for k in kills)
            avg_isk = total_isk / kill_count if kill_count > 0 else 0

            # Get top 3 systems
            system_counts = {}
            for kill in kills:
                system_id = kill['solar_system_id']
                system_counts[system_id] = system_counts.get(system_id, 0) + 1
            top_systems = sorted(system_counts.items(), key=lambda x: x[1], reverse=True)[:3]

            # Get top 3 ship types
            ship_counts = {}
            for kill in kills:
                ship_id = kill['ship_type_id']
                ship_counts[ship_id] = ship_counts.get(ship_id, 0) + 1
            top_ships = sorted(ship_counts.items(), key=lambda x: x[1], reverse=True)[:3]

            # Get top 5 destroyed items/modules
            item_counts = {}
            for kill in kills:
                for item in kill.get('destroyed_items', []):
                    item_id = item['item_type_id']
                    quantity = item['quantity']
                    item_counts[item_id] = item_counts.get(item_id, 0) + quantity
            top_items = sorted(item_counts.items(), key=lambda x: x[1], reverse=True)[:5]

            # Get region name from DB
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        'SELECT "regionName" FROM "mapRegions" WHERE "regionID" = %s',
                        (region_id,)
                    )
                    row = cur.fetchone()
                    region_name = row[0] if row else f"Region {region_id}"

                    # Get system names
                    top_systems_with_names = []
                    for system_id, count in top_systems:
                        cur.execute(
                            'SELECT "solarSystemName" FROM "mapSolarSystems" WHERE "solarSystemID" = %s',
                            (system_id,)
                        )
                        row = cur.fetchone()
                        system_name = row[0] if row else f"System {system_id}"
                        top_systems_with_names.append({
                            "system_id": system_id,
                            "system_name": system_name,
                            "kills": count
                        })

                    # Get ship names
                    top_ships_with_names = []
                    for ship_id, count in top_ships:
                        cur.execute(
                            'SELECT "typeName" FROM "invTypes" WHERE "typeID" = %s',
                            (ship_id,)
                        )
                        row = cur.fetchone()
                        ship_name = row[0] if row else f"Ship {ship_id}"
                        top_ships_with_names.append({
                            "ship_type_id": ship_id,
                            "ship_name": ship_name,
                            "losses": count
                        })

                    # Get item/module names
                    top_items_with_names = []
                    for item_id, quantity in top_items:
                        cur.execute(
                            'SELECT "typeName" FROM "invTypes" WHERE "typeID" = %s',
                            (item_id,)
                        )
                        row = cur.fetchone()
                        item_name = row[0] if row else f"Item {item_id}"
                        top_items_with_names.append({
                            "item_type_id": item_id,
                            "item_name": item_name,
                            "quantity_destroyed": quantity
                        })

            regional_stats.append({
                "region_id": region_id,
                "region_name": region_name,
                "kills": kill_count,
                "total_isk_destroyed": total_isk,
                "avg_kill_value": avg_isk,
                "top_systems": top_systems_with_names,
                "top_ships": top_ships_with_names,
                "top_destroyed_items": top_items_with_names
            })

            total_kills_global += kill_count
            total_isk_global += total_isk

        # Sort regions by kills descending
        regional_stats.sort(key=lambda x: x['kills'], reverse=True)

        # Find most active and most expensive regions
        most_active_region = regional_stats[0] if regional_stats else None
        most_expensive_region = max(regional_stats, key=lambda x: x['total_isk_destroyed']) if regional_stats else None

        report = {
            "period": "24h",
            "global": {
                "total_kills": total_kills_global,
                "total_isk_destroyed": total_isk_global,
                "most_active_region": most_active_region['region_name'] if most_active_region else None,
                "most_expensive_region": most_expensive_region['region_name'] if most_expensive_region else None
            },
            "regions": regional_stats
        }

        # Cache report for 10 minutes
        self.redis_client.setex(cache_key, BATTLE_REPORT_CACHE_TTL, json.dumps(report))

        return report
