"""
EVE Co-Pilot OAuth2 Authentication Module
Handles EVE SSO authentication and token management
"""

import os
import json
import base64
import hashlib
import secrets
import time
from datetime import datetime, timedelta
from urllib.parse import urlencode
import requests

from config import (
    EVE_SSO_CLIENT_ID,
    EVE_SSO_SECRET_KEY,
    EVE_SSO_CALLBACK_URL,
    EVE_SSO_AUTH_URL,
    EVE_SSO_TOKEN_URL,
    EVE_SSO_VERIFY_URL,
    ESI_SCOPES,
    TOKEN_STORAGE_PATH,
    ESI_BASE_URL,
    ESI_USER_AGENT
)


STATE_STORAGE_PATH = "/home/cytrex/eve_copilot/auth_state.json"


class EVEAuth:
    """Handles EVE SSO OAuth2 authentication"""

    def __init__(self):
        self.client_id = os.environ.get("EVE_SSO_CLIENT_ID", EVE_SSO_CLIENT_ID)
        self.secret_key = os.environ.get("EVE_SSO_SECRET_KEY", EVE_SSO_SECRET_KEY)
        self.callback_url = EVE_SSO_CALLBACK_URL
        self.scopes = ESI_SCOPES
        self._state_store = self._load_state()
        self._tokens = self._load_tokens()

    def _load_state(self) -> dict:
        """Load state store from file"""
        if os.path.exists(STATE_STORAGE_PATH):
            try:
                with open(STATE_STORAGE_PATH, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_state(self):
        """Save state store to file"""
        try:
            with open(STATE_STORAGE_PATH, 'w') as f:
                json.dump(self._state_store, f)
        except Exception as e:
            print(f"Error saving state: {e}")

    def _load_tokens(self) -> dict:
        """Load tokens from storage"""
        if os.path.exists(TOKEN_STORAGE_PATH):
            try:
                with open(TOKEN_STORAGE_PATH, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading tokens: {e}")
        return {}

    def _save_tokens(self):
        """Save tokens to storage"""
        try:
            with open(TOKEN_STORAGE_PATH, 'w') as f:
                json.dump(self._tokens, f, indent=2)
        except Exception as e:
            print(f"Error saving tokens: {e}")

    def get_auth_url(self) -> dict:
        """Generate OAuth2 authorization URL with PKCE"""
        if not self.client_id:
            return {"error": "EVE_SSO_CLIENT_ID not configured"}

        # Generate state for CSRF protection
        state = secrets.token_urlsafe(32)

        # Generate PKCE code verifier and challenge
        code_verifier = secrets.token_urlsafe(64)
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).decode().rstrip('=')

        # Store state and verifier (expires in 10 minutes)
        self._state_store[state] = {
            "code_verifier": code_verifier,
            "created_at": time.time(),
            "expires_at": time.time() + 600
        }
        self._save_state()

        # Build authorization URL
        params = {
            "response_type": "code",
            "redirect_uri": self.callback_url,
            "client_id": self.client_id,
            "scope": " ".join(self.scopes),
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256"
        }

        auth_url = f"{EVE_SSO_AUTH_URL}?{urlencode(params)}"

        return {
            "auth_url": auth_url,
            "state": state,
            "scopes": self.scopes,
            "message": "Open the auth_url in your browser to authorize"
        }

    def handle_callback(self, code: str, state: str) -> dict:
        """Handle OAuth2 callback and exchange code for tokens"""
        # Reload state from file (in case of server restart)
        self._state_store = self._load_state()

        # Validate state
        if state not in self._state_store:
            return {"error": "Invalid or expired state parameter"}

        state_data = self._state_store.pop(state)
        self._save_state()  # Remove used state

        # Check if state expired
        if time.time() > state_data["expires_at"]:
            return {"error": "State parameter expired"}

        code_verifier = state_data["code_verifier"]

        # Exchange code for tokens
        token_data = {
            "grant_type": "authorization_code",
            "code": code,
            "code_verifier": code_verifier
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Host": "login.eveonline.com"
        }

        # Use Basic Auth header for confidential clients, or client_id in body for public
        if self.secret_key:
            auth_string = f"{self.client_id}:{self.secret_key}"
            auth_bytes = base64.b64encode(auth_string.encode()).decode()
            headers["Authorization"] = f"Basic {auth_bytes}"
        else:
            token_data["client_id"] = self.client_id

        try:
            response = requests.post(
                EVE_SSO_TOKEN_URL,
                data=token_data,
                headers=headers,
                timeout=30
            )

            if response.status_code != 200:
                return {
                    "error": "Token exchange failed",
                    "status_code": response.status_code,
                    "details": response.text
                }

            tokens = response.json()

            # Verify and decode the access token to get character info
            char_info = self._verify_token(tokens["access_token"])
            if "error" in char_info:
                return char_info

            # Store tokens with character info
            character_id = char_info["CharacterID"]
            self._tokens[str(character_id)] = {
                "access_token": tokens["access_token"],
                "refresh_token": tokens["refresh_token"],
                "expires_at": time.time() + tokens.get("expires_in", 1199),
                "character_id": character_id,
                "character_name": char_info["CharacterName"],
                "scopes": char_info.get("Scopes", "").split(),
                "updated_at": datetime.now().isoformat()
            }

            self._save_tokens()

            return {
                "success": True,
                "character_id": character_id,
                "character_name": char_info["CharacterName"],
                "scopes": char_info.get("Scopes", "").split(),
                "message": f"Successfully authenticated as {char_info['CharacterName']}"
            }

        except Exception as e:
            return {"error": f"Token exchange error: {str(e)}"}

    def _verify_token(self, access_token: str) -> dict:
        """Verify access token and get character info"""
        headers = {
            "Authorization": f"Bearer {access_token}",
            "User-Agent": ESI_USER_AGENT
        }

        try:
            response = requests.get(
                EVE_SSO_VERIFY_URL,
                headers=headers,
                timeout=30
            )

            if response.status_code != 200:
                return {"error": "Token verification failed"}

            return response.json()

        except Exception as e:
            return {"error": f"Verification error: {str(e)}"}

    def refresh_token(self, character_id: int) -> dict:
        """Refresh access token for a character"""
        char_id_str = str(character_id)

        if char_id_str not in self._tokens:
            return {"error": f"No token found for character {character_id}"}

        token_data = self._tokens[char_id_str]
        refresh_token = token_data.get("refresh_token")

        if not refresh_token:
            return {"error": "No refresh token available"}

        # Prepare refresh request
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Host": "login.eveonline.com"
        }

        # Use Basic Auth for confidential clients, or client_id in body for public
        if self.secret_key:
            auth_string = f"{self.client_id}:{self.secret_key}"
            auth_bytes = base64.b64encode(auth_string.encode()).decode()
            headers["Authorization"] = f"Basic {auth_bytes}"
        else:
            data["client_id"] = self.client_id

        try:
            response = requests.post(
                EVE_SSO_TOKEN_URL,
                data=data,
                headers=headers,
                timeout=30
            )

            if response.status_code != 200:
                return {
                    "error": "Token refresh failed",
                    "status_code": response.status_code,
                    "details": response.text
                }

            tokens = response.json()

            # Update stored tokens
            self._tokens[char_id_str]["access_token"] = tokens["access_token"]
            self._tokens[char_id_str]["refresh_token"] = tokens.get(
                "refresh_token",
                refresh_token
            )
            self._tokens[char_id_str]["expires_at"] = time.time() + tokens.get("expires_in", 1199)
            self._tokens[char_id_str]["updated_at"] = datetime.now().isoformat()

            self._save_tokens()

            return {
                "success": True,
                "character_id": character_id,
                "expires_at": self._tokens[char_id_str]["expires_at"]
            }

        except Exception as e:
            return {"error": f"Refresh error: {str(e)}"}

    def get_valid_token(self, character_id: int) -> str | None:
        """Get a valid access token, refreshing if necessary"""
        char_id_str = str(character_id)

        if char_id_str not in self._tokens:
            return None

        token_data = self._tokens[char_id_str]

        # Check if token is about to expire (within 5 minutes)
        if time.time() > (token_data["expires_at"] - 300):
            result = self.refresh_token(character_id)
            if "error" in result:
                return None

        return self._tokens[char_id_str]["access_token"]

    def get_authenticated_characters(self) -> list:
        """Get list of authenticated characters"""
        characters = []
        for char_id, data in self._tokens.items():
            characters.append({
                "character_id": int(char_id),
                "character_name": data.get("character_name", "Unknown"),
                "scopes": data.get("scopes", []),
                "expires_at": data.get("expires_at"),
                "is_valid": time.time() < data.get("expires_at", 0)
            })
        return characters

    def remove_character(self, character_id: int) -> dict:
        """Remove a character's authentication"""
        char_id_str = str(character_id)

        if char_id_str not in self._tokens:
            return {"error": f"Character {character_id} not found"}

        char_name = self._tokens[char_id_str].get("character_name", "Unknown")
        del self._tokens[char_id_str]
        self._save_tokens()

        return {
            "success": True,
            "message": f"Removed authentication for {char_name}"
        }


# Global auth instance
eve_auth = EVEAuth()
