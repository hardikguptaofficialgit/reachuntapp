"""Safe read/write for CSV (Excel lock handling, string columns)."""

from __future__ import annotations

import csv
import time
from pathlib import Path

import pandas as pd

from src.pipeline import FIELDNAMES as DEFAULT_FIELDNAMES


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


def prepare_results_df(df: pd.DataFrame, fieldnames: list[str] | None = None) -> pd.DataFrame:
    cols = fieldnames or list(df.columns)
    out = df.copy()
    for col in cols:
        if col in out.columns:
            out[col] = out[col].fillna("").astype(str)
            out[col] = out[col].replace({"nan": "", "None": ""})
    return out


def load_results_csv(path: Path, fieldnames: list[str] | None = None) -> pd.DataFrame:
    df = pd.read_csv(path)
    return prepare_results_df(df, fieldnames)


def safe_write_results_csv(
    path: Path,
    df: pd.DataFrame,
    fieldnames: list[str] | None = None,
    max_retries: int = 8,
) -> None:
    path = Path(path)
    cols = fieldnames or list(df.columns)
    df = prepare_results_df(df, cols)
    rows = df.to_dict(orient="records")
    tmp = path.with_suffix(".csv.tmp")

    for attempt in range(max_retries):
        try:
            write_csv(tmp, rows, cols)
            tmp.replace(path)
            return
        except PermissionError:
            if attempt < max_retries - 1:
                print(
                    "  Cannot save CSV — close the file in Excel, retrying in 3s...",
                    flush=True,
                )
                time.sleep(3)
                continue
            fallback = path.parent / f"results_backup_{int(time.time())}.csv"
            write_csv(fallback, rows, cols)
            raise PermissionError(
                f"Could not write to {path} (file locked?).\n"
                f"Close Excel and copy from backup:\n  {fallback}"
            ) from None
