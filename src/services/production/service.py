"""
Production Service
Business logic layer for manufacturing simulation and cost calculations
"""

import math
from typing import Dict, List, Tuple, Optional

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
from src.services.production.repository import ProductionRepository
from src.services.market.service import MarketService
from src.core.exceptions import NotFoundError, EVECopilotError


class ProductionService:
    """
    Production Service provides business logic for manufacturing calculations.

    This service combines the Production Repository (for SDE blueprint data) with the
    Market Service (for pricing) to simulate production runs and calculate profitability.

    Responsibilities:
    - Calculate Bill of Materials (BOM) with Material Efficiency (ME) bonuses
    - Match BOM against character assets
    - Calculate production financials (cost, profit, ROI)
    - Simulate complete production runs with time and warnings
    - Provide quick profit checks for bulk scanning

    Pattern: Dependency Injection
    - No direct database access (delegates to repository)
    - No direct market access (delegates to market service)
    - Returns Pydantic models for type safety
    """

    def __init__(
        self,
        repository: ProductionRepository,
        market_service: MarketService,
        region_id: int = 10000002  # The Forge/Jita default
    ):
        """
        Initialize Production Service with dependencies.

        Args:
            repository: Production repository for blueprint queries
            market_service: Market service for price lookups
            region_id: Default region for market prices (The Forge/Jita)
        """
        self.repository = repository
        self.market_service = market_service
        self.region_id = region_id

    def get_bom(self, type_id: int, runs: int, me: int) -> Dict[int, int]:
        """
        Calculate Bill of Materials for manufacturing with ME bonus.

        The Material Efficiency (ME) bonus reduces material requirements:
        - ME 10 = 10% reduction (factor 0.9)
        - Formula: max(1, ceil(base_quantity * (1 - me/100)))
        - Applied per run, then multiplied by runs

        Args:
            type_id: Product type ID to manufacture
            runs: Number of production runs
            me: Material Efficiency level (0-10)

        Returns:
            Dictionary {material_type_id: total_quantity}

        Raises:
            NotFoundError: If blueprint not found for product
        """
        # Find blueprint for this product
        blueprint_id = self.repository.get_blueprint_for_product(type_id)
        if not blueprint_id:
            raise NotFoundError("blueprint", f"product {type_id}")

        # Get base materials
        materials = self.repository.get_blueprint_materials(blueprint_id)

        # Calculate quantities with ME bonus
        bom = {}
        me_factor = 1 - (me / 100)  # ME 10 = 0.9 factor

        for material_id, base_quantity in materials:
            # Calculate quantity with ME bonus (per run)
            # EVE rounds up each material per run, then multiplies by runs
            quantity_per_run = max(1, math.ceil(base_quantity * me_factor))
            total_quantity = quantity_per_run * runs
            bom[material_id] = total_quantity

        return bom

    def get_bom_with_names(
        self, type_id: int, runs: int, me: int
    ) -> List[MaterialItem]:
        """
        Get Bill of Materials with item names and costs.

        This method enhances the basic BOM with item names for display purposes.
        Note: This doesn't include prices - use calculate_financials for that.

        Args:
            type_id: Product type ID to manufacture
            runs: Number of production runs
            me: Material Efficiency level (0-10)

        Returns:
            List of MaterialItem objects sorted by name

        Raises:
            NotFoundError: If blueprint not found for product
        """
        bom = self.get_bom(type_id, runs, me)
        result = []

        for material_id, quantity in bom.items():
            name = self.repository.get_item_name(material_id) or "Unknown"

            # Create MaterialItem with zero prices (will be filled later if needed)
            result.append(MaterialItem(
                type_id=material_id,
                name=name,
                quantity=quantity,
                unit_price=0.0,
                total_cost=0.0
            ))

        # Sort by name for consistent display
        result.sort(key=lambda x: x.name)
        return result

    def match_assets(
        self, bom: Dict[int, int], character_assets: List[Dict]
    ) -> Tuple[Dict[int, int], Dict[int, int]]:
        """
        Match Bill of Materials against character assets.

        Compares required materials against available character assets to determine
        what materials are available and what needs to be purchased.

        Args:
            bom: Bill of materials as {material_type_id: quantity_needed}
            character_assets: List of asset dicts from ESI with type_id and quantity

        Returns:
            Tuple of (available_materials, missing_materials)
            - available_materials: {material_type_id: quantity} for materials owned
            - missing_materials: {material_type_id: quantity} for materials to buy
        """
        # Build asset lookup by aggregating quantities
        asset_totals: Dict[int, int] = {}
        for asset in character_assets:
            type_id = asset.get("type_id")
            quantity = asset.get("quantity", 0)
            if type_id:
                asset_totals[type_id] = asset_totals.get(type_id, 0) + quantity

        available = {}
        missing = {}

        for material_id, needed in bom.items():
            have = asset_totals.get(material_id, 0)

            if have >= needed:
                # Fully available
                available[material_id] = needed
            elif have > 0:
                # Partially available
                available[material_id] = have
                missing[material_id] = needed - have
            else:
                # Not available at all
                missing[material_id] = needed

        return available, missing

    def calculate_financials(
        self,
        type_id: int,
        runs: int,
        bom: Dict[int, int],
        missing: Dict[int, int]
    ) -> ProductionFinancials:
        """
        Calculate financial metrics for production.

        Calculates all costs, revenue, profit, margin, and ROI based on current
        market prices from the market service.

        Financial calculations:
        - build_cost: Total cost of all materials at market price
        - cash_to_invest: Cost of missing materials only
        - revenue: Product sell price * output quantity
        - profit: revenue - build_cost
        - margin: (profit / build_cost) * 100
        - roi: (profit / cash_to_invest) * 100 (infinite if no investment needed)

        Args:
            type_id: Product type ID
            runs: Number of production runs
            bom: Full Bill of Materials {material_type_id: quantity}
            missing: Missing materials {material_type_id: quantity}

        Returns:
            ProductionFinancials: Complete financial metrics

        Raises:
            EVECopilotError: If price lookup fails
        """
        # Get blueprint info for output quantity
        blueprint_id = self.repository.get_blueprint_for_product(type_id)
        output_per_run = 1
        if blueprint_id:
            output_per_run = self.repository.get_output_quantity(blueprint_id, type_id)
        output_quantity = output_per_run * runs

        # Get all prices in one bulk operation
        all_type_ids = list(bom.keys()) + [type_id]
        prices = self.market_service.get_cached_prices_bulk(all_type_ids)

        # Calculate total build cost (all materials at market price)
        build_cost = sum(
            prices.get(material_id, 0.0) * quantity
            for material_id, quantity in bom.items()
        )

        # Calculate cash to invest (only missing materials)
        cash_to_invest = sum(
            prices.get(material_id, 0.0) * quantity
            for material_id, quantity in missing.items()
        )

        # Calculate revenue
        product_price = prices.get(type_id, 0.0)
        revenue = product_price * output_quantity

        # Calculate profit metrics
        profit = revenue - build_cost
        margin = (profit / build_cost * 100) if build_cost > 0 else 0.0

        # ROI calculation - handle zero investment case
        if cash_to_invest > 0:
            roi = (profit / cash_to_invest * 100)
        elif profit > 0:
            roi = float('inf')  # Infinite ROI when no investment needed but making profit
        else:
            roi = 0.0

        return ProductionFinancials(
            build_cost=round(build_cost, 2),
            cash_to_invest=round(cash_to_invest, 2),
            revenue=round(revenue, 2),
            profit=round(profit, 2),
            margin=round(margin, 2),
            roi=round(roi, 2) if not math.isinf(roi) else roi
        )

    def _format_time(self, seconds: int) -> str:
        """
        Format production time in human-readable format.

        Args:
            seconds: Time in seconds

        Returns:
            Formatted string like "2h 30m"
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"

    def simulate_build(
        self,
        type_id: int,
        runs: int,
        me: int,
        te: int,
        character_assets: Optional[List[Dict]],
        region_id: Optional[int]
    ) -> ProductionSimulation:
        """
        Full production simulation with all metrics and warnings.

        This is the main orchestration method that combines all aspects of production
        simulation: BOM calculation, asset matching, financial analysis, time calculation,
        and warning generation.

        Args:
            type_id: Product type ID to manufacture
            runs: Number of production runs
            me: Material Efficiency level (0-10)
            te: Time Efficiency level (0-20)
            character_assets: Optional list of character assets from ESI
            region_id: Optional region override (uses default if None)

        Returns:
            ProductionSimulation: Complete simulation result

        Raises:
            NotFoundError: If product or blueprint not found
            EVECopilotError: If calculation fails
        """
        # Use provided region or default
        actual_region = region_id or self.region_id

        # Get product info
        product_name = self.repository.get_item_name(type_id)
        if not product_name:
            raise NotFoundError("product", type_id)

        # Get BOM
        bom = self.get_bom(type_id, runs, me)
        if not bom:
            raise NotFoundError("blueprint", f"product {type_id}")

        # Get BOM with names for display
        bom_items = self.get_bom_with_names(type_id, runs, me)

        # Match against assets if provided
        if character_assets:
            available, missing = self.match_assets(bom, character_assets)
        else:
            available = {}
            missing = bom.copy()

        # Calculate financials
        financials = self.calculate_financials(type_id, runs, bom, missing)

        # Get production time with TE bonus
        blueprint_id = self.repository.get_blueprint_for_product(type_id)
        base_time_per_run = 0
        if blueprint_id:
            base_time_per_run = self.repository.get_base_production_time(blueprint_id)

        base_time_total = base_time_per_run * runs
        te_factor = 1 - (te / 100)  # TE 20 = 0.8 factor
        actual_time = int(base_time_total * te_factor)

        production_time = ProductionTime(
            base_seconds=base_time_total,
            actual_seconds=actual_time,
            formatted=self._format_time(actual_time)
        )

        # Get output quantity for product info
        output_per_run = 1
        if blueprint_id:
            output_per_run = self.repository.get_output_quantity(blueprint_id, type_id)
        output_quantity = output_per_run * runs

        # Get product price
        prices = self.market_service.get_cached_prices_bulk([type_id])
        product_price = prices.get(type_id, 0.0)

        # Build product info
        product = ProductionProduct(
            type_id=type_id,
            name=product_name,
            output_quantity=output_quantity,
            unit_sell_price=product_price
        )

        # Build parameters
        parameters = ProductionParameters(
            runs=runs,
            me_level=me,
            te_level=te,
            region_id=actual_region
        )

        # Build asset match summary
        asset_match = AssetMatch(
            materials_available=len(available),
            materials_missing=len(missing),
            fully_covered=(len(missing) == 0)
        )

        # Build shopping list with prices
        shopping_list = []
        if missing:
            missing_prices = self.market_service.get_cached_prices_bulk(list(missing.keys()))
            for material_id, quantity in missing.items():
                name = self.repository.get_item_name(material_id) or "Unknown"
                price = missing_prices.get(material_id, 0.0)
                shopping_list.append(MaterialItem(
                    type_id=material_id,
                    name=name,
                    quantity=quantity,
                    unit_price=price,
                    total_cost=price * quantity
                ))
            # Sort by total cost descending
            shopping_list.sort(key=lambda x: x.total_cost, reverse=True)

        # Generate warnings
        warnings = []
        if financials.profit < 0:
            warnings.append(
                f"LOSS WARNING: Building costs {abs(financials.profit):,.2f} ISK "
                f"more than selling. Consider selling materials instead."
            )
        if financials.margin < 5 and financials.profit >= 0:
            warnings.append(
                f"LOW MARGIN: Only {financials.margin:.1f}% profit margin. "
                f"Market fees may eat into profits."
            )

        # Build BOM for result
        bom_result = BillOfMaterials(materials=bom_items)

        return ProductionSimulation(
            product=product,
            parameters=parameters,
            production_time=production_time,
            bill_of_materials=bom_result,
            asset_match=asset_match,
            financials=financials,
            shopping_list=shopping_list,
            warnings=warnings
        )

    def quick_profit_check(
        self, type_id: int, runs: int, me: int
    ) -> Optional[QuickProfitCheck]:
        """
        Fast profit calculation for bulk scanning.

        This is an optimized version of simulate_build that returns only essential
        profitability metrics. Ideal for scanning many items to find opportunities.

        Args:
            type_id: Product type ID
            runs: Number of production runs
            me: Material Efficiency level (0-10)

        Returns:
            QuickProfitCheck or None if no blueprint found
        """
        # Get BOM
        blueprint_id = self.repository.get_blueprint_for_product(type_id)
        if not blueprint_id:
            return None

        bom = self.get_bom(type_id, runs, me)
        if not bom:
            return None

        # Get output quantity
        output_per_run = self.repository.get_output_quantity(blueprint_id, type_id)
        output_quantity = output_per_run * runs

        # Get all prices at once
        all_type_ids = list(bom.keys()) + [type_id]
        prices = self.market_service.get_cached_prices_bulk(all_type_ids)

        # Calculate costs
        material_cost = sum(
            prices.get(material_id, 0.0) * quantity
            for material_id, quantity in bom.items()
        )
        product_price = prices.get(type_id, 0.0)
        revenue = product_price * output_quantity
        profit = revenue - material_cost
        margin = (profit / material_cost * 100) if material_cost > 0 else 0.0

        # Get product name
        name = self.repository.get_item_name(type_id) or "Unknown"

        return QuickProfitCheck(
            type_id=type_id,
            name=name,
            runs=runs,
            me=me,
            output_quantity=output_quantity,
            material_cost=round(material_cost, 2),
            product_price=round(product_price, 2),
            revenue=round(revenue, 2),
            profit=round(profit, 2),
            margin_percent=round(margin, 2)
        )
