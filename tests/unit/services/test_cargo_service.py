"""
Unit tests for Cargo Service

Tests for cargo volume calculations and ship recommendations following TDD
"""

import pytest
from unittest.mock import Mock, MagicMock
from typing import List

from src.services.cargo.service import CargoService
from src.services.cargo.models import (
    CargoItem,
    CargoCalculation,
    CargoItemBreakdown,
    ShipRecommendations,
    ShipRecommendation,
)
from src.services.cargo.repository import CargoRepository


class TestCargoServiceVolumeCalculation:
    """Test calculate_cargo_volume method"""

    @pytest.fixture
    def mock_repository(self):
        """Create mock repository"""
        return Mock(spec=CargoRepository)

    @pytest.fixture
    def service(self, mock_repository):
        """Create service with mock repository"""
        return CargoService(repository=mock_repository)

    def test_calculate_single_item(self, service, mock_repository):
        """Test volume calculation for single item"""
        # Given
        mock_repository.get_item_volume.return_value = 10.0
        items = [CargoItem(type_id=34, quantity=5)]

        # When
        result = service.calculate_cargo_volume(items)

        # Then
        assert isinstance(result, CargoCalculation)
        assert result.total_volume_m3 == 50.0
        assert result.total_volume_formatted == "50 m³"
        assert len(result.items) == 1
        assert result.items[0].type_id == 34
        assert result.items[0].quantity == 5
        assert result.items[0].unit_volume == 10.0
        assert result.items[0].total_volume == 50.0
        mock_repository.get_item_volume.assert_called_once_with(34)

    def test_calculate_multiple_items(self, service, mock_repository):
        """Test volume calculation for multiple items"""
        # Given
        mock_repository.get_item_volume.side_effect = [10.0, 20.0, 5.0]
        items = [
            CargoItem(type_id=34, quantity=5),
            CargoItem(type_id=35, quantity=3),
            CargoItem(type_id=36, quantity=10),
        ]

        # When
        result = service.calculate_cargo_volume(items)

        # Then
        assert result.total_volume_m3 == 160.0  # 50 + 60 + 50
        assert len(result.items) == 3
        assert result.items[0].total_volume == 50.0
        assert result.items[1].total_volume == 60.0
        assert result.items[2].total_volume == 50.0

    def test_calculate_empty_items_list(self, service, mock_repository):
        """Test volume calculation with empty items list"""
        # Given
        items = []

        # When
        result = service.calculate_cargo_volume(items)

        # Then
        assert result.total_volume_m3 == 0.0
        assert result.total_volume_formatted == "0 m³"
        assert len(result.items) == 0
        mock_repository.get_item_volume.assert_not_called()

    def test_calculate_with_unknown_item_volume(self, service, mock_repository):
        """Test that items with unknown volumes (None) are skipped"""
        # Given
        mock_repository.get_item_volume.side_effect = [10.0, None, 5.0]
        items = [
            CargoItem(type_id=34, quantity=5),
            CargoItem(type_id=999, quantity=3),  # Unknown item
            CargoItem(type_id=36, quantity=10),
        ]

        # When
        result = service.calculate_cargo_volume(items)

        # Then
        assert result.total_volume_m3 == 100.0  # 50 + 0 + 50 (skip unknown)
        assert len(result.items) == 2  # Only known items in breakdown
        assert result.items[0].type_id == 34
        assert result.items[1].type_id == 36

    def test_calculate_all_unknown_items(self, service, mock_repository):
        """Test with all items having unknown volumes"""
        # Given
        mock_repository.get_item_volume.side_effect = [None, None, None]
        items = [
            CargoItem(type_id=999, quantity=5),
            CargoItem(type_id=998, quantity=3),
            CargoItem(type_id=997, quantity=10),
        ]

        # When
        result = service.calculate_cargo_volume(items)

        # Then
        assert result.total_volume_m3 == 0.0
        assert len(result.items) == 0

    def test_calculate_with_large_volume(self, service, mock_repository):
        """Test volume calculation with large volumes"""
        # Given
        mock_repository.get_item_volume.return_value = 1000.0
        items = [CargoItem(type_id=34, quantity=1500)]

        # When
        result = service.calculate_cargo_volume(items)

        # Then
        assert result.total_volume_m3 == 1500000.0
        assert result.total_volume_formatted == "1.50M m³"

    def test_calculate_with_decimal_volumes(self, service, mock_repository):
        """Test volume calculation with decimal volumes"""
        # Given
        mock_repository.get_item_volume.return_value = 0.01
        items = [CargoItem(type_id=34, quantity=100)]

        # When
        result = service.calculate_cargo_volume(items)

        # Then
        assert result.total_volume_m3 == 1.0
        assert result.total_volume_formatted == "1 m³"


