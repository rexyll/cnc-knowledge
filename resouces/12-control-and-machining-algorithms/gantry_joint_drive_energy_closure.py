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
REFERENCE_TIMESERIES_NAME = "gantry-joint-drive-energy-closure-reference-h16-timeseries.csv"
REFERENCE_LEVEL = "reference_h/16"
CONFIG_SCHEMA_VERSION = 4
MANIFEST_SCHEMA_VERSION = 6
LEVELS = ("h", "h/2", "h/4", "h/8")
# Bound aggregate output rows before allocating RK4 trajectories and row dictionaries.
MAX_TOTAL_SAMPLES = 50_000
MAX_TOTAL_STAGE_SAMPLES = 200_000
STATE_VECTOR_FIELDS = [
    "q1_m", "q2_rad", "q3_m", "q4_rad",
    "qdot1_m_s", "qdot2_rad_s", "qdot3_m_s", "qdot4_rad_s",
    "s_m", "s_dot_m_s", "current_A", "current_integrator_V",
]
STATE_COMPARISON_UNITS = {
    "q1_m": "m", "q2_rad": "rad", "q3_m": "m", "q4_rad": "rad",
    "qdot1_m_s": "m/s", "qdot2_rad_s": "rad/s",
    "qdot3_m_s": "m/s", "qdot4_rad_s": "rad/s",
    "s_m": "m", "s_dot_m_s": "m/s",
    "current_A": "A", "current_integrator_V": "V",
}
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
STAGE_TIMESERIES_NAME = "gantry-joint-drive-energy-closure-stage-power-timeseries.csv"
STAGE_FIELDS = [
    "case_id", "step_level", "interval_index", "stage_index", "stage_time_s", "step_s",
    "requested_current_command_A", "limited_current_reference_A", "current_A",
    "raw_voltage_V", "terminal_voltage_V",
    "terminal_input_power_W", "copper_loss_W", "structural_damping_loss_W",
    "axis_friction_loss_W", "external_generalized_power_W",
    "electromechanical_mismatch_power_W", "net_power_W",
    "current_reference_saturated", "voltage_saturated",
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
    "fixed_trajectory_net_power_work_J", "fixed_trajectory_absolute_net_power_work_J",
    "fixed_trajectory_quadrature_delta_from_finest_J",
    "coupled_vs_fixed_trajectory_net_work_delta_J",
    "coupled_stored_energy_delta_vs_finest_J",
    "coupled_net_work_delta_vs_finest_J",
    "coupled_energy_residual_delta_vs_finest_J",
    "rk4_stage_terminal_input_work_J", "rk4_stage_copper_loss_J",
    "rk4_stage_structural_damping_loss_J", "rk4_stage_axis_friction_loss_J",
    "rk4_stage_external_generalized_work_J", "rk4_stage_electromechanical_mismatch_work_J",
    "rk4_stage_net_power_work_J", "rk4_stage_absolute_net_power_work_J",
    "rk4_stage_energy_residual_J", "rk4_stage_vs_endpoint_simpson_net_work_delta_J",
    "current_reference_saturated_stages", "voltage_saturated_stages",
    "any_limiter_active_stages", "expected_rk4_stage_evaluations",
    "observed_rk4_stage_evaluations", "stage_count_matches_expected",
    "smooth_unsaturated", "residual_order_gate_status",
    "residual_order_noise_floor_J", "empirical_residual_order_from_previous",
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

def _validate_state_comparison_scale_contract(
    raw_scales: Any, source: Any, source_ids: Any, *, context: str,
) -> tuple[dict[str, float], str, list[str]]:
    """Validate sourced characteristic scales for the 12 state-vector components.

    These scales only nondimensionalize componentwise trajectory differences;
    they are not acceptance tolerances, state bounds, or an aggregate score.
    """
    if not isinstance(raw_scales, dict) or set(raw_scales) != set(STATE_VECTOR_FIELDS):
        raise EnergyClosureError(
            f"{context}.state_comparison_scales must define exactly all 12 state-vector fields"
        )
    scales = {
        field: path_support._number(
            raw_scales[field], f"{context}.state_comparison_scales.{field}", positive=True
        )
        for field in STATE_VECTOR_FIELDS
    }
    if not isinstance(source, str) or not source.strip():
        raise EnergyClosureError(f"{context}.state_comparison_scale_source is required")
    if not isinstance(source_ids, list) or not source_ids or any(
        not isinstance(item, str) or not item.strip() for item in source_ids
    ):
        raise EnergyClosureError(
            f"{context}.state_comparison_scale_source_ids must be a non-empty string array"
        )
    normalized_ids = [item.strip() for item in source_ids]
    if len(set(normalized_ids)) != len(normalized_ids):
        raise EnergyClosureError(f"{context}.state_comparison_scale_source_ids must be unique")
    return scales, source.strip(), normalized_ids


FLOAT64_UNIT_ROUNDOFF = 2.0 ** -53
FLOAT64_FORMAT_NAME = "IEEE-754 binary64"
NOISE_BUDGET_NUMERIC_FIELDS = (
    "max_abs_stored_energy_J",
    "stored_energy_evaluation_error_bound_J",
    "trajectory_energy_roundoff_effect_bound_J",
    "max_abs_net_power_W",
    "net_power_evaluation_error_bound_W",
    "trajectory_power_roundoff_effect_bound_W",
    "time_grid_roundoff_effect_bound_J",
)
NOISE_BUDGET_FIELDS = {
    "floating_point_format", "rounding_mode", "arithmetic_assumptions_confirmed",
    "no_overflow_or_subnormal_intermediates", *NOISE_BUDGET_NUMERIC_FIELDS,
}


def _gamma(operation_count: int, unit_roundoff: float = FLOAT64_UNIT_ROUNDOFF) -> float:
    """Higham-style gamma_k bound for k rounded operations, when k*u < 1."""
    if type(operation_count) is not int or operation_count < 0:
        raise ValueError("floating-point operation count must be a nonnegative integer")
    if operation_count == 0:
        return 0.0
    product = operation_count * unit_roundoff
    if product >= 1.0:
        raise ValueError("gamma_k is undefined for operation_count * unit_roundoff >= 1")
    denominator_lower = math.nextafter(1.0 - product, -math.inf)
    return math.nextafter(product / denominator_lower, math.inf)


def _derive_energy_residual_noise_budget(
    raw_budget: Any, duration_s: float, base_intervals: int, *, context: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Derive a conservative post-processing roundoff floor for all five levels.

    The supplied endpoint/sample/trajectory/time-grid bounds remain analyst
    inputs. The code derives the composite-Simpson accumulation and residual
    subtraction terms for the runner's current binary64 operation sequence.
    This is not a proof of the supplied physical-envelope or RK4 propagation
    bounds, nor does it include model-parameter uncertainty or RK4 truncation.
    """
    if not isinstance(raw_budget, dict) or set(raw_budget) != NOISE_BUDGET_FIELDS:
        raise EnergyClosureError(
            f"{context}.energy_residual_noise_budget must define the exact required fields"
        )
    if raw_budget.get("floating_point_format") != FLOAT64_FORMAT_NAME:
        raise EnergyClosureError(
            f"{context}.energy_residual_noise_budget.floating_point_format must be {FLOAT64_FORMAT_NAME}"
        )
    if raw_budget.get("rounding_mode") != "roundTiesToEven":
        raise EnergyClosureError(
            f"{context}.energy_residual_noise_budget.rounding_mode must be roundTiesToEven"
        )
    if raw_budget.get("arithmetic_assumptions_confirmed") is not True:
        raise EnergyClosureError(
            f"{context}.energy_residual_noise_budget.arithmetic_assumptions_confirmed must be true"
        )
    if raw_budget.get("no_overflow_or_subnormal_intermediates") is not True:
        raise EnergyClosureError(
            f"{context}.energy_residual_noise_budget.no_overflow_or_subnormal_intermediates must be true"
        )
    if (sys.float_info.radix != 2 or sys.float_info.mant_dig != 53
            or np.dtype(np.float64).itemsize != 8):
        raise EnergyClosureError("runtime does not satisfy the required IEEE-754 binary64 assumptions")
    budget = {
        "floating_point_format": FLOAT64_FORMAT_NAME,
        "rounding_mode": "roundTiesToEven",
        "arithmetic_assumptions_confirmed": True,
        "no_overflow_or_subnormal_intermediates": True,
    }
    for field in NOISE_BUDGET_NUMERIC_FIELDS:
        budget[field] = path_support._number(
            raw_budget.get(field), f"{context}.energy_residual_noise_budget.{field}", positive=True
        )

    if type(base_intervals) is not int or base_intervals < 2 or base_intervals % 2:
        raise ValueError("noise budget requires an even base interval count >= 2")
    finest_intervals = 16 * base_intervals
    unit_roundoff = FLOAT64_UNIT_ROUNDOFF
    gamma_one = _gamma(1)
    gamma_three = _gamma(3)
    odd_count = finest_intervals // 2
    even_count = odd_count - 1
    gamma_odd = _gamma(max(odd_count - 1, 0))
    gamma_even = _gamma(max(even_count - 1, 0))

    def up(value: float) -> float:
        return math.nextafter(float(value), math.inf)

    endpoint_energy_error = up(
        budget["stored_energy_evaluation_error_bound_J"]
        + budget["trajectory_energy_roundoff_effect_bound_J"]
    )
    sample_power_error = up(
        budget["net_power_evaluation_error_bound_W"]
        + budget["trajectory_power_roundoff_effect_bound_W"]
    )
    computed_power_abs_bound = up(budget["max_abs_net_power_W"] + sample_power_error)
    odd_weighted_abs_bound = up(odd_count * (1.0 + gamma_odd))
    even_weighted_abs_bound = up(even_count * (1.0 + gamma_even))
    weighted_abs_coefficient = up(
        2.0 + up(4.0 * odd_weighted_abs_bound) + up(2.0 * even_weighted_abs_bound)
    )
    weighted_abs_sum_bound = up(computed_power_abs_bound * weighted_abs_coefficient)
    odd_sum_roundoff = up(up(gamma_odd * odd_count) * computed_power_abs_bound)
    even_sum_roundoff = up(up(gamma_even * even_count) * computed_power_abs_bound)
    weighted_sum_roundoff = up(
        up(up(4.0 * odd_sum_roundoff) + up(2.0 * even_sum_roundoff))
        + up(gamma_three * weighted_abs_sum_bound)
    )

    reference_step = duration_s / finest_intervals
    alpha = reference_step / 3.0
    if not math.isfinite(alpha) or alpha <= sys.float_info.min:
        raise EnergyClosureError("reference Simpson h/3 is outside the normal binary64 range")
    alpha_upper = up(alpha)
    one_plus_u_upper = math.nextafter(1.0, math.inf)
    product_factor_upper = up(one_plus_u_upper * one_plus_u_upper)
    product_error_factor_upper = up(product_factor_upper - 1.0)
    simpson_accumulation_error = up(alpha_upper * up(
        product_factor_upper * weighted_sum_roundoff
        + product_error_factor_upper * weighted_abs_sum_bound
    ))
    time_factor_upper = up(1.0 + _gamma(2))
    time_bound = up(duration_s * time_factor_upper)
    sample_power_work_error = up(time_bound * sample_power_error)
    delta_energy_subtraction_error = up(
        gamma_one * 2.0 * up(budget["max_abs_stored_energy_J"] + endpoint_energy_error)
    )
    delta_energy_abs_bound = up(
        2.0 * up(budget["max_abs_stored_energy_J"] + endpoint_energy_error)
        + delta_energy_subtraction_error
    )
    net_work_abs_bound = up(
        time_bound * computed_power_abs_bound
        + simpson_accumulation_error
        + budget["time_grid_roundoff_effect_bound_J"]
    )
    residual_subtraction_error = up(
        gamma_one * up(delta_energy_abs_bound + net_work_abs_bound)
    )
    components = {
        "two_endpoint_energy_evaluation_and_trajectory_error_J": up(2.0 * endpoint_energy_error),
        "delta_energy_subtraction_roundoff_J": delta_energy_subtraction_error,
        "net_power_sample_evaluation_and_trajectory_error_J": sample_power_work_error,
        "composite_simpson_accumulation_roundoff_J": simpson_accumulation_error,
        "time_grid_roundoff_effect_J": budget["time_grid_roundoff_effect_bound_J"],
        "final_energy_residual_subtraction_roundoff_J": residual_subtraction_error,
    }
    subtotal = math.fsum(components.values())
    gamma_positive_sum = _gamma(len(components) - 1)
    aggregation_guard = up((gamma_positive_sum / (1.0 - gamma_positive_sum)) * subtotal)
    minimum_floor = math.nextafter(up(subtotal + aggregation_guard), math.inf)
    derived = {
        "floating_point_format": FLOAT64_FORMAT_NAME,
        "unit_roundoff": unit_roundoff,
        "duration_bound_s": time_bound,
        "finest_interval_count": finest_intervals,
        "reference_step_s": reference_step,
        "odd_sample_count": odd_count,
        "even_interior_sample_count": even_count,
        "gamma_odd_sum": gamma_odd,
        "gamma_even_sum": gamma_even,
        "gamma_outer_weighted_sum": gamma_three,
        "computed_net_power_sample_abs_bound_W": computed_power_abs_bound,
        "weighted_power_abs_sum_bound_W": weighted_abs_sum_bound,
        "weighted_sum_roundoff_bound_W": weighted_sum_roundoff,
        **components,
        "component_subtotal_J": subtotal,
        "positive_sum_aggregation_guard_J": aggregation_guard,
        "minimum_noise_floor_J": minimum_floor,
    }
    if not all(math.isfinite(float(value)) and float(value) >= 0.0
               for value in derived.values() if isinstance(value, (int, float))):
        raise FloatingPointError("derived ENE residual noise budget is non-finite or negative")
    return budget, derived


def _validate_noise_floor_not_below_derived_minimum(
    noise_floor_J: float, budget_report: dict[str, Any], *, context: str,
) -> None:
    minimum = float(budget_report["minimum_noise_floor_J"])
    if float(noise_floor_J) < minimum:
        raise EnergyClosureError(
            f"{context}.energy_residual_noise_floor_J is below the derived minimum "
            f"({minimum:.17g} J)"
        )


def _validate_residual_noise_floor_contract(
    value: Any, method: Any, source: Any, source_ids: Any, *, context: str,
) -> tuple[float, str, str, list[str]]:
    """Validate a pre-run, sourced bound for residual numerical noise.

    This is not derived from energy scales or this run's observed residuals.
    The source method must justify a conservative bound for the residual
    evaluation path and execution environment.
    """
    floor = path_support._number(
        value, f"{context}.energy_residual_noise_floor_J", positive=True
    )
    if not isinstance(method, str) or not method.strip():
        raise EnergyClosureError(f"{context}.energy_residual_noise_floor_method is required")
    if not isinstance(source, str) or not source.strip():
        raise EnergyClosureError(f"{context}.energy_residual_noise_floor_source is required")
    if not isinstance(source_ids, list) or not source_ids or any(
        not isinstance(item, str) or not item.strip() for item in source_ids
    ):
        raise EnergyClosureError(
            f"{context}.energy_residual_noise_floor_source_ids must be a non-empty string array"
        )
    normalized_ids = [item.strip() for item in source_ids]
    if len(set(normalized_ids)) != len(normalized_ids):
        raise EnergyClosureError(
            f"{context}.energy_residual_noise_floor_source_ids must be unique"
        )
    return floor, method.strip(), source.strip(), normalized_ids


def _residual_order_diagnostics(
    summaries: list[dict[str, Any]],
    reference_diagnostics: dict[str, Any],
    smooth_flags: list[bool],
    noise_floor_J: float,
) -> dict[str, Any]:
    """Gate energy-residual exponents against a predeclared floor and trend.

    Orders are emitted only when all five levels are smooth, all residuals
    exceed the floor, signs do not cross, and absolute residuals decrease
    strictly under refinement. This is a diagnostic gate, not a proof of
    asymptotic convergence or an error bound.
    """
    if len(summaries) != len(LEVELS) or len(smooth_flags) != len(LEVELS) + 1:
        raise ValueError("residual-order diagnostics require four primary and one reference level")
    finest = reference_diagnostics.get("finest") if isinstance(reference_diagnostics, dict) else None
    if not isinstance(finest, dict):
        raise ValueError("h/16 reference energy diagnostics are missing")
    residuals = [float(row["energy_residual_simpson_J"]) for row in summaries]
    residuals.append(float(finest["energy_residual_simpson_J"]))
    if not all(math.isfinite(value) for value in residuals):
        raise FloatingPointError("residual-order inputs must be finite")
    floor = float(noise_floor_J)
    if not math.isfinite(floor) or floor <= 0.0:
        raise ValueError("residual noise floor must be finite and positive")

    magnitudes = [abs(value) for value in residuals]
    if not all(smooth_flags):
        gate_status = "NONSMOOTH_OR_LIMITER_ACTIVE"
    elif any(value <= floor for value in magnitudes):
        gate_status = "AT_OR_BELOW_NOISE_FLOOR"
    elif any((value > 0.0) != (residuals[0] > 0.0) for value in residuals[1:]):
        gate_status = "SIGN_CROSSING"
    elif not all(fine < coarse for coarse, fine in zip(magnitudes, magnitudes[1:])):
        gate_status = "NON_MONOTONIC_MAGNITUDE"
    else:
        gate_status = "ELIGIBLE"

    orders: list[float | None] = [None] * len(LEVELS)
    if gate_status == "ELIGIBLE":
        log_two = math.log(2.0)
        for index, (coarse, fine) in enumerate(zip(magnitudes, magnitudes[1:])):
            order = (math.log(coarse) - math.log(fine)) / log_two
            if not math.isfinite(order):
                raise FloatingPointError("empirical residual order is non-finite")
            orders[index] = order
    return {
        "levels": [*LEVELS, REFERENCE_LEVEL],
        "energy_residual_simpson_J": residuals,
        "noise_floor_J": floor,
        "gate_status": gate_status,
        "pairwise_empirical_orders": orders,
    }


def _validate(config: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(config, dict) or type(config.get("schema_version")) is not int:
        raise EnergyClosureError("configuration must be an object with integer schema_version")
    if config["schema_version"] != CONFIG_SCHEMA_VERSION:
        raise EnergyClosureError(
            f"unsupported schema_version; expected integer {CONFIG_SCHEMA_VERSION} "
            "with sourced state scales and a derived residual noise budget"
        )
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
    total_samples = sum(intervals * (2 ** level) + 1 for level in range(len(LEVELS))) + 16 * intervals + 1
    total_stage_samples = sum(4 * intervals * (2 ** level) for level in range(len(LEVELS))) + 64 * intervals
    if total_stage_samples > MAX_TOTAL_STAGE_SAMPLES:
        raise EnergyClosureError(
            f"refinement schedule requires {total_stage_samples} RK4 stage rows; "
            f"configured safety limit is {MAX_TOTAL_STAGE_SAMPLES}"
        )
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
    state_comparison_scales, state_comparison_scale_source, state_comparison_scale_source_ids = (
        _validate_state_comparison_scale_contract(
            metrics.get("state_comparison_scales"),
            metrics.get("state_comparison_scale_source"),
            metrics.get("state_comparison_scale_source_ids"),
            context="metrics",
        )
    )
    residual_noise_floor, residual_noise_method, residual_noise_source, residual_noise_source_ids = (
        _validate_residual_noise_floor_contract(
            metrics.get("energy_residual_noise_floor_J"),
            metrics.get("energy_residual_noise_floor_method"),
            metrics.get("energy_residual_noise_floor_source"),
            metrics.get("energy_residual_noise_floor_source_ids"),
            context="metrics",
        )
    )
    residual_noise_budget, residual_noise_budget_report = _derive_energy_residual_noise_budget(
        metrics.get("energy_residual_noise_budget"), duration, intervals, context="metrics",
    )
    _validate_noise_floor_not_below_derived_minimum(
        residual_noise_floor, residual_noise_budget_report, context="metrics",
    )
    return {
        "case_id": case_id, "model": model, "initial": initial,
        "external": external, "duration": duration, "base_step": base_step,
        "intervals": intervals, "command": command, "scale": scale,
        "floor": floor, "threshold": threshold, "source": source.strip(),
        "source_ids": [x.strip() for x in ids],
        "state_comparison_scales": state_comparison_scales,
        "state_comparison_scale_source": state_comparison_scale_source,
        "state_comparison_scale_source_ids": state_comparison_scale_source_ids,
        "energy_residual_noise_floor_J": residual_noise_floor,
        "energy_residual_noise_floor_method": residual_noise_method,
        "energy_residual_noise_floor_source": residual_noise_source,
        "energy_residual_noise_floor_source_ids": residual_noise_source_ids,
        "energy_residual_noise_budget": residual_noise_budget,
        "energy_residual_noise_budget_report": residual_noise_budget_report,
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


def _fixed_trajectory_quadrature_diagnostics(
    fine_times: np.ndarray,
    fine_net_power: np.ndarray,
    coupled_net_works: list[float],
    coupled_stored_energy_deltas: list[float],
) -> list[dict[str, float]]:
    """Compare nested Simpson grids on one frozen finest-level state trajectory.

    The finest h/8 trajectory is sampled once. Coarser quadrature grids are
    exact nested subsets of those same time/state snapshots. This isolates
    quadrature-grid sensitivity conditional on that frozen trajectory; it
    does not bound the h/8 trajectory's own integration error.
    """
    times = np.asarray(fine_times, dtype=float)
    power = np.asarray(fine_net_power, dtype=float)
    if times.ndim != 1 or power.ndim != 1 or times.size != power.size:
        raise ValueError("fixed-trajectory time and power arrays must be matching vectors")
    if times.size < 17 or (times.size - 1) % 16:
        raise ValueError("fixed-trajectory grid must contain at least sixteen intervals divisible by sixteen")
    if not np.all(np.isfinite(times)) or not np.all(np.isfinite(power)):
        raise FloatingPointError("fixed-trajectory grid and power samples must be finite")
    if np.any(np.diff(times) <= 0):
        raise ValueError("fixed-trajectory times must be strictly increasing")
    if len(coupled_net_works) != len(LEVELS) or len(coupled_stored_energy_deltas) != len(LEVELS):
        raise ValueError("coupled comparison arrays must contain four refinement levels")
    if not all(math.isfinite(float(x)) for x in (*coupled_net_works, *coupled_stored_energy_deltas)):
        raise FloatingPointError("coupled comparison metrics must be finite")
    intervals = times.size - 1
    if not np.allclose(np.diff(times), (times[-1] - times[0]) / intervals,
                       rtol=1e-9, atol=1e-12):
        raise ValueError("fixed-trajectory time grid must be uniformly spaced")

    fixed_work = []
    fixed_abs_work = []
    for level_index in range(len(LEVELS)):
        stride = 2 ** (len(LEVELS) - 1 - level_index)
        selected_times = times[::stride]
        selected_power = power[::stride]
        if selected_times[-1] != times[-1]:
            raise ValueError("nested fixed-trajectory grid does not retain terminal sample")
        fixed_work.append(float(path_support.composite_simpson_13(selected_times, selected_power)))
        fixed_abs_work.append(float(path_support.composite_simpson_13(selected_times, np.abs(selected_power))))
    fine_reference_work = fixed_work[-1]
    fine_reference_delta = float(coupled_stored_energy_deltas[-1])
    result = []
    for index in range(len(LEVELS)):
        coupled_work = float(coupled_net_works[index])
        coupled_delta = float(coupled_stored_energy_deltas[index])
        fixed = fixed_work[index]
        quadrature_delta = fixed - fine_reference_work
        trajectory_delta = coupled_work - fixed
        total_work_delta = coupled_work - fine_reference_work
        stored_delta = coupled_delta - fine_reference_delta
        residual_delta = stored_delta - total_work_delta
        row = {
            "fixed_trajectory_net_power_work_J": fixed,
            "fixed_trajectory_absolute_net_power_work_J": fixed_abs_work[index],
            "fixed_trajectory_quadrature_delta_from_finest_J": quadrature_delta,
            "coupled_vs_fixed_trajectory_net_work_delta_J": trajectory_delta,
            "coupled_stored_energy_delta_vs_finest_J": stored_delta,
            "coupled_net_work_delta_vs_finest_J": total_work_delta,
            "coupled_energy_residual_delta_vs_finest_J": residual_delta,
        }
        if not all(math.isfinite(value) for value in row.values()):
            raise FloatingPointError("non-finite fixed-trajectory quadrature diagnostic")
        if not math.isclose(
            total_work_delta, quadrature_delta + trajectory_delta,
            rel_tol=1e-9, abs_tol=1e-12,
        ):
            raise ArithmeticError("fixed-trajectory quadrature/trajectory work decomposition failed")
        result.append(row)
    return result



def _rk4_stage_power_diagnostics(
    stage_rows: list[dict[str, Any]],
    delta_stored_energy: float,
    endpoint_simpson_net_work: float,
) -> dict[str, float]:
    """Integrate persisted RK4-stage power snapshots with classical RK4 weights.

    This is an in-step sampling diagnostic tied to the solver's own RK4 stages.
    It is not an independent high-order quadrature oracle or an error bound.
    """
    if len(stage_rows) == 0 or len(stage_rows) % 4:
        raise ValueError("RK4 stage power trace must contain complete groups of four")
    component_fields = {
        "terminal_input": "terminal_input_power_W",
        "copper": "copper_loss_W",
        "structural": "structural_damping_loss_W",
        "friction": "axis_friction_loss_W",
        "external": "external_generalized_power_W",
        "mismatch": "electromechanical_mismatch_power_W",
        "net": "net_power_W",
    }
    totals = {key: 0.0 for key in component_fields}
    absolute_net = 0.0
    weights = (1.0, 2.0, 2.0, 1.0)
    for offset in range(0, len(stage_rows), 4):
        block = stage_rows[offset:offset + 4]
        if [int(float(row["stage_index"])) for row in block] != [0, 1, 2, 3]:
            raise ValueError("RK4 stage power trace order must be k1,k2,k3,k4 per interval")
        step = float(block[0]["step_s"])
        if not math.isfinite(step) or step <= 0.0 or any(
            not math.isclose(float(row["step_s"]), step, rel_tol=1e-12, abs_tol=0.0)
            for row in block
        ):
            raise ValueError("RK4 stage power trace has inconsistent step size")
        for key, field in component_fields.items():
            values = [float(row[field]) for row in block]
            if not all(math.isfinite(value) for value in values):
                raise FloatingPointError("RK4 stage power trace contains non-finite power")
            totals[key] += step / 6.0 * math.fsum(w * value for w, value in zip(weights, values))
        net_values = [float(row["net_power_W"]) for row in block]
        absolute_net += step / 6.0 * math.fsum(
            w * abs(value) for w, value in zip(weights, net_values)
        )
    result = {
        "rk4_stage_terminal_input_work_J": totals["terminal_input"],
        "rk4_stage_copper_loss_J": totals["copper"],
        "rk4_stage_structural_damping_loss_J": totals["structural"],
        "rk4_stage_axis_friction_loss_J": totals["friction"],
        "rk4_stage_external_generalized_work_J": totals["external"],
        "rk4_stage_electromechanical_mismatch_work_J": totals["mismatch"],
        "rk4_stage_net_power_work_J": totals["net"],
        "rk4_stage_absolute_net_power_work_J": absolute_net,
        "rk4_stage_energy_residual_J": float(delta_stored_energy) - totals["net"],
        "rk4_stage_vs_endpoint_simpson_net_work_delta_J":
            totals["net"] - float(endpoint_simpson_net_work),
    }
    if not all(math.isfinite(value) for value in result.values()):
        raise FloatingPointError("non-finite RK4-stage power diagnostic")
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




def _timeseries_row(case_id: str, step_level: str, step: float, time_s: float,
                    vector: np.ndarray, sample: dict[str, Any],
                    command: float) -> dict[str, Any]:
    """Build the canonical endpoint/reference power timeseries row."""
    vector = np.asarray(vector, dtype=float)
    if vector.shape != (12,) or not np.all(np.isfinite(vector)):
        raise FloatingPointError("timeseries state must contain 12 finite values")
    row = {"case_id": case_id, "step_level": step_level,
           "step_s": float(step), "time_s": float(time_s)}
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
    return row


def _reference_trajectory_diagnostics(
    reference_rows: list[dict[str, Any]],
    primary_rows: list[dict[str, Any]],
    summary_by_level: dict[str, dict[str, Any]],
    scale: float,
    floor: float,
) -> dict[str, Any]:
    """Compare the four coupled trajectories against one h/16 RK4 reference.

    The h/16 path is a finer numerical reference from the same solver, not an
    exact solution or an independent physical model. Coarse reference powers
    are sampled on each matching output grid before comparing coupled work.
    """
    if len(reference_rows) < 33 or (len(reference_rows) - 1) % 16:
        raise ValueError("h/16 reference trajectory requires at least 32 intervals divisible by sixteen")
    ref_times = np.asarray([float(row["time_s"]) for row in reference_rows], dtype=float)
    ref_states = np.asarray([
        [float(row[field]) for field in STATE_VECTOR_FIELDS] for row in reference_rows
    ], dtype=float)
    ref_stored = np.asarray([float(row["stored_energy_J"]) for row in reference_rows], dtype=float)
    ref_net = np.asarray([float(row["net_power_W"]) for row in reference_rows], dtype=float)
    if not all(np.all(np.isfinite(array)) for array in (ref_times, ref_states, ref_stored, ref_net)):
        raise FloatingPointError("h/16 reference trajectory contains non-finite data")
    if np.any(np.diff(ref_times) <= 0):
        raise ValueError("h/16 reference times must be strictly increasing")
    intervals = ref_times.size - 1
    if not np.allclose(np.diff(ref_times), (ref_times[-1] - ref_times[0]) / intervals,
                       rtol=1e-9, atol=1e-12):
        raise ValueError("h/16 reference time grid must be uniformly spaced")
    delta_reference = float(ref_stored[-1] - ref_stored[0])
    fine_work = float(path_support.composite_simpson_13(ref_times, ref_net))
    fine_abs_work = float(path_support.composite_simpson_13(ref_times, np.abs(ref_net)))
    fine_residual = delta_reference - fine_work
    fine_rho = abs(fine_residual) / max(scale, fine_abs_work, floor)
    finest = {
        "intervals": intervals, "samples": int(ref_times.size),
        "step_s": float((ref_times[-1] - ref_times[0]) / intervals),
        "delta_stored_energy_J": delta_reference,
        "net_power_work_J": fine_work,
        "absolute_net_power_work_J": fine_abs_work,
        "energy_residual_simpson_J": fine_residual,
        "normalized_energy_residual": fine_rho,
    }
    if not all(math.isfinite(float(value)) for value in finest.values()):
        raise FloatingPointError("non-finite h/16 reference energy-closure metric")
    comparisons = []
    for level_index, label in enumerate(LEVELS):
        level_rows = [row for row in primary_rows if row["step_level"] == label]
        expected_intervals = intervals // (2 ** (len(LEVELS) - level_index))
        expected_samples = expected_intervals + 1
        if len(level_rows) != expected_samples:
            raise ValueError(f"primary trajectory row count does not align with h/16 reference at {label}")
        stride = 2 ** (len(LEVELS) - level_index)
        selected_times = ref_times[::stride]
        selected_states = ref_states[::stride]
        selected_net = ref_net[::stride]
        if selected_times.size != expected_samples:
            raise ValueError(f"h/16 reference nested grid has wrong sample count at {label}")
        primary_times = np.asarray([float(row["time_s"]) for row in level_rows], dtype=float)
        primary_states = np.asarray([
            [float(row[field]) for field in STATE_VECTOR_FIELDS] for row in level_rows
        ], dtype=float)
        primary_net = np.asarray([float(row["net_power_W"]) for row in level_rows], dtype=float)
        if not all(np.all(np.isfinite(array)) for array in (primary_times, primary_states, primary_net)):
            raise FloatingPointError(f"primary trajectory comparison contains non-finite data at {label}")
        if not np.allclose(primary_times, selected_times, rtol=1e-9, atol=1e-12):
            raise ValueError(f"primary and h/16 reference time grids do not align at {label}")
        state_difference = primary_states - selected_states
        net_difference = primary_net - selected_net
        reference_work = float(path_support.composite_simpson_13(selected_times, selected_net))
        reference_abs_work = float(path_support.composite_simpson_13(selected_times, np.abs(selected_net)))
        reference_residual = delta_reference - reference_work
        reference_rho = abs(reference_residual) / max(scale, reference_abs_work, floor)
        primary_summary = summary_by_level[label]
        primary_work = float(primary_summary["net_power_work_J"])
        primary_delta = float(primary_summary["delta_stored_energy_J"])
        primary_residual = float(primary_summary["energy_residual_simpson_J"])
        comparisons.append({
            "step_level": label,
            "reference_net_power_work_J": reference_work,
            "reference_absolute_net_power_work_J": reference_abs_work,
            "reference_quadrature_delta_from_h16_J": reference_work - fine_work,
            "reference_energy_residual_at_level_J": reference_residual,
            "reference_normalized_energy_residual_at_level": reference_rho,
            "coupled_vs_reference_net_work_delta_J": primary_work - reference_work,
            "coupled_stored_energy_delta_vs_reference_J": primary_delta - delta_reference,
            "coupled_energy_residual_delta_vs_reference_J": primary_residual - reference_residual,
            "state_max_abs_difference": np.max(np.abs(state_difference), axis=0).tolist(),
            "state_rms_difference": np.sqrt(np.mean(state_difference**2, axis=0)).tolist(),
            "net_power_max_abs_difference_W": float(np.max(np.abs(net_difference))),
            "net_power_rms_difference_W": float(np.sqrt(np.mean(net_difference**2))),
        })
    if not all(math.isfinite(value) for item in comparisons
               for value in (item["reference_net_power_work_J"],
                             item["reference_absolute_net_power_work_J"],
                             item["reference_quadrature_delta_from_h16_J"],
                             item["reference_energy_residual_at_level_J"],
                             item["reference_normalized_energy_residual_at_level"],
                             item["coupled_vs_reference_net_work_delta_J"],
                             item["coupled_stored_energy_delta_vs_reference_J"],
                             item["coupled_energy_residual_delta_vs_reference_J"],
                             item["net_power_max_abs_difference_W"],
                             item["net_power_rms_difference_W"],
                             *item["state_max_abs_difference"], *item["state_rms_difference"])):
        raise FloatingPointError("non-finite h/16 reference comparison metric")
    return {"level": REFERENCE_LEVEL, "finest": finest, "comparisons": comparisons}




def _adjacent_refinement_diagnostics(
    primary_rows: list[dict[str, Any]],
    reference_rows: list[dict[str, Any]],
    smooth_flags: dict[str, bool],
    state_comparison_scales: dict[str, float],
) -> dict[str, Any]:
    """Compare adjacent trajectories on a common grid and normalize each component.

    The same-model RK4 solutions are compared without collapsing mixed-unit
    state errors or inferring an error order. Sourced characteristic scales only
    nondimensionalize each of the 12 component differences; they are not
    tolerances or an aggregate score. This is not an error bound or acceptance gate.
    """
    trajectories = {
        label: [row for row in primary_rows if row["step_level"] == label]
        for label in LEVELS
    }
    trajectories[REFERENCE_LEVEL] = reference_rows
    ordered_levels = list(LEVELS) + [REFERENCE_LEVEL]
    if any(not isinstance(smooth_flags.get(level), bool) for level in ordered_levels):
        raise ValueError("adjacent-refinement smooth flags must cover all five levels")
    pairs = []
    for coarse_level, fine_level in zip(ordered_levels[:-1], ordered_levels[1:]):
        coarse_rows = trajectories[coarse_level]
        fine_rows = trajectories[fine_level]
        if len(coarse_rows) < 3 or (len(coarse_rows) - 1) % 2:
            raise ValueError(f"coarse trajectory grid must have an even interval count at {coarse_level}")
        expected_fine_samples = 2 * (len(coarse_rows) - 1) + 1
        if len(fine_rows) != expected_fine_samples:
            raise ValueError(
                f"adjacent trajectory sample count is not nested for {coarse_level}/{fine_level}"
            )
        coarse_times = np.asarray([float(row["time_s"]) for row in coarse_rows], dtype=float)
        fine_times_all = np.asarray([float(row["time_s"]) for row in fine_rows], dtype=float)
        fine_times = fine_times_all[::2]
        if not np.all(np.isfinite(coarse_times)) or not np.all(np.isfinite(fine_times_all)):
            raise FloatingPointError("adjacent trajectory times must be finite")
        if np.any(np.diff(coarse_times) <= 0) or np.any(np.diff(fine_times_all) <= 0):
            raise ValueError("adjacent trajectory times must be strictly increasing")
        if not np.allclose(np.diff(coarse_times),
                           (coarse_times[-1] - coarse_times[0]) / (len(coarse_times) - 1),
                           rtol=1e-9, atol=1e-12):
            raise ValueError(f"coarse trajectory grid must be uniform at {coarse_level}")
        if not np.allclose(np.diff(fine_times_all),
                           (fine_times_all[-1] - fine_times_all[0]) / (len(fine_times_all) - 1),
                           rtol=1e-9, atol=1e-12):
            raise ValueError(f"fine trajectory grid must be uniform at {fine_level}")
        if not np.allclose(coarse_times, fine_times, rtol=1e-9, atol=1e-12):
            raise ValueError(f"adjacent trajectory grids do not align for {coarse_level}/{fine_level}")

        coarse_states = np.asarray([
            [float(row[field]) for field in STATE_VECTOR_FIELDS] for row in coarse_rows
        ], dtype=float)
        fine_states = np.asarray([
            [float(row[field]) for field in STATE_VECTOR_FIELDS] for row in fine_rows
        ], dtype=float)[::2]
        coarse_net = np.asarray([float(row["net_power_W"]) for row in coarse_rows], dtype=float)
        fine_net = np.asarray([float(row["net_power_W"]) for row in fine_rows], dtype=float)[::2]
        coarse_stored = np.asarray([float(row["stored_energy_J"]) for row in coarse_rows], dtype=float)
        fine_stored = np.asarray([float(row["stored_energy_J"]) for row in fine_rows], dtype=float)[::2]
        arrays = (coarse_states, fine_states, coarse_net, fine_net, coarse_stored, fine_stored)
        if not all(np.all(np.isfinite(array)) for array in arrays):
            raise FloatingPointError(f"adjacent trajectory samples must be finite for {coarse_level}/{fine_level}")

        state_difference = fine_states - coarse_states
        scale_vector = np.asarray(
            [state_comparison_scales[field] for field in STATE_VECTOR_FIELDS], dtype=float
        )
        if scale_vector.shape != (len(STATE_VECTOR_FIELDS),) or not np.all(
            np.isfinite(scale_vector) & (scale_vector > 0.0)
        ):
            raise ValueError("state comparison scales must be finite and positive for all fields")
        power_difference = fine_net - coarse_net
        coarse_work = float(path_support.composite_simpson_13(coarse_times, coarse_net))
        fine_work = float(path_support.composite_simpson_13(coarse_times, fine_net))
        coarse_delta = float(coarse_stored[-1] - coarse_stored[0])
        fine_delta = float(fine_stored[-1] - fine_stored[0])
        coarse_residual = coarse_delta - coarse_work
        fine_residual = fine_delta - fine_work
        row = {
            "coarse_level": coarse_level,
            "fine_level": fine_level,
            "shared_samples": int(len(coarse_times)),
            "both_paths_smooth_unsaturated": bool(
                smooth_flags[coarse_level] and smooth_flags[fine_level]
            ),
            "state_max_abs_difference": np.max(np.abs(state_difference), axis=0).tolist(),
            "state_rms_difference": np.sqrt(np.mean(state_difference**2, axis=0)).tolist(),
            "state_max_abs_difference_normalized":
                (np.max(np.abs(state_difference), axis=0) / scale_vector).tolist(),
            "state_rms_difference_normalized":
                (np.sqrt(np.mean(state_difference**2, axis=0)) / scale_vector).tolist(),
            "net_power_max_abs_difference_W": float(np.max(np.abs(power_difference))),
            "net_power_rms_difference_W": float(np.sqrt(np.mean(power_difference**2))),
            "coarse_net_power_work_on_shared_grid_J": coarse_work,
            "fine_net_power_work_on_shared_grid_J": fine_work,
            "fine_minus_coarse_net_work_on_shared_grid_J": fine_work - coarse_work,
            "coarse_stored_energy_delta_J": coarse_delta,
            "fine_stored_energy_delta_on_shared_grid_J": fine_delta,
            "fine_minus_coarse_stored_energy_delta_J": fine_delta - coarse_delta,
            "coarse_energy_residual_on_shared_grid_J": coarse_residual,
            "fine_energy_residual_on_shared_grid_J": fine_residual,
            "fine_minus_coarse_energy_residual_J": fine_residual - coarse_residual,
        }
        numeric = [
            row["net_power_max_abs_difference_W"], row["net_power_rms_difference_W"],
            row["coarse_net_power_work_on_shared_grid_J"],
            row["fine_net_power_work_on_shared_grid_J"],
            row["fine_minus_coarse_net_work_on_shared_grid_J"],
            row["coarse_stored_energy_delta_J"],
            row["fine_stored_energy_delta_on_shared_grid_J"],
            row["fine_minus_coarse_stored_energy_delta_J"],
            row["coarse_energy_residual_on_shared_grid_J"],
            row["fine_energy_residual_on_shared_grid_J"],
            row["fine_minus_coarse_energy_residual_J"],
            *row["state_max_abs_difference"], *row["state_rms_difference"],
            *row["state_max_abs_difference_normalized"],
            *row["state_rms_difference_normalized"],
        ]
        if not all(math.isfinite(value) for value in numeric):
            raise FloatingPointError("non-finite adjacent-refinement comparison metric")
        pairs.append(row)
    return {
        "pair_order": [list(pair) for pair in zip(ordered_levels[:-1], ordered_levels[1:])],
        "pairs": pairs,
    }


def _assert_json_metrics_close(actual: Any, expected: Any, path: str = "reference") -> None:
    """Compare nested manifest diagnostics with independently recomputed values."""
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or set(actual) != set(expected):
            raise EnergyClosureError(f"{path} structure is inconsistent")
        for key in expected:
            _assert_json_metrics_close(actual[key], expected[key], f"{path}.{key}")
    elif isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            raise EnergyClosureError(f"{path} array length is inconsistent")
        for index, (actual_item, expected_item) in enumerate(zip(actual, expected)):
            _assert_json_metrics_close(actual_item, expected_item, f"{path}[{index}]")
    elif expected is None:
        if actual is not None:
            raise EnergyClosureError(f"{path} value is inconsistent")
    elif isinstance(expected, bool) or isinstance(expected, str):
        if actual != expected:
            raise EnergyClosureError(f"{path} value is inconsistent")
    else:
        if isinstance(actual, bool) or not isinstance(actual, (int, float)) or not math.isfinite(float(actual)):
            raise EnergyClosureError(f"{path} numeric value is invalid")
        if not math.isclose(float(actual), float(expected), rel_tol=1e-9, abs_tol=1e-12):
            raise EnergyClosureError(f"{path} numeric value is inconsistent")


def _assert_json_metrics_exact(actual: Any, expected: Any, path: str = "reference") -> None:
    """Require exact JSON value equality for the deterministic noise-budget contract."""
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or set(actual) != set(expected):
            raise EnergyClosureError(f"{path} structure is inconsistent")
        for key in expected:
            _assert_json_metrics_exact(actual[key], expected[key], f"{path}.{key}")
    elif isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            raise EnergyClosureError(f"{path} array length is inconsistent")
        for index, (actual_item, expected_item) in enumerate(zip(actual, expected)):
            _assert_json_metrics_exact(actual_item, expected_item, f"{path}[{index}]")
    elif isinstance(expected, bool):
        if actual is not expected:
            raise EnergyClosureError(f"{path} value is inconsistent")
    elif expected is None:
        if actual is not None:
            raise EnergyClosureError(f"{path} value is inconsistent")
    elif isinstance(expected, (int, float)):
        if isinstance(actual, bool) or not isinstance(actual, (int, float)) or actual != expected:
            raise EnergyClosureError(f"{path} value is inconsistent")
    elif actual != expected:
        raise EnergyClosureError(f"{path} value is inconsistent")


def _atomic_bundle(output: Path, times: list[dict[str, Any]],
                   stage_rows: list[dict[str, Any]], reference_rows: list[dict[str, Any]],
                   summaries: list[dict[str, Any]], manifest: dict[str, Any]) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    time_path, stage_path, reference_path, summary_path, manifest_path = (
        output / TIMESERIES_NAME, output / STAGE_TIMESERIES_NAME,
        output / REFERENCE_TIMESERIES_NAME, output / SUMMARY_NAME, output / MANIFEST_NAME
    )
    targets = (time_path, stage_path, reference_path, summary_path, manifest_path)
    if any(p.exists() for p in targets):
        raise FileExistsError("ENE output bundle already exists; choose a new directory")
    with tempfile.TemporaryDirectory(prefix=".ene-staging-", dir=output) as tmp:
        stage = Path(tmp)
        staged_time, staged_stage, staged_reference, staged_summary, staged_manifest = (
            stage / TIMESERIES_NAME, stage / STAGE_TIMESERIES_NAME,
            stage / REFERENCE_TIMESERIES_NAME, stage / SUMMARY_NAME, stage / MANIFEST_NAME
        )
        for path, fields, rows in (
            (staged_time, TIME_FIELDS, times),
            (staged_stage, STAGE_FIELDS, stage_rows),
            (staged_reference, TIME_FIELDS, reference_rows),
            (staged_summary, SUMMARY_FIELDS, summaries),
        ):
            with path.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="raise")
                writer.writeheader()
                writer.writerows(rows)
        artifacts = {}
        for key, path, rows, fields in (
            ("timeseries_csv", staged_time, times, TIME_FIELDS),
            ("stage_power_csv", staged_stage, stage_rows, STAGE_FIELDS),
            ("reference_timeseries_csv", staged_reference, reference_rows, TIME_FIELDS),
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
        os.replace(staged_stage, stage_path)
        os.replace(staged_reference, reference_path)
        os.replace(staged_summary, summary_path)
        os.replace(staged_manifest, manifest_path)
    return artifacts


def _validate_manifest_contract(manifest: dict[str, Any]) -> dict[str, Any]:
    if type(manifest.get("schema_version")) is not int or manifest["schema_version"] != MANIFEST_SCHEMA_VERSION:
        raise EnergyClosureError(
            "invalid ENE manifest schema; expected version 6 with derived residual-noise budget"
        )
    if type(manifest.get("config_schema_version")) is not int or manifest["config_schema_version"] != CONFIG_SCHEMA_VERSION:
        raise EnergyClosureError("manifest config_schema_version must be 4")
    if manifest.get("case_id") not in ("ENE-01", "ENE-02", "ENE-03"):
        raise EnergyClosureError("invalid ENE manifest case_id")
    status = manifest.get("status")
    if status not in ("PASS", "FAIL", "COMPLETED_REPORT_ONLY"):
        raise EnergyClosureError("manifest status is missing or invalid")
    if manifest.get("numerical_results_present") is not True:
        raise EnergyClosureError("manifest numerical_results_present must be true")
    if manifest.get("resource_tests_executed") is not False:
        raise EnergyClosureError("manifest resource_tests_executed must be false")
    state_comparison_scales, state_comparison_scale_source, state_comparison_scale_source_ids = (
        _validate_state_comparison_scale_contract(
            manifest.get("state_comparison_scales"),
            manifest.get("state_comparison_scale_source"),
            manifest.get("state_comparison_scale_source_ids"),
            context="manifest",
        )
    )
    if manifest.get("state_vector_order") != STATE_VECTOR_FIELDS:
        raise EnergyClosureError("manifest state_vector_order is inconsistent")
    if manifest.get("state_comparison_units") != STATE_COMPARISON_UNITS:
        raise EnergyClosureError("manifest state_comparison_units are inconsistent")
    residual_noise_floor, residual_noise_method, residual_noise_source, residual_noise_source_ids = (
        _validate_residual_noise_floor_contract(
            manifest.get("energy_residual_noise_floor_J"),
            manifest.get("energy_residual_noise_floor_method"),
            manifest.get("energy_residual_noise_floor_source"),
            manifest.get("energy_residual_noise_floor_source_ids"),
            context="manifest",
        )
    )
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
    if not math.isfinite(ratio) or ratio > sys.maxsize // 16:
        raise EnergyClosureError("manifest duration/base_step ratio exceeds the supported index range for h/16 refinement")
    base_intervals = int(round(ratio))
    if base_intervals < 2 or base_intervals % 2 or not math.isclose(
        base_intervals * base_step, duration, rel_tol=1e-9, abs_tol=1e-12
    ):
        raise EnergyClosureError("manifest duration/base_step does not define an even integer interval count")
    total_samples = sum(base_intervals * (2 ** level) + 1 for level in range(len(LEVELS))) + 16 * base_intervals + 1
    total_stage_samples = sum(4 * base_intervals * (2 ** level) for level in range(len(LEVELS))) + 64 * base_intervals
    if total_stage_samples > MAX_TOTAL_STAGE_SAMPLES:
        raise EnergyClosureError(
            f"manifest refinement schedule requires {total_stage_samples} RK4 stage rows; "
            f"supported limit is {MAX_TOTAL_STAGE_SAMPLES}"
        )
    if total_samples > MAX_TOTAL_SAMPLES:
        raise EnergyClosureError(
            f"manifest refinement schedule requires {total_samples} samples; "
            f"supported limit is {MAX_TOTAL_SAMPLES}"
        )
    noise_budget, noise_budget_report = _derive_energy_residual_noise_budget(
        manifest.get("energy_residual_noise_budget"), duration, base_intervals,
        context="manifest",
    )
    _validate_noise_floor_not_below_derived_minimum(
        residual_noise_floor, noise_budget_report, context="manifest",
    )
    _assert_json_metrics_exact(
        manifest.get("energy_residual_noise_budget_report"), noise_budget_report,
        "energy_residual_noise_budget_report",
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
    reference_report = manifest.get("reference_trajectory_report")
    if not isinstance(reference_report, dict) or reference_report.get("level") != REFERENCE_LEVEL:
        raise EnergyClosureError("manifest h/16 reference trajectory report is missing or invalid")
    reference_intervals = 16 * base_intervals
    reference_expected_stages = 4 * reference_intervals
    for key, expected_value in (("intervals", reference_intervals),
                                ("samples", reference_intervals + 1),
                                ("expected_stage_evaluations", reference_expected_stages)):
        if type(reference_report.get(key)) is not int or reference_report[key] != expected_value:
            raise EnergyClosureError(f"manifest h/16 reference {key} is inconsistent")
    if not math.isclose(float(reference_report.get("step_s", math.nan)),
                        duration / reference_intervals, rel_tol=1e-9, abs_tol=1e-12):
        raise EnergyClosureError("manifest h/16 reference step size is inconsistent")
    for key in ("stage_evaluations", "current_reference_saturated_stages",
                "voltage_saturated_stages", "any_limiter_active_stages"):
        if type(reference_report.get(key)) is not int or reference_report[key] < 0:
            raise EnergyClosureError(f"manifest h/16 reference {key} is invalid")
    if reference_report["stage_evaluations"] != reference_expected_stages:
        raise EnergyClosureError("manifest h/16 reference stage evaluation count is inconsistent")
    ref_counts = [reference_report[k] for k in (
        "current_reference_saturated_stages", "voltage_saturated_stages", "any_limiter_active_stages")]
    if any(x > reference_expected_stages for x in ref_counts) or ref_counts[2] < max(ref_counts[:2]) or ref_counts[2] > sum(ref_counts[:2]):
        raise EnergyClosureError("manifest h/16 reference limiter counts are inconsistent")
    if reference_report.get("stage_count_matches_expected") is not True:
        raise EnergyClosureError("manifest h/16 reference stage count does not match expected")
    if reference_report.get("smooth_unsaturated") is not (ref_counts[2] == 0):
        raise EnergyClosureError("manifest h/16 reference smooth-unsaturated flag is inconsistent")
    if not isinstance(reference_report.get("stage_power_diagnostics"), dict):
        raise EnergyClosureError("manifest h/16 stage power diagnostics are missing")
    return {
        "status": status, "threshold": None if threshold is None else float(threshold),
        "duration": duration, "base_intervals": base_intervals,
        "all_smooth": all_smooth,
        "all_stage_counts_match": all(stage_match_flags),
        "reference_report": reference_report,
        "smooth_flags": [*smooth_flags, reference_report["smooth_unsaturated"]],
        "energy_residual_noise_floor_J": residual_noise_floor,
        "energy_residual_noise_floor_method": residual_noise_method,
        "energy_residual_noise_floor_source": residual_noise_source,
        "energy_residual_noise_floor_source_ids": residual_noise_source_ids,
        "energy_residual_noise_budget": noise_budget,
        "energy_residual_noise_budget_report": noise_budget_report,
        "state_comparison_scales": state_comparison_scales,
        "state_comparison_scale_source": state_comparison_scale_source,
        "state_comparison_scale_source_ids": state_comparison_scale_source_ids,
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
            categorical = {
                "case_id", "step_level", "status", "residual_order_gate_status", *boolean_fields
            }
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
    if not isinstance(artifacts, dict) or set(artifacts) != {"timeseries_csv", "stage_power_csv", "reference_timeseries_csv", "summary_csv"}:
        raise EnergyClosureError("manifest output_artifacts must contain exactly four CSV artifacts")
    verified: dict[str, dict[str, Any]] = {}
    parsed: dict[str, list[dict[str, str]]] = {}
    for key, name, fields, bool_fields, blank_fields in (
        ("timeseries_csv", TIMESERIES_NAME, TIME_FIELDS,
         ("current_reference_saturated", "voltage_saturated"), ()),
        ("stage_power_csv", STAGE_TIMESERIES_NAME, STAGE_FIELDS,
         ("current_reference_saturated", "voltage_saturated"), ()),
        ("reference_timeseries_csv", REFERENCE_TIMESERIES_NAME, TIME_FIELDS,
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
    expected_residual_order = _residual_order_diagnostics(
        summary_rows, manifest.get("reference_trajectory_diagnostics"),
        contract["smooth_flags"], contract["energy_residual_noise_floor_J"],
    )
    _assert_json_metrics_exact(
        manifest.get("residual_order_diagnostic"), expected_residual_order,
        "residual_order_diagnostic",
    )
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
        expected_order = (
            None if index == 0
            else expected_residual_order["pairwise_empirical_orders"][index - 1]
        )
        order_text = row["empirical_residual_order_from_previous"]
        if expected_order is None:
            if order_text != "":
                raise EnergyClosureError(f"empirical residual order must be blank at {label}")
        elif not order_text or not math.isclose(
            float(order_text), expected_order, rel_tol=1e-9, abs_tol=1e-12
        ):
            raise EnergyClosureError(f"empirical residual order is inconsistent at {label}")
        if row["residual_order_gate_status"] != expected_residual_order["gate_status"]:
            raise EnergyClosureError(f"residual-order gate status is inconsistent at {label}")
        if not math.isclose(
            float(row["residual_order_noise_floor_J"]),
            contract["energy_residual_noise_floor_J"], rel_tol=1e-12, abs_tol=0.0,
        ):
            raise EnergyClosureError(f"residual noise floor is inconsistent at {label}")
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
        report = (contract["reference_report"] if label == REFERENCE_LEVEL
                  else manifest["limiter_stage_reports"][index])
        reference_count = sum(row["current_reference_saturated"] == "True" for row in block)
        voltage_count = sum(row["voltage_saturated"] == "True" for row in block)
        any_count = sum(
            row["current_reference_saturated"] == "True" or row["voltage_saturated"] == "True"
            for row in block
        )
        if (
            reference_count != report["current_reference_saturated_stages"]
            or voltage_count != report["voltage_saturated_stages"]
            or any_count != report["any_limiter_active_stages"]
        ):
            raise EnergyClosureError(f"RK4 stage limiter trace disagrees with manifest at {label}")
        if label == REFERENCE_LEVEL:
            reference_stored = float(reference_rows[-1]["stored_energy_J"]) - float(reference_rows[0]["stored_energy_J"])
            reference_net_work = float(path_support.composite_simpson_13(
                np.asarray([float(item["time_s"]) for item in reference_rows], dtype=float),
                np.asarray([float(item["net_power_W"]) for item in reference_rows], dtype=float),
            ))
            expected_stage_metrics = _rk4_stage_power_diagnostics(block, reference_stored, reference_net_work)
            _assert_json_metrics_close(
                report["stage_power_diagnostics"], expected_stage_metrics,
                "reference_trajectory_report.stage_power_diagnostics",
            )
        else:
            summary = summary_by_level[label]
            summary_counts = {
                "expected_rk4_stage_evaluations": report["expected_stage_evaluations"],
                "observed_rk4_stage_evaluations": report["stage_evaluations"],
                "current_reference_saturated_stages": report["current_reference_saturated_stages"],
                "voltage_saturated_stages": report["voltage_saturated_stages"],
                "any_limiter_active_stages": report["any_limiter_active_stages"],
            }
            for field, expected_value in summary_counts.items():
                if not float(summary[field]).is_integer() or int(float(summary[field])) != expected_value:
                    raise EnergyClosureError(f"summary {field} disagrees with manifest at {label}")
            if summary["stage_count_matches_expected"] != str(report["stage_count_matches_expected"]):
                raise EnergyClosureError(f"summary stage-count flag disagrees with manifest at {label}")
            if summary["smooth_unsaturated"] != str(report["smooth_unsaturated"]):
                raise EnergyClosureError(f"summary smooth-unsaturated flag disagrees with manifest at {label}")
        stage_cursor += count
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
    fine_block_start = sum(contract["base_intervals"] * (2 ** index) + 1
                           for index in range(len(LEVELS) - 1))
    fine_block = timeseries_rows[fine_block_start:]
    fine_times = np.asarray([float(row["time_s"]) for row in fine_block], dtype=float)
    fine_net = np.asarray([float(row["net_power_W"]) for row in fine_block], dtype=float)
    expected_fixed = _fixed_trajectory_quadrature_diagnostics(
        fine_times, fine_net,
        [float(summary_by_level[level]["net_power_work_J"]) for level in LEVELS],
        [float(summary_by_level[level]["delta_stored_energy_J"]) for level in LEVELS],
    )
    for label, expected_row in zip(LEVELS, expected_fixed):
        row = summary_by_level[label]
        for field, expected_value in expected_row.items():
            if not math.isclose(float(row[field]), expected_value, rel_tol=1e-9, abs_tol=1e-12):
                raise EnergyClosureError(
                    f"fixed-trajectory diagnostic {field} is inconsistent at {label}"
                )
    reference_rows = parsed["reference_timeseries_csv"]
    reference_report = contract["reference_report"]
    reference_intervals = 16 * contract["base_intervals"]
    reference_step = contract["duration"] / reference_intervals
    if len(reference_rows) != reference_intervals + 1:
        raise EnergyClosureError("h/16 reference timeseries row count mismatch")
    for sample_index, row in enumerate(reference_rows):
        expected_time = sample_index * reference_step
        if row["case_id"] != manifest["case_id"] or row["step_level"] != REFERENCE_LEVEL:
            raise EnergyClosureError("h/16 reference timeseries identity/order mismatch")
        if not math.isclose(float(row["step_s"]), reference_step, rel_tol=1e-9, abs_tol=1e-12):
            raise EnergyClosureError("h/16 reference timeseries step mismatch")
        if not math.isclose(float(row["time_s"]), expected_time, rel_tol=1e-9, abs_tol=1e-12):
            raise EnergyClosureError("h/16 reference timeseries time grid mismatch")
        current = float(row["current_A"])
        voltage = float(row["terminal_voltage_V"])
        if not math.isclose(float(row["terminal_input_power_W"]), voltage * current,
                            rel_tol=1e-9, abs_tol=1e-12):
            raise EnergyClosureError("h/16 reference terminal input power is inconsistent")
        expected_net = (
            float(row["terminal_input_power_W"]) - float(row["copper_loss_W"])
            - float(row["structural_damping_loss_W"]) - float(row["axis_friction_loss_W"])
            + float(row["external_generalized_power_W"])
            + float(row["electromechanical_mismatch_power_W"])
        )
        if not math.isclose(float(row["net_power_W"]), expected_net, rel_tol=1e-9, abs_tol=1e-12):
            raise EnergyClosureError("h/16 reference net power ledger is inconsistent")
        if (row["current_reference_saturated"] == "True") != (
            float(row["limited_current_reference_A"]) != float(row["requested_current_command_A"])
        ):
            raise EnergyClosureError("h/16 reference current limiter flag is inconsistent")
    expected_reference_diagnostics = _reference_trajectory_diagnostics(
        reference_rows, timeseries_rows, summary_by_level,
        float(manifest["energy_normalization_scale_J"]),
        float(manifest["energy_normalization_floor_J"]),
    )
    _assert_json_metrics_close(
        manifest.get("reference_trajectory_diagnostics"),
        expected_reference_diagnostics, "reference_trajectory_diagnostics",
    )
    adjacent_smooth_flags = {
        report["level"]: report["smooth_unsaturated"]
        for report in manifest["limiter_stage_reports"]
    }
    adjacent_smooth_flags[REFERENCE_LEVEL] = contract["reference_report"]["smooth_unsaturated"]
    expected_adjacent_diagnostics = _adjacent_refinement_diagnostics(
        timeseries_rows, reference_rows, adjacent_smooth_flags,
        contract["state_comparison_scales"],
    )
    _assert_json_metrics_close(
        manifest.get("adjacent_refinement_diagnostics"),
        expected_adjacent_diagnostics, "adjacent_refinement_diagnostics",
    )

    stage_rows = parsed["stage_power_csv"]
    stage_cursor = 0
    stage_abscissae = (0.0, 0.5, 0.5, 1.0)
    stage_levels = list(LEVELS) + [REFERENCE_LEVEL]
    for index, label in enumerate(stage_levels):
        intervals = (16 * contract["base_intervals"] if label == REFERENCE_LEVEL
                     else contract["base_intervals"] * (2 ** index))
        step = contract["duration"] / intervals
        count = intervals * 4
        block = stage_rows[stage_cursor:stage_cursor + count]
        if len(block) != count:
            raise EnergyClosureError(f"RK4 stage trace row count mismatch at {label}")
        for row_index, row in enumerate(block):
            expected_interval, expected_stage = divmod(row_index, 4)
            expected_time = (expected_interval + stage_abscissae[expected_stage]) * step
            if row["case_id"] != manifest["case_id"] or row["step_level"] != label:
                raise EnergyClosureError(f"RK4 stage trace identity/order mismatch at {label}")
            interval_value = float(row["interval_index"])
            stage_value = float(row["stage_index"])
            if (not interval_value.is_integer() or not stage_value.is_integer()
                    or int(interval_value) != expected_interval or int(stage_value) != expected_stage):
                raise EnergyClosureError(f"RK4 stage trace index mismatch at {label}")
            if not math.isclose(float(row["step_s"]), step, rel_tol=1e-9, abs_tol=1e-12):
                raise EnergyClosureError(f"RK4 stage trace step mismatch at {label}")
            if not math.isclose(float(row["stage_time_s"]), expected_time, rel_tol=1e-9, abs_tol=1e-12):
                raise EnergyClosureError(f"RK4 stage trace time mismatch at {label}")
            current = float(row["current_A"])
            terminal_voltage = float(row["terminal_voltage_V"])
            if not math.isclose(
                float(row["terminal_input_power_W"]), terminal_voltage * current,
                rel_tol=1e-9, abs_tol=1e-12,
            ):
                raise EnergyClosureError(f"RK4 stage terminal input power is inconsistent at {label}")
            expected_net = (
                float(row["terminal_input_power_W"]) - float(row["copper_loss_W"])
                - float(row["structural_damping_loss_W"]) - float(row["axis_friction_loss_W"])
                + float(row["external_generalized_power_W"])
                + float(row["electromechanical_mismatch_power_W"])
            )
            if not math.isclose(float(row["net_power_W"]), expected_net, rel_tol=1e-9, abs_tol=1e-12):
                raise EnergyClosureError(f"RK4 stage net power ledger is inconsistent at {label}")
            requested = float(row["requested_current_command_A"])
            limited = float(row["limited_current_reference_A"])
            if (row["current_reference_saturated"] == "True") != (limited != requested):
                raise EnergyClosureError(f"RK4 stage current-reference limiter flag is inconsistent at {label}")
        report = (contract["reference_report"] if label == REFERENCE_LEVEL
                  else manifest["limiter_stage_reports"][index])
        reference_count = sum(row["current_reference_saturated"] == "True" for row in block)
        voltage_count = sum(row["voltage_saturated"] == "True" for row in block)
        any_count = sum(
            row["current_reference_saturated"] == "True" or row["voltage_saturated"] == "True"
            for row in block
        )
        if (
            reference_count != report["current_reference_saturated_stages"]
            or voltage_count != report["voltage_saturated_stages"]
            or any_count != report["any_limiter_active_stages"]
        ):
            raise EnergyClosureError(f"RK4 stage limiter trace disagrees with manifest at {label}")
        if label == REFERENCE_LEVEL:
            reference_stored = float(reference_rows[-1]["stored_energy_J"]) - float(reference_rows[0]["stored_energy_J"])
            reference_net_work = float(path_support.composite_simpson_13(
                np.asarray([float(row["time_s"]) for row in reference_rows], dtype=float),
                np.asarray([float(row["net_power_W"]) for row in reference_rows], dtype=float),
            ))
            expected_stage_metrics = _rk4_stage_power_diagnostics(
                block, reference_stored, reference_net_work
            )
            _assert_json_metrics_close(
                reference_report.get("stage_power_diagnostics"), expected_stage_metrics,
                "reference_trajectory_report.stage_power_diagnostics",
            )
        else:
            summary = summary_by_level[label]
            stage_metrics = _rk4_stage_power_diagnostics(
                block, float(summary["delta_stored_energy_J"]),
                float(summary["net_power_work_J"]),
            )
            for field, expected_value in stage_metrics.items():
                if not math.isclose(float(summary[field]), expected_value, rel_tol=1e-9, abs_tol=1e-12):
                    raise EnergyClosureError(f"RK4 stage diagnostic {field} is inconsistent at {label}")
        stage_cursor += count
    if stage_cursor != len(stage_rows):
        raise EnergyClosureError("RK4 stage trace contains unexpected extra rows")
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
    all_stage_rows: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []
    saturation_by_level = []
    power_samples_by_level: list[tuple[np.ndarray, dict[str, np.ndarray]]] = []
    started = datetime.now(timezone.utc).isoformat()
    for level, label in enumerate(LEVELS):
        intervals = v["intervals"] * (2 ** level)
        step = v["duration"] / intervals
        observations = {"count": 0, "reference": 0, "voltage": 0, "any": 0}

        stage_row_start = len(all_stage_rows)
        def tracked(_time: float, state: Any) -> float:
            stage_number = observations["count"]
            stage_index = stage_number % 4
            interval_index = stage_number // 4
            power = _power_sample(model, model.pack(state), command, external, v["case_id"])
            all_stage_rows.append({
                "case_id": v["case_id"], "step_level": label,
                "interval_index": interval_index, "stage_index": stage_index,
                "stage_time_s": float(_time), "step_s": step,
                "requested_current_command_A": power["requested_command"],
                "limited_current_reference_A": power["limited_reference"],
                "current_A": float(state.current_A),
                "raw_voltage_V": power["raw_voltage"],
                "terminal_voltage_V": power["terminal_voltage"],
                "terminal_input_power_W": power["terminal_input"],
                "copper_loss_W": power["copper"],
                "structural_damping_loss_W": power["structural"],
                "axis_friction_loss_W": power["friction"],
                "external_generalized_power_W": power["external"],
                "electromechanical_mismatch_power_W": power["mismatch"],
                "net_power_W": power["net"],
                "current_reference_saturated": bool(power["current_reference_saturated"]),
                "voltage_saturated": bool(power["voltage_saturated"]),
            })
            ref = bool(power["current_reference_saturated"])
            volt = bool(power["voltage_saturated"])
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
        power_samples_by_level.append((np.asarray(times, dtype=float).copy(), arrays))
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
            all_rows.append(_timeseries_row(
                v["case_id"], label, step, float(time_s), vector, sample, command
            ))
        stage_diagnostics = _rk4_stage_power_diagnostics(
            all_stage_rows[stage_row_start:], delta, net_work
        )
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
            **stage_diagnostics,
            "current_reference_saturated_stages": observations["reference"],
            "voltage_saturated_stages": observations["voltage"],
            "any_limiter_active_stages": observations["any"],
            "expected_rk4_stage_evaluations": expected_stages,
            "observed_rk4_stage_evaluations": stage_count,
            "stage_count_matches_expected": stage_match,
            "smooth_unsaturated": smooth,
            "residual_order_gate_status": "PENDING",
            "residual_order_noise_floor_J": v["energy_residual_noise_floor_J"],
            "empirical_residual_order_from_previous": None,
            "energy_closure_threshold": v["threshold"],
            "status": "PENDING",
        })
    reference_intervals = v["intervals"] * 16
    reference_step = v["duration"] / reference_intervals
    reference_observations = {"count": 0, "reference": 0, "voltage": 0, "any": 0}
    reference_stage_start = len(all_stage_rows)

    def reference_tracked(_time: float, state: Any) -> float:
        stage_number = reference_observations["count"]
        stage_power = _power_sample(model, model.pack(state), command, external, v["case_id"])
        stage_index = stage_number % 4
        interval_index = stage_number // 4
        all_stage_rows.append({
            "case_id": v["case_id"], "step_level": REFERENCE_LEVEL,
            "interval_index": interval_index, "stage_index": stage_index,
            "stage_time_s": float(_time), "step_s": reference_step,
            "requested_current_command_A": stage_power["requested_command"],
            "limited_current_reference_A": stage_power["limited_reference"],
            "current_A": float(state.current_A),
            "raw_voltage_V": stage_power["raw_voltage"],
            "terminal_voltage_V": stage_power["terminal_voltage"],
            "terminal_input_power_W": stage_power["terminal_input"],
            "copper_loss_W": stage_power["copper"],
            "structural_damping_loss_W": stage_power["structural"],
            "axis_friction_loss_W": stage_power["friction"],
            "external_generalized_power_W": stage_power["external"],
            "electromechanical_mismatch_power_W": stage_power["mismatch"],
            "net_power_W": stage_power["net"],
            "current_reference_saturated": bool(stage_power["current_reference_saturated"]),
            "voltage_saturated": bool(stage_power["voltage_saturated"]),
        })
        ref_active = bool(stage_power["current_reference_saturated"])
        voltage_active = bool(stage_power["voltage_saturated"])
        reference_observations["count"] += 1
        reference_observations["reference"] += int(ref_active)
        reference_observations["voltage"] += int(voltage_active)
        reference_observations["any"] += int(ref_active or voltage_active)
        return command

    def reference_load(_time: float, _state: Any) -> np.ndarray:
        return external.copy()

    reference_times, reference_states = model.simulate(
        initial, v["duration"], reference_step, reference_tracked, reference_load
    )
    reference_samples = [
        _power_sample(model, reference_states[index], command, external, v["case_id"])
        for index in range(len(reference_times))
    ]
    reference_rows = [
        _timeseries_row(v["case_id"], REFERENCE_LEVEL, reference_step, time_s,
                        reference_states[index], reference_samples[index], command)
        for index, time_s in enumerate(reference_times)
    ]
    reference_expected_stages = 4 * reference_intervals
    reference_stage_count = reference_observations["count"]
    reference_stage_match = reference_stage_count == reference_expected_stages
    reference_smooth = reference_stage_match and reference_observations["any"] == 0
    reference_net = np.asarray([sample["net"] for sample in reference_samples], dtype=float)
    reference_delta = float(reference_samples[-1]["stored"] - reference_samples[0]["stored"])
    reference_work = float(path_support.composite_simpson_13(reference_times, reference_net))
    reference_stage_power_diagnostics = _rk4_stage_power_diagnostics(
        all_stage_rows[reference_stage_start:], reference_delta, reference_work
    )
    if not reference_stage_match:
        raise EnergyClosureError("h/16 reference RK4 stage callback count does not match expected")
    reference_trajectory_report = {
        "level": REFERENCE_LEVEL, "intervals": int(reference_intervals),
        "samples": len(reference_times), "step_s": reference_step,
        "stage_evaluations": reference_stage_count,
        "expected_stage_evaluations": reference_expected_stages,
        "current_reference_saturated_stages": reference_observations["reference"],
        "voltage_saturated_stages": reference_observations["voltage"],
        "any_limiter_active_stages": reference_observations["any"],
        "stage_count_matches_expected": reference_stage_match,
        "smooth_unsaturated": reference_smooth,
        "stage_power_diagnostics": reference_stage_power_diagnostics,
    }
    summary_by_level = {row["step_level"]: row for row in summaries}
    reference_trajectory_diagnostics = _reference_trajectory_diagnostics(
        reference_rows, all_rows, summary_by_level, v["scale"], v["floor"]
    )
    adjacent_smooth_flags = {
        item["level"]: bool(item["smooth_unsaturated"]) for item in saturation_by_level
    }
    adjacent_smooth_flags[REFERENCE_LEVEL] = bool(reference_smooth)
    adjacent_refinement_diagnostics = _adjacent_refinement_diagnostics(
        all_rows, reference_rows, adjacent_smooth_flags, v["state_comparison_scales"]
    )

    fine_times, fine_arrays = power_samples_by_level[-1]
    fixed_trajectory_diagnostics = _fixed_trajectory_quadrature_diagnostics(
        fine_times, fine_arrays["net"],
        [float(row["net_power_work_J"]) for row in summaries],
        [float(row["delta_stored_energy_J"]) for row in summaries],
    )
    for summary, diagnostic in zip(summaries, fixed_trajectory_diagnostics):
        summary.update(diagnostic)
    residual_order_diagnostic = _residual_order_diagnostics(
        summaries, reference_trajectory_diagnostics,
        [*[bool(item["smooth_unsaturated"]) for item in saturation_by_level], bool(reference_smooth)],
        v["energy_residual_noise_floor_J"],
    )
    for index, summary in enumerate(summaries):
        summary["residual_order_gate_status"] = residual_order_diagnostic["gate_status"]
        summary["empirical_residual_order_from_previous"] = (
            None if index == 0
            else residual_order_diagnostic["pairwise_empirical_orders"][index - 1]
        )
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
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "config_schema_version": CONFIG_SCHEMA_VERSION,
        "case_id": v["case_id"], "status": status,
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
        "energy_residual_noise_floor_J": v["energy_residual_noise_floor_J"],
        "energy_residual_noise_floor_method": v["energy_residual_noise_floor_method"],
        "energy_residual_noise_floor_source": v["energy_residual_noise_floor_source"],
        "energy_residual_noise_floor_source_ids": v["energy_residual_noise_floor_source_ids"],
        "energy_residual_noise_budget": v["energy_residual_noise_budget"],
        "energy_residual_noise_budget_report": v["energy_residual_noise_budget_report"],
        "residual_order_diagnostic": residual_order_diagnostic,
        "all_refinements_smooth_unsaturated": all_smooth,
        "limiter_stage_reports": saturation_by_level,
        "reference_trajectory_report": reference_trajectory_report,
        "reference_trajectory_diagnostics": reference_trajectory_diagnostics,
        "adjacent_refinement_diagnostics": adjacent_refinement_diagnostics,
        "state_comparison_scales": v["state_comparison_scales"],
        "state_comparison_scale_source": v["state_comparison_scale_source"],
        "state_comparison_scale_source_ids": v["state_comparison_scale_source_ids"],
        "state_vector_order": STATE_VECTOR_FIELDS,
        "state_comparison_units": STATE_COMPARISON_UNITS,
        "notes": [
            "Power accounting is implemented independently of PATH-01 energy ledger/metrics.",
            "The same solver state vector field and stored-energy function are reused; this is not an independent physical model.",
            "Terminal power uses the actual voltage after PI voltage saturation.",
            "Current reference limiting is not a hard state-current clamp or hardware overcurrent protection.",
            "RK4-stage power uses the classical 1:2:2:1 stage weights and is a solver-coupled sampling diagnostic, not an independent quadrature oracle or error bound.",
            "A VERIFIED archive proves file integrity/schema only, not simulation correctness or physical validity.",
            "Residual empirical order is reported only when all five levels are smooth, above the predeclared sourced noise floor, same-sign and strictly decreasing in magnitude; it is diagnostic, not an error bound.",
            "The residual noise floor must be at least the automatically derived binary64 post-processing bound; analyst-supplied stored-energy, net-power, RK4-state-propagation and time-grid bounds are recorded separately.",
            "The derived binary64 bound does not cover parameter/model uncertainty or RK4 truncation error, and does not prove the supplied envelope and state-propagation bounds.",
            "The h/16 reference path uses the same RK4 solver and constant command/load; it is a finer numerical reference, not an exact or independent physical solution.",
            "The h/16 reference comparison uses nested common time nodes to compare state, net power, stored-energy change and same-grid power work; it is diagnostic and excluded from the four-level primary PASS threshold.",
            "Adjacent-level trajectory differences are reported on each pair shared coarse grid as raw per-state and power differences; they do not infer convergence order, establish an error bound or alter PASS.",
            "The h/16 reference is excluded from the primary four-level PASS threshold and remains a diagnostic comparison only.",
            "State-comparison characteristic scales are sourced and predeclared per component; normalized component differences are not tolerances, state bounds, or aggregate scores.",
            "Bundle files are staged first and then published by per-file atomic replacement; the five-file bundle is not a single filesystem transaction.",
            "No hardware, SIL, HIL or machine measurement validation is implied.",
        ],
    }
    artifacts = _atomic_bundle(output_dir.resolve(), all_rows, all_stage_rows, reference_rows, summaries, manifest)
    return {"case_id": v["case_id"], "status": status,
            "stage_power_csv": str(output_dir.resolve() / STAGE_TIMESERIES_NAME),
            "summary_csv": str(output_dir.resolve() / SUMMARY_NAME),
            "timeseries_csv": str(output_dir.resolve() / TIMESERIES_NAME),
            "reference_timeseries_csv": str(output_dir.resolve() / REFERENCE_TIMESERIES_NAME),
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
