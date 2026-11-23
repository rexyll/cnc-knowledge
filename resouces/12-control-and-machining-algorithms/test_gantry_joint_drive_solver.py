"""Unit tests for the joint gantry / axis / current-loop resource module.

Run from the repository root:
python -m unittest discover -s resouces/12-control-and-machining-algorithms -p 'test_gantry_joint_drive_solver.py' -v
These tests are authored but are not executed by the knowledge-structure CI workflow.
"""
from __future__ import annotations

import unittest

import numpy as np

from gantry_joint_drive_solver import (
    ActuatorKinematics,
    CurrentLoopParameters,
    GantryJointDriveModel,
    JointState,
    MechanicalParameters,
    SinusoidalBeamGeometry,
)


def make_model(payload_mass: float = 15.0) -> GantryJointDriveModel:
    M0 = np.diag([75.0, 12.0, 9.0, 2.0])
    D0 = np.diag([10.0, 2.0, 3.0, 1.0])
    K0 = np.diag([0.0, 120.0, 180.0, 60.0])
    mechanics = MechanicalParameters(
        M0=M0,
        D0=D0,
        K0=K0,
        payload_mass_kg=payload_mass,
        axis_equivalent_mass_kg=8.0,
        gravity_acceleration_m_s2=np.array([0.0, 0.0, -9.80665]),
        axis_viscous_Ns_m=2.0,
        axis_coulomb_N=1.0,
        friction_smoothing_speed_m_s=0.01,
    )
    drive = CurrentLoopParameters(
        resistance_ohm=1.5,
        inductance_h=0.02,
        back_emf_V_per_m_s=4.0,
        force_constant_N_per_A=4.0,
        current_limit_A=8.0,
        voltage_min_V=-48.0,
        voltage_max_V=48.0,
        kp_V_per_A=3.0,
        ki_V_per_A_s=20.0,
        antiwindup_gain_per_s=5.0,
    )
    actuator = ActuatorKinematics(
        q_coefficients=np.array([0.0, 0.0, 0.0, 0.0]),
        s_coefficient=1.0,
    )
    return GantryJointDriveModel(
        SinusoidalBeamGeometry(span_m=1.6),
        mechanics,
        drive,
        actuator,
    )


