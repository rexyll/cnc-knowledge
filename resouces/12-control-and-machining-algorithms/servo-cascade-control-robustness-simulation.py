#!/usr/bin/env python3
"""Synthetic servo feedforward, notch/low-pass co-design and margin study.

Python 3.10+, NumPy and SciPy. Values are synthetic teaching data only.
No drive-specific settings, CNC acceptance criteria, or safety evidence.
"""
from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
from scipy.signal import bilinear, butter, sosfreqz, tf2sos

TS = 0.0005
FS = 1.0 / TS
TAU_CURRENT = 0.001
TORQUE_LIMIT = 1.0
VELOCITY_REFERENCE_LIMIT = 1.5
ANTI_WINDUP_TAW = 0.030
TRAJECTORY_HZ = 1.0
TRAJECTORY_AMPLITUDE_RAD = 0.040
REFERENCE_RIPPLE_RAD = 0.0002
MEASUREMENT_NOISE_STD_RAD_S = 0.0005
NOTCH_CENTERS_HZ = (42.0, 70.0, 94.0)
NOTCH_POLE_DAMPING = 0.12
NOTCH_CENTER_GAIN = 0.05
SPEED_FEEDBACK_LOWPASS_HZ = 150.0
FREQUENCIES_HZ = np.logspace(np.log10(0.1), np.log10(900.0), 7000)
RANDOM_SEED = 20261122
FREQUENCIES_HZ = np.logspace(np.log10(0.1), np.log10(900.0), 7000)


@dataclass(frozen=True)
class Plant:
    name: str
    inertia: tuple[float, ...]
    viscous: tuple[float, ...]
    stiffness: tuple[float, ...]
    shaft_damping: tuple[float, ...]
    coulomb: tuple[float, ...]


PLANTS = (
    Plant("nominal_cold", (0.010, 0.020), (0.006, 0.014), (1400.0,), (0.35,), (0.012, 0.018)),
    Plant("heavy_load_cold", (0.010, 0.032), (0.006, 0.018), (1400.0,), (0.42,), (0.012, 0.020)),
    Plant("heavy_load_hot", (0.010, 0.032), (0.008, 0.025), (1260.0,), (0.39,), (0.014, 0.022)),
    Plant("three_mode_reference", (0.010, 0.008, 0.020), (0.005, 0.007, 0.013),
          (1200.0, 850.0), (0.35, 0.28), (0.010, 0.012, 0.018)),
)

# Rigid-body inertia is the sum for a directly coupled axis with common
# low-frequency angular acceleration. Reduced inertia is used only for the
# relative torsional mode, not for rigid-body acceleration feedforward.
J_RIGID_NOMINAL = sum(PLANTS[0].inertia)
B_RIGID_NOMINAL = sum(PLANTS[0].viscous)

CONTROLLERS = (
    {"name": "aggressive_corrected", "speed_bandwidth_hz": 16.0,
     "integral_zero_hz": 6.0, "position_bandwidth_hz": 2.5},
    {"name": "conservative_corrected", "speed_bandwidth_hz": 12.0,
     "integral_zero_hz": 4.0, "position_bandwidth_hz": 1.5},
)

FILTERS = ("none", "notch", "lp", "both")
FEEDFORWARD_VARIANTS = (
    {"name": "no_ff_none", "velocity_ff": False, "acceleration_ff": False, "filter": "none"},
    {"name": "velocity_ff_none", "velocity_ff": True, "acceleration_ff": False, "filter": "none"},
    {"name": "velocity_acceleration_ff_none", "velocity_ff": True, "acceleration_ff": True, "filter": "none"},
    {"name": "velocity_acceleration_ff_notch", "velocity_ff": True, "acceleration_ff": True, "filter": "notch"},
    {"name": "velocity_acceleration_ff_notch_lp", "velocity_ff": True, "acceleration_ff": True, "filter": "both"},
    {"name": "velocity_acceleration_ff_lp", "velocity_ff": True, "acceleration_ff": True, "filter": "lp"},
)


