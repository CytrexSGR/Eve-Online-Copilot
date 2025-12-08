"""Tests for War Room repository."""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, MagicMock, call
from typing import List, Dict, Any

from src.services.warroom.repository import WarRoomRepository
from src.services.warroom.models import SovCampaign, FWSystemStatus


@pytest.fixture
def mock_db():
    """Create mock database pool."""
    mock_pool = Mock()
    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    # Setup context managers
    mock_pool.get_connection.return_value.__enter__ = Mock(return_value=mock_conn)
    mock_pool.get_connection.return_value.__exit__ = Mock(return_value=False)
    mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)

    return mock_pool, mock_conn, mock_cursor


@pytest.fixture
def repository(mock_db):
    """Create repository instance with mock database."""
    mock_pool, _, _ = mock_db
    return WarRoomRepository(db=mock_pool)


class TestStoreCampaigns:
    """Tests for store_campaigns method."""

    def test_store_campaigns_empty_list(self, repository, mock_db):
        """Test storing empty campaign list."""
        _, mock_conn, mock_cursor = mock_db

        result = repository.store_campaigns([])

        assert result == 0
        mock_cursor.execute.assert_not_called()

    def test_store_single_campaign(self, repository, mock_db):
        """Test storing a single campaign."""
        _, mock_conn, mock_cursor = mock_db

        campaigns = [
            SovCampaign(
                campaign_id=123456,
                system_id=30001234,
                constellation_id=20000123,
                structure_type_id=32226,
                event_type="tcu_defense",
                start_time=datetime.now(timezone.utc),
                defender_id=98785281,
                defender_score=0.5,
                attackers_score=0.3,
            )
        ]

        result = repository.store_campaigns(campaigns)

        assert result == 1
        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()

    def test_store_multiple_campaigns(self, repository, mock_db):
        """Test storing multiple campaigns."""
        _, mock_conn, mock_cursor = mock_db

        campaigns = [
            SovCampaign(
                campaign_id=123,
                system_id=30001234,
                constellation_id=20000123,
                structure_type_id=32226,
                event_type="tcu_defense",
                start_time=datetime.now(timezone.utc),
                defender_id=98785281,
                defender_score=0.5,
                attackers_score=0.3,
            ),
            SovCampaign(
                campaign_id=456,
                system_id=30001235,
                constellation_id=20000124,
                structure_type_id=32226,
                event_type="ihub_defense",
                start_time=datetime.now(timezone.utc),
                defender_id=98785282,
                defender_score=0.7,
                attackers_score=0.2,
            ),
        ]

        result = repository.store_campaigns(campaigns)

        assert result == 2
        assert mock_cursor.execute.call_count == 2
        mock_conn.commit.assert_called_once()

    def test_store_campaigns_with_structure_id(self, repository, mock_db):
        """Test storing campaigns with optional structure_id."""
        _, mock_conn, mock_cursor = mock_db

        campaigns = [
            SovCampaign(
                campaign_id=123456,
                system_id=30001234,
                constellation_id=20000123,
                structure_type_id=32226,
                event_type="tcu_defense",
                start_time=datetime.now(timezone.utc),
                defender_id=98785281,
                defender_score=0.5,
                attackers_score=0.3,
                structure_id=1234567890,
            )
        ]

        result = repository.store_campaigns(campaigns)

        assert result == 1
        # Verify structure_id is included in the execute call
        call_args = mock_cursor.execute.call_args[0]
        assert "structure_id" in call_args[0].lower()


class TestGetCampaigns:
    """Tests for get_campaigns method."""

    def test_get_all_campaigns(self, repository, mock_db):
        """Test getting all campaigns without region filter."""
        _, mock_conn, mock_cursor = mock_db

        mock_cursor.fetchall.return_value = [
            (123, 30001234, 20000123, 32226, "tcu_defense", datetime.now(timezone.utc), 98785281, 0.5, 0.3, 1234567890),
            (456, 30001235, 20000124, 32226, "ihub_defense", datetime.now(timezone.utc), 98785282, 0.7, 0.2, None),
        ]

        campaigns = repository.get_campaigns()

        assert len(campaigns) == 2
        assert campaigns[0]["campaign_id"] == 123
        assert campaigns[1]["campaign_id"] == 456
        mock_cursor.execute.assert_called_once()

    def test_get_campaigns_by_region(self, repository, mock_db):
        """Test getting campaigns filtered by region."""
        _, mock_conn, mock_cursor = mock_db

        mock_cursor.fetchall.return_value = [
            (123, 30001234, 20000123, 32226, "tcu_defense", datetime.now(timezone.utc), 98785281, 0.5, 0.3, None),
        ]

        campaigns = repository.get_campaigns(region_id=10000002)

        assert len(campaigns) == 1
        mock_cursor.execute.assert_called_once()
        # Verify region_id is used in query
        call_args = mock_cursor.execute.call_args[0]
        assert 10000002 in call_args[1]

    def test_get_campaigns_empty_result(self, repository, mock_db):
        """Test getting campaigns when none exist."""
        _, mock_conn, mock_cursor = mock_db

        mock_cursor.fetchall.return_value = []

        campaigns = repository.get_campaigns()

        assert len(campaigns) == 0


class TestCleanupOldCampaigns:
    """Tests for cleanup_old_campaigns method."""

    def test_cleanup_old_campaigns(self, repository, mock_db):
        """Test cleaning up old campaigns."""
        _, mock_conn, mock_cursor = mock_db
        mock_cursor.rowcount = 5

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=1)
        result = repository.cleanup_old_campaigns(cutoff_date)

        assert result == 5
        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()

    def test_cleanup_no_old_campaigns(self, repository, mock_db):
        """Test cleanup when no old campaigns exist."""
        _, mock_conn, mock_cursor = mock_db
        mock_cursor.rowcount = 0

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=1)
        result = repository.cleanup_old_campaigns(cutoff_date)

        assert result == 0


