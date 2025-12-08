"""Sovereignty service - business logic for sovereignty campaign tracking."""

from datetime import datetime, timezone, timedelta
from typing import List, Optional

from src.integrations.esi.client import ESIClient
from src.services.warroom.repository import WarRoomRepository
from src.services.warroom.models import SovCampaign, SovCampaignList
from src.core.exceptions import ESIError, RepositoryError, ExternalAPIError


class SovereigntyService:
    """
    Sovereignty Service handles sovereignty campaign tracking.

    This service combines the ESI Client (for fetching campaign data)
    with the WarRoom Repository (for database operations).

    Responsibilities:
    - Fetch sovereignty campaigns from ESI
    - Store and update campaign data in database
    - Provide campaign queries with optional region filtering
    - Clean up old/expired campaigns
    """

    def __init__(self, repository: WarRoomRepository, esi_client: ESIClient):
        """
        Initialize Sovereignty Service with dependencies.

        Args:
            repository: WarRoom repository for database operations
            esi_client: ESI API client for fetching campaign data
        """
        self.repository = repository
        self.esi_client = esi_client

    def fetch_campaigns(self) -> List[SovCampaign]:
        """
        Fetch all active sovereignty campaigns from ESI.

        ESI Endpoint: GET /sovereignty/campaigns/

        Returns:
            List[SovCampaign]: List of sovereignty campaign models

        Raises:
            ESIError: If ESI API call fails

        Example:
            >>> service = SovereigntyService(repository, esi_client)
            >>> campaigns = await service.fetch_campaigns()
            >>> print(f"Found {len(campaigns)} active campaigns")
        """
        try:
            # Fetch from ESI
            esi_data = self.esi_client.get("/sovereignty/campaigns/")

            # Convert to models
            campaigns = []
            for item in esi_data:
                try:
                    # Parse start_time from ISO format
                    start_time_str = item.get("start_time")
                    if start_time_str:
                        # ESI returns ISO 8601 format like "2025-12-07T18:00:00Z"
                        start_time = datetime.fromisoformat(
                            start_time_str.replace('Z', '+00:00')
                        )
                    else:
                        # Skip campaigns without start_time
                        continue

                    campaign = SovCampaign(
                        campaign_id=item["campaign_id"],
                        system_id=item["solar_system_id"],
                        constellation_id=item["constellation_id"],
                        structure_type_id=item["structure_type_id"],
                        event_type=item["event_type"],
                        start_time=start_time,
                        defender_id=item["defender_id"],
                        defender_score=item["defender_score"],
                        attackers_score=item["attackers_score"],
                        structure_id=item.get("structure_id"),
                    )
                    campaigns.append(campaign)

                except (KeyError, ValueError) as e:
                    # Skip invalid entries but continue processing
                    continue

            return campaigns

        except ExternalAPIError as e:
            # Convert to ESIError for consistency
            raise ESIError(message=str(e), status_code=e.status_code) from e
        except Exception as e:
            raise ESIError(message=f"Failed to fetch campaigns: {str(e)}") from e

    def update_campaigns(self) -> int:
        """
        Fetch campaigns from ESI and store in database.

        This method orchestrates the complete update workflow:
        1. Fetch campaigns from ESI API
        2. Store campaigns in database (upsert)
        3. Return number of campaigns stored

        Returns:
            int: Number of campaigns stored

        Raises:
            ESIError: If ESI API call fails
            RepositoryError: If database operation fails

        Example:
            >>> service = SovereigntyService(repository, esi_client)
            >>> count = await service.update_campaigns()
            >>> print(f"Updated {count} campaigns")
        """
        # Fetch from ESI
        campaigns = self.fetch_campaigns()

        # Store in database
        count = self.repository.store_campaigns(campaigns)

        return count

    def get_campaigns(self, region_id: Optional[int] = None) -> SovCampaignList:
        """
        Get sovereignty campaigns from database.

        Args:
            region_id: Optional region ID to filter by

        Returns:
            SovCampaignList: List of campaigns with count

        Raises:
            RepositoryError: If database operation fails

        Example:
            >>> service = SovereigntyService(repository, esi_client)
            >>> campaigns = service.get_campaigns(region_id=10000002)
            >>> print(f"Found {campaigns.count} campaigns in The Forge")
        """
        # Get campaigns from repository
        campaign_data = self.repository.get_campaigns(region_id=region_id)

        # Convert to models
        campaigns = []
        for data in campaign_data:
            try:
                campaign = SovCampaign(
                    campaign_id=data["campaign_id"],
                    system_id=data["system_id"],
                    constellation_id=data["constellation_id"],
                    structure_type_id=data["structure_type_id"],
                    event_type=data["event_type"],
                    start_time=data["start_time"],
                    defender_id=data["defender_id"],
                    defender_score=data["defender_score"],
                    attackers_score=data["attackers_score"],
                    structure_id=data.get("structure_id"),
                )
                campaigns.append(campaign)
            except (KeyError, ValueError):
                # Skip invalid entries
                continue

        return SovCampaignList(campaigns=campaigns, count=len(campaigns))

    def get_upcoming_battles(self, hours: int = 48) -> List[SovCampaign]:
        """
        Get sovereignty campaigns starting within the next X hours.

        Args:
            hours: Number of hours to look ahead (default: 48)

        Returns:
            List[SovCampaign]: List of upcoming campaigns sorted by start time

        Raises:
            RepositoryError: If database operation fails

        Example:
            >>> service = SovereigntyService(repository, esi_client)
            >>> battles = service.get_upcoming_battles(hours=48)
            >>> print(f"Found {len(battles)} battles in next 48 hours")
        """
        # Get all campaigns from database
        all_campaigns = self.get_campaigns(region_id=None)

        # Calculate time window
        now = datetime.now(timezone.utc)
        future_cutoff = now + timedelta(hours=hours)

        # Filter campaigns starting within the time window
        upcoming = []
        for campaign in all_campaigns.campaigns:
            # Make start_time timezone-aware if it's naive
            start_time = campaign.start_time
            if start_time.tzinfo is None:
                start_time = start_time.replace(tzinfo=timezone.utc)

            # Include campaigns that haven't started yet and start within the window
            if now <= start_time <= future_cutoff:
                upcoming.append(campaign)

        # Sort by start time (earliest first)
        upcoming.sort(key=lambda c: c.start_time)

        return upcoming

    def cleanup_old_campaigns(self, days: int = 1) -> int:
        """
        Delete campaigns older than specified days.

        Args:
            days: Number of days to retain (default: 1)

        Returns:
            int: Number of campaigns deleted

        Raises:
            RepositoryError: If database operation fails

        Example:
            >>> service = SovereigntyService(repository, esi_client)
            >>> deleted = service.cleanup_old_campaigns(days=1)
            >>> print(f"Deleted {deleted} old campaigns")
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        return self.repository.cleanup_old_campaigns(cutoff_date)
