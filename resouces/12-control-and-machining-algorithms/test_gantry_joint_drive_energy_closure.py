"""Resource tests for the independent ENE energy-closure accounting.

These tests are intentionally not executed by the repository Knowledge Quality CI.
"""
from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

import gantry_joint_drive_path_comparison as path_support
import gantry_joint_drive_energy_closure as energy_runner

from gantry_joint_drive_solver import (
    ActuatorKinematics, CurrentLoopParameters, GantryJointDriveModel,
    JointState, MechanicalParameters, SinusoidalBeamGeometry,
)
from gantry_joint_drive_energy_closure import (
    EnergyClosureError, _power_sample, _validate_case_contract,
    _validate_manifest_contract, _read_verified_csv,
    _fixed_trajectory_quadrature_diagnostics, _rk4_stage_power_diagnostics,
    _reference_trajectory_diagnostics, _adjacent_refinement_diagnostics,
    _validate_state_comparison_scale_contract, _validate_residual_noise_floor_contract,
    _residual_order_diagnostics, _assert_json_metrics_close, _assert_json_metrics_exact,
    _derive_energy_residual_noise_budget, _validate_noise_floor_not_below_derived_minimum,
    STATE_VECTOR_FIELDS, STATE_COMPARISON_UNITS,
)


def make_model(*, damping: bool = False, friction: bool = False) -> GantryJointDriveModel:
    D0 = np.diag([2.0, 1.0, 3.0, 0.5]) if damping else np.zeros((4, 4))
    mechanical = MechanicalParameters(
        M0=np.diag([20.0, 8.0, 6.0, 2.0]), D0=D0,
        K0=np.diag([0.0, 10.0, 12.0, 4.0]),
        payload_mass_kg=3.0, axis_equivalent_mass_kg=5.0,
        gravity_acceleration_m_s2=np.zeros(3),
        axis_viscous_Ns_m=1.5 if friction else 0.0,
        axis_coulomb_N=0.8 if friction else 0.0,
        friction_smoothing_speed_m_s=0.02,
    )
    electrical = CurrentLoopParameters(
        resistance_ohm=1.2, inductance_h=0.015,
        back_emf_V_per_m_s=3.0, force_constant_N_per_A=3.0,
        current_limit_A=10.0, voltage_min_V=-60.0, voltage_max_V=60.0,
        kp_V_per_A=2.0, ki_V_per_A_s=5.0,
    )
    actuator = ActuatorKinematics(
        q_coefficients=np.array([0.0, 0.0, 0.0, 0.0]), s_coefficient=1.0
    )
    return GantryJointDriveModel(
        SinusoidalBeamGeometry(span_m=1.0), mechanical, electrical, actuator
    )


