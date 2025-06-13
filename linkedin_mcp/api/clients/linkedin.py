"""
LinkedIn API Client

This module provides a high-level client for interacting with the LinkedIn API.
It handles authentication, request/response serialization, and error handling.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Type, TypeVar, Union, cast

import aiohttp
from pydantic import ValidationError

from ...core.exceptions import (
    APIError,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    RateLimitError,
    ServiceUnavailableError,
    TimeoutError,
    NetworkError,
    ValidationError as LinkedInValidationError,
    RetryError,
    QuotaExceededError,
)
from ...utils.rate_limiter import RateLimiter
from ...utils.retry import retry, RetryConfig
from ..models.common import LinkedInSessionState, JobDetails, Profile
from ..models.requests import (
    JobSearchRequest,
    ProfileRequest,
    ApplyToJobRequest,
    SendMessageRequest,
    ConnectionRequest,
    PostEngagementRequest,
)
from ..models.responses import (
    JobSearchResponse,
    ProfileResponse,
    ApplyToJobResponse,
    MessageResponse,
    ConnectionResponse,
    PostEngagementResponse,
    ErrorResponse,
    ApiResponse,
)

logger = logging.getLogger(__name__)
T = TypeVar('T')

# Default retry configuration for LinkedIn API calls
DEFAULT_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    initial_delay=1.0,
    max_delay=10.0,
    factor=2.0,
    jitter=0.2,
    retry_on_status_codes=[429, 500, 502, 503, 504],
)

class LinkedInAPIClient:
    """
    A client for interacting with the LinkedIn API.
    
    This client handles authentication, request/response serialization, and error handling
    for the LinkedIn API. It provides methods for common operations like searching for jobs,
    viewing profiles, sending messages, and more.
    """
    
    BASE_URL = "https://api.linkedin.com/v2"
    AUTH_URL = "https://www.linkedin.com/oauth/v2"
    
    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        redirect_uri: Optional[str] = None,
        session: Optional[aiohttp.ClientSession] = None,
        rate_limiter: Optional[RateLimiter] = None,
        timeout: int = 30,
    ):
        """
        Initialize the LinkedIn API client.
        
        Args:
            client_id: LinkedIn API client ID
            client_secret: LinkedIn API client secret
            redirect_uri: OAuth 2.0 redirect URI
            session: Optional aiohttp ClientSession to use
            rate_limiter: Optional rate limiter instance
            timeout: Request timeout in seconds
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self._session = session
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.rate_limiter = rate_limiter or RateLimiter(
            max_requests=30,  # LinkedIn's standard rate limit
            window=60,  # Per minute
            retry_attempts=3,
        )
        self._session_state: Optional[LinkedInSessionState] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self.timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._session and not self._session.closed:
            await self._session.close()
    
    @property
    def session_state(self) -> Optional[LinkedInSessionState]:
        """Get the current session state."""
        return self._session_state
    
    @session_state.setter
    def session_state(self, value: LinkedInSessionState):
        """Set the session state."""
        self._session_state = value
    
    def is_authenticated(self) -> bool:
        """Check if the client is authenticated."""
        if not self._session_state or not self._session_state.access_token:
            return False
            
        # Check if token is expired
        if self._session_state.expires_at and self._session_state.expires_at < datetime.utcnow():
            return False
            
        return True
    
    def get_authorization_url(
        self,
        state: Optional[str] = None,
        scopes: Optional[List[str]] = None,
    ) -> str:
        """
        Generate an OAuth 2.0 authorization URL.
        
        Args:
            state: Optional state parameter for CSRF protection
            scopes: List of OAuth scopes to request
            
        Returns:
            str: Authorization URL
        """
        if not self.client_id or not self.redirect_uri:
            raise LinkedInValidationError("Client ID and redirect URI must be set")
            
        scopes = scopes or [
            'r_liteprofile',
            'r_emailaddress',
            'w_member_social',
            'r_basicprofile',
            'rw_company_admin',
            'w_share',
            'r_organization_social',
            'w_organization_social',
            'rw_organization_admin',
            'r_1st_connections',
        ]
        
        params = {
            'response_type': 'code',
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scope': ' '.join(scopes),
        }
        
        if state:
            params['state'] = state
            
        query = '&'.join(f"{k}={v}" for k, v in params.items())
        return f"{self.AUTH_URL}/authorization?{query}"
    
    @retry(config=DEFAULT_RETRY_CONFIG)
    async def exchange_code_for_token(self, code: str) -> LinkedInSessionState:
        """
        Exchange an authorization code for an access token.
        
        Args:
            code: Authorization code from the OAuth 2.0 redirect
            
        Returns:
            LinkedInSessionState with access and refresh tokens
            
        Raises:
            AuthenticationError: If the code exchange fails
            ValidationError: If the response is invalid
        """
        if not self.client_id or not self.client_secret or not self.redirect_uri:
            raise LinkedInValidationError(
                "client_id, client_secret, and redirect_uri must be set"
            )
            
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': self.redirect_uri,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
        }
        
        try:
            async with self._session.post(
                f"{self.AUTH_URL}/accessToken",
                data=data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            ) as response:
                response_data = await response.json()
                
                if response.status != 200:
                    error = response_data.get('error', 'unknown_error')
                    description = response_data.get('error_description', 'No error description provided')
                    raise AuthenticationError(
                        f"Failed to exchange code for token: {error} - {description}",
                        status_code=response.status,
                        details=response_data
                    )
                
                try:
                    self._session_state = LinkedInSessionState(
                        access_token=response_data['access_token'],
                        expires_at=datetime.utcnow() + timedelta(seconds=response_data.get('expires_in', 3600)),
                        refresh_token=response_data.get('refresh_token'),
                        token_type=response_data.get('token_type', 'bearer'),
                        scope=response_data.get('scope', '').split(),
                    )
                    return self._session_state
                    
                except (KeyError, ValidationError) as e:
                    raise LinkedInValidationError(
                        "Invalid response from LinkedIn API",
                        details={"error": str(e), "response": response_data}
                    )
        except aiohttp.ClientError as e:
            raise NetworkError("Network error during token exchange") from e
    
    @retry(config=DEFAULT_RETRY_CONFIG)
    async def refresh_access_token(self, refresh_token: Optional[str] = None) -> LinkedInSessionState:
        """
        Refresh an expired access token using a refresh token.
        
        Args:
            refresh_token: Optional refresh token (uses instance token if not provided)
            
        Returns:
            Updated LinkedInSessionState with new tokens
            
        Raises:
            AuthenticationError: If the token refresh fails
            ValidationError: If the response is invalid
        """
        refresh_token = refresh_token or (self._session_state.refresh_token if self._session_state else None)
        if not refresh_token:
            raise AuthenticationError("No refresh token available")
            
        if not self.client_id or not self.client_secret:
            raise LinkedInValidationError("client_id and client_secret must be set to refresh token")
        
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
        }
        
        try:
            async with self._session.post(
                f"{self.AUTH_URL}/accessToken",
                data=data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            ) as response:
                response_data = await response.json()
                
                if response.status != 200:
                    error = response_data.get('error', 'unknown_error')
                    description = response_data.get('error_description', 'No error description provided')
                    raise AuthenticationError(
                        f"Failed to refresh access token: {error} - {description}",
                        status_code=response.status,
                        details=response_data
                    )
                
                try:
                    self._session_state = LinkedInSessionState(
                        access_token=response_data['access_token'],
                        expires_at=datetime.utcnow() + timedelta(seconds=response_data.get('expires_in', 3600)),
                        refresh_token=response_data.get('refresh_token', refresh_token),  # Use new refresh token if provided
                        token_type=response_data.get('token_type', 'bearer'),
                        scope=response_data.get('scope', '').split(),
                    )
                    return self._session_state
                    
                except (KeyError, ValidationError) as e:
                    raise LinkedInValidationError(
                        "Invalid response from LinkedIn API",
                        details={"error": str(e), "response": response_data}
                    )
        except aiohttp.ClientError as e:
            raise NetworkError("Network error during token refresh") from e
    
    async def _ensure_authenticated(self):
        """Ensure the client is authenticated, refreshing the token if necessary."""
        if not self.is_authenticated():
            if self._session_state and self._session_state.refresh_token:
                await self.refresh_access_token()
            else:
                raise AuthenticationError("Not authenticated and no refresh token available")
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        response_model: Type[T],
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        requires_auth: bool = True,
    ) -> T:
        """
        Make an authenticated request to the LinkedIn API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (without base URL)
            response_model: Pydantic model to parse the response into
            params: Query parameters
            json_data: Request body as JSON
            headers: Additional headers
            requires_auth: Whether the endpoint requires authentication
            
        Returns:
            Parsed response as the specified model
            
        Raises:
            LinkedInAPIError: For API errors
            LinkedInAuthError: For authentication errors
            LinkedInRateLimitError: For rate limit errors
        """
        if requires_auth:
            await self._ensure_authenticated()
        
        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"
        
        # Prepare headers
        request_headers = {
            'Content-Type': 'application/json',
            'X-Restli-Protocol-Version': '2.0.0',
            'User-Agent': 'linkedin-mcp/1.0.0',
        }
        
        if requires_auth and self._session_state:
            request_headers['Authorization'] = f"Bearer {self._session_state.access_token}"
        
        if headers:
            request_headers.update(headers)
        
        # Make the request with rate limiting
        try:
            await self.rate_limiter.acquire()
            
            async with self._session.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
                headers=request_headers,
            ) as response:
                response_data = await response.json()
                
                # Handle rate limiting
                if response.status == 429:
                    retry_after = int(response.headers.get('Retry-After', 60))
                    raise RateLimitError(
                        "Rate limit exceeded",
                        status_code=response.status,
                        retry_after=retry_after,
                        details=response_data,
                    )
                
                # Handle authentication errors
                if response.status == 401:
                    raise AuthenticationError(
                        "Invalid or expired access token",
                        status_code=response.status,
                        details=response_data,
                    )
                
                # Handle authorization errors
                if response.status == 403:
                    raise AuthorizationError(
                        "Insufficient permissions",
                        status_code=response.status,
                        details=response_data,
                    )
                
                # Handle not found errors
                if response.status == 404:
                    raise NotFoundError(
                        "Resource not found",
                        status_code=response.status,
                        details=response_data,
                    )
                
                # Handle other error status codes
                if response.status >= 400:
                    error_message = response_data.get('message', 'Unknown error')
                    error_code = response_data.get('code', 'unknown_error')
                    
                    if response.status == 429:
                        retry_after = int(response.headers.get('Retry-After', 60))
                        raise RateLimitError(
                            f"Rate limit exceeded: {error_message}",
                            status_code=response.status,
                            retry_after=retry_after,
                            details=response_data,
                        )
                    elif response.status >= 500:
                        raise ServiceUnavailableError(
                            f"Server error: {error_message}",
                            status_code=response.status,
                            details=response_data,
                        )
                    else:
                        raise APIError(
                            f"API error: {error_message}",
                            status_code=response.status,
                            details=response_data,
                        )
                
                # Parse and validate the response
                try:
                    if isinstance(response_data, dict):
                        return response_model(**response_data)
                    elif isinstance(response_data, list):
                        # Handle paginated responses
                        return response_model(jobs=response_data)
                    else:
                        raise LinkedInValidationError(
                            f"Unexpected response format: {type(response_data).__name__}",
                            details={"response": response_data},
                        )
                except ValidationError as e:
                    raise LinkedInValidationError(
                        "Failed to validate response",
                        details={"error": str(e), "response": response_data},
                    )
                
        except aiohttp.ClientError as e:
            if isinstance(e, aiohttp.ClientConnectionError):
                raise NetworkError("Failed to connect to LinkedIn API") from e
            elif isinstance(e, asyncio.TimeoutError):
                raise TimeoutError("Request to LinkedIn API timed out") from e
            else:
                raise NetworkError("Network error occurred") from e
        finally:
            self.rate_limiter.release()
    
    # High-level API methods
    
    async def search_jobs(self, request: JobSearchRequest) -> JobSearchResponse:
        """
        Search for jobs on LinkedIn.
        
        Args:
            request: Job search parameters
            
        Returns:
            JobSearchResponse containing matching jobs
        """
        params = request.dict(exclude_none=True)
        return await self._make_request(
            method="GET",
            endpoint="/jobs",
            response_model=JobSearchResponse,
            params=params,
        )
    
    async def get_job(self, job_id: str) -> JobDetails:
        """
        Get details for a specific job.
        
        Args:
            job_id: LinkedIn job ID
            
        Returns:
            JobDetails for the specified job
        """
        return await self._make_request(
            method="GET",
            endpoint=f"/jobs/{job_id}",
            response_model=JobDetails,
        )
    
    async def get_profile(self, request: Optional[ProfileRequest] = None) -> ProfileResponse:
        """
        Get profile information for the current user or a specified profile.
        
        Args:
            request: Profile request parameters
            
        Returns:
            ProfileResponse containing the requested profile information
        """
        params = {}
        if request:
            params = request.dict(exclude_none=True)
            
        endpoint = "/me" if not request or not request.profile_id else f"/people/{request.profile_id}"
        
        return await self._make_request(
            method="GET",
            endpoint=endpoint,
            response_model=ProfileResponse,
            params=params,
        )
    
    async def apply_to_job(self, request: ApplyToJobRequest) -> ApplyToJobResponse:
        """
        Apply to a job on LinkedIn.
        
        Args:
            request: Job application details
            
        Returns:
            ApplyToJobResponse with application status
        """
        return await self._make_request(
            method="POST",
            endpoint=f"/jobs/{request.job_id}/apply",
            response_model=ApplyToJobResponse,
            json_data=request.dict(exclude_none=True, exclude={"job_id"}),
        )
    
    async def send_message(self, request: SendMessageRequest) -> MessageResponse:
        """
        Send a message to a connection on LinkedIn.
        
        Args:
            request: Message details
            
        Returns:
            MessageResponse with message status
        """
        return await self._make_request(
            method="POST",
            endpoint="/messages",
            response_model=MessageResponse,
            json_data=request.dict(exclude_none=True),
        )
    
    async def connect(self, request: ConnectionRequest) -> ConnectionResponse:
        """
        Send a connection request to another LinkedIn member.
        
        Args:
            request: Connection request details
            
        Returns:
            ConnectionResponse with request status
        """
        return await self._make_request(
            method="POST",
            endpoint="/relationships/invitations",
            response_model=ConnectionResponse,
            json_data=request.dict(exclude_none=True),
        )
    
    async def engage_with_post(self, request: PostEngagementRequest) -> PostEngagementResponse:
        """
        Engage with a post (like, comment, share, react).
        
        Args:
            request: Engagement details
            
        Returns:
            PostEngagementResponse with engagement status
        """
        endpoint = f"/socialActions/{request.post_urn}/"
        
        if request.action == 'like':
            endpoint += "likes"
        elif request.action == 'comment':
            endpoint += "comments"
        elif request.action == 'share':
            endpoint += "shares"
        elif request.action == 'react':
            endpoint += f"reactions?action={request.reaction_type}"
        else:
            raise LinkedInValidationError(f"Invalid engagement action: {request.action}")
        
        return await self._make_request(
            method="POST",
            endpoint=endpoint,
            response_model=PostEngagementResponse,
            json_data=request.dict(exclude_none=True, exclude={"post_urn", "action", "reaction_type"}),
        )
