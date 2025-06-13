"""
Pydantic models for LinkedIn API requests and responses.

This module contains all the data models used for validating and serializing
data to/from the LinkedIn API.
"""

__all__ = [
    # Common models
    'LinkedInSessionState',
    'JobSearchFilter',
    'JobDetails',
    'Profile',
    'Company',
    'Education',
    'Experience',
    'Skill',
    'ContactInfo',
    
    # Request/Response models
    'JobSearchRequest',
    'JobSearchResponse',
    'ProfileRequest',
    'ProfileResponse',
    'ApplyToJobRequest',
    'ApplyToJobResponse',
    
    # Enums
    'JobType',
    'ExperienceLevel',
    'LocationType',
    'Industry',
]

# Import models for easier access
from .common import (
    LinkedInSessionState,
    JobSearchFilter,
    JobDetails,
    Profile,
    Company,
    Education,
    Experience,
    Skill,
    ContactInfo,
)

from .requests import (
    JobSearchRequest,
    ProfileRequest,
    ApplyToJobRequest,
)

from .responses import (
    JobSearchResponse,
    ProfileResponse,
    ApplyToJobResponse,
)

from .enums import (
    JobType,
    ExperienceLevel,
    LocationType,
    Industry,
)
