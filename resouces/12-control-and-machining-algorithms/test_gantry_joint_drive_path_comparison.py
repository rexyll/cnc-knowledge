"""Pure-function tests for the PATH-01 comparison runner.

These are resource tests and are not executed by the repository knowledge CI.
Run with:
python -m unittest discover -s resouces/12-control-and-machining-algorithms -p 'test_gantry_joint_drive_path_comparison.py' -v
"""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

import gantry_joint_drive_path_comparison as path_runner
from gantry_joint_drive_solver import (
    ActuatorKinematics,
    CurrentLoopParameters,
    GantryJointDriveModel,
    JointState,
    MechanicalParameters,
    SinusoidalBeamGeometry,
)
from gantry_joint_drive_path_comparison import (
    _interval_count,
    _number,
    _write_output_bundle,
    verify_output_bundle,
    _acceptance_decision,
    _current_reference_was_limited,
    _energy_metrics,
    _energy_ledger,
    _saturation_stage_report,
    _source_document_ids,
    composite_simpson_13,
    trapezoid_integral,
    normalized_state_error,
    quintic_rest_to_rest,
)


def make_energy_ledger_model(
    force_constant_N_per_A: float = 4.2,
    back_emf_V_per_m_s: float = 3.7,
    structural_damping: np.ndarray | None = None,
    axis_viscous_Ns_m: float = 0.0,
    axis_coulomb_N: float = 0.0,
) -> GantryJointDriveModel:
    """Build a configurable model for exact energy-ledger sign checks."""
    mechanics = MechanicalParameters(
        M0=np.diag([75.0, 12.0, 9.0, 2.0]),
        D0=(np.zeros((4, 4)) if structural_damping is None
            else np.asarray(structural_damping, dtype=float)),
        K0=np.zeros((4, 4)),
        payload_mass_kg=0.0,
        axis_equivalent_mass_kg=8.0,
        gravity_acceleration_m_s2=np.zeros(3),
        axis_viscous_Ns_m=axis_viscous_Ns_m,
        axis_coulomb_N=axis_coulomb_N,
        friction_smoothing_speed_m_s=0.1,
    )
    electrical = CurrentLoopParameters(
        resistance_ohm=1.5,
        inductance_h=0.02,
        back_emf_V_per_m_s=back_emf_V_per_m_s,
        force_constant_N_per_A=force_constant_N_per_A,
        current_limit_A=8.0,
        voltage_min_V=-48.0,
        voltage_max_V=48.0,
        kp_V_per_A=1.0,
        ki_V_per_A_s=0.0,
        antiwindup_gain_per_s=0.0,
    )
    actuator = ActuatorKinematics(
        q_coefficients=np.array([1.0, 0.0, 0.0, 0.0]),
        s_coefficient=1.0,
    )
    return GantryJointDriveModel(
        SinusoidalBeamGeometry(span_m=1.6),
        mechanics,
        electrical,
        actuator,
    )


