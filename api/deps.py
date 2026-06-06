"""FastAPI dependencies and shared app paths."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import Request

from api.db import Database
from api.jobs import JobStore
from api.linkedin_session import LinkedInSessionManager
from api.lookup_service import WebLookupService

ROOT = Path(__file__).resolve().parent.parent
WEB_DIST = ROOT / "web" / "dist"


def cors_origins() -> list[str]:
    raw = os.environ.get("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    return [o.strip() for o in raw.split(",") if o.strip()]


def get_db(request: Request) -> Database:
    return request.app.state.db


def get_store(request: Request) -> JobStore:
    return request.app.state.job_store


def get_linkedin(request: Request) -> LinkedInSessionManager:
    return request.app.state.linkedin


def get_lookup_service(request: Request) -> WebLookupService:
    return request.app.state.lookup_service
