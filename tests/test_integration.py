"""Integration tests — verify all MCP tool handlers work end-to-end with mocked services."""

import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from mcp.server.fastmcp.exceptions import ToolError

from linkedin_mcp.config import get_settings
from linkedin_mcp.models import (
    JobListing, JobDetails, Profile, CompanyInfo,
)
from linkedin_mcp.server import (
    search_jobs, get_job_details, get_recommended_jobs,
    get_profile, get_company, analyze_profile,
    generate_resume, list_templates,
    track_application, list_applications, update_application_status,
)


@pytest.fixture(autouse=True)
def _set_env(monkeypatch):
    monkeypatch.setenv("LINKEDIN_USERNAME", "test-user")
    monkeypatch.setenv("LINKEDIN_PASSWORD", "test-pass")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _build_mock_ctx():
    ctx = MagicMock()

    # search_jobs returns a dict (from JobSearchService)
    ctx.jobs.search_jobs = AsyncMock(return_value={
        "jobs": [
            {"job_id": "123", "title": "Software Engineer", "company": "Acme", "location": "SF", "url": "", "date_posted": ""},
            {"job_id": "456", "title": "Senior Developer", "company": "BigCo", "location": "NYC", "url": "", "date_posted": ""},
        ],
        "page": 1,
        "count": 2,
        "has_more": True,
    })

    ctx.jobs.get_job_details = AsyncMock(return_value=JobDetails(
        job_id="123", title="Software Engineer", company="Acme Corp",
        location="San Francisco", description="Build systems.",
        url="https://linkedin.com/jobs/123", employment_type="Full-time",
        seniority_level="Mid-Senior", industries=["Tech"], job_functions=["Eng"],
    ))

    ctx.jobs.get_recommended_jobs = AsyncMock(return_value=[
        JobListing(job_id="789", title="SRE", company="CloudCo",
                   location="Remote", url="", date_posted=""),
    ])

    ctx.profiles.get_profile = AsyncMock(return_value=Profile(
        profile_id="test-user", name="Jane Doe",
        headline="Engineer", summary="10 yrs experience.",
        industry="Tech", location="SF",
        email="jane@example.com", phone="555-1234",
        experience=[], education=[], skills=["Python", "Go"],
        certifications=[], languages=[],
    ))

    ctx.profiles.get_company = AsyncMock(return_value=CompanyInfo(
        company_id="acme", name="Acme Corp", description="A tech company.",
        industry="Technology", website="https://acme.com",
        company_size="1001-5000", headquarters="SF",
        specialties=["Engineering"], follower_count=50000,
    ))

    ctx.ai = None

    # list_templates is a plain (non-async) method on the generator services
    ctx.resume_gen.list_templates = MagicMock(return_value=[
        {"name": "professional", "description": "Professional template"}
    ])
    ctx.cover_letter_gen.list_templates = MagicMock(return_value=[
        {"name": "standard", "description": "Standard cover letter"}
    ])

    ctx.tracker.list_applications = AsyncMock(return_value=[])
    ctx.tracker.track_application = AsyncMock()
    ctx.tracker.update_status = AsyncMock()

    return ctx


@pytest.fixture
def mock_ctx():
    ctx = _build_mock_ctx()
    with patch("linkedin_mcp.server.get_ctx", AsyncMock(return_value=ctx)):
        yield ctx


# ── Job tools ─────────────────────────────────────────────────────────────


async def test_search_jobs_basic(mock_ctx):
    result = json.loads(await search_jobs(keywords="python", location="SF"))
    assert len(result["jobs"]) == 2
    assert result["has_more"] is True
    assert result["jobs"][0]["title"] == "Software Engineer"


async def test_search_jobs_returns_pagination_info(mock_ctx):
    result = json.loads(await search_jobs(keywords="python"))
    assert "page" in result
    assert "count" in result
    assert "has_more" in result


async def test_get_job_details_returns_data(mock_ctx):
    result = json.loads(await get_job_details(job_id="123"))
    assert result["title"] == "Software Engineer"
    assert result["company"] == "Acme Corp"
    assert "description" in result


async def test_get_recommended_jobs_returns_data(mock_ctx):
    result = json.loads(await get_recommended_jobs(count=5))
    assert len(result) == 1
    assert result[0]["title"] == "SRE"


async def test_get_recommended_jobs_count_capped(mock_ctx):
    """Count above 25 should be capped to 25."""
    await get_recommended_jobs(count=100)
    args, _ = mock_ctx.jobs.get_recommended_jobs.call_args
    assert args[0] == 25


async def test_get_recommended_jobs_count_minimum(mock_ctx):
    """Count below 1 should be floored to 1."""
    await get_recommended_jobs(count=-5)
    args, _ = mock_ctx.jobs.get_recommended_jobs.call_args
    assert args[0] == 1


