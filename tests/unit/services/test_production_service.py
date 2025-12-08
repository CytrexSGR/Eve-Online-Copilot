"""
Unit tests for Production Service
Tests manufacturing calculations, asset matching, and financial analysis
"""

import math
from typing import Dict, List
from unittest.mock import Mock, MagicMock

import pytest

from src.services.production.service import ProductionService
from src.services.production.models import (
    MaterialItem,
    BillOfMaterials,
    ProductionFinancials,
    ProductionSimulation,
    QuickProfitCheck,
)
from src.services.production.repository import ProductionRepository
from src.services.market.service import MarketService
from src.core.exceptions import NotFoundError, EVECopilotError


@pytest.fixture
def mock_repository():
    """Mock ProductionRepository"""
    repo = Mock(spec=ProductionRepository)
    return repo


@pytest.fixture
def mock_market_service():
    """Mock MarketService"""
    service = Mock(spec=MarketService)
    return service


@pytest.fixture
def production_service(mock_repository, mock_market_service):
    """Create ProductionService with mocked dependencies"""
    return ProductionService(
        repository=mock_repository,
        market_service=mock_market_service,
        region_id=10000002  # The Forge
    )


class TestProductionServiceInit:
    """Test ProductionService initialization"""

    def test_init_with_default_region(self, mock_repository, mock_market_service):
        """Test initialization with default region"""
        service = ProductionService(
            repository=mock_repository,
            market_service=mock_market_service
        )
        assert service.repository == mock_repository
        assert service.market_service == mock_market_service
        assert service.region_id == 10000002  # The Forge default

    def test_init_with_custom_region(self, mock_repository, mock_market_service):
        """Test initialization with custom region"""
        service = ProductionService(
            repository=mock_repository,
            market_service=mock_market_service,
            region_id=10000043  # Domain
        )
        assert service.region_id == 10000043


class TestGetBOM:
    """Test Bill of Materials calculation with ME bonus"""

    def test_get_bom_basic(self, production_service, mock_repository):
        """Test basic BOM calculation without ME bonus"""
        mock_repository.get_blueprint_for_product.return_value = 1000
        mock_repository.get_blueprint_materials.return_value = [
            (34, 100),  # Tritanium
            (35, 50),   # Pyerite
        ]

        result = production_service.get_bom(type_id=648, runs=1, me=0)

        assert result == {34: 100, 35: 50}
        mock_repository.get_blueprint_for_product.assert_called_once_with(648)
        mock_repository.get_blueprint_materials.assert_called_once_with(1000)

    def test_get_bom_with_me_bonus(self, production_service, mock_repository):
        """Test BOM calculation with ME bonus"""
        mock_repository.get_blueprint_for_product.return_value = 1000
        mock_repository.get_blueprint_materials.return_value = [
            (34, 100),  # Tritanium: 100 * 0.9 = 90
            (35, 50),   # Pyerite: 50 * 0.9 = 45
        ]

        result = production_service.get_bom(type_id=648, runs=1, me=10)

        # ME 10 = 10% reduction, so 100 * 0.9 = 90, 50 * 0.9 = 45
        assert result == {34: 90, 35: 45}

    def test_get_bom_rounds_up(self, production_service, mock_repository):
        """Test that BOM quantities are rounded up per run"""
        mock_repository.get_blueprint_for_product.return_value = 1000
        mock_repository.get_blueprint_materials.return_value = [
            (34, 10),  # 10 * 0.9 = 9
        ]

        result = production_service.get_bom(type_id=648, runs=1, me=10)

        # 10 * 0.9 = 9.0, ceil(9.0) = 9
        assert result[34] == 9

    def test_get_bom_minimum_one(self, production_service, mock_repository):
        """Test that BOM quantities never go below 1"""
        mock_repository.get_blueprint_for_product.return_value = 1000
        mock_repository.get_blueprint_materials.return_value = [
            (34, 1),  # 1 * 0.9 = 0.9, but min is 1
        ]

        result = production_service.get_bom(type_id=648, runs=1, me=10)

        assert result[34] == 1  # Always at least 1

    def test_get_bom_multiple_runs(self, production_service, mock_repository):
        """Test BOM calculation with multiple runs"""
        mock_repository.get_blueprint_for_product.return_value = 1000
        mock_repository.get_blueprint_materials.return_value = [
            (34, 100),  # Per run: 100 * 0.9 = 90, total: 90 * 10 = 900
            (35, 50),   # Per run: 50 * 0.9 = 45, total: 45 * 10 = 450
        ]

        result = production_service.get_bom(type_id=648, runs=10, me=10)

        assert result == {34: 900, 35: 450}

    def test_get_bom_no_blueprint(self, production_service, mock_repository):
        """Test BOM when blueprint not found"""
        mock_repository.get_blueprint_for_product.return_value = None

        with pytest.raises(NotFoundError) as exc_info:
            production_service.get_bom(type_id=999999, runs=1, me=0)

        assert "blueprint" in str(exc_info.value).lower()
        assert "999999" in str(exc_info.value)


