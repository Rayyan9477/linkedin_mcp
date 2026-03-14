"""Tests for ProfileService."""

import pytest
from unittest.mock import AsyncMock

from linkedin_mcp.services.cache import JSONCache
from linkedin_mcp.services.profile import ProfileService


@pytest.fixture
def cache(tmp_path):
    return JSONCache(tmp_path / "cache", ttl_hours=1)


@pytest.fixture
def profile_service(mock_linkedin_client, cache):
    return ProfileService(mock_linkedin_client, cache)


@pytest.mark.asyncio
async def test_get_profile(profile_service, mock_linkedin_client, sample_profile):
    mock_linkedin_client.get_profile.return_value = sample_profile
    result = await profile_service.get_profile("johndoe")
    assert result.name == "John Doe"
    assert len(result.skills) == 6


@pytest.mark.asyncio
async def test_get_profile_caches(profile_service, mock_linkedin_client, sample_profile):
    mock_linkedin_client.get_profile.return_value = sample_profile
    result1 = await profile_service.get_profile("johndoe")
    result2 = await profile_service.get_profile("johndoe")
    assert mock_linkedin_client.get_profile.call_count == 1
    assert result1.name == result2.name


@pytest.mark.asyncio
async def test_get_company(profile_service, mock_linkedin_client):
    from linkedin_mcp.models.linkedin import CompanyInfo
    company = CompanyInfo(
        company_id="acme", name="Acme Corp", industry="Tech"
    )
    mock_linkedin_client.get_company.return_value = company
    result = await profile_service.get_company("acme")
    assert result.name == "Acme Corp"
    assert result.industry == "Tech"


@pytest.mark.asyncio
async def test_get_company_caches(profile_service, mock_linkedin_client):
    from linkedin_mcp.models.linkedin import CompanyInfo
    company = CompanyInfo(company_id="acme", name="Acme Corp")
    mock_linkedin_client.get_company.return_value = company
    await profile_service.get_company("acme")
    await profile_service.get_company("acme")
    assert mock_linkedin_client.get_company.call_count == 1
