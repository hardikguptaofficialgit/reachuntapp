"""Query intent helpers for API responses."""

from __future__ import annotations

from enum import Enum

from src.query_common import DOMAIN_RE, clean_domain
from src.query_parse import PersonQuery


class QueryKind(str, Enum):
    PERSON = "person"
    COMPANY_DOMAIN = "company_domain"
    COMPANY_NAME = "company_name"


def query_kind_for(pq: PersonQuery) -> QueryKind:
    if not pq.company_only:
        return QueryKind.PERSON
    if DOMAIN_RE.match(clean_domain(pq.raw)) and " " not in pq.raw.strip():
        return QueryKind.COMPANY_DOMAIN
    return QueryKind.COMPANY_NAME


def parse_payload_from_query(pq: PersonQuery) -> dict:
    return {
        "ok": True,
        "name": pq.name,
        "domain": pq.domain,
        "company_only": pq.company_only,
        "company_label": pq.company_label,
        "query_kind": query_kind_for(pq).value,
    }
