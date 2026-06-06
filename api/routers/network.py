from fastapi import APIRouter, Depends

from api.auth import get_current_user
from api.config import WEB_LINKEDIN_CLIENT_MODE, WEB_LINKEDIN_LOGIN_URL
from api.db import Database
from api.deps import get_db, get_linkedin
from api.linkedin_session import ConnectStatus, LinkedInSessionManager

router = APIRouter(tags=["network"])

_LINKEDIN_LOGIN = WEB_LINKEDIN_LOGIN_URL or "https://www.linkedin.com/login"


def _network_payload(live, user: dict, *, open_url: str | None = None) -> dict:
    connected = live.state == "connected" or bool(user.get("is_dev"))
    payload = {
        "state": live.state,
        "message": live.message,
        "can_lookup": connected,
        "client_mode": WEB_LINKEDIN_CLIENT_MODE,
    }
    if open_url:
        payload["open_url"] = open_url
    return payload


def _client_status(db: Database, user_id: str) -> tuple[str, str]:
    integration = db.get_integration(user_id)
    if integration.get("linkedin_connected"):
        return "connected", "Network ready."
    return "disconnected", "Connect to unlock discovery."


@router.get("/api/v1/integrations/network")
async def network_status(
    user: dict = Depends(get_current_user),
    linkedin: LinkedInSessionManager = Depends(get_linkedin),
    db: Database = Depends(get_db),
):
    if user.get("is_dev"):
        return {
            "state": "connected",
            "message": "Workspace ready.",
            "can_lookup": True,
            "client_mode": WEB_LINKEDIN_CLIENT_MODE,
        }
    if WEB_LINKEDIN_CLIENT_MODE:
        state, message = _client_status(db, user["id"])
        live = ConnectStatus(state=state, message=message)  # type: ignore[arg-type]
        return _network_payload(live, user)

    live = await linkedin.status(user["id"])
    if live.state == "connected":
        db.set_linkedin_connected(user["id"], True)
    elif live.state == "disconnected":
        db.set_linkedin_connected(user["id"], False)
    return _network_payload(live, user)


@router.post("/api/v1/integrations/network/connect")
async def network_connect(
    user: dict = Depends(get_current_user),
    linkedin: LinkedInSessionManager = Depends(get_linkedin),
):
    if user.get("is_dev"):
        return {
            "state": "connected",
            "message": "Development mode — network ready.",
            "can_lookup": True,
            "client_mode": WEB_LINKEDIN_CLIENT_MODE,
        }
    if WEB_LINKEDIN_CLIENT_MODE:
        status = ConnectStatus(
            state="connecting",
            message="Sign in to LinkedIn in your browser, then click I've signed in.",
        )
        return _network_payload(status, user, open_url=_LINKEDIN_LOGIN)

    status = await linkedin.start_connect(user["id"])
    return _network_payload(status, user)


@router.post("/api/v1/integrations/network/refresh")
async def network_refresh(
    user: dict = Depends(get_current_user),
    linkedin: LinkedInSessionManager = Depends(get_linkedin),
    db: Database = Depends(get_db),
):
    if user.get("is_dev"):
        return {
            "state": "connected",
            "message": "Development mode — network ready.",
            "can_lookup": True,
            "client_mode": WEB_LINKEDIN_CLIENT_MODE,
        }
    if WEB_LINKEDIN_CLIENT_MODE:
        db.set_linkedin_connected(user["id"], True)
        status = ConnectStatus(state="connected", message="Network ready.")
        return _network_payload(status, user)

    status = await linkedin.refresh_connection(user["id"], deep=True)
    if status.state == "connected":
        db.set_linkedin_connected(user["id"], True)
    return _network_payload(status, user)
