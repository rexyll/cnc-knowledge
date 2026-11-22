#!/usr/bin/env python3
"""Synthetic four-coordinate gantry modal/load-position/discrete-delay study.

Requires Python 3.10+, NumPy and SciPy. All parameters are illustrative.
This reduced-order frozen-position model is not an FE model or measured CNC plant.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np
from scipy.linalg import eigvalsh
from scipy.signal import cont2discrete

TS = 1.0e-3
SPAN_M = 1.60
DERIVATIVE_FILTER_HZ = 60.0
WF = 2.0 * np.pi * DERIVATIVE_FILTER_HZ
ALPHA = float(np.exp(-WF * TS))
KP_BASE = 50_000.0
KD_BASE = 2_500.0
PAYLOAD_MASSES_KG = [5.0, 15.0, 30.0]
LOAD_POSITIONS = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
DELAYS_SAMPLES = list(range(7))
CONTROLLERS = [
    ("decentralized_PD", 0.0, 0.0),
    ("sync_PD_low", 10_000.0, 100.0),
    ("sync_PD_medium", 20_000.0, 200.0),
    ("sync_P_only_medium", 20_000.0, 0.0),
]
I2 = np.eye(2)
L_DIFF = np.array([[1.0, -1.0], [-1.0, 1.0]])

# Coordinates: common translation (m), yaw (rad), beam bending mode (m),
# beam torsion mode (rad). Common translation is a structural rigid-body mode.
M0 = np.diag([75.0, 12.0, 9.0, 2.0])
K0 = np.diag([
    0.0,
    12.0 * (2.0 * np.pi * 25.0) ** 2,
    9.0 * (2.0 * np.pi * 50.0) ** 2,
    2.0 * (2.0 * np.pi * 72.0) ** 2,
])
MODE_COUPLING_VECTOR = np.array([0.0, 1.0, 0.0, -1.0])
KY = 0.15 * np.sqrt(K0[1, 1] * K0[3, 3])
K0 = K0 + KY * np.outer(MODE_COUPLING_VECTOR, MODE_COUPLING_VECTOR)
D0 = np.diag([
    1_600.0,
    2.0 * 0.035 * 12.0 * (2.0 * np.pi * 25.0),
    2.0 * 0.020 * 9.0 * (2.0 * np.pi * 50.0),
    2.0 * 0.025 * 2.0 * (2.0 * np.pi * 72.0),
])
D_COUPLING = 2.0 * 0.03 * np.sqrt(K0[1, 1] * K0[3, 3])
D0 = D0 + D_COUPLING * np.outer(MODE_COUPLING_VECTOR, MODE_COUPLING_VECTOR)

# End forces act on common translation and yaw moment.
B_FORCE = np.array([
    [1.0, 1.0],
    [-SPAN_M / 2.0, SPAN_M / 2.0],
    [0.0, 0.0],
    [0.0, 0.0],
])
C_CARRIAGE = np.array([
    [1.0, -SPAN_M / 2.0, 0.0, 0.0],
    [1.0, SPAN_M / 2.0, 0.0, 0.0],
])


def build_plant(payload_mass_kg: float, load_position: float):
    """Build one frozen-position LTI plant; no Mdot/Coriolis terms."""
    if not 0.0 <= load_position <= 1.0:
        raise ValueError("load_position must be normalized to [0, 1]")
    if payload_mass_kg < 0.0:
        raise ValueError("payload mass cannot be negative")
    x_offset = (load_position - 0.5) * SPAN_M
    phi = float(np.sin(np.pi * load_position))
    g = np.array([1.0, x_offset, phi, 0.18 * phi])
    mass = M0 + payload_mass_kg * np.outer(g, g)
    min_mass_eig = float(np.min(np.linalg.eigvalsh(mass)))
    if min_mass_eig <= 0.0:
        raise ValueError("generalized mass matrix is not positive definite")
    modal_hz = np.sqrt(np.maximum(eigvalsh(K0, mass), 0.0)) / (2.0 * np.pi)
    a_c = np.block([
        [np.zeros((4, 4)), np.eye(4)],
        [-np.linalg.solve(mass, K0), -np.linalg.solve(mass, D0)],
    ])
    b_c = np.vstack([np.zeros((4, 2)), np.linalg.solve(mass, B_FORCE)])
    c_c = np.hstack([C_CARRIAGE, np.zeros((2, 4))])
    a_d, b_d, c_d, _, _ = cont2discrete(
        (a_c, b_c, c_c, np.zeros((2, 2))), TS, method="zoh"
    )
    return mass, a_d, b_d, c_d, modal_hz, g, min_mass_eig


def controller_matrices(sync_kp: float, sync_kd: float):
    return KP_BASE * I2 + sync_kp * L_DIFF, KD_BASE * I2 + sync_kd * L_DIFF


def closed_loop_matrix(a_d, b_d, c_d, delay_samples: int, sync_kp: float, sync_kd: float):
    """Exact sampled state matrix with an integer command FIFO delay."""
    gp, gd = controller_matrices(sync_kp, sync_kd)
    nx = a_d.shape[0]
    nd = 2 * delay_samples
    ep0 = nx + nd
    df0 = ep0 + 2
    acl = np.zeros((nx + nd + 4, nx + nd + 4))
    plant_slice = slice(0, nx)
    gamma = (1.0 - ALPHA) / TS
    hx = -(gp + gd * gamma) @ c_d
    hep = -gd * gamma
    hdf = gd * ALPHA
    acl[plant_slice, plant_slice] = a_d
    if delay_samples == 0:
        acl[plant_slice, plant_slice] += b_d @ hx
        acl[plant_slice, ep0:ep0 + 2] = b_d @ hep
        acl[plant_slice, df0:df0 + 2] = b_d @ hdf
    else:
        acl[plant_slice, nx:nx + 2] = b_d
        for idx in range(delay_samples - 1):
            r0 = nx + 2 * idx
            c0 = nx + 2 * (idx + 1)
            acl[r0:r0 + 2, c0:c0 + 2] = I2
        tail = slice(nx + 2 * (delay_samples - 1), nx + 2 * delay_samples)
        acl[tail, plant_slice] = hx
        acl[tail, ep0:ep0 + 2] = hep
        acl[tail, df0:df0 + 2] = hdf
    acl[ep0:ep0 + 2, plant_slice] = -c_d
    acl[df0:df0 + 2, plant_slice] = -gamma * c_d
    acl[df0:df0 + 2, ep0:ep0 + 2] = -gamma * I2
    acl[df0:df0 + 2, df0:df0 + 2] = ALPHA * I2
    return acl


def discrete_frequency_metrics(a_d, b_d, c_d, sync_kp, sync_kd, delay_samples, n_frequency=1024):
    """Sampled MIMO return-difference and output-multiplicative SG diagnostics."""
    gp, gd = controller_matrices(sync_kp, sync_kd)
    min_sigma = np.inf
    peak_s = peak_t = peak_t_frequency = 0.0
    gamma = (1.0 - ALPHA) / TS
    for frequency in np.geomspace(0.2, 0.499 / TS, n_frequency):
        z = np.exp(1j * 2.0 * np.pi * frequency * TS)
        plant = c_d @ np.linalg.solve(z * np.eye(a_d.shape[0]) - a_d, b_d)
        deriv = gamma * (1.0 - 1.0 / z) / (1.0 - ALPHA / z)
        loop = plant @ (gp + gd * deriv) * z ** (-delay_samples)
        rd = I2 + loop
        min_sigma = min(min_sigma, float(np.linalg.svd(rd, compute_uv=False)[-1]))
        sensitivity = np.linalg.inv(rd)
        complementary = sensitivity @ loop
        peak_s = max(peak_s, float(np.linalg.svd(sensitivity, compute_uv=False)[0]))
        sigma_t = float(np.linalg.svd(complementary, compute_uv=False)[0])
        if sigma_t > peak_t:
            peak_t = sigma_t
            peak_t_frequency = float(frequency)
    return {
        "minimum_sigma_min_I_plus_L": min_sigma,
        "peak_sigma_max_S": peak_s,
        "peak_sigma_max_T": peak_t,
        "sampled_output_multiplicative_sg_radius": 1.0 / peak_t if peak_t > 0 else np.inf,
        "peak_T_frequency_hz": peak_t_frequency,
    }


def simulate_step(a_d, b_d, c_d, load_position, payload_mass_kg, delay_samples,
                  sync_kp, sync_kd, n_steps=1600):
    gp, gd = controller_matrices(sync_kp, sync_kd)
    x = np.zeros(a_d.shape[0])
    previous_error = np.zeros(2)
    derivative_state = np.zeros(2)
    queue = [np.zeros(2) for _ in range(delay_samples)]
    reference = np.array([1.0e-3, 1.0e-3])
    q_history = []
    y_history = []
    max_force = 0.0
    for _ in range(n_steps):
        y = c_d @ x
        error = reference - y
        derivative_state = ALPHA * derivative_state + (1.0 - ALPHA) * (error - previous_error) / TS
        command = gp @ error + gd @ derivative_state
        applied = queue.pop(0) if delay_samples else command
        if delay_samples:
            queue.append(command.copy())
        x = a_d @ x + b_d @ applied
        previous_error = error
        q_history.append(x[:4].copy())
        y_history.append(c_d @ x)
        max_force = max(max_force, float(np.max(np.abs(applied))))
    q = np.asarray(q_history)
    y = np.asarray(y_history)
    skew = y[:, 1] - y[:, 0]
    xi = load_position
    x_offset = (xi - 0.5) * SPAN_M
    phi = np.sin(np.pi * xi)
    payload_position = q[:, 0] + x_offset * q[:, 1] + phi * q[:, 2] + 0.18 * phi * q[:, 3]
    payload_error = payload_position - 1.0e-3
    settling_index = None
    band = 0.02 * 1.0e-3
    for idx in range(10, len(payload_error)):
        if np.all(np.abs(payload_error[idx:]) <= band):
            settling_index = idx
            break
    return {
        "payload_mass_kg": payload_mass_kg,
        "load_position_fraction": load_position,
        "delay_samples": delay_samples,
        "delay_ms": delay_samples * TS * 1000.0,
        "sync_kp_n_per_m": sync_kp,
        "sync_kd_n_s_per_m": sync_kd,
        "peak_sync_skew_um": float(np.max(np.abs(skew)) * 1e6),
        "rms_sync_skew_um_after_10_samples": float(np.sqrt(np.mean(skew[10:] ** 2)) * 1e6),
        "peak_beam_bending_um": float(np.max(np.abs(q[:, 2])) * 1e6),
        "peak_beam_twist_mrad": float(np.max(np.abs(q[:, 3])) * 1e3),
        "peak_payload_point_error_after_10_samples_um": float(np.max(np.abs(payload_error[10:])) * 1e6),
        "payload_point_settling_2pct_ms": settling_index * TS * 1000.0 if settling_index is not None else None,
        "peak_motor_force_n": max_force,
    }


def write_csv(path: Path, rows: list[dict]):
    if rows:
        with path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    default_out = Path(__file__).resolve().parent / "generated-modal-delay"
    parser.add_argument("--output-dir", default=str(default_out))
    args = parser.parse_args()
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    modal_rows = []
    plants = {}
    for payload_mass in PAYLOAD_MASSES_KG:
        for xi in LOAD_POSITIONS:
            mass, ad, bd, cd, modes, g, min_mass_eig = build_plant(payload_mass, xi)
            plants[payload_mass, xi] = (mass, ad, bd, cd, modes, g, min_mass_eig)
            modal_rows.append({
                "payload_mass_kg": payload_mass, "load_position_fraction": xi,
                "payload_x_offset_m": (xi - 0.5) * SPAN_M,
                "min_generalized_mass_eigenvalue": min_mass_eig,
                "rigid_body_mode_hz": modes[0], "flexible_mode_1_hz": modes[1],
                "flexible_mode_2_hz": modes[2], "flexible_mode_3_hz": modes[3],
                "positive_definite_mass": True,
            })

    delay_rows = []
    for name, skp, skd in CONTROLLERS:
        for mass in PAYLOAD_MASSES_KG:
            for xi in LOAD_POSITIONS:
                _, ad, bd, cd, _, _, _ = plants[mass, xi]
                for delay in DELAYS_SAMPLES:
                    poles = np.linalg.eigvals(closed_loop_matrix(ad, bd, cd, delay, skp, skd))
                    radius = float(np.max(np.abs(poles)))
                    dominant = poles[int(np.argmax(np.abs(poles)))]
                    delay_rows.append({
                        "controller": name, "payload_mass_kg": mass,
                        "load_position_fraction": xi, "delay_samples": delay,
                        "delay_ms": delay * TS * 1000.0,
                        "max_closed_loop_pole_radius": radius,
                        "stable_by_discrete_poles": radius < 1.0,
                        "dominant_pole_real": float(dominant.real),
                        "dominant_pole_imag": float(dominant.imag),
                    })

    robustness_rows = []
    for name, skp, skd in CONTROLLERS:
        controller_rows = [r for r in delay_rows if r["controller"] == name]
        first_failure = next((r["delay_samples"] for r in controller_rows
                              if not r["stable_by_discrete_poles"]), None)
        for delay in DELAYS_SAMPLES:
            group = [r for r in controller_rows if r["delay_samples"] == delay]
            stable_count = sum(r["stable_by_discrete_poles"] for r in group)
            robustness_rows.append({
                "controller": name, "sync_kp_n_per_m": skp, "sync_kd_n_s_per_m": skd,
                "delay_samples": delay, "delay_ms": delay * TS * 1000.0,
                "tested_load_position_mass_cases": len(group), "stable_cases": stable_count,
                "unstable_cases": len(group) - stable_count,
                "worst_closed_loop_pole_radius": max(r["max_closed_loop_pole_radius"] for r in group),
                "first_failure_delay_samples_for_controller": first_failure,
            })

    step_rows = []
    for mass, xi in [(5.0, 0.1), (15.0, 0.5), (30.0, 0.9)]:
        _, ad, bd, cd, modes, _, _ = plants[mass, xi]
        for name, skp, skd in CONTROLLERS[:3]:
            result = simulate_step(ad, bd, cd, xi, mass, 1, skp, skd)
            step_rows.append({
                "controller": name, **result, "rigid_body_mode_hz": modes[0],
                "flexible_mode_1_hz": modes[1], "flexible_mode_2_hz": modes[2],
                "flexible_mode_3_hz": modes[3],
            })

    small_gain_rows = []
    _, ad, bd, cd, _, _, _ = plants[15.0, 0.5]
    for name, skp, skd in CONTROLLERS:
        for delay in [0, 1, 2, 3]:
            metrics = discrete_frequency_metrics(ad, bd, cd, skp, skd, delay)
            radius = float(np.max(np.abs(np.linalg.eigvals(
                closed_loop_matrix(ad, bd, cd, delay, skp, skd)
            ))))
            stable = radius < 1.0
            if not stable:
                metrics["sampled_output_multiplicative_sg_radius"] = None
            small_gain_rows.append({
                "controller": name, "payload_mass_kg": 15.0,
                "load_position_fraction": 0.5, "delay_samples": delay,
                "delay_ms": delay * TS * 1000.0,
                "nominal_closed_loop_stable_by_poles": stable,
                "nominal_max_pole_radius": radius, "sg_bound_applicable": stable,
                **metrics,
                "interpretation": "Sampled 1/||T||inf indicator for stable output-multiplicative full-block uncertainty; not disk margin or parametric proof",
            })

    write_csv(out / "gantry-mimo-modal-position-envelope.csv", modal_rows)
    write_csv(out / "gantry-mimo-discrete-delay-sweep.csv", delay_rows)
    write_csv(out / "gantry-mimo-delay-robustness-envelope.csv", robustness_rows)
    write_csv(out / "gantry-mimo-discrete-step-comparison.csv", step_rows)
    write_csv(out / "gantry-mimo-discrete-small-gain-margin.csv", small_gain_rows)
    print(f"modal_cases={len(modal_rows)} delay_eigen_cases={len(delay_rows)} step_cases={len(step_rows)}")
    for name, _, _ in CONTROLLERS:
        rows = [r for r in robustness_rows if r["controller"] == name]
        all_stable = [r["delay_samples"] for r in rows if r["unstable_cases"] == 0]
        first_bad = next((r["delay_samples"] for r in rows if r["unstable_cases"] > 0), None)
        print(name, "all-case-stable-delays=", all_stable, "first-failure=", first_bad)


if __name__ == "__main__":
    main()
