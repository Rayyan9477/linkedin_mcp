"""Tests for LinkedInClient data formatting methods."""

import pytest

from linkedin_mcp.services.linkedin_client import LinkedInClient
from linkedin_mcp.models.linkedin import JobListing, JobDetails, Profile, CompanyInfo


@pytest.fixture
def client():
    """LinkedInClient with dummy settings (won't authenticate)."""
    from unittest.mock import MagicMock
    settings = MagicMock()
    return LinkedInClient(settings)


class TestFormatDate:
    def test_empty_dict(self, client):
        assert client._format_date({}) == ""

    def test_none(self, client):
        assert client._format_date(None) == ""

    def test_year_only(self, client):
        assert client._format_date({"year": 2020}) == "2020"

    def test_month_and_year(self, client):
        assert client._format_date({"month": 3, "year": 2021}) == "Mar 2021"

    def test_month_zero(self, client):
        assert client._format_date({"month": 0, "year": 2021}) == "2021"

    def test_month_exceeds_12(self, client):
        result = client._format_date({"month": 15, "year": 2021})
        assert result == "Dec 2021"


class TestFormatJobListing:
    def test_basic(self, client):
        job = {
            "entityUrn": "urn:li:jobPosting:12345",
            "title": "Engineer",
            "companyName": "Acme",
            "formattedLocation": "NYC",
        }
        result = client._format_job_listing(job)
        assert isinstance(result, JobListing)
        assert result.job_id == "12345"
        assert result.title == "Engineer"
        assert result.company == "Acme"
        assert "12345" in result.url

    def test_fallback_to_job_posting_id(self, client):
        job = {"jobPostingId": "999", "title": "Dev", "companyName": "Co"}
        result = client._format_job_listing(job)
        assert result.job_id == "999"

    def test_missing_entity_urn(self, client):
        job = {"title": "Dev", "companyName": "Co"}
        result = client._format_job_listing(job)
        assert result.title == "Dev"


class TestFormatJobDetails:
    def test_basic(self, client):
        job = {
            "title": "Engineer",
            "companyDetails": {"company": "Acme"},
            "formattedLocation": "NYC",
            "description": {"text": "Job description here"},
            "matchedSkills": [
                {"skill": {"name": "Python"}},
                "JavaScript",
            ],
        }
        result = client._format_job_details("123", job)
        assert isinstance(result, JobDetails)
        assert result.title == "Engineer"
        assert result.company == "Acme"
        assert result.description == "Job description here"
        assert "Python" in result.skills
        assert "JavaScript" in result.skills

    def test_string_description(self, client):
        job = {"title": "Dev", "description": "Plain string"}
        result = client._format_job_details("1", job)
        assert result.description == "Plain string"


class TestFormatProfile:
    def test_basic(self, client):
        data = {
            "firstName": "Jane",
            "lastName": "Smith",
            "headline": "Engineer",
            "summary": "Summary text",
            "locationName": "NYC",
            "experience": [
                {
                    "title": "Dev",
                    "companyName": "Co",
                    "timePeriod": {
                        "startDate": {"month": 1, "year": 2020},
                        "endDate": {"month": 6, "year": 2022},
                    },
                }
            ],
            "education": [
                {
                    "schoolName": "MIT",
                    "degreeName": "BS",
                    "fieldOfStudy": "CS",
                    "timePeriod": {
                        "startDate": {"year": 2016},
                        "endDate": {"year": 2020},
                    },
                }
            ],
            "languages": [{"name": "English", "proficiency": "Native"}],
            "certifications": [{"name": "AWS", "authority": "Amazon"}],
        }
        skills = [{"name": "Python"}, {"name": "Go"}]
        contact = {"email_address": "jane@example.com", "phone_numbers": ["555-1234"]}

        result = client._format_profile("janesmith", data, skills, contact)
        assert isinstance(result, Profile)
        assert result.name == "Jane Smith"
        assert result.email == "jane@example.com"
        assert result.phone == "555-1234"
        assert len(result.experience) == 1
        assert result.experience[0].start_date == "Jan 2020"
        assert len(result.skills) == 2
        assert result.languages[0]["name"] == "English"


class TestFormatCompany:
    def test_basic(self, client):
        data = {
            "name": "Acme Corp",
            "tagline": "We build things",
            "description": "A company",
            "industryName": "Tech",
            "staffCount": 500,
            "headquarter": {
                "city": "SF",
                "geographicArea": "CA",
                "country": "US",
            },
            "specialities": ["AI", "ML"],
        }
        result = client._format_company("acme", data)
        assert isinstance(result, CompanyInfo)
        assert result.name == "Acme Corp"
        assert result.industry == "Tech"
        assert result.headquarters == "SF, CA, US"
        assert "AI" in result.specialties

    def test_empty_company_industries_fallback(self, client):
        data = {
            "name": "Co",
            "companyIndustries": [{"localizedName": "Finance"}],
        }
        result = client._format_company("co", data)
        assert result.industry == "Finance"

    def test_empty_company_industries_list(self, client):
        data = {"name": "Co", "companyIndustries": []}
        result = client._format_company("co", data)
        assert result.industry == ""
