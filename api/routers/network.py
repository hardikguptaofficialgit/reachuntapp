from fastapi import APIRouter, Depends

from api.auth import get_current_user
from api.db import Database
from api.deps import get_db, get_linkedin
from api.linkedin_session import LinkedInSessionManager

router = APIRouter(tags=["network"])


def _network_payload(live, user: dict) -> dict:
    connected = live.state == "connected" or bool(user.get("is_dev"))
    return {
        "state": live.state,
        "message": live.message,
        "can_lookup": connected,
    }


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
        }
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
        }
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
        }
    status = await linkedin.refresh_connection(user["id"], deep=True)
    if status.state == "connected":
        db.set_linkedin_connected(user["id"], True)
    return _network_payload(status, user)
