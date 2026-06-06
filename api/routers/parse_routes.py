from fastapi import APIRouter, Depends

from api.auth import get_current_user
from api.messages import sanitize_message
from api.schemas import LookupRequest
from src.query_intent import parse_payload_from_query
from src.query_parse import parse_person_query

router = APIRouter(tags=["parse"])


@router.post("/api/v1/parse")
async def parse_query(body: LookupRequest, user: dict = Depends(get_current_user)):
    del user
    try:
        pq = parse_person_query(body.query.strip())
        return parse_payload_from_query(pq)
    except ValueError as exc:
        return {"ok": False, "error": sanitize_message(str(exc))}