def make_energy_ledger_state(path_velocity_m_s: float = 0.2) -> JointState:
    return JointState(
        q=np.zeros(4),
        q_dot=np.array([0.4, 0.0, 0.0, 0.0]),
        s=0.5,
        s_dot=path_velocity_m_s,
        current_A=2.0,
        current_integrator_V=0.0,
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

    def test_energy_ledger_port_mismatch_sign_matches_power_reciprocity(self) -> None:
        state = make_energy_ledger_state()
        times = np.array([0.0])
        external = np.zeros(5)
        path = np.array([[state.s, state.s_dot, 0.0]])
        for force_constant, back_emf, expected in (
            (4.2, 3.7, 0.6),
            (3.7, 4.2, -0.6),
            (4.0, 4.0, 0.0),
        ):
            with self.subTest(force_constant=force_constant, back_emf=back_emf):
                model = make_energy_ledger_model(force_constant, back_emf)
                states = np.array([model.pack(state)])
                ledger = _energy_ledger(
                    model, times, states, lambda _time, _state: 0.5,
                    external, np.zeros(1), path, constrained=False,
                )
                self.assertAlmostEqual(ledger[0]["port_mismatch"], expected, places=12)
                expected_net = (
                    ledger[0]["terminal"] - ledger[0]["copper"]
                    - ledger[0]["structural_damping"] - ledger[0]["axis_friction"]
                    + ledger[0]["external"] + expected
                )
                self.assertAlmostEqual(ledger[0]["net"], expected_net, places=12)

    def test_energy_ledger_constraint_power_sign_matches_lambda_times_path_speed(self) -> None:
        model = make_energy_ledger_model()
        external = np.zeros(5)
        for path_speed, reaction, expected_power in ((0.2, 5.0, 1.0), (-0.2, 5.0, -1.0)):
            state = make_energy_ledger_state(path_speed)
            ledger = _energy_ledger(
                model, np.array([0.0]), np.array([model.pack(state)]),
                lambda _time, _state: 0.5, external,
                np.array([reaction]),
                np.array([[state.s, path_speed, 0.0]]),
                constrained=True,
            )
            self.assertAlmostEqual(ledger[0]["lambda_power"], expected_power, places=12)

    def test_free_energy_ledger_excludes_constraint_reaction_power(self) -> None:
        model = make_energy_ledger_model()
        state = make_energy_ledger_state()
        ledger = _energy_ledger(
            model, np.array([0.0]), np.array([model.pack(state)]),
            lambda _time, _state: 0.5, np.zeros(5),
            np.array([1.0e6]),
            np.array([[state.s, state.s_dot, 0.0]]),
            constrained=False,
        )
        self.assertEqual(ledger[0]["lambda_power"], 0.0)

    def test_energy_ledger_dissipation_is_nonnegative_in_both_path_directions(self) -> None:
        model = make_energy_ledger_model(
            structural_damping=np.diag([2.0, 0.0, 0.0, 0.0]),
            axis_viscous_Ns_m=3.0,
            axis_coulomb_N=1.0,
        )
        external = np.zeros(5)
        for direction in (1.0, -1.0):
            base = make_energy_ledger_state(direction * 0.2)
            state = JointState(
                q=base.q.copy(),
                q_dot=np.array([direction * 0.4, 0.0, 0.0, 0.0]),
                s=base.s, s_dot=base.s_dot,
                current_A=base.current_A,
                current_integrator_V=base.current_integrator_V,
            )
            ledger = _energy_ledger(
                model, np.array([0.0]), np.array([model.pack(state)]),
                lambda _time, _state: 0.5, external, np.zeros(1),
                np.array([[state.s, state.s_dot, 0.0]]), constrained=False,
            )[0]
            expected_structural = 2.0 * (0.4 ** 2)
            expected_axis = (
                3.0 * (0.2 ** 2)
                + 1.0 * np.tanh(0.2 / 0.1) * 0.2
            )
            self.assertAlmostEqual(ledger["structural_damping"], expected_structural, places=12)
            self.assertAlmostEqual(ledger["axis_friction"], expected_axis, places=12)
            self.assertGreaterEqual(ledger["structural_damping"], 0.0)
            self.assertGreaterEqual(ledger["axis_friction"], 0.0)

    def test_energy_ledger_external_generalized_power_tracks_force_velocity_sign(self) -> None:
        model = make_energy_ledger_model()
        external = np.array([3.0, 0.0, 0.0, 0.0, 4.0])
        for direction, expected_power in ((1.0, 2.0), (-1.0, -2.0), (0.0, 0.0)):
            base = make_energy_ledger_state(direction * 0.2)
            state = JointState(
                q=base.q.copy(),
                q_dot=np.array([direction * 0.4, 0.0, 0.0, 0.0]),
                s=base.s, s_dot=base.s_dot,
                current_A=base.current_A,
                current_integrator_V=base.current_integrator_V,
            )
            ledger = _energy_ledger(
                model, np.array([0.0]), np.array([model.pack(state)]),
                lambda _time, _state: 0.5, external, np.zeros(1),
                np.array([[state.s, state.s_dot, 0.0]]), constrained=False,
            )[0]
            self.assertAlmostEqual(ledger["external"], expected_power, places=12)
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

    def test_energy_metrics_reject_non_finite_ledger_samples(self) -> None:
        times = np.array([0.0, 1.0, 2.0])
        ledger = [
            {"stored": 0.0, "net": 0.0},
            {"stored": float("inf"), "net": 1.0},
            {"stored": 2.0, "net": 0.0},
        ]
        with self.assertRaisesRegex(FloatingPointError, "non-finite"):
            _energy_metrics(times, ledger, energy_scale=1.0, energy_floor=1.0)

    def test_trapezoid_integral_rejects_non_finite_and_mismatched_inputs(self) -> None:
        with self.assertRaisesRegex(ValueError, "finite"):
            trapezoid_integral(np.array([0.0, 1.0]), np.array([0.0, np.nan]))
        with self.assertRaisesRegex(ValueError, "equal length"):
            trapezoid_integral(np.array([0.0, 1.0]), np.array([0.0]))

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

    def test_output_bundle_verifier_accepts_matching_manifest_and_csvs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _write_output_bundle(
                root / "gantry-joint-drive-path-comparison-timeseries.csv",
                root / "gantry-joint-drive-path-comparison-summary.csv",
                root / "gantry-joint-drive-path-comparison-run-manifest.json",
                timeseries_rows=[{}], summary_rows=[{}, {}],
                manifest={"schema_version": 2, "case_id": "PATH-01",
                          "status": "COMPLETED_REPORT_ONLY",
                          "output_files": {
                              "timeseries_csv": "gantry-joint-drive-path-comparison-timeseries.csv",
                              "summary_csv": "gantry-joint-drive-path-comparison-summary.csv",
                          }},
            )
            verified = verify_output_bundle(root)
            self.assertEqual(verified["status"], "VERIFIED")
            self.assertEqual(verified["recorded_run_status"], "COMPLETED_REPORT_ONLY")
            self.assertTrue(verified["artifacts"]["timeseries_csv"]["verified"])
            self.assertEqual(verified["artifacts"]["summary_csv"]["data_rows"], 2)

    def test_output_bundle_verifier_cli_needs_no_config_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _write_output_bundle(
                root / "gantry-joint-drive-path-comparison-timeseries.csv",
                root / "gantry-joint-drive-path-comparison-summary.csv",
                root / "gantry-joint-drive-path-comparison-run-manifest.json",
                timeseries_rows=[{}], summary_rows=[{}],
                manifest={"schema_version": 2, "case_id": "PATH-01",
                          "status": "COMPLETED_REPORT_ONLY",
                          "output_files": {
                              "timeseries_csv": "gantry-joint-drive-path-comparison-timeseries.csv",
                              "summary_csv": "gantry-joint-drive-path-comparison-summary.csv",
                          }},
            )
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = path_runner.main(["--verify-archive", "--output-dir", str(root)])
            self.assertEqual(exit_code, 0)
            self.assertEqual(json.loads(stdout.getvalue())["status"], "VERIFIED")

    def test_output_bundle_verifier_detects_csv_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            timeseries = root / "gantry-joint-drive-path-comparison-timeseries.csv"
            summary = root / "gantry-joint-drive-path-comparison-summary.csv"
            manifest = root / "gantry-joint-drive-path-comparison-run-manifest.json"
            _write_output_bundle(
                timeseries, summary, manifest,
                timeseries_rows=[{}], summary_rows=[{}],
                manifest={"schema_version": 2, "case_id": "PATH-01",
                          "status": "FAIL",
                          "output_files": {
                              "timeseries_csv": timeseries.name,
                              "summary_csv": summary.name,
                          }},
            )
            original_bytes = timeseries.read_bytes()
            timeseries.write_bytes(b"X" + original_bytes[1:])
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                verify_output_bundle(root)

    def test_output_bundle_verifier_rejects_non_string_status_without_type_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _write_output_bundle(
                root / "gantry-joint-drive-path-comparison-timeseries.csv",
                root / "gantry-joint-drive-path-comparison-summary.csv",
                root / "gantry-joint-drive-path-comparison-run-manifest.json",
                timeseries_rows=[{}], summary_rows=[{}],
                manifest={"schema_version": 2, "case_id": "PATH-01",
                          "status": ["PASS"],
                          "output_files": {
                              "timeseries_csv": "gantry-joint-drive-path-comparison-timeseries.csv",
                              "summary_csv": "gantry-joint-drive-path-comparison-summary.csv",
                          }},
            )
            with self.assertRaisesRegex(ValueError, "status is missing or invalid"):
                verify_output_bundle(root)

    def test_output_bundle_verifier_rejects_manifest_path_override(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            timeseries = root / "gantry-joint-drive-path-comparison-timeseries.csv"
            summary = root / "gantry-joint-drive-path-comparison-summary.csv"
            manifest_path = root / "gantry-joint-drive-path-comparison-run-manifest.json"
            _write_output_bundle(
                timeseries, summary, manifest_path,
                timeseries_rows=[{}], summary_rows=[{}],
                manifest={"schema_version": 2, "case_id": "PATH-01",
                          "status": "PASS",
                          "output_files": {
                              "timeseries_csv": "../outside.csv",
                              "summary_csv": summary.name,
                          }},
            )
            with self.assertRaisesRegex(ValueError, "output_files.timeseries_csv"):
                verify_output_bundle(root)

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

    def test_config_schema_version_rejects_boolean_true(self) -> None:
        with self.assertRaisesRegex(ValueError, "expected integer 1"):
            path_runner._validate_config({"schema_version": True, "case_id": "PATH-01"})

    def test_config_requires_explicit_source_document_id_array(self) -> None:
        config = {
            "schema_version": 1,
            "case_id": "PATH-01",
            "provenance": {"parameter_source": "synthetic fixture"},
        }
        with self.assertRaisesRegex(ValueError, "source_documents_or_measurement_ids is required"):
            path_runner._validate_config(config)

    def test_number_rejects_integer_that_overflows_float_conversion(self) -> None:
        with self.assertRaisesRegex(ValueError, "finite floating-point"):
            _number(10**10000, "oversized_integer")

    def test_interval_count_rejects_overflowing_ratio(self) -> None:
        with self.assertRaisesRegex(ValueError, "must be finite"):
            _interval_count(1.0e308, 1.0e-308)

    def test_interval_count_rejects_unrepresentable_index_range(self) -> None:
        with self.assertRaisesRegex(ValueError, "platform index range"):
            _interval_count(1.0, 1.0e-30)

    def test_interval_count_checks_the_finest_refinement_index_range(self) -> None:
        with self.assertRaisesRegex(ValueError, "h/8 refinement factor"):
            _interval_count(1.5e18, 1.0)

    def test_cli_reports_missing_config_as_a_path01_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                exit_code = path_runner.main([
                    "--config", str(root / "missing-config.json"),
                    "--output-dir", str(root / "results"),
                ])
            self.assertEqual(exit_code, 2)
            self.assertIn("PATH-01 ERROR", stderr.getvalue())

    def test_normalized_state_error_rejects_nonpositive_absolute_tolerance(self) -> None:
        values = np.zeros((2, 2))
        with self.assertRaisesRegex(ValueError, "absolute tolerances must be positive"):
            normalized_state_error(
                values, values, np.array([0.0, 1.0]), np.zeros(2)
            )



class TestSyntheticPATH01Integration(unittest.TestCase):
    CONFIG_PATH = (
        Path(__file__).resolve().parent
        / "gantry-joint-drive-path-01-synthetic-config.json"
    )

    def test_committed_path01_fixture_contract_and_report_only_limits(self) -> None:
        with self.CONFIG_PATH.open("r", encoding="utf-8") as stream:
            config = json.load(stream)
        validated = path_runner._validate_config(config)
        self.assertEqual(config["case_id"], "PATH-01")
        self.assertEqual(validated["start_m"], 0.72)
        self.assertEqual(validated["end_m"], 0.735)
        self.assertEqual(validated["duration_s"], 0.2)
        self.assertEqual(validated["initial_state"].s_dot, 0.0)
        self.assertEqual(validated["external_force"].tolist(), [0.25, 0.01, -0.02, 0.005, 0.20])
        self.assertTrue(all(value is None for value in validated["limits"].values()))
        self.assertEqual(config["provenance"]["source_documents_or_measurement_ids"][0], "SYNTHETIC:CH12-PATH-01:v1")

    def test_path01_runs_both_models_and_verifies_report_only_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output_dir = Path(temporary) / "path-01-output"
            result = path_runner.run_path_comparison(self.CONFIG_PATH, output_dir)
            self.assertEqual(result["case_id"], "PATH-01")
            self.assertEqual(result["status"], "COMPLETED_REPORT_ONLY")
            self.assertEqual(result["acceptance_decision"], "DESCRIPTIVE_ONLY")
            self.assertTrue(result["free_convergence_screen"])
            self.assertTrue(result["prescribed_convergence_screen"])
            self.assertTrue(result["smooth_unsaturated_regime"])
            with (output_dir / "gantry-joint-drive-path-comparison-summary.csv").open(
                "r", encoding="utf-8", newline=""
            ) as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), 4)
            for row in rows:
                self.assertEqual(row["status"], "COMPLETED_REPORT_ONLY")
                self.assertEqual(row["acceptance_decision"], "DESCRIPTIVE_ONLY")
                self.assertTrue(float(row["free_convergence_screen"] in ("True","False")) == 1.0)
                self.assertTrue(float(row["prescribed_convergence_screen"] in ("True","False")) == 1.0)
                self.assertEqual(int(row["free_any_limiter_active_stages"]), 0)
                self.assertEqual(int(row["prescribed_any_limiter_active_stages"]), 0)
                self.assertEqual(int(row["free_rk4_stage_evaluations"]), int(row["expected_rk4_stage_evaluations"]))
                self.assertEqual(int(row["prescribed_rk4_stage_evaluations"]), int(row["expected_rk4_stage_evaluations"]))
                for field in (
                    "path_error_rms_m", "path_error_peak_m",
                    "payload_point_error_rms_m", "lambda_peak_N",
                    "lambda_rms_N", "constraint_work_J",
                    "free_energy_residual_normalized",
                    "prescribed_energy_residual_normalized",
                ):
                    self.assertTrue(np.isfinite(float(row[field])), field)
            verified = path_runner.verify_output_bundle(output_dir)
            self.assertEqual(verified["status"], "VERIFIED")
            self.assertEqual(verified["recorded_run_status"], "COMPLETED_REPORT_ONLY")
            self.assertEqual(len(verified["artifacts"]), 2)


if __name__ == "__main__":
    unittest.main()
