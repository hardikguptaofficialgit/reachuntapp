import unittest
from unittest.mock import patch

from src.custom_email_finder import CustomEmailResult
from src.email_lookup import lookup_email


class FakeMailmeteor:
    def __init__(self, email: str, status: str):
        self.email = email
        self.status = status
        self.calls = 0

    async def find_email_with_delay(self, *args, **kwargs):
        self.calls += 1
        return self.email, self.status


class EmailLookupPipelineTests(unittest.IsolatedAsyncioTestCase):
    async def test_mailmeteor_fallback_when_custom_has_no_hit(self):
        finder = FakeMailmeteor("jensen@nvidia.com", "found")
        with patch("src.email_lookup.find_custom_email", return_value=CustomEmailResult()):
            email, status = await lookup_email(
                finder,
                "https://www.linkedin.com/in/jensenhuang/",
                rate_limit_wait_minutes=0,
                name="Jensen Huang",
                domain="nvidia.com",
            )
        self.assertEqual(email, "jensen@nvidia.com")
        self.assertEqual(status, "found")
        self.assertEqual(finder.calls, 1)

    async def test_custom_hit_skips_mailmeteor(self):
        finder = FakeMailmeteor("mailmeteor@nvidia.com", "found")
        custom = CustomEmailResult(email="jensen.huang@nvidia.com", status="found_custom_public")
        with patch("src.email_lookup.find_custom_email", return_value=custom):
            email, status = await lookup_email(
                finder,
                "https://www.linkedin.com/in/jensenhuang/",
                rate_limit_wait_minutes=0,
                name="Jensen Huang",
                domain="nvidia.com",
            )
        self.assertEqual(email, "jensen.huang@nvidia.com")
        self.assertEqual(status, "found_custom_public")
        self.assertEqual(finder.calls, 0)


if __name__ == "__main__":
    unittest.main()