class TestGetBOMWithNames:
    """Test BOM with item names"""

    def test_get_bom_with_names(self, production_service, mock_repository):
        """Test BOM with item names"""
        mock_repository.get_blueprint_for_product.return_value = 1000
        mock_repository.get_blueprint_materials.return_value = [
            (34, 100),
            (35, 50),
        ]
        mock_repository.get_item_name.side_effect = lambda tid: {
            34: "Tritanium",
            35: "Pyerite"
        }.get(tid, "Unknown")

        result = production_service.get_bom_with_names(type_id=648, runs=1, me=0)

        assert len(result) == 2
        assert all(isinstance(item, MaterialItem) for item in result)

        # Find items by type_id
        trit = next(item for item in result if item.type_id == 34)
        pyerite = next(item for item in result if item.type_id == 35)

        assert trit.name == "Tritanium"
        assert trit.quantity == 100
        assert pyerite.name == "Pyerite"
        assert pyerite.quantity == 50

    def test_get_bom_with_names_sorted(self, production_service, mock_repository):
        """Test that BOM is sorted by name"""
        mock_repository.get_blueprint_for_product.return_value = 1000
        mock_repository.get_blueprint_materials.return_value = [
            (35, 50),   # Pyerite (comes first alphabetically)
            (34, 100),  # Tritanium
        ]
        mock_repository.get_item_name.side_effect = lambda tid: {
            34: "Tritanium",
            35: "Pyerite"
        }.get(tid, "Unknown")

        result = production_service.get_bom_with_names(type_id=648, runs=1, me=0)

        # Should be sorted by name
        assert result[0].name == "Pyerite"
        assert result[1].name == "Tritanium"


class TestMatchAssets:
    """Test asset matching against BOM"""

    def test_match_assets_all_available(self, production_service):
        """Test when all materials are available"""
        bom = {34: 100, 35: 50}
        character_assets = [
            {"type_id": 34, "quantity": 200},
            {"type_id": 35, "quantity": 100},
        ]

        available, missing = production_service.match_assets(bom, character_assets)

        assert available == {34: 100, 35: 50}
        assert missing == {}

    def test_match_assets_none_available(self, production_service):
        """Test when no materials are available"""
        bom = {34: 100, 35: 50}
        character_assets = []

        available, missing = production_service.match_assets(bom, character_assets)

        assert available == {}
        assert missing == {34: 100, 35: 50}

    def test_match_assets_partial(self, production_service):
        """Test when some materials are partially available"""
        bom = {34: 100, 35: 50, 36: 25}
        character_assets = [
            {"type_id": 34, "quantity": 200},  # Fully available
            {"type_id": 35, "quantity": 30},   # Partially available
            # type_id 36 missing
        ]

        available, missing = production_service.match_assets(bom, character_assets)

        assert available == {34: 100, 35: 30}
        assert missing == {35: 20, 36: 25}

    def test_match_assets_aggregates_quantities(self, production_service):
        """Test that asset quantities are aggregated"""
        bom = {34: 100}
        character_assets = [
            {"type_id": 34, "quantity": 30},
            {"type_id": 34, "quantity": 40},
            {"type_id": 34, "quantity": 50},
        ]

        available, missing = production_service.match_assets(bom, character_assets)

        assert available == {34: 100}  # Sum is 120, but only need 100
        assert missing == {}


