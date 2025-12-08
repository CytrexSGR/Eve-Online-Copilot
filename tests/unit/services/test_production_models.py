"""
Tests for Production Models
Following TDD - tests written first, then implementation
"""

import pytest
from pydantic import ValidationError
from src.services.production.models import (
    MaterialItem,
    BillOfMaterials,
    AssetMatch,
    ProductionTime,
    ProductionFinancials,
    ProductionParameters,
    ProductionProduct,
    ProductionSimulation,
    QuickProfitCheck,
)


class TestMaterialItem:
    """Test MaterialItem model"""

    def test_create_material_item_valid(self):
        """Test creating a valid MaterialItem"""
        material = MaterialItem(
            type_id=34,
            name="Tritanium",
            quantity=1000,
            unit_price=5.50,
            total_cost=5500.0
        )
        assert material.type_id == 34
        assert material.name == "Tritanium"
        assert material.quantity == 1000
        assert material.unit_price == 5.50
        assert material.total_cost == 5500.0

    def test_material_item_type_id_positive(self):
        """Test that type_id must be positive"""
        with pytest.raises(ValidationError) as exc_info:
            MaterialItem(
                type_id=0,
                name="Test",
                quantity=100,
                unit_price=10.0,
                total_cost=1000.0
            )
        assert "type_id" in str(exc_info.value)

    def test_material_item_quantity_positive(self):
        """Test that quantity must be positive"""
        with pytest.raises(ValidationError) as exc_info:
            MaterialItem(
                type_id=34,
                name="Tritanium",
                quantity=0,
                unit_price=5.0,
                total_cost=0.0
            )
        assert "quantity" in str(exc_info.value)

    def test_material_item_unit_price_non_negative(self):
        """Test that unit_price can be zero or positive"""
        material = MaterialItem(
            type_id=34,
            name="Tritanium",
            quantity=100,
            unit_price=0.0,
            total_cost=0.0
        )
        assert material.unit_price == 0.0

    def test_material_item_negative_unit_price_fails(self):
        """Test that negative unit_price fails"""
        with pytest.raises(ValidationError) as exc_info:
            MaterialItem(
                type_id=34,
                name="Tritanium",
                quantity=100,
                unit_price=-5.0,
                total_cost=-500.0
            )
        assert "unit_price" in str(exc_info.value)


class TestBillOfMaterials:
    """Test BillOfMaterials model"""

    def test_create_bom_valid(self):
        """Test creating a valid BOM"""
        materials = [
            MaterialItem(
                type_id=34,
                name="Tritanium",
                quantity=1000,
                unit_price=5.0,
                total_cost=5000.0
            ),
            MaterialItem(
                type_id=35,
                name="Pyerite",
                quantity=500,
                unit_price=10.0,
                total_cost=5000.0
            )
        ]
        bom = BillOfMaterials(materials=materials)
        assert len(bom.materials) == 2
        assert bom.materials[0].name == "Tritanium"

    def test_create_bom_empty(self):
        """Test creating a BOM with no materials"""
        bom = BillOfMaterials(materials=[])
        assert len(bom.materials) == 0


class TestAssetMatch:
    """Test AssetMatch model"""

    def test_asset_match_fully_covered(self):
        """Test asset match when all materials are available"""
        match = AssetMatch(
            materials_available=5,
            materials_missing=0,
            fully_covered=True
        )
        assert match.materials_available == 5
        assert match.materials_missing == 0
        assert match.fully_covered is True

    def test_asset_match_partial_coverage(self):
        """Test asset match with partial coverage"""
        match = AssetMatch(
            materials_available=3,
            materials_missing=2,
            fully_covered=False
        )
        assert match.materials_available == 3
        assert match.materials_missing == 2
        assert match.fully_covered is False

    def test_asset_match_non_negative_counts(self):
        """Test that material counts must be non-negative"""
        with pytest.raises(ValidationError) as exc_info:
            AssetMatch(
                materials_available=-1,
                materials_missing=0,
                fully_covered=False
            )
        assert "materials_available" in str(exc_info.value)


class TestProductionTime:
    """Test ProductionTime model"""

    def test_production_time_valid(self):
        """Test creating valid production time"""
        time = ProductionTime(
            base_seconds=3600,
            actual_seconds=3240,
            formatted="0h 54m"
        )
        assert time.base_seconds == 3600
        assert time.actual_seconds == 3240
        assert time.formatted == "0h 54m"

    def test_production_time_non_negative(self):
        """Test that time values must be non-negative"""
        with pytest.raises(ValidationError) as exc_info:
            ProductionTime(
                base_seconds=-100,
                actual_seconds=0,
                formatted="0h 0m"
            )
        assert "base_seconds" in str(exc_info.value)


