#!/usr/bin/env python3
"""Audit SEC UPLOAD timing fields without modifying the completed census.

The matched filing manifest points to SEC submission wrappers already preserved
locally.  This script extracts the private acceptance fields and the later
private-to-public archive fields into a sidecar dataset.  It deliberately does
not replace ``DateFiled`` in the approved membership rule.
"""

from __future__ import annotations

import argparse
import csv
from datetime import date, datetime, timedelta
import hashlib
from pathlib import Path
import re
import statistics
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = (
    PROJECT_ROOT
    / "data/sec_upload_documents_2006_2025/download_manifest.csv"
)
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data/audit"
CANONICAL_CENSUS = (
    PROJECT_ROOT / "data/sec_upload_census_2006_2025/upload_metadata_sp500.csv"
)
EXISTING_INTEGRITY_REPORT = (
    PROJECT_ROOT / "data/audit/extended_integrity_report_2006_2025.csv"
)
STUDY_END = date(2025, 12, 31)
EXPECTED_FILINGS = 11_607

DATE_FILED_RE = re.compile(
    r"(?im)^FILED AS OF DATE:[ \t]*(\d{8})[ \t]*$"
)
ACCEPTANCE_RE = re.compile(
    r"(?im)^<ACCEPTANCE-DATETIME>[ \t]*(\d{14})[ \t]*$"
)
SEC_DOCUMENT_RE = re.compile(
    r"(?im)^<SEC-DOCUMENT>[^\r\n]*?:[ \t]*(\d{8})[ \t]*$"
)
SEC_HEADER_RE = re.compile(
    r"(?im)^<SEC-HEADER>[^\r\n]*?:[ \t]*(\d{8})[ \t]*$"
)
PUBLIC_RELEASE_RE = re.compile(
    r"(?im)^<PUBLIC-REL-DATE>[ \t]*(\d{8})[ \t]*$"
)
PDS_TIMESTAMP_RE = re.compile(
    r"(?im)^<TIMESTAMP>[ \t]*(\d{8}):?(\d{6})[ \t]*$"
)
PRIVATE_TO_PUBLIC_RE = re.compile(
    r"(?im)^<PRIVATE-TO-PUBLIC>[ \t]*$"
)
ACCESSION_RE = re.compile(
    r"(?im)^ACCESSION NUMBER:[ \t]*([0-9-]+)[ \t]*$"
)
SUBMISSION_TYPE_RE = re.compile(
    r"(?im)^CONFORMED SUBMISSION TYPE:[ \t]*([^\r\n]+?)\s*$"
)
PUBLIC_REFERENCE_RE = re.compile(
    r"(?im)^PUBLIC REFERENCE ACCESSION NUMBER:[ \t]*"
    r"([0-9-]+)(?:[ \t]+\[[^\]]+\])?[ \t]*$"
)

OUTPUT_FIELDS = [
    "CIK",
    "CompanyName",
    "FormType",
    "DateFiled",
    "FileName",
    "URL",
    "LocalRawPath",
    "LetterDocumentDate",
    "LetterDocumentDateStatus",
    "AcceptanceDateTimeRaw",
    "AcceptanceDate",
    "FiledAsOfDate",
    "SecDocumentDate",
    "SecHeaderDate",
    "SecHeaderDateEqualsSecDocumentDate",
    "SecHeaderToDocumentLagCalendarDays",
    "PublicReleaseDateTag",
    "PdsDisseminationTimestampRaw",
    "AvailabilityDateCandidate",
    "AvailabilityDateTimeCandidate",
    "AvailabilityCandidateSource",
    "AvailabilityTimeStatus",
    "PrivateToPublicFlag",
    "WrapperAccessionNumber",
    "AccessionMatchesFileName",
    "WrapperSubmissionType",
    "PublicReferenceAccessionNumber",
    "RawFileStatus",
    "RawByteLengthManifest",
    "RawByteLengthObserved",
    "RawByteLengthMatchesManifest",
    "RawSHA256",
    "AcceptanceDateEqualsDateFiled",
    "FiledAsOfDateEqualsDateFiled",
    "SecDocumentDateEqualsDateFiled",
    "SecDocumentDateAfterDateFiled",
    "AvailabilityLagCalendarDays",
    "DateFiledWeekFriday",
    "AvailabilityWeekFriday",
    "WeekAssignmentChanged",
    "AvailabilityAfterStudyEnd",
    "ParseStatus",
    "ParseMessages",
    "ParseNotes",
]


