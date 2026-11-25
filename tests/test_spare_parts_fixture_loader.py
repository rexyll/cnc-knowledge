from __future__ import annotations

import csv
import json
import shutil
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

from scripts import spare_parts_fixture_loader as loader


class SparePartsFixtureLoaderTests(unittest.TestCase):
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

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_single_scenario_stages_only_local_files(self) -> None:
        output = self.root / "out"
        summary = loader.stage_scenarios(self.root, ["SPAT-001"], output)
        package = output / "SPAT-001"
        manifest = json.loads((package / "scenario-manifest.json").read_text(encoding="utf-8"))
        plan = json.loads((package / "load-plan.json").read_text(encoding="utf-8"))
        self.assertEqual(summary["staged_package_count"], 1)
        self.assertEqual(manifest["execution_scope"], "FILESYSTEM_STAGING_ONLY")
        self.assertFalse(manifest["external_connections"])
        self.assertFalse(manifest["database_or_api_writes"])
        self.assertFalse(plan["mutations_performed"])
        self.assertTrue((package / "fixtures.csv").is_file())
        self.assertTrue((package / "objects.csv").is_file())
        self.assertTrue((package / "events.csv").is_file())
        self.assertTrue((package / "reset-plan.json").is_file())

    def test_load_plan_places_parent_before_child(self) -> None:
        summary = loader.stage_scenarios(self.root, ["SPAT-001"], self.root / "order-out")
        plan = json.loads(
            (self.root / "order-out" / "SPAT-001" / "load-plan.json").read_text(encoding="utf-8")
        )
        order = plan["load_order"]
        fixtures = loader.read_dict_csv(self.root / loader.FIXTURES, loader.validator.FIXTURE_HEADERS)
        by_id = {row["fixture_id"]: row for row in fixtures}
        positions = {fixture_id: index for index, fixture_id in enumerate(order)}
        for fixture_id in order:
            parent = by_id[fixture_id].get("parent_fixture_id", "")
            if parent and parent in positions:
                self.assertLess(positions[parent], positions[fixture_id])

    def test_reset_plan_is_plan_only_and_cleanup_is_reverse_order(self) -> None:
        loader.stage_scenarios(self.root, ["SPAT-017"], self.root / "reset-out")
        package = self.root / "reset-out" / "SPAT-017"
        plan = json.loads((package / "reset-plan.json").read_text(encoding="utf-8"))
        self.assertEqual(plan["execution_mode"], "PLAN_ONLY")
        self.assertFalse(plan["mutations_performed"])
        self.assertFalse(plan["enterprise_reset_performed"])
        self.assertEqual(plan["cleanup_order"], list(reversed(plan["load_order"])))
        self.assertEqual(plan["scope"], "GENERATED_FILESYSTEM_PACKAGE_ONLY")

    def test_all_30_scenarios_stage(self) -> None:
        summary = loader.stage_scenarios(
            self.root, loader.validator.EXPECTED_CASE_IDS, self.root / "all-out"
        )
        self.assertEqual(summary["staged_package_count"], 30)
        self.assertEqual(
            {row["test_case_id"] for row in summary["packages"]},
            set(loader.validator.EXPECTED_CASE_IDS),
        )

    def test_unknown_scenario_is_rejected_without_package(self) -> None:
        with self.assertRaises(loader.ScenarioLoadError):
            loader.stage_scenarios(self.root, ["SPAT-999"], self.root / "bad-out")
        self.assertFalse((self.root / "bad-out" / "SPAT-999").exists())

    def test_existing_package_is_never_overwritten(self) -> None:
        output = self.root / "repeat-out"
        loader.stage_scenarios(self.root, ["SPAT-001"], output)
        target = output / "SPAT-001" / "scenario-manifest.json"
        before = target.read_bytes()
        with self.assertRaises(FileExistsError):
            loader.stage_scenarios(self.root, ["SPAT-001"], output)
        self.assertEqual(target.read_bytes(), before)

    def test_modified_reset_profile_is_rejected(self) -> None:
        profile_path = self.root / loader.PROFILES
        with profile_path.open("r", encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream)
            headers = reader.fieldnames
            rows = list(reader)
        rows[0]["reset_group_ids"] = "RESET-UNRELATED"
        with profile_path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=headers, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        with self.assertRaises(loader.ScenarioLoadError):
            loader.stage_scenarios(self.root, ["SPAT-001"], self.root / "profile-out")

    def test_staging_does_not_modify_source_fixture_hash(self) -> None:
        source = self.root / loader.FIXTURES
        before = source.read_bytes()
        loader.stage_scenarios(self.root, ["SPAT-029"], self.root / "readonly-out")
        self.assertEqual(source.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
