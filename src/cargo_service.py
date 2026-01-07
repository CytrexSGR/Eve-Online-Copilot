"""
Cargo Volume Calculator for EVE Co-Pilot
Calculates cargo requirements and recommends ships
"""

from math import ceil
from typing import List, Dict, Optional
from src.database import get_db_connection
from psycopg2.extras import RealDictCursor


# Ship cargo capacities (m³)
SHIP_CARGO = {
    'shuttle': {'capacity': 10, 'name': 'Shuttle'},
    'frigate': {'capacity': 400, 'name': 'Frigate'},
    'destroyer': {'capacity': 500, 'name': 'Destroyer'},
    'cruiser': {'capacity': 500, 'name': 'Cruiser'},
    'industrial': {'capacity': 5000, 'name': 'Industrial (Nereus, etc.)'},
    'blockade_runner': {'capacity': 10000, 'name': 'Blockade Runner'},
    'deep_space_transport': {'capacity': 60000, 'name': 'Deep Space Transport'},
    'freighter': {'capacity': 1000000, 'name': 'Freighter'},
    'jump_freighter': {'capacity': 350000, 'name': 'Jump Freighter'},
}


class CargoService:

    def get_item_volume(self, type_id: int) -> Optional[float]:
        """Get volume of an item from SDE"""
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute('''
                    SELECT "volume" FROM "invTypes"
                    WHERE "typeID" = %s
                ''', (type_id,))
                result = cur.fetchone()
                return float(result['volume']) if result and result['volume'] else None

    def calculate_cargo_volume(self, items: List[Dict]) -> Dict:
        """
        Calculate total cargo volume for a list of items

        Args:
            items: List of {'type_id': int, 'quantity': int}

        Returns:
            Total volume and item breakdown
        """
        total_volume = 0.0
        breakdown = []

        for item in items:
            type_id = item['type_id']
            quantity = item.get('quantity', 1)
            volume = self.get_item_volume(type_id)

            if volume is not None:
                item_total = volume * quantity
                total_volume += item_total
                breakdown.append({
                    'type_id': type_id,
                    'quantity': quantity,
                    'unit_volume': volume,
                    'total_volume': item_total
                })

        return {
            'total_volume_m3': round(total_volume, 2),
            'total_volume_formatted': self._format_volume(total_volume),
            'items': breakdown
        }

    def recommend_ship(self, volume_m3: float, prefer_safe: bool = True) -> Dict:
        """
        Recommend ship based on cargo volume

        Args:
            volume_m3: Total cargo volume
            prefer_safe: Prefer blockade runners over industrials

        Returns:
            Ship recommendation with trips needed
        """
        recommendations = []

        for ship_type, info in SHIP_CARGO.items():
            capacity = info['capacity']
            if capacity >= volume_m3:
                recommendations.append({
                    'ship_type': ship_type,
                    'ship_name': info['name'],
                    'capacity': capacity,
                    'trips': 1,
                    'fill_percent': round((volume_m3 / capacity) * 100, 1),
                    'excess_capacity': capacity - volume_m3
                })

        # Sort by capacity (smallest that fits first)
        recommendations.sort(key=lambda x: x['capacity'])

        # If nothing fits, recommend freighter with multiple trips
        if not recommendations:
            freighter_cap = SHIP_CARGO['freighter']['capacity']
            trips = ceil(volume_m3 / freighter_cap)
            recommendations = [{
                'ship_type': 'freighter',
                'ship_name': SHIP_CARGO['freighter']['name'],
                'capacity': freighter_cap,
                'trips': trips,
                'fill_percent': round((volume_m3 / (freighter_cap * trips)) * 100, 1),
                'excess_capacity': (freighter_cap * trips) - volume_m3
            }]

        # Best recommendation
        best = recommendations[0] if recommendations else None

        # Alternative: prefer blockade runner for safety in lowsec
        safe_options = [r for r in recommendations if r['ship_type'] in ['blockade_runner', 'deep_space_transport']]

        return {
            'volume_m3': round(volume_m3, 2),
            'volume_formatted': self._format_volume(volume_m3),
            'recommended': best,
            'safe_option': safe_options[0] if safe_options else None,
            'all_options': recommendations[:5]  # Top 5 options
        }

    def _format_volume(self, volume: float) -> str:
        """Format volume for display"""
        if volume >= 1_000_000:
            return f"{volume / 1_000_000:.2f}M m³"
        if volume >= 1_000:
            return f"{volume / 1_000:.1f}K m³"
        return f"{volume:.0f} m³"


cargo_service = CargoService()
