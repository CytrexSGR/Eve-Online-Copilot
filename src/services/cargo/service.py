"""
Cargo Service

Business logic for cargo volume calculations and ship recommendations
"""

from math import ceil
from typing import List

from src.services.cargo.models import (
    CargoItem,
    CargoCalculation,
    CargoItemBreakdown,
    ShipRecommendations,
    ShipRecommendation,
)
from src.services.cargo.repository import CargoRepository
from src.services.cargo.constants import SHIP_CARGO


class CargoService:
    """
    Service for cargo volume calculations and ship recommendations
    """

    def __init__(self, repository: CargoRepository):
        """
        Initialize service with repository dependency

        Args:
            repository: CargoRepository instance for data access
        """
        self.repository = repository

    def calculate_cargo_volume(self, items: List[CargoItem]) -> CargoCalculation:
        """
        Calculate total cargo volume for a list of items

        Args:
            items: List of CargoItem objects with type_id and quantity

        Returns:
            CargoCalculation with total volume and item breakdown
        """
        total_volume = 0.0
        breakdown = []

        for item in items:
            # Get volume from repository
            volume = self.repository.get_item_volume(item.type_id)

            # Skip items with unknown volumes (None)
            if volume is None:
                continue

            # Calculate total volume for this item
            item_total = volume * item.quantity
            total_volume += item_total

            # Add to breakdown
            breakdown.append(
                CargoItemBreakdown(
                    type_id=item.type_id,
                    quantity=item.quantity,
                    unit_volume=volume,
                    total_volume=item_total,
                )
            )

        return CargoCalculation(
            total_volume_m3=round(total_volume, 2),
            total_volume_formatted=self._format_volume(total_volume),
            items=breakdown,
        )

    def recommend_ship(
        self, volume_m3: float, prefer_safe: bool = True
    ) -> ShipRecommendations:
        """
        Recommend ship based on cargo volume

        Args:
            volume_m3: Total cargo volume in cubic meters
            prefer_safe: Whether to prioritize safe transport options

        Returns:
            ShipRecommendations with best option, safe option, and all alternatives
        """
        recommendations = []

        # Find all ships that can fit the volume in one trip
        for ship_type, info in SHIP_CARGO.items():
            capacity = info["capacity"]

            if capacity >= volume_m3:
                trips = 1
                fill_percent = round((volume_m3 / capacity) * 100, 1)
                excess_capacity = capacity - volume_m3

                recommendations.append(
                    ShipRecommendation(
                        ship_type=ship_type,
                        ship_name=info["name"],
                        capacity=capacity,
                        trips=trips,
                        fill_percent=fill_percent,
                        excess_capacity=excess_capacity,
                    )
                )

        # Sort by capacity (smallest that fits first)
        recommendations.sort(key=lambda x: x.capacity)

        # If no ship fits in one trip, recommend freighter with multiple trips
        if not recommendations:
            freighter_capacity = SHIP_CARGO["freighter"]["capacity"]
            trips = ceil(volume_m3 / freighter_capacity)
            total_capacity = freighter_capacity * trips
            fill_percent = round((volume_m3 / total_capacity) * 100, 1)
            excess_capacity = total_capacity - volume_m3

            recommendations.append(
                ShipRecommendation(
                    ship_type="freighter",
                    ship_name=SHIP_CARGO["freighter"]["name"],
                    capacity=freighter_capacity,
                    trips=trips,
                    fill_percent=fill_percent,
                    excess_capacity=excess_capacity,
                )
            )

        # Best recommendation (smallest that fits)
        best = recommendations[0]

        # Find safe options (blockade runner or deep space transport)
        safe_options = [
            r
            for r in recommendations
            if r.ship_type in ["blockade_runner", "deep_space_transport"]
        ]
        safe_option = safe_options[0] if safe_options else None

        return ShipRecommendations(
            volume_m3=round(volume_m3, 2),
            volume_formatted=self._format_volume(volume_m3),
            recommended=best,
            safe_option=safe_option,
            all_options=recommendations[:5],  # Top 5 options
        )

    def _format_volume(self, volume: float) -> str:
        """
        Format volume for human-readable display

        Args:
            volume: Volume in cubic meters

        Returns:
            Formatted string (e.g., "1.50M m³", "5.0K m³", "250 m³")
        """
        if volume >= 1_000_000:
            return f"{volume / 1_000_000:.2f}M m³"
        if volume >= 1_000:
            return f"{volume / 1_000:.1f}K m³"
        return f"{volume:.0f} m³"
