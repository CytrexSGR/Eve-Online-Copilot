"""
Authentication router - EVE SSO OAuth2 endpoints.
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import RedirectResponse

from src.core.config import get_settings
from src.core.exceptions import AuthenticationError, ValidationError, EVECopilotError
from src.services.auth.service import AuthService
from src.services.auth.repository import AuthRepository
from src.integrations.esi.client import ESIClient
from config import ESI_SCOPES

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


def get_auth_service() -> AuthService:
    """Dependency injection for AuthService."""
    settings = get_settings()
    esi_client = ESIClient(settings)
    auth_repository = AuthRepository()
    return AuthService(auth_repository, esi_client, settings)


@router.get("/login")
async def auth_login(
    redirect: bool = False,
    service: AuthService = Depends(get_auth_service)
):
    """Start OAuth2 authentication flow"""
    try:
        result = service.get_auth_url()
        if redirect:
            return RedirectResponse(url=result.auth_url)
        return result.model_dump()
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except EVECopilotError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/callback")
async def auth_callback(
    code: str = Query(..., description="Authorization code from EVE SSO"),
    state: str = Query(..., description="State parameter for CSRF protection"),
    service: AuthService = Depends(get_auth_service)
):
    """OAuth2 callback endpoint"""
    try:
        result = service.handle_callback(code, state)
        # Convert CharacterAuthLegacy model to dict for response
        return result.model_dump()
    except AuthenticationError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except EVECopilotError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/characters")
async def auth_characters(
    service: AuthService = Depends(get_auth_service)
):
    """Get list of authenticated characters"""
    try:
        characters = service.get_authenticated_characters()
        # Convert list of CharacterAuthSummary models to dicts
        return {
            "authenticated_characters": len(characters),
            "characters": [char.model_dump() for char in characters]
        }
    except EVECopilotError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/refresh/{character_id}")
async def auth_refresh(
    character_id: int,
    service: AuthService = Depends(get_auth_service)
):
    """Manually refresh token for a character"""
    try:
        result = service.refresh_token(character_id)
        return result.model_dump()
    except AuthenticationError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except EVECopilotError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/character/{character_id}")
async def auth_remove_character(
    character_id: int,
    service: AuthService = Depends(get_auth_service)
):
    """Remove authentication for a character"""
    try:
        result = service.logout_character(character_id)
        if not result:
            raise HTTPException(status_code=404, detail=f"Character {character_id} not found")
        return {"status": "removed", "character_id": character_id}
    except EVECopilotError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scopes")
async def auth_scopes():
    """Get required ESI scopes"""
    return {"required_scopes": ESI_SCOPES}
