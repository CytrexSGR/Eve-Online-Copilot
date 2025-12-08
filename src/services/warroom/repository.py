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

    # ==================== War Analyzer Methods ====================

    def get_demand_analysis(self, region_id: int, days: int) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get demand analysis data (ships and items lost with market stock).

        Args:
            region_id: Region ID to analyze
            days: Number of days to look back

        Returns:
            Dictionary with 'ships' and 'items' lists

        Raises:
            RepositoryError: If database operation fails
        """
        try:
            with self.db.connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Get top ships lost
                    cur.execute(
                        """
                        SELECT
                            csl.ship_type_id as type_id,
                            it."typeName" as name,
                            SUM(csl.quantity) as quantity,
                            COALESCE(mp.sell_volume, 0) as market_stock
                        FROM combat_ship_losses csl
                        JOIN "invTypes" it ON csl.ship_type_id = it."typeID"
                        LEFT JOIN market_prices mp ON mp.type_id = csl.ship_type_id
                            AND mp.region_id = %s
                        WHERE csl.region_id = %s
                        AND csl.date >= CURRENT_DATE - %s
                        GROUP BY csl.ship_type_id, it."typeName", mp.sell_volume
                        ORDER BY quantity DESC
                        LIMIT 20
                        """,
                        (region_id, region_id, days)
                    )
                    ships = [dict(row) for row in cur.fetchall()]

                    # Get top items lost
                    cur.execute(
                        """
                        SELECT
                            cil.item_type_id as type_id,
                            it."typeName" as name,
                            SUM(cil.quantity_destroyed) as quantity,
                            COALESCE(mp.sell_volume, 0) as market_stock
                        FROM combat_item_losses cil
                        JOIN "invTypes" it ON cil.item_type_id = it."typeID"
                        LEFT JOIN market_prices mp ON mp.type_id = cil.item_type_id
                            AND mp.region_id = %s
                        WHERE cil.region_id = %s
                        AND cil.date >= CURRENT_DATE - %s
                        GROUP BY cil.item_type_id, it."typeName", mp.sell_volume
                        ORDER BY quantity DESC
                        LIMIT 20
                        """,
                        (region_id, region_id, days)
                    )
                    items = [dict(row) for row in cur.fetchall()]

                    return {"ships": ships, "items": items}

        except Exception as e:
            raise RepositoryError(f"Failed to get demand analysis: {str(e)}") from e

    def get_heatmap_data(self, days: int, min_kills: int) -> List[Dict[str, Any]]:
        """
        Get kill heatmap data with system coordinates.

        Args:
            days: Number of days to look back
            min_kills: Minimum kills to include system

        Returns:
            List of system dictionaries with coordinates and kills

        Raises:
            RepositoryError: If database operation fails
        """
        try:
            with self.db.connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        """
                        SELECT
                            csl.solar_system_id as system_id,
                            srm.solar_system_name as name,
                            srm.region_id,
                            srm.region_name as region,
                            srm.security_status as security,
                            s.x / 1e16 as x,
                            s.z / 1e16 as z,
                            SUM(csl.quantity) as kills
                        FROM combat_ship_losses csl
                        JOIN system_region_map srm ON csl.solar_system_id = srm.solar_system_id
                        JOIN "mapSolarSystems" s ON csl.solar_system_id = s."solarSystemID"
                        WHERE csl.date >= CURRENT_DATE - %s
                        GROUP BY csl.solar_system_id, srm.solar_system_name,
                                 srm.region_id, srm.region_name, srm.security_status,
                                 s.x, s.z
                        HAVING SUM(csl.quantity) >= %s
                        ORDER BY kills DESC
                        """,
                        (days, min_kills)
                    )

                    results = cur.fetchall()
                    return [dict(row) for row in results]

        except Exception as e:
            raise RepositoryError(f"Failed to get heatmap data: {str(e)}") from e

    def get_doctrine_losses(self, region_id: int, days: int, min_size: int) -> List[Dict[str, Any]]:
        """
        Get bulk ship losses (potential fleet doctrines).

        Args:
            region_id: Region ID to analyze
            days: Number of days to look back
            min_size: Minimum fleet size to detect

        Returns:
            List of doctrine detection dictionaries

        Raises:
            RepositoryError: If database operation fails
        """
        try:
            with self.db.connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        """
                        SELECT
                            csl.date,
                            csl.solar_system_id as system_id,
                            srm.solar_system_name as system_name,
                            csl.ship_type_id,
                            it."typeName" as ship_name,
                            csl.quantity as fleet_size
                        FROM combat_ship_losses csl
                        JOIN system_region_map srm ON csl.solar_system_id = srm.solar_system_id
                        JOIN "invTypes" it ON csl.ship_type_id = it."typeID"
                        WHERE csl.region_id = %s
                        AND csl.date >= CURRENT_DATE - %s
                        AND csl.quantity >= %s
                        ORDER BY csl.quantity DESC
                        LIMIT 20
                        """,
                        (region_id, days, min_size)
                    )

                    results = cur.fetchall()
                    return [dict(row) for row in results]

        except Exception as e:
            raise RepositoryError(f"Failed to get doctrine losses: {str(e)}") from e

    def get_system_kills(self, system_id: int, days: int) -> int:
        """
        Get total kills in a system over specified days.

        Args:
            system_id: Solar system ID
            days: Number of days to look back

        Returns:
            Total number of kills

        Raises:
            RepositoryError: If database operation fails
        """
        try:
            with self.db.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT COALESCE(SUM(quantity), 0)
                        FROM combat_ship_losses
                        WHERE solar_system_id = %s
                        AND date >= CURRENT_DATE - %s
                        """,
                        (system_id, days)
                    )

                    result = cur.fetchone()
                    return int(result[0]) if result else 0

        except Exception as e:
            raise RepositoryError(f"Failed to get system kills: {str(e)}") from e

    def get_conflict_intel(self, alliance_id: Optional[int], days: int) -> List[Dict[str, Any]]:
        """
        Get alliance conflict intelligence.

        Args:
            alliance_id: Optional alliance ID to filter, None for all
            days: Number of days to look back

        Returns:
            List of conflict intel dictionaries

        Raises:
            RepositoryError: If database operation fails
        """
        try:
            with self.db.connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    if alliance_id is not None:
                        # Get specific alliance conflicts
                        cur.execute(
                            """
                            SELECT
                                alliance_a as alliance_id,
                                alliance_a as alliance_name,
                                ARRAY_AGG(DISTINCT alliance_b) as enemy_alliances,
                                SUM(kill_count) as total_losses,
                                COUNT(DISTINCT region_id) as active_fronts
                            FROM alliance_conflicts
                            WHERE alliance_a = %s
                            AND date >= CURRENT_DATE - %s
                            GROUP BY alliance_a
                            """,
                            (alliance_id, days)
                        )
                    else:
                        # Get all alliance conflicts
                        cur.execute(
                            """
                            SELECT
                                alliance_a as alliance_id,
                                alliance_a as alliance_name,
                                ARRAY_AGG(DISTINCT alliance_b) as enemy_alliances,
                                SUM(kill_count) as total_losses,
                                COUNT(DISTINCT region_id) as active_fronts
                            FROM alliance_conflicts
                            WHERE date >= CURRENT_DATE - %s
                            GROUP BY alliance_a
                            ORDER BY total_losses DESC
                            LIMIT 20
                            """,
                            (days,)
                        )

                    results = cur.fetchall()
                    return [dict(row) for row in results]

        except Exception as e:
            raise RepositoryError(f"Failed to get conflict intel: {str(e)}") from e
