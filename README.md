# LinkedIn Model Context Protocol (MCP) Server

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

A powerful Model Context Protocol server for LinkedIn interactions that enables AI assistants to search for jobs, generate resumes and cover letters, and manage job applications programmatically.

## Features

- **Authentication**: Secure LinkedIn authentication with session management
- **Profile Management**: Access and update LinkedIn profile information
- **Job Search**: Search for jobs with flexible filtering options
- **Resume Generation**: Create customized resumes from LinkedIn profiles
- **Cover Letter Generation**: Generate tailored cover letters for specific job applications
- **Job Applications**: Submit and track job applications

## Architecture

This project implements the [Model Context Protocol (MCP)](https://github.com/anthropics/model-context-protocol-spec) specification, allowing AI assistants to interact with LinkedIn through standardized JSON-RPC style requests and responses.

### Components:

- **MCP Handler**: Routes requests to appropriate service handlers
- **API Modules**: Specialized modules for LinkedIn interactions (auth, job search, profile, etc.)
- **Core Protocol**: Defines request/response structures and data models
- **Utilities**: Configuration management and helper functions

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/linkedin-mcp.git
cd linkedin-mcp

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Configuration

Create a `.env` file in the project root with the following variables:

```
# LinkedIn Credentials
LINKEDIN_USERNAME=your_email@example.com
LINKEDIN_PASSWORD=your_password

# API Settings
OPENAI_API_KEY=your_openai_api_key
SESSION_DIR=sessions
DATA_DIR=data
```

## Usage

### Starting the Server

```bash
python server.py
```

### Example MCP Requests

#### Authentication

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "linkedin.login",
  "params": {
    "username": "user@example.com",
    "password": "password123"
  }
}
```

#### Searching for Jobs

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "linkedin.searchJobs",
  "params": {
    "filter": {
      "keywords": "software engineer",
      "location": "New York, NY",
      "distance": 25
    },
    "page": 1,
    "count": 20
  }
}
```

#### Generating a Resume

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "linkedin.generateResume",
  "params": {
    "profileId": "user123",
    "template": "standard",
    "format": "pdf"
  }
}
```

## Available Methods

| Method | Description |
|--------|-------------|
| `linkedin.login` | Authenticate with LinkedIn |
| `linkedin.logout` | End the current session |
| `linkedin.checkSession` | Check if the current session is valid |
| `linkedin.getFeed` | Get LinkedIn feed posts |
| `linkedin.getProfile` | Get LinkedIn profile information |
| `linkedin.getCompany` | Get company profile information |
| `linkedin.searchJobs` | Search for jobs with filters |
| `linkedin.getJobDetails` | Get detailed information about a job |
| `linkedin.getRecommendedJobs` | Get job recommendations |
| `linkedin.generateResume` | Generate a resume from a LinkedIn profile |
| `linkedin.generateCoverLetter` | Generate a cover letter for a job application |
| `linkedin.tailorResume` | Customize a resume for a specific job |
| `linkedin.applyToJob` | Apply to a job |
| `linkedin.getApplicationStatus` | Check application status |
| `linkedin.getSavedJobs` | Get saved jobs |
| `linkedin.saveJob` | Save a job for later |

## Development

### Project Structure

```
linkedin-mcp/
├── README.md
├── requirements.txt
├── server.py
├── data/
│   ├── applications/
│   ├── companies/
│   ├── cover_letters/
│   ├── jobs/
│   ├── profiles/
│   └── resumes/
├── linkedin_mcp/
│   ├── api/
│   │   ├── auth.py
│   │   ├── cover_letter_generator.py
│   │   ├── job_application.py
│   │   ├── job_search.py
│   │   ├── profile.py
│   │   └── resume_generator.py
│   ├── core/
│   │   ├── mcp_handler.py
│   │   └── protocol.py
│   └── utils/
│       └── config.py
├── sessions/
└── templates/
    ├── cover_letter/
    │   └── standard.html
    └── resume/
        └── standard.html
```

### Running Tests

```bash
pytest
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- LinkedIn API documentation
- Model Context Protocol specification