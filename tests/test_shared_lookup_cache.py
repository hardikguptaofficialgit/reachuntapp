import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timezone

from api.db import Database


class SharedLookupCacheTests(unittest.TestCase):
    def test_shared_cache_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "webapp.db")
            db.upsert_shared_lookup_cache(
                "Jensen Huang - nvidia.com",
                email="jensen.huang@nvidia.com",
                status="verified",
                linkedin_url="https://www.linkedin.com/in/jensenhuang/",
                founder_name="Jensen Huang",
                domain="nvidia.com",
            )
            hit = db.get_shared_cached_lookup("  jensen   huang - NVIDIA.com ")
            self.assertIsNotNone(hit)
            self.assertEqual(hit["email"], "jensen.huang@nvidia.com")
            self.assertEqual(hit["domain"], "nvidia.com")

    def test_shared_cache_does_not_store_empty_email(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "webapp.db")
            db.upsert_shared_lookup_cache("no hit", email="", status="unavailable")
            self.assertIsNone(db.get_shared_cached_lookup("no hit"))

    def test_count_lookup_jobs_today_counts_queued_jobs(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "webapp.db")
            now = datetime.now(timezone.utc).isoformat()
            with db.session() as conn:
                conn.execute(
                    """
                    INSERT INTO lookup_jobs (
                        id, user_id, query, status, phase, priority,
                        result_json, error, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    ("job-1", "user-1", "Alice - example.com", "queued", "queued", 0, None, None, now, now),
                )
            self.assertEqual(db.count_lookup_jobs_today("user-1"), 1)
            self.assertEqual(db.count_lookup_jobs_today("user-2"), 0)


if __name__ == "__main__":
    unittest.main()
