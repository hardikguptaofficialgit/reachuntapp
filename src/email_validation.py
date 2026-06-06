"""Layered email validation and risk scoring.

The default path avoids SMTP because many mail hosts block recipient probing and
it can slow lookups. Set EMAIL_SMTP_VERIFY=true to enable the optional check.
"""

from __future__ import annotations

import os
import random
import smtplib
import socket
import string
from functools import lru_cache
from dataclasses import asdict, dataclass

from src.email_patterns import EMAIL_RE, GENERIC_LOCAL_PARTS, normalize_email
from src.query_common import DOMAIN_RE, clean_domain

DISPOSABLE_DOMAINS = {
    "10minutemail.com",
    "guerrillamail.com",
    "mailinator.com",
    "sharklasers.com",
    "tempmail.com",
    "temp-mail.org",
    "throwawaymail.com",
    "yopmail.com",
}

FREE_PROVIDERS = {
    "aol.com",
    "gmail.com",
    "googlemail.com",
    "hotmail.com",
    "icloud.com",
    "live.com",
    "outlook.com",
    "proton.me",
    "protonmail.com",
    "yahoo.com",
}


@dataclass(frozen=True)
class EmailValidation:
    email: str
    valid_syntax: bool
    domain_valid: bool
    mx_found: bool
    disposable: bool
    free_provider: bool
    role_account: bool
    smtp_checked: bool
    smtp_valid: bool | None
    catch_all: bool | None
    score: int
    verdict: str
    signals: list[str]

    def public_dict(self) -> dict:
        return asdict(self)


def smtp_verification_enabled() -> bool:
    return os.environ.get("EMAIL_SMTP_VERIFY", "false").lower() in ("1", "true", "yes")


def _smtp_timeout() -> float:
    try:
        return max(3.0, min(15.0, float(os.environ.get("EMAIL_SMTP_TIMEOUT_SEC", "8"))))
    except ValueError:
        return 8.0


@lru_cache(maxsize=4096)
def _domain_mx(domain: str) -> list[str]:
    try:
        import dns.resolver

        answers = dns.resolver.resolve(domain, "MX", lifetime=4)
        hosts = sorted(
            [(int(getattr(r, "preference", 0)), str(r.exchange).rstrip(".")) for r in answers],
            key=lambda row: row[0],
        )
        return [host for _, host in hosts if host]
    except Exception:
        return []


def _smtp_rcpt(email: str, mx_host: str) -> tuple[bool | None, str]:
    timeout = _smtp_timeout()
    try:
        with smtplib.SMTP(mx_host, 25, timeout=timeout) as smtp:
            smtp.helo("reachhunt.arclabs.page")
            smtp.mail("verify@reachhunt.arclabs.page")
            code, msg = smtp.rcpt(email)
        if 200 <= code < 300:
            return True, str(msg)
        if code in {550, 551, 552, 553}:
            return False, str(msg)
        return None, str(msg)
    except (OSError, smtplib.SMTPException, socket.timeout) as exc:
        return None, str(exc)


def _random_address(domain: str) -> str:
    token = "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(18))
    return f"no-such-{token}@{domain}"


def _smtp_check(email: str, domain: str, mx_hosts: list[str]) -> tuple[bool | None, bool | None]:
    if not mx_hosts:
        return None, None
    smtp_valid, _ = _smtp_rcpt(email, mx_hosts[0])
    catch_all: bool | None = None
    if smtp_valid is True:
        fake_valid, _ = _smtp_rcpt(_random_address(domain), mx_hosts[0])
        if fake_valid is True:
            catch_all = True
        elif fake_valid is False:
            catch_all = False
    return smtp_valid, catch_all


def validate_email(email: str, *, check_smtp: bool | None = None) -> EmailValidation:
    normalized = normalize_email(email)
    signals: list[str] = []
    valid_syntax = bool(EMAIL_RE.fullmatch(normalized))
    domain = clean_domain(normalized.split("@", 1)[1]) if "@" in normalized else ""
    domain_valid = bool(domain and DOMAIN_RE.match(domain))
    local = normalized.split("@", 1)[0] if "@" in normalized else ""
    disposable = domain in DISPOSABLE_DOMAINS
    free_provider = domain in FREE_PROVIDERS
    role_account = local in GENERIC_LOCAL_PARTS
    mx_hosts = _domain_mx(domain) if domain_valid else []
    mx_found = bool(mx_hosts)
    smtp_checked = bool(check_smtp if check_smtp is not None else smtp_verification_enabled())
    smtp_valid: bool | None = None
    catch_all: bool | None = None

    score = 0
    if valid_syntax:
        score += 25
        signals.append("syntax_ok")
    if domain_valid:
        score += 15
        signals.append("domain_ok")
    if mx_found:
        score += 25
        signals.append("mx_found")
    if disposable:
        score -= 45
        signals.append("disposable")
    if free_provider:
        score -= 12
        signals.append("free_provider")
    if role_account:
        score -= 18
        signals.append("role_account")

    if smtp_checked and mx_found:
        smtp_valid, catch_all = _smtp_check(normalized, domain, mx_hosts)
        if smtp_valid is True:
            score += 25
            signals.append("smtp_accepts")
        elif smtp_valid is False:
            score -= 60
            signals.append("smtp_rejects")
        else:
            signals.append("smtp_unknown")
        if catch_all is True:
            score -= 12
            signals.append("catch_all")
        elif catch_all is False:
            signals.append("not_catch_all")

    if not valid_syntax:
        verdict = "invalid"
        score = 0
    elif not domain_valid or not mx_found:
        verdict = "undeliverable"
        score = min(score, 25)
    elif disposable:
        verdict = "risky"
        score = min(score, 40)
    elif smtp_valid is False:
        verdict = "undeliverable"
        score = min(score, 25)
    elif score >= 85:
        verdict = "verified"
    elif score >= 60:
        verdict = "likely"
    else:
        verdict = "risky"

    return EmailValidation(
        email=normalized,
        valid_syntax=valid_syntax,
        domain_valid=domain_valid,
        mx_found=mx_found,
        disposable=disposable,
        free_provider=free_provider,
        role_account=role_account,
        smtp_checked=smtp_checked,
        smtp_valid=smtp_valid,
        catch_all=catch_all,
        score=max(0, min(100, score)),
        verdict=verdict,
        signals=signals,
    )
