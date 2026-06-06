"""SQLite persistence for web app users."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from api.config import DATABASE_PATH, SHARED_LOOKUP_CACHE_TTL_DAYS

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = ROOT / "data" / "webapp.db"
SQLITE_BUSY_TIMEOUT_MS = 15_000

AVATAR_STYLES = frozenset(
    {
        "notionists",
        "lorelei",
        "avataaars",
        "bottts",
        "pixel-art",
        "thumbs",
        "fun-emoji",
        "adventurer",
        "micah",
        "croodles",
    }
)
DEFAULT_AVATAR_STYLE = "notionists"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Database:
    def __init__(self, path: Path | None = None):
        if path is not None:
            self.path = path
        elif DATABASE_PATH:
            self.path = Path(DATABASE_PATH)
        else:
            self.path = DEFAULT_DB
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, check_same_thread=False, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute(f"PRAGMA busy_timeout = {SQLITE_BUSY_TIMEOUT_MS}")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        return conn

    @contextmanager
    def session(self):
        conn = self._connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _migrate(self, conn: sqlite3.Connection) -> None:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(lookup_history)")}
        if "linkedin_url" not in cols:
            conn.execute("ALTER TABLE lookup_history ADD COLUMN linkedin_url TEXT DEFAULT ''")
        if "founder_name" not in cols:
            conn.execute("ALTER TABLE lookup_history ADD COLUMN founder_name TEXT DEFAULT ''")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS shared_lookup_cache (
                cache_key TEXT PRIMARY KEY,
                query TEXT NOT NULL,
                email TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT '',
                linkedin_url TEXT NOT NULL DEFAULT '',
                founder_name TEXT NOT NULL DEFAULT '',
                domain TEXT NOT NULL DEFAULT '',
                hit_count INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_shared_lookup_cache_updated
            ON shared_lookup_cache(updated_at DESC)
            """
        )

        user_cols = {row[1] for row in conn.execute("PRAGMA table_info(users)")}
        if "password_hash" not in user_cols:
            conn.execute("ALTER TABLE users ADD COLUMN password_hash TEXT NOT NULL DEFAULT ''")
        if "linkit_uid" not in user_cols:
            conn.execute("ALTER TABLE users ADD COLUMN linkit_uid TEXT")
        if "display_name" not in user_cols:
            conn.execute("ALTER TABLE users ADD COLUMN display_name TEXT NOT NULL DEFAULT ''")
        if "avatar_style" not in user_cols:
            conn.execute(
                "ALTER TABLE users ADD COLUMN avatar_style TEXT NOT NULL DEFAULT 'notionists'"
            )
        if "avatar_seed" not in user_cols:
            conn.execute("ALTER TABLE users ADD COLUMN avatar_seed TEXT NOT NULL DEFAULT ''")
        # Index only after column exists (old DBs had users without linkit_uid).
        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_users_linkit_uid
            ON users(linkit_uid) WHERE linkit_uid IS NOT NULL AND linkit_uid != ''
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS build_prompt_usage (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                query TEXT NOT NULL,
                prompt_type TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT 'ai',
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_build_prompt_usage_user_day
            ON build_prompt_usage(user_id, created_at DESC)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS lookup_jobs (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                query TEXT NOT NULL,
                status TEXT NOT NULL,
                phase TEXT NOT NULL,
                priority INTEGER NOT NULL DEFAULT 0,
                result_json TEXT,
                error TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_lookup_jobs_user_status
            ON lookup_jobs(user_id, status)
            """
        )

    def _init_schema(self) -> None:
        with self.session() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS user_integrations (
                    user_id TEXT PRIMARY KEY,
                    linkedin_connected INTEGER NOT NULL DEFAULT 0,
                    linkedin_connected_at TEXT,
                    lookup_count INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );
                CREATE TABLE IF NOT EXISTS lookup_history (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    query TEXT NOT NULL,
                    email TEXT,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );
                CREATE INDEX IF NOT EXISTS idx_lookup_history_user
                    ON lookup_history(user_id, created_at DESC);
                CREATE TABLE IF NOT EXISTS favorites (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    query TEXT NOT NULL,
                    email TEXT,
                    created_at TEXT NOT NULL,
                    UNIQUE(user_id, query),
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );
                """
            )
            self._migrate(conn)

    def create_user(self, user_id: str, email: str, password_hash: str) -> None:
        with self.session() as conn:
            conn.execute(
                "INSERT INTO users (id, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
                (user_id, email.lower().strip(), password_hash, _now()),
            )
            conn.execute(
                "INSERT INTO user_integrations (user_id) VALUES (?)",
                (user_id,),
            )
        self._ensure_account_defaults(user_id, email)

    def get_user_by_email(self, email: str) -> sqlite3.Row | None:
        with self.session() as conn:
            cur = conn.execute(
                "SELECT * FROM users WHERE email = ?",
                (email.lower().strip(),),
            )
            return cur.fetchone()

    def get_user_by_id(self, user_id: str) -> sqlite3.Row | None:
        with self.session() as conn:
            cur = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            return cur.fetchone()

    def get_user_by_linkit_uid(self, linkit_uid: str) -> sqlite3.Row | None:
        with self.session() as conn:
            cur = conn.execute(
                "SELECT * FROM users WHERE linkit_uid = ?",
                (linkit_uid.strip(),),
            )
            return cur.fetchone()

    def upsert_linkit_user(self, linkit_uid: str, email: str) -> str:
        """Map Firebase uid → local user id (creates or links by email)."""
        uid = linkit_uid.strip()
        mail = email.lower().strip()
        if not uid or not mail:
            raise ValueError("linkit_uid and email required")

        existing = self.get_user_by_linkit_uid(uid)
        if existing:
            user_id = str(existing["id"])
            self._ensure_account_defaults(user_id, mail)
            return user_id

        by_email = self.get_user_by_email(mail)
        if by_email:
            user_id = str(by_email["id"])
            with self.session() as conn:
                conn.execute(
                    "UPDATE users SET linkit_uid = ?, email = ? WHERE id = ?",
                    (uid, mail, user_id),
                )
            self._ensure_account_defaults(user_id, mail)
            return user_id

        user_id = uid
        with self.session() as conn:
            conn.execute(
                """
                INSERT INTO users (id, email, password_hash, linkit_uid, created_at)
                VALUES (?, ?, '', ?, ?)
                """,
                (user_id, mail, uid, _now()),
            )
            conn.execute(
                "INSERT OR IGNORE INTO user_integrations (user_id) VALUES (?)",
                (user_id,),
            )
        self._ensure_account_defaults(user_id, mail)
        return user_id

    def _ensure_account_defaults(self, user_id: str, email: str = "") -> None:
        user = self.get_user_by_id(user_id)
        if not user:
            return
        seed = str(user["avatar_seed"] or "").strip() if "avatar_seed" in user.keys() else ""
        style = str(user["avatar_style"] or "").strip() if "avatar_style" in user.keys() else ""
        if seed and style in AVATAR_STYLES:
            return
        fallback_seed = seed or email.split("@")[0] or user_id
        fallback_style = style if style in AVATAR_STYLES else DEFAULT_AVATAR_STYLE
        with self.session() as conn:
            conn.execute(
                """
                UPDATE users
                SET avatar_seed = CASE WHEN avatar_seed = '' OR avatar_seed IS NULL THEN ? ELSE avatar_seed END,
                    avatar_style = CASE WHEN avatar_style = '' OR avatar_style IS NULL THEN ? ELSE avatar_style END
                WHERE id = ?
                """,
                (fallback_seed, fallback_style, user_id),
            )

    def get_account(self, user_id: str) -> dict[str, Any]:
        user = self.get_user_by_id(user_id)
        if not user:
            raise ValueError("user not found")
        keys = user.keys()
        style = str(user["avatar_style"] if "avatar_style" in keys else DEFAULT_AVATAR_STYLE)
        if style not in AVATAR_STYLES:
            style = DEFAULT_AVATAR_STYLE
        seed = str(user["avatar_seed"] if "avatar_seed" in keys else "").strip() or str(user["id"])
        display = str(user["display_name"] if "display_name" in keys else "").strip()
        if not display:
            display = str(user["email"]).split("@")[0]
        return {
            "display_name": display,
            "email": str(user["email"]),
            "avatar_style": style,
            "avatar_seed": seed,
            "created_at": str(user["created_at"]),
            "linkit_uid": str(user["linkit_uid"] or "") if "linkit_uid" in keys else "",
        }

    def update_account(
        self,
        user_id: str,
        *,
        display_name: str | None = None,
        avatar_style: str | None = None,
        avatar_seed: str | None = None,
    ) -> dict[str, Any]:
        if avatar_style is not None and avatar_style not in AVATAR_STYLES:
            raise ValueError(f"avatar_style must be one of: {', '.join(sorted(AVATAR_STYLES))}")
        if avatar_seed is not None and len(avatar_seed.strip()) > 80:
            raise ValueError("avatar_seed too long")

        updates: list[str] = []
        params: list[Any] = []
        if display_name is not None:
            updates.append("display_name = ?")
            params.append(display_name.strip()[:80])
        if avatar_style is not None:
            updates.append("avatar_style = ?")
            params.append(avatar_style)
        if avatar_seed is not None:
            updates.append("avatar_seed = ?")
            params.append(avatar_seed.strip()[:80])

        if updates:
            params.append(user_id)
            with self.session() as conn:
                conn.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = ?", params)

        return self.get_account(user_id)

    def get_integration(self, user_id: str) -> dict[str, Any]:
        with self.session() as conn:
            cur = conn.execute(
                "SELECT * FROM user_integrations WHERE user_id = ?",
                (user_id,),
            )
            row = cur.fetchone()
            if not row:
                return {"linkedin_connected": False, "lookup_count": 0}
            return {
                "linkedin_connected": bool(row["linkedin_connected"]),
                "linkedin_connected_at": row["linkedin_connected_at"],
                "lookup_count": row["lookup_count"] or 0,
            }

    def set_linkedin_connected(self, user_id: str, connected: bool) -> None:
        with self.session() as conn:
            conn.execute(
                """
                UPDATE user_integrations
                SET linkedin_connected = ?, linkedin_connected_at = ?
                WHERE user_id = ?
                """,
                (1 if connected else 0, _now() if connected else None, user_id),
            )

    def increment_lookup_count(self, user_id: str) -> None:
        with self.session() as conn:
            conn.execute(
                "UPDATE user_integrations SET lookup_count = lookup_count + 1 WHERE user_id = ?",
                (user_id,),
            )

    def add_lookup_history(
        self,
        record_id: str,
        user_id: str,
        query: str,
        email: str,
        status: str,
        *,
        linkedin_url: str = "",
        founder_name: str = "",
    ) -> None:
        with self.session() as conn:
            conn.execute(
                """
                INSERT INTO lookup_history (
                    id, user_id, query, email, status, created_at, linkedin_url, founder_name
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record_id,
                    user_id,
                    query,
                    email,
                    status,
                    _now(),
                    linkedin_url or "",
                    founder_name or "",
                ),
            )

    def _norm_query(self, query: str) -> str:
        return query.strip().lower()

    def shared_cache_key(self, query: str) -> str:
        return " ".join((query or "").strip().lower().split())

    def get_cached_lookup(self, user_id: str, query: str) -> dict[str, Any] | None:
        """Latest successful hit (email + profile) for this exact query."""
        with self.session() as conn:
            cur = conn.execute(
                """
                SELECT query, email, status, linkedin_url, founder_name, created_at
                FROM lookup_history
                WHERE user_id = ?
                  AND LOWER(TRIM(query)) = LOWER(TRIM(?))
                  AND email IS NOT NULL AND TRIM(email) != ''
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (user_id, query.strip()),
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def get_shared_cached_lookup(self, query: str) -> dict[str, Any] | None:
        key = self.shared_cache_key(query)
        if not key:
            return None
        with self.session() as conn:
            cur = conn.execute(
                """
                SELECT query, email, status, linkedin_url, founder_name, domain, updated_at
                FROM shared_lookup_cache
                WHERE cache_key = ?
                  AND email IS NOT NULL AND TRIM(email) != ''
                  AND updated_at >= datetime('now', ?)
                LIMIT 1
                """,
                (key, f"-{SHARED_LOOKUP_CACHE_TTL_DAYS} days"),
            )
            row = cur.fetchone()
            if not row:
                return None
            conn.execute(
                """
                UPDATE shared_lookup_cache
                SET hit_count = hit_count + 1, updated_at = ?
                WHERE cache_key = ?
                """,
                (_now(), key),
            )
            return dict(row)

    def upsert_shared_lookup_cache(
        self,
        query: str,
        *,
        email: str,
        status: str,
        linkedin_url: str = "",
        founder_name: str = "",
        domain: str = "",
    ) -> None:
        key = self.shared_cache_key(query)
        if not key or not email.strip():
            return
        now = _now()
        with self.session() as conn:
            conn.execute(
                """
                INSERT INTO shared_lookup_cache (
                    cache_key, query, email, status, linkedin_url, founder_name, domain,
                    hit_count, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                ON CONFLICT(cache_key) DO UPDATE SET
                    email = excluded.email,
                    status = excluded.status,
                    linkedin_url = excluded.linkedin_url,
                    founder_name = excluded.founder_name,
                    domain = excluded.domain,
                    hit_count = shared_lookup_cache.hit_count + 1,
                    updated_at = excluded.updated_at
                """,
                (
                    key,
                    query.strip(),
                    email.strip(),
                    status,
                    linkedin_url or "",
                    founder_name or "",
                    domain or "",
                    now,
                    now,
                ),
            )

    def get_cached_profile(self, user_id: str, query: str) -> dict[str, Any] | None:
        """Latest profile URL for this query (skip LinkedIn search, retry email only)."""
        with self.session() as conn:
            cur = conn.execute(
                """
                SELECT query, email, status, linkedin_url, founder_name, created_at
                FROM lookup_history
                WHERE user_id = ?
                  AND LOWER(TRIM(query)) = LOWER(TRIM(?))
                  AND linkedin_url IS NOT NULL AND TRIM(linkedin_url) != ''
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (user_id, query.strip()),
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def list_history(
        self,
        user_id: str,
        *,
        limit: int = 50,
        search: str = "",
        verified_only: bool = False,
        missed_only: bool = False,
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT id, query, email, status, created_at
            FROM lookup_history
            WHERE user_id = ?
        """
        params: list[Any] = [user_id]
        if verified_only:
            sql += " AND email IS NOT NULL AND TRIM(email) != ''"
        if missed_only:
            sql += " AND (email IS NULL OR TRIM(email) = '')"
        if search.strip():
            sql += " AND LOWER(query) LIKE ?"
            params.append(f"%{search.strip().lower()}%")
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        with self.session() as conn:
            cur = conn.execute(sql, params)
            return [dict(r) for r in cur.fetchall()]

    def remove_history_item(self, user_id: str, history_id: str) -> bool:
        with self.session() as conn:
            cur = conn.execute(
                "DELETE FROM lookup_history WHERE user_id = ? AND id = ?",
                (user_id, history_id),
            )
            return cur.rowcount > 0

    def clear_history(
        self,
        user_id: str,
        *,
        search: str = "",
        verified_only: bool = False,
        missed_only: bool = False,
    ) -> int:
        sql = "DELETE FROM lookup_history WHERE user_id = ?"
        params: list[Any] = [user_id]
        if verified_only:
            sql += " AND email IS NOT NULL AND TRIM(email) != ''"
        if missed_only:
            sql += " AND (email IS NULL OR TRIM(email) = '')"
        if search.strip():
            sql += " AND LOWER(query) LIKE ?"
            params.append(f"%{search.strip().lower()}%")
        with self.session() as conn:
            cur = conn.execute(sql, params)
            return int(cur.rowcount or 0)

    def history_has_query(self, user_id: str, query: str) -> bool:
        with self.session() as conn:
            cur = conn.execute(
                """
                SELECT 1 FROM lookup_history
                WHERE user_id = ? AND LOWER(query) = LOWER(?)
                LIMIT 1
                """,
                (user_id, query.strip()),
            )
            return cur.fetchone() is not None

    def activity_by_day(self, user_id: str, days: int = 7) -> list[dict[str, Any]]:
        with self.session() as conn:
            cur = conn.execute(
                """
                SELECT substr(created_at, 1, 10) AS day,
                       COUNT(*) AS total,
                       SUM(CASE WHEN email IS NOT NULL AND TRIM(email) != '' THEN 1 ELSE 0 END) AS verified
                FROM lookup_history
                WHERE user_id = ?
                  AND created_at >= datetime('now', ?)
                GROUP BY substr(created_at, 1, 10)
                ORDER BY day ASC
                """,
                (user_id, f"-{max(days - 1, 0)} days"),
            )
            return [dict(r) for r in cur.fetchall()]

    def add_favorite(self, fav_id: str, user_id: str, query: str, email: str = "") -> None:
        with self.session() as conn:
            conn.execute(
                """
                INSERT INTO favorites (id, user_id, query, email, created_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id, query) DO UPDATE SET email = excluded.email
                """,
                (fav_id, user_id, query.strip(), email, _now()),
            )

    def remove_favorite(self, user_id: str, fav_id: str) -> bool:
        with self.session() as conn:
            cur = conn.execute(
                "DELETE FROM favorites WHERE user_id = ? AND id = ?",
                (user_id, fav_id),
            )
            return cur.rowcount > 0

    def clear_favorites(self, user_id: str) -> int:
        with self.session() as conn:
            cur = conn.execute("DELETE FROM favorites WHERE user_id = ?", (user_id,))
            return int(cur.rowcount or 0)

    def list_favorites(self, user_id: str) -> list[dict[str, Any]]:
        with self.session() as conn:
            cur = conn.execute(
                """
                SELECT id, query, email, created_at
                FROM favorites
                WHERE user_id = ?
                ORDER BY created_at DESC
                """,
                (user_id,),
            )
            return [dict(r) for r in cur.fetchall()]

    def count_today(self, user_id: str) -> int:
        with self.session() as conn:
            cur = conn.execute(
                """
                SELECT COUNT(*) AS n FROM lookup_history
                WHERE user_id = ?
                  AND substr(created_at, 1, 10) = substr(datetime('now'), 1, 10)
                """,
                (user_id,),
            )
            row = cur.fetchone()
            return int(row["n"] or 0) if row else 0

    def recent_queries(self, user_id: str, limit: int = 8) -> list[str]:
        with self.session() as conn:
            cur = conn.execute(
                """
                SELECT query FROM lookup_history
                WHERE user_id = ?
                GROUP BY query
                ORDER BY MAX(created_at) DESC
                LIMIT ?
                """,
                (user_id, limit),
            )
            return [row["query"] for row in cur.fetchall()]

    def count_ai_build_prompts_today(self, user_id: str) -> int:
        with self.session() as conn:
            cur = conn.execute(
                """
                SELECT COUNT(*) AS n FROM build_prompt_usage
                WHERE user_id = ?
                  AND source = 'ai'
                  AND substr(created_at, 1, 10) = substr(datetime('now'), 1, 10)
                """,
                (user_id,),
            )
            row = cur.fetchone()
            return int(row["n"] or 0) if row else 0

    def record_ai_build_prompt(
        self,
        usage_id: str,
        user_id: str,
        query: str,
        prompt_type: str,
    ) -> None:
        with self.session() as conn:
            conn.execute(
                """
                INSERT INTO build_prompt_usage (id, user_id, query, prompt_type, source, created_at)
                VALUES (?, ?, ?, ?, 'ai', ?)
                """,
                (usage_id, user_id, query.strip(), prompt_type, _now()),
            )

    def get_build_prompt_quota(self, user_id: str, *, daily_limit: int) -> dict[str, int]:
        used = self.count_ai_build_prompts_today(user_id)
        remaining = max(0, daily_limit - used)
        return {"limit": daily_limit, "used": used, "remaining": remaining}

    def get_analytics(self, user_id: str) -> dict[str, Any]:
        with self.session() as conn:
            cur = conn.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    SUM(CASE WHEN email IS NOT NULL AND TRIM(email) != '' THEN 1 ELSE 0 END) AS verified
                FROM lookup_history
                WHERE user_id = ?
                """,
                (user_id,),
            )
            row = cur.fetchone()
            total = int(row["total"] or 0) if row else 0
            verified = int(row["verified"] or 0) if row else 0
            rate = round((verified / total) * 100) if total else 0
            return {"total": total, "verified": verified, "hit_rate": rate}

    def save_lookup_job(self, job: dict[str, Any]) -> None:
        result_json = None
        if job.get("result") is not None:
            result_json = json.dumps(job["result"], default=str)
        with self.session() as conn:
            conn.execute(
                """
                INSERT INTO lookup_jobs (
                    id, user_id, query, status, phase, priority,
                    result_json, error, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    status = excluded.status,
                    phase = excluded.phase,
                    result_json = excluded.result_json,
                    error = excluded.error,
                    updated_at = excluded.updated_at
                """,
                (
                    job["id"],
                    job["user_id"],
                    job["query"],
                    job["status"],
                    job["phase"],
                    int(job.get("priority") or 0),
                    result_json,
                    job.get("error"),
                    job["created_at"],
                    job["updated_at"],
                ),
            )

    def get_lookup_job(self, job_id: str) -> dict[str, Any] | None:
        with self.session() as conn:
            row = conn.execute(
                "SELECT * FROM lookup_jobs WHERE id = ?",
                (job_id,),
            ).fetchone()
        if not row:
            return None
        result = None
        if row["result_json"]:
            try:
                result = json.loads(row["result_json"])
            except json.JSONDecodeError:
                result = None
        return {
            "id": row["id"],
            "user_id": row["user_id"],
            "query": row["query"],
            "status": row["status"],
            "phase": row["phase"],
            "priority": row["priority"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "result": result,
            "error": row["error"],
        }

    def count_user_active_jobs(self, user_id: str) -> int:
        with self.session() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS n FROM lookup_jobs
                WHERE user_id = ? AND status IN ('queued', 'running')
                """,
                (user_id,),
            ).fetchone()
        return int(row["n"] or 0) if row else 0

    def fail_stale_running_jobs(self) -> int:
        """Mark interrupted jobs failed after process restart."""
        with self.session() as conn:
            cur = conn.execute(
                """
                UPDATE lookup_jobs
                SET status = 'failed', phase = 'failed',
                    error = 'Interrupted by server restart.',
                    updated_at = ?
                WHERE status = 'running'
                """,
                (_now(),),
            )
            return cur.rowcount
