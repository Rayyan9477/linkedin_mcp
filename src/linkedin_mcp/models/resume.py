"""Resume and cover letter content models."""

from typing import Any

from pydantic import BaseModel, Field


class ResumeHeader(BaseModel):
    """Resume header information."""

    name: str
    headline: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    linkedin_url: str = ""


class ResumeExperience(BaseModel):
    """A work experience entry formatted for resume."""

    title: str
    company: str
    location: str = ""
    start_date: str = ""
    end_date: str = "Present"
    description: str = ""


class ResumeEducation(BaseModel):
    """An education entry formatted for resume."""

    school: str
    degree: str = ""
    field: str = ""
    start_date: str = ""
    end_date: str = ""


class ResumeContent(BaseModel):
    """Structured resume content for template rendering."""

    header: ResumeHeader
    summary: str = ""
    experience: list[ResumeExperience] = Field(default_factory=list)
    education: list[ResumeEducation] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    certifications: list[dict[str, Any]] = Field(default_factory=list)
    languages: list[dict[str, str]] = Field(default_factory=list)


class CoverLetterContent(BaseModel):
    """Structured cover letter content for template rendering."""

    date: str
    candidate_name: str
    candidate_contact: str = ""
    recipient: str = ""
    company: str = ""
    job_title: str = ""
    greeting: str = "Dear Hiring Manager,"
    introduction: str = ""
    body_paragraphs: list[str] = Field(default_factory=list)
    closing: str = ""
    signature: str = ""


class GeneratedDocument(BaseModel):
    """Result of generating a resume or cover letter."""

    content: str
    format: str  # "html", "md", or "pdf"
    file_path: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
