"""Find founder LinkedIn URLs via logged-in LinkedIn search."""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass

from playwright.async_api import Page

from src.linkedin_auth import page_looks_authed, verify_linkedin_session

LINKEDIN_IN = re.compile(r"https?://(?:[\w.]+)?linkedin\.com/in/([a-zA-Z0-9\-_%]+)/?", re.I)
FOUNDER_KEYWORDS = re.compile(
    r"\b(founder|co-founder|cofounder|ceo|chief executive|owner|president)\b",
    re.I,
)


@dataclass
class LinkedInFounder:
    name: str
    linkedin_url: str
    title_hint: str = ""


def _normalize_in_url(url: str) -> str:
    m = LINKEDIN_IN.search(url)
    if not m:
        return ""
    slug = m.group(1).split("?")[0].rstrip("/")
    if slug.lower() == "me":
        return ""
    return f"https://www.linkedin.com/in/{slug}/"


_PROFILE_NAME_JUNK = re.compile(
    r"(?:\s*[·•|,]\s*)?"
    r"(?:you\b|1st(?:\s+degree)?|2nd(?:\s+degree)?|3rd\+?|following)\s*$",
    re.I,
)


def clean_linkedin_profile_name(name: str) -> str:
    """Strip LinkedIn UI suffixes (e.g. '· You', '· 1st') from result names."""
    n = re.sub(r"\s+", " ", (name or "").strip())
    n = n.strip("\"'“”‘’")
    n = re.sub(r"\s+[0-9A-Fa-f]{6,}$", "", n).strip()
    for _ in range(4):
        prev = n
        n = _PROFILE_NAME_JUNK.sub("", n).strip()
        n = re.sub(r"\s*[·•]\s*$", "", n).strip()
        if n == prev:
            break
    return n


async def _is_logged_in(page: Page) -> bool:
    return await page_looks_authed(page)


async def setup_linkedin_login(page: Page, wait_seconds: int = 300) -> None:
    await page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded", timeout=90000)
    print(
        "\n=== LinkedIn login ===\n"
        "Log in to LinkedIn in the browser window.\n"
        "When your feed / home loads, press ENTER here...\n",
        flush=True,
    )
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, input, ">>> Press ENTER after LinkedIn login... ")
    if not await _is_logged_in(page):
        print("Warning: you may still be on login — continuing anyway.", flush=True)


async def search_founders(
    page: Page,
    startup_name: str,
    max_founders: int = 5,
) -> list[LinkedInFounder]:
    """Search LinkedIn people for startup founders."""
    from src.linkedin_search import run_linkedin_search

    queries = [
        f"{startup_name} founder",
        f"{startup_name} CEO",
        startup_name,
    ]

    seen_urls: set[str] = set()
    founders: list[LinkedInFounder] = []

    for query in queries:
        if len(founders) >= max_founders:
            break

        if not await _is_logged_in(page):
            raise RuntimeError("LinkedIn session expired — run setup-linkedin again")

        batch = await run_linkedin_search(page, query)
        for f in batch:
            if f.linkedin_url in seen_urls:
                continue
            seen_urls.add(f.linkedin_url)
            founders.append(f)
            if len(founders) >= max_founders:
                break

    def score(f: LinkedInFounder) -> int:
        return 1 if FOUNDER_KEYWORDS.search(f.title_hint or f.name) else 0

    founders.sort(key=score, reverse=True)
    return founders[:max_founders]


async def search_people_with_queries(
    page: Page,
    queries: list[str],
    *,
    max_people: int = 15,
) -> list[LinkedInFounder]:
    """Run LinkedIn people search for explicit query strings."""
    from src.linkedin_search import run_linkedin_search

    seen_urls: set[str] = set()
    people: list[LinkedInFounder] = []

    for query in queries:
        if len(people) >= max_people:
            break
        if not await _is_logged_in(page):
            raise RuntimeError("LinkedIn session expired — run setup-linkedin again")

        batch = await run_linkedin_search(page, query)
        for person in batch:
            if person.linkedin_url in seen_urls:
                continue
            seen_urls.add(person.linkedin_url)
            people.append(person)
            if len(people) >= max_people:
                break

    return people[:max_people]
