"""Exception hierarchy for LinkedIn MCP server.

Seven focused exceptions replacing 18+ duplicated classes across the old codebase.
"""

from typing import Any


class LinkedInMCPError(Exception):
    """Base exception for all LinkedIn MCP errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)


class AuthenticationError(LinkedInMCPError):
    """LinkedIn authentication failed."""


class LinkedInAPIError(LinkedInMCPError):
    """Error communicating with LinkedIn API."""


class RateLimitError(LinkedInAPIError):
    """LinkedIn rate limit exceeded."""

    def __init__(self, message: str = "Rate limit exceeded", retry_after: int = 60):
        self.retry_after = retry_after
        super().__init__(message, {"retry_after": retry_after})


class NotFoundError(LinkedInMCPError):
    """Requested resource not found on LinkedIn."""

    def __init__(self, resource_type: str, resource_id: str):
        self.resource_type = resource_type
        self.resource_id = resource_id
        super().__init__(
            f"{resource_type} not found: {resource_id}",
            {"resource_type": resource_type, "resource_id": resource_id},
        )


class AIProviderError(LinkedInMCPError):
    """Error from AI provider (Anthropic Claude)."""


class TemplateError(LinkedInMCPError):
    """Template rendering error."""
