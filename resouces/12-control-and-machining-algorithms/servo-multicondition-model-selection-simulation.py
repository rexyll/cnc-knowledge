#!/usr/bin/env python3
"""Synthetic multi-condition servo FRF and model-order selection study.

Requirements: Python 3.10+, NumPy, SciPy.
All generated data are synthetic teaching examples, not measurements,
acceptance evidence, or tuning recommendations for any CNC drive.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np
from scipy.optimize import least_squares

SEED = 20261122
NOISE_RATIO = 0.015
REPETITIONS = 24
ORDERS = (1, 2, 3)

CONDITIONS: dict[str, dict[str, Any]] = {
    "nominal_cold": {
        "description": "Nominal load, cold-state reference; synthetic two-mass axis",
        "order": 2,
        "parameters": [0.010, 0.020, 0.006, 0.014, 1400.0, 0.35],
        "frequency_max_hz": 180.0,
    },
    "heavy_load_cold": {
        "description": "Higher table/workpiece inertia, cold state; synthetic two-mass axis",
        "order": 2,
        "parameters": [0.010, 0.032, 0.006, 0.018, 1400.0, 0.42],
        "frequency_max_hz": 180.0,
    },
    "heavy_load_hot": {
        "description": "Same heavy load, illustrative hot-state stiffness/damping drift",
        "order": 2,
        "parameters": [0.010, 0.032, 0.008, 0.025, 1260.0, 0.39],
        "frequency_max_hz": 180.0,
    },
    "three_mode_reference": {
        "description": "Three-inertia/two-coupling reference for a second flexible mode",
        "order": 3,
        "parameters": [0.010, 0.008, 0.020, 0.005, 0.007, 0.013,
                       1200.0, 0.35, 850.0, 0.28],
        "frequency_max_hz": 220.0,
    },
}

BOUNDS: dict[int, tuple[np.ndarray, np.ndarray]] = {
    1: (np.array([0.001, 0.0001]), np.array([0.15, 2.0])),
    2: (
        np.array([0.001, 0.001, 0.0001, 0.0001, 10.0, 0.001]),
        np.array([0.15, 0.15, 2.0, 2.0, 1.0e5, 100.0]),
    ),
    3: (
        np.array([0.001, 0.001, 0.001, 0.0001, 0.0001, 0.0001,
                  10.0, 0.001, 10.0, 0.001]),
        np.array([0.15, 0.15, 0.15, 2.0, 2.0, 2.0,
                  1.0e5, 100.0, 1.0e5, 100.0]),
    ),
}
INITIAL: dict[int, np.ndarray] = {
    1: np.array([0.030, 0.020]),
    2: np.array([0.010, 0.020, 0.008, 0.015, 1000.0, 0.25]),
    3: np.array([0.010, 0.008, 0.020, 0.006, 0.006, 0.014,
                 1100.0, 0.30, 900.0, 0.25]),
}


def write_csv(path: Path, header: list[str], rows: list[list[object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(header)
        writer.writerows(rows)


def chain_frequency_response(freq_hz: np.ndarray, parameters: np.ndarray,
                             order: int) -> np.ndarray:
    """Return torque-to-motor-speed and torque-to-load-speed FRFs."""
    s_values = 1j * 2.0 * np.pi * np.asarray(freq_hz, dtype=float)
    result = np.zeros((len(s_values), 2), dtype=complex)

    for index, s in enumerate(s_values):
        if order == 1:
            inertia, damping = parameters
            dynamic_stiffness = np.array(
                [[inertia * s**2 + damping * s]], dtype=complex
            )
            displacement = np.linalg.solve(dynamic_stiffness, np.array([1.0 + 0j]))
            speed = s * displacement[0]
            result[index] = [speed, speed]
        elif order == 2:
            jm, jl, bm, bl, stiffness, shaft_damping = parameters
            coupling = stiffness + shaft_damping * s
            dynamic_stiffness = np.array([
                [jm * s**2 + bm * s + coupling, -coupling],
                [-coupling, jl * s**2 + bl * s + coupling],
            ], dtype=complex)
            displacement = np.linalg.solve(
                dynamic_stiffness, np.array([1.0 + 0j, 0.0 + 0j])
            )
            result[index] = s * displacement
        elif order == 3:
            j1, j2, j3, b1, b2, b3, k1, c1, k2, c2 = parameters
            coupling1 = k1 + c1 * s
            coupling2 = k2 + c2 * s
            dynamic_stiffness = np.array([
                [j1 * s**2 + b1 * s + coupling1, -coupling1, 0.0],
                [-coupling1, j2 * s**2 + b2 * s + coupling1 + coupling2,
                 -coupling2],
                [0.0, -coupling2, j3 * s**2 + b3 * s + coupling2],
            ], dtype=complex)
            displacement = np.linalg.solve(
                dynamic_stiffness, np.array([1.0 + 0j, 0.0 + 0j, 0.0 + 0j])
            )
            result[index] = s * np.array([displacement[0], displacement[2]])
        else:
            raise ValueError(f"Unsupported model order: {order}")
    return result


def estimate_h1(true_frf: np.ndarray, seed: int) -> tuple[np.ndarray, np.ndarray]:
    """Estimate H1 FRFs and magnitude-squared coherence from repeated spectra."""
    rng = np.random.default_rng(seed)
    frequency_count, output_count = true_frf.shape
    inputs = (rng.normal(size=(frequency_count, REPETITIONS))
              + 1j * rng.normal(size=(frequency_count, REPETITIONS))) / np.sqrt(2.0)
    noise = (rng.normal(size=(frequency_count, output_count, REPETITIONS))
             + 1j * rng.normal(size=(frequency_count, output_count, REPETITIONS))) / np.sqrt(2.0)
    sigma = NOISE_RATIO * np.maximum(np.abs(true_frf), 1.0e-5)
    outputs = true_frf[:, :, None] * inputs[:, None, :]
    outputs += noise * sigma[:, :, None]

    cross_spectrum = np.sum(outputs * np.conj(inputs[:, None, :]), axis=2)
    input_power = np.sum(np.abs(inputs)**2, axis=1)
    output_power = np.sum(np.abs(outputs)**2, axis=2)
    h1 = cross_spectrum / input_power[:, None]
    coherence = np.abs(cross_spectrum)**2 / (
        input_power[:, None] * output_power + 1.0e-30
    )
    return h1, np.clip(coherence.real, 0.0, 1.0)


def fit_model(freq_hz: np.ndarray, measured_frf: np.ndarray,
              order: int) -> tuple[np.ndarray, float, int]:
    """Fit positive physical parameters to complex multi-output FRF data."""
    lower, upper = BOUNDS[order]
    channel_scale = np.maximum(np.median(np.abs(measured_frf), axis=0), 1.0e-8)

    def residual(log_parameters: np.ndarray) -> np.ndarray:
        parameters = np.exp(log_parameters)
        predicted = chain_frequency_response(freq_hz, parameters, order)
        difference = (predicted - measured_frf) / channel_scale
        return np.concatenate((difference.real.ravel(), difference.imag.ravel()))

    result = least_squares(
        residual,
        np.log(INITIAL[order]),
        bounds=(np.log(lower), np.log(upper)),
        max_nfev=4000,
        ftol=1.0e-10,
        xtol=1.0e-10,
        gtol=1.0e-10,
    )
    return np.exp(result.x), float(np.sum(result.fun**2)), len(result.fun)


def corrected_aic(sse: float, sample_count: int, parameter_count: int) -> float:
    if sample_count <= parameter_count + 1:
        return float("inf")
    safe_sse = max(sse, 1.0e-15)
    aic = sample_count * np.log(safe_sse / sample_count) + 2 * parameter_count
    return float(aic + 2 * parameter_count * (parameter_count + 1)
                 / (sample_count - parameter_count - 1))


def normalized_rmse(predicted: np.ndarray, measured: np.ndarray,
                    scale: np.ndarray) -> float:
    difference = (predicted - measured) / scale
    reference = measured / scale
    return float(np.sqrt(np.mean(np.abs(difference)**2))
                 / np.sqrt(np.mean(np.abs(reference)**2)))


def identify_directional_friction(seed: int) -> list[list[object]]:
    """Fit separate direction sweeps; intercept is not split into Tc and bias."""
    rng = np.random.default_rng(seed)
    rows: list[list[object]] = []
    settings = [
        ("nominal_cold", "CW", 0.075, 0.142, 0.020),
        ("nominal_cold", "CCW", 0.083, 0.164, -0.018),
        ("heavy_load_cold", "CW", 0.078, 0.151, 0.025),
        ("heavy_load_cold", "CCW", 0.087, 0.173, -0.022),
        ("heavy_load_hot", "CW", 0.086, 0.160, 0.030),
        ("heavy_load_hot", "CCW", 0.095, 0.182, -0.028),
    ]
    for condition, direction, damping, friction, offset in settings:
        speed_magnitude = np.linspace(0.08, 1.2, 80)
        speed = speed_magnitude if direction == "CW" else -speed_magnitude
        torque = damping * speed + friction * np.sign(speed) + offset
        torque += rng.normal(0.0, 0.0015, len(speed))
        design = np.column_stack((speed, np.ones_like(speed)))
        estimate, _, rank, _ = np.linalg.lstsq(design, torque, rcond=None)
        residual = torque - design @ estimate
        rows.append([
            condition, direction, f"{estimate[0]:.8g}", f"{estimate[1]:.8g}",
            f"{np.sqrt(np.mean(residual**2)):.8g}", int(rank), len(speed),
            "Synthetic directional sweep; intercept combines Coulomb friction and offset",
        ])
    return rows


def run_study(output_dir: Path, include_raw_frf: bool = False) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    selection_rows: list[list[object]] = []
    drift_rows: list[list[object]] = []
    frf_rows: list[list[object]] = []
    selected_by_condition: dict[str, int] = {}

    for condition_index, (condition_name, specification) in enumerate(CONDITIONS.items()):
        true_order = int(specification["order"])
        true_parameters = np.asarray(specification["parameters"], dtype=float)
        frequencies = np.geomspace(2.0, float(specification["frequency_max_hz"]),
                                   100 if true_order == 3 else 80)
        true_response = chain_frequency_response(frequencies, true_parameters, true_order)
        train_frf, _ = estimate_h1(true_response, SEED + 10 * condition_index + 1)
        validation_frf, validation_coherence = estimate_h1(
            true_response, SEED + 10 * condition_index + 2
        )
        train_mask = np.arange(len(frequencies)) % 2 == 0
        validation_mask = ~train_mask

        model_results: list[tuple[int, float]] = []
        fitted_models: dict[int, tuple[np.ndarray, float, float, float, float]] = {}
        for candidate_order in ORDERS:
            parameters, sse, residual_count = fit_model(
                frequencies[train_mask], train_frf[train_mask], candidate_order
            )
            predicted_train = chain_frequency_response(
                frequencies[train_mask], parameters, candidate_order
            )
            predicted_validation = chain_frequency_response(
                frequencies[validation_mask], parameters, candidate_order
            )
            scale = np.maximum(np.median(np.abs(train_frf[train_mask]), axis=0), 1.0e-8)
            train_error = normalized_rmse(
                predicted_train, train_frf[train_mask], scale
            )
            validation_error = normalized_rmse(
                predicted_validation, validation_frf[validation_mask], scale
            )
            aicc = corrected_aic(sse, residual_count, len(parameters))
            coherence_median = float(np.median(validation_coherence[validation_mask]))
            model_results.append((candidate_order, aicc))
            fitted_models[candidate_order] = (
                parameters, train_error, validation_error, aicc, coherence_median
            )

        selected_order = min(model_results, key=lambda item: item[1])[0]
        selected_by_condition[condition_name] = selected_order
        for candidate_order in ORDERS:
            parameters, train_error, validation_error, aicc, coherence_median = (
                fitted_models[candidate_order]
            )
            selection_rows.append([
                condition_name, true_order, candidate_order, len(parameters),
                f"{train_error:.8g}", f"{validation_error:.8g}", f"{aicc:.8g}",
                f"{coherence_median:.8g}",
                "yes" if candidate_order == selected_order else "no",
                "Synthetic H1 FRF; alternating frequency bins used for fit/validation",
            ])

        names = (
            ["J_motor_kg_m2", "J_load_kg_m2", "B_motor_Nm_s_rad",
             "B_load_Nm_s_rad", "shaft_stiffness_Nm_rad", "shaft_damping_Nm_s_rad"]
            if true_order == 2 else
            ["J_motor_kg_m2", "J_intermediate_kg_m2", "J_load_kg_m2",
             "B_motor_Nm_s_rad", "B_intermediate_Nm_s_rad", "B_load_Nm_s_rad",
             "shaft1_stiffness_Nm_rad", "shaft1_damping_Nm_s_rad",
             "shaft2_stiffness_Nm_rad", "shaft2_damping_Nm_s_rad"]
        )
        drift_rows.append([
            condition_name, true_order, specification["description"],
            json.dumps({key: float(value) for key, value in zip(names, true_parameters)},
                       separators=(",", ":")),
            "Synthetic plant parameter set; not measured machine data",
        ])

        if include_raw_frf:
            for index, frequency in enumerate(frequencies):
                frf_rows.append([
                    condition_name, f"{frequency:.8g}",
                    f"{abs(validation_frf[index, 0]):.10g}",
                    f"{np.angle(validation_frf[index, 0], deg=True):.10g}",
                    f"{abs(validation_frf[index, 1]):.10g}",
                    f"{np.angle(validation_frf[index, 1], deg=True):.10g}",
                    f"{validation_coherence[index, 0]:.8g}",
                    f"{validation_coherence[index, 1]:.8g}",
                    "Synthetic H1 frequency response and coherence",
                ])

    write_csv(
        output_dir / "servo-multicondition-frf-model-selection.csv",
        ["condition", "true_synthetic_order", "candidate_model_order",
         "parameter_count", "train_normalized_rmse", "validation_normalized_rmse",
         "AICc", "median_validation_coherence", "selected_by_AICc",
         "data_classification_and_split"],
        selection_rows,
    )
    write_csv(
        output_dir / "servo-multicondition-plant-configurations.csv",
        ["condition", "true_synthetic_order", "description", "synthetic_parameters",
         "classification"],
        drift_rows,
    )
    write_csv(
        output_dir / "servo-directional-friction-fit-synthetic.csv",
        ["condition", "direction", "estimated_B_Nm_s_rad",
         "estimated_directional_intercept_Nm", "residual_rms_Nm",
         "design_matrix_rank", "samples", "notes"],
        identify_directional_friction(SEED + 100),
    )
    if include_raw_frf:
        write_csv(
            output_dir / "servo-multicondition-h1-frf-synthetic.csv",
            ["condition", "frequency_hz", "motor_speed_magnitude_rad_s_per_Nm",
             "motor_speed_phase_deg", "load_speed_magnitude_rad_s_per_Nm",
             "load_speed_phase_deg", "motor_magnitude_squared_coherence",
             "load_magnitude_squared_coherence", "classification"],
            frf_rows,
        )

    configuration = {
        "classification": "synthetic_simulation_not_machine_measurement",
        "python": "3.10+",
        "dependencies": {"numpy": np.__version__, "scipy": "least_squares"},
        "random_seed_base": SEED,
        "records_per_frequency": REPETITIONS,
        "relative_complex_output_noise_ratio": NOISE_RATIO,
        "frequency_split": "alternating frequency bins: even indices for fit, odd indices for validation",
        "conditions": CONDITIONS,
        "candidate_models": {
            "1": "single rigid inertia and viscous damping; motor/load outputs constrained equal",
            "2": "two inertias coupled by one stiffness/damping element",
            "3": "three inertias coupled by two stiffness/damping elements; motor and final-load outputs observed"
        },
        "frf_estimator": "H1 from independent repeated complex spectra; magnitude-squared coherence per output",
        "model_selection": "AICc on fit bins plus held-out validation normalized complex-FRF RMSE; no universal threshold",
        "limitations": [
            "Synthetic linear models only; no current-loop or controller closed-loop implementation",
            "No real torque sensor, encoder, thermal sensor or machine data",
            "No controller gain/phase/disk margins are calculated; no controller has been designed",
            "Directional friction intercept combines Coulomb friction and constant torque offset",
            "Three-mass fit is an equivalent model, not proof of a physical component layout",
            "Finite frequency grid and synthetic noise do not constitute equipment acceptance or safety evidence"
        ],
    }
    (output_dir / "servo-multicondition-model-validation-config.json").write_text(
        json.dumps(configuration, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"selected_model_orders": selected_by_condition,
            "selection_rows": len(selection_rows),
            "raw_frf_rows": len(frf_rows)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--include-raw-frf", action="store_true",
                        help="also write 340 rows of synthetic H1 FRF and coherence data")
    args = parser.parse_args()
    print(json.dumps(run_study(args.output_dir, args.include_raw_frf),
                     indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
