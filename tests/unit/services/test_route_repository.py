"""
Unit tests for Route Service Repository

Following TDD: Tests written first, then implement repository.
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from typing import Dict, Any, List

from src.services.route.repository import RouteRepository
from src.core.exceptions import EVECopilotError


@pytest.fixture
def mock_db_pool():
    """Create a mock DatabasePool"""
    pool = Mock()
    return pool


@pytest.fixture
def mock_connection():
    """Create a mock database connection"""
    conn = Mock()
    cursor = Mock()

    # Setup context managers
    conn.__enter__ = Mock(return_value=conn)
    conn.__exit__ = Mock(return_value=False)
    cursor.__enter__ = Mock(return_value=cursor)
    cursor.__exit__ = Mock(return_value=False)

    conn.cursor = Mock(return_value=cursor)
    return conn, cursor


class TestRouteRepositoryInit:
    """Test RouteRepository initialization"""

    def test_create_repository(self, mock_db_pool):
        """Test creating repository with DatabasePool"""
        repo = RouteRepository(db=mock_db_pool)

        assert repo._db == mock_db_pool
        assert repo._systems is None
        assert repo._graph is None
        assert repo._loaded is False

    def test_repository_requires_db(self):
        """Test that repository requires db parameter"""
        with pytest.raises(TypeError):
            RouteRepository()


class TestLoadSystems:
    """Test load_systems method"""

    def test_load_systems_success(self, mock_db_pool, mock_connection):
        """Test successfully loading systems from database"""
        conn, cursor = mock_connection
        mock_db_pool.get_connection.return_value = conn

        # Mock database response
        cursor.fetchall.return_value = [
            {
                'solarSystemID': 30000142,
                'solarSystemName': 'Jita',
                'security': 0.9458591,
                'regionID': 10000002
            },
            {
                'solarSystemID': 30002187,
                'solarSystemName': 'Amarr',
                'security': 1.0,
                'regionID': 10000043
            },
        ]

        repo = RouteRepository(db=mock_db_pool)
        systems = repo.load_systems()

        # Verify results
        assert len(systems) == 2
        assert 30000142 in systems
        assert systems[30000142]['name'] == 'Jita'
        assert systems[30000142]['security'] == 0.9458591
        assert systems[30000142]['region_id'] == 10000002

        # Verify SQL query was called
        cursor.execute.assert_called_once()
        sql = cursor.execute.call_args[0][0]
        assert 'mapSolarSystems' in sql
        assert 'solarSystemID' in sql

    def test_load_systems_caching(self, mock_db_pool, mock_connection):
        """Test that systems are cached after first load"""
        conn, cursor = mock_connection
        mock_db_pool.get_connection.return_value = conn

        cursor.fetchall.return_value = [
            {
                'solarSystemID': 30000142,
                'solarSystemName': 'Jita',
                'security': 0.95,
                'regionID': 10000002
            }
        ]

        repo = RouteRepository(db=mock_db_pool)

        # First call should query database
        systems1 = repo.load_systems()
        assert cursor.execute.call_count == 1

        # Second call should use cache
        systems2 = repo.load_systems()
        assert cursor.execute.call_count == 1  # Still 1, no new query

        # Both should return same data
        assert systems1 == systems2

    def test_load_systems_database_error(self, mock_db_pool, mock_connection):
        """Test handling database errors"""
        conn, cursor = mock_connection
        mock_db_pool.get_connection.return_value = conn

        # Simulate database error
        cursor.execute.side_effect = Exception("Database connection failed")

        repo = RouteRepository(db=mock_db_pool)

        with pytest.raises(EVECopilotError) as exc_info:
            repo.load_systems()

        assert "Failed to load systems" in str(exc_info.value)


class TestLoadJumpGraph:
    """Test load_jump_graph method"""

    def test_load_jump_graph_success(self, mock_db_pool, mock_connection):
        """Test successfully loading jump graph"""
        conn, cursor = mock_connection
        mock_db_pool.get_connection.return_value = conn

        # Mock database response (bidirectional jumps)
        cursor.fetchall.return_value = [
            {'fromSolarSystemID': 1, 'toSolarSystemID': 2},
            {'fromSolarSystemID': 2, 'toSolarSystemID': 3},
            {'fromSolarSystemID': 3, 'toSolarSystemID': 1},
        ]

        repo = RouteRepository(db=mock_db_pool)
        graph = repo.load_jump_graph()

        # Verify graph structure
        assert 1 in graph
        assert 2 in graph
        assert 3 in graph
        assert 2 in graph[1]
        assert 3 in graph[2]
        assert 1 in graph[3]

        # Verify SQL query
        cursor.execute.assert_called_once()
        sql = cursor.execute.call_args[0][0]
        assert 'mapSolarSystemJumps' in sql

    def test_load_jump_graph_caching(self, mock_db_pool, mock_connection):
        """Test that jump graph is cached"""
        conn, cursor = mock_connection
        mock_db_pool.get_connection.return_value = conn

        cursor.fetchall.return_value = [
            {'fromSolarSystemID': 1, 'toSolarSystemID': 2},
        ]

        repo = RouteRepository(db=mock_db_pool)

        # First call
        graph1 = repo.load_jump_graph()
        assert cursor.execute.call_count == 1

        # Second call should use cache
        graph2 = repo.load_jump_graph()
        assert cursor.execute.call_count == 1

        assert graph1 == graph2

    def test_load_jump_graph_database_error(self, mock_db_pool, mock_connection):
        """Test handling database errors in jump graph loading"""
        conn, cursor = mock_connection
        mock_db_pool.get_connection.return_value = conn

        cursor.execute.side_effect = Exception("Database error")

        repo = RouteRepository(db=mock_db_pool)

        with pytest.raises(EVECopilotError) as exc_info:
            repo.load_jump_graph()

        assert "Failed to load jump graph" in str(exc_info.value)


class TestGetSystemByName:
    """Test get_system_by_name method"""

    def test_get_system_by_name_exact_match(self, mock_db_pool, mock_connection):
        """Test finding system by exact name"""
        conn, cursor = mock_connection
        mock_db_pool.get_connection.return_value = conn

        cursor.fetchone.return_value = {
            'solarSystemID': 30000142,
            'solarSystemName': 'Jita',
            'security': 0.9458591,
            'regionID': 10000002
        }

        repo = RouteRepository(db=mock_db_pool)
        system = repo.get_system_by_name("Jita")

        assert system is not None
        assert system['system_id'] == 30000142
        assert system['name'] == 'Jita'
        assert system['security'] == 0.9458591
        assert system['region_id'] == 10000002

    def test_get_system_by_name_case_insensitive(self, mock_db_pool, mock_connection):
        """Test case-insensitive search"""
        conn, cursor = mock_connection
        mock_db_pool.get_connection.return_value = conn

        cursor.fetchone.return_value = {
            'solarSystemID': 30000142,
            'solarSystemName': 'Jita',
            'security': 0.95,
            'regionID': 10000002
        }

        repo = RouteRepository(db=mock_db_pool)

        # Test various cases
        system1 = repo.get_system_by_name("jita")
        system2 = repo.get_system_by_name("JITA")
        system3 = repo.get_system_by_name("JiTa")

        assert system1 is not None
        assert system2 is not None
        assert system3 is not None
        assert system1['name'] == 'Jita'

    def test_get_system_by_name_not_found(self, mock_db_pool, mock_connection):
        """Test when system is not found"""
        conn, cursor = mock_connection
        mock_db_pool.get_connection.return_value = conn

        cursor.fetchone.return_value = None

        repo = RouteRepository(db=mock_db_pool)
        system = repo.get_system_by_name("NonExistentSystem")

        assert system is None

    def test_get_system_by_name_database_error(self, mock_db_pool, mock_connection):
        """Test handling database errors"""
        conn, cursor = mock_connection
        mock_db_pool.get_connection.return_value = conn

        cursor.execute.side_effect = Exception("Database error")

        repo = RouteRepository(db=mock_db_pool)

        with pytest.raises(EVECopilotError) as exc_info:
            repo.get_system_by_name("Jita")

        assert "Failed to find system" in str(exc_info.value)


class TestSearchSystems:
    """Test search_systems method"""

    def test_search_systems_success(self, mock_db_pool, mock_connection):
        """Test searching systems by partial name"""
        conn, cursor = mock_connection
        mock_db_pool.get_connection.return_value = conn

        cursor.fetchall.return_value = [
            {
                'solarSystemID': 30000142,
                'solarSystemName': 'Jita',
                'security': 0.95,
                'regionID': 10000002
            },
            {
                'solarSystemID': 30000143,
                'solarSystemName': 'Jita IV',
                'security': 0.95,
                'regionID': 10000002
            },
        ]

        repo = RouteRepository(db=mock_db_pool)
        results = repo.search_systems("Jit", limit=10)

        assert len(results) == 2
        assert results[0]['system_id'] == 30000142
        assert results[0]['name'] == 'Jita'

    def test_search_systems_with_limit(self, mock_db_pool, mock_connection):
        """Test search with limit parameter"""
        conn, cursor = mock_connection
        mock_db_pool.get_connection.return_value = conn

        # Return more results than limit
        cursor.fetchall.return_value = [
            {'solarSystemID': i, 'solarSystemName': f'System{i}', 'security': 0.5, 'regionID': 1}
            for i in range(5)
        ]

        repo = RouteRepository(db=mock_db_pool)
        results = repo.search_systems("System", limit=3)

        # Verify LIMIT clause in SQL
        sql = cursor.execute.call_args[0][0]
        assert 'LIMIT' in sql.upper()

    def test_search_systems_case_insensitive(self, mock_db_pool, mock_connection):
        """Test case-insensitive search"""
        conn, cursor = mock_connection
        mock_db_pool.get_connection.return_value = conn

        cursor.fetchall.return_value = [
            {'solarSystemID': 1, 'solarSystemName': 'Jita', 'security': 0.95, 'regionID': 1}
        ]

        repo = RouteRepository(db=mock_db_pool)

        # Both should work
        results1 = repo.search_systems("jit")
        results2 = repo.search_systems("JIT")

        assert len(results1) > 0
        assert len(results2) > 0

    def test_search_systems_empty_result(self, mock_db_pool, mock_connection):
        """Test search with no results"""
        conn, cursor = mock_connection
        mock_db_pool.get_connection.return_value = conn

        cursor.fetchall.return_value = []

        repo = RouteRepository(db=mock_db_pool)
        results = repo.search_systems("XYZ123")

        assert len(results) == 0

    def test_search_systems_database_error(self, mock_db_pool, mock_connection):
        """Test handling database errors"""
        conn, cursor = mock_connection
        mock_db_pool.get_connection.return_value = conn

        cursor.execute.side_effect = Exception("Database error")

        repo = RouteRepository(db=mock_db_pool)

        with pytest.raises(EVECopilotError) as exc_info:
            repo.search_systems("Test")

        assert "Failed to search systems" in str(exc_info.value)


class TestLazyLoading:
    """Test lazy loading pattern"""

    def test_lazy_loading_on_first_access(self, mock_db_pool, mock_connection):
        """Test that data is loaded lazily on first access"""
        conn, cursor = mock_connection
        mock_db_pool.get_connection.return_value = conn

        cursor.fetchall.return_value = []

        repo = RouteRepository(db=mock_db_pool)

        # Initially not loaded
        assert repo._loaded is False
        assert repo._systems is None
        assert repo._graph is None

        # First access triggers load
        repo.load_systems()

        # Now should be loaded
        assert repo._systems is not None

    def test_no_reload_on_subsequent_access(self, mock_db_pool, mock_connection):
        """Test that subsequent access doesn't reload data"""
        conn, cursor = mock_connection
        mock_db_pool.get_connection.return_value = conn

        cursor.fetchall.return_value = []

        repo = RouteRepository(db=mock_db_pool)

        # Load data
        repo.load_systems()
        call_count_after_first = cursor.execute.call_count

        # Access again
        repo.load_systems()
        call_count_after_second = cursor.execute.call_count

        # Should be same (no additional query)
        assert call_count_after_first == call_count_after_second
