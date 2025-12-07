"""
Transport Options Service for EVE Co-Pilot
Calculates optimal transport options for shopping lists
"""

from math import ceil
from database import get_db_connection
from psycopg2.extras import RealDictCursor
from typing import Optional, List, Dict
from capability_service import capability_service
from shopping_service import shopping_service

# Flight time per jump by ship group (minutes)
FLIGHT_TIME_PER_JUMP = {
    'Industrial': 2.0,
    'Blockade Runner': 1.5,
    'Deep Space Transport': 2.5,
    'Freighter': 3.5,
    'Jump Freighter': 2.0,
}

# Trade hub system IDs
TRADE_HUB_SYSTEMS = {
    30000142: 'Jita',
    30002187: 'Amarr',
    30002659: 'Dodixie',
    30002510: 'Rens',
    30002053: 'Hek',
}

# Home system
HOME_SYSTEM_ID = 30000119  # Isikemi


class TransportService:

    def get_transport_options(
        self,
        list_id: int,
        safe_only: bool = True
    ) -> dict:
        """
        Calculate transport options for a shopping list

        Returns options sorted by efficiency (fewer trips, faster)
        """
        # 1. Get cargo summary
        cargo = shopping_service.get_cargo_summary(list_id)
        total_volume = cargo['materials']['total_volume_m3']

        if total_volume == 0:
            return {
                'total_volume_m3': 0,
                'options': [],
                'message': 'No materials to transport'
            }

        # 2. Get regions with items
        regions_needed = list(cargo['materials']['breakdown_by_region'].keys())
        regions_needed = [r for r in regions_needed if r != 'unassigned']

        # 3. Get available ships
        # Include home system + trade hubs
        relevant_systems = [HOME_SYSTEM_ID] + list(TRADE_HUB_SYSTEMS.keys())
        available_ships = capability_service.get_all_available_ships(
            location_ids=relevant_systems,
            can_fly_only=True
        )

        if not available_ships:
            return {
                'total_volume_m3': total_volume,
                'options': [],
                'message': 'No ships available at relevant locations'
            }

        # 4. Calculate route
        route_summary = self._build_route_summary(regions_needed)

        # 5. Generate options
        options = []
        for idx, ship in enumerate(available_ships):
            option = self._calculate_option(
                idx + 1,
                ship,
                total_volume,
                cargo['materials']['total_items'],
                route_summary,
                safe_only
            )
            if option:
                options.append(option)

        # 6. Sort by efficiency
        options.sort(key=lambda x: (x['trips'], x['flight_time_min']))

        return {
            'total_volume_m3': total_volume,
            'volume_formatted': cargo['materials']['volume_formatted'],
            'route_summary': route_summary['summary'],
            'options': options,
            'filters_available': ['fewest_trips', 'fastest', 'single_char', 'lowest_risk']
        }

    def _calculate_option(
        self,
        option_id: int,
        ship: dict,
        total_volume: float,
        total_items: int,
        route_info: dict,
        safe_only: bool
    ) -> Optional[dict]:
        """Calculate a single transport option"""
        cargo_capacity = ship['cargo_capacity']
        if not cargo_capacity or cargo_capacity <= 0:
            return None

        trips = ceil(total_volume / cargo_capacity)
        ship_group = ship['ship_group'] or 'Industrial'

        # Flight time
        time_per_jump = FLIGHT_TIME_PER_JUMP.get(ship_group, 2.0)
        jumps = route_info.get('total_jumps', 10)  # Default estimate
        docking_time = len(route_info.get('legs', [])) * 2  # 2 min per stop
        flight_time = int((jumps * time_per_jump + docking_time) * trips)

        # Risk score (simplified - would use route_service for real calculation)
        risk_score = route_info.get('lowsec_systems', 0)
        risk_label = 'Safe' if risk_score == 0 else 'Low Risk' if risk_score <= 2 else 'Medium Risk'

        # Skip risky options if safe_only
        if safe_only and risk_score > 0:
            # Still include but mark as risky
            pass

        # Capacity utilization
        capacity_used = (total_volume / (cargo_capacity * trips)) * 100

        return {
            'id': option_id,
            'characters': [{
                'id': ship['character_id'],
                'name': ship['character_name'],
                'ship_type_id': ship['type_id'],
                'ship_name': ship['ship_name'],
                'ship_group': ship_group,
                'ship_location': ship['location_name']
            }],
            'trips': trips,
            'flight_time_min': flight_time,
            'flight_time_formatted': self._format_time(flight_time),
            'capacity_m3': cargo_capacity,
            'capacity_used_pct': round(capacity_used, 1),
            'risk_score': risk_score,
            'risk_label': risk_label,
            'dangerous_systems': [],
            'isk_per_trip': 0  # Would need list total cost
        }

    def _build_route_summary(self, regions: List[str]) -> dict:
        """Build route summary from regions"""
        # Map region keys to hub names
        region_to_hub = {
            'the_forge': 'Jita',
            'domain': 'Amarr',
            'sinq_laison': 'Dodixie',
            'heimatar': 'Rens',
            'metropolis': 'Hek',
        }

        hubs = [region_to_hub.get(r, r) for r in regions if r in region_to_hub]

        if not hubs:
            return {
                'summary': 'No route needed',
                'total_jumps': 0,
                'legs': [],
                'lowsec_systems': 0
            }

        # Build summary string
        route_parts = ['Isikemi'] + hubs + ['Isikemi']
        summary = ' → '.join(route_parts)

        # Estimate jumps (simplified)
        estimated_jumps = len(hubs) * 8  # ~8 jumps per hub average

        return {
            'summary': summary,
            'total_jumps': estimated_jumps,
            'legs': [{'from': route_parts[i], 'to': route_parts[i+1]}
                    for i in range(len(route_parts)-1)],
            'lowsec_systems': 0  # Would calculate from actual route
        }

    def _format_time(self, minutes: int) -> str:
        """Format minutes as human-readable time"""
        if minutes < 60:
            return f"{minutes} min"
        hours = minutes // 60
        mins = minutes % 60
        if mins == 0:
            return f"{hours}h"
        return f"{hours}h {mins}m"


transport_service = TransportService()
