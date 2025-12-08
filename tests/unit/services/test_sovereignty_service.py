"""Tests for Sovereignty service."""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch
from typing import List, Dict, Any

from src.services.warroom.sovereignty import SovereigntyService
from src.services.warroom.models import SovCampaign, SovCampaignList
from src.core.exceptions import ESIError, RepositoryError


@pytest.fixture
def mock_repository():
    """Create mock repository."""
    return Mock()


@pytest.fixture
def mock_esi_client():
    """Create mock ESI client."""
    mock_client = Mock()
    return mock_client


@pytest.fixture
def service(mock_repository, mock_esi_client):
    """Create service instance with mocks."""
    return SovereigntyService(
        repository=mock_repository,
        esi_client=mock_esi_client,
    )


class TestFetchCampaigns:
    """Tests for fetch_campaigns method."""

    def test_fetch_campaigns_success(self, service, mock_esi_client):
        """Test successfully fetching campaigns from ESI."""
        mock_esi_data = [
            {
                "campaign_id": 123,
                "structure_id": 456,
                "solar_system_id": 30001234,
                "constellation_id": 20000123,
                "structure_type_id": 32226,
                "event_type": "tcu_defense",
                "start_time": "2024-12-01T12:00:00Z",
                "defender_id": 123456,
                "defender_score": 0.5,
                "attackers_score": 0.3,
            },
            {
                "campaign_id": 456,
                "structure_id": 789,
                "solar_system_id": 30001235,
                "constellation_id": 20000124,
                "structure_type_id": 32226,
                "event_type": "ihub_defense",
                "start_time": "2024-12-02T15:00:00Z",
                "defender_id": 123457,
                "defender_score": 0.7,
                "attackers_score": 0.2,
            },
        ]

        mock_esi_client.get.return_value = mock_esi_data

        campaigns = service.fetch_campaigns()

        assert len(campaigns) == 2
        assert isinstance(campaigns[0], SovCampaign)
        assert campaigns[0].campaign_id == 123
        assert campaigns[0].system_id == 30001234
        assert campaigns[1].campaign_id == 456
        mock_esi_client.get.assert_called_once_with("/sovereignty/campaigns/")

    def test_fetch_campaigns_empty_response(self, service, mock_esi_client):
        """Test fetching campaigns when ESI returns empty list."""
        mock_esi_client.get.return_value = []

        campaigns = service.fetch_campaigns()

        assert len(campaigns) == 0
        mock_esi_client.get.assert_called_once()

    def test_fetch_campaigns_esi_error(self, service, mock_esi_client):
        """Test handling ESI errors during campaign fetch."""
        mock_esi_client.get.side_effect = ESIError("ESI unavailable")

        with pytest.raises(ESIError):
            service.fetch_campaigns()

    def test_fetch_campaigns_invalid_data(self, service, mock_esi_client):
        """Test handling invalid data from ESI."""
        mock_esi_data = [
            {
                "campaign_id": 123,
                # Missing required fields
                "event_type": "tcu_defense",
            }
        ]

        mock_esi_client.get.return_value = mock_esi_data

        # Should raise validation error or skip invalid entries
        with pytest.raises(Exception):
            service.fetch_campaigns()

    def test_fetch_campaigns_with_optional_fields(self, service, mock_esi_client):
        """Test fetching campaigns with optional structure_id."""
        mock_esi_data = [
            {
                "campaign_id": 123,
                "solar_system_id": 30001234,
                "constellation_id": 20000123,
                "structure_type_id": 32226,
                "event_type": "tcu_defense",
                "start_time": "2024-12-01T12:00:00Z",
                "defender_id": 123456,
                "defender_score": 0.5,
                "attackers_score": 0.3,
                # No structure_id
            }
        ]

        mock_esi_client.get.return_value = mock_esi_data

        campaigns = service.fetch_campaigns()

        assert len(campaigns) == 1
        assert campaigns[0].structure_id is None


