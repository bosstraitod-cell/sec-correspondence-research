from datetime import date
from pathlib import Path
import math
import unittest

from research_demo import align_wrapper, demonstration, eligible, weekly_rv

FIXTURE = (Path(__file__).resolve().parents[1] / "examples/synthetic_wrapper.txt").read_text()


class TimingAndMembershipTests(unittest.TestCase):
    def test_expected_public_and_target_dates(self):
        row = align_wrapper(FIXTURE)
        self.assertEqual(row["filed"], "2024-01-08")
        self.assertEqual(row["public_archive"], "2024-03-14")
        self.assertEqual(row["information_week"], "2024-03-15")
        self.assertEqual(row["target_week"], "2024-03-22")
        self.assertEqual(row["lag_calendar_days"], 66)

    def test_header_date_does_not_override_outer_date(self):
        text = FIXTURE.replace(".hdr.sgml : 20240313", ".hdr.sgml : 20240108")
        self.assertEqual(align_wrapper(text)["public_archive"], "2024-03-14")

    def test_weekend_and_year_boundary(self):
        text = FIXTURE.replace(".txt : 20240314", ".txt : 20241228")
        row = align_wrapper(text)
        self.assertEqual(row["information_week"], "2025-01-03")
        self.assertEqual(row["target_week"], "2025-01-10")

    def test_invalid_wrappers_fail(self):
        for text in [FIXTURE.replace("<PRIVATE-TO-PUBLIC>", ""),
                     FIXTURE.replace("UPLOAD", "CORRESP"),
                     FIXTURE.replace(".txt : 20240314", ".txt : 20230101"),
                     FIXTURE.replace(".txt : 20240314", ".txt : 20240230"),
                     FIXTURE.replace("20240108133005", "20240109133005")]:
            with self.subTest(text=text), self.assertRaises(ValueError):
                align_wrapper(text)

    def test_end_exclusive_and_start_inclusive(self):
        start, end = date(2024, 1, 8), date(2024, 2, 1)
        self.assertTrue(eligible(start, start, end))
        self.assertFalse(eligible(end, start, end))
        self.assertFalse(eligible(date(2023, 12, 31), start, end))
        self.assertTrue(eligible(date(2025, 1, 1), start, None))

    def test_release_after_exit_does_not_change_filing_eligibility(self):
        self.assertTrue(demonstration()["timing"]["membership_eligible_at_filing"])


class VolatilityTests(unittest.TestCase):
    def setUp(self):
        self.sessions = [date(2024, 3, day) for day in (18, 19, 20, 22)]
        self.closes = list(zip([date(2024, 3, 15)] + self.sessions,
                               [100, 100 * math.exp(.01), 100, 100 * math.exp(.02), 100]))

    def test_known_squared_returns_and_four_day_scaling(self):
        result = weekly_rv(self.closes, self.sessions)
        self.assertAlmostEqual(result["raw_rv"], math.sqrt(.001))
        self.assertAlmostEqual(result["five_day_normalized_rv"], math.sqrt(.00125))

    def test_exact_duplicate_is_neutral(self):
        self.assertEqual(weekly_rv(self.closes, self.sessions),
                         weekly_rv(self.closes + [self.closes[-1]], self.sessions))

    def test_conflicting_duplicate_fails(self):
        with self.assertRaises(ValueError):
            weekly_rv(self.closes + [(self.sessions[-1], 99)], self.sessions)

    def test_missing_and_unexpected_sessions_fail(self):
        for closes in [self.closes[1:], self.closes[:-1],
                       self.closes + [(date(2024, 3, 21), 101)]]:
            with self.subTest(closes=closes), self.assertRaises(ValueError):
                weekly_rv(closes, self.sessions)

    def test_invalid_prices_fail(self):
        for price in [0, -1, float("nan"), float("inf")]:
            with self.subTest(price=price), self.assertRaises(ValueError):
                weekly_rv(self.closes[:-1] + [(self.sessions[-1], price)], self.sessions)

    def test_zero_volatility_has_undefined_log(self):
        result = weekly_rv([(day, 100) for day, _ in self.closes], self.sessions)
        self.assertEqual(result["raw_rv"], 0)
        self.assertIsNone(result["log_normalized_rv"])

    def test_sessions_cannot_span_weeks(self):
        with self.assertRaises(ValueError):
            weekly_rv(self.closes, [date(2024, 3, 15), date(2024, 3, 18)])


if __name__ == "__main__":
    unittest.main()
