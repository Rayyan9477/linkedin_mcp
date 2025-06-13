"""
API client implementations for various services.

This package contains client implementations for interacting with external APIs
such as LinkedIn, OpenAI, and other third-party services.
"""
from typing import Optional

__all__ = [
    'LinkedInAPIClient',
    'OpenAIClient',
    'create_linkedin_client',
]

# Import clients for easier access
from .linkedin import LinkedInAPIClient
from .openai import OpenAIClient


def create_linkedin_client(
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
    redirect_uri: Optional[str] = None,
    access_token: Optional[str] = None,
    refresh_token: Optional[str] = None,
    timeout: int = 30,
) -> LinkedInAPIClient:
    """
    Create and configure a LinkedIn API client.
    
    This factory function simplifies the creation of a LinkedInAPIClient instance
    with common configuration options.
    
    Args:
        client_id: LinkedIn API client ID (required for OAuth)
        client_secret: LinkedIn API client secret (required for OAuth)
        redirect_uri: OAuth 2.0 redirect URI (required for OAuth)
        access_token: OAuth 2.0 access token (if already authenticated)
        refresh_token: OAuth 2.0 refresh token (if available)
        timeout: Request timeout in seconds
        
    Returns:
        LinkedInAPIClient: Configured LinkedIn API client instance
        
    Example:
        ```python
        # Create a client with OAuth credentials
        client = create_linkedin_client(
            client_id="your_client_id",
            client_secret="your_client_secret",
            redirect_uri="https://yourapp.com/callback",
        )
        
        # Or create a client with an existing access token
        client = create_linkedin_client(
            access_token="existing_access_token",
            refresh_token="existing_refresh_token",  # Optional
        )
        ```
    """
    client = LinkedInAPIClient(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        timeout=timeout,
    )
    
    # Set session state if tokens are provided
    if access_token:
        from datetime import datetime, timedelta
        from ..models.common import LinkedInSessionState
        
        # Create a session state with the provided tokens
        # Note: We don't know the expiration time, so we'll set it to 1 hour from now
        # The client will refresh the token when needed if a refresh token is provided
        client.session_state = LinkedInSessionState(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=datetime.utcnow() + timedelta(hours=1),
            token_type="Bearer",
            scope=[],  # We don't know the scopes, so we'll leave this empty
        )
    
    return client
