"""Killmail Repository for database operations."""

from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from psycopg2.extras import RealDictCursor, execute_values

from src.core.database import DatabasePool
from src.services.killmail.models import ItemLoss, ShipLoss


class KillmailRepository:
    """Handles database operations for killmail data."""

    def __init__(self, db: DatabasePool):
        """Initialize repository with database pool."""
        self.db = db

    def store_ship_losses(self, losses: List[ShipLoss]) -> int:
        """
        Bulk insert ship losses into database.

        Args:
            losses: List of ShipLoss instances

        Returns:
            Number of records inserted
        """
        if not losses:
            return 0

        with self.db.get_connection() as conn:
            with conn.cursor() as cur:
                # Prepare values for bulk insert
                values = [
                    (
                        loss.system_id,
                        loss.region_id,
                        loss.ship_type_id,
                        loss.loss_count,
                        loss.date,
                        loss.total_value_destroyed
                    )
                    for loss in losses
                ]

                # Bulk insert with conflict resolution
                execute_values(
                    cur,
                    """
                    INSERT INTO combat_ship_losses
                        (solar_system_id, region_id, ship_type_id, quantity, date, total_value_destroyed)
                    VALUES %s
                    ON CONFLICT (date, solar_system_id, ship_type_id)
                    DO UPDATE SET
                        quantity = combat_ship_losses.quantity + EXCLUDED.quantity,
                        total_value_destroyed = combat_ship_losses.total_value_destroyed + EXCLUDED.total_value_destroyed
                    """,
                    values,
                    page_size=1000
                )

                conn.commit()

        return len(losses)

    def store_item_losses(self, losses: List[ItemLoss]) -> int:
        """
        Bulk insert item losses into database.

        Args:
            losses: List of ItemLoss instances

        Returns:
            Number of records inserted
        """
        if not losses:
            return 0

        with self.db.get_connection() as conn:
            with conn.cursor() as cur:
                # Prepare values for bulk insert
                values = [
                    (
                        loss.region_id,
                        loss.item_type_id,
                        loss.loss_count,
                        loss.date
                    )
                    for loss in losses
                ]

                # Bulk insert with conflict resolution
                execute_values(
                    cur,
                    """
                    INSERT INTO combat_item_losses
                        (region_id, item_type_id, quantity_destroyed, date)
                    VALUES %s
                    ON CONFLICT (date, region_id, item_type_id)
                    DO UPDATE SET
                        quantity_destroyed = combat_item_losses.quantity_destroyed + EXCLUDED.quantity_destroyed
                    """,
                    values,
                    page_size=1000
                )

                conn.commit()

        return len(losses)

    def get_ship_losses(
        self,
        region_id: Optional[int] = None,
        system_id: Optional[int] = None,
        days: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Get ship losses from database.

        Args:
            region_id: Filter by region (None = all regions)
            system_id: Filter by system (None = all systems)
            days: Number of days to look back

        Returns:
            List of ship loss records
        """
        cutoff_date = date.today() - timedelta(days=days)

        with self.db.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Build query based on filters
                query = """
                    SELECT
                        solar_system_id as system_id,
                        region_id,
                        ship_type_id,
                        quantity as loss_count,
                        date,
                        total_value_destroyed
                    FROM combat_ship_losses
                    WHERE date >= %s
                """
                params = [cutoff_date]

                if region_id is not None:
                    query += " AND region_id = %s"
                    params.append(region_id)

                if system_id is not None:
                    query += " AND solar_system_id = %s"
                    params.append(system_id)

                query += " ORDER BY date DESC, quantity DESC"

                cur.execute(query, params)
                return [dict(row) for row in cur.fetchall()]

    def get_item_losses(
        self,
        region_id: Optional[int] = None,
        days: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Get item losses from database.

        Args:
            region_id: Filter by region (None = all regions)
            days: Number of days to look back

        Returns:
            List of item loss records
        """
        cutoff_date = date.today() - timedelta(days=days)

        with self.db.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                query = """
                    SELECT
                        region_id,
                        item_type_id,
                        quantity_destroyed as loss_count,
                        date
                    FROM combat_item_losses
                    WHERE date >= %s
                """
                params = [cutoff_date]

                if region_id is not None:
                    query += " AND region_id = %s"
                    params.append(region_id)

                query += " ORDER BY date DESC, quantity_destroyed DESC"

                cur.execute(query, params)
                return [dict(row) for row in cur.fetchall()]

    def get_system_danger_score(self, system_id: int, days: int = 7) -> Dict[str, Any]:
        """
        Calculate danger score for a system based on kills.

        Args:
            system_id: Solar system ID
            days: Number of days to look back

        Returns:
            Dictionary with danger score information
        """
        cutoff_date = date.today() - timedelta(days=days)

        with self.db.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT SUM(quantity) as kill_count
                    FROM combat_ship_losses
                    WHERE solar_system_id = %s AND date >= %s
                    """,
                    (system_id, cutoff_date)
                )

                result = cur.fetchone()

                kill_count = result['kill_count'] if result and result['kill_count'] else 0

                return {
                    'system_id': system_id,
                    'kill_count': kill_count,
                    'days': days
                }

    def cleanup_old_data(self, days: int) -> int:
        """
        Delete data older than specified days.

        Args:
            days: Retention period in days

        Returns:
            Total number of records deleted
        """
        cutoff_date = date.today() - timedelta(days=days)

        with self.db.get_connection() as conn:
            with conn.cursor() as cur:
                # Delete old ship losses
                cur.execute(
                    "DELETE FROM combat_ship_losses WHERE date < %s",
                    (cutoff_date,)
                )
                ship_deleted = cur.rowcount

                # Delete old item losses
                cur.execute(
                    "DELETE FROM combat_item_losses WHERE date < %s",
                    (cutoff_date,)
                )
                item_deleted = cur.rowcount

                conn.commit()

        return ship_deleted + item_deleted

    def get_system_region_map(self) -> Dict[int, int]:
        """
        Load solar_system_id -> region_id mapping from database.

        Returns:
            Dictionary mapping system IDs to region IDs
        """
        with self.db.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT solar_system_id, region_id FROM system_region_map")
                return {row['solar_system_id']: row['region_id'] for row in cur.fetchall()}
