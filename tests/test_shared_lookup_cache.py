import tempfile
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()

