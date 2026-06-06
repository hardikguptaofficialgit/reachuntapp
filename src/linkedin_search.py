"""LinkedIn search navigation and result extraction (global /all/ results)."""

from __future__ import annotations

import asyncio
import os
import re
import time
from urllib.parse import quote

from playwright.async_api import Page

from src.linkedin_auth import page_looks_authed
from src.linkedin_founders import (
    LINKEDIN_IN,
    LinkedInFounder,
    _normalize_in_url,
    clean_linkedin_profile_name,
)

SKIP_SLUGS = frozenset({"me", "feed", "search", "notifications", "jobs", "learning"})

RESULT_WAIT_SELECTORS = (
    "div.entity-result",
    "li.reusable-search__result-container",
    "[data-chameleon-result-urn]",
    'div[data-view-name="search-entity-result-universal-template"]',
    'main a[href*="/in/"]',
)

EMPTY_STATE_PHRASES = (
    "no results found",
    "we couldn't find",
    "try different keywords",
    "0 results",
)


def _search_timeout_ms() -> int:
    return int(os.environ.get("LINKEDIN_SEARCH_TIMEOUT_MS", "10000"))


def linkedin_search_url(keywords: str) -> str:
    q = quote(keywords.strip())
    return (
        "https://www.linkedin.com/search/results/all/"
        f"?keywords={q}&origin=GLOBAL_SEARCH_HEADER"
    )


def people_search_url(keywords: str) -> str:
    q = quote(keywords.strip())
    return (
        "https://www.linkedin.com/search/results/people/"
        f"?keywords={q}&origin=GLOBAL_SEARCH_HEADER"
    )


async def _page_says_empty(page: Page) -> bool:
    try:
        text = (await page.inner_text("main")).lower()
    except Exception:
        try:
            text = (await page.inner_text("body")).lower()[:4000]
        except Exception:
            return False
    return any(p in text for p in EMPTY_STATE_PHRASES)


async def wait_for_people_results(page: Page, *, timeout_ms: int | None = None) -> bool:
    timeout_ms = timeout_ms or _search_timeout_ms()
    deadline = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < deadline:
        if await _page_says_empty(page):
            return False
        for sel in RESULT_WAIT_SELECTORS:
            try:
                if await page.locator(sel).count() > 0:
                    return True
            except Exception:
                continue
        await asyncio.sleep(0.2)
    return False


_EXTRACT_JS = """
() => {
  const seen = new Set();
  const out = [];
  const push = (href, name, cardText) => {
    if (!href || !href.includes('/in/')) return;
    const clean = href.split('?')[0].split('#')[0];
    if (!clean || seen.has(clean)) return;
    seen.add(clean);
    const slug = clean.split('/in/').pop().replace(/\\/$/, '');
    if (!slug || ['me','feed','search'].includes(slug.toLowerCase())) return;
    out.push({
      href: clean.startsWith('http') ? clean : ('https://www.linkedin.com' + clean),
      name: (name || '').trim(),
      cardText: (cardText || '').trim().slice(0, 500),
    });
  };

  const cardTextFrom = (root) => {
    if (!root) return '';
    const sub = root.querySelector(
      '.entity-result__primary-subtitle, .entity-result__summary, [data-view-name*="subtitle"]'
    );
    const bits = [sub?.innerText, root.innerText].filter(Boolean);
    return bits.join(' ').trim().slice(0, 500);
  };

  // Hero / top match on "All" results (Product Owner @ Marico style)
  const heroRoots = document.querySelectorAll(
    'main .search-results-container > div, main .artdeco-card, [data-chameleon-result-urn]'
  );
  for (const root of heroRoots) {
    if (out.length >= 1) break;
    const link = root.querySelector(
      'a[href*="/in/"][data-test-app-aware-link], a.app-aware-link[href*="/in/"], a[href*="/in/"]'
    );
    if (!link) continue;
    let name = '';
    const hidden = link.querySelector('span[aria-hidden="true"]');
    if (hidden) name = hidden.textContent || '';
    if (!name) name = (link.innerText || '').split('\\n')[0];
    name = name.replace(/\\s*[·•]\\s*You\\s*$/i, '').replace(/\\s*[·•]\\s*(1st|2nd|3rd\\+?)\\s*$/i, '').trim();
    push(link.href || link.getAttribute('href'), name, cardTextFrom(root));
  }

  const cards = document.querySelectorAll(
    '.entity-result, li.reusable-search__result-container, [data-chameleon-result-urn]'
  );
  for (const card of cards) {
    const title = card.querySelector(
      '.entity-result__title-text a[href*="/in/"], .entity-result__title a[href*="/in/"]'
    );
    const link = title || card.querySelector(
      'a[href*="/in/"][data-test-app-aware-link], a.app-aware-link[href*="/in/"], a[href*="/in/"]'
    );
    if (!link) continue;
    let name = '';
    const hidden = link.querySelector('span[aria-hidden="true"]');
    if (hidden) name = hidden.textContent || '';
    if (!name) name = (link.innerText || '').split('\\n')[0];
    name = name.replace(/\\s*[·•]\\s*You\\s*$/i, '').replace(/\\s*[·•]\\s*(1st|2nd|3rd\\+?)\\s*$/i, '').trim();
    push(link.href || link.getAttribute('href'), name, cardTextFrom(card));
    if (out.length >= 25) break;
  }

  if (!out.length) {
    const main = document.querySelector('main') || document.body;
    for (const link of main.querySelectorAll('a[href*="/in/"]')) {
      const href = link.href || link.getAttribute('href');
      let name = '';
      const hidden = link.querySelector('span[aria-hidden="true"]');
      if (hidden) name = hidden.textContent || '';
      if (!name) name = (link.innerText || '').split('\\n')[0];
      const box = link.closest('li, div.entity-result, [data-chameleon-result-urn]');
      push(href, name, box ? box.innerText : '');
      if (out.length >= 25) break;
    }
  }
  return out;
}
"""


