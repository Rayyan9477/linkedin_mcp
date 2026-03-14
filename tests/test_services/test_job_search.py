"""Tests for JobSearchService."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from linkedin_mcp.models.linkedin import JobDetails, JobListing, JobSearchFilter
from linkedin_mcp.services.cache import JSONCache
from linkedin_mcp.services.job_search import JobSearchService


def _make_listing(**kwargs):
    defaults = {"job_id": "1", "title": "Dev", "company": "A", "location": "Remote"}
    defaults.update(kwargs)
    return JobListing(**defaults)


@pytest.fixture
def cache(tmp_path):
    return JSONCache(tmp_path / "cache", ttl_hours=1)


@pytest.fixture
def job_service(mock_linkedin_client, cache):
    return JobSearchService(mock_linkedin_client, cache)


@pytest.mark.asyncio
async def test_search_jobs(job_service, mock_linkedin_client):
    mock_linkedin_client.search_jobs.return_value = [_make_listing()]
    filter = JobSearchFilter(keywords="python")
    result = await job_service.search_jobs(filter, page=1, count=10)
    assert isinstance(result, dict)
    assert "jobs" in result
    assert len(result["jobs"]) == 1
    mock_linkedin_client.search_jobs.assert_called_once()


@pytest.mark.asyncio
async def test_get_job_details(job_service, mock_linkedin_client, sample_job_details):
    mock_linkedin_client.get_job.return_value = sample_job_details
    result = await job_service.get_job_details("test_job_456")
    assert result.title == "Senior Machine Learning Engineer"


@pytest.mark.asyncio
async def test_get_job_details_caches(job_service, mock_linkedin_client, sample_job_details):
    mock_linkedin_client.get_job.return_value = sample_job_details
    await job_service.get_job_details("test_job_456")
    await job_service.get_job_details("test_job_456")
    # Second call should use cache, so client called only once
    assert mock_linkedin_client.get_job.call_count == 1


@pytest.mark.asyncio
async def test_get_recommended_jobs(job_service, mock_linkedin_client):
    listings = [_make_listing(job_id="1"), _make_listing(job_id="2")]
    mock_linkedin_client.search_jobs.return_value = listings
    result = await job_service.get_recommended_jobs(10)
    assert len(result) == 2
    mock_linkedin_client.search_jobs.assert_called_with(limit=10)


@pytest.mark.asyncio
async def test_search_jobs_pagination_offset(job_service, mock_linkedin_client):
    mock_linkedin_client.search_jobs.return_value = []
    filter = JobSearchFilter(keywords="python")
    await job_service.search_jobs(filter, page=3, count=10)
    call_kwargs = mock_linkedin_client.search_jobs.call_args[1]
    assert call_kwargs["offset"] == 20  # (3-1) * 10


@pytest.mark.asyncio
async def test_search_jobs_has_more_flag(job_service, mock_linkedin_client):
    # When returned count equals requested count, has_more should be True
    mock_linkedin_client.search_jobs.return_value = [_make_listing(job_id=str(i)) for i in range(5)]
    filter = JobSearchFilter(keywords="python")
    result = await job_service.search_jobs(filter, page=1, count=5)
    assert result["has_more"] is True

    # When fewer results returned, has_more should be False
    mock_linkedin_client.search_jobs.return_value = [_make_listing(job_id="1")]
    result = await job_service.search_jobs(filter, page=1, count=5)
    assert result["has_more"] is False
