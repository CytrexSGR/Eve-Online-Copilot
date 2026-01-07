"""
Route calculation service using SDE jump data
A* pathfinding algorithm with HighSec filtering
"""

from src.database import get_db_connection
from psycopg2.extras import RealDictCursor
from typing import List, Optional, Dict
from heapq import heappush, heappop
from itertools import permutations


# Trade hub system IDs
TRADE_HUB_SYSTEMS = {
    'jita': 30000142,
    'amarr': 30002187,
    'rens': 30002510,
    'dodixie': 30002659,
    'hek': 30002053,
    'isikemi': 30001365,  # Home base for Minimal Industries
}

# Reverse lookup
SYSTEM_ID_TO_HUB = {v: k for k, v in TRADE_HUB_SYSTEMS.items()}


class RouteService:
    def __init__(self):
        self._graph: Optional[Dict[int, List[int]]] = None
        self._systems: Optional[Dict[int, dict]] = None
        self._loaded = False

    def _load_graph(self):
        """Load jump graph from database (lazy loading)"""
        if self._loaded:
            return

        self._graph = {}
        self._systems = {}

        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Load systems with security
                cur.execute('''
                    SELECT "solarSystemID", "solarSystemName", "security", "regionID"
                    FROM "mapSolarSystems"
                ''')
                for row in cur.fetchall():
                    self._systems[row['solarSystemID']] = {
                        'name': row['solarSystemName'],
                        'security': float(row['security']),
                        'region_id': row['regionID']
                    }

                # Load jumps (bidirectional graph)
                cur.execute('''
                    SELECT "fromSolarSystemID", "toSolarSystemID"
                    FROM "mapSolarSystemJumps"
                ''')
                for row in cur.fetchall():
                    from_id = row['fromSolarSystemID']
                    to_id = row['toSolarSystemID']

                    if from_id not in self._graph:
                        self._graph[from_id] = []
                    self._graph[from_id].append(to_id)

        self._loaded = True
        print(f"Route graph loaded: {len(self._systems)} systems, {sum(len(v) for v in self._graph.values())} jumps")

    def find_route(
        self,
        from_system_id: int,
        to_system_id: int,
        avoid_lowsec: bool = True,
        avoid_nullsec: bool = True,
        min_security: float = 0.5
    ) -> Optional[List[dict]]:
        """
        Find route using A* algorithm

        Args:
            from_system_id: Starting system ID
            to_system_id: Destination system ID
            avoid_lowsec: Avoid systems with security < 0.5
            avoid_nullsec: Avoid systems with security < 0.0
            min_security: Minimum security level (overrides avoid_lowsec/nullsec)

        Returns:
            List of system dicts with route info, or None if no route found
        """
        self._load_graph()

        if from_system_id not in self._systems or to_system_id not in self._systems:
            return None

        # Determine security threshold
        if avoid_lowsec:
            min_sec = max(min_security, 0.45)  # 0.45 rounds to 0.5 in EVE
        elif avoid_nullsec:
            min_sec = 0.0
        else:
            min_sec = -1.0

        # A* implementation
        # Priority queue: (f_score, g_score, current_system, path)
        start_h = self._heuristic(from_system_id, to_system_id)
        open_set = [(start_h, 0, from_system_id, [from_system_id])]
        visited = set()

        while open_set:
            _, g_score, current, path = heappop(open_set)

            if current == to_system_id:
                return self._build_route_info(path)

            if current in visited:
                continue
            visited.add(current)

            for neighbor in self._graph.get(current, []):
                if neighbor in visited:
                    continue

                # Check security filter
                neighbor_sec = self._systems[neighbor]['security']
                if neighbor_sec < min_sec:
                    continue

                new_g = g_score + 1
                new_h = self._heuristic(neighbor, to_system_id)
                new_f = new_g + new_h
                new_path = path + [neighbor]

                heappush(open_set, (new_f, new_g, neighbor, new_path))

        return None  # No route found

    def _heuristic(self, from_id: int, to_id: int) -> int:
        """
        Heuristic for A* - using region-based estimation
        Systems in same region are closer
        """
        if from_id == to_id:
            return 0

        from_region = self._systems.get(from_id, {}).get('region_id')
        to_region = self._systems.get(to_id, {}).get('region_id')

        if from_region == to_region:
            return 1  # Same region, likely close
        return 5  # Different region, estimate higher

    def _build_route_info(self, path: List[int]) -> List[dict]:
        """Build detailed route information"""
        return [
            {
                'system_id': sys_id,
                'system_name': self._systems[sys_id]['name'],
                'security': round(self._systems[sys_id]['security'], 2),
                'region_id': self._systems[sys_id]['region_id'],
                'jump_number': i,
                'is_trade_hub': sys_id in SYSTEM_ID_TO_HUB,
                'hub_name': SYSTEM_ID_TO_HUB.get(sys_id)
            }
            for i, sys_id in enumerate(path)
        ]

    def get_system_by_name(self, name: str) -> Optional[dict]:
        """Find system by name (case-insensitive)"""
        self._load_graph()
        name_lower = name.lower()
        for sys_id, info in self._systems.items():
            if info['name'].lower() == name_lower:
                return {
                    'system_id': sys_id,
                    'system_name': info['name'],
                    'security': round(info['security'], 2),
                    'region_id': info['region_id'],
                    'is_trade_hub': sys_id in SYSTEM_ID_TO_HUB,
                    'hub_name': SYSTEM_ID_TO_HUB.get(sys_id)
                }
        return None

    def search_systems(self, query: str, limit: int = 10) -> List[dict]:
        """Search systems by partial name"""
        self._load_graph()
        query_lower = query.lower()
        results = []

        for sys_id, info in self._systems.items():
            if query_lower in info['name'].lower():
                results.append({
                    'system_id': sys_id,
                    'system_name': info['name'],
                    'security': round(info['security'], 2),
                    'is_trade_hub': sys_id in SYSTEM_ID_TO_HUB
                })
                if len(results) >= limit:
                    break

        return results

    def calculate_travel_time(
        self,
        route: List[dict],
        align_time_seconds: int = 10,
        warp_time_per_system: int = 30
    ) -> dict:
        """
        Estimate travel time for a route

        Args:
            route: Route from find_route()
            align_time_seconds: Ship align time (default 10s for cruiser)
            warp_time_per_system: Average warp time per system

        Returns:
            Travel time info dict
        """
        jumps = len(route) - 1 if route else 0
        total_seconds = jumps * (align_time_seconds + warp_time_per_system)

        return {
            'jumps': jumps,
            'estimated_seconds': total_seconds,
            'estimated_minutes': round(total_seconds / 60, 1),
            'formatted': f"{jumps} jumps (~{round(total_seconds/60)} min)"
        }

    def get_hub_distances(self, from_system: str = 'isikemi') -> dict:
        """
        Get distances from a system to all trade hubs

        Args:
            from_system: System name or hub key (default: isikemi)

        Returns:
            Dict of hub distances with jump counts
        """
        self._load_graph()

        # Resolve from_system
        from_id = TRADE_HUB_SYSTEMS.get(from_system.lower())
        if not from_id:
            sys_info = self.get_system_by_name(from_system)
            from_id = sys_info['system_id'] if sys_info else None

        if not from_id:
            return {'error': f'System not found: {from_system}'}

        distances = {}
        for hub_name, hub_id in TRADE_HUB_SYSTEMS.items():
            if hub_id == from_id:
                distances[hub_name] = {
                    'jumps': 0,
                    'time': '0 min',
                    'reachable': True
                }
                continue

            route = self.find_route(from_id, hub_id, avoid_lowsec=True)
            if route:
                travel = self.calculate_travel_time(route)
                distances[hub_name] = {
                    'jumps': travel['jumps'],
                    'time': travel['formatted'],
                    'reachable': True
                }
            else:
                distances[hub_name] = {
                    'jumps': None,
                    'time': 'No HighSec route',
                    'reachable': False
                }

        return {
            'from_system': from_system,
            'from_system_id': from_id,
            'distances': distances
        }

    def calculate_multi_hub_route(self, from_system: str, hub_regions: List[str], include_systems: bool = True, return_home: bool = True) -> dict:
        """
        Calculate optimal route through multiple trade hubs.
        Uses brute-force TSP (fine for up to 5 hubs).

        Args:
            from_system: Starting system name
            hub_regions: List of region keys (e.g., ['the_forge', 'domain'])

        Returns:
            Optimal route with total jumps and leg details
        """
        self._load_graph()

        # Map region keys to hub names
        REGION_TO_HUB = {
            'the_forge': 'jita',
            'domain': 'amarr',
            'heimatar': 'rens',
            'sinq_laison': 'dodixie',
            'metropolis': 'hek',
        }

        # Get unique hubs to visit
        hubs_to_visit = list(set(REGION_TO_HUB.get(r, r) for r in hub_regions if r in REGION_TO_HUB))

        if not hubs_to_visit:
            return {'error': 'No valid hubs specified', 'total_jumps': 0, 'route': []}

        # Resolve starting system
        from_id = TRADE_HUB_SYSTEMS.get(from_system.lower())
        if not from_id:
            sys_info = self.get_system_by_name(from_system)
            from_id = sys_info['system_id'] if sys_info else None

        if not from_id:
            return {'error': f'System not found: {from_system}', 'total_jumps': 0, 'route': []}

        # If only one hub, simple route
        if len(hubs_to_visit) == 1:
            hub_id = TRADE_HUB_SYSTEMS[hubs_to_visit[0]]
            route = self.find_route(from_id, hub_id, avoid_lowsec=True)
            if route:
                jumps = len(route) - 1
                leg = {
                    'from': from_system,
                    'to': hubs_to_visit[0].title(),
                    'jumps': jumps
                }
                if include_systems:
                    leg['systems'] = [
                        {'name': s['system_name'], 'security': s['security']}
                        for s in route
                    ]
                route_legs = [leg]
                total_jumps = jumps
                order = [from_system, hubs_to_visit[0].title()]

                # Add return trip if requested
                if return_home:
                    return_route = self.find_route(hub_id, from_id, avoid_lowsec=True)
                    if return_route:
                        return_jumps = len(return_route) - 1
                        return_leg = {
                            'from': hubs_to_visit[0].title(),
                            'to': from_system,
                            'jumps': return_jumps
                        }
                        if include_systems:
                            return_leg['systems'] = [
                                {'name': s['system_name'], 'security': s['security']}
                                for s in return_route
                            ]
                        route_legs.append(return_leg)
                        total_jumps += return_jumps
                        order.append(from_system)

                return {
                    'total_jumps': total_jumps,
                    'route': route_legs,
                    'order': order,
                    'return_home': return_home
                }
            return {'error': 'No route found', 'total_jumps': 0, 'route': []}

        # Pre-calculate distances between all relevant systems
        all_systems = [from_system.lower()] + hubs_to_visit
        distances = {}
        routes = {}  # Store full routes for system list

        for i, sys1 in enumerate(all_systems):
            sys1_id = TRADE_HUB_SYSTEMS.get(sys1, from_id if sys1 == from_system.lower() else None)
            for sys2 in all_systems[i+1:]:
                sys2_id = TRADE_HUB_SYSTEMS.get(sys2)
                if sys1_id and sys2_id:
                    route = self.find_route(sys1_id, sys2_id, avoid_lowsec=True)
                    dist = len(route) - 1 if route else 999
                    distances[(sys1, sys2)] = dist
                    distances[(sys2, sys1)] = dist
                    if route and include_systems:
                        routes[(sys1, sys2)] = route
                        routes[(sys2, sys1)] = list(reversed(route))

        # Try all permutations of hubs (TSP)
        best_order = None
        best_total = float('inf')

        for perm in permutations(hubs_to_visit):
            total = 0
            prev = from_system.lower()
            for hub in perm:
                total += distances.get((prev, hub), 999)
                prev = hub
            if total < best_total:
                best_total = total
                best_order = perm

        if not best_order:
            return {'error': 'Could not calculate route', 'total_jumps': 0, 'route': []}

        # Build route details
        route_legs = []
        prev = from_system
        prev_key = from_system.lower()

        for hub in best_order:
            jumps = distances.get((prev_key, hub), 0)
            leg = {
                'from': prev.title() if prev != from_system else from_system,
                'to': hub.title(),
                'jumps': jumps
            }
            # Add system names if requested
            if include_systems and (prev_key, hub) in routes:
                leg['systems'] = [
                    {
                        'name': s['system_name'],
                        'security': s['security']
                    }
                    for s in routes[(prev_key, hub)]
                ]
            route_legs.append(leg)
            prev = hub
            prev_key = hub

        total_jumps = best_total
        order = [from_system] + [h.title() for h in best_order]

        # Add return trip if requested
        if return_home:
            last_hub = best_order[-1]
            last_hub_id = TRADE_HUB_SYSTEMS[last_hub]
            return_route = self.find_route(last_hub_id, from_id, avoid_lowsec=True)
            if return_route:
                return_jumps = len(return_route) - 1
                return_leg = {
                    'from': last_hub.title(),
                    'to': from_system,
                    'jumps': return_jumps
                }
                if include_systems:
                    return_leg['systems'] = [
                        {'name': s['system_name'], 'security': s['security']}
                        for s in return_route
                    ]
                route_legs.append(return_leg)
                total_jumps += return_jumps
                order.append(from_system)

        return {
            'total_jumps': total_jumps,
            'route': route_legs,
            'order': order,
            'return_home': return_home
        }


    def get_route_with_danger(
        self,
        from_system_id: int,
        to_system_id: int,
        avoid_lowsec: bool = True,
        avoid_nullsec: bool = True
    ) -> Optional[dict]:
        """
        Find route with danger scores for each system.
        Returns route with kill activity overlay.
        """
        from war_analyzer import war_analyzer

        route = self.find_route(from_system_id, to_system_id, avoid_lowsec, avoid_nullsec)

        if not route:
            return None

        # Add danger scores
        total_danger = 0
        dangerous_systems = []

        for system in route:
            danger = war_analyzer.get_system_danger_score(system['system_id'], days=1)
            system['danger_score'] = danger['danger_score']
            system['kills_24h'] = danger['kills_24h']
            total_danger += danger['danger_score']

            if danger['danger_score'] >= 5:
                dangerous_systems.append({
                    'name': system['system_name'],
                    'kills': danger['kills_24h'],
                    'score': danger['danger_score']
                })

        return {
            'route': route,
            'total_jumps': len(route) - 1,
            'total_danger_score': total_danger,
            'average_danger': round(total_danger / len(route), 1) if route else 0,
            'dangerous_systems': dangerous_systems,
            'warning': len(dangerous_systems) > 0
        }


# Singleton instance
route_service = RouteService()