class TestStoreFWSystems:
    """Tests for store_fw_systems method."""

    def test_store_fw_systems_empty_list(self, repository, mock_db):
        """Test storing empty FW systems list."""
        _, mock_conn, mock_cursor = mock_db

        result = repository.store_fw_systems([])

        assert result == 0
        mock_cursor.execute.assert_not_called()

    def test_store_single_fw_system(self, repository, mock_db):
        """Test storing a single FW system."""
        _, mock_conn, mock_cursor = mock_db

        systems = [
            FWSystemStatus(
                system_id=30002502,
                owning_faction_id=500001,
                occupying_faction_id=500002,
                contested="captured",
                victory_points=2500,
                victory_points_threshold=3000,
            )
        ]

        result = repository.store_fw_systems(systems)

        assert result == 1
        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()

    def test_store_multiple_fw_systems(self, repository, mock_db):
        """Test storing multiple FW systems."""
        _, mock_conn, mock_cursor = mock_db

        systems = [
            FWSystemStatus(
                system_id=30002502,
                owning_faction_id=500001,
                occupying_faction_id=500002,
                contested="captured",
                victory_points=2500,
                victory_points_threshold=3000,
            ),
            FWSystemStatus(
                system_id=30002503,
                owning_faction_id=500001,
                occupying_faction_id=500002,
                contested="uncontested",
                victory_points=500,
                victory_points_threshold=3000,
            ),
        ]

        result = repository.store_fw_systems(systems)

        assert result == 2
        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()


class TestGetFWSystems:
    """Tests for get_fw_systems method."""

    def test_get_all_fw_systems(self, repository, mock_db):
        """Test getting all FW systems."""
        _, mock_conn, mock_cursor = mock_db

        mock_cursor.fetchall.return_value = [
            (30002502, 500001, 500002, "captured", 2500, 3000, datetime.now(timezone.utc)),
            (30002503, 500001, 500002, "uncontested", 500, 3000, datetime.now(timezone.utc)),
        ]

        systems = repository.get_fw_systems(contested_only=False)

        assert len(systems) == 2
        assert systems[0]["system_id"] == 30002502
        assert systems[1]["system_id"] == 30002503
        mock_cursor.execute.assert_called_once()

    def test_get_contested_fw_systems_only(self, repository, mock_db):
        """Test getting only contested FW systems."""
        _, mock_conn, mock_cursor = mock_db

        mock_cursor.fetchall.return_value = [
            (30002502, 500001, 500002, "captured", 2500, 3000, datetime.now(timezone.utc)),
        ]

        systems = repository.get_fw_systems(contested_only=True)

        assert len(systems) == 1
        assert systems[0]["system_id"] == 30002502
        mock_cursor.execute.assert_called_once()
        # Verify contested filter is applied
        call_args = mock_cursor.execute.call_args[0]
        assert "contested" in call_args[0].lower()

    def test_get_fw_systems_empty_result(self, repository, mock_db):
        """Test getting FW systems when none exist."""
        _, mock_conn, mock_cursor = mock_db

        mock_cursor.fetchall.return_value = []

        systems = repository.get_fw_systems(contested_only=False)

        assert len(systems) == 0


class TestGetFWHotspots:
    """Tests for get_fw_hotspots method."""

    def test_get_fw_hotspots_default_threshold(self, repository, mock_db):
        """Test getting FW hotspots with default threshold."""
        _, mock_conn, mock_cursor = mock_db

        mock_cursor.fetchall.return_value = [
            (30002502, "Kourmonen", 500001, 500002, "captured", 2700, 3000, 90.0, datetime.now(timezone.utc)),
            (30002503, "Huola", 500001, 500002, "captured", 2800, 3000, 93.33, datetime.now(timezone.utc)),
        ]

        hotspots = repository.get_fw_hotspots(min_progress=50.0)

        assert len(hotspots) == 2
        assert hotspots[0]["system_id"] == 30002502
        assert hotspots[0]["progress_percent"] == 90.0
        mock_cursor.execute.assert_called_once()

    def test_get_fw_hotspots_high_threshold(self, repository, mock_db):
        """Test getting FW hotspots with high threshold (critical systems)."""
        _, mock_conn, mock_cursor = mock_db

        mock_cursor.fetchall.return_value = [
            (30002503, "Huola", 500001, 500002, "captured", 2800, 3000, 93.33, datetime.now(timezone.utc)),
        ]

        hotspots = repository.get_fw_hotspots(min_progress=90.0)

        assert len(hotspots) == 1
        assert hotspots[0]["progress_percent"] == 93.33
        mock_cursor.execute.assert_called_once()
        # Verify min_progress is used in query
        call_args = mock_cursor.execute.call_args[0]
        assert 90.0 in call_args[1]

    def test_get_fw_hotspots_empty_result(self, repository, mock_db):
        """Test getting FW hotspots when none meet criteria."""
        _, mock_conn, mock_cursor = mock_db

        mock_cursor.fetchall.return_value = []

        hotspots = repository.get_fw_hotspots(min_progress=95.0)

        assert len(hotspots) == 0

    def test_get_fw_hotspots_with_system_names(self, repository, mock_db):
        """Test that hotspots include system names from joins."""
        _, mock_conn, mock_cursor = mock_db

        mock_cursor.fetchall.return_value = [
            (30002502, "Kourmonen", 500001, 500002, "captured", 2700, 3000, 90.0, datetime.now(timezone.utc)),
        ]

        hotspots = repository.get_fw_hotspots(min_progress=50.0)

        assert len(hotspots) == 1
        assert hotspots[0]["system_name"] == "Kourmonen"
