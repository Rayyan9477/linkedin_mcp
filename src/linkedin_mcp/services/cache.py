"""Unified JSON file-based cache with TTL.

Replaces scattered per-service caching and pickle files.
"""

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger("linkedin-mcp.cache")


class JSONCache:
    """Simple JSON file-based cache with TTL support."""

    def __init__(self, cache_dir: Path, ttl_hours: int = 24):
        self._cache_dir = cache_dir
        self._ttl_seconds = ttl_hours * 3600

    @staticmethod
    def _sanitize(value: str) -> str:
        """Sanitize a string for use as a filesystem path component."""
        import re
        return re.sub(r'[^\w\-]', '_', value)[:200]

    def _get_path(self, namespace: str, key: str) -> Path:
        safe_ns = self._sanitize(namespace)
        safe_key = self._sanitize(key)
        ns_dir = self._cache_dir / safe_ns
        ns_dir.mkdir(parents=True, exist_ok=True)
        result = ns_dir / f"{safe_key}.json"
        # Verify the path stays within the cache directory
        if not result.resolve().is_relative_to(self._cache_dir.resolve()):
            raise ValueError(f"Invalid cache path: namespace={namespace}, key={key}")
        return result

    async def get(self, namespace: str, key: str) -> dict[str, Any] | None:
        """Get cached item. Returns None if missing or expired."""
        path = self._get_path(namespace, key)

        def _read() -> dict[str, Any] | None:
            if not path.exists():
                return None
            try:
                with open(path, "r", encoding="utf-8") as f:
                    cached = json.load(f)
                cached_at = cached.get("_cached_at", 0)
                if time.time() - cached_at > self._ttl_seconds:
                    path.unlink(missing_ok=True)
                    return None
                return cached.get("data")
            except (json.JSONDecodeError, KeyError):
                path.unlink(missing_ok=True)
                return None

        return await asyncio.to_thread(_read)

    async def set(self, namespace: str, key: str, data: dict[str, Any]) -> None:
        """Store item in cache."""
        path = self._get_path(namespace, key)

        def _write() -> None:
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"_cached_at": time.time(), "data": data}, f, indent=2, default=str)

        await asyncio.to_thread(_write)
        logger.debug(f"Cached {namespace}/{key}")

    async def delete(self, namespace: str, key: str) -> None:
        """Remove cached item."""
        path = self._get_path(namespace, key)
        if path.exists():
            await asyncio.to_thread(path.unlink)

    async def clear(self, namespace: str | None = None) -> None:
        """Clear cache, optionally for a specific namespace."""
        if namespace:
            ns_dir = self._cache_dir / namespace
            if ns_dir.exists():
                for f in ns_dir.glob("*.json"):
                    f.unlink()
        else:
            for ns_dir in self._cache_dir.iterdir():
                if ns_dir.is_dir():
                    for f in ns_dir.glob("*.json"):
                        f.unlink()
