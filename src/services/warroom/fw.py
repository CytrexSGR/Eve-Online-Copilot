"""Faction Warfare service - business logic for FW system status tracking."""

from datetime import datetime
from typing import List, Dict
from collections import Counter

from src.integrations.esi.client import ESIClient
from src.services.warroom.repository import WarRoomRepository
from src.services.warroom.models import FWSystemStatus, FWHotspot, FWStats
from src.core.exceptions import ESIError, RepositoryError, ExternalAPIError


class FactionWarfareService:
    """
    Faction Warfare Service handles FW system status tracking and hotspot detection.

    This service combines the ESI Client (for fetching FW data)
    with the WarRoom Repository (for database operations).

    Responsibilities:
    - Fetch FW system status from ESI
    - Store and update FW system data in database
    - Identify contested systems (hotspots)
    - Calculate FW statistics and faction breakdown
    """

    # Faction ID to name mapping
    FACTIONS = {
        500001: "Caldari State",
        500002: "Minmatar Republic",
        500003: "Amarr Empire",
        500004: "Gallente Federation",
    }

    def __init__(self, repository: WarRoomRepository, esi_client: ESIClient):
        """
        Initialize Faction Warfare Service with dependencies.

        Args:
            repository: WarRoom repository for database operations
            esi_client: ESI API client for fetching FW data
        """
        self.repository = repository
        self.esi_client = esi_client

    def fetch_fw_systems(self) -> List[FWSystemStatus]:
        """
        Fetch all FW system status from ESI.

        ESI Endpoint: GET /fw/systems/

        Returns:
            List[FWSystemStatus]: List of FW system status models

        Raises:
            ESIError: If ESI API call fails

        Example:
            >>> service = FactionWarfareService(repository, esi_client)
            >>> systems = await service.fetch_fw_systems()
            >>> print(f"Found {len(systems)} FW systems")
        """
        try:
            # Fetch from ESI
            esi_data = self.esi_client.get("/fw/systems/")

            # Convert to models
            systems = []
            for item in esi_data:
                try:
                    system = FWSystemStatus(
                        system_id=item["solar_system_id"],
                        owning_faction_id=item["owning_faction_id"],
                        occupying_faction_id=item["occupying_faction_id"],
                        contested=item["contested"],
                        victory_points=item["victory_points"],
                        victory_points_threshold=item["victory_points_threshold"],
                    )
                    systems.append(system)

                except (KeyError, ValueError):
                    # Skip invalid entries but continue processing
                    continue

            return systems

        except ExternalAPIError as e:
            # Convert to ESIError for consistency
            raise ESIError(message=str(e), status_code=e.status_code) from e
        except Exception as e:
            raise ESIError(message=f"Failed to fetch FW systems: {str(e)}") from e

    def update_fw_systems(self) -> int:
        """
        Fetch FW systems from ESI and store in database.

        This method orchestrates the complete update workflow:
        1. Fetch FW systems from ESI API
        2. Store systems in database (upsert)
        3. Return number of systems stored

        Returns:
            int: Number of systems stored

        Raises:
            ESIError: If ESI API call fails
            RepositoryError: If database operation fails

        Example:
            >>> service = FactionWarfareService(repository, esi_client)
            >>> count = await service.update_fw_systems()
            >>> print(f"Updated {count} FW systems")
        """
        # Fetch from ESI
        systems = self.fetch_fw_systems()

        # Store in database
        count = self.repository.store_fw_systems(systems)

        return count

    def get_fw_hotspots(self, min_progress: float = 50.0) -> List[FWHotspot]:
        """
        Get highly contested FW systems (hotspots).

        Args:
            min_progress: Minimum contest progress percentage (0-100, default: 50.0)

        Returns:
            List[FWHotspot]: List of hotspot systems with details

        Raises:
            RepositoryError: If database operation fails

        Example:
            >>> service = FactionWarfareService(repository, esi_client)
            >>> hotspots = service.get_fw_hotspots(min_progress=90.0)
            >>> print(f"Found {len(hotspots)} critical systems")
        """
        # Get hotspots from repository
        hotspot_data = self.repository.get_fw_hotspots(min_progress=min_progress)

        # Convert to models
        hotspots = []
        for data in hotspot_data:
            try:
                progress = float(data.get("progress_percent", 0.0))

                # Get faction names from IDs
                owner_faction_id = data.get("owning_faction_id")
                occupier_faction_id = data.get("occupying_faction_id")
                owner_faction_name = self.FACTIONS.get(owner_faction_id, f"Faction {owner_faction_id}")
                occupier_faction_name = self.FACTIONS.get(occupier_faction_id, f"Faction {occupier_faction_id}")

                hotspot = FWHotspot(
                    system_id=data["system_id"],
                    system_name=data.get("system_name"),
                    contested=data["contested"],
                    victory_points=data["victory_points"],
                    progress_percent=progress,
                    is_critical=(progress >= 90.0),  # Critical if >= 90%
                    owner_faction_name=owner_faction_name,
                    occupier_faction_name=occupier_faction_name,
                )
                hotspots.append(hotspot)

            except (KeyError, ValueError):
                # Skip invalid entries
                continue

        return hotspots

    def get_fw_stats(self) -> FWStats:
        """
        Get FW statistics including faction breakdown.

        Returns:
            FWStats: Statistics with total systems, contested count, and faction breakdown

        Raises:
            RepositoryError: If database operation fails

        Example:
            >>> service = FactionWarfareService(repository, esi_client)
            >>> stats = service.get_fw_stats()
            >>> print(f"Total: {stats.total_systems}, Contested: {stats.contested_count}")
        """
        # Get all FW systems from repository
        systems_data = self.repository.get_fw_systems(contested_only=False)

        # Calculate statistics
        total_systems = len(systems_data)
        contested_count = 0
        owning_factions = []

        for system in systems_data:
            # Count contested systems
            if system.get("contested") != "uncontested":
                contested_count += 1

            # Track owning faction
            owning_faction_id = system.get("owning_faction_id")
            if owning_faction_id:
                owning_factions.append(owning_faction_id)

        # Calculate faction breakdown
        faction_breakdown = dict(Counter(owning_factions))

        return FWStats(
            total_systems=total_systems,
            contested_count=contested_count,
            faction_breakdown=faction_breakdown,
        )
