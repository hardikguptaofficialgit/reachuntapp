"""Smart ranking for LinkedIn search candidates."""

from __future__ import annotations

import re

from rapidfuzz import fuzz

from src.linkedin_founders import FOUNDER_KEYWORDS, LinkedInFounder, clean_linkedin_profile_name
from src.target_roles import TargetRole, get_target_role

DOMAIN_FRAGMENT_RE = re.compile(r"[a-z0-9-]+", re.I)

STUDENT_HINTS = re.compile(
    r"\b("
    r"pgdm|pgdbm|mba\b|m\.?ba|b\.?tech|b\.?e\.?|ms\b|m\.?sc|"
    r"student|intern\b|aspiring|fresher|graduate\s+student|"
    r"pursuing|seeking|looking for|campus|"
    r"jims\b|iim\b|university|college|institute of|"
    r"'2[4-9]|20[2-3][0-9]\s*[-–]\s*20[2-3][0-9]"
    r")\b",
    re.I,
)

CURRENT_ROLE_HINTS = re.compile(
    r"\b("
    r"product owner|product manager|founder|co-founder|cofounder|ceo|cto|"
    r"director|head of|vp |vice president|manager|lead|engineer|"
    r"consultant|analyst|owner|president|partner"
    r")\b",
    re.I,
)

STRONG_MATCH_SCORE = 85
MIN_MATCH_SCORE = 60


def _domain_tokens(domain: str) -> set[str]:
    base = _company_base(domain)
    tokens = {base} if base else set()
    for part in DOMAIN_FRAGMENT_RE.findall(base):
        if len(part) >= 3:
            tokens.add(part.lower())
    return tokens


def _company_base(domain: str) -> str:
    return domain.lower().split(".")[0].strip()


def _company_label(domain: str) -> str:
    base = _company_base(domain)
    if not base:
        return ""
    return base.replace("-", " ").title()


def _name_matches(candidate: str, target: str) -> int:
    c = re.sub(r"\s+", " ", clean_linkedin_profile_name(candidate).lower()).strip()
    t = re.sub(r"\s+", " ", clean_linkedin_profile_name(target).lower()).strip()
    if not c or not t:
        return 0

    t_parts = t.split()
    c_parts = c.split()
    if len(t_parts) >= 2 and len(c_parts) >= 2:
        if t_parts[-1] != c_parts[-1]:
            return 0
        if fuzz.ratio(t_parts[0], c_parts[0]) < 82:
            return 0

    if c == t:
        return 100
    if t in c or c in t:
        return 92
    score = int(fuzz.token_sort_ratio(c, t))
    if len(t_parts) >= 2 and len(c_parts) >= 2 and t_parts[0] == c_parts[0]:
        score = max(score, 88)
    return score


def _works_at_company(text: str, domain: str) -> bool:
    base = _company_base(domain)
    if not base or len(base) < 2:
        return False
    low = text.lower()
    if domain.lower() in low:
        return True
    if base == "linkitapp" and re.search(r"\blinkit\b", low):
        return True
    label = _company_label(domain).lower()
    if label and label in low:
        return True
    emp_pat = (
        rf"(?:@|at)\s+{re.escape(base)}\b|"
        rf"{re.escape(base)}\s+(?:limited|ltd|inc|group|company)\b"
    )
    if re.search(emp_pat, low, re.I):
        return True
    if re.search(rf"\b{re.escape(base)}\b", low) and (
        "@" in low or " at " in low or f"{base} limited" in low or f"{base} ltd" in low
    ):
        return True
    return False


def _student_only_profile(text: str, domain: str) -> bool:
    if not STUDENT_HINTS.search(text):
        return False
    return not _works_at_company(text, domain)


