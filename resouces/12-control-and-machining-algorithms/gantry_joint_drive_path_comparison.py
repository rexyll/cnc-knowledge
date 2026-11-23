#!/usr/bin/env python3
"""Run the CH12 PATH-01 free-axis / prescribed-path comparison.

Python 3.10+ and NumPy are required. The JSON configuration must contain
explicit, traceable values; this runner never supplies machine ratings.
No arbitrary Python expressions are loaded from configuration files.
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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import numpy as np

from gantry_joint_drive_solver import (
    ActuatorKinematics,
    CurrentLoopParameters,
    GantryJointDriveModel,
    JointState,
    MechanicalParameters,
    SinusoidalBeamGeometry,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SOLVER_PATH = Path(__file__).with_name("gantry_joint_drive_solver.py")

TIMESERIES_FIELDS = [
    "step_level", "step_s", "time_s",
    "s_ref_m", "sdot_ref_m_s", "sddot_ref_m_s2",
    "free_s_m", "free_sdot_m_s", "free_path_error_m",
    "free_path_velocity_error_m_s",
    "prescribed_s_m", "prescribed_sdot_m_s",
    "lambda_N", "lambda_power_W",
    "free_q1_m", "free_q2_rad", "free_q3_m", "free_q4_rad",
    "prescribed_q1_m", "prescribed_q2_rad", "prescribed_q3_m", "prescribed_q4_rad",
    "free_qdot1_m_s", "free_qdot2_rad_s", "free_qdot3_m_s", "free_qdot4_rad_s",
    "prescribed_qdot1_m_s", "prescribed_qdot2_rad_s",
    "prescribed_qdot3_m_s", "prescribed_qdot4_rad_s",
    "free_current_A", "prescribed_current_A",
    "free_requested_current_command_A", "prescribed_requested_current_command_A",
    "free_limited_current_reference_A", "prescribed_limited_current_reference_A",
    "free_current_reference_saturated", "prescribed_current_reference_saturated",
    "free_voltage_saturated", "prescribed_voltage_saturated",
    "free_current_integrator_V", "prescribed_current_integrator_V",
    "free_terminal_voltage_V", "prescribed_terminal_voltage_V",
    "free_payload_x_m", "free_payload_y_m", "free_payload_z_m",
    "prescribed_payload_x_m", "prescribed_payload_y_m", "prescribed_payload_z_m",
    "payload_point_error_norm_m",
    "free_kinetic_energy_J", "free_potential_energy_J",
    "free_magnetic_energy_J", "free_stored_energy_J",
    "prescribed_kinetic_energy_J", "prescribed_potential_energy_J",
    "prescribed_magnetic_energy_J", "prescribed_stored_energy_J",
    "free_terminal_power_W", "free_copper_loss_W",
    "free_structural_damping_loss_W", "free_axis_friction_loss_W",
    "free_external_power_W", "free_port_mismatch_power_W", "free_net_power_W",
    "prescribed_terminal_power_W", "prescribed_copper_loss_W",
    "prescribed_structural_damping_loss_W", "prescribed_axis_friction_loss_W",
    "prescribed_external_power_W", "prescribed_port_mismatch_power_W",
    "prescribed_net_power_including_constraint_W",
]

SUMMARY_FIELDS = [
    "case_id", "config_sha256", "solver_git_sha", "duration_s",
    "step_level", "step_s", "output_samples",
    "path_error_rms_m", "path_error_peak_m",
    "path_velocity_error_rms_m_s", "path_velocity_error_peak_m_s",
    "q1_error_rms_normalized", "q1_error_peak_normalized",
    "q2_error_rms_normalized", "q2_error_peak_normalized",
    "q3_error_rms_normalized", "q3_error_peak_normalized",
    "q4_error_rms_normalized", "q4_error_peak_normalized",
    "qdot1_error_rms_normalized", "qdot1_error_peak_normalized",
    "qdot2_error_rms_normalized", "qdot2_error_peak_normalized",
    "qdot3_error_rms_normalized", "qdot3_error_peak_normalized",
    "qdot4_error_rms_normalized", "qdot4_error_peak_normalized",
    "payload_point_error_rms_m", "payload_point_error_peak_m",
    "lambda_peak_N", "lambda_rms_N", "constraint_work_J",
    "constraint_work_trapezoid_check_J",
    "free_energy_residual_J", "free_energy_residual_normalized",
    "prescribed_energy_residual_J", "prescribed_energy_residual_normalized",
    "normalized_comparison_error_rms", "normalized_comparison_error_peak",
    "free_D_h", "free_D_h2", "free_D_h4",
    "free_observed_order_h_h2", "free_observed_order_h2_h4",
    "free_convergence_screen",
    "prescribed_D_h", "prescribed_D_h2", "prescribed_D_h4",
    "prescribed_observed_order_h_h2", "prescribed_observed_order_h2_h4",
    "prescribed_convergence_screen",
    "expected_rk4_stage_evaluations",
    "free_rk4_stage_evaluations",
    "free_current_reference_saturated_stages",
    "free_voltage_saturated_stages",
    "free_any_limiter_active_stages",
    "free_limiter_active_stage_fraction",
    "free_stage_count_matches_expected",
    "prescribed_rk4_stage_evaluations",
    "prescribed_current_reference_saturated_stages",
    "prescribed_voltage_saturated_stages",
    "prescribed_any_limiter_active_stages",
    "prescribed_limiter_active_stage_fraction",
    "prescribed_stage_count_matches_expected",
    "smooth_unsaturated_regime",
    "all_refinements_smooth_unsaturated_regime",
    "acceptance_profile_id", "acceptance_decision", "status",
    "timeseries_artifact", "exit_code",
]


class ConfigurationError(ValueError):
    """Raised when a PATH-01 config is incomplete or inconsistent."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _number(value: Any, name: str, *, positive: bool = False,
            nonnegative: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigurationError(f"{name} must be numeric; null/strings are not accepted")
    result = float(value)
    if not math.isfinite(result):
        raise ConfigurationError(f"{name} must be finite")
    if positive and result <= 0.0:
        raise ConfigurationError(f"{name} must be > 0")
    if nonnegative and result < 0.0:
        raise ConfigurationError(f"{name} must be >= 0")
    return result


def _vector(value: Any, name: str, size: int, *,
            positive: bool = False, nonnegative: bool = False) -> np.ndarray:
    if not isinstance(value, list) or len(value) != size:
        raise ConfigurationError(f"{name} must be a list with {size} numeric entries")
    return np.array([
        _number(item, f"{name}[{index}]", positive=positive, nonnegative=nonnegative)
        for index, item in enumerate(value)
    ], dtype=float)


def _matrix(value: Any, name: str, size: int) -> np.ndarray:
    if not isinstance(value, list) or len(value) != size:
        raise ConfigurationError(f"{name} must be a {size}x{size} numeric matrix")
    rows = [_vector(row, f"{name}[{index}]", size) for index, row in enumerate(value)]
    return np.vstack(rows)


