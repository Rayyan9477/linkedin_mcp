"""
LinkedIn job search module
Supports searching jobs, fetching job details, and saving jobs
"""

import json
import logging
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from bs4 import BeautifulSoup
import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from linkedin_mcp.api.auth import LinkedInAuth
from linkedin_mcp.core.protocol import JobDetails, JobSearchFilter
from linkedin_mcp.utils.config import get_config

logger = logging.getLogger("linkedin-mcp")

class LinkedInJobSearch:
    """
    Handles LinkedIn job search operations
    """
    
    def __init__(self):
        """Initialize the job search module"""
        self.config = get_config()
        self.auth = LinkedInAuth()
        self.data_dir = Path(self.config.get("data_dir", "data"))
        self.data_dir.mkdir(exist_ok=True)
        self.jobs_dir = self.data_dir / "jobs"
        self.jobs_dir.mkdir(exist_ok=True)
    
    def search_jobs(self, search_filter: Dict[str, Any], page: int = 1, count: int = 20) -> Dict[str, Any]:
        """
        Search for jobs on LinkedIn using the provided filters
        
        Args:
            search_filter: Dictionary containing search parameters
            page: Page number for pagination
            count: Number of results per page
            
        Returns:
            Dict containing search results with job listings
        """
        logger.info(f"Searching jobs with filter: {search_filter}, page: {page}, count: {count}")
        
        # Validate session
        if not self._check_session():
            raise Exception("Not logged in")
        
        # Convert dict to JobSearchFilter object for validation
        filter_obj = JobSearchFilter(**search_filter)
        
        # Try API-based search first
        api_client = self.auth.get_api_client()
        if api_client:
            try:
                return self._api_search_jobs(filter_obj, page, count)
            except Exception as e:
                logger.warning(f"API job search failed: {str(e)}, falling back to browser")
        
        # Fall back to browser-based search
        return self._browser_search_jobs(filter_obj, page, count)
    
    def _api_search_jobs(self, search_filter: JobSearchFilter, page: int, count: int) -> Dict[str, Any]:
        """
        Search jobs using the LinkedIn API
        
        Args:
            search_filter: JobSearchFilter containing search parameters
            page: Page number for pagination
            count: Number of results per page
            
        Returns:
            Dict containing search results with job listings
        """
        api_client = self.auth.get_api_client()
        if not api_client:
            raise Exception("API client not available")
            
        # Prepare search parameters
        params = {}
        if search_filter.keywords:
            params["keywords"] = search_filter.keywords
        if search_filter.location:
            params["location"] = search_filter.location
        if search_filter.distance is not None:
            params["distance"] = search_filter.distance
            
        # Convert page/count to LinkedIn's expectations
        start = (page - 1) * count
        
        # Make the API call with retries
        max_retries = self.config.get("max_retry_attempts", 3)
        retry_delay = self.config.get("retry_delay", 2)
        
        for attempt in range(max_retries):
            try:
                # Using the unofficial API to search jobs
                jobs_data = api_client.search_jobs(
                    keywords=params.get("keywords", ""),
                    location=params.get("location", ""),
                    limit=count,
                    offset=start
                )
                
                # Process and format results
                results = []
                for job in jobs_data:
                    job_details = self._format_job_result(job)
                    results.append(job_details)
                    
                    # Cache job details for later retrieval
                    self._cache_job_details(job_details)
                
                return {
                    "total": len(jobs_data),  # This is just the current page count
                    "page": page,
                    "count": count,
                    "results": results
                }
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Job search failed (attempt {attempt+1}/{max_retries}): {str(e)}")
                    time.sleep(retry_delay)
                else:
                    raise Exception(f"Job search failed after {max_retries} attempts: {str(e)}")
    
    def _browser_search_jobs(self, search_filter: JobSearchFilter, page: int, count: int) -> Dict[str, Any]:
        """
        Search jobs using browser automation
        
        Args:
            search_filter: JobSearchFilter containing search parameters
            page: Page number for pagination
            count: Number of results per page
            
        Returns:
            Dict containing search results with job listings
        """
        driver = self.auth.get_driver()
        if not driver:
            raise Exception("Browser driver not available, please login first")
        
        try:
            # Construct search URL
            base_url = "https://www.linkedin.com/jobs/search/?"
            params = []
            
            if search_filter.keywords:
                params.append(f"keywords={search_filter.keywords}")
            if search_filter.location:
                params.append(f"location={search_filter.location}")
            if search_filter.distance is not None:
                params.append(f"distance={search_filter.distance}")
            if search_filter.job_type:
                job_types = ",".join(search_filter.job_type)
                params.append(f"f_JT={job_types}")
            if search_filter.experience_level:
                exp_levels = ",".join(search_filter.experience_level)
                params.append(f"f_E={exp_levels}")
            
            # Add pagination parameters
            start = (page - 1) * count
            params.append(f"start={start}")
            params.append(f"count={count}")
            
            # Construct full URL
            search_url = base_url + "&".join(params)
            
            # Navigate to search URL
            driver.get(search_url)
            
            # Wait for job results to load
            timeout = self.config.get("browser_timeout", 30)
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".jobs-search__results-list"))
            )
            
            # Extract job listings
            job_elements = driver.find_elements(By.CSS_SELECTOR, ".jobs-search__results-list li")
            
            results = []
            for job_element in job_elements:
                try:
                    # Extract job information from listing
                    job_id_elem = job_element.find_element(By.CSS_SELECTOR, ".job-card-container")
                    job_id = job_id_elem.get_attribute("data-job-id")
                    
                    title_elem = job_element.find_element(By.CSS_SELECTOR, ".job-card-list__title")
                    title = title_elem.text.strip()
                    
                    company_elem = job_element.find_element(By.CSS_SELECTOR, ".job-card-container__company-name")
                    company = company_elem.text.strip()
                    
                    location_elem = job_element.find_element(By.CSS_SELECTOR, ".job-card-container__metadata-item")
                    location = location_elem.text.strip()
                    
                    # Extract job URL
                    url = title_elem.get_attribute("href")
                    
                    job_details = JobDetails(
                        job_id=job_id,
                        title=title,
                        company=company,
                        location=location,
                        url=url
                    )
                    
                    results.append(job_details.dict())
                    
                    # Cache basic job info
                    self._cache_job_details(job_details.dict())
                except Exception as e:
                    logger.warning(f"Error extracting job listing: {str(e)}")
            
            # Try to get total count from results header
            try:
                results_count_elem = driver.find_element(By.CSS_SELECTOR, ".jobs-search-results-list__title-heading span")
                count_text = results_count_elem.text.strip()
                total_count_match = re.search(r'(\d+(?:,\d+)*)', count_text)
                total_count = int(total_count_match.group(1).replace(',', '')) if total_count_match else len(results)
            except:
                total_count = len(results)
            
            return {
                "total": total_count,
                "page": page,
                "count": count,
                "results": results
            }
        except Exception as e:
            raise Exception(f"Browser job search failed: {str(e)}")
    
    def get_job_details(self, job_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific job posting
        
        Args:
            job_id: LinkedIn job ID
            
        Returns:
            Dict containing detailed job information
        """
        logger.info(f"Getting job details for job ID: {job_id}")
        
        # Validate session
        if not self._check_session():
            raise Exception("Not logged in")
        
        # Check if we have cached job details
        cached_job = self._get_cached_job(job_id)
        if cached_job and "description" in cached_job and cached_job["description"]:
            logger.info(f"Returning cached job details for job ID: {job_id}")
            return cached_job
        
        # Try API-based retrieval first
        api_client = self.auth.get_api_client()
        if api_client:
            try:
                return self._api_get_job_details(job_id)
            except Exception as e:
                logger.warning(f"API job details failed: {str(e)}, falling back to browser")
        
        # Fall back to browser-based retrieval
        return self._browser_get_job_details(job_id)
    
    def _api_get_job_details(self, job_id: str) -> Dict[str, Any]:
        """
        Get job details using the LinkedIn API
        
        Args:
            job_id: LinkedIn job ID
            
        Returns:
            Dict containing detailed job information
        """
        api_client = self.auth.get_api_client()
        if not api_client:
            raise Exception("API client not available")
        
        # Make API call with retries
        max_retries = self.config.get("max_retry_attempts", 3)
        retry_delay = self.config.get("retry_delay", 2)
        
        for attempt in range(max_retries):
            try:
                # Using the unofficial API to get job details
                job_data = api_client.get_job(job_id)
                
                # Format job details
                job_details = self._format_job_details(job_data)
                
                # Cache the job details for later retrieval
                self._cache_job_details(job_details)
                
                return job_details
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Job details failed (attempt {attempt+1}/{max_retries}): {str(e)}")
                    time.sleep(retry_delay)
                else:
                    raise Exception(f"Job details failed after {max_retries} attempts: {str(e)}")
    
    def _browser_get_job_details(self, job_id: str) -> Dict[str, Any]:
        """
        Get job details using browser automation
        
        Args:
            job_id: LinkedIn job ID
            
        Returns:
            Dict containing detailed job information
        """
        driver = self.auth.get_driver()
        if not driver:
            raise Exception("Browser driver not available, please login first")
        
        try:
            # Navigate to job page
            job_url = f"https://www.linkedin.com/jobs/view/{job_id}/"
            driver.get(job_url)
            
            # Wait for job details to load
            timeout = self.config.get("browser_timeout", 30)
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.CLASS_NAME, "job-view-layout"))
            )
            
            # Extract basic job information
            title = driver.find_element(By.CLASS_NAME, "job-details-jobs-unified-top-card__job-title").text.strip()
            company = driver.find_element(By.CLASS_NAME, "job-details-jobs-unified-top-card__company-name").text.strip()
            location = driver.find_element(By.CLASS_NAME, "job-details-jobs-unified-top-card__bullet").text.strip()
            
            # Extract job description
            description = driver.find_element(By.CLASS_NAME, "jobs-description__content").text.strip()
            
            # Try to extract additional details
            try:
                job_details_section = driver.find_element(By.CLASS_NAME, "job-details-jobs-unified-top-card__job-insight")
                details_text = job_details_section.text
                
                # Parse employment type
                employment_type = None
                if "Full-time" in details_text:
                    employment_type = "Full-time"
                elif "Part-time" in details_text:
                    employment_type = "Part-time"
                elif "Contract" in details_text:
                    employment_type = "Contract"
                elif "Temporary" in details_text:
                    employment_type = "Temporary"
                
                # Try to extract seniority level
                seniority_level = None
                seniority_matches = re.search(r'(Entry|Associate|Mid-Senior|Director|Executive) level', details_text)
                if seniority_matches:
                    seniority_level = seniority_matches.group(0)
            except:
                employment_type = None
                seniority_level = None
            
            # Create job details object
            job_details = JobDetails(
                job_id=job_id,
                title=title,
                company=company,
                location=location,
                description=description,
                url=job_url,
                employment_type=employment_type,
                seniority_level=seniority_level
            )
            
            # Extract skills (if available)
            try:
                skills_section = driver.find_element(By.CLASS_NAME, "job-details-skill-match-status-list")
                skill_elements = skills_section.find_elements(By.TAG_NAME, "li")
                skills = [skill.text.strip() for skill in skill_elements]
                job_details.skills = skills
            except:
                pass
            
            result = job_details.dict()
            
            # Cache the job details
            self._cache_job_details(result)
            
            return result
        except Exception as e:
            raise Exception(f"Browser job details failed: {str(e)}")
    
    def get_recommended_jobs(self, count: int = 10) -> Dict[str, Any]:
        """
        Get recommended jobs based on user profile
        
        Args:
            count: Number of recommended jobs to retrieve
            
        Returns:
            Dict containing recommended job listings
        """
        logger.info(f"Getting {count} recommended jobs")
        
        # Validate session
        if not self._check_session():
            raise Exception("Not logged in")
        
        # Try API-based retrieval first
        api_client = self.auth.get_api_client()
        if api_client:
            try:
                # Use similar method as search but without filters
                return self._api_search_jobs(JobSearchFilter(), 1, count)
            except Exception as e:
                logger.warning(f"API recommended jobs failed: {str(e)}, falling back to browser")
        
        # Fall back to browser-based retrieval
        driver = self.auth.get_driver()
        if not driver:
            raise Exception("Browser driver not available, please login first")
        
        try:
            # Navigate to recommended jobs page
            driver.get("https://www.linkedin.com/jobs/")
            
            # Wait for job recommendations to load
            timeout = self.config.get("browser_timeout", 30)
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".job-card-container"))
            )
            
            # Extract job listings (using the same logic as browser search)
            job_elements = driver.find_elements(By.CSS_SELECTOR, ".job-card-container")[:count]
            
            results = []
            for job_element in job_elements:
                try:
                    job_id = job_element.get_attribute("data-job-id")
                    title_elem = job_element.find_element(By.CSS_SELECTOR, ".job-card-list__title")
                    title = title_elem.text.strip()
                    company_elem = job_element.find_element(By.CSS_SELECTOR, ".job-card-container__company-name")
                    company = company_elem.text.strip()
                    location_elem = job_element.find_element(By.CSS_SELECTOR, ".job-card-container__metadata-item")
                    location = location_elem.text.strip()
                    url = title_elem.get_attribute("href")
                    
                    job_details = JobDetails(
                        job_id=job_id,
                        title=title,
                        company=company,
                        location=location,
                        url=url
                    )
                    
                    results.append(job_details.dict())
                    self._cache_job_details(job_details.dict())
                except Exception as e:
                    logger.warning(f"Error extracting recommended job: {str(e)}")
            
            return {
                "total": len(results),
                "results": results
            }
        except Exception as e:
            raise Exception(f"Browser recommended jobs failed: {str(e)}")
    
    def get_saved_jobs(self, count: int = 10) -> Dict[str, Any]:
        """
        Get jobs saved by the user
        
        Args:
            count: Number of saved jobs to retrieve
            
        Returns:
            Dict containing saved job listings
        """
        logger.info(f"Getting {count} saved jobs")
        
        # Validate session
        if not self._check_session():
            raise Exception("Not logged in")
        
        # Browser-based retrieval (API doesn't support this well)
        driver = self.auth.get_driver()
        if not driver:
            raise Exception("Browser driver not available, please login first")
        
        try:
            # Navigate to saved jobs page
            driver.get("https://www.linkedin.com/my-items/saved-jobs/")
            
            # Wait for saved jobs to load
            timeout = self.config.get("browser_timeout", 30)
            try:
                WebDriverWait(driver, timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".entity-result__item"))
                )
            except TimeoutException:
                # No saved jobs
                return {"total": 0, "results": []}
            
            # Extract job listings
            job_elements = driver.find_elements(By.CSS_SELECTOR, ".entity-result__item")[:count]
            
            results = []
            for job_element in job_elements:
                try:
                    # Extract job information
                    title_elem = job_element.find_element(By.CSS_SELECTOR, ".entity-result__title-text a")
                    title = title_elem.text.strip()
                    url = title_elem.get_attribute("href")
                    job_id = re.search(r'/jobs/view/(\d+)/', url).group(1)
                    
                    company_elem = job_element.find_element(By.CSS_SELECTOR, ".entity-result__primary-subtitle")
                    company = company_elem.text.strip()
                    
                    location_elem = job_element.find_element(By.CSS_SELECTOR, ".entity-result__secondary-subtitle")
                    location = location_elem.text.strip()
                    
                    job_details = JobDetails(
                        job_id=job_id,
                        title=title,
                        company=company,
                        location=location,
                        url=url
                    )
                    
                    results.append(job_details.dict())
                    self._cache_job_details(job_details.dict())
                except Exception as e:
                    logger.warning(f"Error extracting saved job: {str(e)}")
            
            return {
                "total": len(results),
                "results": results
            }
        except Exception as e:
            raise Exception(f"Browser saved jobs failed: {str(e)}")
    
    def save_job(self, job_id: str) -> Dict[str, Any]:
        """
        Save a job to the user's saved jobs list
        
        Args:
            job_id: LinkedIn job ID
            
        Returns:
            Dict indicating success status
        """
        logger.info(f"Saving job with ID: {job_id}")
        
        # Validate session
        if not self._check_session():
            raise Exception("Not logged in")
        
        # Browser-based operation (API doesn't support this)
        driver = self.auth.get_driver()
        if not driver:
            raise Exception("Browser driver not available, please login first")
        
        try:
            # Navigate to job page
            job_url = f"https://www.linkedin.com/jobs/view/{job_id}/"
            driver.get(job_url)
            
            # Wait for job details to load
            timeout = self.config.get("browser_timeout", 30)
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.CLASS_NAME, "job-details-jobs-unified-top-card__job-title"))
            )
            
            # Find and click the save button
            try:
                save_button = driver.find_element(By.CSS_SELECTOR, "button[aria-label='Save']")
                save_button.click()
                
                # Wait for confirmation
                time.sleep(1)
                
                return {"success": True, "message": "Job saved successfully"}
            except NoSuchElementException:
                # Check if job is already saved
                try:
                    saved_button = driver.find_element(By.CSS_SELECTOR, "button[aria-label='Unsave']")
                    return {"success": True, "message": "Job was already saved"}
                except:
                    raise Exception("Save button not found")
        except Exception as e:
            raise Exception(f"Failed to save job: {str(e)}")
    
    def _format_job_result(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format job search result from API response
        
        Args:
            job_data: Raw job data from API
            
        Returns:
            Formatted job details
        """
        job_id = job_data.get("entityUrn", "").split(":")[-1]
        
        return {
            "job_id": job_id,
            "title": job_data.get("title", ""),
            "company": job_data.get("companyName", ""),
            "location": job_data.get("formattedLocation", ""),
            "url": f"https://www.linkedin.com/jobs/view/{job_id}/",
            "date_posted": job_data.get("listedAt", ""),
            "applicant_count": job_data.get("applicantCount", None)
        }
    
    def _format_job_details(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format detailed job information from API response
        
        Args:
            job_data: Raw job data from API
            
        Returns:
            Formatted job details
        """
        job_id = job_data.get("entityUrn", "").split(":")[-1]
        
        # Extract more detailed information
        description = job_data.get("description", {}).get("text", "")
        
        # Try to extract employment type and seniority level
        employment_type = None
        seniority_level = None
        
        job_info = job_data.get("jobInfo", {})
        if job_info:
            employment_type_info = job_info.get("jobType", {})
            if employment_type_info:
                employment_type = employment_type_info.get("text", None)
            
            seniority_info = job_info.get("seniority", {})
            if seniority_info:
                seniority_level = seniority_info.get("text", None)
        
        # Create job details dictionary
        job_details = {
            "job_id": job_id,
            "title": job_data.get("title", ""),
            "company": job_data.get("companyName", ""),
            "location": job_data.get("formattedLocation", ""),
            "description": description,
            "url": f"https://www.linkedin.com/jobs/view/{job_id}/",
            "date_posted": job_data.get("listedAt", ""),
            "employment_type": employment_type,
            "seniority_level": seniority_level,
            "applicant_count": job_data.get("applicantCount", None)
        }
        
        # Try to extract skills if available
        skills = []
        matched_skills = job_data.get("matchedSkills", [])
        for skill in matched_skills:
            skill_name = skill.get("skill", {}).get("name", "")
            if skill_name:
                skills.append(skill_name)
        
        if skills:
            job_details["skills"] = skills
        
        return job_details
    
    def _cache_job_details(self, job_details: Dict[str, Any]) -> None:
        """
        Cache job details to disk for later retrieval
        
        Args:
            job_details: Job details to cache
        """
        job_id = job_details.get("job_id")
        if not job_id:
            return
        
        job_file = self.jobs_dir / f"{job_id}.json"
        
        # If file exists, update with new information rather than overwrite
        existing_data = {}
        if job_file.exists():
            try:
                with open(job_file, "r") as f:
                    existing_data = json.load(f)
                    
                # Only update with new fields to avoid overwriting detailed info
                # with less detailed search results
                for key, value in job_details.items():
                    if value is not None and (key not in existing_data or existing_data[key] is None):
                        existing_data[key] = value
                        
                job_details = existing_data
            except Exception:
                pass
        
        # Add timestamp
        job_details["_cached_at"] = datetime.now().isoformat()
        
        try:
            with open(job_file, "w") as f:
                json.dump(job_details, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to cache job details: {str(e)}")
    
    def _get_cached_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached job details from disk
        
        Args:
            job_id: LinkedIn job ID
            
        Returns:
            Cached job details or None if not found
        """
        job_file = self.jobs_dir / f"{job_id}.json"
        if not job_file.exists():
            return None
        
        try:
            with open(job_file, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to read cached job details: {str(e)}")
            return None
    
    def _check_session(self) -> bool:
        """
        Check if user is logged in
        
        Returns:
            Boolean indicating if session is valid
        """
        session_state = self.auth.check_session()
        return session_state.get("logged_in", False)