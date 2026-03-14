"""LinkedIn MCP Server — entry point using FastMCP.

Registers all tools, resources, and prompts. Initializes services via async lifespan.
"""

import asyncio
import logging
import json
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dataclasses import dataclass

from mcp.server.fastmcp import FastMCP, Context
from mcp.server.fastmcp.exceptions import ToolError
from pydantic import ValidationError

from linkedin_mcp.ai.claude_provider import ClaudeProvider
from linkedin_mcp.config import get_settings
from linkedin_mcp.exceptions import LinkedInMCPError
from linkedin_mcp.services.application_tracker import ApplicationTrackerService
from linkedin_mcp.services.cache import JSONCache
from linkedin_mcp.services.cover_letter_generator import CoverLetterGeneratorService
from linkedin_mcp.services.job_search import JobSearchService
from linkedin_mcp.services.linkedin_client import LinkedInClient
from linkedin_mcp.services.profile import ProfileService
from linkedin_mcp.services.resume_generator import ResumeGeneratorService
from linkedin_mcp.services.template_manager import TemplateManager

logger = logging.getLogger("linkedin-mcp")


@dataclass
class AppContext:
    """Application context holding all initialized services."""

    client: LinkedInClient
    cache: JSONCache
    jobs: JobSearchService
    profiles: ProfileService
    resume_gen: ResumeGeneratorService
    cover_letter_gen: CoverLetterGeneratorService
    tracker: ApplicationTrackerService
    ai: ClaudeProvider | None


def _get_app_context() -> AppContext:
    """Initialize all services. Called once at startup."""
    settings = get_settings()

    client = LinkedInClient(settings)
    cache = JSONCache(settings.data_dir / "cache", ttl_hours=settings.cache_ttl_hours)
    template_manager = TemplateManager()

    ai = None
    if settings.has_ai:
        ai = ClaudeProvider(settings.anthropic_api_key, settings.ai_model)

    jobs = JobSearchService(client, cache)
    profiles = ProfileService(client, cache)
    resume_gen = ResumeGeneratorService(
        profiles, jobs, ai, template_manager, settings.data_dir / "resumes"
    )
    cover_letter_gen = CoverLetterGeneratorService(
        profiles, jobs, ai, template_manager, settings.data_dir / "cover_letters"
    )
    tracker = ApplicationTrackerService(settings.data_dir)

    return AppContext(
        client=client,
        cache=cache,
        jobs=jobs,
        profiles=profiles,
        resume_gen=resume_gen,
        cover_letter_gen=cover_letter_gen,
        tracker=tracker,
        ai=ai,
    )


# Lazy-initialized app context with async lock for thread safety
_app_ctx: AppContext | None = None
_app_ctx_lock = asyncio.Lock()


async def get_ctx() -> AppContext:
    global _app_ctx
    if _app_ctx is not None:
        return _app_ctx
    async with _app_ctx_lock:
        if _app_ctx is None:
            _app_ctx = _get_app_context()
    return _app_ctx


# ── Lifespan ──────────────────────────────────────────────────────────────


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[dict]:
    """Validate config and pre-initialize services on startup."""
    settings = get_settings()
    errors = settings.validate()
    if errors:
        logger.warning(f"Configuration warnings: {', '.join(errors)}")

    # Pre-initialize context eagerly so startup failures are visible
    global _app_ctx
    _app_ctx = _get_app_context()
    logger.info("LinkedIn MCP Server initialized")
    try:
        yield {}
    finally:
        logger.info("LinkedIn MCP Server shutting down")


mcp = FastMCP("linkedin-mcp", lifespan=app_lifespan)


# ── Helpers ───────────────────────────────────────────────────────────────

_VALID_FORMATS = {"html", "md", "pdf"}


def _validate_format(output_format: str) -> None:
    """Raise ToolError if format is invalid."""
    if output_format not in _VALID_FORMATS:
        raise ToolError(
            f"Invalid format '{output_format}'. Must be one of: {sorted(_VALID_FORMATS)}"
        )


def _resolve_profile_id(profile_id: str) -> str:
    """Resolve 'me' to the configured LinkedIn username."""
    if profile_id == "me":
        username = get_settings().linkedin_username
        if not username:
            raise ToolError(
                "LinkedIn username not configured. Set LINKEDIN_USERNAME environment variable."
            )
        return username
    return profile_id


# ── Job Tools ──────────────────────────────────────────────────────────────