class TestIndependentEnergyPowerAccounting(unittest.TestCase):
    def setUp(self) -> None:
        self.state = JointState(
            q=np.array([0.01, 0.02, -0.003, 0.004]),
            q_dot=np.array([0.1, -0.2, 0.03, 0.04]),
            s=0.4, s_dot=0.25, current_A=2.0,
            current_integrator_V=0.0,
        )

    def test_ene01_net_power_is_terminal_input_minus_copper_loss(self) -> None:
        model = make_model()
        sample = _power_sample(model, model.pack(self.state), 2.0,
                               np.zeros(5), "ENE-01")
        self.assertAlmostEqual(sample["terminal_voltage"], 0.0, places=12)
        self.assertAlmostEqual(sample["net"], -1.2 * 4.0, places=12)
        self.assertAlmostEqual(sample["mismatch"], 0.0, places=12)

    def test_ene02_subtracts_structural_and_axis_friction_dissipation(self) -> None:
        model = make_model(damping=True, friction=True)
        sample = _power_sample(model, model.pack(self.state), 2.0,
                               np.zeros(5), "ENE-02")
        expected_damping = float(self.state.q_dot @ model.mechanical.D0 @ self.state.q_dot)
        expected_friction = (
            model.mechanical.axis_viscous_Ns_m * self.state.s_dot**2
            + model.mechanical.axis_coulomb_N
            * np.tanh(self.state.s_dot / model.mechanical.friction_smoothing_speed_m_s)
            * self.state.s_dot
        )
        self.assertGreaterEqual(sample["structural"], 0.0)
        self.assertGreaterEqual(sample["friction"], 0.0)
        self.assertAlmostEqual(sample["net"], -4.8 - expected_damping - expected_friction, places=12)

    def test_ene03_adds_signed_external_generalized_power(self) -> None:
        model = make_model(damping=True, friction=True)
        external = np.array([1.0, -2.0, 3.0, 4.0, 5.0])
        sample = _power_sample(model, model.pack(self.state), 2.0,
                               external, "ENE-03")
        velocity = np.concatenate((self.state.q_dot, [self.state.s_dot]))
        expected_external = float(external @ velocity)
        self.assertAlmostEqual(sample["external"], expected_external, places=12)
        self.assertAlmostEqual(sample["net"], -4.8 - sample["structural"]
                               - sample["friction"] + expected_external, places=12)

    def test_ene02_rejects_degenerate_zero_dissipation_configuration(self) -> None:
        model = make_model()
        with self.assertRaisesRegex(EnergyClosureError, "structural damping"):
            _validate_case_contract("ENE-02", model, np.zeros(5), [
                "Q_x_common", "Q_yaw", "Q_bending", "Q_torsion", "Q_s"
            ])

    def test_ene02_requires_both_viscous_and_coulomb_friction(self) -> None:
        model = make_model(damping=True, friction=False)
        with self.assertRaisesRegex(EnergyClosureError, "viscous and Coulomb"):
            _validate_case_contract("ENE-02", model, np.zeros(5), [
                "Q_x_common", "Q_yaw", "Q_bending", "Q_torsion", "Q_s"
            ])

    def test_ene03_rejects_zero_external_generalized_force(self) -> None:
        model = make_model(damping=True, friction=True)
        with self.assertRaisesRegex(EnergyClosureError, "nonzero external"):
            _validate_case_contract("ENE-03", model, np.zeros(5), [
                "Q_x_common", "Q_yaw", "Q_bending", "Q_torsion", "Q_s"
            ])

    def test_external_generalized_force_order_is_exact(self) -> None:
        model = make_model(damping=True, friction=True)
        with self.assertRaisesRegex(EnergyClosureError, "must exactly match"):
            _validate_case_contract("ENE-03", model, np.ones(5), [
                "Q_yaw", "Q_x_common", "Q_bending", "Q_torsion", "Q_s"
            ])

    def test_energy_diagnostics_attribute_absolute_component_work(self) -> None:
        from gantry_joint_drive_energy_closure import _energy_diagnostics
        integrals = {
            "terminal_input": 100.0, "copper": -80.0, "structural": -10.0,
            "friction": -5.0, "external": 4.0, "mismatch": 1.0,
        }
        result = _energy_diagnostics(integrals, 2.0, 50.0, 1e-6, 10.0, 3.0)
        self.assertAlmostEqual(result["absolute_component_work_sum_J"], 200.0)
        self.assertAlmostEqual(result["terminal_input_abs_contribution_fraction"], 0.5)
        self.assertAlmostEqual(result["copper_loss_abs_contribution_fraction"], 0.4)
        self.assertAlmostEqual(result["energy_residual_over_scale"], 0.04)
        self.assertAlmostEqual(result["energy_residual_over_absolute_net_power_work"], 0.2)
        self.assertAlmostEqual(result["energy_residual_over_absolute_component_work"], 0.01)
        self.assertAlmostEqual(result["simpson_trapezoid_net_work_difference_J"], 1.0)

    def test_energy_diagnostics_use_floor_for_zero_component_and_net_work(self) -> None:
        from gantry_joint_drive_energy_closure import _energy_diagnostics
        integrals = {key: 0.0 for key in (
            "terminal_input", "copper", "structural", "friction", "external", "mismatch"
        )}
        result = _energy_diagnostics(integrals, 2.0, 10.0, 0.5, 0.0, 2.0)
        self.assertEqual(result["absolute_component_work_sum_J"], 0.0)
        self.assertEqual(result["terminal_input_abs_contribution_fraction"], 0.0)
        self.assertEqual(result["energy_residual_over_absolute_net_power_work"], 4.0)
        self.assertEqual(result["energy_residual_over_absolute_component_work"], 4.0)

    def test_energy_diagnostics_do_not_relabel_simpson_trapezoid_gap_as_error_bound(self) -> None:
        from gantry_joint_drive_energy_closure import _energy_diagnostics
        integrals = {
            "terminal_input": 3.0, "copper": -2.0, "structural": 0.0,
            "friction": 0.0, "external": 0.0, "mismatch": 0.0,
        }
        result = _energy_diagnostics(integrals, 0.25, 1.0, 1e-9, 1.0, -0.75)
        self.assertEqual(result["simpson_trapezoid_net_work_difference_J"], 1.0)

    def test_fixed_trajectory_quadrature_uses_nested_samples_and_decomposes_work_delta(self) -> None:
        times = np.linspace(0.0, 1.0, 17)
        power = 1.0 + times ** 4

        def simpson(values: np.ndarray, step: float) -> float:
            return float(step / 3.0 * (
                values[0] + values[-1]
                + 4.0 * np.sum(values[1:-1:2])
                + 2.0 * np.sum(values[2:-1:2])
            ))

        expected_fixed = [
            simpson(power[::8], 0.5),
            simpson(power[::4], 0.25),
            simpson(power[::2], 0.125),
            simpson(power, 0.0625),
        ]
        coupled_work = [11.0, 9.0, 8.0, expected_fixed[-1]]
        stored_delta = [7.0, 5.0, 3.0, 2.0]
        result = _fixed_trajectory_quadrature_diagnostics(
            times, power, coupled_work, stored_delta
        )
        for row, expected in zip(result, expected_fixed):
            self.assertAlmostEqual(row["fixed_trajectory_net_power_work_J"], expected)
        self.assertAlmostEqual(
            result[0]["fixed_trajectory_quadrature_delta_from_finest_J"],
            expected_fixed[0] - expected_fixed[-1],
        )
        self.assertAlmostEqual(
            result[0]["coupled_vs_fixed_trajectory_net_work_delta_J"],
            coupled_work[0] - expected_fixed[0],
        )
        self.assertAlmostEqual(
            result[0]["coupled_net_work_delta_vs_finest_J"],
            result[0]["fixed_trajectory_quadrature_delta_from_finest_J"]
            + result[0]["coupled_vs_fixed_trajectory_net_work_delta_J"],
        )
        self.assertAlmostEqual(
            result[0]["coupled_energy_residual_delta_vs_finest_J"],
            (stored_delta[0] - stored_delta[-1])
            - (coupled_work[0] - coupled_work[-1]),
        )

    def test_fixed_trajectory_quadrature_rejects_non_nested_interval_count(self) -> None:
        with self.assertRaisesRegex(ValueError, "divisible by sixteen"):
            _fixed_trajectory_quadrature_diagnostics(
                np.linspace(0.0, 1.0, 7), np.ones(7),
                [1.0, 1.0, 1.0, 1.0], [0.0, 0.0, 0.0, 0.0],
            )

    def test_fixed_trajectory_quadrature_rejects_non_finite_samples(self) -> None:
        power = np.ones(17)
        power[8] = np.nan
        with self.assertRaisesRegex(FloatingPointError, "must be finite"):
            _fixed_trajectory_quadrature_diagnostics(
                np.linspace(0.0, 1.0, 17), power,
                [1.0, 1.0, 1.0, 1.0], [0.0, 0.0, 0.0, 0.0],
            )


    def test_rk4_stage_power_uses_classical_weights_and_reports_endpoint_gap(self) -> None:
        rows = []
        for index, net in enumerate((1.0, -1.0, 1.0, -1.0)):
            rows.append({
                "stage_index": index, "step_s": 0.1,
                "terminal_input_power_W": 6.0, "copper_loss_W": 2.0,
                "structural_damping_loss_W": 1.0, "axis_friction_loss_W": 0.5,
                "external_generalized_power_W": 0.0,
                "electromechanical_mismatch_power_W": 0.0,
                "net_power_W": net,
            })
        result = _rk4_stage_power_diagnostics(rows, 0.3, 0.02)
        self.assertAlmostEqual(result["rk4_stage_terminal_input_work_J"], 0.6)
        self.assertAlmostEqual(result["rk4_stage_copper_loss_J"], 0.2)
        self.assertAlmostEqual(result["rk4_stage_net_power_work_J"], 0.0)
        self.assertAlmostEqual(result["rk4_stage_absolute_net_power_work_J"], 0.1)
        self.assertAlmostEqual(result["rk4_stage_energy_residual_J"], 0.3)
        self.assertAlmostEqual(
            result["rk4_stage_vs_endpoint_simpson_net_work_delta_J"], -0.02
        )

    def test_rk4_stage_power_rejects_incomplete_or_misordered_groups(self) -> None:
        base = {
            "step_s": 0.1, "terminal_input_power_W": 1.0,
            "copper_loss_W": 0.0, "structural_damping_loss_W": 0.0,
            "axis_friction_loss_W": 0.0, "external_generalized_power_W": 0.0,
            "electromechanical_mismatch_power_W": 0.0, "net_power_W": 1.0,
        }
        rows = [{**base, "stage_index": i} for i in (0, 1, 3, 2)]
        with self.assertRaisesRegex(ValueError, "k1,k2,k3,k4"):
            _rk4_stage_power_diagnostics(rows, 0.0, 0.0)
        with self.assertRaisesRegex(ValueError, "groups of four"):
            _rk4_stage_power_diagnostics(rows[:3], 0.0, 0.0)

    def test_rk4_stage_power_rejects_non_finite_samples(self) -> None:
        rows = [{
            "stage_index": i, "step_s": 0.1,
            "terminal_input_power_W": 1.0, "copper_loss_W": 0.0,
            "structural_damping_loss_W": 0.0, "axis_friction_loss_W": 0.0,
            "external_generalized_power_W": 0.0,
            "electromechanical_mismatch_power_W": 0.0,
            "net_power_W": float("nan") if i == 2 else 1.0,
        } for i in range(4)]
        with self.assertRaisesRegex(FloatingPointError, "non-finite power"):
            _rk4_stage_power_diagnostics(rows, 0.0, 0.0)


    def _state_comparison_scales(self) -> dict[str, float]:
        return {field: float(index + 1) for index, field in enumerate(STATE_VECTOR_FIELDS)}

    def _make_reference_fixture(self, intervals: int = 32):
        times = np.linspace(0.0, 1.0, intervals + 1)
        reference_rows = []
        for time_s in times:
            row = {
                "case_id": "ENE-01", "step_level": "reference_h/16",
                "time_s": float(time_s), "stored_energy_J": 5.0 + float(time_s),
                "net_power_W": 1.0 + float(time_s**2),
            }
            row.update({field: float((index + 1) * time_s)
                        for index, field in enumerate(STATE_VECTOR_FIELDS)})
            reference_rows.append(row)
        primary_rows = []
        summaries = {}
        for level_index, label in enumerate(("h", "h/2", "h/4", "h/8")):
            stride = 2 ** (4 - level_index)
            selected = reference_rows[::stride]
            perturbation = 0.01 * (level_index + 1)
            level_rows = []
            for source in selected:
                row = dict(source)
                row["step_level"] = label
                row["time_s"] = float(source["time_s"])
                row["net_power_W"] = float(source["net_power_W"]) + perturbation
                for field in STATE_VECTOR_FIELDS:
                    row[field] = float(source[field]) + perturbation
                level_rows.append(row)
            primary_rows.extend(level_rows)
            level_times = np.asarray([row["time_s"] for row in level_rows], dtype=float)
            level_power = np.asarray([row["net_power_W"] for row in level_rows], dtype=float)
            delta = float(level_rows[-1]["stored_energy_J"] - level_rows[0]["stored_energy_J"])
            work = float(path_support.composite_simpson_13(level_times, level_power))
            summaries[label] = {
                "net_power_work_J": work,
                "delta_stored_energy_J": delta,
                "energy_residual_simpson_J": delta - work,
            }
        return reference_rows, primary_rows, summaries

    def test_h16_reference_comparison_uses_nested_nodes_and_reports_componentwise_state_error(self) -> None:
        reference_rows, primary_rows, summaries = self._make_reference_fixture()
        result = _reference_trajectory_diagnostics(
            reference_rows, primary_rows, summaries, 10.0, 1e-6
        )
        self.assertEqual(result["level"], "reference_h/16")
        self.assertEqual(result["finest"]["intervals"], 32)
        self.assertEqual(len(result["comparisons"]), 4)
        self.assertEqual([row["step_level"] for row in result["comparisons"]],
                         ["h", "h/2", "h/4", "h/8"])
        for index, row in enumerate(result["comparisons"]):
            self.assertEqual(len(row["state_max_abs_difference"]), 12)
            self.assertAlmostEqual(
                row["state_max_abs_difference"][0], 0.01 * (index + 1)
            )
            self.assertAlmostEqual(
                row["coupled_vs_reference_net_work_delta_J"],
                summaries[row["step_level"]]["net_power_work_J"]
                - row["reference_net_power_work_J"],
            )

    def test_h16_reference_comparison_rejects_fewer_than_32_intervals(self) -> None:
        reference_rows, primary_rows, summaries = self._make_reference_fixture()
        # Keep all other fixture data valid, then reduce only the reference
        # grid so the target precondition rejects it before any comparison.
        reference_rows = reference_rows[::2]
        with self.assertRaisesRegex(ValueError, "at least 32 intervals"):
            _reference_trajectory_diagnostics(
                reference_rows, primary_rows, summaries, 10.0, 1e-6
            )

    def test_h16_reference_comparison_rejects_non_finite_state_or_power(self) -> None:
        reference_rows, primary_rows, summaries = self._make_reference_fixture()
        reference_rows[8]["net_power_W"] = float("nan")
        with self.assertRaisesRegex(FloatingPointError, "non-finite data"):
            _reference_trajectory_diagnostics(
                reference_rows, primary_rows, summaries, 10.0, 1e-6
            )


    def test_adjacent_refinement_reports_shared_grid_componentwise_differences(self) -> None:
        reference_rows, primary_rows, _ = self._make_reference_fixture()
        offsets = {"h": 0.08, "h/2": 0.04, "h/4": 0.02, "h/8": 0.01}
        reference_by_time = {float(row["time_s"]): row for row in reference_rows}
        for row in primary_rows:
            offset = offsets[row["step_level"]]
            base = reference_by_time[float(row["time_s"])]
            row["net_power_W"] = float(base["net_power_W"]) + offset
            for field in STATE_VECTOR_FIELDS:
                row[field] = float(base[field]) + offset
        smooth = {"h": True, "h/2": True, "h/4": False,
                  "h/8": True, "reference_h/16": True}
        scales = self._state_comparison_scales()
        result = _adjacent_refinement_diagnostics(primary_rows, reference_rows, smooth, scales)
        self.assertEqual(result["pair_order"], [
            ["h", "h/2"], ["h/2", "h/4"], ["h/4", "h/8"],
            ["h/8", "reference_h/16"],
        ])
        self.assertEqual(len(result["pairs"]), 4)
        expected = (0.04, 0.02, 0.01, 0.01)
        for row, difference in zip(result["pairs"], expected):
            self.assertEqual(len(row["state_max_abs_difference"]), 12)
            self.assertAlmostEqual(row["state_max_abs_difference"][0], difference)
        self.assertAlmostEqual(result["pairs"][0]["state_max_abs_difference_normalized"][0], 0.04)
        self.assertAlmostEqual(result["pairs"][0]["state_max_abs_difference_normalized"][1], 0.02)
        self.assertEqual(len(result["pairs"][0]["state_rms_difference_normalized"]), 12)
        self.assertFalse(result["pairs"][1]["both_paths_smooth_unsaturated"])
        self.assertAlmostEqual(
            result["pairs"][0]["fine_minus_coarse_net_work_on_shared_grid_J"], -0.04
        )

    def test_adjacent_refinement_rejects_non_nested_sample_counts(self) -> None:
        reference_rows, primary_rows, _ = self._make_reference_fixture()
        broken = [row for row in primary_rows if row["step_level"] != "h/2"]
        with self.assertRaisesRegex(ValueError, "sample count is not nested"):
            _adjacent_refinement_diagnostics(
                broken, reference_rows,
                {"h": True, "h/2": True, "h/4": True, "h/8": True,
                 "reference_h/16": True}, self._state_comparison_scales(),
            )

    def test_adjacent_refinement_rejects_non_finite_state_or_power(self) -> None:
        reference_rows, primary_rows, _ = self._make_reference_fixture()
        primary_rows[3]["q1_m"] = float("nan")
        with self.assertRaisesRegex(FloatingPointError, "samples must be finite"):
            _adjacent_refinement_diagnostics(
                primary_rows, reference_rows,
                {"h": True, "h/2": True, "h/4": True, "h/8": True,
                 "reference_h/16": True}, self._state_comparison_scales(),
            )

    def _valid_noise_budget(self) -> dict:
        return {
            "floating_point_format": "IEEE-754 binary64",
            "rounding_mode": "roundTiesToEven",
            "arithmetic_assumptions_confirmed": True,
            "no_overflow_or_subnormal_intermediates": True,
            "max_abs_stored_energy_J": 100.0,
            "stored_energy_evaluation_error_bound_J": 1e-12,
            "trajectory_energy_roundoff_effect_bound_J": 2e-12,
            "max_abs_net_power_W": 10.0,
            "net_power_evaluation_error_bound_W": 1e-13,
            "trajectory_power_roundoff_effect_bound_W": 2e-13,
            "time_grid_roundoff_effect_bound_J": 1e-12,
        }

    def _valid_manifest_contract(self) -> dict:
        noise_budget = self._valid_noise_budget()
        noise_budget_report = _derive_energy_residual_noise_budget(
            noise_budget, 1.0, 4, context="manifest",
        )[1]
        return {
            "schema_version": 7, "config_schema_version": 4,
            "config_sha256": "a" * 64, "solver_sha256": "b" * 64,
            "path_support_sha256": "c" * 64, "runner_sha256": "d" * 64,
            "case_id": "ENE-01", "status": "COMPLETED_REPORT_ONLY",
            "numerical_results_present": True, "resource_tests_executed": False,
            "parameter_source": "synthetic test fixture", "source_documents_or_measurement_ids": [],
            "started_at_utc": "2026-01-01T00:00:00+00:00",
            "completed_at_utc": "2026-01-01T00:00:01+00:00",
            "duration_s": 1.0, "base_step_s": 0.25,
            "energy_normalization_scale_J": 1.0, "energy_normalization_floor_J": 1.0,
            "state_comparison_scales": {field: float(index + 1) for index, field in enumerate(STATE_VECTOR_FIELDS)},
            "state_comparison_scale_source": "synthetic unit-test characteristic scales",
            "state_comparison_scale_source_ids": ["test-fixture:state-scales-v1"],
            "state_vector_order": list(STATE_VECTOR_FIELDS),
            "state_comparison_units": dict(STATE_COMPARISON_UNITS),
            "energy_residual_noise_floor_J": noise_budget_report["minimum_noise_floor_J"] * 1.25,
            "energy_residual_noise_budget": noise_budget,
            "energy_residual_noise_budget_report": noise_budget_report,
            "energy_residual_noise_floor_method": "pre-run operation-bound fixture",
            "energy_residual_noise_floor_source": "synthetic test evidence",
            "energy_residual_noise_floor_source_ids": ["test-fixture:noise-floor-v1"],
            "normalized_energy_closure_threshold": None,
            "refinement_schedule": ["h", "h/2", "h/4", "h/8"],
            "limiter_stage_reports": [
                {"level": label, "stage_evaluations": 4 * 4 * (2 ** i),
                 "expected_stage_evaluations": 4 * 4 * (2 ** i),
                 "current_reference_saturated_stages": 0, "voltage_saturated_stages": 0,
                 "any_limiter_active_stages": 0, "stage_count_matches_expected": True,
                 "smooth_unsaturated": True}
                for i, label in enumerate(("h", "h/2", "h/4", "h/8"))
            ],
            "all_refinements_smooth_unsaturated": True,
            "reference_trajectory_report": {
                "level": "reference_h/16", "intervals": 64, "samples": 65,
                "step_s": 1.0 / 64.0, "stage_evaluations": 256,
                "expected_stage_evaluations": 256,
                "current_reference_saturated_stages": 0,
                "voltage_saturated_stages": 0, "any_limiter_active_stages": 0,
                "stage_count_matches_expected": True, "smooth_unsaturated": True,
                "stage_power_diagnostics": {"rk4_stage_net_power_work_J": 0.0},
            },
        }



    def test_derived_noise_budget_accounts_for_simpson_reduction_and_residual_subtractions(self) -> None:
        budget = self._valid_noise_budget()
        normalized, report = _derive_energy_residual_noise_budget(
            budget, 1.0, 4, context="metrics",
        )
        self.assertEqual(normalized["floating_point_format"], "IEEE-754 binary64")
        self.assertEqual(sys.float_info.rounds, 1)
        self.assertEqual(report["finest_interval_count"], 64)
        self.assertEqual(report["odd_sample_count"], 32)
        self.assertEqual(report["even_interior_sample_count"], 31)
        self.assertGreater(report["composite_simpson_accumulation_roundoff_J"], 0.0)
        self.assertGreater(report["delta_energy_subtraction_roundoff_J"], 0.0)
        self.assertGreater(report["final_energy_residual_subtraction_roundoff_J"], 0.0)
        self.assertGreater(report["minimum_noise_floor_J"], report["component_subtotal_J"])
        _assert_json_metrics_exact(report, dict(report))
        tampered_report = dict(report)
        tampered_report["composite_simpson_accumulation_roundoff_J"] += 1e-13
        with self.assertRaisesRegex(EnergyClosureError, "composite_simpson_accumulation_roundoff_J"):
            _assert_json_metrics_exact(tampered_report, report)

        _, finer_report = _derive_energy_residual_noise_budget(
            budget, 1.0, 8, context="metrics",
        )
        self.assertGreater(
            finer_report["composite_simpson_accumulation_roundoff_J"],
            report["composite_simpson_accumulation_roundoff_J"],
        )

    def test_derived_noise_budget_rejects_unconfirmed_arithmetic_and_missing_bounds(self) -> None:
        budget = self._valid_noise_budget()
        budget["arithmetic_assumptions_confirmed"] = False
        with self.assertRaisesRegex(EnergyClosureError, "must be true"):
            _derive_energy_residual_noise_budget(budget, 1.0, 4, context="metrics")
        budget = self._valid_noise_budget()
        budget["rounding_mode"] = "roundTowardZero"
        with self.assertRaisesRegex(EnergyClosureError, "rounding_mode"):
            _derive_energy_residual_noise_budget(budget, 1.0, 4, context="metrics")
        budget = self._valid_noise_budget()
        del budget["trajectory_power_roundoff_effect_bound_W"]
        with self.assertRaisesRegex(EnergyClosureError, "exact required fields"):
            _derive_energy_residual_noise_budget(budget, 1.0, 4, context="metrics")

    def test_noise_floor_must_not_be_below_derived_arithmetic_bound(self) -> None:
        _, report = _derive_energy_residual_noise_budget(
            self._valid_noise_budget(), 1.0, 4, context="metrics",
        )
        _validate_noise_floor_not_below_derived_minimum(
            report["minimum_noise_floor_J"], report, context="metrics",
        )
        with self.assertRaisesRegex(EnergyClosureError, "below the derived minimum"):
            _validate_noise_floor_not_below_derived_minimum(
                report["minimum_noise_floor_J"] * 0.5, report, context="metrics",
            )

    def test_state_comparison_scale_validation_requires_exact_positive_components(self) -> None:
        scales = self._state_comparison_scales()
        validated, source, source_ids = _validate_state_comparison_scale_contract(
            scales, "machine specification and commissioning envelope",
            ["spec:gantry-axis-envelope-v1", "commissioning:stroke-velocity-envelope-v2"],
            context="metrics",
        )
        self.assertEqual(list(validated), STATE_VECTOR_FIELDS)
        self.assertEqual(source, "machine specification and commissioning envelope")
        self.assertEqual(len(source_ids), 2)
        with self.assertRaisesRegex(EnergyClosureError, "exactly all 12"):
            _validate_state_comparison_scale_contract(
                {key: value for key, value in scales.items() if key != "current_A"},
                "source", ["doc:scale"], context="metrics",
            )
        scales["q1_m"] = 0.0
        with self.assertRaises(ValueError):
            _validate_state_comparison_scale_contract(
                scales, "source", ["doc:scale"], context="metrics",
            )

    def test_state_comparison_scale_validation_requires_traceable_source_ids(self) -> None:
        with self.assertRaisesRegex(EnergyClosureError, "scale_source is required"):
            _validate_state_comparison_scale_contract(
                self._state_comparison_scales(), " ", ["doc:scale"], context="metrics",
            )
        with self.assertRaisesRegex(EnergyClosureError, "non-empty string array"):
            _validate_state_comparison_scale_contract(
                self._state_comparison_scales(), "engineering envelope", [], context="metrics",
            )
        with self.assertRaisesRegex(EnergyClosureError, "must be unique"):
            _validate_state_comparison_scale_contract(
                self._state_comparison_scales(), "engineering envelope",
                ["doc:scale", "doc:scale"], context="metrics",
            )

    def test_manifest_rejects_nonpositive_or_incomplete_state_comparison_scales(self) -> None:
        manifest = self._valid_manifest_contract()
        manifest["state_comparison_scales"]["current_A"] = -1.0
        with self.assertRaises(ValueError):
            _validate_manifest_contract(manifest)
        manifest = self._valid_manifest_contract()
        del manifest["state_comparison_scales"]["q1_m"]
        with self.assertRaisesRegex(EnergyClosureError, "exactly all 12"):
            _validate_manifest_contract(manifest)
        manifest = self._valid_manifest_contract()
        manifest["state_vector_order"].reverse()
        with self.assertRaisesRegex(EnergyClosureError, "state_vector_order"):
            _validate_manifest_contract(manifest)
        manifest = self._valid_manifest_contract()
        manifest["state_comparison_units"]["q1_m"] = "mm"
        with self.assertRaisesRegex(EnergyClosureError, "state_comparison_units"):
            _validate_manifest_contract(manifest)

    def test_json_diagnostic_comparison_accepts_and_checks_null_order_values(self) -> None:
        _assert_json_metrics_close(
            {"gate_status": "AT_OR_BELOW_NOISE_FLOOR", "orders": [None, None]},
            {"gate_status": "AT_OR_BELOW_NOISE_FLOOR", "orders": [None, None]},
        )
        with self.assertRaisesRegex(EnergyClosureError, "orders\\[1\\] value is inconsistent"):
            _assert_json_metrics_close(
                {"gate_status": "AT_OR_BELOW_NOISE_FLOOR", "orders": [None, 0.0]},
                {"gate_status": "AT_OR_BELOW_NOISE_FLOOR", "orders": [None, None]},
            )

    def test_residual_noise_floor_validation_requires_positive_sourced_contract(self) -> None:
        floor, method, source, ids = _validate_residual_noise_floor_contract(
            1e-12, "operation-bound numerical analysis", "numerical method note",
            ["test-fixture:noise-bound-v1"], context="metrics",
        )
        self.assertEqual(floor, 1e-12)
        self.assertEqual(method, "operation-bound numerical analysis")
        self.assertEqual(source, "numerical method note")
        self.assertEqual(ids, ["test-fixture:noise-bound-v1"])
        with self.assertRaises(ValueError):
            _validate_residual_noise_floor_contract(
                0.0, "method", "source", ["doc:noise"], context="metrics",
            )
        with self.assertRaisesRegex(EnergyClosureError, "method is required"):
            _validate_residual_noise_floor_contract(
                1e-12, " ", "source", ["doc:noise"], context="metrics",
            )
        with self.assertRaisesRegex(EnergyClosureError, "must be unique"):
            _validate_residual_noise_floor_contract(
                1e-12, "method", "source", ["doc:noise", "doc:noise"], context="metrics",
            )

    def test_residual_order_requires_above_floor_same_sign_monotone_smooth_series(self) -> None:
        summaries = [
            {"energy_residual_simpson_J": value}
            for value in (16.0, 8.0, 4.0, 2.0)
        ]
        reference = {"finest": {"energy_residual_simpson_J": 1.0}}
        eligible = _residual_order_diagnostics(
            summaries, reference, [True, True, True, True, True], 0.5,
        )
        self.assertEqual(eligible["gate_status"], "ELIGIBLE")
        for order in eligible["pairwise_empirical_orders"]:
            self.assertAlmostEqual(order, 1.0)

        below_floor = _residual_order_diagnostics(
            summaries, reference, [True, True, True, True, True], 1.0,
        )
        self.assertEqual(below_floor["gate_status"], "AT_OR_BELOW_NOISE_FLOOR")
        self.assertTrue(all(order is None for order in below_floor["pairwise_empirical_orders"]))

        sign_crossing = [dict(row) for row in summaries]
        sign_crossing[1]["energy_residual_simpson_J"] *= -1.0
        crossed = _residual_order_diagnostics(
            sign_crossing, reference, [True, True, True, True, True], 0.5,
        )
        self.assertEqual(crossed["gate_status"], "SIGN_CROSSING")

        non_monotone = [dict(row) for row in summaries]
        non_monotone[2]["energy_residual_simpson_J"] = 9.0
        unstable = _residual_order_diagnostics(
            non_monotone, reference, [True, True, True, True, True], 0.5,
        )
        self.assertEqual(unstable["gate_status"], "NON_MONOTONIC_MAGNITUDE")

        limited = _residual_order_diagnostics(
            summaries, reference, [True, True, False, True, True], 0.5,
        )
        self.assertEqual(limited["gate_status"], "NONSMOOTH_OR_LIMITER_ACTIVE")

    def test_manifest_rejects_missing_residual_noise_floor_provenance(self) -> None:
        manifest = self._valid_manifest_contract()
        manifest["energy_residual_noise_floor_source_ids"] = []
        with self.assertRaisesRegex(EnergyClosureError, "non-empty string array"):
            _validate_manifest_contract(manifest)
        manifest = self._valid_manifest_contract()
        manifest["energy_residual_noise_floor_J"] = 0.0
        with self.assertRaises(ValueError):
            _validate_manifest_contract(manifest)

    def test_manifest_rejects_inconsistent_h16_reference_stage_count(self) -> None:
        manifest = self._valid_manifest_contract()
        manifest["reference_trajectory_report"]["stage_evaluations"] -= 1
        with self.assertRaisesRegex(EnergyClosureError, "reference stage evaluation count"):
            _validate_manifest_contract(manifest)

    def test_archive_manifest_rejects_invalid_or_unsubstantiated_status(self) -> None:
        manifest = self._valid_manifest_contract()
        manifest["status"] = "VERIFIED"
        with self.assertRaisesRegex(EnergyClosureError, "status"):
            _validate_manifest_contract(manifest)
        manifest = self._valid_manifest_contract()
        manifest["resource_tests_executed"] = True
        with self.assertRaisesRegex(EnergyClosureError, "resource_tests_executed"):
            _validate_manifest_contract(manifest)

    def test_archive_manifest_rejects_inconsistent_rk4_stage_count(self) -> None:
        manifest = self._valid_manifest_contract()
        manifest["limiter_stage_reports"][2]["stage_evaluations"] -= 1
        with self.assertRaisesRegex(EnergyClosureError, "stage-count flag"):
            _validate_manifest_contract(manifest)

    def test_archive_csv_rejects_non_finite_numeric_values(self) -> None:
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.csv"
            path.write_text("value,flag\nNaN,True\n", encoding="utf-8")
            with self.assertRaisesRegex(EnergyClosureError, "non-finite"):
                _read_verified_csv(path, ["value", "flag"], path.name,
                                   boolean_fields=("flag",))

    def test_archive_csv_rejects_invalid_boolean_tokens(self) -> None:
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.csv"
            path.write_text("value,flag\n1,yes\n", encoding="utf-8")
            with self.assertRaisesRegex(EnergyClosureError, "invalid boolean"):
                _read_verified_csv(path, ["value", "flag"], path.name,
                                   boolean_fields=("flag",))

    def test_manifest_rejects_unbounded_refinement_sample_count(self) -> None:
        manifest = self._valid_manifest_contract()
        manifest["duration_s"] = 100000.0
        manifest["base_step_s"] = 0.25
        with self.assertRaisesRegex(EnergyClosureError, "supported limit"):
            _validate_manifest_contract(manifest)

    def test_archive_manifest_marks_stage_count_mismatch_as_not_valid_for_pass(self) -> None:
        manifest = self._valid_manifest_contract()
        manifest["limiter_stage_reports"][1]["stage_evaluations"] -= 1
        manifest["limiter_stage_reports"][1]["stage_count_matches_expected"] = False
        manifest["limiter_stage_reports"][1]["smooth_unsaturated"] = False
        manifest["all_refinements_smooth_unsaturated"] = False
        contract = _validate_manifest_contract(manifest)
        self.assertFalse(contract["all_stage_counts_match"])

    def test_power_sample_rejects_non_finite_state(self) -> None:
        model = make_model()
        vector = model.pack(self.state)
        vector[10] = float("nan")
        with self.assertRaisesRegex(FloatingPointError, "12 finite values"):
            _power_sample(model, vector, 2.0, np.zeros(5), "ENE-01")

    def test_rk4_stage_snapshots_and_energy_voltage_match_current_rhs(self) -> None:
        model = make_model()
        stage_snapshots = []

        def command(time_s: float, state: JointState) -> float:
            stage_snapshots.append((time_s, state.copy()))
            return 2.0

        model.simulate(self.state, 0.2, 0.1, command)
        self.assertEqual(len(stage_snapshots), 4 * 2)
        expected_times = (0.0, 0.05, 0.05, 0.1, 0.1, 0.15, 0.15, 0.2)
        for (time_s, state), expected_time in zip(stage_snapshots, expected_times):
            self.assertAlmostEqual(time_s, expected_time, places=12)
            vector = model.pack(state)
            sample = _power_sample(model, vector, 2.0, np.zeros(5), "ENE-01")
            derivative = model.derivative(time_s, vector, 2.0)
            ell_dot = model.actuator_relative_velocity(state.q_dot, state.s_dot)
            expected_current_rate = (
                sample["terminal_voltage"]
                - model.electrical.resistance_ohm * state.current_A
                - model.electrical.back_emf_V_per_m_s * ell_dot
            ) / model.electrical.inductance_h
            self.assertAlmostEqual(
                derivative[10], expected_current_rate, places=12
            )
            self.assertAlmostEqual(
                sample["terminal_input"],
                sample["terminal_voltage"] * state.current_A,
                places=12,
            )

    def test_external_power_changes_sign_when_velocity_reverses(self) -> None:
        model = make_model()
        forward = self.state
        reverse = JointState(
            q=forward.q.copy(), q_dot=-forward.q_dot.copy(),
            s=forward.s, s_dot=-forward.s_dot,
            current_A=forward.current_A,
            current_integrator_V=forward.current_integrator_V,
        )
        external = np.array([1.0, -2.0, 3.0, 4.0, 5.0])
        positive = _power_sample(model, model.pack(forward), 2.0, external, "ENE-03")
        negative = _power_sample(model, model.pack(reverse), 2.0, external, "ENE-03")
        self.assertAlmostEqual(positive["external"], -negative["external"], places=12)