def _mapping(parent: dict[str, Any], key: str, path: str) -> dict[str, Any]:
    value = parent.get(key)
    if not isinstance(value, dict):
        raise ConfigurationError(f"{path} must be a JSON object")
    return value


def _source_document_ids(value: Any) -> list[str]:
    """Validate and normalize provenance document/measurement identifiers."""
    if not isinstance(value, list):
        raise ConfigurationError(
            "provenance.source_documents_or_measurement_ids must be a JSON string array"
        )
    normalized: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise ConfigurationError(
                "provenance.source_documents_or_measurement_ids"
                f"[{index}] must be a non-empty string"
            )
        identifier = item.strip()
        if identifier in seen:
            raise ConfigurationError(
                "provenance.source_documents_or_measurement_ids"
                f" contains duplicate identifier {identifier!r}"
            )
        seen.add(identifier)
        normalized.append(identifier)
    return normalized


def quintic_rest_to_rest(
    time_s: float, start_m: float, end_m: float, duration_s: float
) -> tuple[float, float, float]:
    """Return analytic position, velocity and acceleration for a quintic move."""
    t = _number(time_s, "time_s")
    start = _number(start_m, "prescribed_path.s0_m")
    end = _number(end_m, "prescribed_path.s1_m")
    duration = _number(duration_s, "prescribed_path.duration_s", positive=True)
    epsilon = max(1e-12, 1e-12 * duration)
    if t < -epsilon or t > duration + epsilon:
        raise ValueError(f"PATH-01 path callback received out-of-range time {t}")
    t = min(max(t, 0.0), duration)
    u = t / duration
    delta = end - start
    position_shape = 10.0*u**3 - 15.0*u**4 + 6.0*u**5
    velocity_shape = 30.0*u**2 - 60.0*u**3 + 30.0*u**4
    acceleration_shape = 60.0*u - 180.0*u**2 + 120.0*u**3
    return (
        start + delta * position_shape,
        delta / duration * velocity_shape,
        delta / (duration * duration) * acceleration_shape,
    )


def composite_simpson_13(time_s: np.ndarray, values: np.ndarray) -> float:
    """Integrate uniformly spaced samples with composite Simpson 1/3."""
    times = np.asarray(time_s, dtype=float)
    samples = np.asarray(values, dtype=float)
    if times.ndim != 1 or samples.ndim != 1 or times.shape != samples.shape:
        raise ValueError("Simpson input arrays must be one-dimensional and equal length")
    if times.size < 3 or (times.size - 1) % 2 != 0:
        raise ValueError("composite Simpson 1/3 requires an even number of intervals")
    if not np.all(np.isfinite(times)) or not np.all(np.isfinite(samples)):
        raise ValueError("Simpson input arrays must be finite")
    differences = np.diff(times)
    step = float(differences[0])
    if step <= 0.0 or not np.allclose(differences, step, rtol=1e-10, atol=1e-14):
        raise ValueError("Simpson time grid must be strictly increasing and uniform")
    result = step / 3.0 * (
        samples[0] + samples[-1]
        + 4.0 * np.sum(samples[1:-1:2])
        + 2.0 * np.sum(samples[2:-1:2])
    )
    return float(result)


def trapezoid_integral(time_s: np.ndarray, values: np.ndarray) -> float:
    times = np.asarray(time_s, dtype=float)
    samples = np.asarray(values, dtype=float)
    return float(np.sum(0.5 * (samples[:-1] + samples[1:]) * np.diff(times)))


def normalized_state_error(
    left: np.ndarray, right: np.ndarray,
    absolute_tolerance: np.ndarray, relative_tolerance: np.ndarray
) -> np.ndarray:
    """Return componentwise error normalized by each component's own scale."""
    a = np.asarray(left, dtype=float)
    b = np.asarray(right, dtype=float)
    if a.shape != b.shape or a.ndim != 2:
        raise ValueError("state arrays must have equal (samples, components) shapes")
    atol = np.asarray(absolute_tolerance, dtype=float)
    rtol = np.asarray(relative_tolerance, dtype=float)
    if atol.shape != (a.shape[1],) or rtol.shape != atol.shape:
        raise ValueError("tolerance vectors must match the state component count")
    if np.any(atol <= 0.0) or np.any(rtol < 0.0):
        raise ValueError("absolute tolerances must be positive and relative tolerances nonnegative")
    if not np.all(np.isfinite(a)) or not np.all(np.isfinite(b)):
        raise ValueError("state arrays must contain only finite values")
    if not np.all(np.isfinite(atol)) or not np.all(np.isfinite(rtol)):
        raise ValueError("tolerance vectors must contain only finite values")
    denominator = atol[None, :] + rtol[None, :] * np.maximum(np.abs(a), np.abs(b))
    return (a - b) / denominator


def _load_tolerances(config: dict[str, Any]) -> tuple[np.ndarray, np.ndarray]:
    section = _mapping(config, "tolerances", "tolerances")
    absolute_q = _vector(section.get("absolute_q"), "tolerances.absolute_q", 4, positive=True)
    relative_q = _vector(section.get("relative_q"), "tolerances.relative_q", 4, nonnegative=True)
    absolute_q_dot = _vector(section.get("absolute_q_dot"), "tolerances.absolute_q_dot", 4, positive=True)
    relative_q_dot = _vector(section.get("relative_q_dot"), "tolerances.relative_q_dot", 4, nonnegative=True)
    absolute = np.concatenate((
        absolute_q,
        absolute_q_dot,
        [_number(section.get("absolute_s_m"), "tolerances.absolute_s_m", positive=True)],
        [_number(section.get("absolute_s_dot_m_s"), "tolerances.absolute_s_dot_m_s", positive=True)],
        [_number(section.get("absolute_current_A"), "tolerances.absolute_current_A", positive=True)],
        [_number(section.get("absolute_current_integrator_V"), "tolerances.absolute_current_integrator_V", positive=True)],
    ))
    relative = np.concatenate((
        relative_q,
        relative_q_dot,
        [_number(section.get("relative_s"), "tolerances.relative_s", nonnegative=True)],
        [_number(section.get("relative_s_dot"), "tolerances.relative_s_dot", nonnegative=True)],
        [_number(section.get("relative_current"), "tolerances.relative_current", nonnegative=True)],
        [_number(section.get("relative_current_integrator"), "tolerances.relative_current_integrator", nonnegative=True)],
    ))
    return absolute, relative


