"""Tests for Faction Warfare service."""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch
from typing import List, Dict, Any

from src.services.warroom.fw import FactionWarfareService
from src.services.warroom.models import FWSystemStatus, FWHotspot, FWStats
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
    return FactionWarfareService(
        repository=mock_repository,
        esi_client=mock_esi_client,
    )


class TestFetchFWSystems:
    """Tests for fetch_fw_systems method."""

    def test_fetch_fw_systems_success(self, service, mock_esi_client):
        """Test successfully fetching FW systems from ESI."""
        mock_esi_data = [
            {
                "solar_system_id": 30002502,
                "owning_faction_id": 500001,
                "occupying_faction_id": 500002,
                "contested": "captured",
                "victory_points": 2500,
                "victory_points_threshold": 3000,
            },
            {
                "solar_system_id": 30002503,
                "owning_faction_id": 500001,
                "occupying_faction_id": 500002,
                "contested": "uncontested",
                "victory_points": 500,
                "victory_points_threshold": 3000,
            },
        ]

        mock_esi_client.get.return_value = mock_esi_data

        systems = service.fetch_fw_systems()

        assert len(systems) == 2
        assert isinstance(systems[0], FWSystemStatus)
        assert systems[0].system_id == 30002502
        assert systems[0].contested == "captured"
        assert systems[1].system_id == 30002503
        mock_esi_client.get.assert_called_once_with("/fw/systems/")

    def test_fetch_fw_systems_empty_response(self, service, mock_esi_client):
        """Test fetching FW systems when ESI returns empty list."""
        mock_esi_client.get.return_value = []

        systems = service.fetch_fw_systems()

        assert len(systems) == 0
        mock_esi_client.get.assert_called_once()

    def test_fetch_fw_systems_esi_error(self, service, mock_esi_client):
        """Test handling ESI errors during FW system fetch."""
        mock_esi_client.get.side_effect = ESIError("ESI unavailable")

        with pytest.raises(ESIError):
            service.fetch_fw_systems()

    def test_fetch_fw_systems_invalid_data(self, service, mock_esi_client):
        """Test handling invalid data from ESI."""
        mock_esi_data = [
            {
                "solar_system_id": 30002502,
                # Missing required fields
                "contested": "captured",
            }
        ]

        mock_esi_client.get.return_value = mock_esi_data

        # Should raise validation error or skip invalid entries
        with pytest.raises(Exception):
            service.fetch_fw_systems()


class TestUpdateFWSystems:
    """Tests for update_fw_systems method."""

    def test_update_fw_systems_success(self, service, mock_esi_client, mock_repository):
        """Test successfully updating FW systems."""
        mock_esi_data = [
            {
                "solar_system_id": 30002502,
                "owning_faction_id": 500001,
                "occupying_faction_id": 500002,
                "contested": "captured",
                "victory_points": 2500,
                "victory_points_threshold": 3000,
            }
        ]

        mock_esi_client.get.return_value = mock_esi_data
        mock_repository.store_fw_systems.return_value = 1

        result = service.update_fw_systems()

        assert result == 1
        mock_esi_client.get.assert_called_once()
        mock_repository.store_fw_systems.assert_called_once()

    def test_update_fw_systems_multiple(self, service, mock_esi_client, mock_repository):
        """Test updating multiple FW systems."""
        mock_esi_data = [
            {
                "solar_system_id": 30002502,
                "owning_faction_id": 500001,
                "occupying_faction_id": 500002,
                "contested": "captured",
                "victory_points": 2500,
                "victory_points_threshold": 3000,
            },
            {
                "solar_system_id": 30002503,
                "owning_faction_id": 500001,
                "occupying_faction_id": 500002,
                "contested": "uncontested",
                "victory_points": 500,
                "victory_points_threshold": 3000,
            },
        ]

        mock_esi_client.get.return_value = mock_esi_data
        mock_repository.store_fw_systems.return_value = 2

        result = service.update_fw_systems()

        assert result == 2

    def test_update_fw_systems_esi_failure(self, service, mock_esi_client, mock_repository):
        """Test handling ESI failure during update."""
        mock_esi_client.get.side_effect = ESIError("ESI unavailable")

        with pytest.raises(ESIError):
            service.update_fw_systems()

        mock_repository.store_fw_systems.assert_not_called()

    def test_update_fw_systems_repository_failure(self, service, mock_esi_client, mock_repository):
        """Test handling repository failure during update."""
        mock_esi_data = [
            {
                "solar_system_id": 30002502,
                "owning_faction_id": 500001,
                "occupying_faction_id": 500002,
                "contested": "captured",
                "victory_points": 2500,
                "victory_points_threshold": 3000,
            }
        ]

        mock_esi_client.get.return_value = mock_esi_data
        mock_repository.store_fw_systems.side_effect = RepositoryError("Database error")

        with pytest.raises(RepositoryError):
            service.update_fw_systems()

    def test_update_fw_systems_empty_esi_response(self, service, mock_esi_client, mock_repository):
        """Test updating when ESI returns no systems."""
        mock_esi_client.get.return_value = []
        mock_repository.store_fw_systems.return_value = 0

        result = service.update_fw_systems()

        assert result == 0
        mock_repository.store_fw_systems.assert_called_once_with([])


