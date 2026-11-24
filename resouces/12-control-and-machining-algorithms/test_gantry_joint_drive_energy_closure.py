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
from gantry_joint_drive_energy_closure import _power_sample


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
