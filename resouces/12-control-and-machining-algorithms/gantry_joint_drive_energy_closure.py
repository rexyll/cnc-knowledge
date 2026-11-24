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
# Bound aggregate output rows before allocating RK4 trajectories and row dictionaries.
MAX_TOTAL_SAMPLES = 50_000
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
    "absolute_component_work_sum_J",
    "terminal_input_abs_contribution_fraction", "copper_loss_abs_contribution_fraction",
    "structural_damping_abs_contribution_fraction", "axis_friction_abs_contribution_fraction",
    "external_generalized_abs_contribution_fraction",
    "electromechanical_mismatch_abs_contribution_fraction",
    "energy_residual_over_scale", "energy_residual_over_absolute_net_power_work",
    "energy_residual_over_absolute_component_work",
    "simpson_trapezoid_net_work_difference_J",
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


EXPECTED_EXTERNAL_FORCE_ORDER = [
    "Q_x_common", "Q_yaw", "Q_bending", "Q_torsion", "Q_s"
]


def _validate_case_contract(case_id: str, model: Any, external: np.ndarray,
                            external_order: Any) -> None:
    if external_order != EXPECTED_EXTERNAL_FORCE_ORDER:
        raise EnergyClosureError(
            "controller_and_loads.external_generalized_force_order must exactly match "
            "[Q_x_common,Q_yaw,Q_bending,Q_torsion,Q_s]"
        )
    mechanical = model.mechanical
    structural_damping_present = bool(np.any(mechanical.D0 != 0.0))
    viscous_friction_present = mechanical.axis_viscous_Ns_m > 0.0
    coulomb_friction_present = mechanical.axis_coulomb_N > 0.0
    external_load_present = bool(np.any(external != 0.0))
    if case_id == "ENE-01":
        if structural_damping_present or viscous_friction_present or coulomb_friction_present:
            raise EnergyClosureError("ENE-01 requires zero structural damping and axis friction")
        if external_load_present:
            raise EnergyClosureError("ENE-01 requires zero external generalized force")
    elif case_id == "ENE-02":
        if not structural_damping_present:
            raise EnergyClosureError("ENE-02 requires nonzero structural damping D0")
        if not viscous_friction_present or not coulomb_friction_present:
            raise EnergyClosureError("ENE-02 requires both nonzero axis viscous and Coulomb friction")
        if external_load_present:
            raise EnergyClosureError("ENE-02 requires zero external generalized force")
    elif case_id == "ENE-03":
        if not structural_damping_present:
            raise EnergyClosureError("ENE-03 requires nonzero structural damping D0")
        if not viscous_friction_present or not coulomb_friction_present:
            raise EnergyClosureError("ENE-03 requires both nonzero axis viscous and Coulomb friction")
        if not external_load_present:
            raise EnergyClosureError("ENE-03 requires a nonzero external generalized force")

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
    controller = config.get("controller_and_loads")
    if not isinstance(controller, dict):
        raise EnergyClosureError("controller_and_loads must be a JSON object")
    _validate_case_contract(
        case_id, model, external,
        controller.get("external_generalized_force_order"),
    )
    integration = config.get("integration")
    if not isinstance(integration, dict):
        raise EnergyClosureError("integration must be a JSON object")
    duration = path_support._number(integration.get("duration_s"), "integration.duration_s", positive=True)
    base_step = path_support._number(integration.get("base_step_s"), "integration.base_step_s", positive=True)
    intervals = path_support._interval_count(duration, base_step)
    total_samples = sum(intervals * (2 ** level) + 1 for level in range(len(LEVELS)))
    if total_samples > MAX_TOTAL_SAMPLES:
        raise EnergyClosureError(
            f"refinement schedule requires {total_samples} samples; "
            f"configured safety limit is {MAX_TOTAL_SAMPLES}"
        )
    if integration.get("refinement_schedule") != list(LEVELS):
        raise EnergyClosureError("refinement_schedule must be [h,h/2,h/4,h/8]")
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


