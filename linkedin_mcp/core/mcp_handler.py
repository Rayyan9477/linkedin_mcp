"""
MCP Handler for processing LinkedIn requests.

This module provides the main request handling logic for the LinkedIn MCP server,
routing requests to the appropriate service modules and handling errors.
"""

import logging
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, Union, cast

from pydantic import BaseModel, ValidationError

from linkedin_mcp.api.auth import LinkedInAuth
from linkedin_mcp.api.job_search import LinkedInJobSearch
from linkedin_mcp.api.profile import LinkedInProfile
from linkedin_mcp.api.resume_generator import ResumeGenerator
from linkedin_mcp.api.cover_letter_generator import CoverLetterGenerator
from linkedin_mcp.api.job_application import JobApplication
from linkedin_mcp.core.protocol import (
    MCPRequest,
    Error,
    ErrorResponse,
    SuccessResponse,
    LinkedInSessionState,
    JobSearchFilter,
    JobDetails,
    Profile
)

# Type variable for generic method return types
T = TypeVar('T', bound=BaseModel)

# Configure logger
logger = logging.getLogger("linkedin-mcp")

class MCPError(Exception):
    """Base exception for MCP handler errors"""
    def __init__(self, message: str, code: int = -32603, data: Optional[Dict[str, Any]] = None):
        self.code = code
        self.message = message
        self.data = data or {}
        super().__init__(self.message)

class AuthenticationError(MCPError):
    """Raised when authentication fails or session is invalid"""
    def __init__(self, message: str = "Authentication failed", data: Optional[Dict[str, Any]] = None):
        super().__init__(message, code=401, data=data)

class ValidationError(MCPError):
    """Raised when request validation fails"""
    def __init__(self, message: str = "Invalid request parameters", data: Optional[Dict[str, Any]] = None):
        super().__init__(message, code=-32602, data=data)

class ResourceNotFoundError(MCPError):
    """Raised when a requested resource is not found"""
    def __init__(self, resource_type: str, resource_id: str):
        super().__init__(f"{resource_type} not found: {resource_id}", code=404)
        self.resource_type = resource_type
        self.resource_id = resource_id

def handle_errors(method: Callable) -> Callable:
    """Decorator to handle errors in MCP handler methods"""
    @wraps(method)
    async def wrapper(self, *args, **kwargs):
        try:
            return await method(self, *args, **kwargs)
        except MCPError as e:
            logger.error(f"MCP error in {method.__name__}: {str(e)}", exc_info=True)
            return ErrorResponse(
                id=kwargs.get('request_id'),
                error=Error(code=e.code, message=e.message, data=e.data)
            )
        except ValidationError as e:
            logger.error(f"Validation error in {method.__name__}: {str(e)}", exc_info=True)
            return ErrorResponse(
                id=kwargs.get('request_id'),
                error=Error(
                    code=-32602,
                    message="Invalid parameters",
                    data={"errors": e.errors()}
                )
            )
        except Exception as e:
            logger.error(f"Unexpected error in {method.__name__}: {str(e)}", exc_info=True)
            return ErrorResponse(
                id=kwargs.get('request_id'),
                error=Error(
                    code=-32603,
                    message="Internal server error",
                    data={"error": str(e)}
                )
            )
    return wrapper

def validate_request_params(params: Optional[Dict[str, Any]], model: Type[T]) -> T:
    """Validate request parameters against a Pydantic model"""
    if params is None:
        params = {}
    try:
        return model(**params)
    except ValidationError as e:
        raise ValidationError("Invalid request parameters") from e

