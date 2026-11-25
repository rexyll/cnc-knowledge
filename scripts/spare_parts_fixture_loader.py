#!/usr/bin/env python3
"""Stage isolated, deterministic scenario bundles from the synthetic spare-parts baseline.

This tool is filesystem-only. It does not connect to databases, APIs, queues, ERP/WMS,
CMMS/EAM/QMS systems, production services, or CNC hardware.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts import spare_parts_fixture_validator as validator  # noqa: E402

DATA_DIR = Path("resouces/17-operation-maintenance-and-repair")
FIXTURES = DATA_DIR / "spare-parts-synthetic-fixture-baseline-v1.csv"
COVERAGE = DATA_DIR / "spare-parts-synthetic-fixture-test-case-coverage-v1.csv"
PROFILES = DATA_DIR / "spare-parts-synthetic-fixture-reset-profiles-v1.csv"
TEST_MATRIX = DATA_DIR / "spare-parts-end-to-end-acceptance-test-matrix.csv"

PROFILE_HEADERS = [
    "profile_id", "test_case_id", "dataset_id", "dataset_version",
    "positive_fixture_ids", "negative_fixture_ids", "event_ids",
    "included_fixture_ids", "reset_group_ids", "load_order_strategy",
    "cleanup_order_strategy", "idempotency_key", "execution_status",
    "execution_scope", "notes",
]


class ScenarioLoadError(RuntimeError):
    """Raised when a scenario cannot be safely staged."""


def read_dict_csv(path: Path, expected_headers: list[str]) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != expected_headers:
            raise ScenarioLoadError(
                f"{path}: unexpected headers; expected {expected_headers!r}, got {reader.fieldnames!r}"
            )
        rows = list(reader)
        for line_number, row in enumerate(rows, start=2):
            if None in row:
                raise ScenarioLoadError(f"{path}: row {line_number} has more columns than the header")
        return rows


def split_ids(value: str) -> list[str]:
    return [part.strip() for part in (value or "").split(";") if part.strip()]


def csv_bytes(headers: list[str], rows: list[dict[str, str]]) -> bytes:
    from io import StringIO

    buffer = StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=headers, lineterminator="\n", extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({name: row.get(name, "") for name in headers})
    return buffer.getvalue().encode("utf-8")


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def dependency_closure(
    direct_ids: list[str],
    fixture_by_id: dict[str, dict[str, str]],
) -> set[str]:
    """Include direct scenario references and all recursively linked dependencies."""
    selected: set[str] = set()
    pending = list(direct_ids)
    while pending:
        fixture_id = pending.pop()
        if fixture_id in selected:
            continue
        row = fixture_by_id.get(fixture_id)
        if row is None:
            raise ScenarioLoadError(f"scenario references missing fixture {fixture_id}")
        selected.add(fixture_id)
        for field in ("parent_fixture_id", "related_fixture_id"):
            dependency = row.get(field, "")
            if dependency and dependency not in selected:
                pending.append(dependency)
    return selected


def build_parent_first_order(
    selected_ids: set[str],
    fixture_by_id: dict[str, dict[str, str]],
) -> list[str]:
    """Topologically sort object parents before children, then events by ingestion order."""
    object_ids = {
        item for item in selected_ids
        if fixture_by_id[item].get("fixture_type") != "BUSINESS_EVENT"
    }
    event_ids = selected_ids - object_ids
    indegree = {item: 0 for item in object_ids}
    children: dict[str, list[str]] = defaultdict(list)
    for item in object_ids:
        parent = fixture_by_id[item].get("parent_fixture_id", "")
        if parent in object_ids:
            indegree[item] += 1
            children[parent].append(item)
    ready = sorted(item for item, degree in indegree.items() if degree == 0)
    ordered_objects: list[str] = []
    while ready:
        current = ready.pop(0)
        ordered_objects.append(current)
        for child in sorted(children[current]):
            indegree[child] -= 1
            if indegree[child] == 0:
                ready.append(child)
                ready.sort()
    if len(ordered_objects) != len(object_ids):
        cyclic = sorted(item for item, degree in indegree.items() if degree > 0)
        raise ScenarioLoadError(f"parent dependency cycle detected: {cyclic}")

    def event_sort_key(item: str) -> tuple[str, int, str]:
        row = fixture_by_id[item]
        try:
            sequence = int(row.get("sequence_no", "0"))
        except ValueError:
            sequence = 0
        return (row.get("ingestion_time", ""), sequence, item)

    return ordered_objects + sorted(event_ids, key=event_sort_key)


def expected_profile_rows(
    manifest: dict[str, str],
    fixtures: list[dict[str, str]],
    coverage: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Derive reset profiles from the canonical coverage map and fixture dependencies."""
    fixture_by_id = {row["fixture_id"]: row for row in fixtures}
    expected: list[dict[str, str]] = []
    for mapping in coverage:
        direct = (
            split_ids(mapping.get("positive_fixture_ids", ""))
            + split_ids(mapping.get("negative_fixture_ids", ""))
            + split_ids(mapping.get("event_ids", ""))
        )
        included = dependency_closure(direct, fixture_by_id)
        ordered = build_parent_first_order(included, fixture_by_id)
        groups = sorted({fixture_by_id[item].get("reset_group", "") for item in included} - {""})
        case_id = mapping["test_case_id"]
        expected.append({
            "profile_id": f"PROFILE-{case_id}",
            "test_case_id": case_id,
            "dataset_id": manifest["dataset_id"],
            "dataset_version": manifest["dataset_version"],
            "positive_fixture_ids": mapping.get("positive_fixture_ids", ""),
            "negative_fixture_ids": mapping.get("negative_fixture_ids", ""),
            "event_ids": mapping.get("event_ids", ""),
            "included_fixture_ids": ";".join(sorted(included)),
            "reset_group_ids": ";".join(groups),
            "load_order_strategy": "PARENT_FIRST_OBJECTS_THEN_EVENTS_BY_INGESTION",
            "cleanup_order_strategy": "DISCARD_STAGING_PACKAGE_ONLY",
            "idempotency_key": f'{manifest["dataset_id"]}:{manifest["dataset_version"]}:{case_id}',
            "execution_status": mapping.get("execution_status", "NOT_RUN"),
            "execution_scope": "FILESYSTEM_STAGING_ONLY",
            "notes": "仅生成本地场景包和计划；不连接数据库、不执行事务、不重置企业系统",
        })
    return expected


