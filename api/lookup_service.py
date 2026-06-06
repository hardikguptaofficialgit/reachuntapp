"""Web lookups - Mailmeteor serialized; LinkedIn parallel up to LINKEDIN_MAX_CONCURRENT."""

from __future__ import annotations

import asyncio

from api.config import (
    LINKEDIN_MAX_CONCURRENT,
    LOOKUP_MAX_SEC,
    MAILMETEOR_LOOKUP_BUDGET_SEC,
    MAILMETEOR_DELAY_SEC,
    MAILMETEOR_JITTER_SEC,
    MAILMETEOR_NOT_FOUND_TIMEOUT_SEC,
    RATE_LIMIT_WAIT_MINUTES,
    WEB_LINKEDIN_CLIENT_MODE,
    WEB_MAILMETEOR_PORT,
)
from api.db import Database
from api.linkedin_session import LinkedInSessionManager
from api.messages import public_status, public_steps, sanitize_message
from src.email_lookup import lookup_email
from src.linkedin_person import resolve_person_search, resolve_person_search_ddg_only
from src.playwright_loop import run_on_playwright_loop, use_playwright_loop
from src.mailmeteor_auto import MailmeteorAuto
from src.query_parse import lookup_cache_key, parse_person_query
from src.lookup_result import LookupResult
from src.email_validation import validate_email


