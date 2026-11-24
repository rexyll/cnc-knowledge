#!/usr/bin/env python3
"""Fixed-step RK4 convergence screen for a declared synthetic CH12 fixture.

The screen compares four nested integrations of the same continuous model.
It is not a machine-accuracy acceptance test, sampled-drive simulation, HIL
result, or substitute for sourced machine parameters.
Python 3.10+ and NumPy are required.
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
PATH_SUPPORT_PATH = ROOT / "gantry_joint_drive_path_comparison.py"
CONFIG_SCHEMA_VERSION = 1
LEVELS = ("h", "h/2", "h/4", "h/8")
STATE_FIELDS = [
    "q1_m", "q2_rad", "q3_m", "q4_rad",
    "qdot1_m_s", "qdot2_rad_s", "qdot3_m_s", "qdot4_rad_s",
    "s_m", "s_dot_m_s", "current_A", "current_integrator_V",
]
STATE_UNITS = {
    "q1_m": "m", "q2_rad": "rad", "q3_m": "m", "q4_rad": "rad",
    "qdot1_m_s": "m/s", "qdot2_rad_s": "rad/s",
    "qdot3_m_s": "m/s", "qdot4_rad_s": "rad/s",
    "s_m": "m", "s_dot_m_s": "m/s",
    "current_A": "A", "current_integrator_V": "V",
}
TIMESERIES_FIELDS = [
    "case_id", "level", "interval_index", "time_s", "step_s", *STATE_FIELDS,
]
LEVEL_FIELDS = [
    "case_id", "level", "intervals", "step_s", "samples",
    "stage_evaluations", "expected_stage_evaluations",
    "current_reference_saturated_stages", "voltage_saturated_stages",
    "any_limiter_active_stages", "stage_count_matches_expected",
    "smooth_unsaturated", "all_states_finite",
]
PAIR_FIELDS = [
    "case_id", "coarse_level", "fine_level",
    "coarse_step_s", "fine_step_s", "samples",
    "normalized_rms_difference", "normalized_max_difference",
    "observed_order_from_this_pair", "screen_next_order",
]
for _field in STATE_FIELDS:
    PAIR_FIELDS.extend((
        f"{_field}_max_abs_difference",
        f"{_field}_rms_difference",
        f"{_field}_max_normalized_difference",
        f"{_field}_rms_normalized_difference",
    ))

TIMESERIES_NAME = "rk4-01-synthetic-timeseries.csv"
LEVELS_NAME = "rk4-01-level-summary.csv"
PAIRS_NAME = "rk4-01-adjacent-differences.csv"
MANIFEST_NAME = "rk4-01-run-manifest.json"


class RK4ScreenError(ValueError):
    """Invalid input, numerical screen failure, or invalid archive."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _file_sha256(path: Path) -> str:
    return _sha256(path.read_bytes())


def _number(value: Any, name: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RK4ScreenError(f"{name} must be a finite number")
    number = float(value)
    if not math.isfinite(number) or (positive and number <= 0.0):
        raise RK4ScreenError(f"{name} must be finite" + (" and positive" if positive else ""))
    return number


def _safe_git_sha() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], check=True, capture_output=True,
            text=True, cwd=Path.cwd(),
        )
        value = result.stdout.strip()
        return value if len(value) == 40 else "UNKNOWN"
    except (OSError, subprocess.SubprocessError):
        return "UNKNOWN"


