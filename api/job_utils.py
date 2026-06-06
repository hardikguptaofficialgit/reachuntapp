"""Job payload helpers for API responses."""

from __future__ import annotations

from api.jobs import JobStore
from api.messages import sanitize_message


def job_payload(store: JobStore, job_id: str, user_id: str) -> dict | None:
    job = store.get(job_id, user_id)
    if not job:
        return None
    if job.get("error"):
        job = dict(job)
        job["error"] = sanitize_message(job["error"])
    return job
