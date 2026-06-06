"""DuckDuckGo text search for LinkedIn profiles (ddgs / duckduckgo_search)."""

from __future__ import annotations

import asyncio
import os
import re
from typing import Any

from src.linkedin_founders import LINKEDIN_IN, LinkedInFounder, _normalize_in_url
from src.linkedin_founders import clean_linkedin_profile_name
from src.query_common import company_label_from_domain

_SKIP_SLUGS = frozenset({"me", "feed", "search", "notifications", "jobs", "learning"})

_TITLE_NAME_RE = re.compile(
    r"^(.+?)\s*[-–|]\s*(?:.+)$",
)


def ddg_search_enabled() -> bool:
    return os.environ.get("DDG_SEARCH_ENABLED", "true").lower() in ("1", "true", "yes")


def _ddg_max_results() -> int:
    try:
        return max(3, min(25, int(os.environ.get("DDG_MAX_RESULTS", "12"))))
    except ValueError:
        return 12


def _ddg_proxy() -> str | None:
    return os.environ.get("DDGS_PROXY") or os.environ.get("DDG_PROXY") or None


def _ddg_timeout() -> int:
    try:
        return max(5, int(os.environ.get("DDG_TIMEOUT_SEC", "15")))
    except ValueError:
        return 15


def _get_ddgs():
    try:
        from ddgs import DDGS  # type: ignore
    except ImportError:
        from duckduckgo_search import DDGS  # type: ignore
    proxy = _ddg_proxy()
    kwargs: dict[str, Any] = {"timeout": _ddg_timeout()}
    if proxy:
        kwargs["proxy"] = proxy
    return DDGS(**kwargs)


def _name_from_title(title: str) -> str:
    t = re.sub(r"\s*\|\s*LinkedIn.*$", "", title, flags=re.I).strip()
    m = _TITLE_NAME_RE.match(t)
    if m:
        return clean_linkedin_profile_name(m.group(1))
    if " linkedin" in t.lower():
        t = re.sub(r"\s+on\s+LinkedIn.*$", "", t, flags=re.I)
    return clean_linkedin_profile_name(t.split(" - ")[0] if " - " in t else t)


def _founders_from_hits(
    hits: list[dict[str, str]],
    *,
    seen: set[str] | None = None,
) -> list[LinkedInFounder]:
    seen_urls = seen or set()
    out: list[LinkedInFounder] = []

    for row in hits:
        href = (row.get("href") or row.get("url") or "").strip()
        norm = _normalize_in_url(href)
        if not norm or norm in seen_urls:
            continue
        slug = norm.split("/in/")[-1].rstrip("/").lower()
        if slug in _SKIP_SLUGS:
            continue

        title = (row.get("title") or "").strip()
        body = (row.get("body") or row.get("snippet") or "").strip()
        name = _name_from_title(title) if title else slug.replace("-", " ").title()
        if not name or len(name) > 80:
            name = slug.replace("-", " ").title()

        hint = " ".join(x for x in (title, body) if x)[:400]
        seen_urls.add(norm)
        out.append(LinkedInFounder(name=name, linkedin_url=norm, title_hint=hint))

    return out


def _run_queries(queries: list[str], max_results: int) -> list[LinkedInFounder]:
    if not queries:
        return []

    try:
        ddgs = _get_ddgs()
    except Exception:
        return []

    seen: set[str] = set()
    merged: list[LinkedInFounder] = []

    for q in queries:
        if len(merged) >= max_results:
            break
        try:
            hits = ddgs.text(q, max_results=max_results)
        except Exception:
            continue
        if not hits:
            continue
        for founder in _founders_from_hits(hits, seen=seen):
            merged.append(founder)
            if len(merged) >= max_results:
                break

    return merged


def _queries_for_person(name: str, domain: str) -> list[str]:
    name = name.strip()
    domain = domain.lower().strip()
    company = company_label_from_domain(domain)
    queries: list[str] = []
    if name and domain:
        queries.append(f'"{name}" site:linkedin.com/in {domain}')
        queries.append(f"{name} {company} founder site:linkedin.com/in")
    elif name:
        queries.append(f'"{name}" site:linkedin.com/in')
    return queries


def _queries_for_company(
    company_label: str,
    domain: str,
    *,
    target_role: str = "founder",
) -> list[str]:
    from src.target_roles import linkedin_queries_for_role

    label = (company_label or company_label_from_domain(domain)).strip()
    domain = domain.lower().strip()
    queries = linkedin_queries_for_role(label, domain, target_role)
    return [f"{q} site:linkedin.com/in" for q in queries[:6]]


def search_linkedin_profiles_sync(
    *,
    name: str = "",
    domain: str = "",
    company_label: str = "",
    target_role: str = "founder",
    max_results: int | None = None,
) -> list[LinkedInFounder]:
    if not ddg_search_enabled():
        return []

    cap = max_results or _ddg_max_results()
    if company_label and not name.strip():
        queries = _queries_for_company(company_label, domain, target_role=target_role)
    else:
        queries = _queries_for_person(name, domain)
        if company_label:
            queries.extend(_queries_for_company(company_label, domain)[:1])

    return _run_queries(queries, cap)


async def search_linkedin_via_ddg(
    *,
    name: str = "",
    domain: str = "",
    company_label: str = "",
    target_role: str = "founder",
    max_results: int | None = None,
) -> list[LinkedInFounder]:
    """Non-blocking wrapper around DDGS text search."""
    if not ddg_search_enabled():
        return []
    return await asyncio.to_thread(
        search_linkedin_profiles_sync,
        name=name,
        domain=domain,
        company_label=company_label,
        target_role=target_role,
        max_results=max_results,
    )
