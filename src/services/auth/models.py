"""Auth service domain models."""

from datetime import datetime, timedelta
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class OAuthToken(BaseModel):
    """OAuth2 token entity for storage and retrieval."""

    model_config = ConfigDict(from_attributes=True)

    access_token: str = Field(..., description="OAuth access token")
    refresh_token: str = Field(..., description="OAuth refresh token")
    expires_at: datetime = Field(..., description="Token expiration timestamp")
    character_id: int = Field(..., description="EVE character ID")
    character_name: str = Field(..., description="EVE character name")
    scopes: List[str] = Field(default_factory=list, description="Granted ESI scopes")

    def is_expired(self) -> bool:
        """Check if token is expired."""
        return datetime.now() >= self.expires_at

    def is_expiring_soon(self, minutes: int = 5) -> bool:
        """Check if token expires within specified minutes."""
        threshold = datetime.now() + timedelta(minutes=minutes)
        return self.expires_at <= threshold


class AuthState(BaseModel):
    """OAuth state data for PKCE flow."""

    model_config = ConfigDict(from_attributes=True)

    state: str = Field(..., description="OAuth state parameter for CSRF protection")
    code_verifier: str = Field(..., description="PKCE code verifier")
    created_at: datetime = Field(default_factory=datetime.now, description="State creation timestamp")
    expires_at: datetime = Field(..., description="State expiration timestamp")

    def is_expired(self) -> bool:
        """Check if state is expired."""
        return datetime.now() >= self.expires_at


class CharacterAuth(BaseModel):
    """Character authentication summary with token."""

    model_config = ConfigDict(from_attributes=True)

    character_id: int = Field(..., description="EVE character ID")
    character_name: str = Field(..., description="EVE character name")
    token: OAuthToken = Field(..., description="OAuth token data")
    authenticated_at: datetime = Field(default_factory=datetime.now, description="Authentication timestamp")

    @property
    def is_valid(self) -> bool:
        """Check if authentication is still valid."""
        return not self.token.is_expired()

    @property
    def needs_refresh(self) -> bool:
        """Check if token needs refresh."""
        return self.token.is_expiring_soon()


# Legacy models for backward compatibility
class CharacterAuthSummary(BaseModel):
    """Summary view of character authentication (legacy)."""
    character_id: int
    character_name: str
    scopes: List[str]
    expires_at: float
    is_valid: bool


class AuthUrl(BaseModel):
    """OAuth2 authorization URL response."""
    auth_url: str
    state: str
    scopes: List[str]
    message: str = "Open the auth_url in your browser to authorize"


class PKCEState(BaseModel):
    """PKCE state storage (legacy - use AuthState instead)."""
    code_verifier: str
    created_at: float
    expires_at: float


class TokenVerifyResponse(BaseModel):
    """Token verification response from ESI."""
    CharacterID: int
    CharacterName: str
    ExpiresOn: str
    Scopes: str = ""
    TokenType: str = "Character"
    CharacterOwnerHash: str = ""
