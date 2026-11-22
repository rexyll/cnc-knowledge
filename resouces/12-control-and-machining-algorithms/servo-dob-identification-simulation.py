#!/usr/bin/env python3
"""Synthetic CNC servo identification and DOB sensitivity examples.

Python 3.10+ and NumPy required. All samples are synthetic teaching data,
not measurements or tuning recommendations for any real drive or machine.
"""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path
import numpy as np

DT = 0.001
J_TRUE, B_TRUE, TC_TRUE, T0_TRUE = 0.025, 0.080, 0.150, 0.030


def write_csv(path: Path, header: list[str], rows: list[list[object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(header)
        writer.writerows(rows)


def identify_inertia(seed: int):
    rng = np.random.default_rng(seed)
    time = np.arange(int(8.0 / DT), dtype=float) * DT
    levels = np.array([0.85, 1.05, -0.80, -1.00, 0.65, -0.95, 1.15, -0.70])
    torque = np.array([levels[int((value // 0.5) % len(levels))] for value in time])
    torque += 0.08 * np.sin(2 * np.pi * 1.3 * time) + 0.05 * np.sin(2 * np.pi * 3.7 * time)
    omega = np.zeros_like(time)
    for k in range(1, len(time)):
        friction = TC_TRUE * np.sign(omega[k - 1])
        alpha = (torque[k - 1] - B_TRUE * omega[k - 1] - friction - T0_TRUE) / J_TRUE
        omega[k] = omega[k - 1] + DT * alpha
    omega_meas = omega + rng.normal(0.0, 0.00025, len(time))
    torque_meas = torque + rng.normal(0.0, 0.002, len(time))
    omega_smooth = np.convolve(omega_meas, np.ones(3) / 3.0, mode="same")
    alpha_est = np.gradient(omega_smooth, DT)
    idx = np.arange(20, len(time) - 20)
    matrix = np.column_stack((alpha_est[idx], omega_smooth[idx],
                              np.sign(omega_smooth[idx]), np.ones(len(idx))))
    observed = torque_meas[idx]
    estimate, _, rank, _ = np.linalg.lstsq(matrix, observed, rcond=None)
    residual = observed - matrix @ estimate
    r2 = 1.0 - float(residual @ residual) / float(np.sum((observed - np.mean(observed)) ** 2))
    condition = float(np.linalg.cond(matrix / np.linalg.norm(matrix, axis=0)))
    names = ["J", "B", "Tc", "T0"]
    truth = [J_TRUE, B_TRUE, TC_TRUE, T0_TRUE]
    result = {}
    for name, value, actual in zip(names, estimate, truth):
        result[f"{name}_estimate"] = float(value)
        result[f"{name}_relative_error_percent"] = float(100.0 * (value - actual) / actual)
    result.update({
        "residual_rms_Nm": float(np.sqrt(np.mean(residual ** 2))),
        "r_squared": float(r2),
        "column_scaled_condition_number": condition,
        "samples_used": int(len(observed)),
        "matrix_rank": int(rank),
    })
    raw = [[f"{time[k]:.6f}", f"{torque[k]:.8f}", f"{torque_meas[k]:.8f}",
            f"{omega[k]:.8f}", f"{omega_meas[k]:.8f}", f"{omega_smooth[k]:.8f}",
            f"{alpha_est[k]:.8f}"] for k in range(len(time))]
    return result, raw


def simulate_dob(cutoff_hz: float | None, seed: int = 10):
    count = int(12.0 / DT)
    rng = np.random.default_rng(seed)
    omega = 0.0
    previous_measured_speed = 0.0
    integrator = 0.0
    d_hat = 0.0
    actual_motor_torque = 0.0
    command_buffer = [0.0, 0.0, 0.0]
    speed = np.zeros(count)
    command_history = np.zeros(count)
    d_hat_history = np.zeros(count)
    j_nom, b_nom = 0.022, 0.075
    j_actual, b_actual = J_TRUE, B_TRUE
    actuator_tau = 0.004
    kp, ki = 0.55, 7.0
    reference = 0.5
    noise_std = 0.0005
    q_alpha = 0.0 if cutoff_hz is None else 1.0 - np.exp(-2.0 * np.pi * cutoff_hz * DT)
    previous_command = 0.0
    for k in range(count):
        now = k * DT
        disturbance = 0.18 if 3.0 <= now < 7.0 else 0.0
        measured = omega + rng.normal(0.0, noise_std)
        acceleration_measured = (measured - previous_measured_speed) / DT if k else 0.0
        error = reference - measured
        integrator = float(np.clip(integrator + ki * error * DT, -1.2, 1.2))
        feedback = kp * error + integrator
        if cutoff_hz is None:
            d_hat = 0.0
        else:
            observer_input = j_nom * acceleration_measured + b_nom * measured - previous_command
            d_hat += q_alpha * (observer_input - d_hat)
        command = float(np.clip(feedback - d_hat, -1.5, 1.5))
        command_buffer.append(command)
        delayed_command = command_buffer.pop(0)
        actual_motor_torque += DT * (delayed_command - actual_motor_torque) / actuator_tau
        omega += DT * ((actual_motor_torque + disturbance - b_actual * omega) / j_actual)
        speed[k] = omega
        command_history[k] = command
        d_hat_history[k] = d_hat
        previous_measured_speed = measured
        previous_command = command
    time = np.arange(count) * DT
    active = (time >= 3.0) & (time < 7.0)
    recovery = (time >= 7.5) & (time < 12.0)
    estimate_window = (time >= 5.0) & (time < 7.0)
    error = speed - reference
    return {
        "q_cutoff_hz": "disabled" if cutoff_hz is None else f"{cutoff_hz:g}",
        "peak_abs_speed_error_during_disturbance_rad_s": float(np.max(np.abs(error[active]))),
        "rms_speed_error_during_disturbance_rad_s": float(np.sqrt(np.mean(error[active] ** 2))),
        "rms_speed_error_after_disturbance_rad_s": float(np.sqrt(np.mean(error[recovery] ** 2))),
        "mean_estimated_disturbance_5_to_7s_Nm": float(np.mean(d_hat_history[estimate_window])),
        "command_torque_std_after_disturbance_Nm": float(np.std(command_history[recovery])),
        "maximum_abs_command_torque_Nm": float(np.max(np.abs(command_history))),
        "command_saturation_samples": int(np.sum(np.abs(command_history) >= 1.499)),
        "maximum_abs_speed_rad_s": float(np.max(np.abs(speed))),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--seed", type=int, default=20261122)
    parser.add_argument("--include-raw-data", action="store_true",
                        help="also write an 8,000-row synthetic identification trace")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    identified, raw = identify_inertia(args.seed)
    summary_rows = [[key, f"{value:.12g}", "synthetic_only"] for key, value in identified.items()]
    write_csv(args.output_dir / "servo-inertia-identification-summary.csv",
              ["metric", "value", "classification"], summary_rows)
    if args.include_raw_data:
        write_csv(args.output_dir / "servo-inertia-identification-synthetic.csv",
                  ["time_s", "torque_command_Nm", "motor_torque_measured_Nm_synthetic",
                   "omega_true_rad_s", "omega_measured_rad_s_synthetic",
                   "omega_smoothed_rad_s", "alpha_estimated_rad_s2"], raw)
    frf_rows = []
    for hz in np.geomspace(0.5, 100.0, 48):
        rad = 2.0 * np.pi * hz
        magnitude = 1.0 / np.sqrt(B_TRUE ** 2 + (J_TRUE * rad) ** 2)
        phase = -np.degrees(np.arctan2(J_TRUE * rad, B_TRUE))
        frf_rows.append([f"{hz:.8g}", f"{magnitude:.10g}",
                         f"{20*np.log10(magnitude):.10g}", f"{phase:.10g}"])
    write_csv(args.output_dir / "servo-rigid-body-frf-analytical-example.csv",
              ["frequency_hz", "magnitude_rad_s_per_Nm", "magnitude_db", "phase_deg"], frf_rows)
    sweep = []
    for cutoff in [None, 2, 5, 10, 20, 40, 80, 100]:
        metrics = simulate_dob(cutoff)
        sweep.append([metrics[k] for k in [
            "q_cutoff_hz", "peak_abs_speed_error_during_disturbance_rad_s",
            "rms_speed_error_during_disturbance_rad_s", "rms_speed_error_after_disturbance_rad_s",
            "mean_estimated_disturbance_5_to_7s_Nm", "command_torque_std_after_disturbance_Nm",
            "maximum_abs_command_torque_Nm", "command_saturation_samples", "maximum_abs_speed_rad_s"
        ]] + ["Synthetic plant mismatch; 4 ms actuator lag and 2 ms unmodelled delay"])
    write_csv(args.output_dir / "dob-q-cutoff-sweep-synthetic.csv",
              ["q_cutoff_hz", "peak_abs_speed_error_during_disturbance_rad_s",
               "rms_speed_error_during_disturbance_rad_s", "rms_speed_error_after_disturbance_rad_s",
               "mean_estimated_disturbance_5_to_7s_Nm", "command_torque_std_after_disturbance_Nm",
               "maximum_abs_command_torque_Nm", "command_saturation_samples",
               "maximum_abs_speed_rad_s", "model_note"], sweep)
    config = {
        "data_classification": "synthetic_simulation_not_machine_measurement",
        "python_requirement": "3.10+",
        "sample_time_s": DT,
        "identification_plant": {"J_kg_m2": J_TRUE, "B_Nm_s_rad": B_TRUE,
                                 "Tc_Nm": TC_TRUE, "constant_torque_bias_Nm": T0_TRUE},
        "dob_plant": {"actual_J_kg_m2": J_TRUE, "actual_B_Nm_s_rad": B_TRUE,
                      "nominal_J_kg_m2": 0.022, "nominal_B_Nm_s_rad": 0.075,
                      "actuator_time_constant_s": 0.004, "unmodelled_command_delay_s": 0.002,
                      "speed_reference_rad_s": 0.5, "disturbance_Nm": 0.18,
                      "disturbance_interval_s": [3.0, 7.0], "measurement_noise_std_rad_s": 0.0005,
                      "PI_Kp_Nm_per_rad_s": 0.55, "PI_Ki_Nm_per_rad": 7.0,
                      "torque_command_limit_Nm": 1.5},
        "random_seeds": {"identification": args.seed, "dob": 10},
        "interpretation": "Finite-horizon sensitivity demonstration only; not robust-stability proof or machine tuning recommendation."
    }
    (args.output_dir / "servo-dob-simulation-config.json").write_text(
        json.dumps(config, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"identification": identified, "dob_sweep_rows": len(sweep)}, indent=2))


if __name__ == "__main__":
    main()
