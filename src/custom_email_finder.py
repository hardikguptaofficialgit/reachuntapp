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


def _pattern_guess_enabled() -> bool:
    return os.environ.get("CUSTOM_EMAIL_PATTERN_GUESS", "true").lower() in ("1", "true", "yes")


def _pattern_guess_min_confidence() -> int:
    try:
        return max(70, min(95, int(os.environ.get("CUSTOM_EMAIL_PATTERN_GUESS_MIN_CONFIDENCE", "80"))))
    except ValueError:
        return 80


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


def _log(message: str) -> None:
    print(f"[custom_email] {message}", flush=True)


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


KNOWN_DOMAIN_PATTERNS: dict[str, tuple[str, ...]] = {
    # These are used as fallback guesses only after MX/risk validation.
    "figma.com": ("{first}",),
    "nvidia.com": ("{f}{last}",),
    "openai.com": ("{first}",),
}


def _pattern_overrides() -> dict[str, tuple[str, ...]]:
    """
    CUSTOM_EMAIL_PATTERN_OVERRIDES format:
    nvidia.com:{f}{last};openai.com:{first},{first}.{last}
    """
    raw = os.environ.get("CUSTOM_EMAIL_PATTERN_OVERRIDES", "").strip()
    out: dict[str, tuple[str, ...]] = {}
    if not raw:
        return out
    for item in raw.split(";"):
        if ":" not in item:
            continue
        domain, patterns = item.split(":", 1)
        clean = clean_domain(domain)
        vals = tuple(p.strip().lower() for p in patterns.split(",") if p.strip())
        if clean and vals:
            out[clean] = vals
    return out


def _render_pattern(pattern: str, name: str, domain: str) -> str:
    first, last = _name_tokens(name)
    if not first:
        return ""
    local = (
        pattern.lower()
        .replace("{first}", first)
        .replace("{last}", last)
        .replace("{f}", first[:1])
        .replace("{l}", last[:1])
    )
    if "{" in local or "}" in local:
        return ""
    local = "".join(ch for ch in local if ch.isalnum() or ch in "._-")
    if not local:
        return ""
    return f"{local}@{clean_domain(domain)}"


def _preferred_pattern_candidates(name: str, domain: str) -> list[str]:
    clean = clean_domain(domain)
    patterns = _pattern_overrides().get(clean) or KNOWN_DOMAIN_PATTERNS.get(clean) or ()
    out: list[str] = []
    for pattern in patterns:
        email = _render_pattern(pattern, name, clean)
        if email and email not in out:
            out.append(email)
    for email in pattern_candidates(name, clean):
        if email not in out:
            out.append(email)
    return out


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


async def _pattern_guess(name: str, domain: str) -> CustomEmailResult:
    if not _pattern_guess_enabled():
        _log("pattern_guess disabled")
        return CustomEmailResult()
    clean = clean_domain(domain)
    known_or_override = bool(_pattern_overrides().get(clean) or KNOWN_DOMAIN_PATTERNS.get(clean))
    threshold = _pattern_guess_min_confidence()
    first, _last = _name_tokens(name)
    for idx, email in enumerate(_preferred_pattern_candidates(name, clean)[:8]):
        local = email.split("@", 1)[0].lower()
        known_single_name = bool(known_or_override and idx == 0 and first and local == first)
        if (
            is_generic_email(email)
            or not email_matches_name(email, name)
            or (not _strong_local_match(email, name) and not known_single_name)
        ):
            _log(f"pattern_guess_skip email={email} reason=name_or_generic")
            continue
        validation = await asyncio.to_thread(validate_email, email, check_smtp=False)
        if validation.verdict in {"invalid", "undeliverable"}:
            _log(f"pattern_guess_skip email={email} verdict={validation.verdict}")
            continue
        if validation.role_account or validation.disposable or validation.free_provider:
            _log(f"pattern_guess_skip email={email} reason=risk")
            continue
        confidence = validation.score + (20 if known_or_override and idx == 0 else 10)
        confidence = max(0, min(88, confidence))
        _log(
            f"pattern_guess_candidate email={email} confidence={confidence} "
            f"known_pattern={known_or_override} verdict={validation.verdict}"
        )
        if confidence >= threshold:
            return CustomEmailResult(
                email=email,
                status="found_custom_pattern",
                confidence=confidence,
                source="pattern_guess",
                signals=tuple([*validation.signals, "name_pattern", "mx_found"]),
            )
    return CustomEmailResult()


async def find_custom_email(*, name: str, domain: str, linkedin_url: str = "") -> CustomEmailResult:
    if not custom_email_finder_enabled():
        _log("disabled")
        return CustomEmailResult()
    person = (name or "").strip()
    clean = clean_domain(domain)
    if not person or not DOMAIN_RE.match(clean):
        _log(f"invalid_input name={person!r} domain={domain!r}")
        return CustomEmailResult()

    _log(f"start name={person!r} domain={clean!r}")
    batches = await asyncio.gather(
        _public_search(person, clean),
        _company_site(person, clean),
        return_exceptions=True,
    )
    candidates: list[EmailCandidate] = []
    for batch in batches:
        if isinstance(batch, list):
            candidates.extend(batch)
    _log(f"public_candidates count={len(candidates)}")

    best = _best(candidates)
    if best and best.confidence >= _min_confidence():
        _log(f"public_hit email={best.email} confidence={best.confidence} source={best.source}")
        return CustomEmailResult(
            email=best.email,
            status="found_custom_public",
            confidence=best.confidence,
            source=best.source,
            signals=("public_proof", "name_match", "mx_found"),
        )

    smtp = await _smtp_pattern(person, clean)
    if smtp.email:
        _log(f"smtp_pattern_hit email={smtp.email} confidence={smtp.confidence}")
        return smtp

    guessed = await _pattern_guess(person, clean)
    if guessed.email:
        _log(f"pattern_guess_hit email={guessed.email} confidence={guessed.confidence}")
        return guessed

    _log("not_found")
    return CustomEmailResult()