def controller_gains(controller: dict[str, Any]) -> tuple[float, float, float]:
    kp_speed = J_RIGID_NOMINAL * 2.0 * np.pi * controller["speed_bandwidth_hz"]
    ki_speed = kp_speed * 2.0 * np.pi * controller["integral_zero_hz"]
    kp_position = 2.0 * np.pi * controller["position_bandwidth_hz"]
    return kp_speed, ki_speed, kp_position


def modal_frequencies(plant: Plant) -> np.ndarray:
    """Undamped elastic mode frequencies; omit the rigid-body zero mode."""
    mass = np.diag(plant.inertia)
    n = len(plant.inertia)
    stiffness = np.zeros((n, n), dtype=float)
    for i, k in enumerate(plant.stiffness):
        stiffness[i, i] += k
        stiffness[i + 1, i + 1] += k
        stiffness[i, i + 1] -= k
        stiffness[i + 1, i] -= k
    eigenvalues = np.linalg.eigvals(np.linalg.solve(mass, stiffness))
    positive = np.sort(eigenvalues[eigenvalues > 1e-8])
    return np.sqrt(positive) / (2.0 * np.pi)


def state_space(plant: Plant):
    n = len(plant.inertia)
    a = np.zeros((2 * n, 2 * n), dtype=float)
    b = np.zeros(2 * n, dtype=float)
    for i in range(n):
        a[2 * i, 2 * i + 1] = 1.0
        a[2 * i + 1, 2 * i + 1] -= plant.viscous[i] / plant.inertia[i]
        if i == 0:
            b[2 * i + 1] = 1.0 / plant.inertia[i]
        if i < n - 1:
            k = plant.stiffness[i]
            c = plant.shaft_damping[i]
            j = i + 1
            a[2 * i + 1, 2 * i] -= k / plant.inertia[i]
            a[2 * i + 1, 2 * i + 1] -= c / plant.inertia[i]
            a[2 * i + 1, 2 * j] += k / plant.inertia[i]
            a[2 * i + 1, 2 * j + 1] += c / plant.inertia[i]
            a[2 * j + 1, 2 * i] += k / plant.inertia[j]
            a[2 * j + 1, 2 * i + 1] += c / plant.inertia[j]
            a[2 * j + 1, 2 * j] -= k / plant.inertia[j]
            a[2 * j + 1, 2 * j + 1] -= c / plant.inertia[j]
    c_motor_speed = np.zeros(2 * n)
    c_motor_speed[1] = 1.0
    c_load_position = np.zeros(2 * n)
    c_load_position[-2] = 1.0
    return a, b, c_motor_speed, c_load_position


def filter_sos(mode: str) -> np.ndarray:
    sections = []
    if mode in ("notch", "both"):
        for center_hz in NOTCH_CENTERS_HZ:
            # Prewarp the analog center frequency so the bilinear transform
            # places the digital notch at the requested frequency.
            wn = 2.0 * FS * np.tan(np.pi * center_hz / FS)
            zeta_p = NOTCH_POLE_DAMPING
            zeta_z = NOTCH_CENTER_GAIN * zeta_p
            numerator = [1.0, 2.0 * zeta_z * wn, wn * wn]
            denominator = [1.0, 2.0 * zeta_p * wn, wn * wn]
            bz, az = bilinear(numerator, denominator, fs=FS)
            sections.extend(tf2sos(bz, az))
    if mode in ("lp", "both"):
        bl, al = butter(1, SPEED_FEEDBACK_LOWPASS_HZ, fs=FS, btype="low")
        sections.extend(tf2sos(bl, al))
    return np.asarray(sections, dtype=float) if sections else np.empty((0, 6), dtype=float)


