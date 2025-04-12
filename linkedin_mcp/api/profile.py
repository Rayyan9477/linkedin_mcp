"""
LinkedIn profile module for retrieving user profile information
"""

import json
import logging
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Tuple

from bs4 import BeautifulSoup
import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from linkedin_mcp.api.auth import LinkedInAuth
from linkedin_mcp.core.protocol import Profile
from linkedin_mcp.utils.config import get_config

logger = logging.getLogger("linkedin-mcp")

class LinkedInProfile:
    """
    Handles LinkedIn profile operations
    Supports retrieving profiles, companies, skills, and feed
    """
    
    def __init__(self):
        """Initialize the profile module"""
        self.config = get_config()
        self.auth = LinkedInAuth()
        self.data_dir = Path(self.config.get("data_dir", "data"))
        self.data_dir.mkdir(exist_ok=True)
        self.profiles_dir = self.data_dir / "profiles"
        self.profiles_dir.mkdir(exist_ok=True)
        self.companies_dir = self.data_dir / "companies"
        self.companies_dir.mkdir(exist_ok=True)
    
    def get_profile(self, profile_id: str) -> Dict[str, Any]:
        """
        Get profile information for a LinkedIn user
        
        Args:
            profile_id: LinkedIn profile ID or username
            
        Returns:
            Dict containing profile information
        """
        logger.info(f"Getting profile information for {profile_id}")
        
        # Validate session
        if not self._check_session():
            raise Exception("Not logged in")
        
        # Check if we have cached profile data
        cached_profile = self._get_cached_profile(profile_id)
        if cached_profile:
            # Check if cache is still valid (less than 7 days old)
            cached_at = cached_profile.get("_cached_at")
            if cached_at:
                try:
                    cached_time = datetime.fromisoformat(cached_at)
                    if (datetime.now() - cached_time).days < 7:
                        logger.info(f"Returning cached profile for {profile_id}")
                        return cached_profile
                except ValueError:
                    pass
        
        # Try API-based retrieval first
        api_client = self.auth.get_api_client()
        if api_client:
            try:
                return self._api_get_profile(profile_id)
            except Exception as e:
                logger.warning(f"API profile retrieval failed: {str(e)}, falling back to browser")
        
        # Fall back to browser-based retrieval
        return self._browser_get_profile(profile_id)
    
    def _api_get_profile(self, profile_id: str) -> Dict[str, Any]:
        """
        Get profile using LinkedIn API
        
        Args:
            profile_id: LinkedIn profile ID or username
            
        Returns:
            Dict containing profile information
        """
        api_client = self.auth.get_api_client()
        if not api_client:
            raise Exception("API client not available")
        
        # Make API call with retries
        max_retries = self.config.get("max_retry_attempts", 3)
        retry_delay = self.config.get("retry_delay", 2)
        
        for attempt in range(max_retries):
            try:
                # Using the unofficial API to get profile data
                profile_data = api_client.get_profile(profile_id)
                
                # Extract standard profile fields
                profile_info = {
                    "profile_id": profile_id,
                    "name": profile_data.get("firstName", "") + " " + profile_data.get("lastName", ""),
                    "headline": profile_data.get("headline", ""),
                    "summary": profile_data.get("summary", ""),
                    "location": profile_data.get("locationName", ""),
                    "industry": profile_data.get("industryName", ""),
                    "profile_url": f"https://www.linkedin.com/in/{profile_id}/"
                }
                
                # Get additional profile details
                try:
                    contact_info = api_client.get_profile_contact_info(profile_id)
                    profile_info["email"] = contact_info.get("email_address", "")
                    profile_info["phone"] = contact_info.get("phone_numbers", [{}])[0].get("number", "") if contact_info.get("phone_numbers") else ""
                except:
                    # Contact info might be restricted
                    pass
                
                # Get experience
                experience = []
                for exp in profile_data.get("experience", []):
                    exp_item = {
                        "title": exp.get("title", ""),
                        "company": exp.get("companyName", ""),
                        "location": exp.get("locationName", ""),
                        "description": exp.get("description", ""),
                        "start_date": self._format_date(exp.get("timePeriod", {}).get("startDate", {})),
                        "end_date": self._format_date(exp.get("timePeriod", {}).get("endDate", {})) or "Present"
                    }
                    experience.append(exp_item)
                
                profile_info["experience"] = experience
                
                # Get education
                education = []
                for edu in profile_data.get("education", []):
                    edu_item = {
                        "school": edu.get("schoolName", ""),
                        "degree": edu.get("degreeName", ""),
                        "field_of_study": edu.get("fieldOfStudy", ""),
                        "description": edu.get("description", ""),
                        "start_date": self._format_year(edu.get("timePeriod", {}).get("startDate", {}).get("year")),
                        "end_date": self._format_year(edu.get("timePeriod", {}).get("endDate", {}).get("year")) or "Present"
                    }
                    education.append(edu_item)
                
                profile_info["education"] = education
                
                # Get skills
                skills = []
                try:
                    skills_data = api_client.get_profile_skills(profile_id)
                    for skill in skills_data:
                        skills.append(skill.get("name", ""))
                except:
                    # Skills might be restricted
                    pass
                
                profile_info["skills"] = skills
                
                # Cache the profile data
                self._cache_profile(profile_id, profile_info)
                
                return profile_info
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Profile retrieval failed (attempt {attempt+1}/{max_retries}): {str(e)}")
                    time.sleep(retry_delay)
                else:
                    raise Exception(f"Profile retrieval failed after {max_retries} attempts: {str(e)}")
    
    def _browser_get_profile(self, profile_id: str) -> Dict[str, Any]:
        """
        Get profile using browser automation
        
        Args:
            profile_id: LinkedIn profile ID or username
            
        Returns:
            Dict containing profile information
        """
        driver = self.auth.get_driver()
        if not driver:
            raise Exception("Browser driver not available, please login first")
        
        try:
            # Navigate to profile page
            profile_url = f"https://www.linkedin.com/in/{profile_id}/"
            driver.get(profile_url)
            
            # Wait for profile to load
            timeout = self.config.get("browser_timeout", 30)
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.CLASS_NAME, "pv-top-card"))
            )
            
            # Extract profile information
            profile_info = {
                "profile_id": profile_id,
                "profile_url": profile_url
            }
            
            # Basic info
            try:
                name_elem = driver.find_element(By.CLASS_NAME, "text-heading-xlarge")
                profile_info["name"] = name_elem.text.strip()
            except:
                profile_info["name"] = ""
            
            try:
                headline_elem = driver.find_element(By.CLASS_NAME, "text-body-medium")
                profile_info["headline"] = headline_elem.text.strip()
            except:
                profile_info["headline"] = ""
            
            try:
                location_elem = driver.find_element(By.CSS_SELECTOR, ".text-body-small.inline.t-black--light.break-words")
                profile_info["location"] = location_elem.text.strip()
            except:
                profile_info["location"] = ""
            
            # About/Summary
            try:
                # Click to expand the about section if needed
                try:
                    about_see_more = driver.find_element(By.CSS_SELECTOR, "#about + div + div button")
                    driver.execute_script("arguments[0].click();", about_see_more)
                    time.sleep(1)
                except:
                    pass
                
                about_elem = driver.find_element(By.CSS_SELECTOR, "#about + div + div .inline-show-more-text")
                profile_info["summary"] = about_elem.text.strip()
            except:
                profile_info["summary"] = ""
            
            # Experience
            experience = []
            try:
                # Scroll to experience section
                experience_section = driver.find_element(By.ID, "experience")
                driver.execute_script("arguments[0].scrollIntoView();", experience_section)
                time.sleep(1)
                
                # Find all experience entries
                exp_items = driver.find_elements(By.CSS_SELECTOR, "#experience + div + div .pvs-list__item--line-separated")
                
                for item in exp_items:
                    try:
                        # Extract experience details
                        title_elem = item.find_element(By.CSS_SELECTOR, ".t-bold .visually-hidden")
                        title = title_elem.text.strip()
                        
                        company_elem = item.find_element(By.CSS_SELECTOR, ".t-normal .visually-hidden")
                        company = company_elem.text.strip()
                        
                        date_elem = item.find_element(By.CSS_SELECTOR, ".t-black--light .visually-hidden")
                        date_range = date_elem.text.strip()
                        
                        # Parse date range
                        start_date, end_date = self._parse_date_range(date_range)
                        
                        # Try to get description
                        description = ""
                        try:
                            # Check if we need to expand the description
                            see_more_btn = item.find_element(By.CSS_SELECTOR, ".inline-show-more-text__button")
                            driver.execute_script("arguments[0].click();", see_more_btn)
                            time.sleep(0.5)
                            
                            desc_elem = item.find_element(By.CSS_SELECTOR, ".inline-show-more-text")
                            description = desc_elem.text.strip()
                        except:
                            # No description or can't expand
                            pass
                        
                        experience.append({
                            "title": title,
                            "company": company,
                            "location": "",  # Hard to extract reliably
                            "start_date": start_date,
                            "end_date": end_date,
                            "description": description
                        })
                    except Exception as e:
                        logger.warning(f"Error extracting experience item: {str(e)}")
            except Exception as e:
                logger.warning(f"Error extracting experience section: {str(e)}")
            
            profile_info["experience"] = experience
            
            # Education
            education = []
            try:
                # Scroll to education section
                education_section = driver.find_element(By.ID, "education")
                driver.execute_script("arguments[0].scrollIntoView();", education_section)
                time.sleep(1)
                
                # Find all education entries
                edu_items = driver.find_elements(By.CSS_SELECTOR, "#education + div + div .pvs-list__item--line-separated")
                
                for item in edu_items:
                    try:
                        # Extract education details
                        school_elem = item.find_element(By.CSS_SELECTOR, ".t-bold .visually-hidden")
                        school = school_elem.text.strip()
                        
                        # Try to get degree and field
                        degree = ""
                        field = ""
                        try:
                            degree_elem = item.find_element(By.CSS_SELECTOR, ".t-normal .visually-hidden")
                            degree_text = degree_elem.text.strip()
                            
                            # Parse degree and field
                            if "," in degree_text:
                                degree, field = degree_text.split(",", 1)
                                degree = degree.strip()
                                field = field.strip()
                            else:
                                degree = degree_text
                        except:
                            pass
                        
                        # Try to get date range
                        start_date = ""
                        end_date = ""
                        try:
                            date_elem = item.find_element(By.CSS_SELECTOR, ".t-black--light .visually-hidden")
                            date_range = date_elem.text.strip()
                            start_date, end_date = self._parse_date_range(date_range)
                        except:
                            pass
                        
                        education.append({
                            "school": school,
                            "degree": degree,
                            "field_of_study": field,
                            "start_date": start_date,
                            "end_date": end_date,
                            "description": ""
                        })
                    except Exception as e:
                        logger.warning(f"Error extracting education item: {str(e)}")
            except Exception as e:
                logger.warning(f"Error extracting education section: {str(e)}")
            
            profile_info["education"] = education
            
            # Skills
            skills = []
            try:
                # Scroll to skills section
                skills_section = driver.find_element(By.ID, "skills")
                driver.execute_script("arguments[0].scrollIntoView();", skills_section)
                time.sleep(1)
                
                # Try to click "Show all skills" if available
                try:
                    show_all = driver.find_element(By.CSS_SELECTOR, "#skills + div + div .artdeco-card__actions button")
                    driver.execute_script("arguments[0].click();", show_all)
                    time.sleep(1)
                    
                    # In the modal, extract skills
                    skill_elems = driver.find_elements(By.CSS_SELECTOR, ".artdeco-modal__content .display-flex .display-flex .mr1 .visually-hidden")
                    for elem in skill_elems:
                        skills.append(elem.text.strip())
                    
                    # Close modal
                    close_btn = driver.find_element(By.CSS_SELECTOR, ".artdeco-modal__dismiss")
                    driver.execute_script("arguments[0].click();", close_btn)
                except:
                    # If "Show all" isn't available, try to extract from the main page
                    skill_elems = driver.find_elements(By.CSS_SELECTOR, "#skills + div + div .pvs-entity__pill-text")
                    for elem in skill_elems:
                        skills.append(elem.text.strip())
            except Exception as e:
                logger.warning(f"Error extracting skills section: {str(e)}")
            
            profile_info["skills"] = skills
            
            # Cache the profile data
            self._cache_profile(profile_id, profile_info)
            
            return profile_info
        except Exception as e:
            raise Exception(f"Browser profile retrieval failed: {str(e)}")
    
    def get_company(self, company_id: str) -> Dict[str, Any]:
        """
        Get company profile information
        
        Args:
            company_id: LinkedIn company ID
            
        Returns:
            Dict containing company information
        """
        logger.info(f"Getting company information for {company_id}")
        
        # Validate session
        if not self._check_session():
            raise Exception("Not logged in")
        
        # Check if we have cached company data
        cached_company = self._get_cached_company(company_id)
        if cached_company:
            # Check if cache is still valid (less than 7 days old)
            cached_at = cached_company.get("_cached_at")
            if cached_at:
                try:
                    cached_time = datetime.fromisoformat(cached_at)
                    if (datetime.now() - cached_time).days < 7:
                        logger.info(f"Returning cached company for {company_id}")
                        return cached_company
                except ValueError:
                    pass
        
        # Try API-based retrieval first
        api_client = self.auth.get_api_client()
        if api_client:
            try:
                return self._api_get_company(company_id)
            except Exception as e:
                logger.warning(f"API company retrieval failed: {str(e)}, falling back to browser")
        
        # Fall back to browser-based retrieval
        return self._browser_get_company(company_id)
    
    def _api_get_company(self, company_id: str) -> Dict[str, Any]:
        """
        Get company information using LinkedIn API
        
        Args:
            company_id: LinkedIn company ID
            
        Returns:
            Dict containing company information
        """
        api_client = self.auth.get_api_client()
        if not api_client:
            raise Exception("API client not available")
        
        # Make API call with retries
        max_retries = self.config.get("max_retry_attempts", 3)
        retry_delay = self.config.get("retry_delay", 2)
        
        for attempt in range(max_retries):
            try:
                # Using the unofficial API to get company data
                company_data = api_client.get_company(company_id)
                
                # Format company information
                company_info = {
                    "company_id": company_id,
                    "name": company_data.get("name", ""),
                    "tagline": company_data.get("tagline", ""),
                    "description": company_data.get("description", ""),
                    "website": company_data.get("website", ""),
                    "industry": company_data.get("industryName", ""),
                    "company_size": company_data.get("staffCount", ""),
                    "headquarters": company_data.get("headquarter", {}).get("country", ""),
                    "founded": company_data.get("foundedOn", {}).get("year", ""),
                    "specialties": company_data.get("specialities", []),
                    "url": f"https://www.linkedin.com/company/{company_id}/"
                }
                
                # Cache the company data
                self._cache_company(company_id, company_info)
                
                return company_info
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Company retrieval failed (attempt {attempt+1}/{max_retries}): {str(e)}")
                    time.sleep(retry_delay)
                else:
                    raise Exception(f"Company retrieval failed after {max_retries} attempts: {str(e)}")
    
    def _browser_get_company(self, company_id: str) -> Dict[str, Any]:
        """
        Get company information using browser automation
        
        Args:
            company_id: LinkedIn company ID
            
        Returns:
            Dict containing company information
        """
        driver = self.auth.get_driver()
        if not driver:
            raise Exception("Browser driver not available, please login first")
        
        try:
            # Navigate to company page
            company_url = f"https://www.linkedin.com/company/{company_id}/"
            driver.get(company_url)
            
            # Wait for company page to load
            timeout = self.config.get("browser_timeout", 30)
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.CLASS_NAME, "org-top-card"))
            )
            
            # Extract company information
            company_info = {
                "company_id": company_id,
                "url": company_url
            }
            
            # Basic info
            try:
                name_elem = driver.find_element(By.CSS_SELECTOR, ".org-top-card__primary-content .org-top-card__title")
                company_info["name"] = name_elem.text.strip()
            except:
                company_info["name"] = ""
            
            try:
                tagline_elem = driver.find_element(By.CSS_SELECTOR, ".org-top-card-summary__tagline")
                company_info["tagline"] = tagline_elem.text.strip()
            except:
                company_info["tagline"] = ""
            
            # Company details (followers, employees, etc.)
            try:
                follower_elem = driver.find_element(By.CSS_SELECTOR, ".org-top-card-summary-info-list__info-item")
                follower_text = follower_elem.text.strip()
                if "followers" in follower_text.lower():
                    followers = ''.join(filter(str.isdigit, follower_text))
                    company_info["followers"] = followers
            except:
                company_info["followers"] = ""
            
            # About section (might need to navigate to about page)
            try:
                # Try to get about section from main page
                about_elem = driver.find_element(By.CSS_SELECTOR, ".org-grid__content-height-enforcer")
                description = about_elem.text.strip()
                if description:
                    company_info["description"] = description
                else:
                    # Navigate to about page
                    about_url = f"{company_url}about/"
                    driver.get(about_url)
                    
                    # Wait for about page to load
                    WebDriverWait(driver, timeout).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".org-grid__content-height-enforcer"))
                    )
                    
                    about_elem = driver.find_element(By.CSS_SELECTOR, ".org-grid__content-height-enforcer")
                    company_info["description"] = about_elem.text.strip()
            except:
                company_info["description"] = ""
            
            # Get company details from the About page
            try:
                # Extract website, industry, size, etc.
                detail_elems = driver.find_elements(By.CSS_SELECTOR, ".org-about-company-module__container")
                
                for elem in detail_elems:
                    try:
                        label_elem = elem.find_element(By.CSS_SELECTOR, ".text-sm")
                        label = label_elem.text.strip().lower()
                        
                        value_elem = elem.find_element(By.CSS_SELECTOR, ".org-about-company-module__company-size-definition-text")
                        value = value_elem.text.strip()
                        
                        if "website" in label:
                            company_info["website"] = value
                        elif "industry" in label:
                            company_info["industry"] = value
                        elif "size" in label:
                            company_info["company_size"] = value
                        elif "founded" in label:
                            company_info["founded"] = value
                        elif "headquarters" in label:
                            company_info["headquarters"] = value
                    except:
                        pass
            except:
                pass
            
            # Try to get specialties
            try:
                specialties_section = driver.find_element(By.CSS_SELECTOR, ".org-about-company-module__specialities")
                specialties_text = specialties_section.text.strip()
                if "Specialties" in specialties_text:
                    specialties = specialties_text.split("Specialties")[1].strip()
                    company_info["specialties"] = [s.strip() for s in specialties.split(",")]
            except:
                company_info["specialties"] = []
            
            # Cache the company data
            self._cache_company(company_id, company_info)
            
            return company_info
        except Exception as e:
            raise Exception(f"Browser company retrieval failed: {str(e)}")
    
    def get_feed(self, count: int = 10, feed_type: str = "general") -> Dict[str, Any]:
        """
        Get LinkedIn feed posts
        
        Args:
            count: Number of feed items to retrieve
            feed_type: Type of feed (general, news, relevant)
            
        Returns:
            Dict containing feed items
        """
        logger.info(f"Getting {count} feed items for feed type: {feed_type}")
        
        # Validate session
        if not self._check_session():
            raise Exception("Not logged in")
        
        # Browser-based feed retrieval
        driver = self.auth.get_driver()
        if not driver:
            raise Exception("Browser driver not available, please login first")
        
        try:
            # Navigate to feed page
            if feed_type == "news":
                driver.get("https://www.linkedin.com/news/")
            else:
                driver.get("https://www.linkedin.com/feed/")
            
            # Wait for feed to load
            timeout = self.config.get("browser_timeout", 30)
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".feed-shared-update-v2"))
            )
            
            # Scroll to load more feed items
            loaded_items = 0
            max_scroll_attempts = 5
            scroll_attempts = 0
            
            while loaded_items < count and scroll_attempts < max_scroll_attempts:
                # Get current feed items
                feed_items = driver.find_elements(By.CSS_SELECTOR, ".feed-shared-update-v2")
                loaded_items = len(feed_items)
                
                # Scroll down if we need more items
                if loaded_items < count:
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(2)  # Wait for more items to load
                    scroll_attempts += 1
            
            # Extract feed items
            feed_items = driver.find_elements(By.CSS_SELECTOR, ".feed-shared-update-v2")[:count]
            results = []
            
            for item in feed_items:
                try:
                    # Extract post details
                    post_info = {}
                    
                    # Author info
                    try:
                        author_elem = item.find_element(By.CSS_SELECTOR, ".feed-shared-actor__name")
                        post_info["author_name"] = author_elem.text.strip()
                        
                        author_description = item.find_element(By.CSS_SELECTOR, ".feed-shared-actor__description")
                        post_info["author_headline"] = author_description.text.strip()
                        
                        # Try to get author profile link
                        try:
                            author_link = author_elem.find_element(By.TAG_NAME, "a").get_attribute("href")
                            post_info["author_profile"] = author_link
                        except:
                            post_info["author_profile"] = ""
                    except:
                        post_info["author_name"] = ""
                        post_info["author_headline"] = ""
                        post_info["author_profile"] = ""
                    
                    # Post content
                    try:
                        content_elem = item.find_element(By.CSS_SELECTOR, ".feed-shared-update-v2__description")
                        post_info["content"] = content_elem.text.strip()
                    except:
                        post_info["content"] = ""
                    
                    # Post time
                    try:
                        time_elem = item.find_element(By.CSS_SELECTOR, ".feed-shared-actor__sub-description")
                        post_info["posted_time"] = time_elem.text.strip()
                    except:
                        post_info["posted_time"] = ""
                    
                    # Try to get media (image, video)
                    try:
                        media_elem = item.find_element(By.CSS_SELECTOR, ".feed-shared-update-v2__content .feed-shared-image")
                        if media_elem:
                            post_info["has_media"] = True
                    except:
                        post_info["has_media"] = False
                    
                    # Try to get reactions count
                    try:
                        reactions_elem = item.find_element(By.CSS_SELECTOR, ".social-details-social-counts__reactions-count")
                        post_info["reactions_count"] = reactions_elem.text.strip()
                    except:
                        post_info["reactions_count"] = "0"
                    
                    # Try to get comments count
                    try:
                        comments_elem = item.find_element(By.CSS_SELECTOR, ".social-details-social-counts__comments")
                        comments_text = comments_elem.text.strip()
                        comments_count = ''.join(filter(str.isdigit, comments_text))
                        post_info["comments_count"] = comments_count if comments_count else "0"
                    except:
                        post_info["comments_count"] = "0"
                    
                    results.append(post_info)
                except Exception as e:
                    logger.warning(f"Error extracting feed item: {str(e)}")
            
            return {
                "type": feed_type,
                "count": len(results),
                "results": results
            }
        except Exception as e:
            raise Exception(f"Feed retrieval failed: {str(e)}")
    
    def _cache_profile(self, profile_id: str, profile_data: Dict[str, Any]) -> None:
        """
        Cache profile data to disk
        
        Args:
            profile_id: LinkedIn profile ID
            profile_data: Profile data to cache
        """
        profile_file = self.profiles_dir / f"{profile_id}.json"
        
        # Add cache timestamp
        profile_data["_cached_at"] = datetime.now().isoformat()
        
        try:
            with open(profile_file, "w") as f:
                json.dump(profile_data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to cache profile: {str(e)}")
    
    def _get_cached_profile(self, profile_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached profile data
        
        Args:
            profile_id: LinkedIn profile ID
            
        Returns:
            Dict containing cached profile data or None if not found
        """
        profile_file = self.profiles_dir / f"{profile_id}.json"
        if not profile_file.exists():
            return None
        
        try:
            with open(profile_file, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to read cached profile: {str(e)}")
            return None
    
    def _cache_company(self, company_id: str, company_data: Dict[str, Any]) -> None:
        """
        Cache company data to disk
        
        Args:
            company_id: LinkedIn company ID
            company_data: Company data to cache
        """
        company_file = self.companies_dir / f"{company_id}.json"
        
        # Add cache timestamp
        company_data["_cached_at"] = datetime.now().isoformat()
        
        try:
            with open(company_file, "w") as f:
                json.dump(company_data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to cache company: {str(e)}")
    
    def _get_cached_company(self, company_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached company data
        
        Args:
            company_id: LinkedIn company ID
            
        Returns:
            Dict containing cached company data or None if not found
        """
        company_file = self.companies_dir / f"{company_id}.json"
        if not company_file.exists():
            return None
        
        try:
            with open(company_file, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to read cached company: {str(e)}")
            return None
    
    def _format_date(self, date_obj: Dict[str, Any]) -> str:
        """
        Format date object from LinkedIn API
        
        Args:
            date_obj: Date object from API
            
        Returns:
            Formatted date string (e.g., "Jan 2020")
        """
        if not date_obj:
            return ""
        
        month = date_obj.get("month", 0)
        year = date_obj.get("year", 0)
        
        if not year:
            return ""
        
        if month:
            month_names = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            return f"{month_names[month]} {year}"
        else:
            return str(year)
    
    def _format_year(self, year: Optional[int]) -> str:
        """
        Format year value
        
        Args:
            year: Year value or None
            
        Returns:
            String representation of year or empty string
        """
        return str(year) if year else ""
    
    def _parse_date_range(self, date_range: str) -> Tuple[str, str]:
        """
        Parse date range string from LinkedIn
        
        Args:
            date_range: Date range string (e.g., "Jan 2020 - Present")
            
        Returns:
            Tuple of (start_date, end_date)
        """
        if " - " in date_range:
            parts = date_range.split(" - ")
            return parts[0].strip(), parts[1].strip()
        else:
            return date_range.strip(), ""
    
    def _check_session(self) -> bool:
        """
        Check if user is logged in
        
        Returns:
            Boolean indicating if session is valid
        """
        session_state = self.auth.check_session()
        return session_state.get("logged_in", False)