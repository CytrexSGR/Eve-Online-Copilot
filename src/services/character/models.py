"""
Character Service Pydantic Models

Pydantic v2 models for all character-related data structures.
These models provide validation, serialization, and type safety for character API responses.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, model_validator


class WalletBalance(BaseModel):
    """Character wallet balance with formatted ISK display"""

    character_id: int = Field(..., gt=0, description="EVE character ID")
    balance: float = Field(..., description="Wallet balance in ISK")
    formatted: str = Field(default="", description="Formatted balance with ISK suffix")

    @model_validator(mode="after")
    def format_balance(self) -> "WalletBalance":
        """Automatically format the balance as ISK"""
        self.formatted = f"{self.balance:,.2f} ISK"
        return self


class Asset(BaseModel):
    """Single asset item from character assets"""

    item_id: int = Field(..., gt=0, description="Unique item instance ID")
    type_id: int = Field(..., gt=0, description="EVE type ID of the item")
    location_id: int = Field(..., gt=0, description="Location where asset is stored")
    quantity: int = Field(..., gt=0, description="Quantity of items")
    is_singleton: bool = Field(..., description="Whether item is a singleton (ship, container)")
    location_flag: Optional[str] = Field(None, description="Location flag (Hangar, Cargo, etc.)")
    location_type: Optional[str] = Field(None, description="Location type (station, solar_system, etc.)")


class AssetList(BaseModel):
    """List of character assets with total count"""

    character_id: int = Field(..., gt=0, description="EVE character ID")
    total_items: int = Field(..., ge=0, description="Total number of assets")
    assets: List[Asset] = Field(default_factory=list, description="List of assets")

    @model_validator(mode="after")
    def validate_count(self) -> "AssetList":
        """Validate that total_items matches the actual number of assets"""
        if self.total_items != len(self.assets):
            raise ValueError(f"total_items ({self.total_items}) must match assets length ({len(self.assets)})")
        return self


class AssetName(BaseModel):
    """Named asset (container, ship, etc.)"""

    item_id: int = Field(..., gt=0, description="Unique item instance ID")
    name: str = Field(..., min_length=1, max_length=255, description="Custom name for the asset")


class Skill(BaseModel):
    """Single skill with training information"""

    skill_id: int = Field(..., gt=0, description="EVE skill type ID")
    skill_name: str = Field(..., min_length=1, description="Name of the skill")
    level: int = Field(..., ge=0, le=5, description="Currently active skill level (0-5)")
    trained_level: int = Field(..., ge=0, le=5, description="Trained skill level (0-5)")
    skillpoints: int = Field(..., ge=0, description="Skillpoints invested in this skill")


class SkillData(BaseModel):
    """Complete character skill data"""

    character_id: int = Field(..., gt=0, description="EVE character ID")
    total_sp: int = Field(..., ge=0, description="Total skillpoints")
    unallocated_sp: int = Field(..., ge=0, description="Unallocated skillpoints")
    skill_count: int = Field(..., ge=0, description="Number of skills")
    skills: List[Skill] = Field(default_factory=list, description="List of skills")

    @model_validator(mode="after")
    def validate_skill_count(self) -> "SkillData":
        """Validate that skill_count matches the actual number of skills"""
        if self.skill_count != len(self.skills):
            raise ValueError(f"skill_count ({self.skill_count}) must match skills length ({len(self.skills)})")
        return self


class SkillQueueItem(BaseModel):
    """Single item in the skill training queue"""

    skill_id: int = Field(..., gt=0, description="EVE skill type ID")
    finish_date: str = Field(..., description="ISO 8601 date when skill finishes training")
    finished_level: int = Field(..., ge=0, le=5, description="Level that will be reached (0-5)")
    queue_position: int = Field(..., ge=0, description="Position in the queue")


class SkillQueue(BaseModel):
    """Character skill training queue"""

    character_id: int = Field(..., gt=0, description="EVE character ID")
    queue_length: int = Field(..., ge=0, description="Number of skills in queue")
    queue: List[SkillQueueItem] = Field(default_factory=list, description="Skill queue items")

    @model_validator(mode="after")
    def validate_queue_length(self) -> "SkillQueue":
        """Validate that queue_length matches the actual queue size"""
        if self.queue_length != len(self.queue):
            raise ValueError(f"queue_length ({self.queue_length}) must match queue length ({len(self.queue)})")
        return self


class MarketOrder(BaseModel):
    """Single market order (buy or sell)"""

    order_id: int = Field(..., gt=0, description="Unique order ID")
    type_id: int = Field(..., gt=0, description="EVE type ID being traded")
    location_id: int = Field(..., gt=0, description="Station/structure location ID")
    volume_total: int = Field(..., gt=0, description="Total volume of order")
    volume_remain: int = Field(..., gt=0, description="Remaining volume")
    price: float = Field(..., gt=0, description="Price per unit")
    is_buy_order: bool = Field(..., description="True for buy orders, False for sell orders")

    @model_validator(mode="after")
    def validate_volumes(self) -> "MarketOrder":
        """Validate that volume_remain does not exceed volume_total"""
        if self.volume_remain > self.volume_total:
            raise ValueError(f"volume_remain ({self.volume_remain}) cannot exceed volume_total ({self.volume_total})")
        return self


class MarketOrderList(BaseModel):
    """List of character market orders"""

    character_id: int = Field(..., gt=0, description="EVE character ID")
    total_orders: int = Field(..., ge=0, description="Total number of orders")
    buy_orders: int = Field(..., ge=0, description="Number of buy orders")
    sell_orders: int = Field(..., ge=0, description="Number of sell orders")
    orders: List[MarketOrder] = Field(default_factory=list, description="List of orders")

    @model_validator(mode="after")
    def validate_counts(self) -> "MarketOrderList":
        """Validate that buy_orders + sell_orders equals total_orders"""
        if self.buy_orders + self.sell_orders != self.total_orders:
            raise ValueError(
                f"buy_orders ({self.buy_orders}) + sell_orders ({self.sell_orders}) "
                f"must equal total_orders ({self.total_orders})"
            )
        if self.total_orders != len(self.orders):
            raise ValueError(f"total_orders ({self.total_orders}) must match orders length ({len(self.orders)})")
        return self


class IndustryJob(BaseModel):
    """Single industry job"""

    job_id: int = Field(..., gt=0, description="Unique job ID")
    activity_id: int = Field(..., gt=0, description="Industry activity ID")
    blueprint_type_id: int = Field(..., gt=0, description="Blueprint type ID")
    status: str = Field(..., description="Job status")
    duration: int = Field(..., gt=0, description="Job duration in seconds")
    installer_id: int = Field(..., gt=0, description="Character ID who installed the job")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate that status is a valid industry job status"""
        valid_statuses = ["active", "cancelled", "delivered", "paused", "ready", "reverted"]
        if v not in valid_statuses:
            raise ValueError(f"status must be one of {valid_statuses}, got {v}")
        return v


