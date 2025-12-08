"""Tests for War Analyzer service."""

import pytest
from datetime import date, datetime
from unittest.mock import Mock, patch
from typing import List, Dict, Any

from src.services.warroom.analyzer import WarAnalyzer
from src.services.warroom.analyzer_models import (
    DemandAnalysis,
    DemandItem,
    HeatmapPoint,
    DoctrineDetection,
    DangerScore,
    ConflictIntel,
)
from src.core.exceptions import RepositoryError


@pytest.fixture(autouse=True)
def mock_settings():
    """Mock settings for all tests."""
    mock_settings_obj = Mock()
    mock_settings_obj.war_heatmap_min_kills = 5
    mock_settings_obj.war_doctrine_min_fleet_size = 10

    with patch("src.services.warroom.analyzer.get_settings", return_value=mock_settings_obj):
        yield mock_settings_obj


@pytest.fixture
def mock_repository():
    """Create mock repository."""
    return Mock()


@pytest.fixture
def service(mock_repository):
    """Create service instance with mock repository."""
    return WarAnalyzer(repository=mock_repository)


class TestAnalyzeDemand:
    """Tests for analyze_demand method."""

    def test_analyze_demand_success(self, service, mock_repository):
        """Test successful demand analysis."""
        mock_repository.get_demand_analysis.return_value = {
            "ships": [
                {"type_id": 1, "name": "Ship A", "quantity": 100, "market_stock": 50},
                {"type_id": 2, "name": "Ship B", "quantity": 80, "market_stock": 0},
            ],
            "items": [
                {"type_id": 3, "name": "Item A", "quantity": 500, "market_stock": 200},
                {"type_id": 4, "name": "Item B", "quantity": 300, "market_stock": 300},
            ],
        }

        result = service.analyze_demand(region_id=10000002, days=7)

        assert isinstance(result, DemandAnalysis)
        assert result.region_id == 10000002
        assert result.days == 7
        assert len(result.ships_lost) == 2
        assert len(result.items_lost) == 2

        # Check market gaps calculated correctly
        assert len(result.market_gaps) > 0

        # First gap should be Ship A with gap of 50
        ship_a_gap = next(g for g in result.market_gaps if g.type_id == 1)
        assert ship_a_gap.gap == 50

        # Ship B has larger gap
        ship_b_gap = next(g for g in result.market_gaps if g.type_id == 2)
        assert ship_b_gap.gap == 80

        # Item with no gap shouldn't appear or has gap 0
        item_b = next((g for g in result.market_gaps if g.type_id == 4), None)
        if item_b:
            assert item_b.gap == 0

        mock_repository.get_demand_analysis.assert_called_once_with(
            region_id=10000002, days=7
        )

    def test_analyze_demand_empty_data(self, service, mock_repository):
        """Test demand analysis with no losses."""
        mock_repository.get_demand_analysis.return_value = {
            "ships": [],
            "items": [],
        }

        result = service.analyze_demand(region_id=10000002, days=7)

        assert isinstance(result, DemandAnalysis)
        assert len(result.ships_lost) == 0
        assert len(result.items_lost) == 0
        assert len(result.market_gaps) == 0

    def test_analyze_demand_market_gaps_sorted(self, service, mock_repository):
        """Test that market gaps are sorted by gap size."""
        mock_repository.get_demand_analysis.return_value = {
            "ships": [
                {"type_id": 1, "name": "Ship A", "quantity": 100, "market_stock": 90},  # gap 10
                {"type_id": 2, "name": "Ship B", "quantity": 80, "market_stock": 0},    # gap 80
                {"type_id": 3, "name": "Ship C", "quantity": 50, "market_stock": 10},   # gap 40
            ],
            "items": [],
        }

        result = service.analyze_demand(region_id=10000002, days=7)

        # Market gaps should be sorted descending
        gaps = [g.gap for g in result.market_gaps]
        assert gaps == sorted(gaps, reverse=True)

        # Largest gap first
        assert result.market_gaps[0].type_id == 2
        assert result.market_gaps[0].gap == 80

    def test_analyze_demand_top_15_gaps(self, service, mock_repository):
        """Test that only top 15 market gaps are returned."""
        ships = [
            {"type_id": i, "name": f"Ship {i}", "quantity": 100 - i, "market_stock": 0}
            for i in range(1, 21)  # 20 ships
        ]

        mock_repository.get_demand_analysis.return_value = {
            "ships": ships,
            "items": [],
        }

        result = service.analyze_demand(region_id=10000002, days=7)

        # Should limit to 15 market gaps
        assert len(result.market_gaps) <= 15

    def test_analyze_demand_repository_error(self, service, mock_repository):
        """Test handling repository errors."""
        mock_repository.get_demand_analysis.side_effect = RepositoryError("DB error")

        with pytest.raises(RepositoryError):
            service.analyze_demand(region_id=10000002, days=7)


