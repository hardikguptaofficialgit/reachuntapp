"""Pipeline: startupsnew.xlsx → LinkedIn founders → Mailmeteor emails → CSV."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

import pandas as pd

from src.browser_cdp import CdpBrowser
from src.csv_store import load_results_csv, prepare_results_df, safe_write_results_csv
from src.email_lookup import lookup_email
from src.email_providers import get_api_client
from src.linkedin_founders import search_founders, setup_linkedin_login
from src.mailmeteor_auto import MailmeteorAuto

DEFAULT_INPUT = Path(r"C:\Users\hardi\Downloads\startupsnew.xlsx")
DEFAULT_OUTPUT = Path(__file__).resolve().parent.parent / "output" / "startupsnew_results.csv"
PROGRESS_PATH = Path(__file__).resolve().parent.parent / "data" / "startupsnew_progress.json"

FIELDNAMES = [
    "startup_name",
    "founder_name",
    "linkedin_url",
    "email",
    "email_status",
    "notes",
]


def load_progress() -> dict:
    if PROGRESS_PATH.exists():
        return json.loads(PROGRESS_PATH.read_text(encoding="utf-8"))
    return {"completed_startups": [], "rows": []}


def save_progress(progress: dict) -> None:
    PROGRESS_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROGRESS_PATH.write_text(json.dumps(progress, indent=2), encoding="utf-8")


def read_startups(path: Path, column: str = "Startup Name") -> list[str]:
    df = pd.read_excel(path)
    if column not in df.columns:
        raise ValueError(f"Column '{column}' not found. Columns: {list(df.columns)}")
    return df[column].dropna().astype(str).str.strip().tolist()


def rows_to_df(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    for col in FIELDNAMES:
        if col not in df.columns:
            df[col] = ""
    return prepare_results_df(df[FIELDNAMES])


def append_rows(path: Path, all_rows: list[dict]) -> None:
    safe_write_results_csv(path, rows_to_df(all_rows), fieldnames=FIELDNAMES)


def has_linkedin(url: str) -> bool:
    return "linkedin.com/in/" in str(url or "")


def needs_email(row: dict) -> bool:
    if not has_linkedin(row.get("linkedin_url", "")):
        return False
    email = str(row.get("email") or "").strip()
    return not email or email.lower() == "nan"


async def run_linkedin_phase(args: argparse.Namespace) -> None:
    names = read_startups(Path(args.input), args.column)
    if args.offset:
        names = names[args.offset :]
    if args.limit:
        names = names[: args.limit]

    progress = load_progress()
    done = set(progress.get("completed_startups", []))
    all_rows: list[dict] = list(progress.get("rows", []))
    output_path = Path(args.output)

    if args.reset:
        progress = {"completed_startups": [], "rows": []}
        done = set()
        all_rows = []
        save_progress(progress)
        if output_path.exists():
            output_path.unlink()

    browser = CdpBrowser(
        browser=args.browser,
        profile_name="brave-linkedin",
        port=args.linkedin_port,
    )
    page = await browser.start("https://www.linkedin.com/feed/")

    if args.setup_linkedin:
        await setup_linkedin_login(page)

    try:
        for i, startup in enumerate(names, 1):
            if startup in done and not args.force:
                print(f"[{i}/{len(names)}] skip (done): {startup}", flush=True)
                continue

            print(f"[{i}/{len(names)}] {startup}", flush=True)
            try:
                founders = await search_founders(page, startup, max_founders=args.max_founders)
            except Exception as exc:
                print(f"  LinkedIn error: {exc}", flush=True)
                row = {
                    "startup_name": startup,
                    "founder_name": "",
                    "linkedin_url": "",
                    "email": "",
                    "email_status": "",
                    "notes": f"linkedin_error: {exc}",
                }
                all_rows.append(row)
                append_rows(output_path, all_rows)
                done.add(startup)
                progress["completed_startups"] = sorted(done)
                progress["rows"] = all_rows
                save_progress(progress)
                await asyncio.sleep(args.linkedin_delay)
                continue

            if not founders:
                print("  no founders found on LinkedIn", flush=True)
                row = {
                    "startup_name": startup,
                    "founder_name": "",
                    "linkedin_url": "",
                    "email": "",
                    "email_status": "",
                    "notes": "no_linkedin_found",
                }
                all_rows.append(row)
                append_rows(output_path, all_rows)
            else:
                for f in founders:
                    print(f"  -> {f.name}: {f.linkedin_url}", flush=True)
                    all_rows.append(
                        {
                            "startup_name": startup,
                            "founder_name": f.name,
                            "linkedin_url": f.linkedin_url,
                            "email": "",
                            "email_status": "",
                            "notes": "",
                        }
                    )
                append_rows(output_path, all_rows)

            done.add(startup)
            progress["completed_startups"] = sorted(done)
            progress["rows"] = all_rows
            save_progress(progress)
            await asyncio.sleep(args.linkedin_delay)
    finally:
        await browser.close()

    print(f"\nLinkedIn phase done. {len(all_rows)} rows → {output_path}")


async def run_email_phase(args: argparse.Namespace) -> None:
    path = Path(args.output)
    if not path.exists():
        print(f"Run LinkedIn phase first. Missing {path}")
        sys.exit(1)

    df = load_results_csv(path)
    indices = [i for i, row in df.iterrows() if needs_email(row.to_dict())]
    if args.limit:
        indices = indices[: args.limit]

    print(f"Founders needing email: {len(indices)}", flush=True)
    if not indices:
        print("All emails done.")
        return

    api_client = get_api_client()
    mail = MailmeteorAuto(
        browser=args.browser,
        port=args.mailmeteor_port,
        delay_seconds=args.delay,
        jitter_seconds=args.jitter,
    )
    mail._not_found_timeout_ms = int(args.lookup_timeout * 1000)
    await mail.start()
    found = 0

    rows = df.to_dict(orient="records")
    try:
        for n, idx in enumerate(indices, 1):
            row = rows[idx]
            startup = str(row.get("startup_name", ""))
            founder = str(row.get("founder_name", ""))
            linkedin = str(row.get("linkedin_url", ""))
            print(f"[{n}/{len(indices)}] {startup} — {founder}", flush=True)
            try:
                email, status = await lookup_email(
                    mail,
                    linkedin,
                    rate_limit_wait_minutes=args.rate_limit_wait,
                    api_client=api_client,
                )
            except Exception as exc:
                email, status = "", "connection_error"
                print(f"  error: {exc}", flush=True)
                await mail.reconnect()

            rows[idx]["email"] = email
            rows[idx]["email_status"] = status
            if email:
                found += 1
                print(f"  => {email}", flush=True)
            else:
                print(f"  => ({status})", flush=True)

            safe_write_results_csv(path, rows_to_df(rows), fieldnames=FIELDNAMES)
            progress = load_progress()
            progress["rows"] = rows
            save_progress(progress)
    finally:
        await mail.close()
        if api_client:
            api_client.close()

    print(f"\nEmail phase done. Found {found} emails → {path}")


async def run_login_only(args: argparse.Namespace) -> None:
    browser = CdpBrowser(
        browser=args.browser,
        profile_name="brave-linkedin",
        port=args.linkedin_port,
    )
    page = await browser.start("https://www.linkedin.com/feed/")
    await setup_linkedin_login(page)
    await browser.close()
    print("\nLinkedIn login saved. Next run: .\\run-linkedin.ps1\n", flush=True)


async def run_all(args: argparse.Namespace) -> None:
    if args.login_only:
        await run_login_only(args)
        return
    if not args.emails_only:
        await run_linkedin_phase(args)
    if not args.linkedin_only:
        await run_email_phase(args)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Startups: LinkedIn founders + Mailmeteor emails")
    p.add_argument("--input", default=str(DEFAULT_INPUT))
    p.add_argument("--output", default=str(DEFAULT_OUTPUT))
    p.add_argument("--column", default="Startup Name")
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--offset", type=int, default=0)
    p.add_argument("--max-founders", type=int, default=5)
    p.add_argument("--linkedin-delay", type=float, default=5.0)
    p.add_argument("--linkedin-port", type=int, default=9223)
    p.add_argument("--mailmeteor-port", type=int, default=9222)
    p.add_argument("--browser", choices=("brave", "chrome"), default="brave")
    p.add_argument("--setup-linkedin", action="store_true", help="With LinkedIn phase: prompt login first")
    p.add_argument("--login-only", action="store_true", help="Only open Brave and log into LinkedIn")
    p.add_argument("--linkedin-only", action="store_true")
    p.add_argument("--emails-only", action="store_true")
    p.add_argument("--reset", action="store_true")
    p.add_argument("--force", action="store_true")
    p.add_argument("--delay", type=float, default=2.0)
    p.add_argument("--jitter", type=float, default=1.0)
    p.add_argument("--lookup-timeout", type=float, default=18.0)
    p.add_argument("--rate-limit-wait", type=float, default=8.0)
    return p


def main() -> None:
    args = build_parser().parse_args()
    asyncio.run(run_all(args))


if __name__ == "__main__":
    main()
