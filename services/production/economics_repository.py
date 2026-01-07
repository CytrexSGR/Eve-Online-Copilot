"""
Production Economics Repository

Handles database operations for production economics data.
Manages cost calculations, market prices, and profitability metrics.
"""

from typing import List, Dict, Any, Optional
from src.database import get_db_connection


class ProductionEconomicsRepository:
    """Repository for production economics data access"""

    def upsert(
        self,
        type_id: int,
        region_id: int,
        material_cost: float,
        base_job_cost: float,
        market_sell_price: Optional[float],
        market_buy_price: Optional[float],
        base_production_time: int,
        market_volume_daily: int = 0
    ) -> int:
        """
        Insert or update production economics data

        Args:
            type_id: Item type
            region_id: Region ID
            material_cost: Total material cost at ME 0
            base_job_cost: Average job cost for region
            market_sell_price: Lowest sell order price
            market_buy_price: Highest buy order price
            base_production_time: Production time in seconds
            market_volume_daily: Daily trading volume

        Returns:
            ID of created/updated record
        """
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO production_economics
                        (type_id, region_id, material_cost, base_job_cost,
                         market_sell_price, market_buy_price, base_production_time,
                         market_volume_daily, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                        ON CONFLICT (type_id, region_id)
                        DO UPDATE SET
                            material_cost = EXCLUDED.material_cost,
                            base_job_cost = EXCLUDED.base_job_cost,
                            market_sell_price = EXCLUDED.market_sell_price,
                            market_buy_price = EXCLUDED.market_buy_price,
                            base_production_time = EXCLUDED.base_production_time,
                            market_volume_daily = EXCLUDED.market_volume_daily,
                            updated_at = NOW()
                        RETURNING id
                    """, (type_id, region_id, material_cost, base_job_cost,
                          market_sell_price, market_buy_price, base_production_time,
                          market_volume_daily))

                    result = cursor.fetchone()
                    conn.commit()
                    return result[0] if result else None
        except Exception as e:
            print(f"Error upserting economics: {e}")
            return None

    def get(self, type_id: int, region_id: int) -> Optional[Dict[str, Any]]:
        """Get production economics for item in region"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT
                            type_id,
                            region_id,
                            material_cost,
                            base_job_cost,
                            total_cost,
                            market_sell_price,
                            market_buy_price,
                            profit_sell,
                            profit_buy,
                            roi_sell_percent,
                            roi_buy_percent,
                            base_production_time,
                            updated_at
                        FROM production_economics_calculated
                        WHERE type_id = %s AND region_id = %s
                    """, (type_id, region_id))

                    row = cursor.fetchone()
                    if not row:
                        return None

                    return {
                        'type_id': row[0],
                        'region_id': row[1],
                        'material_cost': float(row[2]) if row[2] else 0,
                        'base_job_cost': float(row[3]) if row[3] else 0,
                        'total_cost': float(row[4]) if row[4] else 0,
                        'market_sell_price': float(row[5]) if row[5] else None,
                        'market_buy_price': float(row[6]) if row[6] else None,
                        'profit_sell': float(row[7]) if row[7] else None,
                        'profit_buy': float(row[8]) if row[8] else None,
                        'roi_sell_percent': float(row[9]) if row[9] else 0,
                        'roi_buy_percent': float(row[10]) if row[10] else 0,
                        'base_production_time': row[11],
                        'updated_at': row[12]
                    }
        except Exception as e:
            print(f"Error getting economics: {e}")
            return None

    def find_opportunities(
        self,
        region_id: int,
        min_roi: float = 0,
        min_profit: float = 0,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Find profitable production opportunities

        Args:
            region_id: Region to search in
            min_roi: Minimum ROI percentage
            min_profit: Minimum profit in ISK
            limit: Max results to return

        Returns:
            List of profitable items sorted by ROI
        """
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT
                            pec.type_id,
                            t."typeName",
                            pec.roi_sell_percent,
                            pec.profit_sell,
                            pec.total_cost,
                            pec.market_sell_price,
                            pec.base_production_time
                        FROM production_economics_calculated pec
                        JOIN "invTypes" t ON pec.type_id = t."typeID"
                        WHERE pec.region_id = %s
                        AND pec.roi_sell_percent >= %s
                        AND pec.profit_sell >= %s
                        AND pec.market_sell_price IS NOT NULL
                        ORDER BY pec.roi_sell_percent DESC
                        LIMIT %s
                    """, (region_id, min_roi, min_profit, limit))

                    rows = cursor.fetchall()
                    return [
                        {
                            'type_id': row[0],
                            'name': row[1],
                            'roi_percent': float(row[2]),
                            'profit': float(row[3]),
                            'total_cost': float(row[4]),
                            'market_price': float(row[5]),
                            'production_time': row[6]
                        }
                        for row in rows
                    ]
        except Exception as e:
            print(f"Error finding opportunities: {e}")
            return []
