import unittest
from unittest.mock import patch

from src.custom_email_finder import CustomEmailResult
from src.email_lookup import lookup_email
from src.mailmeteor_auto import MailmeteorAuto


class FakeMailmeteor:
    def __init__(self, email: str, status: str):
        self.email = email
        self.status = status
        self.calls = 0

    async def find_email_with_delay(self, *args, **kwargs):
        self.calls += 1
        return self.email, self.status


class RateLimitedMailmeteor(MailmeteorAuto):
    def __init__(self):
        super().__init__(browser="chrome")
        self.calls = 0

    async def find_email(self, linkedin_url: str, timeout_ms: int | None = None):
        self.calls += 1
        return "", "rate_limit"


class EmailLookupPipelineTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.env_patch = patch.dict("os.environ", {"CUSTOM_EMAIL_BUDGET_SEC": "1"}, clear=False)
        self.env_patch.start()

    async def asyncTearDown(self):
        self.env_patch.stop()

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

    async def test_custom_finder_timeout_falls_back_to_mailmeteor(self):
        async def slow_custom(*args, **kwargs):
            import asyncio

            await asyncio.sleep(5)
            return CustomEmailResult(email="slow@nvidia.com", status="found_custom_public")

        finder = FakeMailmeteor("jensen@nvidia.com", "found")
        with patch("src.email_lookup.find_custom_email", side_effect=slow_custom):
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

    async def test_mailmeteor_skip_cooldown_returns_rate_limit_without_waiting(self):
        finder = RateLimitedMailmeteor()
        with patch("src.mailmeteor_auto.asyncio.sleep") as sleep:
            email, status = await finder.find_email_with_delay(
                "https://www.linkedin.com/in/jensenhuang/",
                rate_limit_wait_minutes=8,
                skip_cooldown=True,
            )
        self.assertEqual(email, "")
        self.assertEqual(status, "rate_limit")
        self.assertEqual(finder.calls, 1)
        sleep.assert_not_called()


if __name__ == "__main__":
    unittest.main()
