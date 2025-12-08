"""War Analyzer service - demand analysis, doctrine detection, and conflict intelligence."""

from typing import List, Optional

from src.core.config import get_settings
from src.services.warroom.repository import WarRoomRepository
from src.services.warroom.analyzer_models import (
    DemandAnalysis,
    DemandItem,
    HeatmapPoint,
    DoctrineDetection,
    DangerScore,
    ConflictIntel,
)


class WarAnalyzer:
    """War Analyzer service for demand analysis and combat intelligence."""

    def __init__(self, repository: WarRoomRepository):
        """
        Initialize War Analyzer service.

        Args:
            repository: War Room repository instance
        """
        self.repository = repository

    def analyze_demand(self, region_id: int, days: int) -> DemandAnalysis:
        """
        Analyze demand for ships and items in a region.

        Combines ship losses and item losses with market stock data to identify
        market gaps where demand exceeds supply.

        Args:
            region_id: Region ID to analyze
            days: Number of days to look back

        Returns:
            Complete demand analysis with market gaps

        Raises:
            RepositoryError: If database operation fails
        """
        # Get raw data from repository
        data = self.repository.get_demand_analysis(region_id=region_id, days=days)

        # Convert to DemandItem models with gap calculation
        ships_lost = [
            DemandItem(
                type_id=ship["type_id"],
                name=ship["name"],
                quantity=int(ship["quantity"]),
                market_stock=int(ship["market_stock"]),
                gap=max(0, int(ship["quantity"]) - int(ship["market_stock"])),
            )
            for ship in data["ships"]
        ]

        items_lost = [
            DemandItem(
                type_id=item["type_id"],
                name=item["name"],
                quantity=int(item["quantity"]),
                market_stock=int(item["market_stock"]),
                gap=max(0, int(item["quantity"]) - int(item["market_stock"])),
            )
            for item in data["items"]
        ]

        # Combine and find market gaps (where gap > 0)
        all_items = ships_lost + items_lost
        market_gaps = [item for item in all_items if item.gap > 0]

        # Sort by gap size descending and take top 15
        market_gaps.sort(key=lambda x: x.gap, reverse=True)
        market_gaps = market_gaps[:15]

        return DemandAnalysis(
            region_id=region_id,
            days=days,
            ships_lost=ships_lost,
            items_lost=items_lost,
            market_gaps=market_gaps,
        )

    def get_heatmap_data(self, days: int, min_kills: Optional[int] = None) -> List[HeatmapPoint]:
        """
        Get kill heatmap data with system coordinates.

        Returns systems with significant kill activity, including coordinates
        for visualization on a galaxy map.

        Args:
            days: Number of days to look back
            min_kills: Minimum kills to include system (uses config default if None)

        Returns:
            List of heatmap points with coordinates and kill counts

        Raises:
            RepositoryError: If database operation fails
        """
        if min_kills is None:
            min_kills = get_settings().war_heatmap_min_kills

        # Get raw data from repository
        data = self.repository.get_heatmap_data(days=days, min_kills=min_kills)

        # Convert to HeatmapPoint models
        points = [
            HeatmapPoint(
                system_id=point["system_id"],
                name=point["name"],
                region_id=point["region_id"],
                region=point["region"],
                security=round(float(point["security"]), 2) if point["security"] else 0.0,
                x=round(float(point["x"]), 2) if point["x"] else 0.0,
                z=round(float(point["z"]), 2) if point["z"] else 0.0,
                kills=int(point["kills"]),
            )
            for point in data
        ]

        # Already sorted by kills DESC from repository
        return points

    def detect_doctrines(self, region_id: int, days: int) -> List[DoctrineDetection]:
        """
        Detect fleet doctrines from bulk ship losses.

        A doctrine is detected when a large number of the same ship type is lost
        in the same system on the same day (indicating a fleet engagement).

        Args:
            region_id: Region ID to analyze
            days: Number of days to look back

        Returns:
            List of detected doctrines with fleet composition

        Raises:
            RepositoryError: If database operation fails
        """
        min_size = get_settings().war_doctrine_min_fleet_size

        # Get raw data from repository
        data = self.repository.get_doctrine_losses(
            region_id=region_id, days=days, min_size=min_size
        )

        # Convert to DoctrineDetection models
        doctrines = [
            DoctrineDetection(
                date=doctrine["date"],
                system_id=doctrine["system_id"],
                system_name=doctrine["system_name"],
                ship_type_id=doctrine["ship_type_id"],
                ship_name=doctrine["ship_name"],
                fleet_size=int(doctrine["fleet_size"]),
                estimated_alliance=None,  # Could be enhanced with alliance tracking
            )
            for doctrine in data
        ]

        return doctrines

    def get_system_danger_score(self, system_id: int, days: int = 1) -> DangerScore:
        """
        Calculate danger score for a system based on recent kills.

        Higher scores indicate more dangerous systems. Score is currently
        a simple linear function of kill count.

        Args:
            system_id: Solar system ID
            days: Number of days to look back (default 1 for 24h)

        Returns:
            Danger score with kill count and danger flag

        Raises:
            RepositoryError: If database operation fails
        """
        # Get kill count from repository
        kills = self.repository.get_system_kills(system_id=system_id, days=days)

        # Simple linear scoring: danger_score = kills
        danger_score = kills

        # System is dangerous if score >= 5
        is_dangerous = danger_score >= 5

        return DangerScore(
            system_id=system_id,
            danger_score=danger_score,
            kills_24h=kills,
            is_dangerous=is_dangerous,
        )

    def get_conflict_intel(
        self, alliance_id: Optional[int] = None, days: int = 7
    ) -> List[ConflictIntel]:
        """
        Get alliance conflict intelligence.

        Tracks which alliances are fighting whom, total losses, and
        the geographic spread of conflicts.

        Args:
            alliance_id: Optional alliance ID to filter, None for all
            days: Number of days to look back

        Returns:
            List of conflict intelligence for alliances

        Raises:
            RepositoryError: If database operation fails
        """
        # Get raw data from repository
        data = self.repository.get_conflict_intel(alliance_id=alliance_id, days=days)

        # Convert to ConflictIntel models
        conflicts = [
            ConflictIntel(
                alliance_id=conflict["alliance_id"],
                alliance_name=str(conflict["alliance_name"]),
                enemy_alliances=conflict.get("enemy_alliances", []) or [],
                total_losses=int(conflict["total_losses"]),
                active_fronts=int(conflict["active_fronts"]),
            )
            for conflict in data
        ]

        return conflicts
