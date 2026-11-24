from __future__ import annotations

import csv
import json
import math
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gantry_joint_drive_scurve_profile as scurve

CONFIG_PATH = Path(__file__).resolve().parent / "gantry-joint-drive-scurve-01-synthetic-config.json"


class TestSCurveProfile(unittest.TestCase):
    def test_scurve_reaches_target_and_respects_declared_limits(self) -> None:
        profile = scurve.plan_rest_to_rest(0.25, 0.20, 1.0, 10.0, 0.001)
        end = profile.evaluate(profile.total_time_s)
        self.assertAlmostEqual(end.position_m, 0.25, places=10)
        self.assertAlmostEqual(end.velocity_m_s, 0.0, places=12)
        self.assertAlmostEqual(end.acceleration_m_s2, 0.0, places=12)
        self.assertLessEqual(profile.peak_velocity_m_s, 0.20 + 1e-12)
        self.assertLessEqual(profile.peak_acceleration_m_s2, 1.0 + 1e-12)
        self.assertLessEqual(profile.peak_jerk_m_s3, 10.0 + 1e-12)
        samples = [profile.evaluate(t) for t in profile.sample_times()]
        self.assertTrue(all(math.isfinite(x.position_m) for x in samples))
        self.assertTrue(all(x.velocity_m_s >= -1e-10 for x in samples))
        self.assertTrue(all(samples[i].position_m <= samples[i + 1].position_m + 1e-12
                            for i in range(len(samples) - 1)))

    def test_triangular_acceleration_branch(self) -> None:
        profile = scurve.plan_rest_to_rest(0.002, 1.0, 1.0, 10.0, 0.0001)
        self.assertEqual(profile.boundaries[1].phase.duration_s, 0.0)
        self.assertEqual(profile.boundaries[5].phase.duration_s, 0.0)
        self.assertLess(profile.peak_acceleration_m_s2, 1.0)
        self.assertEqual(profile.boundaries[3].phase.duration_s, 0.0)

    def test_trapezoidal_acceleration_branch(self) -> None:
        profile = scurve.plan_rest_to_rest(0.25, 0.20, 1.0, 10.0, 0.001)
        self.assertAlmostEqual(profile.boundaries[1].phase.duration_s, 0.1, places=12)
        self.assertAlmostEqual(profile.peak_acceleration_m_s2, 1.0, places=12)

    def test_cruise_and_no_cruise_branches(self) -> None:
        long_move = scurve.plan_rest_to_rest(0.25, 0.20, 1.0, 10.0, 0.001)
        short_move = scurve.plan_rest_to_rest(0.04, 0.20, 1.0, 10.0, 0.001)
        self.assertGreater(long_move.boundaries[3].phase.duration_s, 0.0)
        self.assertEqual(short_move.boundaries[3].phase.duration_s, 0.0)
        self.assertLess(short_move.total_time_s, long_move.total_time_s)

    def test_position_velocity_and_acceleration_are_continuous_at_boundaries(self) -> None:
        profile = scurve.plan_rest_to_rest(0.25, 0.20, 1.0, 10.0, 0.001)
        for boundary in profile.boundaries[:-1]:
            if boundary.phase.duration_s <= 0.0 or boundary.end_time_s >= profile.total_time_s:
                continue
            epsilon = 1e-9
            before = profile.evaluate(boundary.end_time_s - epsilon)
            after = profile.evaluate(boundary.end_time_s + epsilon)
            self.assertAlmostEqual(before.position_m, after.position_m, delta=1e-7)
            self.assertAlmostEqual(before.velocity_m_s, after.velocity_m_s, delta=1e-7)
            self.assertAlmostEqual(before.acceleration_m_s2, after.acceleration_m_s2, delta=1e-7)

    def test_committed_fixture_and_archive_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output_dir = Path(temporary) / "scurve-output"
            manifest = scurve.run_config(CONFIG_PATH, output_dir)
            self.assertEqual(manifest["case_id"], "SCURVE-01")
            self.assertEqual(manifest["status"], "COMPLETED_REPORT_ONLY")
            self.assertEqual(manifest["acceptance_decision"], "DESCRIPTIVE_ONLY")
            with (output_dir / scurve.SUMMARY_NAME).open("r", encoding="utf-8", newline="") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["status"], "COMPLETED_REPORT_ONLY")
            self.assertAlmostEqual(float(rows[0]["end_position_m"]), 0.25, places=10)
            verified = scurve.verify_archive(output_dir)
            self.assertEqual(verified["status"], "VERIFIED")
            self.assertEqual(len(verified["artifacts"]), 3)

    def test_invalid_inputs_and_archive_tampering_are_rejected(self) -> None:
        for args in (
            (0.0, 0.2, 1.0, 10.0, 0.001),
            (0.2, -0.2, 1.0, 10.0, 0.001),
            (0.2, 0.2, 0.0, 10.0, 0.001),
            (0.2, 0.2, 1.0, float("nan"), 0.001),
        ):
            with self.assertRaises(scurve.SCurveError):
                scurve.plan_rest_to_rest(*args)
        with tempfile.TemporaryDirectory() as temporary:
            output_dir = Path(temporary) / "tampered-output"
            scurve.run_config(CONFIG_PATH, output_dir)
            csv_path = output_dir / scurve.TIMESERIES_NAME
            csv_path.write_text(csv_path.read_text(encoding="utf-8") + "tamper\n", encoding="utf-8")
            with self.assertRaisesRegex(scurve.SCurveError, "hash/size mismatch"):
                scurve.verify_archive(output_dir)


if __name__ == "__main__":
    unittest.main()
