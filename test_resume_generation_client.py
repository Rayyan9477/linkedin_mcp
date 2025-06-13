"""
Test client for resume generation
"""
import json
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from linkedin_mcp.core.protocol import MCPRequest
from linkedin_mcp.utils.config import get_config

class TestClient:
    def __init__(self, server):
        self.server = server
    
    def send_request(self, method: str, params: dict) -> dict:
        """Send a request to the server"""
        request = MCPRequest(
            id=f"test_{method}_{hash(frozenset(params.items()))}",
            method=method,
            params=params
        )
        
        # In a real scenario, this would be sent over a network connection
        # For testing, we'll directly call the server's handle_request method
        response = self.server.handle_request(request.model_dump_json())
        return json.loads(response)

def login(server):
    """Login to LinkedIn"""
    config = get_config()
    username = config.get('linkedin', {}).get('username')
    password = config.get('linkedin', {}).get('password')
    
    if not username or not password:
        print("Error: LinkedIn credentials not found in config.json")
        print("Please update config.json with your LinkedIn credentials")
        sys.exit(1)
    
    print("Logging in to LinkedIn...")
    response = server.handler.auth.login(username, password)
    if not response.get('success'):
        print(f"Login failed: {response.get('error')}")
        sys.exit(1)
    
    print("Successfully logged in to LinkedIn")

def main():
    from server import LinkedInMCPServer
    
    # Initialize the server
    server = LinkedInMCPServer()
    client = TestClient(server)
    
    # Login to LinkedIn
    login(server)
    
    # Test data
    test_profile_id = "test_profile_123"
    test_job_id = "test_job_456"
    
    print("=== Testing Resume Generation ===")
    
    # Test 1: Generate resume with default template and format
    print("\n--- Test 1: Default template and format ---")
    response = client.send_request(
        "linkedin.generateResume",
        {"profileId": test_profile_id}
    )
    print_response(response)
    
    # Test 2: Generate resume with modern template and PDF format
    print("\n--- Test 2: Modern template, PDF format ---")
    response = client.send_request(
        "linkedin.generateResume",
        {
            "profileId": test_profile_id,
            "template": "modern",
            "format": "pdf"
        }
    )
    print_response(response)
    
    # Test 3: Tailor resume for a job
    print("\n--- Test 3: Tailor resume for a job ---")
    response = client.send_request(
        "linkedin.tailorResume",
        {
            "profileId": test_profile_id,
            "jobId": test_job_id,
            "template": "modern",
            "format": "pdf"
        }
    )
    print_response(response)
    
    # Test 4: Generate cover letter
    print("\n--- Test 4: Generate cover letter ---")
    response = client.send_request(
        "linkedin.generateCoverLetter",
        {
            "profileId": test_profile_id,
            "jobId": test_job_id,
            "template": "professional",
            "format": "pdf"
        }
    )
    print_response(response)

def print_response(response: dict):
    """Print the response in a readable format"""
    if response.get("success", False):
        print("[SUCCESS]")
        for key, value in response.items():
            if key != "success":
                print(f"  {key}: {value}")
    else:
        print("[ERROR]")
        print(f"  {response.get('error', 'Unknown error')}")

if __name__ == "__main__":
    main()