class TestGetFWHotspots:
    """Tests for get_fw_hotspots method."""

    def test_get_fw_hotspots_default_threshold(self, service, mock_repository):
        """Test getting FW hotspots with default threshold."""
        mock_repository.get_fw_hotspots.return_value = [
            {
                "system_id": 30002502,
                "system_name": "Kourmonen",
                "owning_faction_id": 500001,
                "occupying_faction_id": 500002,
                "contested": "captured",
                "victory_points": 2700,
                "victory_points_threshold": 3000,
                "progress_percent": 90.0,
            },
            {
                "system_id": 30002503,
                "system_name": "Huola",
                "owning_faction_id": 500001,
                "occupying_faction_id": 500002,
                "contested": "captured",
                "victory_points": 2800,
                "victory_points_threshold": 3000,
                "progress_percent": 93.33,
            },
        ]

        result = service.get_fw_hotspots(min_progress=50.0)

        assert len(result) == 2
        assert isinstance(result[0], FWHotspot)
        assert result[0].system_id == 30002502
        assert result[0].system_name == "Kourmonen"
        assert result[0].progress_percent == 90.0
        assert result[0].is_critical is True  # >= 90%
        mock_repository.get_fw_hotspots.assert_called_once_with(min_progress=50.0)

    def test_get_fw_hotspots_high_threshold(self, service, mock_repository):
        """Test getting FW hotspots with high threshold (critical systems)."""
        mock_repository.get_fw_hotspots.return_value = [
            {
                "system_id": 30002503,
                "system_name": "Huola",
                "owning_faction_id": 500001,
                "occupying_faction_id": 500002,
                "contested": "captured",
                "victory_points": 2800,
                "victory_points_threshold": 3000,
                "progress_percent": 93.33,
            }
        ]

        result = service.get_fw_hotspots(min_progress=90.0)

        assert len(result) == 1
        assert result[0].system_name == "Huola"
        assert result[0].is_critical is True
        mock_repository.get_fw_hotspots.assert_called_once_with(min_progress=90.0)

    def test_get_fw_hotspots_empty_result(self, service, mock_repository):
        """Test getting FW hotspots when none meet criteria."""
        mock_repository.get_fw_hotspots.return_value = []

        result = service.get_fw_hotspots(min_progress=95.0)

        assert len(result) == 0

    def test_get_fw_hotspots_is_critical_flag(self, service, mock_repository):
        """Test is_critical flag is set correctly based on progress."""
        mock_repository.get_fw_hotspots.return_value = [
            {
                "system_id": 30002502,
                "system_name": "System1",
                "owning_faction_id": 500001,
                "occupying_faction_id": 500002,
                "contested": "captured",
                "victory_points": 2400,
                "victory_points_threshold": 3000,
                "progress_percent": 80.0,
            },
            {
                "system_id": 30002503,
                "system_name": "System2",
                "owning_faction_id": 500001,
                "occupying_faction_id": 500002,
                "contested": "captured",
                "victory_points": 2700,
                "victory_points_threshold": 3000,
                "progress_percent": 90.0,
            },
        ]

        result = service.get_fw_hotspots(min_progress=50.0)

        assert len(result) == 2
        assert result[0].is_critical is False  # 80% < 90%
        assert result[1].is_critical is True   # 90% >= 90%


