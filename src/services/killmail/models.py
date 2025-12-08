"""Killmail Service Models."""

from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, Optional, Tuple


@dataclass
class ShipLoss:
    """Represents a ship loss aggregated by system/ship type/date."""

    system_id: int
    region_id: int
    ship_type_id: int
    loss_count: int
    date: date
    total_value_destroyed: float = 0.0

    def __post_init__(self):
        """Validate ship loss data."""
        if self.loss_count <= 0:
            raise ValueError("loss_count must be positive")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'system_id': self.system_id,
            'region_id': self.region_id,
            'ship_type_id': self.ship_type_id,
            'loss_count': self.loss_count,
            'date': self.date,
            'total_value_destroyed': self.total_value_destroyed
        }

    def __eq__(self, other):
        """Check equality."""
        if not isinstance(other, ShipLoss):
            return False
        return (
            self.system_id == other.system_id and
            self.region_id == other.region_id and
            self.ship_type_id == other.ship_type_id and
            self.loss_count == other.loss_count and
            self.date == other.date and
            self.total_value_destroyed == other.total_value_destroyed
        )


@dataclass
class ItemLoss:
    """Represents an item loss aggregated by region/item type/date."""

    region_id: int
    item_type_id: int
    loss_count: int
    date: date

    def __post_init__(self):
        """Validate item loss data."""
        if self.loss_count <= 0:
            raise ValueError("loss_count must be positive")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'region_id': self.region_id,
            'item_type_id': self.item_type_id,
            'loss_count': self.loss_count,
            'date': self.date
        }

    def __eq__(self, other):
        """Check equality."""
        if not isinstance(other, ItemLoss):
            return False
        return (
            self.region_id == other.region_id and
            self.item_type_id == other.item_type_id and
            self.loss_count == other.loss_count and
            self.date == other.date
        )


@dataclass
class KillmailStats:
    """Statistics for processed killmails."""

    total_kills: int
    ships_destroyed: int
    items_lost: int
    isk_destroyed: float
    date_range: Tuple[date, date]

    def __post_init__(self):
        """Validate killmail stats."""
        if self.total_kills < 0:
            raise ValueError("total_kills must be non-negative")
        if self.ships_destroyed < 0:
            raise ValueError("ships_destroyed must be non-negative")
        if self.items_lost < 0:
            raise ValueError("items_lost must be non-negative")
        if self.isk_destroyed < 0:
            raise ValueError("isk_destroyed must be non-negative")

        start, end = self.date_range
        if end < start:
            raise ValueError("date_range end must be >= start")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'total_kills': self.total_kills,
            'ships_destroyed': self.ships_destroyed,
            'items_lost': self.items_lost,
            'isk_destroyed': self.isk_destroyed,
            'date_range': {
                'start': self.date_range[0],
                'end': self.date_range[1]
            }
        }


@dataclass
class DailyArchive:
    """Information about a daily killmail archive."""

    date: date
    url: str
    filename: str
    file_size: int

    def __post_init__(self):
        """Validate daily archive data."""
        if self.file_size < 0:
            raise ValueError("file_size must be non-negative")

    @property
    def file_size_mb(self) -> float:
        """Get file size in megabytes."""
        return self.file_size / (1024 * 1024)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'date': self.date,
            'url': self.url,
            'filename': self.filename,
            'file_size': self.file_size,
            'file_size_mb': self.file_size_mb
        }
