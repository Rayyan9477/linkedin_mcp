"""Shared test fixtures for LinkedIn MCP server tests."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from linkedin_mcp.models.linkedin import (
    CompanyInfo,
    Education,
    Experience,
    JobDetails,
    JobListing,
    Profile,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_profile_data():
    """Raw profile data as dict."""
    with open(FIXTURES_DIR / "sample_profile.json") as f:
        return json.load(f)


@pytest.fixture
def sample_job_data():
    """Raw job data as dict."""
    with open(FIXTURES_DIR / "sample_job.json") as f:
        return json.load(f)


@pytest.fixture
def sample_profile(sample_profile_data):
    """Profile model instance."""
    return Profile(
        profile_id=sample_profile_data["profile_id"],
        name=sample_profile_data["name"],
        headline=sample_profile_data["headline"],
        summary=sample_profile_data["summary"],
        location=sample_profile_data["location"],
        email=sample_profile_data["email"],
        phone=sample_profile_data["phone"],
        profile_url=sample_profile_data["profile_url"],
        experience=[Experience(**e) for e in sample_profile_data["experience"]],
        education=[Education(**e) for e in sample_profile_data["education"]],
        skills=sample_profile_data["skills"],
    )


@pytest.fixture
def sample_job_details(sample_job_data):
    """JobDetails model instance."""
    return JobDetails(**sample_job_data)


@pytest.fixture
def sample_job_listing(sample_job_data):
    """JobListing model instance."""
    return JobListing(
        job_id=sample_job_data["job_id"],
        title=sample_job_data["title"],
        company=sample_job_data["company"],
        location=sample_job_data["location"],
        url=sample_job_data["url"],
        date_posted=sample_job_data["date_posted"],
    )


@pytest.fixture
def mock_linkedin_client():
    """Mock LinkedInClient with async methods."""
    client = MagicMock()
    client.ensure_authenticated = AsyncMock()
    client.search_jobs = AsyncMock(return_value=[])
    client.get_job = AsyncMock()
    client.get_profile = AsyncMock()
    client.get_company = AsyncMock()
    return client


@pytest.fixture
def mock_ai_provider():
    """Mock AIProvider with async methods."""
    ai = AsyncMock()
    ai.enhance_resume = AsyncMock(return_value={
        "summary": "Enhanced summary.",
        "experience": [],
        "skills": ["Python", "ML"],
        "highlights": ["Led team of 5"],
    })
    ai.generate_cover_letter = AsyncMock(return_value={
        "greeting": "Dear Hiring Manager,",
        "introduction": "I am excited to apply.",
        "body_paragraphs": ["Relevant experience paragraph."],
        "closing": "Thank you for your consideration.",
        "signature": "Sincerely,\nJohn Doe",
    })
    ai.analyze_profile = AsyncMock(return_value={
        "overall_score": 80,
        "headline_suggestions": ["Add keywords"],
        "summary_suggestions": ["Be more specific"],
        "experience_suggestions": ["Quantify achievements"],
        "skills_suggestions": ["Add cloud skills"],
        "general_tips": ["Add a photo"],
        "keyword_recommendations": ["machine learning", "AI"],
    })
    return ai


@pytest.fixture
def tmp_data_dir(tmp_path):
    """Temporary data directory for tests."""
    return tmp_path / "data"
