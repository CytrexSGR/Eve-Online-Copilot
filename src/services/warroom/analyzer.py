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
    RegionalSummary,
    TopShip,
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

    def get_regional_summary(self, days: int) -> List[RegionalSummary]:
        """
        Get summary of combat activity per region.

        Returns combat statistics aggregated by region, showing which regions
        have the most kill activity and ISK destroyed.

        Args:
            days: Number of days to look back

        Returns:
            List of regional summaries with combat statistics

        Raises:
            RepositoryError: If database operation fails
        """
        # Get raw data from repository
        data = self.repository.get_regional_summary(days=days)

        # Convert to RegionalSummary models
        summaries = [
            RegionalSummary(
                region_id=region["region_id"],
                region_name=region["region_name"],
                active_systems=int(region["active_systems"]),
                total_kills=int(region["total_kills"]),
                total_value=float(region["total_value"]) if region["total_value"] else 0.0,
            )
            for region in data
        ]

        return summaries

    def get_top_ships_galaxy(self, days: int, limit: int) -> List[TopShip]:
        """
        Get most destroyed ships across all regions.

        Returns the most frequently destroyed ship types galaxy-wide, useful
        for identifying current meta doctrines and popular fleet compositions.

        Args:
            days: Number of days to look back
            limit: Maximum number of ships to return

        Returns:
            List of top destroyed ships with quantities and values

        Raises:
            RepositoryError: If database operation fails
        """
        # Get raw data from repository
        data = self.repository.get_top_ships_galaxy(days=days, limit=limit)

        # Convert to TopShip models using aliases
        ships = [
            TopShip(
                ship_type_id=ship["ship_type_id"],
                name=ship["name"],
                ship_group=ship["ship_group"],
                total_lost=int(ship["total_lost"]),
                total_value=float(ship["total_value"]) if ship["total_value"] else 0.0,
            )
            for ship in data
        ]

        return ships

    def get_item_combat_stats(self, type_id: int, days: int) -> dict:
        """
        Get combat statistics for a specific item/ship type.

        Returns detailed combat stats including total destroyed, regions affected,
        systems affected, and top loss locations.

        Args:
            type_id: Item/ship type ID
            days: Number of days to look back

        Returns:
            Dictionary with combat statistics

        Raises:
            RepositoryError: If database operation fails
        """
        return self.repository.get_item_combat_stats(type_id=type_id, days=days)

    def get_alliance_conflicts(self, days: int, top: int) -> List[ConflictIntel]:
        """
        Get top alliance conflicts.

        Wrapper method for compatibility with router expectations.

        Args:
            days: Number of days to look back
            top: Maximum number of conflicts to return

        Returns:
            List of conflict intelligence for top alliances

        Raises:
            RepositoryError: If database operation fails
        """
        # Get all conflicts and limit to top N
        conflicts = self.get_conflict_intel(alliance_id=None, days=days)
        return conflicts[:top]
