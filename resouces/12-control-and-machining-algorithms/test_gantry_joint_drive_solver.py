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


def make_model(
    payload_mass: float = 15.0,
    gravity_acceleration_m_s2: np.ndarray | None = None,
) -> GantryJointDriveModel:
    M0 = np.diag([75.0, 12.0, 9.0, 2.0])
    D0 = np.diag([10.0, 2.0, 3.0, 1.0])
    K0 = np.diag([0.0, 120.0, 180.0, 60.0])
    mechanics = MechanicalParameters(
        M0=M0,
        D0=D0,
        K0=K0,
        payload_mass_kg=payload_mass,
        axis_equivalent_mass_kg=8.0,
        gravity_acceleration_m_s2=(
            np.array([0.0, 0.0, -9.80665])
            if gravity_acceleration_m_s2 is None
            else np.asarray(gravity_acceleration_m_s2, dtype=float)
        ),
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
        diagnostics = model.electrical_diagnostics(state, current_command_A=100.0)
        derivative = model.derivative(0.0, model.pack(state), current_command_A=100.0)
        self.assertAlmostEqual(
            diagnostics["current_reference_A"], model.electrical.current_limit_A
        )
        self.assertTrue(diagnostics["voltage_saturated"])
        self.assertAlmostEqual(
            diagnostics["voltage_V"], model.electrical.voltage_max_V
        )
        # Back-calculation anti-windup must pull the PI integrator away
        # from its extreme positive stored value.
        self.assertLess(float(derivative[-1]), 0.0)

    def test_current_reference_limit_does_not_hard_clamp_state_current(self) -> None:
        model = make_model()
        above_limit = 2.0 * model.electrical.current_limit_A
        state = JointState(
            q=np.zeros(4), q_dot=np.zeros(4), s=0.5, s_dot=0.0,
            current_A=above_limit, current_integrator_V=0.0,
        )
        diagnostics = model.electrical_diagnostics(state, current_command_A=100.0)
        derivative = model.derivative(
            0.0, model.pack(state), current_command_A=100.0
        )
        expected_current_rate = (
            diagnostics["voltage_V"] - model.electrical.resistance_ohm * above_limit
        ) / model.electrical.inductance_h

        self.assertAlmostEqual(
            diagnostics["current_reference_A"], model.electrical.current_limit_A
        )
        self.assertGreater(abs(state.current_A), model.electrical.current_limit_A)
        self.assertAlmostEqual(
            diagnostics["current_rate_A_s"], expected_current_rate, places=10
        )
        self.assertAlmostEqual(
            float(derivative[2 * model.nq + 2]), expected_current_rate, places=10
        )
        self.assertLess(expected_current_rate, 0.0)

    def test_zero_input_rest_state_has_zero_acceleration_without_gravity(self) -> None:
        model = make_model(
            payload_mass=0.0,
            gravity_acceleration_m_s2=np.zeros(3),
        )
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

    def test_rk4_stage_times_match_returned_grid_with_rounded_step_count(self) -> None:
        model = make_model(payload_mass=0.0)
        initial = JointState(
            q=np.zeros(4), q_dot=np.zeros(4), s=0.5, s_dot=0.0,
            current_A=0.0, current_integrator_V=0.0,
        )
        stage_times: list[float] = []
        duration = 1.0
        requested_step = 0.10000000005

        times, _ = model.simulate(
            initial,
            duration_s=duration,
            step_s=requested_step,
            current_command=lambda time_s, _state: stage_times.append(time_s) or 0.0,
        )

        # Per RK4 step, evaluations are k1, k2, k3, k4. The k4
        # timestamp must coincide with the next returned output-grid point.
        for index in range(len(times) - 1):
            k4_time = stage_times[4 * index + 3]
            next_step_time = stage_times[4 * (index + 1)]
            self.assertAlmostEqual(
                k4_time, next_step_time, delta=2.0e-15
            )
        self.assertEqual(len(times), 11)

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

    def test_parameter_arrays_are_snapshotted_and_read_only(self) -> None:
        source_M0 = np.diag([75.0, 12.0, 9.0, 2.0])
        source_D0 = np.diag([10.0, 2.0, 3.0, 1.0])
        source_K0 = np.diag([0.0, 120.0, 180.0, 60.0])
        source_gravity = np.array([0.0, 0.0, -9.80665])
        source_actuator_coefficients = np.zeros(4)
        mechanics = MechanicalParameters(
            M0=source_M0,
            D0=source_D0,
            K0=source_K0,
            payload_mass_kg=0.0,
            axis_equivalent_mass_kg=8.0,
            gravity_acceleration_m_s2=source_gravity,
        )
        actuator = ActuatorKinematics(
            q_coefficients=source_actuator_coefficients,
            s_coefficient=1.0,
        )
        base = make_model()
        model = GantryJointDriveModel(
            base.geometry, mechanics, base.electrical, actuator
        )

        source_M0[0, 0] = -1.0
        source_D0[0, 0] = -1.0
        source_K0[1, 1] = -1.0
        source_gravity[2] = 0.0
        source_actuator_coefficients[0] = 1.0

        self.assertAlmostEqual(float(model.mechanical.M0[0, 0]), 75.0)
        self.assertAlmostEqual(float(model.mechanical.D0[0, 0]), 10.0)
        self.assertAlmostEqual(float(model.mechanical.K0[1, 1]), 120.0)
        self.assertAlmostEqual(
            float(model.mechanical.gravity_acceleration_m_s2[2]), -9.80665
        )
        self.assertAlmostEqual(float(model.actuator.q_coefficients[0]), 0.0)
        protected_arrays = (
            model.mechanical.M0,
            model.mechanical.D0,
            model.mechanical.K0,
            model.mechanical.gravity_acceleration_m_s2,
            model.actuator.q_coefficients,
        )
        for values in protected_arrays:
            with self.subTest(shape=values.shape):
                with self.assertRaises(ValueError):
                    values.setflags(write=True)
        with self.assertRaises(ValueError):
            model.mechanical.M0[0, 0] = 1.0
        with self.assertRaises(ValueError):
            model.actuator.q_coefficients[0] = 1.0

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


    def test_rejects_non_finite_current_command(self) -> None:
        model = make_model()
        state = JointState(
            q=np.zeros(4), q_dot=np.zeros(4), s=0.5, s_dot=0.0,
            current_A=0.0, current_integrator_V=0.0,
        )
        with self.assertRaisesRegex(ValueError, "current_command_A must be finite"):
            model.derivative(0.0, model.pack(state), current_command_A=float("nan"))

    def test_electrical_diagnostics_rejects_non_finite_commands(self) -> None:
        model = make_model()
        state = JointState(
            q=np.zeros(4), q_dot=np.zeros(4), s=0.5, s_dot=0.0,
            current_A=0.0, current_integrator_V=0.0,
        )
        for command in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(command=command):
                with self.assertRaisesRegex(ValueError, "current_command_A must be finite"):
                    model.electrical_diagnostics(state, current_command_A=command)

    def test_electrical_diagnostics_rejects_non_finite_state(self) -> None:
        model = make_model()
        state = JointState(
            q=np.array([0.0, 0.0, float("nan"), 0.0]),
            q_dot=np.zeros(4),
            s=0.5,
            s_dot=0.0,
            current_A=0.0,
            current_integrator_V=0.0,
        )
        with self.assertRaisesRegex(ValueError, "state values must all be finite"):
            model.electrical_diagnostics(state, current_command_A=0.0)

    def test_rejects_non_finite_external_generalized_force(self) -> None:
        model = make_model()
        state = JointState(
            q=np.zeros(4), q_dot=np.zeros(4), s=0.5, s_dot=0.0,
            current_A=0.0, current_integrator_V=0.0,
        )
        force = np.zeros(model.nq + 1)
        force[-1] = float("inf")
        with self.assertRaisesRegex(ValueError, "external_generalized_force"):
            model.derivative(
                0.0, model.pack(state), current_command_A=0.0,
                external_generalized_force=force,
            )


    def test_simulation_callbacks_receive_independent_stage_state_snapshots(self) -> None:
        model = make_model(payload_mass=0.0)
        initial = JointState(
            q=np.array([0.125, 0.0, 0.0, 0.0]),
            q_dot=np.zeros(4),
            s=0.5,
            s_dot=0.0,
            current_A=0.0,
            current_integrator_V=0.0,
        )
        external_force_observations: list[float] = []

        def current_command(_time_s: float, state: JointState) -> float:
            state.q[0] = 123.0
            return 0.0

        def external_force(_time_s: float, state: JointState) -> np.ndarray:
            external_force_observations.append(float(state.q[0]))
            state.q[0] = -456.0
            return np.zeros(model.nq + 1, dtype=float)

        _, states = model.simulate(
            initial,
            duration_s=0.002,
            step_s=0.001,
            current_command=current_command,
            external_force=external_force,
        )

        self.assertEqual(len(external_force_observations), 8)
        for observed_q0 in external_force_observations:
            self.assertAlmostEqual(observed_q0, initial.q[0], places=12)
        self.assertTrue(
            np.allclose(states[:, 0], initial.q[0], atol=1e-12, rtol=0.0)
        )


    def test_prescribed_path_partition_matches_free_dynamics_at_zero_reaction(self) -> None:
        model = make_model(payload_mass=15.0)
        state = JointState(
            q=np.array([1.0e-4, -2.0e-4, 3.0e-5, 4.0e-4]),
            q_dot=np.array([0.012, -0.006, 0.002, -0.001]),
            s=0.61,
            s_dot=0.13,
            current_A=0.35,
            current_integrator_V=0.2,
        )
        command = 0.8
        external = np.array([0.2, -0.1, 0.05, 0.03, 0.4])
        free_derivative = model.derivative(
            0.17, model.pack(state), command, external
        )
        n = model.nq
        reduced = np.concatenate((
            state.q, state.q_dot, [state.current_A, state.current_integrator_V]
        ))
        constrained_derivative, reaction = model.prescribed_path_derivative(
            0.17, reduced, command,
            state.s, state.s_dot, float(free_derivative[2*n+1]), external
        )
        free_reduced_derivative = np.concatenate((
            free_derivative[:2*n], free_derivative[2*n+2:]
        ))
        self.assertTrue(np.allclose(
            constrained_derivative, free_reduced_derivative,
            atol=2e-12, rtol=2e-12
        ))
        self.assertAlmostEqual(reaction, 0.0, delta=2e-11)

    def test_prescribed_path_constraint_force_sign_for_rest_acceleration(self) -> None:
        model = make_model(
            payload_mass=0.0,
            gravity_acceleration_m_s2=np.zeros(3),
        )
        state = JointState(
            q=np.zeros(4), q_dot=np.zeros(4), s=0.5, s_dot=0.0,
            current_A=0.0, current_integrator_V=0.0,
        )
        reduced = np.concatenate((
            state.q, state.q_dot, [state.current_A, state.current_integrator_V]
        ))
        derivative, reaction = model.prescribed_path_derivative(
            0.0, reduced, 0.0, 0.5, 0.0, 0.5
        )
        self.assertTrue(np.all(np.isfinite(derivative)))
        self.assertAlmostEqual(reaction, 8.0 * 0.5, places=12)

    def test_simulate_prescribed_path_tracks_reference_position_and_velocity(self) -> None:
        model = make_model(payload_mass=0.0)
        initial = JointState(
            q=np.zeros(4), q_dot=np.zeros(4), s=0.5, s_dot=0.2,
            current_A=0.0, current_integrator_V=0.0,
        )

        def path(time_s: float) -> tuple[float, float, float]:
            acceleration = 0.4
            return (
                0.5 + 0.2*time_s + 0.5*acceleration*time_s**2,
                0.2 + acceleration*time_s,
                acceleration,
            )

        times, states, reactions = model.simulate_prescribed_path(
            initial, duration_s=0.01, step_s=0.001,
            prescribed_path=path,
            current_command=lambda _time, _state: 0.0,
        )
        expected_s = 0.5 + 0.2*times + 0.5*0.4*times**2
        expected_s_dot = 0.2 + 0.4*times
        self.assertTrue(np.allclose(states[:, 2*model.nq], expected_s, atol=1e-14))
        self.assertTrue(np.allclose(states[:, 2*model.nq+1], expected_s_dot, atol=1e-14))
        self.assertTrue(np.all(np.isfinite(reactions)))
        self.assertEqual(reactions.shape, times.shape)

    def test_simulate_prescribed_path_rejects_initial_path_mismatch(self) -> None:
        model = make_model()
        initial = JointState(
            q=np.zeros(4), q_dot=np.zeros(4), s=0.5, s_dot=0.0,
            current_A=0.0, current_integrator_V=0.0,
        )
        with self.assertRaisesRegex(ValueError, "must match prescribed_path"):
            model.simulate_prescribed_path(
                initial, duration_s=0.01, step_s=0.001,
                prescribed_path=lambda _time: (0.6, 0.0, 0.0),
                current_command=lambda _time, _state: 0.0,
            )

    def test_simulate_prescribed_path_rejects_non_finite_path_values(self) -> None:
        model = make_model()
        initial = JointState(
            q=np.zeros(4), q_dot=np.zeros(4), s=0.5, s_dot=0.0,
            current_A=0.0, current_integrator_V=0.0,
        )
        with self.assertRaisesRegex(ValueError, "three finite values"):
            model.simulate_prescribed_path(
                initial, duration_s=0.01, step_s=0.001,
                prescribed_path=lambda _time: (0.5, 0.0, float("nan")),
                current_command=lambda _time, _state: 0.0,
            )

    def test_prescribed_path_callbacks_receive_independent_state_snapshots(self) -> None:
        model = make_model(payload_mass=0.0)
        initial = JointState(
            q=np.array([0.125, 0.0, 0.0, 0.0]),
            q_dot=np.zeros(4), s=0.5, s_dot=0.0,
            current_A=0.0, current_integrator_V=0.0,
        )
        observed_q0: list[float] = []

        def current_command(_time_s: float, state: JointState) -> float:
            state.q[0] = 123.0
            return 0.0

        def external_force(_time_s: float, state: JointState) -> np.ndarray:
            observed_q0.append(float(state.q[0]))
            state.q[0] = -456.0
            return np.zeros(model.nq + 1, dtype=float)

        _, states, _ = model.simulate_prescribed_path(
            initial, duration_s=0.002, step_s=0.001,
            prescribed_path=lambda _time: (0.5, 0.0, 0.0),
            current_command=current_command,
            external_force=external_force,
        )
        self.assertEqual(len(observed_q0), 9)
        for value in observed_q0:
            self.assertAlmostEqual(value, initial.q[0], places=12)
        self.assertTrue(np.allclose(
            states[:, 0], initial.q[0], atol=1e-12, rtol=0.0
        ))

if __name__ == "__main__":
    unittest.main()