@mcp.tool()
async def search_jobs(
    keywords: str,
    location: str = "",
    job_type: str = "",
    experience_level: str = "",
    remote: bool = False,
    date_posted: str = "",
    page: int = 1,
    count: int = 20,
) -> str:
    """Search for job listings on LinkedIn with filters.

    Args:
        keywords: Search keywords (job title, skills, company)
        location: Geographic location (city, state, country)
        job_type: Filter by type: FULL_TIME, PART_TIME, CONTRACT, TEMPORARY, INTERNSHIP
        experience_level: Filter: INTERNSHIP, ENTRY_LEVEL, ASSOCIATE, MID_SENIOR, DIRECTOR, EXECUTIVE
        remote: Filter for remote jobs only
        date_posted: Filter by recency: past-24h, past-week, past-month
        page: Page number for pagination (default 1)
        count: Results per page (1-50, default 20)
    """
    try:
        from linkedin_mcp.models.linkedin import JobSearchFilter

        ctx = await get_ctx()
        search_filter = JobSearchFilter(
            keywords=keywords,
            location=location,
            job_type=[job_type] if job_type else None,
            experience_level=[experience_level] if experience_level else None,
            remote=remote or None,
            date_posted=date_posted or None,
        )
        result = await ctx.jobs.search_jobs(search_filter, max(page, 1), max(min(count, 50), 1))
        return json.dumps(result, indent=2, default=str)
    except LinkedInMCPError as e:
        raise ToolError(str(e)) from e


@mcp.tool()
async def get_job_details(job_id: str) -> str:
    """Get detailed information about a specific LinkedIn job posting.

    Args:
        job_id: LinkedIn job ID
    """
    try:
        ctx = await get_ctx()
        details = await ctx.jobs.get_job_details(job_id)
        return json.dumps(details.model_dump(), indent=2, default=str)
    except LinkedInMCPError as e:
        raise ToolError(str(e)) from e


@mcp.tool()
async def get_recommended_jobs(count: int = 10) -> str:
    """Get job recommendations from LinkedIn.

    Args:
        count: Number of recommendations (1-25, default 10)
    """
    try:
        ctx = await get_ctx()
        jobs = await ctx.jobs.get_recommended_jobs(max(min(count, 25), 1))
        return json.dumps([j.model_dump() for j in jobs], indent=2, default=str)
    except LinkedInMCPError as e:
        raise ToolError(str(e)) from e


# ── Profile Tools ──────────────────────────────────────────────────────────


@mcp.tool()
async def get_profile(profile_id: str) -> str:
    """Retrieve a LinkedIn profile including experience, education, and skills.

    Args:
        profile_id: LinkedIn profile ID (username slug) or 'me' for self
    """
    try:
        ctx = await get_ctx()
        profile_id = _resolve_profile_id(profile_id)
        profile = await ctx.profiles.get_profile(profile_id)
        return json.dumps(profile.model_dump(), indent=2, default=str)
    except LinkedInMCPError as e:
        raise ToolError(str(e)) from e


@mcp.tool()
async def get_company(company_id: str) -> str:
    """Get company information from LinkedIn.

    Args:
        company_id: LinkedIn company ID or URL slug
    """
    try:
        ctx = await get_ctx()
        company = await ctx.profiles.get_company(company_id)
        return json.dumps(company.model_dump(), indent=2, default=str)
    except LinkedInMCPError as e:
        raise ToolError(str(e)) from e


@mcp.tool()
async def analyze_profile(profile_id: str) -> str:
    """Analyze a LinkedIn profile using AI and provide optimization suggestions.

    Args:
        profile_id: LinkedIn profile ID or 'me' for self
    """
    try:
        ctx = await get_ctx()
        if not ctx.ai:
            raise ToolError("AI provider not configured. Set ANTHROPIC_API_KEY.")

        profile_id = _resolve_profile_id(profile_id)
        profile = await ctx.profiles.get_profile(profile_id)
        analysis = await ctx.ai.analyze_profile(profile.model_dump())
        return json.dumps(analysis, indent=2, default=str)
    except LinkedInMCPError as e:
        raise ToolError(str(e)) from e


# ── Resume & Cover Letter Tools ───────────────────────────────────────────


