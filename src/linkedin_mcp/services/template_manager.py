"""Jinja2 template manager for resume and cover letter rendering.

Reused from original codebase with updated paths.
"""

import logging
from pathlib import Path
from typing import Any

from jinja2 import FileSystemLoader, select_autoescape
from jinja2.sandbox import SandboxedEnvironment

logger = logging.getLogger("linkedin-mcp.templates")


class TemplateManager:
    """Manages Jinja2 templates for resume and cover letter generation."""

    def __init__(self, template_dirs: list[str] | None = None):
        default_dirs = [
            Path(__file__).parent.parent / "templates",
            Path.home() / ".linkedin_mcp" / "templates",
        ]

        self.template_dirs = [Path(d) for d in (template_dirs or [])] + default_dirs

        for template_dir in self.template_dirs:
            try:
                template_dir.mkdir(parents=True, exist_ok=True)
            except OSError:
                pass  # Skip read-only directories (e.g. installed packages)

        self.env = SandboxedEnvironment(
            loader=FileSystemLoader([str(d) for d in self.template_dirs]),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def get_available_templates(self, template_type: str) -> dict[str, str]:
        """Get available templates. Returns {name: display_name}."""
        templates = {}
        for template_dir in self.template_dirs:
            type_dir = template_dir / template_type
            if not type_dir.exists():
                continue
            for template_file in type_dir.glob("*.j2"):
                name = template_file.stem
                templates[name] = name.replace("_", " ").title()
        return templates

    def render_template(
        self,
        template_type: str,
        template_name: str,
        context: dict[str, Any],
        output_format: str = "html",
    ) -> str:
        """Render a template with the given context."""
        template_path = f"{template_type}/{template_name}.j2"
        try:
            template = self.env.get_template(template_path)
            rendered = template.render(**context)
            if output_format == "md":
                rendered = "\n".join(line.rstrip() for line in rendered.split("\n"))
            return rendered
        except Exception as e:
            logger.error(f"Error rendering template {template_path}: {e}")
            raise

    def get_template_preview(
        self,
        template_type: str,
        template_name: str,
        sample_context: dict[str, Any] | None = None,
    ) -> str:
        """Preview a template with sample data."""
        if sample_context is None:
            sample_context = self._get_sample_context(template_type)
        try:
            return self.render_template(template_type, template_name, sample_context)
        except Exception as e:
            return f"Error generating preview: {e}"

    def _get_sample_context(self, template_type: str) -> dict[str, Any]:
        if template_type == "resume":
            return {
                "header": {
                    "name": "John Doe",
                    "headline": "Senior Software Engineer",
                    "email": "john.doe@example.com",
                    "phone": "(123) 456-7890",
                    "location": "San Francisco, CA",
                    "linkedin_url": "https://linkedin.com/in/johndoe",
                },
                "summary": "Experienced software engineer with 5+ years...",
                "experience": [
                    {
                        "title": "Senior Software Engineer",
                        "company": "Tech Corp",
                        "location": "San Francisco, CA",
                        "start_date": "Jan 2020",
                        "end_date": "Present",
                        "description": "Led development of key features...",
                    }
                ],
                "education": [
                    {
                        "school": "UC Berkeley",
                        "degree": "B.S.",
                        "field": "Computer Science",
                        "end_date": "2015",
                    }
                ],
                "skills": ["Python", "JavaScript", "AWS", "Docker"],
                "languages": [{"name": "English", "proficiency": "Native"}],
            }
        else:
            return {
                "date": "2024-01-15",
                "candidate_name": "John Doe",
                "candidate_contact": "john.doe@example.com | (123) 456-7890",
                "recipient": "Hiring Manager",
                "company": "Tech Innovations Inc.",
                "job_title": "Senior Software Engineer",
                "greeting": "Dear Hiring Manager,",
                "introduction": "I am excited to apply...",
                "body_paragraphs": ["With over 5 years of experience..."],
                "closing": "I look forward to discussing...",
                "signature": "Best regards,\nJohn Doe",
            }
