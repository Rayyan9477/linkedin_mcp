"""Shared utility functions for LinkedIn MCP server."""

import re


def sanitize_filename(value: str, max_length: int = 200) -> str:
    """Sanitize a string for use as a filesystem path component."""
    return re.sub(r'[^\w\-]', '_', value)[:max_length]
