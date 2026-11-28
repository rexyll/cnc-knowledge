#!/usr/bin/env python3
"""Local SQLite reference for an external Provider Grant monotonic floor.

This module models a separate authority database. It is NOT an etcd adapter,
not a quorum-backed authority and not rollback-resistant storage. Keep this
database outside the Provider SQLite backup/restore domain.
"""
from __future__ import annotations

import base64
import hashlib
import math
import os
import re
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from scripts.spare_parts_provider_grant_receipt import (
    ProviderGrantReceiptError,
    ProviderReceiptTrustKey,
    canonical_receipt_json,
    parse_receipt_envelope,
    verify_provider_grant_receipt,
)

SCHEMA_VERSION = 3
MAX_SQLITE_INTEGER = (1 << 63) - 1
_DIGEST_RE = re.compile(r"[0-9a-f]{64}\Z")
_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")
_SCOPE_STATES = {
    "IDLE", "FENCE_PENDING", "FENCED", "ACTIVATE_PENDING",
    "ACTIVE", "RECOVERY_REQUIRED",
}
Action = Literal["FENCE", "ACTIVATE"]


class ProviderGrantFloorError(ValueError):
    """Base error for the local Provider Grant floor reference."""


class ProviderGrantFloorConflict(ProviderGrantFloorError):
    """A CAS, identity, operation or state-machine conflict was detected."""


class ProviderGrantFloorRevisionRegression(ProviderGrantFloorError):
    """A caller-supplied trusted revision floor is newer than this snapshot."""


@dataclass(frozen=True)
class ProviderGrantScopeKey:
    provider_id: str
    tenant_id: str
    scope: str

    def __post_init__(self) -> None:
        for field, value in (
            ("provider_id", self.provider_id),
            ("tenant_id", self.tenant_id),
            ("scope", self.scope),
        ):
            if not isinstance(value, str) or not value.strip() or len(value) > 256:
                raise ProviderGrantFloorError(f"{field} must be non-empty text up to 256 characters")
            if any(ord(ch) < 32 for ch in value):
                raise ProviderGrantFloorError(f"{field} contains a control character")
        parts = self.scope.split("/")
        if (
            self.scope.startswith("/") or self.scope.endswith("/")
            or any(part in {"", ".", ".."} for part in parts)
        ):
            raise ProviderGrantFloorError("scope is not canonical")


@dataclass(frozen=True)
class ProviderGrantFloorSnapshot:
    key: ProviderGrantScopeKey
    provider_generation_floor: int
    coordinator_epoch_floor: int
    coordinator_namespace: str | None
    leader_id: str | None
    native_lease_id: int | None
    lease_expires_at_unix: float | None
    state: str
    current_grant_id: str | None
    pending_operation_id: str | None
    pending_action: str | None
    pending_command_digest: str | None
    pending_generation: int | None
    pending_fence_command_digest: str | None
    last_fence_command_digest: str | None
    last_fence_receipt_digest: str | None
    last_activation_command_digest: str | None
    last_activation_receipt_digest: str | None
    revision: int
    authority_revision: int


@dataclass(frozen=True)
class ProviderGrantFloorReservation:
    operation_id: str
    action: Action
    key: ProviderGrantScopeKey
    grant_id: str
    generation: int
    command_digest: str
    fence_command_digest: str | None
    coordinator_namespace: str
    leader_id: str
    leader_epoch: int
    native_lease_id: int
    lease_expires_at_unix: float
    reserved_scope_revision: int
    authority_revision: int


@dataclass(frozen=True)
class ProviderGrantFloorOperation:
    operation_id: str
    action: Action
    key: ProviderGrantScopeKey
    grant_id: str
    generation: int
    command_digest: str
    fence_command_digest: str | None
    state: Literal["PENDING", "CONFIRMED"]
    provider_receipt_digest: str | None
    reserved_scope_revision: int
    confirmed_scope_revision: int | None
    authority_revision: int
    receipt_signer_key_id: str | None = None
    receipt_key_fingerprint: str | None = None
    receipt_trust_revision: int | None = None
    provider_applied_at_unix: float | None = None


class ProviderGrantFloorAuthority:
    """Structural port implemented by an independent linearizable authority."""

    def snapshot(
        self, key: ProviderGrantScopeKey, *, minimum_revision: int | None = None
    ) -> ProviderGrantFloorSnapshot:
        raise NotImplementedError

    def reserve_fence(self, **kwargs) -> ProviderGrantFloorReservation:
        raise NotImplementedError

    def reserve_activate(self, **kwargs) -> ProviderGrantFloorReservation:
        raise NotImplementedError

    def confirm_provider_receipt(self, **kwargs) -> ProviderGrantFloorSnapshot:
        raise NotImplementedError

    def operation_status(self, operation_id: str) -> ProviderGrantFloorOperation | None:
        raise NotImplementedError


