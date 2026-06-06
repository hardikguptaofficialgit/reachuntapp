"""Mailmeteor + optional API fallback + rate-limit handling."""

from __future__ import annotations

import asyncio
import os
import random
from typing import TYPE_CHECKING

from src.email_providers import AnymailFinderClient, get_api_client

if TYPE_CHECKING:
    from src.mailmeteor_auto import MailmeteorAuto


def _fast_mode() -> bool:
    return os.environ.get("FAST_LOOKUP", "true").lower() in ("1", "true", "yes")


def _api_first() -> bool:
    return os.environ.get("EMAIL_API_FIRST", "true").lower() in ("1", "true", "yes")


async def lookup_email(
    finder: "MailmeteorAuto",
    linkedin_url: str,
    *,
    rate_limit_wait_minutes: float,
    api_client: AnymailFinderClient | None,
    extra_delay: float = 0.0,
) -> tuple[str, str]:
    client = api_client or get_api_client()

    if client and _api_first():
        email, status = await asyncio.to_thread(client.find_by_linkedin, linkedin_url)
        if email:
            return email, "found_api"

    email, status = await finder.find_email_with_delay(
        linkedin_url,
        rate_limit_wait_minutes=rate_limit_wait_minutes,
        skip_cooldown=_fast_mode(),
    )

    if status == "rate_limit" and client:
        email, status = await asyncio.to_thread(client.find_by_linkedin, linkedin_url)
        if email:
            return email, "found_api"

    if extra_delay > 0:
        await asyncio.sleep(extra_delay)

    return email, status


async def cooldown_minutes(minutes: float, label: str = "Mailmeteor") -> None:
    total = int(minutes * 60)
    print(f"\n=== {label}: pausing {minutes:g} min to avoid rate limit ===\n", flush=True)
    for remaining in range(total, 0, -60):
        mins = remaining // 60
        print(f"  ... {mins} min left", flush=True)
        await asyncio.sleep(min(60, remaining))
    print("  Resuming...\n", flush=True)
