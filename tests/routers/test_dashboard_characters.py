import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_get_character_summaries():
    """Should return summaries for all configured characters"""
    response = client.get("/api/dashboard/characters/summary")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 3  # 3 characters configured

def test_character_summary_structure():
    """Each character should have required fields"""
    response = client.get("/api/dashboard/characters/summary")
    assert response.status_code == 200

    data = response.json()
    if len(data) > 0:
        char = data[0]
        assert 'character_id' in char
        assert 'name' in char
        assert 'isk_balance' in char
        assert 'location' in char
        assert 'active_jobs' in char

def test_get_portfolio_total():
    """Should return total ISK across all characters"""
    response = client.get("/api/dashboard/characters/portfolio")
    assert response.status_code == 200

    data = response.json()
    assert 'total_isk' in data
    assert 'character_count' in data
    assert isinstance(data['total_isk'], (int, float))
