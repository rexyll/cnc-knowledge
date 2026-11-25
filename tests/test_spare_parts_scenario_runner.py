from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

from scripts import spare_parts_fixture_loader as loader
from scripts import spare_parts_scenario_runner as runner


class SparePartsScenarioRunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        for relative in (
            loader.validator.MANIFEST,
            loader.FIXTURES,
            loader.COVERAGE,
            loader.PROFILES,
            loader.TEST_MATRIX,
        ):
            source = REPO_ROOT / relative
            destination = self.root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
        self.packages = self.root / "packages"
        loader.stage_scenarios(self.root, loader.validator.EXPECTED_CASE_IDS, self.packages)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_single_idempotency_scenario_replays_duplicate_as_zero_delta(self) -> None:
        report = runner.run_scenarios(self.root, self.packages, ["SPAT-010"])
        self.assertEqual(report["result"], "PASS")
        case = report["cases"][0]
        self.assertEqual(case["simulation_status"], "PASS")
        self.assertEqual(case["business_test_status"], "NOT_RUN")
        self.assertEqual(case["business_rule_assertions"], "NOT_EVALUATED")
        trace = case["replay"]["event_trace"]
        duplicate = next(row for row in trace if row["event_type"] == "DUPLICATE_MESSAGE_REPLAY")
        self.assertEqual(duplicate["expected_quantity_delta"], "0")
        self.assertEqual(duplicate["replay_behavior"], "IDEMPOTENCY_NO_OP")
        self.assertEqual(duplicate["applied_to_real_inventory"], False)

    def test_all_30_packages_pass_offline_integrity_and_projection(self) -> None:
        report = runner.run_scenarios(
            self.root, self.packages, loader.validator.EXPECTED_CASE_IDS
        )
        self.assertEqual(report["result"], "PASS", json.dumps(report, ensure_ascii=False))
        self.assertEqual(report["simulated_case_count"], 30)
        self.assertEqual(report["failed_case_count"], 0)
        self.assertEqual(report["business_test_status"], "NOT_RUN")
        self.assertFalse(report["external_connections"])
        self.assertFalse(report["database_or_api_writes"])
        self.assertFalse(report["source_fixture_modified"])

    def test_multi_group_projection_never_emits_global_inventory_total(self) -> None:
        report = runner.run_scenarios(self.root, self.packages, ["SPAT-023"])
        replay = report["cases"][0]["replay"]
        groups = {row["reset_group"] for row in replay["bucket_deltas_by_reset_group"]}
        self.assertGreater(len(groups), 1)
        self.assertIsNone(replay["global_inventory_total"])
        self.assertFalse(replay["groups_are_aggregated_together"])

    def test_late_reversal_preserves_original_event_and_out_of_order_marker(self) -> None:
        report = runner.run_scenarios(self.root, self.packages, ["SPAT-030"])
        replay = report["cases"][0]["replay"]
        trace = replay["event_trace"]
        ids = {row["event_id"] for row in trace}
        reversal = next(row for row in trace if row["event_type"] == "LATE_REVERSAL_RECEIVED")
        out_of_order = next(row for row in trace if row["event_type"] == "OUT_OF_ORDER_EVENT")
        self.assertIn("EVT-RECEIPT-PARTIAL-001", ids)
        self.assertEqual(reversal["replay_behavior"], "RECOVERY_NO_OP")
        self.assertTrue(out_of_order["out_of_order_business_time"])
        self.assertEqual(out_of_order["expected_quantity_delta"], "0")

    def test_tampered_package_file_is_rejected(self) -> None:
        path = self.packages / "SPAT-001" / "fixtures.csv"
        path.write_bytes(path.read_bytes() + b"\n")
        report = runner.run_scenarios(self.root, self.packages, ["SPAT-001"])
        self.assertEqual(report["result"], "FAIL")
        self.assertIn("deterministic package reconstruction", report["cases"][0]["errors"][0])

    def test_missing_package_file_is_rejected(self) -> None:
        (self.packages / "SPAT-002" / "events.csv").unlink()
        report = runner.run_scenarios(self.root, self.packages, ["SPAT-002"])
        self.assertEqual(report["result"], "FAIL")
        self.assertTrue(report["cases"][0]["errors"])

    def test_unknown_event_type_is_rejected(self) -> None:
        # Modify the canonical source in the isolated test copy and rebuild that one package.
        import csv
        source = self.root / loader.FIXTURES
        with source.open("r", encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
            headers = list(rows[0])
        for row in rows:
            if row["fixture_id"] == "EVT-RECEIPT-PARTIAL-001":
                row["event_type"] = "UNREGISTERED_EVENT"
        with source.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=headers, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        # The changed source is not valid against the original hashes/mappings; the runner must fail closed.
        report = runner.run_scenarios(self.root, self.packages, ["SPAT-006"])
        self.assertEqual(report["result"], "FAIL")

    def test_source_test_status_and_fixture_files_remain_unchanged(self) -> None:
        source = self.root / loader.FIXTURES
        before = source.read_bytes()
        report = runner.run_scenarios(self.root, self.packages, ["SPAT-012"])
        self.assertEqual(report["cases"][0]["test_case"]["source_execution_status"], "NOT_RUN")
        self.assertEqual(source.read_bytes(), before)

    def test_cli_writes_json_report(self) -> None:
        import subprocess
        import sys
        from scripts import spare_parts_scenario_runner
        target = self.root / "report.json"
        result = subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "scripts" / "spare_parts_scenario_runner.py"),
                "--root", str(self.root),
                "--packages-dir", str(self.packages),
                "--all",
                "--report-json", str(target),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        data = json.loads(target.read_text(encoding="utf-8"))
        self.assertEqual(data["simulated_case_count"], 30)
        self.assertEqual(data["business_test_status"], "NOT_RUN")


if __name__ == "__main__":
    unittest.main()
