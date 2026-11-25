#!/usr/bin/env python3
"""Validate the versioned synthetic spare-parts fixture baseline without external dependencies."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

DATA_DIR = Path("resouces/17-operation-maintenance-and-repair")
MANIFEST = DATA_DIR / "spare-parts-synthetic-fixture-baseline-v1-manifest.csv"
FIXTURES = DATA_DIR / "spare-parts-synthetic-fixture-baseline-v1.csv"
COVERAGE = DATA_DIR / "spare-parts-synthetic-fixture-test-case-coverage-v1.csv"
TEST_MATRIX = DATA_DIR / "spare-parts-end-to-end-acceptance-test-matrix.csv"

MANIFEST_HEADERS = [
    "dataset_id", "dataset_name", "dataset_version", "dataset_status", "synthetic_only",
    "source_data_policy", "fixture_schema_version", "generator_name", "generator_version",
    "seed_reference", "created_at", "owner_role", "approver_role", "approved_environment_ids",
    "approved_test_levels", "covered_test_case_ids", "object_domains", "object_types",
    "dependency_profile", "timezone_policy", "determinism_policy", "reset_strategy",
    "retention_policy", "data_classification", "sensitive_data_scan_status",
    "approval_reference", "checksum_algorithm", "checksum_value", "notes",
]
FIXTURE_HEADERS = [
    "dataset_id", "dataset_version", "fixture_id", "fixture_type", "source_domain",
    "source_system_alias", "synthetic_only", "logical_key_scope", "logical_key_value",
    "parent_fixture_id", "relationship_type", "related_fixture_id", "event_id", "event_type",
    "business_event_time", "ingestion_time", "sequence_no", "record_version", "valid_from",
    "valid_to", "test_case_ids", "expected_state", "expected_inventory_bucket",
    "expected_quantity_delta", "negative_case_flag", "reset_group", "notes",
]
COVERAGE_HEADERS = [
    "test_case_id", "category", "title", "fixture_profile_id", "positive_fixture_ids",
    "negative_fixture_ids", "event_ids", "source_preconditions", "expected_assertion",
    "execution_status", "fixture_boundary_notes",
]
EXPECTED_CASE_IDS = [f"SPAT-{number:03d}" for number in range(1, 31)]
ALLOWED_TEST_STATUSES = {"NOT_RUN", "IN_PROGRESS", "PASS", "FAIL", "BLOCKED", "NOT_APPLICABLE"}
ALLOWED_DATASET_STATUSES = {"DRAFT", "REVIEW", "APPROVED", "FROZEN", "RETIRED"}


def parse_timestamp(value: str) -> datetime:
    """Parse an ISO-8601 timestamp and require an explicit UTC offset."""
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must include an explicit UTC offset")
    return parsed


def split_ids(value: str) -> list[str]:
    return [item.strip() for item in (value or "").split(";") if item.strip()]


def load_csv(path: Path, expected_headers: list[str] | None, errors: list[str]) -> tuple[list[str], list[dict[str, str]]]:
    """Read a CSV with strict row-width and unique-header checks."""
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.reader(stream)
            headers = next(reader, None)
            if not headers:
                errors.append(f"{path}: CSV is empty or has no header")
                return [], []
            if len(headers) != len(set(headers)):
                errors.append(f"{path}: duplicate CSV column names")
            if expected_headers is not None and headers != expected_headers:
                errors.append(
                    f"{path}: header mismatch; expected {len(expected_headers)} columns "
                    f"with the defined order, got {len(headers)}"
                )
            rows: list[dict[str, str]] = []
            for line_number, values in enumerate(reader, start=2):
                if not values or all(value == "" for value in values):
                    continue
                if len(values) != len(headers):
                    errors.append(
                        f"{path}: row {line_number} has {len(values)} columns; expected {len(headers)}"
                    )
                    continue
                rows.append(dict(zip(headers, values)))
            return headers, rows
    except (OSError, UnicodeError, csv.Error) as exc:
        errors.append(f"{path}: cannot read CSV: {exc}")
        return [], []


def _add_check(checks: list[dict[str, str]], errors: list[str], name: str, ok: bool, detail: str) -> None:
    checks.append({"name": name, "status": "PASS" if ok else "FAIL", "detail": detail})
    if not ok:
        errors.append(f"{name}: {detail}")


def _file_info(root: Path, path: Path, rows: list[dict[str, str]], headers: list[str]) -> dict[str, Any]:
    try:
        raw = path.read_bytes()
        return {
            "path": path.relative_to(root).as_posix(),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "data_rows": len(rows),
            "columns": len(headers),
        }
    except OSError:
        return {"path": path.relative_to(root).as_posix(), "sha256": None, "data_rows": len(rows), "columns": len(headers)}


def validate_dataset(root: Path) -> dict[str, Any]:
    """Validate manifest, fixture objects/events, BOM windows and complete SPAT mapping."""
    root = root.resolve()
    errors: list[str] = []
    warnings: list[str] = []
    checks: list[dict[str, str]] = []

    manifest_path = root / MANIFEST
    fixture_path = root / FIXTURES
    coverage_path = root / COVERAGE
    matrix_path = root / TEST_MATRIX

    manifest_headers, manifest_rows = load_csv(manifest_path, MANIFEST_HEADERS, errors)
    fixture_headers, fixture_rows = load_csv(fixture_path, FIXTURE_HEADERS, errors)
    coverage_headers, coverage_rows = load_csv(coverage_path, COVERAGE_HEADERS, errors)
    matrix_headers, matrix_rows = load_csv(matrix_path, None, errors)

    required_matrix_headers = {
        "test_case_id", "category", "title", "preconditions", "execution_status"
    }
    matrix_header_ok = required_matrix_headers.issubset(set(matrix_headers))
    _add_check(
        checks, errors, "source_test_matrix_headers", matrix_header_ok,
        "source acceptance matrix contains required identifiers, scenario and state fields"
        if matrix_header_ok else f"missing {sorted(required_matrix_headers - set(matrix_headers))}",
    )

    manifest_ok = len(manifest_rows) == 1 and bool(manifest_headers)
    manifest = manifest_rows[0] if len(manifest_rows) == 1 else {}
    if manifest_ok:
        if not manifest.get("dataset_id") or not manifest.get("dataset_version"):
            manifest_ok = False
            errors.append("manifest: dataset_id and dataset_version must be non-empty")
        if manifest.get("dataset_status") not in ALLOWED_DATASET_STATUSES:
            manifest_ok = False
            errors.append(f"manifest: unsupported dataset_status {manifest.get('dataset_status')!r}")
        if manifest.get("synthetic_only", "").upper() != "TRUE":
            manifest_ok = False
            errors.append("manifest: synthetic_only must be TRUE")
        if manifest.get("source_data_policy") != "NO_SOURCE_DATA_USED_STATIC_SYNTHETIC_ONLY":
            manifest_ok = False
            errors.append("manifest: source_data_policy must explicitly declare no source data")
        if manifest.get("checksum_algorithm") != "SHA-256":
            manifest_ok = False
            errors.append("manifest: checksum_algorithm must be SHA-256")
    else:
        errors.append(f"manifest: expected exactly one data row, found {len(manifest_rows)}")
    _add_check(
        checks, errors, "manifest_identity_and_policy", manifest_ok,
        "one versioned dataset row declares pure synthetic data and a supported lifecycle status"
        if manifest_ok else "manifest structure, identity, status or synthetic-only declaration is invalid",
    )

    expected_cases = set(EXPECTED_CASE_IDS)
    matrix_by_id: dict[str, dict[str, str]] = {}
    matrix_ids = [row.get("test_case_id", "") for row in matrix_rows]
    matrix_unique = len(matrix_ids) == len(set(matrix_ids))
    matrix_complete = set(matrix_ids) == expected_cases and len(matrix_ids) == len(EXPECTED_CASE_IDS)
    matrix_status_ok = all(row.get("execution_status") in ALLOWED_TEST_STATUSES for row in matrix_rows)
    for row in matrix_rows:
        case_id = row.get("test_case_id", "")
        if case_id:
            matrix_by_id[case_id] = row
    _add_check(
        checks, errors, "source_test_matrix_coverage", matrix_unique and matrix_complete and matrix_status_ok,
        f"{len(matrix_rows)} source scenarios; expected exactly SPAT-001..SPAT-030"
        if matrix_unique and matrix_complete and matrix_status_ok
        else "source test matrix has duplicate/missing/extra case IDs or an unsupported execution status",
    )

    dataset_id = manifest.get("dataset_id", "")
    dataset_version = manifest.get("dataset_version", "")
    fixture_by_id: dict[str, dict[str, str]] = {}
    fixture_ids = [row.get("fixture_id", "") for row in fixture_rows]
    duplicate_ids = sorted({item for item in fixture_ids if fixture_ids.count(item) > 1})
    fixture_ok = bool(fixture_rows) and not duplicate_ids
    fixture_errors_before = len(errors)
    for row in fixture_rows:
        fixture_id = row.get("fixture_id", "")
        if not fixture_id:
            errors.append("fixtures: blank fixture_id")
            fixture_ok = False
            continue
        if fixture_id in fixture_by_id:
            fixture_ok = False
            continue
        fixture_by_id[fixture_id] = row
        if not (fixture_id.startswith("FX-") or fixture_id.startswith("EVT-")):
            errors.append(f"fixtures: {fixture_id} must use FX- or EVT- namespace")
            fixture_ok = False
        if row.get("dataset_id") != dataset_id or row.get("dataset_version") != dataset_version:
            errors.append(f"fixtures: {fixture_id} dataset ID/version differs from manifest")
            fixture_ok = False
        if row.get("synthetic_only", "").upper() != "TRUE":
            errors.append(f"fixtures: {fixture_id} is not marked synthetic_only=TRUE")
            fixture_ok = False
        if not row.get("logical_key_value"):
            errors.append(f"fixtures: {fixture_id} has no logical_key_value")
            fixture_ok = False
        if not row.get("reset_group"):
            errors.append(f"fixtures: {fixture_id} has no reset_group")
            fixture_ok = False
        if row.get("negative_case_flag", "").upper() not in {"TRUE", "FALSE"}:
            errors.append(f"fixtures: {fixture_id} has invalid negative_case_flag")
            fixture_ok = False
        for case_id in split_ids(row.get("test_case_ids", "")):
            if case_id not in expected_cases:
                errors.append(f"fixtures: {fixture_id} references unknown test case {case_id}")
                fixture_ok = False
    if duplicate_ids:
        errors.append(f"fixtures: duplicate fixture IDs {duplicate_ids}")
    _add_check(
        checks, errors, "fixture_identity_and_namespace", fixture_ok,
        f"{len(fixture_rows)} records; {len(set(fixture_ids))} unique IDs; all records are marked synthetic"
        if fixture_ok else "fixture IDs, dataset identity, namespaces or synthetic metadata are invalid",
    )

    references_ok = True
    for fixture_id, row in fixture_by_id.items():
        for field in ("parent_fixture_id", "related_fixture_id"):
            target = row.get(field, "")
            if target and target not in fixture_by_id:
                errors.append(f"fixtures: {fixture_id} {field} references missing {target}")
                references_ok = False
            if target == fixture_id:
                errors.append(f"fixtures: {fixture_id} {field} cannot reference itself")
                references_ok = False
    _add_check(
        checks, errors, "fixture_object_references", references_ok,
        "all parent_fixture_id and related_fixture_id values resolve to fixture IDs"
        if references_ok else "one or more parent/related fixture references are unresolved or self-referential",
    )

    event_rows = [row for row in fixture_rows if row.get("fixture_type") == "BUSINESS_EVENT"]
    object_rows = [row for row in fixture_rows if row.get("fixture_type") != "BUSINESS_EVENT"]
    event_ok = bool(event_rows)
    event_ids: set[str] = set()
    events_by_reset: dict[str, list[tuple[datetime, int, dict[str, str]]]] = defaultdict(list)
    for row in event_rows:
        event_id = row.get("fixture_id", "")
        if not event_id.startswith("EVT-") or row.get("event_id") != event_id:
            errors.append(f"events: {event_id} must use EVT- ID and event_id must equal fixture_id")
            event_ok = False
        if event_id in event_ids:
            errors.append(f"events: duplicate event_id {event_id}")
            event_ok = False
        event_ids.add(event_id)
        if not row.get("event_type"):
            errors.append(f"events: {event_id} has no event_type")
            event_ok = False
        try:
            business_time = parse_timestamp(row.get("business_event_time", ""))
            ingestion_time = parse_timestamp(row.get("ingestion_time", ""))
            if ingestion_time < business_time:
                raise ValueError("ingestion_time is earlier than business_event_time")
        except ValueError as exc:
            errors.append(f"events: {event_id} has invalid business/ingestion time: {exc}")
            event_ok = False
            continue
        try:
            sequence = int(row.get("sequence_no", ""))
            if sequence < 1:
                raise ValueError("sequence_no must be positive")
        except ValueError as exc:
            errors.append(f"events: {event_id} has invalid sequence_no: {exc}")
            event_ok = False
            continue
        events_by_reset[row.get("reset_group", "")].append((ingestion_time, sequence, row))
    duplicate_sequence_groups: list[str] = []
    out_of_order_count = 0
    delayed_count = 0
    for reset_group, events in events_by_reset.items():
        seen_sequences: set[int] = set()
        previous_sequence: int | None = None
        previous_business_time: datetime | None = None
        for ingestion_time, sequence, row in sorted(events, key=lambda item: (item[0], item[1])):
            event_id = row.get("event_id", "")
            if sequence in seen_sequences:
                duplicate_sequence_groups.append(reset_group)
                errors.append(f"events: duplicate sequence_no {sequence} in reset_group {reset_group}")
                event_ok = False
            seen_sequences.add(sequence)
            business_time = parse_timestamp(row["business_event_time"])
            if ingestion_time > business_time:
                delayed_count += 1
            if previous_sequence is not None and sequence < previous_sequence:
                if row.get("event_type") == "OUT_OF_ORDER_EVENT":
                    out_of_order_count += 1
                else:
                    errors.append(
                        f"events: sequence decreases in {reset_group} at {event_id} without OUT_OF_ORDER_EVENT marker"
                    )
                    event_ok = False
            if previous_business_time is not None and business_time < previous_business_time:
                if row.get("event_type") != "OUT_OF_ORDER_EVENT":
                    errors.append(
                        f"events: business time moves backward in {reset_group} at {event_id} without marker"
                    )
                    event_ok = False
            previous_sequence = sequence
            previous_business_time = business_time
    _add_check(
        checks, errors, "event_time_sequence_and_idempotency", event_ok,
        f"{len(event_rows)} events have unique IDs, offset-aware timestamps and positive sequences; "
        f"{delayed_count} delayed deliveries and {out_of_order_count} explicitly marked out-of-order event(s)"
        if event_ok else "event identity, timestamps, timezone, sequence or ordering markers are invalid",
    )

    case_tokens_ok = True
    for fixture_id, row in fixture_by_id.items():
        for case_id in split_ids(row.get("test_case_ids", "")):
            if case_id not in matrix_by_id:
                errors.append(f"fixtures: {fixture_id} references case absent from source matrix: {case_id}")
                case_tokens_ok = False
    _add_check(
        checks, errors, "fixture_case_references", case_tokens_ok,
        "fixture test_case_ids tokens resolve to the canonical SPAT test matrix"
        if case_tokens_ok else "fixture test_case_ids contain unknown or unavailable SPAT cases",
    )

    mapping_ids = [row.get("test_case_id", "") for row in coverage_rows]
    mapping_unique = len(mapping_ids) == len(set(mapping_ids))
    mapping_complete = set(mapping_ids) == expected_cases and len(mapping_ids) == len(EXPECTED_CASE_IDS)
    coverage_ok = mapping_unique and mapping_complete
    mapping_refs: dict[str, set[str]] = defaultdict(set)
    for mapping in coverage_rows:
        case_id = mapping.get("test_case_id", "")
        source_case = matrix_by_id.get(case_id)
        if source_case is None:
            errors.append(f"coverage: {case_id} is not present in source test matrix")
            coverage_ok = False
            continue
        for field in ("category", "title"):
            if mapping.get(field) != source_case.get(field):
                errors.append(f"coverage: {case_id} {field} differs from source test matrix")
                coverage_ok = False
        if mapping.get("source_preconditions") != source_case.get("preconditions"):
            errors.append(f"coverage: {case_id} source_preconditions differs from source matrix")
            coverage_ok = False
        if mapping.get("execution_status") != source_case.get("execution_status"):
            errors.append(f"coverage: {case_id} execution_status differs from source matrix")
            coverage_ok = False
        if mapping.get("fixture_profile_id") != f"PROFILE-{case_id}":
            errors.append(f"coverage: {case_id} fixture_profile_id must be PROFILE-{case_id}")
            coverage_ok = False
        positive = split_ids(mapping.get("positive_fixture_ids", ""))
        negative = split_ids(mapping.get("negative_fixture_ids", ""))
        mapped_events = split_ids(mapping.get("event_ids", ""))
        if not positive:
            errors.append(f"coverage: {case_id} needs at least one positive fixture")
            coverage_ok = False
        for field_name, refs, required_prefix in (
            ("positive_fixture_ids", positive, "FX-"),
            ("negative_fixture_ids", negative, "FX-"),
            ("event_ids", mapped_events, "EVT-"),
        ):
            for ref in refs:
                fixture = fixture_by_id.get(ref)
                if fixture is None:
                    errors.append(f"coverage: {case_id} {field_name} references missing {ref}")
                    coverage_ok = False
                    continue
                if not ref.startswith(required_prefix):
                    errors.append(f"coverage: {case_id} {field_name} reference {ref} must use {required_prefix}")
                    coverage_ok = False
                if required_prefix == "EVT-" and fixture.get("fixture_type") != "BUSINESS_EVENT":
                    errors.append(f"coverage: {case_id} event reference {ref} is not a BUSINESS_EVENT")
                    coverage_ok = False
                if case_id not in split_ids(fixture.get("test_case_ids", "")):
                    errors.append(f"coverage: {case_id} references {ref}, but fixture test_case_ids omits this case")
                    coverage_ok = False
                mapping_refs[case_id].add(ref)
    _add_check(
        checks, errors, "test_case_fixture_coverage", coverage_ok,
        f"{len(coverage_rows)} unique mapping rows cover exactly SPAT-001..SPAT-030; every referenced fixture/event exists"
        if coverage_ok else "coverage map has missing/duplicate cases; expected exactly SPAT-001..SPAT-030 with matching source fields and valid fixture/event references",
    )

    manifest_coverage = set(split_ids(manifest.get("covered_test_case_ids", "")))
    manifest_coverage_ok = manifest_coverage == expected_cases
    _add_check(
        checks, errors, "manifest_test_case_scope", manifest_coverage_ok,
        "manifest declares all 30 SPAT scenarios" if manifest_coverage_ok
        else "manifest covered_test_case_ids differs from SPAT-001..SPAT-030",
    )

    bom_revisions = [row for row in fixture_rows if row.get("fixture_type") == "BOM_REVISION"]
    bom_groups: dict[str, list[tuple[datetime, datetime | None, str]]] = defaultdict(list)
    bom_ok = len(bom_revisions) >= 2
    for row in bom_revisions:
        fixture_id = row.get("fixture_id", "")
        try:
            start = parse_timestamp(row.get("valid_from", ""))
            end = parse_timestamp(row["valid_to"]) if row.get("valid_to", "") else None
            if end is not None and end <= start:
                raise ValueError("valid_to must be later than valid_from")
            group = row.get("parent_fixture_id") or row.get("related_fixture_id")
            if not group:
                raise ValueError("BOM revision must reference its configuration scope")
            bom_groups[group].append((start, end, fixture_id))
        except ValueError as exc:
            errors.append(f"BOM: {fixture_id} has invalid validity interval: {exc}")
            bom_ok = False
    for scope, revisions in bom_groups.items():
        ordered = sorted(revisions, key=lambda item: item[0])
        for previous, current in zip(ordered, ordered[1:]):
            prev_end = previous[1]
            if prev_end is None or current[0] <= prev_end:
                errors.append(
                    f"BOM: overlapping validity windows in {scope}: {previous[2]} and {current[2]}"
                )
                bom_ok = False
    _add_check(
        checks, errors, "bom_revision_validity_windows", bom_ok,
        f"{len(bom_revisions)} BOM revisions have timezone-aware, non-overlapping validity windows"
        if bom_ok else "BOM revision windows are missing, invalid, or overlapping",
    )

    if manifest.get("dataset_status") == "DRAFT":
        warnings.append("dataset status is DRAFT; this validation does not approve or freeze it for an enterprise environment")
    if manifest.get("approved_environment_ids") in {"", "NONE_NOT_APPROVED"}:
        warnings.append("no enterprise test environment is approved in the dataset manifest")
    if manifest.get("approved_test_levels") in {"", "NONE_NOT_APPROVED"}:
        warnings.append("no enterprise test level is approved in the dataset manifest")
    not_run_count = sum(1 for row in matrix_rows if row.get("execution_status") == "NOT_RUN")
    if not_run_count:
        warnings.append(f"{not_run_count} source test cases remain NOT_RUN; fixture validation is not test execution")
    if manifest.get("checksum_value", "").startswith("PENDING"):
        warnings.append("manifest content checksum is pending; source-file SHA-256 values are included in this report")

    file_info = [
        _file_info(root, manifest_path, manifest_rows, manifest_headers),
        _file_info(root, fixture_path, fixture_rows, fixture_headers),
        _file_info(root, coverage_path, coverage_rows, coverage_headers),
        _file_info(root, matrix_path, matrix_rows, matrix_headers),
    ]
    object_count = sum(1 for row in fixture_rows if row.get("fixture_type") != "BUSINESS_EVENT")
    counts = {
        "fixture_records": len(fixture_rows),
        "object_records": object_count,
        "event_records": len(event_rows),
        "unique_fixture_ids": len(set(fixture_ids)),
        "mapped_test_cases": len(set(mapping_ids)),
        "source_test_cases": len(matrix_rows),
        "bom_revisions": len(bom_revisions),
        "reset_groups": len({row.get("reset_group", "") for row in fixture_rows}),
        "delayed_events": delayed_count,
        "explicit_out_of_order_events": out_of_order_count,
        "test_cases_not_run": not_run_count,
    }
    result = {
        "report_schema_version": "1.0",
        "dataset_id": dataset_id,
        "dataset_version": dataset_version,
        "dataset_status": manifest.get("dataset_status"),
        "result": "PASS" if not errors else "FAIL",
        "checks": checks,
        "counts": counts,
        "files": file_info,
        "warnings": warnings,
        "errors": errors,
        "scope_note": "Static synthetic-fixture validation only; does not execute SIT/UAT, approve data, connect enterprise systems, or validate machine hardware.",
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the CH17 synthetic spare-parts fixture baseline.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--json", action="store_true", help="print the full machine-readable report as JSON")
    parser.add_argument("--report-json", type=Path, help="also write the report JSON to this path")
    args = parser.parse_args()

    report = validate_dataset(args.root)
    serialized = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.report_json:
        output_path = args.report_json if args.report_json.is_absolute() else args.root / args.report_json
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(serialized, encoding="utf-8")
    if args.json:
        print(serialized, end="")
    else:
        print(f"Dataset: {report['dataset_id']} v{report['dataset_version']} [{report['dataset_status']}]")
        for name, value in sorted(report["counts"].items()):
            print(f"{name}: {value}")
        for check in report["checks"]:
            print(f"{check['status']}: {check['name']} — {check['detail']}")
        for warning in report["warnings"]:
            print(f"WARNING: {warning}")
        for error in report["errors"]:
            print(f"ERROR: {error}")
        print(f"RESULT: {report['result']} ({len(report['errors'])} errors, {len(report['warnings'])} warnings)")
        if args.report_json:
            print(f"REPORT_JSON: {output_path}")
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