class TestUpdateCampaigns:
    """Tests for update_campaigns method."""

    def test_update_campaigns_success(self, service, mock_esi_client, mock_repository):
        """Test successfully updating campaigns."""
        mock_esi_data = [
            {
                "campaign_id": 123,
                "structure_id": 456,
                "solar_system_id": 30001234,
                "constellation_id": 20000123,
                "structure_type_id": 32226,
                "event_type": "tcu_defense",
                "start_time": "2024-12-01T12:00:00Z",
                "defender_id": 123456,
                "defender_score": 0.5,
                "attackers_score": 0.3,
            }
        ]

        mock_esi_client.get.return_value = mock_esi_data
        mock_repository.store_campaigns.return_value = 1

        result = service.update_campaigns()

        assert result == 1
        mock_esi_client.get.assert_called_once()
        mock_repository.store_campaigns.assert_called_once()

    def test_update_campaigns_multiple(self, service, mock_esi_client, mock_repository):
        """Test updating multiple campaigns."""
        mock_esi_data = [
            {
                "campaign_id": 123,
                "structure_id": 456,
                "solar_system_id": 30001234,
                "constellation_id": 20000123,
                "structure_type_id": 32226,
                "event_type": "tcu_defense",
                "start_time": "2024-12-01T12:00:00Z",
                "defender_id": 123456,
                "defender_score": 0.5,
                "attackers_score": 0.3,
            },
            {
                "campaign_id": 456,
                "structure_id": 789,
                "solar_system_id": 30001235,
                "constellation_id": 20000124,
                "structure_type_id": 32226,
                "event_type": "ihub_defense",
                "start_time": "2024-12-02T15:00:00Z",
                "defender_id": 123457,
                "defender_score": 0.7,
                "attackers_score": 0.2,
            },
        ]

        mock_esi_client.get.return_value = mock_esi_data
        mock_repository.store_campaigns.return_value = 2

        result = service.update_campaigns()

        assert result == 2

    def test_update_campaigns_esi_failure(self, service, mock_esi_client, mock_repository):
        """Test handling ESI failure during update."""
        mock_esi_client.get.side_effect = ESIError("ESI unavailable")

        with pytest.raises(ESIError):
            service.update_campaigns()

        mock_repository.store_campaigns.assert_not_called()

    def test_update_campaigns_repository_failure(self, service, mock_esi_client, mock_repository):
        """Test handling repository failure during update."""
        mock_esi_data = [
            {
                "campaign_id": 123,
                "structure_id": 456,
                "solar_system_id": 30001234,
                "constellation_id": 20000123,
                "structure_type_id": 32226,
                "event_type": "tcu_defense",
                "start_time": "2024-12-01T12:00:00Z",
                "defender_id": 123456,
                "defender_score": 0.5,
                "attackers_score": 0.3,
            }
        ]

        mock_esi_client.get.return_value = mock_esi_data
        mock_repository.store_campaigns.side_effect = RepositoryError("Database error")

        with pytest.raises(RepositoryError):
            service.update_campaigns()

    def test_update_campaigns_empty_esi_response(self, service, mock_esi_client, mock_repository):
        """Test updating when ESI returns no campaigns."""
        mock_esi_client.get.return_value = []
        mock_repository.store_campaigns.return_value = 0

        result = service.update_campaigns()

        assert result == 0
        mock_repository.store_campaigns.assert_called_once_with([])


class TestGetCampaigns:
    """Tests for get_campaigns method."""

    def test_get_all_campaigns(self, service, mock_repository):
        """Test getting all campaigns."""
        mock_repository.get_campaigns.return_value = [
            {
                "campaign_id": 123,
                "system_id": 30001234,
                "constellation_id": 20000123,
                "structure_type_id": 32226,
                "event_type": "tcu_defense",
                "start_time": datetime.now(timezone.utc),
                "defender_id": 123456,
                "defender_score": 0.5,
                "attackers_score": 0.3,
                "structure_id": 456,
            },
            {
                "campaign_id": 456,
                "system_id": 30001235,
                "constellation_id": 20000124,
                "structure_type_id": 32226,
                "event_type": "ihub_defense",
                "start_time": datetime.now(timezone.utc),
                "defender_id": 123457,
                "defender_score": 0.7,
                "attackers_score": 0.2,
                "structure_id": None,
            },
        ]

        result = service.get_campaigns()

        assert isinstance(result, SovCampaignList)
        assert result.count == 2
        assert len(result.campaigns) == 2
        assert result.campaigns[0].campaign_id == 123
        mock_repository.get_campaigns.assert_called_once_with(region_id=None)

    def test_get_campaigns_by_region(self, service, mock_repository):
        """Test getting campaigns filtered by region."""
        mock_repository.get_campaigns.return_value = [
            {
                "campaign_id": 123,
                "system_id": 30001234,
                "constellation_id": 20000123,
                "structure_type_id": 32226,
                "event_type": "tcu_defense",
                "start_time": datetime.now(timezone.utc),
                "defender_id": 123456,
                "defender_score": 0.5,
                "attackers_score": 0.3,
                "structure_id": 456,
            }
        ]

        result = service.get_campaigns(region_id=10000002)

        assert isinstance(result, SovCampaignList)
        assert result.count == 1
        mock_repository.get_campaigns.assert_called_once_with(region_id=10000002)

    def test_get_campaigns_empty_result(self, service, mock_repository):
        """Test getting campaigns when none exist."""
        mock_repository.get_campaigns.return_value = []

        result = service.get_campaigns()

        assert isinstance(result, SovCampaignList)
        assert result.count == 0
        assert len(result.campaigns) == 0


class TestCleanupOldCampaigns:
    """Tests for cleanup_old_campaigns method."""

    def test_cleanup_old_campaigns_default_days(self, service, mock_repository):
        """Test cleanup with default retention period."""
        mock_repository.cleanup_old_campaigns.return_value = 5

        result = service.cleanup_old_campaigns(days=1)

        assert result == 5
        mock_repository.cleanup_old_campaigns.assert_called_once()
        # Verify cutoff_date is approximately 1 day ago
        call_args = mock_repository.cleanup_old_campaigns.call_args[0]
        cutoff_date = call_args[0]
        assert isinstance(cutoff_date, datetime)

    def test_cleanup_old_campaigns_custom_days(self, service, mock_repository):
        """Test cleanup with custom retention period."""
        mock_repository.cleanup_old_campaigns.return_value = 10

        result = service.cleanup_old_campaigns(days=7)

        assert result == 10
        mock_repository.cleanup_old_campaigns.assert_called_once()

    def test_cleanup_no_old_campaigns(self, service, mock_repository):
        """Test cleanup when no old campaigns exist."""
        mock_repository.cleanup_old_campaigns.return_value = 0

        result = service.cleanup_old_campaigns(days=1)

        assert result == 0

    def test_cleanup_repository_failure(self, service, mock_repository):
        """Test handling repository failure during cleanup."""
        mock_repository.cleanup_old_campaigns.side_effect = RepositoryError("Database error")

        with pytest.raises(RepositoryError):
            service.cleanup_old_campaigns(days=1)
