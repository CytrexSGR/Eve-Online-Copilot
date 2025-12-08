"""Tests for core configuration module."""

import pytest
from pydantic import ValidationError


def test_config_loads_from_env(monkeypatch):
    """Test configuration loads from environment variables."""
    monkeypatch.setenv("DB_HOST", "testhost")
    monkeypatch.setenv("DB_PORT", "5433")
    monkeypatch.setenv("DB_NAME", "testdb")
    monkeypatch.setenv("DB_USER", "testuser")
    monkeypatch.setenv("DB_PASSWORD", "testpass")
    monkeypatch.setenv("EVE_CLIENT_ID", "test_client_id")
    monkeypatch.setenv("EVE_CLIENT_SECRET", "test_secret")
    monkeypatch.setenv("EVE_CALLBACK_URL", "http://test/callback")

    from src.core.config import get_settings

    settings = get_settings()
    assert settings.db_host == "testhost"
    assert settings.db_port == 5433
    assert settings.db_name == "testdb"


def test_config_has_defaults():
    """Test configuration has sensible defaults."""
    from src.core.config import Settings

    settings = Settings(
        db_host="localhost",
        db_name="eve_sde",
        db_user="eve",
        db_password="test",
        eve_client_id="id",
        eve_client_secret="secret",
        eve_callback_url="http://test"
    )

    assert settings.api_host == "0.0.0.0"
    assert settings.api_port == 8000
    assert settings.hunter_min_roi == 15.0


def test_config_validates_required_fields():
    """Test configuration validates required database fields."""
    from src.core.config import Settings

    with pytest.raises(ValidationError):
        Settings(eve_client_id="id", eve_client_secret="secret")
