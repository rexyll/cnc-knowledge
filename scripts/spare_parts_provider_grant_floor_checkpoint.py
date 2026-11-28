#!/usr/bin/env python3
"""Checkpoint guard for the local SQLite Provider Grant Floor reference.

The checkpoint store MUST live outside the SQLite database and its backup
domain. The included in-memory implementation is test-only: it demonstrates
the protocol contract but is neither durable nor production anti-rollback
storage. A production implementation needs an independently managed,
linearizable monotonic CAS authority (preferably one transaction domain for
the floor records and checkpoint).
"""
from __future__ import annotations

import base64
import hashlib
import json
import math
import sqlite3
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from scripts.spare_parts_provider_grant_floor import (
    ProviderGrantFloorSnapshot,
    ProviderGrantFloorReservation,
    ProviderGrantFloorOperation,
    ProviderGrantScopeKey,
    SQLiteProviderGrantFloorAuthority,
)

_REQUIRED_TABLES = {
    "provider_grant_floor_meta",
    "provider_grant_floor_scopes",
    "provider_grant_floor_operations",
    "provider_grant_floor_receipt_keys",
    "provider_grant_floor_coordinator_keys",
}
_DIGEST_LENGTH = 64


class ProviderGrantFloorCheckpointError(RuntimeError):
    """Base error for external checkpoint validation and update failures."""


class ProviderGrantFloorCheckpointMissing(ProviderGrantFloorCheckpointError):
    """No external checkpoint has been explicitly bootstrapped."""


class ProviderGrantFloorCheckpointMismatch(ProviderGrantFloorCheckpointError):
    """The SQLite Floor state does not exactly match its external checkpoint."""


class ProviderGrantFloorCheckpointConflict(ProviderGrantFloorCheckpointError):
    """The external checkpoint CAS did not match its expected sequence."""


class ProviderGrantFloorCheckpointUncertain(ProviderGrantFloorCheckpointError):
    """A checkpoint update outcome could not be proven by an exact read-back."""


class ProviderGrantFloorCheckpointBootstrapDenied(ProviderGrantFloorCheckpointError):
    """Bootstrap was attempted for a non-empty or previously used Floor."""


@dataclass(frozen=True)
class ProviderGrantFloorCheckpoint:
    sequence: int
    authority_revision: int
    state_sha256: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.sequence, int)
            or isinstance(self.sequence, bool)
            or self.sequence < 1
        ):
            raise ProviderGrantFloorCheckpointError("checkpoint sequence must be a positive integer")
        if (
            not isinstance(self.authority_revision, int)
            or isinstance(self.authority_revision, bool)
            or self.authority_revision < 0
        ):
            raise ProviderGrantFloorCheckpointError("authority revision must be a non-negative integer")
        if (
            not isinstance(self.state_sha256, str)
            or len(self.state_sha256) != _DIGEST_LENGTH
            or any(ch not in "0123456789abcdef" for ch in self.state_sha256)
        ):
            raise ProviderGrantFloorCheckpointError("state digest must be lowercase SHA-256 hex")


@dataclass(frozen=True)
class ProviderGrantFloorCheckpointState:
    authority_revision: int
    state_sha256: str


class ProviderGrantFloorCheckpointStore(Protocol):
    """Independent monotonic CAS store; never persist this beside the Floor DB."""

    def read_checkpoint(self) -> ProviderGrantFloorCheckpoint | None:
        ...

    def compare_and_set(
        self,
        *,
        expected_sequence: int | None,
        authority_revision: int,
        state_sha256: str,
    ) -> ProviderGrantFloorCheckpoint:
        ...


