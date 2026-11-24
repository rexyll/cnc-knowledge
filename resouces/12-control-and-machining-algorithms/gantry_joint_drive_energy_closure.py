#!/usr/bin/env python3
"""Independent ENE-01..03 integrated energy-closure runner.

The solver supplies the state vector field and RK4 integration. This module
builds its own sampled power ledger and energy-closure metrics; it never calls
PATH-01's _energy_ledger or _energy_metrics. Parameters must be explicitly
sourced by the caller. No machine ratings are supplied here.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import platform
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

import gantry_joint_drive_path_comparison as path_support

ROOT = Path(__file__).resolve().parent
SOLVER_PATH = ROOT / "gantry_joint_drive_solver.py"
TIMESERIES_NAME = "gantry-joint-drive-energy-closure-timeseries.csv"
SUMMARY_NAME = "gantry-joint-drive-energy-closure-summary.csv"
MANIFEST_NAME = "gantry-joint-drive-energy-closure-run-manifest.json"
LEVELS = ("h", "h/2", "h/4", "h/8")
TIME_FIELDS = [
    "case_id", "step_level", "step_s", "time_s",
    "q1_m", "q2_rad", "q3_m", "q4_rad",
    "qdot1_m_s", "qdot2_rad_s", "qdot3_m_s", "qdot4_rad_s",
    "s_m", "s_dot_m_s", "current_A", "current_integrator_V",
    "kinetic_energy_J", "potential_energy_J", "magnetic_energy_J", "stored_energy_J",
    "requested_current_command_A", "limited_current_reference_A",
    "current_reference_saturated", "raw_voltage_V", "terminal_voltage_V",
    "voltage_saturated", "terminal_input_power_W", "copper_loss_W",
    "structural_damping_loss_W", "axis_friction_loss_W",
    "external_generalized_power_W", "electromechanical_mismatch_power_W",
    "net_power_W",
]
SUMMARY_FIELDS = [
    "case_id", "step_level", "step_s", "intervals", "samples",
    "delta_stored_energy_J", "terminal_input_work_J", "copper_loss_J",
    "structural_damping_loss_J", "axis_friction_loss_J",
    "external_generalized_work_J", "electromechanical_mismatch_work_J",
    "net_power_work_J", "absolute_net_power_work_J",
    "energy_residual_simpson_J", "energy_residual_trapezoid_J",
    "normalized_energy_residual", "normalized_energy_residual_trapezoid",
    "current_reference_saturated_stages", "voltage_saturated_stages",
    "any_limiter_active_stages", "expected_rk4_stage_evaluations",
    "observed_rk4_stage_evaluations", "stage_count_matches_expected",
    "smooth_unsaturated", "empirical_residual_order_from_previous",
    "energy_closure_threshold", "status",
]


class EnergyClosureError(ValueError):
    """Invalid ENE configuration or output archive."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_sha() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT.parents[1],
            check=True, capture_output=True, text=True, timeout=5,
        )
        return result.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def _validate(config: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(config, dict) or type(config.get("schema_version")) is not int:
        raise EnergyClosureError("configuration must be an object with integer schema_version")
    if config["schema_version"] != 1:
        raise EnergyClosureError("unsupported schema_version; expected integer 1")
    case_id = config.get("case_id")
    if case_id not in ("ENE-01", "ENE-02", "ENE-03"):
        raise EnergyClosureError("case_id must be ENE-01, ENE-02 or ENE-03")
    provenance = config.get("provenance")
    if not isinstance(provenance, dict):
        raise EnergyClosureError("provenance must be a JSON object")
    source = provenance.get("parameter_source")
    if not isinstance(source, str) or not source.strip():
        raise EnergyClosureError("provenance.parameter_source is required")
    ids = provenance.get("source_documents_or_measurement_ids")
    if not isinstance(ids, list) or any(not isinstance(x, str) or not x.strip() for x in ids):
        raise EnergyClosureError("provenance.source_documents_or_measurement_ids must be a string array")
    if len(set(x.strip() for x in ids)) != len(ids):
        raise EnergyClosureError("provenance source IDs must be unique")
    model, initial, external = path_support._build_model(config)
    e = model.electrical
    if e.force_constant_N_per_A != e.back_emf_V_per_m_s:
        raise EnergyClosureError("ENE-01..03 require reciprocal SI constants: Kf must equal Ke")
    m = model.mechanical
    if case_id == "ENE-01":
        if np.any(m.D0 != 0.0) or m.axis_viscous_Ns_m != 0.0 or m.axis_coulomb_N != 0.0:
            raise EnergyClosureError("ENE-01 requires zero structural damping and axis friction")
        if np.any(external != 0.0):
            raise EnergyClosureError("ENE-01 requires zero external generalized force")
    elif case_id == "ENE-02":
        if np.any(external != 0.0):
            raise EnergyClosureError("ENE-02 requires zero external generalized force")
    integration = config.get("integration")
    if not isinstance(integration, dict):
        raise EnergyClosureError("integration must be a JSON object")
    duration = path_support._number(integration.get("duration_s"), "integration.duration_s", positive=True)
    base_step = path_support._number(integration.get("base_step_s"), "integration.base_step_s", positive=True)
    intervals = path_support._interval_count(duration, base_step)
    if integration.get("refinement_schedule") != list(LEVELS):
        raise EnergyClosureError("refinement_schedule must be [h,h/2,h/4,h/8]")
    controller = config.get("controller_and_loads")
    if not isinstance(controller, dict):
        raise EnergyClosureError("controller_and_loads must be a JSON object")
    command = path_support._number(controller.get("feedforward_current_A"), "controller_and_loads.feedforward_current_A")
    metrics = config.get("metrics")
    if not isinstance(metrics, dict):
        raise EnergyClosureError("metrics must be a JSON object")
    scale = path_support._number(metrics.get("energy_normalization_scale_J"), "metrics.energy_normalization_scale_J", positive=True)
    floor = path_support._number(metrics.get("energy_normalization_floor_J"), "metrics.energy_normalization_floor_J", positive=True)
    threshold_value = metrics.get("normalized_energy_closure_threshold")
    threshold = None if threshold_value is None else path_support._number(
        threshold_value, "metrics.normalized_energy_closure_threshold", positive=True
    )
    return {
        "case_id": case_id, "model": model, "initial": initial,
        "external": external, "duration": duration, "base_step": base_step,
        "intervals": intervals, "command": command, "scale": scale,
        "floor": floor, "threshold": threshold, "source": source.strip(),
        "source_ids": [x.strip() for x in ids],
    }


def _power_sample(model: Any, vector: np.ndarray, command: float,
                  external: np.ndarray, case_id: str) -> dict[str, float | bool]:
    state = model.unpack(vector)
    diagnostics = model.electrical_diagnostics(state, command)
    kinetic, potential = model.mechanical_energy(state)
    magnetic = 0.5 * model.electrical.inductance_h * state.current_A**2
    terminal_voltage = float(diagnostics["voltage_V"])
    terminal_input = terminal_voltage * state.current_A
    copper = model.electrical.resistance_ohm * state.current_A**2
    structural = float(state.q_dot @ model.mechanical.D0 @ state.q_dot)
    friction_force = (
        model.mechanical.axis_viscous_Ns_m * state.s_dot
        + model.mechanical.axis_coulomb_N
        * math.tanh(state.s_dot / model.mechanical.friction_smoothing_speed_m_s)
    )
    friction = friction_force * state.s_dot
    velocity = np.concatenate((state.q_dot, [state.s_dot]))
    external_power = float(external @ velocity) if case_id == "ENE-03" else 0.0
    ell_dot = model.actuator_relative_velocity(state.q_dot, state.s_dot)
    mismatch = (
        model.electrical.force_constant_N_per_A
        - model.electrical.back_emf_V_per_m_s
    ) * state.current_A * ell_dot
    net = terminal_input - copper - structural - friction + external_power + mismatch
    values = {
        "kinetic": float(kinetic), "potential": float(potential),
        "magnetic": float(magnetic), "stored": float(kinetic + potential + magnetic),
        "requested_command": float(command),
        "limited_reference": float(diagnostics["current_reference_A"]),
        "current_reference_saturated": float(
            float(diagnostics["current_reference_A"]) != float(command)
        ),
        "raw_voltage": float(diagnostics["raw_voltage_V"]),
        "terminal_voltage": terminal_voltage,
        "voltage_saturated": bool(diagnostics["voltage_saturated"]),
        "terminal_input": float(terminal_input), "copper": float(copper),
        "structural": float(structural), "friction": float(friction),
        "external": float(external_power), "mismatch": float(mismatch),
        "net": float(net),
    }
    for key, value in values.items():
        if not isinstance(value, bool) and not math.isfinite(float(value)):
            raise FloatingPointError(f"non-finite ENE power/energy term {key}")
    return values


def _atomic_bundle(output: Path, times: list[dict[str, Any]],
                   summaries: list[dict[str, Any]], manifest: dict[str, Any]) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    time_path, summary_path, manifest_path = (
        output / TIMESERIES_NAME, output / SUMMARY_NAME, output / MANIFEST_NAME
    )
    targets = (time_path, summary_path, manifest_path)
    if any(p.exists() for p in targets):
        raise FileExistsError("ENE output bundle already exists; choose a new directory")
    with tempfile.TemporaryDirectory(prefix=".ene-staging-", dir=output) as tmp:
        stage = Path(tmp)
        staged_time, staged_summary, staged_manifest = (
            stage / TIMESERIES_NAME, stage / SUMMARY_NAME, stage / MANIFEST_NAME
        )
        for path, fields, rows in (
            (staged_time, TIME_FIELDS, times),
            (staged_summary, SUMMARY_FIELDS, summaries),
        ):
            with path.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="raise")
                writer.writeheader()
                writer.writerows(rows)
        artifacts = {}
        for key, path, rows, fields in (
            ("timeseries_csv", staged_time, times, TIME_FIELDS),
            ("summary_csv", staged_summary, summaries, SUMMARY_FIELDS),
        ):
            artifacts[key] = {
                "file": path.name, "sha256": _sha256(path),
                "size_bytes": path.stat().st_size,
                "data_rows": len(rows), "columns": len(fields),
            }
        manifest["output_artifacts"] = artifacts
        with staged_manifest.open("w", encoding="utf-8") as stream:
            json.dump(manifest, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
        os.replace(staged_time, time_path)
        os.replace(staged_summary, summary_path)
        os.replace(staged_manifest, manifest_path)
    return artifacts


def verify_archive(output_dir: Path) -> dict[str, Any]:
    output = output_dir.resolve()
    manifest_path = output / MANIFEST_NAME
    if not manifest_path.is_file():
        raise EnergyClosureError("ENE run manifest is missing")
    with manifest_path.open("r", encoding="utf-8") as stream:
        manifest = json.load(stream)
    if not isinstance(manifest, dict) or type(manifest.get("schema_version")) is not int or manifest["schema_version"] != 1:
        raise EnergyClosureError("invalid ENE manifest schema")
    if manifest.get("case_id") not in ("ENE-01", "ENE-02", "ENE-03"):
        raise EnergyClosureError("invalid ENE manifest case_id")
    artifacts = manifest.get("output_artifacts")
    if not isinstance(artifacts, dict):
        raise EnergyClosureError("manifest output_artifacts must be an object")
    for key, name, fields in (
        ("timeseries_csv", TIMESERIES_NAME, TIME_FIELDS),
        ("summary_csv", SUMMARY_NAME, SUMMARY_FIELDS),
    ):
        record = artifacts.get(key)
        path = output / name
        if not isinstance(record, dict) or record.get("file") != name or not path.is_file():
            raise EnergyClosureError(f"missing or invalid artifact {name}")
        if record.get("sha256") != _sha256(path) or record.get("size_bytes") != path.stat().st_size:
            raise EnergyClosureError(f"integrity mismatch for {name}")
        with path.open("r", encoding="utf-8", newline="") as stream:
            reader = csv.reader(stream)
            if next(reader, None) != fields:
                raise EnergyClosureError(f"CSV schema mismatch for {name}")
            count = 0
            for row in reader:
                if len(row) != len(fields):
                    raise EnergyClosureError(f"CSV row width mismatch for {name}")
                count += 1
        if count != record.get("data_rows") or record.get("columns") != len(fields):
            raise EnergyClosureError(f"CSV dimensions mismatch for {name}")
    return {"case_id": manifest["case_id"], "status": "VERIFIED",
            "recorded_status": manifest.get("status"), "manifest_json": str(manifest_path)}


def run(config_path: Path, output_dir: Path) -> dict[str, Any]:
    config_path = config_path.resolve()
    with config_path.open("r", encoding="utf-8") as stream:
        config = json.load(stream)
    v = _validate(config)
    model, initial = v["model"], v["initial"]
    command = v["command"]
    external = v["external"]
    all_rows: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []
    residuals: list[float] = []
    saturation_by_level = []
    started = datetime.now(timezone.utc).isoformat()
    for level, label in enumerate(LEVELS):
        intervals = v["intervals"] * (2 ** level)
        step = v["duration"] / intervals
        observations = {"count": 0, "reference": 0, "voltage": 0, "any": 0}

        def tracked(_time: float, state: Any) -> float:
            diag = model.electrical_diagnostics(state.copy(), command)
            ref = float(diag["current_reference_A"]) != float(command)
            volt = bool(diag["voltage_saturated"])
            observations["count"] += 1
            observations["reference"] += int(ref)
            observations["voltage"] += int(volt)
            observations["any"] += int(ref or volt)
            return command

        def load(_time: float, _state: Any) -> np.ndarray:
            return external.copy()

        times, states = model.simulate(initial, v["duration"], step, tracked, load)
        expected_stages = 4 * intervals
        stage_count = observations["count"]
        stage_match = stage_count == expected_stages
        smooth = stage_match and observations["any"] == 0
        saturation_by_level.append({
            "level": label, "stage_evaluations": stage_count,
            "expected_stage_evaluations": expected_stages,
            "current_reference_saturated_stages": observations["reference"],
            "voltage_saturated_stages": observations["voltage"],
            "any_limiter_active_stages": observations["any"],
            "stage_count_matches_expected": stage_match, "smooth_unsaturated": smooth,
        })
        samples = [
            _power_sample(model, states[index], command, external, v["case_id"])
            for index in range(len(times))
        ]
        arrays = {key: np.asarray([sample[key] for sample in samples], dtype=float)
                  for key in ("stored", "terminal_input", "copper", "structural",
                              "friction", "external", "mismatch", "net")}
        delta = float(arrays["stored"][-1] - arrays["stored"][0])
        integrals = {
            key: path_support.composite_simpson_13(times, values)
            for key, values in arrays.items() if key != "stored"
        }
        net_work = integrals["net"]
        abs_work = path_support.composite_simpson_13(times, np.abs(arrays["net"]))
        residual = delta - net_work
        denominator = max(v["scale"], abs_work, v["floor"])
        trapezoid_net = path_support.trapezoid_integral(times, arrays["net"])
        trap_residual = delta - trapezoid_net
        rho = abs(residual) / denominator
        trap_rho = abs(trap_residual) / denominator
        if not all(math.isfinite(x) for x in (delta, net_work, residual, rho, trap_residual, trap_rho)):
            raise FloatingPointError(f"non-finite ENE closure metric at {label}")
        residuals.append(abs(residual))
        for index, (time_s, vector, sample) in enumerate(zip(times, states, samples)):
            row = {
                "case_id": v["case_id"], "step_level": label, "step_s": step,
                "time_s": float(time_s),
            }
            row.update({f"q{i+1}_m" if i in (0, 2) else f"q{i+1}_rad": float(vector[i])
                        for i in range(4)})
            row.update({f"qdot{i+1}_m_s" if i in (0, 2) else f"qdot{i+1}_rad_s": float(vector[4+i])
                        for i in range(4)})
            row.update({
                "s_m": float(vector[8]), "s_dot_m_s": float(vector[9]),
                "current_A": float(vector[10]), "current_integrator_V": float(vector[11]),
                "kinetic_energy_J": sample["kinetic"], "potential_energy_J": sample["potential"],
                "magnetic_energy_J": sample["magnetic"], "stored_energy_J": sample["stored"],
                "requested_current_command_A": command,
                "limited_current_reference_A": sample["limited_reference"],
                "current_reference_saturated": bool(sample["current_reference_saturated"]),
                "raw_voltage_V": sample["raw_voltage"], "terminal_voltage_V": sample["terminal_voltage"],
                "voltage_saturated": bool(sample["voltage_saturated"]),
                "terminal_input_power_W": sample["terminal_input"], "copper_loss_W": sample["copper"],
                "structural_damping_loss_W": sample["structural"],
                "axis_friction_loss_W": sample["friction"],
                "external_generalized_power_W": sample["external"],
                "electromechanical_mismatch_power_W": sample["mismatch"],
                "net_power_W": sample["net"],
            })
            all_rows.append(row)
        previous_order = None
        if len(residuals) >= 2 and residuals[-2] > 0.0 and residuals[-1] > 0.0:
            previous_order = math.log2(residuals[-2] / residuals[-1])
            if not math.isfinite(previous_order):
                previous_order = None
        summaries.append({
            "case_id": v["case_id"], "step_level": label, "step_s": step,
            "intervals": intervals, "samples": len(times),
            "delta_stored_energy_J": delta,
            "terminal_input_work_J": integrals["terminal_input"],
            "copper_loss_J": integrals["copper"],
            "structural_damping_loss_J": integrals["structural"],
            "axis_friction_loss_J": integrals["friction"],
            "external_generalized_work_J": integrals["external"],
            "electromechanical_mismatch_work_J": integrals["mismatch"],
            "net_power_work_J": net_work, "absolute_net_power_work_J": abs_work,
            "energy_residual_simpson_J": residual,
            "energy_residual_trapezoid_J": trap_residual,
            "normalized_energy_residual": rho,
            "normalized_energy_residual_trapezoid": trap_rho,
            "current_reference_saturated_stages": observations["reference"],
            "voltage_saturated_stages": observations["voltage"],
            "any_limiter_active_stages": observations["any"],
            "expected_rk4_stage_evaluations": expected_stages,
            "observed_rk4_stage_evaluations": stage_count,
            "stage_count_matches_expected": stage_match,
            "smooth_unsaturated": smooth,
            "empirical_residual_order_from_previous": previous_order,
            "energy_closure_threshold": v["threshold"],
            "status": "PENDING",
        })
    all_smooth = all(item["smooth_unsaturated"] for item in saturation_by_level)
    if v["threshold"] is None or not all_smooth:
        status = "COMPLETED_REPORT_ONLY"
    elif summaries[-1]["normalized_energy_residual"] <= v["threshold"] and summaries[-2]["normalized_energy_residual"] <= v["threshold"]:
        status = "PASS"
    else:
        status = "FAIL"
    for row in summaries:
        row["status"] = status
    completed = datetime.now(timezone.utc).isoformat()
    manifest = {
        "schema_version": 1, "case_id": v["case_id"], "status": status,
        "numerical_results_present": True, "resource_tests_executed": False,
        "started_at_utc": started, "completed_at_utc": completed,
        "parameter_source": v["source"], "source_documents_or_measurement_ids": v["source_ids"],
        "config_sha256": _sha256(config_path), "solver_sha256": _sha256(SOLVER_PATH),
        "runner_sha256": _sha256(Path(__file__).resolve()), "solver_git_sha": _git_sha(),
        "python_version": sys.version, "numpy_version": np.__version__,
        "operating_system": platform.platform(), "cpu": platform.processor() or None,
        "duration_s": v["duration"], "base_step_s": v["base_step"],
        "refinement_schedule": list(LEVELS), "energy_normalization_scale_J": v["scale"],
        "energy_normalization_floor_J": v["floor"],
        "normalized_energy_closure_threshold": v["threshold"],
        "all_refinements_smooth_unsaturated": all_smooth,
        "limiter_stage_reports": saturation_by_level,
        "notes": [
            "Power accounting is implemented independently of PATH-01 energy ledger/metrics.",
            "The same solver state vector field and stored-energy function are reused; this is not an independent physical model.",
            "Terminal power uses the actual voltage after PI voltage saturation.",
            "Current reference limiting is not a hard state-current clamp or hardware overcurrent protection.",
            "A VERIFIED archive proves file integrity/schema only, not simulation correctness or physical validity.",
            "No hardware, SIL, HIL or machine measurement validation is implied.",
        ],
    }
    artifacts = _atomic_bundle(output_dir.resolve(), all_rows, summaries, manifest)
    return {"case_id": v["case_id"], "status": status,
            "summary_csv": str(output_dir.resolve() / SUMMARY_NAME),
            "timeseries_csv": str(output_dir.resolve() / TIMESERIES_NAME),
            "manifest_json": str(output_dir.resolve() / MANIFEST_NAME),
            "output_artifacts": artifacts}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run one ENE-01..03 integrated energy-closure case.")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--verify-archive", action="store_true")
    args = parser.parse_args(argv)
    if args.verify_archive and args.config is not None:
        parser.error("--config must be omitted with --verify-archive")
    if not args.verify_archive and args.config is None:
        parser.error("--config is required unless --verify-archive is used")
    try:
        result = verify_archive(args.output_dir) if args.verify_archive else run(args.config, args.output_dir)
    except (OSError, ValueError, RuntimeError, OverflowError, np.linalg.LinAlgError) as error:
        print(f"ENE ERROR: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
