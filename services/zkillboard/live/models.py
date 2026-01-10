"""
Live Service Models and Constants.

Provides data structures and configuration for real-time killmail processing.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional


# Redis Configuration
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 0
REDIS_TTL = 86400  # 24 hours

# zKillboard Configuration
ZKILL_API_URL = "https://zkillboard.com/api/kills/"
ZKILL_USER_AGENT = "EVE-CoPilot/1.0 (Live Combat Intelligence)"
ZKILL_REQUEST_TIMEOUT = 10  # seconds
ZKILL_POLL_INTERVAL = 10  # Poll every 10 seconds

# ESI Configuration
ESI_KILLMAIL_URL = "https://esi.evetech.net/latest/killmails/{killmail_id}/{hash}/"
ESI_USER_AGENT = "EVE-CoPilot/1.0"

# Hotspot Detection Configuration
HOTSPOT_WINDOW_SECONDS = 300  # 5 minutes
HOTSPOT_THRESHOLD_KILLS = 5   # 5+ kills in 5min = hotspot
HOTSPOT_ALERT_COOLDOWN = 600  # 10 minutes between alerts for same system


@dataclass
class LiveKillmail:
    """Structured killmail data"""
    killmail_id: int
    killmail_time: str
    solar_system_id: int
    region_id: int
    ship_type_id: int
    ship_value: float
    victim_character_id: Optional[int]
    victim_corporation_id: Optional[int]
    victim_alliance_id: Optional[int]
    attacker_count: int
    is_solo: bool
    is_npc: bool
    destroyed_items: List[Dict]  # Items that were destroyed (market demand)
    dropped_items: List[Dict]    # Items that dropped (no market demand)
    attacker_corporations: List[int]  # Corp IDs of attackers
    attacker_alliances: List[int]     # Alliance IDs of attackers
