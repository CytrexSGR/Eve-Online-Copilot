"""Tests for auth service OAuth2 business logic."""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.core.exceptions import AuthenticationError, ValidationError


@pytest.fixture
def mock_repository():
    """Mock auth repository."""
    return Mock()


@pytest.fixture
def mock_esi_client():
    """Mock ESI client."""
    return Mock()


@pytest.fixture
def mock_config():
    """Mock configuration."""
    config = Mock()
    config.eve_client_id = "test_client_id"
    config.eve_client_secret = "test_client_secret"
    config.eve_callback_url = "http://localhost:8000/callback"
    return config


@pytest.fixture
def mock_requests():
    """Mock requests module."""
    with patch("src.services.auth.service.requests") as mock:
        yield mock


class TestGetAuthUrl:
    """Tests for get_auth_url method."""

    def test_generate_auth_url_success(self, mock_repository, mock_esi_client, mock_config):
        """Test successful auth URL generation with PKCE."""
        from src.services.auth.service import AuthService

        service = AuthService(mock_repository, mock_esi_client, mock_config)

        result = service.get_auth_url()

        # Verify AuthUrl model returned
        assert result.auth_url.startswith("https://login.eveonline.com/v2/oauth/authorize")
        assert "client_id=test_client_id" in result.auth_url
        assert "code_challenge=" in result.auth_url
        assert "code_challenge_method=S256" in result.auth_url
        assert "response_type=code" in result.auth_url
        assert result.state is not None
        assert len(result.state) > 0
        assert result.scopes is not None
        assert isinstance(result.scopes, list)

        # Verify PKCE state was saved
        mock_repository.save_pkce_state.assert_called_once()
        call_args = mock_repository.save_pkce_state.call_args
        state = call_args[0][0]
        state_data = call_args[0][1]

        assert state == result.state
        assert "code_verifier" in state_data
        assert "created_at" in state_data
        assert "expires_at" in state_data
        # Code verifier should be ~86 chars (64 bytes base64url)
        assert len(state_data["code_verifier"]) >= 43

    def test_pkce_code_challenge_generation(self, mock_repository, mock_esi_client, mock_config):
        """Test PKCE code challenge is properly generated."""
        from src.services.auth.service import AuthService
        import hashlib
        import base64

        service = AuthService(mock_repository, mock_esi_client, mock_config)
        result = service.get_auth_url()

        # Extract code_verifier from saved state
        saved_state_data = mock_repository.save_pkce_state.call_args[0][1]
        code_verifier = saved_state_data["code_verifier"]

        # Calculate expected code_challenge
        expected_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).decode().rstrip('=')

        # Verify challenge is in URL
        assert f"code_challenge={expected_challenge}" in result.auth_url

    def test_scopes_included_in_url(self, mock_repository, mock_esi_client, mock_config):
        """Test ESI scopes are included in auth URL."""
        from src.services.auth.service import AuthService

        service = AuthService(mock_repository, mock_esi_client, mock_config)
        result = service.get_auth_url()

        assert "scope=" in result.auth_url
        assert len(result.scopes) > 0


