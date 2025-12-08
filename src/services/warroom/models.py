"""War Room domain models for sovereignty and faction warfare."""

from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, Field, ConfigDict


# ==================== Sovereignty Models ====================


class SovCampaign(BaseModel):
    """Sovereignty campaign model."""

    model_config = ConfigDict(from_attributes=True)

    campaign_id: int = Field(..., description="Unique campaign identifier")
    system_id: int = Field(..., description="Solar system ID where campaign is active")
    constellation_id: int = Field(..., description="Constellation ID")
    structure_type_id: int = Field(..., description="Structure type being contested")
    event_type: str = Field(..., description="Event type (tcu_defense, ihub_defense, etc.)")
    start_time: datetime = Field(..., description="Campaign start time")
    defender_id: int = Field(..., description="Defender alliance ID")
    defender_score: float = Field(..., description="Defender progress score (0.0-1.0)")
    attackers_score: float = Field(..., description="Attackers progress score (0.0-1.0)")
    structure_id: Optional[int] = Field(None, description="Structure ID if applicable")


class SovCampaignList(BaseModel):
    """List of sovereignty campaigns with count."""

    model_config = ConfigDict(from_attributes=True)

    campaigns: List[SovCampaign] = Field(default_factory=list, description="List of campaigns")
    count: int = Field(..., description="Total number of campaigns")


class SovSystemInfo(BaseModel):
    """Sovereignty system information."""

    model_config = ConfigDict(from_attributes=True)

    system_id: int = Field(..., description="Solar system ID")
    alliance_id: Optional[int] = Field(None, description="Alliance holding sovereignty")
    corporation_id: Optional[int] = Field(None, description="Corporation holding sovereignty")
    vulnerability_occupancy_level: Optional[float] = Field(
        None, description="Vulnerability occupancy level"
    )


# ==================== Faction Warfare Models ====================


class FWSystemStatus(BaseModel):
    """Faction warfare system status model."""

    model_config = ConfigDict(from_attributes=True)

    system_id: int = Field(..., description="Solar system ID")
    owning_faction_id: int = Field(..., description="Faction that owns the system")
    occupying_faction_id: int = Field(..., description="Faction currently occupying the system")
    contested: str = Field(..., description="Contest status (captured, contested, uncontested, vulnerable)")
    victory_points: int = Field(..., description="Current victory points")
    victory_points_threshold: int = Field(..., description="Victory points needed to flip")


class FWHotspot(BaseModel):
    """Faction warfare hotspot (highly contested system)."""

    model_config = ConfigDict(from_attributes=True)

    system_id: int = Field(..., description="Solar system ID")
    system_name: Optional[str] = Field(None, description="Solar system name")
    contested: str = Field(..., description="Contest status")
    victory_points: int = Field(..., description="Current victory points")
    progress_percent: float = Field(..., description="Contest progress percentage")
    is_critical: bool = Field(..., description="Critical system flag (>=90% contested)")


class FWStats(BaseModel):
    """Faction warfare statistics."""

    model_config = ConfigDict(from_attributes=True)

    total_systems: int = Field(..., description="Total number of FW systems")
    contested_count: int = Field(..., description="Number of contested systems")
    faction_breakdown: Dict[int, int] = Field(
        default_factory=dict,
        description="Systems owned per faction (faction_id -> count)"
    )
