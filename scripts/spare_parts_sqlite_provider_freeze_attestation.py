#!/usr/bin/env python3
"""Verify frozen-Provider attestations and consume their evidence IDs once.

The verifier is offline. The SQLite ledger is a single-host durable reference
implementation only; multi-host production deployments need an equivalent
linearizable shared ledger (for example, an isolated etcd transaction).
"""
from __future__ import annotations

import hashlib
import os
import re
import sqlite3
import stat
import uuid
from pathlib import Path
from typing import Any

from scripts.spare_parts_sqlite_provider_fencing_reconciliation import (
    ProviderFencingReconciliationError,
    _canonical,
    validate_provider_fencing_reconciliation,
)
from scripts.spare_parts_sqlite_provider_fencing_signed_evidence import (
    verify_signed_provider_payload,
)


FREEZE_SIGNATURE_DOMAIN = b"cnc-knowledge-provider-freeze-attestation-v1\x00"
FREEZE_ENVELOPE_FORMAT = "ch17-provider-freeze-attestation-envelope-v1"
FREEZE_CLAIMS_FORMAT = "ch17-provider-freeze-attestation-v1"
COORDINATOR_SNAPSHOT_FORMAT = "ch17-coordinator-leader-snapshot-v1"


class ProviderFreezeReplayError(ProviderFencingReconciliationError):
    """Raised when a previously consumed Provider freeze proof is replayed."""


class ProviderFreezeReplayLedgerError(ProviderFencingReconciliationError):
    """Raised when the replay ledger cannot durably record evidence consumption."""


class SQLiteProviderFreezeEvidenceReplayLedger:
    """Single-host SQLite reference ledger with an atomic unique consume."""

    def __init__(self, database_path: str | os.PathLike[str]) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.database_path.is_symlink():
            raise ProviderFreezeReplayLedgerError("replay ledger path must not be a symlink")

    def consume_once(self, record: dict[str, Any]) -> None:
        required = {
            "provider_id", "evidence_id", "challenge_nonce_sha256",
            "claim_sha256", "freeze_id", "freeze_generation", "leader_id",
            "leader_epoch", "lease_id", "consumed_at_unix",
        }
        if not isinstance(record, dict) or set(record) != required:
            raise ProviderFreezeReplayLedgerError("replay ledger record schema mismatch")
        path = self.database_path
        try:
            try:
                descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600)
            except FileExistsError:
                descriptor = None
            if descriptor is not None:
                os.close(descriptor)
            info = path.lstat()
            if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) & 0o077:
                raise ProviderFreezeReplayLedgerError(
                    "existing replay ledger must be a regular file with mode 0600"
                )
            if hasattr(os, "getuid") and info.st_uid != os.getuid():
                raise ProviderFreezeReplayLedgerError("replay ledger owner mismatch")
            connection = sqlite3.connect(path, timeout=10.0, isolation_level=None)
            try:
                connection.execute("PRAGMA journal_mode=DELETE")
                connection.execute("PRAGMA synchronous=FULL")
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS consumed_provider_freeze_evidence (
                        provider_id TEXT NOT NULL,
                        evidence_id TEXT NOT NULL,
                        challenge_nonce_sha256 TEXT NOT NULL,
                        claim_sha256 TEXT NOT NULL,
                        freeze_id TEXT NOT NULL,
                        freeze_generation INTEGER NOT NULL,
                        leader_id TEXT NOT NULL,
                        leader_epoch INTEGER NOT NULL,
                        lease_id INTEGER NOT NULL,
                        consumed_at_unix REAL NOT NULL,
                        UNIQUE(provider_id, evidence_id),
                        UNIQUE(provider_id, challenge_nonce_sha256),
                        UNIQUE(provider_id, freeze_id, freeze_generation)
                    )
                    """
                )
                os.chmod(path, 0o600)
                connection.execute("BEGIN IMMEDIATE")
                connection.execute(
                    """
                    INSERT INTO consumed_provider_freeze_evidence (
                        provider_id, evidence_id, challenge_nonce_sha256,
                        claim_sha256, freeze_id, freeze_generation, leader_id,
                        leader_epoch, lease_id, consumed_at_unix
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record["provider_id"], record["evidence_id"],
                        record["challenge_nonce_sha256"], record["claim_sha256"],
                        record["freeze_id"], record["freeze_generation"],
                        record["leader_id"], record["leader_epoch"],
                        record["lease_id"], record["consumed_at_unix"],
                    ),
                )
                connection.commit()
            except sqlite3.IntegrityError as exc:
                connection.rollback()
                raise ProviderFreezeReplayError(
                    "Provider freeze evidence ID, challenge nonce or freeze generation was already consumed"
                ) from exc
            except Exception:
                connection.rollback()
                raise
            finally:
                connection.close()
        except ProviderFencingReconciliationError:
            raise
        except (OSError, sqlite3.Error) as exc:
            raise ProviderFreezeReplayLedgerError(
                "Provider freeze replay ledger could not durably consume evidence"
            ) from exc


