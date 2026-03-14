"""Job application tracking models."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


VALID_STATUSES = ["interested", "applied", "interviewing", "offered", "rejected", "withdrawn"]

StatusType = Literal["interested", "applied", "interviewing", "offered", "rejected", "withdrawn"]


class TrackedApplication(BaseModel):
    """A tracked job application (stored locally)."""

    model_config = ConfigDict(validate_assignment=True)

    job_id: str
    job_title: str
    company: str
    status: StatusType = "interested"
    applied_date: str | None = None
    notes: str = ""
    url: str = ""
    resume_used: str | None = None
    cover_letter_used: str | None = None
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
