"""
Production Repository
Database access layer for production-related queries
"""

from typing import Optional, List, Tuple
from src.core.exceptions import EVECopilotError


class ProductionRepository:
    """Repository for production-related database queries"""

    def __init__(self, db):
        """
        Initialize repository with database pool

        Args:
            db: DatabasePool instance
        """
        self.db = db

    def get_blueprint_for_product(self, product_type_id: int) -> Optional[int]:
        """
        Find the blueprint that produces a given item

        Args:
            product_type_id: Type ID of the product

        Returns:
            Blueprint type ID or None if not found

        Raises:
            EVECopilotError: If database query fails
        """
        try:
            with self.db.get_connection() as conn:
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
        except Exception as e:
            raise EVECopilotError(f"Database error while fetching blueprint for product {product_type_id}: {e}")

    def get_blueprint_materials(self, blueprint_id: int) -> List[Tuple[int, int]]:
        """
        Get materials required for a blueprint

        Args:
            blueprint_id: Blueprint type ID

        Returns:
            List of tuples (material_type_id, base_quantity)

        Raises:
            EVECopilotError: If database query fails
        """
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute('''
                        SELECT "materialTypeID", "quantity"
                        FROM "industryActivityMaterials"
                        WHERE "typeID" = %s
                        AND "activityID" = 1
                    ''', (blueprint_id,))
                    return cur.fetchall()
        except Exception as e:
            raise EVECopilotError(f"Database error while fetching materials for blueprint {blueprint_id}: {e}")

    def get_output_quantity(self, blueprint_id: int, product_type_id: int) -> int:
        """
        Get output quantity per run for a blueprint

        Args:
            blueprint_id: Blueprint type ID
            product_type_id: Product type ID

        Returns:
            Output quantity per run (defaults to 1 if not found)

        Raises:
            EVECopilotError: If database query fails
        """
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute('''
                        SELECT "quantity"
                        FROM "industryActivityProducts"
                        WHERE "typeID" = %s
                        AND "productTypeID" = %s
                        AND "activityID" = 1
                    ''', (blueprint_id, product_type_id))
                    result = cur.fetchone()
                    return result[0] if result else 1
        except Exception as e:
            raise EVECopilotError(f"Database error while fetching output quantity for blueprint {blueprint_id}: {e}")

    def get_base_production_time(self, blueprint_id: int) -> int:
        """
        Get base production time for a blueprint

        Args:
            blueprint_id: Blueprint type ID

        Returns:
            Production time in seconds (defaults to 0 if not found)

        Raises:
            EVECopilotError: If database query fails
        """
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute('''
                        SELECT "time"
                        FROM "industryActivity"
                        WHERE "typeID" = %s
                        AND "activityID" = 1
                    ''', (blueprint_id,))
                    result = cur.fetchone()
                    return result[0] if result else 0
        except Exception as e:
            raise EVECopilotError(f"Database error while fetching production time for blueprint {blueprint_id}: {e}")

    def get_item_name(self, type_id: int) -> Optional[str]:
        """
        Get item name from SDE

        Args:
            type_id: Item type ID

        Returns:
            Item name or None if not found

        Raises:
            EVECopilotError: If database query fails
        """
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute('''
                        SELECT "typeName"
                        FROM "invTypes"
                        WHERE "typeID" = %s
                    ''', (type_id,))
                    result = cur.fetchone()
                    return result[0] if result else None
        except Exception as e:
            raise EVECopilotError(f"Database error while fetching item name for type {type_id}: {e}")
