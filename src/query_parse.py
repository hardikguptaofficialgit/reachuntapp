"""Parse user queries: person + domain, or startup/company name only."""

from __future__ import annotations

from dataclasses import dataclass

from src.query_common import (
    COMPANY_HINTS,
    DOMAIN_RE,
    KNOWN_COMPANY_DOMAINS,
    NAME_SEPARATORS,
    clean_domain,
    company_label_from_domain,
    company_slug,
    looks_like_person_name,
    meaningful_person_name,
)
from src.query_common import classify_company_input


@dataclass(frozen=True)
class PersonQuery:
    name: str
    domain: str
    raw: str
    company_only: bool = False
    company_label: str = ""
    target_role: str = ""
    query_kind: str = "person"


def domain_candidates_for_company(label: str) -> list[str]:
    cleaned = clean_domain(label)
    if DOMAIN_RE.match(cleaned):
        return [cleaned]

    slug = company_slug(label)
    if not slug:
        return []

    out: list[str] = []
    known = KNOWN_COMPANY_DOMAINS.get(slug)
    if known:
        out.append(known)
    for tld in (".com", ".so", ".io", ".co", ".in", ".app", ".ai", ".dev"):
        candidate = f"{slug}{tld}"
        if DOMAIN_RE.match(candidate):
            out.append(candidate)
    return list(dict.fromkeys(out))


def guess_primary_domain(label: str) -> str:
    slug = company_slug(label)
    if slug in KNOWN_COMPANY_DOMAINS:
        return KNOWN_COMPANY_DOMAINS[slug]
    candidates = domain_candidates_for_company(label)
    if not candidates:
        raise ValueError("Could not infer a company domain from that name.")
    return candidates[0]


def _company_only_query(
    *,
    raw: str,
    domain: str,
    company_label: str,
    kind: str,
) -> PersonQuery:
    from src.target_roles import DEFAULT_TARGET_ROLE

    return PersonQuery(
        name="",
        domain=domain,
        raw=raw,
        company_only=True,
        company_label=company_label,
        target_role=DEFAULT_TARGET_ROLE,
        query_kind=kind,
    )


def parse_person_query(text: str) -> PersonQuery:
    raw = (text or "").strip().strip("\"'“”‘’")
    if not raw:
        raise ValueError("Enter full name - company domain.")

    for sep in NAME_SEPARATORS:
        if sep in raw:
            left, right = raw.split(sep, 1)
            name = left.strip()
            domain = clean_domain(right)
            if meaningful_person_name(name) and domain and DOMAIN_RE.match(domain):
                return PersonQuery(
                    name=name,
                    domain=domain,
                    raw=raw,
                    query_kind="person",
                )
            company_label = right.strip()
            if meaningful_person_name(name) and company_label:
                try:
                    inferred_domain = guess_primary_domain(company_label)
                except ValueError:
                    inferred_domain = ""
                if inferred_domain and DOMAIN_RE.match(inferred_domain):
                    return PersonQuery(
                        name=name,
                        domain=inferred_domain,
                        raw=raw,
                        query_kind="person",
                    )

    if "@" in raw:
        name, domain = raw.split("@", 1)
        domain = clean_domain(domain)
        name = name.strip()
        if meaningful_person_name(name) and DOMAIN_RE.match(domain):
            return PersonQuery(
                name=name,
                domain=domain,
                raw=raw,
                query_kind="person",
            )

    parts = raw.split()
    if len(parts) >= 2:
        maybe_domain = clean_domain(parts[-1])
        if DOMAIN_RE.match(maybe_domain):
            name = " ".join(parts[:-1]).strip()
            if meaningful_person_name(name):
                return PersonQuery(
                    name=name,
                    domain=maybe_domain,
                    raw=raw,
                    query_kind="person",
                )

    lone = clean_domain(raw)
    if DOMAIN_RE.match(lone) and len(parts) <= 1:
        return _company_only_query(
            raw=raw,
            domain=lone,
            company_label=company_label_from_domain(lone),
            kind="company_domain",
        )

    if looks_like_person_name(raw):
        raise ValueError("Add their company domain, like Arushi Gupta - notion.so.")

    kind = classify_company_input(raw)
    if kind is None:
        raise ValueError("Use full name - company domain, or enter a company domain.")

    domain = guess_primary_domain(raw)
    label = raw.strip() if kind == "company_name" else company_label_from_domain(domain)
    return _company_only_query(
        raw=raw,
        domain=domain,
        company_label=label,
        kind=kind,
    )


def lookup_cache_key(text: str, target_role: str | None = None) -> str:
    q = text.strip()
    role = (target_role or "").strip()
    if role:
        return f"{q}|role:{role}"
    return q
