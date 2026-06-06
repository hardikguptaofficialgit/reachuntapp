"""Background asyncio loop for Playwright (Windows + uvicorn subprocess fix)."""

from __future__ import annotations

import asyncio
import sys
import threading
from collections.abc import Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")

_runner: "PlaywrightLoop | None" = None
_runner_lock = threading.Lock()


def _apply_windows_policy() -> None:
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


class PlaywrightLoop:
    def __init__(self) -> None:
        self._ready = threading.Event()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread = threading.Thread(target=self._thread_main, name="playwright-loop", daemon=True)
        self._thread.start()
        if not self._ready.wait(timeout=60):
            raise RuntimeError("Playwright background loop failed to start.")

    def _thread_main(self) -> None:
        _apply_windows_policy()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._loop = loop
        self._ready.set()
        loop.run_forever()

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        if not self._loop:
            raise RuntimeError("Playwright loop not ready.")
        return self._loop

    async def run(self, coro: Awaitable[T]) -> T:
        caller = asyncio.get_running_loop()
        if caller is self.loop:
            return await coro
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        return await asyncio.wrap_future(future)


def get_playwright_loop() -> PlaywrightLoop:
    global _runner
    with _runner_lock:
        if _runner is None:
            _runner = PlaywrightLoop()
        return _runner


def use_playwright_loop() -> bool:
    return sys.platform == "win32"


async def run_on_playwright_loop(fn: Callable[[], Awaitable[T]]) -> T:
    if not use_playwright_loop():
        return await fn()
    return await get_playwright_loop().run(fn())
