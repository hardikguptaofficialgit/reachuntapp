"""Mailmeteor-first email lookup with strict custom fallback."""

from __future__ import annotations

import asyncio
import os
from typing import TYPE_CHECKING

from src.custom_email_finder import find_custom_email

if TYPE_CHECKING:
    from src.mailmeteor_auto import MailmeteorAuto


def _fast_mode() -> bool:
    return os.environ.get("FAST_LOOKUP", "true").lower() in ("1", "true", "yes")


def _custom_email_budget_sec() -> float:
    try:
        return max(1.0, min(30.0, float(os.environ.get("CUSTOM_EMAIL_BUDGET_SEC", "8"))))
    except ValueError:
        return 8.0


async def lookup_email(
    finder: "MailmeteorAuto",
    linkedin_url: str,
    *,
    rate_limit_wait_minutes: float,
    api_client: object | None = None,
    name: str = "",
    domain: str = "",
    extra_delay: float = 0.0,
) -> tuple[str, str]:
    email, status = await finder.find_email_with_delay(
        linkedin_url,
        rate_limit_wait_minutes=rate_limit_wait_minutes,
        skip_cooldown=_fast_mode(),
    )

    if extra_delay > 0:
        await asyncio.sleep(extra_delay)

    if email:
        return email, status

    try:
        custom = await asyncio.wait_for(
            find_custom_email(
                name=name,
                domain=domain,
                linkedin_url=linkedin_url,
            ),
            timeout=_custom_email_budget_sec(),
        )
    except TimeoutError:
        custom = None
    if custom and custom.email:
        return custom.email, custom.status

    return "", status


async def cooldown_minutes(minutes: float, label: str = "Mailmeteor") -> None:
    total = int(minutes * 60)
    print(f"\n=== {label}: pausing {minutes:g} min to avoid rate limit ===\n", flush=True)
    for remaining in range(total, 0, -60):
        mins = remaining // 60
        print(f"  ... {mins} min left", flush=True)
        await asyncio.sleep(min(60, remaining))
    print("  Resuming...\n", flush=True)
