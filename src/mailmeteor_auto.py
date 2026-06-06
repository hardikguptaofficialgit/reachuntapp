"""Automated Mailmeteor via real Brave/Chrome (CDP)."""

from __future__ import annotations

import asyncio
import random
import re
import subprocess
import time
from pathlib import Path
from urllib.parse import quote

import httpx
from playwright.async_api import Browser, Page, async_playwright
from playwright.async_api import Error as PlaywrightError

EMAIL_RE = re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b")
TOOL_URL = "https://mailmeteor.com/tools/linkedin-email-finder"
ERROR_SNIPPET = "oops, it didn't work"

BROWSER_PATHS = {
    "brave": (
        Path(r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"),
        Path(r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe"),
        Path.home() / "AppData/Local/BraveSoftware/Brave-Browser/Application/brave.exe",
    ),
    "chrome": (
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
    ),
}


def profile_dir(browser: str, profile_name: str | None = None) -> Path:
    base = Path(__file__).resolve().parent.parent / "data"
    folder = profile_name or f"{browser}-cdp-profile"
    return base / folder


def find_browser_exe(browser: str) -> Path:
    browser = browser.lower()
    if browser not in BROWSER_PATHS:
        raise ValueError(f"Unknown browser: {browser}. Use 'brave' or 'chrome'.")
    for p in BROWSER_PATHS[browser]:
        if p.exists():
            return p
    label = "Brave" if browser == "brave" else "Google Chrome"
    raise RuntimeError(f"{label} not found. Install it or use --browser chrome / --manual")


def cdp_ready(port: int) -> bool:
    try:
        r = httpx.get(f"http://127.0.0.1:{port}/json/version", timeout=2)
        return r.status_code == 200
    except Exception:
        return False


def launch_browser_cdp(
    browser: str,
    port: int = 9222,
    profile_name: str | None = None,
) -> None:
    exe = find_browser_exe(browser)
    user_data = profile_dir(browser, profile_name)
    user_data.mkdir(parents=True, exist_ok=True)
    subprocess.Popen(
        [
            str(exe),
            f"--remote-debugging-port={port}",
            f"--user-data-dir={user_data}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-blink-features=AutomationControlled",
            TOOL_URL,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
    )


async def ensure_browser(
    browser: str,
    port: int = 9222,
    wait_seconds: int = 30,
    profile_name: str | None = None,
) -> None:
    if cdp_ready(port):
        return
    launch_browser_cdp(browser, port, profile_name)
    deadline = time.monotonic() + wait_seconds
    while time.monotonic() < deadline:
        if cdp_ready(port):
            await asyncio.sleep(1.5)
            return
        await asyncio.sleep(0.5)
    raise RuntimeError(
        f"{browser.title()} CDP not ready on port {port}. "
        f"Close all {browser.title()} windows and retry."
    )


class MailmeteorAuto:
    """Attach to real Brave/Chrome and automate Mailmeteor lookups."""

    def __init__(
        self,
        browser: str = "brave",
        port: int = 9222,
        delay_seconds: float = 6.0,
        jitter_seconds: float = 4.0,
        profile_name: str | None = None,
    ):
        self.browser = browser.lower()
        self.port = port
        self.profile_name = profile_name
        self.delay_seconds = delay_seconds
        self.jitter_seconds = jitter_seconds
        self._playwright = None
        self._browser: Browser | None = None
        self._page: Page | None = None
        self._tool_ready = False
        self._not_found_timeout_ms = 45000

    async def start(self, first_run_setup: bool = False) -> None:
        await ensure_browser(self.browser, self.port, profile_name=self.profile_name)
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.connect_over_cdp(
            f"http://127.0.0.1:{self.port}"
        )
        context = self._browser.contexts[0] if self._browser.contexts else await self._browser.new_context()
        self._page = context.pages[0] if context.pages else await context.new_page()
        self._tool_ready = False

        if first_run_setup:
            await self._first_time_setup()

    async def _first_time_setup(self) -> None:
        page = self._page
        assert page is not None
        name = self.browser.title()
        print(
            f"\n=== One-time {name} setup (30s) ===\n"
            f"If you see Cloudflare, complete it in the {name} window.\n"
            "Test FIND EMAIL once manually if needed.\n",
            flush=True,
        )
        await page.goto(TOOL_URL, wait_until="domcontentloaded", timeout=90000)
        await asyncio.sleep(30)

    async def close(self) -> None:
        if self._browser:
            try:
                await self._browser.close()
            except Exception:
                pass
        if self._playwright:
            await self._playwright.stop()
        self._browser = None
        self._page = None
        self._playwright = None

    async def reconnect(self) -> None:
        """Brave closed or CDP lost — restart browser and re-attach."""
        print("  Reconnecting to Brave...", flush=True)
        await self.close()
        await ensure_browser(self.browser, self.port, wait_seconds=45)
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.connect_over_cdp(
            f"http://127.0.0.1:{self.port}"
        )
        context = self._browser.contexts[0] if self._browser.contexts else await self._browser.new_context()
        self._page = context.pages[0] if context.pages else await context.new_page()
        self._tool_ready = False

    async def _extract_email(self) -> tuple[str, str]:
        page = self._page
        assert page is not None
        body = await page.inner_text("body")
        low = body.lower()
        if "rate_limit" in low or "at capacity" in low or "try again in a few minutes" in low:
            return "", "rate_limit"
        if ERROR_SNIPPET in low:
            return "", "error"

        for sel in (".email-result-card", ".linkedin-email-finder__container", "[class*='email-result']"):
            loc = page.locator(sel)
            if await loc.count() > 0:
                text = await loc.first.inner_text()
                for e in EMAIL_RE.findall(text):
                    if "mailmeteor" not in e.lower():
                        return e, "found"

        for e in EMAIL_RE.findall(body):
            if "mailmeteor" not in e.lower() and "example.com" not in e.lower():
                return e, "found"

        if "no email" in low:
            return "", "not_found"
        return "", "not_found"

    async def find_email(self, linkedin_url: str, timeout_ms: int | None = None) -> tuple[str, str]:
        page = self._page
        assert page is not None
        timeout_ms = timeout_ms or self._not_found_timeout_ms
        linkedin_url = linkedin_url.strip()

        inp = page.locator('input[name="linkedin-url"]')
        btn = page.get_by_role("button", name=re.compile(r"find email", re.I))

        if not self._tool_ready:
            url = f"{TOOL_URL}?linkedin-url={quote(linkedin_url, safe='')}"
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            self._tool_ready = True
            await asyncio.sleep(0.5)
        else:
            # Same tab — fill + click only (much faster than full reload)
            if await inp.count():
                await inp.click()
                await inp.fill("")
                await inp.fill(linkedin_url)
            else:
                url = f"{TOOL_URL}?linkedin-url={quote(linkedin_url, safe='')}"
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)

        if await btn.count():
            await btn.click()

        deadline = time.monotonic() + timeout_ms / 1000
        poll = 0.35
        while time.monotonic() < deadline:
            await asyncio.sleep(poll)
            email, status = await self._extract_email()
            if status in ("found", "error", "rate_limit"):
                return email, status
            if await page.locator(".skeleton-loader").count() > 0:
                continue
        return "", "not_found"

    def _is_connection_error(self, exc: BaseException) -> bool:
        msg = str(exc).lower()
        return any(
            x in msg
            for x in (
                "err_connection_closed",
                "target closed",
                "browser has been closed",
                "connection closed",
                "not connected",
            )
        )

    async def find_email_with_delay(
        self,
        linkedin_url: str,
        rate_limit_wait_minutes: float = 10.0,
        *,
        skip_cooldown: bool = False,
    ) -> tuple[str, str]:
        last_exc: BaseException | None = None
        for attempt in range(3):
            try:
                email, status = await self.find_email(linkedin_url)
                if status == "rate_limit":
                    wait_s = int(rate_limit_wait_minutes * 60)
                    print(
                        f"\n  Mailmeteor rate limit — waiting {rate_limit_wait_minutes:g} min "
                        f"({wait_s}s), then retrying...\n",
                        flush=True,
                    )
                    await asyncio.sleep(wait_s)
                    email, status = await self.find_email(linkedin_url)
                if not skip_cooldown:
                    await asyncio.sleep(
                        self.delay_seconds + random.uniform(0.5, self.jitter_seconds)
                    )
                else:
                    await asyncio.sleep(0.35)
                return email, status
            except (PlaywrightError, OSError) as exc:
                last_exc = exc
                if self._is_connection_error(exc) and attempt < 2:
                    print(f"  Connection lost ({exc.__class__.__name__}), retrying...", flush=True)
                    await self.reconnect()
                    await asyncio.sleep(2)
                    continue
                raise
        if last_exc:
            raise last_exc
        return "", "not_found"