class InMemoryProviderGrantFloorCheckpointStore:
    """Test-only monotonic CAS fake. State disappears when the process exits."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._checkpoint: ProviderGrantFloorCheckpoint | None = None

    def read_checkpoint(self) -> ProviderGrantFloorCheckpoint | None:
        with self._lock:
            return self._checkpoint

    def compare_and_set(
        self,
        *,
        expected_sequence: int | None,
        authority_revision: int,
        state_sha256: str,
    ) -> ProviderGrantFloorCheckpoint:
        with self._lock:
            current = self._checkpoint
            actual_sequence = current.sequence if current is not None else None
            if actual_sequence != expected_sequence:
                raise ProviderGrantFloorCheckpointConflict(
                    "external checkpoint sequence CAS failed"
                )
            if (
                not isinstance(authority_revision, int)
                or isinstance(authority_revision, bool)
                or authority_revision < 0
            ):
                raise ProviderGrantFloorCheckpointError("authority revision must be non-negative")
            candidate = ProviderGrantFloorCheckpoint(
                sequence=1 if current is None else current.sequence + 1,
                authority_revision=authority_revision,
                state_sha256=state_sha256,
            )
            if current is not None and candidate.authority_revision < current.authority_revision:
                raise ProviderGrantFloorCheckpointConflict(
                    "external authority revision cannot move backwards"
                )
            self._checkpoint = candidate
            return candidate


def _sqlite_value(value: object) -> object:
    if value is None or isinstance(value, (str, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ProviderGrantFloorCheckpointError(
                "Floor database contains a non-finite numeric value"
            )
        return {"$float_hex": value.hex()}
    if isinstance(value, bytes):
        return {"$base64": base64.b64encode(value).decode("ascii")}
    raise ProviderGrantFloorCheckpointError(
        f"unsupported SQLite value in checkpoint digest: {type(value).__name__}"
    )


def _canonical_json(value: object) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ProviderGrantFloorCheckpointError(
            "Floor state cannot be deterministically serialized"
        ) from exc


def calculate_floor_checkpoint_state(
    authority: SQLiteProviderGrantFloorAuthority,
) -> ProviderGrantFloorCheckpointState:
    """Hash every logical Floor table and its schema using a read-only snapshot.

    This intentionally favors auditability over throughput and is suitable only
    for the local reference. A production multi-host authority should keep its
    state and monotonic checkpoint in one linearizable transaction domain.
    """
    if not isinstance(authority, SQLiteProviderGrantFloorAuthority):
        raise ProviderGrantFloorCheckpointError(
            "checkpoint state calculation requires SQLiteProviderGrantFloorAuthority"
        )
    database_path = Path(authority.database_path).resolve()
    uri = database_path.as_uri() + "?mode=ro"
    try:
        connection = sqlite3.connect(uri, uri=True, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only=ON")
        connection.execute("BEGIN")
        integrity = connection.execute("PRAGMA integrity_check").fetchone()
        if integrity is None or integrity[0] != "ok":
            raise ProviderGrantFloorCheckpointError("Floor SQLite integrity check failed")

        objects = [
            {
                "type": row["type"],
                "name": row["name"],
                "table_name": row["tbl_name"],
                "sql": row["sql"],
            }
            for row in connection.execute(
                """SELECT type,name,tbl_name,sql FROM sqlite_master
                   WHERE name NOT LIKE 'sqlite_%'
                   ORDER BY type,name"""
            )
        ]
        table_names = {
            row["name"] for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
        }
        if table_names != _REQUIRED_TABLES:
            raise ProviderGrantFloorCheckpointError(
                "Floor database schema contains missing or unexpected tables"
            )

        tables: list[dict[str, object]] = []
        for table_name in sorted(_REQUIRED_TABLES):
            quoted = '"' + table_name.replace('"', '""') + '"'
            columns = [
                {
                    "name": row["name"],
                    "type": row["type"],
                    "not_null": int(row["notnull"]),
                    "default": row["dflt_value"],
                    "primary_key": int(row["pk"]),
                }
                for row in connection.execute(f"PRAGMA table_info({quoted})")
            ]
            encoded_rows: list[bytes] = []
            for row in connection.execute(f"SELECT * FROM {quoted}"):
                encoded_rows.append(
                    _canonical_json([_sqlite_value(row[column["name"]]) for column in columns])
                )
            encoded_rows.sort()
            tables.append({
                "name": table_name,
                "columns": columns,
                "rows": [json.loads(item.decode("utf-8")) for item in encoded_rows],
            })

        meta_rows = tables[[item["name"] for item in tables].index(
            "provider_grant_floor_meta"
        )]["rows"]
        if len(meta_rows) != 1:
            raise ProviderGrantFloorCheckpointError("Floor metadata row is missing or duplicated")
        meta_columns = tables[[item["name"] for item in tables].index(
            "provider_grant_floor_meta"
        )]["columns"]
        column_names = [item["name"] for item in meta_columns]
        meta = dict(zip(column_names, meta_rows[0]))
        revision = meta.get("authority_revision")
        if (
            not isinstance(revision, int)
            or isinstance(revision, bool)
            or revision < 0
        ):
            raise ProviderGrantFloorCheckpointError("Floor authority revision is invalid")

        logical_state = {
            "schema_objects": objects,
            "tables": tables,
        }
        digest = hashlib.sha256(_canonical_json(logical_state)).hexdigest()
        connection.commit()
        return ProviderGrantFloorCheckpointState(
            authority_revision=revision,
            state_sha256=digest,
        )
    except ProviderGrantFloorCheckpointError:
        raise
    except (OSError, sqlite3.Error, ValueError, TypeError) as exc:
        raise ProviderGrantFloorCheckpointError(
            "could not calculate a consistent Floor checkpoint digest"
        ) from exc
    finally:
        if "connection" in locals():
            try:
                connection.rollback()
            finally:
                connection.close()


class CheckpointedSQLiteProviderGrantFloorAuthority:
    """Single-process guard that anchors every public Floor operation.

    Construct exactly one wrapper for a given SQLite Floor path in a process,
    and do not access the wrapped authority directly while the guard is active.
    This is not a cross-process lock or distributed transaction.
    """

    _READ_METHODS = {"snapshot", "operation_status"}
    _WRITE_METHODS = {
        "reserve_fence",
        "reserve_activate",
        "reserve_fence_from_command",
        "reserve_activate_from_command",
        "confirm_provider_receipt",
        "admin_register_provider_receipt_key",
        "admin_set_provider_receipt_key_status",
        "admin_register_coordinator_command_key",
        "admin_set_coordinator_command_key_status",
    }

    def __init__(
        self,
        authority: SQLiteProviderGrantFloorAuthority,
        checkpoint_store: ProviderGrantFloorCheckpointStore,
    ) -> None:
        if not isinstance(authority, SQLiteProviderGrantFloorAuthority):
            raise ProviderGrantFloorCheckpointError(
                "a SQLite Provider Grant Floor authority is required"
            )
        if not callable(getattr(checkpoint_store, "read_checkpoint", None)) or not callable(
            getattr(checkpoint_store, "compare_and_set", None)
        ):
            raise ProviderGrantFloorCheckpointError(
                "checkpoint store must provide read_checkpoint and compare_and_set"
            )
        self._authority = authority
        self._checkpoint_store = checkpoint_store
        self._lock = threading.RLock()

    def __getattr__(self, name: str):
        if name.startswith("_"):
            raise AttributeError(name)
        return getattr(self._authority, name)

    def _read_checkpoint_state(self) -> tuple[
        ProviderGrantFloorCheckpoint | None, ProviderGrantFloorCheckpointState
    ]:
        try:
            checkpoint = self._checkpoint_store.read_checkpoint()
        except Exception as exc:
            raise ProviderGrantFloorCheckpointUncertain(
                "external checkpoint read failed"
            ) from exc
        if checkpoint is not None and not isinstance(
            checkpoint, ProviderGrantFloorCheckpoint
        ):
            raise ProviderGrantFloorCheckpointError(
                "external checkpoint store returned an invalid record"
            )
        return checkpoint, calculate_floor_checkpoint_state(self._authority)

    def _assert_anchored(self) -> tuple[
        ProviderGrantFloorCheckpoint, ProviderGrantFloorCheckpointState
    ]:
        checkpoint, state = self._read_checkpoint_state()
        if checkpoint is None:
            raise ProviderGrantFloorCheckpointMissing(
                "Floor has no external checkpoint; explicit empty-database bootstrap is required"
            )
        if (
            checkpoint.authority_revision != state.authority_revision
            or checkpoint.state_sha256 != state.state_sha256
        ):
            raise ProviderGrantFloorCheckpointMismatch(
                "Floor state does not match the independent monotonic checkpoint"
            )
        return checkpoint, state

    def _is_pristine(self, state: ProviderGrantFloorCheckpointState) -> bool:
        if state.authority_revision != 0:
            return False
        connection = sqlite3.connect(
            Path(self._authority.database_path).resolve().as_uri() + "?mode=ro",
            uri=True,
        )
        try:
            connection.execute("PRAGMA query_only=ON")
            for table in (
                "provider_grant_floor_scopes",
                "provider_grant_floor_operations",
                "provider_grant_floor_receipt_keys",
                "provider_grant_floor_coordinator_keys",
            ):
                count = connection.execute(
                    'SELECT COUNT(*) FROM "' + table + '"'
                ).fetchone()[0]
                if count != 0:
                    return False
            meta = connection.execute(
                """SELECT authority_revision,trust_revision,
                          coordinator_command_auth_required
                   FROM provider_grant_floor_meta WHERE singleton=1"""
            ).fetchone()
            return bool(
                meta is not None
                and meta[0] == 0
                and meta[1] == 0
                and meta[2] == 1
            )
        finally:
            connection.close()

    def bootstrap_empty_floor(self) -> ProviderGrantFloorCheckpoint:
        """Explicitly anchor a pristine new Floor; never adopt existing history."""
        with self._lock:
            try:
                existing = self._checkpoint_store.read_checkpoint()
            except Exception as exc:
                raise ProviderGrantFloorCheckpointUncertain(
                    "cannot establish whether an external checkpoint already exists"
                ) from exc
            if existing is not None:
                raise ProviderGrantFloorCheckpointConflict(
                    "an external Floor checkpoint already exists"
                )
            state = calculate_floor_checkpoint_state(self._authority)
            if not self._is_pristine(state):
                raise ProviderGrantFloorCheckpointBootstrapDenied(
                    "only a completely empty strict Floor database may be bootstrapped"
                )
            expected = ProviderGrantFloorCheckpoint(
                sequence=1,
                authority_revision=state.authority_revision,
                state_sha256=state.state_sha256,
            )
            try:
                checkpoint = self._checkpoint_store.compare_and_set(
                    expected_sequence=None,
                    authority_revision=state.authority_revision,
                    state_sha256=state.state_sha256,
                )
            except Exception as exc:
                return self._confirm_checkpoint_readback(
                    expected,
                    "empty Floor bootstrap checkpoint outcome is unknown",
                    cause=exc,
                )
            if checkpoint != expected:
                return self._confirm_checkpoint_readback(
                    expected,
                    "empty Floor bootstrap returned an unexpected checkpoint",
                )
            return checkpoint

    def _confirm_checkpoint_readback(
        self,
        expected: ProviderGrantFloorCheckpoint,
        message: str,
        *,
        cause: Exception | None = None,
    ) -> ProviderGrantFloorCheckpoint:
        try:
            observed = self._checkpoint_store.read_checkpoint()
        except Exception as read_exc:
            raise ProviderGrantFloorCheckpointUncertain(message) from read_exc
        if observed == expected:
            return observed
        error = ProviderGrantFloorCheckpointUncertain(message)
        if cause is not None:
            raise error from cause
        raise error

    def verify_checkpoint(self) -> ProviderGrantFloorCheckpoint:
        with self._lock:
            checkpoint, _ = self._assert_anchored()
            return checkpoint

    def _advance_checkpoint(
        self,
        previous: ProviderGrantFloorCheckpoint,
        state: ProviderGrantFloorCheckpointState,
    ) -> ProviderGrantFloorCheckpoint:
        expected = ProviderGrantFloorCheckpoint(
            sequence=previous.sequence + 1,
            authority_revision=state.authority_revision,
            state_sha256=state.state_sha256,
        )
        try:
            actual = self._checkpoint_store.compare_and_set(
                expected_sequence=previous.sequence,
                authority_revision=state.authority_revision,
                state_sha256=state.state_sha256,
            )
        except Exception as exc:
            return self._confirm_checkpoint_readback(
                expected,
                "Floor mutation committed but external checkpoint advance is unconfirmed",
                cause=exc,
            )
        if actual != expected:
            return self._confirm_checkpoint_readback(
                expected,
                "checkpoint store returned an unexpected checkpoint after Floor mutation",
            )
        return actual

    def _run_read(self, method_name: str, *args, **kwargs):
        with self._lock:
            self._assert_anchored()
            result = getattr(self._authority, method_name)(*args, **kwargs)
            self._assert_anchored()
            return result

    def _run_write(self, method_name: str, *args, **kwargs):
        with self._lock:
            previous, before = self._assert_anchored()
            method = getattr(self._authority, method_name)
            try:
                result = method(*args, **kwargs)
            except Exception as exc:
                try:
                    after = calculate_floor_checkpoint_state(self._authority)
                except Exception as digest_exc:
                    raise ProviderGrantFloorCheckpointUncertain(
                        "Floor write outcome is unknown and its state cannot be checked"
                    ) from digest_exc
                if after != before:
                    raise ProviderGrantFloorCheckpointUncertain(
                        "Floor write raised after changing durable state; checkpoint was not advanced"
                    ) from exc
                raise
            try:
                after = calculate_floor_checkpoint_state(self._authority)
            except Exception as exc:
                raise ProviderGrantFloorCheckpointUncertain(
                    "Floor mutation committed but its resulting state digest is unavailable"
                ) from exc
            if after != before:
                self._advance_checkpoint(previous, after)
            self._assert_anchored()
            return result

    def snapshot(
        self, key: ProviderGrantScopeKey, *, minimum_revision: int | None = None
    ) -> ProviderGrantFloorSnapshot:
        return self._run_read("snapshot", key, minimum_revision=minimum_revision)

    def operation_status(self, operation_id: str) -> ProviderGrantFloorOperation | None:
        return self._run_read("operation_status", operation_id)

    def reserve_fence(self, **kwargs) -> ProviderGrantFloorReservation:
        return self._run_write("reserve_fence", **kwargs)

    def reserve_activate(self, **kwargs) -> ProviderGrantFloorReservation:
        return self._run_write("reserve_activate", **kwargs)

    def reserve_fence_from_command(self, **kwargs) -> ProviderGrantFloorReservation:
        return self._run_write("reserve_fence_from_command", **kwargs)

    def reserve_activate_from_command(self, **kwargs) -> ProviderGrantFloorReservation:
        return self._run_write("reserve_activate_from_command", **kwargs)

    def confirm_provider_receipt(self, **kwargs) -> ProviderGrantFloorSnapshot:
        return self._run_write("confirm_provider_receipt", **kwargs)

    def admin_register_provider_receipt_key(self, **kwargs):
        return self._run_write("admin_register_provider_receipt_key", **kwargs)

    def admin_set_provider_receipt_key_status(self, **kwargs):
        return self._run_write("admin_set_provider_receipt_key_status", **kwargs)

    def admin_register_coordinator_command_key(self, **kwargs):
        return self._run_write("admin_register_coordinator_command_key", **kwargs)

    def admin_set_coordinator_command_key_status(self, **kwargs):
        return self._run_write("admin_set_coordinator_command_key_status", **kwargs)
