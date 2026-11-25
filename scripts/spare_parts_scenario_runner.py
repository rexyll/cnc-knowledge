#!/usr/bin/env python3
"""Validate generated CH17 scenario packages and replay synthetic expected event deltas offline.

This is a fixture-integrity and expectation-projection tool, not an ERP/WMS/QMS/CMMS
business-rule implementation. It never connects to external systems or posts transactions.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from datetime import datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts import spare_parts_fixture_loader as loader  # noqa: E402
from scripts import spare_parts_fixture_validator as validator  # noqa: E402

SCENARIO_RE = re.compile(r"^SPAT-\d{3}$")
PACKAGE_FILES = {
    "fixtures.csv", "objects.csv", "events.csv",
    "load-plan.json", "reset-plan.json", "scenario-manifest.json",
}
EVENT_BEHAVIOR = {
    "GOODS_RECEIPT_POSTED": "EXPECTED_BUCKET_DELTA",
    "DUPLICATE_MESSAGE_REPLAY": "IDEMPOTENCY_NO_OP",
    "QUALITY_RELEASE": "EXPECTED_BUCKET_DELTA",
    "QUALITY_HOLD": "EXPECTED_BUCKET_DELTA",
    "RESERVATION_CREATED": "EXPECTED_BUCKET_DELTA",
    "ALLOCATION_CREATED": "EXPECTED_BUCKET_DELTA",
    "RESERVATION_CANCELLED": "EXPECTED_BUCKET_DELTA",
    "PURCHASE_ORDER_CANCELLED": "NO_INVENTORY_EFFECT",
    "MATERIAL_ISSUED": "EXPECTED_BUCKET_DELTA",
    "PART_INSTALLED": "EXPECTED_BUCKET_DELTA",
    "UNUSED_PART_RETURNED": "EXPECTED_BUCKET_DELTA",
    "REMOVED_PART_RETURNED": "EXPECTED_BUCKET_DELTA",
    "REPAIRABLE_PART_RELEASED": "EXPECTED_BUCKET_DELTA",
    "SCRAP_POSTED": "EXPECTED_BUCKET_DELTA",
    "CYCLE_COUNT_VARIANCE_FOUND": "NO_INVENTORY_EFFECT",
    "PCN_RECEIVED": "NO_INVENTORY_EFFECT",
    "UNVERIFIED_EOL_CLAIM_RECEIVED": "NO_INVENTORY_EFFECT",
    "UNAUTHORIZED_STATUS_CHANGE_ATTEMPT": "NO_INVENTORY_EFFECT",
    "IMPORT_WITHOUT_SOR": "NO_INVENTORY_EFFECT",
    "SYNTHETIC_EXPORT_FILTER": "NO_INVENTORY_EFFECT",
    "LATE_REVERSAL_RECEIVED": "RECOVERY_NO_OP",
    "OUT_OF_ORDER_EVENT": "RECOVERY_NO_OP",
}


class ScenarioRunError(RuntimeError):
    """Raised when source data or a staged scenario package cannot be checked."""


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ScenarioRunError(f"{path}: cannot read valid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ScenarioRunError(f"{path}: JSON root must be an object")
    return value


def _read_csv(path: Path, expected_headers: list[str]) -> list[dict[str, str]]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames != expected_headers:
                raise ScenarioRunError(
                    f"{path}: header mismatch; expected {expected_headers!r}, got {reader.fieldnames!r}"
                )
            rows: list[dict[str, str]] = []
            for line_number, row in enumerate(reader, start=2):
                if None in row or any(value is None for value in row.values()):
                    raise ScenarioRunError(f"{path}: malformed row at line {line_number}")
                rows.append({key: value for key, value in row.items()})
            return rows
    except (OSError, UnicodeError, csv.Error) as exc:
        raise ScenarioRunError(f"{path}: cannot read CSV: {exc}") from exc


def _check(name: str, ok: bool, detail: str) -> dict[str, str]:
    return {"name": name, "status": "PASS" if ok else "FAIL", "detail": detail}


def validate_package(
    root: Path,
    package_root: Path,
    case_id: str,
    source_manifest: dict[str, str],
    source_fixtures: list[dict[str, str]],
    source_coverage: list[dict[str, str]],
) -> tuple[dict[str, Any], list[dict[str, str]], list[dict[str, str]]]:
    package = package_root / case_id
    if package.is_symlink() or not package.is_dir():
        raise ScenarioRunError(f"{case_id}: package directory is missing or is a symlink")
    entries = {item.name: item for item in package.iterdir()}
    if set(entries) != PACKAGE_FILES:
        missing = sorted(PACKAGE_FILES - set(entries))
        extra = sorted(set(entries) - PACKAGE_FILES)
        raise ScenarioRunError(f"{case_id}: package file set mismatch; missing={missing}, extra={extra}")
    for name, item in entries.items():
        if item.is_symlink() or not item.is_file():
            raise ScenarioRunError(f"{case_id}: package entry must be a regular file: {name}")

    # Rebuild the canonical package from source data and require exact byte equality.
    expected_files = loader.build_scenario_files(
        root, case_id, source_manifest, source_fixtures, source_coverage
    )
    for name, expected in expected_files.items():
        actual = (package / name).read_bytes()
        if actual != expected:
            raise ScenarioRunError(
                f"{case_id}: {name} differs from deterministic package reconstruction"
            )

    manifest = _read_json(package / "scenario-manifest.json")
    if manifest.get("test_case_id") != case_id:
        raise ScenarioRunError(f"{case_id}: scenario manifest case identity mismatch")
    if manifest.get("execution_scope") != "FILESYSTEM_STAGING_ONLY":
        raise ScenarioRunError(f"{case_id}: execution scope is not filesystem-only")
    if manifest.get("external_connections") is not False:
        raise ScenarioRunError(f"{case_id}: package does not explicitly disable external connections")
    if manifest.get("database_or_api_writes") is not False:
        raise ScenarioRunError(f"{case_id}: package does not explicitly disable database/API writes")
    if manifest.get("source_data_modified") is not False:
        raise ScenarioRunError(f"{case_id}: source modification flag must be false")

    fixture_rows = _read_csv(package / "fixtures.csv", validator.FIXTURE_HEADERS)
    object_rows = _read_csv(package / "objects.csv", validator.FIXTURE_HEADERS)
    event_rows = _read_csv(package / "events.csv", validator.FIXTURE_HEADERS)
    if not all(row.get("synthetic_only") == "TRUE" for row in fixture_rows):
        raise ScenarioRunError(f"{case_id}: package contains a record not marked synthetic_only=TRUE")
    if any(row.get("expected_state") != "EXPECTED_ONLY" for row in event_rows):
        raise ScenarioRunError(f"{case_id}: event is not marked EXPECTED_ONLY")

    fixture_ids = [row["fixture_id"] for row in fixture_rows]
    if len(fixture_ids) != len(set(fixture_ids)):
        raise ScenarioRunError(f"{case_id}: duplicate fixture IDs in package")
    object_ids = [row["fixture_id"] for row in object_rows]
    event_ids = [row["fixture_id"] for row in event_rows]
    if set(object_ids) & set(event_ids) or set(object_ids) | set(event_ids) != set(fixture_ids):
        raise ScenarioRunError(f"{case_id}: objects/events do not partition fixtures exactly")
    if any(row.get("fixture_type") == "BUSINESS_EVENT" for row in object_rows):
        raise ScenarioRunError(f"{case_id}: BUSINESS_EVENT found in objects.csv")
    if any(row.get("fixture_type") != "BUSINESS_EVENT" for row in event_rows):
        raise ScenarioRunError(f"{case_id}: non-event record found in events.csv")
    checks = [
        _check("package_files_match_canonical_rebuild", True, "all six package files exactly match deterministic source reconstruction"),
        _check("package_is_synthetic_and_offline", True, "all rows are synthetic and manifest disables external connections and writes"),
        _check("object_event_partition", True, f"{len(object_rows)} objects and {len(event_rows)} events partition {len(fixture_rows)} fixture rows"),
    ]
    return {"package_path": package.as_posix(), "manifest": manifest, "checks": checks}, fixture_rows, event_rows


def replay_expected_event_deltas(
    case_id: str,
    event_rows: list[dict[str, str]],
) -> dict[str, Any]:
    """Project fixture-declared expected deltas without calculating business inventory state."""
    event_by_id = {row["event_id"]: row for row in event_rows}
    if len(event_by_id) != len(event_rows):
        raise ScenarioRunError(f"{case_id}: event IDs are not unique")

    previous_ingestion: tuple[str, int, str] | None = None
    latest_business_time: dict[str, datetime] = {}
    group_bucket_deltas: dict[str, dict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
    trace: list[dict[str, Any]] = []
    duplicate_checks = 0
    reversal_checks = 0
    explicit_out_of_order = 0
    no_effect_events = 0

    for row in event_rows:
        event_id = row["event_id"]
        event_type = row["event_type"]
        behavior = EVENT_BEHAVIOR.get(event_type)
        if behavior is None:
            raise ScenarioRunError(f"{case_id}: no offline replay contract for event type {event_type}")
        try:
            delta = Decimal(row.get("expected_quantity_delta") or "0")
        except InvalidOperation as exc:
            raise ScenarioRunError(f"{case_id}: invalid quantity delta on {event_id}") from exc
        if not delta.is_finite():
            raise ScenarioRunError(f"{case_id}: non-finite quantity delta on {event_id}")
        bucket = row.get("expected_inventory_bucket", "")
        reset_group = row.get("reset_group", "")
        if not reset_group:
            raise ScenarioRunError(f"{case_id}: event {event_id} has no reset group")
        try:
            business_time = validator.parse_timestamp(row["business_event_time"])
            ingestion_time = validator.parse_timestamp(row["ingestion_time"])
            sequence = int(row["sequence_no"])
        except (ValueError, KeyError) as exc:
            raise ScenarioRunError(f"{case_id}: invalid time/sequence on event {event_id}: {exc}") from exc
        order_key = (ingestion_time.isoformat(), sequence, event_id)
        if previous_ingestion is not None and order_key < previous_ingestion:
            raise ScenarioRunError(f"{case_id}: events are not in ingestion/sequence order")
        previous_ingestion = order_key

        previous_business = latest_business_time.get(reset_group)
        is_out_of_order = previous_business is not None and business_time < previous_business
        if is_out_of_order and event_type != "OUT_OF_ORDER_EVENT":
            raise ScenarioRunError(
                f"{case_id}: unmarked business-time regression in reset group {reset_group} at {event_id}"
            )
        if event_type == "OUT_OF_ORDER_EVENT":
            if not is_out_of_order:
                raise ScenarioRunError(f"{case_id}: OUT_OF_ORDER_EVENT does not regress business time")
            explicit_out_of_order += 1
        if previous_business is None or business_time > previous_business:
            latest_business_time[reset_group] = business_time

        related = row.get("related_fixture_id", "")
        if behavior == "IDEMPOTENCY_NO_OP":
            original = event_by_id.get(related)
            if original is None:
                raise ScenarioRunError(f"{case_id}: duplicate replay {event_id} does not resolve original event {related}")
            if original["event_type"] != "GOODS_RECEIPT_POSTED" or delta != 0:
                raise ScenarioRunError(f"{case_id}: duplicate replay {event_id} must reference receipt and have zero delta")
            duplicate_checks += 1
        elif behavior == "RECOVERY_NO_OP":
            if event_type == "LATE_REVERSAL_RECEIVED":
                original = event_by_id.get(related)
                if original is None or original["event_type"] != "GOODS_RECEIPT_POSTED":
                    raise ScenarioRunError(f"{case_id}: late reversal {event_id} must retain its original receipt reference")
                if delta != 0:
                    raise ScenarioRunError(f"{case_id}: late reversal event must remain zero-delta in this projection")
                reversal_checks += 1
            else:
                if delta != 0:
                    raise ScenarioRunError(f"{case_id}: out-of-order marker must be zero-delta")
        elif behavior == "NO_INVENTORY_EFFECT":
            if delta != 0 or bucket:
                raise ScenarioRunError(f"{case_id}: non-inventory event {event_id} must have zero delta and no bucket")
            no_effect_events += 1
        elif behavior == "EXPECTED_BUCKET_DELTA":
            if delta != 0 and not bucket:
                raise ScenarioRunError(f"{case_id}: nonzero delta on {event_id} has no inventory bucket")
            if bucket:
                group_bucket_deltas[reset_group][bucket] += delta

        trace.append({
            "event_id": event_id,
            "event_type": event_type,
            "reset_group": reset_group,
            "business_event_time": row["business_event_time"],
            "ingestion_time": row["ingestion_time"],
            "sequence_no": sequence,
            "expected_inventory_bucket": bucket or None,
            "expected_quantity_delta": format(delta, "f"),
            "replay_behavior": behavior,
            "out_of_order_business_time": is_out_of_order,
            "source_state": row.get("expected_state"),
            "applied_to_real_inventory": False,
        })

    group_projection = []
    for group in sorted(group_bucket_deltas):
        group_projection.append({
            "reset_group": group,
            "bucket_deltas": [
                {"bucket": bucket, "expected_delta": format(delta, "f")}
                for bucket, delta in sorted(group_bucket_deltas[group].items())
            ],
        })

    return {
        "replay_mode": "EXPECTED_FIXTURE_DELTA_PROJECTION",
        "simulation_status": "PASS",
        "business_rule_assertions": "NOT_EVALUATED",
        "business_test_status": "NOT_RUN",
        "event_count": len(event_rows),
        "event_trace": trace,
        "bucket_deltas_by_reset_group": group_projection,
        "global_inventory_total": None,
        "groups_are_aggregated_together": False,
        "checks": [
            _check("event_type_replay_contract", True, f"{len(EVENT_BEHAVIOR)} known event types; all package events have an explicit offline behavior"),
            _check("ingestion_order_and_time_regression", True, f"events are in ingestion order; {explicit_out_of_order} explicit out-of-order marker(s)"),
            _check("idempotency_reference", True, f"{duplicate_checks} duplicate replay event(s) retain a source-event reference and zero expected delta"),
            _check("reversal_history_preserved", True, f"{reversal_checks} late reversal event(s) retain their original receipt reference and zero expected delta"),
            _check("non_inventory_events_do_not_change_buckets", True, f"{no_effect_events} non-inventory event(s) carry no bucket delta"),
            _check("reset_group_ledger_isolation", True, f"{len(group_projection)} independent reset-group projection(s); no cross-group/global inventory sum is produced"),
        ],
    }


def run_scenarios(root: Path, packages_dir: Path, requested_cases: list[str]) -> dict[str, Any]:
    root = root.resolve()
    if packages_dir.is_symlink():
        raise ScenarioRunError(f"scenario packages directory is a symlink: {packages_dir}")
    packages_dir = packages_dir.resolve()
    manifest, fixtures, coverage, _profiles = loader.load_and_check_inputs(root)
    known_cases = [row["test_case_id"] for row in coverage]
    cases = list(dict.fromkeys(requested_cases))
    if not cases:
        raise ScenarioRunError("select one or more scenario IDs")
    unknown = sorted(set(cases) - set(known_cases))
    if unknown:
        raise ScenarioRunError(f"unknown scenario IDs: {unknown}")
    fixture_by_case: dict[str, list[str]] = {}
    matrix_headers, matrix_rows = validator.load_csv(
        root / validator.TEST_MATRIX, None, []
    )
    matrix_by_case = {row["test_case_id"]: row for row in matrix_rows}
    coverage_by_case = {row["test_case_id"]: row for row in coverage}

    if not packages_dir.is_dir() or packages_dir.is_symlink():
        raise ScenarioRunError(f"scenario packages directory is missing or is a symlink: {packages_dir}")

    case_results: list[dict[str, Any]] = []
    for case_id in cases:
        try:
            package_result, _fixture_rows, event_rows = validate_package(
                root, packages_dir, case_id, manifest, fixtures, coverage
            )
            replay = replay_expected_event_deltas(case_id, event_rows)
            source_case = matrix_by_case[case_id]
            if source_case.get("execution_status") != "NOT_RUN":
                raise ScenarioRunError(f"{case_id}: source business test status must remain NOT_RUN")
            package_result["replay"] = replay
            package_result["simulation_status"] = "PASS"
            package_result["business_test_status"] = "NOT_RUN"
            package_result["business_rule_assertions"] = "NOT_EVALUATED"
            package_result["test_case"] = {
                "test_case_id": case_id,
                "title": source_case.get("title", ""),
                "test_level": source_case.get("test_level", ""),
                "pass_criteria_reference": source_case.get("pass_criteria", ""),
                "source_execution_status": source_case.get("execution_status"),
            }
            case_results.append(package_result)
        except (OSError, KeyError, ValueError, ScenarioRunError) as exc:
            case_results.append({
                "test_case_id": case_id,
                "simulation_status": "FAIL",
                "business_test_status": "NOT_RUN",
                "business_rule_assertions": "NOT_EVALUATED",
                "errors": [str(exc)],
            })

    passed = sum(item.get("simulation_status") == "PASS" for item in case_results)
    failed = len(case_results) - passed
    return {
        "report_schema_version": "1.0",
        "dataset": {
            "dataset_id": manifest["dataset_id"],
            "dataset_version": manifest["dataset_version"],
            "dataset_status": manifest["dataset_status"],
            "synthetic_only": manifest["synthetic_only"],
        },
        "execution_mode": "OFFLINE_SYNTHETIC_SIMULATION",
        "external_connections": False,
        "database_or_api_writes": False,
        "source_fixture_modified": False,
        "staged_case_count": len(cases),
        "simulated_case_count": passed,
        "failed_case_count": failed,
        "business_test_status": "NOT_RUN",
        "business_rule_assertions": "NOT_EVALUATED",
        "result": "PASS" if failed == 0 else "FAIL",
        "cases": case_results,
        "warnings": [
            "This report validates package integrity and projects fixture-declared expected event deltas only.",
            "No independent ERP/WMS/CMMS/EAM/QMS business rules are implemented or evaluated.",
            "Expected deltas are isolated by reset_group; no cross-group or global inventory balance is calculated.",
            "All source acceptance tests remain NOT_RUN; the dataset remains DRAFT and is not enterprise-approved.",
            "No database, API, queue, production system, CNC hardware or physical inventory was accessed or modified.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate staged CH17 packages and perform an offline synthetic expected-event projection."
    )
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="repository root")
    parser.add_argument("--packages-dir", type=Path, required=True, help="directory containing SPAT-xxx package folders")
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--test-case", help="run one staged scenario, e.g. SPAT-010")
    selection.add_argument("--all", action="store_true", help="run all 30 staged scenarios")
    parser.add_argument("--report-json", type=Path, help="write machine-readable report")
    args = parser.parse_args()
    root = args.root.resolve()
    packages_dir = args.packages_dir if args.packages_dir.is_absolute() else root / args.packages_dir
    cases = validator.EXPECTED_CASE_IDS if args.all else [args.test_case]
    try:
        report = run_scenarios(root, packages_dir, cases)
    except (OSError, ScenarioRunError, KeyError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    serialized = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.report_json:
        target = args.report_json if args.report_json.is_absolute() else root / args.report_json
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(serialized, encoding="utf-8")
    print(
        f"RESULT: {report['result']}; simulated={report['simulated_case_count']}; "
        f"failed={report['failed_case_count']}; business_test_status=NOT_RUN; "
        f"external_connections=NO; writes=NO"
    )
    for item in report["cases"]:
        if item["simulation_status"] == "PASS":
            replay = item["replay"]
            print(
                f"{item['test_case']['test_case_id']}: package=PASS; "
                f"events={replay['event_count']}; "
                f"reset_groups={len(replay['bucket_deltas_by_reset_group'])}; "
                "business_assertions=NOT_EVALUATED"
            )
        else:
            print(f"{item['test_case_id']}: FAIL: {'; '.join(item['errors'])}")
    if args.report_json:
        print(f"REPORT: {target}")
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
