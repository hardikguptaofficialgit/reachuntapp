"""Mailmeteor via YOUR normal browser — avoids Playwright bot detection."""

from __future__ import annotations

import re
import subprocess
import webbrowser
from urllib.parse import quote

TOOL_BASE = "https://mailmeteor.com/tools/linkedin-email-finder"
EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


def mailmeteor_url(linkedin_url: str) -> str:
    return f"{TOOL_BASE}?linkedin-url={quote(linkedin_url.strip(), safe='')}"


def copy_windows(text: str) -> None:
    try:
        subprocess.run(
            ["clip"],
            input=text,
            text=True,
            check=True,
            shell=True,
        )
    except Exception:
        pass


def prompt_email(linkedin_url: str, startup: str, founder: str) -> tuple[str, str]:
    """
    Opens Mailmeteor in the system default browser (your real Chrome/Edge).
    You click FIND EMAIL; paste the result back here.
    """
    url = mailmeteor_url(linkedin_url)
    copy_windows(linkedin_url)

    print("\n" + "=" * 60)
    print(f"  {startup}  |  {founder}")
    print("=" * 60)
    print("  LinkedIn copied to clipboard.")
    print("  Opening Mailmeteor in YOUR browser (not the script's Chrome)...")
    print()
    print("  1. In the browser tab, click FIND EMAIL")
    print("  2. Copy the email Mailmeteor shows (or leave blank if none)")
    print("  3. Come back here and paste it, then press Enter")
    print()
    print(f"  Direct link:\n  {url}")
    print("=" * 60)

    webbrowser.open(url)

    raw = input("\nPaste email here (or press Enter if none / error): ").strip()
    if not raw:
        return "", "not_found"

    # User might paste extra text — pull first email-like token
    match = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", raw)
    if match:
        email = match.group(0)
        if "mailmeteor" in email.lower():
            return "", "not_found"
        return email, "found"

    if raw.lower() in ("skip", "none", "no", "error", "oops"):
        return "", "not_found"

    return "", "not_found"
