"""AI build prompts via Groq OpenAI-compatible API."""

from __future__ import annotations

import re

import httpx

from api.config import GROQ_API_BASE, GROQ_API_KEY, GROQ_MODEL
from src.build_prompts import PROMPT_TYPES, BuildContext, generate_prompt

_TYPE_BRIEF: dict[str, str] = {
    "landing": "Premium single-page marketing site to impress the company during outreach.",
    "mvp": "Credible MVP web app prototype with dashboard and one core workflow.",
    "outreach": "Personal microsite: 'I built this for you' — founder-to-founder tone.",
    "pitch": "One-page fundraise / pitch site with metrics and vision slides as sections.",
    "dashboard": "Production-quality admin dashboard UI with KPIs and data table.",
    "email": "Short cold email under 120 words with subject line (not a web app).",
}


def _api_key() -> str | None:
    return GROQ_API_KEY or None


def ai_prompts_enabled() -> bool:
    return _api_key() is not None


def _system_instruction() -> str:
    return """You write copy-paste prompts for AI app builders (Lovable, v0, Bolt, Cursor).
Output ONLY the prompt text the user will paste into the builder — no preamble, no markdown code fences.

Format rules:
- Use clear section headers in ALL CAPS or Title Case (OBJECTIVE, DESIGN, STRUCTURE, TECH STACK, etc.)
- Use bullet lists and numbered steps where helpful
- Be specific to the exact company and domain given — never "Acme Corp"
- Black & white minimal aesthetic, clay-style soft shadows, no purple gradients unless requested
- Include React + TypeScript + Tailwind unless the type is email
- Sound like a senior product designer briefing an engineer
- For email type: output Subject: line then body only"""


def _user_message(ctx: BuildContext, prompt_type: str) -> str:
    brief = _TYPE_BRIEF.get(prompt_type, _TYPE_BRIEF["landing"])
    founder = ctx.founder_name.strip()
    email = ctx.founder_email.strip()
    audience = ""
    if founder:
        audience = f"Primary contact: {founder}" + (f" ({email})" if email else "")

    return f"""Create a builder prompt for: {prompt_type.upper()}

Company: {ctx.company}
Domain: {ctx.domain}
Raw query: {ctx.raw_query or ctx.domain}
{audience}

Brief: {brief}

Requirements:
- Tailor value prop and features to what {ctx.domain} likely does (infer industry intelligently)
- Mention "{ctx.company}" and "{ctx.domain}" throughout
- Ready to paste into Lovable / v0 / Bolt without edits"""


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-z]*\n?", "", text, flags=re.I)
        text = re.sub(r"\n?```\s*$", "", text)
    return text.strip()


def _extract_content(data: dict) -> str:
    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError("No response from Groq")
    message = choices[0].get("message") or {}
    content = (message.get("content") or "").strip()
    if not content:
        raise RuntimeError("Empty response from Groq")
    return content


async def generate_ai_build_prompt(ctx: BuildContext, prompt_type: str) -> str:
    """Generate a formatted prompt using Groq. Raises on failure."""
    key = _api_key()
    if not key:
        raise RuntimeError("GROQ_API_KEY is not set")

    prompt_type = prompt_type if prompt_type in PROMPT_TYPES else "landing"
    url = f"{GROQ_API_BASE}/chat/completions"
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": _system_instruction()},
            {"role": "user", "content": _user_message(ctx, prompt_type)},
        ],
        "temperature": 0.65,
        "max_tokens": 4096,
    }

    async with httpx.AsyncClient(timeout=90.0) as client:
        res = await client.post(
            url,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        if res.status_code == 429:
            raise RuntimeError(
                "Groq rate limit reached — wait a moment or check your Groq console."
            )
        if res.status_code >= 400:
            detail = res.text[:500]
            raise RuntimeError(f"Groq API error ({res.status_code}): {detail}")

        return _strip_fences(_extract_content(res.json()))


async def generate_build_prompt(
    ctx: BuildContext,
    prompt_type: str,
    *,
    use_ai: bool,
) -> tuple[str, str]:
    """Returns (prompt_text, source) where source is 'ai' or 'template'."""
    if use_ai and ai_prompts_enabled():
        try:
            return await generate_ai_build_prompt(ctx, prompt_type), "ai"
        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError(f"AI prompt generation failed: {exc}") from exc
    return generate_prompt(ctx, prompt_type), "template"