class MCPHandler:
    """
    Handles all MCP requests by routing to appropriate service modules.
    
    This class serves as the main entry point for processing MCP requests,
    validating inputs, and dispatching to the appropriate service methods.
    It also handles error handling, logging, and response formatting.
    """
    
    def __init__(self):
        """Initialize all required service instances.
        
        This sets up the necessary service clients and registers all available
        MCP methods with their corresponding handler methods.
        """
        logger.info("Initializing MCP handler")
        
        # Initialize service clients
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
            
            # Profile methods
            "linkedin.getProfile": self._handle_get_profile,
            "linkedin.updateProfile": self._handle_update_profile,
            
            # Company methods
            "linkedin.getCompany": self._handle_get_company,
            "linkedin.searchCompanies": self._handle_search_companies,
            
            # Job search methods
            "linkedin.searchJobs": self._handle_search_jobs,
            "linkedin.getJobDetails": self._handle_get_job_details,
            "linkedin.getRecommendedJobs": self._handle_get_recommended_jobs,
            "linkedin.saveJob": self._handle_save_job,
            "linkedin.unsaveJob": self._handle_unsave_job,
            
            # Resume and cover letter methods
            "linkedin.generateResume": self._handle_generate_resume,
            "linkedin.generateCoverLetter": self._handle_generate_cover_letter,
            "linkedin.getResumeTemplates": self._handle_get_resume_templates,
            "linkedin.getCoverLetterTemplates": self._handle_get_cover_letter_templates,
            
            # Job application methods
            "linkedin.applyToJob": self._handle_apply_to_job,
            "linkedin.trackApplication": self._handle_track_application,
            "linkedin.withdrawApplication": self._handle_withdraw_application,
            
            # Connection methods
            "linkedin.getConnections": self._handle_get_connections,
            "linkedin.sendConnectionRequest": self._handle_send_connection_request,
            "linkedin.acceptConnectionRequest": self._handle_accept_connection_request,
            
            # Messaging methods
            "linkedin.sendMessage": self._handle_send_message,
            "linkedin.getMessages": self._handle_get_messages,
            "linkedin.getMessageThread": self._handle_get_message_thread,
            
            # Feed and content methods
            "linkedin.getFeed": self._handle_get_feed,
            "linkedin.getPost": self._handle_get_post,
            "linkedin.createPost": self._handle_create_post,
            "linkedin.likePost": self._handle_like_post,
            "linkedin.commentOnPost": self._handle_comment_on_post,
            
            # Notification methods
            "linkedin.getNotifications": self._handle_get_notifications,
            "linkedin.markNotificationAsRead": self._handle_mark_notification_as_read,
            
            # Settings and preferences
            "linkedin.getPrivacySettings": self._handle_get_privacy_settings,
            "linkedin.updatePrivacySettings": self._handle_update_privacy_settings,
            "linkedin.getEmailPreferences": self._handle_get_email_preferences,
            "linkedin.updateEmailPreferences": self._handle_update_email_preferences,
        }
        
        logger.info(f"Registered {len(self.method_handlers)} MCP methods")
    
    @handle_errors
    async def process_request(self, request: MCPRequest) -> Union[SuccessResponse, ErrorResponse]:
        """
        Process an incoming MCP request and return a response.
        
        This is the main entry point for handling MCP requests. It validates the request,
        routes it to the appropriate handler method, and formats the response.
        
        Args:
            request: The MCP request to process
            
        Returns:
            SuccessResponse with the result if the request was processed successfully,
            or ErrorResponse if an error occurred.
            
        Raises:
            MCPError: If there's an error processing the request
        """
        logger.info(f"Processing request: {request.method} (ID: {request.id})")
        
        # Check if the method exists
        handler = self.method_handlers.get(request.method)
        if not handler:
            logger.warning(f"Method not found: {request.method}")
            return ErrorResponse(
                id=request.id,
                error=Error(
                    code=-32601,
                    message=f"Method not found: {request.method}",
                    data={"available_methods": list(self.method_handlers.keys())}
                )
            )
        
        try:
            # Call the appropriate handler with parameters
            logger.debug(f"Dispatching to handler for {request.method}")
            result = await handler(params=request.params or {}, request_id=request.id)
            
            # If the handler already returned a response, return it as-is
            if isinstance(result, (SuccessResponse, ErrorResponse)):
                return result
                
            # Otherwise, wrap the result in a SuccessResponse
            return SuccessResponse(id=request.id, result=result)
            
        except Exception as e:
            # This should be caught by the error handler decorator,
            # but we'll include it as a fallback
            logger.exception(f"Unexpected error processing {request.method}")
            return ErrorResponse(
                id=request.id,
                error=Error(
                    code=-32603,
                    message="Internal server error",
                    data={"method": request.method, "error": str(e)}
                )
            )
    
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
        """
        Handle resume generation request.
        Supports optional 'template' and 'format' params. If template is None or not found, uses the first available template.
        """
        profile_id = params.get("profileId")
        template = params.get("template")  # Let generator handle default
        format_type = params.get("format", "pdf")
        
        if not profile_id:
            raise Exception("Profile ID is required")
        
        try:
            return self.resume_generator.generate_resume(profile_id, template, format_type)
        except Exception as e:
            logger.error(f"Failed to generate resume: {e}")
            return {"success": False, "error": str(e)}
    
    def _handle_generate_cover_letter(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle cover letter generation request.
        Supports optional 'template' and 'format' params. If template is None or not found, uses the first available template.
        """
        profile_id = params.get("profileId")
        job_id = params.get("jobId")
        template = params.get("template")  # Let generator handle default
        format_type = params.get("format", "pdf")
        
        if not profile_id or not job_id:
            raise Exception("Profile ID and Job ID are required")
        
        try:
            return self.cover_letter_generator.generate_cover_letter(profile_id, job_id, template, format_type)
        except Exception as e:
            logger.error(f"Failed to generate cover letter: {e}")
            return {"success": False, "error": str(e)}
    
    def _handle_tailor_resume(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle resume tailoring request.
        Supports optional 'template' and 'format' params. If template is None or not found, uses the first available template.
        """
        profile_id = params.get("profileId")
        job_id = params.get("jobId")
        template = params.get("template")  # Let generator handle default
        format_type = params.get("format", "pdf")
        
        if not profile_id or not job_id:
            raise Exception("Profile ID and Job ID are required")
        
        try:
            return self.resume_generator.tailor_resume(profile_id, job_id, template, format_type)
        except Exception as e:
            logger.error(f"Failed to tailor resume: {e}")
            return {"success": False, "error": str(e)}
    
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