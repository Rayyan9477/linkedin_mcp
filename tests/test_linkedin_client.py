"""
Tests for the LinkedIn API client.

This module contains unit tests for the LinkedIn API client implementation.
"""

import asyncio
import json
import os
import time
from datetime import datetime, timedelta
from unittest import mock, IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
from aiohttp import ClientResponse, ClientResponseError, ClientSession, ClientTimeout

from linkedin_mcp.api.clients.linkedin import LinkedInAPIClient
from linkedin_mcp.api.models.common import LinkedInSessionState
from linkedin_mcp.api.models.enums import JobType, ExperienceLevel
from linkedin_mcp.api.models.requests import JobSearchRequest
from linkedin_mcp.api.models.responses import JobSearchResponse, JobDetails
from linkedin_mcp.core.exceptions import (
    AuthenticationError,
    RateLimitError,
    NetworkError,
    ServiceUnavailableError,
)

# Test fixtures
@pytest.fixture
def mock_session():
    """Create a mock aiohttp client session."""
    with mock.patch('aiohttp.ClientSession') as mock_session:
        yield mock_session

@pytest.fixture
def mock_response():
    """Create a mock aiohttp client response."""
    response = AsyncMock(spec=ClientResponse)
    response.status = 200
    response.json = AsyncMock(return_value={})
    response.text = AsyncMock(return_value='{}')
    response.headers = {}
    response.content_type = 'application/json'
    return response

@pytest.fixture
def linkedin_client():
    """Create a LinkedIn API client with test credentials."""
    return LinkedInAPIClient(
        client_id="test_client_id",
        client_secret="test_client_secret",
        redirect_uri="http://localhost:8080/callback",
    )

