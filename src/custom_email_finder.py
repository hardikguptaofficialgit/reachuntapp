"""Strict custom email finder.

This is intentionally conservative. It only returns an email when there is
strong evidence:
- public/company page email that matches the person's name and passes MX/risk checks
- pattern email that passes SMTP validation when explicitly enabled

Weak guesses return no result and Mailmeteor remains the fallback.
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx

from src.email_patterns import EmailCandidate, email_matches_name, extract_emails, is_generic_email, pattern_candidates
from src.email_validation import validate_email
from src.query_common import DOMAIN_RE, clean_domain


@dataclass(frozen=True)
class CustomEmailResult:
    email: str = ""
    status: str = "not_found"
    confidence: int = 0
    source: str = ""
    signals: tuple[str, ...] = ()


def custom_email_finder_enabled() -> bool:
    return os.environ.get("CUSTOM_EMAIL_FINDER", "true").lower() in ("1", "true", "yes")


def _public_search_enabled() -> bool:
    return os.environ.get("CUSTOM_EMAIL_PUBLIC_SEARCH", "true").lower() in ("1", "true", "yes")


def _site_scrape_enabled() -> bool:
    return os.environ.get("CUSTOM_EMAIL_SITE_SCRAPE", "true").lower() in ("1", "true", "yes")


def _pattern_enabled() -> bool:
    return os.environ.get("CUSTOM_EMAIL_PATTERN_SMTP", "false").lower() in ("1", "true", "yes")


def _timeout() -> float:
    try:
        return max(2.0, min(15.0, float(os.environ.get("CUSTOM_EMAIL_TIMEOUT_SEC", "6"))))
    except ValueError:
        return 6.0


def _max_pages() -> int:
    try:
        return max(1, min(12, int(os.environ.get("CUSTOM_EMAIL_MAX_PAGES", "6"))))
    except ValueError:
        return 6


def _min_confidence() -> int:
    try:
        return max(70, min(98, int(os.environ.get("CUSTOM_EMAIL_MIN_CONFIDENCE", "90"))))
    except ValueError:
        return 90


def _get_ddgs():
    from src.ddg_search import _get_ddgs

    return _get_ddgs()


def _safe_company_url(url: str, domain: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return ""
    host = clean_domain(parsed.netloc)
    wanted = clean_domain(domain)
    if host == wanted or host.endswith(f".{wanted}"):
        return url
    return ""


def _queries(name: str, domain: str) -> list[str]:
    return [
        f'"{name}" "@{domain}"',
        f'"{name}" "{domain}" email',
        f'site:{domain} "{name}" "@{domain}"',
        f'site:{domain} "{name}" email',
        f'site:{domain} "{name}" mailto',
        f'site:{domain} "{name}" contact',
    ]


def _name_tokens(name: str) -> tuple[str, str]:
    import re

    parts = [
        re.sub(r"[^a-z]", "", part.lower())
        for part in name.split()
        if re.sub(r"[^a-z]", "", part.lower())
    ]
    if not parts:
        return "", ""
    return parts[0], parts[-1] if len(parts) > 1 else ""


def _strong_local_match(email: str, name: str) -> bool:
    import re

    first, last = _name_tokens(name)
    if not first or not last or first == last:
        return False
    local = email.split("@", 1)[0].lower()
    compact = re.sub(r"[^a-z]", "", local)
    dotted = re.sub(r"[^a-z.]", "", local)
    return compact in {
        f"{first}{last}",
        f"{first[0]}{last}",
        f"{first}{last[0]}",
        f"{last}{first}",
        f"{last}{first[0]}",
    } or dotted in {f"{first}.{last}", f"{last}.{first}"}


def _name_near_email(text: str, email: str, name: str, radius: int = 240) -> bool:
    first, last = _name_tokens(name)
    if not first:
        return False
    low = text.lower()
    idx = low.find(email.lower())
    if idx < 0:
        return False
    window = low[max(0, idx - radius) : idx] + " " + low[idx + len(email) : idx + len(email) + radius]
    if last and first in window and last in window:
        return True
    return bool(not last and first in window)


async def _fetch_text(client: httpx.AsyncClient, url: str) -> str:
    try:
        res = await client.get(url, follow_redirects=True)
        if res.status_code >= 400:
            return ""
        content_type = res.headers.get("content-type", "")
        if content_type and "text" not in content_type and "html" not in content_type:
            return ""
        return res.text[:300_000]
    except Exception:
        return ""


LINK_KEYWORDS = (
    "about",
    "advisor",
    "author",
    "board",
    "company",
    "contact",
    "founder",
    "leadership",
    "management",
    "people",
    "press",
    "profile",
    "team",
)


def _discover_internal_links(html: str, *, base_url: str, domain: str, limit: int) -> list[str]:
    if not html or limit <= 0:
        return []
    try:
        from bs4 import BeautifulSoup
    except Exception:
        return []

    wanted = clean_domain(domain)
    out: list[str] = []
    soup = BeautifulSoup(html[:500_000], "html.parser")
    for a in soup.find_all("a"):
        href = str(a.get("href") or "").strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        text = " ".join(str(a.get_text(" ") or "").lower().split())
        abs_url = urljoin(base_url, href)
        safe = _safe_company_url(abs_url, wanted)
        if not safe:
            continue
        parsed = urlparse(safe)
        haystack = f"{parsed.path.lower()} {text}"
        if not any(k in haystack for k in LINK_KEYWORDS):
            continue
        safe = safe.split("#", 1)[0]
        if safe not in out:
            out.append(safe)
        if len(out) >= limit:
            break
    return out


def _strict_candidates_from_text(text: str, *, name: str, domain: str, source: str) -> list[EmailCandidate]:
    out: list[EmailCandidate] = []
    for email in extract_emails(text, domain=domain):
        if is_generic_email(email) or not email_matches_name(email, name):
            continue
        strong_local = _strong_local_match(email, name)
        nearby_name = _name_near_email(text, email, name)
        if not nearby_name:
            continue
        validation = validate_email(email, check_smtp=False)
        if validation.verdict in {"invalid", "undeliverable"}:
            continue
        if validation.disposable or validation.free_provider or validation.role_account:
            continue
        confidence = min(98, max(84, validation.score + (28 if nearby_name else 18)))
        out.append(EmailCandidate(email=email, source=source, confidence=confidence))
    return out


def _best(candidates: list[EmailCandidate]) -> EmailCandidate | None:
    if not candidates:
        return None
    return sorted(candidates, key=lambda c: (c.confidence, -len(c.email)), reverse=True)[0]


async def _public_search(name: str, domain: str) -> list[EmailCandidate]:
    if not _public_search_enabled():
        return []
    try:
        ddgs = _get_ddgs()
    except Exception:
        return []

    candidates: list[EmailCandidate] = []
    urls: list[str] = []
    for q in _queries(name, domain):
        try:
            hits = await asyncio.to_thread(ddgs.text, q, max_results=_max_pages())
        except Exception:
            continue
        for hit in hits or []:
            row: dict[str, Any] = dict(hit)
            snippet = "\n".join(
                str(row.get(key) or "") for key in ("title", "body", "snippet")
            )
            candidates.extend(
                _strict_candidates_from_text(snippet, name=name, domain=domain, source="public_search")
            )
            href = _safe_company_url(str(row.get("href") or row.get("url") or ""), domain)
            if href and href not in urls:
                urls.append(href)
            if len(urls) >= _max_pages():
                break

    if urls:
        async with httpx.AsyncClient(
            timeout=_timeout(),
            headers={"User-Agent": "ReachuntBot/1.0 (+https://reachhunt.arclabs.page)"},
        ) as client:
            pages = await asyncio.gather(*[_fetch_text(client, url) for url in urls[: _max_pages()]])
        for text in pages:
            candidates.extend(
                _strict_candidates_from_text(text, name=name, domain=domain, source="public_page")
            )
    return candidates


async def _company_site(name: str, domain: str) -> list[EmailCandidate]:
    if not _site_scrape_enabled():
        return []
    base = clean_domain(domain)
    if not DOMAIN_RE.match(base):
        return []
    paths = (
        "",
        "/about",
        "/team",
        "/people",
        "/founders",
        "/leadership",
        "/contact",
        "/company",
        "/blog",
        "/press",
    )
    seed_urls = [f"https://{base}{path}" for path in paths]
    async with httpx.AsyncClient(
        timeout=_timeout(),
        headers={"User-Agent": "ReachuntBot/1.0 (+https://reachhunt.arclabs.page)"},
    ) as client:
        pages = await asyncio.gather(*[_fetch_text(client, url) for url in seed_urls])
        discovered: list[str] = []
        for url, html in zip(seed_urls, pages):
            for link in _discover_internal_links(
                html,
                base_url=url,
                domain=base,
                limit=max(0, _max_pages() - len(discovered)),
            ):
                if link not in seed_urls and link not in discovered:
                    discovered.append(link)
            if len(discovered) >= _max_pages():
                break
        if discovered:
            pages.extend(await asyncio.gather(*[_fetch_text(client, url) for url in discovered]))
    candidates: list[EmailCandidate] = []
    for text in pages:
        candidates.extend(_strict_candidates_from_text(text, name=name, domain=base, source="company_site"))
    return candidates


async def _smtp_pattern(name: str, domain: str) -> CustomEmailResult:
    if not _pattern_enabled():
        return CustomEmailResult()
    for email in pattern_candidates(name, domain)[:5]:
        if is_generic_email(email) or not _strong_local_match(email, name):
            continue
        validation = await asyncio.to_thread(validate_email, email, check_smtp=True)
        if validation.verdict != "verified":
            continue
        if validation.role_account or validation.disposable or validation.free_provider or validation.catch_all:
            continue
        return CustomEmailResult(
            email=email,
            status="found_custom_smtp",
            confidence=validation.score,
            source="pattern_smtp",
            signals=tuple(validation.signals),
        )
    return CustomEmailResult()


async def find_custom_email(*, name: str, domain: str, linkedin_url: str = "") -> CustomEmailResult:
    if not custom_email_finder_enabled():
        return CustomEmailResult()
    person = (name or "").strip()
    clean = clean_domain(domain)
    if not person or not DOMAIN_RE.match(clean):
        return CustomEmailResult()

    batches = await asyncio.gather(
        _public_search(person, clean),
        _company_site(person, clean),
        return_exceptions=True,
    )
    candidates: list[EmailCandidate] = []
    for batch in batches:
        if isinstance(batch, list):
            candidates.extend(batch)

    best = _best(candidates)
    if best and best.confidence >= _min_confidence():
        return CustomEmailResult(
            email=best.email,
            status="found_custom_public",
            confidence=best.confidence,
            source=best.source,
            signals=("public_proof", "name_match", "mx_found"),
        )

    return await _smtp_pattern(person, clean)
