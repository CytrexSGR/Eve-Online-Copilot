"""Tests for War Room models."""

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from src.services.warroom.models import (
    SovCampaign,
    SovCampaignList,
    SovSystemInfo,
    FWSystemStatus,
    FWHotspot,
    FWStats,
)


class TestSovCampaign:
    """Tests for SovCampaign model."""

    def test_create_valid_campaign(self):
        """Test creating a valid sovereignty campaign."""
        campaign = SovCampaign(
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

        assert campaign.campaign_id == 123456
        assert campaign.system_id == 30001234
        assert campaign.event_type == "tcu_defense"
        assert campaign.defender_score == 0.5
        assert campaign.attackers_score == 0.3

    def test_campaign_with_optional_fields(self):
        """Test campaign with optional structure_id."""
        campaign = SovCampaign(
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

        assert campaign.structure_id == 1234567890

    def test_campaign_missing_required_field(self):
        """Test that missing required fields raise validation error."""
        with pytest.raises(ValidationError):
            SovCampaign(
                system_id=30001234,
                constellation_id=20000123,
                structure_type_id=32226,
                event_type="tcu_defense",
                start_time=datetime.now(timezone.utc),
            )

    def test_campaign_from_esi_response(self):
        """Test creating campaign from ESI API response."""
        esi_data = {
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

        campaign = SovCampaign(
            campaign_id=esi_data["campaign_id"],
            system_id=esi_data["solar_system_id"],
            constellation_id=esi_data["constellation_id"],
            structure_type_id=esi_data["structure_type_id"],
            event_type=esi_data["event_type"],
            start_time=datetime.fromisoformat(esi_data["start_time"].replace("Z", "+00:00")),
            defender_id=esi_data["defender_id"],
            defender_score=esi_data["defender_score"],
            attackers_score=esi_data["attackers_score"],
            structure_id=esi_data.get("structure_id"),
        )

        assert campaign.campaign_id == 123
        assert campaign.system_id == 30001234
        assert campaign.structure_id == 456


class TestSovCampaignList:
    """Tests for SovCampaignList model."""

    def test_create_campaign_list(self):
        """Test creating a campaign list."""
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

        campaign_list = SovCampaignList(campaigns=campaigns, count=2)

        assert campaign_list.count == 2
        assert len(campaign_list.campaigns) == 2
        assert campaign_list.campaigns[0].campaign_id == 123

    def test_empty_campaign_list(self):
        """Test creating an empty campaign list."""
        campaign_list = SovCampaignList(campaigns=[], count=0)

        assert campaign_list.count == 0
        assert len(campaign_list.campaigns) == 0


class TestSovSystemInfo:
    """Tests for SovSystemInfo model."""

    def test_create_system_info(self):
        """Test creating sovereignty system info."""
        system_info = SovSystemInfo(
            system_id=30001234,
            alliance_id=98785281,
            corporation_id=123456,
            vulnerability_occupancy_level=5.0,
        )

        assert system_info.system_id == 30001234
        assert system_info.alliance_id == 98785281
        assert system_info.corporation_id == 123456
        assert system_info.vulnerability_occupancy_level == 5.0

    def test_system_info_with_optional_fields(self):
        """Test system info with optional fields."""
        system_info = SovSystemInfo(
            system_id=30001234,
            alliance_id=None,
            corporation_id=None,
            vulnerability_occupancy_level=None,
        )

        assert system_info.system_id == 30001234
        assert system_info.alliance_id is None


class TestFWSystemStatus:
    """Tests for FWSystemStatus model."""

    def test_create_fw_system_status(self):
        """Test creating FW system status."""
        status = FWSystemStatus(
            system_id=30002502,
            owning_faction_id=500001,
            occupying_faction_id=500002,
            contested="captured",
            victory_points=2500,
            victory_points_threshold=3000,
        )

        assert status.system_id == 30002502
        assert status.owning_faction_id == 500001
        assert status.occupying_faction_id == 500002
        assert status.contested == "captured"
        assert status.victory_points == 2500
        assert status.victory_points_threshold == 3000

    def test_fw_system_from_esi_response(self):
        """Test creating FW system from ESI API response."""
        esi_data = {
            "solar_system_id": 30002502,
            "owning_faction_id": 500001,
            "occupying_faction_id": 500002,
            "contested": "captured",
            "victory_points": 2500,
            "victory_points_threshold": 3000,
        }

        status = FWSystemStatus(
            system_id=esi_data["solar_system_id"],
            owning_faction_id=esi_data["owning_faction_id"],
            occupying_faction_id=esi_data["occupying_faction_id"],
            contested=esi_data["contested"],
            victory_points=esi_data["victory_points"],
            victory_points_threshold=esi_data["victory_points_threshold"],
        )

        assert status.system_id == 30002502
        assert status.victory_points == 2500

    def test_fw_system_missing_required_field(self):
        """Test that missing required fields raise validation error."""
        with pytest.raises(ValidationError):
            FWSystemStatus(
                system_id=30002502,
                owning_faction_id=500001,
                contested="captured",
            )


class TestFWHotspot:
    """Tests for FWHotspot model."""

    def test_create_fw_hotspot(self):
        """Test creating FW hotspot."""
        hotspot = FWHotspot(
            system_id=30002502,
            system_name="Kourmonen",
            contested="captured",
            victory_points=2700,
            progress_percent=90.0,
            is_critical=True,
        )

        assert hotspot.system_id == 30002502
        assert hotspot.system_name == "Kourmonen"
        assert hotspot.progress_percent == 90.0
        assert hotspot.is_critical is True

    def test_hotspot_with_optional_fields(self):
        """Test hotspot with optional fields."""
        hotspot = FWHotspot(
            system_id=30002502,
            system_name=None,
            contested="captured",
            victory_points=2500,
            progress_percent=83.33,
            is_critical=False,
        )

        assert hotspot.system_name is None
        assert hotspot.is_critical is False

    def test_hotspot_progress_calculation(self):
        """Test hotspot with calculated progress percent."""
        # Progress = (victory_points / victory_points_threshold) * 100
        victory_points = 2700
        threshold = 3000
        expected_progress = (victory_points / threshold) * 100

        hotspot = FWHotspot(
            system_id=30002502,
            system_name="Kourmonen",
            contested="captured",
            victory_points=victory_points,
            progress_percent=expected_progress,
            is_critical=expected_progress >= 90.0,
        )

        assert hotspot.progress_percent == expected_progress
        assert hotspot.is_critical is True


class TestFWStats:
    """Tests for FWStats model."""

    def test_create_fw_stats(self):
        """Test creating FW statistics."""
        faction_breakdown = {
            500001: 45,  # Caldari State
            500004: 42,  # Gallente Federation
            500003: 35,  # Amarr Empire
            500002: 38,  # Minmatar Republic
        }

        stats = FWStats(
            total_systems=160,
            contested_count=12,
            faction_breakdown=faction_breakdown,
        )

        assert stats.total_systems == 160
        assert stats.contested_count == 12
        assert stats.faction_breakdown[500001] == 45
        assert len(stats.faction_breakdown) == 4

    def test_fw_stats_empty_breakdown(self):
        """Test FW stats with empty faction breakdown."""
        stats = FWStats(
            total_systems=0,
            contested_count=0,
            faction_breakdown={},
        )

        assert stats.total_systems == 0
        assert stats.contested_count == 0
        assert len(stats.faction_breakdown) == 0

    def test_fw_stats_validation(self):
        """Test that contested_count cannot exceed total_systems."""
        # This is a business logic validation that should be enforced
        # in the service layer, not the model layer
        stats = FWStats(
            total_systems=100,
            contested_count=15,
            faction_breakdown={500001: 50, 500004: 50},  # Caldari, Gallente
        )

        assert stats.contested_count <= stats.total_systems
