"""Priority job queue for web lookups — workers, persistence, bounded memory."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any

from api.config import (
    BULK_LOOKUP_PRIORITY,
    JOB_MEMORY_MAX,
    JOB_WORKER_COUNT,
    QUEUE_MAX_PER_USER,
    SINGLE_LOOKUP_PRIORITY,
)
from api.db import Database
from api.lookup_service import WebLookupService
from api.messages import public_steps, sanitize_message
from src.lookup_result import LookupResult


class QueueFullError(Exception):
    """Raised when a user exceeds their queued job cap."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _public_result(result: LookupResult) -> dict[str, Any]:
    return {
        "name": result.name,
        "domain": result.domain,
        "display_name": result.founder_name,
        "profile_url": result.linkedin_url,
        "email": result.email,
        "status": result.email_status,
        "confidence": result.email_confidence,
        "validation": result.email_validation,
        "message": sanitize_message(result.message),
        "steps": public_steps(result.steps),
    }


class JobStore:
    def __init__(self, service: WebLookupService, db: Database):
        self.service = service
        self.db = db
        self._jobs: dict[str, dict[str, Any]] = {}
        self._queue: asyncio.PriorityQueue[tuple[int, int, str]] = asyncio.PriorityQueue()
        self._seq = 0
        self._worker_tasks: list[asyncio.Task] = []
        self._waiters: dict[str, list[asyncio.Event]] = {}

    def _next_seq(self) -> int:
        self._seq += 1
        return self._seq

    def _user_active_count(self, user_id: str) -> int:
        memory = sum(
            1
            for j in self._jobs.values()
            if j.get("user_id") == user_id and j.get("status") in ("queued", "running")
        )
        db_count = self.db.count_user_active_jobs(user_id)
        return max(memory, db_count)

    def _persist(self, job_id: str) -> None:
        job = self._jobs.get(job_id)
        if job:
            self.db.save_lookup_job(job)

    def _notify(self, job_id: str) -> None:
        for event in self._waiters.pop(job_id, []):
            event.set()

    async def wait_for_update(self, job_id: str, timeout: float = 2.0) -> None:
        event = asyncio.Event()
        self._waiters.setdefault(job_id, []).append(event)
        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
        except TimeoutError:
            pass

    def recover_after_restart(self) -> None:
        n = self.db.fail_stale_running_jobs()
        if n:
            print(f"Marked {n} stale running job(s) as failed after restart.", flush=True)

    def _enqueue(self, job_id: str, priority: int) -> None:
        self._queue.put_nowait((priority, self._next_seq(), job_id))

    def create(self, user_id: str, query: str, *, priority: int = SINGLE_LOOKUP_PRIORITY) -> str:
        if self._user_active_count(user_id) >= QUEUE_MAX_PER_USER:
            raise QueueFullError(
                f"Queue full ({QUEUE_MAX_PER_USER} active jobs). Wait for current runs to finish."
            )
        job_id = str(uuid.uuid4())
        self._jobs[job_id] = {
            "id": job_id,
            "user_id": user_id,
            "query": query,
            "status": "queued",
            "phase": "queued",
            "priority": priority,
            "created_at": _utc_now(),
            "updated_at": _utc_now(),
            "result": None,
            "error": None,
        }
        self._persist(job_id)
        self._enqueue(job_id, priority)
        self._maybe_evict()
        return job_id

    def create_bulk(self, user_id: str, queries: list[str]) -> list[str]:
        remaining = QUEUE_MAX_PER_USER - self._user_active_count(user_id)
        if remaining <= 0:
            raise QueueFullError(
                f"Queue full ({QUEUE_MAX_PER_USER} active jobs). Wait for current runs to finish."
            )
        ids: list[str] = []
        for q in queries:
            if not q.strip():
                continue
            if len(ids) >= remaining:
                break
            ids.append(self.create(user_id, q.strip(), priority=BULK_LOOKUP_PRIORITY))
        return ids

    def list_user_jobs(self, user_id: str, job_ids: list[str]) -> list[dict[str, Any]]:
        out = []
        for jid in job_ids:
            job = self.get(jid, user_id)
            if job:
                out.append(job)
        return out

    def get(self, job_id: str, user_id: str | None = None) -> dict[str, Any] | None:
        job = self._jobs.get(job_id)
        if not job:
            job = self.db.get_lookup_job(job_id)
            if job:
                self._jobs[job_id] = job
        if not job:
            return None
        if user_id and job.get("user_id") != user_id:
            return None
        return dict(job)

    def stats(self, user_id: str | None = None) -> dict[str, int]:
        jobs = list(self._jobs.values())
        if user_id:
            jobs = [j for j in jobs if j.get("user_id") == user_id]
        return {
            "total": len(jobs),
            "queued": sum(1 for j in jobs if j.get("status") == "queued"),
            "running": sum(1 for j in jobs if j.get("status") == "running"),
            "completed": sum(1 for j in jobs if j.get("status") == "completed"),
            "failed": sum(1 for j in jobs if j.get("status") == "failed"),
            "queue_depth": self._queue.qsize(),
            "workers": len(self._worker_tasks),
        }

    def _update(self, job_id: str, **fields: Any) -> None:
        job = self._jobs[job_id]
        job.update(fields)
        job["updated_at"] = _utc_now()
        self._persist(job_id)
        self._notify(job_id)

    def _maybe_evict(self) -> None:
        if len(self._jobs) <= JOB_MEMORY_MAX:
            return
        done = [
            (j["updated_at"], jid)
            for jid, j in self._jobs.items()
            if j.get("status") in ("completed", "failed")
        ]
        done.sort()
        to_remove = len(self._jobs) - JOB_MEMORY_MAX + 500
        for _, jid in done[:to_remove]:
            self._jobs.pop(jid, None)

    async def start_worker(self) -> None:
        self.recover_after_restart()
        alive = [t for t in self._worker_tasks if not t.done()]
        self._worker_tasks = alive
        while len(self._worker_tasks) < JOB_WORKER_COUNT:
            self._worker_tasks.append(asyncio.create_task(self._worker_loop()))

    async def stop_worker(self) -> None:
        for task in self._worker_tasks:
            task.cancel()
        for task in self._worker_tasks:
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._worker_tasks = []

    async def _worker_loop(self) -> None:
        while True:
            _prio, _seq, job_id = await self._queue.get()
            job = self.get(job_id)
            if not job or job.get("status") != "queued":
                continue
            user_id = job["user_id"]
            query = job["query"]
            self._update(job_id, status="running", phase="discovering")
            try:
                result = await self.service.run_query(user_id, query)
                payload = _public_result(result)
                final_status = (
                    result.status if result.status in ("completed", "failed") else "completed"
                )
                phase = "complete" if final_status == "completed" else "failed"
                self._update(
                    job_id,
                    status=final_status,
                    phase=phase,
                    result=payload,
                    error=payload["message"] if final_status == "failed" else None,
                )
                if user_id != "local":
                    self.db.increment_lookup_count(user_id)
                    self.db.add_lookup_history(
                        job_id,
                        user_id,
                        query,
                        payload.get("email") or "",
                        payload.get("status") or final_status,
                        linkedin_url=payload.get("profile_url") or "",
                        founder_name=payload.get("display_name") or "",
                    )
            except Exception as exc:
                self._update(
                    job_id,
                    status="failed",
                    phase="failed",
                    error=sanitize_message(str(exc)),
                    result=None,
                )
            finally:
                self._maybe_evict()
