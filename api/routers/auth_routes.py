from fastapi import APIRouter, Depends, HTTPException, Response

from api.auth import COOKIE_NAME
from api.config import COOKIE_DOMAIN, COOKIE_SAMESITE
from api.db import Database
from api.deps import get_db
from api.linkit_auth import set_session_cookie
from api.linkit_firebase import verify_linkit_id_token
from api.messages import sanitize_message
from api.schemas import LinkitExchangeRequest

router = APIRouter(tags=["auth"])


@router.post("/api/v1/auth/linkit/exchange")
async def linkit_exchange(
    body: LinkitExchangeRequest,
    response: Response,
    db: Database = Depends(get_db),
):
    try:
        claims = verify_linkit_id_token(body.id_token)
    except Exception as exc:
        raise HTTPException(
            status_code=401,
            detail=sanitize_message(str(exc) or "Invalid Linkit sign-in."),
        ) from exc

    try:
        user_id = db.upsert_linkit_user(claims["uid"], claims["email"])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    token = set_session_cookie(response, user_id, claims["email"])
    return {
        "token": token,
        "user": {"id": user_id, "email": claims["email"], "linkit_uid": claims["uid"]},
    }


@router.post("/api/v1/auth/logout")
async def logout(response: Response):
    kwargs: dict = {"key": COOKIE_NAME}
    if COOKIE_SAMESITE in ("lax", "strict", "none"):
        kwargs["samesite"] = COOKIE_SAMESITE
    if COOKIE_DOMAIN:
        kwargs["domain"] = COOKIE_DOMAIN
    response.delete_cookie(**kwargs)
    return {"ok": True}
