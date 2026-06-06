from fastapi import APIRouter, Request

from api.config import (
    APP_TITLE,
    JOB_WORKER_COUNT,
    LINKEDIN_MAX_CONCURRENT,
    LINKIT_APP_URL,
    LINKIT_SOURCE,
    REQUIRE_AUTH,
)

router = APIRouter(tags=["health"])


@router.get("/api/v1/health")
async def health():
    return {
        "ok": True,
        "app": APP_TITLE,
        "auth_required": REQUIRE_AUTH,
        "auth_provider": "linkit",
        "linkit_app_url": LINKIT_APP_URL,
    }


@router.get("/api/v1/ready")
async def ready(request: Request):
    """Load balancer readiness — DB reachable and job workers running."""
    db = request.app.state.db
    store = request.app.state.job_store
    try:
        with db.session() as conn:
            conn.execute("SELECT 1")
    except Exception as exc:
        return {"ready": False, "reason": str(exc)}
    workers = len([t for t in store._worker_tasks if not t.done()])
    if workers < JOB_WORKER_COUNT:
        return {"ready": False, "reason": "job_workers_starting"}
    return {
        "ready": True,
        "workers": workers,
        "linkedin_max_concurrent": LINKEDIN_MAX_CONCURRENT,
    }


@router.get("/api/v1/auth/config")
async def auth_config():
    return {
        "provider": "linkit",
        "linkit_app_url": LINKIT_APP_URL,
        "sign_in_path": "/signin",
        "source": LINKIT_SOURCE,
    }
