"""
LinkedIn job application module
Supports applying to jobs, tracking applications, and managing application status
"""

import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from linkedin_mcp.api.auth import LinkedInAuth
from linkedin_mcp.utils.config import get_config

logger = logging.getLogger("linkedin-mcp")

class JobApplication:
    """
    Handles LinkedIn job application operations
    """
    
    def __init__(self):
        """Initialize the job application module"""
        self.config = get_config()
        self.auth = LinkedInAuth()
        self.data_dir = Path(self.config.get("data_dir", "data"))
        self.data_dir.mkdir(exist_ok=True)
        self.applications_dir = self.data_dir / "applications"
        self.applications_dir.mkdir(exist_ok=True)
    
    def apply_to_job(self, job_id: str, resume_path: str = None, cover_letter_path: str = None, phone_number: str = None) -> Dict[str, Any]:
        """
        Apply to a job on LinkedIn
        
        Args:
            job_id: LinkedIn job ID
            resume_path: Path to resume file (PDF)
            cover_letter_path: Path to cover letter file (PDF)
            phone_number: Phone number for application
            
        Returns:
            Dict containing application status
        """
        logger.info(f"Applying to job with ID: {job_id}")
        
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
            
            # Extract job and company info for recording
            job_title = driver.find_element(By.CLASS_NAME, "job-details-jobs-unified-top-card__job-title").text.strip()
            company = driver.find_element(By.CLASS_NAME, "job-details-jobs-unified-top-card__company-name").text.strip()
            
            # Find and click the apply button
            try:
                apply_button = driver.find_element(By.CSS_SELECTOR, "button[aria-label='Apply']")
                apply_button.click()
                
                # Wait for application form to load
                WebDriverWait(driver, timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".jobs-easy-apply-content"))
                )
                
                # Check if this is an Easy Apply form
                is_easy_apply = True
                
                # Process the application form
                application_submitted = self._process_application_form(
                    driver, resume_path, cover_letter_path, phone_number
                )
                
                # Record the application
                application_data = {
                    "job_id": job_id,
                    "job_title": job_title,
                    "company": company,
                    "application_date": datetime.now().isoformat(),
                    "status": "submitted" if application_submitted else "started",
                    "method": "easy_apply" if is_easy_apply else "external",
                    "url": job_url
                }
                
                self._save_application_record(job_id, application_data)
                
                # Return status
                if application_submitted:
                    return {
                        "success": True, 
                        "message": "Application submitted successfully", 
                        "job_id": job_id,
                        "status": "submitted"
                    }
                else:
                    return {
                        "success": False, 
                        "message": "Application process started but not completed", 
                        "job_id": job_id,
                        "status": "in_progress"
                    }
                
            except NoSuchElementException:
                # Check if there's an external application link
                try:
                    external_apply_button = driver.find_element(By.CSS_SELECTOR, "button[data-control-name='jobdetails_topcard_inapply']")
                    external_apply_url = external_apply_button.get_attribute("data-job-url")
                    
                    # Record external application
                    application_data = {
                        "job_id": job_id,
                        "job_title": job_title,
                        "company": company,
                        "application_date": datetime.now().isoformat(),
                        "status": "external_redirect",
                        "method": "external",
                        "url": external_apply_url or job_url
                    }
                    
                    self._save_application_record(job_id, application_data)
                    
                    return {
                        "success": True, 
                        "message": "External application link found", 
                        "job_id": job_id,
                        "external_url": external_apply_url,
                        "status": "external_redirect"
                    }
                except:
                    # Neither Easy Apply nor external link found
                    return {
                        "success": False, 
                        "message": "No application method found", 
                        "job_id": job_id,
                        "status": "no_apply_option"
                    }
        except Exception as e:
            raise Exception(f"Failed to apply to job: {str(e)}")
    
    def _process_application_form(self, driver, resume_path: str = None, cover_letter_path: str = None, phone_number: str = None) -> bool:
        """
        Process LinkedIn's Easy Apply application form
        
        Args:
            driver: Selenium WebDriver instance
            resume_path: Path to resume file
            cover_letter_path: Path to cover letter file
            phone_number: Phone number for application
            
        Returns:
            Boolean indicating if application was submitted successfully
        """
        try:
            # Multi-step application process
            while True:
                # Wait for current step to load
                time.sleep(1)
                
                # Check if we need to upload a resume
                try:
                    resume_upload = driver.find_element(By.CSS_SELECTOR, "input[name='resume']")
                    if resume_path and os.path.exists(resume_path):
                        resume_upload.send_keys(os.path.abspath(resume_path))
                except:
                    pass
                
                # Check if we need to upload a cover letter
                try:
                    cover_letter_upload = driver.find_element(By.CSS_SELECTOR, "input[name='coverLetter']")
                    if cover_letter_path and os.path.exists(cover_letter_path):
                        cover_letter_upload.send_keys(os.path.abspath(cover_letter_path))
                except:
                    pass
                
                # Check for phone number field
                try:
                    phone_field = driver.find_element(By.CSS_SELECTOR, "input[name='phoneNumber']")
                    if phone_number and not phone_field.get_attribute("value"):
                        phone_field.send_keys(phone_number)
                except:
                    pass
                
                # Look for common form fields and fill them if empty
                self._fill_common_form_fields(driver)
                
                # Check if there's a next button
                try:
                    next_button = driver.find_element(By.CSS_SELECTOR, "button[aria-label='Continue to next step']")
                    next_button.click()
                    continue
                except:
                    pass
                
                # Check if there's a submit button
                try:
                    submit_button = driver.find_element(By.CSS_SELECTOR, "button[aria-label='Submit application']")
                    submit_button.click()
                    
                    # Wait for submission confirmation
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".artdeco-modal__content"))
                    )
                    
                    return True
                except:
                    pass
                
                # Check if there's a review button
                try:
                    review_button = driver.find_element(By.CSS_SELECTOR, "button[aria-label='Review your application']")
                    review_button.click()
                    continue
                except:
                    pass
                
                # If we reached here, we're likely stuck at a form page
                # Try once more to find submit or next buttons with different selectors
                try:
                    buttons = driver.find_elements(By.TAG_NAME, "button")
                    for button in buttons:
                        button_text = button.text.lower()
                        if "submit" in button_text or "apply" in button_text:
                            button.click()
                            return True
                        elif "next" in button_text or "continue" in button_text:
                            button.click()
                            break
                    continue
                except:
                    # If we can't find any navigation buttons, we're stuck
                    return False
        except Exception as e:
            logger.error(f"Error processing application form: {str(e)}")
            return False
    
    def _fill_common_form_fields(self, driver):
        """
        Fill common application form fields if they're empty
        """
        try:
            # Look for work experience fields (years of experience)
            experience_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='number']")
            for input_elem in experience_inputs:
                if not input_elem.get_attribute("value"):
                    input_elem.send_keys("3")  # Default value
        except:
            pass
        
        # Handle dropdown selections
        try:
            dropdowns = driver.find_elements(By.TAG_NAME, "select")
            for dropdown in dropdowns:
                if not dropdown.get_attribute("value"):
                    # Select the second option (often the first is "Please select")
                    options = dropdown.find_elements(By.TAG_NAME, "option")
                    if len(options) > 1:
                        options[1].click()
        except:
            pass
        
        # Handle yes/no radio buttons (usually select "Yes" for positive questions)
        try:
            radio_groups = driver.find_elements(By.CSS_SELECTOR, "fieldset")
            for group in radio_groups:
                # Check if it's likely a yes/no question
                labels = group.find_elements(By.TAG_NAME, "label")
                if len(labels) == 2:
                    # Click the first radio button (usually "Yes")
                    radio = group.find_element(By.CSS_SELECTOR, "input[type='radio']")
                    radio.click()
        except:
            pass
    
    def get_application_status(self, job_id: str) -> Dict[str, Any]:
        """
        Get the status of a job application
        
        Args:
            job_id: LinkedIn job ID
            
        Returns:
            Dict containing application status information
        """
        logger.info(f"Getting application status for job ID: {job_id}")
        
        # Check if we have a local record
        application_data = self._get_application_record(job_id)
        if application_data:
            return application_data
        
        # No record found
        return {
            "job_id": job_id,
            "status": "not_applied",
            "message": "No application record found for this job"
        }
    
    def get_application_history(self) -> List[Dict[str, Any]]:
        """
        Get history of job applications
        
        Returns:
            List of application records
        """
        logger.info("Getting application history")
        
        # Validate session
        if not self._check_session():
            raise Exception("Not logged in")
        
        applications = []
        
        # Get local application records
        for file_path in self.applications_dir.glob("*.json"):
            try:
                with open(file_path, "r") as f:
                    application_data = json.load(f)
                    applications.append(application_data)
            except Exception as e:
                logger.warning(f"Error reading application record {file_path}: {str(e)}")
        
        # Sort by application date (newest first)
        applications.sort(
            key=lambda x: x.get("application_date", ""), 
            reverse=True
        )
        
        return applications
    
    def withdraw_application(self, job_id: str) -> Dict[str, Any]:
        """
        Withdraw a job application if possible
        
        Args:
            job_id: LinkedIn job ID
            
        Returns:
            Dict indicating success status
        """
        logger.info(f"Withdrawing application for job ID: {job_id}")
        
        # Validate session
        if not self._check_session():
            raise Exception("Not logged in")
        
        # Check if application exists
        application_data = self._get_application_record(job_id)
        if not application_data:
            return {
                "success": False,
                "message": "No application record found for this job",
                "job_id": job_id
            }
        
        # Update local record
        application_data["status"] = "withdrawn"
        application_data["withdrawn_date"] = datetime.now().isoformat()
        self._save_application_record(job_id, application_data)
        
        # Attempt to withdraw on LinkedIn (this is limited as LinkedIn doesn't fully support this)
        # For most applications, this is just updating our local record
        
        return {
            "success": True,
            "message": "Application marked as withdrawn",
            "job_id": job_id,
            "status": "withdrawn"
        }
    
    def _save_application_record(self, job_id: str, data: Dict[str, Any]) -> None:
        """
        Save application record to disk
        
        Args:
            job_id: LinkedIn job ID
            data: Application data to save
        """
        application_file = self.applications_dir / f"{job_id}.json"
        
        try:
            with open(application_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save application record: {str(e)}")
    
    def _get_application_record(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve application record from disk
        
        Args:
            job_id: LinkedIn job ID
            
        Returns:
            Application data or None if not found
        """
        application_file = self.applications_dir / f"{job_id}.json"
        if not application_file.exists():
            return None
        
        try:
            with open(application_file, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to read application record: {str(e)}")
            return None
    
    def _check_session(self) -> bool:
        """
        Check if user is logged in
        
        Returns:
            Boolean indicating if session is valid
        """
        session_state = self.auth.check_session()
        return session_state.get("logged_in", False)