"""
LinkedIn authentication module for managing user sessions
"""

import json
import logging
import os
import pickle
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

import requests
from linkedin_api import Linkedin
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from linkedin_mcp.core.protocol import LinkedInSessionState
from linkedin_mcp.utils.config import get_config

logger = logging.getLogger("linkedin-mcp")

class LinkedInAuth:
    """
    Handles LinkedIn authentication and session management
    Supports both API-based and browser-based authentication
    """
    
    def __init__(self):
        """Initialize the LinkedIn auth module"""
        self.config = get_config()
        self.session_dir = Path(self.config.get("session_dir", "sessions"))
        self.session_dir.mkdir(exist_ok=True)
        self.api_client = None
        self.driver = None
        self.session_state = LinkedInSessionState(logged_in=False)
    
    def login(self, username: str, password: str) -> Dict[str, Any]:
        """
        Log in to LinkedIn using the provided credentials
        Attempts API login first, falls back to browser-based login if needed
        
        Args:
            username: LinkedIn username (email)
            password: LinkedIn password
            
        Returns:
            Dict containing session state information
        """
        logger.info(f"Attempting to login with username: {username}")
        
        # Check if we have a saved session
        session_path = self.session_dir / f"{username}.session"
        if session_path.exists():
            try:
                with open(session_path, "rb") as f:
                    session_data = pickle.load(f)
                    
                # Check if session is still valid (less than 7 days old)
                if datetime.now() - session_data.get("timestamp", datetime.now()) < timedelta(days=7):
                    logger.info("Found valid saved session, restoring...")
                    self.api_client = Linkedin(username, password, cookies=session_data.get("cookies"))
                    
                    # Update session state
                    self.session_state = LinkedInSessionState(
                        logged_in=True,
                        username=username,
                        cookies=session_data.get("cookies"),
                        headers=session_data.get("headers")
                    )
                    
                    logger.info("Successfully restored session")
                    return self.session_state.dict()
                else:
                    logger.info("Saved session expired, creating new session")
            except Exception as e:
                logger.error(f"Error restoring session: {str(e)}")
        
        # Try API-based login first
        try:
            logger.info("Attempting API-based login")
            self.api_client = Linkedin(username, password)
            
            # Save session for future use
            session_data = {
                "timestamp": datetime.now(),
                "cookies": self.api_client.client.cookies,
                "headers": self.api_client.client.headers
            }
            
            with open(session_path, "wb") as f:
                pickle.dump(session_data, f)
            
            # Update session state
            self.session_state = LinkedInSessionState(
                logged_in=True,
                username=username,
                cookies=dict(self.api_client.client.cookies),
                headers=dict(self.api_client.client.headers)
            )
            
            logger.info("API-based login successful")
            return self.session_state.dict()
        except Exception as api_error:
            logger.warning(f"API login failed: {str(api_error)}, falling back to browser-based login")
            
            # Fall back to browser-based login
            try:
                logger.info("Attempting browser-based login")
                self._browser_login(username, password)
                
                # Update session state
                self.session_state = LinkedInSessionState(
                    logged_in=True,
                    username=username,
                    cookies=self._get_browser_cookies() if self.driver else None
                )
                
                logger.info("Browser-based login successful")
                return self.session_state.dict()
            except Exception as browser_error:
                logger.error(f"Browser login failed: {str(browser_error)}")
                raise Exception(f"Failed to login: {str(browser_error)}")
    
    def _browser_login(self, username: str, password: str) -> None:
        """
        Log in to LinkedIn using a browser automation
        
        Args:
            username: LinkedIn username (email)
            password: LinkedIn password
        """
        # Set up undetected Chrome driver to avoid detection
        options = uc.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        
        # Initialize the driver
        self.driver = uc.Chrome(options=options)
        
        try:
            # Navigate to LinkedIn login page
            self.driver.get("https://www.linkedin.com/login")
            
            # Wait for the page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "username"))
            )
            
            # Fill in login form
            self.driver.find_element(By.ID, "username").send_keys(username)
            self.driver.find_element(By.ID, "password").send_keys(password)
            self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
            
            # Wait for successful login
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".global-nav__me-photo"))
            )
            
            # Save cookies for future use
            session_path = self.session_dir / f"{username}.session"
            session_data = {
                "timestamp": datetime.now(),
                "cookies": self._get_browser_cookies()
            }
            
            with open(session_path, "wb") as f:
                pickle.dump(session_data, f)
            
            logger.info("Browser login successful and cookies saved")
        except TimeoutException:
            # Check if we might have encountered a security verification page
            if "security verification" in self.driver.page_source.lower():
                raise Exception("Security verification required. Please login manually first.")
            raise Exception("Login timed out - LinkedIn might be blocking automated logins")
        except Exception as e:
            raise Exception(f"Browser login error: {str(e)}")
    
    def _get_browser_cookies(self) -> Dict[str, str]:
        """
        Get cookies from the browser session
        
        Returns:
            Dict containing cookies from the browser
        """
        if not self.driver:
            return {}
            
        return {cookie["name"]: cookie["value"] for cookie in self.driver.get_cookies()}
    
    def logout(self) -> Dict[str, Any]:
        """
        Log out from LinkedIn
        
        Returns:
            Dict indicating logout success
        """
        logger.info("Logging out from LinkedIn")
        
        if self.api_client:
            self.api_client = None
        
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            finally:
                self.driver = None
        
        # Update session state
        self.session_state = LinkedInSessionState(logged_in=False)
        
        return {"success": True, "message": "Logged out successfully"}
    
    def check_session(self) -> Dict[str, Any]:
        """
        Check if the current session is valid
        
        Returns:
            Dict containing session state information
        """
        logger.info("Checking LinkedIn session")
        
        # If we have an API client or driver, assume we're logged in
        logged_in = bool(self.api_client or (self.driver and self._is_browser_session_valid()))
        self.session_state.logged_in = logged_in
        
        return self.session_state.dict()
    
    def _is_browser_session_valid(self) -> bool:
        """
        Check if the browser session is valid by visiting LinkedIn homepage
        
        Returns:
            Boolean indicating if session is valid
        """
        if not self.driver:
            return False
            
        try:
            self.driver.get("https://www.linkedin.com/feed/")
            
            # Wait for feed to load
            WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".global-nav__me-photo"))
            )
            
            return True
        except:
            return False
    
    def get_api_client(self) -> Optional[Linkedin]:
        """
        Get the LinkedIn API client if available
        
        Returns:
            LinkedIn API client or None if not logged in
        """
        return self.api_client
    
    def get_driver(self) -> Optional[uc.Chrome]:
        """
        Get the Selenium WebDriver if available
        
        Returns:
            Selenium WebDriver or None if not using browser-based access
        """
        return self.driver