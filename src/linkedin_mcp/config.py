"""Configuration management for LinkedIn MCP server.

Loads settings from .env file and environment variables. No plaintext config files.
"""

import logging
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
import os


@dataclass(frozen=True)
class Settings:
    """Immutable application settings loaded from environment variables."""

    linkedin_username: str = ""
    linkedin_password: str = ""
    anthropic_api_key: str = ""
    ai_model: str = "claude-sonnet-4-20250514"
    data_dir: Path = field(default_factory=lambda: Path.home() / ".linkedin_mcp" / "data")
    cache_ttl_hours: int = 24
    log_level: str = "INFO"

    def validate(self) -> list[str]:
        """Return list of missing required settings."""
        errors = []
        if not self.linkedin_username:
            errors.append("LINKEDIN_USERNAME is required")
        if not self.linkedin_password:
            errors.append("LINKEDIN_PASSWORD is required")
        return errors

    @property
    def has_ai(self) -> bool:
        """Whether AI generation is available."""
        return bool(self.anthropic_api_key)

    def __repr__(self) -> str:
        """Redact credentials in repr output."""
        return (
            f"Settings(linkedin_username={self.linkedin_username!r}, "
            f"linkedin_password='***', "
            f"anthropic_api_key='***', "
            f"ai_model={self.ai_model!r}, "
            f"data_dir={self.data_dir!r}, "
            f"cache_ttl_hours={self.cache_ttl_hours!r}, "
            f"log_level={self.log_level!r})"
        )


def _parse_int(value: str, default: int) -> int:
    """Safely parse an integer from env var, returning default on failure."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Load settings from environment variables. Cached after first call."""
    load_dotenv()
    settings = Settings(
        linkedin_username=os.getenv("LINKEDIN_USERNAME", ""),
        linkedin_password=os.getenv("LINKEDIN_PASSWORD", ""),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
        ai_model=os.getenv("AI_MODEL", "claude-sonnet-4-20250514"),
        data_dir=Path(os.getenv("DATA_DIR", str(Path.home() / ".linkedin_mcp" / "data"))),
        cache_ttl_hours=_parse_int(os.getenv("CACHE_TTL_HOURS", "24"), 24),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )

    # Ensure data directory exists
    settings.data_dir.mkdir(parents=True, exist_ok=True)

    return settings
