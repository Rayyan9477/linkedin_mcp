"""Tests for MCP tool handlers in server.py."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from linkedin_mcp.models.linkedin import JobDetails, Profile, CompanyInfo, Experience, Education


@pytest.fixture
def mock_ctx():
    """Mock AppContext with all services."""
    ctx = MagicMock()
    ctx.jobs = MagicMock()
    ctx.jobs.search_jobs = AsyncMock(return_value={"jobs": [], "page": 1, "count": 0, "has_more": False})
    ctx.jobs.get_job_details = AsyncMock()
    ctx.jobs.get_recommended_jobs = AsyncMock(return_value=[])
    ctx.profiles = MagicMock()
    ctx.profiles.get_profile = AsyncMock()
    ctx.profiles.get_company = AsyncMock()
    ctx.ai = None
    ctx.resume_gen = MagicMock()
    ctx.resume_gen.generate_resume = AsyncMock()
    ctx.resume_gen.tailor_resume = AsyncMock()
    ctx.resume_gen.list_templates = MagicMock(return_value={"modern": "Modern"})
    ctx.cover_letter_gen = MagicMock()
    ctx.cover_letter_gen.generate_cover_letter = AsyncMock()
    ctx.cover_letter_gen.list_templates = MagicMock(return_value={"professional": "Professional"})
    ctx.tracker = MagicMock()
    ctx.tracker.track_application = AsyncMock()
    ctx.tracker.list_applications = AsyncMock(return_value=[])
    ctx.tracker.update_status = AsyncMock()
    return ctx


@pytest.mark.asyncio
async def test_search_jobs_caps_count(mock_ctx):
    from linkedin_mcp.server import search_jobs
    with patch("linkedin_mcp.server.get_ctx", return_value=mock_ctx):
        await search_jobs(keywords="python", count=100)
        # count should be capped to 50
        call_args = mock_ctx.jobs.search_jobs.call_args
        assert call_args[0][1] == 1  # page
        assert call_args[0][2] == 50  # count capped


@pytest.mark.asyncio
async def test_search_jobs_page_minimum(mock_ctx):
    from linkedin_mcp.server import search_jobs
    with patch("linkedin_mcp.server.get_ctx", return_value=mock_ctx):
        await search_jobs(keywords="python", page=-5)
        call_args = mock_ctx.jobs.search_jobs.call_args
        assert call_args[0][1] == 1  # page clamped to 1


@pytest.mark.asyncio
async def test_search_jobs_empty_filters(mock_ctx):
    from linkedin_mcp.server import search_jobs
    with patch("linkedin_mcp.server.get_ctx", return_value=mock_ctx):
        await search_jobs(keywords="python", job_type="", experience_level="", remote=False)
        call_args = mock_ctx.jobs.search_jobs.call_args
        filter_obj = call_args[0][0]
        assert filter_obj.job_type is None
        assert filter_obj.experience_level is None
        assert filter_obj.remote is None


@pytest.mark.asyncio
async def test_get_profile_me_substitution(mock_ctx):
    from linkedin_mcp.server import get_profile
    mock_profile = Profile(
        profile_id="testuser", name="Test User", headline="Dev"
    )
    mock_ctx.profiles.get_profile.return_value = mock_profile
    with patch("linkedin_mcp.server.get_ctx", return_value=mock_ctx), \
         patch("linkedin_mcp.server.get_settings") as mock_settings:
        mock_settings.return_value.linkedin_username = "testuser"
        result = await get_profile(profile_id="me")
        mock_ctx.profiles.get_profile.assert_called_with("testuser")
        data = json.loads(result)
        assert data["name"] == "Test User"


@pytest.mark.asyncio
async def test_analyze_profile_no_ai(mock_ctx):
    from linkedin_mcp.server import analyze_profile
    mock_ctx.ai = None
    with patch("linkedin_mcp.server.get_ctx", return_value=mock_ctx):
        result = await analyze_profile(profile_id="someone")
        data = json.loads(result)
        assert "error" in data


@pytest.mark.asyncio
async def test_generate_resume_invalid_format(mock_ctx):
    from linkedin_mcp.server import generate_resume
    with patch("linkedin_mcp.server.get_ctx", return_value=mock_ctx):
        result = await generate_resume(profile_id="johndoe", output_format="docx")
        data = json.loads(result)
        assert "error" in data
        assert "docx" in data["message"]


@pytest.mark.asyncio
async def test_list_templates_resume_only(mock_ctx):
    from linkedin_mcp.server import list_templates
    with patch("linkedin_mcp.server.get_ctx", return_value=mock_ctx):
        result = await list_templates(template_type="resume")
        data = json.loads(result)
        assert "resume" in data
        assert "cover_letter" not in data


@pytest.mark.asyncio
async def test_list_templates_all(mock_ctx):
    from linkedin_mcp.server import list_templates
    with patch("linkedin_mcp.server.get_ctx", return_value=mock_ctx):
        result = await list_templates(template_type="all")
        data = json.loads(result)
        assert "resume" in data
        assert "cover_letter" in data


@pytest.mark.asyncio
async def test_list_applications_empty_status_becomes_none(mock_ctx):
    from linkedin_mcp.server import list_applications
    with patch("linkedin_mcp.server.get_ctx", return_value=mock_ctx):
        await list_applications(status="")
        mock_ctx.tracker.list_applications.assert_called_with(None)


@pytest.mark.asyncio
async def test_get_recommended_jobs_caps_count(mock_ctx):
    from linkedin_mcp.server import get_recommended_jobs
    with patch("linkedin_mcp.server.get_ctx", return_value=mock_ctx):
        await get_recommended_jobs(count=50)
        mock_ctx.jobs.get_recommended_jobs.assert_called_with(25)
