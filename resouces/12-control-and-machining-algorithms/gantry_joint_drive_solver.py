#!/usr/bin/env python3
"""Joint flexible-gantry / moving-axis / current-loop model.

Python 3.10+ and NumPy are required. Parameters are supplied by the caller;
there are deliberately no default machine ratings or vendor-specific values.
This module defines a low-order engineering model, not a machine digital twin.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]


@dataclass(frozen=True)
class SinusoidalBeamGeometry:
    """Four-coordinate assumed-mode geometry used by the CH12 example.

    q = [common_translation_m, yaw_rad, bending_m, torsion_rad].
    The sinusoidal bending/torsion shapes and offsets are illustrative.
    """

    span_m: float
    torsion_x_offset_m: float = 0.12
    torsion_z_offset_m: float = 0.18

    def evaluate(
        self, q: FloatArray, s: float
    ) -> tuple[FloatArray, FloatArray, FloatArray, FloatArray,
               FloatArray, FloatArray]:
        if q.shape != (4,):
            raise ValueError("SinusoidalBeamGeometry requires exactly four q coordinates")
        if not np.all(np.isfinite([self.span_m, self.torsion_x_offset_m, self.torsion_z_offset_m])):
            raise ValueError("geometry parameters must be finite")
        if self.span_m <= 0.0:
            raise ValueError("span_m must be positive")
        if not np.isfinite(s):
            raise ValueError("path coordinate s must be finite")

        k = np.pi / self.span_m
        shape = np.sin(k * s)
        dshape = k * np.cos(k * s)
        ddshape = -(k * k) * shape
        tx = self.torsion_x_offset_m
        tz = self.torsion_z_offset_m

        r0 = np.array([0.0, s, 0.0], dtype=float)
        r0_s = np.array([0.0, 1.0, 0.0], dtype=float)
        r0_ss = np.zeros(3, dtype=float)

        phi = np.array([
            [1.0, s - self.span_m / 2.0, shape, tx * shape],
            [0.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, tz * shape],
        ], dtype=float)
        phi_s = np.array([
            [0.0, 1.0, dshape, tx * dshape],
            [0.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, tz * dshape],
        ], dtype=float)
        phi_ss = np.array([
            [0.0, 0.0, ddshape, tx * ddshape],
            [0.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, tz * ddshape],
        ], dtype=float)
        return r0, phi, phi_s, phi_ss, r0_s, r0_ss


@dataclass(frozen=True)
class MechanicalParameters:
    """Mechanical parameters in the declared generalized-coordinate units."""

    M0: FloatArray
    D0: FloatArray
    K0: FloatArray
    payload_mass_kg: float
    axis_equivalent_mass_kg: float
    gravity_acceleration_m_s2: FloatArray
    axis_viscous_Ns_m: float = 0.0
    axis_coulomb_N: float = 0.0
    friction_smoothing_speed_m_s: float = 1.0e-3


@dataclass(frozen=True)
class CurrentLoopParameters:
    """Single-axis equivalent RL current loop.

    Force and back-EMF constants must use mutually consistent SI conventions.
    The model is not a complete PMSM dq model or inverter switching model.
    """

    resistance_ohm: float
    inductance_h: float
    back_emf_V_per_m_s: float
    force_constant_N_per_A: float
    current_limit_A: float
    voltage_min_V: float
    voltage_max_V: float
    kp_V_per_A: float
    ki_V_per_A_s: float
    antiwindup_gain_per_s: float = 0.0


@dataclass(frozen=True)
class ActuatorKinematics:
    """Affine actuator relative displacement ell_a = c_q @ q + c_s * s + c0."""

    q_coefficients: FloatArray
    s_coefficient: float = 1.0
    offset_m: float = 0.0

    def jacobian(self) -> FloatArray:
        return np.concatenate((self.q_coefficients, [self.s_coefficient])).astype(float)

    def length(self, q: FloatArray, s: float) -> float:
        return float(self.q_coefficients @ q + self.s_coefficient * s + self.offset_m)


@dataclass(frozen=True)
class JointState:
    q: FloatArray
    q_dot: FloatArray
    s: float
    s_dot: float
    current_A: float
    current_integrator_V: float

    def copy(self) -> "JointState":
        return JointState(
            self.q.copy(), self.q_dot.copy(), float(self.s), float(self.s_dot),
            float(self.current_A), float(self.current_integrator_V)
        )


CurrentCommand = Callable[[float, JointState], float]
ExternalForce = Callable[[float, JointState], FloatArray]


class GantryJointDriveModel:
    """Coupled generalized mechanics and a continuous PI current-loop state.

    State ordering is x = [q, q_dot, s, s_dot, i, x_i]. The path coordinate s
    is free; it is not a prescribed trajectory. Hard stops, contact loss,
    backlash, flexible screw modes, sampled-data control and inverter PWM are
    intentionally outside this first implementation.
    """

    def __init__(
        self,
        geometry: SinusoidalBeamGeometry,
        mechanical: MechanicalParameters,
        electrical: CurrentLoopParameters,
        actuator: ActuatorKinematics,
    ) -> None:
        self.geometry = geometry
        self.mechanical = mechanical
        self.electrical = electrical
        self.actuator = actuator
        mass_shape = np.asarray(mechanical.M0).shape
        if len(mass_shape) != 2 or mass_shape[0] != mass_shape[1] or mass_shape[0] < 1:
            raise ValueError("M0 must be a non-empty square matrix")
        self.nq = int(mass_shape[0])
        if self.nq != 4:
            raise ValueError(
                "SinusoidalBeamGeometry requires exactly four generalized coordinates"
            )
        self._validate_parameters()

    def _validate_parameters(self) -> None:
        m = self.mechanical
        e = self.electrical
        n = self.nq
        if n < 1 or np.asarray(m.M0).shape != (n, n):
            raise ValueError("M0 must be a non-empty square matrix")
        for name, matrix in (("D0", m.D0), ("K0", m.K0)):
            if np.asarray(matrix).shape != (n, n):
                raise ValueError(f"{name} must have the same shape as M0")
            if not np.allclose(matrix, np.asarray(matrix).T, atol=1e-10, rtol=1e-10):
                raise ValueError(f"{name} must be symmetric")
        numeric_arrays = {
            "M0": np.asarray(m.M0, dtype=float),
            "D0": np.asarray(m.D0, dtype=float),
            "K0": np.asarray(m.K0, dtype=float),
            "gravity_acceleration_m_s2": np.asarray(m.gravity_acceleration_m_s2, dtype=float),
            "actuator q_coefficients": np.asarray(self.actuator.q_coefficients, dtype=float),
        }
        for name, values in numeric_arrays.items():
            if not np.all(np.isfinite(values)):
                raise ValueError(f"{name} must contain only finite values")
        if not np.allclose(m.M0, np.asarray(m.M0).T, atol=1e-10, rtol=1e-10):
            raise ValueError("M0 must be symmetric")
        if np.min(np.linalg.eigvalsh(m.M0)) <= 0.0:
            raise ValueError("M0 must be positive definite")
        if np.min(np.linalg.eigvalsh(m.D0)) < -1e-10:
            raise ValueError("D0 must be positive semidefinite")
        if np.min(np.linalg.eigvalsh(m.K0)) < -1e-10:
            raise ValueError("K0 must be positive semidefinite")
        if np.asarray(m.gravity_acceleration_m_s2).shape != (3,):
            raise ValueError("gravity_acceleration_m_s2 must be a 3-vector")
        if self.actuator.q_coefficients.shape != (n,):
            raise ValueError("actuator q_coefficients must have one entry per q coordinate")
        mechanical_scalars = np.array([
            m.payload_mass_kg, m.axis_equivalent_mass_kg,
            m.axis_viscous_Ns_m, m.axis_coulomb_N,
            m.friction_smoothing_speed_m_s,
        ], dtype=float)
        electrical_scalars = np.array([
            e.resistance_ohm, e.inductance_h, e.back_emf_V_per_m_s,
            e.force_constant_N_per_A, e.current_limit_A, e.voltage_min_V,
            e.voltage_max_V, e.kp_V_per_A, e.ki_V_per_A_s,
            e.antiwindup_gain_per_s,
            self.actuator.s_coefficient, self.actuator.offset_m,
        ], dtype=float)
        if not np.all(np.isfinite(mechanical_scalars)):
            raise ValueError("mechanical scalar parameters must be finite")
        if not np.all(np.isfinite(electrical_scalars)):
            raise ValueError("electrical and actuator scalar parameters must be finite")
        if m.payload_mass_kg < 0.0 or m.axis_equivalent_mass_kg <= 0.0:
            raise ValueError("payload mass must be nonnegative and axis equivalent mass positive")
        if m.axis_viscous_Ns_m < 0.0 or m.axis_coulomb_N < 0.0:
            raise ValueError("axis friction coefficients must be nonnegative")
        if m.friction_smoothing_speed_m_s <= 0.0:
            raise ValueError("friction smoothing speed must be positive")
        if e.resistance_ohm <= 0.0 or e.inductance_h <= 0.0:
            raise ValueError("electrical resistance and inductance must be positive")
        if e.current_limit_A <= 0.0 or e.voltage_min_V >= e.voltage_max_V:
            raise ValueError("invalid current or voltage limits")
        if e.force_constant_N_per_A <= 0.0 or e.back_emf_V_per_m_s < 0.0:
            raise ValueError("force constant must be positive and back-EMF constant nonnegative")
        if e.kp_V_per_A < 0.0 or e.ki_V_per_A_s < 0.0 or e.antiwindup_gain_per_s < 0.0:
            raise ValueError("PI and anti-windup gains must be nonnegative")

    def pack(self, state: JointState) -> FloatArray:
        if state.q.shape != (self.nq,) or state.q_dot.shape != (self.nq,):
            raise ValueError("state q and q_dot dimensions do not match M0")
        packed = np.concatenate((
            state.q, state.q_dot,
            np.array([state.s, state.s_dot, state.current_A, state.current_integrator_V])
        )).astype(float)
        if not np.all(np.isfinite(packed)):
            raise ValueError("state values must all be finite")
        return packed

    def unpack(self, vector: FloatArray) -> JointState:
        y = np.asarray(vector, dtype=float)
        if y.shape != (2 * self.nq + 4,):
            raise ValueError("state vector has an incorrect length")
        n = self.nq
        return JointState(y[:n].copy(), y[n:2*n].copy(),
                          float(y[2*n]), float(y[2*n+1]),
                          float(y[2*n+2]), float(y[2*n+3]))

    def geometry_terms(self, q: FloatArray, s: float) -> dict[str, FloatArray]:
        r0, phi, phi_s, phi_ss, r0_s, r0_ss = self.geometry.evaluate(q, s)
        r = r0 + phi @ q
        r_s = r0_s + phi_s @ q
        r_ss = r0_ss + phi_ss @ q
        return {
            "r": r, "Phi": phi, "Phi_s": phi_s, "Phi_ss": phi_ss,
            "r_s": r_s, "r_ss": r_ss,
        }

    def joint_mass_matrix(self, q: FloatArray, s: float) -> FloatArray:
        """Return diag(M0, m_s0) + m_p * J.T @ J, J=[Phi, r_s]."""
        g = self.geometry_terms(q, s)
        J = np.column_stack((g["Phi"], g["r_s"]))
        base = np.zeros((self.nq + 1, self.nq + 1), dtype=float)
        base[:self.nq, :self.nq] = self.mechanical.M0
        base[-1, -1] = self.mechanical.axis_equivalent_mass_kg
        return base + self.mechanical.payload_mass_kg * (J.T @ J)

    def actuator_relative_velocity(self, q_dot: FloatArray, s_dot: float) -> float:
        velocity = np.concatenate((q_dot, [s_dot]))
        return float(self.actuator.jacobian() @ velocity)

    def mechanical_energy(self, state: JointState) -> tuple[float, float]:
        """Return (kinetic, potential) energy for the stated low-order model."""
        g = self.geometry_terms(state.q, state.s)
        point_velocity = g["Phi"] @ state.q_dot + g["r_s"] * state.s_dot
        m = self.mechanical
        kinetic = (
            0.5 * state.q_dot @ m.M0 @ state.q_dot
            + 0.5 * m.axis_equivalent_mass_kg * state.s_dot**2
            + 0.5 * m.payload_mass_kg * (point_velocity @ point_velocity)
        )
        potential = (
            0.5 * state.q @ m.K0 @ state.q
            - m.payload_mass_kg
            * (m.gravity_acceleration_m_s2 @ g["r"])
        )
        return float(kinetic), float(potential)

    def total_stored_energy(self, state: JointState) -> float:
        """Mechanical energy plus the equivalent inductor magnetic energy."""
        kinetic, potential = self.mechanical_energy(state)
        magnetic = 0.5 * self.electrical.inductance_h * state.current_A**2
        return float(kinetic + potential + magnetic)

    def electrical_diagnostics(self, state: JointState, current_command_A: float) -> dict[str, float | bool]:
        e = self.electrical
        i_ref = float(np.clip(current_command_A, -e.current_limit_A, e.current_limit_A))
        error = i_ref - state.current_A
        raw_voltage = e.kp_V_per_A * error + state.current_integrator_V
        voltage = float(np.clip(raw_voltage, e.voltage_min_V, e.voltage_max_V))
        ell_dot = self.actuator_relative_velocity(state.q_dot, state.s_dot)
        current_rate = (
            voltage - e.resistance_ohm * state.current_A
            - e.back_emf_V_per_m_s * ell_dot
        ) / e.inductance_h
        integrator_rate = (
            e.ki_V_per_A_s * error
            + e.antiwindup_gain_per_s * (voltage - raw_voltage)
        )
        return {
            "current_reference_A": i_ref,
            "current_error_A": error,
            "raw_voltage_V": raw_voltage,
            "voltage_V": voltage,
            "voltage_saturated": not np.isclose(voltage, raw_voltage, rtol=0.0, atol=1e-12),
            "actuator_relative_velocity_m_s": ell_dot,
            "current_rate_A_s": current_rate,
            "integrator_rate_V_s": integrator_rate,
        }

    def derivative(
        self,
        time_s: float,
        state_vector: FloatArray,
        current_command_A: float,
        external_generalized_force: FloatArray | None = None,
    ) -> FloatArray:
        state = self.unpack(state_vector)
        m = self.mechanical
        e = self.electrical
        g = self.geometry_terms(state.q, state.s)
        phi = g["Phi"]
        phi_s = g["Phi_s"]
        r_s = g["r_s"]
        r_ss = g["r_ss"]

        # Particle acceleration excluding J @ z_ddot:
        # 2*Phi_s*q_dot*s_dot + r_ss*s_dot^2.
        transport = (
            2.0 * (phi_s @ state.q_dot) * state.s_dot
            + r_ss * state.s_dot**2
        )
        J = np.column_stack((phi, r_s))
        mass = self.joint_mass_matrix(state.q, state.s)
        bias = m.payload_mass_kg * (J.T @ transport)

        axis_friction = (
            m.axis_viscous_Ns_m * state.s_dot
            + m.axis_coulomb_N
            * np.tanh(state.s_dot / m.friction_smoothing_speed_m_s)
        )
        damping = np.concatenate((m.D0 @ state.q_dot, [axis_friction]))
        potential_gradient = np.concatenate((m.K0 @ state.q, [0.0]))
        potential_gradient -= m.payload_mass_kg * (J.T @ m.gravity_acceleration_m_s2)

        electrical = self.electrical_diagnostics(state, current_command_A)
        actuator_force_N = e.force_constant_N_per_A * state.current_A
        actuator_generalized_force = self.actuator.jacobian() * actuator_force_N

        if external_generalized_force is None:
            external = np.zeros(self.nq + 1, dtype=float)
        else:
            external = np.asarray(external_generalized_force, dtype=float)
            if external.shape != (self.nq + 1,):
                raise ValueError("external_generalized_force must have nq+1 entries")

        rhs = (
            actuator_generalized_force + external
            - bias - damping - potential_gradient
        )
        acceleration = np.linalg.solve(mass, rhs)
        q_ddot = acceleration[:self.nq]
        s_ddot = float(acceleration[-1])

        result = np.concatenate((
            state.q_dot, q_ddot,
            np.array([
                state.s_dot, s_ddot,
                float(electrical["current_rate_A_s"]),
                float(electrical["integrator_rate_V_s"]),
            ])
        ))
        if not np.all(np.isfinite(result)):
            raise FloatingPointError(f"non-finite state derivative at t={time_s}")
        return result

    def simulate(
        self,
        initial_state: JointState,
        duration_s: float,
        step_s: float,
        current_command: CurrentCommand,
        external_force: ExternalForce | None = None,
    ) -> tuple[FloatArray, FloatArray]:
        """Integrate with fixed-step RK4; return (time vector, packed states).

        The current command is evaluated at each RK4 stage. This is a
        continuous-command model; it does not emulate a sampled drive task.
        """
        if not np.all(np.isfinite([duration_s, step_s])):
            raise ValueError("duration_s and step_s must be finite")
        if duration_s <= 0.0 or step_s <= 0.0:
            raise ValueError("duration_s and step_s must be positive")
        count = int(round(duration_s / step_s))
        if count < 1 or not np.isclose(count * step_s, duration_s, rtol=1e-9, atol=1e-12):
            raise ValueError("duration_s must be an integer multiple of step_s")

        def evaluate(t: float, y: FloatArray) -> FloatArray:
            x = self.unpack(y)
            command = float(current_command(t, x))
            force = None if external_force is None else external_force(t, x)
            return self.derivative(t, y, command, force)

        times = np.linspace(0.0, duration_s, count + 1)
        states = np.empty((count + 1, 2 * self.nq + 4), dtype=float)
        states[0] = self.pack(initial_state)
        y = states[0].copy()
        for index in range(count):
            t = times[index]
            h = step_s
            k1 = evaluate(t, y)
            k2 = evaluate(t + 0.5*h, y + 0.5*h*k1)
            k3 = evaluate(t + 0.5*h, y + 0.5*h*k2)
            k4 = evaluate(t + h, y + h*k3)
            y = y + (h / 6.0) * (k1 + 2.0*k2 + 2.0*k3 + k4)
            if not np.all(np.isfinite(y)):
                raise FloatingPointError(f"non-finite integrated state at t={times[index+1]}")
            states[index + 1] = y
        return times, states
