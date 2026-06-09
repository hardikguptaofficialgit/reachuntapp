from fastapi import APIRouter, Depends, HTTPException

from api.auth import get_current_user
from api.config import LOOKUP_DAILY_LIMIT
from api.db import AVATAR_STYLES, DEFAULT_AVATAR_STYLE, Database
from api.deps import get_db
from api.schemas import AccountUpdateRequest

router = APIRouter(tags=["account"])


def _dev_account(user: dict) -> dict:
    local = user["email"].split("@")[0] or "dev"
    return {
        "display_name": local.title(),
        "email": user["email"],
        "avatar_style": DEFAULT_AVATAR_STYLE,
        "avatar_seed": local,
        "created_at": "",
        "linkit_uid": "",
    }


@router.get("/api/v1/me")
async def me(user: dict = Depends(get_current_user), db: Database = Depends(get_db)):
    if user.get("is_dev"):
        integration = {"linkedin_connected": False, "linkedin_connected_at": None, "lookup_count": 0}
        analytics = {"total": 0, "verified": 0, "hit_rate": 0}
        today = 0
        daily_limit = LOOKUP_DAILY_LIMIT
        daily_remaining = LOOKUP_DAILY_LIMIT
        suggestions: list[str] = []
        account = _dev_account(user)
    else:
        integration = db.get_integration(user["id"])
        analytics = db.get_analytics(user["id"])
        today = db.count_lookup_jobs_today(user["id"])
        daily_limit = LOOKUP_DAILY_LIMIT
        daily_remaining = max(0, daily_limit - today) if daily_limit else 0
        suggestions = db.recent_queries(user["id"])
        account = db.get_account(user["id"])
    return {
        "user": {"id": user["id"], "email": user["email"]},
        "account": account,
        "integration": {
            "network_connected": integration["linkedin_connected"],
            "connected_at": integration["linkedin_connected_at"],
        },
        "stats": {
            "lookups": integration["lookup_count"],
            "verified": analytics["verified"],
            "hit_rate": analytics["hit_rate"],
            "today": today,
            "daily_limit": daily_limit,
            "daily_remaining": daily_remaining,
            "daily_unlimited": user.get("is_dev") or daily_limit == 0,
        },
        "suggestions": suggestions,
        "avatar_styles": sorted(AVATAR_STYLES),
    }


@router.patch("/api/v1/me/account")
async def patch_account(
    body: AccountUpdateRequest,
    user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    if user.get("is_dev"):
        raise HTTPException(status_code=400, detail="Account profile is not saved in dev bypass mode.")
    if (
        body.display_name is None
        and body.avatar_style is None
        and body.avatar_seed is None
    ):
        raise HTTPException(status_code=400, detail="No fields to update.")
    try:
        account = db.update_account(
            user["id"],
            display_name=body.display_name,
            avatar_style=body.avatar_style,
            avatar_seed=body.avatar_seed,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"account": account}
