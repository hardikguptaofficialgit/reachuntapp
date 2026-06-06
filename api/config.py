"""Web API configuration (isolated from batch pipeline ports)."""

from __future__ import annotations

import os

# Batch pipeline keeps 9223 (LinkedIn) and 9222 (Mailmeteor) - do not use here.
WEB_MAILMETEOR_PORT = int(os.environ.get("WEB_MAILMETEOR_PORT", "9224"))
WEB_LINKEDIN_PORT_BASE = int(os.environ.get("WEB_LINKEDIN_PORT_BASE", "9300"))
WEB_BROWSER = os.environ.get(
    "WEB_BROWSER",
    "brave" if os.name == "nt" else "chrome",
).strip().lower()

APP_SECRET = os.environ.get("APP_SECRET", "change-me-in-production")
REQUIRE_AUTH = os.environ.get("REQUIRE_AUTH", "true").lower() in ("1", "true", "yes")
JWT_EXPIRE_HOURS = int(os.environ.get("JWT_EXPIRE_HOURS", "168"))
DATABASE_PATH = os.environ.get("DATABASE_PATH", "").strip()

# Abuse protection (per authenticated user)
RATE_LIMIT_LOOKUPS_PER_MIN = max(1, int(os.environ.get("RATE_LIMIT_LOOKUPS_PER_MIN", "20")))
RATE_LIMIT_WINDOW_SEC = float(os.environ.get("RATE_LIMIT_WINDOW_SEC", "60"))

# Browser concurrency (Mailmeteor stays serialized; LinkedIn can run in parallel per user)
LINKEDIN_MAX_CONCURRENT = max(1, int(os.environ.get("LINKEDIN_MAX_CONCURRENT", "4")))
LOOKUP_MAX_SEC = float(os.environ.get("LOOKUP_MAX_SEC", "120"))

# Cross-origin SPA (Vercel/Pages) + API on another subdomain
COOKIE_DOMAIN = os.environ.get("COOKIE_DOMAIN", "").strip()
COOKIE_SAMESITE = os.environ.get("COOKIE_SAMESITE", "lax").strip().lower()

# Speed defaults (set FAST_LOOKUP=false to use slower, safer pacing)
FAST_LOOKUP = os.environ.get("FAST_LOOKUP", "true").lower() in ("1", "true", "yes")
LINKEDIN_SEARCH_TIMEOUT_MS = int(os.environ.get("LINKEDIN_SEARCH_TIMEOUT_MS", "10000"))
MAILMETEOR_DELAY_SEC = float(os.environ.get("MAILMETEOR_DELAY_SEC", "1.5" if FAST_LOOKUP else "6"))
MAILMETEOR_JITTER_SEC = float(os.environ.get("MAILMETEOR_JITTER_SEC", "0.5" if FAST_LOOKUP else "4"))
LOOKUP_TIMEOUT_SEC = float(os.environ.get("LOOKUP_TIMEOUT_SEC", "12" if FAST_LOOKUP else "18"))
RATE_LIMIT_WAIT_MINUTES = float(os.environ.get("RATE_LIMIT_WAIT_MINUTES", "8"))
EMAIL_API_FIRST = os.environ.get("EMAIL_API_FIRST", "true").lower() in ("1", "true", "yes")

# DuckDuckGo (ddgs) - enriches LinkedIn discovery without extra browser tabs
DDG_SEARCH_ENABLED = os.environ.get("DDG_SEARCH_ENABLED", "true").lower() in ("1", "true", "yes")
DDG_MAX_RESULTS = int(os.environ.get("DDG_MAX_RESULTS", "12"))

# Queue - Mailmeteor is serialized; LinkedIn runs up to LINKEDIN_MAX_CONCURRENT; raise JOB_WORKER_COUNT cautiously
BULK_MAX_QUERIES = int(os.environ.get("BULK_MAX_QUERIES", "100"))
QUEUE_MAX_PER_USER = int(os.environ.get("QUEUE_MAX_PER_USER", "200"))
JOB_WORKER_COUNT = max(1, int(os.environ.get("JOB_WORKER_COUNT", "1")))
JOB_STATUS_BATCH_MAX = int(os.environ.get("JOB_STATUS_BATCH_MAX", "100"))
JOB_MEMORY_MAX = int(os.environ.get("JOB_MEMORY_MAX", "8000"))
SINGLE_LOOKUP_PRIORITY = int(os.environ.get("SINGLE_LOOKUP_PRIORITY", "0"))
BULK_LOOKUP_PRIORITY = int(os.environ.get("BULK_LOOKUP_PRIORITY", "10"))

# Production droplet: use DDG for LinkedIn profile discovery (no per-user LinkedIn Chrome).
WEB_LINKEDIN_CLIENT_MODE = os.environ.get("WEB_LINKEDIN_CLIENT_MODE", "true").lower() in (
    "1",
    "true",
    "yes",
)
# App branding + Linkit SSO (source slug must stay founder-email for existing Linkit redirects)
APP_TITLE = os.environ.get("APP_TITLE", "Reachunt")
LINKIT_APP_URL = os.environ.get("LINKIT_APP_URL", "http://localhost:8080").rstrip("/")
LINKIT_SOURCE = os.environ.get("LINKIT_SOURCE", "founder-email")
ANYONE_EMAIL_APP_ID = os.environ.get(
    "ANYONE_EMAIL_APP_ID",
    os.environ.get("FOUNDER_EMAIL_APP_ID", "anyone-email"),
)

# Groq - build-tab AI prompts (OpenAI-compatible chat completions)
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
GROQ_API_BASE = os.environ.get("GROQ_API_BASE", "https://api.groq.com/openai/v1").rstrip("/")
BUILD_PROMPT_DAILY_LIMIT = max(1, int(os.environ.get("BUILD_PROMPT_DAILY_LIMIT", "3")))
