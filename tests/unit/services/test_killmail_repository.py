"""Tests for Killmail Repository."""

from datetime import date, timedelta
from unittest.mock import MagicMock, call, patch

import pytest

from src.services.killmail.models import ItemLoss, ShipLoss
from src.services.killmail.repository import KillmailRepository


@pytest.fixture
def mock_db_pool():
    """Create a mock database pool."""
    pool = MagicMock()
    pool.get_connection = MagicMock()
    return pool


@pytest.fixture
def repository(mock_db_pool):
    """Create a KillmailRepository with mock database."""
    return KillmailRepository(db=mock_db_pool)


class TestKillmailRepository:
    """Test KillmailRepository class."""

    def test_initialization(self, mock_db_pool):
        """Test repository initialization."""
        repo = KillmailRepository(db=mock_db_pool)
        assert repo.db == mock_db_pool

    def test_store_ship_losses_empty_list(self, repository, mock_db_pool):
        """Test storing empty ship losses list."""
        result = repository.store_ship_losses([])
        assert result == 0
        mock_db_pool.get_connection.assert_not_called()

    @patch('src.services.killmail.repository.execute_values')
    def test_store_ship_losses_success(self, mock_execute_values, repository, mock_db_pool):
        """Test successfully storing ship losses."""
        # Setup
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_db_pool.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db_pool.get_connection.return_value.__exit__ = MagicMock(return_value=False)

        losses = [
            ShipLoss(
                system_id=30001234,
                region_id=10000002,
                ship_type_id=648,
                loss_count=5,
                date=date(2025, 12, 7)
            ),
            ShipLoss(
                system_id=30001235,
                region_id=10000002,
                ship_type_id=649,
                loss_count=3,
                date=date(2025, 12, 7),
                total_value_destroyed=500000000.0
            )
        ]

        # Execute
        result = repository.store_ship_losses(losses)

        # Verify
        assert result == 2
        mock_execute_values.assert_called_once()
        call_args = mock_execute_values.call_args

        # Check the values passed
        values = call_args[0][2]
        assert len(values) == 2
        assert values[0] == (30001234, 10000002, 648, 5, date(2025, 12, 7), 0.0)
        assert values[1] == (30001235, 10000002, 649, 3, date(2025, 12, 7), 500000000.0)

        # Check commit was called
        mock_conn.commit.assert_called_once()

    def test_store_item_losses_empty_list(self, repository, mock_db_pool):
        """Test storing empty item losses list."""
        result = repository.store_item_losses([])
        assert result == 0
        mock_db_pool.get_connection.assert_not_called()

    @patch('src.services.killmail.repository.execute_values')
    def test_store_item_losses_success(self, mock_execute_values, repository, mock_db_pool):
        """Test successfully storing item losses."""
        # Setup
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_db_pool.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db_pool.get_connection.return_value.__exit__ = MagicMock(return_value=False)

        losses = [
            ItemLoss(
                region_id=10000002,
                item_type_id=456,
                loss_count=100,
                date=date(2025, 12, 7)
            ),
            ItemLoss(
                region_id=10000002,
                item_type_id=457,
                loss_count=50,
                date=date(2025, 12, 7)
            )
        ]

        # Execute
        result = repository.store_item_losses(losses)

        # Verify
        assert result == 2
        mock_execute_values.assert_called_once()
        call_args = mock_execute_values.call_args

        values = call_args[0][2]
        assert len(values) == 2
        assert values[0] == (10000002, 456, 100, date(2025, 12, 7))
        assert values[1] == (10000002, 457, 50, date(2025, 12, 7))

        mock_conn.commit.assert_called_once()

    def test_get_ship_losses_all_regions(self, repository, mock_db_pool):
        """Test getting ship losses for all regions."""
        # Setup
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {
                'system_id': 30001234,
                'region_id': 10000002,
                'ship_type_id': 648,
                'loss_count': 5,
                'date': date(2025, 12, 7),
                'total_value_destroyed': 100000000.0
            }
        ]
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_db_pool.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db_pool.get_connection.return_value.__exit__ = MagicMock(return_value=False)

        # Execute
        result = repository.get_ship_losses(region_id=None, system_id=None, days=7)

        # Verify
        assert len(result) == 1
        assert result[0]['system_id'] == 30001234
        assert result[0]['ship_type_id'] == 648
        mock_cursor.execute.assert_called_once()

    def test_get_ship_losses_specific_region(self, repository, mock_db_pool):
        """Test getting ship losses for specific region."""
        # Setup
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_db_pool.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db_pool.get_connection.return_value.__exit__ = MagicMock(return_value=False)

        # Execute
        result = repository.get_ship_losses(region_id=10000002, system_id=None, days=7)

        # Verify
        assert len(result) == 0
        mock_cursor.execute.assert_called_once()
        # Check that region_id was in the query parameters
        call_args = mock_cursor.execute.call_args
        assert 10000002 in call_args[0][1]

    def test_get_ship_losses_specific_system(self, repository, mock_db_pool):
        """Test getting ship losses for specific system."""
        # Setup
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_db_pool.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db_pool.get_connection.return_value.__exit__ = MagicMock(return_value=False)

        # Execute
        result = repository.get_ship_losses(region_id=None, system_id=30001234, days=7)

        # Verify
        assert len(result) == 0
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args
        assert 30001234 in call_args[0][1]

    def test_get_item_losses_all_regions(self, repository, mock_db_pool):
        """Test getting item losses for all regions."""
        # Setup
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {
                'region_id': 10000002,
                'item_type_id': 456,
                'loss_count': 100,
                'date': date(2025, 12, 7)
            }
        ]
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_db_pool.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db_pool.get_connection.return_value.__exit__ = MagicMock(return_value=False)

        # Execute
        result = repository.get_item_losses(region_id=None, days=7)

        # Verify
        assert len(result) == 1
        assert result[0]['item_type_id'] == 456
        mock_cursor.execute.assert_called_once()

    def test_get_item_losses_specific_region(self, repository, mock_db_pool):
        """Test getting item losses for specific region."""
        # Setup
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_db_pool.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db_pool.get_connection.return_value.__exit__ = MagicMock(return_value=False)

        # Execute
        result = repository.get_item_losses(region_id=10000002, days=7)

        # Verify
        assert len(result) == 0
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args
        assert 10000002 in call_args[0][1]

    def test_get_system_danger_score(self, repository, mock_db_pool):
        """Test getting danger score for a system."""
        # Setup
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {'kill_count': 42}
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_db_pool.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db_pool.get_connection.return_value.__exit__ = MagicMock(return_value=False)

        # Execute
        result = repository.get_system_danger_score(system_id=30001234, days=7)

        # Verify
        assert result['system_id'] == 30001234
        assert result['kill_count'] == 42
        assert result['days'] == 7
        mock_cursor.execute.assert_called_once()

    def test_get_system_danger_score_no_data(self, repository, mock_db_pool):
        """Test getting danger score for system with no data."""
        # Setup
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_db_pool.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db_pool.get_connection.return_value.__exit__ = MagicMock(return_value=False)

        # Execute
        result = repository.get_system_danger_score(system_id=30001234, days=7)

        # Verify
        assert result['system_id'] == 30001234
        assert result['kill_count'] == 0
        assert result['days'] == 7

    def test_cleanup_old_data(self, repository, mock_db_pool):
        """Test cleanup of old data."""
        # Setup
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 10
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_db_pool.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db_pool.get_connection.return_value.__exit__ = MagicMock(return_value=False)

        # Execute
        result = repository.cleanup_old_data(days=30)

        # Verify
        assert result == 20  # 10 ship + 10 item deletions
        assert mock_cursor.execute.call_count == 2  # Two DELETE queries
        mock_conn.commit.assert_called_once()

    def test_get_system_region_map(self, repository, mock_db_pool):
        """Test getting system to region mapping."""
        # Setup
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {'solar_system_id': 30001234, 'region_id': 10000002},
            {'solar_system_id': 30001235, 'region_id': 10000002}
        ]
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_db_pool.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db_pool.get_connection.return_value.__exit__ = MagicMock(return_value=False)

        # Execute
        result = repository.get_system_region_map()

        # Verify
        assert result == {30001234: 10000002, 30001235: 10000002}
        mock_cursor.execute.assert_called_once()
