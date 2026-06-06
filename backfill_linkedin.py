"""Re-fetch LinkedIn for startups missing founder URLs in results.csv."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import httpx
import pandas as pd

from src.yc_founders import fetch_founders
from src.yc_index import YCIndex
from src.pipeline import FIELDNAMES, PROGRESS_PATH, DEFAULT_OUTPUT

OUTPUT = Path(DEFAULT_OUTPUT)


def has_linkedin(url: object) -> bool:
    s = str(url or "")
    return "linkedin.com/in/" in s


def main() -> None:
    if not OUTPUT.exists():
        print(f"Missing {OUTPUT}. Run the main pipeline first.")
        sys.exit(1)

    df = pd.read_csv(OUTPUT)
    by_startup = df.groupby("startup_name", sort=False)

    missing_startups: list[str] = []
    for name, grp in by_startup:
        if not grp["linkedin_url"].apply(has_linkedin).any():
            missing_startups.append(name)

    print(f"Startups missing LinkedIn: {len(missing_startups)}")

    index = YCIndex.load()
    client = httpx.Client(
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
        follow_redirects=True,
        timeout=60,
    )

    new_rows: list[dict] = []
    fixed = 0
    still_missing = 0

    try:
        for i, startup_name in enumerate(missing_startups, 1):
            print(f"[{i}/{len(missing_startups)}] {startup_name}", flush=True)
            company = index.match(startup_name)
            if not company:
                print("  yc_not_found")
                still_missing += 1
                continue

            founders = fetch_founders(company.url, client=client)
            if not founders:
                print("  still no founders on page")
                still_missing += 1
                continue

            fixed += 1
            for f in founders:
                row = {
                    "startup_name": startup_name,
                    "founder_name": f.name,
                    "linkedin_url": f.linkedin_url,
                    "email": "",
                    "email_status": "",
                    "yc_company_name": company.name,
                    "yc_company_url": company.url,
                    "notes": "backfilled_linkedin",
                }
                new_rows.append(row)
                print(f"  -> {f.name}: {f.linkedin_url}", flush=True)
    finally:
        client.close()

    if not new_rows:
        print("Nothing new to add.")
        return

    # Remove old placeholder rows for fixed startups
    fixed_names = {r["startup_name"] for r in new_rows}
    df = df[~((df["startup_name"].isin(fixed_names)) & (~df["linkedin_url"].apply(has_linkedin)))]
    df_new = pd.DataFrame(new_rows)
    df = pd.concat([df, df_new], ignore_index=True)
    df.to_csv(OUTPUT, index=False, encoding="utf-8")

    if PROGRESS_PATH.exists():
        progress = json.loads(PROGRESS_PATH.read_text(encoding="utf-8"))
        progress["rows"] = df.to_dict(orient="records")
        PROGRESS_PATH.write_text(json.dumps(progress, indent=2), encoding="utf-8")

    total_li = df["linkedin_url"].apply(has_linkedin).sum()
    print(f"\nBackfill done. Fixed startups: {fixed}. Still missing: {still_missing}")
    print(f"Updated {OUTPUT} — rows with LinkedIn: {total_li} / {len(df)}")


if __name__ == "__main__":
    main()
