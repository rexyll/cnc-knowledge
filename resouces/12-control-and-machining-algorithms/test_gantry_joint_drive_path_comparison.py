"""Pure-function tests for the PATH-01 comparison runner.

These are resource tests and are not executed by the repository knowledge CI.
Run with:
python -m unittest discover -s resouces/12-control-and-machining-algorithms -p 'test_gantry_joint_drive_path_comparison.py' -v
"""
from __future__ import annotations

import unittest

import numpy as np

from gantry_joint_drive_path_comparison import (
    _acceptance_decision,
    _saturation_stage_report,
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

    def test_normalized_state_error_rejects_nonpositive_absolute_tolerance(self) -> None:
        values = np.zeros((2, 2))
        with self.assertRaisesRegex(ValueError, "absolute tolerances must be positive"):
            normalized_state_error(
                values, values, np.array([0.0, 1.0]), np.zeros(2)
            )


if __name__ == "__main__":
    unittest.main()
