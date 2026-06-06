"""Lightweight per-user rate limits for abuse protection under load."""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict

from fastapi import HTTPException

from api.config import RATE_LIMIT_LOOKUPS_PER_MIN, RATE_LIMIT_WINDOW_SEC


class RateLimiter:
    def __init__(self, max_events: int, window_sec: float):
        self.max_events = max(1, max_events)
        self.window_sec = window_sec
        self._hits: dict[str, list[float]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def check(self, key: str, *, label: str = "requests") -> None:
        now = time.monotonic()
        async with self._lock:
            window_start = now - self.window_sec
            recent = [t for t in self._hits[key] if t >= window_start]
            if len(recent) >= self.max_events:
                retry = int(self.window_sec - (now - recent[0])) + 1
                raise HTTPException(
                    status_code=429,
                    detail=f"Too many {label}. Wait {retry}s and try again.",
                )
            recent.append(now)
            self._hits[key] = recent


lookup_limiter = RateLimiter(RATE_LIMIT_LOOKUPS_PER_MIN, RATE_LIMIT_WINDOW_SEC)
build_prompt_limiter = RateLimiter(
    max(RATE_LIMIT_LOOKUPS_PER_MIN * 2, 30),
    RATE_LIMIT_WINDOW_SEC,
)
