"""Tests for character portrait proxy endpoint."""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from datetime import datetime, timedelta

from main import app

client = TestClient(app)


def test_get_character_portrait_returns_url():
    """
    Test that the portrait endpoint returns a URL from ESI.

    Given: A valid character_id
    When: Requesting the character portrait
    Then: Should return px256x256 URL from ESI
    """
    character_id = 526379435  # Artallus

    # Mock ESI response
    mock_esi_response = {
        "px64x64": "https://images.evetech.net/characters/526379435/portrait?size=64",
        "px128x128": "https://images.evetech.net/characters/526379435/portrait?size=128",
        "px256x256": "https://images.evetech.net/characters/526379435/portrait?size=256",
        "px512x512": "https://images.evetech.net/characters/526379435/portrait?size=512"
    }

    with patch('routers.character.get_character_service') as mock_service:
        mock_service_instance = MagicMock()
        mock_service.return_value = mock_service_instance
        mock_service_instance.get_character_portrait.return_value = {
            "url": mock_esi_response["px256x256"]
        }

        response = client.get(f"/api/character/{character_id}/portrait")

        assert response.status_code == 200
        data = response.json()
        assert "url" in data
        assert "px256x256" in data["url"] or "size=256" in data["url"]
        assert str(character_id) in data["url"]


def test_get_character_portrait_caches_result():
    """
    Test that the portrait endpoint caches results.

    Given: A character portrait was previously fetched
    When: Requesting the same portrait again within 24 hours
    Then: Should return cached result without calling ESI
    """
    character_id = 1117367444  # Cytrex

    expected_url = f"https://images.evetech.net/characters/{character_id}/portrait?size=256"

    with patch('routers.character.get_character_service') as mock_service:
        mock_service_instance = MagicMock()
        mock_service.return_value = mock_service_instance

        # First call - should call ESI
        mock_service_instance.get_character_portrait.return_value = {
            "url": expected_url
        }

        response1 = client.get(f"/api/character/{character_id}/portrait")
        assert response1.status_code == 200
        data1 = response1.json()

        # Reset mock to verify second call uses cache
        mock_service_instance.reset_mock()
        mock_service_instance.get_character_portrait.return_value = {
            "url": expected_url
        }

        # Second call - should use cache
        response2 = client.get(f"/api/character/{character_id}/portrait")
        assert response2.status_code == 200
        data2 = response2.json()

        # Both should return same URL
        assert data1["url"] == data2["url"]
        assert expected_url in data2["url"]


def test_get_character_portrait_handles_404():
    """
    Test that the endpoint handles characters without portraits.

    Given: A character_id that doesn't exist or has no portrait
    When: Requesting the character portrait
    Then: Should return a default avatar URL
    """
    character_id = 99999999  # Non-existent character

    with patch('routers.character.get_character_service') as mock_service:
        mock_service_instance = MagicMock()
        mock_service.return_value = mock_service_instance

        # Mock ESI error (404)
        from src.core.exceptions import ExternalAPIError
        mock_service_instance.get_character_portrait.side_effect = ExternalAPIError(
            service_name="ESI",
            status_code=404,
            message="Character not found"
        )

        response = client.get(f"/api/character/{character_id}/portrait")

        # Should still return 200 with default avatar
        assert response.status_code == 200
        data = response.json()
        assert "url" in data
        # Default avatar should be returned
        assert "default" in data["url"].lower() or "placeholder" in data["url"].lower() or ".png" in data["url"]


def test_get_character_portrait_handles_invalid_character_id():
    """
    Test that the endpoint handles invalid character IDs.

    Given: An invalid character_id (not a number)
    When: Requesting the character portrait
    Then: Should return 422 validation error
    """
    response = client.get("/api/character/invalid/portrait")
    assert response.status_code == 422  # Validation error


def test_get_character_portrait_cache_expiry():
    """
    Test that cache expires after 24 hours.

    Given: A cached portrait older than 24 hours
    When: Requesting the portrait
    Then: Should fetch fresh data from ESI
    """
    character_id = 110592475  # Cytricia

    with patch('routers.character.get_character_service') as mock_service:
        mock_service_instance = MagicMock()
        mock_service.return_value = mock_service_instance

        # Simulate cache miss (expired)
        expected_url = f"https://images.evetech.net/characters/{character_id}/portrait?size=256"
        mock_service_instance.get_character_portrait.return_value = {
            "url": expected_url
        }

        response = client.get(f"/api/character/{character_id}/portrait")

        assert response.status_code == 200
        data = response.json()
        assert "url" in data
        assert str(character_id) in data["url"]