def _build_model(config: dict[str, Any]) -> tuple[GantryJointDriveModel, JointState, np.ndarray]:
    mechanical_cfg = _mapping(config, "mechanical", "mechanical")
    electrical_cfg = _mapping(config, "electrical", "electrical")
    actuator_cfg = _mapping(config, "actuator", "actuator")
    geometry = SinusoidalBeamGeometry(
        span_m=_number(mechanical_cfg.get("geometry_span_m"), "mechanical.geometry_span_m", positive=True),
        torsion_x_offset_m=_number(mechanical_cfg.get("torsion_x_offset_m"), "mechanical.torsion_x_offset_m"),
        torsion_z_offset_m=_number(mechanical_cfg.get("torsion_z_offset_m"), "mechanical.torsion_z_offset_m"),
    )
    mechanical = MechanicalParameters(
        M0=_matrix(mechanical_cfg.get("M0"), "mechanical.M0", 4),
        D0=_matrix(mechanical_cfg.get("D0"), "mechanical.D0", 4),
        K0=_matrix(mechanical_cfg.get("K0"), "mechanical.K0", 4),
        payload_mass_kg=_number(mechanical_cfg.get("payload_mass_kg"), "mechanical.payload_mass_kg", nonnegative=True),
        axis_equivalent_mass_kg=_number(mechanical_cfg.get("axis_equivalent_mass_kg"), "mechanical.axis_equivalent_mass_kg", positive=True),
        gravity_acceleration_m_s2=_vector(mechanical_cfg.get("gravity_acceleration_m_s2"), "mechanical.gravity_acceleration_m_s2", 3),
        axis_viscous_Ns_m=_number(mechanical_cfg.get("axis_viscous_Ns_m"), "mechanical.axis_viscous_Ns_m", nonnegative=True),
        axis_coulomb_N=_number(mechanical_cfg.get("axis_coulomb_N"), "mechanical.axis_coulomb_N", nonnegative=True),
        friction_smoothing_speed_m_s=_number(
            mechanical_cfg.get("friction_smoothing_speed_m_s"),
            "mechanical.friction_smoothing_speed_m_s", positive=True
        ),
    )
    electrical = CurrentLoopParameters(
        resistance_ohm=_number(electrical_cfg.get("resistance_ohm"), "electrical.resistance_ohm", positive=True),
        inductance_h=_number(electrical_cfg.get("inductance_h"), "electrical.inductance_h", positive=True),
        back_emf_V_per_m_s=_number(electrical_cfg.get("back_emf_V_per_m_s"), "electrical.back_emf_V_per_m_s", nonnegative=True),
        force_constant_N_per_A=_number(electrical_cfg.get("force_constant_N_per_A"), "electrical.force_constant_N_per_A", positive=True),
        current_limit_A=_number(electrical_cfg.get("current_limit_A"), "electrical.current_limit_A", positive=True),
        voltage_min_V=_number(electrical_cfg.get("voltage_min_V"), "electrical.voltage_min_V"),
        voltage_max_V=_number(electrical_cfg.get("voltage_max_V"), "electrical.voltage_max_V"),
        kp_V_per_A=_number(electrical_cfg.get("kp_V_per_A"), "electrical.kp_V_per_A", nonnegative=True),
        ki_V_per_A_s=_number(electrical_cfg.get("ki_V_per_A_s"), "electrical.ki_V_per_A_s", nonnegative=True),
        antiwindup_gain_per_s=_number(electrical_cfg.get("antiwindup_gain_per_s"), "electrical.antiwindup_gain_per_s", nonnegative=True),
    )
    actuator = ActuatorKinematics(
        q_coefficients=_vector(actuator_cfg.get("q_coefficients"), "actuator.q_coefficients", 4),
        s_coefficient=_number(actuator_cfg.get("s_coefficient"), "actuator.s_coefficient"),
        offset_m=_number(actuator_cfg.get("offset_m"), "actuator.offset_m"),
    )
    model = GantryJointDriveModel(geometry, mechanical, electrical, actuator)

    state_cfg = _mapping(config, "initial_state", "initial_state")
    initial_state = JointState(
        q=_vector(state_cfg.get("q"), "initial_state.q", 4),
        q_dot=_vector(state_cfg.get("q_dot"), "initial_state.q_dot", 4),
        s=_number(state_cfg.get("s_m"), "initial_state.s_m"),
        s_dot=_number(state_cfg.get("s_dot_m_s"), "initial_state.s_dot_m_s"),
        current_A=_number(state_cfg.get("current_A"), "initial_state.current_A"),
        current_integrator_V=_number(state_cfg.get("current_integrator_V"), "initial_state.current_integrator_V"),
    )
    model.pack(initial_state)
    load_cfg = _mapping(config, "controller_and_loads", "controller_and_loads")
    external_force = _vector(
        load_cfg.get("external_generalized_force_constant"),
        "controller_and_loads.external_generalized_force_constant", 5
    )
    return model, initial_state, external_force