class TestHandleCallback:
    """Tests for handle_callback method."""

    def test_callback_success(self, mock_repository, mock_esi_client, mock_config, mock_requests):
        """Test successful OAuth2 callback handling."""
        from src.services.auth.service import AuthService

        # Mock repository responses
        mock_repository.get_pkce_state.return_value = {
            "code_verifier": "test_verifier_123",
            "created_at": time.time(),
            "expires_at": time.time() + 600
        }

        # Mock token exchange response
        mock_token_response = Mock()
        mock_token_response.status_code = 200
        mock_token_response.json.return_value = {
            "access_token": "test_access_token",
            "refresh_token": "test_refresh_token",
            "expires_in": 1200
        }
        mock_requests.post.return_value = mock_token_response

        # Mock token verification response
        mock_verify_response = Mock()
        mock_verify_response.status_code = 200
        mock_verify_response.json.return_value = {
            "CharacterID": 123456,
            "CharacterName": "Test Character",
            "Scopes": "esi-wallet.read_character_wallet.v1 esi-assets.read_assets.v1"
        }
        mock_requests.get.return_value = mock_verify_response

        service = AuthService(mock_repository, mock_esi_client, mock_config)
        result = service.handle_callback(code="test_code", state="test_state")

        # Verify CharacterAuthLegacy returned
        assert result.character_id == 123456
        assert result.character_name == "Test Character"
        assert result.access_token == "test_access_token"
        assert result.refresh_token == "test_refresh_token"
        assert len(result.scopes) == 2

        # Verify state was retrieved and deleted
        mock_repository.get_pkce_state.assert_called_once_with("test_state")
        mock_repository.delete_pkce_state.assert_called_once_with("test_state")

        # Verify character auth was saved
        mock_repository.save_character_auth.assert_called_once()

    def test_callback_invalid_state(self, mock_repository, mock_esi_client, mock_config):
        """Test callback with invalid state raises error."""
        from src.services.auth.service import AuthService

        mock_repository.get_pkce_state.return_value = None

        service = AuthService(mock_repository, mock_esi_client, mock_config)

        with pytest.raises(AuthenticationError) as exc_info:
            service.handle_callback(code="test_code", state="invalid_state")

        assert "Invalid or expired state" in str(exc_info.value)

    def test_callback_expired_state(self, mock_repository, mock_esi_client, mock_config):
        """Test callback with expired state raises error."""
        from src.services.auth.service import AuthService

        # State expired 10 seconds ago
        mock_repository.get_pkce_state.return_value = {
            "code_verifier": "test_verifier",
            "created_at": time.time() - 700,
            "expires_at": time.time() - 10
        }

        service = AuthService(mock_repository, mock_esi_client, mock_config)

        with pytest.raises(AuthenticationError) as exc_info:
            service.handle_callback(code="test_code", state="expired_state")

        assert "expired" in str(exc_info.value).lower()

    def test_callback_token_exchange_failure(self, mock_repository, mock_esi_client, mock_config, mock_requests):
        """Test callback when token exchange fails."""
        from src.services.auth.service import AuthService

        mock_repository.get_pkce_state.return_value = {
            "code_verifier": "test_verifier",
            "created_at": time.time(),
            "expires_at": time.time() + 600
        }

        # Mock failed token exchange
        mock_token_response = Mock()
        mock_token_response.status_code = 400
        mock_token_response.text = "invalid_grant"
        mock_requests.post.return_value = mock_token_response

        service = AuthService(mock_repository, mock_esi_client, mock_config)

        with pytest.raises(AuthenticationError) as exc_info:
            service.handle_callback(code="bad_code", state="test_state")

        assert "Token exchange failed" in str(exc_info.value)

    def test_callback_token_verification_failure(self, mock_repository, mock_esi_client, mock_config, mock_requests):
        """Test callback when token verification fails."""
        from src.services.auth.service import AuthService

        mock_repository.get_pkce_state.return_value = {
            "code_verifier": "test_verifier",
            "created_at": time.time(),
            "expires_at": time.time() + 600
        }

        # Mock successful token exchange
        mock_token_response = Mock()
        mock_token_response.status_code = 200
        mock_token_response.json.return_value = {
            "access_token": "test_token",
            "refresh_token": "test_refresh",
            "expires_in": 1200
        }

        # Mock failed verification
        mock_verify_response = Mock()
        mock_verify_response.status_code = 401
        mock_verify_response.text = "Unauthorized"

        mock_requests.post.return_value = mock_token_response
        mock_requests.get.return_value = mock_verify_response

        service = AuthService(mock_repository, mock_esi_client, mock_config)

        with pytest.raises(AuthenticationError) as exc_info:
            service.handle_callback(code="test_code", state="test_state")

        assert "Token verification failed" in str(exc_info.value)

    def test_callback_uses_basic_auth(self, mock_repository, mock_esi_client, mock_config, mock_requests):
        """Test callback uses Basic Auth header when secret is configured."""
        from src.services.auth.service import AuthService
        import base64

        mock_repository.get_pkce_state.return_value = {
            "code_verifier": "test_verifier",
            "created_at": time.time(),
            "expires_at": time.time() + 600
        }

        mock_token_response = Mock()
        mock_token_response.status_code = 200
        mock_token_response.json.return_value = {
            "access_token": "test_token",
            "refresh_token": "test_refresh",
            "expires_in": 1200
        }

        mock_verify_response = Mock()
        mock_verify_response.status_code = 200
        mock_verify_response.json.return_value = {
            "CharacterID": 123,
            "CharacterName": "Test",
            "Scopes": ""
        }

        mock_requests.post.return_value = mock_token_response
        mock_requests.get.return_value = mock_verify_response

        service = AuthService(mock_repository, mock_esi_client, mock_config)
        service.handle_callback(code="test_code", state="test_state")

        # Verify Basic Auth header was used
        call_args = mock_requests.post.call_args
        headers = call_args[1]["headers"]
        assert "Authorization" in headers
        assert headers["Authorization"].startswith("Basic ")


