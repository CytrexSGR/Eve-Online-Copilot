"""
Tests for Cargo Repository

Following TDD approach - tests written before implementation
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from psycopg2.extras import RealDictRow

from src.services.cargo.repository import CargoRepository
from src.core.exceptions import EVECopilotError


class TestCargoRepository:
    """Test CargoRepository"""

    @pytest.fixture
    def mock_db_pool(self):
        """Create a mock database pool"""
        return Mock()

    @pytest.fixture
    def repo(self, mock_db_pool):
        """Create a repository instance with mock db"""
        return CargoRepository(db=mock_db_pool)

    def setup_mock_db(self, mock_db_pool, fetchone_result):
        """Helper to setup database mocks with context managers"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_cursor.fetchone.return_value = fetchone_result
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)

        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)

        mock_db_pool.get_connection.return_value = mock_conn

        return mock_conn, mock_cursor

    def test_init(self, mock_db_pool):
        """Test repository initialization"""
        repo = CargoRepository(db=mock_db_pool)
        assert repo.db == mock_db_pool

    def test_get_item_volume_success(self, repo, mock_db_pool):
        """Test getting item volume successfully"""
        # Setup mock
        mock_conn, mock_cursor = self.setup_mock_db(mock_db_pool, {'volume': 0.01})

        # Execute
        volume = repo.get_item_volume(34)

        # Assert
        assert volume == 0.01
        mock_cursor.execute.assert_called_once_with(
            'SELECT "volume" FROM "invTypes" WHERE "typeID" = %s',
            (34,)
        )

    def test_get_item_volume_not_found(self, repo, mock_db_pool):
        """Test getting volume for non-existent item"""
        # Setup mock
        self.setup_mock_db(mock_db_pool, None)

        # Execute
        volume = repo.get_item_volume(999999)

        # Assert
        assert volume is None

    def test_get_item_volume_zero_volume(self, repo, mock_db_pool):
        """Test getting item with zero volume"""
        # Setup mock
        self.setup_mock_db(mock_db_pool, {'volume': 0.0})

        # Execute
        volume = repo.get_item_volume(34)

        # Assert
        assert volume == 0.0

    def test_get_item_volume_null_volume(self, repo, mock_db_pool):
        """Test getting item with NULL volume in database"""
        # Setup mock
        self.setup_mock_db(mock_db_pool, {'volume': None})

        # Execute
        volume = repo.get_item_volume(34)

        # Assert
        assert volume is None

    def test_get_item_volume_large_volume(self, repo, mock_db_pool):
        """Test getting item with large volume"""
        # Setup mock
        self.setup_mock_db(mock_db_pool, {'volume': 1500000.0})

        # Execute
        volume = repo.get_item_volume(648)  # Capital Ship Assembly Array

        # Assert
        assert volume == 1500000.0

    def test_get_item_volume_uses_real_dict_cursor(self, repo, mock_db_pool):
        """Test that repository uses RealDictCursor"""
        # Setup mock
        mock_conn, mock_cursor = self.setup_mock_db(mock_db_pool, {'volume': 0.01})

        # Execute
        repo.get_item_volume(34)

        # Assert - verify cursor_factory was passed
        from psycopg2.extras import RealDictCursor
        mock_conn.cursor.assert_called_once_with(cursor_factory=RealDictCursor)

    def test_get_item_volume_database_error(self, repo, mock_db_pool):
        """Test handling database errors"""
        # Setup mock to raise exception
        mock_db_pool.get_connection.side_effect = Exception("Database connection failed")

        # Execute and assert
        with pytest.raises(EVECopilotError) as exc_info:
            repo.get_item_volume(34)

        assert "Failed to get item volume" in str(exc_info.value)

    def test_get_item_volume_query_error(self, repo, mock_db_pool):
        """Test handling query execution errors"""
        # Setup mock
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        # Simulate query error
        mock_cursor.execute.side_effect = Exception("Query execution failed")
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)

        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)

        mock_db_pool.get_connection.return_value = mock_conn

        # Execute and assert
        with pytest.raises(EVECopilotError) as exc_info:
            repo.get_item_volume(34)

        assert "Failed to get item volume" in str(exc_info.value)

    def test_get_item_volume_invalid_type_id(self, repo, mock_db_pool):
        """Test with invalid type_id (edge case - repository should still query)"""
        # Setup mock
        mock_conn, mock_cursor = self.setup_mock_db(mock_db_pool, None)

        # Execute with negative type_id
        volume = repo.get_item_volume(-1)

        # Assert - should return None (not found)
        assert volume is None
        mock_cursor.execute.assert_called_once()

    def test_get_item_volume_decimal_result(self, repo, mock_db_pool):
        """Test handling decimal volume values"""
        # Setup mock
        self.setup_mock_db(mock_db_pool, {'volume': 0.015})

        # Execute
        volume = repo.get_item_volume(34)

        # Assert
        assert isinstance(volume, float)
        assert volume == 0.015

    def test_multiple_queries(self, repo, mock_db_pool):
        """Test multiple consecutive queries"""
        # Setup mock
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        # Different results for different calls
        mock_cursor.fetchone.side_effect = [
            {'volume': 0.01},
            {'volume': 0.02},
            None,
        ]
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)

        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)

        mock_db_pool.get_connection.return_value = mock_conn

        # Execute multiple queries
        vol1 = repo.get_item_volume(34)
        vol2 = repo.get_item_volume(35)
        vol3 = repo.get_item_volume(999999)

        # Assert
        assert vol1 == 0.01
        assert vol2 == 0.02
        assert vol3 is None
        assert mock_cursor.execute.call_count == 3