def _validate(config: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(config, dict) or type(config.get("schema_version")) is not int:
        raise RK4ScreenError("configuration must be an object with integer schema_version")
    if config["schema_version"] != CONFIG_SCHEMA_VERSION:
        raise RK4ScreenError(f"unsupported schema_version; expected {CONFIG_SCHEMA_VERSION}")
    if config.get("case_id") != "RK4-01":
        raise RK4ScreenError("case_id must be RK4-01")

    provenance = config.get("provenance")
    if not isinstance(provenance, dict):
        raise RK4ScreenError("provenance must be an object")
    parameter_source = provenance.get("parameter_source")
    if not isinstance(parameter_source, str) or "synthetic" not in parameter_source.lower():
        raise RK4ScreenError("RK4-01 requires an explicitly labelled synthetic parameter source")
    source_ids = provenance.get("source_documents_or_measurement_ids")
    if not isinstance(source_ids, list) or any(
        not isinstance(item, str) or not item.strip() for item in source_ids
    ):
        raise RK4ScreenError("provenance source IDs must be an array of non-empty strings")
    source_ids = [item.strip() for item in source_ids]
    if len(set(source_ids)) != len(source_ids):
        raise RK4ScreenError("provenance source IDs must be unique")

    model, initial, external = path_support._build_model(config)
    controller = config.get("controller_and_loads")
    if not isinstance(controller, dict) or controller.get("current_command_model") != "constant_current":
        raise RK4ScreenError("RK4-01 supports only the declared smooth constant_current callback")
    current_command = _number(
        controller.get("feedforward_current_A"),
        "controller_and_loads.feedforward_current_A",
    )

    integration = config.get("integration")
    if not isinstance(integration, dict):
        raise RK4ScreenError("integration must be an object")
    duration = _number(integration.get("duration_s"), "integration.duration_s", positive=True)
    base_step = _number(integration.get("base_step_s"), "integration.base_step_s", positive=True)
    ratio = duration / base_step
    if not math.isfinite(ratio) or ratio > 100_000:
        raise RK4ScreenError("duration/base_step is outside the supported range")
    intervals = int(round(ratio))
    if intervals < 2 or intervals % 2 or not math.isclose(
        intervals * base_step, duration, rel_tol=1e-9, abs_tol=1e-12
    ):
        raise RK4ScreenError("duration/base_step must define an even integer interval count")
    if integration.get("refinement_schedule") != list(LEVELS):
        raise RK4ScreenError("refinement_schedule must be [h,h/2,h/4,h/8]")
    total_samples = sum(intervals * (2 ** i) + 1 for i in range(4))
    total_stages = sum(4 * intervals * (2 ** i) for i in range(4))
    if total_samples > 100_000 or total_stages > 400_000:
        raise RK4ScreenError("requested refinement schedule exceeds the configured resource limit")

    metrics = config.get("metrics")
    if not isinstance(metrics, dict):
        raise RK4ScreenError("metrics must be an object")
    scales = metrics.get("state_characteristic_scales")
    if not isinstance(scales, dict) or set(scales) != set(STATE_FIELDS):
        raise RK4ScreenError("state_characteristic_scales must contain exactly all 12 state fields")
    normalized_scales = {
        key: _number(scales[key], f"metrics.state_characteristic_scales.{key}", positive=True)
        for key in STATE_FIELDS
    }
    scale_source = metrics.get("state_characteristic_scale_source")
    if not isinstance(scale_source, str) or not scale_source.strip():
        raise RK4ScreenError("state_characteristic_scale_source is required")
    scale_source_ids = metrics.get("state_characteristic_scale_source_ids")
    if not isinstance(scale_source_ids, list) or not scale_source_ids or any(
        not isinstance(item, str) or not item.strip() for item in scale_source_ids
    ):
        raise RK4ScreenError("state_characteristic_scale_source_ids must be a non-empty string array")
    scale_source_ids = [item.strip() for item in scale_source_ids]
    if len(set(scale_source_ids)) != len(scale_source_ids):
        raise RK4ScreenError("state characteristic scale source IDs must be unique")
    screen = metrics.get("numerical_screen")
    if not isinstance(screen, dict):
        raise RK4ScreenError("metrics.numerical_screen must be an object")
    minimum_order = _number(
        screen.get("observed_order_min"),
        "metrics.numerical_screen.observed_order_min",
        positive=True,
    )
    if minimum_order < 3.0:
        raise RK4ScreenError("observed_order_min must be at least 3.0 for this RK4 screen")

    model.pack(initial)
    return {
        "case_id": "RK4-01",
        "model": model,
        "initial": initial,
        "external": np.asarray(external, dtype=float),
        "duration": duration,
        "base_step": base_step,
        "intervals": intervals,
        "current_command": current_command,
        "parameter_source": parameter_source.strip(),
        "source_ids": source_ids,
        "scales": normalized_scales,
        "scale_source": scale_source.strip(),
        "scale_source_ids": scale_source_ids,
        "minimum_order": minimum_order,
    }


def _atomic_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", newline="", dir=path.parent,
        prefix=f".{path.name}.", suffix=".tmp", delete=False,
    ) as stream:
        temp_path = Path(stream.name)
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp_path, path)


def _artifact_record(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "file_name": path.name,
        "sha256": _sha256(data),
        "size_bytes": len(data),
        "data_rows": len(rows),
        "columns": len(fields),
    }


