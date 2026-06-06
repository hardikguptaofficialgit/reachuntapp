"""JWT auth helpers."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from fastapi import HTTPException, Request
from jose import JWTError, jwt

from api.config import APP_SECRET, JWT_EXPIRE_HOURS, REQUIRE_AUTH
ALGORITHM = "HS256"
COOKIE_NAME = "founder_session"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def create_token(user_id: str, email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS)
    payload = {"sub": user_id, "email": email, "exp": expire}
    return jwt.encode(payload, APP_SECRET, algorithm=ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, APP_SECRET, algorithms=[ALGORITHM])


def _token_from_request(request: Request) -> str | None:
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return request.cookies.get(COOKIE_NAME)


async def get_current_user(request: Request) -> dict[str, Any]:
    if not REQUIRE_AUTH:
        return {"id": "local", "email": "local@dev", "is_dev": True}

    token = _token_from_request(request)
    if not token:
        raise HTTPException(status_code=401, detail="Sign in required.")
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid session.")
    except JWTError:
        raise HTTPException(status_code=401, detail="Session expired. Sign in again.")

    db = request.app.state.db
    user = db.get_user_by_id(str(user_id))
    if not user:
        raise HTTPException(status_code=401, detail="Account not found.")
    return {"id": user["id"], "email": user["email"], "is_dev": False}


def new_user_id() -> str:
    return str(uuid.uuid4())
