"""
EVE Co-Pilot Production Simulator Module
Simulates production runs with asset matching and financial calculations

Supports two pricing modes:
- 'cache': Uses pre-cached adjusted_prices from market_prices_cache (fast, for bulk operations)
- 'live': Fetches real-time prices from ESI (accurate, for individual queries)
"""

import math
from typing import Dict, List, Tuple, Optional, Literal
from src.database import get_db_connection, get_item_info, get_item_by_name
from src.esi_client import esi_client
from config import REGIONS

# Lazy import to avoid circular dependencies
_market_service = None

def get_market_service():
    """Lazy load market service"""
    global _market_service
    if _market_service is None:
        from src.market_service import market_service
        _market_service = market_service
    return _market_service


class ProductionSimulator:
    """Simulates EVE Online production with asset matching and profitability analysis"""

    def __init__(self, region_id: int = None, source: Literal['cache', 'live'] = 'cache'):
        """
        Initialize the production simulator

        Args:
            region_id: Region for market prices (default: The Forge/Jita)
            source: Pricing source - 'cache' for bulk ops, 'live' for accuracy
        """
        self.region_id = region_id or REGIONS["the_forge"]
        self.source = source

    def _get_price(self, type_id: int, region_id: int = None) -> float:
        """
        Get price based on current source mode.

        In 'cache' mode: Uses adjusted_price from market_prices_cache
        In 'live' mode: Fetches lowest sell from ESI
        """
        if self.source == 'cache':
            market_service = get_market_service()
            price = market_service.get_cached_price(type_id)
            return price if price else 0
        else:
            region_id = region_id or self.region_id
            return esi_client.get_lowest_sell_price(region_id, type_id) or 0

    def _get_prices_bulk(self, type_ids: List[int], region_id: int = None) -> Dict[int, float]:
        """
        Get multiple prices at once - optimized for bulk operations.

        In 'cache' mode: Single DB query for all prices
        In 'live' mode: Individual ESI calls (slower)
        """
        if self.source == 'cache':
            market_service = get_market_service()
            return market_service.get_cached_prices_bulk(type_ids)
        else:
            region_id = region_id or self.region_id
            return {
                tid: esi_client.get_lowest_sell_price(region_id, tid) or 0
                for tid in type_ids
            }

    def get_blueprint_for_product(self, product_type_id: int) -> Optional[int]:
        """Find the blueprint that produces a given item"""
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    SELECT "typeID" as blueprint_id
                    FROM "industryActivityProducts"
                    WHERE "productTypeID" = %s
                    AND "activityID" = 1
                    LIMIT 1
                ''', (product_type_id,))
                result = cur.fetchone()
                return result[0] if result else None

    def get_bom(self, type_id: int, runs: int = 1, me: int = 0) -> Dict[int, int]:
        """
        Get Bill of Materials for manufacturing

        Args:
            type_id: The typeID of the product to manufacture
            runs: Number of production runs
            me: Material Efficiency level (0-10)

        Returns:
            Dictionary {material_type_id: quantity_needed}
        """
        # Find the blueprint for this product
        blueprint_id = self.get_blueprint_for_product(type_id)
        if not blueprint_id:
            return {}

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Get base materials from industryActivityMaterials
                cur.execute('''
                    SELECT "materialTypeID", "quantity"
                    FROM "industryActivityMaterials"
                    WHERE "typeID" = %s
                    AND "activityID" = 1
                ''', (blueprint_id,))

                materials = cur.fetchall()

        bom = {}
        me_factor = 1 - (me / 100)  # ME 10 = 0.9 factor

        for material_id, base_quantity in materials:
            # Calculate quantity with ME bonus
            # EVE rounds up each material per run, then multiplies by runs
            quantity_per_run = max(1, math.ceil(base_quantity * me_factor))
            total_quantity = quantity_per_run * runs
            bom[material_id] = total_quantity

        return bom

    def get_bom_with_names(self, type_id: int, runs: int = 1, me: int = 0) -> List[Dict]:
        """
        Get Bill of Materials with item names

        Returns:
            List of dicts with material_id, material_name, quantity
        """
        bom = self.get_bom(type_id, runs, me)
        result = []

        for material_id, quantity in bom.items():
            item_info = get_item_info(material_id)
            result.append({
                "material_id": material_id,
                "material_name": item_info.get("typeName", "Unknown") if item_info else "Unknown",
                "quantity": quantity
            })

        # Sort by name
        result.sort(key=lambda x: x["material_name"])
        return result

    def match_assets(self, bom: Dict[int, int], character_assets: List[Dict]) -> Tuple[Dict[int, int], Dict[int, int]]:
        """
        Match BOM against character assets

        Args:
            bom: Dictionary {material_type_id: quantity_needed}
            character_assets: List of asset dicts from ESI

        Returns:
            Tuple of (available_materials, missing_materials)
            Each is {material_type_id: quantity}
        """
        # Build asset lookup {type_id: total_quantity}
        asset_totals = {}
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
                available[material_id] = needed
            elif have > 0:
                available[material_id] = have
                missing[material_id] = needed - have
            else:
                missing[material_id] = needed

        return available, missing

    def calculate_financials(
        self,
        type_id: int,
        runs: int,
        bom: Dict[int, int],
        missing: Dict[int, int],
        region_id: int = None
    ) -> Dict:
        """
        Calculate financial metrics for production

        Args:
            type_id: Product type ID
            runs: Number of runs
            bom: Full Bill of Materials
            missing: Missing materials to buy
            region_id: Region for market prices

        Returns:
            Dictionary with financial metrics
        """
        region_id = region_id or self.region_id

        # Get product output quantity
        output_quantity = runs  # Default 1 per run
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                blueprint_id = self.get_blueprint_for_product(type_id)
                if blueprint_id:
                    cur.execute('''
                        SELECT "quantity"
                        FROM "industryActivityProducts"
                        WHERE "typeID" = %s AND "productTypeID" = %s AND "activityID" = 1
                    ''', (blueprint_id, type_id))
                    result = cur.fetchone()
                    if result:
                        output_quantity = result[0] * runs

        # Get all prices at once (optimized for bulk operations)
        all_type_ids = list(bom.keys()) + [type_id]
        prices = self._get_prices_bulk(all_type_ids, region_id)

        # Calculate total build cost (all materials at market price)
        total_build_cost = 0
        material_costs = []

        for material_id, quantity in bom.items():
            price = prices.get(material_id, 0)
            cost = price * quantity
            total_build_cost += cost

            item_info = get_item_info(material_id)
            material_costs.append({
                "material_id": material_id,
                "material_name": item_info.get("typeName", "Unknown") if item_info else "Unknown",
                "quantity": quantity,
                "unit_price": price,
                "total_cost": cost
            })

        # Calculate cash to invest (only missing materials)
        cash_to_invest = 0
        shopping_list = []

        for material_id, quantity in missing.items():
            price = prices.get(material_id, 0)
            cost = price * quantity
            cash_to_invest += cost

            item_info = get_item_info(material_id)
            shopping_list.append({
                "material_id": material_id,
                "material_name": item_info.get("typeName", "Unknown") if item_info else "Unknown",
                "quantity": quantity,
                "unit_price": price,
                "total_cost": cost
            })

        # Get product sell price
        product_price = prices.get(type_id, 0)
        projected_revenue = product_price * output_quantity

        # Calculate profit metrics
        profit_vs_full_cost = projected_revenue - total_build_cost
        profit_vs_investment = projected_revenue - cash_to_invest

        margin_vs_full = (profit_vs_full_cost / total_build_cost * 100) if total_build_cost > 0 else 0
        margin_vs_investment = (profit_vs_investment / cash_to_invest * 100) if cash_to_invest > 0 else float('inf')

        return {
            "total_build_cost": round(total_build_cost, 2),
            "cash_to_invest": round(cash_to_invest, 2),
            "projected_revenue": round(projected_revenue, 2),
            "profit_vs_full_cost": round(profit_vs_full_cost, 2),
            "profit_vs_investment": round(profit_vs_investment, 2),
            "margin_percent": round(margin_vs_full, 2),
            "roi_percent": round(margin_vs_investment, 2),
            "output_quantity": output_quantity,
            "unit_sell_price": product_price,
            "material_costs": sorted(material_costs, key=lambda x: x["total_cost"], reverse=True),
            "shopping_list": sorted(shopping_list, key=lambda x: x["total_cost"], reverse=True)
        }

    def simulate_build(
        self,
        type_id: int,
        runs: int = 1,
        me: int = 0,
        te: int = 0,
        character_assets: List[Dict] = None,
        region_id: int = None,
        source: Literal['cache', 'live'] = None
    ) -> Dict:
        """
        Full production simulation

        Args:
            type_id: Product type ID
            runs: Number of production runs
            me: Material Efficiency (0-10)
            te: Time Efficiency (0-20)
            character_assets: List of character assets (optional)
            region_id: Region for market prices
            source: Override pricing source ('cache' or 'live')

        Returns:
            Complete simulation results
        """
        # Allow per-call source override
        if source:
            original_source = self.source
            self.source = source

        region_id = region_id or self.region_id

        # Get product info
        product_info = get_item_info(type_id)
        if not product_info:
            return {"error": f"Product type_id {type_id} not found"}

        # Get BOM
        bom = self.get_bom(type_id, runs, me)
        if not bom:
            return {"error": f"No blueprint found for {product_info.get('typeName', type_id)}"}

        # Get BOM with names
        bom_with_names = self.get_bom_with_names(type_id, runs, me)

        # Match against assets if provided
        if character_assets:
            available, missing = self.match_assets(bom, character_assets)
        else:
            available = {}
            missing = bom.copy()

        # Calculate financials
        financials = self.calculate_financials(type_id, runs, bom, missing, region_id)

        # Get base production time
        base_time = 0
        blueprint_id = self.get_blueprint_for_product(type_id)
        if blueprint_id:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute('''
                        SELECT "time"
                        FROM "industryActivity"
                        WHERE "typeID" = %s AND "activityID" = 1
                    ''', (blueprint_id,))
                    result = cur.fetchone()
                    if result:
                        base_time = result[0]

        # Calculate actual production time with TE
        te_factor = 1 - (te / 100)
        production_time = base_time * runs * te_factor
        hours = int(production_time // 3600)
        minutes = int((production_time % 3600) // 60)

        # Build result
        result = {
            "product": {
                "type_id": type_id,
                "name": product_info.get("typeName", "Unknown"),
                "output_quantity": financials["output_quantity"],
                "unit_sell_price": financials["unit_sell_price"]
            },
            "parameters": {
                "runs": runs,
                "me_level": me,
                "te_level": te,
                "region_id": region_id
            },
            "production_time": {
                "base_seconds": base_time * runs,
                "actual_seconds": int(production_time),
                "formatted": f"{hours}h {minutes}m"
            },
            "bill_of_materials": bom_with_names,
            "asset_match": {
                "materials_available": len(available),
                "materials_missing": len(missing),
                "fully_covered": len(missing) == 0
            },
            "financials": {
                "total_build_cost": financials["total_build_cost"],
                "cash_to_invest": financials["cash_to_invest"],
                "projected_revenue": financials["projected_revenue"],
                "profit": financials["profit_vs_full_cost"],
                "margin_percent": financials["margin_percent"],
                "roi_on_investment": financials["roi_percent"]
            },
            "shopping_list": financials["shopping_list"],
            "warnings": []
        }

        # Add warnings
        if financials["profit_vs_full_cost"] < 0:
            result["warnings"].append(
                f"LOSS WARNING: Building costs {abs(financials['profit_vs_full_cost']):,.2f} ISK more than selling. Consider selling materials instead."
            )

        if financials["margin_percent"] < 5:
            result["warnings"].append(
                f"LOW MARGIN: Only {financials['margin_percent']:.1f}% profit margin. Market fees may eat into profits."
            )

        # Restore original source if overridden
        if source:
            self.source = original_source

        return result

    def quick_profit_check(self, type_id: int, runs: int = 1, me: int = 10) -> Optional[Dict]:
        """
        Fast profit calculation for bulk scanning.

        Uses cache mode and returns minimal data for quick filtering.
        Returns None if no blueprint found.

        Args:
            type_id: Product type ID
            runs: Number of runs
            me: Material Efficiency (default 10 for T1)

        Returns:
            Dict with type_id, name, material_cost, product_price, profit, margin
        """
        bom = self.get_bom(type_id, runs, me)
        if not bom:
            return None

        # Get output quantity
        output_quantity = runs
        blueprint_id = self.get_blueprint_for_product(type_id)
        if blueprint_id:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute('''
                        SELECT "quantity"
                        FROM "industryActivityProducts"
                        WHERE "typeID" = %s AND "productTypeID" = %s AND "activityID" = 1
                    ''', (blueprint_id, type_id))
                    result = cur.fetchone()
                    if result:
                        output_quantity = result[0] * runs

        # Get all prices at once
        all_type_ids = list(bom.keys()) + [type_id]
        prices = self._get_prices_bulk(all_type_ids)

        # Calculate costs
        material_cost = sum(prices.get(mid, 0) * qty for mid, qty in bom.items())
        product_price = prices.get(type_id, 0)
        revenue = product_price * output_quantity
        profit = revenue - material_cost
        margin = (profit / material_cost * 100) if material_cost > 0 else 0

        product_info = get_item_info(type_id)

        return {
            "type_id": type_id,
            "name": product_info.get("typeName", "Unknown") if product_info else "Unknown",
            "runs": runs,
            "me": me,
            "output_quantity": output_quantity,
            "material_cost": round(material_cost, 2),
            "product_price": round(product_price, 2),
            "revenue": round(revenue, 2),
            "profit": round(profit, 2),
            "margin_percent": round(margin, 2)
        }


# Global simulator instance (uses cache by default)
production_simulator = ProductionSimulator(source='cache')

# Live simulator for accurate individual queries
production_simulator_live = ProductionSimulator(source='live')
