"""Golden tests — Python parse is the source of truth for lookups."""

from __future__ import annotations

import unittest

from src.query_intent import QueryKind, query_kind_for
from src.query_parse import parse_person_query


class TestQueryParseGolden(unittest.TestCase):
    def test_person_split(self):
        pq = parse_person_query("Jane Doe — acme.com")
        self.assertEqual(pq.name, "Jane Doe")
        self.assertEqual(pq.domain, "acme.com")
        self.assertFalse(pq.company_only)
        self.assertEqual(query_kind_for(pq), QueryKind.PERSON)

    def test_person_split_company_name_infers_domain(self):
        pq = parse_person_query("Kanish Gupta - ZSCALER")
        self.assertEqual(pq.name, "Kanish Gupta")
        self.assertEqual(pq.domain, "zscaler.com")
        self.assertFalse(pq.company_only)
        self.assertEqual(query_kind_for(pq), QueryKind.PERSON)

    def test_company_domain(self):
        pq = parse_person_query("stripe.com")
        self.assertEqual(pq.domain, "stripe.com")
        self.assertTrue(pq.company_only)
        self.assertEqual(query_kind_for(pq), QueryKind.COMPANY_DOMAIN)

    def test_company_name_notion(self):
        pq = parse_person_query("Notion")
        self.assertEqual(pq.domain, "notion.so")
        self.assertTrue(pq.company_only)
        self.assertEqual(query_kind_for(pq), QueryKind.COMPANY_NAME)

    def test_person_name_without_company_rejected(self):
        with self.assertRaises(ValueError):
            parse_person_query("arushi gupta")

    def test_empty_rejected(self):
        with self.assertRaises(ValueError):
            parse_person_query("   ")


if __name__ == "__main__":
    unittest.main()
