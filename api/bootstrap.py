"""Must run before asyncio creates the event loop (Windows + Playwright)."""

from __future__ import annotations

import asyncio
import sys


def apply_windows_event_loop_policy() -> None:
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


apply_windows_event_loop_policy()