class TestCargoServiceShipRecommendation:
    """Test recommend_ship method"""

    @pytest.fixture
    def mock_repository(self):
        """Create mock repository"""
        return Mock(spec=CargoRepository)

    @pytest.fixture
    def service(self, mock_repository):
        """Create service with mock repository"""
        return CargoService(repository=mock_repository)

    def test_recommend_ship_small_volume(self, service):
        """Test recommendation for small volume (fits in frigate)"""
        # Given
        volume = 300.0  # Fits in frigate (400 m³)

        # When
        result = service.recommend_ship(volume, prefer_safe=False)

        # Then
        assert isinstance(result, ShipRecommendations)
        assert result.volume_m3 == 300.0
        assert result.volume_formatted == "300 m³"
        assert result.recommended.ship_type == "frigate"  # Smallest that fits
        assert result.recommended.trips == 1
        assert result.recommended.capacity == 400

    def test_recommend_ship_industrial_size(self, service):
        """Test recommendation for industrial-sized cargo"""
        # Given
        volume = 3000.0  # Fits in industrial (5000 m³)

        # When
        result = service.recommend_ship(volume, prefer_safe=False)

        # Then
        assert result.recommended.ship_type == "industrial"
        assert result.recommended.trips == 1
        assert result.recommended.fill_percent == pytest.approx(60.0, rel=0.1)
        assert result.recommended.excess_capacity == 2000.0

    def test_recommend_ship_multiple_options(self, service):
        """Test that multiple ship options are returned"""
        # Given
        volume = 1000.0

        # When
        result = service.recommend_ship(volume, prefer_safe=False)

        # Then
        assert len(result.all_options) >= 1
        # All options should fit the volume in 1 trip
        for option in result.all_options:
            assert option.capacity >= volume
            assert option.trips == 1

    def test_recommend_ship_sorted_by_capacity(self, service):
        """Test that recommendations are sorted by capacity (smallest first)"""
        # Given
        volume = 1000.0

        # When
        result = service.recommend_ship(volume, prefer_safe=False)

        # Then
        capacities = [opt.capacity for opt in result.all_options]
        assert capacities == sorted(capacities)

    def test_recommend_ship_freighter_multiple_trips(self, service):
        """Test freighter recommendation for oversized cargo (multiple trips)"""
        # Given
        volume = 2500000.0  # Requires 3 freighter trips (1M m³ each)

        # When
        result = service.recommend_ship(volume, prefer_safe=False)

        # Then
        assert result.recommended.ship_type == "freighter"
        assert result.recommended.trips == 3
        # Fill percent should be volume / (capacity * trips) * 100
        expected_fill = (2500000.0 / (1000000.0 * 3)) * 100
        assert result.recommended.fill_percent == pytest.approx(expected_fill, rel=0.1)
        # Excess should be (capacity * trips) - volume
        expected_excess = (1000000.0 * 3) - 2500000.0
        assert result.recommended.excess_capacity == pytest.approx(expected_excess, rel=1.0)

    def test_recommend_ship_exactly_fits(self, service):
        """Test recommendation when volume exactly matches ship capacity"""
        # Given
        volume = 5000.0  # Exactly fits industrial

        # When
        result = service.recommend_ship(volume, prefer_safe=False)

        # Then
        assert result.recommended.ship_type == "industrial"
        assert result.recommended.trips == 1
        assert result.recommended.fill_percent == 100.0
        assert result.recommended.excess_capacity == 0.0

    def test_recommend_ship_safe_option_blockade_runner(self, service):
        """Test safe option recommendation (blockade runner)"""
        # Given
        volume = 8000.0  # Fits in blockade runner (10,000 m³)

        # When
        result = service.recommend_ship(volume, prefer_safe=True)

        # Then
        assert result.safe_option is not None
        assert result.safe_option.ship_type in ["blockade_runner", "deep_space_transport"]

    def test_recommend_ship_safe_option_deep_space_transport(self, service):
        """Test safe option with larger volume needing DST"""
        # Given
        volume = 50000.0  # Too big for blockade runner, needs DST

        # When
        result = service.recommend_ship(volume, prefer_safe=True)

        # Then
        assert result.safe_option is not None
        assert result.safe_option.ship_type == "deep_space_transport"

    def test_recommend_ship_no_safe_option_available(self, service):
        """Test when no safe option can fit the cargo"""
        # Given
        volume = 100000.0  # Too big for DST, no safe option

        # When
        result = service.recommend_ship(volume, prefer_safe=True)

        # Then
        # Safe option should be None if volume exceeds DST capacity
        if volume > 60000:
            assert result.safe_option is None

    def test_recommend_ship_zero_volume(self, service):
        """Test recommendation with zero volume"""
        # Given
        volume = 0.0

        # When
        result = service.recommend_ship(volume, prefer_safe=False)

        # Then
        assert result.volume_m3 == 0.0
        assert result.recommended is not None
        # Should recommend smallest ship (shuttle)
        assert result.recommended.ship_type == "shuttle"

    def test_recommend_ship_tiny_volume(self, service):
        """Test recommendation with very small volume"""
        # Given
        volume = 0.5

        # When
        result = service.recommend_ship(volume, prefer_safe=False)

        # Then
        assert result.recommended.ship_type == "shuttle"
        assert result.recommended.trips == 1


