"""Shared query parsing helpers and constants."""

from __future__ import annotations

import re

DOMAIN_RE = re.compile(
    r"^([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}$",
    re.I,
)

COMPANY_HINTS = re.compile(
    r"\b(ai|labs?|inc|llc|ltd|corp|app|tech|hq|health|data|cloud|software|studio|group)\b",
    re.I,
)

NAME_SEPARATORS = (" - ", " – ", " — ", " | ", ",")

KNOWN_COMPANY_DOMAINS: dict[str, str] = {
    "notion": "notion.so",
    "stripe": "stripe.com",
    "linkit": "linkitapp.in",
    "linkitapp": "linkitapp.in",
    "linear": "linear.app",
    "vercel": "vercel.com",
    "figma": "figma.com",
    "openai": "openai.com",
    "anthropic": "anthropic.com",
}


def clean_domain(value: str) -> str:
    d = value.strip().strip("\"'“”‘’").lower()
    d = re.sub(r"^https?://", "", d)
    d = d.split("/")[0].split("?")[0]
    if d.startswith("www."):
        d = d[4:]
    return d


def company_slug(label: str) -> str:
    return re.sub(r"[^a-z0-9]", "", label.lower())


def company_label_from_domain(domain: str) -> str:
    base = domain.lower().split(".")[0].strip()
    return base.replace("-", " ").title() if base else domain


def meaningful_person_name(name: str) -> bool:
    """Reject empty, whitespace, or punctuation-only \"names\"."""
    return bool(re.sub(r"[\s\-–—|,.]+", "", (name or "").strip()))


ORG_NAME_HINTS = re.compile(
    r"\b(ventures?|capital|partners?|combinator|holdings|systems|solutions|technologies|"
    r"software|digital|global|media|health|bank|insurance|university|foundation)\b",
    re.I,
)


def looks_like_person_name(text: str) -> bool:
    """2–4 word human names (any casing). Avoids guessing name.com for people."""
    parts = [p for p in text.split() if p]
    if len(parts) < 2 or len(parts) > 4:
        return False
    if COMPANY_HINTS.search(text) or ORG_NAME_HINTS.search(text):
        return False
    if company_slug(text) in KNOWN_COMPANY_DOMAINS:
        return False
    return all(re.match(r"^[a-zA-Z][a-zA-Z.'-]*$", p) for p in parts)


def classify_company_input(raw: str) -> str | None:
    """
    Return company intent kind string, or None if not confident company-only input.
    Values: company_domain | company_name
    """
    text = (raw or "").strip().strip("\"'“”‘’")
    if not text:
        return None

    if looks_like_person_name(text):
        return None

    lone = clean_domain(text)
    if DOMAIN_RE.match(lone) and " " not in text.strip():
        return "company_domain"

    slug = company_slug(text)
    if not slug:
        return None

    if slug in KNOWN_COMPANY_DOMAINS:
        return "company_name"

    if COMPANY_HINTS.search(text):
        return "company_name"

    return None
