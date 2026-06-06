"""Mailmeteor LinkedIn email finder — requires real Chrome (Cloudflare Turnstile)."""

from __future__ import annotations

import asyncio
import random
import re
import time
from pathlib import Path

from playwright.async_api import BrowserContext, Page, async_playwright

EMAIL_RE = re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b")
TOOL_URL = "https://mailmeteor.com/tools/linkedin-email-finder"
ERROR_SNIPPET = "oops, it didn't work"
PROFILE_DIR = Path(__file__).resolve().parent.parent / "data" / "chrome-mailmeteor-profile"


class MailmeteorFinder:
    """
    Uses a persistent Chrome profile so Cloudflare / Turnstile only needs to be
    solved once. Run warmup() or the first lookup may ask you to verify in the browser.
    """

    def __init__(
        self,
        delay_seconds: float = 5.0,
        connect_cdp: str | None = None,
        profile_dir: Path | None = None,
        manual_click: bool = False,
    ):
        self.delay_seconds = delay_seconds
        self.connect_cdp = connect_cdp
        self.profile_dir = profile_dir or PROFILE_DIR
        self.manual_click = manual_click
        self._playwright = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._owns_context = True

    async def start(self) -> None:
        self._playwright = await async_playwright().start()

        if self.connect_cdp:
            browser = await self._playwright.chromium.connect_over_cdp(self.connect_cdp)
            self._context = browser.contexts[0] if browser.contexts else await browser.new_context()
            self._owns_context = False
            self._page = self._context.pages[0] if self._context.pages else await self._context.new_page()
        else:
            self.profile_dir.mkdir(parents=True, exist_ok=True)
            try:
                self._context = await self._playwright.chromium.launch_persistent_context(
                    user_data_dir=str(self.profile_dir),
                    headless=False,
                    channel="chrome",
                    args=["--disable-blink-features=AutomationControlled"],
                    viewport={"width": 1280, "height": 900},
                    locale="en-US",
                )
            except Exception:
                self._context = await self._playwright.chromium.launch_persistent_context(
                    user_data_dir=str(self.profile_dir),
                    headless=False,
                    args=["--disable-blink-features=AutomationControlled"],
                    viewport={"width": 1280, "height": 900},
                    locale="en-US",
                )
            self._page = self._context.pages[0] if self._context.pages else await self._context.new_page()

        await self._page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

    async def close(self) -> None:
        if self._context and self._owns_context:
            await self._context.close()
        if self._playwright:
            await self._playwright.stop()
        self._context = None
        self._page = None
        self._playwright = None

    async def warmup(self, wait_seconds: int = 180, interactive: bool = True) -> None:
        """Open Mailmeteor once; complete Cloudflare in the browser if prompted."""
        if not self._page:
            raise RuntimeError("Call start() first")
        print(
            "\n=== Mailmeteor warmup ===\n"
            "Chrome will open the Mailmeteor LinkedIn Email Finder.\n"
            "1. Complete any Cloudflare / security check in that window.\n"
            "2. Paste any LinkedIn URL and click FIND EMAIL — confirm you see an email.\n",
            flush=True,
        )
        await self._page.goto(TOOL_URL, wait_until="domcontentloaded", timeout=90000)
        await self._wait_cloudflare_clear(wait_seconds)

        if interactive:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: input(
                    "\n>>> When Mailmeteor works in Chrome, press ENTER here to continue... "
                ),
            )
        print("Warmup done. Starting automated lookups.\n", flush=True)

    async def _wait_cloudflare_clear(self, wait_seconds: int) -> None:
        page = self._page
        assert page is not None
        deadline = time.monotonic() + wait_seconds
        while time.monotonic() < deadline:
            body = (await page.inner_text("body")).lower()
            blocked = (
                "checking your browser" in body
                or "verify you are human" in body
                or "just a moment" in body
            )
            if not blocked and await page.locator('input[name="linkedin-url"]').is_visible():
                return
            await page.wait_for_timeout(1500)
        print("Warning: Cloudflare check may still be active.", flush=True)

    async def _extract_email_from_page(self) -> tuple[str, str]:
        page = self._page
        assert page is not None

        body = await page.inner_text("body")
        low = body.lower()
        if ERROR_SNIPPET in low:
            return "", "error"

        # Result card (Mailmeteor UI)
        for selector in (
            ".email-result-card",
            ".linkedin-email-finder__container",
            "[class*='email-result']",
        ):
            loc = page.locator(selector)
            if await loc.count() > 0:
                card_text = await loc.first.inner_text()
                emails = [
                    e
                    for e in EMAIL_RE.findall(card_text)
                    if "mailmeteor" not in e.lower() and "example.com" not in e.lower()
                ]
                if emails:
                    return emails[0], "found"

        emails = [
            e
            for e in EMAIL_RE.findall(body)
            if "mailmeteor" not in e.lower() and "example.com" not in e.lower()
        ]
        if emails:
            return emails[0], "found"

        if "no email" in low or "not found" in low:
            return "", "not_found"

        return "", "not_found"

    async def find_email(self, linkedin_url: str, timeout_ms: int = 40000) -> tuple[str, str]:
        if not self._page:
            raise RuntimeError("Call start() first")

        page = self._page
        await page.goto(TOOL_URL, wait_until="domcontentloaded", timeout=90000)
        await self._wait_cloudflare_clear(30)

        if await page.locator('iframe[src*="challenges.cloudflare"]').count() > 0:
            print(
                "Cloudflare is blocking Mailmeteor. Complete the check in Chrome, "
                "or run: python warmup_mailmeteor.py",
                flush=True,
            )

        inp = page.locator('input[name="linkedin-url"]')
        await inp.click()
        await inp.fill("")
        await inp.type(linkedin_url, delay=30)

        if self.manual_click:
            # Mailmeteor often detects automation when the script clicks the button.
            # In manual mode we prefill the URL and let the user click "FIND EMAIL".
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: input(
                    "\n>>> Mailmeteor is ready in Chrome. Click FIND EMAIL, wait for a result, then press ENTER here... "
                ),
            )
        else:
            await page.get_by_role("button", name=re.compile(r"find email", re.I)).click()

        deadline = time.monotonic() + timeout_ms / 1000
        while time.monotonic() < deadline:
            await page.wait_for_timeout(800)
            email, status = await self._extract_email_from_page()
            if status in ("found", "error"):
                return email, status
            # Still loading?
            if await page.locator(".skeleton-loader").count() > 0:
                continue

        return "", "not_found"

    async def find_email_with_delay(self, linkedin_url: str) -> tuple[str, str]:
        """Single attempt — no retry (move on if Mailmeteor has no email)."""
        try:
            email, status = await asyncio.wait_for(
                self.find_email(linkedin_url),
                timeout=50,
            )
        except asyncio.TimeoutError:
            email, status = "", "not_found"
        except Exception:
            email, status = "", "error"
        await asyncio.sleep(self.delay_seconds + random.uniform(0.5, 1.5))
        return email, status


def find_email_sync(
    linkedin_url: str,
    connect_cdp: str | None = None,
    warmup: bool = False,
) -> tuple[str, str]:
    async def _run() -> tuple[str, str]:
        finder = MailmeteorFinder(connect_cdp=connect_cdp)
        await finder.start()
        try:
            if warmup:
                await finder.warmup()
            return await finder.find_email(linkedin_url)
        finally:
            await finder.close()

    return asyncio.run(_run())
