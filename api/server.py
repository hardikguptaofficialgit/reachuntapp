"""Uvicorn entrypoint — sets Windows asyncio policy before the server loop starts."""

from __future__ import annotations

import argparse
import sys

from api.bootstrap import apply_windows_event_loop_policy

apply_windows_event_loop_policy()


def main() -> None:
    import uvicorn

    parser = argparse.ArgumentParser(description="Founder lookup API server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Auto-reload (disabled on Windows — breaks Playwright subprocesses)",
    )
    args = parser.parse_args()

    reload = args.reload
    if sys.platform == "win32" and reload:
        print(
            "Note: --reload is disabled on Windows so LinkedIn/Playwright can spawn correctly.",
            flush=True,
        )
        reload = False

    uvicorn.run(
        "api.main:app",
        host=args.host,
        port=args.port,
        reload=reload,
        loop="asyncio",
    )


if __name__ == "__main__":
    main()
