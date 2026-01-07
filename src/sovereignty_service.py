"""
EVE Co-Pilot Sovereignty Service Module
Handles sovereignty campaigns tracking from ESI

Fetches:
- Active sovereignty campaigns (timers)
- Alliance information
- System region mapping

Database tables:
- sovereignty_campaigns: All active campaigns
- system_region_map: System->Region mapping
"""

import requests
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from src.database import get_db_connection
from config import ESI_BASE_URL, ESI_USER_AGENT

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sovereignty_service")


class SovereigntyService:
    """Service for tracking EVE sovereignty campaigns"""

    def __init__(self):
        self.base_url = ESI_BASE_URL
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": ESI_USER_AGENT,
            "Accept": "application/json"
        })

        # Alliance name cache (in-memory)
        self._alliance_cache: Dict[int, str] = {}

    def fetch_campaigns(self) -> Optional[List[Dict]]:
        """
        Fetch all active sovereignty campaigns from ESI.

        ESI Endpoint: GET /sovereignty/campaigns/

        Returns:
            List of campaign dicts or None on error
        """
        url = f"{self.base_url}/sovereignty/campaigns/"

        try:
            response = self.session.get(
                url,
                params={"datasource": "tranquility"},
                timeout=30
            )

            if response.status_code != 200:
                logger.error(f"ESI request failed with status {response.status_code}: {response.text[:200]}")
                return None

            campaigns = response.json()
            logger.info(f"Fetched {len(campaigns)} active campaigns from ESI")
            return campaigns

        except requests.Timeout:
            logger.error("ESI timeout on /sovereignty/campaigns/")
            return None
        except requests.RequestException as e:
            logger.error(f"ESI request error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching campaigns: {e}")
            return None

    def get_alliance_name(self, alliance_id: int) -> Optional[str]:
        """
        Get alliance name from ESI (with caching).

        Args:
            alliance_id: Alliance ID

        Returns:
            Alliance name or None
        """
        # Check cache
        if alliance_id in self._alliance_cache:
            return self._alliance_cache[alliance_id]

        url = f"{self.base_url}/alliances/{alliance_id}/"

        try:
            response = self.session.get(
                url,
                params={"datasource": "tranquility"},
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                name = data.get("name", f"Alliance {alliance_id}")

                # Cache it
                self._alliance_cache[alliance_id] = name
                return name
            else:
                logger.warning(f"Failed to fetch alliance {alliance_id}: {response.status_code}")
                return f"Alliance {alliance_id}"

        except Exception as e:
            logger.warning(f"Error fetching alliance {alliance_id}: {e}")
            return f"Alliance {alliance_id}"

    def update_campaigns(self) -> Dict:
        """
        Fetch campaigns from ESI and sync to database.

        Process:
        1. Fetch campaigns from ESI
        2. Get alliance names (cached)
        3. Upsert to database
        4. Clean up old campaigns (>24h past start time)

        Returns:
            Stats dict {updated, new, deleted, total}
        """
        # Fetch campaigns
        campaigns = self.fetch_campaigns()

        if campaigns is None:
            return {
                "error": "Failed to fetch campaigns from ESI",
                "updated": 0,
                "new": 0,
                "deleted": 0
            }

        # Get alliance names for all defenders
        for campaign in campaigns:
            defender_id = campaign.get("defender_id")
            if defender_id:
                campaign["defender_name"] = self.get_alliance_name(defender_id)
            else:
                campaign["defender_name"] = None

        # Sync to database
        updated = 0
        new = 0

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                for campaign in campaigns:
                    # Parse start_time from ISO format
                    start_time_str = campaign.get("start_time")
                    if start_time_str:
                        # ESI returns ISO 8601 format like "2025-12-07T18:00:00Z"
                        start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
                    else:
                        start_time = None

                    # Check if campaign exists
                    cur.execute("""
                        SELECT id FROM sovereignty_campaigns
                        WHERE campaign_id = %s
                    """, (campaign.get("campaign_id"),))

                    exists = cur.fetchone()

                    if exists:
                        # Update existing
                        cur.execute("""
                            UPDATE sovereignty_campaigns
                            SET
                                event_type = %s,
                                solar_system_id = %s,
                                constellation_id = %s,
                                defender_id = %s,
                                defender_name = %s,
                                attacker_score = %s,
                                defender_score = %s,
                                start_time = %s,
                                structure_id = %s,
                                last_updated_at = NOW()
                            WHERE campaign_id = %s
                        """, (
                            campaign.get("event_type"),
                            campaign.get("solar_system_id"),
                            campaign.get("constellation_id"),
                            campaign.get("defender_id"),
                            campaign.get("defender_name"),
                            campaign.get("attackers_score"),
                            campaign.get("defender_score"),
                            start_time,
                            campaign.get("structure_id"),
                            campaign.get("campaign_id")
                        ))
                        updated += 1
                    else:
                        # Insert new
                        cur.execute("""
                            INSERT INTO sovereignty_campaigns (
                                campaign_id, event_type, solar_system_id, constellation_id,
                                defender_id, defender_name, attacker_score, defender_score,
                                start_time, structure_id, first_seen_at, last_updated_at
                            ) VALUES (
                                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW()
                            )
                        """, (
                            campaign.get("campaign_id"),
                            campaign.get("event_type"),
                            campaign.get("solar_system_id"),
                            campaign.get("constellation_id"),
                            campaign.get("defender_id"),
                            campaign.get("defender_name"),
                            campaign.get("attackers_score"),
                            campaign.get("defender_score"),
                            start_time,
                            campaign.get("structure_id")
                        ))
                        new += 1

                # Clean up old campaigns (>24h past start time)
                cur.execute("""
                    DELETE FROM sovereignty_campaigns
                    WHERE start_time < NOW() - INTERVAL '24 hours'
                """)
                deleted = cur.rowcount

                conn.commit()

        logger.info(f"Campaigns synced: {new} new, {updated} updated, {deleted} deleted")

        return {
            "success": True,
            "total_campaigns": len(campaigns),
            "new": new,
            "updated": updated,
            "deleted": deleted,
            "timestamp": datetime.now().isoformat()
        }

    def get_upcoming_battles(self, hours: int = 48) -> List[Dict]:
        """
        Get campaigns starting in the next X hours.

        Args:
            hours: Time window for upcoming battles (default 48h)

        Returns:
            List of campaign dicts with system/region info
        """
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        sc.campaign_id,
                        sc.event_type,
                        sc.solar_system_id,
                        srm.solar_system_name,
                        srm.region_name,
                        sc.defender_id,
                        sc.defender_name,
                        sc.attacker_score,
                        sc.defender_score,
                        sc.start_time,
                        sc.structure_id,
                        EXTRACT(EPOCH FROM (sc.start_time - NOW())) / 3600 as hours_until_start
                    FROM sovereignty_campaigns sc
                    LEFT JOIN system_region_map srm ON sc.solar_system_id = srm.solar_system_id
                    WHERE sc.start_time > NOW()
                    AND sc.start_time < NOW() + INTERVAL '%s hours'
                    ORDER BY sc.start_time ASC
                """, (hours,))

                battles = []
                for row in cur.fetchall():
                    battles.append({
                        "campaign_id": row[0],
                        "event_type": row[1],
                        "solar_system_id": row[2],
                        "solar_system_name": row[3],
                        "region_name": row[4],
                        "defender_id": row[5],
                        "defender_name": row[6],
                        "attacker_score": row[7],
                        "defender_score": row[8],
                        "start_time": row[9].isoformat() if row[9] else None,
                        "structure_id": row[10],
                        "hours_until_start": round(row[11], 1) if row[11] else None
                    })

                return battles

    def get_stats(self) -> Dict:
        """Get statistics about tracked campaigns"""
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        COUNT(*) as total,
                        COUNT(DISTINCT defender_id) as unique_defenders,
                        COUNT(DISTINCT solar_system_id) as systems_involved,
                        MIN(start_time) as next_battle,
                        MAX(start_time) as latest_battle
                    FROM sovereignty_campaigns
                    WHERE start_time > NOW()
                """)
                row = cur.fetchone()

                return {
                    "total_campaigns": row[0] if row else 0,
                    "unique_defenders": row[1] if row else 0,
                    "systems_involved": row[2] if row else 0,
                    "next_battle": row[3].isoformat() if row and row[3] else None,
                    "latest_battle": row[4].isoformat() if row and row[4] else None
                }


# Global sovereignty service instance
sovereignty_service = SovereigntyService()