def _adjacent_pair(
    case_id: str,
    coarse_label: str,
    fine_label: str,
    coarse_step: float,
    fine_step: float,
    coarse_times: np.ndarray,
    coarse_states: np.ndarray,
    fine_times: np.ndarray,
    fine_states: np.ndarray,
    scales: np.ndarray,
) -> tuple[dict[str, Any], float]:
    sampled_times = fine_times[::2]
    sampled_states = fine_states[::2]
    if sampled_states.shape != coarse_states.shape or sampled_times.shape != coarse_times.shape:
        raise RK4ScreenError(f"{coarse_label}/{fine_label} grids are not nested")
    if not np.allclose(sampled_times, coarse_times, rtol=0.0, atol=2e-12):
        raise RK4ScreenError(f"{coarse_label}/{fine_label} time grids do not align")
    delta = sampled_states - coarse_states
    if not np.all(np.isfinite(delta)):
        raise FloatingPointError(f"non-finite state difference at {coarse_label}/{fine_label}")
    normalized = delta / scales[None, :]
    normalized_rms = float(np.sqrt(np.mean(normalized * normalized)))
    normalized_max = float(np.max(np.abs(normalized)))
    row: dict[str, Any] = {
        "case_id": case_id,
        "coarse_level": coarse_label,
        "fine_level": fine_label,
        "coarse_step_s": coarse_step,
        "fine_step_s": fine_step,
        "samples": int(coarse_times.size),
        "normalized_rms_difference": normalized_rms,
        "normalized_max_difference": normalized_max,
        "observed_order_from_this_pair": "",
        "screen_next_order": "",
    }
    for index, field in enumerate(STATE_FIELDS):
        component = delta[:, index]
        component_norm = normalized[:, index]
        row[f"{field}_max_abs_difference"] = float(np.max(np.abs(component)))
        row[f"{field}_rms_difference"] = float(np.sqrt(np.mean(component * component)))
        row[f"{field}_max_normalized_difference"] = float(np.max(np.abs(component_norm)))
        row[f"{field}_rms_normalized_difference"] = float(
            np.sqrt(np.mean(component_norm * component_norm))
        )
    return row, normalized_rms


