"""Single LinkedIn API client wrapping the linkedin-api library.

All synchronous linkedin-api calls are wrapped in asyncio.to_thread() for
consistent async interface. This is the sole point of contact with LinkedIn.
"""

import asyncio
import logging
from typing import Any

from linkedin_mcp.config import Settings
from linkedin_mcp.exceptions import AuthenticationError, LinkedInAPIError, NotFoundError
from linkedin_mcp.models.linkedin import (
    CompanyInfo,
    Education,
    Experience,
    JobDetails,
    JobListing,
    Profile,
)

logger = logging.getLogger("linkedin-mcp.client")


class LinkedInClient:
    """Async wrapper around the linkedin-api library."""

    def __init__(self, settings: Settings):
        self._settings = settings
        self._api: Any = None  # linkedin_api.Linkedin instance
        self._authenticated = False

    async def ensure_authenticated(self) -> None:
        """Authenticate with LinkedIn. Runs linkedin-api login in thread."""
        if self._authenticated and self._api is not None:
            return

        def _login() -> Any:
            try:
                from linkedin_api import Linkedin

                return Linkedin(
                    self._settings.linkedin_username,
                    self._settings.linkedin_password,
                    refresh_cookies=True,
                )
            except Exception as e:
                error_msg = str(e).lower()
                if "challenge" in error_msg or "captcha" in error_msg:
                    raise AuthenticationError(
                        "LinkedIn security challenge detected. Try logging in via browser first."
                    ) from e
                raise AuthenticationError(f"LinkedIn login failed: {e}") from e

        self._api = await asyncio.to_thread(_login)
        self._authenticated = True
        logger.info("LinkedIn authentication successful")

    async def search_jobs(
        self,
        keywords: str = "",
        location: str = "",
        limit: int = 20,
        offset: int = 0,
        **filters: Any,
    ) -> list[JobListing]:
        """Search for jobs on LinkedIn."""
        await self.ensure_authenticated()

        def _search() -> list[dict[str, Any]]:
            return self._api.search_jobs(
                keywords=keywords,
                location_name=location,
                limit=limit,
                offset=offset,
            )

        try:
            results = await asyncio.to_thread(_search)
        except Exception as e:
            raise LinkedInAPIError(f"Job search failed: {e}") from e

        return [self._format_job_listing(job) for job in (results or [])]

    async def get_job(self, job_id: str) -> JobDetails:
        """Get detailed job information."""
        await self.ensure_authenticated()

        def _get() -> dict[str, Any]:
            return self._api.get_job(job_id)

        try:
            job_data = await asyncio.to_thread(_get)
        except Exception as e:
            raise LinkedInAPIError(f"Failed to get job {job_id}: {e}") from e

        if not job_data:
            raise NotFoundError("Job", job_id)

        return self._format_job_details(job_id, job_data)

    async def get_profile(self, profile_id: str) -> Profile:
        """Get a LinkedIn profile with skills and contact info."""
        await self.ensure_authenticated()

        def _get_profile() -> dict[str, Any]:
            return self._api.get_profile(profile_id)

        def _get_skills() -> list[dict[str, Any]]:
            try:
                return self._api.get_profile_skills(profile_id)
            except Exception:
                return []

        def _get_contact() -> dict[str, Any]:
            try:
                return self._api.get_profile_contact_info(profile_id)
            except Exception:
                return {}

        try:
            profile_data, skills_data, contact_data = await asyncio.gather(
                asyncio.to_thread(_get_profile),
                asyncio.to_thread(_get_skills),
                asyncio.to_thread(_get_contact),
            )
        except Exception as e:
            raise LinkedInAPIError(f"Failed to get profile {profile_id}: {e}") from e

        if not profile_data:
            raise NotFoundError("Profile", profile_id)

        return self._format_profile(profile_id, profile_data, skills_data, contact_data)

    async def get_company(self, company_id: str) -> CompanyInfo:
        """Get company information."""
        await self.ensure_authenticated()

        def _get() -> dict[str, Any]:
            return self._api.get_company(company_id)

        try:
            company_data = await asyncio.to_thread(_get)
        except Exception as e:
            raise LinkedInAPIError(f"Failed to get company {company_id}: {e}") from e

        if not company_data:
            raise NotFoundError("Company", company_id)

        return self._format_company(company_id, company_data)

    # -- Data formatting (salvaged from api/job_search.py and api/profile.py) --

    def _format_job_listing(self, job: dict[str, Any]) -> JobListing:
        entity_urn = job.get("entityUrn", "")
        job_id = entity_urn.split(":")[-1] if entity_urn else str(job.get("jobPostingId", ""))
        return JobListing(
            job_id=job_id,
            title=job.get("title", "Unknown"),
            company=job.get("companyName", job.get("companyDetails", {}).get("company", "Unknown")),
            location=job.get("formattedLocation", job.get("location", "")),
            url=f"https://www.linkedin.com/jobs/view/{job_id}" if job_id else "",
            date_posted=str(job.get("listedAt", "")),
            applicant_count=job.get("applicantCount"),
        )

    def _format_job_details(self, job_id: str, job: dict[str, Any]) -> JobDetails:
        description = job.get("description", {})
        if isinstance(description, dict):
            description = description.get("text", str(description))

        skills = []
        for skill in job.get("matchedSkills", []):
            if isinstance(skill, dict):
                skills.append(skill.get("skill", {}).get("name", ""))
            elif isinstance(skill, str):
                skills.append(skill)
        skills = [s for s in skills if s]

        return JobDetails(
            job_id=job_id,
            title=job.get("title", "Unknown"),
            company=job.get("companyDetails", {}).get("company", job.get("companyName", "Unknown")),
            location=job.get("formattedLocation", job.get("location", "")),
            description=description if isinstance(description, str) else "",
            url=f"https://www.linkedin.com/jobs/view/{job_id}",
            employment_type=job.get("employmentType", ""),
            seniority_level=job.get("seniorityLevel", ""),
            skills=skills,
            industries=job.get("industries", []),
            job_functions=job.get("jobFunctions", []),
            date_posted=str(job.get("listedAt", "")),
            applicant_count=job.get("applicantCount"),
        )

    def _format_profile(
        self,
        profile_id: str,
        data: dict[str, Any],
        skills_data: list[dict[str, Any]],
        contact_data: dict[str, Any],
    ) -> Profile:
        experience = []
        for exp in data.get("experience", []):
            time_period = exp.get("timePeriod", {})
            start = self._format_date(time_period.get("startDate", {}))
            end = self._format_date(time_period.get("endDate", {})) if time_period.get("endDate") else "Present"
            experience.append(
                Experience(
                    title=exp.get("title", ""),
                    company=exp.get("companyName", ""),
                    location=exp.get("locationName", ""),
                    start_date=start,
                    end_date=end,
                    description=exp.get("description", ""),
                )
            )

        education = []
        for edu in data.get("education", []):
            time_period = edu.get("timePeriod", {})
            start = self._format_date(time_period.get("startDate", {}))
            end = self._format_date(time_period.get("endDate", {}))
            education.append(
                Education(
                    school=edu.get("schoolName", ""),
                    degree=edu.get("degreeName", ""),
                    field_of_study=edu.get("fieldOfStudy", ""),
                    start_date=start,
                    end_date=end,
                )
            )

        skills = [s.get("name", "") for s in skills_data if s.get("name")]

        return Profile(
            profile_id=profile_id,
            name=f"{data.get('firstName', '')} {data.get('lastName', '')}".strip(),
            headline=data.get("headline", ""),
            summary=data.get("summary", ""),
            location=data.get("locationName", ""),
            industry=data.get("industryName", ""),
            email=contact_data.get("email_address", ""),
            phone=", ".join(contact_data.get("phone_numbers", [])) if contact_data.get("phone_numbers") else "",
            profile_url=f"https://www.linkedin.com/in/{profile_id}",
            experience=experience,
            education=education,
            skills=skills,
            languages=[
                {"name": lang.get("name", ""), "proficiency": lang.get("proficiency", "")}
                for lang in data.get("languages", [])
            ],
            certifications=[
                {"name": cert.get("name", ""), "authority": cert.get("authority", "")}
                for cert in data.get("certifications", [])
            ],
        )

    def _format_company(self, company_id: str, data: dict[str, Any]) -> CompanyInfo:
        hq = data.get("headquarter", {})
        headquarters = ""
        if hq:
            parts = [hq.get("city", ""), hq.get("geographicArea", ""), hq.get("country", "")]
            headquarters = ", ".join(p for p in parts if p)

        return CompanyInfo(
            company_id=company_id,
            name=data.get("name", ""),
            tagline=data.get("tagline", ""),
            description=data.get("description", ""),
            website=data.get("companyPageUrl", data.get("website", "")),
            industry=data.get("industryName", "") or (
                data["companyIndustries"][0].get("localizedName", "")
                if data.get("companyIndustries")
                else ""
            ),
            company_size=f"{data.get('staffCount', 'Unknown')} employees",
            headquarters=headquarters,
            specialties=data.get("specialities", data.get("specialties", [])),
            url=f"https://www.linkedin.com/company/{company_id}",
        )

    @staticmethod
    def _format_date(date_obj: dict[str, Any] | None) -> str:
        if not date_obj:
            return ""
        month = date_obj.get("month", 0)
        year = date_obj.get("year", 0)
        if month and year:
            months = [
                "", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
            ]
            return f"{months[min(month, 12)]} {year}"
        elif year:
            return str(year)
        return ""
