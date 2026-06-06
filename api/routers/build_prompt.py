import uuid

from fastapi import APIRouter, Depends, HTTPException, Request

from api.auth import get_current_user
from api.config import BUILD_PROMPT_DAILY_LIMIT, GROQ_API_KEY
from api.db import Database
from api.deps import get_db
from api.messages import sanitize_message
from api.rate_limit import build_prompt_limiter
from api.schemas import BuildPromptRequest
from src.build_prompts import PROMPT_TYPES, context_from_query
from src.groq_prompts import ai_prompts_enabled, generate_build_prompt

router = APIRouter(tags=["build"])


@router.get("/api/v1/build-prompt/types")
async def build_prompt_types(user: dict = Depends(get_current_user)):
    del user
    return {
        "types": [
            {"id": "landing", "label": "Landing page", "hint": "Impress with a premium site"},
            {"id": "mvp", "label": "MVP demo", "hint": "Full product prototype"},
            {"id": "outreach", "label": "Outreach microsite", "hint": "Built for them"},
            {"id": "pitch", "label": "Pitch one-pager", "hint": "Fundraise-style page"},
            {"id": "dashboard", "label": "Dashboard UI", "hint": "Admin product shell"},
            {"id": "email", "label": "Outreach email", "hint": "Short cold email copy"},
        ],
        "ai_enabled": ai_prompts_enabled(),
    }


@router.get("/api/v1/build-prompt/quota")
async def build_prompt_quota(
    user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    if user.get("is_dev"):
        return {
            "limit": BUILD_PROMPT_DAILY_LIMIT,
            "used": 0,
            "remaining": BUILD_PROMPT_DAILY_LIMIT,
            "ai_enabled": ai_prompts_enabled(),
            "unlimited": True,
        }
    quota = db.get_build_prompt_quota(user["id"], daily_limit=BUILD_PROMPT_DAILY_LIMIT)
    return {**quota, "ai_enabled": ai_prompts_enabled(), "unlimited": False}


@router.post("/api/v1/build-prompt")
async def build_prompt(
    body: BuildPromptRequest,
    user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    await build_prompt_limiter.check(user["id"], label="AI prompts")
    ctx = context_from_query(
        body.query.strip(),
        founder_name=body.founder_name.strip(),
        founder_email=body.founder_email.strip(),
    )
    ptype = body.prompt_type if body.prompt_type in PROMPT_TYPES else "landing"

    is_dev = bool(user.get("is_dev"))
    want_ai = ai_prompts_enabled() and bool(GROQ_API_KEY)

    if want_ai and not is_dev:
        quota = db.get_build_prompt_quota(user["id"], daily_limit=BUILD_PROMPT_DAILY_LIMIT)
        if quota["remaining"] <= 0:
            raise HTTPException(
                status_code=429,
                detail=f"Daily AI prompt limit reached ({BUILD_PROMPT_DAILY_LIMIT} per day). Try again tomorrow.",
            )

    try:
        prompt_text, source = await generate_build_prompt(ctx, ptype, use_ai=want_ai)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=sanitize_message(str(exc))) from exc

    if source == "ai" and want_ai and not is_dev:
        db.record_ai_build_prompt(
            str(uuid.uuid4()),
            user["id"],
            body.query.strip(),
            ptype,
        )

    quota_after = (
        {"limit": BUILD_PROMPT_DAILY_LIMIT, "used": 0, "remaining": BUILD_PROMPT_DAILY_LIMIT}
        if is_dev
        else db.get_build_prompt_quota(user["id"], daily_limit=BUILD_PROMPT_DAILY_LIMIT)
    )

    return {
        "prompt": prompt_text,
        "prompt_type": ptype,
        "company": ctx.company,
        "domain": ctx.domain,
        "founder_name": ctx.founder_name,
        "source": source,
        "quota": quota_after,
    }
