"""
Cargo Service Models

Pydantic models for cargo calculations and ship recommendations
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class CargoItem(BaseModel):
    """
    A single cargo item with type_id and quantity
    """
    type_id: int = Field(..., gt=0, description="EVE item type ID (must be positive)")
    quantity: int = Field(default=1, gt=0, description="Item quantity (must be positive)")


class CargoItemBreakdown(BaseModel):
    """
    Cargo item with volume breakdown
    """
    type_id: int = Field(..., gt=0, description="EVE item type ID (must be positive)")
    quantity: int = Field(..., gt=0, description="Item quantity (must be positive)")
    unit_volume: float = Field(..., ge=0, description="Volume per unit in m³ (must be >= 0)")
    total_volume: float = Field(..., ge=0, description="Total volume for all units in m³ (must be >= 0)")


class CargoCalculation(BaseModel):
    """
    Complete cargo calculation result
    """
    total_volume_m3: float = Field(..., ge=0, description="Total cargo volume in m³ (must be >= 0)")
    total_volume_formatted: str = Field(..., description="Formatted volume string (e.g., '2.5K m³')")
    items: List[CargoItemBreakdown] = Field(default_factory=list, description="Breakdown of individual items")


class ShipInfo(BaseModel):
    """
    Basic ship information
    """
    ship_type: str = Field(..., description="Ship type key (e.g., 'industrial', 'freighter')")
    ship_name: str = Field(..., description="Human-readable ship name")
    capacity: float = Field(..., gt=0, description="Cargo capacity in m³ (must be positive)")


class ShipRecommendation(ShipInfo):
    """
    Ship recommendation with trip calculations
    """
    trips: int = Field(..., ge=1, description="Number of trips required (must be >= 1)")
    fill_percent: float = Field(..., ge=0, description="Percentage of cargo hold filled")
    excess_capacity: float = Field(..., description="Remaining cargo space in m³")


class ShipRecommendations(BaseModel):
    """
    Complete ship recommendation result
    """
    volume_m3: float = Field(..., ge=0, description="Total cargo volume in m³ (must be >= 0)")
    volume_formatted: str = Field(..., description="Formatted volume string")
    recommended: ShipRecommendation = Field(..., description="Best recommended ship")
    safe_option: Optional[ShipRecommendation] = Field(None, description="Safest transport option (if available)")
    all_options: List[ShipRecommendation] = Field(default_factory=list, description="All available ship options")
