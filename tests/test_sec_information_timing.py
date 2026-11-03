#!/usr/bin/env python3
"""Unit tests for the non-destructive SEC information-timing audit."""

from __future__ import annotations

from datetime import date
import sys
from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from audit_sec_information_timing import (  # noqa: E402
    choose_availability,
    friday_of_week,
    parse_wrapper,
)


PRIVATE_UPLOAD = """\
<SEC-DOCUMENT>0000000000-06-000155.txt : 20061011
<SEC-HEADER>0000000000-06-000155.hdr.sgml : 20061011
<ACCEPTANCE-DATETIME>20060103133005
<PRIVATE-TO-PUBLIC>
ACCESSION NUMBER:        0000000000-06-000155
CONFORMED SUBMISSION TYPE: UPLOAD
FILED AS OF DATE:        20060103
PUBLIC REFERENCE ACCESSION NUMBER: 0000950135-05-001489 [HTML]
"""


class TimingParserTests(unittest.TestCase):
    def test_private_upload_fields_are_separate(self) -> None:
        parsed = parse_wrapper(PRIVATE_UPLOAD)
        self.assertEqual(parsed["acceptance_raw"], "20060103133005")
        self.assertEqual(parsed["filed_as_of_raw"], "20060103")
        self.assertEqual(parsed["sec_document_raw"], "20061011")
        self.assertEqual(parsed["sec_header_raw"], "20061011")
        self.assertTrue(parsed["private_to_public"])
        self.assertEqual(parsed["accession"], "0000000000-06-000155")
        self.assertEqual(parsed["submission_type"], "UPLOAD")
        self.assertEqual(
            parsed["public_reference_accession"],
            "0000950135-05-001489",
        )

    def test_sec_document_date_is_date_only_fallback(self) -> None:
        parsed = parse_wrapper(PRIVATE_UPLOAD)
        candidate = choose_availability(parsed)
        self.assertEqual(candidate[0], "20061011")
        self.assertEqual(candidate[1], "")
        self.assertEqual(candidate[2], "SEC-DOCUMENT archive date")
        self.assertEqual(
            candidate[3], "date_only_no_public_time_in_archived_wrapper"
        )

    def test_public_release_tag_has_priority(self) -> None:
        parsed = parse_wrapper(
            PRIVATE_UPLOAD + "\n<PUBLIC-REL-DATE>20061012\n"
        )
        candidate = choose_availability(parsed)
        self.assertEqual(candidate[0], "20061012")
        self.assertEqual(candidate[2], "PUBLIC-REL-DATE")

    def test_pds_timestamp_provides_time_when_release_tag_absent(self) -> None:
        parsed = parse_wrapper(
            PRIVATE_UPLOAD + "\n<TIMESTAMP>20061011:091530\n"
        )
        candidate = choose_availability(parsed)
        self.assertEqual(candidate[0], "20061011")
        self.assertEqual(candidate[1], "20061011091530")
        self.assertEqual(candidate[2], "PDS_TIMESTAMP")

    def test_friday_calendar_assignment(self) -> None:
        self.assertEqual(friday_of_week(date(2025, 1, 6)), date(2025, 1, 10))
        self.assertEqual(friday_of_week(date(2025, 1, 10)), date(2025, 1, 10))
        self.assertEqual(friday_of_week(date(2025, 1, 11)), date(2025, 1, 17))


if __name__ == "__main__":
    unittest.main()