def _non_empty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProviderFencingReconciliationError(f"{field} must be a non-empty string")
    return value


def _finite_number(value: Any, field: str) -> float:
    import math

    if (
        not isinstance(value, (int, float)) or isinstance(value, bool)
        or not math.isfinite(float(value))
    ):
        raise ProviderFencingReconciliationError(f"{field} must be a finite number")
    return float(value)


def _positive_integer(value: Any, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ProviderFencingReconciliationError(f"{field} must be a positive integer")
    return value


def validate_provider_freeze_attestation(
    candidate: dict[str, Any],
    envelope: dict[str, Any],
    trust_store: dict[str, Any],
    coordinator_snapshot: dict[str, Any],
    replay_ledger: SQLiteProviderFreezeEvidenceReplayLedger,
    *,
    expected_challenge_nonce: str,
    now_unix: float,
    maximum_evidence_age_seconds: float = 300.0,
    maximum_coordinator_snapshot_age_seconds: float = 5.0,
) -> dict[str, Any]:
    """Verify and atomically consume a fresh freeze attestation.

    The signed claim binds Provider generation/floors to the observed current
    Coordinator Leader epoch, Lease ID, a caller-issued one-time nonce, and a
    Provider freeze generation. The ledger rejects a second use of any of
    evidence ID, nonce, or Provider freeze generation.
    """
    claims, signer_key_id, trust_store_digest = verify_signed_provider_payload(
        envelope,
        trust_store,
        expected_envelope_format=FREEZE_ENVELOPE_FORMAT,
        signature_domain=FREEZE_SIGNATURE_DOMAIN,
    )
    expected_claim_fields = {
        "format", "provider_id", "freeze_id", "freeze_generation", "frozen",
        "freeze_mode", "evidence_id", "challenge_nonce", "freeze_started_at_unix",
        "freeze_expires_at_unix", "issued_at_unix", "expires_at_unix",
        "coordinator", "evidence",
    }
    if not isinstance(claims, dict) or set(claims) != expected_claim_fields:
        raise ProviderFencingReconciliationError("Provider freeze claims schema mismatch")
    if claims.get("format") != FREEZE_CLAIMS_FORMAT:
        raise ProviderFencingReconciliationError("unsupported Provider freeze claims format")
    if claims.get("frozen") is not True or claims.get("freeze_mode") != "provider-native-write-gate":
        raise ProviderFencingReconciliationError("Provider has not attested its native write gate as frozen")

    provider_id = _non_empty_string(claims.get("provider_id"), "provider_id")
    freeze_id = _non_empty_string(claims.get("freeze_id"), "freeze_id")
    evidence_id = _non_empty_string(claims.get("evidence_id"), "evidence_id")
    try:
        if str(uuid.UUID(evidence_id)) != evidence_id:
            raise ValueError("non-canonical UUID")
    except (ValueError, AttributeError) as exc:
        raise ProviderFencingReconciliationError("evidence_id must be a canonical UUID") from exc

    nonce = claims.get("challenge_nonce")
    if (
        not isinstance(nonce, str)
        or re.fullmatch(r"[0-9a-f]{64}", nonce) is None
        or not isinstance(expected_challenge_nonce, str)
        or re.fullmatch(r"[0-9a-f]{64}", expected_challenge_nonce) is None
        or not __import__("hmac").compare_digest(nonce, expected_challenge_nonce)
    ):
        raise ProviderFencingReconciliationError("Provider freeze challenge nonce mismatch")
    freeze_generation = _positive_integer(claims.get("freeze_generation"), "freeze_generation")

    now = _finite_number(now_unix, "now_unix")
    started = _finite_number(claims.get("freeze_started_at_unix"), "freeze_started_at_unix")
    freeze_expires = _finite_number(claims.get("freeze_expires_at_unix"), "freeze_expires_at_unix")
    issued = _finite_number(claims.get("issued_at_unix"), "issued_at_unix")
    expires = _finite_number(claims.get("expires_at_unix"), "expires_at_unix")
    if not (started <= issued <= now < expires <= freeze_expires):
        raise ProviderFencingReconciliationError("Provider freeze attestation time window is invalid")

    coordinator_fields = {
        "leader_id", "leader_epoch", "lease_id", "lease_expires_at_unix"
    }
    coordinator = claims.get("coordinator")
    if not isinstance(coordinator, dict) or set(coordinator) != coordinator_fields:
        raise ProviderFencingReconciliationError("signed Coordinator binding schema mismatch")
    leader_id = _non_empty_string(coordinator.get("leader_id"), "leader_id")
    leader_epoch = _positive_integer(coordinator.get("leader_epoch"), "leader_epoch")
    lease_id = _positive_integer(coordinator.get("lease_id"), "lease_id")
    lease_expires = _finite_number(
        coordinator.get("lease_expires_at_unix"), "lease_expires_at_unix"
    )
    if lease_expires < expires:
        raise ProviderFencingReconciliationError("Coordinator Lease expires before freeze attestation")

    snapshot_fields = {
        "format", "observed_at_unix", "leader_id", "leader_epoch",
        "lease_id", "lease_expires_at_unix", "scopes",
    }
    if not isinstance(coordinator_snapshot, dict) or set(coordinator_snapshot) != snapshot_fields:
        raise ProviderFencingReconciliationError("current Coordinator snapshot schema mismatch")
    if coordinator_snapshot.get("format") != COORDINATOR_SNAPSHOT_FORMAT:
        raise ProviderFencingReconciliationError("unsupported current Coordinator snapshot format")
    snapshot_time = _finite_number(
        coordinator_snapshot.get("observed_at_unix"), "Coordinator snapshot time"
    )
    snapshot_age = now - snapshot_time
    max_snapshot_age = _finite_number(
        maximum_coordinator_snapshot_age_seconds, "maximum Coordinator snapshot age"
    )
    if max_snapshot_age <= 0 or snapshot_age < 0 or snapshot_age > max_snapshot_age:
        raise ProviderFencingReconciliationError("current Coordinator snapshot is stale or from the future")
    for field, expected in (
        ("leader_id", leader_id), ("leader_epoch", leader_epoch),
        ("lease_id", lease_id), ("lease_expires_at_unix", lease_expires),
    ):
        if coordinator_snapshot.get(field) != expected:
            raise ProviderFencingReconciliationError(
                f"Provider freeze attestation Coordinator {field} mismatch"
            )
    if _finite_number(coordinator_snapshot.get("lease_expires_at_unix"), "snapshot Lease expiry") <= now:
        raise ProviderFencingReconciliationError("current Coordinator Lease is expired")

    evidence = claims.get("evidence")
    if not isinstance(evidence, dict) or evidence.get("provider_id") != provider_id:
        raise ProviderFencingReconciliationError("freeze claim Provider identity does not match evidence")
    evidence_time = _finite_number(evidence.get("observed_at_unix"), "Provider evidence time")
    if not (started <= evidence_time <= issued <= now < freeze_expires):
        raise ProviderFencingReconciliationError("Provider evidence was not sampled within the freeze window")

    candidate_state = candidate.get("state_template") if isinstance(candidate, dict) else None
    candidate_coord = candidate_state.get("coordinator") if isinstance(candidate_state, dict) else None
    candidate_scopes = candidate_coord.get("scopes") if isinstance(candidate_coord, dict) else None
    snapshot_scopes = coordinator_snapshot.get("scopes")
    evidence_scopes = evidence.get("scopes")
    if not isinstance(candidate_scopes, dict) or not isinstance(snapshot_scopes, dict):
        raise ProviderFencingReconciliationError("candidate or Coordinator scope map is malformed")
    if set(snapshot_scopes) != set(candidate_scopes):
        raise ProviderFencingReconciliationError("Coordinator snapshot must cover exactly every candidate scope")
    if not isinstance(evidence_scopes, dict) or set(evidence_scopes) != set(candidate_scopes):
        raise ProviderFencingReconciliationError("frozen Provider evidence must cover exactly every candidate scope")
    for scope_name in candidate_scopes:
        observed = evidence_scopes[scope_name]
        authority = snapshot_scopes[scope_name]
        if not isinstance(authority, dict) or set(authority) != {
            "provider_generation", "high_water_token", "latest_operation_sequence"
        }:
            raise ProviderFencingReconciliationError(
                f"Coordinator scope snapshot schema mismatch for {scope_name}"
            )
        if observed != authority:
            raise ProviderFencingReconciliationError(
                f"Provider frozen floor differs from Coordinator authority for scope {scope_name}"
            )

    reconciliation = validate_provider_fencing_reconciliation(
        candidate, evidence, now_unix=now,
        maximum_age_seconds=maximum_evidence_age_seconds,
    )
    claims_digest = hashlib.sha256(_canonical(claims)).hexdigest()
    replay_ledger.consume_once({
        "provider_id": provider_id,
        "evidence_id": evidence_id,
        "challenge_nonce_sha256": hashlib.sha256(nonce.encode("ascii")).hexdigest(),
        "claim_sha256": claims_digest,
        "freeze_id": freeze_id,
        "freeze_generation": freeze_generation,
        "leader_id": leader_id,
        "leader_epoch": leader_epoch,
        "lease_id": lease_id,
        "consumed_at_unix": now,
    })

    return {
        "format": "ch17-provider-freeze-attestation-result-v1",
        "provider_id": provider_id,
        "freeze_id": freeze_id,
        "freeze_generation": freeze_generation,
        "evidence_id": evidence_id,
        "evidence_sha256": reconciliation["evidence_sha256"],
        "claim_sha256": claims_digest,
        "signer_key_id": signer_key_id,
        "trust_store_sha256": trust_store_digest,
        "coordinator_leader_id": leader_id,
        "coordinator_leader_epoch": leader_epoch,
        "coordinator_lease_id": lease_id,
        "coordinator_lease_expires_at_unix": lease_expires,
        "coordinator_snapshot_age_seconds": snapshot_age,
        "provider_fencing_reconciliation": "PASS",
        "freeze_attestation_signature_verified": True,
        "freeze_evidence_replay_consumed": True,
        "provider_write_freeze_enforced": False,
        "application_activation_authorized": False,
        "provider_operations_authorized": False,
        "limitations": [
            "The Provider-native write-gate assertion is signed but this offline verifier does not inspect or control the actual Provider write path.",
            "The Coordinator snapshot is caller-supplied; production integration must obtain it from a fresh authenticated linearizable authority read.",
            "The SQLite replay ledger is single-host only and is not a multi-host consensus or etcd authority implementation.",
            "Freeze remains unproven after this attestation expires or if any Provider mutation path bypasses the asserted native gate.",
        ],
    }
