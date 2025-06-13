"""
Authentication utilities for the LinkedIn API.

This module provides helper functions for handling OAuth 2.0 authentication
flows with the LinkedIn API, including token management and refresh logic.
"""

import asyncio
import logging
import webbrowser
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, Union, Any, Callable, Awaitable

from ..core.exceptions import (
    AuthenticationError,
    ConfigurationError,
    NetworkError,
    ValidationError as LinkedInValidationError,
)
from ..api.clients import create_linkedin_client, LinkedInAPIClient
from ..api.models.common import LinkedInSessionState

logger = logging.getLogger(__name__)

# Type alias for callback functions
AuthCallback = Callable[[LinkedInSessionState], Awaitable[None]]

async def authenticate_interactive(
    client_id: str,
    client_secret: str,
    redirect_uri: str,
    scopes: Optional[list[str]] = None,
    state: Optional[str] = None,
    timeout: int = 300,
    open_browser: bool = True,
    callback: Optional[AuthCallback] = None,
) -> LinkedInAPIClient:
    """
    Perform interactive OAuth 2.0 authentication with LinkedIn.
    
    This function handles the complete OAuth 2.0 authorization code flow,
    including starting a temporary HTTP server to handle the redirect.
    
    Args:
        client_id: LinkedIn API client ID
        client_secret: LinkedIn API client secret
        redirect_uri: OAuth 2.0 redirect URI (must match LinkedIn app settings)
        scopes: List of OAuth scopes to request
        state: Optional state parameter for CSRF protection
        timeout: Maximum time to wait for authentication to complete (seconds)
        open_browser: Whether to automatically open the browser for authentication
        callback: Optional async callback function that receives the session state
        
    Returns:
        LinkedInAPIClient: Authenticated LinkedIn API client
        
    Raises:
        ConfigurationError: If required parameters are missing
        AuthenticationError: If authentication fails
        TimeoutError: If authentication times out
        
    Example:
        ```python
        client = await authenticate_interactive(
            client_id="your_client_id",
            client_secret="your_client_secret",
            redirect_uri="http://localhost:8080/callback",
            scopes=["r_liteprofile", "r_emailaddress"],
            open_browser=True,
        )
        ```
    """
    if not all([client_id, client_secret, redirect_uri]):
        raise ConfigurationError("client_id, client_secret, and redirect_uri are required")
    
    # Create a client instance
    client = create_linkedin_client(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
    )
    
    # Generate the authorization URL
    auth_url = client.get_authorization_url(
        state=state,
        scopes=scopes,
    )
    
    # Parse the redirect URI to get the port
    from urllib.parse import urlparse
    parsed_uri = urlparse(redirect_uri)
    host = parsed_uri.hostname or 'localhost'
    port = parsed_uri.port or 8080
    
    # Start a temporary HTTP server to handle the OAuth callback
    from http.server import HTTPServer, BaseHTTPRequestHandler
    from urllib.parse import parse_qs, urlparse
    
    auth_code = None
    auth_error = None
    
    class OAuthHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            nonlocal auth_code, auth_error
            
            # Parse the query parameters
            query = urlparse(self.path).query
            params = parse_qs(query)
            
            if 'code' in params:
                auth_code = params['code'][0]
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(
                    b'<html><body><h1>Authentication successful!</h1>'
                    b'<p>You can close this window and return to the application.</p>'
                    b'</body></html>'
                )
            else:
                auth_error = params.get('error', ['Unknown error'])[0]
                error_desc = params.get('error_description', [''])[0]
                self.send_response(400)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(
                    f'<html><body><h1>Authentication failed</h1>'
                    f'<p>Error: {auth_error}</p>'
                    f'<p>{error_desc}</p>'
                    f'</body></html>'.encode('utf-8')
                )
            
            # Shutdown the server after handling the request
            def shutdown():
                self.server.shutdown()
            
            self.server.shutdown = shutdown
    
    # Start the server in a separate thread
    import threading
    
    def run_server():
        server = HTTPServer((host, port), OAuthHandler)
        server.timeout = timeout
        server.auth_code = None
        server.serve_forever()
    
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    try:
        # Open the browser for authentication
        if open_browser:
            webbrowser.open(auth_url)
            print(f"Please complete the authentication in your browser. If it doesn't open, visit: {auth_url}")
        else:
            print(f"Please visit this URL to authenticate: {auth_url}")
        
        # Wait for the server to be ready
        import time
        time.sleep(1)
        
        # Wait for the authentication to complete or timeout
        server_thread.join(timeout=timeout)
        
        if auth_error:
            raise AuthenticationError(f"Authentication failed: {auth_error}")
        
        if not auth_code:
            raise TimeoutError("Authentication timed out or was cancelled")
        
        # Exchange the authorization code for an access token
        session_state = await client.exchange_code_for_token(auth_code)
        
        # Call the callback if provided
        if callback:
            await callback(session_state)
        
        return client
        
    finally:
        # Ensure the server is shut down
        if 'server' in locals():
            try:
                server.shutdown()
                server.server_close()
            except Exception as e:
                logger.warning(f"Error shutting down server: {e}")


