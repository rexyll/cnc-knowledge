from __future__ import annotations

import csv
import json
import shutil
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

from scripts import spare_parts_fixture_validator as validator


class SparePartsFixtureValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        for relative in (
            validator.MANIFEST,
            validator.FIXTURES,
            validator.COVERAGE,
            validator.TEST_MATRIX,
        ):
            source = REPO_ROOT / relative
            destination = self.root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _mutate_csv(self, relative: Path, callback) -> None:
        path = self.root / relative
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            headers = reader.fieldnames
            rows = list(reader)
        callback(rows)
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=headers, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)

    def test_repository_fixture_baseline_passes_static_validation(self) -> None:
        report = validator.validate_dataset(REPO_ROOT)
        self.assertEqual(report["result"], "PASS", "\n".join(report["errors"]))
        self.assertEqual(report["counts"]["fixture_records"], 89)
        self.assertEqual(report["counts"]["object_records"], 67)
        self.assertEqual(report["counts"]["event_records"], 22)
        self.assertEqual(report["counts"]["mapped_test_cases"], 30)
        self.assertEqual(report["counts"]["test_cases_not_run"], 30)
        self.assertEqual(report["dataset_status"], "DRAFT")
        self.assertTrue(any("does not approve" in item for item in report["warnings"]))

    def test_duplicate_fixture_id_fails(self) -> None:
        def mutate(rows):
            rows[1]["fixture_id"] = rows[0]["fixture_id"]
        self._mutate_csv(validator.FIXTURES, mutate)
        report = validator.validate_dataset(self.root)
        self.assertEqual(report["result"], "FAIL")
        self.assertTrue(any("duplicate fixture IDs" in error for error in report["errors"]))

    def test_dangling_parent_reference_fails(self) -> None:
        def mutate(rows):
            rows[0]["parent_fixture_id"] = "FX-MISSING-999"
        self._mutate_csv(validator.FIXTURES, mutate)
        report = validator.validate_dataset(self.root)
        self.assertEqual(report["result"], "FAIL")
        self.assertTrue(any("references missing FX-MISSING-999" in error for error in report["errors"]))

    def test_missing_test_case_mapping_fails(self) -> None:
        path = self.root / validator.COVERAGE
        with path.open("r", encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
            headers = list(rows[0])
        rows.pop()
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=headers, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        report = validator.validate_dataset(self.root)
        self.assertEqual(report["result"], "FAIL")
        self.assertTrue(any("exactly SPAT-001..SPAT-030" in check["detail"] for check in report["checks"] if check["name"] == "test_case_fixture_coverage"))

    def test_bom_revision_overlap_fails(self) -> None:
        def mutate(rows):
            for row in rows:
                if row["fixture_id"] == "FX-BOM-R1":
                    row["valid_to"] = "2026-07-01T00:00:00+08:00"
        self._mutate_csv(validator.FIXTURES, mutate)
        report = validator.validate_dataset(self.root)
        self.assertEqual(report["result"], "FAIL")
        self.assertTrue(any("overlapping validity windows" in error for error in report["errors"]))

    def test_missing_event_timestamp_fails(self) -> None:
        def mutate(rows):
            for row in rows:
                if row["fixture_id"] == "EVT-RECEIPT-PARTIAL-001":
                    row["business_event_time"] = ""
        self._mutate_csv(validator.FIXTURES, mutate)
        report = validator.validate_dataset(self.root)
        self.assertEqual(report["result"], "FAIL")
        self.assertTrue(any("invalid business/ingestion time" in error for error in report["errors"]))

    def test_report_json_is_reproducible_and_serializable(self) -> None:
        report = validator.validate_dataset(self.root)
        target = self.root / "validation-report.json"
        target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        loaded = json.loads(target.read_text(encoding="utf-8"))
        self.assertEqual(loaded["result"], "PASS")
        self.assertEqual(loaded["dataset_id"], "SPAREPARTS-SYN-BASE-001")
        self.assertEqual(len(loaded["files"]), 4)


if __name__ == "__main__":
    unittest.main()