class TestCalculateFinancials:
    """Test financial calculations"""

    def test_calculate_financials_basic(
        self, production_service, mock_repository, mock_market_service
    ):
        """Test basic financial calculation"""
        bom = {34: 100, 35: 50}
        missing = {35: 50}  # Only Pyerite is missing

        # Mock prices
        mock_market_service.get_cached_prices_bulk.return_value = {
            34: 5.0,    # Tritanium
            35: 10.0,   # Pyerite
            648: 2000.0  # Product
        }

        # Mock output quantity
        mock_repository.get_output_quantity.return_value = 1

        result = production_service.calculate_financials(
            type_id=648, runs=1, bom=bom, missing=missing
        )

        # Build cost: (100 * 5) + (50 * 10) = 500 + 500 = 1000
        # Cash to invest: 50 * 10 = 500
        # Revenue: 2000 * 1 = 2000
        # Profit: 2000 - 1000 = 1000
        # Margin: (1000 / 1000) * 100 = 100%
        # ROI: (1000 / 500) * 100 = 200%

        assert isinstance(result, ProductionFinancials)
        assert result.build_cost == 1000.0
        assert result.cash_to_invest == 500.0
        assert result.revenue == 2000.0
        assert result.profit == 1000.0
        assert result.margin == 100.0
        assert result.roi == 200.0

    def test_calculate_financials_with_loss(
        self, production_service, mock_repository, mock_market_service
    ):
        """Test financial calculation with loss"""
        bom = {34: 100}
        missing = {34: 100}

        mock_market_service.get_cached_prices_bulk.return_value = {
            34: 50.0,
            648: 1000.0
        }
        mock_repository.get_output_quantity.return_value = 1

        result = production_service.calculate_financials(
            type_id=648, runs=1, bom=bom, missing=missing
        )

        # Build cost: 100 * 50 = 5000
        # Revenue: 1000 * 1 = 1000
        # Profit: 1000 - 5000 = -4000 (loss)
        assert result.profit == -4000.0
        assert result.margin < 0

    def test_calculate_financials_multiple_output(
        self, production_service, mock_repository, mock_market_service
    ):
        """Test financial calculation with multiple output per run"""
        bom = {34: 100}
        missing = {}

        mock_market_service.get_cached_prices_bulk.return_value = {
            34: 5.0,
            648: 100.0
        }
        mock_repository.get_output_quantity.return_value = 10  # 10 per run

        result = production_service.calculate_financials(
            type_id=648, runs=1, bom=bom, missing=missing
        )

        # Revenue: 100 * 10 = 1000
        assert result.revenue == 1000.0

    def test_calculate_financials_no_missing(
        self, production_service, mock_repository, mock_market_service
    ):
        """Test financial calculation when all materials available"""
        bom = {34: 100}
        missing = {}  # All materials available

        mock_market_service.get_cached_prices_bulk.return_value = {
            34: 5.0,
            648: 2000.0
        }
        mock_repository.get_output_quantity.return_value = 1

        result = production_service.calculate_financials(
            type_id=648, runs=1, bom=bom, missing=missing
        )

        # Cash to invest should be 0 (nothing to buy)
        assert result.cash_to_invest == 0.0
        # ROI would be infinite, but implementation should handle this
        assert result.roi > 0 or math.isinf(result.roi)