async def extract_people_results(page: Page, *, max_results: int = 25) -> list[LinkedInFounder]:
    founders: list[LinkedInFounder] = []
    seen: set[str] = set()

    try:
        raw = await page.evaluate(_EXTRACT_JS)
    except Exception:
        raw = []

    for item in raw or []:
        norm = _normalize_in_url(item.get("href") or "")
        if not norm or norm in seen:
            continue
        slug = norm.split("/in/")[-1].rstrip("/").lower()
        if slug in SKIP_SLUGS:
            continue

        name = clean_linkedin_profile_name(item.get("name") or "")
        if not name or len(name) > 100:
            m = LINKEDIN_IN.search(norm)
            name = (m.group(1) if m else slug).replace("-", " ").title()

        card_text = (item.get("cardText") or name)[:400]
        seen.add(norm)
        founders.append(
            LinkedInFounder(name=name, linkedin_url=norm, title_hint=card_text)
        )
        if len(founders) >= max_results:
            return founders

    if founders:
        return founders

    anchors = page.locator('main a[href*="/in/"]')
    try:
        count = min(await anchors.count(), 30)
    except Exception:
        count = 0

    for i in range(count):
        a = anchors.nth(i)
        href = await a.get_attribute("href")
        norm = _normalize_in_url(href or "")
        if not norm or norm in seen:
            continue
        slug = norm.split("/in/")[-1].rstrip("/").lower()
        if slug in SKIP_SLUGS:
            continue

        display = ""
        try:
            hidden = a.locator('span[aria-hidden="true"]')
            if await hidden.count():
                display = (await hidden.first.inner_text()).strip()
        except Exception:
            pass
        if not display:
            display = (await a.inner_text()).strip().split("\n")[0].strip()
        display = clean_linkedin_profile_name(display)
        if not display:
            display = slug.replace("-", " ").title()

        card_text = display
        try:
            card = a.locator(
                "xpath=ancestor::li[contains(@class,'reusable-search') or contains(@class,'entity-result')][1]"
            )
            if await card.count():
                card_text = await card.first.inner_text()
        except Exception:
            pass

        seen.add(norm)
        founders.append(
            LinkedInFounder(name=display, linkedin_url=norm, title_hint=card_text[:400])
        )

    return founders


async def _search_one_url(page: Page, url: str, *, fast: bool) -> list[LinkedInFounder]:
    await page.goto(url, wait_until="commit", timeout=60000)

    if fast:
        await asyncio.sleep(0.75)
    else:
        await asyncio.sleep(1.5)

    if not await page_looks_authed(page):
        raise RuntimeError("LinkedIn session expired — connect your network again.")

    if not await wait_for_people_results(page):
        return []

    await page.mouse.wheel(0, 700)
    await asyncio.sleep(0.3 if fast else 0.6)
    if not fast:
        for _ in range(2):
            await page.mouse.wheel(0, 600)
            await asyncio.sleep(0.5)

    return await extract_people_results(page)


async def run_linkedin_search(
    page: Page,
    keywords: str,
    *,
    fast: bool = True,
) -> list[LinkedInFounder]:
    seen: set[str] = set()
    merged: list[LinkedInFounder] = []

    for url in (people_search_url(keywords), linkedin_search_url(keywords)):
        batch = await _search_one_url(page, url, fast=fast)
        for founder in batch:
            if founder.linkedin_url not in seen:
                seen.add(founder.linkedin_url)
                merged.append(founder)
        if merged and fast:
            break

    return merged


async def run_people_search(page: Page, keywords: str) -> list[LinkedInFounder]:
    return await run_linkedin_search(page, keywords, fast=_fast_mode())


def _fast_mode() -> bool:
    return os.environ.get("FAST_LOOKUP", "true").lower() in ("1", "true", "yes")
