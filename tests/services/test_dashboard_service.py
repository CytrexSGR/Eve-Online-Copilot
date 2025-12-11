import pytest
from unittest.mock import MagicMock, patch
from services.dashboard_service import DashboardService

@pytest.fixture
def dashboard_service():
    service = DashboardService()
    # Clear cache before each test to ensure fresh state
    service.cache.clear()
    return service

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
    with patch('services.dashboard_service.get_best_arbitrage_opportunities') as mock_arb:
        with patch('services.dashboard_service.get_db_connection') as mock_db:
            # Mock database call for production opportunities
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = []
            mock_conn = MagicMock()
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            mock_db.return_value.__enter__.return_value = mock_conn

            # Mock arbitrage function
            mock_arb.return_value = [{
                'type_id': 645,
                'type_name': 'Thorax',
                'buy_region_id': 10000002,
                'buy_region_name': 'the_forge',
                'sell_region_id': 10000032,
                'sell_region_name': 'sinq_laison',
                'buy_price': 20000000,
                'sell_price': 25000000,
                'profit': 5000000,
                'roi': 25.0
            }]
            result = dashboard_service.get_opportunities()
            trade_ops = [op for op in result if op['category'] == 'trade']
            assert len(trade_ops) > 0

def test_get_opportunities_includes_war_demand(dashboard_service):
    """Should include war demand opportunities"""
    with patch('services.dashboard_service.DashboardService._get_war_demand_opportunities') as mock_war:
        with patch('services.dashboard_service.get_db_connection') as mock_db:
            with patch('services.dashboard_service.get_best_arbitrage_opportunities') as mock_arb:
                # Mock database call for production opportunities
                mock_cursor = MagicMock()
                mock_cursor.fetchall.return_value = []
                mock_conn = MagicMock()
                mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
                mock_db.return_value.__enter__.return_value = mock_conn

                # Mock arbitrage (empty)
                mock_arb.return_value = []

                # Mock war demand
                mock_war.return_value = [{
                    'category': 'war_demand',
                    'type_id': 16236,
                    'name': 'Gila',
                    'profit': 10000000,
                    'roi': 35.0
                }]
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

def test_trade_opportunities_from_arbitrage(dashboard_service):
    """Should calculate arbitrage opportunities between trade hubs"""
    with patch('services.dashboard_service.get_best_arbitrage_opportunities') as mock_arbitrage:
        mock_arbitrage.return_value = [
            {
                'type_id': 645,
                'type_name': 'Thorax',
                'buy_region_id': 10000002,
                'buy_region_name': 'The Forge',
                'sell_region_id': 10000032,
                'sell_region_name': 'Sinq Laison',
                'buy_price': 20000000,
                'sell_price': 25000000,
                'profit': 5000000,
                'roi': 25.0
            }
        ]

        result = dashboard_service._get_trade_opportunities()

        assert len(result) == 1
        assert result[0]['category'] == 'trade'
        assert result[0]['profit'] == 5000000

def test_war_demand_opportunities_from_analyzer(dashboard_service):
    """Should fetch war demand opportunities from war analyzer"""
    with patch('services.dashboard_service.war_analyzer.war_analyzer') as mock_war:
        mock_war.get_demand_opportunities.return_value = [
            {
                'type_id': 16236,
                'type_name': 'Gila',
                'region_id': 10000032,
                'region_name': 'Sinq Laison',
                'destroyed_count': 150,
                'market_stock': 20,
                'estimated_profit': 10000000
            }
        ]

        result = dashboard_service._get_war_demand_opportunities()

        assert len(result) == 1
        assert result[0]['category'] == 'war_demand'
        assert result[0]['type_id'] == 16236