class SQLiteProviderGrantFloorAuthority(ProviderGrantFloorAuthority):
    """Separate-file SQLite reference; single-host only, with transactional CAS.

    Revision checks protect concurrent callers and detect a rollback when the
    caller supplies a trusted minimum revision obtained outside this database.
    The SQLite file cannot detect its own restoration from an old snapshot.
    """

    def __init__(
        self, database_path: str | os.PathLike[str], *, busy_timeout_seconds: float = 5.0
    ) -> None:
        if not isinstance(database_path, (str, os.PathLike)) or not str(database_path).strip():
            raise ProviderGrantFloorError("external Grant floor database path is required")
        if (
            not isinstance(busy_timeout_seconds, (int, float))
            or isinstance(busy_timeout_seconds, bool)
            or not 0 < float(busy_timeout_seconds) <= 120.0
        ):
            raise ProviderGrantFloorError("busy timeout must be in (0, 120] seconds")
        raw = Path(database_path).expanduser()
        if raw.is_symlink():
            raise ProviderGrantFloorError("external Grant floor database cannot be a symlink")
        raw.parent.mkdir(parents=True, exist_ok=True)
        self.database_path = raw.resolve()
        self.busy_timeout_seconds = float(busy_timeout_seconds)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            str(self.database_path),
            timeout=self.busy_timeout_seconds,
            isolation_level=None,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute(f"PRAGMA busy_timeout={int(self.busy_timeout_seconds * 1000)}")
        connection.execute("PRAGMA synchronous=FULL")
        return connection

    def _initialize(self) -> None:
        connection = self._connect()
        try:
            connection.execute("PRAGMA journal_mode=DELETE")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS provider_grant_floor_meta (
                    singleton INTEGER PRIMARY KEY CHECK(singleton=1),
                    schema_version INTEGER NOT NULL,
                    authority_revision INTEGER NOT NULL,
                    trust_revision INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS provider_grant_floor_scopes (
                    provider_id TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    provider_generation_floor INTEGER NOT NULL,
                    coordinator_epoch_floor INTEGER NOT NULL,
                    coordinator_namespace TEXT,
                    leader_id TEXT,
                    native_lease_id INTEGER,
                    lease_expires_at_unix REAL,
                    state TEXT NOT NULL,
                    current_grant_id TEXT,
                    pending_operation_id TEXT,
                    pending_action TEXT,
                    pending_command_digest TEXT,
                    pending_generation INTEGER,
                    pending_fence_command_digest TEXT,
                    last_fence_command_digest TEXT,
                    last_fence_receipt_digest TEXT,
                    last_activation_command_digest TEXT,
                    last_activation_receipt_digest TEXT,
                    revision INTEGER NOT NULL,
                    PRIMARY KEY(provider_id, tenant_id, scope),
                    CHECK(state IN (
                        'IDLE','FENCE_PENDING','FENCED','ACTIVATE_PENDING',
                        'ACTIVE','RECOVERY_REQUIRED'
                    ))
                );
                CREATE TABLE IF NOT EXISTS provider_grant_floor_operations (
                    operation_id TEXT PRIMARY KEY,
                    provider_id TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    action TEXT NOT NULL CHECK(action IN ('FENCE','ACTIVATE')),
                    grant_id TEXT NOT NULL,
                    generation INTEGER NOT NULL,
                    command_digest TEXT NOT NULL,
                    fence_command_digest TEXT,
                    coordinator_namespace TEXT NOT NULL,
                    leader_id TEXT NOT NULL,
                    leader_epoch INTEGER NOT NULL,
                    native_lease_id INTEGER NOT NULL,
                    lease_expires_at_unix REAL NOT NULL,
                    state TEXT NOT NULL CHECK(state IN ('PENDING','CONFIRMED')),
                    provider_receipt_digest TEXT,
                    reserved_scope_revision INTEGER NOT NULL,
                    confirmed_scope_revision INTEGER,
                    authority_revision INTEGER NOT NULL,
                    receipt_signer_key_id TEXT,
                    receipt_key_fingerprint TEXT,
                    receipt_trust_revision INTEGER,
                    provider_applied_at_unix REAL
                );
                CREATE TABLE IF NOT EXISTS provider_grant_floor_receipt_keys (
                    provider_id TEXT NOT NULL,
                    key_id TEXT NOT NULL,
                    algorithm TEXT NOT NULL CHECK(algorithm='ED25519'),
                    public_key_base64 TEXT NOT NULL,
                    public_key_sha256 TEXT NOT NULL CHECK(length(public_key_sha256)=64),
                    status TEXT NOT NULL CHECK(status IN ('ACTIVE','RETIRING','REVOKED')),
                    not_before REAL NOT NULL,
                    not_after REAL,
                    retiring_effective_at REAL,
                    revocation_effective_at REAL,
                    revocation_reason TEXT,
                    trust_revision INTEGER NOT NULL,
                    created_at REAL NOT NULL,
                    PRIMARY KEY(provider_id,key_id)
                );
                """
            )
            row = connection.execute(
                "SELECT schema_version FROM provider_grant_floor_meta WHERE singleton=1"
            ).fetchone()
            if row is None:
                connection.execute(
                    """INSERT INTO provider_grant_floor_meta
                       (singleton, schema_version, authority_revision, trust_revision)
                       VALUES (1, ?, 0, 0)""",
                    (SCHEMA_VERSION,),
                )
            else:
                version = int(row["schema_version"])
                if version < 1 or version > SCHEMA_VERSION:
                    raise ProviderGrantFloorError(
                        "unsupported external Grant floor schema version"
                    )
                if version < 2:
                    meta_columns = {
                        item[1] for item in connection.execute(
                            "PRAGMA table_info(provider_grant_floor_meta)"
                        ).fetchall()
                    }
                    if "trust_revision" not in meta_columns:
                        connection.execute(
                            "ALTER TABLE provider_grant_floor_meta "
                            "ADD COLUMN trust_revision INTEGER NOT NULL DEFAULT 0"
                        )
                    operation_columns = {
                        item[1] for item in connection.execute(
                            "PRAGMA table_info(provider_grant_floor_operations)"
                        ).fetchall()
                    }
                    for column, declaration in (
                        ("receipt_signer_key_id", "TEXT"),
                        ("receipt_key_fingerprint", "TEXT"),
                        ("receipt_trust_revision", "INTEGER"),
                        ("provider_applied_at_unix", "REAL"),
                    ):
                        if column not in operation_columns:
                            connection.execute(
                                f"ALTER TABLE provider_grant_floor_operations "
                                f"ADD COLUMN {column} {declaration}"
                            )
                    version = 2
                if version < 3:
                    key_columns = {
                        item[1] for item in connection.execute(
                            "PRAGMA table_info(provider_grant_floor_receipt_keys)"
                        ).fetchall()
                    }
                    if "retiring_effective_at" not in key_columns:
                        connection.execute(
                            "ALTER TABLE provider_grant_floor_receipt_keys "
                            "ADD COLUMN retiring_effective_at REAL"
                        )
                    version = 3
                connection.execute(
                    "UPDATE provider_grant_floor_meta SET schema_version=? WHERE singleton=1",
                    (version,),
                )
                if version != SCHEMA_VERSION:
                    raise ProviderGrantFloorError(
                        "unsupported external Grant floor schema version"
                    )
        finally:
            connection.close()
        os.chmod(self.database_path, 0o600)

    @staticmethod
    def _integer(value: int, field: str, *, minimum: int = 1) -> int:
        if (
            not isinstance(value, int) or isinstance(value, bool)
            or value < minimum or value > MAX_SQLITE_INTEGER
        ):
            raise ProviderGrantFloorError(
                f"{field} must be a SQLite-safe integer >= {minimum}"
            )
        return value

    @staticmethod
    def _identifier(value: str, field: str) -> str:
        if not isinstance(value, str) or not _ID_RE.fullmatch(value):
            raise ProviderGrantFloorError(f"{field} is invalid")
        return value

    @staticmethod
    def _digest(value: str, field: str) -> str:
        if not isinstance(value, str) or not _DIGEST_RE.fullmatch(value):
            raise ProviderGrantFloorError(f"{field} must be a lowercase SHA-256 digest")
        return value

    @staticmethod
    def _namespace(value: str) -> str:
        if (
            not isinstance(value, str)
            or not value.startswith("/")
            or not value.endswith("/")
            or "//" in value
            or any(ch.isspace() for ch in value)
        ):
            raise ProviderGrantFloorError(
                "Coordinator namespace must match /cnc/migration/isolated/{single-id}/"
            )
        parts = value.strip("/").split("/")
        if (
            len(parts) != 4
            or parts[:3] != ["cnc", "migration", "isolated"]
            or not _ID_RE.fullmatch(parts[3])
        ):
            raise ProviderGrantFloorError(
                "Coordinator namespace must match /cnc/migration/isolated/{single-id}/"
            )
        return value

    @staticmethod
    def _lease_expiry(value: float) -> float:
        if (
            not isinstance(value, (int, float)) or isinstance(value, bool)
            or not math.isfinite(float(value)) or float(value) <= 0
        ):
            raise ProviderGrantFloorError("Coordinator native Lease expiry must be finite and positive")
        return float(value)

    @staticmethod
    def _key_tuple(key: ProviderGrantScopeKey) -> tuple[str, str, str]:
        if not isinstance(key, ProviderGrantScopeKey):
            raise ProviderGrantFloorError("a ProviderGrantScopeKey is required")
        return key.provider_id, key.tenant_id, key.scope

    @staticmethod
    def _bump_authority_revision(connection: sqlite3.Connection) -> int:
        connection.execute(
            "UPDATE provider_grant_floor_meta SET authority_revision=authority_revision+1 WHERE singleton=1"
        )
        row = connection.execute(
            "SELECT authority_revision FROM provider_grant_floor_meta WHERE singleton=1"
        ).fetchone()
        return int(row["authority_revision"])

    @staticmethod
    def _snapshot_from_rows(key, row, authority_revision) -> ProviderGrantFloorSnapshot:
        if row is None:
            return ProviderGrantFloorSnapshot(
                key=key, provider_generation_floor=0, coordinator_epoch_floor=0,
                coordinator_namespace=None, leader_id=None, native_lease_id=None,
                lease_expires_at_unix=None, state="IDLE", current_grant_id=None,
                pending_operation_id=None, pending_action=None,
                pending_command_digest=None, pending_generation=None,
                pending_fence_command_digest=None, last_fence_command_digest=None,
                last_fence_receipt_digest=None, last_activation_command_digest=None,
                last_activation_receipt_digest=None, revision=0,
                authority_revision=authority_revision,
            )
        return ProviderGrantFloorSnapshot(
            key=key,
            provider_generation_floor=int(row["provider_generation_floor"]),
            coordinator_epoch_floor=int(row["coordinator_epoch_floor"]),
            coordinator_namespace=row["coordinator_namespace"],
            leader_id=row["leader_id"], native_lease_id=row["native_lease_id"],
            lease_expires_at_unix=row["lease_expires_at_unix"], state=row["state"],
            current_grant_id=row["current_grant_id"],
            pending_operation_id=row["pending_operation_id"],
            pending_action=row["pending_action"],
            pending_command_digest=row["pending_command_digest"],
            pending_generation=row["pending_generation"],
            pending_fence_command_digest=row["pending_fence_command_digest"],
            last_fence_command_digest=row["last_fence_command_digest"],
            last_fence_receipt_digest=row["last_fence_receipt_digest"],
            last_activation_command_digest=row["last_activation_command_digest"],
            last_activation_receipt_digest=row["last_activation_receipt_digest"],
            revision=int(row["revision"]), authority_revision=authority_revision,
        )

    def snapshot(
        self, key: ProviderGrantScopeKey, *, minimum_revision: int | None = None
    ) -> ProviderGrantFloorSnapshot:
        self._key_tuple(key)
        if minimum_revision is not None:
            self._integer(minimum_revision, "minimum_revision", minimum=0)
        connection = self._connect()
        try:
            connection.execute("BEGIN")
            meta = connection.execute(
                "SELECT authority_revision FROM provider_grant_floor_meta WHERE singleton=1"
            ).fetchone()
            row = connection.execute(
                """SELECT * FROM provider_grant_floor_scopes
                   WHERE provider_id=? AND tenant_id=? AND scope=?""",
                self._key_tuple(key),
            ).fetchone()
            result = self._snapshot_from_rows(key, row, int(meta["authority_revision"]))
            if minimum_revision is not None and result.revision < minimum_revision:
                raise ProviderGrantFloorRevisionRegression(
                    "external Grant floor scope revision is below the trusted minimum"
                )
            connection.commit()
            return result
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _operation_from_row(self, row) -> ProviderGrantFloorOperation:
        key = ProviderGrantScopeKey(row["provider_id"], row["tenant_id"], row["scope"])
        return ProviderGrantFloorOperation(
            operation_id=row["operation_id"], action=row["action"], key=key,
            grant_id=row["grant_id"], generation=int(row["generation"]),
            command_digest=row["command_digest"],
            fence_command_digest=row["fence_command_digest"], state=row["state"],
            provider_receipt_digest=row["provider_receipt_digest"],
            reserved_scope_revision=int(row["reserved_scope_revision"]),
            confirmed_scope_revision=(
                int(row["confirmed_scope_revision"])
                if row["confirmed_scope_revision"] is not None else None
            ),
            authority_revision=int(row["authority_revision"]),
            receipt_signer_key_id=row["receipt_signer_key_id"],
            receipt_key_fingerprint=row["receipt_key_fingerprint"],
            receipt_trust_revision=(
                int(row["receipt_trust_revision"])
                if row["receipt_trust_revision"] is not None else None
            ),
            provider_applied_at_unix=(
                float(row["provider_applied_at_unix"])
                if row["provider_applied_at_unix"] is not None else None
            ),
        )

    def operation_status(self, operation_id: str) -> ProviderGrantFloorOperation | None:
        self._identifier(operation_id, "operation_id")
        with self._read_connection() as connection:
            row = connection.execute(
                "SELECT * FROM provider_grant_floor_operations WHERE operation_id=?",
                (operation_id,),
            ).fetchone()
            return self._operation_from_row(row) if row is not None else None

    def _read_connection(self):
        class ReadContext:
            def __init__(self, owner):
                self.owner = owner
                self.connection = None
            def __enter__(self):
                self.connection = self.owner._connect()
                return self.connection
            def __exit__(self, exc_type, exc, tb):
                self.connection.close()
        return ReadContext(self)

    def _existing_reservation(
        self, connection, operation_id: str, *, action: Action,
        key: ProviderGrantScopeKey, grant_id: str, command_digest: str,
        fence_command_digest: str | None, coordinator_namespace: str,
        leader_id: str, leader_epoch: int, native_lease_id: int,
        lease_expires_at_unix: float,
    ) -> ProviderGrantFloorReservation | None:
        row = connection.execute(
            "SELECT * FROM provider_grant_floor_operations WHERE operation_id=?",
            (operation_id,),
        ).fetchone()
        if row is None:
            return None
        expected = (
            row["action"], row["provider_id"], row["tenant_id"], row["scope"],
            row["grant_id"], row["command_digest"], row["fence_command_digest"],
            row["coordinator_namespace"], row["leader_id"], int(row["leader_epoch"]),
            int(row["native_lease_id"]), float(row["lease_expires_at_unix"]),
        )
        supplied = (
            action, key.provider_id, key.tenant_id, key.scope, grant_id,
            command_digest, fence_command_digest, coordinator_namespace, leader_id,
            leader_epoch, native_lease_id, lease_expires_at_unix,
        )
        if expected != supplied:
            raise ProviderGrantFloorConflict(
                "operation ID was already used for a different Grant floor reservation"
            )
        return ProviderGrantFloorReservation(
            operation_id=operation_id, action=action, key=key, grant_id=grant_id,
            generation=int(row["generation"]), command_digest=command_digest,
            fence_command_digest=fence_command_digest,
            coordinator_namespace=coordinator_namespace, leader_id=leader_id,
            leader_epoch=leader_epoch, native_lease_id=native_lease_id,
            lease_expires_at_unix=lease_expires_at_unix,
            reserved_scope_revision=int(row["reserved_scope_revision"]),
            authority_revision=int(row["authority_revision"]),
        )

    def _reserve(
        self, action: Action, *, operation_id: str, key: ProviderGrantScopeKey,
        grant_id: str, command_digest: str, fence_command_digest: str | None,
        coordinator_namespace: str, leader_id: str, leader_epoch: int,
        native_lease_id: int, lease_expires_at_unix: float,
        expected_revision: int,
    ) -> ProviderGrantFloorReservation:
        self._identifier(operation_id, "operation_id")
        self._identifier(grant_id, "grant_id")
        self._key_tuple(key)
        command_digest = self._digest(command_digest, "command_digest")
        if fence_command_digest is not None:
            fence_command_digest = self._digest(fence_command_digest, "fence_command_digest")
        coordinator_namespace = self._namespace(coordinator_namespace)
        leader_id = self._identifier(leader_id, "leader_id")
        leader_epoch = self._integer(leader_epoch, "leader_epoch")
        native_lease_id = self._integer(native_lease_id, "native_lease_id")
        lease_expires_at_unix = self._lease_expiry(lease_expires_at_unix)
        expected_revision = self._integer(expected_revision, "expected_revision", minimum=0)
        if action == "FENCE" and fence_command_digest is not None:
            raise ProviderGrantFloorError("FENCE reservation cannot reference a previous FENCE command")
        if action == "ACTIVATE" and fence_command_digest is None:
            raise ProviderGrantFloorError("ACTIVATE reservation must bind the exact FENCE command digest")

        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            existing = self._existing_reservation(
                connection, operation_id, action=action, key=key, grant_id=grant_id,
                command_digest=command_digest, fence_command_digest=fence_command_digest,
                coordinator_namespace=coordinator_namespace, leader_id=leader_id,
                leader_epoch=leader_epoch, native_lease_id=native_lease_id,
                lease_expires_at_unix=lease_expires_at_unix,
            )
            if existing is not None:
                connection.commit()
                return existing

            key_values = self._key_tuple(key)
            connection.execute(
                """INSERT OR IGNORE INTO provider_grant_floor_scopes
                   (provider_id,tenant_id,scope,provider_generation_floor,
                    coordinator_epoch_floor,state,revision)
                   VALUES (?,?,?,0,0,'IDLE',0)""",
                key_values,
            )
            row = connection.execute(
                """SELECT * FROM provider_grant_floor_scopes
                   WHERE provider_id=? AND tenant_id=? AND scope=?""",
                key_values,
            ).fetchone()
            actual_revision = int(row["revision"])
            if actual_revision != expected_revision:
                raise ProviderGrantFloorConflict(
                    f"scope revision CAS failed: expected {expected_revision}, actual {actual_revision}"
                )
            if row["state"] in {"FENCE_PENDING", "ACTIVATE_PENDING", "RECOVERY_REQUIRED"}:
                raise ProviderGrantFloorConflict("scope has a pending or recovery-required operation")

            same_identity = (
                row["coordinator_namespace"] == coordinator_namespace
                and row["leader_id"] == leader_id
                and row["native_lease_id"] == native_lease_id
            )
            if (
                row["coordinator_namespace"] is not None
                and row["coordinator_namespace"] != coordinator_namespace
            ):
                raise ProviderGrantFloorConflict(
                    "Coordinator namespace is immutable for an established Provider scope"
                )
            current_epoch = int(row["coordinator_epoch_floor"])
            if action == "FENCE":
                if row["state"] == "FENCED":
                    raise ProviderGrantFloorConflict("scope is already FENCED; duplicate FENCE is not allowed")
                if leader_epoch < current_epoch:
                    raise ProviderGrantFloorConflict("Coordinator Leader epoch is below the external floor")
                if current_epoch > 0 and leader_epoch == current_epoch and not same_identity:
                    raise ProviderGrantFloorConflict(
                        "same Leader epoch cannot change namespace, Leader ID or native Lease ID"
                    )
                if current_epoch > 0 and leader_epoch == current_epoch and (
                    lease_expires_at_unix < float(row["lease_expires_at_unix"])
                ):
                    raise ProviderGrantFloorConflict("same-Leader native Lease expiry cannot regress")
                if row["current_grant_id"] is not None and row["current_grant_id"] != grant_id:
                    raise ProviderGrantFloorConflict("FENCE grant ID does not match the current scope Grant")
                next_generation = int(row["provider_generation_floor"]) + 1
                if next_generation > MAX_SQLITE_INTEGER:
                    raise ProviderGrantFloorError("Provider generation floor overflow")
                next_state = "FENCE_PENDING"
                next_fence_digest = None
            else:
                if row["state"] != "FENCED":
                    raise ProviderGrantFloorConflict("ACTIVATE requires a confirmed FENCED scope")
                if leader_epoch != current_epoch or not same_identity:
                    raise ProviderGrantFloorConflict("ACTIVATE Coordinator Leader/native Lease identity mismatch")
                if lease_expires_at_unix < float(row["lease_expires_at_unix"]):
                    raise ProviderGrantFloorConflict("ACTIVATE native Lease expiry cannot regress")
                if grant_id != row["current_grant_id"]:
                    raise ProviderGrantFloorConflict("ACTIVATE grant ID does not match the FENCED grant")
                if fence_command_digest != row["last_fence_command_digest"]:
                    raise ProviderGrantFloorConflict("ACTIVATE does not bind the latest confirmed FENCE command")
                next_generation = int(row["provider_generation_floor"]) + 1
                if next_generation > MAX_SQLITE_INTEGER:
                    raise ProviderGrantFloorError("Provider generation floor overflow")
                next_state = "ACTIVATE_PENDING"
                next_fence_digest = fence_command_digest

            next_revision = actual_revision + 1
            authority_revision = self._bump_authority_revision(connection)
            connection.execute(
                """UPDATE provider_grant_floor_scopes SET
                    provider_generation_floor=?, coordinator_epoch_floor=?,
                    coordinator_namespace=?, leader_id=?, native_lease_id=?,
                    lease_expires_at_unix=?, state=?, current_grant_id=?,
                    pending_operation_id=?, pending_action=?, pending_command_digest=?,
                    pending_generation=?, pending_fence_command_digest=?, revision=?
                   WHERE provider_id=? AND tenant_id=? AND scope=?""",
                (
                    next_generation, leader_epoch, coordinator_namespace, leader_id,
                    native_lease_id, lease_expires_at_unix, next_state, grant_id,
                    operation_id, action, command_digest, next_generation,
                    next_fence_digest, next_revision, *key_values,
                ),
            )
            connection.execute(
                """INSERT INTO provider_grant_floor_operations
                   (operation_id,provider_id,tenant_id,scope,action,grant_id,generation,
                    command_digest,fence_command_digest,coordinator_namespace,leader_id,
                    leader_epoch,native_lease_id,lease_expires_at_unix,state,
                    reserved_scope_revision,authority_revision)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,'PENDING',?,?)""",
                (
                    operation_id, *key_values, action, grant_id, next_generation,
                    command_digest, fence_command_digest, coordinator_namespace,
                    leader_id, leader_epoch, native_lease_id, lease_expires_at_unix,
                    next_revision, authority_revision,
                ),
            )
            connection.commit()
            return ProviderGrantFloorReservation(
                operation_id=operation_id, action=action, key=key, grant_id=grant_id,
                generation=next_generation, command_digest=command_digest,
                fence_command_digest=fence_command_digest,
                coordinator_namespace=coordinator_namespace, leader_id=leader_id,
                leader_epoch=leader_epoch, native_lease_id=native_lease_id,
                lease_expires_at_unix=lease_expires_at_unix,
                reserved_scope_revision=next_revision,
                authority_revision=authority_revision,
            )
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def reserve_fence(
        self, *, operation_id: str, key: ProviderGrantScopeKey, grant_id: str,
        command_digest: str, coordinator_namespace: str, leader_id: str,
        leader_epoch: int, native_lease_id: int, lease_expires_at_unix: float,
        expected_revision: int,
    ) -> ProviderGrantFloorReservation:
        return self._reserve(
            "FENCE", operation_id=operation_id, key=key, grant_id=grant_id,
            command_digest=command_digest, fence_command_digest=None,
            coordinator_namespace=coordinator_namespace, leader_id=leader_id,
            leader_epoch=leader_epoch, native_lease_id=native_lease_id,
            lease_expires_at_unix=lease_expires_at_unix,
            expected_revision=expected_revision,
        )

    def reserve_activate(
        self, *, operation_id: str, key: ProviderGrantScopeKey, grant_id: str,
        command_digest: str, fence_command_digest: str, coordinator_namespace: str,
        leader_id: str, leader_epoch: int, native_lease_id: int,
        lease_expires_at_unix: float, expected_revision: int,
    ) -> ProviderGrantFloorReservation:
        return self._reserve(
            "ACTIVATE", operation_id=operation_id, key=key, grant_id=grant_id,
            command_digest=command_digest, fence_command_digest=fence_command_digest,
            coordinator_namespace=coordinator_namespace, leader_id=leader_id,
            leader_epoch=leader_epoch, native_lease_id=native_lease_id,
            lease_expires_at_unix=lease_expires_at_unix,
            expected_revision=expected_revision,
        )

    @staticmethod
    def _trust_key_from_row(row) -> ProviderReceiptTrustKey:
        try:
            public_key = base64.b64decode(row["public_key_base64"], validate=True)
        except (ValueError, base64.binascii.Error) as exc:
            raise ProviderGrantFloorError(
                "Provider receipt trust registry contains an invalid public key"
            ) from exc
        return ProviderReceiptTrustKey(
            provider_id=row["provider_id"],
            key_id=row["key_id"],
            public_key=public_key,
            public_key_sha256=row["public_key_sha256"],
            status=row["status"],
            not_before=float(row["not_before"]),
            not_after=(float(row["not_after"]) if row["not_after"] is not None else None),
            retiring_effective_at=(
                float(row["retiring_effective_at"])
                if row["retiring_effective_at"] is not None else None
            ),
            revocation_effective_at=(
                float(row["revocation_effective_at"])
                if row["revocation_effective_at"] is not None else None
            ),
            trust_revision=int(row["trust_revision"]),
        )

    def admin_register_provider_receipt_key(
        self, *, provider_id: str, key_id: str, public_key: bytes,
        not_before: float, not_after: float | None = None,
    ) -> dict[str, object]:
        """Register a Provider receipt key through the local database-owner control path."""
        self._identifier(provider_id, "provider_id")
        if not isinstance(key_id, str) or not re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", key_id
        ):
            raise ProviderGrantFloorError("Provider receipt key ID is invalid")
        if not isinstance(public_key, bytes) or len(public_key) != 32:
            raise ProviderGrantFloorError("Provider receipt Ed25519 public key must contain 32 bytes")
        before = self._lease_expiry(not_before)
        after = self._lease_expiry(not_after) if not_after is not None else None
        if after is not None and after <= before:
            raise ProviderGrantFloorError("Provider receipt key validity interval is invalid")
        fingerprint = hashlib.sha256(public_key).hexdigest()
        encoded = base64.b64encode(public_key).decode("ascii")
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT * FROM provider_grant_floor_receipt_keys WHERE provider_id=? AND key_id=?",
                (provider_id, key_id),
            ).fetchone()
            if existing is not None:
                if (
                    existing["public_key_sha256"] != fingerprint
                    or existing["public_key_base64"] != encoded
                    or float(existing["not_before"]) != before
                    or existing["not_after"] != after
                ):
                    raise ProviderGrantFloorConflict(
                        "Provider receipt key ID is already bound to different key material or validity"
                    )
                result = dict(existing)
                connection.commit()
                return result
            connection.execute(
                "UPDATE provider_grant_floor_meta SET trust_revision=trust_revision+1 WHERE singleton=1"
            )
            trust_revision = int(connection.execute(
                "SELECT trust_revision FROM provider_grant_floor_meta WHERE singleton=1"
            ).fetchone()["trust_revision"])
            created_at = time.time()
            connection.execute(
                """INSERT INTO provider_grant_floor_receipt_keys(
                    provider_id,key_id,algorithm,public_key_base64,public_key_sha256,
                    status,not_before,not_after,retiring_effective_at,revocation_effective_at,
                    revocation_reason,trust_revision,created_at
                ) VALUES(?,?,'ED25519',?,?, 'ACTIVE',?,?,NULL,NULL,NULL,?,?)""",
                (provider_id,key_id,encoded,fingerprint,before,after,trust_revision,created_at),
            )
            result = dict(connection.execute(
                "SELECT * FROM provider_grant_floor_receipt_keys WHERE provider_id=? AND key_id=?",
                (provider_id,key_id),
            ).fetchone())
            connection.commit()
            return result
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def admin_set_provider_receipt_key_status(
        self, *, provider_id: str, key_id: str, status: str,
        revocation_effective_at: float | None = None, revocation_reason: str | None = None,
    ) -> dict[str, object]:
        """Advance a registered receipt key to RETIRING or REVOKED; never reactivate it."""
        self._identifier(provider_id, "provider_id")
        if not isinstance(key_id, str) or not re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", key_id
        ):
            raise ProviderGrantFloorError("Provider receipt key ID is invalid")
        if not isinstance(status, str) or status not in {"RETIRING", "REVOKED"}:
            raise ProviderGrantFloorError("Provider receipt key may only transition to RETIRING or REVOKED")
        effective = None
        reason = None
        if status == "REVOKED":
            effective = self._lease_expiry(revocation_effective_at)
            if (
                not isinstance(revocation_reason, str) or not revocation_reason.strip()
                or len(revocation_reason) > 256
                or any(ord(ch) < 32 for ch in revocation_reason)
            ):
                raise ProviderGrantFloorError("Provider receipt revocation reason is invalid")
            reason = revocation_reason.strip()
        elif revocation_effective_at is not None or revocation_reason is not None:
            raise ProviderGrantFloorError("RETIRING key must not carry revocation metadata")
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM provider_grant_floor_receipt_keys WHERE provider_id=? AND key_id=?",
                (provider_id,key_id),
            ).fetchone()
            if row is None:
                raise ProviderGrantFloorConflict("unknown Provider receipt trust key")
            old_status = row["status"]
            if old_status == status and (
                status != "REVOKED"
                or (
                    row["revocation_effective_at"] == effective
                    and row["revocation_reason"] == reason
                )
            ):
                result = dict(row)
                connection.commit()
                return result
            if old_status not in {"ACTIVE", "RETIRING"} or status not in {"RETIRING","REVOKED"}:
                raise ProviderGrantFloorConflict("Provider receipt key lifecycle transition is invalid")
            if old_status == "RETIRING" and status != "REVOKED":
                raise ProviderGrantFloorConflict("Provider receipt key lifecycle transition is invalid")
            retiring_effective = (
                float(row["retiring_effective_at"])
                if row["retiring_effective_at"] is not None else time.time()
            )
            connection.execute(
                "UPDATE provider_grant_floor_meta SET trust_revision=trust_revision+1 WHERE singleton=1"
            )
            trust_revision = int(connection.execute(
                "SELECT trust_revision FROM provider_grant_floor_meta WHERE singleton=1"
            ).fetchone()["trust_revision"])
            connection.execute(
                """UPDATE provider_grant_floor_receipt_keys SET status=?,retiring_effective_at=?,
                   revocation_effective_at=?,revocation_reason=?,trust_revision=?
                   WHERE provider_id=? AND key_id=?""",
                (status,retiring_effective,effective,reason,trust_revision,provider_id,key_id),
            )
            result = dict(connection.execute(
                "SELECT * FROM provider_grant_floor_receipt_keys WHERE provider_id=? AND key_id=?",
                (provider_id,key_id),
            ).fetchone())
            connection.commit()
            return result
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def confirm_provider_receipt(
        self, *, operation_id: str, receipt_envelope: dict | bytes | str,
        expected_revision: int,
    ) -> ProviderGrantFloorSnapshot:
        self._identifier(operation_id, "operation_id")
        expected_revision = self._integer(expected_revision, "expected_revision", minimum=0)
        try:
            parsed = parse_receipt_envelope(receipt_envelope)
            canonical_envelope = canonical_receipt_json(parsed)
            receipt_digest = hashlib.sha256(canonical_envelope).hexdigest()
        except ProviderGrantReceiptError as exc:
            raise ProviderGrantFloorError(str(exc)) from exc
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            operation = connection.execute(
                "SELECT * FROM provider_grant_floor_operations WHERE operation_id=?",
                (operation_id,),
            ).fetchone()
            if operation is None:
                raise ProviderGrantFloorConflict("unknown external Grant floor operation ID")
            if operation["state"] == "CONFIRMED":
                if operation["provider_receipt_digest"] != receipt_digest:
                    raise ProviderGrantFloorConflict("confirmed Provider receipt digest cannot be replaced")
                key = ProviderGrantScopeKey(
                    operation["provider_id"], operation["tenant_id"], operation["scope"]
                )
                current = connection.execute(
                    """SELECT * FROM provider_grant_floor_scopes
                       WHERE provider_id=? AND tenant_id=? AND scope=?""",
                    self._key_tuple(key),
                ).fetchone()
                meta = connection.execute(
                    "SELECT authority_revision FROM provider_grant_floor_meta WHERE singleton=1"
                ).fetchone()
                result = self._snapshot_from_rows(key, current, int(meta["authority_revision"]))
                connection.commit()
                return result

            key = ProviderGrantScopeKey(
                operation["provider_id"], operation["tenant_id"], operation["scope"]
            )
            key_values = self._key_tuple(key)
            signature_key_id = parsed["signature"]["key_id"]
            trust_row = connection.execute(
                """SELECT * FROM provider_grant_floor_receipt_keys
                   WHERE provider_id=? AND key_id=?""",
                (operation["provider_id"],signature_key_id),
            ).fetchone()
            if trust_row is None:
                raise ProviderGrantFloorConflict("Provider receipt signer key is not trusted")
            trust_key = self._trust_key_from_row(trust_row)
            expected_claims = {
                "provider_id": operation["provider_id"],
                "tenant_id": operation["tenant_id"],
                "scope": operation["scope"],
                "action": operation["action"],
                "grant_id": operation["grant_id"],
                "generation": int(operation["generation"]),
                "command_sha256": operation["command_digest"],
                "fence_command_sha256": operation["fence_command_digest"],
                "coordinator_namespace": operation["coordinator_namespace"],
                "leader_id": operation["leader_id"],
                "leader_epoch": int(operation["leader_epoch"]),
                "native_lease_id": int(operation["native_lease_id"]),
                "native_lease_expires_at_unix": float(operation["lease_expires_at_unix"]),
            }
            try:
                verified = verify_provider_grant_receipt(
                    parsed, trust_key, expected_claims=expected_claims
                )
            except ProviderGrantReceiptError as exc:
                raise ProviderGrantFloorConflict(str(exc)) from exc

            scope = connection.execute(
                """SELECT * FROM provider_grant_floor_scopes
                   WHERE provider_id=? AND tenant_id=? AND scope=?""",
                key_values,
            ).fetchone()
            if scope is None or int(scope["revision"]) != expected_revision:
                actual = int(scope["revision"]) if scope is not None else 0
                raise ProviderGrantFloorConflict(
                    f"scope revision CAS failed: expected {expected_revision}, actual {actual}"
                )
            if (
                scope["pending_operation_id"] != operation_id
                or scope["pending_command_digest"] != operation["command_digest"]
                or int(scope["pending_generation"]) != int(operation["generation"])
                or scope["pending_action"] != operation["action"]
            ):
                raise ProviderGrantFloorConflict("Provider receipt does not match the pending scope operation")
            if operation["action"] == "ACTIVATE":
                if scope["last_fence_command_digest"] != operation["fence_command_digest"]:
                    raise ProviderGrantFloorConflict("ACTIVATE receipt does not match the latest confirmed FENCE")
                fence_row = connection.execute(
                    """SELECT provider_applied_at_unix FROM provider_grant_floor_operations
                       WHERE provider_id=? AND tenant_id=? AND scope=? AND action='FENCE'
                         AND state='CONFIRMED' AND command_digest=?""",
                    (
                        operation["provider_id"],operation["tenant_id"],operation["scope"],
                        operation["fence_command_digest"],
                    ),
                ).fetchone()
                if (
                    fence_row is None or fence_row["provider_applied_at_unix"] is None
                    or verified.applied_at_unix < float(fence_row["provider_applied_at_unix"])
                ):
                    raise ProviderGrantFloorConflict(
                        "ACTIVATE receipt applied time precedes its confirmed FENCE receipt"
                    )

            next_state = "FENCED" if operation["action"] == "FENCE" else "ACTIVE"
            next_revision = int(scope["revision"]) + 1
            authority_revision = self._bump_authority_revision(connection)
            if operation["action"] == "FENCE":
                connection.execute(
                    """UPDATE provider_grant_floor_scopes SET
                       state=?, pending_operation_id=NULL, pending_action=NULL,
                       pending_command_digest=NULL, pending_generation=NULL,
                       pending_fence_command_digest=NULL,
                       last_fence_command_digest=?, last_fence_receipt_digest=?,
                       revision=? WHERE provider_id=? AND tenant_id=? AND scope=?""",
                    (
                        next_state, operation["command_digest"], verified.receipt_digest,
                        next_revision, *key_values,
                    ),
                )
            else:
                connection.execute(
                    """UPDATE provider_grant_floor_scopes SET
                       state=?, pending_operation_id=NULL, pending_action=NULL,
                       pending_command_digest=NULL, pending_generation=NULL,
                       pending_fence_command_digest=NULL,
                       last_activation_command_digest=?, last_activation_receipt_digest=?,
                       revision=? WHERE provider_id=? AND tenant_id=? AND scope=?""",
                    (
                        next_state, operation["command_digest"], verified.receipt_digest,
                        next_revision, *key_values,
                    ),
                )
            connection.execute(
                """UPDATE provider_grant_floor_operations SET state='CONFIRMED',
                   provider_receipt_digest=?, receipt_signer_key_id=?,
                   receipt_key_fingerprint=?, receipt_trust_revision=?,
                   provider_applied_at_unix=?, confirmed_scope_revision=?, authority_revision=?
                   WHERE operation_id=?""",
                (
                    verified.receipt_digest, verified.signer_key_id,
                    verified.signer_public_key_sha256, verified.trust_revision,
                    verified.applied_at_unix, next_revision, authority_revision, operation_id,
                ),
            )
            result_row = connection.execute(
                """SELECT * FROM provider_grant_floor_scopes
                   WHERE provider_id=? AND tenant_id=? AND scope=?""",
                key_values,
            ).fetchone()
            result = self._snapshot_from_rows(key, result_row, authority_revision)
            connection.commit()
            return result
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
