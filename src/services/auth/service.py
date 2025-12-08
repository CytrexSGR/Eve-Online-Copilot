"""Auth service - OAuth2 business logic layer."""

import time
import secrets
import hashlib
import base64
from typing import List, Optional, Protocol
from urllib.parse import urlencode
from datetime import datetime

import requests

from src.services.auth.models import (
    AuthUrl,
    CharacterAuth,
    CharacterAuthLegacy,
    CharacterAuthSummary,
    OAuthToken,
    OAuthTokenResponse,
    TokenVerifyResponse,
)
from src.core.exceptions import AuthenticationError, ValidationError


# EVE SSO Constants
EVE_SSO_AUTH_URL = "https://login.eveonline.com/v2/oauth/authorize"
EVE_SSO_TOKEN_URL = "https://login.eveonline.com/v2/oauth/token"
EVE_SSO_VERIFY_URL = "https://esi.evetech.net/verify/"

# Default ESI scopes
DEFAULT_ESI_SCOPES = [
    "esi-wallet.read_character_wallet.v1",
    "esi-assets.read_assets.v1",
    "esi-markets.read_character_orders.v1",
    "esi-skills.read_skills.v1",
    "esi-industry.read_character_jobs.v1",
    "esi-characters.read_blueprints.v1",
]


class AuthRepository(Protocol):
    """Protocol for auth repository operations."""

    def save_pkce_state(self, state: str, state_data: dict) -> None: ...
    def get_pkce_state(self, state: str) -> Optional[dict]: ...
    def delete_pkce_state(self, state: str) -> bool: ...
    def save_character_auth(self, character_id: int, auth_data: dict) -> None: ...
    def get_character_auth(self, character_id: int) -> Optional[dict]: ...
    def get_all_character_auths(self) -> List[dict]: ...
    def delete_character_auth(self, character_id: int) -> bool: ...


class ESIClientProtocol(Protocol):
    """Protocol for ESI client dependency."""

    def get(self, endpoint: str, **kwargs) -> dict: ...


