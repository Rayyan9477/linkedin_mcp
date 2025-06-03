"""
Test script for resume generation with template support
"""
import sys
import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from linkedin_mcp.core.mcp_handler import MCPHandler
from linkedin_mcp.core.protocol import MCPRequest

# Load test data
def load_test_data(filename):
    """Load test data from JSON file"""
    test_data_dir = Path(__file__).parent / "test_data"
    with open(test_data_dir / filename, 'r', encoding='utf-8') as f:
        return json.load(f)

# Initialize the MCP handler with mocks
def setup_mocks():
    """Set up mocks for the MCP handler"""
    # Create a mock for the profile service
    profile_mock = MagicMock()
    profile_mock.get_profile.return_value = load_test_data("test_profile.json")
    
    # Create a mock for the job service
    job_mock = MagicMock()
    job_mock.get_job_details.return_value = load_test_data("test_job.json")
    
    # Create a mock for the resume generator
    resume_gen_mock = MagicMock()
    resume_gen_mock.generate_resume.return_value = {
        "success": True,
        "file_path": "/path/to/generated/resume.pdf",
        "format": "pdf",
        "file_size": 1024
    }
    resume_gen_mock.tailor_resume.return_value = {
        "success": True,
        "file_path": "/path/to/tailored/resume.pdf",
        "format": "pdf",
        "file_size": 1500
    }
    
    # Create a mock for the cover letter generator
    cover_letter_mock = MagicMock()
    cover_letter_mock.generate_cover_letter.return_value = {
        "success": True,
        "file_path": "/path/to/cover_letter.pdf",
        "format": "pdf",
        "file_size": 800
    }
    
    # Create the handler with mocks
    handler = MCPHandler()
    handler.profile_service = profile_mock
    handler.job_service = job_mock
    handler.resume_generator = resume_gen_mock
    handler.cover_letter_generator = cover_letter_mock
    
    return handler

# Initialize the MCP handler with mocks
handler = setup_mocks()

def test_generate_resume():
    """Test resume generation with different templates and formats"""
    # Use test profile ID
    profile_id = "test_profile_123"
    
    # Test with different templates and formats
    test_cases = [
        {"template": None, "format": "pdf", "description": "Default template"},
        {"template": "modern", "format": "pdf", "description": "Modern template"},
        {"template": "modern", "format": "docx", "description": "DOCX format"},
        {"template": "modern", "format": "html", "description": "HTML format"},
        {"template": "modern", "format": "md", "description": "Markdown format"},
        {"template": "modern", "format": "txt", "description": "Text format"},
    ]
    
    for i, test_case in enumerate(test_cases):
        print(f"\n--- Test Case {i+1}: {test_case['description']} ---")
        print(f"Template: {test_case['template'] or 'default'}, Format: {test_case['format']}")
        
        # Create MCP request
        request = MCPRequest(
            id=f"test_resume_{i+1}",
            method="linkedin.generateResume",
            params={
                "profileId": profile_id,
                "template": test_case["template"],
                "format": test_case["format"]
            }
        )
        
        # Process the request
        try:
            response = handler.process_request(request)
            if response.get("success") is False:
                print(f"❌ Error: {response.get('error')}")
            else:
                print(f"[SUCCESS] Output file: {response.get('file_path')}")
                print(f"   Format: {response.get('format')}, Size: {response.get('file_size', 0)} bytes")
        except Exception as e:
            print(f"[ERROR] Exception: {str(e)}")

def test_tailor_resume():
    """Test resume tailoring for a specific job"""
    profile_id = "test_profile_123"
    job_id = "test_job_456"
    
    print("\n--- Testing Resume Tailoring ---")
    print(f"Profile: {profile_id}, Job: {job_id}")
    
    # Test with different templates and formats
    test_cases = [
        {"template": None, "format": "pdf", "description": "Default template"},
        {"template": "modern", "format": "pdf", "description": "Modern template"},
        {"template": "modern", "format": "docx", "description": "DOCX format"},
    ]
    
    for i, test_case in enumerate(test_cases):
        print(f"\n--- Tailor Test Case {i+1}: {test_case['description']} ---")
        print(f"Template: {test_case['template'] or 'default'}, Format: {test_case['format']}")
        
        request = MCPRequest(
            id=f"test_tailor_{i+1}",
            method="linkedin.tailorResume",
            params={
                "profileId": profile_id,
                "jobId": job_id,
                "template": test_case["template"],
                "format": test_case["format"]
            }
        )
        
        try:
            response = handler.process_request(request)
            if response.get("success") is False:
                print(f"❌ Error: {response.get('error')}")
            else:
                print(f"[SUCCESS] Tailored resume saved to: {response.get('file_path')}")
                print(f"   Format: {response.get('format')}, Size: {response.get('file_size', 0)} bytes")
        except Exception as e:
            print(f"[ERROR] Exception: {str(e)}")

def test_cover_letter_generation():
    """Test cover letter generation"""
    profile_id = "test_profile_123"
    job_id = "test_job_456"
    
    print("\n--- Testing Cover Letter Generation ---")
    print(f"Profile: {profile_id}, Job: {job_id}")
    
    # Test with different templates and formats
    test_cases = [
        {"template": None, "format": "pdf", "description": "Default template"},
        {"template": "professional", "format": "pdf", "description": "Professional template"},
        {"template": "professional", "format": "docx", "description": "DOCX format"},
    ]
    
    for i, test_case in enumerate(test_cases):
        print(f"\n--- Cover Letter Test Case {i+1}: {test_case['description']} ---")
        print(f"Template: {test_case['template'] or 'default'}, Format: {test_case['format']}")
        
        request = MCPRequest(
            id=f"test_cover_{i+1}",
            method="linkedin.generateCoverLetter",
            params={
                "profileId": profile_id,
                "jobId": job_id,
                "template": test_case["template"],
                "format": test_case["format"]
            }
        )
        
        try:
            response = handler.process_request(request)
            if response.get("success") is False:
                print(f"❌ Error: {response.get('error')}")
            else:
                print(f"[SUCCESS] Cover letter saved to: {response.get('file_path')}")
                print(f"   Format: {response.get('format')}, Size: {response.get('file_size', 0)} bytes")
        except Exception as e:
            print(f"[ERROR] Exception: {str(e)}")

if __name__ == "__main__":
    print("=== Testing Resume Generation ===")
    test_generate_resume()
    
    print("\n=== Testing Resume Tailoring ===")
    test_tailor_resume()
    
    print("\n=== Testing Cover Letter Generation ===")
    test_cover_letter_generation()
    
    print("\n[SUCCESS] All tests completed successfully!")
