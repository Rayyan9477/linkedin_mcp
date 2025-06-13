"""
Common data models used across the LinkedIn MCP application.

This module contains the core data models that represent LinkedIn entities
and are used throughout the application for type safety and validation.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Union
from pydantic import BaseModel, Field, HttpUrl, EmailStr, validator

class LinkedInSessionState(BaseModel):
    """Represents the state of a LinkedIn user session."""
    access_token: str = Field(..., description="OAuth 2.0 access token")
    expires_at: datetime = Field(..., description="When the access token expires")
    refresh_token: Optional[str] = Field(None, description="OAuth 2.0 refresh token")
    token_type: str = Field("Bearer", description="Type of token, typically 'Bearer'")
    scope: List[str] = Field(default_factory=list, description="List of granted OAuth scopes")
    user_id: Optional[str] = Field(None, description="LinkedIn user ID")
    
    @validator('expires_at', pre=True)
    def parse_expires_at(cls, v):
        if isinstance(v, (int, float)):
            return datetime.fromtimestamp(v)
        return v

class JobSearchFilter(BaseModel):
    """Filter criteria for job searches."""
    keywords: Optional[str] = Field(None, description="Keywords to search for in job postings")
    location: Optional[str] = Field(None, description="Geographic location filter")
    company: Optional[str] = Field(None, description="Company name filter")
    job_type: Optional[str] = Field(None, description="Type of job (full-time, part-time, etc.)")
    experience_level: Optional[str] = Field(None, description="Experience level filter")
    date_posted: Optional[str] = Field(None, description="Date range for when jobs were posted")
    remote: Optional[bool] = Field(None, description="Whether to include only remote jobs")
    distance: Optional[int] = Field(None, description="Distance in miles from location")

class JobDetails(BaseModel):
    """Detailed information about a job posting."""
    job_id: str = Field(..., description="Unique identifier for the job")
    title: str = Field(..., description="Job title")
    company_name: str = Field(..., description="Name of the company")
    company_id: Optional[str] = Field(None, description="Company's LinkedIn ID")
    location: str = Field(..., description="Job location")
    description: str = Field(..., description="Job description")
    job_poster_url: Optional[HttpUrl] = Field(None, description="URL to the job poster's profile")
    apply_url: Optional[HttpUrl] = Field(None, description="URL to apply for the job")
    posted_date: datetime = Field(..., description="When the job was posted")
    expiry_date: Optional[datetime] = Field(None, description="When the job posting expires")
    job_type: Optional[str] = Field(None, description="Type of job (full-time, etc.)")
    salary: Optional[str] = Field(None, description="Salary information")
    seniority_level: Optional[str] = Field(None, description="Experience level required")
    employment_type: Optional[str] = Field(None, description="Type of employment")
    industry: Optional[str] = Field(None, description="Industry of the job")
    job_function: Optional[str] = Field(None, description="Job function category")
    skills: List[str] = Field(default_factory=list, description="List of required skills")

class ContactInfo(BaseModel):
    """Contact information for a LinkedIn profile."""
    email: Optional[EmailStr] = Field(None, description="Email address")
    phone: Optional[str] = Field(None, description="Phone number")
    address: Optional[str] = Field(None, description="Physical address")
    twitter: Optional[str] = Field(None, description="Twitter handle")
    websites: List[HttpUrl] = Field(default_factory=list, description="List of personal websites")
    im_accounts: Dict[str, str] = Field(default_factory=dict, description="Instant messaging accounts")

class Education(BaseModel):
    """Education history entry."""
    school: str = Field(..., description="Name of the educational institution")
    degree: str = Field(..., description="Degree obtained or pursuing")
    field_of_study: str = Field(..., description="Field of study")
    start_date: str = Field(..., description="Start date (YYYY-MM or YYYY)")
    end_date: Optional[str] = Field(None, description="End date (YYYY-MM or YYYY) if applicable")
    grade: Optional[str] = Field(None, description="Grade/GPA achieved")
    activities: Optional[str] = Field(None, description="Extracurricular activities")
    description: Optional[str] = Field(None, description="Additional details")

class Experience(BaseModel):
    """Work experience entry."""
    title: str = Field(..., description="Job title")
    company: str = Field(..., description="Company name")
    location: Optional[str] = Field(None, description="Job location")
    start_date: str = Field(..., description="Start date (YYYY-MM or YYYY)")
    end_date: Optional[str] = Field(None, description="End date (YYYY-MM or YYYY) if applicable")
    current: bool = Field(False, description="Whether this is a current position")
    description: Optional[str] = Field(None, description="Job description and achievements")

class Skill(BaseModel):
    """Skill or competency."""
    name: str = Field(..., description="Name of the skill")
    proficiency: Optional[str] = Field(None, description="Proficiency level")
    endorsements: int = Field(0, description="Number of endorsements")

class Profile(BaseModel):
    """LinkedIn user profile information."""
    profile_id: str = Field(..., description="LinkedIn profile ID")
    first_name: str = Field(..., description="First name")
    last_name: str = Field(..., description="Last name")
    headline: Optional[str] = Field(None, description="Profile headline")
    summary: Optional[str] = Field(None, description="Profile summary")
    location: Optional[str] = Field(None, description="Current location")
    industry: Optional[str] = Field(None, description="Industry")
    profile_picture_url: Optional[HttpUrl] = Field(None, description="URL to profile picture")
    profile_url: Optional[HttpUrl] = Field(None, description="URL to public profile")
    email: Optional[EmailStr] = Field(None, description="Primary email address")
    phone: Optional[str] = Field(None, description="Primary phone number")
    connections: int = Field(0, description="Number of connections")
    experience: List[Experience] = Field(default_factory=list, description="Work experience")
    education: List[Education] = Field(default_factory=list, description="Education history")
    skills: List[Skill] = Field(default_factory=list, description="List of skills")
    languages: List[Dict[str, str]] = Field(default_factory=list, description="Languages spoken")
    certifications: List[Dict[str, str]] = Field(default_factory=list, description="Certifications")
    volunteer_experience: List[Dict[str, str]] = Field(default_factory=list, description="Volunteer work")
    recommendations: List[Dict[str, str]] = Field(default_factory=list, description="Recommendations")
    contact_info: Optional[ContactInfo] = Field(None, description="Detailed contact information")
