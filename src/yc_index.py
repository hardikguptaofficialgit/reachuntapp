"""YC company index from yc-oss API with fuzzy name matching."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

import httpx
from rapidfuzz import fuzz, process

YC_ALL_URL = "https://yc-oss.github.io/api/companies/all.json"
CACHE_PATH = Path(__file__).resolve().parent.parent / "data" / "yc_companies.json"


def normalize_name(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "", s)
    return s


@dataclass
class YCCompany:
    name: str
    slug: str
    url: str
    website: str | None


class YCIndex:
    def __init__(self, companies: list[dict]):
        self._companies = companies
        self._by_norm: dict[str, dict] = {}
        self._choices: list[str] = []
        for c in companies:
            names = [c.get("name", "")]
            names.extend(c.get("former_names") or [])
            slug = c.get("slug", "")
            if slug:
                names.append(slug.replace("-", " "))
            for n in names:
                norm = normalize_name(n)
                if norm and norm not in self._by_norm:
                    self._by_norm[norm] = c
            norm_main = normalize_name(c.get("name", ""))
            if norm_main:
                self._choices.append(norm_main)

    @classmethod
    def load(cls, refresh: bool = False) -> "YCIndex":
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        if CACHE_PATH.exists() and not refresh:
            companies = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        else:
            r = httpx.get(YC_ALL_URL, timeout=120)
            r.raise_for_status()
            companies = r.json()
            CACHE_PATH.write_text(json.dumps(companies), encoding="utf-8")
        return cls(companies)

    def match(self, startup_name: str, min_score: int = 82) -> YCCompany | None:
        norm_query = normalize_name(startup_name)
        if not norm_query:
            return None

        if norm_query in self._by_norm:
            return self._to_company(self._by_norm[norm_query])

        result = process.extractOne(
            norm_query,
            self._choices,
            scorer=fuzz.WRatio,
        )
        if not result:
            return None
        _choice, score, _ = result
        if score < min_score:
            return None
        raw = self._by_norm.get(_choice)
        if not raw:
            return None
        return self._to_company(raw)

    def _to_company(self, raw: dict) -> YCCompany:
        slug = raw.get("slug", "")
        return YCCompany(
            name=raw.get("name", ""),
            slug=slug,
            url=raw.get("url") or f"https://www.ycombinator.com/companies/{slug}",
            website=raw.get("website"),
        )
