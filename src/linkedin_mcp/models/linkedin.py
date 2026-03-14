"""LinkedIn data models — single source of truth.

Replaces duplicate models from core/protocol.py and api/models/common.py.
"""

from typing import Any

from pydantic import BaseModel, Field


class Experience(BaseModel):
    """A work experience entry."""

    title: str
    company: str
    location: str = ""
    start_date: str = ""
    end_date: str = "Present"
    description: str = ""


class Education(BaseModel):
    """An education entry."""

    school: str
    degree: str = ""
    field_of_study: str = ""
    start_date: str = ""
    end_date: str = ""


class Certification(BaseModel):
    """A certification entry."""

    name: str = ""
    authority: str = ""


class Language(BaseModel):
    """A language proficiency entry."""

    name: str = ""
    proficiency: str = ""


class Profile(BaseModel):
    """LinkedIn user profile."""

    profile_id: str
    name: str
    headline: str = ""
    summary: str = ""
    location: str = ""
    industry: str = ""
    email: str = ""
    phone: str = ""
    profile_url: str = ""
    experience: list[Experience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    certifications: list[Certification] = Field(default_factory=list)
    languages: list[Language] = Field(default_factory=list)


class JobSearchFilter(BaseModel):
    """Job search filter parameters."""

    keywords: str = ""
    location: str = ""
    distance: int | None = None
    job_type: list[str] | None = None
    experience_level: list[str] | None = None
    remote: bool | None = None
    date_posted: str | None = None
    company: str | None = None


class JobListing(BaseModel):
    """A job listing in search results (summary view)."""

    job_id: str
    title: str
    company: str
    location: str
    url: str = ""
    date_posted: str = ""
    applicant_count: int | None = None


class JobDetails(BaseModel):
    """Full job posting details."""

    job_id: str
    title: str
    company: str
    location: str
    description: str = ""
    url: str = ""
    employment_type: str = ""
    seniority_level: str = ""
    skills: list[str] = Field(default_factory=list)
    industries: list[str] = Field(default_factory=list)
    job_functions: list[str] = Field(default_factory=list)
    date_posted: str = ""
    applicant_count: int | None = None


class CompanyInfo(BaseModel):
    """LinkedIn company information."""

    company_id: str
    name: str
    tagline: str = ""
    description: str = ""
    website: str = ""
    industry: str = ""
    company_size: str = ""
    headquarters: str = ""
    specialties: list[str] = Field(default_factory=list)
    url: str = ""
