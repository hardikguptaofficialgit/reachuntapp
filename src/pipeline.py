"""Main enrichment pipeline: Excel -> YC founders -> Mailmeteor emails -> CSV."""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pandas as pd

from src.mailmeteor import MailmeteorFinder
from src.yc_founders import fetch_founders
from src.yc_index import YCIndex

FIELDNAMES = [
    "startup_name",
    "founder_name",
    "linkedin_url",
    "email",
    "email_status",
    "yc_company_name",
    "yc_company_url",
    "notes",
]

DEFAULT_INPUT = Path(__file__).resolve().parent.parent / "data" / "yc_startups.xlsx"
DEFAULT_OUTPUT = Path(__file__).resolve().parent.parent / "output" / "results.csv"
PROGRESS_PATH = Path(__file__).resolve().parent.parent / "data" / "progress.json"


def load_progress() -> dict:
    if PROGRESS_PATH.exists():
        return json.loads(PROGRESS_PATH.read_text(encoding="utf-8"))
    return {"completed_startups": [], "rows": []}


def save_progress(progress: dict) -> None:
    PROGRESS_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROGRESS_PATH.write_text(json.dumps(progress, indent=2), encoding="utf-8")


def read_startup_names(path: Path, column: str = "Startup") -> list[str]:
    df = pd.read_excel(path)
    if column not in df.columns:
        raise ValueError(f"Column '{column}' not found. Columns: {list(df.columns)}")
    return df[column].dropna().astype(str).str.strip().tolist()


def append_csv_row(output_path: Path, row: dict) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    exists = output_path.exists()
    with output_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if not exists:
            writer.writeheader()
        writer.writerow({k: row.get(k, "") for k in FIELDNAMES})


def write_full_csv(output_path: Path, rows: list[dict]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in FIELDNAMES})


