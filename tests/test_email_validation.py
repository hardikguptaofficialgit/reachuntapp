import unittest
from unittest.mock import patch

from src.email_validation import validate_email


class EmailValidationTests(unittest.TestCase):
    def test_invalid_syntax(self):
        result = validate_email("john@", check_smtp=False)
        self.assertEqual(result.verdict, "invalid")
        self.assertFalse(result.valid_syntax)
        self.assertEqual(result.score, 0)

    def test_no_mx_is_undeliverable(self):
        with patch("src.email_validation._domain_mx", return_value=[]):
            result = validate_email("john@example.invalid", check_smtp=False)
        self.assertEqual(result.verdict, "undeliverable")
        self.assertFalse(result.mx_found)

    def test_disposable_is_risky(self):
        with patch("src.email_validation._domain_mx", return_value=["mx.mailinator.com"]):
            result = validate_email("john@mailinator.com", check_smtp=False)
        self.assertEqual(result.verdict, "risky")
        self.assertTrue(result.disposable)

    def test_business_email_with_mx_is_likely(self):
        with patch("src.email_validation._domain_mx", return_value=["mx.acme.com"]):
            result = validate_email("jane@acme.com", check_smtp=False)
        self.assertEqual(result.verdict, "likely")
        self.assertGreaterEqual(result.score, 60)

    def test_available_address_is_role_account(self):
        with patch("src.email_validation._domain_mx", return_value=["mx.nvidia.com"]):
            result = validate_email("available@nvidia.com", check_smtp=False)
        self.assertTrue(result.role_account)
        self.assertIn("role_account", result.signals)

    def test_smtp_accept_boosts_to_verified(self):
        with (
            patch("src.email_validation._domain_mx", return_value=["mx.acme.com"]),
            patch("src.email_validation._smtp_check", return_value=(True, False)),
        ):
            result = validate_email("jane@acme.com", check_smtp=True)
        self.assertEqual(result.verdict, "verified")
        self.assertTrue(result.smtp_valid)


if __name__ == "__main__":
    unittest.main()
