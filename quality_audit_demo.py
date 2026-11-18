"""Offline example of a finite-population, zero-acceptance source audit.

The sample-size arithmetic reflects the thesis's approved audit rule. The IDs
and seed used below are synthetic; this does not reproduce the private draw or
classify any original SEC document.
"""

from __future__ import annotations

import hashlib
import json
import math


def probability_of_zero_misses(population: int, defective: int, sample: int) -> float:
    """Exact P(no defects drawn) under sampling without replacement."""
    if not all(type(value) is int for value in (population, defective, sample)):
        raise TypeError("Counts must be integers")
    if population < 1 or not 0 <= defective <= population or not 0 <= sample <= population:
        raise ValueError("Counts must describe a nonempty finite population")
    if sample > population - defective:
        return 0.0
    probability = 1.0
    for draw in range(sample):
        probability *= (population - defective - draw) / (population - draw)
    return probability


def minimum_zero_miss_sample(population: int, ceiling: float, false_pass_limit: float) -> dict:
    """Find the smallest zero-acceptance sample for a chosen quality ceiling."""
    if type(population) is not int or population < 1:
        raise ValueError("Population must be a positive integer")
    if not math.isfinite(ceiling) or not 0 < ceiling <= 1:
        raise ValueError("Ceiling must be in (0, 1]")
    if not math.isfinite(false_pass_limit) or not 0 < false_pass_limit < 1:
        raise ValueError("False-pass limit must be in (0, 1)")
    defective = math.ceil(ceiling * population)
    sample = 0
    probability = 1.0
    while probability > false_pass_limit:
        probability *= (population - defective - sample) / (population - sample)
        sample += 1
    return {
        "population": population,
        "project_chosen_ceiling": ceiling,
        "false_pass_limit": false_pass_limit,
        "defective_count_at_ceiling": defective,
        "minimum_sample": sample,
        "probability_zero_at_minimum": probability,
        "probability_zero_with_one_fewer": probability_of_zero_misses(
            population, defective, sample - 1
        ),
    }


def select_ids(ids: list[str], sample_size: int, seed_hex: str) -> list[str]:
    """Select unique IDs by a recorded-seed partial Fisher–Yates shuffle."""
    if not all(isinstance(item, str) and item for item in ids):
        raise ValueError("Frame IDs must be nonempty strings")
    if len(set(ids)) != len(ids):
        raise ValueError("Frame IDs must be unique")
    if type(sample_size) is not int or not 0 <= sample_size <= len(ids):
        raise ValueError("Sample size must fit the frame")
    try:
        seed = bytes.fromhex(seed_hex)
    except (TypeError, ValueError) as exc:
        raise ValueError("Seed must be 64 hexadecimal characters") from exc
    if len(seed) != 32:
        raise ValueError("Seed must be 64 hexadecimal characters")

    frame = sorted(ids)
    counter = 0

    def random_below(bound: int) -> int:
        nonlocal counter
        ceiling = (1 << 256) - ((1 << 256) % bound)
        while True:
            digest = hashlib.sha256(
                b"sec-zero-srs-v1\0" + seed + counter.to_bytes(8, "big")
            ).digest()
            counter += 1
            value = int.from_bytes(digest, "big")
            if value < ceiling:
                return value % bound

    for position in range(sample_size):
        chosen = position + random_below(len(frame) - position)
        frame[position], frame[chosen] = frame[chosen], frame[position]
    return frame[:sample_size]


def demonstration() -> dict:
    plan = minimum_zero_miss_sample(3_849, 0.01, 0.05)
    synthetic_frame = [f"synthetic-letter-{number:04d}" for number in range(3_849)]
    synthetic_seed = "00" * 32  # Fixed for the public example; not the thesis seed.
    selected = select_ids(synthetic_frame, plan["minimum_sample"], synthetic_seed)
    fingerprint = hashlib.sha256("\n".join(selected).encode("utf-8")).hexdigest()
    return {
        "data_type": "SYNTHETIC IDs — no real sampled SEC letters",
        "plan": plan,
        "synthetic_draw": {
            "selected_count": len(selected),
            "all_unique": len(set(selected)) == len(selected),
            "draw_sha256": fingerprint,
        },
        "interpretation": "A plan and draw are not a passed source audit.",
    }


if __name__ == "__main__":
    print(json.dumps(demonstration(), indent=2))
