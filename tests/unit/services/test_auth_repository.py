"""Unit tests for AuthRepository."""

import json
import os
import pytest
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, mock_open, patch

from src.core.exceptions import EVECopilotError, NotFoundError
from src.services.auth.models import OAuthToken, AuthState, CharacterAuth
from src.services.auth.repository import AuthRepository


class TestAuthRepository:
    """Test cases for AuthRepository."""

    @pytest.fixture
    def mock_data_dir(self, tmp_path):
        """Create temporary data directory for tests."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        return data_dir

    @pytest.fixture
    def repository(self, mock_data_dir):
        """Create AuthRepository instance with test data directory."""
        return AuthRepository(str(mock_data_dir))

    @pytest.fixture
    def sample_token(self) -> OAuthToken:
        """Create sample OAuth token."""
        return OAuthToken(
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            expires_at=datetime.now() + timedelta(hours=1),
            character_id=123456,
            character_name="Test Character",
            scopes=["esi-markets.read_character_orders.v1", "esi-wallet.read_character_wallet.v1"]
        )

    @pytest.fixture
    def sample_state(self) -> AuthState:
        """Create sample auth state."""
        return AuthState(
            state="test_state_123",
            code_verifier="test_code_verifier_456",
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(minutes=10)
        )

    # Token Tests

    def test_save_token_creates_new_file(self, repository, sample_token):
        """Test save_token creates tokens.json if it doesn't exist."""
        result = repository.save_token(sample_token.character_id, sample_token)

        assert result is True
        tokens_file = Path(repository.data_dir) / "tokens.json"
        assert tokens_file.exists()

        # Verify content
        with open(tokens_file, 'r') as f:
            data = json.load(f)
        assert str(sample_token.character_id) in data
        assert data[str(sample_token.character_id)]["character_name"] == "Test Character"

    def test_save_token_updates_existing_token(self, repository, sample_token):
        """Test save_token updates existing token for character."""
        # Save initial token
        repository.save_token(sample_token.character_id, sample_token)

        # Update token
        updated_token = sample_token.model_copy(update={"access_token": "new_access_token"})
        result = repository.save_token(sample_token.character_id, updated_token)

        assert result is True
        token = repository.get_token(sample_token.character_id)
        assert token is not None
        assert token.access_token == "new_access_token"

    def test_save_token_preserves_other_tokens(self, repository, sample_token):
        """Test save_token preserves other characters' tokens."""
        # Save first token
        repository.save_token(123456, sample_token)

        # Save second token for different character
        token2 = sample_token.model_copy(update={
            "character_id": 789012,
            "character_name": "Another Character"
        })
        repository.save_token(789012, token2)

        # Verify both tokens exist
        token1 = repository.get_token(123456)
        token2_retrieved = repository.get_token(789012)

        assert token1 is not None
        assert token2_retrieved is not None
        assert token1.character_name == "Test Character"
        assert token2_retrieved.character_name == "Another Character"

    def test_get_token_returns_token_when_found(self, repository, sample_token):
        """Test get_token returns token when character exists."""
        repository.save_token(sample_token.character_id, sample_token)

        token = repository.get_token(sample_token.character_id)

        assert token is not None
        assert token.character_id == sample_token.character_id
        assert token.character_name == sample_token.character_name
        assert token.access_token == sample_token.access_token

    def test_get_token_returns_none_when_not_found(self, repository):
        """Test get_token returns None when character doesn't exist."""
        token = repository.get_token(999999)
        assert token is None

    def test_get_token_returns_none_when_file_missing(self, repository):
        """Test get_token returns None when tokens.json doesn't exist."""
        token = repository.get_token(123456)
        assert token is None

    def test_delete_token_removes_character(self, repository, sample_token):
        """Test delete_token removes character's token."""
        repository.save_token(sample_token.character_id, sample_token)

        result = repository.delete_token(sample_token.character_id)

        assert result is True
        token = repository.get_token(sample_token.character_id)
        assert token is None

    def test_delete_token_returns_false_when_not_found(self, repository):
        """Test delete_token returns False when character doesn't exist."""
        result = repository.delete_token(999999)
        assert result is False

    def test_delete_token_preserves_other_tokens(self, repository, sample_token):
        """Test delete_token preserves other characters' tokens."""
        # Save two tokens
        repository.save_token(123456, sample_token)
        token2 = sample_token.model_copy(update={
            "character_id": 789012,
            "character_name": "Another Character"
        })
        repository.save_token(789012, token2)

        # Delete first token
        repository.delete_token(123456)

        # Verify second token still exists
        token2_retrieved = repository.get_token(789012)
        assert token2_retrieved is not None
        assert token2_retrieved.character_name == "Another Character"

    def test_list_tokens_returns_all_tokens(self, repository, sample_token):
        """Test list_tokens returns all authenticated characters."""
        # Save multiple tokens
        repository.save_token(123456, sample_token)
        token2 = sample_token.model_copy(update={
            "character_id": 789012,
            "character_name": "Character Two"
        })
        repository.save_token(789012, token2)

        characters = repository.list_tokens()

        assert len(characters) == 2
        char_ids = [char.character_id for char in characters]
        assert 123456 in char_ids
        assert 789012 in char_ids

    def test_list_tokens_returns_empty_list_when_no_tokens(self, repository):
        """Test list_tokens returns empty list when no tokens exist."""
        characters = repository.list_tokens()
        assert characters == []

    # State Tests

    def test_save_state_creates_new_file(self, repository, sample_state):
        """Test save_state creates auth_state.json if it doesn't exist."""
        result = repository.save_state(sample_state.state, sample_state)

        assert result is True
        state_file = Path(repository.data_dir) / "auth_state.json"
        assert state_file.exists()

    def test_save_state_stores_state_correctly(self, repository, sample_state):
        """Test save_state stores state data correctly."""
        repository.save_state(sample_state.state, sample_state)

        retrieved_state = repository.get_state(sample_state.state)

        assert retrieved_state is not None
        assert retrieved_state.state == sample_state.state
        assert retrieved_state.code_verifier == sample_state.code_verifier

    def test_save_state_preserves_other_states(self, repository, sample_state):
        """Test save_state preserves other states."""
        # Save first state
        repository.save_state("state1", sample_state)

        # Save second state
        state2 = sample_state.model_copy(update={
            "state": "state2",
            "code_verifier": "verifier2"
        })
        repository.save_state("state2", state2)

        # Verify both exist
        state1 = repository.get_state("state1")
        state2_retrieved = repository.get_state("state2")

        assert state1 is not None
        assert state2_retrieved is not None
        assert state1.code_verifier == "test_code_verifier_456"
        assert state2_retrieved.code_verifier == "verifier2"

    def test_get_state_returns_state_when_found(self, repository, sample_state):
        """Test get_state returns state when found."""
        repository.save_state(sample_state.state, sample_state)

        state = repository.get_state(sample_state.state)

        assert state is not None
        assert state.state == sample_state.state

    def test_get_state_returns_none_when_not_found(self, repository):
        """Test get_state returns None when state doesn't exist."""
        state = repository.get_state("nonexistent_state")
        assert state is None

    def test_get_state_returns_none_when_file_missing(self, repository):
        """Test get_state returns None when auth_state.json doesn't exist."""
        state = repository.get_state("some_state")
        assert state is None

    def test_delete_state_removes_state(self, repository, sample_state):
        """Test delete_state removes state after use."""
        repository.save_state(sample_state.state, sample_state)

        result = repository.delete_state(sample_state.state)

        assert result is True
        state = repository.get_state(sample_state.state)
        assert state is None

    def test_delete_state_returns_false_when_not_found(self, repository):
        """Test delete_state returns False when state doesn't exist."""
        result = repository.delete_state("nonexistent_state")
        assert result is False

    def test_delete_state_preserves_other_states(self, repository, sample_state):
        """Test delete_state preserves other states."""
        # Save two states
        repository.save_state("state1", sample_state)
        state2 = sample_state.model_copy(update={
            "state": "state2",
            "code_verifier": "verifier2"
        })
        repository.save_state("state2", state2)

        # Delete first state
        repository.delete_state("state1")

        # Verify second state still exists
        state2_retrieved = repository.get_state("state2")
        assert state2_retrieved is not None
        assert state2_retrieved.code_verifier == "verifier2"

    # Error Handling Tests

    def test_save_token_handles_permission_error(self, repository, sample_token):
        """Test save_token handles file permission errors."""
        with patch("builtins.open", side_effect=PermissionError("Permission denied")):
            with pytest.raises(EVECopilotError, match="Failed to save token"):
                repository.save_token(sample_token.character_id, sample_token)

    def test_get_token_handles_corrupted_json(self, repository):
        """Test get_token handles corrupted JSON file."""
        tokens_file = Path(repository.data_dir) / "tokens.json"
        tokens_file.write_text("{ invalid json }")

        # Should return None instead of raising
        token = repository.get_token(123456)
        assert token is None

    def test_save_state_handles_write_error(self, repository, sample_state):
        """Test save_state handles write errors."""
        with patch("builtins.open", side_effect=OSError("Disk full")):
            with pytest.raises(EVECopilotError, match="Failed to save state"):
                repository.save_state(sample_state.state, sample_state)

    def test_get_state_handles_corrupted_json(self, repository):
        """Test get_state handles corrupted JSON file."""
        state_file = Path(repository.data_dir) / "auth_state.json"
        state_file.write_text("{ bad json }")

        # Should return None instead of raising
        state = repository.get_state("some_state")
        assert state is None

    # Data Directory Tests

    def test_repository_creates_data_directory(self, tmp_path):
        """Test repository creates data directory if it doesn't exist."""
        data_dir = tmp_path / "new_data"
        repository = AuthRepository(str(data_dir))

        assert Path(data_dir).exists()

    def test_repository_uses_default_data_dir(self):
        """Test repository uses default data/ directory when not specified."""
        with patch("pathlib.Path.mkdir") as mock_mkdir:
            repository = AuthRepository()
            assert "data" in repository.data_dir