class TestProductionFinancials:
    """Test ProductionFinancials model"""

    def test_financials_valid(self):
        """Test creating valid financials"""
        financials = ProductionFinancials(
            build_cost=1000000.0,
            cash_to_invest=500000.0,
            revenue=1200000.0,
            profit=200000.0,
            margin=20.0,
            roi=40.0
        )
        assert financials.build_cost == 1000000.0
        assert financials.cash_to_invest == 500000.0
        assert financials.revenue == 1200000.0
        assert financials.profit == 200000.0
        assert financials.margin == 20.0
        assert financials.roi == 40.0

    def test_financials_negative_values_allowed(self):
        """Test that negative profit/margin/roi are allowed (losses)"""
        financials = ProductionFinancials(
            build_cost=1000000.0,
            cash_to_invest=1000000.0,
            revenue=800000.0,
            profit=-200000.0,
            margin=-20.0,
            roi=-20.0
        )
        assert financials.profit == -200000.0
        assert financials.margin == -20.0

    def test_financials_non_negative_costs(self):
        """Test that costs must be non-negative"""
        with pytest.raises(ValidationError) as exc_info:
            ProductionFinancials(
                build_cost=-1000.0,
                cash_to_invest=0.0,
                revenue=0.0,
                profit=0.0,
                margin=0.0,
                roi=0.0
            )
        assert "build_cost" in str(exc_info.value)


class TestProductionParameters:
    """Test ProductionParameters model"""

    def test_parameters_valid(self):
        """Test creating valid parameters"""
        params = ProductionParameters(
            runs=10,
            me_level=10,
            te_level=20,
            region_id=10000002
        )
        assert params.runs == 10
        assert params.me_level == 10
        assert params.te_level == 20
        assert params.region_id == 10000002

    def test_parameters_runs_positive(self):
        """Test that runs must be positive"""
        with pytest.raises(ValidationError) as exc_info:
            ProductionParameters(
                runs=0,
                me_level=0,
                te_level=0,
                region_id=10000002
            )
        assert "runs" in str(exc_info.value)

    def test_parameters_me_range(self):
        """Test that ME must be 0-10"""
        with pytest.raises(ValidationError) as exc_info:
            ProductionParameters(
                runs=1,
                me_level=11,
                te_level=0,
                region_id=10000002
            )
        assert "me_level" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            ProductionParameters(
                runs=1,
                me_level=-1,
                te_level=0,
                region_id=10000002
            )
        assert "me_level" in str(exc_info.value)

    def test_parameters_te_range(self):
        """Test that TE must be 0-20"""
        with pytest.raises(ValidationError) as exc_info:
            ProductionParameters(
                runs=1,
                me_level=0,
                te_level=21,
                region_id=10000002
            )
        assert "te_level" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            ProductionParameters(
                runs=1,
                me_level=0,
                te_level=-1,
                region_id=10000002
            )
        assert "te_level" in str(exc_info.value)

    def test_parameters_region_id_positive(self):
        """Test that region_id must be positive"""
        with pytest.raises(ValidationError) as exc_info:
            ProductionParameters(
                runs=1,
                me_level=0,
                te_level=0,
                region_id=0
            )
        assert "region_id" in str(exc_info.value)


class TestProductionProduct:
    """Test ProductionProduct model"""

    def test_product_valid(self):
        """Test creating valid product"""
        product = ProductionProduct(
            type_id=648,
            name="Hornet I",
            output_quantity=100,
            unit_sell_price=50000.0
        )
        assert product.type_id == 648
        assert product.name == "Hornet I"
        assert product.output_quantity == 100
        assert product.unit_sell_price == 50000.0

    def test_product_type_id_positive(self):
        """Test that type_id must be positive"""
        with pytest.raises(ValidationError) as exc_info:
            ProductionProduct(
                type_id=0,
                name="Test",
                output_quantity=1,
                unit_sell_price=100.0
            )
        assert "type_id" in str(exc_info.value)

    def test_product_output_quantity_positive(self):
        """Test that output_quantity must be positive"""
        with pytest.raises(ValidationError) as exc_info:
            ProductionProduct(
                type_id=648,
                name="Hornet I",
                output_quantity=0,
                unit_sell_price=100.0
            )
        assert "output_quantity" in str(exc_info.value)


