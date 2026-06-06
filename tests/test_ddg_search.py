"""DuckDuckGo LinkedIn discovery — offline parsing + optional live smoke test."""

from __future__ import annotations

import os

import pytest

from src.ddg_search import (
    _founders_from_hits,
    _queries_for_person,
    ddg_search_enabled,
    search_linkedin_profiles_sync,
)


def test_ddg_enabled_by_default(monkeypatch):
    monkeypatch.delenv("DDG_SEARCH_ENABLED", raising=False)
    assert ddg_search_enabled() is True


def test_ddg_disabled_returns_empty(monkeypatch):
    monkeypatch.setenv("DDG_SEARCH_ENABLED", "false")
    hits = search_linkedin_profiles_sync(name="Jane Doe", domain="acme.com")
    assert hits == []


def test_queries_for_person_include_domain_and_linkedin():
    queries = _queries_for_person("Jane Doe", "acme.com")
    assert len(queries) >= 2
    joined = " ".join(queries).lower()
    assert "jane doe" in joined
    assert "linkedin.com/in" in joined
    assert "acme.com" in joined


def test_founders_from_hits_parses_linkedin_urls():
    hits = [
        {
            "title": "Jane Doe - CEO at Acme | LinkedIn",
            "href": "https://www.linkedin.com/in/jane-doe/",
            "body": "Founder at Acme",
        },
        {
            "title": "Feed | LinkedIn",
            "href": "https://www.linkedin.com/in/feed/",
            "body": "",
        },
    ]
    founders = _founders_from_hits(hits)
    assert len(founders) == 1
    assert founders[0].name == "Jane Doe"
    assert founders[0].linkedin_url == "https://www.linkedin.com/in/jane-doe/"


@pytest.mark.skipif(
    os.environ.get("DDG_INTEGRATION") != "1",
    reason="Set DDG_INTEGRATION=1 for live DuckDuckGo smoke test",
)
def test_ddg_live_smoke():
    """Requires network; run: DDG_INTEGRATION=1 pytest tests/test_ddg_search.py -k live"""
    results = search_linkedin_profiles_sync(
        name="Ethan Hilton",
        domain="caseflood.ai",
        max_results=3,
    )
    assert len(results) >= 1
    assert all("linkedin.com/in/" in f.linkedin_url for f in results)
