"""Per-user LinkedIn browser sessions (separate ports from batch pipeline)."""

from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass
from typing import Literal

from src.browser_cdp import CdpBrowser, cdp_ready
from src.linkedin_auth import page_looks_authed, verify_linkedin_session

ConnectState = Literal["disconnected", "connecting", "connected"]


@dataclass
class ConnectStatus:
    state: ConnectState
    message: str


class LinkedInSessionManager:
    """One isolated Brave profile + port per user for web lookups."""

    def __init__(self, port_base: int = 9300):
        self.port_base = port_base
        self._sessions: dict[str, CdpBrowser] = {}
        self._connecting: set[str] = set()
        self._verified: set[str] = set()
        self._lock = asyncio.Lock()

    def _port_for(self, user_id: str) -> int:
        digest = hashlib.sha256(user_id.encode()).hexdigest()
        offset = int(digest[:4], 16) % 80
        return self.port_base + offset

    def _profile_name(self, user_id: str) -> str:
        short = hashlib.sha256(user_id.encode()).hexdigest()[:12]
        return f"web-linkedin-{short}"

    async def get_browser(self, user_id: str) -> CdpBrowser:
        async with self._lock:
            if user_id in self._sessions:
                return self._sessions[user_id]
            browser = CdpBrowser(
                browser="brave",
                profile_name=self._profile_name(user_id),
                port=self._port_for(user_id),
            )
            await browser.start("https://www.linkedin.com/feed/")
            self._sessions[user_id] = browser
            return browser

    async def _browser_for_user(self, user_id: str) -> CdpBrowser | None:
        """Return active session, or re-attach if Brave is still running on this user's port."""
        if user_id in self._sessions:
            return self._sessions[user_id]
        port = self._port_for(user_id)
        if not cdp_ready(port):
            return None
        async with self._lock:
            if user_id in self._sessions:
                return self._sessions[user_id]
            browser = CdpBrowser(
                browser="brave",
                profile_name=self._profile_name(user_id),
                port=port,
            )
            await browser.start("https://www.linkedin.com/feed/")
            self._sessions[user_id] = browser
            return browser

    async def _detect_logged_in(self, browser: CdpBrowser, user_id: str) -> bool:
        if user_id in self._verified:
            return True

        async def work() -> bool:
            try:
                await browser.ensure_playwright_connected()
            except Exception:
                return False

            if await browser.has_linkedin_session():
                return True

            for page in browser.all_pages:
                try:
                    if await page_looks_authed(page):
                        browser.set_active_page(page)
                        return True
                except Exception:
                    continue

            try:
                page = await browser.get_or_create_page()
                return await verify_linkedin_session(page)
            except Exception:
                return False

        from src.playwright_loop import run_on_playwright_loop

        try:
            ok = await run_on_playwright_loop(work)
        except Exception:
            return False
        if ok:
            self._verified.add(user_id)
        return ok

    async def status(self, user_id: str) -> ConnectStatus:
        if user_id in self._connecting:
            return ConnectStatus(
                state="connecting",
                message="Complete sign-in in the secure browser window, then return here.",
            )
        browser = await self._browser_for_user(user_id)
        if not browser:
            return ConnectStatus(
                state="disconnected",
                message="Connect your professional network to enable discovery.",
            )
        if await self._detect_logged_in(browser, user_id):
            return ConnectStatus(state="connected", message="Network connected.")
        return ConnectStatus(
            state="connecting",
            message="Waiting for sign-in to finish.",
        )

    async def start_connect(self, user_id: str) -> ConnectStatus:
        async with self._lock:
            self._connecting.add(user_id)
        try:
            browser = await self.get_browser(user_id)
            await browser.open_url(
                "https://www.linkedin.com/login",
                wait_until="domcontentloaded",
                timeout=90000,
            )
            return ConnectStatus(
                state="connecting",
                message="A secure window opened — sign in with your professional account.",
            )
        finally:
            async with self._lock:
                self._connecting.discard(user_id)

    async def is_connected(self, user_id: str) -> bool:
        st = await self.status(user_id)
        return st.state == "connected"

    async def refresh_connection(self, user_id: str, *, deep: bool = False) -> ConnectStatus:
        """Poll endpoint after user signs in."""
        browser = await self._browser_for_user(user_id)
        if not browser:
            return ConnectStatus(state="disconnected", message="Start connection first.")
        if deep:
            await asyncio.sleep(0.5)
        if await self._detect_logged_in(browser, user_id):
            return ConnectStatus(state="connected", message="Network connected.")
        return ConnectStatus(
            state="connecting",
            message="Still waiting — finish sign-in in the browser window.",
        )

    async def close_all(self) -> None:
        async with self._lock:
            for browser in self._sessions.values():
                try:
                    await browser.close()
                except Exception:
                    pass
            self._sessions.clear()
            self._verified.clear()
