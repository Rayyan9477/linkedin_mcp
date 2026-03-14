"""Cover letter generation service with AI and template rendering."""

import asyncio
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from linkedin_mcp.ai.base import AIProvider
from linkedin_mcp.exceptions import TemplateError
from linkedin_mcp.models.resume import CoverLetterContent, GeneratedDocument
from linkedin_mcp.services.format_converter import convert_html_to_markdown, convert_html_to_pdf
from linkedin_mcp.services.job_search import JobSearchService
from linkedin_mcp.services.profile import ProfileService
from linkedin_mcp.services.template_manager import TemplateManager

logger = logging.getLogger("linkedin-mcp.cover_letter")


class CoverLetterGeneratorService:
    """Generates AI-powered cover letters for job applications."""

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

    async def generate_cover_letter(
        self, profile_id: str, job_id: str, template: str = "professional", format: str = "html"
    ) -> GeneratedDocument:
        """Generate a personalized cover letter for a job."""
        profile = await self._profiles.get_profile(profile_id)
        job = await self._jobs.get_job_details(job_id)

        profile_data = profile.model_dump()
        job_data = job.model_dump()

        if self._ai:
            try:
                ai_content = await self._ai.generate_cover_letter(profile_data, job_data)
                content = CoverLetterContent(
                    date=datetime.now().strftime("%B %d, %Y"),
                    candidate_name=profile.name,
                    candidate_contact=f"{profile.email} | {profile.phone}".strip(" |"),
                    recipient=ai_content.get("recipient", "Hiring Manager"),
                    company=job.company,
                    job_title=job.title,
                    greeting=ai_content.get("greeting", "Dear Hiring Manager,"),
                    introduction=ai_content.get("introduction", ""),
                    body_paragraphs=ai_content.get("body_paragraphs", []),
                    closing=ai_content.get("closing", ""),
                    signature=ai_content.get("signature", f"Sincerely,\n{profile.name}"),
                )
            except Exception as e:
                logger.warning(f"AI generation failed, using basic template: {e}")
                content = self._build_basic_content(profile_data, job_data)
        else:
            content = self._build_basic_content(profile_data, job_data)

        return await self._render(content, profile_id, job_id, template, format)

    def list_templates(self) -> dict[str, str]:
        """List available cover letter templates."""
        return self._templates.get_available_templates("cover_letter")

    def _build_basic_content(
        self, profile: dict[str, Any], job: dict[str, Any]
    ) -> CoverLetterContent:
        """Build basic cover letter content without AI."""
        name = profile.get("name", "Candidate")
        title = job.get("title", "the position")
        company = job.get("company", "your company")

        return CoverLetterContent(
            date=datetime.now().strftime("%B %d, %Y"),
            candidate_name=name,
            candidate_contact=f"{profile.get('email', '')} | {profile.get('phone', '')}".strip(" |"),
            company=company,
            job_title=title,
            greeting="Dear Hiring Manager,",
            introduction=f"I am writing to express my interest in the {title} position at {company}.",
            body_paragraphs=[
                f"With my background as {profile.get('headline', 'a professional')}, "
                f"I bring relevant experience and skills to this role.",
                f"My key skills include: {', '.join(profile.get('skills', [])[:5])}.",
            ],
            closing=f"I am excited about the opportunity to contribute to {company} and would welcome the chance to discuss how my experience aligns with your needs.",
            signature=f"Sincerely,\n{name}",
        )

    async def _render(
        self,
        content: CoverLetterContent,
        profile_id: str,
        job_id: str,
        template: str,
        format: str,
    ) -> GeneratedDocument:
        """Render cover letter to the requested format."""
        context = content.model_dump()

        available = self.list_templates()
        if template not in available:
            if available:
                template = next(iter(available))
            else:
                raise TemplateError("No cover letter templates available")

        try:
            html = self._templates.render_template("cover_letter", template, context)
        except Exception as e:
            raise TemplateError(f"Failed to render cover letter template: {e}") from e

        metadata = {
            "profile_id": profile_id,
            "job_id": job_id,
            "template": template,
            "generated_at": datetime.now().isoformat(),
        }

        if format == "md":
            return GeneratedDocument(
                content=convert_html_to_markdown(html), format="md", metadata=metadata
            )
        elif format == "pdf":
            safe_profile = re.sub(r'[^\w\-]', '_', profile_id)
            safe_job = re.sub(r'[^\w\-]', '_', job_id)
            filename = f"cover_letter_{safe_profile}_{safe_job}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
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
