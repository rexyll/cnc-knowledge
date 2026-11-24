#!/usr/bin/env python3
"""Synthetic scalar seven-segment jerk-limited S-curve reference profile.

The classical third-order S-curve bounds jerk but has piecewise-constant jerk
jumps at phase boundaries. It is a scalar rest-to-rest reference, not a
multi-axis CNC look-ahead or snap-limited planner.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

SCHEMA_VERSION = 1
CASE_ID = "SCURVE-01"
MANIFEST_NAME = "cnc-scurve-profile-run-manifest.json"
TIMESERIES_NAME = "cnc-scurve-profile-timeseries.csv"
SEGMENTS_NAME = "cnc-scurve-profile-segments.csv"
SUMMARY_NAME = "cnc-scurve-profile-summary.csv"

TIME_FIELDS = (
    "sample_index", "time_s", "position_m", "velocity_m_s",
    "acceleration_m_s2", "jerk_m_s3", "segment_index", "segment_name",
)
SEGMENT_FIELDS = (
    "segment_index", "segment_name", "start_time_s", "duration_s",
    "end_time_s", "jerk_m_s3", "start_position_m", "start_velocity_m_s",
    "start_acceleration_m_s2", "end_position_m", "end_velocity_m_s",
    "end_acceleration_m_s2",
)
SUMMARY_FIELDS = (
    "case_id", "distance_m", "max_velocity_m_s", "max_acceleration_m_s2",
    "max_jerk_m_s3", "peak_velocity_m_s", "peak_acceleration_m_s2",
    "peak_jerk_m_s3", "acceleration_jerk_ramp_s", "constant_acceleration_s",
    "cruise_s", "total_time_s", "sample_period_s", "sample_count",
    "phase_count", "end_position_m", "end_velocity_m_s",
    "end_acceleration_m_s2", "status",
)
PHASE_NAMES = (
    "positive_jerk_ramp", "constant_positive_acceleration",
    "negative_jerk_ramp", "constant_velocity", "negative_jerk_ramp",
    "constant_negative_acceleration", "positive_jerk_ramp",
)


class SCurveError(ValueError):
    """Invalid profile configuration or generated result."""


@dataclass(frozen=True)
class Phase:
    index: int
    name: str
    duration_s: float
    jerk_m_s3: float


@dataclass(frozen=True)
class KinematicState:
    time_s: float
    position_m: float
    velocity_m_s: float
    acceleration_m_s2: float
    jerk_m_s3: float
    segment_index: int
    segment_name: str


@dataclass(frozen=True)
class PhaseBoundary:
    phase: Phase
    start_time_s: float
    start_position_m: float
    start_velocity_m_s: float
    start_acceleration_m_s2: float
    end_time_s: float
    end_position_m: float
    end_velocity_m_s: float
    end_acceleration_m_s2: float


@dataclass(frozen=True)
class SCurveProfile:
    distance_m: float
    max_velocity_m_s: float
    max_acceleration_m_s2: float
    max_jerk_m_s3: float
    peak_velocity_m_s: float
    peak_acceleration_m_s2: float
    peak_jerk_m_s3: float
    sample_period_s: float
    phases: tuple[Phase, ...]
    boundaries: tuple[PhaseBoundary, ...]
    total_time_s: float

    def evaluate(self, time_s: float) -> KinematicState:
        t = _finite_number(time_s, "time_s")
        if t < -1e-12 or t > self.total_time_s + 1e-10:
            raise SCurveError("time_s is outside the planned profile")
        if t >= self.total_time_s - 1e-12:
            return KinematicState(
                self.total_time_s, self.distance_m, 0.0, 0.0, 0.0,
                len(self.phases) - 1, "terminal_boundary",
            )
        t = max(0.0, t)
        for boundary in self.boundaries:
            phase = boundary.phase
            if phase.duration_s <= 0.0:
                continue
            if t < boundary.end_time_s - 1e-13:
                tau = max(0.0, t - boundary.start_time_s)
                jerk = phase.jerk_m_s3
                position = (
                    boundary.start_position_m
                    + boundary.start_velocity_m_s * tau
                    + 0.5 * boundary.start_acceleration_m_s2 * tau * tau
                    + jerk * tau * tau * tau / 6.0
                )
                velocity = (
                    boundary.start_velocity_m_s
                    + boundary.start_acceleration_m_s2 * tau
                    + 0.5 * jerk * tau * tau
                )
                acceleration = boundary.start_acceleration_m_s2 + jerk * tau
                return KinematicState(
                    t, position, velocity, acceleration, jerk,
                    phase.index, phase.name,
                )
        return KinematicState(
            self.total_time_s, self.distance_m, 0.0, 0.0, 0.0,
            len(self.phases) - 1, "terminal_boundary",
        )

    def sample_times(self) -> tuple[float, ...]:
        count = int(math.floor(self.total_time_s / self.sample_period_s))
        times = [i * self.sample_period_s for i in range(count + 1)]
        if not times or self.total_time_s - times[-1] > 1e-12:
            times.append(self.total_time_s)
        else:
            times[-1] = self.total_time_s
        return tuple(min(t, self.total_time_s) for t in times)


def _finite_number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SCurveError(f"{name} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise SCurveError(f"{name} must be a finite number")
    return result


def _positive(value: Any, name: str) -> float:
    result = _finite_number(value, name)
    if result <= 0.0:
        raise SCurveError(f"{name} must be positive")
    return result


def _acceleration_phase(
    peak_velocity_m_s: float,
    max_acceleration_m_s2: float,
    max_jerk_m_s3: float,
) -> tuple[float, float, float]:
    """Return jerk-ramp duration, constant-acceleration duration, total T_acc."""
    if peak_velocity_m_s <= 0.0:
        return 0.0, 0.0, 0.0
    transition_velocity = max_acceleration_m_s2**2 / max_jerk_m_s3
    if peak_velocity_m_s <= transition_velocity:
        jerk_time = math.sqrt(peak_velocity_m_s / max_jerk_m_s3)
        constant_acceleration_time = 0.0
    else:
        jerk_time = max_acceleration_m_s2 / max_jerk_m_s3
        constant_acceleration_time = (
            peak_velocity_m_s / max_acceleration_m_s2 - jerk_time
        )
    return jerk_time, constant_acceleration_time, (
        2.0 * jerk_time + constant_acceleration_time
    )


def _accel_decel_distance(
    peak_velocity_m_s: float,
    max_acceleration_m_s2: float,
    max_jerk_m_s3: float,
) -> float:
    _, _, acceleration_time = _acceleration_phase(
        peak_velocity_m_s, max_acceleration_m_s2, max_jerk_m_s3
    )
    # Symmetric acceleration and deceleration each cover v_peak*T_acc/2.
    return peak_velocity_m_s * acceleration_time


def plan_rest_to_rest(
    distance_m: float,
    max_velocity_m_s: float,
    max_acceleration_m_s2: float,
    max_jerk_m_s3: float,
    sample_period_s: float,
) -> SCurveProfile:
    """Plan a minimum-time symmetric scalar seven-segment rest-to-rest profile."""
    distance = _positive(distance_m, "distance_m")
    velocity_limit = _positive(max_velocity_m_s, "max_velocity_m_s")
    acceleration_limit = _positive(max_acceleration_m_s2, "max_acceleration_m_s2")
    jerk_limit = _positive(max_jerk_m_s3, "max_jerk_m_s3")
    sample_period = _positive(sample_period_s, "sample_period_s")

    distance_at_velocity_limit = _accel_decel_distance(
        velocity_limit, acceleration_limit, jerk_limit
    )
    if distance >= distance_at_velocity_limit:
        peak_velocity = velocity_limit
        _, _, acceleration_time = _acceleration_phase(
            peak_velocity, acceleration_limit, jerk_limit
        )
        cruise_time = (distance - distance_at_velocity_limit) / peak_velocity
    else:
        low, high = 0.0, velocity_limit
        for _ in range(120):
            mid = 0.5 * (low + high)
            if _accel_decel_distance(mid, acceleration_limit, jerk_limit) < distance:
                low = mid
            else:
                high = mid
        peak_velocity = 0.5 * (low + high)
        _, _, acceleration_time = _acceleration_phase(
            peak_velocity, acceleration_limit, jerk_limit
        )
        cruise_time = 0.0

    jerk_time, constant_acceleration_time, _ = _acceleration_phase(
        peak_velocity, acceleration_limit, jerk_limit
    )
    peak_acceleration = jerk_limit * jerk_time
    durations = (
        jerk_time, constant_acceleration_time, jerk_time, cruise_time,
        jerk_time, constant_acceleration_time, jerk_time,
    )
    jerks = (
        jerk_limit, 0.0, -jerk_limit, 0.0,
        -jerk_limit, 0.0, jerk_limit,
    )
    phases = tuple(
        Phase(i, PHASE_NAMES[i], durations[i], jerks[i]) for i in range(7)
    )

    total_time = sum(phase.duration_s for phase in phases)
    if not math.isfinite(total_time) or total_time <= 0.0:
        raise SCurveError("planned profile duration is invalid")
    if math.ceil(total_time / sample_period) + 1 > 1_000_000:
        raise SCurveError("sample grid exceeds the 1,000,000-row resource limit")

    boundaries: list[PhaseBoundary] = []
    elapsed = position = speed = acceleration = 0.0
    for phase in phases:
        duration = phase.duration_s
        end_position = (
            position + speed * duration
            + 0.5 * acceleration * duration**2
            + phase.jerk_m_s3 * duration**3 / 6.0
        )
        end_speed = (
            speed + acceleration * duration
            + 0.5 * phase.jerk_m_s3 * duration**2
        )
        end_acceleration = acceleration + phase.jerk_m_s3 * duration
        boundaries.append(PhaseBoundary(
            phase, elapsed, position, speed, acceleration,
            elapsed + duration, end_position, end_speed, end_acceleration,
        ))
        elapsed += duration
        position, speed, acceleration = end_position, end_speed, end_acceleration

    scale = max(1.0, distance)
    if abs(position - distance) > 1e-9 * scale:
        raise SCurveError("internal profile integration misses requested distance")
    if abs(speed) > 1e-9 or abs(acceleration) > 1e-9:
        raise SCurveError("internal profile integration does not end at rest")
    return SCurveProfile(
        distance, velocity_limit, acceleration_limit, jerk_limit,
        peak_velocity, peak_acceleration, jerk_limit, sample_period,
        phases, tuple(boundaries), total_time,
    )


def _validate_config(config: Any) -> dict[str, Any]:
    if not isinstance(config, dict):
        raise SCurveError("configuration root must be a JSON object")
    if config.get("schema_version") != SCHEMA_VERSION or config.get("case_id") != CASE_ID:
        raise SCurveError("configuration schema_version/case_id mismatch")
    provenance = config.get("provenance")
    source_ids = provenance.get("source_documents_or_measurement_ids") if isinstance(provenance, dict) else None
    if not isinstance(source_ids, list) or not source_ids or any(
        not isinstance(item, str) or not item.strip() for item in source_ids
    ):
        raise SCurveError("source_documents_or_measurement_ids must be non-empty")
    profile = config.get("profile")
    if not isinstance(profile, dict) or profile.get("type") != "third_order_seven_segment_s_curve":
        raise SCurveError("profile.type mismatch")
    return {
        "source_ids": [item.strip() for item in source_ids],
        "interpretation": str(config.get("interpretation", "")),
        "distance": _positive(profile.get("distance_m"), "profile.distance_m"),
        "velocity": _positive(profile.get("max_velocity_m_s"), "profile.max_velocity_m_s"),
        "acceleration": _positive(profile.get("max_acceleration_m_s2"), "profile.max_acceleration_m_s2"),
        "jerk": _positive(profile.get("max_jerk_m_s3"), "profile.max_jerk_m_s3"),
        "sample_period": _positive(profile.get("sample_period_s"), "profile.sample_period_s"),
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_csv(path: Path, fields: Iterable[str], rows: Iterable[dict[str, Any]]) -> int:
    count = 0
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=tuple(fields), extrasaction="raise")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
            count += 1
    return count


def _artifact(path: Path, rows: int, fields: tuple[str, ...]) -> dict[str, Any]:
    return {
        "file": path.name, "sha256": _sha256(path),
        "size_bytes": path.stat().st_size, "data_rows": rows,
        "columns": len(fields),
    }


def run_config(config_path: Path, output_dir: Path) -> dict[str, Any]:
    config_path = Path(config_path).resolve()
    output_dir = Path(output_dir).resolve()
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SCurveError(f"cannot read config: {exc}") from exc
    values = _validate_config(config)
    profile = plan_rest_to_rest(
        values["distance"], values["velocity"], values["acceleration"],
        values["jerk"], values["sample_period"],
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    sample_rows = []
    for index, time_s in enumerate(profile.sample_times()):
        state = profile.evaluate(time_s)
        sample_rows.append({
            "sample_index": index, "time_s": f"{state.time_s:.12g}",
            "position_m": f"{state.position_m:.15g}",
            "velocity_m_s": f"{state.velocity_m_s:.15g}",
            "acceleration_m_s2": f"{state.acceleration_m_s2:.15g}",
            "jerk_m_s3": f"{state.jerk_m_s3:.15g}",
            "segment_index": state.segment_index, "segment_name": state.segment_name,
        })
    timeseries_path = output_dir / TIMESERIES_NAME
    sample_count = _write_csv(timeseries_path, TIME_FIELDS, sample_rows)

    segment_rows = []
    for boundary in profile.boundaries:
        phase = boundary.phase
        segment_rows.append({
            "segment_index": phase.index, "segment_name": phase.name,
            "start_time_s": f"{boundary.start_time_s:.15g}",
            "duration_s": f"{phase.duration_s:.15g}",
            "end_time_s": f"{boundary.end_time_s:.15g}",
            "jerk_m_s3": f"{phase.jerk_m_s3:.15g}",
            "start_position_m": f"{boundary.start_position_m:.15g}",
            "start_velocity_m_s": f"{boundary.start_velocity_m_s:.15g}",
            "start_acceleration_m_s2": f"{boundary.start_acceleration_m_s2:.15g}",
            "end_position_m": f"{boundary.end_position_m:.15g}",
            "end_velocity_m_s": f"{boundary.end_velocity_m_s:.15g}",
            "end_acceleration_m_s2": f"{boundary.end_acceleration_m_s2:.15g}",
        })
    segments_path = output_dir / SEGMENTS_NAME
    segment_count = _write_csv(segments_path, SEGMENT_FIELDS, segment_rows)

    end = profile.evaluate(profile.total_time_s)
    summary_row = {
        "case_id": CASE_ID, "distance_m": f"{profile.distance_m:.15g}",
        "max_velocity_m_s": f"{profile.max_velocity_m_s:.15g}",
        "max_acceleration_m_s2": f"{profile.max_acceleration_m_s2:.15g}",
        "max_jerk_m_s3": f"{profile.max_jerk_m_s3:.15g}",
        "peak_velocity_m_s": f"{profile.peak_velocity_m_s:.15g}",
        "peak_acceleration_m_s2": f"{profile.peak_acceleration_m_s2:.15g}",
        "peak_jerk_m_s3": f"{profile.peak_jerk_m_s3:.15g}",
        "acceleration_jerk_ramp_s": f"{profile.boundaries[0].phase.duration_s:.15g}",
        "constant_acceleration_s": f"{profile.boundaries[1].phase.duration_s:.15g}",
        "cruise_s": f"{profile.boundaries[3].phase.duration_s:.15g}",
        "total_time_s": f"{profile.total_time_s:.15g}",
        "sample_period_s": f"{profile.sample_period_s:.15g}",
        "sample_count": sample_count, "phase_count": len(profile.phases),
        "end_position_m": f"{end.position_m:.15g}",
        "end_velocity_m_s": f"{end.velocity_m_s:.15g}",
        "end_acceleration_m_s2": f"{end.acceleration_m_s2:.15g}",
        "status": "COMPLETED_REPORT_ONLY",
    }
    summary_path = output_dir / SUMMARY_NAME
    summary_count = _write_csv(summary_path, SUMMARY_FIELDS, [summary_row])
    artifacts = {
        "timeseries_csv": _artifact(timeseries_path, sample_count, TIME_FIELDS),
        "segments_csv": _artifact(segments_path, segment_count, SEGMENT_FIELDS),
        "summary_csv": _artifact(summary_path, summary_count, SUMMARY_FIELDS),
    }
    manifest = {
        "schema_version": SCHEMA_VERSION, "case_id": CASE_ID,
        "status": "COMPLETED_REPORT_ONLY", "acceptance_decision": "DESCRIPTIVE_ONLY",
        "profile_type": "third_order_seven_segment_s_curve",
        "source_documents_or_measurement_ids": values["source_ids"],
        "interpretation": values["interpretation"],
        "config_sha256": _sha256(config_path),
        "runner_sha256": _sha256(Path(__file__).resolve()),
        "python_version": sys.version.split()[0],
        "operating_system": platform.platform(),
        "duration_s": profile.total_time_s,
        "profile_parameters": {
            "distance_m": profile.distance_m,
            "max_velocity_m_s": profile.max_velocity_m_s,
            "max_acceleration_m_s2": profile.max_acceleration_m_s2,
            "max_jerk_m_s3": profile.max_jerk_m_s3,
            "peak_velocity_m_s": profile.peak_velocity_m_s,
            "peak_acceleration_m_s2": profile.peak_acceleration_m_s2,
            "peak_jerk_m_s3": profile.peak_jerk_m_s3,
            "acceleration_jerk_ramp_s": profile.boundaries[0].phase.duration_s,
            "constant_acceleration_s": profile.boundaries[1].phase.duration_s,
            "cruise_s": profile.boundaries[3].phase.duration_s,
        },
        "output_artifacts": artifacts,
        "notes": [
            "All fixture inputs are synthetic, not machine specifications or recommended settings.",
            "Third-order seven-segment profile has bounded piecewise-constant jerk with jumps at phase boundaries.",
            "No multi-axis inverse kinematics, block-chain look-ahead, corner blending, snap limit, servo dynamics or machine acceptance is implemented.",
            "COMPLETED_REPORT_ONLY and DESCRIPTIVE_ONLY do not mean machine or application acceptance.",
        ],
    }
    (output_dir / MANIFEST_NAME).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def verify_archive(output_dir: Path) -> dict[str, Any]:
    output_dir = Path(output_dir).resolve()
    manifest_path = output_dir / MANIFEST_NAME
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SCurveError(f"cannot read manifest: {exc}") from exc
    if manifest.get("schema_version") != SCHEMA_VERSION or manifest.get("case_id") != CASE_ID:
        raise SCurveError("manifest identity/schema mismatch")
    if manifest.get("status") != "COMPLETED_REPORT_ONLY":
        raise SCurveError("manifest status mismatch")
    if manifest.get("acceptance_decision") != "DESCRIPTIVE_ONLY":
        raise SCurveError("manifest acceptance must remain descriptive-only")
    expected = (
        ("timeseries_csv", TIMESERIES_NAME, TIME_FIELDS),
        ("segments_csv", SEGMENTS_NAME, SEGMENT_FIELDS),
        ("summary_csv", SUMMARY_NAME, SUMMARY_FIELDS),
    )
    records = manifest.get("output_artifacts")
    if not isinstance(records, dict):
        raise SCurveError("manifest output_artifacts missing")
    verified = []
    for key, filename, fields in expected:
        record = records.get(key)
        path = output_dir / filename
        if not isinstance(record, dict) or not path.is_file():
            raise SCurveError(f"archive artifact missing: {filename}")
        if _sha256(path) != record.get("sha256") or path.stat().st_size != record.get("size_bytes"):
            raise SCurveError(f"archive hash/size mismatch: {filename}")
        with path.open("r", encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream)
            if tuple(reader.fieldnames or ()) != fields:
                raise SCurveError(f"archive column schema mismatch: {filename}")
            rows = list(reader)
        if len(rows) != record.get("data_rows") or len(fields) != record.get("columns"):
            raise SCurveError(f"archive row/column metadata mismatch: {filename}")
        if any(not row for row in rows):
            raise SCurveError(f"archive empty row: {filename}")
        verified.append(filename)
    return {
        "status": "VERIFIED", "recorded_status": manifest["status"],
        "acceptance_decision": manifest["acceptance_decision"],
        "artifacts": verified,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate and archive a synthetic scalar seven-segment jerk-limited S-curve."
    )
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        manifest = run_config(args.config, args.output_dir)
        verified = verify_archive(args.output_dir)
    except (SCurveError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    profile = manifest["profile_parameters"]
    print(
        f"{CASE_ID} {manifest['status']} duration_s={manifest['duration_s']:.9g} "
        f"peak_v={profile['peak_velocity_m_s']:.9g} "
        f"peak_a={profile['peak_acceleration_m_s2']:.9g} "
        f"peak_j={profile['peak_jerk_m_s3']:.9g} archive={verified['status']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
