"""Generate build prompts for AI app builders (Lovable, v0, Bolt, etc.)."""

from __future__ import annotations

from dataclasses import dataclass

from src.query_parse import PersonQuery, parse_person_query

PROMPT_TYPES = (
    "landing",
    "mvp",
    "outreach",
    "pitch",
    "dashboard",
    "email",
)


@dataclass
class BuildContext:
    company: str
    domain: str
    founder_name: str = ""
    founder_email: str = ""
    raw_query: str = ""


def _company_from_domain(domain: str) -> str:
    base = domain.lower().split(".")[0]
    return base.replace("-", " ").title()


def context_from_query(
    query: str,
    *,
    founder_name: str = "",
    founder_email: str = "",
) -> BuildContext:
    try:
        pq: PersonQuery = parse_person_query(query)
        company = _company_from_domain(pq.domain)
        return BuildContext(
            company=company,
            domain=pq.domain,
            founder_name=founder_name or pq.name,
            founder_email=founder_email,
            raw_query=query,
        )
    except ValueError:
        domain = query.strip()
        return BuildContext(
            company=_company_from_domain(domain) if "." in domain else query,
            domain=domain,
            founder_name=founder_name,
            founder_email=founder_email,
            raw_query=query,
        )


def generate_prompt(ctx: BuildContext, prompt_type: str) -> str:
    prompt_type = prompt_type if prompt_type in PROMPT_TYPES else "landing"
    company = ctx.company
    domain = ctx.domain
    founder = ctx.founder_name
    email = ctx.founder_email

    if prompt_type == "landing":
        return f"""Build a premium landing page for {company} ({domain}).

Goals:
- Impress visitors in the first 5 seconds — this is for outreach to {company}, not a generic template.
- Black & white minimal aesthetic, clay-style soft shadows, no gradients, no stock-photo clichés.
- Feel like a real funded startup: confident typography, generous whitespace.

Structure:
1. Hero — company name, one-line value prop tailored to what {domain} likely does, primary CTA "Get early access"
2. Problem — 3 bullets describing pain their customers feel
3. Solution — how {company} solves it (infer intelligently from domain name & industry)
4. Social proof — placeholder logos row + one quote
5. Feature grid — 3 features with short titles
6. CTA footer — email capture + link to {domain}

Technical:
- React + Tailwind, fully responsive, accessible
- Use "{company}" and "{domain}" throughout — never "Acme Corp"
{f'- Subtle note in footer: Built for {founder}' + (f' ({email})' if email else '') if founder else ''}

Ship a complete, polished single-page app ready to deploy."""

    if prompt_type == "mvp":
        return f"""Build an MVP web app demo for {company} ({domain}).

Concept: A credible product prototype that shows you understand their space — use this to impress the {company} team.

Include:
- Auth UI (mock — no real backend required unless easy)
- Dashboard with 3–5 realistic metrics widgets for their industry
- One core workflow screen (infer from domain: e.g. analytics, booking, devtools, etc.)
- Settings page with profile

Design: minimal black & white, premium SaaS, subtle clay shadows, no purple gradients.

Stack: React, TypeScript, Tailwind. Seed data should use "{company}" branding.
Domain context: {domain}
{f'Audience: {founder}' + (f' <{email}>' if email else '') + ' may see this demo.' if founder else ''}

Deliver runnable code with clear README."""

    if prompt_type == "outreach":
        return f"""Build a microsite whose only job is to impress {founder or 'the founder'} at {company} ({domain}).

Narrative: "I built this for you in an afternoon — imagine what we could ship together."

Pages (single scroll or 2 pages):
1. Cover — "Made for {company}" + personalized headline mentioning {founder or 'your team'}
2. What I noticed — 3 insights about {domain}'s market (infer from domain)
3. Prototype — embedded-style preview section describing a feature idea for {company}
4. Next step — calendar/email CTA{f' (use placeholder: {email})' if email else ''}

Tone: respectful, founder-to-founder, not salesy. Design: ultra-minimal B&W, editorial serif headlines.

React + Tailwind. Every section should feel custom to {company}, not templated."""

    if prompt_type == "pitch":
        return f"""Build a one-page pitch site for {company} ({domain}) as if you are helping them raise their next round.

Sections: vision headline, market size (plausible placeholders), product slide, traction metrics (placeholder charts), team, ask/CTA.

Visual: black & white, McKinsey-meets-YC aesthetic — charts, big numbers, crisp grids.

Company: {company} · {domain}
{f'Primary contact context: {founder}' + (f', {email}' if email else '') if founder else ''}

React + Tailwind. Make it presentation-quality."""

    if prompt_type == "dashboard":
        return f"""Build an admin dashboard UI for {company} ({domain}).

Show: sidebar nav, overview KPIs, data table with filters, detail drawer, empty states.

Industry: infer from "{domain}" — use realistic labels, not lorem ipsum.

Design system: monochrome, minimal, clay cards, soft borders — production-grade.

React + TypeScript + Tailwind. Company name in sidebar header: {company}."""

    if prompt_type == "email":
        founder_line = founder or "the founder"
        return f"""Write a short cold email (under 120 words) to {founder_line} at {company} ({domain}).

Context: I built a small custom project to show genuine interest in their company — I will link the demo.

Rules:
- No "I hope this finds you well"
- Specific compliment about {domain}'s space (inferred)
- One clear ask: 15-min call
- Confident, peer-to-peer tone
{f'- Sign off with my name; they can reply to {email}' if email else ''}

Output only the email subject line + body."""

    return generate_prompt(ctx, "landing")
