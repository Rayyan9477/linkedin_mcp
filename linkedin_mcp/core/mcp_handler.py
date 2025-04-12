"""
MCP Handler for processing LinkedIn requests
"""

import logging
from typing import Any, Dict, List, Optional, Union

from linkedin_mcp.api.auth import LinkedInAuth
from linkedin_mcp.api.job_search import LinkedInJobSearch
from linkedin_mcp.api.profile import LinkedInProfile
from linkedin_mcp.api.resume_generator import ResumeGenerator
from linkedin_mcp.api.cover_letter_generator import CoverLetterGenerator
from linkedin_mcp.api.job_application import JobApplication
from linkedin_mcp.core.protocol import MCPRequest, Error

logger = logging.getLogger("linkedin-mcp")

class MCPHandler:
    """
    Handles all MCP requests by routing to appropriate service
    """
    
    def __init__(self):
        """Initialize all required service instances"""
        self.auth = LinkedInAuth()
        self.job_search = LinkedInJobSearch()
        self.profile = LinkedInProfile()
        self.resume_generator = ResumeGenerator()
        self.cover_letter_generator = CoverLetterGenerator()
        self.job_application = JobApplication()
        
        # Register method handlers
        self.method_handlers = {
            # Authentication methods
            "linkedin.login": self._handle_login,
            "linkedin.logout": self._handle_logout,
            "linkedin.checkSession": self._handle_check_session,
            
            # Browsing methods
            "linkedin.getFeed": self._handle_get_feed,
            "linkedin.getProfile": self._handle_get_profile,
            "linkedin.getCompany": self._handle_get_company,
            
            # Job search methods
            "linkedin.searchJobs": self._handle_search_jobs,
            "linkedin.getJobDetails": self._handle_get_job_details,
            "linkedin.getRecommendedJobs": self._handle_get_recommended_jobs,
            
            # Resume and cover letter methods
            "linkedin.generateResume": self._handle_generate_resume,
            "linkedin.generateCoverLetter": self._handle_generate_cover_letter,
            "linkedin.tailorResume": self._handle_tailor_resume,
            
            # Application methods
            "linkedin.applyToJob": self._handle_apply_to_job,
            "linkedin.getApplicationStatus": self._handle_get_application_status,
            "linkedin.getSavedJobs": self._handle_get_saved_jobs,
            "linkedin.saveJob": self._handle_save_job,
        }
    
    def process_request(self, request: MCPRequest) -> Any:
        """
        Process an MCP request by routing to the appropriate handler
        
        Args:
            request: The MCP request to process
            
        Returns:
            The result of the request
            
        Raises:
            Exception: If the method is not supported or an error occurs
        """
        method = request.method
        params = request.params or {}
        
        handler = self.method_handlers.get(method)
        if not handler:
            logger.error(f"Method not supported: {method}")
            raise Exception(f"Method not supported: {method}")
        
        logger.info(f"Processing request for method: {method}")
        return handler(params)
    
    # Authentication handlers
    def _handle_login(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle LinkedIn login request"""
        username = params.get("username")
        password = params.get("password")
        
        if not username or not password:
            raise Exception("Username and password are required")
        
        return self.auth.login(username, password)
    
    def _handle_logout(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle LinkedIn logout request"""
        return self.auth.logout()
    
    def _handle_check_session(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle LinkedIn session check request"""
        return self.auth.check_session()
    
    # Browsing handlers
    def _handle_get_feed(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle LinkedIn feed request"""
        count = params.get("count", 10)
        feed_type = params.get("type", "general")
        return self.profile.get_feed(count, feed_type)
    
    def _handle_get_profile(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle LinkedIn profile request"""
        profile_id = params.get("profileId")
        if not profile_id:
            raise Exception("Profile ID is required")
        
        return self.profile.get_profile(profile_id)
    
    def _handle_get_company(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle LinkedIn company profile request"""
        company_id = params.get("companyId")
        if not company_id:
            raise Exception("Company ID is required")
        
        return self.profile.get_company(company_id)
    
    # Job search handlers
    def _handle_search_jobs(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle LinkedIn job search request"""
        search_filter = params.get("filter", {})
        page = params.get("page", 1)
        count = params.get("count", 20)
        
        return self.job_search.search_jobs(search_filter, page, count)
    
    def _handle_get_job_details(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle LinkedIn job details request"""
        job_id = params.get("jobId")
        if not job_id:
            raise Exception("Job ID is required")
        
        return self.job_search.get_job_details(job_id)
    
    def _handle_get_recommended_jobs(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle LinkedIn recommended jobs request"""
        count = params.get("count", 10)
        return self.job_search.get_recommended_jobs(count)
    
    # Resume and cover letter handlers
    def _handle_generate_resume(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle resume generation request"""
        profile_id = params.get("profileId")
        template = params.get("template", "standard")
        format_type = params.get("format", "pdf")
        
        if not profile_id:
            raise Exception("Profile ID is required")
        
        return self.resume_generator.generate_resume(profile_id, template, format_type)
    
    def _handle_generate_cover_letter(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle cover letter generation request"""
        profile_id = params.get("profileId")
        job_id = params.get("jobId")
        template = params.get("template", "standard")
        format_type = params.get("format", "pdf")
        
        if not profile_id or not job_id:
            raise Exception("Profile ID and Job ID are required")
        
        return self.cover_letter_generator.generate_cover_letter(profile_id, job_id, template, format_type)
    
    def _handle_tailor_resume(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle resume tailoring request"""
        profile_id = params.get("profileId")
        job_id = params.get("jobId")
        template = params.get("template", "standard")
        format_type = params.get("format", "pdf")
        
        if not profile_id or not job_id:
            raise Exception("Profile ID and Job ID are required")
        
        return self.resume_generator.tailor_resume(profile_id, job_id, template, format_type)
    
    # Application handlers
    def _handle_apply_to_job(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle job application request"""
        job_id = params.get("jobId")
        resume_id = params.get("resumeId")
        cover_letter_id = params.get("coverLetterId")
        
        if not job_id or not resume_id:
            raise Exception("Job ID and Resume ID are required")
        
        return self.job_application.apply_to_job(job_id, resume_id, cover_letter_id)
    
    def _handle_get_application_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle job application status request"""
        application_id = params.get("applicationId")
        
        if not application_id:
            raise Exception("Application ID is required")
        
        return self.job_application.get_application_status(application_id)
    
    def _handle_get_saved_jobs(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle saved jobs request"""
        count = params.get("count", 10)
        return self.job_search.get_saved_jobs(count)
    
    def _handle_save_job(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle save job request"""
        job_id = params.get("jobId")
        
        if not job_id:
            raise Exception("Job ID is required")
        
        return self.job_search.save_job(job_id)