class TestRefreshToken:
    """Tests for refresh_token method."""

    def test_refresh_token_success(self, mock_repository, mock_esi_client, mock_config, mock_requests):
        """Test successful token refresh."""
        from src.services.auth.service import AuthService

        # Mock stored auth
        mock_repository.get_character_auth.return_value = {
            "character_id": 123,
            "character_name": "Test",
            "refresh_token": "old_refresh_token",
            "access_token": "old_access_token",
            "expires_at": time.time() - 100,
            "scopes": ["scope1"],
            "updated_at": datetime.now().isoformat()
        }

        # Mock refresh response
        mock_refresh_response = Mock()
        mock_refresh_response.status_code = 200
        mock_refresh_response.json.return_value = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "expires_in": 1200
        }
        mock_requests.post.return_value = mock_refresh_response

        service = AuthService(mock_repository, mock_esi_client, mock_config)
        result = service.refresh_token(character_id=123)

        # Verify OAuthTokenResponse returned
        assert result.access_token == "new_access_token"
        assert result.refresh_token == "new_refresh_token"
        assert result.expires_at > time.time()

        # Verify updated auth was saved
        mock_repository.save_character_auth.assert_called_once()

    def test_refresh_token_character_not_found(self, mock_repository, mock_esi_client, mock_config):
        """Test refresh when character auth not found."""
        from src.services.auth.service import AuthService

        mock_repository.get_character_auth.return_value = None

        service = AuthService(mock_repository, mock_esi_client, mock_config)

        with pytest.raises(AuthenticationError) as exc_info:
            service.refresh_token(character_id=999)

        assert "No token found" in str(exc_info.value)

    def test_refresh_token_no_refresh_token(self, mock_repository, mock_esi_client, mock_config):
        """Test refresh when refresh token is missing."""
        from src.services.auth.service import AuthService

        mock_repository.get_character_auth.return_value = {
            "character_id": 123,
            "access_token": "token",
            "refresh_token": None,
            "expires_at": time.time()
        }

        service = AuthService(mock_repository, mock_esi_client, mock_config)

        with pytest.raises(AuthenticationError) as exc_info:
            service.refresh_token(character_id=123)

        assert "No refresh token available" in str(exc_info.value)

    def test_refresh_token_api_failure(self, mock_repository, mock_esi_client, mock_config, mock_requests):
        """Test refresh when API call fails."""
        from src.services.auth.service import AuthService

        mock_repository.get_character_auth.return_value = {
            "character_id": 123,
            "refresh_token": "refresh_token",
            "access_token": "access_token",
            "expires_at": time.time()
        }

        # Mock failed refresh
        mock_refresh_response = Mock()
        mock_refresh_response.status_code = 400
        mock_refresh_response.text = "invalid_grant"
        mock_requests.post.return_value = mock_refresh_response

        service = AuthService(mock_repository, mock_esi_client, mock_config)

        with pytest.raises(AuthenticationError) as exc_info:
            service.refresh_token(character_id=123)

        assert "Token refresh failed" in str(exc_info.value)