class IndustryJobList(BaseModel):
    """List of character industry jobs"""

    character_id: int = Field(..., gt=0, description="EVE character ID")
    total_jobs: int = Field(..., ge=0, description="Total number of jobs")
    active_jobs: int = Field(..., ge=0, description="Number of active jobs")
    jobs: List[IndustryJob] = Field(default_factory=list, description="List of jobs")

    @model_validator(mode="after")
    def validate_counts(self) -> "IndustryJobList":
        """Validate that active_jobs does not exceed total_jobs"""
        if self.active_jobs > self.total_jobs:
            raise ValueError(f"active_jobs ({self.active_jobs}) cannot exceed total_jobs ({self.total_jobs})")
        if self.total_jobs != len(self.jobs):
            raise ValueError(f"total_jobs ({self.total_jobs}) must match jobs length ({len(self.jobs)})")
        return self


class Blueprint(BaseModel):
    """Single blueprint (original or copy)"""

    item_id: int = Field(..., gt=0, description="Unique item instance ID")
    type_id: int = Field(..., gt=0, description="Blueprint type ID")
    location_id: int = Field(..., gt=0, description="Location where blueprint is stored")
    quantity: int = Field(..., description="Blueprint type: -1 = original, -2 = copy")
    material_efficiency: int = Field(..., ge=0, le=10, description="Material efficiency level (0-10)")
    time_efficiency: int = Field(..., ge=0, le=20, description="Time efficiency level (0-20)")
    runs: Optional[int] = Field(None, ge=0, description="Remaining runs (for copies)")

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: int) -> int:
        """Validate that quantity is -1 (original) or -2 (copy)"""
        if v not in [-1, -2]:
            raise ValueError(f"quantity must be -1 (original) or -2 (copy), got {v}")
        return v


class BlueprintList(BaseModel):
    """List of character blueprints"""

    character_id: int = Field(..., gt=0, description="EVE character ID")
    total_blueprints: int = Field(..., ge=0, description="Total number of blueprints")
    originals: int = Field(..., ge=0, description="Number of original blueprints")
    copies: int = Field(..., ge=0, description="Number of blueprint copies")
    blueprints: List[Blueprint] = Field(default_factory=list, description="List of blueprints")

    @model_validator(mode="after")
    def validate_counts(self) -> "BlueprintList":
        """Validate that originals + copies equals total_blueprints"""
        if self.originals + self.copies != self.total_blueprints:
            raise ValueError(
                f"originals ({self.originals}) + copies ({self.copies}) "
                f"must equal total_blueprints ({self.total_blueprints})"
            )
        if self.total_blueprints != len(self.blueprints):
            raise ValueError(
                f"total_blueprints ({self.total_blueprints}) must match blueprints length ({len(self.blueprints)})"
            )
        return self


class CharacterInfo(BaseModel):
    """Public character information"""

    character_id: int = Field(..., gt=0, description="EVE character ID")
    name: str = Field(..., min_length=1, description="Character name")
    corporation_id: int = Field(..., gt=0, description="Corporation ID")
    birthday: str = Field(..., description="Character creation date (ISO 8601)")
    alliance_id: Optional[int] = Field(None, gt=0, description="Alliance ID (if in alliance)")


class CorporationInfo(BaseModel):
    """Public corporation information"""

    corporation_id: int = Field(..., gt=0, description="EVE corporation ID")
    name: str = Field(..., min_length=1, description="Corporation name")
    ticker: str = Field(..., min_length=1, max_length=5, description="Corporation ticker")
    member_count: int = Field(..., gt=0, description="Number of members")
    ceo_id: int = Field(..., gt=0, description="CEO character ID")
    alliance_id: Optional[int] = Field(None, gt=0, description="Alliance ID (if in alliance)")


class CorporationWalletDivision(BaseModel):
    """Single corporation wallet division"""

    division: int = Field(..., ge=1, le=7, description="Wallet division number (1-7)")
    balance: float = Field(..., description="Division balance in ISK")


class CorporationWallet(BaseModel):
    """Corporation wallet with all divisions"""

    corporation_id: int = Field(..., gt=0, description="EVE corporation ID")
    corporation_name: str = Field(..., min_length=1, description="Corporation name")
    divisions: List[CorporationWalletDivision] = Field(default_factory=list, description="Wallet divisions")
    total_balance: float = Field(..., description="Total balance across all divisions")
    formatted_total: str = Field(..., description="Formatted total with ISK suffix")
