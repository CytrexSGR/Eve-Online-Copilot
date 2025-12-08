"""
Route Service

A* pathfinding and route calculation for EVE Online solar systems.
Provides route finding, travel time estimation, and TSP optimization for multi-hub routes.
"""

from typing import Dict, List, Optional, Protocol
from heapq import heappush, heappop
from itertools import permutations

from src.services.route.models import (
    SystemInfo,
    RouteSystemInfo,
    RouteResult,
    TravelTime,
    HubDistance,
    HubDistances,
    RouteLeg,
    MultiHubRoute,
    RouteWithDanger,
)
from src.services.route.constants import (
    TRADE_HUB_SYSTEMS,
    SYSTEM_ID_TO_HUB,
    REGION_TO_HUB,
)
from src.core.exceptions import EVECopilotError


class RouteRepository(Protocol):
    """
    Protocol for Route Repository

    Defines the interface for data access layer.
    This allows dependency injection and easy testing with mocks.
    """

    def get_systems(self) -> Dict[int, dict]:
        """Get all solar systems with their properties"""
        ...

    def get_graph(self) -> Dict[int, List[int]]:
        """Get jump graph (adjacency list)"""
        ...

    def get_system_by_id(self, system_id: int) -> Optional[dict]:
        """Get system by ID"""
        ...

    def get_system_by_name(self, name: str) -> Optional[dict]:
        """Get system by name (case-insensitive)"""
        ...

    def search_systems(self, query: str, limit: int = 10) -> List[dict]:
        """Search systems by partial name"""
        ...


