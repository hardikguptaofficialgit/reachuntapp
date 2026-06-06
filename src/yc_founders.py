"""Extract Active Founders from YC company pages."""

from __future__ import annotations

import re
from dataclasses import dataclass

import httpx

# linkedin.com/in with or without www
LINKEDIN_IN_RE = re.compile(
    r'href="(https?://(?:www\.)?linkedin\.com/in/[^"?#]+)"'
    r'[^>]*aria-label="LinkedIn profile"',
    re.IGNORECASE,
)
NAME_RE = re.compile(
    r'class="text-(?:xl|lg) font-bold">([^<]+)</div>',
    re.IGNORECASE,
)
AVATAR_ALT_RE = re.compile(
    r'alt="([^"]+)"[^>]*class="[^"]*object-cover',
    re.IGNORECASE,
)


@dataclass
class Founder:
    name: str
    linkedin_url: str


def _normalize_linkedin(url: str) -> str:
    url = url.split("?")[0].rstrip("/") + "/"
    if url.startswith("https://linkedin.com/"):
        url = "https://www." + url[len("https://") :]
    return url


def _active_founders_section(html: str) -> str:
    if "Active Founders" not in html:
        return ""
    section = html.split("Active Founders", 1)[1]
    for marker in (
        "Primary Partner",
        "Company Launches",
        "Similar Companies",
        'aria-label="LinkedIn profile" target="_blank" rel="nofollow noopener"',
    ):
        if marker in section:
            section = section.split(marker, 1)[0]
    return section


def _parse_section(section: str) -> list[Founder]:
    if not section:
        return []

    seen: set[str] = set()
    founders: list[Founder] = []

    # Split into per-founder blocks (desktop + mobile duplicates)
    blocks = re.split(
        r'<div class="flex flex-col gap-2 border-b border-gray-100',
        section,
    )

    for block in blocks:
        links = LINKEDIN_IN_RE.findall(block)
        if not links:
            continue
        url = _normalize_linkedin(links[0])

        names = NAME_RE.findall(block)
        name = names[0].strip() if names else ""
        if not name:
            alts = AVATAR_ALT_RE.findall(block)
            name = alts[0].strip() if alts else ""

        if url in seen:
            continue
        seen.add(url)
        founders.append(Founder(name=name, linkedin_url=url))

    if founders:
        return founders

    # Fallback: walk each LinkedIn /in/ link in section and find nearest name
    for m in LINKEDIN_IN_RE.finditer(section):
        url = _normalize_linkedin(m.group(1))
        if url in seen:
            continue
        before = section[max(0, m.start() - 2500) : m.start()]
        names = NAME_RE.findall(before)
        name = names[-1].strip() if names else ""
        if not name:
            alts = AVATAR_ALT_RE.findall(before)
            name = alts[-1].strip() if alts else ""
        seen.add(url)
        founders.append(Founder(name=name, linkedin_url=url))

    return founders


def fetch_founders(company_url: str, client: httpx.Client | None = None) -> list[Founder]:
    own_client = client is None
    if own_client:
        client = httpx.Client(
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
                )
            },
            follow_redirects=True,
            timeout=60,
        )
    try:
        r = client.get(company_url)
        r.raise_for_status()
        html = r.text
    finally:
        if own_client:
            client.close()

    section = _active_founders_section(html)
    return _parse_section(section)
