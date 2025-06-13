"""
Response models for LinkedIn API interactions.

This module contains Pydantic models that represent the structure of responses
received from the LinkedIn API endpoints.
"""

from datetime import datetime
from typing import Dict, List, Optional, Union, Any
from pydantic import BaseModel, Field, HttpUrl, validator

from .common import JobDetails, Profile
from .enums import JobType, ExperienceLevel, LocationType

class PaginatedResponse(BaseModel):
    """Base class for paginated API responses."""
    start: int = Field(..., description="Starting index (0-based)")
    count: int = Field(..., description="Number of items in the current response")
    total: int = Field(..., description="Total number of items available")

class JobSearchResponse(PaginatedResponse):
    """Response model for job search operations."""
    jobs: List[JobDetails] = Field(default_factory=list, description="List of matching jobs")
    suggested_keywords: Optional[List[str]] = Field(
        None,
        description="Suggested search keywords"
    )
    filters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Available filters and their options"
    )

class ProfileResponse(BaseModel):
    """Response model for profile information."""
    profile: Profile = Field(..., description="Profile information")
    is_self: bool = Field(False, description="Whether this is the current user's profile")
    connection_degree: Optional[int] = Field(
        None,
        ge=1,
        le=3,
        description="Degree of connection (1st, 2nd, 3rd)"
    )
    shared_connections: Optional[int] = Field(
        None,
        description="Number of shared connections"
    )

class ApplyToJobResponse(BaseModel):
    """Response model for job applications."""
    application_id: str = Field(..., description="Unique identifier for the application")
    job_id: str = Field(..., description="ID of the applied job")
    applied_at: datetime = Field(default_factory=datetime.utcnow, description="When the application was submitted")
    confirmation_number: Optional[str] = Field(
        None,
        description="Application confirmation number or reference"
    )
    next_steps: Optional[str] = Field(
        None,
        description="Information about next steps in the application process"
    )

class MessageResponse(BaseModel):
    """Response model for sent messages."""
    message_id: str = Field(..., description="Unique identifier for the message")
    thread_id: str = Field(..., description="ID of the conversation thread")
    sent_at: datetime = Field(default_factory=datetime.utcnow, description="When the message was sent")
    recipient_urn: str = Field(..., description="Recipient's URN")

class ConnectionResponse(BaseModel):
    """Response model for connection requests."""
    invitation_id: str = Field(..., description="Unique identifier for the connection invitation")
    sent_at: datetime = Field(default_factory=datetime.utcnow, description="When the invitation was sent")
    message: Optional[str] = Field(
        None,
        description="The personalized message included with the invitation"
    )

class PostEngagementResponse(BaseModel):
    """Response model for post engagements (likes, comments, shares, reactions)."""
    engagement_id: str = Field(..., description="Unique identifier for the engagement")
    post_urn: str = Field(..., description="URN of the post that was engaged with")
    action: str = Field(..., description="Type of engagement (like, comment, share, react)")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="When the engagement was created")
    content: Optional[str] = Field(
        None,
        description="Content of the comment or share, if applicable"
    )
    reaction_type: Optional[str] = Field(
        None,
        description="Type of reaction, if action is 'react'"
    )

class ErrorResponse(BaseModel):
    """Standard error response model."""
    error: str = Field(..., description="Error message")
    code: int = Field(..., description="Error code")
    details: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional error details"
    )
    request_id: Optional[str] = Field(
        None,
        description="Unique identifier for the request that caused the error"
    )

class RateLimitInfo(BaseModel):
    """Rate limit information included in responses."""
    limit: int = Field(..., description="Request limit per time window")
    remaining: int = Field(..., description="Remaining requests in the current window")
    reset_at: datetime = Field(..., description="When the rate limit will reset")

class ApiResponse(BaseModel):
    """Generic API response wrapper with metadata."""
    success: bool = Field(..., description="Whether the request was successful")
    data: Optional[Any] = Field(None, description="Response data")
    error: Optional[ErrorResponse] = Field(None, description="Error information")
    rate_limit: Optional[RateLimitInfo] = Field(None, description="Rate limit information")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When the response was generated")