class TestGetFWStats:
    """Tests for get_fw_stats method."""

    def test_get_fw_stats_success(self, service, mock_repository):
        """Test getting FW statistics."""
        mock_repository.get_fw_systems.return_value = [
            {
                "system_id": 30002502,
                "owning_faction_id": 500001,
                "occupying_faction_id": 500002,
                "contested": "captured",
                "victory_points": 2500,
                "victory_points_threshold": 3000,
            },
            {
                "system_id": 30002503,
                "owning_faction_id": 500001,
                "occupying_faction_id": 500002,
                "contested": "uncontested",
                "victory_points": 500,
                "victory_points_threshold": 3000,
            },
            {
                "system_id": 30002504,
                "owning_faction_id": 500003,
                "occupying_faction_id": 500004,
                "contested": "captured",
                "victory_points": 2700,
                "victory_points_threshold": 3000,
            },
        ]

        result = service.get_fw_stats()

        assert isinstance(result, FWStats)
        assert result.total_systems == 3
        assert result.contested_count == 2
        assert 500001 in result.faction_breakdown
        assert 500003 in result.faction_breakdown
        assert result.faction_breakdown[500001] == 2  # 2 systems owned by faction 500001
        assert result.faction_breakdown[500003] == 1
        mock_repository.get_fw_systems.assert_called_once_with(contested_only=False)

    def test_get_fw_stats_empty_systems(self, service, mock_repository):
        """Test getting FW stats when no systems exist."""
        mock_repository.get_fw_systems.return_value = []

        result = service.get_fw_stats()

        assert isinstance(result, FWStats)
        assert result.total_systems == 0
        assert result.contested_count == 0
        assert len(result.faction_breakdown) == 0

    def test_get_fw_stats_all_contested(self, service, mock_repository):
        """Test FW stats when all systems are contested."""
        mock_repository.get_fw_systems.return_value = [
            {
                "system_id": 30002502,
                "owning_faction_id": 500001,
                "occupying_faction_id": 500002,
                "contested": "captured",
                "victory_points": 2500,
                "victory_points_threshold": 3000,
            },
            {
                "system_id": 30002503,
                "owning_faction_id": 500001,
                "occupying_faction_id": 500002,
                "contested": "vulnerable",
                "victory_points": 2800,
                "victory_points_threshold": 3000,
            },
        ]

        result = service.get_fw_stats()

        assert result.total_systems == 2
        assert result.contested_count == 2

    def test_get_fw_stats_faction_breakdown(self, service, mock_repository):
        """Test faction breakdown calculation."""
        mock_repository.get_fw_systems.return_value = [
            {
                "system_id": 30002502,
                "owning_faction_id": 500001,
                "occupying_faction_id": 500002,
                "contested": "uncontested",
                "victory_points": 0,
                "victory_points_threshold": 3000,
            },
            {
                "system_id": 30002503,
                "owning_faction_id": 500001,
                "occupying_faction_id": 500002,
                "contested": "uncontested",
                "victory_points": 0,
                "victory_points_threshold": 3000,
            },
            {
                "system_id": 30002504,
                "owning_faction_id": 500003,
                "occupying_faction_id": 500004,
                "contested": "uncontested",
                "victory_points": 0,
                "victory_points_threshold": 3000,
            },
            {
                "system_id": 30002505,
                "owning_faction_id": 500003,
                "occupying_faction_id": 500004,
                "contested": "uncontested",
                "victory_points": 0,
                "victory_points_threshold": 3000,
            },
            {
                "system_id": 30002506,
                "owning_faction_id": 500003,
                "occupying_faction_id": 500004,
                "contested": "uncontested",
                "victory_points": 0,
                "victory_points_threshold": 3000,
            },
        ]

        result = service.get_fw_stats()

        assert result.total_systems == 5
        assert result.faction_breakdown[500001] == 2
        assert result.faction_breakdown[500003] == 3

    def test_get_fw_stats_repository_failure(self, service, mock_repository):
        """Test handling repository failure during stats calculation."""
        mock_repository.get_fw_systems.side_effect = RepositoryError("Database error")

        with pytest.raises(RepositoryError):
            service.get_fw_stats()
