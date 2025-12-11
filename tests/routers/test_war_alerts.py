import pytest
from fastapi.testclient import TestClient
from main import app
from datetime import datetime

client = TestClient(app)

def test_get_war_alerts_returns_recent_events():
    """Should return formatted alerts from high-value kills"""
    response = client.get("/api/war/alerts")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)

    # Verify alert structure if there are any alerts
    if len(data) > 0:
        alert = data[0]
        assert 'priority' in alert
        assert 'message' in alert
        assert 'timestamp' in alert
        assert 'value' in alert

        # Priority should be either 'high' or 'medium'
        assert alert['priority'] in ['high', 'medium']

        # Value should be a number (ISK)
        assert isinstance(alert['value'], (int, float))
        assert alert['value'] > 0

        # Message should be a string
        assert isinstance(alert['message'], str)
        assert len(alert['message']) > 0

def test_get_war_alerts_limits_to_5():
    """Should default to limit of 5 alerts"""
    response = client.get("/api/war/alerts")
    assert response.status_code == 200

    data = response.json()
    assert len(data) <= 5

def test_get_war_alerts_includes_timestamps():
    """Timestamps should be in ISO format"""
    response = client.get("/api/war/alerts")
    assert response.status_code == 200

    data = response.json()

    # Verify timestamp format if there are any alerts
    if len(data) > 0:
        alert = data[0]
        assert 'timestamp' in alert

        # Should be parseable as ISO datetime
        timestamp_str = alert['timestamp']
        try:
            parsed = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            assert isinstance(parsed, datetime)
        except ValueError:
            pytest.fail(f"Timestamp '{timestamp_str}' is not valid ISO format")

def test_get_war_alerts_custom_limit():
    """Should respect custom limit parameter"""
    response = client.get("/api/war/alerts?limit=3")
    assert response.status_code == 200

    data = response.json()
    assert len(data) <= 3

def test_get_war_alerts_priority_classification():
    """Should classify alerts by value (high >5B, medium >1B)"""
    response = client.get("/api/war/alerts?limit=10")
    assert response.status_code == 200

    data = response.json()

    # Verify priority classification if there are alerts
    for alert in data:
        value = alert['value']
        priority = alert['priority']

        if value > 5_000_000_000:
            assert priority == 'high', f"Value {value} should be high priority"
        elif value > 1_000_000_000:
            assert priority in ['high', 'medium'], f"Value {value} should be high or medium priority"
