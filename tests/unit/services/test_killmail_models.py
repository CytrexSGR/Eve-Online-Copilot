"""Tests for Killmail Service Models."""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from src.services.killmail.models import (
    DailyArchive,
    ItemLoss,
    KillmailStats,
    ShipLoss,
)


class TestShipLoss:
    """Test ShipLoss model."""

    def test_ship_loss_creation(self):
        """Test creating a ShipLoss instance."""
        loss = ShipLoss(
            system_id=30001234,
            region_id=10000002,
            ship_type_id=648,
            loss_count=5,
            date=date(2025, 12, 7)
        )

        assert loss.system_id == 30001234
        assert loss.region_id == 10000002
        assert loss.ship_type_id == 648
        assert loss.loss_count == 5
        assert loss.date == date(2025, 12, 7)

    def test_ship_loss_with_isk_value(self):
        """Test ShipLoss with ISK value."""
        loss = ShipLoss(
            system_id=30001234,
            region_id=10000002,
            ship_type_id=648,
            loss_count=3,
            date=date(2025, 12, 7),
            total_value_destroyed=500000000.0
        )

        assert loss.total_value_destroyed == 500000000.0

    def test_ship_loss_validation_negative_count(self):
        """Test that negative loss count raises ValueError."""
        with pytest.raises(ValueError, match="loss_count must be positive"):
            ShipLoss(
                system_id=30001234,
                region_id=10000002,
                ship_type_id=648,
                loss_count=-1,
                date=date(2025, 12, 7)
            )

    def test_ship_loss_validation_zero_count(self):
        """Test that zero loss count raises ValueError."""
        with pytest.raises(ValueError, match="loss_count must be positive"):
            ShipLoss(
                system_id=30001234,
                region_id=10000002,
                ship_type_id=648,
                loss_count=0,
                date=date(2025, 12, 7)
            )

    def test_ship_loss_to_dict(self):
        """Test converting ShipLoss to dict."""
        loss = ShipLoss(
            system_id=30001234,
            region_id=10000002,
            ship_type_id=648,
            loss_count=5,
            date=date(2025, 12, 7),
            total_value_destroyed=1000000.0
        )

        result = loss.to_dict()

        assert result == {
            'system_id': 30001234,
            'region_id': 10000002,
            'ship_type_id': 648,
            'loss_count': 5,
            'date': date(2025, 12, 7),
            'total_value_destroyed': 1000000.0
        }

    def test_ship_loss_equality(self):
        """Test ShipLoss equality comparison."""
        loss1 = ShipLoss(
            system_id=30001234,
            region_id=10000002,
            ship_type_id=648,
            loss_count=5,
            date=date(2025, 12, 7)
        )
        loss2 = ShipLoss(
            system_id=30001234,
            region_id=10000002,
            ship_type_id=648,
            loss_count=5,
            date=date(2025, 12, 7)
        )

        assert loss1 == loss2


class TestItemLoss:
    """Test ItemLoss model."""

    def test_item_loss_creation(self):
        """Test creating an ItemLoss instance."""
        loss = ItemLoss(
            region_id=10000002,
            item_type_id=456,
            loss_count=100,
            date=date(2025, 12, 7)
        )

        assert loss.region_id == 10000002
        assert loss.item_type_id == 456
        assert loss.loss_count == 100
        assert loss.date == date(2025, 12, 7)

    def test_item_loss_validation_negative_count(self):
        """Test that negative loss count raises ValueError."""
        with pytest.raises(ValueError, match="loss_count must be positive"):
            ItemLoss(
                region_id=10000002,
                item_type_id=456,
                loss_count=-5,
                date=date(2025, 12, 7)
            )

    def test_item_loss_to_dict(self):
        """Test converting ItemLoss to dict."""
        loss = ItemLoss(
            region_id=10000002,
            item_type_id=456,
            loss_count=100,
            date=date(2025, 12, 7)
        )

        result = loss.to_dict()

        assert result == {
            'region_id': 10000002,
            'item_type_id': 456,
            'loss_count': 100,
            'date': date(2025, 12, 7)
        }

    def test_item_loss_equality(self):
        """Test ItemLoss equality comparison."""
        loss1 = ItemLoss(
            region_id=10000002,
            item_type_id=456,
            loss_count=100,
            date=date(2025, 12, 7)
        )
        loss2 = ItemLoss(
            region_id=10000002,
            item_type_id=456,
            loss_count=100,
            date=date(2025, 12, 7)
        )

        assert loss1 == loss2


