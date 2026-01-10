"""
Kill analysis utilities for zkillboard reports.

Provides shared analysis functions:
- Capital kill extraction
- High-value kill identification
- Danger zone analysis
- Ship breakdown statistics
- Timeline analysis
"""

from datetime import datetime
from typing import Dict, List, Optional
from collections import defaultdict

from .base import ReportsBase, CAPITAL_GROUPS


class KillAnalysisMixin:
    """Mixin providing kill analysis methods."""

    def extract_capital_kills(
        self,
        killmails: List[Dict],
        location_cache: Dict = None,
        ship_cache: Dict = None,
        limit: int = 10
    ) -> List[Dict]:
        """Extract capital ship kills from killmail list."""
        capitals = []

        for km in killmails:
            ship_type_id = km.get('ship_type_id')
            if not ship_type_id:
                continue

            # Get ship info
            if ship_cache and ship_type_id in ship_cache:
                ship_info = ship_cache[ship_type_id]
            else:
                ship_info = self.get_ship_info_batch([ship_type_id]).get(ship_type_id, {})
                if ship_cache is not None:
                    ship_cache[ship_type_id] = ship_info

            group_id = ship_info.get('group_id', 0)
            if group_id not in CAPITAL_GROUPS:
                continue

            system_id = km.get('solar_system_id')
            if location_cache and system_id in location_cache:
                location = location_cache[system_id]
            else:
                location = self.get_system_location_info(system_id, location_cache)

            capitals.append({
                'killmail_id': km.get('killmail_id'),
                'ship_name': ship_info.get('ship_name', 'Unknown'),
                'ship_type_id': ship_type_id,
                'ship_class': ship_info.get('ship_class', 'capital'),
                'system_id': system_id,
                'system_name': location.get('system_name', 'Unknown'),
                'region_name': location.get('region_name', 'Unknown'),
                'security': location.get('security', 0.0),
                'value': km.get('zkb_total_value', km.get('ship_value', 0)),
                'timestamp': km.get('killmail_time', ''),
                'victim_alliance_id': km.get('victim_alliance_id'),
                'attacker_count': km.get('attacker_count', 0)
            })

        # Sort by value
        capitals.sort(key=lambda x: x['value'], reverse=True)
        return capitals[:limit]

    def extract_high_value_kills(
        self,
        killmails: List[Dict],
        limit: int = 20,
        min_value: int = 100_000_000,
        location_cache: Dict = None,
        ship_cache: Dict = None
    ) -> List[Dict]:
        """Extract high-value kills above threshold."""
        high_value = []

        for km in killmails:
            value = km.get('zkb_total_value', km.get('ship_value', 0))
            if value < min_value:
                continue

            ship_type_id = km.get('ship_type_id')
            if ship_cache and ship_type_id in ship_cache:
                ship_info = ship_cache[ship_type_id]
            else:
                ship_info = self.get_ship_info_batch([ship_type_id]).get(ship_type_id, {})
                if ship_cache is not None:
                    ship_cache[ship_type_id] = ship_info

            system_id = km.get('solar_system_id')
            if location_cache and system_id in location_cache:
                location = location_cache[system_id]
            else:
                location = self.get_system_location_info(system_id, location_cache)

            high_value.append({
                'killmail_id': km.get('killmail_id'),
                'ship_name': ship_info.get('ship_name', 'Unknown'),
                'ship_type_id': ship_type_id,
                'ship_class': ship_info.get('ship_class', 'other'),
                'system_id': system_id,
                'system_name': location.get('system_name', 'Unknown'),
                'region_name': location.get('region_name', 'Unknown'),
                'security': location.get('security', 0.0),
                'value': value,
                'timestamp': km.get('killmail_time', ''),
                'victim_alliance_id': km.get('victim_alliance_id'),
                'attacker_count': km.get('attacker_count', 0)
            })

        high_value.sort(key=lambda x: x['value'], reverse=True)
        return high_value[:limit]

    def identify_danger_zones(
        self,
        killmails: List[Dict],
        min_kills: int = 3,
        location_cache: Dict = None
    ) -> List[Dict]:
        """Identify systems with high kill activity."""
        system_kills = defaultdict(list)

        for km in killmails:
            system_id = km.get('solar_system_id')
            if system_id:
                system_kills[system_id].append(km)

        danger_zones = []
        for system_id, kills in system_kills.items():
            if len(kills) < min_kills:
                continue

            if location_cache and system_id in location_cache:
                location = location_cache[system_id]
            else:
                location = self.get_system_location_info(system_id, location_cache)

            total_value = sum(k.get('zkb_total_value', k.get('ship_value', 0)) for k in kills)

            danger_zones.append({
                'system_id': system_id,
                'system_name': location.get('system_name', 'Unknown'),
                'region_name': location.get('region_name', 'Unknown'),
                'security': location.get('security', 0.0),
                'kill_count': len(kills),
                'total_value': total_value,
                'avg_value': total_value // len(kills) if kills else 0
            })

        danger_zones.sort(key=lambda x: x['kill_count'], reverse=True)
        return danger_zones

    def calculate_ship_breakdown(
        self,
        killmails: List[Dict],
        ship_cache: Dict = None
    ) -> Dict:
        """Calculate breakdown of ships destroyed by class."""
        breakdown = defaultdict(lambda: {'count': 0, 'value': 0, 'ships': defaultdict(int)})

        for km in killmails:
            ship_type_id = km.get('ship_type_id')
            if not ship_type_id:
                continue

            if ship_cache and ship_type_id in ship_cache:
                ship_info = ship_cache[ship_type_id]
            else:
                ship_info = self.get_ship_info_batch([ship_type_id]).get(ship_type_id, {})
                if ship_cache is not None:
                    ship_cache[ship_type_id] = ship_info

            ship_class = ship_info.get('ship_class', 'other')
            ship_name = ship_info.get('ship_name', 'Unknown')
            value = km.get('zkb_total_value', km.get('ship_value', 0))

            breakdown[ship_class]['count'] += 1
            breakdown[ship_class]['value'] += value
            breakdown[ship_class]['ships'][ship_name] += 1

        # Convert to serializable format
        result = {}
        for ship_class, data in breakdown.items():
            top_ships = sorted(data['ships'].items(), key=lambda x: x[1], reverse=True)[:5]
            result[ship_class] = {
                'count': data['count'],
                'value': data['value'],
                'top_ships': [{'name': name, 'count': count} for name, count in top_ships]
            }

        return result

    def calculate_hourly_timeline(self, killmails: List[Dict]) -> List[Dict]:
        """Calculate kills per hour for timeline display."""
        hourly = defaultdict(lambda: {'kills': 0, 'value': 0})

        for km in killmails:
            timestamp = km.get('killmail_time')
            if not timestamp:
                continue

            try:
                if isinstance(timestamp, str):
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                else:
                    dt = timestamp

                hour_key = dt.strftime('%Y-%m-%d %H:00')
                hourly[hour_key]['kills'] += 1
                hourly[hour_key]['value'] += km.get('zkb_total_value', km.get('ship_value', 0))
            except Exception:
                continue

        # Sort by time
        timeline = []
        for hour, data in sorted(hourly.items()):
            timeline.append({
                'hour': hour,
                'kills': data['kills'],
                'value': data['value']
            })

        return timeline

    def find_peak_activity(self, timeline: List[Dict]) -> Dict:
        """Find the hour with peak activity."""
        if not timeline:
            return {'hour': None, 'kills': 0, 'value': 0}

        peak = max(timeline, key=lambda x: x['kills'])
        return peak

    def extract_hot_zones(
        self,
        killmails: List[Dict],
        limit: int = 15,
        location_cache: Dict = None,
        ship_cache: Dict = None
    ) -> List[Dict]:
        """Extract hot combat zones with detailed stats."""
        system_data = defaultdict(lambda: {
            'kills': [],
            'ship_classes': defaultdict(int),
            'total_value': 0
        })

        for km in killmails:
            system_id = km.get('solar_system_id')
            if not system_id:
                continue

            ship_type_id = km.get('ship_type_id')
            if ship_cache and ship_type_id in ship_cache:
                ship_info = ship_cache[ship_type_id]
            else:
                ship_info = self.get_ship_info_batch([ship_type_id]).get(ship_type_id, {})
                if ship_cache is not None:
                    ship_cache[ship_type_id] = ship_info

            ship_class = ship_info.get('ship_class', 'other')
            value = km.get('zkb_total_value', km.get('ship_value', 0))

            system_data[system_id]['kills'].append(km)
            system_data[system_id]['ship_classes'][ship_class] += 1
            system_data[system_id]['total_value'] += value

        hot_zones = []
        for system_id, data in system_data.items():
            if len(data['kills']) < 2:
                continue

            if location_cache and system_id in location_cache:
                location = location_cache[system_id]
            else:
                location = self.get_system_location_info(system_id, location_cache)

            # Top ship classes
            top_classes = sorted(
                data['ship_classes'].items(),
                key=lambda x: x[1],
                reverse=True
            )[:3]

            hot_zones.append({
                'system_id': system_id,
                'system_name': location.get('system_name', 'Unknown'),
                'region_name': location.get('region_name', 'Unknown'),
                'security': location.get('security', 0.0),
                'kill_count': len(data['kills']),
                'total_value': data['total_value'],
                'top_ship_classes': [
                    {'class': cls, 'count': cnt} for cls, cnt in top_classes
                ]
            })

        hot_zones.sort(key=lambda x: x['kill_count'], reverse=True)
        return hot_zones[:limit]
