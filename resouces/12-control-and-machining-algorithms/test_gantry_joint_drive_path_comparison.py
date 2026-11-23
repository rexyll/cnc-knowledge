"""Pure-function tests for the PATH-01 comparison runner.

These are resource tests and are not executed by the repository knowledge CI.
Run with:
python -m unittest discover -s resouces/12-control-and-machining-algorithms -p 'test_gantry_joint_drive_path_comparison.py' -v
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

import gantry_joint_drive_path_comparison as path_runner
from gantry_joint_drive_path_comparison import (
    _write_output_bundle,
    _acceptance_decision,
    _current_reference_was_limited,
    _energy_metrics,
    _saturation_stage_report,
    _source_document_ids,
    composite_simpson_13,
    normalized_state_error,
    quintic_rest_to_rest,
)


class TestPathComparisonRunnerHelpers(unittest.TestCase):
    def test_quintic_path_rest_to_rest_endpoint_conditions(self) -> None:
        start = quintic_rest_to_rest(0.0, 0.25, 0.85, 2.0)
        end = quintic_rest_to_rest(2.0, 0.25, 0.85, 2.0)
        self.assertEqual(start, (0.25, 0.0, 0.0))
        self.assertEqual(end, (0.85, 0.0, 0.0))

    def test_quintic_path_midpoint_is_half_travel(self) -> None:
        position, velocity, acceleration = quintic_rest_to_rest(1.0, 0.2, 0.8, 2.0)
        self.assertAlmostEqual(position, 0.5, places=14)
        self.assertAlmostEqual(velocity, 0.5625, places=14)
        self.assertAlmostEqual(acceleration, 0.0, places=14)

    def test_quintic_path_rejects_out_of_range_time(self) -> None:
        with self.assertRaisesRegex(ValueError, "out-of-range"):
            quintic_rest_to_rest(2.1, 0.0, 1.0, 2.0)

    def test_simpson_one_third_integrates_cubic_exactly(self) -> None:
        times = np.linspace(0.0, 1.0, 5)
        values = times**3
        self.assertAlmostEqual(composite_simpson_13(times, values), 0.25, places=14)

    def test_simpson_one_third_rejects_odd_interval_count(self) -> None:
        times = np.linspace(0.0, 1.0, 4)
        with self.assertRaisesRegex(ValueError, "even number of intervals"):
            composite_simpson_13(times, times**2)

    def test_normalized_state_error_uses_componentwise_units(self) -> None:
        left = np.array([[1.0, 0.1], [2.0, 0.2]])
        right = np.array([[0.9, 0.09], [2.1, 0.21]])
        normalized = normalized_state_error(
            left, right,
            absolute_tolerance=np.array([0.1, 0.01]),
            relative_tolerance=np.array([0.0, 0.0]),
        )
        self.assertTrue(np.allclose(normalized, [[1.0, 1.0], [-1.0, -1.0]]))

    def test_saturation_stage_report_identifies_smooth_unsaturated_stages(self) -> None:
        report = _saturation_stage_report(
            {
                "callback_evaluations": 8,
                "current_reference_saturated": 0,
                "voltage_saturated": 0,
                "any_limiter_active": 0,
                "last": None,
            },
            expected_stage_evaluations=8,
        )
        self.assertEqual(report["rk4_stage_evaluations"], 8)
        self.assertEqual(report["any_limiter_active_stages"], 0)
        self.assertEqual(report["limiter_active_stage_fraction"], 0.0)
        self.assertTrue(report["stage_count_matches_expected"])

    def test_saturation_stage_report_excludes_prescribed_terminal_probe(self) -> None:
        report = _saturation_stage_report(
            {
                "callback_evaluations": 9,
                "current_reference_saturated": 2,
                "voltage_saturated": 1,
                "any_limiter_active": 2,
                "last": {
                    "current_reference_saturated": True,
                    "voltage_saturated": False,
                    "any_limiter_active": True,
                },
            },
            expected_stage_evaluations=8,
            exclude_last_evaluation=True,
        )
        self.assertEqual(report["rk4_stage_evaluations"], 8)
        self.assertEqual(report["current_reference_saturated_stages"], 1)
        self.assertEqual(report["voltage_saturated_stages"], 1)
        self.assertEqual(report["any_limiter_active_stages"], 1)
        self.assertEqual(report["limiter_active_stage_fraction"], 0.125)
        self.assertTrue(report["stage_count_matches_expected"])

    def test_saturation_stage_report_detects_voltage_only_saturation(self) -> None:
        report = _saturation_stage_report(
            {
                "callback_evaluations": 4,
                "current_reference_saturated": 0,
                "voltage_saturated": 2,
                "any_limiter_active": 2,
                "last": None,
            },
            expected_stage_evaluations=4,
        )
        self.assertEqual(report["current_reference_saturated_stages"], 0)
        self.assertEqual(report["voltage_saturated_stages"], 2)
        self.assertEqual(report["any_limiter_active_stages"], 2)

    def test_source_document_ids_require_a_list(self) -> None:
        with self.assertRaisesRegex(ValueError, "must be a JSON string array"):
            _source_document_ids(None)

    def test_source_document_ids_reject_blank_or_non_string_entries(self) -> None:
        for invalid in (["SRC-1", "  "], ["SRC-1", 7]):
            with self.subTest(invalid=invalid):
                with self.assertRaisesRegex(ValueError, "must be a non-empty string"):
                    _source_document_ids(invalid)

    def test_source_document_ids_trim_and_reject_duplicates(self) -> None:
        self.assertEqual(_source_document_ids([" SRC-1 ", "SRC-2"]), ["SRC-1", "SRC-2"])
        with self.assertRaisesRegex(ValueError, "duplicate identifier"):
            _source_document_ids(["SRC-1", " SRC-1 "])

    def test_energy_metrics_report_trapezoid_residual(self) -> None:
        times = np.array([0.0, 1.0, 2.0])
        ledger = [
            {"stored": 0.0, "net": 0.0},
            {"stored": 2.0, "net": 1.0},
            {"stored": 4.0, "net": 4.0},
        ]
        metrics = _energy_metrics(times, ledger, energy_scale=1.0, energy_floor=1.0)
        self.assertAlmostEqual(metrics["residual"], 4.0 / 3.0, places=14)
        self.assertAlmostEqual(metrics["trapezoid_residual"], 1.0, places=14)
        self.assertNotAlmostEqual(metrics["residual"], metrics["trapezoid_residual"])

    def test_current_reference_limiter_detects_adjacent_float_clipping(self) -> None:
        requested = np.nextafter(1.0, np.inf)
        self.assertTrue(_current_reference_was_limited(requested, 1.0))
        self.assertFalse(_current_reference_was_limited(1.0, 1.0))

    def test_acceptance_requires_all_refinements_to_be_unsaturated(self) -> None:
        summary = {
            "free_convergence_screen": True,
            "prescribed_convergence_screen": True,
            "smooth_unsaturated_regime": True,
            "all_refinements_smooth_unsaturated_regime": False,
        }
        limits = {
            "application_path_error_limit_m": 0.0,
            "application_path_velocity_error_limit_m_s": 0.0,
            "payload_point_error_limit_m": 0.0,
            "application_force_limit_N": 0.0,
            "application_force_rms_limit_N": 0.0,
            "constraint_work_limit_J": 0.0,
            "normalized_energy_residual_limit": 0.0,
        }
        decision, status = _acceptance_decision(summary, limits)
        self.assertEqual(decision, "DESCRIPTIVE_ONLY")
        self.assertEqual(status, "COMPLETED_REPORT_ONLY")

    def test_acceptance_fails_when_convergence_screen_fails_even_if_limited(self) -> None:
        summary = {
            "free_convergence_screen": False,
            "prescribed_convergence_screen": True,
            "smooth_unsaturated_regime": False,
            "all_refinements_smooth_unsaturated_regime": False,
        }
        decision, status = _acceptance_decision(summary, {})
        self.assertEqual(decision, "FAIL")
        self.assertEqual(status, "FAIL")

    def test_output_bundle_manifest_binds_csv_hashes_and_dimensions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            timeseries = root / "timeseries.csv"
            summary = root / "summary.csv"
            manifest_path = root / "manifest.json"
            records = _write_output_bundle(
                timeseries, summary, manifest_path,
                timeseries_rows=[{}, {}], summary_rows=[{}],
                manifest={"schema_version": 2, "case_id": "PATH-01"},
            )
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["output_artifacts"], records)
            for key, path, row_count, column_count in (
                ("timeseries_csv", timeseries, 2, len(path_runner.TIMESERIES_FIELDS)),
                ("summary_csv", summary, 1, len(path_runner.SUMMARY_FIELDS)),
            ):
                artifact = records[key]
                self.assertEqual(artifact["sha256"], hashlib.sha256(path.read_bytes()).hexdigest())
                self.assertEqual(artifact["size_bytes"], path.stat().st_size)
                self.assertEqual(artifact["data_rows"], row_count)
                self.assertEqual(artifact["columns"], column_count)
                self.assertEqual(artifact["file"], path.name)

    def test_output_bundle_staging_failure_preserves_previous_archive(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            timeseries = root / "timeseries.csv"
            summary = root / "summary.csv"
            manifest_path = root / "manifest.json"
            previous = {
                timeseries: b"previous-timeseries",
                summary: b"previous-summary",
                manifest_path: b"previous-manifest",
            }
            for path, content in previous.items():
                path.write_bytes(content)

            with self.assertRaises(TypeError):
                _write_output_bundle(
                    timeseries, summary, manifest_path,
                    timeseries_rows=[{}], summary_rows=[{}],
                    manifest={"not_json_serializable": object()},
                )

            for path, content in previous.items():
                self.assertEqual(path.read_bytes(), content)
            self.assertEqual(sorted(path.name for path in root.iterdir()),
                             ["manifest.json", "summary.csv", "timeseries.csv"])

    def test_output_bundle_publish_failure_removes_completion_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            timeseries = root / "timeseries.csv"
            summary = root / "summary.csv"
            manifest_path = root / "manifest.json"
            timeseries.write_text("old-timeseries", encoding="utf-8")
            summary.write_text("old-summary", encoding="utf-8")
            manifest_path.write_text("old-manifest", encoding="utf-8")

            original_replace = os.replace
            replace_calls = 0

            def fail_second_replace(source: str, destination: str) -> None:
                nonlocal replace_calls
                replace_calls += 1
                if replace_calls == 2:
                    raise OSError("injected publication failure")
                original_replace(source, destination)

            with patch.object(path_runner.os, "replace", side_effect=fail_second_replace):
                with self.assertRaisesRegex(OSError, "injected publication failure"):
                    _write_output_bundle(
                        timeseries, summary, manifest_path,
                        timeseries_rows=[{}], summary_rows=[{}],
                        manifest={"schema_version": 2, "case_id": "PATH-01"},
                    )

            self.assertFalse(manifest_path.exists())
            # Recovery is explicit: rerun the whole bundle, not just the missing CSV.
            _write_output_bundle(
                timeseries, summary, manifest_path,
                timeseries_rows=[{}], summary_rows=[{}],
                manifest={"schema_version": 2, "case_id": "PATH-01"},
            )
            self.assertTrue(manifest_path.is_file())
            verified = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(
                verified["output_artifacts"]["timeseries_csv"]["sha256"],
                hashlib.sha256(timeseries.read_bytes()).hexdigest(),
            )

    def test_normalized_state_error_rejects_nonpositive_absolute_tolerance(self) -> None:
        values = np.zeros((2, 2))
        with self.assertRaisesRegex(ValueError, "absolute tolerances must be positive"):
            normalized_state_error(
                values, values, np.array([0.0, 1.0]), np.zeros(2)
            )


if __name__ == "__main__":
    unittest.main()
