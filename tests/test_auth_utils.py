"""
Tests for the authentication utilities.

This module contains unit tests for the authentication helper functions.
"""

import asyncio
from datetime import datetime, timedelta
from unittest import TestCase, mock, IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from linkedin_mcp.api.clients.linkedin import LinkedInAPIClient
from linkedin_mcp.api.models.common import LinkedInSessionState
from linkedin_mcp.utils.auth import (
    authenticate_interactive,
    refresh_token_if_needed,
    get_authorization_url,
    exchange_code_for_tokens,
    create_client_from_session_state,
)
from linkedin_mcp.core.exceptions import AuthenticationError

class TestAuthUtils(IsolatedAsyncioTestCase):
    """Test cases for authentication utilities."""
    
    async def asyncSetUp(self):
        """Set up test fixtures."""
        self.client_id = "test_client_id"
        self.client_secret = "test_client_secret"
        self.redirect_uri = "http://localhost:8080/callback"
        self.scopes = ["r_liteprofile", "r_emailaddress"]
        
        # Create a mock LinkedInAPIClient
        self.mock_client = AsyncMock(spec=LinkedInAPIClient)
        self.mock_client.client_id = self.client_id
        self.mock_client.client_secret = self.client_secret
        self.mock_client.redirect_uri = self.redirect_uri
        
        # Patch the create_linkedin_client function
        self.patcher = patch(
            "linkedin_mcp.utils.auth.create_linkedin_client",
            return_value=self.mock_client
        )
        self.mock_create_client = self.patcher.start()
    
    async def asyncTearDown(self):
        """Clean up after tests."""
        self.patcher.stop()
    
    @patch("webbrowser.open")
    @patch("http.server.HTTPServer")
    async def test_authenticate_interactive_success(self, mock_server, mock_webbrowser):
        """Test interactive authentication flow."""
        # Set up mock server
        mock_server_instance = MagicMock()
        mock_server.return_value = mock_server_instance
        
        # Set up mock request handler
        mock_request_handler = MagicMock()
        mock_request_handler.params = {"code": ["test_auth_code"]}
        mock_server_instance.RequestHandlerClass.return_value = mock_request_handler
        
        # Set up mock client methods
        mock_session_state = LinkedInSessionState(
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            expires_at=datetime.utcnow() + timedelta(hours=1),
            token_type="Bearer",
            scope=self.scopes,
        )
        self.mock_client.exchange_code_for_token.return_value = mock_session_state
        
        # Call the function
        client = await authenticate_interactive(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.redirect_uri,
            scopes=self.scopes,
            open_browser=False,  # Don't actually open a browser in tests
        )
        
        # Verify the client was created with the correct parameters
        self.mock_create_client.assert_called_once_with(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.redirect_uri,
        )
        
        # Verify the authorization URL was generated
        self.mock_client.get_authorization_url.assert_called_once_with(
            scopes=self.scopes,
            state=None,
        )
        
        # Verify the code was exchanged for a token
        self.mock_client.exchange_code_for_token.assert_awaited_once_with("test_auth_code")
        
        # Verify the client was returned
        self.assertEqual(client, self.mock_client)
    
    async def test_refresh_token_if_needed_not_needed(self):
        """Test token refresh when not needed."""
        # Set up a client with a valid session
        session_state = LinkedInSessionState(
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            expires_at=datetime.utcnow() + timedelta(hours=1),  # Token is still valid
            token_type="Bearer",
            scope=self.scopes,
        )
        self.mock_client.session_state = session_state
        
        # Call the function
        result = await refresh_token_if_needed(self.mock_client)
        
        # Verify the token was not refreshed
        self.assertFalse(result)
        self.mock_client.refresh_access_token.assert_not_awaited()
    
    async def test_refresh_token_if_needed_success(self):
        """Test successful token refresh."""
        # Set up a client with an expired session
        session_state = LinkedInSessionState(
            access_token="expired_token",
            refresh_token="test_refresh_token",
            expires_at=datetime.utcnow() - timedelta(minutes=5),  # Token is expired
            token_type="Bearer",
            scope=self.scopes,
        )
        self.mock_client.session_state = session_state
        
        # Mock the refresh method
        self.mock_client.refresh_access_token.return_value = None
        
        # Call the function
        result = await refresh_token_if_needed(self.mock_client)
        
        # Verify the token was refreshed
        self.assertTrue(result)
        self.mock_client.refresh_access_token.assert_awaited_once()
    
    async def test_refresh_token_if_needed_error(self):
        """Test token refresh error handling."""
        # Set up a client with an expired session and no refresh token
        session_state = LinkedInSessionState(
            access_token="expired_token",
            refresh_token=None,  # No refresh token available
            expires_at=datetime.utcnow() - timedelta(minutes=5),
            token_type="Bearer",
            scope=self.scopes,
        )
        self.mock_client.session_state = session_state
        
        # Call the function and expect an exception
        with self.assertRaises(AuthenticationError):
            await refresh_token_if_needed(self.mock_client)
        
        # Verify the refresh method was not called
        self.mock_client.refresh_access_token.assert_not_awaited()
    
    def test_get_authorization_url(self):
        """Test generating an authorization URL."""
        # Mock the client's get_authorization_url method
        self.mock_client.get_authorization_url.return_value = "https://example.com/auth"
        
        # Call the function
        url = get_authorization_url(
            client_id=self.client_id,
            redirect_uri=self.redirect_uri,
            scopes=self.scopes,
            state="test_state",
        )
        
        # Verify the client was created with the correct parameters
        self.mock_create_client.assert_called_once_with(
            client_id=self.client_id,
            redirect_uri=self.redirect_uri,
        )
        
        # Verify the authorization URL was generated
        self.mock_client.get_authorization_url.assert_called_once_with(
            scopes=self.scopes,
            state="test_state",
        )
        
        # Verify the URL was returned
        self.assertEqual(url, "https://example.com/auth")
    
    async def test_exchange_code_for_tokens_success(self):
        """Test exchanging a code for tokens."""
        # Set up mock session state
        mock_session_state = LinkedInSessionState(
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            expires_at=datetime.utcnow() + timedelta(hours=1),
            token_type="Bearer",
            scope=self.scopes,
        )
        
        # Mock the client's exchange_code_for_token method
        self.mock_client.exchange_code_for_token.return_value = mock_session_state
        
        # Call the function
        result = await exchange_code_for_tokens(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.redirect_uri,
            code="test_auth_code",
        )
        
        # Verify the client was created with the correct parameters
        self.mock_create_client.assert_called_once_with(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.redirect_uri,
        )
        
        # Verify the code was exchanged for tokens
        self.mock_client.exchange_code_for_token.assert_awaited_once_with("test_auth_code")
        
        # Verify the session state was returned
        self.assertEqual(result, mock_session_state)
    
    def test_create_client_from_session_state_dict(self):
        """Test creating a client from a session state dictionary."""
        # Create a session state dictionary
        session_state_dict = {
            "access_token": "test_access_token",
            "refresh_token": "test_refresh_token",
            "expires_at": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
            "token_type": "Bearer",
            "scope": self.scopes,
        }
        
        # Call the function
        client = create_client_from_session_state(
            session_state_dict,
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.redirect_uri,
            timeout=60,
        )
        
        # Verify the client was created with the correct parameters
        self.mock_create_client.assert_called_once_with(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.redirect_uri,
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            timeout=60,
        )
        
        # Verify the client was returned
        self.assertEqual(client, self.mock_client)
    
    def test_create_client_from_session_state_object(self):
        """Test creating a client from a LinkedInSessionState object."""
        # Create a session state object
        session_state = LinkedInSessionState(
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            expires_at=datetime.utcnow() + timedelta(hours=1),
            token_type="Bearer",
            scope=self.scopes,
        )
        
        # Call the function
        client = create_client_from_session_state(
            session_state,
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.redirect_uri,
        )
        
        # Verify the client was created with the correct parameters
        self.mock_create_client.assert_called_once_with(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.redirect_uri,
            access_token="test_access_token",
            refresh_token="test_refresh_token",
        )
        
        # Verify the client was returned
        self.assertEqual(client, self.mock_client)
        
        # Verify the session state was preserved
        self.assertEqual(client.session_state, session_state)

# This allows running the tests with `python -m pytest tests/test_auth_utils.py`
if __name__ == "__main__":
    import pytest
    import sys
    sys.exit(pytest.main(["-v", __file__]))
