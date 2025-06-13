# LinkedIn Model Context Protocol (MCP) Server

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A powerful Model Context Protocol server for LinkedIn interactions that enables AI assistants to search for jobs, generate resumes and cover letters, and manage job applications programmatically.

## Features

- **Authentication**: Secure OAuth 2.0 authentication with token refresh
- **Profile Management**: Access and update LinkedIn profile information
- **Job Search**: Advanced job search with filtering and pagination
- **Resume & Cover Letters**: Generate tailored resumes and cover letters
- **Messaging**: Send messages and connection requests
- **Analytics**: Track job applications and engagement metrics
- **Async API**: Built with asyncio for high performance
- **Modular Design**: Clean, maintainable code with separation of concerns

## Architecture

This project implements the [Model Context Protocol (MCP)](https://github.com/anthropics/model-context-protocol-spec) specification, allowing AI assistants to interact with LinkedIn through standardized JSON-RPC style requests and responses.

### Project Structure

```
linkedin_mcp/
├── api/
│   ├── clients/         # API client implementations
│   │   ├── __init__.py   # Client factory functions
│   │   ├── linkedin.py   # LinkedIn API client
│   │   └── openai.py     # OpenAI integration
│   │
│   ├── models/          # Data models and schemas
│   │   ├── __init__.py   # Model exports
│   │   ├── common.py     # Common data models
│   │   ├── enums.py      # Enumerations
│   │   ├── requests.py   # Request models
│   │   └── responses.py  # Response models
│   │
│   └── services/        # Business logic
│       └── ...
│
├── core/                # Core application logic
│   ├── __init__.py
│   ├── exceptions.py    # Custom exceptions
│   ├── mcp_handler.py   # MCP protocol handler
│   └── protocol.py      # Protocol definitions
│
├── utils/              # Utility functions
│   ├── __init__.py
│   ├── auth.py          # Authentication helpers
│   ├── rate_limiter.py  # Rate limiting
│   └── retry.py         # Retry mechanisms
│
├── examples/           # Example scripts
│   └── basic_usage.py   # Basic client usage example
│
├── .env.example       # Example environment variables
├── README.md           # This file
└── requirements.txt    # Project dependencies
```

## Getting Started

### Prerequisites

- Python 3.8+
- LinkedIn Developer Account
- OAuth 2.0 credentials from [LinkedIn Developers](https://www.linkedin.com/developers/)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/linkedin-mcp.git
   cd linkedin-mcp
   ```

2. **Create and activate a virtual environment**
   ```bash
   # Linux/macOS
   python -m venv venv
   source venv/bin/activate
   
   # Windows
   python -m venv venv
   .\venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   ```
   Edit the `.env` file with your LinkedIn API credentials and other settings.

## Configuration

Create a `.env` file in the project root with the following variables (see `.env.example` for details):

```env
# LinkedIn API Credentials (required)
LINKEDIN_CLIENT_ID=your_client_id_here
LINKEDIN_CLIENT_SECRET=your_client_secret_here
LINKEDIN_REDIRECT_URI=http://localhost:8080/callback

# Optional: OpenAI API Key (for resume/cover letter generation)
# OPENAI_API_KEY=your_openai_api_key_here

# Optional: Logging
LOG_LEVEL=INFO

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