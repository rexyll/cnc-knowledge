#!/usr/bin/env python3
"""Durable Coordinator authority reference for per-scope fencing and failover.

This implementation stores authority state in the same local SQLite database as
SQLiteProviderAdmissionCoordinator. SQLite WAL is a same-host reference only;
it is not a distributed consensus or multi-host coordination service.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterator

from scripts.spare_parts_fencing_attestation import create_fencing_attestation_ed25519


class CoordinatorAuthorityError(RuntimeError):
    """Base class for durable Coordinator authority failures."""


class CoordinatorAuthorityConflictError(CoordinatorAuthorityError):
    """A state, idempotency key, or authority transition conflicts."""


class CoordinatorAuthorityStaleLeaderError(CoordinatorAuthorityError):
    """The caller's persisted Leader epoch is no longer current."""


class CoordinatorAuthorityUnavailableError(CoordinatorAuthorityError):
    """The durable authority database is unavailable; callers must fail closed."""


@dataclass(frozen=True)
class CoordinatorLeadershipLease:
    leader_id: str
    epoch: int
    expires_at: float


@dataclass(frozen=True)
class DurableAuthorityOperation:
    scope: str
    kind: str
    idempotency_key: str
    request_sha256: str
    fencing_token: int
    operation_sequence: int | None
    lease_id: str
    owner_id: str
    tenant_id: str
    domain: str
    lease_expires_at: float
    state: str
    provider_generation: str | None
    manifest_key: str | None = None
    manifest_sha256: str | None = None


def _required_text(value: Any, name: str, *, maximum: int = 512) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum or "\x00" in value:
        raise CoordinatorAuthorityError(f"{name} must contain 1..{maximum} non-NUL characters")
    return value.strip()


def _scope(value: Any) -> str:
    text = _required_text(value, "fencing scope")
    parts = text.split("/")
    if text.startswith("/") or text.endswith("/") or any(part in {"", ".", ".."} for part in parts):
        raise CoordinatorAuthorityError("fencing scope must be a normalized relative path")
    return text


def _tenant_scope(value: Any, tenant_id: str) -> str:
    scope = _scope(value)
    tenant = _required_text(tenant_id, "tenant ID", maximum=128)
    if not scope.startswith(f"tenants/{tenant}/"):
        raise CoordinatorAuthorityError(
            "Coordinator fencing scope must be namespaced below tenants/<tenant_id>/"
        )
    return scope