def _energy_diagnostics(integrals: dict[str, float], residual: float,
                       scale: float, floor: float, absolute_net_work: float,
                       trapezoid_residual: float) -> dict[str, float]:
    """Return component attribution and residuals against distinct energy scales.

    Fractions are absolute-work attribution diagnostics, not causal error
    allocations. Every denominator has the predeclared positive floor.
    """
    component_keys = ("terminal_input", "copper", "structural", "friction",
                      "external", "mismatch")
    component_abs_sum = math.fsum(abs(float(integrals[key])) for key in component_keys)
    denominator = max(component_abs_sum, floor)
    result = {
        "absolute_component_work_sum_J": component_abs_sum,
        "terminal_input_abs_contribution_fraction": abs(float(integrals["terminal_input"])) / denominator,
        "copper_loss_abs_contribution_fraction": abs(float(integrals["copper"])) / denominator,
        "structural_damping_abs_contribution_fraction": abs(float(integrals["structural"])) / denominator,
        "axis_friction_abs_contribution_fraction": abs(float(integrals["friction"])) / denominator,
        "external_generalized_abs_contribution_fraction": abs(float(integrals["external"])) / denominator,
        "electromechanical_mismatch_abs_contribution_fraction": abs(float(integrals["mismatch"])) / denominator,
        "energy_residual_over_scale": abs(residual) / scale,
        "energy_residual_over_absolute_net_power_work": abs(residual) / max(absolute_net_work, floor),
        "energy_residual_over_absolute_component_work": abs(residual) / denominator,
        "simpson_trapezoid_net_work_difference_J": abs(residual - trapezoid_residual),
    }
    if not all(math.isfinite(value) for value in result.values()):
        raise FloatingPointError("non-finite ENE component/residual diagnostic")
    return result


def _power_sample(model: Any, vector: np.ndarray, command: float,
                  external: np.ndarray, case_id: str) -> dict[str, float | bool]:
    vector = np.asarray(vector, dtype=float)
    if vector.shape != (12,) or not np.all(np.isfinite(vector)):
        raise FloatingPointError("ENE state vector must contain 12 finite values")
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


