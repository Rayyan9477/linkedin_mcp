"""Anthropic Claude AI provider for content generation."""

import json
import logging
from typing import Any

from linkedin_mcp.ai.base import AIProvider
from linkedin_mcp.exceptions import AIProviderError

logger = logging.getLogger("linkedin-mcp.ai")


class ClaudeProvider(AIProvider):
    """AI provider using Anthropic Claude for content generation."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        try:
            from anthropic import AsyncAnthropic

            self._client = AsyncAnthropic(api_key=api_key)
        except ImportError:
            raise AIProviderError("anthropic package is required. Install with: pip install anthropic")
        self._model = model

    async def _generate(self, system: str, user: str) -> str:
        """Make a Claude API call and return the text response."""
        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=4096,
                messages=[{"role": "user", "content": user}],
                system=system,
            )
            return response.content[0].text
        except Exception as e:
            raise AIProviderError(f"Claude API call failed: {e}") from e

    async def _generate_json(self, system: str, user: str) -> dict[str, Any]:
        """Make a Claude API call expecting JSON output."""
        system_with_json = system + "\n\nIMPORTANT: Respond ONLY with valid JSON. No markdown, no explanation."
        text = await self._generate(system_with_json, user)

        # Extract JSON from response (handle potential markdown wrapping)
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise AIProviderError(f"Failed to parse AI response as JSON: {e}") from e

    async def enhance_resume(
        self, profile_data: dict[str, Any], job_data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Enhance resume content using Claude."""
        system = """You are an expert resume writer. Your task is to enhance a resume based on
LinkedIn profile data. Improve descriptions to highlight achievements and impact using
action verbs and quantifiable results. Keep content truthful — enhance wording, don't
fabricate experience."""

        job_context = ""
        if job_data:
            job_context = f"""
The resume should be tailored for this specific job:
- Title: {job_data.get('title', 'N/A')}
- Company: {job_data.get('company', 'N/A')}
- Description: {job_data.get('description', 'N/A')[:1500]}
- Required skills: {', '.join(job_data.get('skills', []))}

Prioritize experience and skills that match this job. Reorder skills to lead with
the most relevant ones."""

        user = f"""Enhance this resume profile data. {job_context}

Profile:
{json.dumps(profile_data, indent=2, default=str)}

Return a JSON object with:
{{
  "summary": "Enhanced professional summary (2-3 sentences)",
  "experience": [
    {{
      "title": "...",
      "company": "...",
      "location": "...",
      "start_date": "...",
      "end_date": "...",
      "description": "Enhanced description with achievements and impact"
    }}
  ],
  "skills": ["ordered by relevance"],
  "highlights": ["3-5 key career highlights"]
}}"""

        return await self._generate_json(system, user)

    async def generate_cover_letter(
        self, profile_data: dict[str, Any], job_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Generate a personalized cover letter."""
        system = """You are an expert cover letter writer. Create compelling, personalized cover
letters that connect the candidate's experience with the job requirements. Be professional
but genuine — avoid generic phrases. Each paragraph should serve a specific purpose."""

        user = f"""Write a cover letter for this candidate and job.

Candidate Profile:
- Name: {profile_data.get('name', 'N/A')}
- Headline: {profile_data.get('headline', 'N/A')}
- Summary: {profile_data.get('summary', 'N/A')[:500]}
- Top Skills: {', '.join(profile_data.get('skills', [])[:10])}
- Recent Experience: {json.dumps(profile_data.get('experience', [])[:3], default=str)}

Job Details:
- Title: {job_data.get('title', 'N/A')}
- Company: {job_data.get('company', 'N/A')}
- Description: {job_data.get('description', 'N/A')[:1500]}
- Required Skills: {', '.join(job_data.get('skills', []))}

Return a JSON object with:
{{
  "greeting": "Dear [appropriate greeting],",
  "introduction": "Opening paragraph connecting candidate to the role",
  "body_paragraphs": [
    "Paragraph about relevant experience and achievements",
    "Paragraph about skills and how they match requirements",
    "Paragraph about cultural fit and enthusiasm for the company"
  ],
  "closing": "Professional closing paragraph with call to action",
  "signature": "Sincerely,\\n{profile_data.get('name', 'Candidate')}"
}}"""

        return await self._generate_json(system, user)

    async def analyze_profile(self, profile_data: dict[str, Any]) -> dict[str, Any]:
        """Analyze a LinkedIn profile and suggest improvements."""
        system = """You are a LinkedIn profile optimization expert. Analyze profiles and provide
specific, actionable suggestions to improve visibility, searchability, and professional
appeal. Focus on what would make the biggest impact."""

        user = f"""Analyze this LinkedIn profile and suggest improvements.

Profile:
{json.dumps(profile_data, indent=2, default=str)}

Return a JSON object with:
{{
  "overall_score": 75,
  "headline_suggestions": ["suggestion 1", "suggestion 2"],
  "summary_suggestions": ["specific improvement 1"],
  "experience_suggestions": ["how to improve experience descriptions"],
  "skills_suggestions": ["skills to add or reorder"],
  "general_tips": ["other profile improvements"],
  "keyword_recommendations": ["keywords to incorporate for better searchability"]
}}"""

        return await self._generate_json(system, user)
