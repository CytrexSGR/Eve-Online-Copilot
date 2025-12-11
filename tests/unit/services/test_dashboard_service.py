import pytest
from src.services.dashboard_service import DashboardService

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