class TestLinkedInAPIClient(IsolatedAsyncioTestCase):
    """Test cases for the LinkedIn API client."""
    
    async def asyncSetUp(self):
        """Set up test fixtures."""
        self.client = LinkedInAPIClient(
            client_id="test_client_id",
            client_secret="test_client_secret",
            redirect_uri="http://localhost:8080/callback",
        )
        
        # Mock the _request method to avoid making actual HTTP requests
        self.original_request = self.client._request
        self.client._request = AsyncMock()
        
        # Set up a mock response
        self.mock_response = AsyncMock(spec=ClientResponse)
        self.mock_response.status = 200
        self.mock_response.json = AsyncMock(return_value={})
        self.client._request.return_value = self.mock_response
    
    async def asyncTearDown(self):
        """Clean up after tests."""
        if hasattr(self, 'client') and hasattr(self.client, '_session'):
            await self.client.close()
    
    async def test_get_authorization_url(self):
        """Test generating an OAuth 2.0 authorization URL."""
        url = self.client.get_authorization_url(
            scopes=["r_liteprofile", "r_emailaddress"],
            state="test_state"
        )
        
        self.assertIn("https://www.linkedin.com/oauth/v2/authorization", url)
        self.assertIn("response_type=code", url)
        self.assertIn("client_id=test_client_id", url)
        self.assertIn("redirect_uri=http%3A%2F%2Flocalhost%3A8080%2Fcallback", url)
        self.assertIn("scope=r_liteprofile%20r_emailaddress", url)
        self.assertIn("state=test_state", url)
    
    async def test_exchange_code_for_token_success(self):
        """Test exchanging an authorization code for an access token."""
        # Mock the token response
        token_data = {
            "access_token": "test_access_token",
            "expires_in": 3600,
            "refresh_token": "test_refresh_token",
            "refresh_token_expires_in": 5184000,
        }
        self.mock_response.json.return_value = token_data
        
        # Call the method
        session_state = await self.client.exchange_code_for_token("test_code")
        
        # Verify the request was made correctly
        self.client._request.assert_awaited_once()
        
        # Verify the session state was updated
        self.assertEqual(session_state.access_token, "test_access_token")
        self.assertEqual(session_state.refresh_token, "test_refresh_token")
        self.assertIsNotNone(session_state.expires_at)
        self.assertGreater(session_state.expires_at, datetime.utcnow())
    
    async def test_refresh_access_token_success(self):
        """Test refreshing an access token."""
        # Set up initial session state with an expired token
        self.client.session_state = LinkedInSessionState(
            access_token="expired_token",
            refresh_token="test_refresh_token",
            expires_at=datetime.utcnow() - timedelta(minutes=5),
            token_type="Bearer",
            scope=["r_liteprofile"],
        )
        
        # Mock the token refresh response
        token_data = {
            "access_token": "new_access_token",
            "expires_in": 3600,
            "refresh_token": "new_refresh_token",
        }
        self.mock_response.json.return_value = token_data
        
        # Call the method
        await self.client.refresh_access_token()
        
        # Verify the request was made correctly
        self.client._request.assert_awaited_once()
        
        # Verify the session state was updated
        self.assertEqual(self.client.session_state.access_token, "new_access_token")
        self.assertEqual(self.client.session_state.refresh_token, "new_refresh_token")
        self.assertIsNotNone(self.client.session_state.expires_at)
        self.assertGreater(self.client.session_state.expires_at, datetime.utcnow())
    
    async def test_search_jobs_success(self):
        """Test searching for jobs."""
        # Mock the job search response
        job_data = {
            "elements": [
                {
                    "job_id": "12345",
                    "title": "Senior Software Engineer",
                    "company_name": "Test Company",
                    "location": "San Francisco, CA",
                    "description": "Job description here",
                    "job_type": "FULL_TIME",
                    "experience_level": "MID_SENIOR",
                    "application_deadline": (datetime.utcnow() + timedelta(days=30)).isoformat(),
                }
            ],
            "paging": {
                "count": 1,
                "start": 0,
                "total": 1,
            }
        }
        self.mock_response.json.return_value = job_data
        
        # Create a job search request
        request = JobSearchRequest(
            keywords="Python Developer",
            location="San Francisco, CA",
            job_type=[JobType.FULL_TIME],
            experience_level=ExperienceLevel.MID_SENIOR,
            page=1,
            count=10,
        )
        
        # Call the method
        response = await self.client.search_jobs(request)
        
        # Verify the response
        self.assertIsInstance(response, JobSearchResponse)
        self.assertEqual(len(response.jobs), 1)
        self.assertEqual(response.jobs[0].job_id, "12345")
        self.assertEqual(response.jobs[0].title, "Senior Software Engineer")
    
    async def test_rate_limiting(self):
        """Test that rate limiting is enforced."""
        # Set up a rate limit response
        self.mock_response.status = 429
        self.mock_response.headers = {"Retry-After": "1"}
        
        # Call a method that will trigger rate limiting
        with self.assertRaises(RateLimitError):
            await self.client.get_profile()
        
        # Verify the request was made
        self.client._request.assert_awaited_once()
    
    async def test_network_error_handling(self):
        """Test handling of network errors."""
        # Simulate a network error
        self.client._request.side_effect = aiohttp.ClientError("Network error")
        
        # Call a method that will trigger the error
        with self.assertRaises(NetworkError):
            await self.client.get_profile()
    
    async def test_service_unavailable(self):
        """Test handling of service unavailable errors."""
        # Simulate a service unavailable error
        self.mock_response.status = 503
        
        # Call a method that will trigger the error
        with self.assertRaises(ServiceUnavailableError):
            await self.client.get_profile()
    
    async def test_authentication_error(self):
        """Test handling of authentication errors."""
        # Simulate an authentication error
        self.mock_response.status = 401
        
        # Call a method that will trigger the error
        with self.assertRaises(AuthenticationError):
            await self.client.get_profile()
    
    async def test_context_manager(self):
        """Test that the client can be used as a context manager."""
        async with LinkedInAPIClient(
            client_id="test_client_id",
            client_secret="test_client_secret",
            redirect_uri="http://localhost:8080/callback",
        ) as client:
            self.assertIsInstance(client, LinkedInAPIClient)
            self.assertIsNotNone(client._session)
            
            # The session should be closed when exiting the context
            self.assertFalse(client._session.closed)
        
        # The session should be closed now
        self.assertTrue(client._session.closed)

# This allows running the tests with `python -m pytest tests/test_linkedin_client.py`
if __name__ == "__main__":
    import pytest
    import sys
    sys.exit(pytest.main(["-v", __file__]))
