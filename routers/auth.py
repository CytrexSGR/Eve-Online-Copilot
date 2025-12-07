"""
Authentication router - EVE SSO OAuth2 endpoints.
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse

from auth import eve_auth
from config import ESI_SCOPES

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.get("/login")
async def auth_login(redirect: bool = False):
    """Start OAuth2 authentication flow"""
    result = eve_auth.get_auth_url()
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    if redirect:
        return RedirectResponse(url=result["auth_url"])
    return result


@router.get("/callback")
async def auth_callback(
    code: str = Query(..., description="Authorization code from EVE SSO"),
    state: str = Query(..., description="State parameter for CSRF protection")
):
    """OAuth2 callback endpoint"""
    result = eve_auth.handle_callback(code, state)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result)
    return result


@router.get("/characters")
async def auth_characters():
    """Get list of authenticated characters"""
    characters = eve_auth.get_authenticated_characters()
    return {"authenticated_characters": len(characters), "characters": characters}


@router.post("/refresh/{character_id}")
async def auth_refresh(character_id: int):
    """Manually refresh token for a character"""
    result = eve_auth.refresh_token(character_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.delete("/character/{character_id}")
async def auth_remove_character(character_id: int):
    """Remove authentication for a character"""
    result = eve_auth.remove_character(character_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/scopes")
async def auth_scopes():
    """Get required ESI scopes"""
    return {"required_scopes": ESI_SCOPES}
