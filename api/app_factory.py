"""Application factory — lifespan, middleware, routers."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

import api.bootstrap  # noqa: F401

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from pathlib import Path

from api.config import (
    APP_SECRET,
    APP_TITLE,
    BULK_MAX_QUERIES,
    DATABASE_PATH,
    FAST_LOOKUP,
    JOB_WORKER_COUNT,
    LINKEDIN_MAX_CONCURRENT,
    LOOKUP_TIMEOUT_SEC,
    QUEUE_MAX_PER_USER,
    RATE_LIMIT_WAIT_MINUTES,
    WEB_BROWSER,
    WEB_MAILMETEOR_PORT,
)
from api.db import Database
from api.deps import WEB_DIST, cors_origins
from api.jobs import JobStore
from api.linkedin_session import LinkedInSessionManager
from api.lookup_service import WebLookupService
from api.routers import account, auth_routes, build_prompt, health, library, lookups, network, parse_routes

API_VERSION = "2.1.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    if APP_SECRET == "change-me-in-production" and os.environ.get("ENV") == "production":
        raise RuntimeError("Set APP_SECRET before production deploy.")

    db_path = Path(DATABASE_PATH) if DATABASE_PATH else None
    db = Database(db_path)
    linkedin = LinkedInSessionManager()
    service = WebLookupService(
        linkedin,
        db,
        browser=WEB_BROWSER,
        mailmeteor_port=WEB_MAILMETEOR_PORT,
        rate_limit_wait=RATE_LIMIT_WAIT_MINUTES,
        lookup_timeout=LOOKUP_TIMEOUT_SEC,
    )
    store = JobStore(service, db)
    await store.start_worker()
    service.schedule_prewarm()
    if FAST_LOOKUP:
        print("Fast lookup mode ON (cache, tight timeouts, bounded email lookup).", flush=True)
    print(
        f"Job queue: {JOB_WORKER_COUNT} worker(s), LinkedIn pool {LINKEDIN_MAX_CONCURRENT}, "
        f"bulk max {BULK_MAX_QUERIES}, per-user cap {QUEUE_MAX_PER_USER}, db {db.path}.",
        flush=True,
    )

    app.state.db = db
    app.state.linkedin = linkedin
    app.state.lookup_service = service
    app.state.job_store = store

    yield

    await store.stop_worker()
    await service.close()
    await linkedin.close_all()


def create_app() -> FastAPI:
    app = FastAPI(title=APP_TITLE, version=API_VERSION, lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    for module in (
        health,
        auth_routes,
        account,
        parse_routes,
        build_prompt,
        network,
        library,
        lookups,
    ):
        app.include_router(module.router)

    if WEB_DIST.is_dir():
        app.mount("/", StaticFiles(directory=str(WEB_DIST), html=True), name="static")

    return app
