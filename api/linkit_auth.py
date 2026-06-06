"""Session cookie helpers for Linkit SSO."""

from __future__ import annotations

import os

from fastapi import Response

from api.auth import COOKIE_NAME, create_token
from api.config import COOKIE_DOMAIN, COOKIE_SAMESITE


def set_session_cookie(response: Response, user_id: str, email: str) -> str:
    token = create_token(user_id, email)
    kwargs: dict = {
        "key": COOKIE_NAME,
        "value": token,
        "httponly": True,
        "max_age": 60 * 60 * 24 * 7,
        "secure": os.environ.get("COOKIE_SECURE", "").lower() == "true",
    }
    if COOKIE_SAMESITE in ("lax", "strict", "none"):
        kwargs["samesite"] = COOKIE_SAMESITE
    if COOKIE_DOMAIN:
        kwargs["domain"] = COOKIE_DOMAIN
    response.set_cookie(**kwargs)
    return token
