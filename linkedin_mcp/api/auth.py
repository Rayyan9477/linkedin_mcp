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
    
    def login(self, username: str, password: str, force_new: bool = False) -> Dict[str, Any]:
        """
        Log in to LinkedIn using the provided credentials
        Attempts API login first, falls back to browser-based login if needed
        
        Args:
            username: LinkedIn username (email)
            password: LinkedIn password
            force_new: If True, forces a new login even if a valid session exists
            
        Returns:
            Dict containing session state information
            
        Raises:
            Exception: If login fails after all attempts
        """
        logger.info(f"Attempting to login with username: {username}")
        
        # Check if we have a valid saved session and not forcing new login
        if not force_new:
            try:
                session_data = self._load_session(username)
                if session_data:
                    logger.info("Successfully restored session from cache")
                    return session_data
            except Exception as e:
                logger.warning(f"Session restoration failed: {str(e)}")
        else:
            logger.info("Forcing new login as requested")
        
        # Attempt API login first
        try:
            logger.info("Attempting API login...")
            self.api_client = Linkedin(
                username, 
                password,
                refresh_cookies=True,
                debug=logger.getEffectiveLevel() == logging.DEBUG
            )
            
            # Get session cookies and headers
            cookies = dict(self.api_client.client.session.cookies)
            headers = dict(self.api_client.client.headers)
            
            # Update session state
            self.session_state = LinkedInSessionState(
                logged_in=True,
                username=username,
                cookies=cookies,
                headers=headers
            )
            
            # Save the session
            self._save_session(username, cookies, headers)
            
            logger.info("API login successful")
            return self.session_state.dict()
            
        except Exception as api_error:
            logger.warning(f"API login failed: {str(api_error)}")
            if "Challenge" in str(api_error):
                logger.warning("Challenge detected, falling back to browser login")
                return self._browser_login_with_retry(username, password)
                
            # If it's not a challenge error, try browser login
            logger.info("Falling back to browser login...")
            return self._browser_login_with_retry(username, password)
    
    def _load_session(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Load a saved session from cache
        
        Args:
            username: LinkedIn username (email)
        
        Returns:
            Dict containing session state information or None if no valid session found
        """
        session_path = self.session_dir / f"{username}.session"
        if session_path.exists():
            try:
                with open(session_path, "rb") as f:
                    session_data = pickle.load(f)
                    
                # Check if session is still valid (less than 7 days old)
                if datetime.now() - session_data.get("timestamp", datetime.now()) < timedelta(days=7):
                    return session_data
            except Exception as e:
                logger.error(f"Error loading session: {str(e)}")
        
        return None
        
    def _save_session(self, username: str, cookies: Dict[str, str], headers: Dict[str, str]) -> None:
        """
        Save session data to cache
        
        Args:
            username: LinkedIn username (email)
            cookies: Session cookies
            headers: Session headers
        """
        session_path = self.session_dir / f"{username}.session"
        session_data = {
            "timestamp": datetime.now(),
            "cookies": cookies,
            "headers": headers
        }
        
        try:
            with open(session_path, "wb") as f:
                pickle.dump(session_data, f)
            logger.info("Session saved successfully")
        except Exception as e:
            logger.error(f"Failed to save session: {str(e)}")
            
    def _browser_login_with_retry(self, username: str, password: str, max_retries: int = 3) -> Dict[str, Any]:
        """
        Attempt browser login with retry logic
        
        Args:
            username: LinkedIn username (email)
            password: LinkedIn password
            max_retries: Maximum number of login attempts
            
        Returns:
            Dict containing session state information
            
        Raises:
            Exception: If all login attempts fail
        """
        last_error = None
        
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"Browser login attempt {attempt}/{max_retries}")
                self._browser_login(username, password)
                
                # Get browser cookies
                cookies = self._get_browser_cookies()
                
                # Save the session
                self._save_session(username, cookies, {})
                
                # Update session state
                self.session_state = LinkedInSessionState(
                    logged_in=True,
                    username=username,
                    cookies=cookies,
                    headers={}
                )
                
                logger.info("Browser login successful")
                return self.session_state.dict()
                
            except Exception as e:
                last_error = e
                logger.warning(f"Browser login attempt {attempt} failed: {str(e)}")
                
                # Clean up any existing driver
                if self.driver:
                    try:
                        self.driver.quit()
                    except:
                        pass
                    self.driver = None
                
                # Add delay between retries
                if attempt < max_retries:
                    retry_delay = 5 * attempt  # Exponential backoff
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
        
        # If we get here, all attempts failed
        raise Exception(f"All {max_retries} browser login attempts failed. Last error: {str(last_error)}")
    
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