class SOSStream:
    """Scalar second-order-section stream filter, direct-form II transposed."""
    def __init__(self, sos: np.ndarray):
        self.sos = sos
        self.state = np.zeros((len(sos), 2), dtype=float)

    def step(self, value: float) -> float:
        y = float(value)
        for i, section in enumerate(self.sos):
            b0, b1, b2, a0, a1, a2 = section
            z1, z2 = self.state[i]
            out = b0 * y + z1
            self.state[i] = (b1 * y - a1 * out + z2, b2 * y - a2 * out)
            y = out
        return y


def mechanical_derivative(state: np.ndarray, t: float, command: float, plant: Plant,
                          modes_hz: np.ndarray, scenario: str) -> np.ndarray:
    n = len(plant.inertia)
    mechanics = state[:-1]
    torque_state = state[-1]
    theta = mechanics[0::2]
    omega = mechanics[1::2]
    inertia = np.asarray(plant.inertia)
    net = -np.asarray(plant.viscous) * omega
    net -= np.asarray(plant.coulomb) * np.tanh(omega / 0.015)
    net[0] += torque_state

    if scenario == "load_disturbance" and 1.0 <= t < 1.30:
        for mode_hz in modes_hz:
            net[-1] += 0.015 * np.sin(2.0 * np.pi * mode_hz * t)

    derivative = np.zeros(2 * n + 1, dtype=float)
    for i in range(n - 1):
        shaft_torque = (plant.stiffness[i] * (theta[i] - theta[i + 1])
                        + plant.shaft_damping[i] * (omega[i] - omega[i + 1]))
        net[i] -= shaft_torque
        net[i + 1] += shaft_torque

    derivative[:-1:2] = omega
    derivative[1:-1:2] = net / inertia
    derivative[-1] = (command - torque_state) / TAU_CURRENT
    return derivative


def modal_rms_components(signal: np.ndarray, modes_hz: np.ndarray) -> list[float]:
    window = np.hanning(len(signal))
    spectrum = np.fft.rfft((signal - np.mean(signal)) * window)
    frequencies = np.fft.rfftfreq(len(signal), TS)
    result = []
    for mode_hz in modes_hz:
        indices = np.where(np.abs(frequencies - mode_hz) <= 2.0)[0]
        amplitude = 2.0 * np.max(np.abs(spectrum[indices])) / np.sum(window) if len(indices) else 0.0
        result.append(float(amplitude / np.sqrt(2.0)))
    return result


