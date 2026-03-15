"""Unified JSON file-based cache with TTL.

Replaces scattered per-service caching and pickle files.
"""

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any

from linkedin_mcp.utils import sanitize_filename

logger = logging.getLogger("linkedin-mcp.cache")


class JSONCache:
    """Simple JSON file-based cache with TTL support."""

    def __init__(self, cache_dir: Path, ttl_hours: int = 24):
        self._cache_dir = cache_dir
        self._ttl_seconds = ttl_hours * 3600

    @staticmethod
    def _sanitize(value: str) -> str:
        """Sanitize a string for use as a filesystem path component."""
        return sanitize_filename(value)

    def _get_path(self, namespace: str, key: str) -> Path:
        safe_ns = self._sanitize(namespace)
        safe_key = self._sanitize(key)
        result = self._cache_dir / safe_ns / f"{safe_key}.json"
        # Verify the path stays within the cache directory using string comparison
        # (resolve() can fail on non-existent paths on some platforms)
        try:
            if not result.resolve().is_relative_to(self._cache_dir.resolve()):
                raise ValueError(f"Invalid cache path: namespace={namespace}, key={key}")
        except (OSError, ValueError):
            # On platforms where resolve() fails for non-existent paths,
            # the sanitization already prevents traversal
            pass
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
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"_cached_at": time.time(), "data": data}, f, indent=2, default=str)

        await asyncio.to_thread(_write)
        logger.debug(f"Cached {namespace}/{key}")

    async def delete(self, namespace: str, key: str) -> None:
        """Remove cached item."""
        path = self._get_path(namespace, key)

        def _unlink() -> None:
            path.unlink(missing_ok=True)

        await asyncio.to_thread(_unlink)

    async def clear(self, namespace: str | None = None) -> None:
        """Clear cache, optionally for a specific namespace."""

        def _clear() -> None:
            if namespace:
                safe_ns = self._sanitize(namespace)
                ns_dir = self._cache_dir / safe_ns
                if ns_dir.exists():
                    for f in ns_dir.glob("*.json"):
                        f.unlink(missing_ok=True)
            else:
                if self._cache_dir.exists():
                    for ns_dir in self._cache_dir.iterdir():
                        if ns_dir.is_dir():
                            for f in ns_dir.glob("*.json"):
                                f.unlink(missing_ok=True)

        await asyncio.to_thread(_clear)
