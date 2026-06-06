"""Email extraction, pattern generation, and lightweight confidence helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass

from src.query_common import DOMAIN_RE, clean_domain

EMAIL_RE = re.compile(
    r"\b[A-Z0-9._%+\-]+@(?:[A-Z0-9](?:[A-Z0-9\-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,}\b",
    re.I,
)

GENERIC_LOCAL_PARTS = {
    "admin",
    "available",
    "careers",
    "contact",
    "hello",
    "help",
    "hi",
    "hr",
    "info",
    "jobs",
    "legal",
    "marketing",
    "media",
    "no-reply",
    "noreply",
    "office",
    "press",
    "privacy",
    "sales",
    "security",
    "support",
    "team",
}


@dataclass(frozen=True)
class EmailCandidate:
    email: str
    source: str
    confidence: int


def normalize_email(email: str) -> str:
    return (email or "").strip().strip(".,;:()[]{}<>\"'").lower()


def extract_emails(text: str, *, domain: str = "") -> list[str]:
    haystack = (text or "").replace("[at]", "@").replace("(at)", "@")
    haystack = re.sub(r"\s+at\s+", "@", haystack, flags=re.I)
    haystack = haystack.replace("[dot]", ".").replace("(dot)", ".")
    haystack = re.sub(r"\s+dot\s+", ".", haystack, flags=re.I)
    haystack = re.sub(r"\s*@\s*", "@", haystack)
    haystack = re.sub(r"\s*\.\s*", ".", haystack)
    wanted_domain = clean_domain(domain)
    found: list[str] = []
    for raw in EMAIL_RE.findall(haystack):
        email = normalize_email(raw)
        if not email or email in found:
            continue
        if wanted_domain and not email.endswith(f"@{wanted_domain}"):
            continue
        if "example.com" in email or "mailmeteor" in email:
            continue
        found.append(email)
    return found


def _name_tokens(name: str) -> list[str]:
    return [
        re.sub(r"[^a-z]", "", part.lower())
        for part in re.split(r"\s+", name.strip())
        if re.sub(r"[^a-z]", "", part.lower())
    ]


def email_matches_name(email: str, name: str) -> bool:
    local = normalize_email(email).split("@", 1)[0]
    tokens = _name_tokens(name)
    if not tokens:
        return False
    first = tokens[0]
    last = tokens[-1] if len(tokens) > 1 else ""
    compact = re.sub(r"[^a-z]", "", local.lower())
    dotted = re.sub(r"[^a-z.]", "", local.lower())
    if first and compact == first:
        return True
    if first and last and compact in {
        f"{first}{last}",
        f"{first[0]}{last}",
        f"{first}{last[0]}",
        f"{last}{first}",
        f"{last}{first[0]}",
    }:
        return True
    if first and last and dotted in {f"{first}.{last}", f"{last}.{first}"}:
        return True
    return False


def is_generic_email(email: str) -> bool:
    local = normalize_email(email).split("@", 1)[0]
    return local in GENERIC_LOCAL_PARTS


def score_public_email(email: str, name: str) -> int:
    if email_matches_name(email, name):
        return 95
    if not is_generic_email(email):
        return 70
    return 35


def pattern_candidates(name: str, domain: str) -> list[str]:
    clean = clean_domain(domain)
    if not DOMAIN_RE.match(clean):
        return []
    tokens = _name_tokens(name)
    if not tokens:
        return []
    first = tokens[0]
    last = tokens[-1] if len(tokens) > 1 else ""
    locals_: list[str] = [first]
    if first and last and first != last:
        locals_.extend(
            [
                f"{first}.{last}",
                f"{first}{last}",
                f"{first[0]}{last}",
                f"{first}{last[0]}",
                f"{last}.{first}",
            ]
        )
    return [f"{local}@{clean}" for local in dict.fromkeys(locals_) if local]