class TestGetHeatmapData:
    """Tests for get_heatmap_data method."""

    def test_get_heatmap_data_success(self, service, mock_repository):
        """Test successfully getting heatmap data."""
        mock_repository.get_heatmap_data.return_value = [
            {
                "system_id": 30000142,
                "name": "Jita",
                "region_id": 10000002,
                "region": "The Forge",
                "security": 0.95,
                "x": 12.34,
                "z": 56.78,
                "kills": 150,
            },
            {
                "system_id": 30002187,
                "name": "Amarr",
                "region_id": 10000043,
                "region": "Domain",
                "security": 1.0,
                "x": -98.76,
                "z": 43.21,
                "kills": 100,
            },
        ]

        result = service.get_heatmap_data(days=7, min_kills=5)

        assert len(result) == 2
        assert isinstance(result[0], HeatmapPoint)
        assert result[0].system_id == 30000142
        assert result[0].name == "Jita"
        assert result[0].kills == 150
        assert result[0].x == 12.34
        assert result[0].z == 56.78

        mock_repository.get_heatmap_data.assert_called_once_with(days=7, min_kills=5)

    def test_get_heatmap_data_default_min_kills(self, service, mock_repository):
        """Test heatmap data with default min_kills from config."""
        mock_repository.get_heatmap_data.return_value = []

        result = service.get_heatmap_data(days=7)

        # Should use default from config (WAR_HEATMAP_MIN_KILLS = 5)
        mock_repository.get_heatmap_data.assert_called_once_with(days=7, min_kills=5)

    def test_get_heatmap_data_empty(self, service, mock_repository):
        """Test heatmap data with no kills."""
        mock_repository.get_heatmap_data.return_value = []

        result = service.get_heatmap_data(days=7, min_kills=5)

        assert len(result) == 0

    def test_get_heatmap_data_sorted_by_kills(self, service, mock_repository):
        """Test that heatmap data preserves repository sort order."""
        # Repository returns data already sorted by kills DESC
        mock_repository.get_heatmap_data.return_value = [
            {
                "system_id": 2,
                "name": "System B",
                "region_id": 1,
                "region": "Region A",
                "security": 0.5,
                "x": 2.0,
                "z": 2.0,
                "kills": 100,
            },
            {
                "system_id": 3,
                "name": "System C",
                "region_id": 1,
                "region": "Region A",
                "security": 0.5,
                "x": 3.0,
                "z": 3.0,
                "kills": 75,
            },
            {
                "system_id": 1,
                "name": "System A",
                "region_id": 1,
                "region": "Region A",
                "security": 0.5,
                "x": 1.0,
                "z": 1.0,
                "kills": 50,
            },
        ]

        result = service.get_heatmap_data(days=7, min_kills=5)

        # Verify order is preserved (already sorted by repository)
        assert result[0].kills == 100
        assert result[1].kills == 75
        assert result[2].kills == 50


class TestDetectDoctrines:
    """Tests for detect_doctrines method."""

    def test_detect_doctrines_success(self, service, mock_repository):
        """Test successfully detecting fleet doctrines."""
        mock_repository.get_doctrine_losses.return_value = [
            {
                "date": date(2025, 12, 8),
                "system_id": 30000142,
                "system_name": "Jita",
                "ship_type_id": 17726,
                "ship_name": "Muninn",
                "fleet_size": 25,
            },
            {
                "date": date(2025, 12, 7),
                "system_id": 30002187,
                "system_name": "Amarr",
                "ship_type_id": 17932,
                "ship_name": "Eagle",
                "fleet_size": 15,
            },
        ]

        result = service.detect_doctrines(region_id=10000002, days=7)

        assert len(result) == 2
        assert isinstance(result[0], DoctrineDetection)
        assert result[0].ship_name == "Muninn"
        assert result[0].fleet_size == 25
        assert result[0].system_name == "Jita"

        mock_repository.get_doctrine_losses.assert_called_once_with(
            region_id=10000002, days=7, min_size=10
        )

    def test_detect_doctrines_empty(self, service, mock_repository):
        """Test doctrine detection with no doctrines found."""
        mock_repository.get_doctrine_losses.return_value = []

        result = service.detect_doctrines(region_id=10000002, days=7)

        assert len(result) == 0

    def test_detect_doctrines_uses_config_min_size(self, service, mock_repository):
        """Test that doctrine detection uses config min fleet size."""
        mock_repository.get_doctrine_losses.return_value = []

        service.detect_doctrines(region_id=10000002, days=7)

        # Should use WAR_DOCTRINE_MIN_FLEET_SIZE from config (10)
        mock_repository.get_doctrine_losses.assert_called_once_with(
            region_id=10000002, days=7, min_size=10
        )