class TestSyntheticENE01Integration(unittest.TestCase):
    CONFIG_PATH = (
        Path(__file__).resolve().parent
        / "gantry-joint-drive-ene-01-synthetic-config.json"
    )

    def test_committed_ene01_fixture_obeys_ideal_one_port_contract(self) -> None:
        config = json.loads(self.CONFIG_PATH.read_text(encoding="utf-8"))
        validated = energy_runner._validate(config)
        model = validated["model"]
        self.assertEqual(config["case_id"], "ENE-01")
        self.assertIsNone(validated["threshold"])
        self.assertEqual(validated["external"].tolist(), [0.0] * 5)
        self.assertTrue(np.array_equal(model.mechanical.D0, np.zeros((4, 4))))
        self.assertEqual(model.mechanical.axis_viscous_Ns_m, 0.0)
        self.assertEqual(model.mechanical.axis_coulomb_N, 0.0)
        self.assertEqual(
            model.electrical.force_constant_N_per_A,
            model.electrical.back_emf_V_per_m_s,
        )
        self.assertGreaterEqual(
            validated["energy_residual_noise_floor_J"],
            validated["energy_residual_noise_budget_report"]["minimum_noise_floor_J"],
        )
        self.assertTrue(
            all(value > 0.0 for value in validated["state_comparison_scales"].values())
        )

    def test_ene01_four_level_plus_h16_bundle_is_report_only_and_verifiable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output_dir = Path(temporary) / "ene-01-output"
            result = energy_runner.run(self.CONFIG_PATH, output_dir)
            self.assertEqual(result["case_id"], "ENE-01")
            self.assertEqual(result["status"], "COMPLETED_REPORT_ONLY")
            manifest = json.loads(
                (output_dir / energy_runner.MANIFEST_NAME).read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["schema_version"], 7)
            self.assertEqual(
                manifest["path_support_sha256"],
                energy_runner._sha256(Path(path_support.__file__).resolve()),
            )
            self.assertIsNone(manifest["normalized_energy_closure_threshold"])
            self.assertTrue(manifest["all_refinements_smooth_unsaturated"])
            self.assertEqual(len(manifest["limiter_stage_reports"]), 4)
            self.assertTrue(all(item["smooth_unsaturated"] for item in manifest["limiter_stage_reports"]))
            self.assertTrue(manifest["reference_trajectory_report"]["smooth_unsaturated"])
            self.assertGreater(
                manifest["energy_residual_noise_floor_J"],
                manifest["energy_residual_noise_budget_report"]["minimum_noise_floor_J"],
            )
            self.assertIn(
                manifest["residual_order_diagnostic"]["gate_status"],
                {
                    "ELIGIBLE", "AT_OR_BELOW_NOISE_FLOOR",
                    "NONSMOOTH_OR_LIMITER_ACTIVE", "SIGN_CROSSING",
                    "NON_MONOTONIC_MAGNITUDE",
                },
            )
            with (output_dir / energy_runner.SUMMARY_NAME).open(
                encoding="utf-8", newline=""
            ) as stream:
                summaries = list(csv.DictReader(stream))
            self.assertEqual(len(summaries), 4)
            self.assertTrue(all(row["status"] == "COMPLETED_REPORT_ONLY" for row in summaries))
            for row in summaries:
                for key in (
                    "delta_stored_energy_J", "terminal_input_work_J", "copper_loss_J",
                    "energy_residual_simpson_J", "energy_residual_trapezoid_J",
                    "normalized_energy_residual",
                ):
                    self.assertTrue(np.isfinite(float(row[key])), key)
                self.assertEqual(float(row["structural_damping_loss_J"]), 0.0)
                self.assertEqual(float(row["axis_friction_loss_J"]), 0.0)
                self.assertEqual(float(row["external_generalized_work_J"]), 0.0)
            verified = energy_runner.verify_archive(output_dir)
            self.assertEqual(verified["status"], "VERIFIED")
            self.assertEqual(verified["recorded_status"], "COMPLETED_REPORT_ONLY")
            self.assertEqual(len(verified["artifacts"]), 4)

    def test_manifest_rejects_invalid_path_support_sha256(self) -> None:
        manifest = self._valid_minimal_manifest()
        manifest["path_support_sha256"] = "not-a-sha256"
        with self.assertRaisesRegex(EnergyClosureError, "path_support_sha256"):
            energy_runner._validate_manifest_contract(manifest)

    def _valid_minimal_manifest(self) -> dict:
        # Reuse the established unit-test manifest fixture and exercise the SHA guard.
        helper = TestIndependentEnergyPowerAccounting()
        return helper._valid_manifest_contract()