async def run_pipeline(args: argparse.Namespace) -> None:
    args.skip_startup_on_error = not args.no_skip_startup_on_error

    names = read_startup_names(Path(args.input), args.column)
    if args.offset:
        names = names[args.offset :]
    if args.limit:
        names = names[: args.limit]

    progress = load_progress()
    done = set(progress.get("completed_startups", []))
    all_rows: list[dict] = list(progress.get("rows", []))

    if args.reset:
        progress = {"completed_startups": [], "rows": []}
        done = set()
        all_rows = []
        save_progress(progress)

    index = YCIndex.load(refresh=args.refresh_yc)
    output_path = Path(args.output)

    if args.reset and output_path.exists():
        output_path.unlink()

    mailmeteor: MailmeteorFinder | None = None
    if not args.skip_email:
        cdp = f"http://127.0.0.1:{args.connect_chrome}" if args.connect_chrome else None
        mailmeteor = MailmeteorFinder(
            delay_seconds=args.delay,
            connect_cdp=cdp,
            manual_click=args.manual_mailmeteor,
        )
        await mailmeteor.start()
        if args.warmup_mailmeteor:
            await mailmeteor.warmup(interactive=True)
        elif not args.connect_chrome:
            print(
                "Mailmeteor: Chrome will open for each lookup.\n"
                "First time? Use --warmup-mailmeteor to complete any browser challenge.\n",
                flush=True,
            )

    client = httpx.Client(
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
        follow_redirects=True,
        timeout=60,
    )

    try:
        for i, startup_name in enumerate(names, 1):
            if startup_name in done and not args.force:
                print(f"[{i}/{len(names)}] skip (done): {startup_name}")
                continue

            print(f"[{i}/{len(names)}] {startup_name}")
            company = index.match(startup_name, min_score=args.min_score)
            if not company:
                row = {
                    "startup_name": startup_name,
                    "founder_name": "",
                    "linkedin_url": "",
                    "email": "",
                    "email_status": "",
                    "yc_company_name": "",
                    "yc_company_url": "",
                    "notes": "yc_not_found",
                }
                all_rows.append(row)
                append_csv_row(output_path, row)
                done.add(startup_name)
                progress["completed_startups"] = sorted(done)
                progress["rows"] = all_rows
                save_progress(progress)
                continue

            founders = fetch_founders(company.url, client=client)
            if not founders:
                row = {
                    "startup_name": startup_name,
                    "founder_name": "",
                    "linkedin_url": "",
                    "email": "",
                    "email_status": "",
                    "yc_company_name": company.name,
                    "yc_company_url": company.url,
                    "notes": "no_founders_on_page",
                }
                all_rows.append(row)
                append_csv_row(output_path, row)
            else:
                startup_rows: list[dict] = []
                any_email = False
                abort_startup = False

                for founder in founders:
                    if abort_startup:
                        break

                    email = ""
                    email_status = "skipped" if args.skip_email else ""
                    if mailmeteor:
                        try:
                            email, email_status = await mailmeteor.find_email_with_delay(
                                founder.linkedin_url
                            )
                        except Exception as exc:
                            email_status = "error"
                            print(f"  -> {founder.name}: error ({exc}), moving on", flush=True)

                    if email_status == "found" and email:
                        any_email = True

                    note = ""
                    if email_status in ("not_found", "error") and not email:
                        note = "no_email"

                    row = {
                        "startup_name": startup_name,
                        "founder_name": founder.name,
                        "linkedin_url": founder.linkedin_url,
                        "email": email,
                        "email_status": email_status,
                        "yc_company_name": company.name,
                        "yc_company_url": company.url,
                        "notes": note,
                    }
                    startup_rows.append(row)
                    all_rows.append(row)
                    append_csv_row(output_path, row)
                    print(f"  -> {founder.name}: {email or email_status}", flush=True)

                    # Mailmeteor broken (Cloudflare) — skip remaining founders for this startup
                    if mailmeteor and email_status == "error" and args.skip_startup_on_error:
                        print(f"  (skipping rest of {startup_name})", flush=True)
                        abort_startup = True

                if mailmeteor and not any_email and startup_rows:
                    print(f"  (no emails for {startup_name} — continuing to next startup)", flush=True)
                    for row in startup_rows:
                        if row["notes"] == "no_email":
                            row["notes"] = "no_emails_for_startup"

            done.add(startup_name)
            progress["completed_startups"] = sorted(done)
            progress["rows"] = all_rows
            save_progress(progress)

    finally:
        client.close()
        if mailmeteor:
            await mailmeteor.close()

    write_full_csv(output_path, all_rows)

    found = sum(1 for r in all_rows if r.get("email_status") == "found" and r.get("email"))
    no_mail_startups = len(
        {
            r["startup_name"]
            for r in all_rows
            if r.get("notes") == "no_emails_for_startup"
        }
    )
    print(f"\nDone. Wrote {len(all_rows)} rows to {output_path}")
    print(f"  Emails found: {found}")
    print(f"  Startups with no emails (skipped forward): {no_mail_startups}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="YC founder LinkedIn + Mailmeteor email enrichment")
    p.add_argument("--input", default=str(DEFAULT_INPUT), help="Path to startups.xlsx")
    p.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Output CSV path")
    p.add_argument("--column", default="Startup", help="Excel column with startup names")
    p.add_argument("--limit", type=int, default=0, help="Process only first N startups")
    p.add_argument("--offset", type=int, default=0, help="Skip first N startups")
    p.add_argument("--min-score", type=int, default=82, help="YC fuzzy match threshold")
    p.add_argument("--delay", type=float, default=5.0, help="Seconds between Mailmeteor lookups")
    p.add_argument(
        "--warmup-mailmeteor",
        action="store_true",
        help="Open Mailmeteor first and wait for Cloudflare (run once)",
    )
    p.add_argument(
        "--connect-chrome",
        type=int,
        default=0,
        metavar="PORT",
        help="Use your Chrome on port 9222 (see README)",
    )
    p.add_argument("--skip-email", action="store_true", help="Only fetch LinkedIn URLs")
    p.add_argument(
        "--manual-mailmeteor",
        action="store_true",
        help="Prefill URL and wait for YOU to click FIND EMAIL (avoids 'Oops')",
    )
    p.add_argument(
        "--no-skip-startup-on-error",
        action="store_true",
        help="Still try every founder if Mailmeteor returns error",
    )
    p.add_argument("--refresh-yc", action="store_true", help="Re-download YC company index")
    p.add_argument("--reset", action="store_true", help="Clear progress and output")
    p.add_argument("--force", action="store_true", help="Re-process startups already marked done")
    return p


def main() -> None:
    args = build_parser().parse_args()
    asyncio.run(run_pipeline(args))


if __name__ == "__main__":
    main()