def simulate_tracking(plant: Plant, variant: dict[str, Any], scenario: str,
                      inertia_estimate: str = "nominal") -> dict[str, Any]:
    duration_s = 2.5
    steps = int(duration_s / TS)
    substeps = 2
    h = TS / substeps
    n = len(plant.inertia)
    modes = modal_frequencies(plant)
    controller = CONTROLLERS[1]
    kp_speed, ki_speed, kp_position = controller_gains(controller)

    if inertia_estimate == "nominal":
        j_est, b_est = J_RIGID_NOMINAL, B_RIGID_NOMINAL
    elif inertia_estimate == "matched":
        j_est, b_est = sum(plant.inertia), sum(plant.viscous)
    elif inertia_estimate == "under20":
        j_est, b_est = 0.8 * sum(plant.inertia), 0.8 * sum(plant.viscous)
    else:
        raise ValueError(f"unsupported inertia estimate: {inertia_estimate}")

    speed_filter = SOSStream(filter_sos("lp" if variant["filter"] in ("lp", "both") else "none"))
    torque_notch = SOSStream(filter_sos("notch" if variant["filter"] in ("notch", "both") else "none"))
    rng = np.random.default_rng(RANDOM_SEED)
    speed_noise = rng.normal(0.0, MEASUREMENT_NOISE_STD_RAD_S, steps)

    state = np.zeros(2 * n + 1)
    integrator = 0.0
    references = np.zeros(steps)
    positions = np.zeros(steps)
    actual_torque = np.zeros(steps)
    saturation = np.zeros(steps, dtype=bool)

    base_omega = 2.0 * np.pi * TRAJECTORY_HZ
    for k in range(steps):
        t = k * TS
        base_position = TRAJECTORY_AMPLITUDE_RAD * np.sin(base_omega * t)
        velocity_ff = TRAJECTORY_AMPLITUDE_RAD * base_omega * np.cos(base_omega * t)
        acceleration_ff = -TRAJECTORY_AMPLITUDE_RAD * base_omega * base_omega * np.sin(base_omega * t)

        ripple = 0.0
        if scenario == "reference_ripple":
            ripple = sum(REFERENCE_RIPPLE_RAD * np.sin(2.0 * np.pi * f * t) for f in modes)
        reference = base_position + ripple

        measured_speed = state[1] + speed_noise[k]
        filtered_speed = speed_filter.step(measured_speed)
        load_position = state[-3]
        speed_reference = kp_position * (reference - load_position)
        if variant["velocity_ff"]:
            speed_reference += velocity_ff
        speed_reference = float(np.clip(speed_reference, -VELOCITY_REFERENCE_LIMIT,
                                        VELOCITY_REFERENCE_LIMIT))

        speed_error = speed_reference - filtered_speed
        torque_feedback = kp_speed * speed_error + integrator
        torque_feedforward = 0.0
        if variant["acceleration_ff"]:
            torque_feedforward = j_est * acceleration_ff + b_est * velocity_ff

        raw_torque = torque_feedback + torque_feedforward
        filtered_torque = torque_notch.step(raw_torque)
        command = float(np.clip(filtered_torque, -TORQUE_LIMIT, TORQUE_LIMIT))
        integrator += (ki_speed * speed_error
                       + (command - filtered_torque) / ANTI_WINDUP_TAW) * TS
        saturation[k] = abs(filtered_torque) > TORQUE_LIMIT

        for sub in range(substeps):
            sub_t = t + sub * h
            k1 = mechanical_derivative(state, sub_t, command, plant, modes, scenario)
            k2 = mechanical_derivative(state + 0.5 * h * k1, sub_t + 0.5 * h,
                                       command, plant, modes, scenario)
            k3 = mechanical_derivative(state + 0.5 * h * k2, sub_t + 0.5 * h,
                                       command, plant, modes, scenario)
            k4 = mechanical_derivative(state + h * k3, sub_t + h,
                                       command, plant, modes, scenario)
            state += h * (k1 + 2.0 * k2 + 2.0 * k3 + k4) / 6.0

        references[k] = reference
        positions[k] = state[-3]
        actual_torque[k] = state[-1]

    active = np.arange(steps) * TS >= 0.5
    error = references[active] - positions[active]
    modal_components = modal_rms_components(positions[active], modes)
    return {
        "scenario": scenario,
        "plant": plant.name,
        "variant": variant["name"],
        "feedforward": ("none" if not variant["velocity_ff"] else
                        ("velocity" if not variant["acceleration_ff"] else "velocity+acceleration")),
        "filter": variant["filter"],
        "J_est_mode": inertia_estimate,
        "J_est_kg_m2": j_est,
        "B_est_Nm_s_rad": b_est,
        "tracking_rms_error_rad": float(np.sqrt(np.mean(error * error))),
        "tracking_peak_abs_error_rad": float(np.max(np.abs(error))),
        "modal_output_rms_max_rad": max(modal_components),
        "modal_output_rms_by_mode_rad": ";".join(f"{x:.9g}" for x in modal_components),
        "modal_frequencies_hz": ";".join(f"{x:.6f}" for x in modes),
        "torque_rms_Nm": float(np.sqrt(np.mean(actual_torque[active] ** 2))),
        "torque_peak_abs_Nm": float(np.max(np.abs(actual_torque[active]))),
        "torque_saturation_fraction_pct": float(np.mean(saturation[active]) * 100.0),
        "classification": "synthetic simulation; not machine measurement",
    }


