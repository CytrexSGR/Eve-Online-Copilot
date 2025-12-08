"""Market service Pydantic models."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class MarketPrice(BaseModel):
    """Market price data model."""

    model_config = ConfigDict(from_attributes=True)

    type_id: int = Field(..., description="EVE type ID")
    adjusted_price: float = Field(..., ge=0, description="Adjusted price from ESI")
    average_price: float = Field(..., ge=0, description="Average price from ESI")
    last_updated: datetime = Field(..., description="Timestamp of last update")


class CacheStats(BaseModel):
    """Market price cache statistics."""

    model_config = ConfigDict(from_attributes=True)

    total_items: int = Field(..., ge=0, description="Total number of cached items")
    oldest_entry: Optional[datetime] = Field(None, description="Timestamp of oldest entry")
    newest_entry: Optional[datetime] = Field(None, description="Timestamp of newest entry")
    cache_age_seconds: Optional[float] = Field(None, ge=0, description="Age of cache in seconds")
    is_stale: bool = Field(..., description="Whether cache is stale (>1 hour)")


class PriceUpdate(BaseModel):
    """Price update result model."""

    model_config = ConfigDict(from_attributes=True)

    success: bool = Field(..., description="Whether update was successful")
    items_updated: int = Field(..., ge=0, description="Number of items updated")
    timestamp: datetime = Field(..., description="Timestamp of update")
    message: str = Field(..., description="Human-readable message")
