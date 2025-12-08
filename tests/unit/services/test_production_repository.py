"""
Tests for Production Repository
Following TDD - tests written first, then implementation
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from contextlib import contextmanager
from src.services.production.repository import ProductionRepository
from src.core.exceptions import EVECopilotError


@pytest.fixture
def mock_db_pool():
    """Create a mock DatabasePool"""
    pool = Mock()
    return pool


@pytest.fixture
def mock_connection():
    """Create a mock database connection with cursor"""
    conn = Mock()
    cursor = Mock()
    conn.cursor.return_value.__enter__ = Mock(return_value=cursor)
    conn.cursor.return_value.__exit__ = Mock(return_value=False)
    return conn, cursor


@pytest.fixture
def repository(mock_db_pool):
    """Create ProductionRepository with mocked pool"""
    return ProductionRepository(mock_db_pool)


class TestProductionRepositoryInit:
    """Test repository initialization"""

    def test_repository_init(self, mock_db_pool):
        """Test repository initializes with database pool"""
        repo = ProductionRepository(mock_db_pool)
        assert repo.db == mock_db_pool


class TestGetBlueprintForProduct:
    """Test get_blueprint_for_product method"""

    def test_blueprint_found(self, repository, mock_db_pool, mock_connection):
        """Test finding a blueprint for a product"""
        conn, cursor = mock_connection
        mock_db_pool.get_connection.return_value.__enter__ = Mock(return_value=conn)
        mock_db_pool.get_connection.return_value.__exit__ = Mock(return_value=False)

        # Mock cursor to return blueprint_id
        cursor.fetchone.return_value = (1010,)

        result = repository.get_blueprint_for_product(648)

        assert result == 1010
        cursor.execute.assert_called_once()
        # Verify SQL query structure
        sql_call = cursor.execute.call_args[0][0]
        assert "industryActivityProducts" in sql_call
        assert "productTypeID" in sql_call
        assert "activityID" in sql_call

    def test_blueprint_not_found(self, repository, mock_db_pool, mock_connection):
        """Test when no blueprint exists for a product"""
        conn, cursor = mock_connection
        mock_db_pool.get_connection.return_value.__enter__ = Mock(return_value=conn)
        mock_db_pool.get_connection.return_value.__exit__ = Mock(return_value=False)

        cursor.fetchone.return_value = None

        result = repository.get_blueprint_for_product(999999)

        assert result is None

    def test_blueprint_database_error(self, repository, mock_db_pool, mock_connection):
        """Test handling database errors"""
        conn, cursor = mock_connection
        mock_db_pool.get_connection.return_value.__enter__ = Mock(return_value=conn)
        mock_db_pool.get_connection.return_value.__exit__ = Mock(return_value=False)

        cursor.execute.side_effect = Exception("Database connection failed")

        with pytest.raises(EVECopilotError) as exc_info:
            repository.get_blueprint_for_product(648)

        assert "Database error" in str(exc_info.value)


class TestGetBlueprintMaterials:
    """Test get_blueprint_materials method"""

    def test_materials_found(self, repository, mock_db_pool, mock_connection):
        """Test retrieving materials for a blueprint"""
        conn, cursor = mock_connection
        mock_db_pool.get_connection.return_value.__enter__ = Mock(return_value=conn)
        mock_db_pool.get_connection.return_value.__exit__ = Mock(return_value=False)

        # Mock materials: Tritanium, Pyerite
        cursor.fetchall.return_value = [
            (34, 1000),
            (35, 500),
            (36, 250)
        ]

        result = repository.get_blueprint_materials(1010)

        assert len(result) == 3
        assert result[0] == (34, 1000)
        assert result[1] == (35, 500)
        assert result[2] == (36, 250)
        cursor.execute.assert_called_once()
        sql_call = cursor.execute.call_args[0][0]
        assert "industryActivityMaterials" in sql_call
        assert "activityID" in sql_call

    def test_materials_empty(self, repository, mock_db_pool, mock_connection):
        """Test when blueprint has no materials"""
        conn, cursor = mock_connection
        mock_db_pool.get_connection.return_value.__enter__ = Mock(return_value=conn)
        mock_db_pool.get_connection.return_value.__exit__ = Mock(return_value=False)

        cursor.fetchall.return_value = []

        result = repository.get_blueprint_materials(1010)

        assert result == []

    def test_materials_database_error(self, repository, mock_db_pool, mock_connection):
        """Test handling database errors"""
        conn, cursor = mock_connection
        mock_db_pool.get_connection.return_value.__enter__ = Mock(return_value=conn)
        mock_db_pool.get_connection.return_value.__exit__ = Mock(return_value=False)

        cursor.execute.side_effect = Exception("Query failed")

        with pytest.raises(EVECopilotError) as exc_info:
            repository.get_blueprint_materials(1010)

        assert "Database error" in str(exc_info.value)


class TestGetOutputQuantity:
    """Test get_output_quantity method"""

    def test_output_quantity_found(self, repository, mock_db_pool, mock_connection):
        """Test retrieving output quantity"""
        conn, cursor = mock_connection
        mock_db_pool.get_connection.return_value.__enter__ = Mock(return_value=conn)
        mock_db_pool.get_connection.return_value.__exit__ = Mock(return_value=False)

        cursor.fetchone.return_value = (10,)

        result = repository.get_output_quantity(1010, 648)

        assert result == 10
        cursor.execute.assert_called_once()
        sql_call = cursor.execute.call_args[0][0]
        assert "industryActivityProducts" in sql_call
        assert "quantity" in sql_call

    def test_output_quantity_not_found(self, repository, mock_db_pool, mock_connection):
        """Test when output quantity is not found (defaults to 1)"""
        conn, cursor = mock_connection
        mock_db_pool.get_connection.return_value.__enter__ = Mock(return_value=conn)
        mock_db_pool.get_connection.return_value.__exit__ = Mock(return_value=False)

        cursor.fetchone.return_value = None

        result = repository.get_output_quantity(1010, 648)

        assert result == 1

    def test_output_quantity_database_error(self, repository, mock_db_pool, mock_connection):
        """Test handling database errors"""
        conn, cursor = mock_connection
        mock_db_pool.get_connection.return_value.__enter__ = Mock(return_value=conn)
        mock_db_pool.get_connection.return_value.__exit__ = Mock(return_value=False)

        cursor.execute.side_effect = Exception("Query failed")

        with pytest.raises(EVECopilotError) as exc_info:
            repository.get_output_quantity(1010, 648)

        assert "Database error" in str(exc_info.value)


class TestGetBaseProductionTime:
    """Test get_base_production_time method"""

    def test_production_time_found(self, repository, mock_db_pool, mock_connection):
        """Test retrieving production time"""
        conn, cursor = mock_connection
        mock_db_pool.get_connection.return_value.__enter__ = Mock(return_value=conn)
        mock_db_pool.get_connection.return_value.__exit__ = Mock(return_value=False)

        cursor.fetchone.return_value = (3600,)

        result = repository.get_base_production_time(1010)

        assert result == 3600
        cursor.execute.assert_called_once()
        sql_call = cursor.execute.call_args[0][0]
        assert "industryActivity" in sql_call
        assert "time" in sql_call

    def test_production_time_not_found(self, repository, mock_db_pool, mock_connection):
        """Test when production time is not found (defaults to 0)"""
        conn, cursor = mock_connection
        mock_db_pool.get_connection.return_value.__enter__ = Mock(return_value=conn)
        mock_db_pool.get_connection.return_value.__exit__ = Mock(return_value=False)

        cursor.fetchone.return_value = None

        result = repository.get_base_production_time(1010)

        assert result == 0

    def test_production_time_database_error(self, repository, mock_db_pool, mock_connection):
        """Test handling database errors"""
        conn, cursor = mock_connection
        mock_db_pool.get_connection.return_value.__enter__ = Mock(return_value=conn)
        mock_db_pool.get_connection.return_value.__exit__ = Mock(return_value=False)

        cursor.execute.side_effect = Exception("Query failed")

        with pytest.raises(EVECopilotError) as exc_info:
            repository.get_base_production_time(1010)

        assert "Database error" in str(exc_info.value)


class TestGetItemName:
    """Test get_item_name method"""

    def test_item_name_found(self, repository, mock_db_pool, mock_connection):
        """Test retrieving item name"""
        conn, cursor = mock_connection
        mock_db_pool.get_connection.return_value.__enter__ = Mock(return_value=conn)
        mock_db_pool.get_connection.return_value.__exit__ = Mock(return_value=False)

        cursor.fetchone.return_value = ("Hornet I",)

        result = repository.get_item_name(648)

        assert result == "Hornet I"
        cursor.execute.assert_called_once()
        sql_call = cursor.execute.call_args[0][0]
        assert "invTypes" in sql_call or "typeName" in sql_call

    def test_item_name_not_found(self, repository, mock_db_pool, mock_connection):
        """Test when item name is not found"""
        conn, cursor = mock_connection
        mock_db_pool.get_connection.return_value.__enter__ = Mock(return_value=conn)
        mock_db_pool.get_connection.return_value.__exit__ = Mock(return_value=False)

        cursor.fetchone.return_value = None

        result = repository.get_item_name(999999)

        assert result is None

    def test_item_name_database_error(self, repository, mock_db_pool, mock_connection):
        """Test handling database errors"""
        conn, cursor = mock_connection
        mock_db_pool.get_connection.return_value.__enter__ = Mock(return_value=conn)
        mock_db_pool.get_connection.return_value.__exit__ = Mock(return_value=False)

        cursor.execute.side_effect = Exception("Query failed")

        with pytest.raises(EVECopilotError) as exc_info:
            repository.get_item_name(648)

        assert "Database error" in str(exc_info.value)


class TestRepositoryIntegration:
    """Test repository with realistic scenarios"""

    def test_complete_workflow(self, repository, mock_db_pool, mock_connection):
        """Test a complete production workflow"""
        conn, cursor = mock_connection
        mock_db_pool.get_connection.return_value.__enter__ = Mock(return_value=conn)
        mock_db_pool.get_connection.return_value.__exit__ = Mock(return_value=False)

        # Step 1: Find blueprint
        cursor.fetchone.return_value = (1010,)
        blueprint_id = repository.get_blueprint_for_product(648)
        assert blueprint_id == 1010

        # Step 2: Get materials
        cursor.fetchall.return_value = [(34, 1000), (35, 500)]
        materials = repository.get_blueprint_materials(blueprint_id)
        assert len(materials) == 2

        # Step 3: Get output quantity
        cursor.fetchone.return_value = (10,)
        output_qty = repository.get_output_quantity(blueprint_id, 648)
        assert output_qty == 10

        # Step 4: Get production time
        cursor.fetchone.return_value = (3600,)
        prod_time = repository.get_base_production_time(blueprint_id)
        assert prod_time == 3600

        # Step 5: Get item names
        cursor.fetchone.return_value = ("Hornet I",)
        item_name = repository.get_item_name(648)
        assert item_name == "Hornet I"