def crossovers(frequencies: np.ndarray, values: np.ndarray, target: float) -> list[float]:
    indices = np.where((values[:-1] - target) * (values[1:] - target) <= 0.0)[0]
    output = []
    for i in indices:
        x1, x2 = np.log(frequencies[i]), np.log(frequencies[i + 1])
        y1, y2 = values[i], values[i + 1]
        crossing = frequencies[i] if y1 == y2 else np.exp(x1 + (target - y1) * (x2 - x1) / (y2 - y1))
        output.append(float(crossing))
    return output


def all_margins(loop: np.ndarray, omega: np.ndarray) -> dict[str, Any]:
    magnitude_db = 20.0 * np.log10(np.maximum(np.abs(loop), 1e-300))
    phase_deg = np.unwrap(np.angle(loop)) * 180.0 / np.pi
    gain_cross = crossovers(omega, magnitude_db, 0.0)
    k_min = int(np.floor((-float(np.max(phase_deg)) - 180.0) / 360.0)) - 1
    k_max = int(np.ceil((-float(np.min(phase_deg)) - 180.0) / 360.0)) + 1
    phase_cross = []
    for k in range(k_min, k_max + 1):
        phase_cross.extend(crossovers(omega, phase_deg, -180.0 - 360.0 * k))

    phase_margins = []
    for wc in gain_cross:
        phase = float(np.interp(np.log(wc), np.log(omega), phase_deg))
        pm = ((180.0 + phase + 180.0) % 360.0) - 180.0
        phase_margins.append((pm, wc / (2.0 * np.pi)))
    gain_margins = []
    for wc in phase_cross:
        gm = -float(np.interp(np.log(wc), np.log(omega), magnitude_db))
        gain_margins.append((gm, wc / (2.0 * np.pi)))
    return {
        "phase_margins_deg": ";".join(f"{x[0]:.2f}" for x in phase_margins),
        "phase_margin_crossovers_hz": ";".join(f"{x[1]:.2f}" for x in phase_margins),
        "gain_margins_db": ";".join(f"{x[0]:.2f}" for x in gain_margins),
        "gain_margin_crossovers_hz": ";".join(f"{x[1]:.2f}" for x in gain_margins),
        "gain_crossover_count": len(gain_cross),
        "phase_crossover_count": len(phase_cross),
    }


def loop_frequency_response(plant: Plant, controller: dict[str, Any], filter_mode: str,
                            feedback_delay_ms: float = 1.0):
    omega = 2.0 * np.pi * FREQUENCIES_HZ
    a, b, c_speed, c_position = state_space(plant)
    identity = np.eye(a.shape[0])
    motor_speed = np.empty(len(omega), dtype=complex)
    load_position = np.empty(len(omega), dtype=complex)
    for i, w in enumerate(omega):
        state = np.linalg.solve(1j * w * identity - a, b)
        motor_speed[i] = c_speed @ state
        load_position[i] = c_position @ state

    if filter_mode in ("notch", "both"):
        _, notch_response = sosfreqz(filter_sos("notch"), worN=FREQUENCIES_HZ, fs=FS)
    else:
        notch_response = np.ones_like(omega, dtype=complex)
    if filter_mode in ("lp", "both"):
        _, lowpass_response = sosfreqz(filter_sos("lp"), worN=FREQUENCIES_HZ, fs=FS)
    else:
        lowpass_response = np.ones_like(omega, dtype=complex)

    # One sample of feedback delay plus a half-sample ZOH approximation.
    zoh_delay = (np.exp(-1j * omega * (feedback_delay_ms / 1000.0))
                 * np.exp(-1j * omega * TS / 2.0) * np.sinc(FREQUENCIES_HZ * TS))
    actuator = 1.0 / (1.0 + 1j * omega * TAU_CURRENT)
    kp_speed, ki_speed, kp_position = controller_gains(controller)
    pi_speed = kp_speed + ki_speed / (1j * omega)

    speed_open = pi_speed * actuator * motor_speed * notch_response * lowpass_response * zoh_delay
    position_open = (kp_position * pi_speed * actuator * load_position
                     * notch_response * zoh_delay / (1.0 + speed_open))
    return omega, speed_open, position_open


