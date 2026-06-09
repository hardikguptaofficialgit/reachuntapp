import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from api.auth import get_current_user
from api.config import (
    BULK_MAX_QUERIES,
    JOB_STATUS_BATCH_MAX,
    JOB_WORKER_COUNT,
    LOOKUP_DAILY_LIMIT,
    QUEUE_MAX_PER_USER,
    WEB_LINKEDIN_CLIENT_MODE,
)
from api.db import Database
from api.deps import get_db, get_linkedin, get_store
from api.job_utils import job_payload
from api.jobs import JobStore, QueueFullError
from api.rate_limit import lookup_limiter
from api.linkedin_session import LinkedInSessionManager
from api.messages import sanitize_message
from api.schemas import (
    BulkLookupRequest,
    BulkLookupResponse,
    JobStatusRequest,
    LookupRequest,
    LookupResponse,
)
from src.query_parse import parse_person_query

router = APIRouter(tags=["lookups"])


def _lookup_quota(db: Database, user: dict) -> dict[str, int | bool]:
    if user.get("is_dev") or LOOKUP_DAILY_LIMIT == 0:
        return {"limit": LOOKUP_DAILY_LIMIT, "used": 0, "remaining": 999_999, "unlimited": True}
    used = db.count_lookup_jobs_today(user["id"])
    remaining = max(0, LOOKUP_DAILY_LIMIT - used)
    return {
        "limit": LOOKUP_DAILY_LIMIT,
        "used": used,
        "remaining": remaining,
        "unlimited": False,
    }


def _require_lookup_quota(db: Database, user: dict, requested: int = 1) -> dict[str, int | bool]:
    quota = _lookup_quota(db, user)
    if not quota["unlimited"] and int(quota["remaining"]) < requested:
        raise HTTPException(
            status_code=429,
            detail=(
                f"Daily lookup limit reached ({quota['used']}/{quota['limit']}). "
                "Try again tomorrow."
            ),
        )
    return quota


@router.get("/api/v1/config/limits")
async def config_limits(
    user: dict = Depends(get_current_user),
    store: JobStore = Depends(get_store),
    db: Database = Depends(get_db),
):
    quota = _lookup_quota(db, user)
    return {
        "bulk_max_queries": BULK_MAX_QUERIES,
        "queue_max_per_user": QUEUE_MAX_PER_USER,
        "job_status_batch_max": JOB_STATUS_BATCH_MAX,
        "job_worker_count": JOB_WORKER_COUNT,
        "lookup_daily_limit": quota["limit"],
        "lookup_daily_used": quota["used"],
        "lookup_daily_remaining": quota["remaining"],
        "lookup_daily_unlimited": quota["unlimited"],
        "queue": store.stats(user["id"]),
    }


@router.get("/api/v1/queue/stats")
async def queue_stats(
    user: dict = Depends(get_current_user),
    store: JobStore = Depends(get_store),
):
    return store.stats(user["id"])


@router.post("/api/v1/lookup/bulk", response_model=BulkLookupResponse)
async def create_bulk_lookup(
    body: BulkLookupRequest,
    user: dict = Depends(get_current_user),
    store: JobStore = Depends(get_store),
    db: Database = Depends(get_db),
    linkedin: LinkedInSessionManager = Depends(get_linkedin),
):
    await lookup_limiter.check(user["id"], label="lookups")
    if not user.get("is_dev") and not WEB_LINKEDIN_CLIENT_MODE:
        if not await linkedin.is_connected(user["id"]):
            raise HTTPException(
                status_code=403,
                detail="Discovery is getting ready. Try again in a moment.",
            )

    cleaned = []
    for raw in body.queries:
        try:
            pq = parse_person_query(raw.strip())
            cleaned.append(f"{pq.name} — {pq.domain}" if pq.name else pq.domain)
        except ValueError:
            continue
    if not cleaned:
        raise HTTPException(status_code=400, detail="No valid queries in batch.")

    quota = _require_lookup_quota(db, user)
    allowed_by_quota = int(quota["remaining"]) if not quota["unlimited"] else BULK_MAX_QUERIES
    batch = cleaned[: min(BULK_MAX_QUERIES, allowed_by_quota)]
    try:
        job_ids = store.create_bulk(user["id"], batch)
    except QueueFullError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    return BulkLookupResponse(
        job_ids=job_ids,
        queued=len(job_ids),
        requested=len(batch),
    )


@router.post("/api/v1/jobs/status")
async def jobs_status(
    body: JobStatusRequest,
    user: dict = Depends(get_current_user),
    store: JobStore = Depends(get_store),
):
    ids = body.job_ids[:JOB_STATUS_BATCH_MAX]
    jobs = store.list_user_jobs(user["id"], ids)
    return {"jobs": jobs}


@router.post("/api/v1/lookup", response_model=LookupResponse)
async def create_lookup(
    body: LookupRequest,
    user: dict = Depends(get_current_user),
    store: JobStore = Depends(get_store),
    db: Database = Depends(get_db),
    linkedin: LinkedInSessionManager = Depends(get_linkedin),
):
    await lookup_limiter.check(user["id"], label="lookups")
    _require_lookup_quota(db, user)
    if not user.get("is_dev") and not WEB_LINKEDIN_CLIENT_MODE:
        if not await linkedin.is_connected(user["id"]):
            raise HTTPException(
                status_code=403,
                detail="Discovery is getting ready. Try again in a moment.",
            )

    try:
        parse_person_query(body.query.strip())
        job_id = store.create(user["id"], body.query.strip())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=sanitize_message(str(exc))) from exc
    except QueueFullError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    return LookupResponse(job_id=job_id)


@router.get("/api/v1/jobs/{job_id}")
async def get_job(
    job_id: str,
    user: dict = Depends(get_current_user),
    store: JobStore = Depends(get_store),
):
    job = job_payload(store, job_id, user["id"])
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/api/v1/jobs/{job_id}/stream")
async def stream_job(
    job_id: str,
    user: dict = Depends(get_current_user),
    store: JobStore = Depends(get_store),
):
    async def events():
        last_payload = ""
        idle_rounds = 0
        while idle_rounds < 120:
            job = job_payload(store, job_id, user["id"])
            if not job:
                yield f"data: {json.dumps({'error': 'not_found'})}\n\n"
                return
            payload = json.dumps(job, default=str)
            if payload != last_payload:
                yield f"data: {payload}\n\n"
                last_payload = payload
                idle_rounds = 0
            if job.get("status") in ("completed", "failed"):
                return
            await store.wait_for_update(job_id, timeout=2.0)
            idle_rounds += 1

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
