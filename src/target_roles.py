"""Target roles for company-only lookups (founder, VP Eng, etc.)."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class TargetRole:
    id: str
    label: str
    hint: str
    search_terms: tuple[str, ...]
    score_re: re.Pattern


def _role(
    id: str,
    label: str,
    hint: str,
    search_terms: tuple[str, ...],
    score_pattern: str,
) -> TargetRole:
    return TargetRole(
        id=id,
        label=label,
        hint=hint,
        search_terms=search_terms,
        score_re=re.compile(score_pattern, re.I),
    )


TARGET_ROLES: tuple[TargetRole, ...] = (
    _role(
        "founder",
        "Founder / CEO",
        "Co-founder, CEO, or owner",
        ("founder", "CEO", "co-founder", "chief executive"),
        r"\b(founder|co-founder|cofounder|ceo|chief executive|owner|president)\b",
    ),
    _role(
        "cto",
        "CTO",
        "Chief technology officer",
        ("CTO", "chief technology officer", "head of technology"),
        r"\b(cto|chief technology officer|head of technology)\b",
    ),
    _role(
        "vp-engineering",
        "VP Engineering",
        "Engineering leadership",
        (
            "VP Engineering",
            "VP of Engineering",
            "vice president engineering",
            "head of engineering",
            "engineering director",
        ),
        r"\b(vp|vice president|svp|head of|director).{0,24}(engineering|engineer)|"
        r"\b(engineering|engineer).{0,24}(vp|vice president|head)\b",
    ),
    _role(
        "vp-sales",
        "VP Sales",
        "Revenue & sales leadership",
        ("VP Sales", "VP of Sales", "chief revenue officer", "head of sales", "CRO"),
        r"\b(vp|vice president|svp|head of|chief).{0,20}(sales|revenue)|"
        r"\b(cro|chief revenue officer)\b",
    ),
    _role(
        "vp-marketing",
        "VP Marketing",
        "Marketing leadership",
        ("VP Marketing", "VP of Marketing", "CMO", "chief marketing officer"),
        r"\b(vp|vice president|svp|head of|chief).{0,20}marketing|"
        r"\b(cmo|chief marketing officer)\b",
    ),
    _role(
        "vp-product",
        "VP Product",
        "Product leadership",
        ("VP Product", "VP of Product", "head of product", "chief product officer", "CPO"),
        r"\b(vp|vice president|svp|head of|chief).{0,20}product|"
        r"\b(cpo|chief product officer)\b",
    ),
    _role(
        "hr",
        "HR / People",
        "People ops & talent",
        ("head of people", "HR director", "chief people officer", "talent acquisition"),
        r"\b(hr|human resources|people ops|chief people|talent|recruiting)\b",
    ),
    _role(
        "engineering-manager",
        "Engineering Manager",
        "Eng managers & leads",
        ("engineering manager", "director of engineering", "eng lead"),
        r"\b(engineering manager|eng manager|director of engineering|engineering lead)\b",
    ),
)

DEFAULT_TARGET_ROLE = "founder"

_ROLES_BY_ID = {r.id: r for r in TARGET_ROLES}


def get_target_role(role_id: str | None) -> TargetRole:
    if role_id and role_id in _ROLES_BY_ID:
        return _ROLES_BY_ID[role_id]
    return _ROLES_BY_ID.get(DEFAULT_TARGET_ROLE, TARGET_ROLES[0])


def list_target_roles() -> list[dict[str, str]]:
    return [
        {"id": r.id, "label": r.label, "hint": r.hint}
        for r in TARGET_ROLES
    ]


def linkedin_queries_for_role(company_label: str, domain: str, role_id: str) -> list[str]:
    role = get_target_role(role_id)
    label = company_label.strip()
    dom = domain.lower().strip()
    company = label or dom.split(".")[0].replace("-", " ").title()
    out: list[str] = []
    for term in role.search_terms:
        out.append(f"{company} {term}")
        if dom:
            out.append(f"{company} {term} {dom}")
    out.append(f"{company} site:linkedin.com/in")
    seen: set[str] = set()
    deduped: list[str] = []
    for q in out:
        k = q.lower()
        if k not in seen:
            seen.add(k)
            deduped.append(q)
    return deduped[:8]