class TestGantryJointDriveSolver(unittest.TestCase):
    def test_augmented_mass_matrix_is_symmetric_positive_definite(self) -> None:
        model = make_model()
        q = np.array([1e-4, 2e-4, -3e-5, 5e-4])
        mass = model.joint_mass_matrix(q, 0.72)
        self.assertTrue(np.allclose(mass, mass.T, atol=1e-12, rtol=1e-12))
        self.assertGreater(float(np.min(np.linalg.eigvalsh(mass))), 0.0)

    def test_zero_payload_reduces_to_block_diagonal_base_mass(self) -> None:
        model = make_model(payload_mass=0.0)
        mass = model.joint_mass_matrix(np.zeros(4), 0.8)
        expected = np.diag([75.0, 12.0, 9.0, 2.0, 8.0])
        self.assertTrue(np.allclose(mass, expected, atol=1e-12, rtol=1e-12))

    def test_actuator_virtual_work_identity(self) -> None:
        model = make_model()
        state = JointState(
            q=np.array([1e-4, 2e-4, 0.0, 1e-4]),
            q_dot=np.array([0.01, -0.02, 0.003, 0.001]),
            s=0.7,
            s_dot=0.15,
            current_A=2.0,
            current_integrator_V=0.0,
        )
        force = model.electrical.force_constant_N_per_A * state.current_A
        generalized = model.actuator.jacobian() * force
        zdot = np.concatenate((state.q_dot, [state.s_dot]))
        actuator_power = force * model.actuator_relative_velocity(state.q_dot, state.s_dot)
        self.assertAlmostEqual(float(generalized @ zdot), actuator_power, places=12)

    def test_zero_speed_electrical_decay_matches_rl_limit(self) -> None:
        model = make_model()
        state = JointState(
            q=np.zeros(4), q_dot=np.zeros(4), s=0.5, s_dot=0.0,
            current_A=2.0, current_integrator_V=0.0,
        )
        derivative = model.derivative(0.0, model.pack(state), current_command_A=0.0)
        expected = -model.electrical.resistance_ohm * state.current_A / model.electrical.inductance_h
        self.assertAlmostEqual(float(derivative[2*model.nq + 2]), expected, places=12)

    def test_current_reference_and_voltage_limits_are_enforced(self) -> None:
        model = make_model()
        state = JointState(
            q=np.zeros(4), q_dot=np.zeros(4), s=0.5, s_dot=0.0,
            current_A=0.0, current_integrator_V=1.0e6,
        )
        derivative = model.derivative(0.0, model.pack(state), current_command_A=100.0)
        # The saturated voltage and back-calculation anti-windup must pull
        # the PI integrator away from its extreme positive stored value.
        self.assertLess(float(derivative[-1]), 0.0)

    def test_zero_input_rest_state_has_zero_acceleration_without_gravity(self) -> None:
        model = make_model(payload_mass=0.0)
        model.mechanical.gravity_acceleration_m_s2[:] = 0.0
        state = JointState(
            q=np.zeros(4), q_dot=np.zeros(4), s=0.5, s_dot=0.0,
            current_A=0.0, current_integrator_V=0.0,
        )
        derivative = model.derivative(0.0, model.pack(state), current_command_A=0.0)
        n = model.nq
        self.assertTrue(np.allclose(derivative[n:2*n], 0.0, atol=1e-12))
        self.assertAlmostEqual(float(derivative[2*n+1]), 0.0, places=12)


    def test_electromechanical_energy_balance_with_matched_si_constants(self) -> None:
        base = make_model(payload_mass=5.0)
        mechanics = MechanicalParameters(
            M0=base.mechanical.M0.copy(),
            D0=np.zeros_like(base.mechanical.D0),
            K0=base.mechanical.K0.copy(),
            payload_mass_kg=5.0,
            axis_equivalent_mass_kg=base.mechanical.axis_equivalent_mass_kg,
            gravity_acceleration_m_s2=np.zeros(3),
            axis_viscous_Ns_m=0.0,
            axis_coulomb_N=0.0,
            friction_smoothing_speed_m_s=0.01,
        )
        # Equality of Kf and Ke is the SI reciprocity condition for this
        # idealized translational actuator port.
        electrical = CurrentLoopParameters(
            resistance_ohm=1.5,
            inductance_h=0.02,
            back_emf_V_per_m_s=4.0,
            force_constant_N_per_A=4.0,
            current_limit_A=8.0,
            voltage_min_V=-48.0,
            voltage_max_V=48.0,
            kp_V_per_A=3.0,
            ki_V_per_A_s=20.0,
            antiwindup_gain_per_s=0.0,
        )
        actuator = ActuatorKinematics(
            q_coefficients=np.array([1.0, 0.0, 0.0, 0.0]),
            s_coefficient=1.0,
        )
        model = GantryJointDriveModel(
            base.geometry, mechanics, electrical, actuator
        )
        initial = JointState(
            q=np.array([1e-4, 2e-4, -1e-5, 1e-4]),
            q_dot=np.array([0.02, -0.01, 0.003, 0.001]),
            s=0.7,
            s_dot=0.01,
            current_A=0.25,
            current_integrator_V=0.0,
        )
        dt = 1.0e-6
        energy_before = model.total_stored_energy(initial)
        _, states = model.simulate(
            initial,
            duration_s=dt,
            step_s=dt,
            current_command=lambda _time, state: state.current_A,
        )
        final = model.unpack(states[-1])
        observed_rate = (
            model.total_stored_energy(final) - energy_before
        ) / dt
        expected_rate = -electrical.resistance_ohm * initial.current_A**2
        self.assertAlmostEqual(
            observed_rate, expected_rate,
            delta=max(1.0e-5, abs(expected_rate) * 1.0e-3),
        )

    def test_path_coordinate_is_integrated_as_a_free_state(self) -> None:
        base = make_model(payload_mass=0.0)
        mechanics = MechanicalParameters(
            M0=base.mechanical.M0.copy(),
            D0=base.mechanical.D0.copy(),
            K0=base.mechanical.K0.copy(),
            payload_mass_kg=0.0,
            axis_equivalent_mass_kg=8.0,
            gravity_acceleration_m_s2=np.zeros(3),
            axis_viscous_Ns_m=0.0,
            axis_coulomb_N=0.0,
            friction_smoothing_speed_m_s=0.01,
        )
        actuator = ActuatorKinematics(
            q_coefficients=np.zeros(4), s_coefficient=0.0
        )
        model = GantryJointDriveModel(
            base.geometry, mechanics, base.electrical, actuator
        )
        initial = JointState(
            q=np.zeros(4), q_dot=np.zeros(4), s=0.5, s_dot=0.2,
            current_A=0.0, current_integrator_V=0.0,
        )
        duration = 0.01
        _, states = model.simulate(
            initial, duration_s=duration, step_s=0.001,
            current_command=lambda _time, _state: 0.0,
        )
        final = model.unpack(states[-1])
        self.assertAlmostEqual(
            final.s - initial.s, initial.s_dot * duration, places=10
        )



    def test_rejects_geometry_coordinate_dimension_mismatch_at_construction(self) -> None:
        base = make_model()
        mechanics = MechanicalParameters(
            M0=np.eye(3),
            D0=np.zeros((3, 3)),
            K0=np.zeros((3, 3)),
            payload_mass_kg=0.0,
            axis_equivalent_mass_kg=1.0,
            gravity_acceleration_m_s2=np.zeros(3),
        )
        actuator = ActuatorKinematics(q_coefficients=np.zeros(3))
        with self.assertRaisesRegex(ValueError, "exactly four generalized coordinates"):
            GantryJointDriveModel(
                base.geometry, mechanics, base.electrical, actuator
            )

    def test_rejects_non_finite_initial_state(self) -> None:
        model = make_model()
        state = JointState(
            q=np.array([0.0, np.nan, 0.0, 0.0]),
            q_dot=np.zeros(4),
            s=0.5,
            s_dot=0.0,
            current_A=0.0,
            current_integrator_V=0.0,
        )
        with self.assertRaisesRegex(ValueError, "finite"):
            model.pack(state)


if __name__ == "__main__":
    unittest.main()
