"""Tests for CoverLetterGeneratorService."""

import pytest
from unittest.mock import AsyncMock

from linkedin_mcp.services.cache import JSONCache
from linkedin_mcp.services.cover_letter_generator import CoverLetterGeneratorService
from linkedin_mcp.services.job_search import JobSearchService
from linkedin_mcp.services.profile import ProfileService
from linkedin_mcp.services.template_manager import TemplateManager


@pytest.fixture
def cache(tmp_path):
    return JSONCache(tmp_path / "cache", ttl_hours=1)


@pytest.fixture
def profile_service(mock_linkedin_client, cache):
    return ProfileService(mock_linkedin_client, cache)


@pytest.fixture
def job_service(mock_linkedin_client, cache):
    return JobSearchService(mock_linkedin_client, cache)


@pytest.fixture
def cover_letter_gen(profile_service, job_service, tmp_path):
    tm = TemplateManager()
    return CoverLetterGeneratorService(
        profile_service, job_service, None, tm, tmp_path / "cover_letters"
    )


@pytest.mark.asyncio
async def test_generate_cover_letter_html(
    cover_letter_gen, mock_linkedin_client, sample_profile, sample_job_details
):
    mock_linkedin_client.get_profile.return_value = sample_profile
    mock_linkedin_client.get_job.return_value = sample_job_details
    doc = await cover_letter_gen.generate_cover_letter(
        "johndoe", "test_job_456", template="professional", format="html"
    )
    assert doc.format == "html"
    assert "John Doe" in doc.content
    assert "<html" in doc.content


@pytest.mark.asyncio
async def test_generate_cover_letter_markdown(
    cover_letter_gen, mock_linkedin_client, sample_profile, sample_job_details
):
    mock_linkedin_client.get_profile.return_value = sample_profile
    mock_linkedin_client.get_job.return_value = sample_job_details
    doc = await cover_letter_gen.generate_cover_letter(
        "johndoe", "test_job_456", template="professional", format="md"
    )
    assert doc.format == "md"
    assert "John Doe" in doc.content


@pytest.mark.asyncio
async def test_list_templates(cover_letter_gen):
    templates = cover_letter_gen.list_templates()
    assert "professional" in templates
    assert "concise" in templates
