"""
Tests for Cargo Service Models

Following TDD approach - tests written before implementation
"""

import pytest
from pydantic import ValidationError

from src.services.cargo.models import (
    CargoItem,
    CargoItemBreakdown,
    CargoCalculation,
    ShipInfo,
    ShipRecommendation,
    ShipRecommendations,
)


class TestCargoItem:
    """Test CargoItem model"""

    def test_create_cargo_item(self):
        """Test creating a valid cargo item"""
        item = CargoItem(type_id=34, quantity=100)
        assert item.type_id == 34
        assert item.quantity == 100

    def test_cargo_item_type_id_must_be_positive(self):
        """Test type_id validation"""
        with pytest.raises(ValidationError) as exc_info:
            CargoItem(type_id=0, quantity=100)
        assert "type_id" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            CargoItem(type_id=-1, quantity=100)
        assert "type_id" in str(exc_info.value)

    def test_cargo_item_quantity_must_be_positive(self):
        """Test quantity validation"""
        with pytest.raises(ValidationError) as exc_info:
            CargoItem(type_id=34, quantity=0)
        assert "quantity" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            CargoItem(type_id=34, quantity=-1)
        assert "quantity" in str(exc_info.value)

    def test_cargo_item_defaults(self):
        """Test default values"""
        item = CargoItem(type_id=34)
        assert item.quantity == 1


class TestCargoItemBreakdown:
    """Test CargoItemBreakdown model"""

    def test_create_cargo_item_breakdown(self):
        """Test creating a valid cargo item breakdown"""
        item = CargoItemBreakdown(
            type_id=34,
            quantity=100,
            unit_volume=0.01,
            total_volume=1.0,
        )
        assert item.type_id == 34
        assert item.quantity == 100
        assert item.unit_volume == 0.01
        assert item.total_volume == 1.0

    def test_cargo_item_breakdown_validation(self):
        """Test validation rules"""
        # Valid with zero volume
        item = CargoItemBreakdown(
            type_id=34, quantity=100, unit_volume=0, total_volume=0
        )
        assert item.unit_volume == 0

        # Invalid negative volume
        with pytest.raises(ValidationError) as exc_info:
            CargoItemBreakdown(
                type_id=34, quantity=100, unit_volume=-0.01, total_volume=1.0
            )
        assert "unit_volume" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            CargoItemBreakdown(
                type_id=34, quantity=100, unit_volume=0.01, total_volume=-1.0
            )
        assert "total_volume" in str(exc_info.value)

    def test_cargo_item_breakdown_calculated_total(self):
        """Test that total_volume calculation is correct"""
        item = CargoItemBreakdown(
            type_id=34, quantity=100, unit_volume=0.01, total_volume=1.0
        )
        # Manual calculation check
        assert item.unit_volume * item.quantity == pytest.approx(item.total_volume)


class TestCargoCalculation:
    """Test CargoCalculation model"""

    def test_create_cargo_calculation_empty(self):
        """Test creating an empty cargo calculation"""
        calc = CargoCalculation(
            total_volume_m3=0.0, total_volume_formatted="0 m³", items=[]
        )
        assert calc.total_volume_m3 == 0.0
        assert calc.total_volume_formatted == "0 m³"
        assert len(calc.items) == 0

    def test_create_cargo_calculation_with_items(self):
        """Test creating a cargo calculation with items"""
        items = [
            CargoItemBreakdown(
                type_id=34, quantity=100, unit_volume=0.01, total_volume=1.0
            ),
            CargoItemBreakdown(
                type_id=35, quantity=50, unit_volume=0.02, total_volume=1.0
            ),
        ]
        calc = CargoCalculation(
            total_volume_m3=2.0, total_volume_formatted="2 m³", items=items
        )
        assert calc.total_volume_m3 == 2.0
        assert len(calc.items) == 2

    def test_cargo_calculation_validation(self):
        """Test validation rules"""
        # Negative total volume should fail
        with pytest.raises(ValidationError) as exc_info:
            CargoCalculation(
                total_volume_m3=-1.0, total_volume_formatted="0 m³", items=[]
            )
        assert "total_volume_m3" in str(exc_info.value)


class TestShipInfo:
    """Test ShipInfo model"""

    def test_create_ship_info(self):
        """Test creating a valid ship info"""
        ship = ShipInfo(
            ship_type="industrial", ship_name="Industrial (Nereus, etc.)", capacity=5000
        )
        assert ship.ship_type == "industrial"
        assert ship.ship_name == "Industrial (Nereus, etc.)"
        assert ship.capacity == 5000

    def test_ship_info_capacity_must_be_positive(self):
        """Test capacity validation"""
        with pytest.raises(ValidationError) as exc_info:
            ShipInfo(ship_type="industrial", ship_name="Industrial", capacity=0)
        assert "capacity" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            ShipInfo(ship_type="industrial", ship_name="Industrial", capacity=-100)
        assert "capacity" in str(exc_info.value)


