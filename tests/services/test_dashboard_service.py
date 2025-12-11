import pytest
from unittest.mock import MagicMock, patch
from services.dashboard_service import DashboardService

@pytest.fixture
def dashboard_service():
    return DashboardService()

def test_get_opportunities_returns_list(dashboard_service):
    """Should return a list of opportunities"""
    result = dashboard_service.get_opportunities()
    assert isinstance(result, list)

def test_get_opportunities_includes_production(dashboard_service):
    """Should include production opportunities"""
    result = dashboard_service.get_opportunities()
    production_ops = [op for op in result if op['category'] == 'production']
    assert len(production_ops) > 0

def test_get_opportunities_includes_trade(dashboard_service):
    """Should include trade opportunities"""
    result = dashboard_service.get_opportunities()
    trade_ops = [op for op in result if op['category'] == 'trade']
    assert len(trade_ops) > 0

def test_get_opportunities_includes_war_demand(dashboard_service):
    """Should include war demand opportunities"""
    result = dashboard_service.get_opportunities()
    war_ops = [op for op in result if op['category'] == 'war_demand']
    assert len(war_ops) > 0

def test_opportunities_sorted_by_priority(dashboard_service):
    """Should sort by category priority: production > trade > war_demand"""
    result = dashboard_service.get_opportunities()
    categories = [op['category'] for op in result[:10]]

    # Production should appear before trade and war_demand
    if 'production' in categories and 'trade' in categories:
        assert categories.index('production') < categories.index('trade')

def test_production_opportunities_from_database(dashboard_service):
    """Should fetch production opportunities from manufacturing_opportunities table"""
    with patch('services.dashboard_service.get_db_connection') as mock_db:
        # Create mocks for connection and cursor using MagicMock (handles context managers)
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            (645, 'Thorax', 5000000, 25.5, 2, 3000000, 8000000),  # type_id, name, profit, roi, difficulty, material_cost, sell_price
            (638, 'Vexor', 3000000, 20.0, 1, 2000000, 5000000)
        ]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        mock_db.return_value.__enter__.return_value = mock_conn

        result = dashboard_service._get_production_opportunities()

        assert len(result) == 2
        assert result[0]['type_id'] == 645
        assert result[0]['name'] == 'Thorax'
        assert result[0]['profit'] == 5000000
        assert result[0]['category'] == 'production'
