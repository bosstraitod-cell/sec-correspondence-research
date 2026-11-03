"""Offline demonstration of SEC date alignment and daily-close weekly RV.

All embedded records and prices are synthetic. This is a portfolio adaptation,
not the production thesis panel or an empirical SEC/volatility test.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from datetime import date, timedelta
from pathlib import Path
import argparse

from scripts.audit_sec_information_timing import parse_wrapper, friday_of_week

ROOT = Path(__file__).resolve().parent


def eligible(filed: date, start: date, end: date | None) -> bool:
    """Membership is start-inclusive and end-exclusive at the filing date."""
    if end is not None and end <= start:
        raise ValueError("Membership end must follow start")
    return start <= filed and (end is None or filed < end)


def align_wrapper(text: str) -> dict[str, str | int]:
    """Apply this thesis's outer-archive-date rule to one private UPLOAD."""
    parsed = parse_wrapper(text)
    if not parsed["private_to_public"] or parsed["submission_type"] != "UPLOAD":
        raise ValueError("Expected a private-to-public UPLOAD wrapper")
    if not parsed["accession"]:
        raise ValueError("Missing accession")
    filed = date.fromisoformat(str(parsed["filed_as_of_raw"]))
    public = date.fromisoformat(str(parsed["sec_document_raw"]))
    acceptance = str(parsed["acceptance_date_raw"])
    if not acceptance or date.fromisoformat(acceptance) != filed:
        raise ValueError("Missing or inconsistent private acceptance date")
    if public < filed:
        raise ValueError("Public archive date precedes private filing date")
    # Header and acceptance dates never substitute for the outer archive date.
    week = friday_of_week(public)
    assert week is not None
    return {
        "accession": str(parsed["accession"]),
        "filed": filed.isoformat(),
        "public_archive": public.isoformat(),
        "information_week": week.isoformat(),
        "target_week": (week + timedelta(days=7)).isoformat(),
        "lag_calendar_days": (public - filed).days,
    }


def weekly_rv(closes: list[tuple[date, float]], expected_sessions: list[date]) -> dict:
    """Compute one week's RV with an explicit predecessor and session calendar.

    Callers supply verified sessions. This demo does not implement an exchange
    holiday calendar. Exact duplicates collapse; conflicting duplicates fail.
    """
    if not 1 <= len(expected_sessions) <= 5:
        raise ValueError("Expected one to five trading sessions")
    if expected_sessions != sorted(set(expected_sessions)):
        raise ValueError("Expected sessions must be sorted and unique")
    if len({friday_of_week(day) for day in expected_sessions}) != 1:
        raise ValueError("Sessions must belong to one target week")
    prices: dict[date, float] = {}
    for day, close in closes:
        if not math.isfinite(close) or close <= 0:
            raise ValueError("Prices must be positive and finite")
        if day in prices and prices[day] != close:
            raise ValueError("Conflicting duplicate price")
        prices[day] = close
    predecessors = [day for day in prices if day < expected_sessions[0]]
    if len(predecessors) != 1:
        raise ValueError("Supply exactly one predecessor close")
    if set(prices) != set(expected_sessions) | set(predecessors):
        raise ValueError("Missing session or unexpected price date")
    previous = prices[predecessors[0]]
    returns = []
    for day in expected_sessions:
        current = prices[day]
        returns.append(math.log(current / previous))
        previous = current
    variance = math.fsum(value * value for value in returns)
    raw = math.sqrt(variance)
    normalized = raw * math.sqrt(5 / len(returns))
    return {"trading_sessions": len(returns), "raw_rv": raw,
            "five_day_normalized_rv": normalized,
            "log_normalized_rv": math.log(normalized) if normalized > 0 else None}


def demonstration() -> dict:
    fixture = ROOT / "examples" / "synthetic_wrapper.txt"
    record = align_wrapper(fixture.read_text())
    record["membership_eligible_at_filing"] = eligible(
        date.fromisoformat(str(record["filed"])), date(2023, 1, 1), date(2024, 2, 1))
    # This deliberately has four sessions. Dates/prices are a made-up exercise.
    sessions = [date(2024, 3, day) for day in (18, 19, 20, 22)]
    prices = list(zip([date(2024, 3, 15)] + sessions, [100, 101, 100, 102, 101]))
    rv = weekly_rv(prices, sessions)
    return {"data_type": "SYNTHETIC — no real issuer, price or market result",
            "fixture_sha256": hashlib.sha256(fixture.read_bytes()).hexdigest(),
            "timing": record, "independent_rv_example": rv,
            "interpretation": "Demonstrates mechanics only; no SEC–RV relationship estimated."}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "demo_output")
    args = parser.parse_args()
    result = demonstration()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "demo.json").write_text(json.dumps(result, indent=2) + "\n")
    row = result["timing"]
    with (args.output_dir / "timing.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