class TestShipRecommendation:
    """Test ShipRecommendation model"""

    def test_create_ship_recommendation(self):
        """Test creating a valid ship recommendation"""
        rec = ShipRecommendation(
            ship_type="industrial",
            ship_name="Industrial (Nereus, etc.)",
            capacity=5000,
            trips=1,
            fill_percent=50.0,
            excess_capacity=2500,
        )
        assert rec.ship_type == "industrial"
        assert rec.capacity == 5000
        assert rec.trips == 1
        assert rec.fill_percent == 50.0
        assert rec.excess_capacity == 2500

    def test_ship_recommendation_validation(self):
        """Test validation rules"""
        # trips must be >= 1
        with pytest.raises(ValidationError) as exc_info:
            ShipRecommendation(
                ship_type="industrial",
                ship_name="Industrial",
                capacity=5000,
                trips=0,
                fill_percent=50.0,
                excess_capacity=2500,
            )
        assert "trips" in str(exc_info.value)

        # fill_percent can be 0-100
        rec = ShipRecommendation(
            ship_type="industrial",
            ship_name="Industrial",
            capacity=5000,
            trips=1,
            fill_percent=0.0,
            excess_capacity=5000,
        )
        assert rec.fill_percent == 0.0

        rec = ShipRecommendation(
            ship_type="industrial",
            ship_name="Industrial",
            capacity=5000,
            trips=1,
            fill_percent=100.0,
            excess_capacity=0,
        )
        assert rec.fill_percent == 100.0

    def test_ship_recommendation_multiple_trips(self):
        """Test ship recommendation with multiple trips"""
        rec = ShipRecommendation(
            ship_type="freighter",
            ship_name="Freighter",
            capacity=1000000,
            trips=3,
            fill_percent=75.5,
            excess_capacity=734567,
        )
        assert rec.trips == 3
        assert rec.fill_percent == 75.5


class TestShipRecommendations:
    """Test ShipRecommendations model"""

    def test_create_ship_recommendations(self):
        """Test creating ship recommendations"""
        recommended = ShipRecommendation(
            ship_type="industrial",
            ship_name="Industrial",
            capacity=5000,
            trips=1,
            fill_percent=50.0,
            excess_capacity=2500,
        )
        safe = ShipRecommendation(
            ship_type="blockade_runner",
            ship_name="Blockade Runner",
            capacity=10000,
            trips=1,
            fill_percent=25.0,
            excess_capacity=7500,
        )
        all_options = [recommended, safe]

        recs = ShipRecommendations(
            volume_m3=2500.0,
            volume_formatted="2.5K m³",
            recommended=recommended,
            safe_option=safe,
            all_options=all_options,
        )

        assert recs.volume_m3 == 2500.0
        assert recs.volume_formatted == "2.5K m³"
        assert recs.recommended.ship_type == "industrial"
        assert recs.safe_option.ship_type == "blockade_runner"
        assert len(recs.all_options) == 2

    def test_ship_recommendations_no_safe_option(self):
        """Test ship recommendations without safe option"""
        recommended = ShipRecommendation(
            ship_type="shuttle",
            ship_name="Shuttle",
            capacity=10,
            trips=1,
            fill_percent=50.0,
            excess_capacity=5,
        )

        recs = ShipRecommendations(
            volume_m3=5.0,
            volume_formatted="5 m³",
            recommended=recommended,
            safe_option=None,
            all_options=[recommended],
        )

        assert recs.safe_option is None
        assert len(recs.all_options) == 1

    def test_ship_recommendations_validation(self):
        """Test validation rules"""
        recommended = ShipRecommendation(
            ship_type="industrial",
            ship_name="Industrial",
            capacity=5000,
            trips=1,
            fill_percent=50.0,
            excess_capacity=2500,
        )

        # Negative volume should fail
        with pytest.raises(ValidationError) as exc_info:
            ShipRecommendations(
                volume_m3=-100.0,
                volume_formatted="0 m³",
                recommended=recommended,
                safe_option=None,
                all_options=[recommended],
            )
        assert "volume_m3" in str(exc_info.value)

    def test_ship_recommendations_empty_options(self):
        """Test ship recommendations with empty options list"""
        recommended = ShipRecommendation(
            ship_type="freighter",
            ship_name="Freighter",
            capacity=1000000,
            trips=1,
            fill_percent=50.0,
            excess_capacity=500000,
        )

        recs = ShipRecommendations(
            volume_m3=500000.0,
            volume_formatted="500K m³",
            recommended=recommended,
            safe_option=None,
            all_options=[],
        )

        assert len(recs.all_options) == 0