class TestProductionSimulation:
    """Test ProductionSimulation model"""

    def test_simulation_valid(self):
        """Test creating valid simulation result"""
        product = ProductionProduct(
            type_id=648,
            name="Hornet I",
            output_quantity=100,
            unit_sell_price=50000.0
        )
        parameters = ProductionParameters(
            runs=10,
            me_level=10,
            te_level=20,
            region_id=10000002
        )
        production_time = ProductionTime(
            base_seconds=3600,
            actual_seconds=2880,
            formatted="0h 48m"
        )
        bom = BillOfMaterials(materials=[])
        asset_match = AssetMatch(
            materials_available=0,
            materials_missing=0,
            fully_covered=True
        )
        financials = ProductionFinancials(
            build_cost=1000000.0,
            cash_to_invest=0.0,
            revenue=5000000.0,
            profit=4000000.0,
            margin=400.0,
            roi=0.0
        )

        simulation = ProductionSimulation(
            product=product,
            parameters=parameters,
            production_time=production_time,
            bill_of_materials=bom,
            asset_match=asset_match,
            financials=financials,
            shopping_list=[],
            warnings=[]
        )

        assert simulation.product.type_id == 648
        assert simulation.parameters.runs == 10
        assert simulation.production_time.base_seconds == 3600
        assert len(simulation.warnings) == 0

    def test_simulation_with_warnings(self):
        """Test simulation with warnings"""
        product = ProductionProduct(
            type_id=648,
            name="Hornet I",
            output_quantity=1,
            unit_sell_price=100.0
        )
        parameters = ProductionParameters(
            runs=1,
            me_level=0,
            te_level=0,
            region_id=10000002
        )
        production_time = ProductionTime(
            base_seconds=100,
            actual_seconds=100,
            formatted="0h 1m"
        )
        bom = BillOfMaterials(materials=[])
        asset_match = AssetMatch(
            materials_available=0,
            materials_missing=0,
            fully_covered=False
        )
        financials = ProductionFinancials(
            build_cost=200.0,
            cash_to_invest=200.0,
            revenue=100.0,
            profit=-100.0,
            margin=-50.0,
            roi=-50.0
        )

        simulation = ProductionSimulation(
            product=product,
            parameters=parameters,
            production_time=production_time,
            bill_of_materials=bom,
            asset_match=asset_match,
            financials=financials,
            shopping_list=[],
            warnings=["LOSS WARNING: Unprofitable production"]
        )

        assert len(simulation.warnings) == 1
        assert "LOSS WARNING" in simulation.warnings[0]


class TestQuickProfitCheck:
    """Test QuickProfitCheck model"""

    def test_quick_profit_check_valid(self):
        """Test creating valid quick profit check"""
        check = QuickProfitCheck(
            type_id=648,
            name="Hornet I",
            runs=10,
            me=10,
            output_quantity=100,
            material_cost=1000000.0,
            product_price=50000.0,
            revenue=5000000.0,
            profit=4000000.0,
            margin_percent=400.0
        )
        assert check.type_id == 648
        assert check.name == "Hornet I"
        assert check.runs == 10
        assert check.me == 10
        assert check.profit == 4000000.0

    def test_quick_profit_check_negative_profit(self):
        """Test quick profit check with negative profit (loss)"""
        check = QuickProfitCheck(
            type_id=648,
            name="Hornet I",
            runs=1,
            me=0,
            output_quantity=1,
            material_cost=1000.0,
            product_price=100.0,
            revenue=100.0,
            profit=-900.0,
            margin_percent=-90.0
        )
        assert check.profit == -900.0
        assert check.margin_percent == -90.0

    def test_quick_profit_check_type_id_positive(self):
        """Test that type_id must be positive"""
        with pytest.raises(ValidationError) as exc_info:
            QuickProfitCheck(
                type_id=0,
                name="Test",
                runs=1,
                me=0,
                output_quantity=1,
                material_cost=100.0,
                product_price=100.0,
                revenue=100.0,
                profit=0.0,
                margin_percent=0.0
            )
        assert "type_id" in str(exc_info.value)

    def test_quick_profit_check_me_range(self):
        """Test that ME must be 0-10"""
        with pytest.raises(ValidationError) as exc_info:
            QuickProfitCheck(
                type_id=648,
                name="Test",
                runs=1,
                me=11,
                output_quantity=1,
                material_cost=100.0,
                product_price=100.0,
                revenue=100.0,
                profit=0.0,
                margin_percent=0.0
            )
        assert "me" in str(exc_info.value)