def run(config_path: Path, output_dir: Path) -> dict[str, Any]:
    config_path = config_path.resolve()
    config_bytes = config_path.read_bytes()
    config = json.loads(config_bytes.decode("utf-8"))
    v = _validate(config)
    output = output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)

    started = datetime.now(timezone.utc).isoformat()
    model = v["model"]
    current_command = v["current_command"]
    external = v["external"]
    times_by_level: list[np.ndarray] = []
    states_by_level: list[np.ndarray] = []
    level_rows: list[dict[str, Any]] = []
    timeseries_rows: list[dict[str, Any]] = []

    for level_index, label in enumerate(LEVELS):
        intervals = v["intervals"] * (2 ** level_index)
        step = v["duration"] / intervals
        observations = {"count": 0, "reference": 0, "voltage": 0, "any": 0}

        def tracked_command(time_s: float, state: Any) -> float:
            diagnostic = model.electrical_diagnostics(state, current_command)
            reference_limited = diagnostic["current_reference_A"] != current_command
            voltage_limited = bool(diagnostic["voltage_saturated"])
            observations["count"] += 1
            observations["reference"] += int(reference_limited)
            observations["voltage"] += int(voltage_limited)
            observations["any"] += int(reference_limited or voltage_limited)
            return current_command

        def external_force(_time_s: float, _state: Any) -> np.ndarray:
            return external.copy()

        times, states = model.simulate(
            v["initial"].copy(), v["duration"], step,
            tracked_command, external_force,
        )
        expected_stages = 4 * intervals
        stage_match = observations["count"] == expected_stages
        smooth = stage_match and observations["any"] == 0
        all_finite = bool(np.all(np.isfinite(states)))
        if not all_finite:
            raise FloatingPointError(f"non-finite state values at {label}")
        level_rows.append({
            "case_id": v["case_id"], "level": label,
            "intervals": intervals, "step_s": step, "samples": int(times.size),
            "stage_evaluations": observations["count"],
            "expected_stage_evaluations": expected_stages,
            "current_reference_saturated_stages": observations["reference"],
            "voltage_saturated_stages": observations["voltage"],
            "any_limiter_active_stages": observations["any"],
            "stage_count_matches_expected": str(stage_match),
            "smooth_unsaturated": str(smooth),
            "all_states_finite": str(all_finite),
        })
        times_by_level.append(np.asarray(times, dtype=float))
        states_by_level.append(np.asarray(states, dtype=float))
        for index, (time_s, state) in enumerate(zip(times, states)):
            row: dict[str, Any] = {
                "case_id": v["case_id"], "level": label,
                "interval_index": index, "time_s": float(time_s), "step_s": step,
            }
            row.update({field: float(state[column]) for column, field in enumerate(STATE_FIELDS)})
            timeseries_rows.append(row)

    scales = np.asarray([v["scales"][field] for field in STATE_FIELDS], dtype=float)
    pair_rows: list[dict[str, Any]] = []
    pair_differences: list[float] = []
    for index in range(3):
        row, difference = _adjacent_pair(
            v["case_id"], LEVELS[index], LEVELS[index + 1],
            v["duration"] / (v["intervals"] * (2 ** index)),
            v["duration"] / (v["intervals"] * (2 ** (index + 1))),
            times_by_level[index], states_by_level[index],
            times_by_level[index + 1], states_by_level[index + 1],
            scales,
        )
        pair_rows.append(row)
        pair_differences.append(difference)

    orders: list[float | None] = []
    for coarse_difference, fine_difference in zip(pair_differences, pair_differences[1:]):
        if coarse_difference <= 0.0 or fine_difference <= 0.0:
            orders.append(None)
        else:
            orders.append(float(math.log2(coarse_difference / fine_difference)))
    if orders:
        pair_rows[0]["observed_order_from_this_pair"] = orders[0] if orders[0] is not None else ""
        pair_rows[1]["observed_order_from_this_pair"] = orders[1] if orders[1] is not None else ""

    all_finite = all(row["all_states_finite"] == "True" for row in level_rows)
    stage_counts_match = all(row["stage_count_matches_expected"] == "True" for row in level_rows)
    all_smooth = all(row["smooth_unsaturated"] == "True" for row in level_rows)
    monotone_reduction = (
        pair_differences[0] > pair_differences[1] > pair_differences[2] > 0.0
    )
    orders_eligible = all(order is not None and math.isfinite(order) for order in orders)
    order_screen = bool(
        orders_eligible and all(float(order) >= v["minimum_order"] for order in orders)
    )
    screen_pass = all_finite and stage_counts_match and all_smooth and monotone_reduction and order_screen
    recorded_status = "COMPLETED_REPORT_ONLY" if screen_pass else "FAIL"

    for index, row in enumerate(pair_rows):
        if index < len(orders):
            row["screen_next_order"] = (
                "PASS_NUMERICAL_SCREEN"
                if orders[index] is not None and orders[index] >= v["minimum_order"]
                else "FAIL_NUMERICAL_SCREEN"
            )
        else:
            row["screen_next_order"] = "NOT_APPLICABLE"

    _atomic_csv(output / TIMESERIES_NAME, TIMESERIES_FIELDS, timeseries_rows)
    _atomic_csv(output / LEVELS_NAME, LEVEL_FIELDS, level_rows)
    _atomic_csv(output / PAIRS_NAME, PAIR_FIELDS, pair_rows)
    artifact_specs = {
        TIMESERIES_NAME: (TIMESERIES_FIELDS, timeseries_rows),
        LEVELS_NAME: (LEVEL_FIELDS, level_rows),
        PAIRS_NAME: (PAIR_FIELDS, pair_rows),
    }
    artifacts = {
        name: _artifact_record(output / name, fields, rows)
        for name, (fields, rows) in artifact_specs.items()
    }
    completed = datetime.now(timezone.utc).isoformat()
    manifest = {
        "schema_version": 1,
        "case_id": v["case_id"],
        "status": recorded_status,
        "numerical_results_present": True,
        "engineering_acceptance_applied": False,
        "parameter_source": v["parameter_source"],
        "source_documents_or_measurement_ids": v["source_ids"],
        "characteristic_scale_source": v["scale_source"],
        "characteristic_scale_source_ids": v["scale_source_ids"],
        "state_vector_order": STATE_FIELDS,
        "state_vector_units": STATE_UNITS,
        "state_characteristic_scales": v["scales"],
        "started_at_utc": started,
        "completed_at_utc": completed,
        "duration_s": v["duration"],
        "base_step_s": v["base_step"],
        "base_intervals": v["intervals"],
        "refinement_schedule": list(LEVELS),
        "level_reports": level_rows,
        "adjacent_pair_normalized_rms_differences": pair_differences,
        "pairwise_observed_orders": orders,
        "numerical_screen": {
            "finite_states": all_finite,
            "rk4_stage_counts_match": stage_counts_match,
            "all_refinements_smooth_unsaturated": all_smooth,
            "adjacent_differences_monotonically_decrease": monotone_reduction,
            "observed_order_minimum": v["minimum_order"],
            "observed_order_screen_pass": order_screen,
            "screen_pass": screen_pass,
        },
        "interpretation": [
            "This is a synthetic continuous-time model run, not a machine parameter set or machine performance result.",
            "The reported pairwise orders are finite-grid diagnostics based on adjacent solution differences, not a proof of an asymptotic error bound.",
            "COMPLETED_REPORT_ONLY means the numerical convergence screen passed; no application accuracy limits or machine acceptance criteria were applied.",
            "The solver command is a constant current reference and the model does not include sampled drive scheduling, PWM, communication delay, hard stops, contact, or hardware protection.",
        ],
        "config_sha256": _sha256(config_bytes),
        "solver_sha256": _file_sha256(SOLVER_PATH),
        "path_support_sha256": _file_sha256(PATH_SUPPORT_PATH),
        "runner_sha256": _file_sha256(Path(__file__)),
        "git_sha": _safe_git_sha(),
        "python_version": sys.version,
        "numpy_version": np.__version__,
        "operating_system": platform.platform(),
        "command_line": " ".join(sys.argv),
        "output_artifacts": artifacts,
    }
    manifest_path = output / MANIFEST_NAME
    payload = (json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
    with tempfile.NamedTemporaryFile(
        mode="wb", dir=output, prefix=f".{MANIFEST_NAME}.", suffix=".tmp", delete=False
    ) as stream:
        temp_path = Path(stream.name)
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp_path, manifest_path)
    return {
        "case_id": v["case_id"],
        "status": recorded_status,
        "output_dir": str(output),
        "pairwise_normalized_rms_differences": pair_differences,
        "pairwise_observed_orders": orders,
        "numerical_screen": manifest["numerical_screen"],
        "manifest": str(manifest_path),
        "output_artifacts": artifacts,
    }


