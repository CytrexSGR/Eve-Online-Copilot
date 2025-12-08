"""Auth repository - data access layer for authentication tokens and state."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from src.core.exceptions import EVECopilotError
from src.services.auth.models import OAuthToken, AuthState, CharacterAuth


class AuthRepository:
    """Repository for managing authentication tokens and OAuth state."""

    def __init__(self, data_dir: Optional[str] = None):
        """
        Initialize repository with data directory.

        Args:
            data_dir: Directory to store auth data files. Defaults to ./data/
        """
        if data_dir is None:
            # Use project root data directory
            project_root = Path(__file__).parent.parent.parent.parent
            self.data_dir = str(project_root / "data")
        else:
            self.data_dir = data_dir

        # Ensure data directory exists
        Path(self.data_dir).mkdir(parents=True, exist_ok=True)

        self.tokens_file = Path(self.data_dir) / "tokens.json"
        self.state_file = Path(self.data_dir) / "auth_state.json"

    # Token Management

    def save_token(self, character_id: int, token: OAuthToken) -> bool:
        """
        Save OAuth token for a character.

        Args:
            character_id: EVE character ID
            token: OAuthToken to save

        Returns:
            True if successful

        Raises:
            EVECopilotError: If save operation fails
        """
        try:
            # Load existing tokens
            tokens = self._load_tokens_file()

            # Update token for character
            tokens[str(character_id)] = {
                "access_token": token.access_token,
                "refresh_token": token.refresh_token,
                "expires_at": token.expires_at.isoformat(),
                "character_id": token.character_id,
                "character_name": token.character_name,
                "scopes": token.scopes
            }

            # Save to file
            self._save_tokens_file(tokens)
            return True

        except Exception as e:
            raise EVECopilotError(f"Failed to save token for character {character_id}: {str(e)}")

    def get_token(self, character_id: int) -> Optional[OAuthToken]:
        """
        Get OAuth token for a character.

        Args:
            character_id: EVE character ID

        Returns:
            OAuthToken if found, None otherwise
        """
        try:
            tokens = self._load_tokens_file()
            token_data = tokens.get(str(character_id))

            if token_data is None:
                return None

            # Parse datetime from ISO format
            expires_at = datetime.fromisoformat(token_data["expires_at"])

            return OAuthToken(
                access_token=token_data["access_token"],
                refresh_token=token_data["refresh_token"],
                expires_at=expires_at,
                character_id=token_data["character_id"],
                character_name=token_data["character_name"],
                scopes=token_data.get("scopes", [])
            )

        except (json.JSONDecodeError, KeyError, ValueError):
            # Return None for corrupted data instead of raising
            return None
        except Exception:
            # Return None for any other errors
            return None

    def delete_token(self, character_id: int) -> bool:
        """
        Delete OAuth token for a character.

        Args:
            character_id: EVE character ID

        Returns:
            True if token was deleted, False if not found
        """
        try:
            tokens = self._load_tokens_file()
            char_id_str = str(character_id)

            if char_id_str not in tokens:
                return False

            del tokens[char_id_str]
            self._save_tokens_file(tokens)
            return True

        except Exception:
            return False

    def list_tokens(self) -> List[CharacterAuth]:
        """
        List all authenticated characters.

        Returns:
            List of CharacterAuth objects
        """
        try:
            tokens = self._load_tokens_file()
            characters = []

            for char_id, token_data in tokens.items():
                try:
                    expires_at = datetime.fromisoformat(token_data["expires_at"])

                    token = OAuthToken(
                        access_token=token_data["access_token"],
                        refresh_token=token_data["refresh_token"],
                        expires_at=expires_at,
                        character_id=token_data["character_id"],
                        character_name=token_data["character_name"],
                        scopes=token_data.get("scopes", [])
                    )

                    character_auth = CharacterAuth(
                        character_id=token_data["character_id"],
                        character_name=token_data["character_name"],
                        token=token,
                        authenticated_at=expires_at  # Use expires_at as fallback
                    )

                    characters.append(character_auth)

                except (KeyError, ValueError):
                    # Skip corrupted entries
                    continue

            return characters

        except Exception:
            return []

    # State Management

    def save_state(self, state_id: str, state: AuthState) -> bool:
        """
        Save OAuth state for PKCE flow.

        Args:
            state_id: State identifier
            state: AuthState to save

        Returns:
            True if successful

        Raises:
            EVECopilotError: If save operation fails
        """
        try:
            # Load existing states
            states = self._load_state_file()

            # Update state
            states[state_id] = {
                "state": state.state,
                "code_verifier": state.code_verifier,
                "created_at": state.created_at.isoformat(),
                "expires_at": state.expires_at.isoformat()
            }

            # Save to file
            self._save_state_file(states)
            return True

        except Exception as e:
            raise EVECopilotError(f"Failed to save state {state_id}: {str(e)}")

    def get_state(self, state_id: str) -> Optional[AuthState]:
        """
        Get OAuth state by ID.

        Args:
            state_id: State identifier

        Returns:
            AuthState if found, None otherwise
        """
        try:
            states = self._load_state_file()
            state_data = states.get(state_id)

            if state_data is None:
                return None

            # Parse datetimes from ISO format
            created_at = datetime.fromisoformat(state_data["created_at"])
            expires_at = datetime.fromisoformat(state_data["expires_at"])

            return AuthState(
                state=state_data["state"],
                code_verifier=state_data["code_verifier"],
                created_at=created_at,
                expires_at=expires_at
            )

        except (json.JSONDecodeError, KeyError, ValueError):
            # Return None for corrupted data
            return None
        except Exception:
            return None

    def delete_state(self, state_id: str) -> bool:
        """
        Delete OAuth state after use.

        Args:
            state_id: State identifier

        Returns:
            True if state was deleted, False if not found
        """
        try:
            states = self._load_state_file()

            if state_id not in states:
                return False

            del states[state_id]
            self._save_state_file(states)
            return True

        except Exception:
            return False

    # Private Helper Methods

    def _load_tokens_file(self) -> Dict:
        """Load tokens from JSON file."""
        if not self.tokens_file.exists():
            return {}

        try:
            with open(self.tokens_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}

    def _save_tokens_file(self, tokens: Dict) -> None:
        """Save tokens to JSON file."""
        with open(self.tokens_file, 'w') as f:
            json.dump(tokens, f, indent=2)

    def _load_state_file(self) -> Dict:
        """Load auth state from JSON file."""
        if not self.state_file.exists():
            return {}

        try:
            with open(self.state_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}

    def _save_state_file(self, states: Dict) -> None:
        """Save auth state to JSON file."""
        with open(self.state_file, 'w') as f:
            json.dump(states, f, indent=2)

    # Adapter methods for Protocol compatibility

    def save_pkce_state(self, state: str, state_data: Dict) -> None:
        """Save PKCE state for OAuth2 flow (Protocol adapter)."""
        auth_state = AuthState(
            state=state,
            code_verifier=state_data["code_verifier"],
            created_at=datetime.fromtimestamp(state_data["created_at"]),
            expires_at=datetime.fromtimestamp(state_data["expires_at"])
        )
        self.save_state(state, auth_state)

    def get_pkce_state(self, state: str) -> Optional[Dict]:
        """Retrieve PKCE state by state parameter (Protocol adapter)."""
        auth_state = self.get_state(state)
        if auth_state is None:
            return None

        return {
            "code_verifier": auth_state.code_verifier,
            "created_at": auth_state.created_at.timestamp(),
            "expires_at": auth_state.expires_at.timestamp()
        }

    def delete_pkce_state(self, state: str) -> bool:
        """Delete PKCE state after use (Protocol adapter)."""
        return self.delete_state(state)

    def save_character_auth(self, character_id: int, auth_data: Dict) -> None:
        """Save character authentication tokens (Protocol adapter)."""
        # Convert timestamp to datetime if needed
        if isinstance(auth_data["expires_at"], (int, float)):
            expires_at = datetime.fromtimestamp(auth_data["expires_at"])
        else:
            expires_at = datetime.fromisoformat(auth_data["expires_at"])

        token = OAuthToken(
            access_token=auth_data["access_token"],
            refresh_token=auth_data["refresh_token"],
            expires_at=expires_at,
            character_id=character_id,
            character_name=auth_data["character_name"],
            scopes=auth_data.get("scopes", [])
        )
        self.save_token(character_id, token)

    def get_character_auth(self, character_id: int) -> Optional[Dict]:
        """Get character authentication by character ID (Protocol adapter)."""
        token = self.get_token(character_id)
        if token is None:
            return None

        return {
            "character_id": token.character_id,
            "character_name": token.character_name,
            "access_token": token.access_token,
            "refresh_token": token.refresh_token,
            "expires_at": token.expires_at.timestamp(),
            "scopes": token.scopes,
            "updated_at": datetime.now().isoformat()
        }

    def get_all_character_auths(self) -> List[Dict]:
        """Get all stored character authentications (Protocol adapter)."""
        characters = self.list_tokens()
        results = []

        for char_auth in characters:
            results.append({
                "character_id": char_auth.character_id,
                "character_name": char_auth.character_name,
                "access_token": char_auth.token.access_token,
                "refresh_token": char_auth.token.refresh_token,
                "expires_at": char_auth.token.expires_at.timestamp(),
                "scopes": char_auth.token.scopes,
                "updated_at": char_auth.authenticated_at.isoformat()
            })

        return results

    def delete_character_auth(self, character_id: int) -> bool:
        """Delete character authentication (Protocol adapter)."""
        return self.delete_token(character_id)
