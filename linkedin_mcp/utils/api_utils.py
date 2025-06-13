"""
Utility functions for handling LinkedIn API requests and responses.

This module provides utilities for making HTTP requests to the LinkedIn API,
handling responses, and managing API-specific concerns like pagination,
error handling, and rate limiting.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Type, TypeVar, Union, cast

import aiohttp
from pydantic import BaseModel, ValidationError, parse_obj_as

from ..core.protocol import ErrorResponse, MCPRequest, SuccessResponse
from .rate_limiter import (
    DEFAULT_LINKEDIN_RATE_LIMITER,
    LOGIN_RATE_LIMITER,
    SEARCH_RATE_LIMITER,
    RateLimitExceeded,
)
from .retry import (
    NETWORK_RETRY_CONFIG,
    RATE_LIMIT_RETRY_CONFIG,
    retry,
    RetryError,
)

logger = logging.getLogger("linkedin-mcp.api_utils")

# Type variables for generic type hints
T = TypeVar('T', bound=BaseModel)
JsonType = Union[Dict[str, Any], List[Any], str, int, float, bool, None]

class LinkedInAPIError(Exception):
    """Base exception for LinkedIn API errors."""
    def __init__(self, message: str, status_code: Optional[int] = None, 
                 error_data: Optional[Dict[str, Any]] = None):
        self.status_code = status_code
        self.error_data = error_data or {}
        super().__init__(message)

class LinkedInAuthError(LinkedInAPIError):
    """Raised when there's an authentication or authorization error."""
    pass

class LinkedInRateLimitError(LinkedInAPIError):
    """Raised when rate limits are exceeded."""
    def __init__(self, retry_after: Optional[float] = None, **kwargs):
        self.retry_after = retry_after
        super().__init__(**kwargs)

class LinkedInAPIResponse:
    """Wrapper for LinkedIn API responses with utilities for parsing and validation."""
    
    def __init__(
        self, 
        status_code: int, 
        headers: Dict[str, str], 
        content: bytes,
        request: Optional[Dict[str, Any]] = None
    ):
        self.status_code = status_code
        self.headers = headers
        self._content = content
        self.request = request or {}
        self._json: Optional[JsonType] = None
        self._text: Optional[str] = None
    
    @property
    def text(self) -> str:
        """Get the response content as text."""
        if self._text is None:
            self._text = self._content.decode('utf-8', errors='replace')
        return self._text
    
    @property
    def json(self) -> JsonType:
        """Parse the response content as JSON."""
        if self._json is None:
            try:
                self._json = json.loads(self.text)
            except json.JSONDecodeError as e:
                logger.error(
                    f"Failed to parse JSON response: {e}\n"
                    f"Status: {self.status_code}\n"
                    f"Headers: {self.headers}\n"
                    f"Content: {self.text[:1000]}"
                )
                raise LinkedInAPIError("Invalid JSON response from LinkedIn API") from e
        return self._json
    
    def raise_for_status(self) -> None:
        """Raise an exception if the response indicates an error."""
        if 400 <= self.status_code < 600:
            error_message = f"HTTP {self.status_code}"
            error_data = {}
            
            try:
                error_json = self.json
                if isinstance(error_json, dict):
                    error_message = error_json.get('message', error_message)
                    error_data = {
                        'error': error_json.get('error'),
                        'error_description': error_json.get('error_description'),
                        'code': error_json.get('code'),
                        'request_id': self.headers.get('x-li-request-id'),
                        'headers': dict(self.headers),
                    }
            except Exception:
                pass
            
            if self.status_code == 401:
                raise LinkedInAuthError(
                    f"Authentication failed: {error_message}",
                    status_code=self.status_code,
                    error_data=error_data
                )
            elif self.status_code == 429:
                retry_after = float(self.headers.get('Retry-After', 60))
                raise LinkedInRateLimitError(
                    f"Rate limit exceeded: {error_message}",
                    status_code=self.status_code,
                    error_data=error_data,
                    retry_after=retry_after
                )
            else:
                raise LinkedInAPIError(
                    error_message,
                    status_code=self.status_code,
                    error_data=error_data
                )
    
    def parse_as(self, model: Type[T]) -> T:
        """Parse the response as a Pydantic model."""
        try:
            if isinstance(self.json, dict):
                return model.parse_obj(self.json)
            else:
                raise ValueError("Expected a JSON object in the response")
        except ValidationError as e:
            logger.error(f"Failed to validate response as {model.__name__}: {e}")
            raise LinkedInAPIError("Failed to parse API response") from e
    
    def parse_list(self, model: Type[T]) -> List[T]:
        """Parse the response as a list of Pydantic models."""
        try:
            if isinstance(self.json, list):
                return [model.parse_obj(item) for item in self.json]
            elif isinstance(self.json, dict) and 'elements' in self.json:
                return [model.parse_obj(item) for item in self.json['elements']]
            else:
                raise ValueError("Expected a JSON array or object with 'elements' in the response")
        except (ValidationError, KeyError) as e:
            logger.error(f"Failed to parse response as List[{model.__name__}]: {e}")
            raise LinkedInAPIError("Failed to parse API response") from e