def _validate_manifest_contract(manifest: dict[str, Any]) -> dict[str, Any]:
    if type(manifest.get("schema_version")) is not int or manifest["schema_version"] != 1:
        raise EnergyClosureError("invalid ENE manifest schema")
    if manifest.get("case_id") not in ("ENE-01", "ENE-02", "ENE-03"):
        raise EnergyClosureError("invalid ENE manifest case_id")
    status = manifest.get("status")
    if status not in ("PASS", "FAIL", "COMPLETED_REPORT_ONLY"):
        raise EnergyClosureError("manifest status is missing or invalid")
    if manifest.get("numerical_results_present") is not True:
        raise EnergyClosureError("manifest numerical_results_present must be true")
    if manifest.get("resource_tests_executed") is not False:
        raise EnergyClosureError("manifest resource_tests_executed must be false")
    source = manifest.get("parameter_source")
    source_ids = manifest.get("source_documents_or_measurement_ids")
    if not isinstance(source, str) or not source.strip():
        raise EnergyClosureError("manifest parameter_source is missing")
    if not isinstance(source_ids, list) or any(
        not isinstance(item, str) or not item.strip() for item in source_ids
    ) or len(set(source_ids)) != len(source_ids):
        raise EnergyClosureError("manifest source document/measurement IDs are invalid")
    try:
        started = datetime.fromisoformat(manifest["started_at_utc"])
        completed = datetime.fromisoformat(manifest["completed_at_utc"])
    except (KeyError, TypeError, ValueError) as error:
        raise EnergyClosureError("manifest UTC timestamps are missing or invalid") from error
    if started.tzinfo is None or completed.tzinfo is None:
        raise EnergyClosureError("manifest timestamps must include an explicit UTC offset")
    if completed < started:
        raise EnergyClosureError("manifest completion timestamp precedes start")
    numeric_positive = (
        "duration_s", "base_step_s", "energy_normalization_scale_J",
        "energy_normalization_floor_J",
    )
    for key in numeric_positive:
        value = manifest.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)) or value <= 0:
            raise EnergyClosureError(f"manifest {key} must be finite and positive")
    duration = float(manifest["duration_s"])
    base_step = float(manifest["base_step_s"])
    try:
        ratio = duration / base_step
    except OverflowError as error:
        raise EnergyClosureError("manifest duration/base_step ratio overflowed") from error
    if not math.isfinite(ratio) or ratio > sys.maxsize // 8:
        raise EnergyClosureError("manifest duration/base_step ratio exceeds the supported index range")
    base_intervals = int(round(ratio))
    if base_intervals < 2 or base_intervals % 2 or not math.isclose(
        base_intervals * base_step, duration, rel_tol=1e-9, abs_tol=1e-12
    ):
        raise EnergyClosureError("manifest duration/base_step does not define an even integer interval count")
    total_samples = sum(base_intervals * (2 ** level) + 1 for level in range(len(LEVELS)))
    if total_samples > MAX_TOTAL_SAMPLES:
        raise EnergyClosureError(
            f"manifest refinement schedule requires {total_samples} samples; "
            f"supported limit is {MAX_TOTAL_SAMPLES}"
        )
    threshold = manifest.get("normalized_energy_closure_threshold")
    if threshold is not None and (
        isinstance(threshold, bool) or not isinstance(threshold, (int, float))
        or not math.isfinite(float(threshold)) or threshold <= 0
    ):
        raise EnergyClosureError("manifest normalized energy threshold is invalid")
    if manifest.get("refinement_schedule") != list(LEVELS):
        raise EnergyClosureError("manifest refinement_schedule is invalid")
    reports = manifest.get("limiter_stage_reports")
    if not isinstance(reports, list) or len(reports) != len(LEVELS):
        raise EnergyClosureError("manifest limiter_stage_reports must contain four levels")
    smooth_flags = []
    stage_match_flags = []
    for index, (report, label) in enumerate(zip(reports, LEVELS)):
        if not isinstance(report, dict) or report.get("level") != label:
            raise EnergyClosureError(f"manifest limiter report {label} is invalid")
        expected = 4 * base_intervals * (2 ** index)
        for key in (
            "stage_evaluations", "expected_stage_evaluations",
            "current_reference_saturated_stages", "voltage_saturated_stages",
            "any_limiter_active_stages",
        ):
            value = report.get(key)
            if type(value) is not int or value < 0:
                raise EnergyClosureError(f"manifest limiter report {label}.{key} is invalid")
        if report["expected_stage_evaluations"] != expected:
            raise EnergyClosureError(f"manifest expected RK4 stage count is invalid at {label}")
        reference_count = report["current_reference_saturated_stages"]
        voltage_count = report["voltage_saturated_stages"]
        any_count = report["any_limiter_active_stages"]
        if any(value > report["stage_evaluations"] for value in (
            reference_count, voltage_count, any_count
        )) or any_count < max(reference_count, voltage_count) or any_count > reference_count + voltage_count:
            raise EnergyClosureError(f"manifest limiter counts are inconsistent at {label}")
        stage_match = report["stage_evaluations"] == expected
        stage_match_flags.append(stage_match)
        smooth = stage_match and report["any_limiter_active_stages"] == 0
        if report.get("stage_count_matches_expected") is not stage_match:
            raise EnergyClosureError(f"manifest stage-count flag is inconsistent at {label}")
        if report.get("smooth_unsaturated") is not smooth:
            raise EnergyClosureError(f"manifest smooth-unsaturated flag is inconsistent at {label}")
        smooth_flags.append(smooth)
    all_smooth = all(smooth_flags)
    if manifest.get("all_refinements_smooth_unsaturated") is not all_smooth:
        raise EnergyClosureError("manifest aggregate smooth-unsaturated flag is inconsistent")
    return {
        "status": status, "threshold": None if threshold is None else float(threshold),
        "duration": duration, "base_intervals": base_intervals,
        "all_smooth": all_smooth,
        "all_stage_counts_match": all(stage_match_flags),
    }


