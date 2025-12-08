"""
Cargo Repository

Data access layer for cargo-related database operations
"""

from typing import Optional
from psycopg2.extras import RealDictCursor

from src.core.database import DatabasePool
from src.core.exceptions import EVECopilotError


class CargoRepository:
    """
    Repository for cargo-related database operations
    """

    def __init__(self, db: DatabasePool):
        """
        Initialize repository with database pool

        Args:
            db: DatabasePool instance for database connections
        """
        self.db = db

    def get_item_volume(self, type_id: int) -> Optional[float]:
        """
        Get the volume of an item from the invTypes table

        Args:
            type_id: EVE item type ID

        Returns:
            Volume in m³ if found, None otherwise

        Raises:
            EVECopilotError: If database operation fails
        """
        try:
            with self.db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        'SELECT "volume" FROM "invTypes" WHERE "typeID" = %s',
                        (type_id,)
                    )
                    result = cur.fetchone()

                    if result is None:
                        return None

                    volume = result['volume']
                    if volume is None:
                        return None

                    return float(volume)

        except Exception as e:
            raise EVECopilotError(
                f"Failed to get item volume for type_id {type_id}: {str(e)}"
            ) from e