class TestSimulateBuild:
    """Test complete production simulation"""

    def test_simulate_build_basic(
        self, production_service, mock_repository, mock_market_service
    ):
        """Test basic production simulation"""
        # Mock blueprint and materials
        mock_repository.get_blueprint_for_product.return_value = 1000
        mock_repository.get_blueprint_materials.return_value = [(34, 100)]
        mock_repository.get_item_name.side_effect = lambda tid: {
            34: "Tritanium",
            648: "Hornet"
        }.get(tid, "Unknown")
        mock_repository.get_output_quantity.return_value = 1
        mock_repository.get_base_production_time.return_value = 3600  # 1 hour

        # Mock prices
        mock_market_service.get_cached_prices_bulk.return_value = {
            34: 5.0,
            648: 1000.0
        }

        result = production_service.simulate_build(
            type_id=648,
            runs=1,
            me=0,
            te=0,
            character_assets=None,
            region_id=None
        )

        assert isinstance(result, ProductionSimulation)
        assert result.product.type_id == 648
        assert result.product.name == "Hornet"
        assert result.parameters.runs == 1
        assert result.parameters.me_level == 0
        assert result.parameters.te_level == 0
        assert result.production_time.base_seconds == 3600
        assert result.production_time.actual_seconds == 3600
        assert result.financials.build_cost == 500.0

    def test_simulate_build_with_assets(
        self, production_service, mock_repository, mock_market_service
    ):
        """Test simulation with character assets"""
        mock_repository.get_blueprint_for_product.return_value = 1000
        mock_repository.get_blueprint_materials.return_value = [(34, 100), (35, 50)]
        mock_repository.get_item_name.side_effect = lambda tid: {
            34: "Tritanium",
            35: "Pyerite",
            648: "Hornet"
        }.get(tid, "Unknown")
        mock_repository.get_output_quantity.return_value = 1
        mock_repository.get_base_production_time.return_value = 3600

        mock_market_service.get_cached_prices_bulk.return_value = {
            34: 5.0,
            35: 10.0,
            648: 2000.0
        }

        character_assets = [
            {"type_id": 34, "quantity": 100}  # Have all Tritanium
        ]

        result = production_service.simulate_build(
            type_id=648,
            runs=1,
            me=0,
            te=0,
            character_assets=character_assets,
            region_id=None
        )

        # Should have Tritanium available, Pyerite missing
        assert result.asset_match.materials_available == 1
        assert result.asset_match.materials_missing == 1
        assert not result.asset_match.fully_covered

        # Shopping list should only have Pyerite
        assert len(result.shopping_list) == 1
        assert result.shopping_list[0].type_id == 35

    def test_simulate_build_with_te_bonus(
        self, production_service, mock_repository, mock_market_service
    ):
        """Test simulation with TE bonus"""
        mock_repository.get_blueprint_for_product.return_value = 1000
        mock_repository.get_blueprint_materials.return_value = [(34, 100)]
        mock_repository.get_item_name.return_value = "Test"
        mock_repository.get_output_quantity.return_value = 1
        mock_repository.get_base_production_time.return_value = 3600  # 1 hour

        mock_market_service.get_cached_prices_bulk.return_value = {
            34: 5.0,
            648: 1000.0
        }

        result = production_service.simulate_build(
            type_id=648,
            runs=1,
            me=0,
            te=20,  # 20% time reduction
            character_assets=None,
            region_id=None
        )

        # TE 20 = 20% reduction: 3600 * 0.8 = 2880
        assert result.production_time.base_seconds == 3600
        assert result.production_time.actual_seconds == 2880
        assert "48m" in result.production_time.formatted or "0h 48m" in result.production_time.formatted

    def test_simulate_build_warns_on_loss(
        self, production_service, mock_repository, mock_market_service
    ):
        """Test that simulation warns on loss"""
        mock_repository.get_blueprint_for_product.return_value = 1000
        mock_repository.get_blueprint_materials.return_value = [(34, 100)]
        mock_repository.get_item_name.return_value = "Test"
        mock_repository.get_output_quantity.return_value = 1
        mock_repository.get_base_production_time.return_value = 3600

        # Make it unprofitable
        mock_market_service.get_cached_prices_bulk.return_value = {
            34: 100.0,  # Expensive materials
            648: 1000.0  # Cheap product
        }

        result = production_service.simulate_build(
            type_id=648, runs=1, me=0, te=0, character_assets=None, region_id=None
        )

        # Should have loss warning
        assert len(result.warnings) > 0
        assert any("LOSS WARNING" in w for w in result.warnings)

    def test_simulate_build_warns_on_low_margin(
        self, production_service, mock_repository, mock_market_service
    ):
        """Test that simulation warns on low margin"""
        mock_repository.get_blueprint_for_product.return_value = 1000
        mock_repository.get_blueprint_materials.return_value = [(34, 100)]
        mock_repository.get_item_name.return_value = "Test"
        mock_repository.get_output_quantity.return_value = 1
        mock_repository.get_base_production_time.return_value = 3600

        # Make it low margin (2%)
        mock_market_service.get_cached_prices_bulk.return_value = {
            34: 10.0,   # Cost: 1000
            648: 1020.0  # Revenue: 1020, profit: 20, margin: 2%
        }

        result = production_service.simulate_build(
            type_id=648, runs=1, me=0, te=0, character_assets=None, region_id=None
        )

        # Should have low margin warning
        assert len(result.warnings) > 0
        assert any("LOW MARGIN" in w for w in result.warnings)

    def test_simulate_build_product_not_found(
        self, production_service, mock_repository
    ):
        """Test simulation when product not found"""
        mock_repository.get_item_name.return_value = None

        with pytest.raises(NotFoundError) as exc_info:
            production_service.simulate_build(
                type_id=999999, runs=1, me=0, te=0,
                character_assets=None, region_id=None
            )

        assert "product" in str(exc_info.value).lower()

    def test_simulate_build_blueprint_not_found(
        self, production_service, mock_repository
    ):
        """Test simulation when blueprint not found"""
        mock_repository.get_item_name.return_value = "Test Product"
        mock_repository.get_blueprint_for_product.return_value = None

        with pytest.raises(NotFoundError) as exc_info:
            production_service.simulate_build(
                type_id=648, runs=1, me=0, te=0,
                character_assets=None, region_id=None
            )

        assert "blueprint" in str(exc_info.value).lower()


