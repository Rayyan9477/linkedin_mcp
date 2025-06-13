"""
LinkedIn API client and models.

This package contains the LinkedIn API client implementation and related models.
"""

__all__ = [
    # Clients
    'LinkedInAPIClient',
    
    # Models
    'LinkedInSessionState',
    'JobSearchFilter',
    'JobDetails',
    'Profile',
    
    # Errors
    'LinkedInAPIError',
    'LinkedInAuthError',
    'LinkedInRateLimitError',
]

# Import client and models for easier access
from .clients.linkedin import LinkedInAPIClient
from .models.common import (
    LinkedInSessionState,
    JobSearchFilter,
    JobDetails,
    Profile,
)
from .exceptions import (
    LinkedInAPIError,
    LinkedInAuthError,
    LinkedInRateLimitError,
)