def verify_archive(output_dir: Path) -> dict[str, Any]:
    output = output_dir.resolve()
    manifest_path = output / MANIFEST_NAME
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RK4ScreenError(f"cannot read RK4 manifest: {error}") from error
    if manifest.get("schema_version") != 1 or manifest.get("case_id") != "RK4-01":
        raise RK4ScreenError("unsupported RK4 archive manifest")
    artifacts = manifest.get("output_artifacts")
    if not isinstance(artifacts, dict) or set(artifacts) != {
        TIMESERIES_NAME, LEVELS_NAME, PAIRS_NAME
    }:
        raise RK4ScreenError("RK4 archive artifact list is incomplete")
    verified = {}
    for name, record in artifacts.items():
        if Path(name).name != name or not isinstance(record, dict):
            raise RK4ScreenError("RK4 archive contains an invalid artifact path or record")
        path = output / name
        try:
            data = path.read_bytes()
        except OSError as error:
            raise RK4ScreenError(f"missing RK4 artifact {name}: {error}") from error
        if len(data) != record.get("size_bytes") or _sha256(data) != record.get("sha256"):
            raise RK4ScreenError(f"RK4 artifact integrity mismatch: {name}")
        with path.open("r", encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream)
            if len(reader.fieldnames or []) != record.get("columns"):
                raise RK4ScreenError(f"RK4 CSV column count mismatch: {name}")
            row_count = sum(1 for _ in reader)
        if row_count != record.get("data_rows"):
            raise RK4ScreenError(f"RK4 CSV row count mismatch: {name}")
        verified[name] = {"sha256": record["sha256"], "data_rows": row_count}
    return {
        "archive_status": "VERIFIED_INTEGRITY_ONLY",
        "recorded_numerical_status": manifest.get("status"),
        "manifest": str(manifest_path),
        "verified_artifacts": verified,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the RK4-01 synthetic fixed-step convergence screen.")
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
        print(f"RK4 SCREEN ERROR: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    if result.get("status") == "FAIL" or result.get("recorded_numerical_status") == "FAIL":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
