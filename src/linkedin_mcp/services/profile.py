"""Profile and company service with caching."""

import logging

from linkedin_mcp.models.linkedin import CompanyInfo, Profile
from linkedin_mcp.services.cache import JSONCache
from linkedin_mcp.services.linkedin_client import LinkedInClient

logger = logging.getLogger("linkedin-mcp.profile")


class ProfileService:
    """Profile retrieval and caching service."""

    def __init__(self, client: LinkedInClient, cache: JSONCache):
        self._client = client
        self._cache = cache

    async def get_profile(self, profile_id: str) -> Profile:
        """Get LinkedIn profile, checking cache first."""
        cached = await self._cache.get("profiles", profile_id)
        if cached:
            return Profile(**cached)

        profile = await self._client.get_profile(profile_id)
        await self._cache.set("profiles", profile_id, profile.model_dump())
        return profile

    async def get_company(self, company_id: str) -> CompanyInfo:
        """Get company info, checking cache first."""
        cached = await self._cache.get("companies", company_id)
        if cached:
            return CompanyInfo(**cached)

        company = await self._client.get_company(company_id)
        await self._cache.set("companies", company_id, company.model_dump())
        return company
