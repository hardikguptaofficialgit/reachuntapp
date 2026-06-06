"""User-facing copy — never expose internal tooling."""

from __future__ import annotations

import re

_STEP_PUBLIC = {
    "parsed": ("parsed", "Request understood"),
    "cache_hit": ("instant", "Loaded from history"),
    "profile_cache": ("profile_cached", "Using saved profile"),
    "linkedin_search": ("discovering", "Discovering professional profile"),
    "linkedin_found": ("profile_matched", "Profile matched"),
    "no_linkedin": ("no_profile", "No matching profile"),
    "email_lookup": ("verifying", "Verifying work email"),
    "email_found": ("verified", "Work email verified"),
    "no_email": ("unverified", "Profile found — email not available"),
    "parse_error": ("invalid_input", "Invalid input"),
    "linkedin_error": ("discovery_error", "Discovery temporarily unavailable"),
    "email_error": ("verification_error", "Verification temporarily unavailable"),
}

_STATUS_PUBLIC = {
    "found": "verified",
    "not_found": "unavailable",
    "rate_limit": "busy",
    "error": "unavailable",
    "found_api": "verified",
    "no_linkedin": "no_profile",
    "connection_error": "unavailable",
}


def public_steps(internal: list[str]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for step in internal:
        key, label = _STEP_PUBLIC.get(step, ("processing", "Processing"))
        out.append({"id": key, "label": label})
    return out


def public_status(internal: str) -> str:
    return _STATUS_PUBLIC.get(internal, "processing")


def sanitize_message(text: str) -> str:
    if not text:
        return ""
    msg = text
    for term in (
        "mailmeteor",
        "linkedin",
        "brave",
        "cdp",
        "playwright",
        "chrome",
        "9222",
        "9223",
        "9224",
        "run-linkedin",
        "targetclosed",
    ):
        msg = re.sub(term, "", msg, flags=re.I)
    msg = re.sub(r"\s+", " ", msg).strip(" -—:")
    friendly = {
        "session expired": "Your network connection expired. Reconnect to continue.",
        "no matching linkedin profile found": "We could not find a matching professional profile.",
        "linkedin profile found, but no email was returned": "Profile located, but no work email is available right now.",
        "email found": "Work email verified.",
    }
    low = msg.lower()
    for k, v in friendly.items():
        if k in low:
            return v
    if not msg or len(msg) < 4:
        return "Something went wrong. Try again in a moment."
    if "error" in low:
        return "Service temporarily unavailable. Try again shortly."
    return msg[:240]
