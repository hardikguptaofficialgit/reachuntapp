"""Firebase Admin — same project/credentials as Linkit Studio (linkit_v5)."""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent


def _linkit_v5_backend_dirs() -> list[Path]:
    dirs: list[Path] = []
    custom = os.environ.get("LINKIT_V5_BACKEND", "").strip()
    if custom:
        dirs.append(Path(custom))
    dirs.append(ROOT.parent / "linkit_v5" / "backend")
    extra = os.environ.get("LINKIT_V5_BACKEND_PATHS", "").strip()
    if extra:
        for part in extra.replace(";", ",").split(","):
            p = part.strip()
            if p:
                dirs.append(Path(p))
    return dirs


def _clean_env(value: str) -> str:
    v = (value or "").strip()
    if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
        return v[1:-1]
    return v


def _account_from_env_fields() -> dict[str, Any] | None:
    private_key = _clean_env(os.environ.get("FIREBASE_PRIVATE_KEY", "")).replace("\\n", "\n")
    project_id = _clean_env(os.environ.get("FIREBASE_PROJECT_ID", ""))
    client_email = _clean_env(os.environ.get("FIREBASE_CLIENT_EMAIL", ""))
    if not project_id or not client_email or not private_key:
        return None
    return {
        "type": _clean_env(os.environ.get("FIREBASE_TYPE", "service_account")),
        "project_id": project_id,
        "private_key_id": _clean_env(os.environ.get("FIREBASE_PRIVATE_KEY_ID", "")),
        "private_key": private_key,
        "client_email": client_email,
        "client_id": _clean_env(os.environ.get("FIREBASE_CLIENT_ID", "")),
        "auth_uri": _clean_env(
            os.environ.get("FIREBASE_AUTH_URI", "https://accounts.google.com/o/oauth2/auth")
        ),
        "token_uri": _clean_env(
            os.environ.get("FIREBASE_TOKEN_URI", "https://oauth2.googleapis.com/token")
        ),
        "auth_provider_x509_cert_url": _clean_env(
            os.environ.get(
                "FIREBASE_AUTH_PROVIDER_X509_CERT_URL",
                "https://www.googleapis.com/oauth2/v1/certs",
            )
        ),
        "client_x509_cert_url": _clean_env(os.environ.get("FIREBASE_CLIENT_X509_CERT_URL", "")),
    }


def _load_service_account() -> dict[str, Any] | None:
    b64 = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON_BASE64", "").strip()
    if b64:
        try:
            return json.loads(base64.b64decode(b64).decode("utf-8"))
        except Exception as exc:
            raise RuntimeError("Invalid FIREBASE_SERVICE_ACCOUNT_JSON_BASE64") from exc

    raw = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON", "").strip()
    if raw:
        try:
            return json.loads(raw)
        except Exception as exc:
            raise RuntimeError("Invalid FIREBASE_SERVICE_ACCOUNT_JSON") from exc

    custom = os.environ.get("LINKIT_SERVICE_ACCOUNT_PATH", "").strip()
    candidates: list[Path] = []
    if custom:
        candidates.append(Path(custom))
    for backend_dir in _linkit_v5_backend_dirs():
        candidates.append(backend_dir / "serviceAccountKey.json")

    for path in candidates:
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))

    return _account_from_env_fields()


_initialized = False


def ensure_firebase_admin() -> None:
    global _initialized
    if _initialized:
        return
    import firebase_admin
    from firebase_admin import credentials

    if firebase_admin._apps:
        _initialized = True
        return

    account = _load_service_account()
    if account:
        firebase_admin.initialize_app(credentials.Certificate(account))
    else:
        firebase_admin.initialize_app()
    _initialized = True


def verify_linkit_id_token(id_token: str) -> dict[str, Any]:
    """Verify Firebase ID token from main Linkit app redirect."""
    ensure_firebase_admin()
    from firebase_admin import auth

    decoded = auth.verify_id_token(id_token.strip(), check_revoked=False)
    uid = str(decoded.get("uid") or "").strip()
    if not uid:
        raise ValueError("Token missing uid.")
    email = str(decoded.get("email") or "").strip().lower()
    if not email:
        raise ValueError("Linkit account must have a verified email.")
    return {
        "uid": uid,
        "email": email,
        "name": str(decoded.get("name") or decoded.get("display_name") or ""),
    }