class TestCargoServiceVolumeFormatting:
    """Test _format_volume private method"""

    @pytest.fixture
    def mock_repository(self):
        """Create mock repository"""
        return Mock(spec=CargoRepository)

    @pytest.fixture
    def service(self, mock_repository):
        """Create service with mock repository"""
        return CargoService(repository=mock_repository)

    def test_format_volume_millions(self, service):
        """Test formatting volumes in millions"""
        assert service._format_volume(1000000.0) == "1.00M m³"
        assert service._format_volume(1500000.0) == "1.50M m³"
        assert service._format_volume(2345678.0) == "2.35M m³"
        assert service._format_volume(999999999.0) == "1000.00M m³"

    def test_format_volume_thousands(self, service):
        """Test formatting volumes in thousands"""
        assert service._format_volume(1000.0) == "1.0K m³"
        assert service._format_volume(5000.0) == "5.0K m³"
        assert service._format_volume(1234.5) == "1.2K m³"
        assert service._format_volume(999999.0) == "1000.0K m³"

    def test_format_volume_small(self, service):
        """Test formatting small volumes (< 1000)"""
        assert service._format_volume(100.0) == "100 m³"
        assert service._format_volume(250.5) == "250 m³"  # Rounded down by :.0f
        assert service._format_volume(0.5) == "0 m³"  # Rounded down
        assert service._format_volume(999.0) == "999 m³"

    def test_format_volume_edge_cases(self, service):
        """Test edge cases for volume formatting"""
        assert service._format_volume(0.0) == "0 m³"
        assert service._format_volume(1.0) == "1 m³"
        assert service._format_volume(999.9) == "1000 m³"  # Rounds up to 1000
        assert service._format_volume(1000.0) == "1.0K m³"
        assert service._format_volume(999999.9) == "1000.0K m³"  # Rounds to 1000.0K
        assert service._format_volume(1000000.0) == "1.00M m³"


class TestCargoServiceIntegration:
    """Integration tests combining multiple methods"""

    @pytest.fixture
    def mock_repository(self):
        """Create mock repository"""
        return Mock(spec=CargoRepository)

    @pytest.fixture
    def service(self, mock_repository):
        """Create service with mock repository"""
        return CargoService(repository=mock_repository)

    def test_full_workflow_small_cargo(self, service, mock_repository):
        """Test full workflow: calculate volume + recommend ship for small cargo"""
        # Given
        mock_repository.get_item_volume.side_effect = [10.0, 5.0]
        items = [
            CargoItem(type_id=34, quantity=10),
            CargoItem(type_id=35, quantity=20),
        ]

        # When
        volume_result = service.calculate_cargo_volume(items)
        ship_result = service.recommend_ship(volume_result.total_volume_m3, prefer_safe=False)

        # Then
        assert volume_result.total_volume_m3 == 200.0
        assert ship_result.volume_m3 == 200.0
        assert ship_result.recommended.trips == 1

    def test_full_workflow_large_cargo(self, service, mock_repository):
        """Test full workflow: calculate volume + recommend ship for large cargo"""
        # Given
        mock_repository.get_item_volume.return_value = 1000.0
        items = [CargoItem(type_id=34, quantity=2000)]

        # When
        volume_result = service.calculate_cargo_volume(items)
        ship_result = service.recommend_ship(volume_result.total_volume_m3, prefer_safe=False)

        # Then
        assert volume_result.total_volume_m3 == 2000000.0
        assert volume_result.total_volume_formatted == "2.00M m³"
        assert ship_result.recommended.ship_type == "freighter"
        assert ship_result.recommended.trips == 2

    def test_full_workflow_with_safe_option(self, service, mock_repository):
        """Test full workflow with safe transport option"""
        # Given
        mock_repository.get_item_volume.return_value = 50.0
        items = [CargoItem(type_id=34, quantity=100)]

        # When
        volume_result = service.calculate_cargo_volume(items)
        ship_result = service.recommend_ship(volume_result.total_volume_m3, prefer_safe=True)

        # Then
        assert volume_result.total_volume_m3 == 5000.0
        assert ship_result.safe_option is not None
        assert ship_result.safe_option.ship_type in ["blockade_runner", "deep_space_transport"]


class TestCargoServiceDependencyInjection:
    """Test that service properly uses dependency injection"""

    def test_service_requires_repository(self):
        """Test that service requires repository in constructor"""
        # Given
        mock_repo = Mock(spec=CargoRepository)

        # When
        service = CargoService(repository=mock_repo)

        # Then
        assert service.repository == mock_repo

    def test_service_uses_repository_for_volume_lookup(self):
        """Test that service delegates volume lookup to repository"""
        # Given
        mock_repo = Mock(spec=CargoRepository)
        mock_repo.get_item_volume.return_value = 10.0
        service = CargoService(repository=mock_repo)
        items = [CargoItem(type_id=34, quantity=1)]

        # When
        service.calculate_cargo_volume(items)

        # Then
        mock_repo.get_item_volume.assert_called_once_with(34)
