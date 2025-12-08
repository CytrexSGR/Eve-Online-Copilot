"""Custom exceptions for EVE Co-Pilot."""

from typing import Any, Dict, Optional


class EVECopilotError(Exception):
    """Base exception for all EVE Co-Pilot errors."""
    pass


class NotFoundError(EVECopilotError):
    """Raised when a resource is not found."""

    def __init__(self, resource: str, resource_id: Any):
        self.resource = resource
        self.resource_id = resource_id
        super().__init__(f"{resource} with ID {resource_id} not found")


class ValidationError(EVECopilotError):
    """Raised when validation fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.details = details or {}
        super().__init__(message)


class ExternalAPIError(EVECopilotError):
    """Raised when external API call fails."""

    def __init__(self, service_name: str, status_code: int, message: str):
        self.service_name = service_name
        self.status_code = status_code
        super().__init__(f"{service_name} error ({status_code}): {message}")


class AuthenticationError(EVECopilotError):
    """Raised when authentication fails."""
    pass


class AuthorizationError(EVECopilotError):
    """Raised when user is not authorized to access resource."""
    pass


class RepositoryError(EVECopilotError):
    """Raised when database repository operation fails."""
    pass


class ESIError(ExternalAPIError):
    """Raised when ESI API operation fails."""

    def __init__(self, message: str, status_code: int = 0):
        super().__init__(service_name="ESI", status_code=status_code, message=message)
