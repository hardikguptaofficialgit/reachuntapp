import os
import unittest
from unittest.mock import patch

from src.custom_email_finder import _discover_internal_links, find_custom_email
from src.email_validation import EmailValidation


def validation(
    email: str,
    *,
    verdict: str = "likely",
    score: int = 65,
    role_account: bool = False,
    catch_all=None,
) -> EmailValidation:
    return EmailValidation(
        email=email,
        valid_syntax=True,
        domain_valid=True,
        mx_found=True,
        disposable=False,
        free_provider=False,
        role_account=role_account,
        smtp_checked=False,
        smtp_valid=None,
        catch_all=catch_all,
        score=score,
        verdict=verdict,
        signals=["syntax_ok", "domain_ok", "mx_found"],
    )


class CustomEmailFinderTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.old_env = dict(os.environ)
        os.environ["CUSTOM_EMAIL_FINDER"] = "true"
        os.environ["CUSTOM_EMAIL_PUBLIC_SEARCH"] = "true"
        os.environ["CUSTOM_EMAIL_SITE_SCRAPE"] = "false"
        os.environ["CUSTOM_EMAIL_PATTERN_SMTP"] = "false"

    async def asyncTearDown(self):
        os.environ.clear()
        os.environ.update(self.old_env)

    async def test_rejects_generic_public_email(self):
        with patch("src.custom_email_finder._get_ddgs") as get_ddgs:
            get_ddgs.return_value.text.return_value = [
                {"title": "NVIDIA contact", "body": "Email available@nvidia.com", "href": ""}
            ]
            result = await find_custom_email(name="Jensen Huang", domain="nvidia.com")
        self.assertEqual(result.email, "")

    async def test_rejects_name_email_without_person_context(self):
        with (
            patch("src.custom_email_finder._get_ddgs") as get_ddgs,
            patch("src.custom_email_finder.validate_email", return_value=validation("jensen.huang@nvidia.com")),
        ):
            get_ddgs.return_value.text.return_value = [
                {"title": "NVIDIA contact", "body": "Email jensen.huang@nvidia.com", "href": ""}
            ]
            result = await find_custom_email(name="Jensen Huang", domain="nvidia.com")
        self.assertEqual(result.email, "")

    async def test_accepts_public_name_matched_email(self):
        with (
            patch("src.custom_email_finder._get_ddgs") as get_ddgs,
            patch("src.custom_email_finder.validate_email", return_value=validation("jensen.huang@nvidia.com")),
        ):
            get_ddgs.return_value.text.return_value = [
                {"title": "Jensen Huang", "body": "Jensen Huang email jensen.huang@nvidia.com", "href": ""}
            ]
            result = await find_custom_email(name="Jensen Huang", domain="nvidia.com")
        self.assertEqual(result.email, "jensen.huang@nvidia.com")
        self.assertEqual(result.status, "found_custom_public")

    async def test_pattern_requires_smtp_flag(self):
        os.environ["CUSTOM_EMAIL_PUBLIC_SEARCH"] = "false"
        result = await find_custom_email(name="Jensen Huang", domain="nvidia.com")
        self.assertEqual(result.email, "")

    async def test_accepts_smtp_verified_pattern_when_enabled(self):
        os.environ["CUSTOM_EMAIL_PUBLIC_SEARCH"] = "false"
        os.environ["CUSTOM_EMAIL_PATTERN_SMTP"] = "true"
        with patch(
            "src.custom_email_finder.validate_email",
            return_value=validation(
                "jensen.huang@nvidia.com",
                verdict="verified",
                score=90,
                catch_all=False,
            ),
        ):
            result = await find_custom_email(name="Jensen Huang", domain="nvidia.com")
        self.assertEqual(result.email, "jensen.huang@nvidia.com")
        self.assertEqual(result.status, "found_custom_smtp")


class InternalLinkDiscoveryTests(unittest.TestCase):
    def test_discovers_relevant_company_links_only(self):
        html = """
        <a href="/team">Team</a>
        <a href="https://nvidia.com/leadership/jensen">Leadership</a>
        <a href="https://evil.example/team">External team</a>
        <a href="/pricing">Pricing</a>
        """
        links = _discover_internal_links(
            html,
            base_url="https://nvidia.com",
            domain="nvidia.com",
            limit=5,
        )
        self.assertIn("https://nvidia.com/team", links)
        self.assertIn("https://nvidia.com/leadership/jensen", links)
        self.assertNotIn("https://evil.example/team", links)
        self.assertNotIn("https://nvidia.com/pricing", links)


if __name__ == "__main__":
    unittest.main()