def first_group(pattern: re.Pattern[str], text: str) -> str:
    match = pattern.search(text)
    return match.group(1).strip() if match else ""


def yyyymmdd(value: str) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y%m%d").date()
    except ValueError:
        return None


def iso_date(value: date | None) -> str:
    return value.isoformat() if value else ""


def parse_iso_date(value: str) -> date | None:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def friday_of_week(value: date | None) -> date | None:
    if value is None:
        return None
    return value + timedelta(days=(4 - value.weekday()) % 7)


def bool_text(value: bool | None) -> str:
    if value is None:
        return ""
    return "True" if value else "False"


def file_accession(file_name: str) -> str:
    return Path(file_name).stem


def parse_wrapper(text: str) -> dict[str, str | bool]:
    acceptance_raw = first_group(ACCEPTANCE_RE, text)
    pds_match = PDS_TIMESTAMP_RE.search(text)
    pds_raw = "".join(pds_match.groups()) if pds_match else ""
    return {
        "acceptance_raw": acceptance_raw,
        "acceptance_date_raw": acceptance_raw[:8] if acceptance_raw else "",
        "filed_as_of_raw": first_group(DATE_FILED_RE, text),
        "sec_document_raw": first_group(SEC_DOCUMENT_RE, text),
        "sec_header_raw": first_group(SEC_HEADER_RE, text),
        "public_release_raw": first_group(PUBLIC_RELEASE_RE, text),
        "pds_timestamp_raw": pds_raw,
        "private_to_public": bool(PRIVATE_TO_PUBLIC_RE.search(text)),
        "accession": first_group(ACCESSION_RE, text),
        "submission_type": first_group(SUBMISSION_TYPE_RE, text),
        "public_reference_accession": first_group(
            PUBLIC_REFERENCE_RE, text
        ),
    }


def choose_availability(
    parsed: dict[str, str | bool],
) -> tuple[str, str, str, str]:
    """Return date, datetime, source, and time-status candidates.

    For private-to-public wrappers the private acceptance timestamp is not a
    public-availability timestamp.  Prefer an explicit public-release date,
    then a PDS dissemination timestamp, then the SEC archive-document date.
    """
    public_release = str(parsed["public_release_raw"])
    pds_timestamp = str(parsed["pds_timestamp_raw"])
    sec_document = str(parsed["sec_document_raw"])
    if public_release:
        return (
            public_release,
            "",
            "PUBLIC-REL-DATE",
            "date_only_no_public_time_in_archived_wrapper",
        )
    if pds_timestamp:
        return (
            pds_timestamp[:8],
            pds_timestamp,
            "PDS_TIMESTAMP",
            "exact_public_dissemination_timestamp_candidate",
        )
    if sec_document:
        return (
            sec_document,
            "",
            "SEC-DOCUMENT archive date",
            "date_only_no_public_time_in_archived_wrapper",
        )
    return "", "", "", "unavailable"


