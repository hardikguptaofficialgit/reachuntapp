"""Reliable LinkedIn login detection (session cookies + feed redirect)."""

from __future__ import annotations

import asyncio

from playwright.async_api import Browser, BrowserContext, Page

SESSION_COOKIE_NAMES = frozenset({"li_at", "li_a"})
_LINKEDIN_URLS = ("https://www.linkedin.com", "https://www.linkedin.com/")


def _cookies_include_session(cookies: list[dict]) -> bool:
    for cookie in cookies:
        name = cookie.get("name") or ""
        value = (cookie.get("value") or "").strip()
        domain = (cookie.get("domain") or "").lower()
        if name in SESSION_COOKIE_NAMES and value and "linkedin" in domain:
            return True
    return False


async def _cookies_via_cdp(page: Page) -> bool:
    """Playwright CDP attach sometimes omits cookies() — read via DevTools protocol."""
    session = None
    try:
        session = await page.context.new_cdp_session(page)
        result = await session.send("Network.getCookies", {"urls": list(_LINKEDIN_URLS)})
        return _cookies_include_session(result.get("cookies", []))
    except Exception:
        return False
    finally:
        if session:
            try:
                await session.detach()
            except Exception:
                pass


async def context_has_linkedin_session(ctx: BrowserContext) -> bool:
    try:
        if _cookies_include_session(await ctx.cookies()):
            return True
    except Exception:
        pass
    for page in ctx.pages[:5]:
        if await _cookies_via_cdp(page):
            return True
    return False


async def browser_has_linkedin_session(browser: Browser | None) -> bool:
    if not browser:
        return False
    for ctx in browser.contexts:
        if await context_has_linkedin_session(ctx):
            return True
    return False


def _url_looks_authed(url: str) -> bool:
    u = url.lower()
    if any(
        part in u
        for part in ("/login", "/checkpoint", "/uas/login", "/signup", "/authwall")
    ):
        return False
    if any(
        part in u
        for part in (
            "/feed",
            "/mynetwork",
            "/messaging",
            "/notifications",
            "/search/results",
            "/jobs/",
        )
    ):
        return True
    if u.rstrip("/") in ("https://www.linkedin.com", "https://linkedin.com"):
        return True
    return "linkedin.com" in u and "/login" not in u


async def page_looks_authed(page: Page) -> bool:
    if await context_has_linkedin_session(page.context):
        return True
    if _url_looks_authed(page.url):
        return True
    try:
        nav = page.locator(
            "#global-nav, .global-nav, header.global-nav, nav[aria-label*='LinkedIn']"
        )
        if await nav.count() > 0:
            return True
    except Exception:
        pass
    return False


async def verify_linkedin_session(page: Page) -> bool:
    """Confirm login via cookies, then optional feed navigation."""
    if await page_looks_authed(page):
        return True
    try:
        await page.goto(
            "https://www.linkedin.com/feed/",
            wait_until="commit",
            timeout=45000,
        )
        await asyncio.sleep(2.0)
    except Exception:
        pass
    if await context_has_linkedin_session(page.context):
        return True
    return _url_looks_authed(page.url)
