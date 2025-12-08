"""
Route Service Models

Pydantic models for route calculation and navigation in EVE Online.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict


class SystemInfo(BaseModel):
    """
    Solar system information

    Basic system data including location, security status, and trade hub info.
    """
    system_id: int = Field(..., description="Solar system ID")
    name: str = Field(..., description="System name")
    security: float = Field(..., description="Security status")
    region_id: int = Field(..., description="Region ID")
    is_trade_hub: bool = Field(default=False, description="Whether system is a trade hub")
    hub_name: Optional[str] = Field(default=None, description="Trade hub name if applicable")

    @field_validator('system_id')
    @classmethod
    def validate_system_id(cls, v: int) -> int:
        """Validate system_id is positive"""
        if v <= 0:
            raise ValueError('system_id must be greater than 0')
        return v

    @field_validator('security')
    @classmethod
    def validate_security(cls, v: float) -> float:
        """Validate security is between -1.0 and 1.0"""
        if v < -1.0 or v > 1.0:
            raise ValueError('security must be between -1.0 and 1.0')
        return v


class RouteSystemInfo(SystemInfo):
    """
    System information within a route

    Extends SystemInfo with route-specific data like jump number and danger scores.
    """
    jump_number: int = Field(..., description="Jump number in route (0-indexed)")
    danger_score: float = Field(default=0.0, description="Danger score based on kill activity")
    kills_24h: int = Field(default=0, description="Number of kills in last 24 hours")

    @field_validator('jump_number')
    @classmethod
    def validate_jump_number(cls, v: int) -> int:
        """Validate jump_number is non-negative"""
        if v < 0:
            raise ValueError('jump_number must be >= 0')
        return v


class TravelTime(BaseModel):
    """
    Travel time calculation for a route

    Estimated travel time based on jumps, align time, and warp time.
    """
    jumps: int = Field(..., description="Number of jumps")
    estimated_seconds: int = Field(..., description="Estimated travel time in seconds")
    estimated_minutes: float = Field(..., description="Estimated travel time in minutes")
    formatted: str = Field(..., description="Formatted time string")

    @field_validator('jumps')
    @classmethod
    def validate_jumps(cls, v: int) -> int:
        """Validate jumps is non-negative"""
        if v < 0:
            raise ValueError('jumps must be >= 0')
        return v


class RouteResult(BaseModel):
    """
    Complete route calculation result

    Contains the full route with all systems and travel time estimate.
    """
    systems: List[RouteSystemInfo] = Field(..., description="Systems in route")
    total_jumps: int = Field(..., description="Total number of jumps")
    travel_time: TravelTime = Field(..., description="Travel time estimate")


class RouteLeg(BaseModel):
    """
    Single leg of a multi-hub route

    Represents one segment of a journey between two systems.
    """
    model_config = ConfigDict(populate_by_name=True)

    from_name: str = Field(..., alias="from", description="Starting system name")
    to_name: str = Field(..., alias="to", description="Destination system name")
    jumps: int = Field(..., description="Number of jumps in this leg")
    systems: Optional[List[Dict[str, Any]]] = Field(default=None, description="Detailed system list")


class MultiHubRoute(BaseModel):
    """
    Multi-hub route calculation result

    Optimal route visiting multiple trade hubs using TSP optimization.
    """
    model_config = ConfigDict(populate_by_name=True)

    total_jumps: int = Field(..., description="Total jumps for entire route")
    route_legs: List[RouteLeg] = Field(..., alias="route", description="Individual route legs")
    order: List[str] = Field(..., description="Order of systems visited")
    return_home: bool = Field(..., description="Whether route returns to starting system")


class HubDistance(BaseModel):
    """
    Distance to a single trade hub

    Contains jump count, time estimate, and reachability status.
    """
    jumps: Optional[int] = Field(..., description="Number of jumps (None if unreachable)")
    time: str = Field(..., description="Formatted time or 'No HighSec route'")
    reachable: bool = Field(..., description="Whether hub is reachable via HighSec")


class HubDistances(BaseModel):
    """
    Distances from a system to all trade hubs

    Result of hub distance calculation showing all available routes.
    """
    from_system: str = Field(..., description="Starting system name")
    from_system_id: int = Field(..., description="Starting system ID")
    distances: Dict[str, HubDistance] = Field(..., description="Distance to each hub")
    error: Optional[str] = Field(default=None, description="Error message if system not found")


class RouteWithDanger(BaseModel):
    """
    Route with danger analysis overlay

    Route calculation with kill activity and danger scores for each system.
    """
    route: List[RouteSystemInfo] = Field(..., description="Route with danger scores")
    total_danger_score: float = Field(..., description="Total danger score for route")
    average_danger: float = Field(..., description="Average danger per system")
    dangerous_systems: List[Dict[str, Any]] = Field(..., description="Systems with high danger")
    warning: bool = Field(..., description="Whether route has dangerous systems")
