"""Tests for ApplicationTrackerService."""

import pytest

from linkedin_mcp.models.tracking import TrackedApplication
from linkedin_mcp.services.application_tracker import ApplicationTrackerService


@pytest.fixture
def tracker(tmp_data_dir):
    return ApplicationTrackerService(tmp_data_dir)


@pytest.fixture
def sample_app():
    return TrackedApplication(
        job_id="job123",
        job_title="Software Engineer",
        company="Test Corp",
        status="applied",
        notes="Applied via website",
    )


@pytest.mark.asyncio
async def test_track_and_get(tracker, sample_app):
    result = await tracker.track_application(sample_app)
    assert result.job_id == "job123"
    assert result.status == "applied"

    fetched = await tracker.get_application("job123")
    assert fetched is not None
    assert fetched.job_title == "Software Engineer"


@pytest.mark.asyncio
async def test_list_applications(tracker, sample_app):
    await tracker.track_application(sample_app)
    apps = await tracker.list_applications()
    assert len(apps) == 1


@pytest.mark.asyncio
async def test_list_filtered_by_status(tracker):
    app1 = TrackedApplication(job_id="j1", job_title="Dev", company="A", status="applied")
    app2 = TrackedApplication(job_id="j2", job_title="PM", company="B", status="interested")
    await tracker.track_application(app1)
    await tracker.track_application(app2)

    applied = await tracker.list_applications("applied")
    assert len(applied) == 1
    assert applied[0].job_id == "j1"


@pytest.mark.asyncio
async def test_update_status(tracker, sample_app):
    await tracker.track_application(sample_app)
    updated = await tracker.update_status("job123", "interviewing", "Phone screen scheduled")
    assert updated.status == "interviewing"
    assert "Phone screen" in updated.notes


@pytest.mark.asyncio
async def test_delete_application(tracker, sample_app):
    await tracker.track_application(sample_app)
    await tracker.delete_application("job123")
    result = await tracker.get_application("job123")
    assert result is None


@pytest.mark.asyncio
async def test_get_missing_returns_none(tracker):
    result = await tracker.get_application("nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_update_nonexistent_raises(tracker):
    with pytest.raises(ValueError, match="No tracked application"):
        await tracker.update_status("nonexistent", "applied")


@pytest.mark.asyncio
async def test_delete_returns_boolean(tracker, sample_app):
    await tracker.track_application(sample_app)
    assert await tracker.delete_application("job123") is True
    assert await tracker.delete_application("job123") is False


def test_invalid_status_raises():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        TrackedApplication(job_id="j1", job_title="Dev", company="A", status="invalid")
