#!/usr/bin/env python3
"""
War Analyzer - Combines combat data for demand analysis
Doctrine detection, heatmap generation, and market gap identification
"""

from datetime import date, timedelta
from typing import List, Dict, Optional
from collections import defaultdict

from database import get_db_connection
from config import WAR_DOCTRINE_MIN_FLEET_SIZE, WAR_HEATMAP_MIN_KILLS


class WarAnalyzer:
    """Combines all data sources for demand analysis"""

    def analyze_demand(self, region_id: int, days: int = 7) -> dict:
        """
        Full demand analysis for a region.
        Returns ships lost, items lost, market gaps, upcoming battles, FW hotspots.
        """
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Top ships lost
                cur.execute('''
                    SELECT
                        csl.ship_type_id,
                        it."typeName",
                        SUM(csl.quantity) as total,
                        COALESCE(mp.sell_volume, 0) as market_stock
                    FROM combat_ship_losses csl
                    JOIN "invTypes" it ON csl.ship_type_id = it."typeID"
                    LEFT JOIN market_prices mp ON mp.type_id = csl.ship_type_id
                        AND mp.region_id = %s
                    WHERE csl.region_id = %s
                    AND csl.date >= CURRENT_DATE - %s
                    GROUP BY csl.ship_type_id, it."typeName", mp.sell_volume
                    ORDER BY total DESC
                    LIMIT 20
                ''', (region_id, region_id, days))

                ships_lost = [
                    {
                        'type_id': row[0],
                        'name': row[1],
                        'quantity': row[2],
                        'market_stock': row[3],
                        'gap': max(0, row[2] - row[3])
                    }
                    for row in cur.fetchall()
                ]

                # Top items lost
                cur.execute('''
                    SELECT
                        cil.item_type_id,
                        it."typeName",
                        SUM(cil.quantity_destroyed) as total,
                        COALESCE(mp.sell_volume, 0) as market_stock
                    FROM combat_item_losses cil
                    JOIN "invTypes" it ON cil.item_type_id = it."typeID"
                    LEFT JOIN market_prices mp ON mp.type_id = cil.item_type_id
                        AND mp.region_id = %s
                    WHERE cil.region_id = %s
                    AND cil.date >= CURRENT_DATE - %s
                    GROUP BY cil.item_type_id, it."typeName", mp.sell_volume
                    ORDER BY total DESC
                    LIMIT 20
                ''', (region_id, region_id, days))

                items_lost = [
                    {
                        'type_id': row[0],
                        'name': row[1],
                        'quantity': row[2],
                        'market_stock': row[3],
                        'gap': max(0, row[2] - row[3])
                    }
                    for row in cur.fetchall()
                ]

                # Market gaps (where losses exceed stock)
                market_gaps = [s for s in ships_lost if s['gap'] > 0][:10]
                market_gaps.extend([i for i in items_lost if i['gap'] > 0][:10])
                market_gaps.sort(key=lambda x: x['gap'], reverse=True)

        return {
            'region_id': region_id,
            'days': days,
            'ships_lost': ships_lost,
            'items_lost': items_lost,
            'market_gaps': market_gaps[:15]
        }

    def get_heatmap_data(self, days: int = 7, min_kills: int = None) -> List[dict]:
        """Get kill data with coordinates for heatmap visualization"""
        if min_kills is None:
            min_kills = WAR_HEATMAP_MIN_KILLS

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    SELECT
                        csl.solar_system_id,
                        srm.solar_system_name,
                        srm.region_id,
                        srm.region_name,
                        srm.security_status,
                        s.x / 1e16 as x,
                        s.z / 1e16 as z,
                        SUM(csl.quantity) as kills
                    FROM combat_ship_losses csl
                    JOIN system_region_map srm ON csl.solar_system_id = srm.solar_system_id
                    JOIN "mapSolarSystems" s ON csl.solar_system_id = s."solarSystemID"
                    WHERE csl.date >= CURRENT_DATE - %s
                    GROUP BY csl.solar_system_id, srm.solar_system_name,
                             srm.region_id, srm.region_name, srm.security_status,
                             s.x, s.z
                    HAVING SUM(csl.quantity) >= %s
                    ORDER BY kills DESC
                ''', (days, min_kills))

                return [
                    {
                        'system_id': row[0],
                        'name': row[1],
                        'region_id': row[2],
                        'region': row[3],
                        'security': round(float(row[4]), 2) if row[4] else 0,
                        'x': round(float(row[5]), 2) if row[5] else 0,
                        'z': round(float(row[6]), 2) if row[6] else 0,
                        'kills': row[7]
                    }
                    for row in cur.fetchall()
                ]

    def detect_doctrines(self, region_id: int, days: int = 7) -> List[dict]:
        """
        Detect fleet doctrines by finding bulk losses of same ship type.
        A doctrine is detected when MIN_FLEET_SIZE+ of same ship die in same system on same day.
        """
        min_size = WAR_DOCTRINE_MIN_FLEET_SIZE

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    SELECT
                        csl.date,
                        csl.solar_system_id,
                        srm.solar_system_name,
                        csl.ship_type_id,
                        it."typeName" as ship_name,
                        csl.quantity
                    FROM combat_ship_losses csl
                    JOIN system_region_map srm ON csl.solar_system_id = srm.solar_system_id
                    JOIN "invTypes" it ON csl.ship_type_id = it."typeID"
                    WHERE csl.region_id = %s
                    AND csl.date >= CURRENT_DATE - %s
                    AND csl.quantity >= %s
                    ORDER BY csl.quantity DESC
                    LIMIT 20
                ''', (region_id, days, min_size))

                return [
                    {
                        'date': row[0].isoformat(),
                        'system_id': row[1],
                        'system_name': row[2],
                        'ship_type_id': row[3],
                        'ship_name': row[4],
                        'quantity': row[5],
                        'estimated_restock': row[5]  # Simple estimate
                    }
                    for row in cur.fetchall()
                ]

    def get_alliance_conflicts(self, days: int = 7, top: int = 20) -> List[dict]:
        """Get top alliance conflicts"""
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    SELECT
                        alliance_a,
                        alliance_b,
                        SUM(kill_count) as total_kills
                    FROM alliance_conflicts
                    WHERE date >= CURRENT_DATE - %s
                    GROUP BY alliance_a, alliance_b
                    ORDER BY total_kills DESC
                    LIMIT %s
                ''', (days, top))

                return [
                    {
                        'alliance_a': row[0],
                        'alliance_b': row[1],
                        'kills': row[2]
                    }
                    for row in cur.fetchall()
                ]

    def get_system_danger_score(self, solar_system_id: int, days: int = 1) -> dict:
        """Get danger score for a system (kills in last X days)"""
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    SELECT COALESCE(SUM(quantity), 0)
                    FROM combat_ship_losses
                    WHERE solar_system_id = %s
                    AND date >= CURRENT_DATE - %s
                ''', (solar_system_id, days))

                kills = cur.fetchone()[0]

                # Score: 0-10 based on kill activity
                if kills == 0:
                    score = 0
                elif kills < 5:
                    score = 2
                elif kills < 20:
                    score = 5
                elif kills < 50:
                    score = 7
                else:
                    score = 10

                return {
                    'system_id': solar_system_id,
                    'kills_24h': kills,
                    'danger_score': score
                }

    def get_regional_summary(self, days: int = 7) -> List[dict]:
        """Get summary of combat activity per region"""
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    SELECT
                        srm.region_id,
                        srm.region_name,
                        COUNT(DISTINCT csl.solar_system_id) as active_systems,
                        SUM(csl.quantity) as total_kills,
                        SUM(csl.total_value_destroyed) as total_value
                    FROM combat_ship_losses csl
                    JOIN system_region_map srm ON csl.solar_system_id = srm.solar_system_id
                    WHERE csl.date >= CURRENT_DATE - %s
                    GROUP BY srm.region_id, srm.region_name
                    ORDER BY total_kills DESC
                    LIMIT 50
                ''', (days,))

                return [
                    {
                        'region_id': row[0],
                        'region_name': row[1],
                        'active_systems': row[2],
                        'total_kills': row[3],
                        'total_value': float(row[4]) if row[4] else 0
                    }
                    for row in cur.fetchall()
                ]

    def get_top_ships_galaxy(self, days: int = 7, limit: int = 20) -> List[dict]:
        """Get most destroyed ships across all regions"""
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    SELECT
                        csl.ship_type_id,
                        it."typeName",
                        ig."groupName",
                        SUM(csl.quantity) as total_lost,
                        SUM(csl.total_value_destroyed) as total_value
                    FROM combat_ship_losses csl
                    JOIN "invTypes" it ON csl.ship_type_id = it."typeID"
                    JOIN "invGroups" ig ON it."groupID" = ig."groupID"
                    WHERE csl.date >= CURRENT_DATE - %s
                    GROUP BY csl.ship_type_id, it."typeName", ig."groupName"
                    ORDER BY total_lost DESC
                    LIMIT %s
                ''', (days, limit))

                return [
                    {
                        'type_id': row[0],
                        'name': row[1],
                        'group': row[2],
                        'quantity': row[3],
                        'value': float(row[4]) if row[4] else 0
                    }
                    for row in cur.fetchall()
                ]

    def get_item_combat_stats(self, type_id: int, days: int = 7) -> dict:
        """Get combat stats for a single item (ship or module)"""
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Check ships first
                cur.execute('''
                    SELECT
                        csl.region_id,
                        srm.region_name,
                        SUM(csl.quantity) as destroyed
                    FROM combat_ship_losses csl
                    JOIN system_region_map srm ON csl.region_id = srm.region_id
                    WHERE csl.ship_type_id = %s
                    AND csl.date >= CURRENT_DATE - %s
                    GROUP BY csl.region_id, srm.region_name
                    ORDER BY destroyed DESC
                ''', (type_id, days))
                ship_results = cur.fetchall()

                # Check items/modules
                cur.execute('''
                    SELECT
                        cil.region_id,
                        srm.region_name,
                        SUM(cil.quantity_destroyed) as destroyed
                    FROM combat_item_losses cil
                    JOIN system_region_map srm ON cil.region_id = srm.region_id
                    WHERE cil.item_type_id = %s
                    AND cil.date >= CURRENT_DATE - %s
                    GROUP BY cil.region_id, srm.region_name
                    ORDER BY destroyed DESC
                ''', (type_id, days))
                item_results = cur.fetchall()

                # Combine results (prefer ship data if exists)
                results = ship_results if ship_results else item_results

                if not results:
                    return {
                        'type_id': type_id,
                        'days': days,
                        'total_destroyed': 0,
                        'by_region': [],
                        'market_comparison': [],
                        'has_data': False
                    }

                by_region = [
                    {'region_id': r[0], 'region_name': r[1], 'destroyed': r[2]}
                    for r in results
                ]
                total_destroyed = sum(r[2] for r in results)

                # Get market stock for comparison
                region_keys = {
                    10000002: 'the_forge',
                    10000043: 'domain',
                    10000030: 'heimatar',
                    10000032: 'sinq_laison',
                    10000042: 'metropolis'
                }

                cur.execute('''
                    SELECT region_id, sell_volume
                    FROM market_prices
                    WHERE type_id = %s
                ''', (type_id,))
                market_data = {r[0]: r[1] for r in cur.fetchall()}

                market_comparison = []
                for r in by_region:
                    region_id = r['region_id']
                    stock = market_data.get(region_id, 0)
                    market_comparison.append({
                        'region': region_keys.get(region_id, str(region_id)),
                        'region_name': r['region_name'],
                        'destroyed': r['destroyed'],
                        'stock': stock,
                        'gap': stock - r['destroyed']
                    })

                # Get type name
                cur.execute('SELECT "typeName" FROM "invTypes" WHERE "typeID" = %s', (type_id,))
                name_row = cur.fetchone()
                type_name = name_row[0] if name_row else f"Type {type_id}"

                return {
                    'type_id': type_id,
                    'type_name': type_name,
                    'days': days,
                    'total_destroyed': total_destroyed,
                    'by_region': by_region,
                    'market_comparison': market_comparison,
                    'has_data': True
                }


# Singleton instance
war_analyzer = WarAnalyzer()
