"""Optional API email lookup when Mailmeteor rate-limits (set ANYMAIL_API_KEY)."""

from __future__ import annotations

import os

import httpx


class AnymailFinderClient:
    """https://anymailfinder.com — needs paid API key for volume."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._client = httpx.Client(timeout=60)

    def find_by_linkedin(self, linkedin_url: str) -> tuple[str, str]:
        try:
            r = self._client.post(
                "https://api.anymailfinder.com/v5.1/find-email/linkedin-url",
                headers={
                    "Authorization": self.api_key,
                    "Content-Type": "application/json",
                },
                json={"linkedin_url": linkedin_url},
            )
            if r.status_code == 429:
                return "", "rate_limit"
            r.raise_for_status()
            data = r.json()
            email = data.get("valid_email") or data.get("email") or ""
            if email:
                return str(email).strip(), "found"
            return "", "not_found"
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429:
                return "", "rate_limit"
            return "", "error"
        except Exception:
            return "", "error"

    def close(self) -> None:
        self._client.close()


def get_api_client() -> AnymailFinderClient | None:
    key = os.environ.get("ANYMAIL_API_KEY", "").strip()
    if key:
        return AnymailFinderClient(key)
    return None
