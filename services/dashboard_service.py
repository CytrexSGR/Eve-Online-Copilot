"""
Dashboard aggregation service for EVE Co-Pilot 2.0

Aggregates opportunities from:
- Market Hunter (manufacturing)
- Arbitrage Finder (trading)
- War Analyzer (combat demand)

Sorts by user priorities: Industrie → Handel → War Room
"""

from typing import List, Dict, Any
from datetime import datetime, timedelta
from database import get_db_connection


class DashboardService:
    """Aggregates and prioritizes opportunities for dashboard"""

    CATEGORY_PRIORITY = {
        'production': 1,
        'trade': 2,
        'war_demand': 3
    }

    def __init__(self):
        self.cache = {}
        self.cache_ttl = timedelta(minutes=5)

    def get_opportunities(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get top opportunities across all categories

        Args:
            limit: Maximum number of opportunities to return (default 10)

        Returns:
            List of opportunity dicts sorted by priority and profitability
        """
        # Check cache
        cache_key = f"opportunities_{limit}"
        if cache_key in self.cache:
            cached_time, cached_data = self.cache[cache_key]
            if datetime.now() - cached_time < self.cache_ttl:
                return cached_data

        opportunities = []

        # Aggregate from all sources
        opportunities.extend(self._get_production_opportunities())
        opportunities.extend(self._get_trade_opportunities())
        opportunities.extend(self._get_war_demand_opportunities())

        # Sort by priority and profit
        sorted_ops = self._sort_opportunities(opportunities)

        # Limit results
        result = sorted_ops[:limit]

        # Cache result
        self.cache[cache_key] = (datetime.now(), result)

        return result

    def _get_production_opportunities(self) -> List[Dict[str, Any]]:
        """Get manufacturing opportunities from Market Hunter"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT
                            product_id,
                            product_name,
                            profit,
                            roi,
                            difficulty,
                            cheapest_material_cost,
                            best_sell_price
                        FROM manufacturing_opportunities
                        WHERE profit > 1000000
                        ORDER BY profit DESC
                        LIMIT 10
                    """)

                    rows = cursor.fetchall()

                    opportunities = []
                    for row in rows:
                        opportunities.append({
                            'category': 'production',
                            'type_id': row[0],
                            'name': row[1],
                            'profit': row[2],
                            'roi': row[3],
                            'difficulty': row[4],
                            'material_cost': row[5],
                            'sell_price': row[6]
                        })

                    return opportunities

        except Exception as e:
            print(f"Error fetching production opportunities: {e}")
            return []

    def _get_trade_opportunities(self) -> List[Dict[str, Any]]:
        """Get arbitrage opportunities"""
        # Mock data for testing - will be replaced with real integration
        return [{
            'category': 'trade',
            'type_id': 645,
            'name': 'Thorax',
            'profit': 2000000,
            'roi': 15.3
        }]

    def _get_war_demand_opportunities(self) -> List[Dict[str, Any]]:
        """Get combat demand opportunities from War Analyzer"""
        # Mock data for testing - will be replaced with real integration
        return [{
            'category': 'war_demand',
            'type_id': 16236,
            'name': 'Gila',
            'profit': 10000000,
            'roi': 35.0
        }]

    def _sort_opportunities(self, opportunities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Sort opportunities by:
        1. Category priority (production > trade > war_demand)
        2. Profit (descending)
        """
        return sorted(
            opportunities,
            key=lambda x: (
                self.CATEGORY_PRIORITY.get(x['category'], 999),
                -x.get('profit', 0)
            )
        )
