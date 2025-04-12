"""
Protocol definitions for the LinkedIn MCP server
Implements Model Context Protocol specification
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field

class Error(BaseModel):
    """Error information returned in responses"""
    code: int
    message: str
    data: Optional[Any] = None

class MCPRequest(BaseModel):
    """
    Base class for MCP requests following the JSON-RPC 2.0 specification
    """
    jsonrpc: str = Field(default="2.0", description="JSON-RPC version")
    id: Optional[Union[str, int]] = Field(description="Request identifier")
    method: str = Field(description="Method name")
    params: Optional[Dict[str, Any]] = Field(default=None, description="Method parameters")

class MCPResponse(BaseModel):
    """
    Base class for MCP responses
    """
    jsonrpc: str = Field(default="2.0", description="JSON-RPC version")
    id: Optional[Union[str, int]] = Field(description="Request identifier")

class SuccessResponse(MCPResponse):
    """
    Response for successful requests
    """
    result: Any = Field(description="Result of the request")

class ErrorResponse(MCPResponse):
    """
    Response for failed requests
    """
    error: Error = Field(description="Error information")

class LinkedInSessionState(BaseModel):
    """
    LinkedIn session state information
    """
    logged_in: bool
    username: Optional[str] = None
    cookies: Optional[Dict[str, str]] = None
    headers: Optional[Dict[str, str]] = None

class JobSearchFilter(BaseModel):
    """
    LinkedIn job search filter parameters
    """
    keywords: Optional[str] = None
    location: Optional[str] = None
    distance: Optional[int] = None
    date_posted: Optional[str] = None
    job_type: Optional[List[str]] = None
    experience_level: Optional[List[str]] = None
    job_function: Optional[List[str]] = None
    industries: Optional[List[str]] = None
    company_name: Optional[str] = None

class JobDetails(BaseModel):
    """
    LinkedIn job details
    """
    job_id: str
    title: str
    company: str
    location: str
    description: Optional[str] = None
    date_posted: Optional[str] = None
    url: Optional[str] = None
    employment_type: Optional[str] = None
    seniority_level: Optional[str] = None
    functions: Optional[List[str]] = None
    industries: Optional[List[str]] = None
    applicant_count: Optional[int] = None
    skills: Optional[List[str]] = None
    benefits: Optional[List[str]] = None

class Profile(BaseModel):
    """
    LinkedIn profile information
    """
    profile_id: str
    name: str
    headline: Optional[str] = None
    summary: Optional[str] = None
    location: Optional[str] = None
    industry: Optional[str] = None
    experience: Optional[List[Dict[str, Any]]] = None
    education: Optional[List[Dict[str, Any]]] = None
    skills: Optional[List[str]] = None
    certifications: Optional[List[Dict[str, Any]]] = None
    projects: Optional[List[Dict[str, Any]]] = None
    languages: Optional[List[Dict[str, str]]] = None
    profile_url: Optional[str] = None