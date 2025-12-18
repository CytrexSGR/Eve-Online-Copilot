"""
Production Economics Service

Business logic for cost calculations, profitability analysis, and ROI.
"""

from typing import Dict, List, Any, Optional
from services.production.economics_repository import ProductionEconomicsRepository
from services.production.chain_repository import ProductionChainRepository
from database import get_db_connection


class ProductionEconomicsService:
    """Service for production economics operations"""

    def __init__(self):
        self.repo = ProductionEconomicsRepository()
        self.chain_repo = ProductionChainRepository()

    def get_economics(
        self,
        type_id: int,
        region_id: int,
        me: int = 0,
        te: int = 0
    ) -> Dict[str, Any]:
        """
        Get complete economics analysis for an item

        Args:
            type_id: Item type ID
            region_id: Region ID
            me: Material Efficiency (0-10)
            te: Time Efficiency (0-20)

        Returns:
            Complete economics data with adjusted costs
        """
        # Get base economics
        economics = self.repo.get(type_id, region_id)

        if not economics:
            return {'error': 'Economics data not found', 'type_id': type_id, 'region_id': region_id}

        # Get item info
        item_info = self._get_item_info(type_id)
        region_name = self._get_region_name(region_id)

        # Apply ME to material cost
        base_material_cost = economics['material_cost']
        adjusted_material_cost = base_material_cost * (1 - me / 100)

        # Apply TE to production time
        base_time = economics['base_production_time']
        adjusted_time = int(base_time * (1 - te / 100))

        total_cost = adjusted_material_cost + economics['base_job_cost']

        # Calculate profit and ROI
        profit_sell = None
        profit_buy = None
        roi_sell = None
        roi_buy = None

        if economics['market_sell_price']:
            profit_sell = economics['market_sell_price'] - total_cost
            roi_sell = (profit_sell / total_cost * 100) if total_cost > 0 else 0

        if economics['market_buy_price']:
            profit_buy = economics['market_buy_price'] - total_cost
            roi_buy = (profit_buy / total_cost * 100) if total_cost > 0 else 0

        return {
            'type_id': type_id,
            'item_name': item_info['name'] if item_info else 'Unknown',
            'region_id': region_id,
            'region_name': region_name,
            'me_level': me,
            'te_level': te,
            'costs': {
                'material_cost': adjusted_material_cost,
                'job_cost': economics['base_job_cost'],
                'total_cost': total_cost
            },
            'market': {
                'sell_price': economics['market_sell_price'],
                'buy_price': economics['market_buy_price'],
                'daily_volume': 0  # TODO: Add when available
            },
            'profitability': {
                'profit_sell': profit_sell,
                'profit_buy': profit_buy,
                'roi_sell_percent': roi_sell,
                'roi_buy_percent': roi_buy
            },
            'production_time': adjusted_time,
            'updated_at': economics['updated_at']
        }

    def find_opportunities(
        self,
        region_id: int,
        min_roi: float = 0,
        min_profit: float = 0,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Find profitable manufacturing opportunities

        Args:
            region_id: Region to search in
            min_roi: Minimum ROI percentage
            min_profit: Minimum profit in ISK
            limit: Max results

        Returns:
            List of opportunities
        """
        opportunities = self.repo.find_opportunities(
            region_id=region_id,
            min_roi=min_roi,
            min_profit=min_profit,
            limit=limit
        )

        return {
            'region_id': region_id,
            'region_name': self._get_region_name(region_id),
            'filters': {
                'min_roi': min_roi,
                'min_profit': min_profit
            },
            'opportunities': opportunities,
            'total_count': len(opportunities)
        }

    def compare_regions(self, type_id: int) -> Dict[str, Any]:
        """
        Compare production economics across multiple regions

        Args:
            type_id: Item type ID

        Returns:
            Multi-region comparison
        """
        # Get data for major regions
        regions = [
            (10000002, 'The Forge'),
            (10000043, 'Domain'),
            (10000030, 'Heimatar'),
            (10000032, 'Sinq Laison'),
            (10000042, 'Metropolis')
        ]

        item_info = self._get_item_info(type_id)
        results = []
        best_region = None
        best_roi = -999999

        for region_id, region_name in regions:
            economics = self.repo.get(type_id, region_id)

            if economics and economics['market_sell_price']:
                roi = economics['roi_sell_percent']
                profit = economics['profit_sell']

                results.append({
                    'region_id': region_id,
                    'region_name': region_name,
                    'roi_percent': roi,
                    'profit': profit,
                    'total_cost': economics['total_cost'],
                    'market_price': economics['market_sell_price']
                })

                if roi > best_roi:
                    best_roi = roi
                    best_region = {
                        'region_id': region_id,
                        'region_name': region_name,
                        'roi_percent': roi,
                        'profit': profit
                    }

        return {
            'type_id': type_id,
            'item_name': item_info['name'] if item_info else 'Unknown',
            'regions': sorted(results, key=lambda x: x['roi_percent'], reverse=True),
            'best_region': best_region,
            'total_regions': len(results)
        }

    def _get_item_info(self, type_id: int) -> Optional[Dict[str, Any]]:
        """Get item name and basic info"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT "typeID", "typeName"
                        FROM "invTypes"
                        WHERE "typeID" = %s
                    """, (type_id,))

                    row = cursor.fetchone()
                    if not row:
                        return None

                    return {'type_id': row[0], 'name': row[1]}
        except Exception as e:
            print(f"Error getting item info: {e}")
            return None

    def _get_region_name(self, region_id: int) -> str:
        """Get region name"""
        region_names = {
            10000002: 'The Forge',
            10000043: 'Domain',
            10000030: 'Heimatar',
            10000032: 'Sinq Laison',
            10000042: 'Metropolis'
        }
        return region_names.get(region_id, f'Region {region_id}')