async def refresh_token_if_needed(
    client: LinkedInAPIClient,
    min_valid_seconds: int = 300,
) -> bool:
    """
    Refresh the access token if it's expired or about to expire.
    
    Args:
        client: LinkedIn API client instance
        min_valid_seconds: Minimum number of seconds the token should be valid for
        
    Returns:
        bool: True if the token was refreshed, False otherwise
        
    Raises:
        AuthenticationError: If token refresh fails
    """
    if not client.session_state or not client.session_state.access_token:
        raise AuthenticationError("No access token available")
    
    # Check if token is expired or about to expire
    now = datetime.utcnow()
    expires_at = client.session_state.expires_at or now
    
    if (expires_at - now) > timedelta(seconds=min_valid_seconds):
        return False  # Token is still valid
    
    # Try to refresh the token if we have a refresh token
    if not client.session_state.refresh_token:
        raise AuthenticationError("Token expired and no refresh token available")
    
    try:
        await client.refresh_access_token()
        return True
    except Exception as e:
        raise AuthenticationError(f"Failed to refresh access token: {str(e)}") from e


def get_authorization_url(
    client_id: str,
    redirect_uri: str,
    scopes: Optional[list[str]] = None,
    state: Optional[str] = None,
) -> str:
    """
    Generate an OAuth 2.0 authorization URL for LinkedIn authentication.
    
    Args:
        client_id: LinkedIn API client ID
        redirect_uri: OAuth 2.0 redirect URI
        scopes: List of OAuth scopes to request
        state: Optional state parameter for CSRF protection
        
    Returns:
        str: Authorization URL
    """
    # Create a temporary client just to generate the URL
    temp_client = create_linkedin_client(
        client_id=client_id,
        redirect_uri=redirect_uri,
    )
    
    return temp_client.get_authorization_url(
        state=state,
        scopes=scopes,
    )


async def exchange_code_for_tokens(
    client_id: str,
    client_secret: str,
    redirect_uri: str,
    code: str,
) -> LinkedInSessionState:
    """
    Exchange an authorization code for an access token.
    
    Args:
        client_id: LinkedIn API client ID
        client_secret: LinkedIn API client secret
        redirect_uri: OAuth 2.0 redirect URI (must match the one used in the authorization request)
        code: Authorization code from the OAuth 2.0 redirect
        
    Returns:
        LinkedInSessionState: Session state with access and refresh tokens
        
    Raises:
        AuthenticationError: If the code exchange fails
    """
    client = create_linkedin_client(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
    )
    
    try:
        return await client.exchange_code_for_token(code)
    except Exception as e:
        raise AuthenticationError(f"Failed to exchange code for token: {str(e)}") from e


def create_client_from_session_state(
    session_state: Union[Dict[str, Any], LinkedInSessionState],
    **kwargs,
) -> LinkedInAPIClient:
    """
    Create a LinkedIn API client from a session state.
    
    Args:
        session_state: Session state dictionary or LinkedInSessionState instance
        **kwargs: Additional arguments to pass to the client constructor
        
    Returns:
        LinkedInAPIClient: Configured LinkedIn API client
    """
    if isinstance(session_state, dict):
        session_state = LinkedInSessionState(**session_state)
    
    client = create_linkedin_client(
        client_id=kwargs.get('client_id'),
        client_secret=kwargs.get('client_secret'),
        redirect_uri=kwargs.get('redirect_uri'),
        access_token=session_state.access_token,
        refresh_token=session_state.refresh_token,
        timeout=kwargs.get('timeout', 30),
    )
    
    # Set the session state to ensure all fields are preserved
    client.session_state = session_state
    
    return client