def score_candidate(
    founder: LinkedInFounder,
    target_name: str,
    domain: str,
    *,
    rank: int = 0,
) -> int:
    name_score = _name_matches(founder.name, target_name)
    if name_score < 50:
        return 0

    text = f"{founder.title_hint} {founder.name}".lower()
    base = _company_base(domain)

    score = name_score
    at_company = _works_at_company(text, domain)

    if at_company:
        score += 55
        if CURRENT_ROLE_HINTS.search(text):
            score += 14
        if FOUNDER_KEYWORDS.search(text):
            score += 10
    else:
        domain_hits = sum(1 for tok in _domain_tokens(domain) if tok in text)
        score += min(domain_hits * 10, 18)
        if CURRENT_ROLE_HINTS.search(text) and base and re.search(rf"\b{re.escape(base)}\b", text):
            score += 12

    if "1st" in text or "· 1st" in text or "1st degree" in text:
        score += 6

    if _student_only_profile(text, domain):
        score -= 60

    if STUDENT_HINTS.search(text) and at_company:
        score -= 8

    if re.search(r"\b(former|ex-|ex )\b", text) and at_company:
        score -= 12

    score += max(0, 24 - rank * 4)

    return score


MIN_COMPANY_MATCH_SCORE = 48


def score_company_founder(
    founder: LinkedInFounder,
    domain: str,
    *,
    rank: int = 0,
) -> int:
    """Rank founders when the user only provided a startup/company."""
    return score_company_role(founder, domain, get_target_role("founder"), rank=rank)


def score_company_role(
    founder: LinkedInFounder,
    domain: str,
    role: TargetRole,
    *,
    rank: int = 0,
) -> int:
    """Rank profiles for a company-only lookup and a chosen target role."""
    text = f"{founder.title_hint} {founder.name}".lower()
    score = 0
    at_company = _works_at_company(text, domain)

    if role.score_re.search(text):
        score += 48
    elif CURRENT_ROLE_HINTS.search(text):
        score += 18
    elif FOUNDER_KEYWORDS.search(text) and role.id == "founder":
        score += 42

    if at_company:
        score += 50
    else:
        domain_hits = sum(1 for tok in _domain_tokens(domain) if tok in text)
        score += min(domain_hits * 14, 28)

    if _student_only_profile(text, domain):
        score -= 45

    if re.search(r"\b(former|ex-|ex )\b", text) and at_company:
        score -= 15

    score += max(0, 22 - rank * 3)
    return score


def pick_best_for_company(
    candidates: list[LinkedInFounder],
    domain: str,
) -> tuple[LinkedInFounder | None, int]:
    return pick_best_for_role(candidates, domain, "founder")


def pick_best_for_role(
    candidates: list[LinkedInFounder],
    domain: str,
    role_id: str,
) -> tuple[LinkedInFounder | None, int]:
    if not candidates:
        return None, 0

    role = get_target_role(role_id)
    scored: list[tuple[LinkedInFounder, int, bool, int]] = []
    for i, c in enumerate(candidates):
        text = f"{c.title_hint} {c.name}"
        s = score_company_role(c, domain, role, rank=i)
        if s >= MIN_COMPANY_MATCH_SCORE:
            scored.append((c, s, _works_at_company(text, domain), i))

    if not scored:
        return None, 0

    scored.sort(key=lambda x: (x[1], x[2], -x[3]), reverse=True)
    best, best_score, _, _ = scored[0]
    return best, best_score


def pick_best(
    candidates: list[LinkedInFounder],
    target_name: str,
    domain: str,
) -> tuple[LinkedInFounder | None, int]:
    if not candidates:
        return None, 0

    scored: list[tuple[LinkedInFounder, int, bool, int]] = []
    for i, c in enumerate(candidates):
        text = f"{c.title_hint} {c.name}"
        s = score_candidate(c, target_name, domain, rank=i)
        if s >= MIN_MATCH_SCORE:
            scored.append((c, s, _works_at_company(text, domain), i))

    if not scored:
        return None, 0

    scored.sort(key=lambda x: (x[1], x[2], -x[3]), reverse=True)
    best, best_score, _, _ = scored[0]
    return best, best_score


def build_search_queries(name: str, domain: str) -> list[str]:
    domain = domain.lower().strip()
    base = _company_base(domain)
    company = _company_label(domain)
    queries = [f"{name} {domain}"]
    if company:
        queries.append(f"{name} {company}")
    if base and base != company.lower():
        queries.append(f"{name} {base}")
    parts = name.split()
    if len(parts) > 1 and company:
        queries.append(f"{parts[0]} {company}")
    seen: set[str] = set()
    out: list[str] = []
    for q in queries:
        k = q.lower().strip()
        if k not in seen:
            seen.add(k)
            out.append(q)
    return out
