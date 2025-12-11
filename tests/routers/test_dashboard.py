import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_get_dashboard_opportunities():
    """Should return list of opportunities"""
    response = client.get("/api/dashboard/opportunities")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    assert len(data) <= 10  # Default limit

def test_get_dashboard_opportunities_with_limit():
    """Should respect limit parameter"""
    response = client.get("/api/dashboard/opportunities?limit=5")
    assert response.status_code == 200

    data = response.json()
    assert len(data) <= 5

def test_opportunity_structure():
    """Each opportunity should have required fields"""
    response = client.get("/api/dashboard/opportunities?limit=1")
    assert response.status_code == 200

    data = response.json()
    if len(data) > 0:
        op = data[0]
        assert 'category' in op
        assert 'type_id' in op
        assert 'name' in op
        assert 'profit' in op
        assert op['category'] in ['production', 'trade', 'war_demand']
