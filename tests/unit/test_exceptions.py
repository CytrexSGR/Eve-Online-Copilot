"""Tests for custom exceptions."""

import pytest


def test_not_found_exception():
    """Test NotFoundError exception."""
    from src.core.exceptions import NotFoundError

    error = NotFoundError("Item", 123)
    assert str(error) == "Item with ID 123 not found"
    assert error.resource == "Item"
    assert error.resource_id == 123


def test_validation_error():
    """Test ValidationError exception."""
    from src.core.exceptions import ValidationError

    error = ValidationError("Invalid input", {"field": "name", "error": "required"})
    assert "Invalid input" in str(error)
    assert error.details == {"field": "name", "error": "required"}


def test_external_api_error():
    """Test ExternalAPIError exception."""
    from src.core.exceptions import ExternalAPIError

    error = ExternalAPIError("ESI API", 503, "Service unavailable")
    assert error.service_name == "ESI API"
    assert error.status_code == 503
    assert "Service unavailable" in str(error)


def test_authentication_error():
    """Test AuthenticationError exception."""
    from src.core.exceptions import AuthenticationError

    error = AuthenticationError("Token expired")
    assert "Token expired" in str(error)