def _validate_config(config: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(config, dict):
        raise ConfigurationError("configuration root must be a JSON object")
    if config.get("schema_version") != 1:
        raise ConfigurationError("unsupported config schema_version; expected 1")
    if config.get("case_id") != "PATH-01":
        raise ConfigurationError("case_id must be PATH-01")
    provenance = _mapping(config, "provenance", "provenance")
    parameter_source = provenance.get("parameter_source")
    if not isinstance(parameter_source, str) or not parameter_source.strip():
        raise ConfigurationError(
            "provenance.parameter_source is required; identify machine data or synthetic fixture"
        )
    parameter_source = parameter_source.strip()
    source_document_ids = _source_document_ids(
        provenance.get("source_documents_or_measurement_ids", [])
    )
    path_cfg = _mapping(config, "prescribed_path", "prescribed_path")
    if path_cfg.get("family") != "quintic_rest_to_rest":
        raise ConfigurationError("only prescribed_path.family=quintic_rest_to_rest is supported")
    start_m = _number(path_cfg.get("s0_m"), "prescribed_path.s0_m")
    end_m = _number(path_cfg.get("s1_m"), "prescribed_path.s1_m")
    duration = _number(path_cfg.get("duration_s"), "prescribed_path.duration_s", positive=True)
    mechanical_cfg = _mapping(config, "mechanical", "mechanical")
    span_m = _number(mechanical_cfg.get("geometry_span_m"), "mechanical.geometry_span_m", positive=True)
    if not (0.0 <= start_m <= span_m and 0.0 <= end_m <= span_m):
        raise ConfigurationError("PATH-01 endpoints s0_m and s1_m must lie within [0, geometry_span_m]")
    initial_cfg = _mapping(config, "initial_state", "initial_state")
    initial_s = _number(initial_cfg.get("s_m"), "initial_state.s_m")
    initial_s_dot = _number(initial_cfg.get("s_dot_m_s"), "initial_state.s_dot_m_s")
    if not math.isclose(initial_s, start_m, rel_tol=1e-9, abs_tol=1e-12):
        raise ConfigurationError("initial_state.s_m must equal prescribed_path.s0_m")
    if not math.isclose(initial_s_dot, 0.0, rel_tol=0.0, abs_tol=1e-12):
        raise ConfigurationError("quintic rest-to-rest path requires initial_state.s_dot_m_s = 0")
    integration = _mapping(config, "integration", "integration")
    integration_duration = _number(integration.get("duration_s"), "integration.duration_s", positive=True)
    base_step = _number(integration.get("base_step_s"), "integration.base_step_s", positive=True)
    if not math.isclose(integration_duration, duration, rel_tol=1e-10, abs_tol=1e-12):
        raise ConfigurationError("integration.duration_s must equal prescribed_path.duration_s")
    intervals = int(round(duration / base_step))
    if intervals < 2 or intervals % 2 != 0 or not math.isclose(
        intervals * base_step, duration, rel_tol=1e-9, abs_tol=1e-12
    ):
        raise ConfigurationError(
            "duration_s/base_step_s must be an integer, even interval count for Simpson 1/3"
        )
    if integration.get("refinement_schedule") != ["h", "h/2", "h/4", "h/8"]:
        raise ConfigurationError("integration.refinement_schedule must be [h,h/2,h/4,h/8]")
    if integration.get("aligned_output_grid") is not True:
        raise ConfigurationError("integration.aligned_output_grid must be true")

    controller = _mapping(config, "controller_and_loads", "controller_and_loads")
    if controller.get("use_identical_deterministic_callback_for_both_models") is not True:
        raise ConfigurationError("both models must use the same deterministic controller callback")
    kp_pos = _number(controller.get("Kp_pos_A_per_m"), "controller_and_loads.Kp_pos_A_per_m", nonnegative=True)
    kd_vel = _number(controller.get("Kd_vel_A_s_per_m"), "controller_and_loads.Kd_vel_A_s_per_m", nonnegative=True)
    feedforward = _number(controller.get("feedforward_current_A"), "controller_and_loads.feedforward_current_A")
    _vector(controller.get("external_generalized_force_constant"),
            "controller_and_loads.external_generalized_force_constant", 5)
    expected_force_order = ["Q_x_common", "Q_yaw", "Q_bending", "Q_torsion", "Q_s"]
    if controller.get("external_generalized_force_order") != expected_force_order:
        raise ConfigurationError("external_generalized_force_order must be [Q_x_common,Q_yaw,Q_bending,Q_torsion,Q_s]")

    absolute_tolerance, relative_tolerance = _load_tolerances(config)
    metrics = _mapping(config, "metrics", "metrics")
    energy_scale = _number(metrics.get("energy_normalization_scale_J"), "metrics.energy_normalization_scale_J", positive=True)
    energy_floor = _number(metrics.get("energy_normalization_floor_J"), "metrics.energy_normalization_floor_J", positive=True)
    model, state, external = _build_model(config)

    acceptance = _mapping(config, "acceptance", "acceptance")
    limit_names = (
        "application_path_error_limit_m",
        "application_path_velocity_error_limit_m_s",
        "payload_point_error_limit_m",
        "application_force_limit_N",
        "application_force_rms_limit_N",
        "constraint_work_limit_J",
        "normalized_energy_residual_limit",
    )
    limits: dict[str, float | None] = {}
    for name in limit_names:
        value = acceptance.get(name)
        limits[name] = None if value is None else _number(value, f"acceptance.{name}", nonnegative=True)
    profile = acceptance.get("profile_id")
    if profile is not None and not isinstance(profile, str):
        raise ConfigurationError("acceptance.profile_id must be a string or null")

    return {
        "model": model,
        "initial_state": state,
        "external_force": external,
        "start_m": start_m,
        "end_m": end_m,
        "duration_s": duration,
        "base_step_s": base_step,
        "base_intervals": intervals,
        "kp_pos": kp_pos,
        "kd_vel": kd_vel,
        "feedforward": feedforward,
        "absolute_tolerance": absolute_tolerance,
        "relative_tolerance": relative_tolerance,
        "energy_scale": energy_scale,
        "energy_floor": energy_floor,
        "limits": limits,
        "acceptance_profile_id": profile or "UNSPECIFIED",
        "parameter_source": parameter_source,
        "source_documents_or_measurement_ids": source_document_ids,
    }




def _current_reference_was_limited(requested_command_A: float, limited_reference_A: float) -> bool:
    """Return whether clipping changed the requested current reference."""
    return float(limited_reference_A) != float(requested_command_A)


def _track_current_command(
    model: GantryJointDriveModel,
    current_command: Callable[[float, JointState], float],
) -> tuple[Callable[[float, JointState], float], dict[str, Any]]:
    """Observe limiter activation at every solver current-command callback."""
    observations: dict[str, Any] = {
        "callback_evaluations": 0,
        "current_reference_saturated": 0,
        "voltage_saturated": 0,
        "any_limiter_active": 0,
        "last": None,
    }

    def tracked(time_s: float, state: JointState) -> float:
        diagnostic_state = state.copy()
        command_state = state.copy()
        requested = float(current_command(float(time_s), command_state))
        diagnostics = model.electrical_diagnostics(diagnostic_state, requested)
        reference_saturated = _current_reference_was_limited(
            requested, float(diagnostics["current_reference_A"])
        )
        voltage_saturated = bool(diagnostics["voltage_saturated"])
        any_limiter_active = reference_saturated or voltage_saturated
        observations["callback_evaluations"] += 1
        observations["current_reference_saturated"] += int(reference_saturated)
        observations["voltage_saturated"] += int(voltage_saturated)
        observations["any_limiter_active"] += int(any_limiter_active)
        observations["last"] = {
            "current_reference_saturated": reference_saturated,
            "voltage_saturated": voltage_saturated,
            "any_limiter_active": any_limiter_active,
        }
        return requested

    return tracked, observations


def _saturation_stage_report(
    observations: dict[str, Any],
    expected_stage_evaluations: int,
    *,
    exclude_last_evaluation: bool = False,
) -> dict[str, Any]:
    """Summarize RK4-stage limiter flags, optionally excluding a terminal probe."""
    if isinstance(expected_stage_evaluations, bool) or expected_stage_evaluations <= 0:
        raise ValueError("expected_stage_evaluations must be a positive integer")
    if int(expected_stage_evaluations) != expected_stage_evaluations:
        raise ValueError("expected_stage_evaluations must be a positive integer")
    total = int(observations.get("callback_evaluations", 0))
    excluded = 1 if exclude_last_evaluation else 0
    if total < excluded:
        raise ValueError("cannot exclude a terminal evaluation when no callback was observed")
    stage_evaluations = total - excluded
    last = observations.get("last") if excluded else None
    counts: dict[str, int] = {}
    for key in (
        "current_reference_saturated",
        "voltage_saturated",
        "any_limiter_active",
    ):
        count = int(observations.get(key, 0))
        if last is not None:
            count -= int(bool(last[key]))
        if count < 0 or count > stage_evaluations:
            raise ValueError(f"invalid saturation counter: {key}")
        counts[key] = count
    return {
        "rk4_stage_evaluations": stage_evaluations,
        "current_reference_saturated_stages": counts["current_reference_saturated"],
        "voltage_saturated_stages": counts["voltage_saturated"],
        "any_limiter_active_stages": counts["any_limiter_active"],
        "limiter_active_stage_fraction": (
            counts["any_limiter_active"] / stage_evaluations
            if stage_evaluations else 0.0
        ),
        "stage_count_matches_expected": stage_evaluations == expected_stage_evaluations,
    }


def _energy_ledger(
    model: GantryJointDriveModel,
    times: np.ndarray,
    states: np.ndarray,
    current_command: Callable[[float, JointState], float],
    external_force: np.ndarray,
    constraint_force: np.ndarray,
    path_samples: np.ndarray,
    *,
    constrained: bool,
) -> list[dict[str, float]]:
    ledger: list[dict[str, float]] = []
    for index, time_s in enumerate(times):
        state = model.unpack(states[index])
        command = float(current_command(float(time_s), state.copy()))
        diagnostics = model.electrical_diagnostics(state, command)
        kinetic, potential = model.mechanical_energy(state)
        magnetic = 0.5 * model.electrical.inductance_h * state.current_A**2
        stored = kinetic + potential + magnetic
        voltage = float(diagnostics["voltage_V"])
        current_reference = float(diagnostics["current_reference_A"])
        current_reference_saturated = _current_reference_was_limited(
            command, current_reference
        )
        voltage_saturated = bool(diagnostics["voltage_saturated"])
        terminal = voltage * state.current_A
        copper = model.electrical.resistance_ohm * state.current_A**2
        structural_damping = float(state.q_dot @ model.mechanical.D0 @ state.q_dot)
        friction_force = (
            model.mechanical.axis_viscous_Ns_m * state.s_dot
            + model.mechanical.axis_coulomb_N
            * math.tanh(state.s_dot / model.mechanical.friction_smoothing_speed_m_s)
        )
        axis_friction = friction_force * state.s_dot
        z_dot = np.concatenate((state.q_dot, [state.s_dot]))
        external_power = float(external_force @ z_dot)
        ell_dot = model.actuator_relative_velocity(state.q_dot, state.s_dot)
        port_mismatch = (
            model.electrical.force_constant_N_per_A
            - model.electrical.back_emf_V_per_m_s
        ) * state.current_A * ell_dot
        lambda_power = float(constraint_force[index] * path_samples[index, 1]) if constrained else 0.0
        net_power = (
            terminal - copper - structural_damping - axis_friction
            + external_power + port_mismatch + lambda_power
        )
        ledger.append({
            "kinetic": float(kinetic),
            "potential": float(potential),
            "magnetic": float(magnetic),
            "stored": float(stored),
            "voltage": voltage,
            "requested_command": command,
            "current_reference": current_reference,
            "current_reference_saturated": current_reference_saturated,
            "voltage_saturated": voltage_saturated,
            "terminal": terminal,
            "copper": float(copper),
            "structural_damping": structural_damping,
            "axis_friction": float(axis_friction),
            "external": external_power,
            "port_mismatch": float(port_mismatch),
            "lambda_power": lambda_power,
            "net": float(net_power),
        })
    return ledger


def _energy_metrics(
    times: np.ndarray, ledger: list[dict[str, float]], energy_scale: float, energy_floor: float
) -> dict[str, float]:
    energy = np.array([row["stored"] for row in ledger], dtype=float)
    power = np.array([row["net"] for row in ledger], dtype=float)
    delta_energy = float(energy[-1] - energy[0])
    input_work = composite_simpson_13(times, power)
    absolute_power_work = composite_simpson_13(times, np.abs(power))
    residual = delta_energy - input_work
    normalization = max(energy_scale, absolute_power_work, energy_floor)
    return {
        "delta_energy": delta_energy,
        "input_work": input_work,
        "absolute_power_work": absolute_power_work,
        "residual": residual,
        "normalized_residual": abs(residual) / normalization,
        "trapezoid_residual": delta_energy - trapezoid_integral(times, power),
    }


def _convergence(
    histories: list[np.ndarray],
    absolute_tolerance: np.ndarray,
    relative_tolerance: np.ndarray,
) -> dict[str, Any]:
    distances: list[float] = []
    peaks: list[float] = []
    for coarse, fine in zip(histories[:-1], histories[1:]):
        if coarse.shape[0] != (fine.shape[0] + 1) // 2:
            raise ValueError("refinement grids cannot be aligned by even-index sampling")
        normalized = normalized_state_error(
            coarse, fine[::2], absolute_tolerance, relative_tolerance
        )
        distances.append(float(np.sqrt(np.mean(normalized**2))))
        peaks.append(float(np.max(np.abs(normalized))))
    orders: list[float | None] = []
    for first, second in zip(distances[:-1], distances[1:]):
        if first > 0.0 and second > 0.0:
            orders.append(float(math.log2(first / second)))
        else:
            orders.append(None)
    exact = all(value <= 1e-15 for value in distances)
    monotonic = distances[0] > distances[1] > distances[2]
    order_ok = all(value is not None and value >= 3.0 for value in orders)
    finite = all(math.isfinite(value) for value in distances + peaks)
    return {
        "distances": distances,
        "peaks": peaks,
        "orders": orders,
        "screen": bool(finite and (exact or (monotonic and order_ok))),
        "exact": exact,
    }


def _rms_peak(values: np.ndarray) -> tuple[float, float]:
    array = np.asarray(values, dtype=float)
    return float(np.sqrt(np.mean(array**2))), float(np.max(np.abs(array)))


def _step_metrics(
    model: GantryJointDriveModel,
    times: np.ndarray,
    free_states: np.ndarray,
    prescribed_states: np.ndarray,
    lambda_values: np.ndarray,
    path_samples: np.ndarray,
    free_ledger: list[dict[str, float]],
    prescribed_ledger: list[dict[str, float]],
    config: dict[str, Any],
    config_sha: str,
    solver_git_sha: str,
    step_label: str,
    step_s: float,
    convergence_free: dict[str, Any],
    convergence_prescribed: dict[str, Any],
    saturation_free: dict[str, Any],
    saturation_prescribed: dict[str, Any],
    artifact_name: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    normalized = normalized_state_error(
        free_states, prescribed_states,
        config["absolute_tolerance"], config["relative_tolerance"]
    )
    free_path_error = free_states[:, 8] - path_samples[:, 0]
    free_velocity_error = free_states[:, 9] - path_samples[:, 1]
    free_payload = np.vstack([
        model.geometry_terms(row[:4], float(row[8]))["r"] for row in free_states
    ])
    prescribed_payload = np.vstack([
        model.geometry_terms(row[:4], float(row[8]))["r"] for row in prescribed_states
    ])
    payload_error = np.linalg.norm(free_payload - prescribed_payload, axis=1)
    path_rms, path_peak = _rms_peak(free_path_error)
    velocity_rms, velocity_peak = _rms_peak(free_velocity_error)
    payload_rms, payload_peak = _rms_peak(payload_error)
    free_energy = _energy_metrics(
        times, free_ledger, config["energy_scale"], config["energy_floor"]
    )
    prescribed_energy = _energy_metrics(
        times, prescribed_ledger, config["energy_scale"], config["energy_floor"]
    )

    summary: dict[str, Any] = {
        "case_id": "PATH-01",
        "config_sha256": config_sha,
        "solver_git_sha": solver_git_sha,
        "duration_s": float(times[-1]),
        "step_level": step_label,
        "step_s": step_s,
        "output_samples": int(times.size),
        "path_error_rms_m": path_rms,
        "path_error_peak_m": path_peak,
        "path_velocity_error_rms_m_s": velocity_rms,
        "path_velocity_error_peak_m_s": velocity_peak,
        "payload_point_error_rms_m": payload_rms,
        "payload_point_error_peak_m": payload_peak,
        "lambda_peak_N": float(np.max(np.abs(lambda_values))),
        "lambda_rms_N": float(np.sqrt(composite_simpson_13(times, lambda_values**2) / times[-1])),
        "constraint_work_J": composite_simpson_13(times, lambda_values * path_samples[:, 1]),
        "constraint_work_trapezoid_check_J": trapezoid_integral(times, lambda_values * path_samples[:, 1]),
        "free_energy_residual_J": free_energy["residual"],
        "free_energy_residual_normalized": free_energy["normalized_residual"],
        "prescribed_energy_residual_J": prescribed_energy["residual"],
        "prescribed_energy_residual_normalized": prescribed_energy["normalized_residual"],
        "normalized_comparison_error_rms": float(np.sqrt(np.mean(normalized**2))),
        "normalized_comparison_error_peak": float(np.max(np.abs(normalized))),
        "free_D_h": convergence_free["distances"][0],
        "free_D_h2": convergence_free["distances"][1],
        "free_D_h4": convergence_free["distances"][2],
        "free_observed_order_h_h2": convergence_free["orders"][0],
        "free_observed_order_h2_h4": convergence_free["orders"][1],
        "free_convergence_screen": convergence_free["screen"],
        "prescribed_D_h": convergence_prescribed["distances"][0],
        "prescribed_D_h2": convergence_prescribed["distances"][1],
        "prescribed_D_h4": convergence_prescribed["distances"][2],
        "prescribed_observed_order_h_h2": convergence_prescribed["orders"][0],
        "prescribed_observed_order_h2_h4": convergence_prescribed["orders"][1],
        "prescribed_convergence_screen": convergence_prescribed["screen"],
        "expected_rk4_stage_evaluations": int(4 * round(times[-1] / step_s)),
        "free_rk4_stage_evaluations": saturation_free["rk4_stage_evaluations"],
        "free_current_reference_saturated_stages": saturation_free["current_reference_saturated_stages"],
        "free_voltage_saturated_stages": saturation_free["voltage_saturated_stages"],
        "free_any_limiter_active_stages": saturation_free["any_limiter_active_stages"],
        "free_limiter_active_stage_fraction": saturation_free["limiter_active_stage_fraction"],
        "free_stage_count_matches_expected": saturation_free["stage_count_matches_expected"],
        "prescribed_rk4_stage_evaluations": saturation_prescribed["rk4_stage_evaluations"],
        "prescribed_current_reference_saturated_stages": saturation_prescribed["current_reference_saturated_stages"],
        "prescribed_voltage_saturated_stages": saturation_prescribed["voltage_saturated_stages"],
        "prescribed_any_limiter_active_stages": saturation_prescribed["any_limiter_active_stages"],
        "prescribed_limiter_active_stage_fraction": saturation_prescribed["limiter_active_stage_fraction"],
        "prescribed_stage_count_matches_expected": saturation_prescribed["stage_count_matches_expected"],
        "smooth_unsaturated_regime": bool(
            saturation_free["stage_count_matches_expected"]
            and saturation_prescribed["stage_count_matches_expected"]
            and saturation_free["any_limiter_active_stages"] == 0
            and saturation_prescribed["any_limiter_active_stages"] == 0
        ),
        "acceptance_profile_id": config["acceptance_profile_id"],
        "timeseries_artifact": artifact_name,
        "exit_code": 0,
    }
    q_slice = normalized[:, :4]
    q_dot_slice = normalized[:, 4:8]
    for index in range(4):
        q_rms, q_peak = _rms_peak(q_slice[:, index])
        qd_rms, qd_peak = _rms_peak(q_dot_slice[:, index])
        summary[f"q{index+1}_error_rms_normalized"] = q_rms
        summary[f"q{index+1}_error_peak_normalized"] = q_peak
        summary[f"qdot{index+1}_error_rms_normalized"] = qd_rms
        summary[f"qdot{index+1}_error_peak_normalized"] = qd_peak

    rows: list[dict[str, Any]] = []
    for sample, time_s in enumerate(times):
        free = free_states[sample]
        prescribed = prescribed_states[sample]
        ref = path_samples[sample]
        free_energy_row = free_ledger[sample]
        prescribed_energy_row = prescribed_ledger[sample]
        free_payload_point = free_payload[sample]
        prescribed_payload_point = prescribed_payload[sample]
        row: dict[str, Any] = {
            "step_level": step_label,
            "step_s": step_s,
            "time_s": float(time_s),
            "s_ref_m": float(ref[0]),
            "sdot_ref_m_s": float(ref[1]),
            "sddot_ref_m_s2": float(ref[2]),
            "free_s_m": float(free[8]),
            "free_sdot_m_s": float(free[9]),
            "free_path_error_m": float(free_path_error[sample]),
            "free_path_velocity_error_m_s": float(free_velocity_error[sample]),
            "prescribed_s_m": float(prescribed[8]),
            "prescribed_sdot_m_s": float(prescribed[9]),
            "lambda_N": float(lambda_values[sample]),
            "lambda_power_W": float(lambda_values[sample] * ref[1]),
            "payload_point_error_norm_m": float(payload_error[sample]),
            "free_kinetic_energy_J": free_energy_row["kinetic"],
            "free_potential_energy_J": free_energy_row["potential"],
            "free_magnetic_energy_J": free_energy_row["magnetic"],
            "free_stored_energy_J": free_energy_row["stored"],
            "prescribed_kinetic_energy_J": prescribed_energy_row["kinetic"],
            "prescribed_potential_energy_J": prescribed_energy_row["potential"],
            "prescribed_magnetic_energy_J": prescribed_energy_row["magnetic"],
            "prescribed_stored_energy_J": prescribed_energy_row["stored"],
            "free_terminal_power_W": free_energy_row["terminal"],
            "free_copper_loss_W": free_energy_row["copper"],
            "free_structural_damping_loss_W": free_energy_row["structural_damping"],
            "free_axis_friction_loss_W": free_energy_row["axis_friction"],
            "free_external_power_W": free_energy_row["external"],
            "free_port_mismatch_power_W": free_energy_row["port_mismatch"],
            "free_net_power_W": free_energy_row["net"],
            "prescribed_terminal_power_W": prescribed_energy_row["terminal"],
            "prescribed_copper_loss_W": prescribed_energy_row["copper"],
            "prescribed_structural_damping_loss_W": prescribed_energy_row["structural_damping"],
            "prescribed_axis_friction_loss_W": prescribed_energy_row["axis_friction"],
            "prescribed_external_power_W": prescribed_energy_row["external"],
            "prescribed_port_mismatch_power_W": prescribed_energy_row["port_mismatch"],
            "prescribed_net_power_including_constraint_W": prescribed_energy_row["net"],
        }
        for index in range(4):
            suffix = "m" if index in (0, 2) else "rad"
            velocity_suffix = "m_s" if index in (0, 2) else "rad_s"
            row[f"free_q{index+1}_{suffix}"] = float(free[index])
            row[f"prescribed_q{index+1}_{suffix}"] = float(prescribed[index])
            row[f"free_qdot{index+1}_{velocity_suffix}"] = float(free[4+index])
            row[f"prescribed_qdot{index+1}_{velocity_suffix}"] = float(prescribed[4+index])
        row.update({
            "free_current_A": float(free[10]),
            "prescribed_current_A": float(prescribed[10]),
            "free_requested_current_command_A": free_energy_row["requested_command"],
            "prescribed_requested_current_command_A": prescribed_energy_row["requested_command"],
            "free_limited_current_reference_A": free_energy_row["current_reference"],
            "prescribed_limited_current_reference_A": prescribed_energy_row["current_reference"],
            "free_current_reference_saturated": free_energy_row["current_reference_saturated"],
            "prescribed_current_reference_saturated": prescribed_energy_row["current_reference_saturated"],
            "free_voltage_saturated": free_energy_row["voltage_saturated"],
            "prescribed_voltage_saturated": prescribed_energy_row["voltage_saturated"],
            "free_current_integrator_V": float(free[11]),
            "prescribed_current_integrator_V": float(prescribed[11]),
            "free_terminal_voltage_V": free_energy_row["voltage"],
            "prescribed_terminal_voltage_V": prescribed_energy_row["voltage"],
            "free_payload_x_m": float(free_payload_point[0]),
            "free_payload_y_m": float(free_payload_point[1]),
            "free_payload_z_m": float(free_payload_point[2]),
            "prescribed_payload_x_m": float(prescribed_payload_point[0]),
            "prescribed_payload_y_m": float(prescribed_payload_point[1]),
            "prescribed_payload_z_m": float(prescribed_payload_point[2]),
        })
        rows.append(row)
    return summary, rows


def _acceptance_decision(
    finest_summary: dict[str, Any], limits: dict[str, float | None]
) -> tuple[str, str]:
    convergence_ok = (
        finest_summary["free_convergence_screen"]
        and finest_summary["prescribed_convergence_screen"]
    )
    if not convergence_ok:
        return "FAIL", "FAIL"
    if not finest_summary["all_refinements_smooth_unsaturated_regime"]:
        return "DESCRIPTIVE_ONLY", "COMPLETED_REPORT_ONLY"
    if any(value is None for value in limits.values()):
        return "DESCRIPTIVE_ONLY", "COMPLETED_REPORT_ONLY"
    checks = [
        finest_summary["path_error_peak_m"] <= limits["application_path_error_limit_m"],
        finest_summary["path_velocity_error_peak_m_s"] <= limits["application_path_velocity_error_limit_m_s"],
        finest_summary["payload_point_error_peak_m"] <= limits["payload_point_error_limit_m"],
        finest_summary["lambda_peak_N"] <= limits["application_force_limit_N"],
        finest_summary["lambda_rms_N"] <= limits["application_force_rms_limit_N"],
        abs(finest_summary["constraint_work_J"]) <= limits["constraint_work_limit_J"],
        finest_summary["free_energy_residual_normalized"] <= limits["normalized_energy_residual_limit"],
        finest_summary["prescribed_energy_residual_normalized"] <= limits["normalized_energy_residual_limit"],
    ]
    return ("PASS", "PASS") if all(checks) else ("FAIL", "FAIL")


def _write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def _git_sha() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT,
            check=True, capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def run_path_comparison(config_path: Path, output_dir: Path, *, force: bool = False) -> dict[str, Any]:
    config_path = config_path.resolve()
    output_dir = output_dir.resolve()
    with config_path.open("r", encoding="utf-8") as stream:
        config = json.load(stream)
    validated = _validate_config(config)
    if not SOLVER_PATH.is_file():
        raise FileNotFoundError(f"solver module not found: {SOLVER_PATH}")

    output_dir.mkdir(parents=True, exist_ok=True)
    timeseries_path = output_dir / "gantry-joint-drive-path-comparison-timeseries.csv"
    summary_path = output_dir / "gantry-joint-drive-path-comparison-summary.csv"
    manifest_path = output_dir / "gantry-joint-drive-path-comparison-run-manifest.json"
    outputs = [timeseries_path, summary_path, manifest_path]
    if not force:
        existing = [str(path) for path in outputs if path.exists()]
        if existing:
            raise FileExistsError(
                "output file(s) already exist; choose another directory or pass --force: "
                + ", ".join(existing)
            )

    model: GantryJointDriveModel = validated["model"]
    initial_state: JointState = validated["initial_state"]
    external_vector: np.ndarray = validated["external_force"]
    start_m = validated["start_m"]
    end_m = validated["end_m"]
    duration = validated["duration_s"]
    kp_pos = validated["kp_pos"]
    kd_vel = validated["kd_vel"]
    feedforward = validated["feedforward"]

    def path_callback(time_s: float) -> tuple[float, float, float]:
        return quintic_rest_to_rest(time_s, start_m, end_m, duration)

    def current_command(time_s: float, state: JointState) -> float:
        s_ref, sdot_ref, _ = path_callback(time_s)
        return float(
            feedforward
            + kp_pos * (s_ref - state.s)
            + kd_vel * (sdot_ref - state.s_dot)
        )

    def external_force(_time_s: float, _state: JointState) -> np.ndarray:
        return external_vector.copy()

    config_sha = sha256_file(config_path)
    solver_sha256 = sha256_file(SOLVER_PATH)
    runner_sha256 = sha256_file(Path(__file__).resolve())
    git_sha = _git_sha()
    labels = ["h", "h/2", "h/4", "h/8"]
    free_histories: list[np.ndarray] = []
    prescribed_histories: list[np.ndarray] = []
    level_data: list[dict[str, Any]] = []
    all_timeseries_rows: list[dict[str, Any]] = []
    started = datetime.now(timezone.utc).isoformat()

    for level, label in enumerate(labels):
        intervals = validated["base_intervals"] * (2**level)
        step = duration / intervals
        free_monitored_command, free_observations = _track_current_command(model, current_command)
        prescribed_monitored_command, prescribed_observations = _track_current_command(model, current_command)
        times, free_states = model.simulate(
            initial_state, duration, step, free_monitored_command, external_force
        )
        prescribed_times, prescribed_states, lambda_values = model.simulate_prescribed_path(
            initial_state, duration, step, path_callback, prescribed_monitored_command, external_force
        )
        expected_stage_evaluations = 4 * intervals
        saturation_free = _saturation_stage_report(
            free_observations, expected_stage_evaluations
        )
        # simulate_prescribed_path performs one extra endpoint diagnostic after
        # its 4*N RK4 stage callbacks; exclude that terminal probe from stage counts.
        saturation_prescribed = _saturation_stage_report(
            prescribed_observations, expected_stage_evaluations,
            exclude_last_evaluation=True,
        )
        if not np.array_equal(times, prescribed_times):
            raise RuntimeError("free and prescribed solvers returned different output time grids")
        path_samples = np.vstack([path_callback(float(time_s)) for time_s in times])
        free_ledger = _energy_ledger(
            model, times, free_states, current_command, external_vector,
            np.zeros_like(lambda_values), path_samples, constrained=False
        )
        prescribed_ledger = _energy_ledger(
            model, times, prescribed_states, current_command, external_vector,
            lambda_values, path_samples, constrained=True
        )
        free_histories.append(free_states)
        prescribed_histories.append(prescribed_states)
        level_data.append({
            "label": label,
            "step": step,
            "intervals": intervals,
            "times": times,
            "free_states": free_states,
            "prescribed_states": prescribed_states,
            "lambda_values": lambda_values,
            "path_samples": path_samples,
            "free_ledger": free_ledger,
            "prescribed_ledger": prescribed_ledger,
            "saturation_free": saturation_free,
            "saturation_prescribed": saturation_prescribed,
        })

    free_convergence = _convergence(
        free_histories, validated["absolute_tolerance"], validated["relative_tolerance"]
    )
    prescribed_convergence = _convergence(
        prescribed_histories, validated["absolute_tolerance"], validated["relative_tolerance"]
    )
    for data in level_data:
        summary, rows = _step_metrics(
            model,
            data["times"],
            data["free_states"],
            data["prescribed_states"],
            data["lambda_values"],
            data["path_samples"],
            data["free_ledger"],
            data["prescribed_ledger"],
            validated,
            config_sha,
            git_sha or "",
            data["label"],
            data["step"],
            free_convergence,
            prescribed_convergence,
            data["saturation_free"],
            data["saturation_prescribed"],
            timeseries_path.name,
        )
        all_timeseries_rows.extend(rows)
        data["summary"] = summary

    all_refinements_smooth_unsaturated = all(
        data["saturation_free"]["stage_count_matches_expected"]
        and data["saturation_prescribed"]["stage_count_matches_expected"]
        and data["saturation_free"]["any_limiter_active_stages"] == 0
        and data["saturation_prescribed"]["any_limiter_active_stages"] == 0
        for data in level_data
    )
    for data in level_data:
        data["summary"]["all_refinements_smooth_unsaturated_regime"] = bool(
            all_refinements_smooth_unsaturated
        )
    decision, final_status = _acceptance_decision(level_data[-1]["summary"], validated["limits"])
    summary_rows: list[dict[str, Any]] = []
    for data in level_data:
        row = data["summary"]
        row["acceptance_decision"] = decision
        row["status"] = final_status
        summary_rows.append(row)

    _write_csv(timeseries_path, TIMESERIES_FIELDS, all_timeseries_rows)
    _write_csv(summary_path, SUMMARY_FIELDS, summary_rows)
    completed = datetime.now(timezone.utc).isoformat()
    manifest = {
        "schema_version": 1,
        "case_id": "PATH-01",
        "status": final_status,
        "acceptance_decision": decision,
        "smooth_unsaturated_regime": bool(all_refinements_smooth_unsaturated),
        "numerical_results_present": True,
        "resource_tests_executed": False,
        "started_at_utc": started,
        "completed_at_utc": completed,
        "parameter_source": validated["parameter_source"],
        "source_documents_or_measurement_ids": validated["source_documents_or_measurement_ids"],
        "config_path": str(config_path),
        "config_sha256": config_sha,
        "solver_git_sha": git_sha,
        "solver_file_sha256": solver_sha256,
        "runner_file_sha256": runner_sha256,
        "python_version": sys.version,
        "numpy_version": np.__version__,
        "operating_system": platform.platform(),
        "cpu": platform.processor() or None,
        "blas_environment": {
            key: os.environ.get(key)
            for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")
            if os.environ.get(key) is not None
        },
        "command_line": sys.argv,
        "output_files": {
            "timeseries_csv": timeseries_path.name,
            "summary_csv": summary_path.name,
        },
        "step_convergence": {
            "free": free_convergence,
            "prescribed": prescribed_convergence,
        },
        "acceptance_limits": validated["limits"],
        "notes": [
            "The prescribed path is an ideal kinematic constraint, not a physical servo capability model.",
            "The same deterministic current-command and constant external-force callbacks are used by both solvers.",
            "Current-reference and voltage saturation are counted at every RK4 stage callback; output-grid diagnostics are also written to the timeseries CSV.",
            "The RK4 observed-order screen is eligible for ordinary smooth-regime PASS only when neither limiter activates in either model at any of the h, h/2, h/4 or h/8 refinements; limiter-active or stage-count-mismatch cases remain report-only.",
            "The prescribed solver's final endpoint diagnostic is excluded from RK4-stage counts.",
            "The constrained energy ledger includes lambda * sdot_ref; the PI integrator is not physical stored energy.",
            "Kf/Ke mismatch power is reported separately as (Kf-Ke)*i*ell_dot.",
            "This runner does not execute resource unit tests or establish machine/HIL validity.",
        ],
    }
    with manifest_path.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(manifest, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    return {
        "case_id": "PATH-01",
        "status": final_status,
        "acceptance_decision": decision,
        "config_sha256": config_sha,
        "solver_git_sha": git_sha,
        "timeseries_csv": str(timeseries_path),
        "summary_csv": str(summary_path),
        "manifest_json": str(manifest_path),
        "free_convergence_screen": free_convergence["screen"],
        "prescribed_convergence_screen": prescribed_convergence["screen"],
        "smooth_unsaturated_regime": bool(all_refinements_smooth_unsaturated),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the configured CH12 PATH-01 free/prescribed path comparison."
    )
    parser.add_argument("--config", type=Path, required=True, help="completed PATH-01 JSON config")
    parser.add_argument(
        "--output-dir", type=Path, required=True,
        help="directory for timeseries, summary and provenance manifest outputs"
    )
    parser.add_argument(
        "--force", action="store_true",
        help="overwrite output files with the same three fixed names"
    )
    arguments = parser.parse_args(argv)
    try:
        result = run_path_comparison(arguments.config, arguments.output_dir, force=arguments.force)
    except (OSError, ValueError, RuntimeError, np.linalg.LinAlgError) as error:
        print(f"PATH-01 ERROR: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