class TestGetSystemDangerScore:
    """Tests for get_system_danger_score method."""

    def test_get_system_danger_score_no_kills(self, service, mock_repository):
        """Test danger score for safe system with no kills."""
        mock_repository.get_system_kills.return_value = 0

        result = service.get_system_danger_score(system_id=30000142, days=1)

        assert isinstance(result, DangerScore)
        assert result.system_id == 30000142
        assert result.kills_24h == 0
        assert result.danger_score == 0
        assert result.is_dangerous is False

    def test_get_system_danger_score_low_danger(self, service, mock_repository):
        """Test danger score for low activity system."""
        mock_repository.get_system_kills.return_value = 3

        result = service.get_system_danger_score(system_id=30000142, days=1)

        assert result.kills_24h == 3
        assert result.danger_score == 3
        assert result.is_dangerous is False

    def test_get_system_danger_score_dangerous(self, service, mock_repository):
        """Test danger score for dangerous system."""
        mock_repository.get_system_kills.return_value = 35

        result = service.get_system_danger_score(system_id=30000142, days=1)

        assert result.kills_24h == 35
        assert result.danger_score == 35
        assert result.is_dangerous is True  # >= 5

    def test_get_system_danger_score_very_dangerous(self, service, mock_repository):
        """Test danger score for very dangerous system."""
        mock_repository.get_system_kills.return_value = 100

        result = service.get_system_danger_score(system_id=30000142, days=1)

        assert result.kills_24h == 100
        assert result.danger_score == 100
        assert result.is_dangerous is True

    def test_get_system_danger_score_threshold(self, service, mock_repository):
        """Test danger threshold at exactly 5 kills."""
        mock_repository.get_system_kills.return_value = 5

        result = service.get_system_danger_score(system_id=30000142, days=1)

        assert result.kills_24h == 5
        assert result.danger_score == 5
        assert result.is_dangerous is True  # >= 5


class TestGetConflictIntel:
    """Tests for get_conflict_intel method."""

    def test_get_conflict_intel_all_alliances(self, service, mock_repository):
        """Test getting conflict intel for all alliances."""
        mock_repository.get_conflict_intel.return_value = [
            {
                "alliance_id": 1,
                "alliance_name": "Alliance A",
                "enemy_alliances": ["Alliance B", "Alliance C"],
                "total_losses": 150,
                "active_fronts": 3,
            },
            {
                "alliance_id": 2,
                "alliance_name": "Alliance B",
                "enemy_alliances": ["Alliance A"],
                "total_losses": 100,
                "active_fronts": 2,
            },
        ]

        result = service.get_conflict_intel(alliance_id=None, days=7)

        assert len(result) == 2
        assert isinstance(result[0], ConflictIntel)
        assert result[0].alliance_name == "Alliance A"
        assert len(result[0].enemy_alliances) == 2
        assert result[0].total_losses == 150
        assert result[0].active_fronts == 3

        mock_repository.get_conflict_intel.assert_called_once_with(
            alliance_id=None, days=7
        )

    def test_get_conflict_intel_specific_alliance(self, service, mock_repository):
        """Test getting conflict intel for specific alliance."""
        mock_repository.get_conflict_intel.return_value = [
            {
                "alliance_id": 1,
                "alliance_name": "Alliance A",
                "enemy_alliances": ["Alliance B"],
                "total_losses": 75,
                "active_fronts": 1,
            }
        ]

        result = service.get_conflict_intel(alliance_id=1, days=7)

        assert len(result) == 1
        assert result[0].alliance_id == 1

        mock_repository.get_conflict_intel.assert_called_once_with(
            alliance_id=1, days=7
        )

    def test_get_conflict_intel_empty(self, service, mock_repository):
        """Test conflict intel with no conflicts."""
        mock_repository.get_conflict_intel.return_value = []

        result = service.get_conflict_intel(alliance_id=None, days=7)

        assert len(result) == 0

    def test_get_conflict_intel_no_enemies(self, service, mock_repository):
        """Test alliance with losses but no identified enemies."""
        mock_repository.get_conflict_intel.return_value = [
            {
                "alliance_id": 1,
                "alliance_name": "Alliance A",
                "enemy_alliances": [],
                "total_losses": 10,
                "active_fronts": 1,
            }
        ]

        result = service.get_conflict_intel(alliance_id=1, days=7)

        assert len(result) == 1
        assert len(result[0].enemy_alliances) == 0
