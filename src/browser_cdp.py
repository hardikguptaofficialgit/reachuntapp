"""Launch / connect to Brave or Chrome via CDP."""

from __future__ import annotations

import asyncio
import subprocess
import sys
import time
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import TypeVar

import httpx
from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from src.browser_paths import find_browser_exe, linux_server_flags
from src.playwright_loop import run_on_playwright_loop, use_playwright_loop

T = TypeVar("T")


def profile_dir(name: str) -> Path:
    return Path(__file__).resolve().parent.parent / "data" / f"{name}-cdp-profile"


def cdp_ready(port: int) -> bool:
    try:
        return httpx.get(f"http://127.0.0.1:{port}/json/version", timeout=2).status_code == 200
    except Exception:
        return False


def launch_browser(browser: str, profile_name: str, port: int, start_url: str) -> None:
    exe = find_browser_exe(browser)
    user_data = profile_dir(profile_name)
    user_data.mkdir(parents=True, exist_ok=True)
    subprocess.Popen(
        [
            str(exe),
            f"--remote-debugging-port={port}",
            f"--user-data-dir={user_data}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-blink-features=AutomationControlled",
            *linux_server_flags(),
            start_url,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
    )


async def ensure_browser(
    browser: str,
    profile_name: str,
    port: int,
    start_url: str,
    wait_seconds: int = 45,
) -> None:
    if cdp_ready(port):
        return
    launch_browser(browser, profile_name, port, start_url)
    deadline = time.monotonic() + wait_seconds
    while time.monotonic() < deadline:
        if cdp_ready(port):
            await asyncio.sleep(1.5)
            return
        await asyncio.sleep(0.5)
    raise RuntimeError(f"Browser CDP not ready on port {port}")


class CdpBrowser:
    def __init__(
        self,
        browser: str = "brave",
        profile_name: str = "brave-linkedin",
        port: int = 9223,
    ):
        self.browser = browser
        self.profile_name = profile_name
        self.port = port
        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    async def _run(self, fn: Callable[[], Awaitable[T]]) -> T:
        return await run_on_playwright_loop(fn)

    async def start(self, start_url: str = "about:blank") -> Page:
        async def work() -> Page:
            await ensure_browser(self.browser, self.profile_name, self.port, start_url)
            await self._connect_playwright()
            return self.page

        if use_playwright_loop():
            return await self._run(work)
        return await work()

    async def _connect_playwright(self) -> None:
        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception:
                pass
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.connect_over_cdp(
            f"http://127.0.0.1:{self.port}"
        )
        self._sync_pages()

    async def ensure_playwright_connected(self) -> None:
        async def work() -> None:
            if not cdp_ready(self.port):
                raise RuntimeError(f"Browser CDP not ready on port {self.port}")
            if self._browser:
                try:
                    _ = self._browser.contexts
                    self._sync_pages()
                    return
                except Exception:
                    pass
            await self._connect_playwright()

        if use_playwright_loop():
            await self._run(work)
        else:
            await work()

    def _sync_pages(self) -> None:
        if not self._browser or not self._browser.contexts:
            return
        self._context = self._browser.contexts[0]
        pages = self.all_pages
        if pages:
            self._page = pages[-1]

    @property
    def page(self) -> Page:
        if not self._page:
            raise RuntimeError("Call start() first")
        return self._page

    @property
    def all_pages(self) -> list[Page]:
        pages: list[Page] = []
        if self._browser:
            for ctx in self._browser.contexts:
                pages.extend(ctx.pages)
        elif self._context:
            pages.extend(self._context.pages)
        if not pages and self._page:
            return [self._page]
        return pages

    def set_active_page(self, page: Page) -> None:
        self._page = page
        self._context = page.context

    async def open_url(self, url: str, **kwargs) -> None:
        async def work() -> None:
            await self.ensure_playwright_connected()
            await self.page.goto(url, **kwargs)

        if use_playwright_loop():
            await self._run(work)
        else:
            await work()

    async def get_or_create_page(self) -> Page:
        async def work() -> Page:
            await self.ensure_playwright_connected()
            if self.all_pages:
                self._sync_pages()
                return self.page
            if self._browser and self._browser.contexts:
                page = await self._browser.contexts[0].new_page()
                self.set_active_page(page)
                return page
            raise RuntimeError("No browser page available")

        if use_playwright_loop():
            return await self._run(work)
        return await work()

    async def has_linkedin_session(self) -> bool:
        from src.linkedin_auth import browser_has_linkedin_session

        async def work() -> bool:
            await self.ensure_playwright_connected()
            return await browser_has_linkedin_session(self._browser)

        if use_playwright_loop():
            return await self._run(work)
        return await work()

    async def close(self) -> None:
        async def work() -> None:
            if self._browser:
                try:
                    await self._browser.close()
                except Exception:
                    pass
            if self._playwright:
                await self._playwright.stop()
            self._browser = None
            self._context = None
            self._page = None
            self._playwright = None

        if use_playwright_loop():
            await self._run(work)
        else:
            await work()
