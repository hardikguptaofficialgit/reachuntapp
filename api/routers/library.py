from fastapi import APIRouter, Depends, HTTPException

from api.auth import get_current_user, new_user_id
from api.db import Database
from api.deps import get_db
from api.schemas import FavoriteRequest

router = APIRouter(tags=["library"])


@router.get("/api/v1/history")
async def history(
    user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
    q: str = "",
    verified_only: bool = False,
    missed_only: bool = False,
    limit: int = 50,
):
    if user.get("is_dev"):
        return {"items": []}
    return {
        "items": db.list_history(
            user["id"],
            limit=min(limit, 100),
            search=q,
            verified_only=verified_only,
            missed_only=missed_only,
        )
    }


@router.get("/api/v1/history/check")
async def history_check(
    q: str,
    user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    if user.get("is_dev"):
        return {"exists": False}
    return {"exists": db.history_has_query(user["id"], q)}


@router.delete("/api/v1/history/{history_id}")
async def delete_history_item(
    history_id: str,
    user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    if user.get("is_dev"):
        return {"ok": True}
    if not db.remove_history_item(user["id"], history_id):
        raise HTTPException(status_code=404, detail="Not found.")
    return {"ok": True}


@router.delete("/api/v1/history")
async def clear_history(
    user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
    q: str = "",
    verified_only: bool = False,
    missed_only: bool = False,
):
    if user.get("is_dev"):
        return {"ok": True, "deleted": 0}
    deleted = db.clear_history(
        user["id"],
        search=q,
        verified_only=verified_only,
        missed_only=missed_only,
    )
    return {"ok": True, "deleted": deleted}


@router.get("/api/v1/activity")
async def activity(
    user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
    days: int = 7,
):
    if user.get("is_dev"):
        return {"days": []}
    return {"days": db.activity_by_day(user["id"], days=min(days, 30))}


@router.get("/api/v1/favorites")
async def list_favorites(user: dict = Depends(get_current_user), db: Database = Depends(get_db)):
    if user.get("is_dev"):
        return {"items": []}
    return {"items": db.list_favorites(user["id"])}


@router.post("/api/v1/favorites")
async def add_favorite(
    body: FavoriteRequest,
    user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    if user.get("is_dev"):
        return {"ok": True, "id": "local"}
    fav_id = new_user_id()
    db.add_favorite(fav_id, user["id"], body.query, body.email)
    return {"ok": True, "id": fav_id}


@router.delete("/api/v1/favorites")
async def clear_favorites(user: dict = Depends(get_current_user), db: Database = Depends(get_db)):
    if user.get("is_dev"):
        return {"ok": True, "deleted": 0}
    return {"ok": True, "deleted": db.clear_favorites(user["id"])}


@router.delete("/api/v1/favorites/{fav_id}")
async def delete_favorite(
    fav_id: str,
    user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    if user.get("is_dev"):
        return {"ok": True}
    if not db.remove_favorite(user["id"], fav_id):
        raise HTTPException(status_code=404, detail="Not found.")
    return {"ok": True}