@mcp.tool()
async def generate_resume(
    profile_id: str, template: str = "modern", output_format: str = "html"
) -> str:
    """Generate a professional resume from a LinkedIn profile using AI enhancement.

    Args:
        profile_id: LinkedIn profile ID or 'me' for self
        template: Template name (modern, professional, minimal)
        output_format: Output format (html, md, pdf)
    """
    _validate_format(output_format)
    try:
        ctx = await get_ctx()
        profile_id = _resolve_profile_id(profile_id)
        doc = await ctx.resume_gen.generate_resume(profile_id, template, output_format)
        if output_format == "pdf":
            return json.dumps({"format": "pdf", "file_path": doc.file_path, "metadata": doc.metadata})
        return doc.content
    except (LinkedInMCPError, RuntimeError) as e:
        raise ToolError(str(e)) from e


@mcp.tool()
async def tailor_resume(
    profile_id: str, job_id: str, template: str = "modern", output_format: str = "html"
) -> str:
    """Generate a resume tailored to a specific job posting.

    Args:
        profile_id: LinkedIn profile ID or 'me' for self
        job_id: LinkedIn job ID to tailor the resume for
        template: Template name (modern, professional, minimal)
        output_format: Output format (html, md, pdf)
    """
    _validate_format(output_format)
    try:
        ctx = await get_ctx()
        profile_id = _resolve_profile_id(profile_id)
        doc = await ctx.resume_gen.tailor_resume(profile_id, job_id, template, output_format)
        if output_format == "pdf":
            return json.dumps({"format": "pdf", "file_path": doc.file_path, "metadata": doc.metadata})
        return doc.content
    except (LinkedInMCPError, RuntimeError) as e:
        raise ToolError(str(e)) from e


@mcp.tool()
async def generate_cover_letter(
    profile_id: str, job_id: str, template: str = "professional", output_format: str = "html"
) -> str:
    """Generate a personalized cover letter for a specific job posting.

    Args:
        profile_id: LinkedIn profile ID or 'me' for self
        job_id: LinkedIn job ID
        template: Template name (professional, concise)
        output_format: Output format (html, md, pdf)
    """
    _validate_format(output_format)
    try:
        ctx = await get_ctx()
        profile_id = _resolve_profile_id(profile_id)
        doc = await ctx.cover_letter_gen.generate_cover_letter(profile_id, job_id, template, output_format)
        if output_format == "pdf":
            return json.dumps({"format": "pdf", "file_path": doc.file_path, "metadata": doc.metadata})
        return doc.content
    except (LinkedInMCPError, RuntimeError) as e:
        raise ToolError(str(e)) from e


@mcp.tool()
async def list_templates(template_type: str = "all") -> str:
    """List all available templates for resumes and cover letters.

    Args:
        template_type: Template type to list: 'resume', 'cover_letter', or 'all'
    """
    if template_type not in ("resume", "cover_letter", "all"):
        raise ToolError(
            f"Invalid template_type '{template_type}'. Must be 'resume', 'cover_letter', or 'all'."
        )
    ctx = await get_ctx()
    result = {}
    if template_type in ("resume", "all"):
        result["resume"] = ctx.resume_gen.list_templates()
    if template_type in ("cover_letter", "all"):
        result["cover_letter"] = ctx.cover_letter_gen.list_templates()
    return json.dumps(result, indent=2)


# ── Application Tracking Tools ────────────────────────────────────────────


@mcp.tool()
async def track_application(
    job_id: str,
    job_title: str,
    company: str,
    status: str = "interested",
    notes: str = "",
    url: str = "",
) -> str:
    """Track a job application locally. Status: interested, applied, interviewing, offered, rejected, withdrawn.

    Args:
        job_id: LinkedIn job ID
        job_title: Job title
        company: Company name
        status: Application status
        notes: Optional notes
        url: Optional job URL
    """
    try:
        from linkedin_mcp.models.tracking import TrackedApplication

        ctx = await get_ctx()
        app = TrackedApplication(
            job_id=job_id, job_title=job_title, company=company, status=status, notes=notes, url=url
        )
        result = await ctx.tracker.track_application(app)
        return json.dumps(result.model_dump(), indent=2, default=str)
    except ValidationError:
        raise ToolError(
            "Invalid status. Must be one of: interested, applied, interviewing, offered, rejected, withdrawn."
        )
    except (LinkedInMCPError, ValueError) as e:
        raise ToolError(str(e)) from e


@mcp.tool()
async def list_applications(status: str = "") -> str:
    """List all tracked job applications, optionally filtered by status.

    Args:
        status: Filter by status (interested, applied, interviewing, offered, rejected, withdrawn). Empty for all.
    """
    try:
        ctx = await get_ctx()
        apps = await ctx.tracker.list_applications(status or None)
        return json.dumps([a.model_dump() for a in apps], indent=2, default=str)
    except LinkedInMCPError as e:
        raise ToolError(str(e)) from e