class TestKillmailStats:
    """Test KillmailStats model."""

    def test_killmail_stats_creation(self):
        """Test creating a KillmailStats instance."""
        stats = KillmailStats(
            total_kills=1500,
            ships_destroyed=1200,
            items_lost=50000,
            isk_destroyed=1500000000000.0,
            date_range=(date(2025, 12, 1), date(2025, 12, 7))
        )

        assert stats.total_kills == 1500
        assert stats.ships_destroyed == 1200
        assert stats.items_lost == 50000
        assert stats.isk_destroyed == 1500000000000.0
        assert stats.date_range == (date(2025, 12, 1), date(2025, 12, 7))

    def test_killmail_stats_validation_negative_values(self):
        """Test that negative values raise ValueError."""
        with pytest.raises(ValueError, match="total_kills must be non-negative"):
            KillmailStats(
                total_kills=-1,
                ships_destroyed=0,
                items_lost=0,
                isk_destroyed=0.0,
                date_range=(date(2025, 12, 1), date(2025, 12, 7))
            )

    def test_killmail_stats_validation_invalid_date_range(self):
        """Test that invalid date range raises ValueError."""
        with pytest.raises(ValueError, match="date_range end must be >= start"):
            KillmailStats(
                total_kills=100,
                ships_destroyed=100,
                items_lost=1000,
                isk_destroyed=1000000.0,
                date_range=(date(2025, 12, 7), date(2025, 12, 1))
            )

    def test_killmail_stats_to_dict(self):
        """Test converting KillmailStats to dict."""
        stats = KillmailStats(
            total_kills=1500,
            ships_destroyed=1200,
            items_lost=50000,
            isk_destroyed=1500000000000.0,
            date_range=(date(2025, 12, 1), date(2025, 12, 7))
        )

        result = stats.to_dict()

        assert result == {
            'total_kills': 1500,
            'ships_destroyed': 1200,
            'items_lost': 50000,
            'isk_destroyed': 1500000000000.0,
            'date_range': {
                'start': date(2025, 12, 1),
                'end': date(2025, 12, 7)
            }
        }


class TestDailyArchive:
    """Test DailyArchive model."""

    def test_daily_archive_creation(self):
        """Test creating a DailyArchive instance."""
        archive = DailyArchive(
            date=date(2025, 12, 7),
            url="https://data.everef.net/killmails/2025/killmails-2025-12-07.tar.bz2",
            filename="killmails-2025-12-07.tar.bz2",
            file_size=52428800
        )

        assert archive.date == date(2025, 12, 7)
        assert archive.url == "https://data.everef.net/killmails/2025/killmails-2025-12-07.tar.bz2"
        assert archive.filename == "killmails-2025-12-07.tar.bz2"
        assert archive.file_size == 52428800

    def test_daily_archive_validation_negative_file_size(self):
        """Test that negative file size raises ValueError."""
        with pytest.raises(ValueError, match="file_size must be non-negative"):
            DailyArchive(
                date=date(2025, 12, 7),
                url="https://data.everef.net/killmails/2025/killmails-2025-12-07.tar.bz2",
                filename="killmails-2025-12-07.tar.bz2",
                file_size=-1
            )

    def test_daily_archive_to_dict(self):
        """Test converting DailyArchive to dict."""
        archive = DailyArchive(
            date=date(2025, 12, 7),
            url="https://data.everef.net/killmails/2025/killmails-2025-12-07.tar.bz2",
            filename="killmails-2025-12-07.tar.bz2",
            file_size=52428800
        )

        result = archive.to_dict()

        assert result == {
            'date': date(2025, 12, 7),
            'url': 'https://data.everef.net/killmails/2025/killmails-2025-12-07.tar.bz2',
            'filename': 'killmails-2025-12-07.tar.bz2',
            'file_size': 52428800,
            'file_size_mb': 50.0
        }

    def test_daily_archive_file_size_mb(self):
        """Test file_size_mb property calculation."""
        archive = DailyArchive(
            date=date(2025, 12, 7),
            url="https://data.everef.net/killmails/2025/killmails-2025-12-07.tar.bz2",
            filename="killmails-2025-12-07.tar.bz2",
            file_size=104857600  # 100 MB
        )

        assert archive.file_size_mb == 100.0