class TestSyntheticENE02Integration(unittest.TestCase):
    CONFIG_PATH = (
        Path(__file__).resolve().parent
        / "gantry-joint-drive-ene-02-synthetic-config.json"
    )

    def test_committed_ene02_fixture_has_both_dissipation_mechanisms(self) -> None:
        config = json.loads(self.CONFIG_PATH.read_text(encoding="utf-8"))
        validated = energy_runner._validate(config)
        model = validated["model"]
        self.assertEqual(config["case_id"], "ENE-02")
        self.assertIsNone(validated["threshold"])
        self.assertTrue(np.array_equal(model.mechanical.D0, np.diag([10.0, 2.0, 4.0, 0.5])))
        self.assertTrue(np.all(np.linalg.eigvalsh(model.mechanical.D0) > 0.0))
        self.assertGreater(model.mechanical.axis_viscous_Ns_m, 0.0)
        self.assertGreater(model.mechanical.axis_coulomb_N, 0.0)
        self.assertEqual(validated["external"].tolist(), [0.0] * 5)
        self.assertEqual(
            model.electrical.force_constant_N_per_A,
            model.electrical.back_emf_V_per_m_s,
        )
        self.assertGreaterEqual(
            validated["energy_residual_noise_floor_J"],
            validated["energy_residual_noise_budget_report"]["minimum_noise_floor_J"],
        )

    def test_ene02_four_level_dissipative_energy_balance_and_archive(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output_dir = Path(temporary) / "ene-02-output"
            result = energy_runner.run(self.CONFIG_PATH, output_dir)
            self.assertEqual(result["case_id"], "ENE-02")
            self.assertEqual(result["status"], "COMPLETED_REPORT_ONLY")
            manifest = json.loads(
                (output_dir / energy_runner.MANIFEST_NAME).read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["schema_version"], 7)
            self.assertIsNone(manifest["normalized_energy_closure_threshold"])
            self.assertTrue(manifest["all_refinements_smooth_unsaturated"])
            self.assertEqual(len(manifest["limiter_stage_reports"]), 4)
            self.assertTrue(all(item["smooth_unsaturated"] for item in manifest["limiter_stage_reports"]))
            self.assertEqual(manifest["residual_order_diagnostic"]["gate_status"], "ELIGIBLE")
            with (output_dir / energy_runner.SUMMARY_NAME).open(
                encoding="utf-8", newline=""
            ) as stream:
                summaries = list(csv.DictReader(stream))
            self.assertEqual(len(summaries), 4)
            for row in summaries:
                self.assertEqual(row["status"], "COMPLETED_REPORT_ONLY")
                for field in (
                    "structural_damping_loss_J", "axis_friction_loss_J",
                    "energy_residual_simpson_J", "energy_residual_trapezoid_J",
                    "normalized_energy_residual"
                ):
                    self.assertTrue(np.isfinite(float(row[field])), field)
                self.assertGreater(float(row["structural_damping_loss_J"]), 0.0)
                self.assertGreater(float(row["axis_friction_loss_J"]), 0.0)
                self.assertEqual(float(row["external_generalized_work_J"]), 0.0)
            archived = energy_runner.verify_archive(output_dir)
            self.assertEqual(archived["status"], "VERIFIED")
            self.assertEqual(archived["recorded_status"], "COMPLETED_REPORT_ONLY")
            self.assertEqual(len(archived["artifacts"]), 4)


if __name__ == "__main__":
    unittest.main()
