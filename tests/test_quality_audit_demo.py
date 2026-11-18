"""Checks for the public, synthetic finite-population audit example."""

import math
import unittest

from quality_audit_demo import (
    demonstration,
    minimum_zero_miss_sample,
    probability_of_zero_misses,
    select_ids,
)


class FinitePopulationAuditTests(unittest.TestCase):
    def test_current_aggregate_plan_is_minimal(self) -> None:
        plan = minimum_zero_miss_sample(3_849, 0.01, 0.05)
        self.assertEqual((plan["defective_count_at_ceiling"], plan["minimum_sample"]), (39, 284))
        self.assertGreater(plan["probability_zero_with_one_fewer"], 0.05)
        self.assertLessEqual(plan["probability_zero_at_minimum"], 0.05)
        self.assertTrue(math.isclose(plan["probability_zero_at_minimum"], 0.049550284409080256))

    def test_probability_matches_exact_combinations(self) -> None:
        expected = math.comb(17, 5) / math.comb(20, 5)
        self.assertAlmostEqual(probability_of_zero_misses(20, 3, 5), expected)
        self.assertEqual(probability_of_zero_misses(20, 3, 18), 0.0)

    def test_draw_replays_without_duplicates(self) -> None:
        ids = [f"synthetic-{number}" for number in range(30)]
        seed = "ab" * 32
        first = select_ids(ids, 7, seed)
        self.assertEqual(first, select_ids(list(reversed(ids)), 7, seed))
        self.assertEqual(len(first), len(set(first)))

    def test_invalid_inputs_fail_closed(self) -> None:
        with self.assertRaises(ValueError):
            minimum_zero_miss_sample(0, 0.01, 0.05)
        with self.assertRaises(ValueError):
            select_ids(["a", "a"], 1, "00" * 32)
        with self.assertRaises(ValueError):
            select_ids(["a"], 1, "not-a-seed")

    def test_demo_is_explicitly_synthetic(self) -> None:
        result = demonstration()
        self.assertIn("SYNTHETIC", result["data_type"])
        self.assertEqual(result["synthetic_draw"]["selected_count"], 284)
        self.assertTrue(result["synthetic_draw"]["all_unique"])


if __name__ == "__main__":
    unittest.main()
