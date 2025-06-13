"""
Basic usage example for the LinkedIn API client.

This script demonstrates how to use the LinkedIn API client to:
1. Authenticate with OAuth 2.0
2. Fetch the authenticated user's profile
3. Search for jobs
4. Apply to a job
5. Send a connection request
6. Engage with a post

Before running this script, make sure to:
1. Create a LinkedIn Developer application at https://www.linkedin.com/developers/
2. Add the necessary OAuth 2.0 redirect URIs
3. Install the required dependencies:
   pip install aiohttp python-dotenv
"""

import asyncio
import os
from dotenv import load_dotenv

# Import the LinkedIn API client and utilities
from linkedin_mcp.api.clients import create_linkedin_client
from linkedin_mcp.utils.auth import authenticate_interactive

# Load environment variables from .env file
load_dotenv()

# Configuration - replace these with your LinkedIn app credentials
CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")
CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET")
REDIRECT_URI = os.getenv("LINKEDIN_REDIRECT_URI", "http://localhost:8080/callback")

# Scopes define the permissions your app needs
SCOPES = [
    "r_liteprofile",
    "r_emailaddress",
    "w_member_social",
    "rw_organization_admin",
    "w_organization_social",
    "r_organization_social",
    "r_1st_connections_size",
    "r_basicprofile",
]


async def main():
    """Main function to demonstrate LinkedIn API usage."""
    print("LinkedIn API Client Example")
    print("=" * 50)

    try:
        # Step 1: Authenticate with LinkedIn
        print("\nStep 1: Authenticating with LinkedIn...")
        client = await authenticate_interactive(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            redirect_uri=REDIRECT_URI,
            scopes=SCOPES,
            open_browser=True,
        )
        print("✅ Successfully authenticated with LinkedIn!")

        # Step 2: Get the authenticated user's profile
        print("\nStep 2: Fetching your profile...")
        profile_response = await client.get_profile()
        profile = profile_response.profile
        print(f"👤 Logged in as: {profile.first_name} {profile.last_name}")
        print(f"   Headline: {profile.headline}")
        print(f"   Location: {profile.location}")

        # Step 3: Search for jobs
        print("\nStep 3: Searching for jobs...")
        from linkedin_mcp.api.models.requests import JobSearchRequest
        from linkedin_mcp.api.models.enums import JobType, ExperienceLevel
        
        job_search_request = JobSearchRequest(
            keywords="Python Developer",
            location="United States",
            job_type=[JobType.FULL_TIME, JobType.REMOTE],
            experience_level=ExperienceLevel.MID_SENIOR,
        )
        
        jobs_response = await client.search_jobs(job_search_request)
        print(f"🔍 Found {len(jobs_response.jobs)} jobs")
        
        if jobs_response.jobs:
            job = jobs_response.jobs[0]  # Get the first job
            print(f"   First job: {job.title} at {job.company_name} ({job.location})")
            
            # Step 4: Apply to the job (commented out to prevent accidental applications)
            """
            print("\nStep 4: Applying to the job...")
            from linkedin_mcp.api.models.requests import ApplyToJobRequest
            
            # In a real application, you would get the resume ID from the user's uploaded resumes
            apply_request = ApplyToJobRequest(
                job_id=job.job_id,
                resume_id="YOUR_RESUME_ID",  # Replace with actual resume ID
                cover_letter="I'm excited to apply for this position...",
            )
            
            apply_response = await client.apply_to_job(apply_request)
            print(f"✅ Application submitted! Application ID: {apply_response.application_id}")
            """
            print("\n⚠️ Job application step skipped (uncomment the code to enable)")
            
            # Step 5: Send a connection request (commented out to prevent accidental requests)
            """
            print("\nStep 5: Sending a connection request...")
            from linkedin_mcp.api.models.requests import ConnectionRequest
            
            # In a real application, you would get the profile ID from search results
            connection_request = ConnectionRequest(
                profile_id="PROFILE_ID_TO_CONNECT",  # Replace with actual profile ID
                message="Hi, I'd like to connect with you on LinkedIn!",
            )
            
            connection_response = await client.connect(connection_request)
            print(f"✅ Connection request sent! Invitation ID: {connection_response.invitation_id}")
            """
            print("\n⚠️ Connection request step skipped (uncomment the code to enable)")
            
            # Step 6: Engage with a post (commented out to prevent accidental engagement)
            """
            print("\nStep 6: Liking a post...")
            from linkedin_mcp.api.models.requests import PostEngagementRequest
            
            # In a real application, you would get the post URN from the feed
            engagement_request = PostEngagementRequest(
                post_urn="urn:li:activity:POST_ID",  # Replace with actual post URN
                action="like",
            )
            
            engagement_response = await client.engage_with_post(engagement_request)
            print(f"✅ Post liked! Engagement ID: {engagement_response.engagement_id}")
            """
            print("\n⚠️ Post engagement step skipped (uncomment the code to enable)")

    except Exception as e:
        print(f"\n❌ An error occurred: {str(e)}")
    finally:
        # Ensure the client is properly closed
        if 'client' in locals() and hasattr(client, '_session') and client._session:
            await client._session.close()
        print("\n✅ Example completed!")


if __name__ == "__main__":
    asyncio.run(main())