class RouteService:
    """
    Route Service

    Provides A* pathfinding, route optimization, and travel calculations
    for EVE Online solar systems.
    """

    def __init__(self, repository: RouteRepository):
        """
        Initialize Route Service

        Args:
            repository: Data access layer for systems and jumps
        """
        self.repository = repository
        self._systems: Optional[Dict[int, dict]] = None
        self._graph: Optional[Dict[int, List[int]]] = None
        self._loaded = False

    def _load_graph(self) -> None:
        """
        Lazy load graph data from repository

        Raises:
            EVECopilotError: If graph loading fails
        """
        if self._loaded:
            return

        try:
            self._systems = self.repository.get_systems()
            self._graph = self.repository.get_graph()
            self._loaded = True
        except Exception as e:
            raise EVECopilotError(f"Failed to load route graph: {str(e)}") from e

    def find_route(
        self,
        from_id: int,
        to_id: int,
        avoid_lowsec: bool = True,
        avoid_nullsec: bool = True,
        min_security: float = 0.5
    ) -> Optional[RouteResult]:
        """
        Find route using A* algorithm

        Args:
            from_id: Starting system ID
            to_id: Destination system ID
            avoid_lowsec: Avoid systems with security < 0.5
            avoid_nullsec: Avoid systems with security < 0.0
            min_security: Minimum security level (overrides avoid flags)

        Returns:
            RouteResult with path and systems, or None if no route found
        """
        self._load_graph()

        # Validate systems exist
        if from_id not in self._systems or to_id not in self._systems:
            return None

        # Handle same system
        if from_id == to_id:
            system = self._build_route_system_info(from_id, 0)
            travel_time = TravelTime(
                jumps=0,
                estimated_seconds=0,
                estimated_minutes=0.0,
                formatted="0 jumps (~0 min)"
            )
            return RouteResult(
                systems=[system],
                total_jumps=0,
                travel_time=travel_time
            )

        # Determine security threshold
        if avoid_lowsec:
            min_sec = max(min_security, 0.45)  # 0.45 rounds to 0.5 in EVE
        elif avoid_nullsec:
            min_sec = max(min_security, 0.0)  # Respect min_security even when allowing lowsec
        else:
            min_sec = min_security if min_security > -1.0 else -1.0

        # A* implementation
        # Priority queue: (f_score, g_score, current_system, path)
        start_h = self._heuristic(from_id, to_id)
        open_set = [(start_h, 0, from_id, [from_id])]
        visited = set()

        while open_set:
            _, g_score, current, path = heappop(open_set)

            if current == to_id:
                # Build route result
                systems = [
                    self._build_route_system_info(sys_id, i)
                    for i, sys_id in enumerate(path)
                ]
                total_jumps = len(path) - 1
                travel_time = self._calculate_default_travel_time(total_jumps)

                return RouteResult(
                    systems=systems,
                    total_jumps=total_jumps,
                    travel_time=travel_time
                )

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
                new_h = self._heuristic(neighbor, to_id)
                new_f = new_g + new_h
                new_path = path + [neighbor]

                heappush(open_set, (new_f, new_g, neighbor, new_path))

        return None  # No route found

    def _heuristic(self, from_id: int, to_id: int) -> int:
        """
        Heuristic for A* - using region-based estimation

        Systems in same region are estimated to be closer.

        Args:
            from_id: Source system ID
            to_id: Target system ID

        Returns:
            Estimated distance (jumps)
        """
        if from_id == to_id:
            return 0

        from_region = self._systems.get(from_id, {}).get('region_id')
        to_region = self._systems.get(to_id, {}).get('region_id')

        if from_region == to_region:
            return 1  # Same region, likely close
        return 5  # Different region, estimate higher

    def _build_route_system_info(self, system_id: int, jump_number: int) -> RouteSystemInfo:
        """
        Build RouteSystemInfo from system data

        Args:
            system_id: System ID
            jump_number: Jump number in route (0-indexed)

        Returns:
            RouteSystemInfo object
        """
        sys_data = self._systems[system_id]
        is_hub = system_id in SYSTEM_ID_TO_HUB

        return RouteSystemInfo(
            system_id=system_id,
            name=sys_data['name'],
            security=round(sys_data['security'], 2),
            region_id=sys_data['region_id'],
            is_trade_hub=is_hub,
            hub_name=SYSTEM_ID_TO_HUB.get(system_id),
            jump_number=jump_number,
            danger_score=0.0,
            kills_24h=0
        )

    def _calculate_default_travel_time(self, jumps: int) -> TravelTime:
        """
        Calculate travel time with default parameters

        Args:
            jumps: Number of jumps

        Returns:
            TravelTime object
        """
        align_time = 10  # Default align time in seconds
        warp_time = 30   # Default warp time per system

        total_seconds = jumps * (align_time + warp_time)
        total_minutes = round(total_seconds / 60, 1)

        return TravelTime(
            jumps=jumps,
            estimated_seconds=total_seconds,
            estimated_minutes=total_minutes,
            formatted=f"{jumps} jumps (~{round(total_seconds/60)} min)"
        )

    def get_system_by_name(self, name: str) -> Optional[SystemInfo]:
        """
        Find system by name (case-insensitive)

        Args:
            name: System name to search for

        Returns:
            SystemInfo if found, None otherwise
        """
        self._load_graph()

        name_lower = name.lower()
        for sys_id, info in self._systems.items():
            if info['name'].lower() == name_lower:
                is_hub = sys_id in SYSTEM_ID_TO_HUB
                return SystemInfo(
                    system_id=sys_id,
                    name=info['name'],
                    security=round(info['security'], 2),
                    region_id=info['region_id'],
                    is_trade_hub=is_hub,
                    hub_name=SYSTEM_ID_TO_HUB.get(sys_id)
                )
        return None

    def search_systems(self, query: str, limit: int = 10) -> List[SystemInfo]:
        """
        Search systems by partial name

        Args:
            query: Search query (partial name match)
            limit: Maximum number of results

        Returns:
            List of matching SystemInfo objects
        """
        self._load_graph()

        query_lower = query.lower()
        results = []

        for sys_id, info in self._systems.items():
            if query_lower in info['name'].lower():
                is_hub = sys_id in SYSTEM_ID_TO_HUB
                results.append(SystemInfo(
                    system_id=sys_id,
                    name=info['name'],
                    security=round(info['security'], 2),
                    region_id=info['region_id'],
                    is_trade_hub=is_hub,
                    hub_name=SYSTEM_ID_TO_HUB.get(sys_id)
                ))
                if len(results) >= limit:
                    break

        return results

    def calculate_travel_time(
        self,
        route: Optional[RouteResult],
        align_time: int = 10,
        warp_time: int = 30
    ) -> TravelTime:
        """
        Estimate travel time for a route

        Args:
            route: Route from find_route() (can be None)
            align_time: Ship align time in seconds (default 10s for cruiser)
            warp_time: Average warp time per system (default 30s)

        Returns:
            TravelTime with jump count and time estimates
        """
        if route is None:
            return TravelTime(
                jumps=0,
                estimated_seconds=0,
                estimated_minutes=0.0,
                formatted="0 jumps (~0 min)"
            )

        jumps = route.total_jumps
        total_seconds = jumps * (align_time + warp_time)
        total_minutes = round(total_seconds / 60, 1)

        return TravelTime(
            jumps=jumps,
            estimated_seconds=total_seconds,
            estimated_minutes=total_minutes,
            formatted=f"{jumps} jumps (~{round(total_seconds/60)} min)"
        )

    def get_hub_distances(self, from_system: str = 'isikemi') -> HubDistances:
        """
        Get distances from a system to all trade hubs

        Args:
            from_system: System name or hub key (default: isikemi)

        Returns:
            HubDistances with jump counts to all hubs
        """
        self._load_graph()

        # Resolve from_system
        from_id = TRADE_HUB_SYSTEMS.get(from_system.lower())
        if not from_id:
            sys_info = self.get_system_by_name(from_system)
            from_id = sys_info.system_id if sys_info else None

        if not from_id:
            return HubDistances(
                from_system=from_system,
                from_system_id=0,
                distances={},
                error=f'System not found: {from_system}'
            )

        distances = {}
        for hub_name, hub_id in TRADE_HUB_SYSTEMS.items():
            if hub_id == from_id:
                distances[hub_name] = HubDistance(
                    jumps=0,
                    time='0 min',
                    reachable=True
                )
                continue

            route = self.find_route(from_id, hub_id, avoid_lowsec=True)
            if route:
                travel = self.calculate_travel_time(route)
                distances[hub_name] = HubDistance(
                    jumps=travel.jumps,
                    time=travel.formatted,
                    reachable=True
                )
            else:
                distances[hub_name] = HubDistance(
                    jumps=None,
                    time='No HighSec route',
                    reachable=False
                )

        return HubDistances(
            from_system=from_system,
            from_system_id=from_id,
            distances=distances
        )

    def calculate_multi_hub_route(
        self,
        from_system: str,
        hub_regions: List[str],
        include_systems: bool = True,
        return_home: bool = True
    ) -> MultiHubRoute:
        """
        Calculate optimal route through multiple trade hubs

        Uses brute-force TSP for optimal ordering (fine for up to 5 hubs).

        Args:
            from_system: Starting system name
            hub_regions: List of hub names or region keys to visit
            include_systems: Include detailed system list in legs
            return_home: Add return leg to starting system

        Returns:
            MultiHubRoute with optimal order and total jumps
        """
        self._load_graph()

        # Map region keys to hub names
        hubs_to_visit = []
        for region in hub_regions:
            hub = REGION_TO_HUB.get(region, region)
            if hub in TRADE_HUB_SYSTEMS:
                hubs_to_visit.append(hub)

        # Remove duplicates
        hubs_to_visit = list(set(hubs_to_visit))

        if not hubs_to_visit:
            return MultiHubRoute(
                total_jumps=0,
                route_legs=[],
                order=[],
                return_home=return_home
            )

        # Resolve starting system
        from_id = TRADE_HUB_SYSTEMS.get(from_system.lower())
        if not from_id:
            sys_info = self.get_system_by_name(from_system)
            from_id = sys_info.system_id if sys_info else None

        if not from_id:
            return MultiHubRoute(
                total_jumps=0,
                route_legs=[],
                order=[],
                return_home=return_home
            )

        # Single hub case - simple route
        if len(hubs_to_visit) == 1:
            return self._single_hub_route(
                from_system, from_id, hubs_to_visit[0],
                include_systems, return_home
            )

        # Multi-hub case - TSP optimization
        return self._tsp_multi_hub_route(
            from_system, from_id, hubs_to_visit,
            include_systems, return_home
        )

    def _single_hub_route(
        self,
        from_system: str,
        from_id: int,
        hub: str,
        include_systems: bool,
        return_home: bool
    ) -> MultiHubRoute:
        """Helper for single hub route"""
        hub_id = TRADE_HUB_SYSTEMS[hub]
        route = self.find_route(from_id, hub_id, avoid_lowsec=True)

        if not route:
            return MultiHubRoute(
                total_jumps=0,
                route_legs=[],
                order=[],
                return_home=return_home
            )

        jumps = route.total_jumps
        leg = RouteLeg(
            from_name=from_system,
            to_name=hub.title(),
            jumps=jumps,
            systems=self._extract_system_list(route) if include_systems else None
        )

        route_legs = [leg]
        total_jumps = jumps
        order = [from_system, hub.title()]

        # Add return trip if requested
        if return_home:
            return_route = self.find_route(hub_id, from_id, avoid_lowsec=True)
            if return_route:
                return_jumps = return_route.total_jumps
                return_leg = RouteLeg(
                    from_name=hub.title(),
                    to_name=from_system,
                    jumps=return_jumps,
                    systems=self._extract_system_list(return_route) if include_systems else None
                )
                route_legs.append(return_leg)
                total_jumps += return_jumps
                order.append(from_system)

        return MultiHubRoute(
            total_jumps=total_jumps,
            route_legs=route_legs,
            order=order,
            return_home=return_home
        )

    def _tsp_multi_hub_route(
        self,
        from_system: str,
        from_id: int,
        hubs_to_visit: List[str],
        include_systems: bool,
        return_home: bool
    ) -> MultiHubRoute:
        """Helper for TSP multi-hub optimization"""
        # Pre-calculate distances between all systems
        all_systems = [from_system.lower()] + hubs_to_visit
        distances = {}
        routes_cache = {}  # Cache full routes for system list

        for i, sys1 in enumerate(all_systems):
            sys1_id = TRADE_HUB_SYSTEMS.get(sys1, from_id if sys1 == from_system.lower() else None)
            for sys2 in all_systems[i+1:]:
                sys2_id = TRADE_HUB_SYSTEMS.get(sys2)
                if sys1_id and sys2_id:
                    route = self.find_route(sys1_id, sys2_id, avoid_lowsec=True)
                    dist = route.total_jumps if route else 999
                    distances[(sys1, sys2)] = dist
                    distances[(sys2, sys1)] = dist
                    if route and include_systems:
                        routes_cache[(sys1, sys2)] = route
                        # Reverse route for opposite direction
                        reversed_systems = list(reversed(route.systems))
                        reversed_route = RouteResult(
                            systems=reversed_systems,
                            total_jumps=route.total_jumps,
                            travel_time=route.travel_time
                        )
                        routes_cache[(sys2, sys1)] = reversed_route

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
            return MultiHubRoute(
                total_jumps=0,
                route_legs=[],
                order=[],
                return_home=return_home
            )

        # Build route details
        route_legs = []
        prev = from_system
        prev_key = from_system.lower()

        for hub in best_order:
            jumps = distances.get((prev_key, hub), 0)
            leg = RouteLeg(
                from_name=prev.title() if prev != from_system else from_system,
                to_name=hub.title(),
                jumps=jumps,
                systems=None
            )

            # Add system names if requested
            if include_systems and (prev_key, hub) in routes_cache:
                leg.systems = self._extract_system_list(routes_cache[(prev_key, hub)])

            route_legs.append(leg)
            prev = hub
            prev_key = hub

        total_jumps = int(best_total)
        order = [from_system] + [h.title() for h in best_order]

        # Add return trip if requested
        if return_home:
            last_hub = best_order[-1]
            last_hub_id = TRADE_HUB_SYSTEMS[last_hub]
            return_route = self.find_route(last_hub_id, from_id, avoid_lowsec=True)
            if return_route:
                return_jumps = return_route.total_jumps
                return_leg = RouteLeg(
                    from_name=last_hub.title(),
                    to_name=from_system,
                    jumps=return_jumps,
                    systems=self._extract_system_list(return_route) if include_systems else None
                )
                route_legs.append(return_leg)
                total_jumps += return_jumps
                order.append(from_system)

        return MultiHubRoute(
            total_jumps=total_jumps,
            route_legs=route_legs,
            order=order,
            return_home=return_home
        )

    def _extract_system_list(self, route: RouteResult) -> List[Dict]:
        """Extract system list from route for API compatibility"""
        return [
            {
                'name': sys.name,
                'security': sys.security
            }
            for sys in route.systems
        ]

    def get_route_with_danger(
        self,
        from_id: int,
        to_id: int,
        avoid_lowsec: bool = True,
        avoid_nullsec: bool = True
    ) -> Optional[RouteWithDanger]:
        """
        Find route with danger scores for each system

        NOTE: This requires war_analyzer integration which is pending.

        Args:
            from_id: Starting system ID
            to_id: Destination system ID
            avoid_lowsec: Avoid lowsec systems
            avoid_nullsec: Avoid nullsec systems

        Returns:
            RouteWithDanger with kill activity overlay

        Raises:
            NotImplementedError: Until war analyzer integration is complete
        """
        raise NotImplementedError("War analyzer integration pending")