@mcp.tool()
async def update_application_status(job_id: str, status: str, notes: str = "") -> str:
    """Update the status of a tracked job application.

    Args:
        job_id: LinkedIn job ID
        status: New status (interested, applied, interviewing, offered, rejected, withdrawn)
        notes: Optional notes about the update
    """
    try:
        ctx = await get_ctx()
        app = await ctx.tracker.update_status(job_id, status, notes)
        return json.dumps(app.model_dump(), indent=2, default=str)
    except ValidationError:
        raise ToolError(
            "Invalid status. Must be one of: interested, applied, interviewing, offered, rejected, withdrawn."
        )
    except (LinkedInMCPError, ValueError) as e:
        raise ToolError(str(e)) from e


# ── Resources ─────────────────────────────────────────────────────────────


@mcp.resource("linkedin://applications")
async def applications_resource() -> str:
    """Summary of all tracked job applications."""
    try:
        ctx = await get_ctx()
        apps = await ctx.tracker.list_applications()
        summary = {
            "total": len(apps),
            "by_status": {},
            "applications": [a.model_dump() for a in apps],
        }
        for app in apps:
            summary["by_status"][app.status] = summary["by_status"].get(app.status, 0) + 1
        return json.dumps(summary, indent=2, default=str)
    except Exception as e:
        logger.error(f"Failed to load applications resource: {e}")
        return json.dumps({"error": "Failed to load applications", "total": 0, "applications": []})


@mcp.resource("linkedin://profile/{profile_id}")
async def profile_resource(profile_id: str) -> str:
    """Retrieve a cached LinkedIn profile."""
    try:
        ctx = await get_ctx()
        profile_id = _resolve_profile_id(profile_id)
        profile = await ctx.profiles.get_profile(profile_id)
        return json.dumps(profile.model_dump(), indent=2, default=str)
    except Exception as e:
        logger.error(f"Failed to load profile resource: {e}")
        return json.dumps({"error": str(e)})


@mcp.resource("linkedin://job/{job_id}")
async def job_resource(job_id: str) -> str:
    """Retrieve cached job details."""
    try:
        ctx = await get_ctx()
        job = await ctx.jobs.get_job_details(job_id)
        return json.dumps(job.model_dump(), indent=2, default=str)
    except Exception as e:
        logger.error(f"Failed to load job resource: {e}")
        return json.dumps({"error": str(e)})


# ── Prompts ───────────────────────────────────────────────────────────────


@mcp.prompt()
async def job_search_workflow(role: str, location: str = "") -> str:
    """Guide through searching for jobs, reviewing listings, and tracking applications."""
    loc = f" in {location}" if location else ""
    return f"""Help me find {role} jobs{loc}.

Steps:
1. Search for jobs matching my criteria using search_jobs
2. Review the most promising listings with get_job_details
3. Compare them with my profile using get_profile('me')
4. Track interesting ones with track_application
5. Generate tailored resumes for top choices with tailor_resume"""


@mcp.prompt()
async def application_workflow(job_id: str) -> str:
    """Guide through preparing a complete application for a specific job."""
    return f"""Help me prepare a complete application for job {job_id}.

Steps:
1. Get the full job details with get_job_details('{job_id}')
2. Review my profile with get_profile('me')
3. Generate a tailored resume with tailor_resume('me', '{job_id}')
4. Generate a cover letter with generate_cover_letter('me', '{job_id}')
5. Track this application with track_application"""


@mcp.prompt()
async def profile_optimization() -> str:
    """Guide through optimizing a LinkedIn profile."""
    return """Help me optimize my LinkedIn profile.

Steps:
1. Analyze my current profile with analyze_profile('me')
2. Review the suggestions and prioritize changes
3. Generate a polished resume to see how the profile looks in document form with generate_resume('me')"""


# ── Entry Point ───────────────────────────────────────────────────────────


def main():
    """Run the LinkedIn MCP server."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    settings = get_settings()

    # Override log level from settings
    log_level = getattr(logging, settings.log_level, logging.INFO)
    logging.getLogger().setLevel(log_level)

    errors = settings.validate()
    if errors:
        logger.warning(f"Configuration warnings: {', '.join(errors)}")

    logger.info("Starting LinkedIn MCP Server")
    mcp.run()


if __name__ == "__main__":
    main()