class TestQuickProfitCheck:
    """Test quick profit checking"""

    def test_quick_profit_check_profitable(
        self, production_service, mock_repository, mock_market_service
    ):
        """Test quick profit check for profitable item"""
        mock_repository.get_blueprint_for_product.return_value = 1000
        mock_repository.get_blueprint_materials.return_value = [(34, 100)]
        mock_repository.get_item_name.side_effect = lambda tid: {
            34: "Tritanium",
            648: "Hornet"
        }.get(tid, "Unknown")
        mock_repository.get_output_quantity.return_value = 1

        mock_market_service.get_cached_prices_bulk.return_value = {
            34: 5.0,
            648: 1000.0
        }

        result = production_service.quick_profit_check(type_id=648, runs=1, me=10)

        assert isinstance(result, QuickProfitCheck)
        assert result.type_id == 648
        assert result.name == "Hornet"
        assert result.runs == 1
        assert result.me == 10
        assert result.material_cost > 0
        assert result.product_price > 0
        assert result.profit > 0
        assert result.margin_percent > 0

    def test_quick_profit_check_unprofitable(
        self, production_service, mock_repository, mock_market_service
    ):
        """Test quick profit check for unprofitable item"""
        mock_repository.get_blueprint_for_product.return_value = 1000
        mock_repository.get_blueprint_materials.return_value = [(34, 100)]
        mock_repository.get_item_name.return_value = "Test"
        mock_repository.get_output_quantity.return_value = 1

        # Expensive materials, cheap product
        mock_market_service.get_cached_prices_bulk.return_value = {
            34: 100.0,
            648: 1000.0
        }

        result = production_service.quick_profit_check(type_id=648, runs=1, me=10)

        assert result.profit < 0
        assert result.margin_percent < 0

    def test_quick_profit_check_no_blueprint(
        self, production_service, mock_repository
    ):
        """Test quick profit check when no blueprint found"""
        mock_repository.get_blueprint_for_product.return_value = None

        result = production_service.quick_profit_check(type_id=999999, runs=1, me=10)

        assert result is None

    def test_quick_profit_check_multiple_runs(
        self, production_service, mock_repository, mock_market_service
    ):
        """Test quick profit check with multiple runs"""
        mock_repository.get_blueprint_for_product.return_value = 1000
        mock_repository.get_blueprint_materials.return_value = [(34, 100)]
        mock_repository.get_item_name.return_value = "Test"
        mock_repository.get_output_quantity.return_value = 1

        mock_market_service.get_cached_prices_bulk.return_value = {
            34: 5.0,
            648: 1000.0
        }

        result = production_service.quick_profit_check(type_id=648, runs=10, me=10)

        # With ME 10: 100 * 0.9 = 90 per run, 90 * 10 = 900 total
        # Cost: 900 * 5 = 4500
        # Revenue: 1000 * 10 = 10000
        # Profit: 10000 - 4500 = 5500
        assert result.runs == 10
        assert result.output_quantity == 10
        assert result.profit > 0


class TestProductionTimeFormatting:
    """Test production time formatting"""

    def test_format_time_hours_and_minutes(self, production_service):
        """Test time formatting with hours and minutes"""
        # This is a helper method test
        formatted = production_service._format_time(7200)  # 2 hours
        assert "2h 0m" in formatted or "2h" in formatted

    def test_format_time_only_minutes(self, production_service):
        """Test time formatting with only minutes"""
        formatted = production_service._format_time(1800)  # 30 minutes
        assert "30m" in formatted or "0h 30m" in formatted

    def test_format_time_zero(self, production_service):
        """Test time formatting with zero"""
        formatted = production_service._format_time(0)
        assert "0" in formatted
