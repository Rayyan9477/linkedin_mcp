"""Tests for ResumeGeneratorService."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from linkedin_mcp.services.cache import JSONCache
from linkedin_mcp.services.job_search import JobSearchService
from linkedin_mcp.services.profile import ProfileService
from linkedin_mcp.services.resume_generator import ResumeGeneratorService
from linkedin_mcp.services.template_manager import TemplateManager


@pytest.fixture
def cache(tmp_path):
    return JSONCache(tmp_path / "cache", ttl_hours=1)


@pytest.fixture
def profile_service(mock_linkedin_client, cache):
    svc = ProfileService(mock_linkedin_client, cache)
    return svc


@pytest.fixture
def job_service(mock_linkedin_client, cache):
    return JobSearchService(mock_linkedin_client, cache)


@pytest.fixture
def resume_gen(profile_service, job_service, tmp_path):
    tm = TemplateManager()
    return ResumeGeneratorService(
        profile_service, job_service, None, tm, tmp_path / "resumes"
    )


@pytest.fixture
def resume_gen_with_ai(profile_service, job_service, mock_ai_provider, tmp_path):
    tm = TemplateManager()
    return ResumeGeneratorService(
        profile_service, job_service, mock_ai_provider, tm, tmp_path / "resumes"
    )


@pytest.mark.asyncio
async def test_generate_resume_html(resume_gen, mock_linkedin_client, sample_profile):
    mock_linkedin_client.get_profile.return_value = sample_profile
    doc = await resume_gen.generate_resume("johndoe", template="modern", format="html")
    assert doc.format == "html"
    assert "John Doe" in doc.content
    assert "<html" in doc.content


@pytest.mark.asyncio
async def test_generate_resume_markdown(resume_gen, mock_linkedin_client, sample_profile):
    mock_linkedin_client.get_profile.return_value = sample_profile
    doc = await resume_gen.generate_resume("johndoe", template="modern", format="md")
    assert doc.format == "md"
    assert "John Doe" in doc.content


@pytest.mark.asyncio
async def test_tailor_resume(resume_gen, mock_linkedin_client, sample_profile, sample_job_details):
    mock_linkedin_client.get_profile.return_value = sample_profile
    mock_linkedin_client.get_job.return_value = sample_job_details
    doc = await resume_gen.tailor_resume("johndoe", "test_job_456", template="modern", format="html")
    assert doc.format == "html"
    assert "John Doe" in doc.content
    assert doc.metadata.get("job_id") == "test_job_456"


@pytest.mark.asyncio
async def test_generate_resume_with_ai(resume_gen_with_ai, mock_linkedin_client, sample_profile):
    mock_linkedin_client.get_profile.return_value = sample_profile
    doc = await resume_gen_with_ai.generate_resume("johndoe", template="modern", format="html")
    assert doc.format == "html"
    # AI-enhanced summary should appear (mock returns "Enhanced summary.")
    assert "Enhanced summary" in doc.content


@pytest.mark.asyncio
async def test_generate_resume_ai_failure_fallback(
    resume_gen_with_ai, mock_linkedin_client, sample_profile, mock_ai_provider
):
    mock_linkedin_client.get_profile.return_value = sample_profile
    mock_ai_provider.enhance_resume.side_effect = Exception("AI failed")
    doc = await resume_gen_with_ai.generate_resume("johndoe", template="modern", format="html")
    # Should fall back to raw profile data without raising
    assert doc.format == "html"
    assert "John Doe" in doc.content


@pytest.mark.asyncio
async def test_list_templates(resume_gen):
    templates = resume_gen.list_templates()
    assert "modern" in templates
    assert "professional" in templates
    assert "minimal" in templates
