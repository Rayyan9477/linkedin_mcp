"""Job search service with caching."""

import logging

from typing import Any

from linkedin_mcp.models.linkedin import JobDetails, JobListing, JobSearchFilter
from linkedin_mcp.services.cache import JSONCache
from linkedin_mcp.services.linkedin_client import LinkedInClient

logger = logging.getLogger("linkedin-mcp.jobs")


class JobSearchService:
    """Job search and discovery service."""

    def __init__(self, client: LinkedInClient, cache: JSONCache):
        self._client = client
        self._cache = cache

    async def search_jobs(
        self, filter: JobSearchFilter, page: int = 1, count: int = 20
    ) -> dict[str, Any]:
        """Search for jobs with filters. Returns paginated results."""
        offset = (page - 1) * count
        jobs = await self._client.search_jobs(
            keywords=filter.keywords,
            location=filter.location,
            limit=count,
            offset=offset,
            job_type=filter.job_type,
            experience_level=filter.experience_level,
            remote=filter.remote,
            date_posted=filter.date_posted,
        )

        # Cache individual job listings
        for job in jobs:
            await self._cache.set("jobs", job.job_id, job.model_dump())

        return {
            "jobs": [j.model_dump() for j in jobs],
            "page": page,
            "count": len(jobs),
            "has_more": len(jobs) == count,
        }

    async def get_job_details(self, job_id: str) -> JobDetails:
        """Get job details, checking cache first."""
        cached = await self._cache.get("jobs", job_id)
        if cached and "description" in cached and cached["description"]:
            return JobDetails(**cached)

        details = await self._client.get_job(job_id)
        await self._cache.set("jobs", job_id, details.model_dump())
        return details

    async def get_recommended_jobs(self, count: int = 10) -> list[JobListing]:
        """Get recommended jobs (delegates to search with empty query)."""
        jobs = await self._client.search_jobs(limit=count)
        return jobs