def audit_row(source: dict[str, str]) -> dict[str, str]:
    result = {field: "" for field in OUTPUT_FIELDS}
    for field in (
        "CIK",
        "CompanyName",
        "FormType",
        "DateFiled",
        "FileName",
        "URL",
        "LocalRawPath",
    ):
        result[field] = source.get(field, "")

    # The document's printed letter date is intentionally not inferred here.
    # Keeping the column separate prevents accidental substitution of either
    # DateFiled or the archive date for that distinct textual field.
    result["LetterDocumentDateStatus"] = "not_extracted_in_timing_audit"

    raw_path = Path(source.get("LocalRawPath", ""))
    if not raw_path.is_file():
        result["RawFileStatus"] = "missing"
        result["ParseStatus"] = "FAIL"
        result["ParseMessages"] = "local raw wrapper is missing"
        return result

    raw_bytes = raw_path.read_bytes()
    result["RawFileStatus"] = "present"
    result["RawByteLengthManifest"] = source.get("RawByteLength", "")
    result["RawByteLengthObserved"] = str(len(raw_bytes))
    result["RawByteLengthMatchesManifest"] = bool_text(
        source.get("RawByteLength", "") == str(len(raw_bytes))
    )
    result["RawSHA256"] = hashlib.sha256(raw_bytes).hexdigest()
    text = raw_bytes.decode("latin-1")
    parsed = parse_wrapper(text)

    acceptance = yyyymmdd(str(parsed["acceptance_date_raw"]))
    filed_as_of = yyyymmdd(str(parsed["filed_as_of_raw"]))
    sec_document = yyyymmdd(str(parsed["sec_document_raw"]))
    sec_header = yyyymmdd(str(parsed["sec_header_raw"]))
    public_release = yyyymmdd(str(parsed["public_release_raw"]))
    date_filed = parse_iso_date(source.get("DateFiled", ""))
    availability_raw, availability_dt, availability_source, time_status = (
        choose_availability(parsed)
    )
    availability = yyyymmdd(availability_raw)

    result.update(
        {
            "AcceptanceDateTimeRaw": str(parsed["acceptance_raw"]),
            "AcceptanceDate": iso_date(acceptance),
            "FiledAsOfDate": iso_date(filed_as_of),
            "SecDocumentDate": iso_date(sec_document),
            "SecHeaderDate": iso_date(sec_header),
            "PublicReleaseDateTag": iso_date(public_release),
            "PdsDisseminationTimestampRaw": str(
                parsed["pds_timestamp_raw"]
            ),
            "AvailabilityDateCandidate": iso_date(availability),
            "AvailabilityDateTimeCandidate": availability_dt,
            "AvailabilityCandidateSource": availability_source,
            "AvailabilityTimeStatus": time_status,
            "PrivateToPublicFlag": bool_text(
                bool(parsed["private_to_public"])
            ),
            "WrapperAccessionNumber": str(parsed["accession"]),
            "WrapperSubmissionType": str(parsed["submission_type"]),
            "PublicReferenceAccessionNumber": str(
                parsed["public_reference_accession"]
            ),
        }
    )

    result["SecHeaderDateEqualsSecDocumentDate"] = bool_text(
        sec_header == sec_document if sec_header and sec_document else None
    )
    if sec_header and sec_document:
        result["SecHeaderToDocumentLagCalendarDays"] = str(
            (sec_document - sec_header).days
        )

    expected_accession = file_accession(source.get("FileName", ""))
    accession_matches = bool(parsed["accession"]) and (
        str(parsed["accession"]) == expected_accession
    )
    result["AccessionMatchesFileName"] = bool_text(accession_matches)
    result["AcceptanceDateEqualsDateFiled"] = bool_text(
        acceptance == date_filed if acceptance and date_filed else None
    )
    result["FiledAsOfDateEqualsDateFiled"] = bool_text(
        filed_as_of == date_filed if filed_as_of and date_filed else None
    )
    result["SecDocumentDateEqualsDateFiled"] = bool_text(
        sec_document == date_filed if sec_document and date_filed else None
    )
    result["SecDocumentDateAfterDateFiled"] = bool_text(
        sec_document > date_filed if sec_document and date_filed else None
    )

    if availability and date_filed:
        result["AvailabilityLagCalendarDays"] = str(
            (availability - date_filed).days
        )
        filed_friday = friday_of_week(date_filed)
        availability_friday = friday_of_week(availability)
        result["DateFiledWeekFriday"] = iso_date(filed_friday)
        result["AvailabilityWeekFriday"] = iso_date(availability_friday)
        result["WeekAssignmentChanged"] = bool_text(
            filed_friday != availability_friday
        )
        result["AvailabilityAfterStudyEnd"] = bool_text(
            availability > STUDY_END
        )

    messages: list[str] = []
    notes: list[str] = []
    if date_filed is None:
        messages.append("invalid DateFiled")
    if acceptance is None:
        messages.append("missing/invalid ACCEPTANCE-DATETIME")
    if filed_as_of is None:
        messages.append("missing/invalid FILED AS OF DATE")
    if sec_document is None:
        messages.append("missing/invalid SEC-DOCUMENT date")
    if sec_header and sec_document and sec_header != sec_document:
        notes.append(
            "SEC-DOCUMENT and SEC-HEADER dates differ; "
            "SEC-DOCUMENT archive date retained as candidate"
        )
    if not parsed["private_to_public"]:
        messages.append("PRIVATE-TO-PUBLIC tag absent")
    if not accession_matches:
        messages.append("wrapper accession does not match FileName")
    if parsed["submission_type"] != source.get("FormType", ""):
        messages.append("wrapper submission type does not match manifest")
    if availability and date_filed and availability < date_filed:
        messages.append("availability candidate predates DateFiled")

    result["ParseMessages"] = "; ".join(messages)
    result["ParseNotes"] = "; ".join(notes)
    result["ParseStatus"] = "PASS" if not messages else "REVIEW"
    return result


