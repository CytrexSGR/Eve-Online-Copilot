"""Tests for War Analyzer domain models."""

import pytest
from datetime import date
from pydantic import ValidationError

from src.services.warroom.analyzer_models import (
    DemandItem,
    DemandAnalysis,
    HeatmapPoint,
    DoctrineDetection,
    DangerScore,
    ConflictIntel,
)


class TestDemandItem:
    """Tests for DemandItem model."""

    def test_demand_item_valid(self):
        """Test creating valid demand item."""
        item = DemandItem(
            type_id=648,
            name="Tritanium",
            quantity=1000,
            market_stock=500,
            gap=500,
        )

        assert item.type_id == 648
        assert item.name == "Tritanium"
        assert item.quantity == 1000
        assert item.market_stock == 500
        assert item.gap == 500

    def test_demand_item_defaults(self):
        """Test demand item with default values."""
        item = DemandItem(
            type_id=648,
            name="Tritanium",
            quantity=1000,
        )

        assert item.market_stock == 0
        assert item.gap == 0

    def test_demand_item_missing_required(self):
        """Test demand item fails without required fields."""
        with pytest.raises(ValidationError):
            DemandItem(type_id=648)

    def test_demand_item_from_dict(self):
        """Test creating demand item from dict."""
        data = {
            "type_id": 648,
            "name": "Tritanium",
            "quantity": 1000,
            "market_stock": 500,
            "gap": 500,
        }

        item = DemandItem(**data)

        assert item.type_id == 648
        assert item.name == "Tritanium"


class TestDemandAnalysis:
    """Tests for DemandAnalysis model."""

    def test_demand_analysis_valid(self):
        """Test creating valid demand analysis."""
        ships = [
            DemandItem(type_id=1, name="Ship A", quantity=10, market_stock=5, gap=5),
            DemandItem(type_id=2, name="Ship B", quantity=8, market_stock=0, gap=8),
        ]

        items = [
            DemandItem(type_id=3, name="Item A", quantity=100, market_stock=50, gap=50),
        ]

        analysis = DemandAnalysis(
            region_id=10000002,
            days=7,
            ships_lost=ships,
            items_lost=items,
            market_gaps=[ships[1], items[0]],
        )

        assert analysis.region_id == 10000002
        assert analysis.days == 7
        assert len(analysis.ships_lost) == 2
        assert len(analysis.items_lost) == 1
        assert len(analysis.market_gaps) == 2

    def test_demand_analysis_empty_lists(self):
        """Test demand analysis with empty lists."""
        analysis = DemandAnalysis(
            region_id=10000002,
            days=7,
        )

        assert len(analysis.ships_lost) == 0
        assert len(analysis.items_lost) == 0
        assert len(analysis.market_gaps) == 0

    def test_demand_analysis_missing_required(self):
        """Test demand analysis fails without required fields."""
        with pytest.raises(ValidationError):
            DemandAnalysis(region_id=10000002)


class TestHeatmapPoint:
    """Tests for HeatmapPoint model."""

    def test_heatmap_point_valid(self):
        """Test creating valid heatmap point."""
        point = HeatmapPoint(
            system_id=30000142,
            name="Jita",
            region_id=10000002,
            region="The Forge",
            security=0.95,
            x=12.34,
            z=56.78,
            kills=150,
        )

        assert point.system_id == 30000142
        assert point.name == "Jita"
        assert point.region_id == 10000002
        assert point.region == "The Forge"
        assert point.security == 0.95
        assert point.x == 12.34
        assert point.z == 56.78
        assert point.kills == 150

    def test_heatmap_point_missing_required(self):
        """Test heatmap point fails without required fields."""
        with pytest.raises(ValidationError):
            HeatmapPoint(
                system_id=30000142,
                name="Jita",
            )

    def test_heatmap_point_from_dict(self):
        """Test creating heatmap point from dict."""
        data = {
            "system_id": 30000142,
            "name": "Jita",
            "region_id": 10000002,
            "region": "The Forge",
            "security": 0.95,
            "x": 12.34,
            "z": 56.78,
            "kills": 150,
        }

        point = HeatmapPoint(**data)

        assert point.system_id == 30000142
        assert point.kills == 150


