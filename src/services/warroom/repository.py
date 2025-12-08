"""War Room repository - data access layer for sovereignty and faction warfare."""

from typing import Dict, List, Optional, Any
from datetime import datetime
from psycopg2.extras import RealDictCursor, execute_values

from src.core.database import DatabasePool
from src.core.exceptions import RepositoryError
from src.services.warroom.models import SovCampaign, FWSystemStatus


class WarRoomRepository:
    """Data access for War Room sovereignty and faction warfare data."""

    def __init__(self, db: DatabasePool):
        """Initialize repository with database pool."""
        self.db = db

    # ==================== Sovereignty Methods ====================

    def store_campaigns(self, campaigns: List[SovCampaign]) -> int:
        """
        Bulk upsert sovereignty campaigns.

        Args:
            campaigns: List of sovereignty campaigns to store

        Returns:
            Number of campaigns stored

        Raises:
            RepositoryError: If database operation fails
        """
        if not campaigns:
            return 0

        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cur:
                    stored_count = 0

                    for campaign in campaigns:
                        cur.execute(
                            """
                            INSERT INTO sovereignty_campaigns (
                                campaign_id, system_id, constellation_id,
                                structure_type_id, event_type, start_time,
                                defender_id, defender_score, attackers_score,
                                structure_id, last_updated
                            ) VALUES (
                                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()
                            )
                            ON CONFLICT (campaign_id) DO UPDATE SET
                                system_id = EXCLUDED.system_id,
                                constellation_id = EXCLUDED.constellation_id,
                                structure_type_id = EXCLUDED.structure_type_id,
                                event_type = EXCLUDED.event_type,
                                start_time = EXCLUDED.start_time,
                                defender_id = EXCLUDED.defender_id,
                                defender_score = EXCLUDED.defender_score,
                                attackers_score = EXCLUDED.attackers_score,
                                structure_id = EXCLUDED.structure_id,
                                last_updated = NOW()
                            """,
                            (
                                campaign.campaign_id,
                                campaign.system_id,
                                campaign.constellation_id,
                                campaign.structure_type_id,
                                campaign.event_type,
                                campaign.start_time,
                                campaign.defender_id,
                                campaign.defender_score,
                                campaign.attackers_score,
                                campaign.structure_id,
                            )
                        )
                        stored_count += 1

                    conn.commit()
                    return stored_count

        except Exception as e:
            raise RepositoryError(f"Failed to store campaigns: {str(e)}") from e

    def get_campaigns(self, region_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get sovereignty campaigns, optionally filtered by region.

        Args:
            region_id: Optional region ID to filter by

        Returns:
            List of campaign dictionaries

        Raises:
            RepositoryError: If database operation fails
        """
        try:
            with self.db.connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    if region_id is not None:
                        # Filter by region using system_region_map
                        cur.execute(
                            """
                            SELECT
                                sc.campaign_id, sc.system_id, sc.constellation_id,
                                sc.structure_type_id, sc.event_type, sc.start_time,
                                sc.defender_id, sc.defender_score, sc.attackers_score,
                                sc.structure_id
                            FROM sovereignty_campaigns sc
                            JOIN system_region_map srm ON sc.system_id = srm.solar_system_id
                            WHERE srm.region_id = %s
                            ORDER BY sc.start_time ASC
                            """,
                            (region_id,)
                        )
                    else:
                        # Get all campaigns
                        cur.execute(
                            """
                            SELECT
                                campaign_id, system_id, constellation_id,
                                structure_type_id, event_type, start_time,
                                defender_id, defender_score, attackers_score,
                                structure_id
                            FROM sovereignty_campaigns
                            ORDER BY start_time ASC
                            """
                        )

                    results = cur.fetchall()
                    return [dict(row) for row in results]

        except Exception as e:
            raise RepositoryError(f"Failed to get campaigns: {str(e)}") from e

    def cleanup_old_campaigns(self, cutoff_date: datetime) -> int:
        """
        Delete campaigns older than cutoff date.

        Args:
            cutoff_date: Delete campaigns with start_time before this date

        Returns:
            Number of campaigns deleted

        Raises:
            RepositoryError: If database operation fails
        """
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        DELETE FROM sovereignty_campaigns
                        WHERE start_time < %s
                        """,
                        (cutoff_date,)
                    )
                    deleted_count = cur.rowcount
                    conn.commit()
                    return deleted_count

        except Exception as e:
            raise RepositoryError(f"Failed to cleanup old campaigns: {str(e)}") from e

    # ==================== Faction Warfare Methods ====================

    def store_fw_systems(self, systems: List[FWSystemStatus]) -> int:
        """
        Bulk upsert faction warfare system status.

        Args:
            systems: List of FW system status to store

        Returns:
            Number of systems stored

        Raises:
            RepositoryError: If database operation fails
        """
        if not systems:
            return 0

        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cur:
                    # Prepare values for bulk insert
                    values = [
                        (
                            system.system_id,
                            system.owning_faction_id,
                            system.occupying_faction_id,
                            system.contested,
                            system.victory_points,
                            system.victory_points_threshold,
                            datetime.now(),
                        )
                        for system in systems
                    ]

                    # Use execute_values for efficient bulk insert
                    execute_values(
                        cur,
                        """
                        INSERT INTO fw_system_status (
                            system_id, owning_faction_id, occupying_faction_id,
                            contested, victory_points, victory_points_threshold,
                            last_updated
                        ) VALUES %s
                        ON CONFLICT (system_id) DO UPDATE SET
                            owning_faction_id = EXCLUDED.owning_faction_id,
                            occupying_faction_id = EXCLUDED.occupying_faction_id,
                            contested = EXCLUDED.contested,
                            victory_points = EXCLUDED.victory_points,
                            victory_points_threshold = EXCLUDED.victory_points_threshold,
                            last_updated = EXCLUDED.last_updated
                        """,
                        values,
                        page_size=1000
                    )

                    conn.commit()
                    return len(systems)

        except Exception as e:
            raise RepositoryError(f"Failed to store FW systems: {str(e)}") from e

    def get_fw_systems(self, contested_only: bool = False) -> List[Dict[str, Any]]:
        """
        Get faction warfare systems.

        Args:
            contested_only: If True, only return contested systems

        Returns:
            List of FW system dictionaries

        Raises:
            RepositoryError: If database operation fails
        """
        try:
            with self.db.connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    if contested_only:
                        cur.execute(
                            """
                            SELECT
                                system_id, owning_faction_id, occupying_faction_id,
                                contested, victory_points, victory_points_threshold,
                                last_updated
                            FROM fw_system_status
                            WHERE contested != 'uncontested'
                            ORDER BY victory_points DESC
                            """
                        )
                    else:
                        cur.execute(
                            """
                            SELECT
                                system_id, owning_faction_id, occupying_faction_id,
                                contested, victory_points, victory_points_threshold,
                                last_updated
                            FROM fw_system_status
                            ORDER BY system_id ASC
                            """
                        )

                    results = cur.fetchall()
                    return [dict(row) for row in results]

        except Exception as e:
            raise RepositoryError(f"Failed to get FW systems: {str(e)}") from e

    def get_fw_hotspots(self, min_progress: float = 50.0) -> List[Dict[str, Any]]:
        """
        Get contested FW systems (hotspots) above progress threshold.

        Args:
            min_progress: Minimum contest progress percentage (0-100)

        Returns:
            List of hotspot dictionaries with system details

        Raises:
            RepositoryError: If database operation fails
        """
        try:
            with self.db.connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        """
                        SELECT
                            fws.system_id,
                            srm.solar_system_name as system_name,
                            fws.owning_faction_id,
                            fws.occupying_faction_id,
                            fws.contested,
                            fws.victory_points,
                            fws.victory_points_threshold,
                            ROUND(
                                (fws.victory_points::numeric / fws.victory_points_threshold * 100),
                                2
                            ) as progress_percent,
                            fws.last_updated
                        FROM fw_system_status fws
                        LEFT JOIN system_region_map srm ON fws.system_id = srm.solar_system_id
                        WHERE (fws.victory_points::numeric / fws.victory_points_threshold * 100) >= %s
                        ORDER BY progress_percent DESC
                        """,
                        (min_progress,)
                    )

                    results = cur.fetchall()
                    return [dict(row) for row in results]

        except Exception as e:
            raise RepositoryError(f"Failed to get FW hotspots: {str(e)}") from e
