"""Find a specific person's LinkedIn profile by name + company domain."""

from __future__ import annotations

import os

from playwright.async_api import Page

from src.linkedin_founders import LinkedInFounder, search_people_with_queries
from src.linkedin_match import (
    MIN_MATCH_SCORE,
    STRONG_MATCH_SCORE,
    build_search_queries,
    pick_best,
    pick_best_for_role,
)
from src.ddg_search import search_linkedin_via_ddg
from src.query_parse import PersonQuery, domain_candidates_for_company
from src.linkedin_search import run_linkedin_search
from src.target_roles import get_target_role, linkedin_queries_for_role


def _merge_candidates(
    primary: list[LinkedInFounder],
    extra: list[LinkedInFounder],
    *,
    max_total: int = 20,
) -> list[LinkedInFounder]:
    seen = {c.linkedin_url for c in primary}
    out = list(primary)
    for c in extra:
        if c.linkedin_url in seen:
            continue
        seen.add(c.linkedin_url)
        out.append(c)
        if len(out) >= max_total:
            break
    return out


def _fast_mode() -> bool:
    return os.environ.get("FAST_LOOKUP", "true").lower() in ("1", "true", "yes")


async def search_person(
    page: Page,
    name: str,
    domain: str,
    *,
    max_candidates: int = 15,
) -> LinkedInFounder | None:
    """Smart search: one fast pass, fallback only if needed."""
    domain = domain.lower().strip()
    queries = build_search_queries(name, domain)
    fast = _fast_mode()

    candidates: list[LinkedInFounder] = []
    seen_urls: set[str] = set()

    for i, query in enumerate(queries):
        batch = await run_linkedin_search(page, query, fast=fast)
        for c in batch:
            if c.linkedin_url not in seen_urls:
                seen_urls.add(c.linkedin_url)
                candidates.append(c)

        best, score = pick_best(candidates, name, domain)
        if best and score >= STRONG_MATCH_SCORE:
            return best
        if candidates and i == 0 and score >= MIN_MATCH_SCORE + 8:
            return best
        if len(candidates) >= max_candidates:
            break
        if candidates and fast:
            break

    ddg_batch = await search_linkedin_via_ddg(name=name, domain=domain)
    candidates = _merge_candidates(candidates, ddg_batch, max_total=max_candidates)

    best, score = pick_best(candidates, name, domain)
    if best and score >= MIN_MATCH_SCORE:
        return best
    return None


async def search_person_for_company_role(
    page: Page,
    company_label: str,
    domain: str,
    role_id: str,
    *,
    max_candidates: int = 15,
) -> LinkedInFounder | None:
    """Find someone in a target role when the user only entered a company name."""
    label = (company_label or domain).strip()
    role = get_target_role(role_id)
    queries = linkedin_queries_for_role(label, domain, role.id)
    people = await search_people_with_queries(page, queries, max_people=max_candidates)
    ddg_batch = await search_linkedin_via_ddg(
        domain=domain,
        company_label=label,
        target_role=role.id,
    )
    people = _merge_candidates(people, ddg_batch, max_total=max_candidates)

    domains_to_try = [domain.lower().strip()]
    for alt in domain_candidates_for_company(label):
        if alt not in domains_to_try:
            domains_to_try.append(alt)

    best: LinkedInFounder | None = None
    best_score = 0
    for dom in domains_to_try:
        candidate, score = pick_best_for_role(people, dom, role.id)
        if candidate and score > best_score:
            best, best_score = candidate, score

    return best


async def search_founder_for_company(
    page: Page,
    company_label: str,
    domain: str,
    *,
    max_candidates: int = 15,
) -> LinkedInFounder | None:
    """Backward-compatible founder search for company-only queries."""
    return await search_person_for_company_role(
        page,
        company_label,
        domain,
        "founder",
        max_candidates=max_candidates,
    )


async def resolve_person_search(page: Page, pq: PersonQuery) -> LinkedInFounder | None:
    if pq.company_only:
        role_id = pq.target_role or "founder"
        return await search_person_for_company_role(
            page,
            pq.company_label or pq.domain,
            pq.domain,
            role_id,
        )
    return await search_person(page, pq.name, pq.domain)


async def resolve_person_search_ddg_only(pq: PersonQuery) -> LinkedInFounder | None:
    """LinkedIn discovery without a browser session (DuckDuckGo site: search)."""
    if pq.company_only:
        role_id = pq.target_role or "founder"
        label = (pq.company_label or pq.domain).strip()
        role = get_target_role(role_id)
        ddg_batch = await search_linkedin_via_ddg(
            domain=pq.domain,
            company_label=label,
            target_role=role.id,
        )
        domains_to_try = [pq.domain.lower().strip()]
        for alt in domain_candidates_for_company(label):
            if alt not in domains_to_try:
                domains_to_try.append(alt)
        best: LinkedInFounder | None = None
        best_score = 0
        for dom in domains_to_try:
            candidate, score = pick_best_for_role(ddg_batch, dom, role.id)
            if candidate and score > best_score:
                best, best_score = candidate, score
        return best

    ddg_batch = await search_linkedin_via_ddg(name=pq.name, domain=pq.domain)
    best, score = pick_best(ddg_batch, pq.name, pq.domain)
    if best and score >= MIN_MATCH_SCORE:
        return best
    return None
