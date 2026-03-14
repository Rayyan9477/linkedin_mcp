"""Resume generation service with AI enhancement and template rendering."""

import asyncio
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from linkedin_mcp.ai.base import AIProvider
from linkedin_mcp.exceptions import TemplateError
from linkedin_mcp.models.resume import GeneratedDocument, ResumeContent, ResumeEducation, ResumeExperience, ResumeHeader
from linkedin_mcp.services.format_converter import convert_html_to_markdown, convert_html_to_pdf
from linkedin_mcp.services.job_search import JobSearchService
from linkedin_mcp.services.profile import ProfileService
from linkedin_mcp.services.template_manager import TemplateManager

logger = logging.getLogger("linkedin-mcp.resume")


class ResumeGeneratorService:
    """Generates AI-enhanced resumes from LinkedIn profiles."""

    def __init__(
        self,
        profile_service: ProfileService,
        job_service: JobSearchService,
        ai_provider: AIProvider | None,
        template_manager: TemplateManager,
        output_dir: Path,
    ):
        self._profiles = profile_service
        self._jobs = job_service
        self._ai = ai_provider
        self._templates = template_manager
        self._output_dir = output_dir
        self._output_dir.mkdir(parents=True, exist_ok=True)

    async def generate_resume(
        self, profile_id: str, template: str = "modern", format: str = "html"
    ) -> GeneratedDocument:
        """Generate a resume from a LinkedIn profile."""
        profile = await self._profiles.get_profile(profile_id)
        profile_data = profile.model_dump()

        # Enhance with AI if available
        enhanced = None
        if self._ai:
            try:
                enhanced = await self._ai.enhance_resume(profile_data)
            except Exception as e:
                logger.warning(f"AI enhancement failed, using raw profile: {e}")

        content = self._build_resume_content(profile_data, enhanced)
        return await self._render(content, profile_id, template, format)

    async def tailor_resume(
        self, profile_id: str, job_id: str, template: str = "modern", format: str = "html"
    ) -> GeneratedDocument:
        """Generate a resume tailored to a specific job."""
        profile = await self._profiles.get_profile(profile_id)
        job = await self._jobs.get_job_details(job_id)
        profile_data = profile.model_dump()
        job_data = job.model_dump()

        enhanced = None
        if self._ai:
            try:
                enhanced = await self._ai.enhance_resume(profile_data, job_data)
            except Exception as e:
                logger.warning(f"AI enhancement failed, using raw profile: {e}")

        content = self._build_resume_content(profile_data, enhanced)
        return await self._render(content, profile_id, template, format, job_id=job_id)

    def list_templates(self) -> dict[str, str]:
        """List available resume templates."""
        return self._templates.get_available_templates("resume")

    def _build_resume_content(
        self, profile: dict[str, Any], enhanced: dict[str, Any] | None
    ) -> ResumeContent:
        """Build resume content from profile data and optional AI enhancement."""
        header = ResumeHeader(
            name=profile.get("name", ""),
            headline=profile.get("headline", ""),
            email=profile.get("email", ""),
            phone=profile.get("phone", ""),
            location=profile.get("location", ""),
            linkedin_url=profile.get("profile_url", ""),
        )

        # Use enhanced data if available, fall back to profile
        summary = (enhanced or {}).get("summary", profile.get("summary", ""))

        experience_data = (enhanced or {}).get("experience", profile.get("experience", []))
        experience = [
            ResumeExperience(
                title=exp.get("title", ""),
                company=exp.get("company", ""),
                location=exp.get("location", ""),
                start_date=exp.get("start_date", ""),
                end_date=exp.get("end_date", "Present"),
                description=exp.get("description", ""),
            )
            for exp in experience_data
        ]

        education = [
            ResumeEducation(
                school=edu.get("school", ""),
                degree=edu.get("degree", ""),
                field=edu.get("field_of_study", edu.get("field", "")),
                start_date=edu.get("start_date", ""),
                end_date=edu.get("end_date", ""),
            )
            for edu in profile.get("education", [])
        ]

        skills = (enhanced or {}).get("skills", profile.get("skills", []))

        return ResumeContent(
            header=header,
            summary=summary,
            experience=experience,
            education=education,
            skills=skills,
            certifications=profile.get("certifications", []),
            languages=profile.get("languages", []),
        )

    async def _render(
        self,
        content: ResumeContent,
        profile_id: str,
        template: str,
        format: str,
        job_id: str | None = None,
    ) -> GeneratedDocument:
        """Render resume content to the requested format."""
        context = content.model_dump()

        # Check template exists, fall back to first available
        available = self.list_templates()
        if template not in available:
            if available:
                template = next(iter(available))
                logger.info(f"Template not found, using '{template}'")
            else:
                raise TemplateError("No resume templates available")

        try:
            html = self._templates.render_template("resume", template, context)
        except Exception as e:
            raise TemplateError(f"Failed to render resume template: {e}") from e

        metadata = {
            "profile_id": profile_id,
            "template": template,
            "generated_at": datetime.now().isoformat(),
        }
        if job_id:
            metadata["job_id"] = job_id

        if format == "md":
            return GeneratedDocument(
                content=convert_html_to_markdown(html), format="md", metadata=metadata
            )
        elif format == "pdf":
            safe_id = re.sub(r'[^\w\-]', '_', profile_id)
            filename = f"resume_{safe_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            output_path = self._output_dir / filename
            await asyncio.to_thread(convert_html_to_pdf, html, output_path)
            return GeneratedDocument(
                content=f"PDF saved to: {output_path}",
                format="pdf",
                file_path=str(output_path),
                metadata=metadata,
            )
        else:
            return GeneratedDocument(content=html, format="html", metadata=metadata)
