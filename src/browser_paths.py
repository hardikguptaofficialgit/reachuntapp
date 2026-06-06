"""Resolve Brave/Chrome executable paths (Windows + Linux)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

_WINDOWS_BRAVE = (
    Path(r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"),
    Path(r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe"),
    Path.home() / "AppData/Local/BraveSoftware/Brave-Browser/Application/brave.exe",
)

_WINDOWS_CHROME = (
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
)

_LINUX_BRAVE = (
    Path("/usr/bin/brave-browser"),
    Path("/usr/bin/brave"),
    Path("/snap/bin/brave"),
)

_LINUX_CHROME = (
    Path("/usr/bin/google-chrome-stable"),
    Path("/usr/bin/google-chrome"),
    Path("/usr/bin/chromium-browser"),
    Path("/usr/bin/chromium"),
)


def browser_candidates(browser: str) -> tuple[Path, ...]:
    browser = browser.lower()
    override = os.environ.get("BROWSER_EXE", "").strip()
    if override:
        return (Path(override),)

    if sys.platform == "win32":
        if browser == "brave":
            return _WINDOWS_BRAVE
        return _WINDOWS_CHROME

    if browser == "brave":
        return _LINUX_BRAVE + _LINUX_CHROME
    return _LINUX_CHROME + _LINUX_BRAVE


def find_browser_exe(browser: str) -> Path:
    browser = browser.lower()
    if browser not in ("brave", "chrome"):
        raise ValueError(f"Unknown browser: {browser}. Use 'brave' or 'chrome'.")
    for path in browser_candidates(browser):
        if path.exists():
            return path
    label = "Brave" if browser == "brave" else "Chrome/Chromium"
    hint = "Install google-chrome-stable or set BROWSER_EXE=/path/to/chrome"
    raise RuntimeError(f"{label} not found. {hint}")


def linux_server_flags() -> list[str]:
    """Extra flags for headless Linux servers (small RAM droplets)."""
    if sys.platform == "win32":
        return []
    return [
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
    ]
