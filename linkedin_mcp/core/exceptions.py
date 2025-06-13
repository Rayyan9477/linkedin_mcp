"""
Core exceptions for the LinkedIn MCP application.

This module defines the base exception classes and specific exceptions
used throughout the application for consistent error handling.
"""

from typing import Any, Dict, Optional, Union

class LinkedInMCPError(Exception):
    """Base exception for all LinkedIn MCP exceptions."""
    def __init__(
        self,
        message: str = "An error occurred in the LinkedIn MCP application",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        return f"{self.message} (status_code={self.status_code})"

class APIError(LinkedInMCPError):
    """Base exception for API-related errors."""
    def __init__(
        self,
        message: str = "An API error occurred",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ):
        self.request_id = request_id
        if request_id and details is not None:
            details["request_id"] = request_id
        super().__init__(message, status_code, details)

class AuthenticationError(APIError):
    """Raised when authentication fails or credentials are invalid."""
    def __init__(
        self,
        message: str = "Authentication failed",
        status_code: int = 401,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, status_code, details)

class AuthorizationError(APIError):
    """Raised when the user is not authorized to perform an action."""
    def __init__(
        self,
        message: str = "Not authorized to perform this action",
        status_code: int = 403,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, status_code, details)

class RateLimitError(APIError):
    """Raised when rate limits are exceeded."""
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        status_code: int = 429,
        retry_after: int = 60,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.retry_after = retry_after
        details = details or {}
        details["retry_after"] = retry_after
        super().__init__(message, status_code, details)

class ValidationError(LinkedInMCPError):
    """Raised when input validation fails."""
    def __init__(
        self,
        message: str = "Validation error",
        status_code: int = 400,
        details: Optional[Dict[str, Any]] = None,
        fields: Optional[Dict[str, Any]] = None,
    ):
        self.fields = fields or {}
        if fields and details is not None:
            details["fields"] = fields
        super().__init__(message, status_code, details)

class NotFoundError(APIError):
    """Raised when a requested resource is not found."""
    def __init__(
        self,
        resource_type: str = "resource",
        resource_id: Optional[Union[str, int]] = None,
        message: Optional[str] = None,
        status_code: int = 404,
        details: Optional[Dict[str, Any]] = None,
    ):
        if message is None:
            message = f"{resource_type} not found"
            if resource_id is not None:
                message += f" with ID: {resource_id}"
        
        details = details or {}
        details["resource_type"] = resource_type
        if resource_id is not None:
            details["resource_id"] = resource_id
            
        super().__init__(message, status_code, details)

class ConflictError(APIError):
    """Raised when there's a conflict with the current state of the resource."""
    def __init__(
        self,
        message: str = "Conflict with the current state of the resource",
        status_code: int = 409,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, status_code, details)

class ServiceUnavailableError(APIError):
    """Raised when a service is temporarily unavailable."""
    def __init__(
        self,
        message: str = "Service temporarily unavailable",
        status_code: int = 503,
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.retry_after = retry_after
        details = details or {}
        if retry_after is not None:
            details["retry_after"] = retry_after
        super().__init__(message, status_code, details)

class TimeoutError(APIError):
    """Raised when a request times out."""
    def __init__(
        self,
        message: str = "Request timed out",
        status_code: int = 408,
        timeout: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.timeout = timeout
        details = details or {}
        if timeout is not None:
            details["timeout"] = timeout
        super().__init__(message, status_code, details)

class NetworkError(APIError):
    """Raised when there's a network-related error."""
    def __init__(
        self,
        message: str = "Network error occurred",
        status_code: int = 0,  # 0 indicates a client-side error
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, status_code, details)

class ConfigurationError(LinkedInMCPError):
    """Raised when there's a configuration error in the application."""
    def __init__(
        self,
        message: str = "Configuration error",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, status_code, details)

class SerializationError(LinkedInMCPError):
    """Raised when there's an error serializing or deserializing data."""
    def __init__(
        self,
        message: str = "Serialization error",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, status_code, details)

class RetryError(LinkedInMCPError):
    """Raised when the maximum number of retries is exceeded."""
    def __init__(
        self,
        message: str = "Maximum number of retries exceeded",
        status_code: int = 500,
        last_exception: Optional[Exception] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.last_exception = last_exception
        details = details or {}
        if last_exception is not None:
            details["last_exception"] = str(last_exception)
        super().__init__(message, status_code, details)

class ResourceExhaustedError(APIError):
    """Raised when a resource has been exhausted."""
    def __init__(
        self,
        message: str = "Resource has been exhausted",
        status_code: int = 429,
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.retry_after = retry_after
        details = details or {}
        if retry_after is not None:
            details["retry_after"] = retry_after
        super().__init__(message, status_code, details)

class UnsupportedOperationError(APIError):
    """Raised when an operation is not supported."""
    def __init__(
        self,
        message: str = "This operation is not supported",
        status_code: int = 501,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, status_code, details)

class QuotaExceededError(ResourceExhaustedError):
    """Raised when a quota has been exceeded."""
    def __init__(
        self,
        message: str = "Quota exceeded",
        status_code: int = 429,
        quota_limit: Optional[int] = None,
        quota_used: Optional[int] = None,
        quota_reset: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.quota_limit = quota_limit
        self.quota_used = quota_used
        self.quota_reset = quota_reset
        
        details = details or {}
        if quota_limit is not None:
            details["quota_limit"] = quota_limit
        if quota_used is not None:
            details["quota_used"] = quota_used
        if quota_reset is not None:
            details["quota_reset"] = quota_reset
            
        super().__init__(message, status_code, None, details)