class AuthService:
    """Business logic for OAuth2 authentication and token management."""

    def __init__(
        self,
        repository: AuthRepository,
        esi_client: Optional[ESIClientProtocol],
        config,
    ):
        """Initialize service with dependencies.

        Args:
            repository: Auth repository for token/state storage
            esi_client: ESI client for API calls (optional)
            config: Application configuration object
        """
        self.repo = repository
        self.esi = esi_client
        self.config = config
        self.client_id = config.eve_client_id
        self.client_secret = config.eve_client_secret
        self.callback_url = config.eve_callback_url
        self.scopes = DEFAULT_ESI_SCOPES

    def get_auth_url(self) -> AuthUrl:
        """Generate OAuth2 authorization URL with PKCE.

        Returns:
            AuthUrl: Object containing auth URL, state, and scopes

        Raises:
            ValidationError: If client ID is not configured
        """
        if not self.client_id:
            raise ValidationError("EVE_CLIENT_ID not configured")

        # Generate state for CSRF protection (43+ chars)
        state = secrets.token_urlsafe(32)

        # Generate PKCE code verifier (43-128 chars)
        code_verifier = secrets.token_urlsafe(64)  # ~86 chars in base64url

        # Generate PKCE code challenge (SHA256 hash of verifier)
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).decode().rstrip("=")

        # Store state and verifier (expires in 10 minutes)
        current_time = time.time()
        self.repo.save_pkce_state(
            state,
            {
                "code_verifier": code_verifier,
                "created_at": current_time,
                "expires_at": current_time + 600,  # 10 minutes
            },
        )

        # Build authorization URL
        params = {
            "response_type": "code",
            "redirect_uri": self.callback_url,
            "client_id": self.client_id,
            "scope": " ".join(self.scopes),
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }

        auth_url = f"{EVE_SSO_AUTH_URL}?{urlencode(params)}"

        return AuthUrl(
            auth_url=auth_url,
            state=state,
            scopes=self.scopes,
            message="Open the auth_url in your browser to authorize",
        )

    def handle_callback(self, code: str, state: str) -> CharacterAuthLegacy:
        """Handle OAuth2 callback and exchange code for tokens.

        Args:
            code: Authorization code from OAuth2 callback
            state: State parameter for CSRF validation

        Returns:
            CharacterAuthLegacy: Character authentication with tokens

        Raises:
            AuthenticationError: If state is invalid, expired, or token exchange fails
        """
        # Validate state
        state_data = self.repo.get_pkce_state(state)
        if not state_data:
            raise AuthenticationError("Invalid or expired state parameter")

        # Check if state expired
        if time.time() > state_data["expires_at"]:
            self.repo.delete_pkce_state(state)
            raise AuthenticationError("State parameter expired")

        # Remove used state
        self.repo.delete_pkce_state(state)

        code_verifier = state_data["code_verifier"]

        # Exchange code for tokens
        token_data = {
            "grant_type": "authorization_code",
            "code": code,
            "code_verifier": code_verifier,
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Host": "login.eveonline.com",
        }

        # Use Basic Auth header for confidential clients
        if self.client_secret:
            auth_string = f"{self.client_id}:{self.client_secret}"
            auth_bytes = base64.b64encode(auth_string.encode()).decode()
            headers["Authorization"] = f"Basic {auth_bytes}"
        else:
            token_data["client_id"] = self.client_id

        try:
            response = requests.post(
                EVE_SSO_TOKEN_URL, data=token_data, headers=headers, timeout=30
            )

            if response.status_code != 200:
                raise AuthenticationError(
                    f"Token exchange failed: {response.status_code} - {response.text}"
                )

            tokens = response.json()

            # Verify and decode the access token to get character info
            char_info = self._verify_access_token(tokens["access_token"])

            # Store tokens with character info
            character_id = char_info.CharacterID
            expires_at = time.time() + tokens.get("expires_in", 1199)

            auth_data = {
                "access_token": tokens["access_token"],
                "refresh_token": tokens["refresh_token"],
                "expires_at": expires_at,
                "character_id": character_id,
                "character_name": char_info.CharacterName,
                "scopes": char_info.Scopes.split() if char_info.Scopes else [],
                "updated_at": datetime.now().isoformat(),
            }

            self.repo.save_character_auth(character_id, auth_data)

            return CharacterAuthLegacy(
                character_id=character_id,
                character_name=char_info.CharacterName,
                access_token=tokens["access_token"],
                refresh_token=tokens["refresh_token"],
                expires_at=expires_at,
                scopes=auth_data["scopes"],
                updated_at=datetime.now(),
            )

        except Exception as e:
            if "AuthenticationError" in type(e).__name__:
                raise
            raise AuthenticationError(f"Token exchange error: {str(e)}")

    def refresh_token(self, character_id: int) -> OAuthTokenResponse:
        """Refresh access token for a character.

        Args:
            character_id: Character ID to refresh token for

        Returns:
            OAuthTokenResponse: New token information

        Raises:
            AuthenticationError: If character not found or refresh fails
        """
        # Get stored auth
        auth_data = self.repo.get_character_auth(character_id)
        if not auth_data:
            raise AuthenticationError(f"No token found for character {character_id}")

        refresh_token = auth_data.get("refresh_token")
        if not refresh_token:
            raise AuthenticationError("No refresh token available")

        # Prepare refresh request
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Host": "login.eveonline.com",
        }

        # Use Basic Auth for confidential clients
        if self.client_secret:
            auth_string = f"{self.client_id}:{self.client_secret}"
            auth_bytes = base64.b64encode(auth_string.encode()).decode()
            headers["Authorization"] = f"Basic {auth_bytes}"
        else:
            data["client_id"] = self.client_id

        try:
            response = requests.post(
                EVE_SSO_TOKEN_URL, data=data, headers=headers, timeout=30
            )

            if response.status_code != 200:
                raise AuthenticationError(
                    f"Token refresh failed: {response.status_code} - {response.text}"
                )

            tokens = response.json()
            expires_at = time.time() + tokens.get("expires_in", 1199)

            # Update stored tokens
            auth_data["access_token"] = tokens["access_token"]
            auth_data["refresh_token"] = tokens.get("refresh_token", refresh_token)
            auth_data["expires_at"] = expires_at
            auth_data["updated_at"] = datetime.now().isoformat()

            self.repo.save_character_auth(character_id, auth_data)

            return OAuthTokenResponse(
                access_token=tokens["access_token"],
                refresh_token=auth_data["refresh_token"],
                expires_at=expires_at,
            )

        except Exception as e:
            if "AuthenticationError" in type(e).__name__:
                raise
            raise AuthenticationError(f"Token refresh error: {str(e)}")

    def verify_token(self, character_id: int) -> TokenVerifyResponse:
        """Verify token with ESI and get character info.

        Args:
            character_id: Character ID to verify

        Returns:
            TokenVerifyResponse: Token verification response from ESI

        Raises:
            AuthenticationError: If character not found or verification fails
        """
        auth_data = self.repo.get_character_auth(character_id)
        if not auth_data:
            raise AuthenticationError(f"No token found for character {character_id}")

        access_token = auth_data.get("access_token")
        return self._verify_access_token(access_token)

    def get_authenticated_characters(self) -> List[CharacterAuthSummary]:
        """Get list of authenticated characters.

        Returns:
            List[CharacterAuthSummary]: List of character auth summaries
        """
        auths = self.repo.get_all_character_auths()
        results = []

        for auth_data in auths:
            expires_at = auth_data.get("expires_at", 0)
            is_valid = time.time() < expires_at

            results.append(
                CharacterAuthSummary(
                    character_id=auth_data["character_id"],
                    character_name=auth_data["character_name"],
                    scopes=auth_data.get("scopes", []),
                    expires_at=expires_at,
                    is_valid=is_valid,
                )
            )

        return results

    def logout_character(self, character_id: int) -> bool:
        """Remove character authentication.

        Args:
            character_id: Character ID to remove

        Returns:
            bool: True if deleted, False if not found
        """
        return self.repo.delete_character_auth(character_id)

    def _verify_access_token(self, access_token: str) -> TokenVerifyResponse:
        """Verify access token and get character info.

        Args:
            access_token: Access token to verify

        Returns:
            TokenVerifyResponse: Verification response

        Raises:
            AuthenticationError: If verification fails
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
            "User-Agent": "EVE-Co-Pilot/1.2.0",
        }

        try:
            response = requests.get(EVE_SSO_VERIFY_URL, headers=headers, timeout=30)

            if response.status_code != 200:
                raise AuthenticationError(
                    f"Token verification failed: {response.status_code}"
                )

            data = response.json()
            return TokenVerifyResponse(**data)

        except Exception as e:
            if "AuthenticationError" in type(e).__name__:
                raise
            raise AuthenticationError(f"Verification error: {str(e)}")
