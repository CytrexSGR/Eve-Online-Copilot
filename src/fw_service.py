"""
EVE Co-Pilot Faction Warfare Service Module
Handles FW system status tracking, hotspot detection, and historical snapshots
"""

import requests
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from psycopg2.extras import execute_values, RealDictCursor
from src.database import get_db_connection
from config import ESI_BASE_URL, ESI_USER_AGENT
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fw_service")

# Faction ID to name mapping
FACTIONS = {
    500001: "Caldari State",
    500002: "Minmatar Republic",
    500003: "Amarr Empire",
    500004: "Gallente Federation"
}


class FactionWarfareService:
    """Service for tracking Faction Warfare system status and detecting hotspots"""

    def __init__(self):
        self.base_url = ESI_BASE_URL
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": ESI_USER_AGENT,
            "Accept": "application/json"
        })

    def fetch_fw_systems(self) -> Optional[List[Dict]]:
        """
        Fetch current FW system status from ESI.

        Returns:
            List of FW system status dicts or None on error
        """
        url = f"{self.base_url}/fw/systems/"

        try:
            response = self.session.get(
                url,
                params={"datasource": "tranquility"},
                timeout=30
            )

            if response.status_code != 200:
                logger.error(f"ESI request failed with status {response.status_code}: {response.text}")
                return None

            systems = response.json()
            logger.info(f"Fetched {len(systems)} FW systems from ESI")
            return systems

        except requests.Timeout:
            logger.error("ESI request timeout")
            return None
        except requests.RequestException as e:
            logger.error(f"ESI request error: {e}")
            return None

    def update_status(self) -> Dict:
        """
        Fetch current FW status from ESI and snapshot to database.

        Returns:
            Dict with update statistics
        """
        systems = self.fetch_fw_systems()

        if not systems:
            return {
                "success": False,
                "error": "Failed to fetch FW systems from ESI"
            }

        # Prepare data for bulk insert
        now = datetime.now()
        values = []

        for system in systems:
            solar_system_id = system.get("solar_system_id")
            owner_faction_id = system.get("owner_faction_id")
            occupier_faction_id = system.get("occupier_faction_id")
            contested = system.get("contested", "uncontested")
            victory_points = system.get("victory_points", 0)
            victory_points_threshold = system.get("victory_points_threshold", 3000)

            if solar_system_id and owner_faction_id and occupier_faction_id:
                values.append((
                    solar_system_id,
                    owner_faction_id,
                    occupier_faction_id,
                    contested,
                    victory_points,
                    victory_points_threshold,
                    now
                ))

        # Bulk insert into database
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                execute_values(
                    cur,
                    """
                    INSERT INTO fw_system_status
                    (solar_system_id, owner_faction_id, occupier_faction_id,
                     contested, victory_points, victory_points_threshold, snapshot_time)
                    VALUES %s
                    """,
                    values,
                    page_size=1000
                )
                conn.commit()

        logger.info(f"Snapshot completed: {len(values)} systems saved")

        return {
            "success": True,
            "systems_updated": len(values),
            "timestamp": now.isoformat(),
            "message": f"Snapshot completed: {len(values)} FW systems saved"
        }

    def get_hotspots(self, min_contested_percent: float = 50.0) -> List[Dict]:
        """
        Get highly contested systems (hotspots).

        Args:
            min_contested_percent: Minimum contested percentage (VP/threshold * 100)

        Returns:
            List of hotspot systems with details
        """
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Get latest snapshot time
                cur.execute("""
                    SELECT MAX(snapshot_time) as latest_time
                    FROM fw_system_status
                """)

                result = cur.fetchone()
                if not result or not result['latest_time']:
                    logger.warning("No FW snapshots found in database")
                    return []

                latest_time = result['latest_time']

                # Get contested systems from latest snapshot
                cur.execute("""
                    SELECT
                        fws.solar_system_id,
                        srm.solar_system_name,
                        srm.region_name,
                        srm.security_status,
                        fws.owner_faction_id,
                        fws.occupier_faction_id,
                        fws.contested,
                        fws.victory_points,
                        fws.victory_points_threshold,
                        ROUND((fws.victory_points::numeric / fws.victory_points_threshold * 100), 2) as contested_percent,
                        fws.snapshot_time
                    FROM fw_system_status fws
                    LEFT JOIN system_region_map srm ON fws.solar_system_id = srm.solar_system_id
                    WHERE fws.snapshot_time = %s
                    AND (fws.victory_points::numeric / fws.victory_points_threshold * 100) >= %s
                    ORDER BY (fws.victory_points::numeric / fws.victory_points_threshold * 100) DESC
                """, (latest_time, min_contested_percent))

                hotspots = cur.fetchall()

                # Add faction names
                for hotspot in hotspots:
                    hotspot['owner_faction_name'] = FACTIONS.get(hotspot['owner_faction_id'], "Unknown")
                    hotspot['occupier_faction_name'] = FACTIONS.get(hotspot['occupier_faction_id'], "Unknown")

                logger.info(f"Found {len(hotspots)} hotspots (>={min_contested_percent}% contested)")
                return hotspots

    def get_vulnerable_systems(self) -> List[Dict]:
        """
        Get systems close to flipping (>90% contested).

        Returns:
            List of vulnerable systems
        """
        return self.get_hotspots(min_contested_percent=90.0)

    def cleanup_old_snapshots(self, days: int = 7) -> Dict:
        """
        Remove old snapshots older than specified days.

        Args:
            days: Number of days to retain

        Returns:
            Dict with cleanup statistics
        """
        cutoff_date = datetime.now() - timedelta(days=days)

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM fw_system_status
                    WHERE snapshot_time < %s
                """, (cutoff_date,))

                deleted_count = cur.rowcount
                conn.commit()

        logger.info(f"Cleanup completed: {deleted_count} old snapshots deleted (older than {days} days)")

        return {
            "success": True,
            "deleted_count": deleted_count,
            "cutoff_date": cutoff_date.isoformat(),
            "message": f"Deleted {deleted_count} snapshots older than {days} days"
        }

    def get_system_history(self, solar_system_id: int, hours: int = 24) -> List[Dict]:
        """
        Get historical snapshots for a specific system.

        Args:
            solar_system_id: Solar system ID
            hours: Number of hours to look back

        Returns:
            List of historical snapshots
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)

        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT
                        solar_system_id,
                        owner_faction_id,
                        occupier_faction_id,
                        contested,
                        victory_points,
                        victory_points_threshold,
                        ROUND((victory_points::numeric / victory_points_threshold * 100), 2) as contested_percent,
                        snapshot_time
                    FROM fw_system_status
                    WHERE solar_system_id = %s
                    AND snapshot_time >= %s
                    ORDER BY snapshot_time DESC
                """, (solar_system_id, cutoff_time))

                history = cur.fetchall()

                # Add faction names
                for snapshot in history:
                    snapshot['owner_faction_name'] = FACTIONS.get(snapshot['owner_faction_id'], "Unknown")
                    snapshot['occupier_faction_name'] = FACTIONS.get(snapshot['occupier_faction_id'], "Unknown")

                return history

    def get_faction_statistics(self) -> Dict:
        """
        Get current statistics per faction from latest snapshot.

        Returns:
            Dict with faction statistics
        """
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Get latest snapshot time
                cur.execute("""
                    SELECT MAX(snapshot_time) as latest_time
                    FROM fw_system_status
                """)

                result = cur.fetchone()
                if not result or not result['latest_time']:
                    return {}

                latest_time = result['latest_time']

                # Get statistics per faction
                cur.execute("""
                    SELECT
                        owner_faction_id,
                        COUNT(*) as systems_owned,
                        SUM(CASE WHEN contested = 'contested' THEN 1 ELSE 0 END) as systems_contested,
                        SUM(CASE WHEN contested = 'vulnerable' THEN 1 ELSE 0 END) as systems_vulnerable,
                        AVG(ROUND((victory_points::numeric / victory_points_threshold * 100), 2)) as avg_contested_percent
                    FROM fw_system_status
                    WHERE snapshot_time = %s
                    GROUP BY owner_faction_id
                """, (latest_time,))

                stats = cur.fetchall()

                # Format results
                faction_stats = {}
                for stat in stats:
                    faction_id = stat['owner_faction_id']
                    faction_name = FACTIONS.get(faction_id, f"Unknown ({faction_id})")
                    faction_stats[faction_name] = {
                        "faction_id": faction_id,
                        "systems_owned": stat['systems_owned'],
                        "systems_contested": stat['systems_contested'],
                        "systems_vulnerable": stat['systems_vulnerable'],
                        "avg_contested_percent": float(stat['avg_contested_percent'] or 0)
                    }

                return faction_stats


# Global singleton instance
fw_service = FactionWarfareService()