def _read_verified_csv(
    path: Path, fields: list[str], name: str, *,
    boolean_fields: tuple[str, ...] = (), blank_fields: tuple[str, ...] = (),
) -> list[dict[str, str]]:
    try:
        with path.open("r", encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames != fields:
                raise EnergyClosureError(f"CSV schema mismatch for {name}")
            records = []
            categorical = {"case_id", "step_level", "status", *boolean_fields}
            for row_number, row in enumerate(reader, start=2):
                if None in row or any(value is None for value in row.values()):
                    raise EnergyClosureError(f"CSV row width mismatch for {name} at row {row_number}")
                for key, value in row.items():
                    if key in categorical:
                        if key in boolean_fields and value not in ("True", "False"):
                            raise EnergyClosureError(f"invalid boolean {key} in {name} row {row_number}")
                        continue
                    if value == "" and key in blank_fields:
                        continue
                    try:
                        number = float(value)
                    except (TypeError, ValueError) as error:
                        raise EnergyClosureError(
                            f"non-numeric value {key} in {name} row {row_number}"
                        ) from error
                    if not math.isfinite(number):
                        raise EnergyClosureError(
                            f"non-finite value {key} in {name} row {row_number}"
                        )
                records.append(row)
            return records
    except (csv.Error, UnicodeError) as error:
        raise EnergyClosureError(f"CSV parse/encoding failure for {name}: {error}") from error


def verify_archive(output_dir: Path) -> dict[str, Any]:
    output = output_dir.resolve()
    manifest_path = output / MANIFEST_NAME
    if not manifest_path.is_file():
        raise EnergyClosureError("ENE run manifest is missing")
    try:
        with manifest_path.open("r", encoding="utf-8") as stream:
            manifest = json.load(stream)
    except (OSError, ValueError, UnicodeError) as error:
        raise EnergyClosureError(f"cannot read ENE manifest: {error}") from error
    if not isinstance(manifest, dict):
        raise EnergyClosureError("ENE manifest root must be a JSON object")
    contract = _validate_manifest_contract(manifest)
    artifacts = manifest.get("output_artifacts")
    if not isinstance(artifacts, dict) or set(artifacts) != {"timeseries_csv", "summary_csv"}:
        raise EnergyClosureError("manifest output_artifacts must contain exactly the two CSV artifacts")
    verified: dict[str, dict[str, Any]] = {}
    parsed: dict[str, list[dict[str, str]]] = {}
    for key, name, fields, bool_fields, blank_fields in (
        ("timeseries_csv", TIMESERIES_NAME, TIME_FIELDS,
         ("current_reference_saturated", "voltage_saturated"), ()),
        ("summary_csv", SUMMARY_NAME, SUMMARY_FIELDS, (), ("empirical_residual_order_from_previous",)),
    ):
        record = artifacts.get(key)
        path = output / name
        if not isinstance(record, dict) or record.get("file") != name or not path.is_file():
            raise EnergyClosureError(f"missing or invalid artifact {name}")
        digest = record.get("sha256")
        if not isinstance(digest, str) or len(digest) != 64 or any(
            character not in "0123456789abcdef" for character in digest
        ):
            raise EnergyClosureError(f"invalid SHA-256 metadata for {name}")
        size_bytes, data_rows, columns = (
            record.get("size_bytes"), record.get("data_rows"), record.get("columns")
        )
        if type(size_bytes) is not int or size_bytes < 0:
            raise EnergyClosureError(f"invalid byte-size metadata for {name}")
        if type(data_rows) is not int or data_rows < 0:
            raise EnergyClosureError(f"invalid row-count metadata for {name}")
        if type(columns) is not int or columns != len(fields):
            raise EnergyClosureError(f"invalid column-count metadata for {name}")
        if size_bytes != path.stat().st_size or digest != _sha256(path):
            raise EnergyClosureError(f"integrity mismatch for {name}")
        records = _read_verified_csv(
            path, fields, name, boolean_fields=bool_fields, blank_fields=blank_fields
        )
        if len(records) != data_rows:
            raise EnergyClosureError(f"CSV row-count mismatch for {name}")
        parsed[key] = records
        verified[key] = {
            "file": name, "sha256": digest, "size_bytes": size_bytes,
            "data_rows": data_rows, "columns": columns,
        }

    summary_rows = parsed["summary_csv"]
    if len(summary_rows) != len(LEVELS):
        raise EnergyClosureError("summary CSV must contain exactly four refinement rows")
    summary_by_level = {}
    for index, (row, label) in enumerate(zip(summary_rows, LEVELS)):
        intervals = contract["base_intervals"] * (2 ** index)
        expected_step = contract["duration"] / intervals
        if row["case_id"] != manifest["case_id"] or row["step_level"] != label:
            raise EnergyClosureError(f"summary row identity/order mismatch at {label}")
        interval_value = float(row["intervals"])
        sample_value = float(row["samples"])
        if not interval_value.is_integer() or not sample_value.is_integer():
            raise EnergyClosureError(f"summary interval/sample fields must be integers at {label}")
        if int(interval_value) != intervals or int(sample_value) != intervals + 1:
            raise EnergyClosureError(f"summary interval/sample count mismatch at {label}")
        if not math.isclose(float(row["step_s"]), expected_step, rel_tol=1e-9, abs_tol=1e-12):
            raise EnergyClosureError(f"summary step size mismatch at {label}")
        if row["status"] != contract["status"]:
            raise EnergyClosureError(f"summary status disagrees with manifest at {label}")
        if row["empirical_residual_order_from_previous"] != "":
            raise EnergyClosureError(f"empirical residual order must remain unreported at {label}")
        threshold_text = row["energy_closure_threshold"]
        if contract["threshold"] is None:
            if threshold_text != "":
                raise EnergyClosureError(f"summary threshold should be blank at {label}")
        elif not math.isclose(float(threshold_text), contract["threshold"], rel_tol=1e-12, abs_tol=0.0):
            raise EnergyClosureError(f"summary threshold disagrees with manifest at {label}")
        if float(row["normalized_energy_residual"]) < 0 or float(row["normalized_energy_residual_trapezoid"]) < 0:
            raise EnergyClosureError(f"negative normalized residual at {label}")
        expected_diagnostics = _energy_diagnostics(
            {
                "terminal_input": float(row["terminal_input_work_J"]),
                "copper": float(row["copper_loss_J"]),
                "structural": float(row["structural_damping_loss_J"]),
                "friction": float(row["axis_friction_loss_J"]),
                "external": float(row["external_generalized_work_J"]),
                "mismatch": float(row["electromechanical_mismatch_work_J"]),
            },
            float(row["energy_residual_simpson_J"]),
            float(manifest["energy_normalization_scale_J"]),
            float(manifest["energy_normalization_floor_J"]),
            float(row["absolute_net_power_work_J"]),
            float(row["energy_residual_trapezoid_J"]),
        )
        for field, expected_value in expected_diagnostics.items():
            actual_value = float(row[field])
            if not math.isclose(actual_value, expected_value, rel_tol=1e-9, abs_tol=1e-12):
                raise EnergyClosureError(f"summary diagnostic {field} is inconsistent at {label}")
        report = manifest["limiter_stage_reports"][index]
        summary_counts = {
            "expected_rk4_stage_evaluations": report["expected_stage_evaluations"],
            "observed_rk4_stage_evaluations": report["stage_evaluations"],
            "current_reference_saturated_stages": report["current_reference_saturated_stages"],
            "voltage_saturated_stages": report["voltage_saturated_stages"],
            "any_limiter_active_stages": report["any_limiter_active_stages"],
        }
        for field, expected_value in summary_counts.items():
            if not float(row[field]).is_integer() or int(float(row[field])) != expected_value:
                raise EnergyClosureError(f"summary {field} disagrees with manifest at {label}")
        if row["stage_count_matches_expected"] != str(report["stage_count_matches_expected"]):
            raise EnergyClosureError(f"summary stage-count flag disagrees with manifest at {label}")
        if row["smooth_unsaturated"] != str(report["smooth_unsaturated"]):
            raise EnergyClosureError(f"summary smooth-unsaturated flag disagrees with manifest at {label}")
        summary_by_level[label] = row
    timeseries_rows = parsed["timeseries_csv"]
    cursor = 0
    for index, label in enumerate(LEVELS):
        intervals = contract["base_intervals"] * (2 ** index)
        samples = intervals + 1
        step = contract["duration"] / intervals
        block = timeseries_rows[cursor:cursor + samples]
        if len(block) != samples:
            raise EnergyClosureError(f"timeseries sample count mismatch at {label}")
        previous_time = None
        for sample_index, row in enumerate(block):
            expected_time = sample_index * step
            if row["case_id"] != manifest["case_id"] or row["step_level"] != label:
                raise EnergyClosureError(f"timeseries row identity/order mismatch at {label}")
            if not math.isclose(float(row["step_s"]), step, rel_tol=1e-9, abs_tol=1e-12):
                raise EnergyClosureError(f"timeseries step size mismatch at {label}")
            time_s = float(row["time_s"])
            if previous_time is not None and time_s <= previous_time:
                raise EnergyClosureError(f"timeseries time is not strictly increasing at {label}")
            if not math.isclose(time_s, expected_time, rel_tol=1e-9, abs_tol=1e-12):
                raise EnergyClosureError(f"timeseries time grid mismatch at {label}")
            previous_time = time_s
        if int(float(summary_by_level[label]["samples"])) != len(block):
            raise EnergyClosureError(f"timeseries/summary row count mismatch at {label}")
        cursor += samples
    if cursor != len(timeseries_rows):
        raise EnergyClosureError("timeseries contains unexpected extra rows")
    threshold = contract["threshold"]
    if not contract["all_stage_counts_match"]:
        expected_status = "FAIL"
    elif threshold is None or not contract["all_smooth"]:
        expected_status = "COMPLETED_REPORT_ONLY"
    elif all(float(summary_by_level[level]["normalized_energy_residual"]) <= threshold
             for level in ("h/4", "h/8")):
        expected_status = "PASS"
    else:
        expected_status = "FAIL"
    if contract["status"] != expected_status:
        raise EnergyClosureError("manifest status is inconsistent with threshold/limiter/summary results")
    return {
        "case_id": manifest["case_id"], "status": "VERIFIED",
        "recorded_status": contract["status"], "manifest_json": str(manifest_path),
        "artifacts": verified,
    }


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
        diagnostics = _energy_diagnostics(
            integrals, residual, v["scale"], v["floor"], abs_work, trap_residual
        )
        finite_metrics = [delta, *integrals.values(), abs_work, residual, rho,
                          trap_residual, trap_rho, *diagnostics.values()]
        if not all(math.isfinite(float(value)) for value in finite_metrics):
            raise FloatingPointError(f"non-finite ENE closure metric or component integral at {label}")
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
        # The protocol requires a predeclared residual noise floor and stable,
        # non-crossing residuals before estimating empirical order. The config
        # schema has no such floor yet, so suppress the estimate.
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
            **diagnostics,
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
    all_stage_counts_match = all(item["stage_count_matches_expected"] for item in saturation_by_level)
    if not all_stage_counts_match:
        status = "FAIL"
    elif v["threshold"] is None or not all_smooth:
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
            "Residual empirical order is intentionally omitted until a predeclared noise floor and stability gate are configured.",
            "Bundle files are staged first and then published by per-file atomic replacement; the three-file bundle is not a single filesystem transaction.",
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