def step_response(plant: Plant, step_rad: float) -> dict[str, Any]:
    duration = 1.5
    steps = int(duration / TS)
    substeps = 4
    h = TS / substeps
    n = len(plant.inertia)
    kp_speed, ki_speed, kp_position = controller_gains(CONTROLLERS[1])
    state = np.zeros(2 * n + 1)
    integrator = 0.0
    feedback = [(0.0, 0.0)] * 2  # two 0.5 ms samples = 1 ms feedback delay
    position = np.zeros(steps)
    command_torque = np.zeros(steps)
    actual_torque = np.zeros(steps)
    saturated = np.zeros(steps, dtype=bool)
    max_twist = 0.0

    for k in range(steps):
        t = k * TS
        feedback.append((state[-3], state[1]))
        position_fb, speed_fb = feedback.pop(0)
        reference = step_rad if t >= 0.05 else 0.0
        speed_ref = float(np.clip(kp_position * (reference - position_fb),
                                  -VELOCITY_REFERENCE_LIMIT, VELOCITY_REFERENCE_LIMIT))
        error = speed_ref - speed_fb
        raw = kp_speed * error + integrator
        command = float(np.clip(raw, -TORQUE_LIMIT, TORQUE_LIMIT))
        integrator += (ki_speed * error + (command - raw) / ANTI_WINDUP_TAW) * TS
        saturated[k] = abs(raw) > TORQUE_LIMIT

        # The step-response comparison retains the prior synthetic 0.25 Nm
        # load-torque pulse over 0.40 to 0.70 seconds.
        def derivative(y: np.ndarray, time_s: float) -> np.ndarray:
            n_local = len(plant.inertia)
            mech = y[:-1]
            torque_state = y[-1]
            theta = mech[0::2]
            omega = mech[1::2]
            net = -np.asarray(plant.viscous) * omega
            net -= np.asarray(plant.coulomb) * np.tanh(omega / 0.015)
            net[0] += torque_state
            if 0.40 <= time_s < 0.70:
                net[-1] -= 0.25
            out = np.zeros(2 * n_local + 1)
            for j in range(n_local - 1):
                shaft = (plant.stiffness[j] * (theta[j] - theta[j + 1])
                         + plant.shaft_damping[j] * (omega[j] - omega[j + 1]))
                net[j] -= shaft
                net[j + 1] += shaft
            out[:-1:2] = omega
            out[1:-1:2] = net / np.asarray(plant.inertia)
            out[-1] = (command - torque_state) / TAU_CURRENT
            return out

        for sub in range(substeps):
            sub_t = t + sub * h
            k1 = derivative(state, sub_t)
            k2 = derivative(state + 0.5 * h * k1, sub_t + 0.5 * h)
            k3 = derivative(state + 0.5 * h * k2, sub_t + 0.5 * h)
            k4 = derivative(state + h * k3, sub_t + h)
            state += h * (k1 + 2.0 * k2 + 2.0 * k3 + k4) / 6.0

        angle = state[0:2 * n:2]
        if n > 1:
            max_twist = max(max_twist, float(np.max(np.abs(np.diff(angle)))))
        position[k] = state[-3]
        command_torque[k] = command
        actual_torque[k] = state[-1]

    times = np.arange(steps) * TS
    active = np.where(times >= 0.05)[0]
    error = step_rad - position[active]
    overshoot = max(0.0, (float(np.max(position[active])) - step_rad) / abs(step_rad) * 100.0)
    tolerance = max(abs(step_rad) * 0.02, 1e-5)
    settling = float("nan")
    for index in active:
        if np.all(np.abs(position[index:] - step_rad) <= tolerance):
            settling = float(times[index] - 0.05)
            break
    return {
        "plant": plant.name,
        "controller": CONTROLLERS[1]["name"],
        "step_rad": step_rad,
        "feedback_delay_ms": 1.0,
        "overshoot_pct": overshoot,
        "settling_time_2pct_s": settling,
        "rmse_rad": float(np.sqrt(np.mean(error * error))),
        "saturation_fraction_pct": float(np.mean(saturated[active]) * 100.0),
        "peak_command_torque_nm": float(np.max(np.abs(command_torque))),
        "peak_actual_torque_nm": float(np.max(np.abs(actual_torque))),
        "max_coupling_twist_rad": max_twist,
        "final_position_error_rad": float(step_rad - position[-1]),
        "classification": "synthetic corrected-inertia step test; not machine measurement",
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"no rows to write: {path}")
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def build_config() -> dict[str, Any]:
    return {
        "classification": "synthetic_simulation_not_machine_measurement",
        "python": "3.10+",
        "dependencies": {"numpy": "runtime", "scipy": "runtime"},
        "inertia_definition_correction": {
            "rigid_body_inertia": "sum of directly coupled inertias when they share the same angular acceleration",
            "relative_mode_reduced_inertia": "Jm*Jl/(Jm+Jl), used only for two-mass relative torsion frequency",
            "nominal_rigid_body_inertia_kg_m2": J_RIGID_NOMINAL,
            "nominal_rigid_body_viscous_damping_nm_s_rad": B_RIGID_NOMINAL,
        },
        "controller_designs": [
            {**controller, "kp_speed_nm_s_rad": controller_gains(controller)[0],
             "ki_speed_nm_rad": controller_gains(controller)[1],
             "kp_position_per_s": controller_gains(controller)[2]}
            for controller in CONTROLLERS
        ],
        "simulation": {
            "sample_time_s": TS, "current_actuator_tau_s": TAU_CURRENT,
            "trajectory_frequency_hz": TRAJECTORY_HZ,
            "trajectory_amplitude_rad": TRAJECTORY_AMPLITUDE_RAD,
            "reference_ripple_rad_per_mode": REFERENCE_RIPPLE_RAD,
            "ripple_frequencies": "elastic mode frequencies of each synthetic plant",
            "measurement_speed_noise_std_rad_s": MEASUREMENT_NOISE_STD_RAD_S,
            "torque_limit_nm": TORQUE_LIMIT,
            "speed_reference_limit_rad_s": VELOCITY_REFERENCE_LIMIT,
            "anti_windup": "back-calculation; 30 ms tracking time constant",
            "time_domain_scenarios": ["reference_ripple", "load_disturbance"],
            "load_disturbance_nm_per_mode": 0.015,
            "load_disturbance_interval_s": [1.0, 1.30],
        },
        "notch_bank": {
            "centers_hz": NOTCH_CENTERS_HZ,
            "pole_damping_ratio": NOTCH_POLE_DAMPING,
            "center_gain": NOTCH_CENTER_GAIN,
            "center_attenuation_db": 20.0 * np.log10(NOTCH_CENTER_GAIN),
            "approximate_quality_factor": 1.0 / (2.0 * NOTCH_POLE_DAMPING),
            "implementation": "second-order sections; prewarped bilinear transform",
            "location": "speed-loop torque command path",
        },
        "speed_feedback_lowpass": {
            "type": "first-order Butterworth IIR",
            "cutoff_hz": SPEED_FEEDBACK_LOWPASS_HZ,
            "implementation": "bilinear digital filter",
            "location": "motor-speed feedback measurement path",
        },
        "frequency_margin_method": {
            "plant": "continuous lumped flexible two/three-inertia SISO state-space",
            "current_torque_actuator": "first-order lag",
            "filters": "digital SOS response evaluated on unit circle",
            "delay": "one 0.5 ms feedback sample plus half-sample ZOH approximation",
            "margins": "all 0 dB and -180 degree crossovers retained; nested speed and position SISO loops",
            "not_a_claim": "not MIMO disk margin, exact delayed discrete closed-loop proof or machine acceptance",
        },
        "plant_conditions": [asdict(plant) for plant in PLANTS],
        "limitations": [
            "All mechanical parameters, controller gains, limits, disturbances and noise are synthetic assumptions",
            "The controller is a simplified SISO position-P / speed-PI / first-order torque-actuator model",
            "No PMSM electrical dynamics, inverter switching, field weakening, bus jitter, encoder quantization, MIMO axis coupling or thermal law",
            "The fixed notch bank is intentionally not scheduled to the hot-state modal drift",
            "A notch on the torque command path may reduce feedback action against an external load disturbance at the same frequency",
            "The first-order feedback lowpass adds phase lag; magnitude attenuation alone is not a filter acceptance criterion",
            "Frequency-domain delay is an approximation; verify exact discrete implementation with the actual drive and timing",
            "No real equipment data, HIL, bench or machine verification",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    margin_rows = []
    omega = 2.0 * np.pi * FREQUENCIES_HZ
    for plant in PLANTS:
        for controller in CONTROLLERS:
            for filter_mode in FILTERS:
                w, speed_open, position_open = loop_frequency_response(plant, controller, filter_mode, 1.0)
                speed_margin = all_margins(speed_open, w)
                position_margin = all_margins(position_open, w)
                kp, ki, kpos = controller_gains(controller)
                margin_rows.append({
                    "plant": plant.name, "controller": controller["name"], "filter": filter_mode,
                    "feedback_delay_ms": 1.0, "sample_time_ms": TS * 1000.0,
                    "kp_speed_nm_s_rad": kp, "ki_speed_nm_rad": ki, "kp_position_per_s": kpos,
                    "speed_phase_margins_deg": speed_margin["phase_margins_deg"],
                    "speed_phase_margin_crossovers_hz": speed_margin["phase_margin_crossovers_hz"],
                    "speed_gain_margins_db": speed_margin["gain_margins_db"],
                    "speed_gain_margin_crossovers_hz": speed_margin["gain_margin_crossovers_hz"],
                    "speed_gain_crossover_count": speed_margin["gain_crossover_count"],
                    "speed_phase_crossover_count": speed_margin["phase_crossover_count"],
                    "position_phase_margins_deg": position_margin["phase_margins_deg"],
                    "position_phase_margin_crossovers_hz": position_margin["phase_margin_crossovers_hz"],
                    "position_gain_margins_db": position_margin["gain_margins_db"],
                    "position_gain_margin_crossovers_hz": position_margin["gain_margin_crossovers_hz"],
                    "position_gain_crossover_count": position_margin["gain_crossover_count"],
                    "position_phase_crossover_count": position_margin["phase_crossover_count"],
                    "classification": "synthetic SISO multiple-crossover frequency analysis",
                })
    write_csv(args.output_dir / "servo-cascade-loop-margin-envelope.csv", margin_rows)

    step_rows = [step_response(plant, step) for plant in PLANTS for step in (0.12, 0.25)]
    write_csv(args.output_dir / "servo-cascade-step-response-envelope.csv", step_rows)

    simulation_rows = []
    for plant in PLANTS:
        for variant in FEEDFORWARD_VARIANTS:
            for scenario in ("reference_ripple", "load_disturbance"):
                simulation_rows.append(simulate_tracking(plant, variant, scenario, "nominal"))
        scheduled_variant = FEEDFORWARD_VARIANTS[4]
        for estimate in ("matched", "under20"):
            simulation_rows.append(simulate_tracking(plant, scheduled_variant, "reference_ripple", estimate))
    write_csv(args.output_dir / "servo-feedforward-filter-co-design.csv", simulation_rows)

    config = build_config()
    (args.output_dir / "servo-cascade-control-simulation-config.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Wrote {len(margin_rows)} margin, {len(step_rows)} step, and "
          f"{len(simulation_rows)} feedforward/filter result rows to {args.output_dir}")


if __name__ == "__main__":
    main()