class TestDoctrineDetection:
    """Tests for DoctrineDetection model."""

    def test_doctrine_detection_valid(self):
        """Test creating valid doctrine detection."""
        doctrine = DoctrineDetection(
            date=date(2025, 12, 8),
            system_id=30000142,
            system_name="Jita",
            ship_type_id=17726,
            ship_name="Muninn",
            fleet_size=25,
            estimated_alliance="Test Alliance",
        )

        assert doctrine.date == date(2025, 12, 8)
        assert doctrine.system_id == 30000142
        assert doctrine.system_name == "Jita"
        assert doctrine.ship_type_id == 17726
        assert doctrine.ship_name == "Muninn"
        assert doctrine.fleet_size == 25
        assert doctrine.estimated_alliance == "Test Alliance"

    def test_doctrine_detection_no_alliance(self):
        """Test doctrine detection without alliance."""
        doctrine = DoctrineDetection(
            date=date(2025, 12, 8),
            system_id=30000142,
            system_name="Jita",
            ship_type_id=17726,
            ship_name="Muninn",
            fleet_size=25,
        )

        assert doctrine.estimated_alliance is None

    def test_doctrine_detection_missing_required(self):
        """Test doctrine detection fails without required fields."""
        with pytest.raises(ValidationError):
            DoctrineDetection(
                date=date(2025, 12, 8),
                system_id=30000142,
            )


class TestDangerScore:
    """Tests for DangerScore model."""

    def test_danger_score_valid(self):
        """Test creating valid danger score."""
        score = DangerScore(
            system_id=30000142,
            danger_score=7,
            kills_24h=35,
            is_dangerous=True,
        )

        assert score.system_id == 30000142
        assert score.danger_score == 7
        assert score.kills_24h == 35
        assert score.is_dangerous is True

    def test_danger_score_not_dangerous(self):
        """Test danger score for safe system."""
        score = DangerScore(
            system_id=30000142,
            danger_score=2,
            kills_24h=3,
            is_dangerous=False,
        )

        assert score.danger_score == 2
        assert score.is_dangerous is False

    def test_danger_score_missing_required(self):
        """Test danger score fails without required fields."""
        with pytest.raises(ValidationError):
            DangerScore(system_id=30000142)


class TestConflictIntel:
    """Tests for ConflictIntel model."""

    def test_conflict_intel_valid(self):
        """Test creating valid conflict intel."""
        intel = ConflictIntel(
            alliance_id=123456,
            alliance_name="Test Alliance",
            enemy_alliances=["Enemy 1", "Enemy 2"],
            total_losses=150,
            active_fronts=3,
        )

        assert intel.alliance_id == 123456
        assert intel.alliance_name == "Test Alliance"
        assert len(intel.enemy_alliances) == 2
        assert intel.total_losses == 150
        assert intel.active_fronts == 3

    def test_conflict_intel_no_enemies(self):
        """Test conflict intel with no enemies."""
        intel = ConflictIntel(
            alliance_id=123456,
            alliance_name="Test Alliance",
            total_losses=0,
            active_fronts=0,
        )

        assert len(intel.enemy_alliances) == 0

    def test_conflict_intel_missing_required(self):
        """Test conflict intel fails without required fields."""
        with pytest.raises(ValidationError):
            ConflictIntel(alliance_id=123456)

    def test_conflict_intel_from_dict(self):
        """Test creating conflict intel from dict."""
        data = {
            "alliance_id": 123456,
            "alliance_name": "Test Alliance",
            "enemy_alliances": ["Enemy 1"],
            "total_losses": 50,
            "active_fronts": 1,
        }

        intel = ConflictIntel(**data)

        assert intel.alliance_id == 123456
        assert len(intel.enemy_alliances) == 1