class TestVerifyToken:
    """Tests for verify_token method."""

    def test_verify_token_success(self, mock_repository, mock_esi_client, mock_config, mock_requests):
        """Test successful token verification."""
        from src.services.auth.service import AuthService

        mock_repository.get_character_auth.return_value = {
            "character_id": 123,
            "access_token": "valid_token",
            "refresh_token": "refresh",
            "expires_at": time.time() + 1000
        }

        # Mock verify response
        mock_verify_response = Mock()
        mock_verify_response.status_code = 200
        mock_verify_response.json.return_value = {
            "CharacterID": 123,
            "CharacterName": "Test Character",
            "ExpiresOn": "2025-12-08T12:00:00",
            "Scopes": "scope1 scope2"
        }
        mock_requests.get.return_value = mock_verify_response

        service = AuthService(mock_repository, mock_esi_client, mock_config)
        result = service.verify_token(character_id=123)

        # Verify TokenVerifyResponse returned
        assert result.CharacterID == 123
        assert result.CharacterName == "Test Character"
        assert "scope1" in result.Scopes

    def test_verify_token_not_found(self, mock_repository, mock_esi_client, mock_config):
        """Test verify when character not found."""
        from src.services.auth.service import AuthService

        mock_repository.get_character_auth.return_value = None

        service = AuthService(mock_repository, mock_esi_client, mock_config)

        with pytest.raises(AuthenticationError) as exc_info:
            service.verify_token(character_id=999)

        assert "No token found" in str(exc_info.value)

    def test_verify_token_invalid(self, mock_repository, mock_esi_client, mock_config, mock_requests):
        """Test verify with invalid token."""
        from src.services.auth.service import AuthService

        mock_repository.get_character_auth.return_value = {
            "character_id": 123,
            "access_token": "invalid_token",
            "refresh_token": "refresh",
            "expires_at": time.time() + 1000
        }

        # Mock failed verification
        mock_verify_response = Mock()
        mock_verify_response.status_code = 401
        mock_verify_response.text = "Unauthorized"
        mock_requests.get.return_value = mock_verify_response

        service = AuthService(mock_repository, mock_esi_client, mock_config)

        with pytest.raises(AuthenticationError) as exc_info:
            service.verify_token(character_id=123)

        assert "Token verification failed" in str(exc_info.value)


class TestGetAuthenticatedCharacters:
    """Tests for get_authenticated_characters method."""

    def test_get_all_characters(self, mock_repository, mock_esi_client, mock_config):
        """Test getting all authenticated characters."""
        from src.services.auth.service import AuthService

        mock_repository.get_all_character_auths.return_value = [
            {
                "character_id": 123,
                "character_name": "Character 1",
                "access_token": "token1",
                "refresh_token": "refresh1",
                "expires_at": time.time() + 1000,
                "scopes": ["scope1"],
                "updated_at": datetime.now().isoformat()
            },
            {
                "character_id": 456,
                "character_name": "Character 2",
                "access_token": "token2",
                "refresh_token": "refresh2",
                "expires_at": time.time() - 100,  # Expired
                "scopes": ["scope2"],
                "updated_at": datetime.now().isoformat()
            }
        ]

        service = AuthService(mock_repository, mock_esi_client, mock_config)
        results = service.get_authenticated_characters()

        # Verify list of CharacterAuthSummary returned
        assert len(results) == 2
        assert results[0].character_id == 123
        assert results[0].is_valid is True
        assert results[1].character_id == 456
        assert results[1].is_valid is False

    def test_get_characters_empty(self, mock_repository, mock_esi_client, mock_config):
        """Test getting characters when none exist."""
        from src.services.auth.service import AuthService

        mock_repository.get_all_character_auths.return_value = []

        service = AuthService(mock_repository, mock_esi_client, mock_config)
        results = service.get_authenticated_characters()

        assert len(results) == 0
        assert isinstance(results, list)


class TestLogoutCharacter:
    """Tests for logout_character method."""

    def test_logout_success(self, mock_repository, mock_esi_client, mock_config):
        """Test successful character logout."""
        from src.services.auth.service import AuthService

        mock_repository.delete_character_auth.return_value = True

        service = AuthService(mock_repository, mock_esi_client, mock_config)
        result = service.logout_character(character_id=123)

        assert result is True
        mock_repository.delete_character_auth.assert_called_once_with(123)

    def test_logout_not_found(self, mock_repository, mock_esi_client, mock_config):
        """Test logout when character not found."""
        from src.services.auth.service import AuthService

        mock_repository.delete_character_auth.return_value = False

        service = AuthService(mock_repository, mock_esi_client, mock_config)
        result = service.logout_character(character_id=999)

        assert result is False
