"""Unit tests for ESI Client."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from requests.exceptions import RequestException, Timeout

from src.core.exceptions import ExternalAPIError
from src.integrations.esi.client import ESIClient


class TestESIClient:
    """Test suite for ESI Client."""

    @pytest.fixture
    def mock_settings(self):
        """Mock settings for testing."""
        settings = MagicMock()
        settings.esi_base_url = "https://esi.evetech.net/latest"
        settings.esi_user_agent = "EVE-Co-Pilot/1.2.0"
        return settings

    @pytest.fixture
    def esi_client(self, mock_settings):
        """Create ESI client instance for testing."""
        with patch("src.integrations.esi.client.get_settings", return_value=mock_settings):
            return ESIClient()

    def test_initialization(self, esi_client):
        """Test ESI client initializes correctly."""
        assert esi_client.base_url == "https://esi.evetech.net/latest"
        assert esi_client.session is not None
        assert esi_client.session.headers["User-Agent"] == "EVE-Co-Pilot/1.2.0"
        assert esi_client.session.headers["Accept"] == "application/json"

    @patch("src.integrations.esi.client.requests.Session.get")
    def test_get_market_prices_success(self, mock_get, esi_client):
        """Test successful market prices API call."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"type_id": 34, "adjusted_price": 50000.0, "average_price": 55000.0},
            {"type_id": 35, "adjusted_price": 60000.0, "average_price": 65000.0},
            {"type_id": 36, "adjusted_price": 70000.0},  # Missing average_price
        ]
        mock_get.return_value = mock_response

        # Act
        result = esi_client.get_market_prices()

        # Assert
        assert len(result) == 3
        assert result[0]["type_id"] == 34
        assert result[0]["adjusted_price"] == 50000.0
        assert result[0]["average_price"] == 55000.0
        assert result[2]["type_id"] == 36
        assert "average_price" not in result[2] or result[2].get("average_price") is None

        # Verify correct API call
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert call_args[0][0] == "https://esi.evetech.net/latest/markets/prices/"
        assert call_args[1]["params"] == {"datasource": "tranquility"}
        assert call_args[1]["timeout"] == 60

    @patch("src.integrations.esi.client.requests.Session.get")
    def test_get_market_prices_api_error(self, mock_get, esi_client):
        """Test API error handling."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_get.return_value = mock_response

        # Act & Assert
        with pytest.raises(ExternalAPIError) as exc_info:
            esi_client.get_market_prices()

        assert "ESI" in str(exc_info.value)
        assert "500" in str(exc_info.value)

    @patch("src.integrations.esi.client.requests.Session.get")
    def test_get_market_prices_timeout(self, mock_get, esi_client):
        """Test timeout handling."""
        # Arrange
        mock_get.side_effect = Timeout("Request timed out")

        # Act & Assert
        with pytest.raises(ExternalAPIError) as exc_info:
            esi_client.get_market_prices()

        assert "ESI" in str(exc_info.value)
        assert "timeout" in str(exc_info.value).lower()

    @patch("src.integrations.esi.client.requests.Session.get")
    def test_get_market_prices_request_exception(self, mock_get, esi_client):
        """Test general request exception handling."""
        # Arrange
        mock_get.side_effect = RequestException("Connection error")

        # Act & Assert
        with pytest.raises(ExternalAPIError) as exc_info:
            esi_client.get_market_prices()

        assert "ESI" in str(exc_info.value)
        assert "Connection error" in str(exc_info.value)

    @patch("src.integrations.esi.client.requests.Session.get")
    def test_get_market_prices_empty_response(self, mock_get, esi_client):
        """Test empty response handling."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        # Act
        result = esi_client.get_market_prices()

        # Assert
        assert result == []

    @patch("src.integrations.esi.client.requests.Session.get")
    def test_get_market_prices_invalid_json(self, mock_get, esi_client):
        """Test invalid JSON response handling."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_response

        # Act & Assert
        with pytest.raises(ExternalAPIError) as exc_info:
            esi_client.get_market_prices()

        assert "ESI" in str(exc_info.value)

    @patch("src.integrations.esi.client.requests.Session.get")
    def test_get_market_prices_with_custom_config(self, mock_get):
        """Test ESI client with custom configuration."""
        # Arrange
        custom_base_url = "https://custom.esi.url/v1"
        custom_user_agent = "CustomAgent/2.0"

        custom_settings = MagicMock()
        custom_settings.esi_base_url = custom_base_url
        custom_settings.esi_user_agent = custom_user_agent

        with patch("src.integrations.esi.client.get_settings", return_value=custom_settings):
            client = ESIClient()

            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = [{"type_id": 34, "adjusted_price": 50000.0}]
            mock_get.return_value = mock_response

            # Act
            result = client.get_market_prices()

            # Assert
            assert len(result) == 1
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert call_args[0][0] == f"{custom_base_url}/markets/prices/"
