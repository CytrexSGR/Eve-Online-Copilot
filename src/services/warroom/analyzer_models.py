"""War Analyzer domain models for demand analysis and doctrine detection."""

from datetime import date as date_type
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


# ==================== Demand Analysis Models ====================


class DemandItem(BaseModel):
    """Single demand item (ship or module)."""

    model_config = ConfigDict(from_attributes=True)

    type_id: int = Field(..., description="Item type ID")
    name: str = Field(..., description="Item name")
    quantity: int = Field(..., description="Total quantity lost/destroyed")
    market_stock: int = Field(default=0, description="Available market stock")
    gap: int = Field(default=0, description="Market gap (quantity - stock, clamped to 0)")


class DemandAnalysis(BaseModel):
    """Complete demand analysis for a region."""

    model_config = ConfigDict(from_attributes=True)

    region_id: int = Field(..., description="Region ID analyzed")
    days: int = Field(..., description="Number of days analyzed")
    ships_lost: List[DemandItem] = Field(default_factory=list, description="Top ships lost")
    items_lost: List[DemandItem] = Field(default_factory=list, description="Top items/modules lost")
    market_gaps: List[DemandItem] = Field(default_factory=list, description="Top 15 market gaps")


# ==================== Heatmap Models ====================


class HeatmapPoint(BaseModel):
    """System kill data for heatmap visualization."""

    model_config = ConfigDict(from_attributes=True)

    system_id: int = Field(..., description="Solar system ID")
    name: str = Field(..., description="System name")
    region_id: int = Field(..., description="Region ID")
    region: str = Field(..., description="Region name")
    security: float = Field(..., description="Security status")
    x: float = Field(..., description="X coordinate (scaled)")
    z: float = Field(..., description="Z coordinate (scaled)")
    kills: int = Field(..., description="Number of kills in system")


# ==================== Doctrine Detection Models ====================


class DoctrineDetection(BaseModel):
    """Detected fleet doctrine from bulk ship losses."""

    model_config = ConfigDict(from_attributes=True)

    date: date_type = Field(..., description="Date of losses")
    system_id: int = Field(..., description="Solar system ID")
    system_name: str = Field(..., description="Solar system name")
    ship_type_id: int = Field(..., description="Ship type ID")
    ship_name: str = Field(..., description="Ship name")
    fleet_size: int = Field(..., description="Number of ships lost")
    estimated_alliance: Optional[str] = Field(None, description="Estimated alliance (if known)")


# ==================== Danger Scoring Models ====================


class DangerScore(BaseModel):
    """System danger score based on recent kills."""

    model_config = ConfigDict(from_attributes=True)

    system_id: int = Field(..., description="Solar system ID")
    danger_score: int = Field(..., description="Danger score (0-10)")
    kills_24h: int = Field(..., description="Kills in last 24 hours")
    is_dangerous: bool = Field(..., description="System is dangerous (score >= 5)")


# ==================== Conflict Intel Models ====================


class ConflictIntel(BaseModel):
    """Alliance conflict intelligence."""

    model_config = ConfigDict(from_attributes=True)

    alliance_id: int = Field(..., description="Alliance ID")
    alliance_name: str = Field(..., description="Alliance name")
    enemy_alliances: List[str] = Field(default_factory=list, description="Enemy alliance names")
    total_losses: int = Field(..., description="Total ships lost")
    active_fronts: int = Field(..., description="Number of active regions with losses")
