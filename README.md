# LinkedIn MCP Server

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![MCP SDK](https://img.shields.io/badge/MCP-FastMCP-6B4FBB.svg)](https://modelcontextprotocol.io/)

An MCP server that gives AI assistants full access to LinkedIn — search jobs, view profiles and companies, generate AI-powered resumes and cover letters, and track applications. Built with the [official MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) (FastMCP).

---

## What It Does

| Category | Capabilities |
|---|---|
| **Job Search** | Search with filters (keywords, location, type, experience level, remote, recency), get job details, get recommendations |
| **Profiles & Companies** | Fetch any LinkedIn profile or company page, AI-powered profile analysis with optimization suggestions |
| **Resume Generation** | Generate resumes from LinkedIn profiles, tailor resumes to specific job postings, 3 built-in templates |
| **Cover Letters** | AI-generated cover letters personalized to each job, 2 built-in templates |
| **Application Tracking** | Track applications locally with status workflow (interested → applied → interviewing → offered/rejected/withdrawn) |
| **Output Formats** | HTML, Markdown, and PDF (via WeasyPrint) |

---

## Quick Start

### 1. Install

```bash
# Core installation
pip install -e .

# With AI features (resume/cover letter generation, profile analysis)
pip install -e ".[ai]"

# With PDF export
pip install -e ".[pdf]"

# Everything
pip install -e ".[all]"
```

### 2. Configure

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
LINKEDIN_USERNAME=your_email@example.com
LINKEDIN_PASSWORD=your_password
ANTHROPIC_API_KEY=sk-ant-...    # Optional — enables AI features
```

### 3. Run

**Standalone:**

```bash
linkedin-mcp
```

**With Claude Desktop** — add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "linkedin": {
      "command": "linkedin-mcp"
    }
  }
}
```

**With Claude Code** — add to `.mcp.json`:

```json
{
  "linkedin": {
    "command": "linkedin-mcp"
  }
}
```

---

## Tools Reference

### Job Tools (3)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `search_jobs` | `keywords`, `location`, `job_type`, `experience_level`, `remote`, `date_posted`, `page`, `count` | Search LinkedIn jobs with rich filters |
| `get_job_details` | `job_id` | Get full description, skills, and metadata for a job posting |
| `get_recommended_jobs` | `count` | Get personalized job recommendations |

### Profile Tools (3)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `get_profile` | `profile_id` | Fetch a LinkedIn profile (`"me"` for your own) — experience, education, skills |
| `get_company` | `company_id` | Get company info — description, size, headquarters, specialties |
| `analyze_profile` | `profile_id` | AI-powered profile review with actionable optimization suggestions |

### Document Generation Tools (4)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `generate_resume` | `profile_id`, `template`, `output_format` | Generate a resume from a LinkedIn profile |
| `tailor_resume` | `profile_id`, `job_id`, `template`, `output_format` | Generate a resume tailored to a specific job posting |
| `generate_cover_letter` | `profile_id`, `job_id`, `template`, `output_format` | Create a personalized cover letter for a job |
| `list_templates` | `template_type` | List available templates (`resume`, `cover_letter`, or `all`) |

**Templates:** `modern` · `professional` · `minimal` (resume) | `professional` · `concise` (cover letter)
**Formats:** `html` · `md` · `pdf`

### Application Tracking Tools (3)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `track_application` | `job_id`, `job_title`, `company`, `status`, `notes`, `url` | Start tracking a job application |
| `list_applications` | `status` | List all tracked applications, optionally filtered by status |
| `update_application_status` | `job_id`, `status`, `notes` | Update application status |

**Status values:** `interested` · `applied` · `interviewing` · `offered` · `rejected` · `withdrawn`

---

## Architecture

```
src/linkedin_mcp/
├── server.py                    # FastMCP entry point — 13 tools, 1 resource
├── config.py                    # Settings from .env (frozen dataclass)
├── exceptions.py                # 7-class exception hierarchy
├── models/
│   ├── linkedin.py              # Profile, Job, Company models (Pydantic v2)
│   ├── resume.py                # Resume & cover letter content models
│   └── tracking.py              # Application tracking model
├── services/
│   ├── linkedin_client.py       # LinkedIn API wrapper (async via asyncio.to_thread)
│   ├── job_search.py            # Job search with TTL caching
│   ├── profile.py               # Profile/company access with caching
│   ├── resume_generator.py      # AI-enhanced resume generation
│   ├── cover_letter_generator.py
│   ├── application_tracker.py   # Local JSON-based application tracking
│   ├── cache.py                 # Unified JSON file cache with TTL
│   ├── template_manager.py      # Jinja2 sandboxed template engine
│   └── format_converter.py      # HTML → PDF/Markdown conversion
├── ai/
│   ├── base.py                  # Abstract AI provider interface
│   └── claude_provider.py       # Anthropic Claude implementation
└── templates/
    ├── resume/                  # modern.j2, professional.j2, minimal.j2
    └── cover_letter/            # professional.j2, concise.j2
```

### Key Design Decisions

- **Official MCP SDK** — Uses `FastMCP` with `@mcp.tool()` decorators, not a custom protocol implementation
- **Async throughout** — All sync LinkedIn API calls wrapped in `asyncio.to_thread()` to avoid blocking
- **Layered architecture** — Tools → Services → Client, with caching at the service layer
- **AI is optional** — Core LinkedIn features work without an Anthropic API key; AI enhances resume/cover letter generation
- **Security hardened** — Jinja2 `SandboxedEnvironment`, WeasyPrint SSRF protection, path traversal guards, credential redaction, input validation

---

## Configuration

All settings are loaded from environment variables (`.env` file supported):

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LINKEDIN_USERNAME` | Yes | — | Your LinkedIn email |
| `LINKEDIN_PASSWORD` | Yes | — | Your LinkedIn password |
| `ANTHROPIC_API_KEY` | No | — | Enables AI features (resume/cover letter generation, profile analysis) |
| `AI_MODEL` | No | `claude-sonnet-4-20250514` | Claude model to use |
| `DATA_DIR` | No | `~/.linkedin_mcp/data` | Directory for cache, tracking data, generated files |
| `CACHE_TTL_HOURS` | No | `24` | How long to cache LinkedIn API responses |
| `LOG_LEVEL` | No | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |

---

## Development

```bash
# Install with all dependencies
pip install -e ".[all,dev]"

# Run tests (82 tests)
pytest

# Run with coverage
pytest --cov=linkedin_mcp

# Lint
ruff check src/ tests/
```

### Test Coverage

Tests cover all layers: config, models, services (cache, tracker, job search, profile, resume/cover letter generation, LinkedIn client formatters, format converter), AI provider, and MCP tool handlers.

---

## Usage Examples

Once connected, ask your AI assistant:

> "Search for remote Python developer jobs in the US"

> "Show me the profile for satyanadella"

> "Generate a resume from my LinkedIn profile tailored to job 3847291056"

> "Create a cover letter for job 3847291056 using the concise template"

> "Track my application for the Senior Engineer role at Google — status: applied"

> "List all my applications that are in the interviewing stage"

> "Analyze my LinkedIn profile and suggest improvements"

---

## License

MIT
