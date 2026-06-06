"""Fill emails in results.csv — automated via real Chrome (default)."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

import pandas as pd

from src.csv_store import load_results_csv, prepare_results_df, safe_write_results_csv
from src.pipeline import DEFAULT_OUTPUT, PROGRESS_PATH


def has_linkedin(url: object) -> bool:
    return "linkedin.com/in/" in str(url or "")


def _cell_str(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    s = str(value).strip()
    return "" if s.lower() == "nan" else s


def needs_email(row) -> bool:
    if not has_linkedin(row.get("linkedin_url")):
        return False
    return not _cell_str(row.get("email"))


def save_df(path: Path, df: pd.DataFrame) -> None:
    df = prepare_results_df(df)
    safe_write_results_csv(path, df)
    if PROGRESS_PATH.exists():
        progress = json.loads(PROGRESS_PATH.read_text(encoding="utf-8"))
        progress["rows"] = df.to_dict(orient="records")
        PROGRESS_PATH.write_text(json.dumps(progress, indent=2), encoding="utf-8")


async def _process_one(
    finder,
    api_client,
    args: argparse.Namespace,
    df: pd.DataFrame,
    path: Path,
    n: int,
    total: int,
    idx: int,
) -> tuple[int, int, bool]:
    """Returns (found_delta, error_delta, hit_rate_limit)."""
    from src.email_lookup import lookup_email

    row = df.loc[idx]
    startup = _cell_str(row.get("startup_name"))
    founder = _cell_str(row.get("founder_name"))
    linkedin = _cell_str(row["linkedin_url"])
    print(f"[{n}/{total}] {startup} — {founder}", flush=True)

    found = errors = 0
    hit_rl = False

    try:
        email, status = await lookup_email(
            finder,
            linkedin,
            rate_limit_wait_minutes=args.rate_limit_wait,
            api_client=api_client,
        )
    except Exception as exc:
        errors = 1
        email, status = "", "connection_error"
        print(f"  => browser/network error ({exc.__class__.__name__})", flush=True)
        try:
            await finder.reconnect()
        except Exception:
            save_df(path, df)
            raise

    df.at[idx, "email"] = email
    df.at[idx, "email_status"] = status

    if email:
        found = 1
        print(f"  => {email}", flush=True)
    elif status == "rate_limit":
        errors = 1
        hit_rl = True
        print("  => rate limit", flush=True)
    elif status == "error":
        errors = 1
        print("  => Mailmeteor error — skipped", flush=True)
    elif status != "connection_error":
        print("  => no email", flush=True)

    save_df(path, df)
    return found, errors, hit_rl


async def run_auto(args: argparse.Namespace) -> None:
    from src.email_lookup import cooldown_minutes
    from src.email_providers import get_api_client
    from src.mailmeteor_auto import MailmeteorAuto

    path = Path(args.output)
    df = load_results_csv(path)
    indices = [i for i, row in df.iterrows() if needs_email(row)]
    if args.limit:
        indices = indices[: args.limit]

    print(f"Founders needing email lookup: {len(indices)}", flush=True)
    if not indices:
        print("All done — no empty emails left.")
        return

    api_client = get_api_client()
    browser = args.browser.lower()

    if args.fast:
        print(
            "\n*** FAST MODE ***\n"
            f"~{args.delay}s between lookups, {args.lookup_timeout:g}s max wait each.\n"
            "No scheduled pauses — runs until done (only waits if Mailmeteor rate-limits).\n",
            flush=True,
        )
    elif args.continuous and args.batch_cooldown > 0:
        print(
            "\n*** CONTINUOUS MODE (with batch pauses) ***\n"
            f"Batches of {args.batch_size}, then pauses {args.batch_cooldown:g} min.\n"
            f"Delay ~{args.delay}s between lookups.\n",
            flush=True,
        )
    else:
        print(
            f"\nAUTO MODE: {browser.title()} + Mailmeteor.\n"
            "Tip: use .\\run-emails-continuous.ps1 to avoid manual stops on rate limit.\n",
            flush=True,
        )

    if api_client:
        print("API fallback: ANYMAIL_API_KEY detected (used when Mailmeteor rate-limits).\n", flush=True)
    else:
        print(
            "No API key — Mailmeteor only. For fewer stops, set ANYMAIL_API_KEY (paid) or use continuous mode.\n",
            flush=True,
        )

    finder = MailmeteorAuto(
        browser=browser,
        port=args.debug_port,
        delay_seconds=args.delay,
        jitter_seconds=args.jitter,
    )
    finder._not_found_timeout_ms = int(args.lookup_timeout * 1000)
    await finder.start(first_run_setup=args.setup)
    found_total = errors_total = 0

    try:
        use_batch_pauses = args.continuous and args.batch_cooldown > 0

        if use_batch_pauses:
            pos = 0
            while pos < len(indices):
                batch_end = min(pos + args.batch_size, len(indices))
                batch = indices[pos:batch_end]
                print(
                    f"\n--- Batch {pos // args.batch_size + 1}: "
                    f"founders {pos + 1}–{batch_end} of {len(indices)} ---\n",
                    flush=True,
                )
                for i, idx in enumerate(batch, start=pos + 1):
                    f, e, hit_rl = await _process_one(
                        finder, api_client, args, df, path, i, len(indices), idx
                    )
                    found_total += f
                    errors_total += e
                pos += len(batch)
                if pos < len(indices):
                    await cooldown_minutes(args.batch_cooldown, label="Batch complete")
        else:
            for i, idx in enumerate(indices, start=1):
                f, e, _hit_rl = await _process_one(
                    finder, api_client, args, df, path, i, len(indices), idx
                )
                found_total += f
                errors_total += e
    finally:
        await finder.close()
        if api_client:
            api_client.close()

    save_df(path, df)
    print(f"\nDone. Found: {found_total} | Errors: {errors_total} | Saved: {path}")


def run_manual(args: argparse.Namespace) -> None:
    from src.mailmeteor_user_browser import prompt_email

    path = Path(args.output)
    df = load_results_csv(path)
    indices = [i for i, row in df.iterrows() if needs_email(row)]
    if args.limit:
        indices = indices[: args.limit]
    print(f"Founders needing email lookup: {len(indices)}", flush=True)
    found = 0
    for n, idx in enumerate(indices, 1):
        row = df.loc[idx]
        email, status = prompt_email(
            _cell_str(row["linkedin_url"]),
            _cell_str(row.get("startup_name")),
            _cell_str(row.get("founder_name")),
        )
        df.at[idx, "email"] = email
        df.at[idx, "email_status"] = status
        if email:
            found += 1
        if n % 3 == 0:
            save_df(path, df)
    save_df(path, df)
    print(f"Done. Found: {found}")


def main() -> None:
    p = argparse.ArgumentParser(description="Fill emails in results.csv")
    p.add_argument("--output", default=str(DEFAULT_OUTPUT))
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--delay", type=float, default=3.0, help="Seconds between lookups (default 3)")
    p.add_argument("--jitter", type=float, default=1.5, help="Random extra delay (seconds)")
    p.add_argument(
        "--lookup-timeout",
        type=float,
        default=22.0,
        help="Max seconds to wait per Mailmeteor result (default 22)",
    )
    p.add_argument(
        "--fast",
        action="store_true",
        help="Fast run, no scheduled pauses (default for run-emails.ps1)",
    )
    p.add_argument(
        "--rate-limit-wait",
        type=float,
        default=12.0,
        help="Minutes to wait on single rate-limit before retry (default 12)",
    )
    p.add_argument(
        "--continuous",
        action="store_true",
        help="Auto batch + cooldown — best for full 1500+ run",
    )
    p.add_argument("--batch-size", type=int, default=75, help="Founders per batch in continuous mode")
    p.add_argument(
        "--batch-cooldown",
        type=float,
        default=45.0,
        help="Minutes pause between batches (continuous mode)",
    )
    p.add_argument(
        "--browser",
        choices=("brave", "chrome"),
        default="brave",
        help="Browser for Mailmeteor automation (default: brave)",
    )
    p.add_argument("--debug-port", type=int, default=9222, help="CDP port (default 9222)")
    p.add_argument(
        "--setup",
        action="store_true",
        help="First run: wait 30s for Cloudflare in the browser",
    )
    p.add_argument(
        "--manual",
        action="store_true",
        help="Fallback: open your browser and paste each email",
    )
    args = p.parse_args()

    if args.fast:
        args.delay = 2.0
        args.jitter = 1.0
        args.rate_limit_wait = 8.0
        args.lookup_timeout = 18.0
        args.continuous = False
        args.batch_cooldown = 0

    if args.manual:
        run_manual(args)
    else:
        asyncio.run(run_auto(args))


if __name__ == "__main__":
    main()
