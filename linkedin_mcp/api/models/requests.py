"""
Request models for LinkedIn API interactions.

This module contains Pydantic models that represent the structure of requests
sent to the LinkedIn API endpoints.
"""

from typing import Dict, List, Optional, Union
from pydantic import BaseModel, Field, HttpUrl, validator

from .common import JobSearchFilter
from .enums import JobType, ExperienceLevel, LocationType

class PaginationParams(BaseModel):
    """Pagination parameters for API requests."""
    start: int = Field(0, ge=0, description="Starting index (0-based)")
    count: int = Field(10, ge=1, le=100, description="Number of items to return")

class JobSearchRequest(BaseModel):
    """Request model for job search operations."""
    keywords: Optional[str] = Field(None, description="Search keywords")
    location: Optional[str] = Field(None, description="Location filter")
    company: Optional[str] = Field(None, description="Company name filter")
    job_type: Optional[Union[JobType, List[JobType]]] = Field(
        None, 
        description="Type of job(s) to search for"
    )
    experience_level: Optional[Union[ExperienceLevel, List[ExperienceLevel]]] = Field(
        None,
        description="Experience level filter"
    )
    location_type: Optional[Union[LocationType, List[LocationType]]] = Field(
        None,
        description="Type of work location"
    )
    date_posted: Optional[str] = Field(
        None,
        regex=r'^(past-24h|past-week|past-month|any-time)$',
        description="Time period when jobs were posted"
    )
    remote: Optional[bool] = Field(
        None,
        description="Whether to include only remote jobs"
    )
    distance: Optional[int] = Field(
        None,
        ge=1,
        le=100,
        description="Distance in miles from location"
    )
    pagination: PaginationParams = Field(
        default_factory=PaginationParams,
        description="Pagination parameters"
    )
    
    @validator('job_type', 'experience_level', 'location_type', pre=True)
    def convert_single_to_list(cls, v):
        """Convert single values to a single-item list for consistency."""
        if v is None:
            return None
        if isinstance(v, (list, tuple, set)):
            return list(v)
        return [v]

class ProfileRequest(BaseModel):
    """Request model for retrieving profile information."""
    profile_id: Optional[str] = Field(
        None,
        description="LinkedIn profile ID. If not provided, returns the current user's profile."
    )
    fields: List[str] = Field(
        default_factory=list,
        description="List of profile fields to include in the response"
    )

class ApplyToJobRequest(BaseModel):
    """Request model for applying to a job."""
    job_id: str = Field(..., description="ID of the job to apply for")
    resume_id: str = Field(..., description="ID of the resume to use")
    cover_letter: Optional[str] = Field(
        None,
        description="Cover letter text or template ID"
    )
    answers: Dict[str, str] = Field(
        default_factory=dict,
        description="Answers to job application questions"
    )
    follow_company: bool = Field(
        False,
        description="Whether to follow the company after applying"
    )

class SendMessageRequest(BaseModel):
    """Request model for sending a message."""
    recipient_urn: str = Field(..., description="Recipient's URN (e.g., 'urn:li:person:12345')")
    subject: Optional[str] = Field(None, description="Message subject")
    body: str = Field(..., description="Message body")
    attachments: List[Dict[str, str]] = Field(
        default_factory=list,
        description="List of attachments (e.g., [{'type': 'file', 'url': '...'}])"
    )

class ConnectionRequest(BaseModel):
    """Request model for sending a connection request."""
    profile_id: str = Field(..., description="LinkedIn profile ID to connect with")
    message: Optional[str] = Field(None, description="Personalized connection message")
    note: Optional[str] = Field(None, description="Additional note (if any)")

class PostEngagementRequest(BaseModel):
    """Request model for engaging with a post (like, comment, share)."""
    post_urn: str = Field(..., description="URN of the post to engage with")
    action: str = Field(..., regex=r'^(like|comment|share|react)$', 
                       description="Type of engagement")
    content: Optional[str] = Field(
        None,
        description="Required for 'comment' and 'share' actions"
    )
    reaction_type: Optional[str] = Field(
        None,
        regex=r'^(LIKE|CELEBRATION|SUPPORT|LOVE|INSIGHTFUL|CURIOUS)$',
        description="Required for 'react' action"
    )
    
    @validator('content')
    def validate_content(cls, v, values):
        if values.get('action') in ['comment', 'share'] and not v:
            raise ValueError(f"Content is required for {values['action']} action")
        return v
    
    @validator('reaction_type')
    def validate_reaction_type(cls, v, values):
        if values.get('action') == 'react' and not v:
            raise ValueError("reaction_type is required for 'react' action")
        return v