class LinkedInAPIClient:
    """HTTP client for making requests to the LinkedIn API."""
    
    BASE_URL = "https://api.linkedin.com/v2"
    
    def __init__(
        self,
        access_token: Optional[str] = None,
        session: Optional[aiohttp.ClientSession] = None,
        timeout: int = 30,
    ):
        """
        Initialize the LinkedIn API client.
        
        Args:
            access_token: OAuth 2.0 access token
            session: Optional aiohttp ClientSession to use
            timeout: Request timeout in seconds
        """
        self.access_token = access_token
        self._session = session
        self.timeout = aiohttp.ClientTimeout(total=timeout)
    
    async def __aenter__(self):
        if self._session is None:
            self._session = aiohttp.ClientSession(timeout=self.timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session and not self._session.closed:
            await self._session.close()
    
    def _get_headers(self, headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Get default headers for API requests."""
        default_headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'X-Restli-Protocol-Version': '2.0.0',
            'User-Agent': 'linkedin-mcp/1.0.0',
        }
        
        if self.access_token:
            default_headers['Authorization'] = f'Bearer {self.access_token}'
        
        if headers:
            default_headers.update(headers)
            
        return default_headers
    
    @retry(**NETWORK_RETRY_CONFIG.dict())
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        rate_limiter: Any = DEFAULT_LINKEDIN_RATE_LIMITER,
    ) -> LinkedInAPIResponse:
        """
        Make an HTTP request to the LinkedIn API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (without base URL)
            params: Query parameters
            json_data: Request body as JSON
            headers: Additional headers
            rate_limiter: Rate limiter to use for this request
            
        Returns:
            LinkedInAPIResponse with the API response
        """
        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"
        headers = self._get_headers(headers)
        
        # Apply rate limiting
        try:
            async with rate_limiter:
                async with self._session.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_data,
                    headers=headers,
                ) as response:
                    content = await response.read()
                    api_response = LinkedInAPIResponse(
                        status_code=response.status,
                        headers=dict(response.headers),
                        content=content,
                        request={
                            'method': method,
                            'url': url,
                            'params': params,
                            'json': json_data,
                            'headers': {k: v for k, v in headers.items() 
                                     if k.lower() != 'authorization'},
                        }
                    )
                    
                    # Check for errors
                    api_response.raise_for_status()
                    return api_response
                    
        except aiohttp.ClientError as e:
            logger.error(f"Request failed: {e}")
            raise LinkedInAPIError(f"Request failed: {e}")
        except asyncio.TimeoutError as e:
            logger.error(f"Request timed out: {e}")
            raise LinkedInAPIError("Request timed out") from e
    
    async def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        rate_limiter: Any = DEFAULT_LINKEDIN_RATE_LIMITER,
    ) -> LinkedInAPIResponse:
        """Make a GET request to the LinkedIn API."""
        return await self._make_request(
            'GET',
            endpoint,
            params=params,
            headers=headers,
            rate_limiter=rate_limiter,
        )
    
    async def post(
        self,
        endpoint: str,
        json_data: Dict[str, Any],
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        rate_limiter: Any = DEFAULT_LINKEDIN_RATE_LIMITER,
    ) -> LinkedInAPIResponse:
        """Make a POST request to the LinkedIn API."""
        return await self._make_request(
            'POST',
            endpoint,
            params=params,
            json_data=json_data,
            headers=headers,
            rate_limiter=rate_limiter,
        )
    
    async def put(
        self,
        endpoint: str,
        json_data: Dict[str, Any],
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        rate_limiter: Any = DEFAULT_LINKEDIN_RATE_LIMITER,
    ) -> LinkedInAPIResponse:
        """Make a PUT request to the LinkedIn API."""
        return await self._make_request(
            'PUT',
            endpoint,
            params=params,
            json_data=json_data,
            headers=headers,
            rate_limiter=rate_limiter,
        )
    
    async def delete(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        rate_limiter: Any = DEFAULT_LINKEDIN_RATE_LIMITER,
    ) -> LinkedInAPIResponse:
        """Make a DELETE request to the LinkedIn API."""
        return await self._make_request(
            'DELETE',
            endpoint,
            params=params,
            headers=headers,
            rate_limiter=rate_limiter,
        )

# Helper functions for common operations

def create_mcp_response(
    request: MCPRequest,
    result: Any = None,
    error: Optional[Exception] = None
) -> Union[SuccessResponse, ErrorResponse]:
    """
    Create a properly formatted MCP response.
    
    Args:
        request: The original MCP request
        result: Result data for successful responses
        error: Exception for error responses
        
    Returns:
        SuccessResponse or ErrorResponse
    """
    if error is not None:
        if isinstance(error, LinkedInAPIError):
            return ErrorResponse(
                id=request.id,
                error={
                    'code': error.status_code or -32000,
                    'message': str(error),
                    'data': error.error_data,
                }
            )
        else:
            return ErrorResponse(
                id=request.id,
                error={
                    'code': -32000,
                    'message': str(error),
                }
            )
    
    return SuccessResponse(id=request.id, result=result)

def validate_mcp_request(
    request: MCPRequest,
    required_params: Optional[List[str]] = None,
    allowed_methods: Optional[List[str]] = None
) -> None:
    """
    Validate an MCP request.
    
    Args:
        request: The MCP request to validate
        required_params: List of required parameter names
        allowed_methods: List of allowed method names
        
    Raises:
        ValueError: If validation fails
    """
    if not request.method:
        raise ValueError("Method is required")
    
    if allowed_methods and request.method not in allowed_methods:
        raise ValueError(f"Method '{request.method}' is not allowed")
    
    if required_params and request.params:
        missing = [p for p in required_params if p not in request.params]
        if missing:
            raise ValueError(f"Missing required parameters: {', '.join(missing)}")
