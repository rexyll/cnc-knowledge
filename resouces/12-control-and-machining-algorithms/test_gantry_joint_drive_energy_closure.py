"""Resource tests for the independent ENE energy-closure accounting.

These tests are intentionally not executed by the repository Knowledge Quality CI.
"""
from __future__ import annotations

import unittest

import numpy as np

from gantry_joint_drive_solver import (
    ActuatorKinematics, CurrentLoopParameters, GantryJointDriveModel,
    JointState, MechanicalParameters, SinusoidalBeamGeometry,
)
from gantry_joint_drive_energy_closure import (
    EnergyClosureError, _power_sample, _validate_case_contract,
    _validate_manifest_contract, _read_verified_csv,
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

    def _valid_manifest_contract(self) -> dict:
        return {
            "schema_version": 1, "case_id": "ENE-01", "status": "COMPLETED_REPORT_ONLY",
            "numerical_results_present": True, "resource_tests_executed": False,
            "parameter_source": "synthetic test fixture", "source_documents_or_measurement_ids": [],
            "started_at_utc": "2026-01-01T00:00:00+00:00",
            "completed_at_utc": "2026-01-01T00:00:01+00:00",
            "duration_s": 1.0, "base_step_s": 0.25,
            "energy_normalization_scale_J": 1.0, "energy_normalization_floor_J": 1.0,
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
        }

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


if __name__ == "__main__":
    unittest.main()