# ── Profile tools ─────────────────────────────────────────────────────────


async def test_get_profile_basic(mock_ctx):
    result = json.loads(await get_profile(profile_id="test-user"))
    assert result["name"] == "Jane Doe"
    assert "Python" in result["skills"]


async def test_get_profile_me_resolves(mock_ctx):
    await get_profile(profile_id="me")
    mock_ctx.profiles.get_profile.assert_called_with("test-user")


async def test_get_profile_me_empty_username(mock_ctx, monkeypatch):
    monkeypatch.setenv("LINKEDIN_USERNAME", "")
    get_settings.cache_clear()
    with pytest.raises(ToolError, match="username not configured"):
        await get_profile(profile_id="me")


async def test_get_company_basic(mock_ctx):
    result = json.loads(await get_company(company_id="acme"))
    assert result["name"] == "Acme Corp"


async def test_analyze_profile_no_ai(mock_ctx):
    """Without AI provider, analyze_profile should raise ToolError."""
    with pytest.raises(ToolError, match="[Aa][Ii]"):
        await analyze_profile(profile_id="test-user")


# ── Template tools ────────────────────────────────────────────────────────


async def test_list_templates_resume(mock_ctx):
    result = json.loads(await list_templates(template_type="resume"))
    assert "resume" in result
    assert len(result["resume"]) == 1


async def test_list_templates_all(mock_ctx):
    result = json.loads(await list_templates(template_type="all"))
    assert "resume" in result
    assert "cover_letter" in result


async def test_list_templates_invalid_type(mock_ctx):
    with pytest.raises(ToolError, match="Invalid template_type"):
        await list_templates(template_type="invalid")


# ── Format validation ─────────────────────────────────────────────────────


async def test_generate_resume_invalid_format(mock_ctx):
    with pytest.raises(ToolError, match="Invalid format"):
        await generate_resume(profile_id="test-user", output_format="docx")


async def test_generate_resume_valid_formats_dont_raise(mock_ctx):
    from linkedin_mcp.server import _validate_format
    for fmt in ("html", "md", "pdf"):
        _validate_format(fmt)  # should not raise


# ── Application tracking tools ────────────────────────────────────────────


async def test_track_application_valid(mock_ctx):
    """Use the actual parameter name: job_title, not title."""
    from linkedin_mcp.models.tracking import TrackedApplication
    app = TrackedApplication(
        job_id="123", job_title="Engineer", company="Acme",
        status="applied", notes="Sent resume",
    )
    mock_ctx.tracker.track_application = AsyncMock(return_value=app)
    result = json.loads(await track_application(
        job_id="123", job_title="Engineer", company="Acme",
        status="applied", notes="Sent resume",
    ))
    assert result["status"] == "applied"
    assert result["job_id"] == "123"


async def test_track_application_invalid_status(mock_ctx):
    with pytest.raises(ToolError, match="[Ii]nvalid"):
        await track_application(
            job_id="123", job_title="Engineer", company="Acme",
            status="BOGUS", notes="",
        )


async def test_list_applications_empty(mock_ctx):
    result = json.loads(await list_applications(status=""))
    assert isinstance(result, list)
    assert len(result) == 0


async def test_update_application_status(mock_ctx):
    from linkedin_mcp.models.tracking import TrackedApplication
    app = TrackedApplication(
        job_id="123", job_title="Engineer", company="Acme",
        status="interviewing", notes="Phone screen",
    )
    mock_ctx.tracker.update_status = AsyncMock(return_value=app)
    result = json.loads(await update_application_status(
        job_id="123", status="interviewing", notes="Phone screen",
    ))
    assert result["status"] == "interviewing"


# ── Error propagation ─────────────────────────────────────────────────────


async def test_linkedin_api_error_becomes_tool_error(mock_ctx):
    from linkedin_mcp.exceptions import LinkedInAPIError
    mock_ctx.jobs.search_jobs = AsyncMock(
        side_effect=LinkedInAPIError("API down", {"status": 500})
    )
    with pytest.raises(ToolError):
        await search_jobs(keywords="fail")


async def test_unexpected_error_in_get_profile(mock_ctx):
    """Unexpected exceptions should propagate (or become ToolError if caught)."""
    mock_ctx.profiles.get_profile = AsyncMock(side_effect=RuntimeError("boom"))
    # The current handler only catches LinkedInMCPError, so RuntimeError propagates
    with pytest.raises(RuntimeError):
        await get_profile(profile_id="test-user")


async def test_validation_error_in_track(mock_ctx):
    """Pydantic ValidationError from invalid status should become ToolError."""
    with pytest.raises(ToolError, match="Invalid status"):
        await track_application(
            job_id="x", job_title="x", company="x",
            status="NOT_A_STATUS", notes="",
        )