def _timestamp(value: Any, name: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        raise CoordinatorAuthorityError(f"{name} must be a finite timestamp")
    return float(value)


def _sha256(value: Any, name: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise CoordinatorAuthorityError(f"{name} must be a lowercase SHA-256 digest")
    return value


def _digest(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _lease_values(lease: Any) -> dict[str, Any]:
    try:
        result = {
            "lease_id": _required_text(lease.lease_id, "lease ID", maximum=128),
            "owner_id": _required_text(lease.owner_id, "lease owner ID", maximum=128),
            "tenant_id": _required_text(lease.tenant_id, "lease tenant ID", maximum=128),
            "domain": _required_text(lease.domain, "lease domain", maximum=32),
            "admission_fencing_token": lease.fencing_token,
            "lease_expires_at": _timestamp(lease.expires_at, "lease expiry"),
        }
    except AttributeError as exc:
        raise CoordinatorAuthorityError("a ProviderAdmissionLease-compatible object is required") from exc
    if (
        not isinstance(result["admission_fencing_token"], int)
        or isinstance(result["admission_fencing_token"], bool)
        or result["admission_fencing_token"] < 1
    ):
        raise CoordinatorAuthorityError("admission fencing token must be a positive integer")
    return result


class SQLiteDurableCoordinatorAuthority:
    """Durable per-scope token/sequence authority and two-phase transition ledger.

    The database is expected to be the same local SQLite file used by the
    admission Coordinator, so admission lease identity is checked transactionally.
    A production multi-host implementation must replace this backend with a
    strongly consistent transactional/consensus service.
    """

    SCHEMA_VERSION = 1
    _PENDING_STATES = ("PENDING_ACTIVATION", "REVOKING", "PENDING_PUBLISH", "RECOVERY_REVIEW")

    def __init__(
        self,
        database_path: str | os.PathLike[str],
        *,
        clock_fn: Callable[[], float] = time.time,
        busy_timeout_seconds: float = 5.0,
    ):
        if not isinstance(database_path, (str, os.PathLike)) or not str(database_path).strip():
            raise CoordinatorAuthorityError("Coordinator authority database path is required")
        if str(database_path) == ":memory:":
            raise CoordinatorAuthorityError("Coordinator authority requires a durable file path")
        if not math.isfinite(busy_timeout_seconds) or busy_timeout_seconds <= 0:
            raise CoordinatorAuthorityError("busy timeout must be finite and positive")
        self.database_path = Path(database_path).expanduser().resolve()
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.clock_fn = clock_fn
        self.busy_timeout_seconds = float(busy_timeout_seconds)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            str(self.database_path),
            timeout=self.busy_timeout_seconds,
            isolation_level=None,
        )
        connection.row_factory = sqlite3.Row
        connection.execute(f"PRAGMA busy_timeout = {int(self.busy_timeout_seconds * 1000)}")
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA synchronous = FULL")
        return connection

    @contextmanager
    def _transaction(self, phase: str) -> Iterator[sqlite3.Connection]:
        try:
            connection = self._connect()
        except sqlite3.Error as exc:
            raise CoordinatorAuthorityUnavailableError(
                f"cannot open Coordinator authority database during {phase}"
            ) from exc
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.commit()
        except sqlite3.Error as exc:
            try:
                connection.rollback()
            except sqlite3.Error:
                pass
            raise CoordinatorAuthorityUnavailableError(
                f"Coordinator authority database failure during {phase}"
            ) from exc
        except Exception:
            try:
                connection.rollback()
            except sqlite3.Error:
                pass
            raise
        finally:
            connection.close()

    def _initialize(self) -> None:
        try:
            connection = self._connect()
            try:
                mode = connection.execute("PRAGMA journal_mode=WAL").fetchone()[0]
                if str(mode).lower() != "wal":
                    raise sqlite3.OperationalError("Coordinator authority database did not enter WAL mode")
                connection.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS coordinator_authority_meta (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS coordinator_authority_leader (
                        singleton INTEGER PRIMARY KEY CHECK(singleton=1),
                        leader_id TEXT,
                        epoch INTEGER NOT NULL,
                        expires_at REAL NOT NULL,
                        state TEXT NOT NULL CHECK(state IN ('UNCLAIMED','ACTIVE','FENCED'))
                    );
                    CREATE TABLE IF NOT EXISTS coordinator_authority_scopes (
                        scope TEXT PRIMARY KEY,
                        high_water_token INTEGER NOT NULL,
                        lease_id TEXT,
                        owner_id TEXT,
                        tenant_id TEXT,
                        domain TEXT,
                        lease_expires_at REAL,
                        lease_state TEXT NOT NULL CHECK(lease_state IN (
                            'IDLE','PENDING_ACTIVATION','ACTIVE','REVOKING','REVOKED',
                            'FENCED','RECOVERY_REQUIRED'
                        )),
                        latest_operation_sequence INTEGER NOT NULL,
                        provider_generation TEXT,
                        updated_at REAL NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS coordinator_authority_operations (
                        scope TEXT NOT NULL,
                        idempotency_key TEXT NOT NULL,
                        kind TEXT NOT NULL CHECK(kind IN ('ACTIVATE','REVOKE','PUBLISH')),
                        request_sha256 TEXT NOT NULL,
                        fencing_token INTEGER NOT NULL,
                        operation_sequence INTEGER,
                        lease_id TEXT NOT NULL,
                        owner_id TEXT NOT NULL,
                        tenant_id TEXT NOT NULL,
                        domain TEXT NOT NULL,
                        lease_expires_at REAL NOT NULL,
                        manifest_key TEXT,
                        manifest_sha256 TEXT,
                        state TEXT NOT NULL CHECK(state IN (
                            'PENDING_ACTIVATION','ACTIVE','REVOKING','REVOKED',
                            'PENDING_PUBLISH','COMMITTED','RECOVERY_REVIEW'
                        )),
                        provider_generation TEXT,
                        created_at REAL NOT NULL,
                        updated_at REAL NOT NULL,
                        PRIMARY KEY(scope,idempotency_key),
                        UNIQUE(scope,operation_sequence)
                    );
                    CREATE INDEX IF NOT EXISTS idx_authority_pending
                        ON coordinator_authority_operations(state,scope,created_at);
                    """
                )
            finally:
                connection.close()
            with self._transaction("initialize") as connection:
                connection.execute(
                    "INSERT OR IGNORE INTO coordinator_authority_meta(key,value) VALUES('schema_version',?)",
                    (str(self.SCHEMA_VERSION),),
                )
                version = connection.execute(
                    "SELECT value FROM coordinator_authority_meta WHERE key='schema_version'"
                ).fetchone()["value"]
                if version != str(self.SCHEMA_VERSION):
                    raise CoordinatorAuthorityError("unsupported Coordinator authority schema version")
                connection.execute(
                    """INSERT OR IGNORE INTO coordinator_authority_leader
                       (singleton,leader_id,epoch,expires_at,state)
                       VALUES(1,NULL,0,0,'UNCLAIMED')"""
                )
        except CoordinatorAuthorityError:
            raise
        except sqlite3.Error as exc:
            raise CoordinatorAuthorityUnavailableError("Coordinator authority initialization failed") from exc

    @staticmethod
    def _leader_row(connection: sqlite3.Connection) -> sqlite3.Row:
        return connection.execute(
            "SELECT * FROM coordinator_authority_leader WHERE singleton=1"
        ).fetchone()

    def _assert_leader(
        self, connection: sqlite3.Connection, leadership: CoordinatorLeadershipLease
    ) -> sqlite3.Row:
        if not isinstance(leadership, CoordinatorLeadershipLease):
            raise CoordinatorAuthorityStaleLeaderError("a current Coordinator leadership lease is required")
        row = self._leader_row(connection)
        now = self.clock_fn()
        if (
            row is None or row["state"] != "ACTIVE"
            or row["leader_id"] != leadership.leader_id
            or int(row["epoch"]) != leadership.epoch
            or float(row["expires_at"]) <= now
        ):
            raise CoordinatorAuthorityStaleLeaderError(
                "Coordinator Leader epoch is stale, expired or no longer authoritative"
            )
        return row

    def claim_leadership(
        self,
        leader_id: str,
        *,
        ttl_seconds: float,
        recovery_epoch_floor: int | None = None,
        reconciliation_ref: str | None = None,
    ) -> CoordinatorLeadershipLease:
        leader_id = _required_text(leader_id, "leader ID", maximum=128)
        if not isinstance(ttl_seconds, (int, float)) or isinstance(ttl_seconds, bool) or not math.isfinite(ttl_seconds) or not 1 <= ttl_seconds <= 300:
            raise CoordinatorAuthorityError("Leader TTL must be in [1, 300] seconds")
        now = self.clock_fn()
        with self._transaction("claim_leadership") as connection:
            current = self._leader_row(connection)
            current_epoch = int(current["epoch"])
            current_active = current["state"] == "ACTIVE" and float(current["expires_at"]) > now
            if recovery_epoch_floor is not None:
                if (
                    not isinstance(recovery_epoch_floor, int)
                    or isinstance(recovery_epoch_floor, bool)
                    or recovery_epoch_floor <= current_epoch
                ):
                    raise CoordinatorAuthorityError("external recovery epoch floor must exceed the restored epoch")
                _required_text(reconciliation_ref, "external leadership reconciliation reference", maximum=256)
            elif current_active:
                raise CoordinatorAuthorityConflictError("another Coordinator Leader lease is still active")
            epoch = max(current_epoch + 1, recovery_epoch_floor or 0)
            expires_at = now + float(ttl_seconds)
            connection.execute(
                """UPDATE coordinator_authority_leader
                   SET leader_id=?,epoch=?,expires_at=?,state='ACTIVE' WHERE singleton=1""",
                (leader_id, epoch, expires_at),
            )
            return CoordinatorLeadershipLease(leader_id, epoch, expires_at)

    def renew_leadership(
        self, leadership: CoordinatorLeadershipLease, *, ttl_seconds: float
    ) -> CoordinatorLeadershipLease:
        if not isinstance(ttl_seconds, (int, float)) or isinstance(ttl_seconds, bool) or not math.isfinite(ttl_seconds) or not 1 <= ttl_seconds <= 300:
            raise CoordinatorAuthorityError("Leader TTL must be in [1, 300] seconds")
        with self._transaction("renew_leadership") as connection:
            self._assert_leader(connection, leadership)
            expires_at = self.clock_fn() + float(ttl_seconds)
            connection.execute(
                "UPDATE coordinator_authority_leader SET expires_at=? WHERE singleton=1",
                (expires_at,),
            )
            return CoordinatorLeadershipLease(leadership.leader_id, leadership.epoch, expires_at)

    @staticmethod
    def _ensure_scope(connection: sqlite3.Connection, scope: str, now: float) -> sqlite3.Row:
        connection.execute(
            """INSERT OR IGNORE INTO coordinator_authority_scopes(
                scope,high_water_token,lease_id,owner_id,tenant_id,domain,lease_expires_at,
                lease_state,latest_operation_sequence,provider_generation,updated_at
            ) VALUES(?,0,NULL,NULL,NULL,NULL,NULL,'IDLE',0,NULL,?)""",
            (scope, now),
        )
        return connection.execute(
            "SELECT * FROM coordinator_authority_scopes WHERE scope=?", (scope,)
        ).fetchone()

    @staticmethod
    def _assert_admission_lease(connection: sqlite3.Connection, lease_values: dict[str, Any], now: float) -> None:
        table = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='admission_requests'"
        ).fetchone()
        if table is None:
            raise CoordinatorAuthorityUnavailableError(
                "durable authority must share the SQLite admission Coordinator database"
            )
        row = connection.execute(
            "SELECT * FROM admission_requests WHERE lease_id=?", (lease_values["lease_id"],)
        ).fetchone()
        if (
            row is None or row["state"] != "ACTIVE"
            or float(row["expires_at"]) <= now
            or row["owner_id"] != lease_values["owner_id"]
            or row["tenant_id"] != lease_values["tenant_id"]
            or row["domain"] != lease_values["domain"]
            or int(row["fencing_token"]) != lease_values["admission_fencing_token"]
            or abs(float(row["expires_at"]) - lease_values["lease_expires_at"]) > 1e-6
        ):
            raise CoordinatorAuthorityConflictError("admission lease is inactive, expired or mismatched")

    @staticmethod
    def _operation_from_row(row: sqlite3.Row) -> DurableAuthorityOperation:
        return DurableAuthorityOperation(
            scope=row["scope"],
            kind=row["kind"],
            idempotency_key=row["idempotency_key"],
            request_sha256=row["request_sha256"],
            fencing_token=int(row["fencing_token"]),
            operation_sequence=None if row["operation_sequence"] is None else int(row["operation_sequence"]),
            lease_id=row["lease_id"],
            owner_id=row["owner_id"],
            tenant_id=row["tenant_id"],
            domain=row["domain"],
            lease_expires_at=float(row["lease_expires_at"]),
            state=row["state"],
            provider_generation=row["provider_generation"],
            manifest_key=row["manifest_key"],
            manifest_sha256=row["manifest_sha256"],
        )

    @staticmethod
    def _existing_operation(
        connection: sqlite3.Connection, scope: str, idempotency_key: str,
        *, kind: str, request_sha256: str,
    ) -> DurableAuthorityOperation | None:
        row = connection.execute(
            "SELECT * FROM coordinator_authority_operations WHERE scope=? AND idempotency_key=?",
            (scope, idempotency_key),
        ).fetchone()
        if row is None:
            return None
        if row["kind"] != kind or row["request_sha256"] != request_sha256:
            raise CoordinatorAuthorityConflictError(
                "Coordinator idempotency key was reused for another operation or payload"
            )
        return SQLiteDurableCoordinatorAuthority._operation_from_row(row)

    def prepare_activation(
        self,
        leadership: CoordinatorLeadershipLease,
        lease: Any,
        *,
        scope: str,
        idempotency_key: str,
    ) -> DurableAuthorityOperation:
        scope, idem = _scope(scope), _required_text(idempotency_key, "activation idempotency key", maximum=256)
        values = _lease_values(lease)
        scope = _tenant_scope(scope, values["tenant_id"])
        digest = _digest({"scope": scope, "kind": "ACTIVATE", **values})
        now = self.clock_fn()
        with self._transaction("prepare_activation") as connection:
            self._assert_leader(connection, leadership)
            self._assert_admission_lease(connection, values, now)
            existing = self._existing_operation(
                connection, scope, idem, kind="ACTIVATE", request_sha256=digest
            )
            if existing is not None:
                return existing
            current = self._ensure_scope(connection, scope, now)
            if current["lease_state"] in {"PENDING_ACTIVATION", "REVOKING"}:
                raise CoordinatorAuthorityConflictError(
                    "scope has an unresolved activation or revocation; reconcile it first"
                )
            token = int(current["high_water_token"]) + 1
            connection.execute(
                """INSERT INTO coordinator_authority_operations(
                    scope,idempotency_key,kind,request_sha256,fencing_token,operation_sequence,
                    lease_id,owner_id,tenant_id,domain,lease_expires_at,manifest_key,manifest_sha256,
                    state,provider_generation,created_at,updated_at
                ) VALUES(?,?,'ACTIVATE',?,?,NULL,?,?,?,?,?,NULL,NULL,'PENDING_ACTIVATION',NULL,?,?)""",
                (
                    scope, idem, digest, token, values["lease_id"], values["owner_id"],
                    values["tenant_id"], values["domain"], values["lease_expires_at"], now, now,
                ),
            )
            connection.execute(
                """UPDATE coordinator_authority_scopes SET
                    high_water_token=?,lease_id=?,owner_id=?,tenant_id=?,domain=?,lease_expires_at=?,
                    lease_state='PENDING_ACTIVATION',provider_generation=NULL,updated_at=?
                   WHERE scope=?""",
                (
                    token, values["lease_id"], values["owner_id"], values["tenant_id"],
                    values["domain"], values["lease_expires_at"], now, scope,
                ),
            )
            row = connection.execute(
                "SELECT * FROM coordinator_authority_operations WHERE scope=? AND idempotency_key=?",
                (scope, idem),
            ).fetchone()
            return self._operation_from_row(row)

    def confirm_activation(
        self,
        leadership: CoordinatorLeadershipLease,
        *,
        scope: str,
        fencing_token: int,
        idempotency_key: str,
        observed_provider_state: str,
        observed_high_water_token: int,
        observed_lease_id: str,
        provider_generation: str,
    ) -> DurableAuthorityOperation:
        scope, idem = _scope(scope), _required_text(idempotency_key, "activation idempotency key", maximum=256)
        generation = _required_text(provider_generation, "Provider generation", maximum=256)
        lease_id = _required_text(observed_lease_id, "observed Provider lease ID", maximum=128)
        now = self.clock_fn()
        if observed_provider_state != "ACTIVE" or observed_high_water_token != fencing_token:
            raise CoordinatorAuthorityConflictError("Provider read-back does not confirm the requested activation")
        with self._transaction("confirm_activation") as connection:
            self._assert_leader(connection, leadership)
            row = connection.execute(
                "SELECT * FROM coordinator_authority_operations WHERE scope=? AND idempotency_key=?",
                (scope, idem),
            ).fetchone()
            if row is None or row["kind"] != "ACTIVATE" or int(row["fencing_token"]) != fencing_token or row["lease_id"] != lease_id:
                raise CoordinatorAuthorityConflictError("activation confirmation does not match a durable request")
            current = self._ensure_scope(connection, scope, now)
            if int(current["high_water_token"]) != fencing_token or current["lease_id"] != lease_id:
                raise CoordinatorAuthorityStaleLeaderError("activation has been superseded by a newer scope token")
            if row["state"] == "ACTIVE":
                if row["provider_generation"] != generation:
                    raise CoordinatorAuthorityConflictError("activation was already confirmed at another Provider generation")
                return self._operation_from_row(row)
            if row["state"] not in {"PENDING_ACTIVATION", "RECOVERY_REVIEW"}:
                raise CoordinatorAuthorityConflictError("activation is not pending reconciliation")
            connection.execute(
                """UPDATE coordinator_authority_operations
                   SET state='ACTIVE',provider_generation=?,updated_at=?
                   WHERE scope=? AND idempotency_key=?""",
                (generation, now, scope, idem),
            )
            connection.execute(
                """UPDATE coordinator_authority_scopes
                   SET lease_state='ACTIVE',provider_generation=?,updated_at=? WHERE scope=?""",
                (generation, now, scope),
            )
            updated = connection.execute(
                "SELECT * FROM coordinator_authority_operations WHERE scope=? AND idempotency_key=?",
                (scope, idem),
            ).fetchone()
            return self._operation_from_row(updated)

    def prepare_revocation(
        self,
        leadership: CoordinatorLeadershipLease,
        lease: Any,
        *,
        scope: str,
        fencing_token: int,
        idempotency_key: str,
    ) -> DurableAuthorityOperation:
        scope, idem = _scope(scope), _required_text(idempotency_key, "revocation idempotency key", maximum=256)
        values = _lease_values(lease)
        scope = _tenant_scope(scope, values["tenant_id"])
        if not isinstance(fencing_token, int) or isinstance(fencing_token, bool) or fencing_token < 1:
            raise CoordinatorAuthorityError("revocation fencing token must be a positive integer")
        digest = _digest({
            "scope": scope, "kind": "REVOKE", "fencing_token": fencing_token,
            "lease_id": values["lease_id"], "owner_id": values["owner_id"],
            "tenant_id": values["tenant_id"],
        })
        now = self.clock_fn()
        with self._transaction("prepare_revocation") as connection:
            self._assert_leader(connection, leadership)
            self._assert_admission_lease(connection, values, now)
            existing = self._existing_operation(
                connection, scope, idem, kind="REVOKE", request_sha256=digest
            )
            if existing is not None:
                return existing
            current = self._ensure_scope(connection, scope, now)
            if (
                current["lease_state"] != "ACTIVE"
                or int(current["high_water_token"]) != fencing_token
                or current["lease_id"] != values["lease_id"]
            ):
                raise CoordinatorAuthorityConflictError("only the exact active scope lease can enter REVOKING")
            connection.execute(
                """INSERT INTO coordinator_authority_operations(
                    scope,idempotency_key,kind,request_sha256,fencing_token,operation_sequence,
                    lease_id,owner_id,tenant_id,domain,lease_expires_at,manifest_key,manifest_sha256,
                    state,provider_generation,created_at,updated_at
                ) VALUES(?,?,'REVOKE',?,?,NULL,?,?,?,?,?,NULL,NULL,'REVOKING',NULL,?,?)""",
                (
                    scope, idem, digest, fencing_token, values["lease_id"], values["owner_id"],
                    values["tenant_id"], values["domain"], values["lease_expires_at"], now, now,
                ),
            )
            connection.execute(
                "UPDATE coordinator_authority_scopes SET lease_state='REVOKING',updated_at=? WHERE scope=?",
                (now, scope),
            )
            row = connection.execute(
                "SELECT * FROM coordinator_authority_operations WHERE scope=? AND idempotency_key=?",
                (scope, idem),
            ).fetchone()
            return self._operation_from_row(row)

    def confirm_revocation(
        self,
        leadership: CoordinatorLeadershipLease,
        *,
        scope: str,
        fencing_token: int,
        idempotency_key: str,
        observed_provider_state: str,
        observed_high_water_token: int,
        observed_lease_id: str,
        provider_generation: str,
    ) -> DurableAuthorityOperation:
        scope, idem = _scope(scope), _required_text(idempotency_key, "revocation idempotency key", maximum=256)
        generation = _required_text(provider_generation, "Provider generation", maximum=256)
        lease_id = _required_text(observed_lease_id, "observed Provider lease ID", maximum=128)
        now = self.clock_fn()
        if observed_provider_state != "REVOKED" or observed_high_water_token != fencing_token:
            raise CoordinatorAuthorityConflictError("Provider read-back does not confirm the requested revocation")
        with self._transaction("confirm_revocation") as connection:
            self._assert_leader(connection, leadership)
            row = connection.execute(
                "SELECT * FROM coordinator_authority_operations WHERE scope=? AND idempotency_key=?",
                (scope, idem),
            ).fetchone()
            if row is None or row["kind"] != "REVOKE" or int(row["fencing_token"]) != fencing_token or row["lease_id"] != lease_id:
                raise CoordinatorAuthorityConflictError("revocation confirmation does not match a durable request")
            current = self._ensure_scope(connection, scope, now)
            if int(current["high_water_token"]) != fencing_token or current["lease_id"] != lease_id:
                raise CoordinatorAuthorityStaleLeaderError("revocation target has been superseded")
            if row["state"] == "REVOKED":
                if row["provider_generation"] != generation:
                    raise CoordinatorAuthorityConflictError("revocation was already confirmed at another Provider generation")
                return self._operation_from_row(row)
            if row["state"] != "REVOKING":
                raise CoordinatorAuthorityConflictError("revocation is not pending reconciliation")
            connection.execute(
                """UPDATE coordinator_authority_operations
                   SET state='REVOKED',provider_generation=?,updated_at=?
                   WHERE scope=? AND idempotency_key=?""",
                (generation, now, scope, idem),
            )
            connection.execute(
                """UPDATE coordinator_authority_scopes
                   SET lease_state='REVOKED',provider_generation=?,updated_at=? WHERE scope=?""",
                (generation, now, scope),
            )
            updated = connection.execute(
                "SELECT * FROM coordinator_authority_operations WHERE scope=? AND idempotency_key=?",
                (scope, idem),
            ).fetchone()
            return self._operation_from_row(updated)

    def allocate_operation_sequence(
        self,
        leadership: CoordinatorLeadershipLease,
        lease: Any,
        *,
        scope: str,
        idempotency_key: str,
        manifest_key: str,
        manifest_sha256: str,
    ) -> DurableAuthorityOperation:
        scope, idem = _scope(scope), _required_text(idempotency_key, "publish idempotency key", maximum=256)
        values = _lease_values(lease)
        scope = _tenant_scope(scope, values["tenant_id"])
        key = _required_text(manifest_key, "manifest key", maximum=1024)
        digest = _sha256(manifest_sha256, "manifest SHA-256")
        if not key.startswith(scope + "/") or any(part in {".", ".."} for part in key.split("/")) or "\\" in key:
            raise CoordinatorAuthorityError("manifest key must be a normalized key below the fencing scope")
        request_sha = _digest({
            "scope": scope, "kind": "PUBLISH", "lease_id": values["lease_id"],
            "manifest_key": key, "manifest_sha256": digest,
        })
        now = self.clock_fn()
        with self._transaction("allocate_operation_sequence") as connection:
            self._assert_leader(connection, leadership)
            existing = self._existing_operation(
                connection, scope, idem, kind="PUBLISH", request_sha256=request_sha
            )
            if existing is not None:
                return existing
            self._assert_admission_lease(connection, values, now)
            current = self._ensure_scope(connection, scope, now)
            if (
                current["lease_state"] != "ACTIVE"
                or current["lease_id"] != values["lease_id"]
                or current["owner_id"] != values["owner_id"]
                or current["tenant_id"] != values["tenant_id"]
                or int(current["high_water_token"]) < 1
                or float(current["lease_expires_at"] or 0) <= now
            ):
                raise CoordinatorAuthorityConflictError("publish requires the exact confirmed ACTIVE scope lease")
            sequence = int(current["latest_operation_sequence"]) + 1
            token = int(current["high_water_token"])
            connection.execute(
                """INSERT INTO coordinator_authority_operations(
                    scope,idempotency_key,kind,request_sha256,fencing_token,operation_sequence,
                    lease_id,owner_id,tenant_id,domain,lease_expires_at,manifest_key,manifest_sha256,
                    state,provider_generation,created_at,updated_at
                ) VALUES(?,?,'PUBLISH',?,?,?,?,?,?,?,?,?,?,'PENDING_PUBLISH',NULL,?,?)""",
                (
                    scope, idem, request_sha, token, sequence, values["lease_id"],
                    values["owner_id"], values["tenant_id"], values["domain"],
                    values["lease_expires_at"], key, digest, now, now,
                ),
            )
            connection.execute(
                """UPDATE coordinator_authority_scopes
                   SET latest_operation_sequence=?,updated_at=? WHERE scope=?""",
                (sequence, now, scope),
            )
            row = connection.execute(
                "SELECT * FROM coordinator_authority_operations WHERE scope=? AND idempotency_key=?",
                (scope, idem),
            ).fetchone()
            return self._operation_from_row(row)

    def confirm_publish(
        self,
        leadership: CoordinatorLeadershipLease,
        *,
        scope: str,
        idempotency_key: str,
        observed_provider_state: str,
        observed_fencing_token: int,
        observed_operation_sequence: int,
        observed_idempotency_key: str,
        observed_manifest_key: str,
        observed_manifest_sha256: str,
        provider_generation: str,
    ) -> DurableAuthorityOperation:
        scope, idem = _scope(scope), _required_text(idempotency_key, "publish idempotency key", maximum=256)
        generation = _required_text(provider_generation, "Provider generation", maximum=256)
        if observed_provider_state != "ACTIVE" or observed_idempotency_key != idem:
            raise CoordinatorAuthorityConflictError("Provider receipt does not identify the requested publish")
        observed_key = _required_text(observed_manifest_key, "observed Provider manifest key", maximum=1024)
        observed_digest = _sha256(observed_manifest_sha256, "observed Provider manifest SHA-256")
        now = self.clock_fn()
        with self._transaction("confirm_publish") as connection:
            self._assert_leader(connection, leadership)
            row = connection.execute(
                "SELECT * FROM coordinator_authority_operations WHERE scope=? AND idempotency_key=?",
                (scope, idem),
            ).fetchone()
            if row is None or row["kind"] != "PUBLISH":
                raise CoordinatorAuthorityConflictError("publish confirmation has no durable sequence allocation")
            if (
                int(row["fencing_token"]) != observed_fencing_token
                or int(row["operation_sequence"]) != observed_operation_sequence
                or row["manifest_key"] != observed_key
                or row["manifest_sha256"] != observed_digest
            ):
                raise CoordinatorAuthorityConflictError(
                    "Provider receipt token/sequence/manifest differs from Coordinator allocation"
                )
            if row["state"] == "COMMITTED":
                if row["provider_generation"] != generation:
                    raise CoordinatorAuthorityConflictError("publish was already confirmed at another Provider generation")
                return self._operation_from_row(row)
            current = self._ensure_scope(connection, scope, now)
            if (
                current["lease_state"] != "ACTIVE"
                or int(current["high_water_token"]) != observed_fencing_token
                or current["lease_id"] != row["lease_id"]
            ):
                raise CoordinatorAuthorityStaleLeaderError("publish lease was superseded before confirmation")
            if row["state"] != "PENDING_PUBLISH":
                raise CoordinatorAuthorityConflictError("publish is not pending reconciliation")
            connection.execute(
                """UPDATE coordinator_authority_operations
                   SET state='COMMITTED',provider_generation=?,updated_at=?
                   WHERE scope=? AND idempotency_key=?""",
                (generation, now, scope, idem),
            )
            updated = connection.execute(
                "SELECT * FROM coordinator_authority_operations WHERE scope=? AND idempotency_key=?",
                (scope, idem),
            ).fetchone()
            return self._operation_from_row(updated)

    def authorize_operation_signing(
        self,
        leadership: CoordinatorLeadershipLease,
        operation: DurableAuthorityOperation,
    ) -> None:
        """Allow proof signing only for a durable pending operation under the current Leader epoch.

        A restarted/new Leader may re-sign an unresolved operation after observing
        its durable row. A stale process cannot use a cached operation object to
        mint a fresh proof after takeover.
        """
        if not isinstance(operation, DurableAuthorityOperation):
            raise CoordinatorAuthorityError("a durable Coordinator operation is required")
        expected_state = {
            "ACTIVATE": "PENDING_ACTIVATION",
            "REVOKE": "REVOKING",
            "PUBLISH": "PENDING_PUBLISH",
        }.get(operation.kind)
        if expected_state is None:
            raise CoordinatorAuthorityError("unsupported distributed fencing operation kind")
        with self._transaction("authorize_operation_signing") as connection:
            self._assert_leader(connection, leadership)
            row = connection.execute(
                "SELECT * FROM coordinator_authority_operations WHERE scope=? AND idempotency_key=?",
                (operation.scope, operation.idempotency_key),
            ).fetchone()
            if (
                row is None
                or row["kind"] != operation.kind
                or row["request_sha256"] != operation.request_sha256
                or int(row["fencing_token"]) != operation.fencing_token
                or row["lease_id"] != operation.lease_id
                or row["state"] != expected_state
                or (
                    None if row["operation_sequence"] is None
                    else int(row["operation_sequence"])
                ) != operation.operation_sequence
                or row["manifest_key"] != operation.manifest_key
                or row["manifest_sha256"] != operation.manifest_sha256
            ):
                raise CoordinatorAuthorityStaleLeaderError(
                    "operation is not pending in the durable Coordinator state"
                )

    def list_pending_operations(
        self, leadership: CoordinatorLeadershipLease, *, scope: str | None = None
    ) -> list[DurableAuthorityOperation]:
        if scope is not None:
            scope = _scope(scope)
        with self._transaction("list_pending_operations") as connection:
            self._assert_leader(connection, leadership)
            placeholders = ",".join("?" for _ in self._PENDING_STATES)
            parameters: list[Any] = list(self._PENDING_STATES)
            sql = f"SELECT * FROM coordinator_authority_operations WHERE state IN ({placeholders})"
            if scope is not None:
                sql += " AND scope=?"
                parameters.append(scope)
            sql += " ORDER BY created_at,scope,operation_sequence"
            rows = connection.execute(sql, parameters).fetchall()
            return [self._operation_from_row(row) for row in rows]

    def reconcile_after_restore(
        self,
        leadership: CoordinatorLeadershipLease,
        *,
        scope: str,
        external_high_water_token: int,
        external_operation_sequence: int,
        reconciliation_ref: str,
    ) -> dict[str, Any]:
        scope = _scope(scope)
        _required_text(reconciliation_ref, "external fencing reconciliation reference", maximum=256)
        for value, name in (
            (external_high_water_token, "external high-water token"),
            (external_operation_sequence, "external operation sequence"),
        ):
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise CoordinatorAuthorityError(f"{name} must be a non-negative integer")
        now = self.clock_fn()
        with self._transaction("reconcile_after_restore") as connection:
            self._assert_leader(connection, leadership)
            current = self._ensure_scope(connection, scope, now)
            if external_high_water_token < int(current["high_water_token"]):
                raise CoordinatorAuthorityConflictError("external Provider token floor is below the restored Coordinator value")
            if external_operation_sequence < int(current["latest_operation_sequence"]):
                raise CoordinatorAuthorityConflictError("external Provider sequence floor is below the restored Coordinator value")
            connection.execute(
                """UPDATE coordinator_authority_operations
                   SET state='RECOVERY_REVIEW',updated_at=?
                   WHERE scope=? AND state IN (
                     'PENDING_ACTIVATION','REVOKING','PENDING_PUBLISH'
                   )""",
                (now, scope),
            )
            connection.execute(
                """UPDATE coordinator_authority_scopes SET
                    high_water_token=?,latest_operation_sequence=?,lease_id=NULL,owner_id=NULL,
                    tenant_id=NULL,domain=NULL,lease_expires_at=NULL,lease_state='RECOVERY_REQUIRED',
                    provider_generation=NULL,updated_at=? WHERE scope=?""",
                (external_high_water_token, external_operation_sequence, now, scope),
            )
            return {
                "scope": scope,
                "high_water_token": external_high_water_token,
                "latest_operation_sequence": external_operation_sequence,
                "lease_state": "RECOVERY_REQUIRED",
                "reconciliation_ref": reconciliation_ref,
                "automatic_cutover": False,
            }

    def snapshot(self, scope: str) -> dict[str, Any]:
        scope = _scope(scope)
        try:
            connection = self._connect()
            try:
                row = connection.execute(
                    "SELECT * FROM coordinator_authority_scopes WHERE scope=?", (scope,)
                ).fetchone()
                if row is None:
                    return {
                        "scope": scope, "high_water_token": 0, "lease_state": "IDLE",
                        "latest_operation_sequence": 0, "provider_generation": None,
                    }
                return dict(row)
            finally:
                connection.close()
        except sqlite3.Error as exc:
            raise CoordinatorAuthorityUnavailableError("Coordinator authority snapshot failed") from exc


def sign_distributed_fencing_proof(
    authority: SQLiteDurableCoordinatorAuthority,
    leadership: CoordinatorLeadershipLease,
    operation: DurableAuthorityOperation,
    lease: Any,
    *,
    issuer_id: str,
    signer: Any,
    ttl_seconds: float = 15.0,
    clock_fn: Callable[[], float] = time.time,
) -> str:
    """Sign an Ed25519 proof after the operation allocation is durably committed."""
    if not isinstance(authority, SQLiteDurableCoordinatorAuthority):
        raise CoordinatorAuthorityError("a durable SQLite Coordinator authority is required")
    if not isinstance(operation, DurableAuthorityOperation):
        raise CoordinatorAuthorityError("a durable Coordinator operation is required")
    authority.authorize_operation_signing(leadership, operation)
    if getattr(signer, "algorithm", None) != "ED25519" or not callable(getattr(signer, "sign", None)):
        raise CoordinatorAuthorityError("distributed fencing requires an Ed25519 signer")
    key_id = _required_text(getattr(signer, "key_id", None), "signing key ID", maximum=64)
    issuer = _required_text(issuer_id, "proof issuer ID", maximum=128)
    values = _lease_values(lease)
    if (
        values["lease_id"] != operation.lease_id
        or values["owner_id"] != operation.owner_id
        or values["tenant_id"] != operation.tenant_id
        or values["domain"] != operation.domain
    ):
        raise CoordinatorAuthorityConflictError("proof lease identity differs from the durable operation")
    if not isinstance(ttl_seconds, (int, float)) or isinstance(ttl_seconds, bool) or not math.isfinite(ttl_seconds) or not 0 < ttl_seconds <= 60:
        raise CoordinatorAuthorityError("proof TTL must be in (0, 60] seconds")
    now = _timestamp(clock_fn(), "current time")
    expires_at = min(operation.lease_expires_at, now + float(ttl_seconds))
    if expires_at <= now:
        raise CoordinatorAuthorityConflictError("cannot sign an expired Coordinator operation")
    expected_states = {
        "ACTIVATE": "PENDING_ACTIVATION",
        "REVOKE": "REVOKING",
        "PUBLISH": "PENDING_PUBLISH",
    }
    if operation.state != expected_states.get(operation.kind):
        raise CoordinatorAuthorityConflictError("only pending distributed fencing operations can be signed")
    operation_names = {
        "ACTIVATE": "fencing:activate",
        "REVOKE": "fencing:revoke",
        "PUBLISH": "fencing:publish",
    }
    claims: dict[str, Any] = {
        "v": 2,
        "alg": "ED25519",
        "iss": issuer,
        "kid": key_id,
        "lease_id": operation.lease_id,
        "owner_id": operation.owner_id,
        "tenant_id": operation.tenant_id,
        "domain": operation.domain,
        "fencing_token": operation.fencing_token,
        "issued_at": now,
        "expires_at": expires_at,
        "lease_expires_at": operation.lease_expires_at,
        "fencing_scope": operation.scope,
        "resource_key": operation.scope,
        "operation": operation_names[operation.kind],
        "idempotency_key": operation.idempotency_key,
    }
    if operation.kind == "PUBLISH":
        if operation.operation_sequence is None or operation.manifest_key is None or operation.manifest_sha256 is None:
            raise CoordinatorAuthorityError("publish allocation is missing its durable sequence or manifest binding")
        claims.update({
            "operation_sequence": operation.operation_sequence,
            "manifest_key": operation.manifest_key,
            "manifest_sha256": operation.manifest_sha256,
        })
    return create_fencing_attestation_ed25519(claims, signer=signer)