def percentile_nearest(values: list[int], probability: float) -> str:
    if not values:
        return ""
    ordered = sorted(values)
    index = round((len(ordered) - 1) * probability)
    return str(ordered[index])


def summary_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    lags = [
        int(row["AvailabilityLagCalendarDays"])
        for row in rows
        if row["AvailabilityLagCalendarDays"]
    ]
    unique_keys = {
        (row["CIK"], row["DateFiled"], row["FileName"]) for row in rows
    }

    def count(field: str, value: str = "True") -> int:
        return sum(row[field] == value for row in rows)

    metrics = [
        ("manifest_rows", len(rows)),
        ("expected_manifest_rows", EXPECTED_FILINGS),
        ("unique_filing_keys", len(unique_keys)),
        ("duplicate_filing_keys", len(rows) - len(unique_keys)),
        ("raw_wrappers_present", count("RawFileStatus", "present")),
        (
            "raw_byte_lengths_match_manifest",
            count("RawByteLengthMatchesManifest"),
        ),
        ("parse_pass_rows", count("ParseStatus", "PASS")),
        ("parse_review_rows", count("ParseStatus", "REVIEW")),
        ("private_to_public_rows", count("PrivateToPublicFlag")),
        ("accession_matches", count("AccessionMatchesFileName")),
        (
            "acceptance_datetime_present",
            sum(bool(row["AcceptanceDateTimeRaw"]) for row in rows),
        ),
        (
            "acceptance_date_equals_DateFiled",
            count("AcceptanceDateEqualsDateFiled"),
        ),
        (
            "filed_as_of_equals_DateFiled",
            count("FiledAsOfDateEqualsDateFiled"),
        ),
        (
            "SEC_DOCUMENT_date_present",
            sum(bool(row["SecDocumentDate"]) for row in rows),
        ),
        (
            "SEC_DOCUMENT_date_equals_DateFiled",
            count("SecDocumentDateEqualsDateFiled"),
        ),
        (
            "SEC_DOCUMENT_date_after_DateFiled",
            count("SecDocumentDateAfterDateFiled"),
        ),
        (
            "SEC_HEADER_date_differs_from_SEC_DOCUMENT_date",
            sum(
                row["SecHeaderDateEqualsSecDocumentDate"] == "False"
                for row in rows
            ),
        ),
        (
            "availability_date_candidate_present",
            sum(bool(row["AvailabilityDateCandidate"]) for row in rows),
        ),
        (
            "exact_public_time_candidate_present",
            sum(bool(row["AvailabilityDateTimeCandidate"]) for row in rows),
        ),
        ("week_assignment_changed", count("WeekAssignmentChanged")),
        (
            "availability_after_study_end",
            count("AvailabilityAfterStudyEnd"),
        ),
        ("minimum_availability_lag_calendar_days", min(lags) if lags else ""),
        (
            "median_availability_lag_calendar_days",
            statistics.median(lags) if lags else "",
        ),
        ("p90_availability_lag_calendar_days", percentile_nearest(lags, 0.90)),
        ("maximum_availability_lag_calendar_days", max(lags) if lags else ""),
    ]
    return [{"Metric": key, "Value": str(value)} for key, value in metrics]


