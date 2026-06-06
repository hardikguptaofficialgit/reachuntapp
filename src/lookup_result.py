"""Shared lookup result model for the web API."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

JobStatus = Literal["queued", "running", "completed", "failed"]


@dataclass
class LookupResult:
    status: JobStatus
    query: str
    name: str = ""
    domain: str = ""
    founder_name: str = ""
    linkedin_url: str = ""
    email: str = ""
    email_status: str = ""
    email_confidence: int = 0
    email_validation: dict = field(default_factory=dict)
    message: str = ""
    steps: list[str] = field(default_factory=list)
