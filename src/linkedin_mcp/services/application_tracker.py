"""Local job application tracking service.

Replaces Selenium-based auto-apply with reliable local tracking.
"""

import asyncio
import json
import logging
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from linkedin_mcp.models.tracking import TrackedApplication
from linkedin_mcp.utils import sanitize_filename

logger = logging.getLogger("linkedin-mcp.tracker")


class ApplicationTrackerService:
    """Tracks job applications locally via JSON files."""

    def __init__(self, data_dir: Path):
        self._dir = data_dir / "applications"
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, job_id: str) -> Path:
        safe_id = sanitize_filename(job_id)
        result = self._dir / f"{safe_id}.json"
        if not result.resolve().is_relative_to(self._dir.resolve()):
            raise ValueError(f"Invalid job ID for path: {job_id}")
        return result

    async def track_application(self, application: TrackedApplication) -> TrackedApplication:
        """Add or update a tracked application."""
        application.updated_at = datetime.now().isoformat()
        path = self._path(application.job_id)

        def _write() -> None:
            # Atomic write: write to temp file then replace
            fd, tmp_path = tempfile.mkstemp(dir=self._dir, suffix=".tmp")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(application.model_dump(), f, indent=2, default=str)
                os.replace(tmp_path, path)
            except BaseException:
                os.unlink(tmp_path)
                raise

        await asyncio.to_thread(_write)
        logger.info(f"Tracked application: {application.job_title} at {application.company}")
        return application

    async def get_application(self, job_id: str) -> TrackedApplication | None:
        """Get tracking info for a specific job."""
        path = self._path(job_id)

        def _read() -> dict[str, Any] | None:
            if not path.exists():
                return None
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)

        data = await asyncio.to_thread(_read)
        return TrackedApplication(**data) if data else None

    async def list_applications(self, status: str | None = None) -> list[TrackedApplication]:
        """List all tracked applications, optionally filtered by status."""

        def _list() -> list[dict[str, Any]]:
            results = []
            for f in sorted(self._dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
                try:
                    with open(f, "r", encoding="utf-8") as fh:
                        results.append(json.load(fh))
                except (json.JSONDecodeError, OSError):
                    continue
            return results

        all_apps = await asyncio.to_thread(_list)
        apps = [TrackedApplication(**data) for data in all_apps]

        if status:
            apps = [a for a in apps if a.status == status]

        return apps

    async def update_status(
        self, job_id: str, status: str, notes: str = ""
    ) -> TrackedApplication:
        """Update the status of a tracked application."""
        app = await self.get_application(job_id)
        if not app:
            raise ValueError(f"No tracked application found for job {job_id}")

        app.status = status
        if notes:
            app.notes = notes
        app.updated_at = datetime.now().isoformat()

        return await self.track_application(app)

    async def delete_application(self, job_id: str) -> bool:
        """Remove a tracked application."""
        path = self._path(job_id)
        if path.exists():
            await asyncio.to_thread(path.unlink)
            return True
        return False