def by_year_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    years = sorted({row["DateFiled"][:4] for row in rows})
    for year in years:
        subset = [row for row in rows if row["DateFiled"].startswith(year)]
        lags = [
            int(row["AvailabilityLagCalendarDays"])
            for row in subset
            if row["AvailabilityLagCalendarDays"]
        ]
        result.append(
            {
                "DateFiledYear": year,
                "Rows": str(len(subset)),
                "PrivateToPublicRows": str(
                    sum(row["PrivateToPublicFlag"] == "True" for row in subset)
                ),
                "AcceptanceEqualsDateFiledRows": str(
                    sum(
                        row["AcceptanceDateEqualsDateFiled"] == "True"
                        for row in subset
                    )
                ),
                "AvailabilityEqualsDateFiledRows": str(
                    sum(
                        row["AvailabilityLagCalendarDays"] == "0"
                        for row in subset
                    )
                ),
                "AvailabilityAfterDateFiledRows": str(
                    sum(
                        row["AvailabilityLagCalendarDays"]
                        and int(row["AvailabilityLagCalendarDays"]) > 0
                        for row in subset
                    )
                ),
                "WeekAssignmentChangedRows": str(
                    sum(row["WeekAssignmentChanged"] == "True" for row in subset)
                ),
                "AvailabilityAfterStudyEndRows": str(
                    sum(
                        row["AvailabilityAfterStudyEnd"] == "True"
                        for row in subset
                    )
                ),
                "MinimumLagCalendarDays": str(min(lags)) if lags else "",
                "MedianLagCalendarDays": (
                    str(statistics.median(lags)) if lags else ""
                ),
                "P90LagCalendarDays": percentile_nearest(lags, 0.90),
                "MaximumLagCalendarDays": str(max(lags)) if lags else "",
            }
        )
    return result