def load_and_check_inputs(root: Path) -> tuple[dict[str, str], list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    validation = validator.validate_dataset(root)
    if validation["result"] != "PASS":
        raise ScenarioLoadError(
            "source fixture validation failed: " + "; ".join(validation["errors"][:10])
        )
    manifest_path = root / validator.MANIFEST
    fixtures_path = root / FIXTURES
    coverage_path = root / COVERAGE
    profiles_path = root / PROFILES
    manifest_rows = read_dict_csv(manifest_path, validator.MANIFEST_HEADERS)
    if len(manifest_rows) != 1:
        raise ScenarioLoadError(f"manifest must contain exactly one row, found {len(manifest_rows)}")
    manifest = manifest_rows[0]
    fixtures = read_dict_csv(fixtures_path, validator.FIXTURE_HEADERS)
    coverage = read_dict_csv(coverage_path, validator.COVERAGE_HEADERS)
    profiles = read_dict_csv(profiles_path, PROFILE_HEADERS)
    expected_profiles = expected_profile_rows(manifest, fixtures, coverage)
    actual_by_case = {row.get("test_case_id", ""): row for row in profiles}
    expected_by_case = {row["test_case_id"]: row for row in expected_profiles}
    if len(actual_by_case) != len(profiles) or set(actual_by_case) != set(expected_by_case):
        raise ScenarioLoadError("reset profile IDs must be unique and cover exactly the canonical SPAT cases")
    for case_id, expected in expected_by_case.items():
        actual = actual_by_case[case_id]
        differences = [field for field in PROFILE_HEADERS if actual.get(field, "") != expected.get(field, "")]
        if differences:
            raise ScenarioLoadError(
                f"reset profile {case_id} differs from derived dependencies in: {', '.join(differences)}"
            )
    return manifest, fixtures, coverage, profiles


def build_scenario_files(
    root: Path,
    test_case_id: str,
    manifest: dict[str, str],
    fixtures: list[dict[str, str]],
    coverage: list[dict[str, str]],
) -> dict[str, bytes]:
    mapping_by_case = {row["test_case_id"]: row for row in coverage}
    mapping = mapping_by_case.get(test_case_id)
    if mapping is None:
        raise ScenarioLoadError(f"unknown test case {test_case_id}; expected SPAT-001..SPAT-030")
    fixture_by_id = {row["fixture_id"]: row for row in fixtures}
    direct_ids = (
        split_ids(mapping.get("positive_fixture_ids", ""))
        + split_ids(mapping.get("negative_fixture_ids", ""))
        + split_ids(mapping.get("event_ids", ""))
    )
    included_ids = dependency_closure(direct_ids, fixture_by_id)
    load_order = build_parent_first_order(included_ids, fixture_by_id)
    ordered_rows = [fixture_by_id[item] for item in load_order]
    selected_events = [
        row for row in ordered_rows if row.get("fixture_type") == "BUSINESS_EVENT"
    ]
    selected_objects = [
        row for row in ordered_rows if row.get("fixture_type") != "BUSINESS_EVENT"
    ]
    profile = expected_profile_rows(manifest, fixtures, [mapping])[0]
    # Keep only the immutable columns defined by the source fixture CSV.
    fixture_csv = csv_bytes(validator.FIXTURE_HEADERS, ordered_rows)
    event_csv = csv_bytes(validator.FIXTURE_HEADERS, selected_events)
    object_csv = csv_bytes(validator.FIXTURE_HEADERS, selected_objects)
    load_plan = {
        "plan_schema_version": "1.0",
        "dataset_id": manifest["dataset_id"],
        "dataset_version": manifest["dataset_version"],
        "test_case_id": test_case_id,
        "profile_id": profile["profile_id"],
        "execution_mode": "FILESYSTEM_STAGING_ONLY",
        "execution_status": mapping.get("execution_status", "NOT_RUN"),
        "database_or_api_connections": False,
        "mutations_performed": False,
        "source_data_modified": False,
        "fixture_count": len(ordered_rows),
        "object_count": len(selected_objects),
        "event_count": len(selected_events),
        "load_order": load_order,
        "steps": [
            "Verify dataset and source file hashes in scenario-manifest.json",
            "Create or select an isolated non-production test namespace only after enterprise approval",
            "Load parent objects before dependent objects using the approved target-system adapter (not included here)",
            "Load event fixtures in ingestion_time/sequence order using an approved test event interface (not included here)",
            "Verify resulting state against the source acceptance criteria and retain evidence",
        ],
        "adapter_status": "NOT_IMPLEMENTED",
        "execution_note": "This is a plan only. The tool only stages local files and never executes these steps.",
    }
    reset_plan = {
        "reset_plan_schema_version": "1.0",
        "dataset_id": manifest["dataset_id"],
        "dataset_version": manifest["dataset_version"],
        "test_case_id": test_case_id,
        "profile_id": profile["profile_id"],
        "execution_mode": "PLAN_ONLY",
        "scope": "GENERATED_FILESYSTEM_PACKAGE_ONLY",
        "mutations_performed": False,
        "enterprise_reset_performed": False,
        "reset_group_ids": split_ids(profile["reset_group_ids"]),
        "idempotency_key": profile["idempotency_key"],
        "reset_before_load": [
            "Confirm the target output directory is empty and dedicated to this scenario",
            "Confirm the dataset version and generated package SHA-256 values",
            "Do not connect or issue reset/delete calls to any external system",
        ],
        "load_order": load_order,
        "cleanup_order": list(reversed(load_order)),
        "cleanup_policy": "Archive required evidence, then discard only this generated local scenario package when no longer needed",
        "cleanup_execution": "NOT_EXECUTED",
    }
    source_hashes = {
        "manifest_sha256": hashlib.sha256((root / validator.MANIFEST).read_bytes()).hexdigest(),
        "fixtures_sha256": hashlib.sha256((root / FIXTURES).read_bytes()).hexdigest(),
        "coverage_sha256": hashlib.sha256((root / COVERAGE).read_bytes()).hexdigest(),
        "reset_profiles_sha256": hashlib.sha256((root / PROFILES).read_bytes()).hexdigest(),
    }
    files: dict[str, bytes] = {
        "fixtures.csv": fixture_csv,
        "objects.csv": object_csv,
        "events.csv": event_csv,
        "load-plan.json": (json.dumps(load_plan, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
        "reset-plan.json": (json.dumps(reset_plan, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
    }
    package_manifest = {
        "package_schema_version": "1.0",
        "dataset_id": manifest["dataset_id"],
        "dataset_version": manifest["dataset_version"],
        "dataset_status": manifest["dataset_status"],
        "test_case_id": test_case_id,
        "profile_id": profile["profile_id"],
        "execution_status": mapping.get("execution_status", "NOT_RUN"),
        "synthetic_only": manifest.get("synthetic_only"),
        "execution_scope": "FILESYSTEM_STAGING_ONLY",
        "external_connections": False,
        "database_or_api_writes": False,
        "source_data_modified": False,
        "direct_fixture_ids": sorted(set(direct_ids)),
        "included_fixture_ids": load_order,
        "reset_group_ids": split_ids(profile["reset_group_ids"]),
        "source_file_sha256": source_hashes,
        "generated_files_sha256": {name: sha256_bytes(content) for name, content in sorted(files.items())},
        "notes": "Scenario package only. DRAFT data is not enterprise-approved. No SIT/UAT test has been executed.",
    }
    files["scenario-manifest.json"] = (
        json.dumps(package_manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    return files


def write_package(output_root: Path, test_case_id: str, files: dict[str, bytes]) -> Path:
    output_root.mkdir(parents=True, exist_ok=True)
    target = output_root / test_case_id
    if target.exists():
        raise FileExistsError(f"scenario package already exists; refusing to overwrite: {target}")
    with tempfile.TemporaryDirectory(prefix=f".{test_case_id}-", dir=output_root) as temporary:
        staging = Path(temporary)
        for filename, content in files.items():
            (staging / filename).write_bytes(content)
        # Atomic directory rename; never replaces an existing package.
        staging.rename(target)
    return target


def stage_scenarios(root: Path, test_case_ids: list[str], output_root: Path) -> dict[str, Any]:
    manifest, fixtures, coverage, _profiles = load_and_check_inputs(root.resolve())
    known_cases = {row["test_case_id"] for row in coverage}
    requested = list(dict.fromkeys(test_case_ids))
    if not requested:
        raise ScenarioLoadError("select one or more test cases")
    unknown = sorted(set(requested) - known_cases)
    if unknown:
        raise ScenarioLoadError(f"unknown test cases: {unknown}")
    prepared = {
        case_id: build_scenario_files(root.resolve(), case_id, manifest, fixtures, coverage)
        for case_id in requested
    }
    # Refuse the whole selection before writing if any target already exists.
    output_root.mkdir(parents=True, exist_ok=True)
    existing = [case_id for case_id in requested if (output_root / case_id).exists()]
    if existing:
        raise FileExistsError(f"refusing to overwrite existing scenario packages: {existing}")
    packages = []
    for case_id in requested:
        location = write_package(output_root, case_id, prepared[case_id])
        packages.append({
            "test_case_id": case_id,
            "path": location.as_posix(),
            "files": sorted(prepared[case_id]),
            "fixture_count": json.loads(prepared[case_id]["scenario-manifest.json"])["included_fixture_ids"].__len__(),
            "package_sha256": sha256_bytes(prepared[case_id]["scenario-manifest.json"]),
        })
    summary = {
        "summary_schema_version": "1.0",
        "dataset_id": manifest["dataset_id"],
        "dataset_version": manifest["dataset_version"],
        "dataset_status": manifest["dataset_status"],
        "execution_mode": "FILESYSTEM_STAGING_ONLY",
        "database_or_api_connections": False,
        "mutations_performed": False,
        "staged_package_count": len(packages),
        "packages": packages,
        "warnings": [
            "Dataset is DRAFT and is not approved/frozen for an enterprise environment.",
            "Scenario packages are not test execution; all source cases remain NOT_RUN unless separately updated with evidence.",
            "This tool does not provide any database, API, queue, WMS, ERP, CMMS, EAM or QMS adapter.",
        ],
    }
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "staging-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Stage local scenario packages from the CH17 synthetic spare-parts fixture dataset."
    )
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="repository root")
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--test-case", help="one scenario, e.g. SPAT-001")
    selection.add_argument("--all", action="store_true", help="stage all 30 SPAT scenarios")
    parser.add_argument("--output-dir", type=Path, required=True, help="new local staging directory")
    args = parser.parse_args()
    root = args.root.resolve()
    output = args.output_dir if args.output_dir.is_absolute() else root / args.output_dir
    selected = validator.EXPECTED_CASE_IDS if args.all else [args.test_case]
    try:
        summary = stage_scenarios(root, selected, output)
    except (OSError, ScenarioLoadError, ValueError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(
        f"STAGED: {summary['staged_package_count']} local package(s); "
        f"mode={summary['execution_mode']}; external connections=NO; mutations=NO"
    )
    for item in summary["packages"]:
        print(
            f"{item['test_case_id']}: {item['fixture_count']} fixture(s); "
            f"{item['path']}; manifest_sha256={item['package_sha256']}"
        )
    print("NOTE: staging is not SIT/UAT execution; source test status is unchanged.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
