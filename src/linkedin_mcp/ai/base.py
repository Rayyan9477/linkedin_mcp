"""Abstract AI provider interface.

Allows swapping AI backends (Claude, OpenAI, etc.) without changing service code.
"""

from abc import ABC, abstractmethod
from typing import Any


class AIProvider(ABC):
    """Abstract interface for AI-powered content generation."""

    @abstractmethod
    async def enhance_resume(
        self, profile_data: dict[str, Any], job_data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Enhance resume content. Returns structured resume sections.

        Args:
            profile_data: LinkedIn profile data
            job_data: Optional job posting to tailor resume for

        Returns:
            Dict with enhanced: summary, experience descriptions, skills ordering
        """

    @abstractmethod
    async def generate_cover_letter(
        self, profile_data: dict[str, Any], job_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Generate cover letter content.

        Returns:
            Dict with: greeting, introduction, body_paragraphs, closing, signature
        """

    @abstractmethod
    async def analyze_profile(self, profile_data: dict[str, Any]) -> dict[str, Any]:
        """Analyze profile and suggest improvements.

        Returns:
            Dict with suggestions for: headline, summary, experience, skills
        """
