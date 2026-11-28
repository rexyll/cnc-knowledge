#!/usr/bin/env python3
"""Fail-closed validation of read-only Provider fencing reconciliation evidence.

This module does not contact Providers, import evidence, change fencing floors,
or enable application access. It only checks an operator-supplied snapshot
against an already validated SQLite candidate before any activation decision.
"""
from __future__ import annotations

import hashlib
import json
import math
from typing import Any


class ProviderFencingReconciliationError(RuntimeError):
    """Raised when Provider fencing evidence is incomplete or unsafe."""


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ProviderFencingReconciliationError(
            "Provider reconciliation evidence is not canonical JSON"
        ) from exc


def validate_provider_fencing_reconciliation(
    candidate: dict[str, Any],
    evidence: dict[str, Any],
    *,
    now_unix: float,
    maximum_age_seconds: float = 300.0,
) -> dict[str, Any]:
    """Validate complete Provider read-only floors without mutating candidate.

    Every candidate scope must have one evidence record. Provider generation
    must match exactly, and observed Provider fencing/sequence floors must not
    exceed the candidate floors. A higher Provider floor requires rebuilding
    the candidate from reconciled floors; it must never be silently lowered.
    """
    if not isinstance(candidate, dict) or candidate.get("format") != (
        "ch17-sqlite-unified-candidate-v2"
    ):
        raise ProviderFencingReconciliationError("unsupported or missing candidate v2")
    if not isinstance(evidence, dict) or set(evidence) != {
        "format", "provider_id", "observed_at_unix", "scopes"
    }:
        raise ProviderFencingReconciliationError("Provider evidence schema mismatch")
    if evidence.get("format") != "ch17-provider-fencing-readonly-evidence-v1":
        raise ProviderFencingReconciliationError("unsupported Provider evidence format")
    provider_id = evidence.get("provider_id")
    if not isinstance(provider_id, str) or not provider_id.strip():
        raise ProviderFencingReconciliationError("Provider identity is required")
    observed_at = evidence.get("observed_at_unix")
    if (
        not isinstance(observed_at, (int, float)) or isinstance(observed_at, bool)
        or not math.isfinite(float(observed_at))
    ):
        raise ProviderFencingReconciliationError("Provider observation time is invalid")
    if (
        not isinstance(now_unix, (int, float)) or isinstance(now_unix, bool)
        or not math.isfinite(float(now_unix))
        or not isinstance(maximum_age_seconds, (int, float))
        or isinstance(maximum_age_seconds, bool)
        or not math.isfinite(float(maximum_age_seconds))
        or maximum_age_seconds <= 0
    ):
        raise ProviderFencingReconciliationError("reconciliation time bounds are invalid")
    age = float(now_unix) - float(observed_at)
    if age < 0 or age > float(maximum_age_seconds):
        raise ProviderFencingReconciliationError("Provider evidence is stale or from the future")

    candidate_state = candidate.get("state_template")
    coordinator = candidate_state.get("coordinator") if isinstance(candidate_state, dict) else None
    candidate_scopes = coordinator.get("scopes") if isinstance(coordinator, dict) else None
    observed_scopes = evidence.get("scopes")
    if not isinstance(candidate_scopes, dict) or not isinstance(observed_scopes, dict):
        raise ProviderFencingReconciliationError("candidate or Provider scope map is malformed")
    if set(observed_scopes) != set(candidate_scopes):
        raise ProviderFencingReconciliationError(
            "Provider evidence must cover exactly every candidate scope"
        )

    verified = []
    for scope_name in sorted(candidate_scopes):
        expected = candidate_scopes[scope_name]
        observed = observed_scopes[scope_name]
        if not isinstance(expected, dict) or not isinstance(observed, dict) or set(observed) != {
            "provider_generation", "high_water_token", "latest_operation_sequence"
        }:
            raise ProviderFencingReconciliationError(
                f"Provider evidence schema mismatch for scope {scope_name}"
            )
        generation = expected.get("provider_generation")
        if observed.get("provider_generation") != generation:
            raise ProviderFencingReconciliationError(
                f"Provider generation mismatch for scope {scope_name}"
            )
        for field in ("high_water_token", "latest_operation_sequence"):
            expected_floor = expected.get(field)
            observed_floor = observed.get(field)
            if (
                not isinstance(expected_floor, int) or isinstance(expected_floor, bool)
                or expected_floor < 0
                or not isinstance(observed_floor, int) or isinstance(observed_floor, bool)
                or observed_floor < 0
            ):
                raise ProviderFencingReconciliationError(
                    f"invalid {field} for scope {scope_name}"
                )
            if observed_floor > expected_floor:
                raise ProviderFencingReconciliationError(
                    f"Provider {field} exceeds candidate floor for scope {scope_name}; rebuild candidate"
                )
        verified.append({
            "scope": scope_name,
            "provider_generation": generation,
            "provider_high_water_token": observed["high_water_token"],
            "candidate_high_water_token": expected["high_water_token"],
            "provider_operation_sequence": observed["latest_operation_sequence"],
            "candidate_operation_sequence": expected["latest_operation_sequence"],
        })

    evidence_digest = hashlib.sha256(_canonical(evidence)).hexdigest()
    return {
        "format": "ch17-provider-fencing-reconciliation-result-v1",
        "provider_id": provider_id,
        "candidate_digest_sha256": candidate.get("candidate_digest_sha256"),
        "evidence_sha256": evidence_digest,
        "observed_at_unix": float(observed_at),
        "age_seconds": age,
        "verified_scope_count": len(verified),
        "scopes": verified,
        "provider_fencing_reconciliation": "PASS",
        "application_activation_authorized": False,
        "provider_operations_authorized": False,
        "limitations": [
            "Evidence is operator-supplied and is not cryptographically authenticated by this validator.",
            "This result is not a production cutover approval or an application-access grant.",
            "Any Provider mutation after observation invalidates this point-in-time reconciliation.",
        ],
    }
