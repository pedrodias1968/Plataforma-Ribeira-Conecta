"""Unit tests for ribeira_platform.time_utils.

Covers the pure helpers only. No database, network or external provider is
required; every case here is deterministic and local.
"""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from ribeira_platform.time_utils import canonical_utc, parse_aware


class ParseAwareTests(unittest.TestCase):
    def test_parses_zulu_suffix_as_utc(self) -> None:
        parsed = parse_aware("2026-09-11T10:59:10Z")
        self.assertEqual(parsed.tzinfo, timezone.utc)
        self.assertEqual(parsed.utcoffset(), timedelta(0))
        self.assertEqual(
            parsed, datetime(2026, 9, 11, 10, 59, 10, tzinfo=timezone.utc)
        )

    def test_parses_explicit_utc_offset(self) -> None:
        parsed = parse_aware("2026-09-11T10:59:10+00:00")
        self.assertEqual(parsed, datetime(2026, 9, 11, 10, 59, 10, tzinfo=timezone.utc))

    def test_preserves_non_utc_offset(self) -> None:
        parsed = parse_aware("2026-09-11T08:00:00-03:00")
        self.assertEqual(parsed.utcoffset(), timedelta(hours=-3))
        self.assertEqual(parsed.hour, 8)

    def test_rejects_naive_timestamp(self) -> None:
        with self.assertRaises(ValueError):
            parse_aware("2026-09-11T10:59:10")

    def test_rejects_empty_string(self) -> None:
        with self.assertRaises(ValueError):
            parse_aware("")

    def test_rejects_malformed_input(self) -> None:
        with self.assertRaises(ValueError):
            parse_aware("not-a-timestamp")

    def test_rejects_lowercase_z_suffix(self) -> None:
        # Only uppercase "Z" is normalized by the module.
        with self.assertRaises(ValueError):
            parse_aware("2026-09-11T10:59:10z")

    def test_parses_microseconds(self) -> None:
        parsed = parse_aware("2026-09-11T10:59:10.123456+00:00")
        self.assertEqual(parsed.microsecond, 123456)


class CanonicalUtcTests(unittest.TestCase):
    def test_normalizes_zulu_to_utc_isoformat(self) -> None:
        self.assertEqual(
            canonical_utc("2026-09-11T10:59:10Z"),
            "2026-09-11T10:59:10+00:00",
        )

    def test_converts_offset_to_utc(self) -> None:
        self.assertEqual(
            canonical_utc("2026-09-11T08:00:00-03:00"),
            "2026-09-11T11:00:00+00:00",
        )

    def test_output_is_reparseable(self) -> None:
        canonical = canonical_utc("2026-09-14T20:00:00-03:00")
        reparsed = parse_aware(canonical)
        self.assertEqual(reparsed, datetime(2026, 9, 14, 23, 0, 0, tzinfo=timezone.utc))

    def test_rejects_naive_timestamp(self) -> None:
        with self.assertRaises(ValueError):
            canonical_utc("2026-09-11T10:59:10")

    def test_rejects_malformed_input(self) -> None:
        with self.assertRaises(ValueError):
            canonical_utc("not-a-timestamp")


if __name__ == "__main__":
    unittest.main()
