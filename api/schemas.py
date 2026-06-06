"""API request/response models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class LinkitExchangeRequest(BaseModel):
    id_token: str = Field(..., min_length=20)


class AccountUpdateRequest(BaseModel):
    display_name: str | None = Field(default=None, max_length=80)
    avatar_style: str | None = None
    avatar_seed: str | None = Field(default=None, max_length=80)


class LookupRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=500)


class LookupResponse(BaseModel):
    job_id: str


class BulkLookupRequest(BaseModel):
    queries: list[str] = Field(..., min_length=1, max_length=100)


class BulkLookupResponse(BaseModel):
    job_ids: list[str]
    queued: int = 0
    requested: int = 0


class FavoriteRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=500)
    email: str = ""


class JobStatusRequest(BaseModel):
    job_ids: list[str] = Field(..., min_length=1, max_length=100)


class BuildPromptRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=500)
    prompt_type: str = Field(default="landing")
    founder_name: str = ""
    founder_email: str = ""
