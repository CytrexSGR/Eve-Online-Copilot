"""
Pydantic models for request/response schemas.
Centralized location for all API models.
"""

from pydantic import BaseModel
from typing import Optional, List

from config import REGIONS


# ============================================================
# Production Models
# ============================================================

class ProductionCostRequest(BaseModel):
    type_id: int
    me_level: int = 0
    te_level: int = 0
    region_id: int = REGIONS["the_forge"]
    use_buy_orders: bool = False


class SimulationRequest(BaseModel):
    blueprint_name: Optional[str] = None
    type_id: Optional[int] = None
    runs: int = 1
    me: int = 0
    te: int = 0
    character_id: Optional[int] = None
    region_id: int = REGIONS["the_forge"]


# ============================================================
# Trade Models
# ============================================================

class ArbitrageRequest(BaseModel):
    group_name: Optional[str] = None
    group_id: Optional[int] = None
    source_region: int = REGIONS["the_forge"]
    target_region: int = REGIONS["domain"]
    min_margin_percent: float = 5.0
    limit: int = 5


# ============================================================
# Bookmark Models
# ============================================================

class BookmarkCreate(BaseModel):
    type_id: int
    item_name: str
    character_id: Optional[int] = None
    corporation_id: Optional[int] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    priority: int = 0


class BookmarkUpdate(BaseModel):
    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    priority: Optional[int] = None


class BookmarkListCreate(BaseModel):
    name: str
    description: Optional[str] = None
    character_id: Optional[int] = None
    corporation_id: Optional[int] = None
    is_shared: bool = False


# ============================================================
# Cargo Models
# ============================================================

class CargoCalculateRequest(BaseModel):
    items: List[dict]
