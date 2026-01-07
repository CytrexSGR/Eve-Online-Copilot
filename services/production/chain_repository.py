"""
Production Chain Repository

Handles database operations for production dependencies and chains.
Manages material dependency graphs from finished products to raw materials.
"""

from typing import List, Dict, Any, Optional
from src.database import get_db_connection


class ProductionChainRepository:
    """Repository for production chain data access"""

    def save_dependency(
        self,
        item_type_id: int,
        material_type_id: int,
        base_quantity: int,
        activity_id: int = 1,
        is_raw_material: bool = False
    ) -> int:
        """
        Save a direct material dependency

        Args:
            item_type_id: Item being produced
            material_type_id: Material required
            base_quantity: Quantity without ME
            activity_id: 1=Manufacturing, 3=Research, 8=Invention
            is_raw_material: True if material has no further dependencies

        Returns:
            ID of created dependency
        """
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO production_dependencies
                        (item_type_id, material_type_id, base_quantity, activity_id, is_raw_material)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT DO NOTHING
                        RETURNING id
                    """, (item_type_id, material_type_id, base_quantity, activity_id, is_raw_material))

                    result = cursor.fetchone()
                    conn.commit()
                    return result[0] if result else None
        except Exception as e:
            print(f"Error saving dependency: {e}")
            return None

    def get_direct_dependencies(self, item_type_id: int, activity_id: int = 1) -> List[Dict[str, Any]]:
        """
        Get direct material dependencies for an item

        Args:
            item_type_id: Item to get dependencies for
            activity_id: Activity type (1=Manufacturing)

        Returns:
            List of dependencies with material info
        """
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT
                            pd.id,
                            pd.material_type_id,
                            t."typeName" as material_name,
                            pd.base_quantity,
                            pd.is_raw_material
                        FROM production_dependencies pd
                        JOIN "invTypes" t ON pd.material_type_id = t."typeID"
                        WHERE pd.item_type_id = %s
                        AND pd.activity_id = %s
                    """, (item_type_id, activity_id))

                    rows = cursor.fetchall()
                    return [
                        {
                            'id': row[0],
                            'material_type_id': row[1],
                            'material_name': row[2],
                            'base_quantity': row[3],
                            'is_raw_material': row[4]
                        }
                        for row in rows
                    ]
        except Exception as e:
            print(f"Error getting dependencies: {e}")
            return []

    def save_chain(
        self,
        item_type_id: int,
        raw_material_type_id: int,
        base_quantity: float,
        chain_depth: int,
        path: str = None
    ) -> int:
        """
        Save a complete production chain to raw material

        Args:
            item_type_id: Final product
            raw_material_type_id: Raw material
            base_quantity: Total quantity without ME
            chain_depth: Number of production steps
            path: Production path for debugging

        Returns:
            ID of created chain
        """
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO production_chains
                        (item_type_id, raw_material_type_id, base_quantity, chain_depth, path)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (item_type_id, raw_material_type_id)
                        DO UPDATE SET
                            base_quantity = EXCLUDED.base_quantity,
                            chain_depth = EXCLUDED.chain_depth,
                            path = EXCLUDED.path
                        RETURNING id
                    """, (item_type_id, raw_material_type_id, base_quantity, chain_depth, path))

                    result = cursor.fetchone()
                    conn.commit()
                    return result[0] if result else None
        except Exception as e:
            print(f"Error saving chain: {e}")
            return None

    def get_full_chain(self, item_type_id: int) -> List[Dict[str, Any]]:
        """
        Get complete production chain to all raw materials

        Args:
            item_type_id: Item to get chain for

        Returns:
            List of raw materials with quantities
        """
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT
                            pc.raw_material_type_id,
                            t."typeName" as material_name,
                            pc.base_quantity,
                            pc.chain_depth,
                            pc.path
                        FROM production_chains pc
                        JOIN "invTypes" t ON pc.raw_material_type_id = t."typeID"
                        WHERE pc.item_type_id = %s
                        ORDER BY pc.chain_depth, t."typeName"
                    """, (item_type_id,))

                    rows = cursor.fetchall()
                    return [
                        {
                            'material_type_id': row[0],
                            'material_name': row[1],
                            'base_quantity': float(row[2]),
                            'chain_depth': row[3],
                            'path': row[4]
                        }
                        for row in rows
                    ]
        except Exception as e:
            print(f"Error getting chain: {e}")
            return []

    def chain_exists(self, item_type_id: int) -> bool:
        """Check if production chain exists for item"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT COUNT(*) FROM production_chains
                        WHERE item_type_id = %s
                    """, (item_type_id,))

                    count = cursor.fetchone()[0]
                    return count > 0
        except Exception as e:
            print(f"Error checking chain: {e}")
            return False

    def delete_chains(self, item_type_id: int) -> bool:
        """Delete all chains for an item (for rebuilding)"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        DELETE FROM production_chains WHERE item_type_id = %s
                    """, (item_type_id,))
                    conn.commit()
                    return True
        except Exception as e:
            print(f"Error deleting chains: {e}")
            return False

    def get_items_without_chains(self, limit: int = 100) -> List[int]:
        """Get items that have blueprints but no chains yet"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT DISTINCT iap."productTypeID"
                        FROM "industryActivityProducts" iap
                        WHERE iap."activityID" = 1  -- Manufacturing
                        AND NOT EXISTS (
                            SELECT 1 FROM production_chains pc
                            WHERE pc.item_type_id = iap."productTypeID"
                        )
                        LIMIT %s
                    """, (limit,))

                    rows = cursor.fetchall()
                    return [row[0] for row in rows]
        except Exception as e:
            print(f"Error getting items without chains: {e}")
            return []