class WebLookupService:
    def __init__(
        self,
        linkedin_manager: LinkedInSessionManager,
        db: Database | None = None,
        *,
        browser: str = "brave",
        mailmeteor_port: int = WEB_MAILMETEOR_PORT,
        rate_limit_wait: float = RATE_LIMIT_WAIT_MINUTES,
        lookup_timeout: float = LOOKUP_MAX_SEC,
    ):
        self.linkedin_manager = linkedin_manager
        self.db = db
        self.browser = browser
        self.mailmeteor_port = mailmeteor_port
        self.rate_limit_wait = rate_limit_wait
        self.lookup_timeout = lookup_timeout
        self._mailmeteor_lock = asyncio.Lock()
        self._linkedin_sem = asyncio.Semaphore(LINKEDIN_MAX_CONCURRENT)
        self._mailmeteor: MailmeteorAuto | None = None
        self._prewarm_task: asyncio.Task | None = None

    async def prewarm(self) -> None:
        """Keep Mailmeteor tab hot so email phase skips full page loads."""
        try:
            await self._email_resolver()
        except Exception:
            pass

    def schedule_prewarm(self) -> None:
        if self._prewarm_task and not self._prewarm_task.done():
            return
        self._prewarm_task = asyncio.create_task(self.prewarm())

    async def _email_resolver(self) -> MailmeteorAuto:
        if self._mailmeteor is None:
            self._mailmeteor = MailmeteorAuto(
                browser=self.browser,
                port=self.mailmeteor_port,
                profile_name="web-mailmeteor-cdp-profile",
                delay_seconds=MAILMETEOR_DELAY_SEC,
                jitter_seconds=MAILMETEOR_JITTER_SEC,
            )
            self._mailmeteor._not_found_timeout_ms = int(MAILMETEOR_NOT_FOUND_TIMEOUT_SEC * 1000)
            await self._mailmeteor.start()
        return self._mailmeteor

    async def close(self) -> None:
        if self._prewarm_task and not self._prewarm_task.done():
            self._prewarm_task.cancel()
        if self._mailmeteor:
            await self._mailmeteor.close()
            self._mailmeteor = None

    async def _try_cache_hit(self, user_id: str, text: str) -> LookupResult | None:
        if not self.db:
            return None
        try:
            pq = parse_person_query(text)
        except ValueError:
            return None
        cache_key = lookup_cache_key(
            text,
            pq.target_role if pq.company_only and not pq.name else None,
        )
        hit = None
        source = "cache_hit"
        if user_id != "local":
            hit = self.db.get_cached_lookup(user_id, cache_key)
        if hit and hit.get("email"):
            source = "cache_hit"
        else:
            hit = self.db.get_shared_cached_lookup(cache_key)
            source = "shared_cache_hit"
        if not hit or not hit.get("email"):
            return None
        validation = await asyncio.to_thread(validate_email, hit["email"])
        if validation.verdict in {"invalid", "undeliverable"} or validation.role_account:
            return None
        return LookupResult(
            status="completed",
            query=text,
            name=pq.name,
            domain=hit.get("domain") or pq.domain,
            founder_name=hit.get("founder_name") or pq.name,
            linkedin_url=hit.get("linkedin_url") or "",
            email=hit["email"],
            email_status=public_status("found_validated" if validation.verdict == "verified" else "found_likely"),
            email_confidence=validation.score,
            email_validation=validation.public_dict(),
            message=(
                "Instant - loaded from your history."
                if source == "cache_hit"
                else "Instant - loaded from shared cache."
            ),
            steps=["parsed", source, "email_found"],
        )

    async def run_query(self, user_id: str, text: str) -> LookupResult:
        cached = await self._try_cache_hit(user_id, text)
        if cached:
            return cached
        try:
            return await asyncio.wait_for(
                self._run_phased(user_id, text),
                timeout=LOOKUP_MAX_SEC,
            )
        except TimeoutError:
            return LookupResult(
                status="failed",
                query=text,
                message="Lookup timed out. Try again in a moment.",
                steps=["timeout"],
            )

    async def _run_phased(self, user_id: str, text: str) -> LookupResult:
        cached = await self._try_cache_hit(user_id, text)
        if cached:
            return cached

        result = await self._linkedin_phase(user_id, text)
        if result.status != "running":
            return result

        async with self._mailmeteor_lock:
            return await self._email_phase(result)

    async def _linkedin_phase(self, user_id: str, text: str) -> LookupResult:
        async with self._linkedin_sem:
            return await self._linkedin_phase_inner(user_id, text)

    async def _linkedin_phase_inner(self, user_id: str, text: str) -> LookupResult:
        steps: list[str] = []
        try:
            pq = parse_person_query(text)
        except ValueError as exc:
            return LookupResult(
                status="failed",
                query=text,
                message=sanitize_message(str(exc)),
                steps=["parse_error"],
            )

        steps.append("parsed")

        if user_id != "local":
            if WEB_LINKEDIN_CLIENT_MODE:
                connected = True
            elif user_id in getattr(self.linkedin_manager, "_verified", set()):
                connected = True
            else:
                connected = await self.linkedin_manager.is_connected(user_id)
            if not connected:
                return LookupResult(
                    status="failed",
                    query=text,
                    message="Discovery is not ready yet.",
                    steps=["parse_error"],
                )

        result = LookupResult(
            status="running",
            query=text,
            name=pq.name,
            domain=pq.domain,
            steps=steps,
        )

        person = None
        cached_profile = None
        if user_id != "local" and self.db:
            cached_profile = self.db.get_cached_profile(user_id, text)

        local_browser = None
        session = None
        try:
            if cached_profile and cached_profile.get("linkedin_url"):
                from src.linkedin_founders import LinkedInFounder

                person = LinkedInFounder(
                    name=cached_profile.get("founder_name") or pq.name,
                    linkedin_url=cached_profile["linkedin_url"],
                    title_hint="",
                )
                steps.append("profile_cache")
            elif WEB_LINKEDIN_CLIENT_MODE and user_id != "local":
                steps.append("linkedin_search")
                person = await resolve_person_search_ddg_only(pq)
            else:
                if user_id == "local":
                    from src.browser_cdp import CdpBrowser

                    local_browser = CdpBrowser(
                        browser=self.browser,
                        profile_name="brave-linkedin",
                        port=9223,
                    )
                    await local_browser.start("https://www.linkedin.com/feed/")
                else:
                    session = await self.linkedin_manager.get_browser(user_id)

                steps.append("linkedin_search")

                async def do_search():
                    if local_browser:
                        await local_browser.ensure_playwright_connected()
                        return await resolve_person_search(local_browser.page, pq)
                    await session.ensure_playwright_connected()
                    return await resolve_person_search(session.page, pq)

                if use_playwright_loop():
                    person = await run_on_playwright_loop(do_search)
                else:
                    person = await do_search()
        except Exception as exc:
            result.status = "failed"
            result.message = sanitize_message(str(exc))
            result.steps = steps + ["linkedin_error"]
            return result
        finally:
            if local_browser:
                await local_browser.close()

        if not person:
            result.status = "completed"
            result.message = "No matching professional profile found."
            result.email_status = "no_profile"
            result.steps = steps + ["no_linkedin"]
            return result

        result.founder_name = person.name
        result.linkedin_url = person.linkedin_url
        if pq.company_only or not (result.name or "").strip():
            result.name = person.name
        result.steps = steps + ["linkedin_found"]
        return result

    async def _email_phase(self, result: LookupResult) -> LookupResult:
        steps = list(result.steps)
        steps.append("email_lookup")
        self.schedule_prewarm()
        resolver = await self._email_resolver()
        try:
            email, email_status = await asyncio.wait_for(
                lookup_email(
                    resolver,
                    result.linkedin_url,
                    rate_limit_wait_minutes=self.rate_limit_wait,
                    api_client=None,
                    name=result.founder_name or result.name,
                    domain=result.domain,
                ),
                timeout=MAILMETEOR_LOOKUP_BUDGET_SEC,
            )
        except TimeoutError:
            result.status = "completed"
            result.email = ""
            result.email_status = public_status("not_found")
            result.message = "Profile located. Email lookup is taking too long right now."
            result.steps = steps + ["no_email"]
            return result
        except Exception as exc:
            result.status = "failed"
            result.message = sanitize_message(str(exc))
            result.steps = steps + ["email_error"]
            return result
        result.email = email or ""
        result.status = "completed"
        if email:
            validation = await asyncio.to_thread(validate_email, email)
            result.email_confidence = validation.score
            result.email_validation = validation.public_dict()
            if validation.verdict in {"invalid", "undeliverable"} or validation.role_account:
                result.email = ""
                result.email_status = public_status("not_found")
                result.message = (
                    "Profile located. Email candidate was a generic inbox."
                    if validation.role_account
                    else "Profile located. Email candidate failed validation."
                )
                steps.append("no_email")
            else:
                if validation.verdict == "verified":
                    internal_status = "found_validated"
                elif validation.verdict == "risky":
                    internal_status = "found_risky"
                else:
                    internal_status = "found_likely"
                result.email_status = public_status(internal_status)
                if result.email_status == "verified":
                    result.message = "Work email validated."
                elif result.email_status == "likely":
                    result.message = "Likely work email found."
                else:
                    result.message = "Email found with risk signals."
                steps.append("email_found")
        else:
            result.email_status = public_status(email_status or "not_found")
            result.message = (
                "Email finder is busy right now. Try again shortly."
                if email_status == "rate_limit"
                else "Profile located. No work email available right now."
            )
            steps.append("no_email")
        result.steps = steps
        return result
