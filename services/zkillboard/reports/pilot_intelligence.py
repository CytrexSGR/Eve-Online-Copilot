"""
Pilot Intelligence Report - 24h battle report.

Provides comprehensive combat intelligence:
- Global kill statistics
- Hot zones (most active systems)
- Capital ship kills
- High-value kills
- Industrial danger zones
- Ship class breakdown
- Hourly activity timeline
"""

import json
import time
from typing import Dict, List

from src.database import get_db_connection
from .base import ReportsBase, REPORT_CACHE_TTL


class PilotIntelligenceMixin:
    """Mixin providing pilot intelligence report methods."""

    def build_pilot_intelligence_report(self) -> Dict:
        """Build complete pilot intelligence battle report (with cache)."""
        start_time = time.time()

        # Check cache first
        cache_key = "report:pilot_intelligence:24h"
        cached_report = self.redis_client.get(cache_key)
        if cached_report:
            print(f"[CACHE HIT] Returning cached pilot intelligence report")
            return json.loads(cached_report)

        print(f"[CACHE MISS] Building pilot intelligence report from scratch...")
        return self._build_pilot_intelligence_report_internal(start_time, cache_key)

    def build_pilot_intelligence_report_fresh(self) -> Dict:
        """Build complete pilot intelligence battle report (skip cache, for cron job)."""
        start_time = time.time()
        print(f"[FRESH] Building pilot intelligence report from scratch...")
        return self._build_pilot_intelligence_report_internal(start_time, None)

    def _build_pilot_intelligence_report_internal(self, start_time: float, cache_key: str = None) -> Dict:
        """Internal method to build the report."""
        # Get all killmails from Redis using PIPELINE for bulk loading
        kill_keys = list(self.redis_client.scan_iter("kill:id:*"))
        print(f"[Performance] Found {len(kill_keys)} killmail keys in {time.time() - start_time:.2f}s")

        # Use pipeline for bulk fetch (10-100x faster than individual gets)
        pipe_start = time.time()
        killmails = []
        if kill_keys:
            # Process in batches to avoid memory issues
            BATCH_SIZE = 1000
            for i in range(0, len(kill_keys), BATCH_SIZE):
                batch_keys = kill_keys[i:i + BATCH_SIZE]
                pipe = self.redis_client.pipeline()
                for key in batch_keys:
                    pipe.get(key)
                results = pipe.execute()
                for kill_data in results:
                    if kill_data:
                        killmails.append(json.loads(kill_data))

        print(f"[Performance] Loaded {len(killmails)} killmails via pipeline in {time.time() - pipe_start:.2f}s")

        if not killmails:
            return self._empty_pilot_report()

        # PRE-LOAD all system and ship data in BATCH (eliminates N+1 queries)
        batch_start = time.time()

        # Collect all unique system IDs
        all_system_ids = list(set(km.get('solar_system_id') for km in killmails if km.get('solar_system_id')))

        # Collect all unique ship type IDs
        all_ship_type_ids = list(set(km.get('ship_type_id') for km in killmails if km.get('ship_type_id')))

        # Batch load system locations (1 query instead of N)
        system_cache = self.get_system_locations_batch(all_system_ids)
        print(f"[Performance] Batch loaded {len(system_cache)} systems in {time.time() - batch_start:.2f}s")

        # Batch load ship info (1 query instead of N)
        ship_start = time.time()
        ship_cache = self.get_ship_info_batch(all_ship_type_ids)
        print(f"[Performance] Batch loaded {len(ship_cache)} ship types in {time.time() - ship_start:.2f}s")

        # Calculate all intelligence sections (using caches)
        calc_start = time.time()
        timeline = self.calculate_hourly_timeline(killmails)
        peak_activity = self.find_peak_activity(timeline)
        hot_zones = self.extract_hot_zones(killmails, limit=15, system_cache=system_cache, ship_cache=ship_cache)
        capital_kills = self.extract_capital_kills(killmails, system_cache=system_cache, ship_cache=ship_cache)
        high_value_kills = self.extract_high_value_kills(killmails, limit=20, system_cache=system_cache, ship_cache=ship_cache)
        danger_zones = self.identify_danger_zones(killmails, min_kills=3, system_cache=system_cache, ship_cache=ship_cache)
        ship_breakdown = self.calculate_ship_breakdown(killmails, ship_cache=ship_cache)
        print(f"[Performance] Calculated all sections in {time.time() - calc_start:.2f}s")

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

        # Cache the report if cache_key provided (not for fresh generation)
        total_time = time.time() - start_time
        if cache_key:
            self.redis_client.setex(cache_key, REPORT_CACHE_TTL, json.dumps(report))
            print(f"[CACHE] Cached pilot intelligence report for {REPORT_CACHE_TTL}s")
        print(f"[Performance] TOTAL report generation time: {total_time:.2f}s")

        return report

    def _empty_pilot_report(self) -> Dict:
        """Return empty report structure."""
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
        """Build simplified region summary for backwards compatibility."""
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