def sample_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    selected: dict[tuple[str, str, str], dict[str, str]] = {}
    reasons: dict[tuple[str, str, str], set[str]] = {}
    years = sorted({row["DateFiled"][:4] for row in rows})
    for year in years:
        subset = [
            row
            for row in rows
            if row["DateFiled"].startswith(year)
            and row["AvailabilityLagCalendarDays"]
        ]
        if not subset:
            continue
        by_lag = sorted(
            subset,
            key=lambda row: (
                int(row["AvailabilityLagCalendarDays"]),
                row["DateFiled"],
                row["FileName"],
            ),
        )
        candidates = [
            (by_lag[0], "year_minimum_lag"),
            (by_lag[len(by_lag) // 2], "year_median_position_lag"),
            (by_lag[-1], "year_maximum_lag"),
        ]
        for row, reason in candidates:
            key = (row["CIK"], row["DateFiled"], row["FileName"])
            selected[key] = row
            reasons.setdefault(key, set()).add(reason)

    result = []
    for key in sorted(selected, key=lambda item: (item[1], item[2])):
        row = dict(selected[key])
        row["SampleReason"] = ";".join(sorted(reasons[key]))
        result.append(row)
    return result


def timing_exception_rows(
    rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    for source in rows:
        reasons: list[str] = []
        lag_text = source["AvailabilityLagCalendarDays"]
        lag = int(lag_text) if lag_text else None
        if source["SecHeaderDateEqualsSecDocumentDate"] == "False":
            reasons.append("SEC_HEADER_DATE_DIFFERS_FROM_SEC_DOCUMENT_DATE")
        if lag == 0:
            reasons.append("ZERO_DAY_PRIVATE_TO_PUBLIC_LAG")
        if lag is not None and lag > 365:
            reasons.append("PUBLIC_DATE_LAG_EXCEEDS_365_DAYS")
        if source["AvailabilityAfterStudyEnd"] == "True":
            reasons.append("PUBLIC_DATE_AFTER_STUDY_END")
        if reasons:
            row = dict(source)
            row["TimingExceptionReasons"] = ";".join(reasons)
            result.append(row)
    return result


def integrity_check_rows(
    manifest_rows: list[dict[str, str]],
    audited_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    with CANONICAL_CENSUS.open(encoding="utf-8-sig", newline="") as handle:
        census_rows = list(csv.DictReader(handle))
    with EXISTING_INTEGRITY_REPORT.open(
        encoding="utf-8-sig", newline=""
    ) as handle:
        existing_checks = list(csv.DictReader(handle))

    def key(row: dict[str, str]) -> tuple[str, str, str]:
        return row["CIK"], row["DateFiled"], row["FileName"]

    manifest_keys = {key(row) for row in manifest_rows}
    census_keys = {key(row) for row in census_rows}
    summary = {row["Metric"]: row["Value"] for row in summary_rows(audited_rows)}
    checks: list[dict[str, str]] = []

    def check(
        name: str,
        passed: bool,
        actual: object,
        expected: object,
        notes: str,
    ) -> None:
        checks.append(
            {
                "Check": name,
                "Status": "PASS" if passed else "FAIL",
                "Actual": str(actual),
                "Expected": str(expected),
                "Notes": notes,
            }
        )

    check(
        "Canonical census row count is preserved",
        len(census_rows) == EXPECTED_FILINGS,
        len(census_rows),
        EXPECTED_FILINGS,
        "Read-only reconciliation; the census file is not rewritten.",
    )
    check(
        "Timing manifest row count is preserved",
        len(manifest_rows) == EXPECTED_FILINGS,
        len(manifest_rows),
        EXPECTED_FILINGS,
        "The timing audit starts from the completed download manifest.",
    )
    check(
        "Timing sidecar has one row per manifest row",
        len(audited_rows) == len(manifest_rows),
        len(audited_rows),
        len(manifest_rows),
        "No census or manifest rows are added or removed.",
    )
    check(
        "Timing manifest filing keys equal canonical census filing keys",
        manifest_keys == census_keys,
        len(manifest_keys & census_keys),
        EXPECTED_FILINGS,
        "Key is CIK + DateFiled + FileName.",
    )
    check(
        "No duplicate timing filing keys",
        int(summary["duplicate_filing_keys"]) == 0,
        summary["duplicate_filing_keys"],
        0,
        "Timing extraction is one-to-one with the completed census.",
    )
    check(
        "All local raw wrappers are present",
        int(summary["raw_wrappers_present"]) == EXPECTED_FILINGS,
        summary["raw_wrappers_present"],
        EXPECTED_FILINGS,
        "Raw SEC wrappers remain read-only.",
    )
    check(
        "All raw byte lengths match the existing manifest",
        int(summary["raw_byte_lengths_match_manifest"]) == EXPECTED_FILINGS,
        summary["raw_byte_lengths_match_manifest"],
        EXPECTED_FILINGS,
        "Detects unexpected raw-file replacement or truncation.",
    )
    check(
        "All wrapper accession numbers match filing keys",
        int(summary["accession_matches"]) == EXPECTED_FILINGS,
        summary["accession_matches"],
        EXPECTED_FILINGS,
        "Protects against path or join misalignment.",
    )
    check(
        "All timing rows parsed without structural errors",
        int(summary["parse_review_rows"]) == 0,
        summary["parse_review_rows"],
        0,
        "Semantic timing exceptions are reported separately.",
    )
    existing_failures = sum(
        row.get("Status", "") != "PASS" for row in existing_checks
    )
    check(
        "Existing extended integrity audit remains all PASS",
        existing_failures == 0,
        existing_failures,
        0,
        "Existing output was read, not regenerated or overwritten.",
    )
    return checks


def write_csv(path: Path, rows: Iterable[dict[str, str]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    with args.manifest.open(encoding="utf-8-sig", newline="") as handle:
        source_rows = list(csv.DictReader(handle))
    audited = [audit_row(row) for row in source_rows]

    detail_path = (
        args.output_dir / "sec_information_timing_audit_2006_2025.csv"
    )
    summary_path = (
        args.output_dir / "sec_information_timing_summary_2006_2025.csv"
    )
    year_path = (
        args.output_dir / "sec_information_timing_by_year_2006_2025.csv"
    )
    sample_path = (
        args.output_dir
        / "sec_information_timing_stratified_sample_2006_2025.csv"
    )
    exception_path = (
        args.output_dir
        / "sec_information_timing_exceptions_2006_2025.csv"
    )
    integrity_path = (
        args.output_dir
        / "sec_information_timing_integrity_checks_2006_2025.csv"
    )
    write_csv(detail_path, audited, OUTPUT_FIELDS)
    summary = summary_rows(audited)
    write_csv(summary_path, summary, ["Metric", "Value"])
    yearly = by_year_rows(audited)
    write_csv(year_path, yearly, list(yearly[0]) if yearly else [])
    sample = sample_rows(audited)
    write_csv(
        sample_path,
        sample,
        OUTPUT_FIELDS + ["SampleReason"],
    )
    exceptions = timing_exception_rows(audited)
    write_csv(
        exception_path,
        exceptions,
        OUTPUT_FIELDS + ["TimingExceptionReasons"],
    )
    integrity = integrity_check_rows(source_rows, audited)
    write_csv(
        integrity_path,
        integrity,
        ["Check", "Status", "Actual", "Expected", "Notes"],
    )

    summary_map = {row["Metric"]: row["Value"] for row in summary}
    print(f"Audited {len(audited):,} manifest rows.")
    print(
        "Private-to-public wrappers: "
        f"{int(summary_map['private_to_public_rows']):,}."
    )
    print(
        "DateFiled equals acceptance date: "
        f"{int(summary_map['acceptance_date_equals_DateFiled']):,}."
    )
    print(
        "SEC-DOCUMENT date after DateFiled: "
        f"{int(summary_map['SEC_DOCUMENT_date_after_DateFiled']):,}."
    )
    print(
        "Weekly assignment changes under the availability-date candidate: "
        f"{int(summary_map['week_assignment_changed']):,}."
    )
    print(f"Detailed audit: {detail_path}")

    critical_ok = all(
        [
            len(audited) == EXPECTED_FILINGS,
            int(summary_map["duplicate_filing_keys"]) == 0,
            int(summary_map["raw_wrappers_present"]) == len(audited),
            int(summary_map["raw_byte_lengths_match_manifest"])
            == len(audited),
            int(summary_map["accession_matches"]) == len(audited),
            int(summary_map["availability_date_candidate_present"])
            == len(audited),
            all(row["Status"] == "PASS" for row in integrity),
        ]
    )
    return 0 if critical_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
