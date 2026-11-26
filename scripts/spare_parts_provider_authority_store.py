#!/usr/bin/env python3
"""Backend-neutral transactional store contract for Coordinator authority.

SQLite and etcd adapters implement the same minimal KV/transaction/lease port.
The in-memory etcd client near the end is a deterministic contract-test double,
not an etcd server and never evidence of multi-host consensus.
"""
from __future__ import annotations

import os
import sqlite3
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator, Mapping, Protocol, Sequence, runtime_checkable


class AuthorityStoreError(RuntimeError):
    """Base class for Coordinator authority store errors."""


class AuthorityStoreUnavailableError(AuthorityStoreError):
    """A read or known-uncommitted request cannot reach the backend."""


class AuthorityStoreOutcomeUnknownError(AuthorityStoreError):
    """A mutating RPC may have committed; reconcile by idempotency/read-back."""


class AuthorityStoreConflictError(AuthorityStoreError):
    """A conditional transaction did not satisfy the expected state."""


class AuthorityStoreLeaseError(AuthorityStoreError):
    """A referenced backend lease does not exist or is no longer valid."""


@dataclass(frozen=True)
class AuthorityStoreEntry:
    key: bytes
    value: bytes
    create_revision: int
    mod_revision: int
    version: int
    lease_id: int = 0


@dataclass(frozen=True)
class AuthorityStoreCompare:
    key: bytes
    target: str
    result: str
    expected: bytes | int

    def __post_init__(self) -> None:
        if not isinstance(self.key, bytes) or not self.key:
            raise ValueError("compare key must be non-empty bytes")
        if self.target not in {"VERSION", "CREATE", "MOD", "VALUE"}:
            raise ValueError("compare target must be VERSION, CREATE, MOD or VALUE")
        if self.result not in {"EQUAL", "NOT_EQUAL", "GREATER", "LESS"}:
            raise ValueError("compare result is invalid")
        if self.target == "VALUE":
            if not isinstance(self.expected, bytes):
                raise ValueError("VALUE compare requires bytes")
        elif not isinstance(self.expected, int) or isinstance(self.expected, bool) or self.expected < 0:
            raise ValueError("revision/version compare requires a non-negative integer")


@dataclass(frozen=True)
class AuthorityStorePut:
    key: bytes
    value: bytes
    lease_id: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.key, bytes) or not self.key:
            raise ValueError("put key must be non-empty bytes")
        if not isinstance(self.value, bytes):
            raise ValueError("put value must be bytes")
        if not isinstance(self.lease_id, int) or isinstance(self.lease_id, bool) or self.lease_id < 0:
            raise ValueError("put lease_id must be a non-negative integer")


@dataclass(frozen=True)
class AuthorityStoreDelete:
    key: bytes

    def __post_init__(self) -> None:
        if not isinstance(self.key, bytes) or not self.key:
            raise ValueError("delete key must be non-empty bytes")


AuthorityStoreMutation = AuthorityStorePut | AuthorityStoreDelete


@dataclass(frozen=True)
class AuthorityStoreGet:
    """Read one exact key inside the selected atomic transaction branch."""

    key: bytes

    def __post_init__(self) -> None:
        if not isinstance(self.key, bytes) or not self.key:
            raise ValueError("transaction get key must be non-empty bytes")


AuthorityStoreTxnOperation = AuthorityStoreMutation | AuthorityStoreGet


@dataclass(frozen=True)
class AuthorityStoreTxnResult:
    succeeded: bool
    revision: int
    reads: tuple[AuthorityStoreEntry | None, ...] = ()


@dataclass(frozen=True)
class AuthorityStoreLease:
    lease_id: int
    ttl_seconds: int


@dataclass(frozen=True)
class AuthorityStoreRangeResult:
    entries: tuple[AuthorityStoreEntry, ...]
    revision: int


@dataclass(frozen=True)
class AuthorityStoreWatchEvent:
    event_type: str
    key: bytes
    revision: int
    entry: AuthorityStoreEntry | None = None
    previous_entry: AuthorityStoreEntry | None = None


@dataclass(frozen=True)
class AuthorityStoreWatchResponse:
    watch_id: int
    header_revision: int
    created: bool = False
    canceled: bool = False
    compact_revision: int = 0
    cancel_reason: str = ""
    fragment: bool = False
    events: tuple[AuthorityStoreWatchEvent, ...] = ()

    @property
    def is_progress(self) -> bool:
        return not self.created and not self.canceled and not self.events

    @property
    def resume_revision(self) -> int | None:
        """Inclusive revision for a safe new watch after this complete response.

        A canceled/compacted watch needs a fresh linearizable rebuild; a
        fragment must not advance the cursor until its final fragment arrives.
        """
        if self.canceled or self.fragment or self.created:
            return None
        return self.header_revision + 1


@runtime_checkable
class CoordinatorAuthorityWatchStore(Protocol):
    """Optional watch capability; Watch is a wake-up hint, never authority."""

    def watch(
        self,
        key: bytes,
        *,
        start_revision: int = 0,
        range_end: bytes | None = None,
        progress_notify: bool = True,
        prev_kv: bool = True,
    ) -> Iterator[AuthorityStoreWatchResponse]: ...


@runtime_checkable
class CoordinatorAuthorityStore(Protocol):
    """Minimal port required by a distributed Coordinator state machine.

    linearizable_get MUST return a value at least as recent as every completed
    write before the read began. transact MUST atomically evaluate all compares
    and execute exactly one branch. A mutating timeout MUST be surfaced as
    AuthorityStoreOutcomeUnknownError, never silently retried with new identity.
    """

    def linearizable_get(self, key: bytes) -> tuple[AuthorityStoreEntry | None, int]: ...

    def transact(
        self,
        compares: Sequence[AuthorityStoreCompare],
        success: Sequence[AuthorityStoreTxnOperation],
        failure: Sequence[AuthorityStoreTxnOperation] = (),
    ) -> AuthorityStoreTxnResult: ...

    def lease_grant(self, ttl_seconds: int) -> AuthorityStoreLease: ...

    def lease_keepalive(self, lease_id: int) -> AuthorityStoreLease: ...

    def lease_revoke(self, lease_id: int) -> None: ...


@runtime_checkable
class DurableCoordinatorAuthorityBackend(Protocol):
    """Application-facing port implemented by the current SQLite authority service.

    This service contract is intentionally separate from CoordinatorAuthorityStore,
    the transactional KV primitive. The current service still uses SQLite SQL
    internally; a future refactor must move its state transitions onto the
    primitive store before an etcd deployment can claim service-level parity.
    """

    def claim_leadership(self, *args: Any, **kwargs: Any) -> Any: ...
    def renew_leadership(self, *args: Any, **kwargs: Any) -> Any: ...
    def prepare_activation(self, *args: Any, **kwargs: Any) -> Any: ...
    def confirm_activation(self, *args: Any, **kwargs: Any) -> Any: ...
    def prepare_revocation(self, *args: Any, **kwargs: Any) -> Any: ...
    def confirm_revocation(self, *args: Any, **kwargs: Any) -> Any: ...
    def allocate_operation_sequence(self, *args: Any, **kwargs: Any) -> Any: ...
    def confirm_publish(self, *args: Any, **kwargs: Any) -> Any: ...
    def authorize_operation_signing(self, *args: Any, **kwargs: Any) -> Any: ...
    def list_pending_operations(self, *args: Any, **kwargs: Any) -> Any: ...
    def reconcile_after_restore(self, *args: Any, **kwargs: Any) -> Any: ...


@runtime_checkable
class EtcdV3Client(Protocol):
    """Normalized client-driver port.

    A concrete driver may use etcd's gRPC API or its gRPC-JSON gateway. It must
    return snake_case response fields and bytes for keys/values, use a
    linearizable Range when serializable=False, and expose the transaction and
    Lease RPCs without weakening their consistency semantics. Watch is an
    optional extension so existing non-watching drivers remain constructible.
    """

    def range(
        self,
        key: bytes,
        *,
        range_end: bytes | None = None,
        serializable: bool = False,
    ) -> Mapping[str, Any]: ...

    def txn(
        self,
        *,
        compare: Sequence[Mapping[str, Any]],
        success: Sequence[Mapping[str, Any]],
        failure: Sequence[Mapping[str, Any]],
    ) -> Mapping[str, Any]: ...

    def lease_grant(self, ttl_seconds: int) -> Mapping[str, Any]: ...

    def lease_keepalive(self, lease_id: int) -> Mapping[str, Any]: ...

    def lease_revoke(self, lease_id: int) -> Mapping[str, Any]: ...


@runtime_checkable
class EtcdV3WatchClient(Protocol):
    """Optional normalized bidirectional Watch stream driver."""

    def watch(
        self,
        key: bytes,
        *,
        start_revision: int = 0,
        range_end: bytes | None = None,
        progress_notify: bool = True,
        prev_kv: bool = True,
    ) -> Iterable[Mapping[str, Any]]: ...

    def watch_progress(self, watch_id: int) -> None: ...


def _watch_kv_entry(kv: Mapping[str, Any]) -> AuthorityStoreEntry:
    return AuthorityStoreEntry(
        key=bytes(kv["key"]),
        value=bytes(kv.get("value", b"")),
        create_revision=int(kv.get("create_revision", 0)),
        mod_revision=int(kv.get("mod_revision", 0)),
        version=int(kv.get("version", 0)),
        lease_id=int(kv.get("lease", 0)),
    )


def _validate_mutations(
    success: Sequence[AuthorityStoreTxnOperation],
    failure: Sequence[AuthorityStoreTxnOperation],
) -> None:
    for branch in (success, failure):
        mutated_keys: set[bytes] = set()
        for op in branch:
            if isinstance(op, AuthorityStoreGet):
                continue
            if not isinstance(op, (AuthorityStorePut, AuthorityStoreDelete)):
                raise ValueError("transaction branch contains an unsupported operation")
            if op.key in mutated_keys:
                raise ValueError("a transaction branch may mutate each key at most once")
            mutated_keys.add(op.key)


def _compare_value(actual: bytes | int, expected: bytes | int, operator: str) -> bool:
    if operator == "EQUAL":
        return actual == expected
    if operator == "NOT_EQUAL":
        return actual != expected
    if operator == "GREATER":
        return actual > expected
    return actual < expected


class SQLiteCoordinatorAuthorityStore:
    """Same-host SQLite WAL implementation of CoordinatorAuthorityStore.

    This adapter is for local development and conformance tests. SQLite WAL is
    not a shared multi-host coordination backend and must not be placed on NFS
    or SMB.
    """

    def __init__(
        self,
        database_path: str | os.PathLike[str],
        *,
        clock_fn: Callable[[], float] = time.time,
        busy_timeout_seconds: float = 5.0,
    ):
        if not isinstance(database_path, (str, os.PathLike)) or not str(database_path).strip():
            raise ValueError("SQLite authority store path is required")
        if str(database_path) == ":memory:":
            raise ValueError("SQLite authority store requires a persistent file")
        if not isinstance(busy_timeout_seconds, (int, float)) or busy_timeout_seconds <= 0:
            raise ValueError("busy timeout must be positive")
        self.database_path = Path(database_path).expanduser().resolve()
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.clock_fn = clock_fn
        self.busy_timeout_seconds = float(busy_timeout_seconds)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        c = sqlite3.connect(
            str(self.database_path),
            timeout=self.busy_timeout_seconds,
            isolation_level=None,
        )
        c.row_factory = sqlite3.Row
        c.execute(f"PRAGMA busy_timeout={int(self.busy_timeout_seconds * 1000)}")
        c.execute("PRAGMA foreign_keys=ON")
        c.execute("PRAGMA synchronous=FULL")
        return c

    def _initialize(self) -> None:
        try:
            c = self._connect()
            try:
                mode = c.execute("PRAGMA journal_mode=WAL").fetchone()[0]
                if str(mode).lower() != "wal":
                    raise sqlite3.OperationalError("SQLite authority store did not enter WAL mode")
                c.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS authority_store_meta (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS authority_store_kv (
                        key BLOB PRIMARY KEY,
                        value BLOB NOT NULL,
                        create_revision INTEGER NOT NULL,
                        mod_revision INTEGER NOT NULL,
                        version INTEGER NOT NULL,
                        lease_id INTEGER NOT NULL DEFAULT 0
                    );
                    CREATE TABLE IF NOT EXISTS authority_store_leases (
                        lease_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        ttl_seconds INTEGER NOT NULL,
                        expires_at REAL NOT NULL
                    );
                    INSERT OR IGNORE INTO authority_store_meta(key,value)
                        VALUES('revision','0');
                    """
                )
            finally:
                c.close()
        except sqlite3.Error as exc:
            raise AuthorityStoreUnavailableError("cannot initialize SQLite authority store") from exc

    def _expire_leases(self, c: sqlite3.Connection) -> None:
        now = self.clock_fn()
        expired = [
            int(row["lease_id"])
            for row in c.execute(
                "SELECT lease_id FROM authority_store_leases WHERE expires_at<=?", (now,)
            ).fetchall()
        ]
        if not expired:
            return
        marks = ",".join("?" for _ in expired)
        deleted = c.execute(
            f"DELETE FROM authority_store_kv WHERE lease_id IN ({marks})", expired
        ).rowcount
        c.execute(
            f"DELETE FROM authority_store_leases WHERE lease_id IN ({marks})", expired
        )
        if deleted:
            self._bump_revision(c)

    @staticmethod
    def _revision(c: sqlite3.Connection) -> int:
        return int(c.execute(
            "SELECT value FROM authority_store_meta WHERE key='revision'"
        ).fetchone()["value"])

    @staticmethod
    def _bump_revision(c: sqlite3.Connection) -> int:
        current = SQLiteCoordinatorAuthorityStore._revision(c) + 1
        c.execute(
            "UPDATE authority_store_meta SET value=? WHERE key='revision'", (str(current),)
        )
        return current

    @staticmethod
    def _entry(row: sqlite3.Row | None) -> AuthorityStoreEntry | None:
        if row is None:
            return None
        return AuthorityStoreEntry(
            key=bytes(row["key"]),
            value=bytes(row["value"]),
            create_revision=int(row["create_revision"]),
            mod_revision=int(row["mod_revision"]),
            version=int(row["version"]),
            lease_id=int(row["lease_id"]),
        )

    def linearizable_get(self, key: bytes) -> tuple[AuthorityStoreEntry | None, int]:
        if not isinstance(key, bytes) or not key:
            raise ValueError("key must be non-empty bytes")
        try:
            c = self._connect()
            try:
                c.execute("BEGIN IMMEDIATE")
                self._expire_leases(c)
                row = c.execute("SELECT * FROM authority_store_kv WHERE key=?", (key,)).fetchone()
                revision = self._revision(c)
                c.commit()
                return self._entry(row), revision
            finally:
                c.close()
        except sqlite3.Error as exc:
            raise AuthorityStoreUnavailableError("SQLite linearizable get failed") from exc

    def _compare(self, c: sqlite3.Connection, condition: AuthorityStoreCompare) -> bool:
        row = c.execute(
            "SELECT * FROM authority_store_kv WHERE key=?", (condition.key,)
        ).fetchone()
        if condition.target == "VERSION":
            actual: bytes | int = 0 if row is None else int(row["version"])
        elif condition.target == "CREATE":
            actual = 0 if row is None else int(row["create_revision"])
        elif condition.target == "MOD":
            actual = 0 if row is None else int(row["mod_revision"])
        else:
            actual = b"" if row is None else bytes(row["value"])
        return _compare_value(actual, condition.expected, condition.result)

    def _apply(self, c: sqlite3.Connection, operations: Sequence[AuthorityStoreMutation]) -> bool:
        changed = False
        for op in operations:
            if isinstance(op, AuthorityStorePut):
                if op.lease_id:
                    valid = c.execute(
                        "SELECT 1 FROM authority_store_leases WHERE lease_id=? AND expires_at>?",
                        (op.lease_id, self.clock_fn()),
                    ).fetchone()
                    if valid is None:
                        raise AuthorityStoreLeaseError("cannot attach key to an expired or unknown lease")
                old = c.execute(
                    "SELECT create_revision,version FROM authority_store_kv WHERE key=?", (op.key,)
                ).fetchone()
                # The actual revision is assigned once per complete transaction below.
                c.execute(
                    """INSERT INTO authority_store_kv(
                        key,value,create_revision,mod_revision,version,lease_id
                    ) VALUES(?,?,0,0,0,?)
                    ON CONFLICT(key) DO UPDATE SET value=excluded.value,lease_id=excluded.lease_id""",
                    (op.key, op.value, op.lease_id),
                )
                # Preserve the old creation/version facts until the transaction revision is known.
                if old is not None:
                    c.execute(
                        "UPDATE authority_store_kv SET create_revision=?,version=? WHERE key=?",
                        (int(old["create_revision"]), int(old["version"]), op.key),
                    )
                changed = True
            else:
                deleted = c.execute(
                    "DELETE FROM authority_store_kv WHERE key=?", (op.key,)
                ).rowcount
                changed = changed or bool(deleted)
        return changed

    def transact(
        self,
        compares: Sequence[AuthorityStoreCompare],
        success: Sequence[AuthorityStoreTxnOperation],
        failure: Sequence[AuthorityStoreTxnOperation] = (),
    ) -> AuthorityStoreTxnResult:
        if any(not isinstance(cmp, AuthorityStoreCompare) for cmp in compares):
            raise ValueError("compares must contain AuthorityStoreCompare values")
        _validate_mutations(success, failure)
        try:
            c = self._connect()
            try:
                c.execute("BEGIN IMMEDIATE")
                self._expire_leases(c)
                succeeded = all(self._compare(c, cmp) for cmp in compares)
                operations = success if succeeded else failure
                next_revision = self._revision(c) + 1
                changed = False
                reads: list[AuthorityStoreEntry | None] = []
                # Preserve operation order: a Get before a Put sees the old value,
                # while a Get after a Put sees the tentative value in this txn.
                for op in operations:
                    if isinstance(op, AuthorityStoreGet):
                        row = c.execute(
                            "SELECT * FROM authority_store_kv WHERE key=?", (op.key,)
                        ).fetchone()
                        reads.append(self._entry(row))
                    elif isinstance(op, AuthorityStorePut):
                        if op.lease_id:
                            valid = c.execute(
                                "SELECT 1 FROM authority_store_leases WHERE lease_id=? AND expires_at>?",
                                (op.lease_id, self.clock_fn()),
                            ).fetchone()
                            if valid is None:
                                raise AuthorityStoreLeaseError(
                                    "cannot attach key to an expired or unknown lease"
                                )
                        old = c.execute(
                            "SELECT create_revision,version FROM authority_store_kv WHERE key=?",
                            (op.key,),
                        ).fetchone()
                        create_revision = next_revision if old is None else int(old["create_revision"])
                        version = 1 if old is None else int(old["version"]) + 1
                        c.execute(
                            """INSERT INTO authority_store_kv(
                                key,value,create_revision,mod_revision,version,lease_id
                            ) VALUES(?,?,?,?,?,?)
                            ON CONFLICT(key) DO UPDATE SET
                                value=excluded.value,mod_revision=excluded.mod_revision,
                                version=excluded.version,lease_id=excluded.lease_id""",
                            (op.key, op.value, create_revision, next_revision, version, op.lease_id),
                        )
                        changed = True
                    else:
                        deleted = c.execute(
                            "DELETE FROM authority_store_kv WHERE key=?", (op.key,)
                        ).rowcount
                        changed = changed or bool(deleted)
                revision = self._bump_revision(c) if changed else self._revision(c)
                c.commit()
                return AuthorityStoreTxnResult(
                    succeeded=succeeded, revision=revision, reads=tuple(reads)
                )
            except AuthorityStoreError:
                c.rollback()
                raise
            finally:
                c.close()
        except sqlite3.Error as exc:
            raise AuthorityStoreUnavailableError("SQLite authority transaction failed") from exc

    def lease_grant(self, ttl_seconds: int) -> AuthorityStoreLease:
        if not isinstance(ttl_seconds, int) or isinstance(ttl_seconds, bool) or not 1 <= ttl_seconds <= 86400:
            raise ValueError("lease TTL must be in [1, 86400] seconds")
        try:
            c = self._connect()
            try:
                c.execute("BEGIN IMMEDIATE")
                self._expire_leases(c)
                cursor = c.execute(
                    "INSERT INTO authority_store_leases(ttl_seconds,expires_at) VALUES(?,?)",
                    (ttl_seconds, self.clock_fn() + ttl_seconds),
                )
                lease = AuthorityStoreLease(int(cursor.lastrowid), ttl_seconds)
                c.commit()
                return lease
            finally:
                c.close()
        except sqlite3.Error as exc:
            raise AuthorityStoreUnavailableError("SQLite lease grant failed") from exc

    def lease_keepalive(self, lease_id: int) -> AuthorityStoreLease:
        if not isinstance(lease_id, int) or isinstance(lease_id, bool) or lease_id < 1:
            raise ValueError("lease ID must be positive")
        try:
            c = self._connect()
            try:
                c.execute("BEGIN IMMEDIATE")
                self._expire_leases(c)
                row = c.execute(
                    "SELECT ttl_seconds FROM authority_store_leases WHERE lease_id=?",
                    (lease_id,),
                ).fetchone()
                if row is None:
                    raise AuthorityStoreLeaseError("lease is expired or unknown")
                ttl = int(row["ttl_seconds"])
                c.execute(
                    "UPDATE authority_store_leases SET expires_at=? WHERE lease_id=?",
                    (self.clock_fn() + ttl, lease_id),
                )
                c.commit()
                return AuthorityStoreLease(lease_id, ttl)
            except AuthorityStoreError:
                c.rollback()
                raise
            finally:
                c.close()
        except sqlite3.Error as exc:
            raise AuthorityStoreUnavailableError("SQLite lease keepalive failed") from exc

    def lease_revoke(self, lease_id: int) -> None:
        if not isinstance(lease_id, int) or isinstance(lease_id, bool) or lease_id < 1:
            raise ValueError("lease ID must be positive")
        try:
            c = self._connect()
            try:
                c.execute("BEGIN IMMEDIATE")
                self._expire_leases(c)
                deleted = c.execute(
                    "DELETE FROM authority_store_kv WHERE lease_id=?", (lease_id,)
                ).rowcount
                c.execute("DELETE FROM authority_store_leases WHERE lease_id=?", (lease_id,))
                if deleted:
                    self._bump_revision(c)
                c.commit()
            finally:
                c.close()
        except sqlite3.Error as exc:
            raise AuthorityStoreUnavailableError("SQLite lease revoke failed") from exc


class EtcdV3CoordinatorAuthorityStore:
    """Adapter from the store port to a normalized etcd v3 client driver.

    The injected client is responsible for mTLS/authentication, endpoint
    failover and actual gRPC or gRPC-JSON gateway transport. This class emits
    the etcd v3 KV Compare/Txn and Lease operations, but it does not construct
    a network client or claim that an etcd cluster is connected.
    """

    def __init__(self, client: EtcdV3Client):
        required = ("range", "txn", "lease_grant", "lease_keepalive", "lease_revoke")
        if any(not callable(getattr(client, name, None)) for name in required):
            raise ValueError("etcd v3 client does not implement the required KV/Txn/Lease methods")
        self.client = client

    def linearizable_get(self, key: bytes) -> tuple[AuthorityStoreEntry | None, int]:
        if not isinstance(key, bytes) or not key:
            raise ValueError("key must be non-empty bytes")
        try:
            response = self.client.range(key, serializable=False)
            header = response.get("header", {})
            revision = int(header.get("revision", 0))
            kvs = response.get("kvs") or []
            if not kvs:
                return None, revision
            if len(kvs) != 1:
                raise AuthorityStoreError("exact-key Range returned multiple records")
            kv = kvs[0]
            return AuthorityStoreEntry(
                key=bytes(kv["key"]),
                value=bytes(kv["value"]),
                create_revision=int(kv["create_revision"]),
                mod_revision=int(kv["mod_revision"]),
                version=int(kv["version"]),
                lease_id=int(kv.get("lease", 0)),
            ), revision
        except AuthorityStoreError:
            raise
        except (TimeoutError, ConnectionError) as exc:
            raise AuthorityStoreUnavailableError("etcd linearizable Range failed") from exc
        except Exception as exc:
            raise AuthorityStoreUnavailableError("etcd Range response is invalid or unavailable") from exc

    def linearizable_range(
        self, key: bytes, *, range_end: bytes | None = None
    ) -> AuthorityStoreRangeResult:
        if not isinstance(key, bytes) or not key:
            raise ValueError("range start key must be non-empty bytes")
        if range_end is not None and (
            not isinstance(range_end, bytes) or (range_end and range_end <= key)
        ):
            raise ValueError("range_end must be empty or lexicographically greater than key")
        try:
            response = self.client.range(
                key, range_end=range_end, serializable=False
            )
            header = response.get("header", {})
            revision = int(header.get("revision", 0))
            entries = tuple(
                AuthorityStoreEntry(
                    key=bytes(kv["key"]),
                    value=bytes(kv["value"]),
                    create_revision=int(kv["create_revision"]),
                    mod_revision=int(kv["mod_revision"]),
                    version=int(kv["version"]),
                    lease_id=int(kv.get("lease", 0)),
                )
                for kv in (response.get("kvs") or [])
            )
            if any(item.mod_revision > revision for item in entries):
                raise AuthorityStoreError("Range entry revision exceeds response header")
            return AuthorityStoreRangeResult(entries=entries, revision=revision)
        except AuthorityStoreError:
            raise
        except (TimeoutError, ConnectionError) as exc:
            raise AuthorityStoreUnavailableError(
                "etcd linearizable Range failed"
            ) from exc
        except Exception as exc:
            raise AuthorityStoreUnavailableError(
                "etcd Range response is invalid or unavailable"
            ) from exc

    def watch(
        self,
        key: bytes,
        *,
        start_revision: int = 0,
        range_end: bytes | None = None,
        progress_notify: bool = True,
        prev_kv: bool = True,
    ) -> Iterator[AuthorityStoreWatchResponse]:
        if not isinstance(key, bytes) or not key:
            raise ValueError("watch key must be non-empty bytes")
        if (
            not isinstance(start_revision, int)
            or isinstance(start_revision, bool)
            or start_revision < 0
        ):
            raise ValueError("watch start_revision must be a non-negative integer")
        if range_end is not None and (
            not isinstance(range_end, bytes) or (range_end and range_end <= key)
        ):
            raise ValueError("watch range_end must be empty or greater than key")
        driver_watch = getattr(self.client, "watch", None)
        if not callable(driver_watch):
            raise AuthorityStoreUnavailableError(
                "etcd client driver does not expose the optional Watch capability"
            )

        def stream() -> Iterator[AuthorityStoreWatchResponse]:
            raw_stream: Any = None
            try:
                raw_stream = driver_watch(
                    key,
                    start_revision=start_revision,
                    range_end=range_end,
                    progress_notify=progress_notify,
                    prev_kv=prev_kv,
                )
                for raw in raw_stream:
                    if not isinstance(raw, Mapping):
                        raise AuthorityStoreError("etcd Watch response is not a mapping")
                    header = raw.get("header", {})
                    revision = int(header.get("revision", 0))
                    if revision < 0:
                        raise AuthorityStoreError("etcd Watch response revision is invalid")
                    watch_id = int(raw.get("watch_id", 0))
                    events: list[AuthorityStoreWatchEvent] = []
                    for event in (raw.get("events") or []):
                        raw_type = event.get("type")
                        if raw_type in (0, "PUT", "put"):
                            event_type = "PUT"
                        elif raw_type in (1, "DELETE", "delete"):
                            event_type = "DELETE"
                        else:
                            raise AuthorityStoreError("etcd Watch event type is invalid")
                        kv = event.get("kv")
                        if not isinstance(kv, Mapping) or not kv.get("key"):
                            raise AuthorityStoreError("etcd Watch event KV is malformed")
                        entry = _watch_kv_entry(kv) if event_type == "PUT" else None
                        previous = event.get("prev_kv")
                        events.append(
                            AuthorityStoreWatchEvent(
                                event_type=event_type,
                                key=bytes(kv["key"]),
                                revision=int(kv.get("mod_revision", revision)),
                                entry=entry,
                                previous_entry=(
                                    _watch_kv_entry(previous)
                                    if isinstance(previous, Mapping) and previous.get("key")
                                    else None
                                ),
                            )
                        )
                    response = AuthorityStoreWatchResponse(
                        watch_id=watch_id,
                        header_revision=revision,
                        created=bool(raw.get("created", False)),
                        canceled=bool(raw.get("canceled", False)),
                        compact_revision=int(raw.get("compact_revision", 0)),
                        cancel_reason=str(raw.get("cancel_reason", "")),
                        fragment=bool(raw.get("fragment", False)),
                        events=tuple(events),
                    )
                    if response.canceled and response.compact_revision < 0:
                        raise AuthorityStoreError("Watch compact_revision is invalid")
                    yield response
                    if response.canceled:
                        return
            except AuthorityStoreError:
                raise
            except (TimeoutError, ConnectionError) as exc:
                raise AuthorityStoreUnavailableError(
                    "etcd Watch stream disconnected; rebuild from a linearizable Range"
                ) from exc
            except Exception as exc:
                raise AuthorityStoreUnavailableError(
                    "etcd Watch stream failed or returned an invalid response"
                ) from exc
            finally:
                close = getattr(raw_stream, "close", None)
                if callable(close):
                    close()

        return stream()

    def watch_progress(self, watch_id: int) -> None:
        request_progress = getattr(self.client, "watch_progress", None)
        if not callable(request_progress):
            raise AuthorityStoreUnavailableError(
                "etcd client driver does not expose WatchProgress"
            )
        try:
            request_progress(watch_id)
        except (TimeoutError, ConnectionError) as exc:
            raise AuthorityStoreUnavailableError(
                "etcd WatchProgress request failed"
            ) from exc

    @staticmethod
    def _compare_request(condition: AuthorityStoreCompare) -> dict[str, Any]:
        target_field = {
            "VERSION": "version",
            "CREATE": "create_revision",
            "MOD": "mod_revision",
            "VALUE": "value",
        }[condition.target]
        expected: int | bytes = condition.expected
        if isinstance(expected, bytes):
            return {
                "key": condition.key,
                "target": condition.target,
                "result": condition.result,
                target_field: expected,
            }
        return {
            "key": condition.key,
            "target": condition.target,
            "result": condition.result,
            target_field: str(expected),
        }

    @staticmethod
    def _txn_request(operation: AuthorityStoreTxnOperation) -> dict[str, Any]:
        if isinstance(operation, AuthorityStoreGet):
            return {"request_range": {"key": operation.key}}
        if isinstance(operation, AuthorityStorePut):
            request: dict[str, Any] = {
                "key": operation.key,
                "value": operation.value,
            }
            if operation.lease_id:
                request["lease"] = str(operation.lease_id)
            return {"request_put": request}
        return {"request_delete_range": {"key": operation.key}}

    @staticmethod
    def _entry_from_txn_range(response: Mapping[str, Any]) -> AuthorityStoreEntry | None:
        kvs = response.get("kvs") or []
        if not kvs:
            return None
        if len(kvs) != 1:
            raise AuthorityStoreError("transaction exact-key Range returned multiple records")
        kv = kvs[0]
        return AuthorityStoreEntry(
            key=bytes(kv["key"]),
            value=bytes(kv["value"]),
            create_revision=int(kv["create_revision"]),
            mod_revision=int(kv["mod_revision"]),
            version=int(kv["version"]),
            lease_id=int(kv.get("lease", 0)),
        )

    def transact(
        self,
        compares: Sequence[AuthorityStoreCompare],
        success: Sequence[AuthorityStoreTxnOperation],
        failure: Sequence[AuthorityStoreTxnOperation] = (),
    ) -> AuthorityStoreTxnResult:
        if any(not isinstance(cmp, AuthorityStoreCompare) for cmp in compares):
            raise ValueError("compares must contain AuthorityStoreCompare values")
        _validate_mutations(success, failure)
        try:
            response = self.client.txn(
                compare=[self._compare_request(cmp) for cmp in compares],
                success=[self._txn_request(op) for op in success],
                failure=[self._txn_request(op) for op in failure],
            )
            header = response.get("header", {})
            reads: list[AuthorityStoreEntry | None] = []
            responses = response.get("responses") or []
            operations = success if bool(response.get("succeeded")) else failure
            read_count = sum(isinstance(op, AuthorityStoreGet) for op in operations)
            if len(responses) != len(operations):
                if read_count:
                    raise AuthorityStoreError(
                        "etcd transaction response count does not match requested operations"
                    )
            else:
                for op, result in zip(operations, responses):
                    if isinstance(op, AuthorityStoreGet):
                        range_result = result.get("response_range")
                        if not isinstance(range_result, Mapping):
                            raise AuthorityStoreError(
                                "etcd transaction Get did not return a Range response"
                            )
                        reads.append(self._entry_from_txn_range(range_result))
            return AuthorityStoreTxnResult(
                succeeded=bool(response.get("succeeded")),
                revision=int(header.get("revision", 0)),
                reads=tuple(reads),
            )
        except (TimeoutError, ConnectionError) as exc:
            # Txn may have committed before the response was lost.
            raise AuthorityStoreOutcomeUnknownError(
                "etcd transaction response was lost; reconcile by operation ID/read-back"
            ) from exc
        except AuthorityStoreError:
            raise
        except Exception as exc:
            raise AuthorityStoreUnavailableError("etcd transaction failed") from exc

    def lease_grant(self, ttl_seconds: int) -> AuthorityStoreLease:
        if not isinstance(ttl_seconds, int) or isinstance(ttl_seconds, bool) or not 1 <= ttl_seconds <= 86400:
            raise ValueError("lease TTL must be in [1, 86400] seconds")
        try:
            response = self.client.lease_grant(ttl_seconds)
            lease_id = int(response["id"])
            ttl = int(response.get("ttl", ttl_seconds))
            if lease_id <= 0 or ttl <= 0:
                raise AuthorityStoreError("etcd returned an invalid lease grant")
            return AuthorityStoreLease(lease_id, ttl)
        except AuthorityStoreError:
            raise
        except (TimeoutError, ConnectionError) as exc:
            raise AuthorityStoreOutcomeUnknownError(
                "etcd LeaseGrant outcome is unknown; do not issue a duplicate logical operation"
            ) from exc
        except Exception as exc:
            raise AuthorityStoreUnavailableError("etcd LeaseGrant failed") from exc

    def lease_keepalive(self, lease_id: int) -> AuthorityStoreLease:
        if not isinstance(lease_id, int) or isinstance(lease_id, bool) or lease_id < 1:
            raise ValueError("lease ID must be positive")
        try:
            response = self.client.lease_keepalive(lease_id)
            ttl = int(response.get("ttl", 0))
            if ttl <= 0:
                raise AuthorityStoreLeaseError("etcd reports the lease expired")
            return AuthorityStoreLease(lease_id, ttl)
        except AuthorityStoreError:
            raise
        except (TimeoutError, ConnectionError) as exc:
            raise AuthorityStoreUnavailableError("etcd LeaseKeepAlive failed; leadership must fail closed") from exc
        except Exception as exc:
            raise AuthorityStoreUnavailableError("etcd LeaseKeepAlive failed") from exc

    def lease_revoke(self, lease_id: int) -> None:
        if not isinstance(lease_id, int) or isinstance(lease_id, bool) or lease_id < 1:
            raise ValueError("lease ID must be positive")
        try:
            self.client.lease_revoke(lease_id)
        except (TimeoutError, ConnectionError) as exc:
            raise AuthorityStoreOutcomeUnknownError(
                "etcd LeaseRevoke outcome is unknown; verify lease/key state before retry"
            ) from exc
        except Exception as exc:
            raise AuthorityStoreUnavailableError("etcd LeaseRevoke failed") from exc


class InMemoryEtcdV3Client:
    """Single-process etcd v3 API test double; not a server or consensus system."""

    def __init__(self, *, clock_fn: Callable[[], float] = time.time):
        self.clock_fn = clock_fn
        self._lock = threading.RLock()
        self._revision = 0
        self._next_lease_id = 1000
        self._kvs: dict[bytes, dict[str, Any]] = {}
        self._leases: dict[int, dict[str, Any]] = {}
        self.serializable_flags: list[bool] = []
        self.before_txn: Callable[[], None] | None = None
        self.fail_next_txn_after_commit = False
        self.unavailable = False

    def _ensure_available(self) -> None:
        if self.unavailable:
            raise ConnectionError("synthetic etcd endpoint unavailable")

    def _expire(self) -> None:
        now = self.clock_fn()
        expired = [lease_id for lease_id, item in self._leases.items() if item["expires_at"] <= now]
        if not expired:
            return
        for lease_id in expired:
            self._leases.pop(lease_id, None)
        deleted = False
        for key in list(self._kvs):
            if self._kvs[key]["lease"] in expired:
                self._kvs.pop(key, None)
                deleted = True
        if deleted:
            self._revision += 1

    def range(self, key: bytes, *, serializable: bool = False) -> Mapping[str, Any]:
        with self._lock:
            self._ensure_available()
            self._expire()
            self.serializable_flags.append(serializable)
            record = self._kvs.get(key)
            kvs = [] if record is None else [{
                "key": key, "value": record["value"],
                "create_revision": record["create_revision"],
                "mod_revision": record["mod_revision"],
                "version": record["version"], "lease": record["lease"],
            }]
            return {"header": {"revision": self._revision}, "kvs": kvs}

    def _matches(self, condition: Mapping[str, Any]) -> bool:
        key = condition["key"]
        record = self._kvs.get(key)
        target = condition["target"]
        expected_field = {
            "VERSION": "version", "CREATE": "create_revision",
            "MOD": "mod_revision", "VALUE": "value",
        }[target]
        expected = condition[expected_field]
        if target == "VALUE":
            actual: bytes | int = b"" if record is None else record["value"]
        else:
            actual = 0 if record is None else record[expected_field]
            expected = int(expected)
        return _compare_value(actual, expected, condition["result"])

    def _apply_requests(
        self, operations: Sequence[Mapping[str, Any]]
    ) -> tuple[bool, list[Mapping[str, Any]]]:
        changed = False
        responses: list[Mapping[str, Any]] = []
        for item in operations:
            if "request_range" in item:
                key = item["request_range"]["key"]
                record = self._kvs.get(key)
                kvs = [] if record is None else [{
                    "key": key,
                    "value": record["value"],
                    "create_revision": record["create_revision"],
                    "mod_revision": record["mod_revision"],
                    "version": record["version"],
                    "lease": record["lease"],
                }]
                responses.append({"response_range": {"kvs": kvs}})
            elif "request_put" in item:
                req = item["request_put"]
                key, value = req["key"], req["value"]
                lease_id = int(req.get("lease", 0))
                if lease_id and lease_id not in self._leases:
                    raise AuthorityStoreLeaseError("etcd test double lease is missing")
                old = self._kvs.get(key)
                self._kvs[key] = {
                    "value": value,
                    "create_revision": self._revision + 1 if old is None else old["create_revision"],
                    "mod_revision": self._revision + 1,
                    "version": 1 if old is None else old["version"] + 1,
                    "lease": lease_id,
                }
                changed = True
                responses.append({"response_put": {}})
            elif "request_delete_range" in item:
                key = item["request_delete_range"]["key"]
                deleted = key in self._kvs
                if deleted:
                    self._kvs.pop(key, None)
                    changed = True
                responses.append({"response_delete_range": {"deleted": int(deleted)}})
            else:
                raise ValueError("unsupported etcd transaction operation")
        return changed, responses

    def txn(
        self,
        *,
        compare: Sequence[Mapping[str, Any]],
        success: Sequence[Mapping[str, Any]],
        failure: Sequence[Mapping[str, Any]],
    ) -> Mapping[str, Any]:
        with self._lock:
            self._ensure_available()
            self._expire()
            if self.before_txn is not None:
                self.before_txn()
            succeeded = all(self._matches(item) for item in compare)
            operations = success if succeeded else failure
            changed, branch_responses = self._apply_requests(operations)
            if changed:
                self._revision += 1
                for item in operations:
                    if "request_put" in item:
                        record = self._kvs[item["request_put"]["key"]]
                        record["mod_revision"] = self._revision
                        if record["create_revision"] == self._revision - 1:
                            record["create_revision"] = self._revision
            response = {
                "header": {"revision": self._revision},
                "succeeded": succeeded,
                "responses": branch_responses,
            }
            if self.fail_next_txn_after_commit:
                self.fail_next_txn_after_commit = False
                raise TimeoutError("synthetic lost transaction response after commit")
            return response

    def lease_grant(self, ttl_seconds: int) -> Mapping[str, Any]:
        with self._lock:
            self._ensure_available()
            self._expire()
            self._next_lease_id += 1
            lease_id = self._next_lease_id
            self._leases[lease_id] = {
                "ttl": ttl_seconds, "expires_at": self.clock_fn() + ttl_seconds,
            }
            return {"id": lease_id, "ttl": ttl_seconds}

    def lease_keepalive(self, lease_id: int) -> Mapping[str, Any]:
        with self._lock:
            self._ensure_available()
            self._expire()
            item = self._leases.get(lease_id)
            if item is None:
                return {"id": lease_id, "ttl": 0}
            item["expires_at"] = self.clock_fn() + item["ttl"]
            return {"id": lease_id, "ttl": item["ttl"]}

    def lease_revoke(self, lease_id: int) -> Mapping[str, Any]:
        with self._lock:
            self._ensure_available()
            self._expire()
            self._leases.pop(lease_id, None)
            deleted = False
            for key in list(self._kvs):
                if self._kvs[key]["lease"] == lease_id:
                    self._kvs.pop(key, None)
                    deleted = True
            if deleted:
                self._revision += 1
            return {"id": lease_id}


class InMemoryEtcdV3WatchClient(InMemoryEtcdV3Client):
    """Shared single-process fake with revisioned Watch and failure injection.

    Multiple EtcdV3CoordinatorAuthorityStore instances may share one instance
    to test independent clients against the same deterministic backend. This
    remains a process-local fake: no Raft, quorum, transport or server clock.
    """

    def __init__(self, *, clock_fn: Callable[[], float] = time.time):
        super().__init__(clock_fn=clock_fn)
        self._condition = threading.Condition(self._lock)
        self._watch_history: list[dict[str, Any]] = []
        self._watchers: dict[int, dict[str, Any]] = {}
        self._next_watch_id = 1
        self._compact_revision = 0
        self.fail_next_txn_before_commit = False
        self.fail_next_lease_grant_after_commit = False
        self.fail_next_lease_keepalive_after_commit = False
        self.fail_next_lease_revoke_after_commit = False
        self.fail_next_watch_after_create = False

    @staticmethod
    def _copy_kv(value: Mapping[str, Any]) -> dict[str, Any]:
        return {key: item for key, item in value.items()}

    def _record_diff(
        self,
        before: Mapping[bytes, Mapping[str, Any]],
        *,
        revision: int,
    ) -> None:
        events: list[dict[str, Any]] = []
        keys = set(before) | set(self._kvs)
        for key in sorted(keys):
            old = before.get(key)
            current = self._kvs.get(key)
            if old == current:
                continue
            if current is None:
                deleted_kv = {
                    "key": key,
                    "value": b"",
                    "create_revision": int(old["create_revision"]),
                    "mod_revision": revision,
                    "version": 0,
                    "lease": 0,
                }
                events.append({
                    "type": 1,
                    "kv": deleted_kv,
                    "prev_kv": {"key": key, **self._copy_kv(old)},
                })
            else:
                events.append({
                    "type": 0,
                    "kv": {"key": key, **self._copy_kv(current)},
                    "prev_kv": (
                        None if old is None
                        else {"key": key, **self._copy_kv(old)}
                    ),
                })
        if events:
            self._watch_history.extend(
                {"revision": revision, "event": event} for event in events
            )
            self._condition.notify_all()

    def _expire(self) -> None:
        before = {key: self._copy_kv(value) for key, value in self._kvs.items()}
        old_revision = self._revision
        super()._expire()
        if self._revision > old_revision:
            self._record_diff(before, revision=self._revision)

    def range(
        self,
        key: bytes,
        *,
        range_end: bytes | None = None,
        serializable: bool = False,
    ) -> Mapping[str, Any]:
        with self._lock:
            self._ensure_available()
            self._expire()
            self.serializable_flags.append(serializable)
            if range_end is None:
                keys = [key] if key in self._kvs else []
            elif range_end == b"\x00":
                keys = sorted(candidate for candidate in self._kvs if candidate >= key)
            else:
                keys = sorted(
                    candidate for candidate in self._kvs
                    if key <= candidate < range_end
                )
            return {
                "header": {"revision": self._revision},
                "kvs": [
                    {"key": candidate, **self._copy_kv(self._kvs[candidate])}
                    for candidate in keys
                ],
            }

    def txn(
        self,
        *,
        compare: Sequence[Mapping[str, Any]],
        success: Sequence[Mapping[str, Any]],
        failure: Sequence[Mapping[str, Any]],
    ) -> Mapping[str, Any]:
        with self._condition:
            self._ensure_available()
            self._expire()
            if self.fail_next_txn_before_commit:
                self.fail_next_txn_before_commit = False
                raise TimeoutError("synthetic Txn response lost before commit")
            before = {key: self._copy_kv(value) for key, value in self._kvs.items()}
            old_revision = self._revision
            try:
                return super().txn(compare=compare, success=success, failure=failure)
            finally:
                if self._revision > old_revision:
                    self._record_diff(before, revision=self._revision)

    def lease_grant(self, ttl_seconds: int) -> Mapping[str, Any]:
        response = super().lease_grant(ttl_seconds)
        if self.fail_next_lease_grant_after_commit:
            self.fail_next_lease_grant_after_commit = False
            raise TimeoutError("synthetic LeaseGrant response lost after grant")
        return response

    def lease_keepalive(self, lease_id: int) -> Mapping[str, Any]:
        response = super().lease_keepalive(lease_id)
        if self.fail_next_lease_keepalive_after_commit:
            self.fail_next_lease_keepalive_after_commit = False
            raise TimeoutError("synthetic LeaseKeepAlive response lost after extension")
        return response

    def lease_revoke(self, lease_id: int) -> Mapping[str, Any]:
        with self._condition:
            self._ensure_available()
            self._expire()
            before = {key: self._copy_kv(value) for key, value in self._kvs.items()}
            old_revision = self._revision
            try:
                response = super().lease_revoke(lease_id)
            finally:
                if self._revision > old_revision:
                    self._record_diff(before, revision=self._revision)
            if self.fail_next_lease_revoke_after_commit:
                self.fail_next_lease_revoke_after_commit = False
                raise TimeoutError("synthetic LeaseRevoke response lost after revoke")
            return response

    def compact(self, revision: int) -> None:
        with self._condition:
            if (
                not isinstance(revision, int)
                or isinstance(revision, bool)
                or revision < 0
                or revision > self._revision
            ):
                raise ValueError("compact revision must be within current revision")
            self._compact_revision = max(self._compact_revision, revision)
            self._watch_history = [
                item for item in self._watch_history
                if int(item["revision"]) > self._compact_revision
            ]
            self._condition.notify_all()

    def watch(
        self,
        key: bytes,
        *,
        start_revision: int = 0,
        range_end: bytes | None = None,
        progress_notify: bool = True,
        prev_kv: bool = True,
    ) -> Iterator[Mapping[str, Any]]:
        if not isinstance(key, bytes) or not key:
            raise ValueError("watch key must be non-empty bytes")
        if not isinstance(start_revision, int) or isinstance(start_revision, bool) or start_revision < 0:
            raise ValueError("start_revision must be non-negative")

        def matches(candidate: bytes) -> bool:
            if range_end is None:
                return candidate == key
            if range_end == b"\x00":
                return candidate >= key
            return key <= candidate < range_end

        def stream() -> Iterator[Mapping[str, Any]]:
            with self._condition:
                self._ensure_available()
                self._expire()
                watch_id = self._next_watch_id
                self._next_watch_id += 1
                current_revision = self._revision
                if start_revision and start_revision <= self._compact_revision:
                    yield {
                        "header": {"revision": current_revision},
                        "watch_id": watch_id,
                        "canceled": True,
                        "compact_revision": self._compact_revision,
                        "cancel_reason": "required revision has been compacted",
                        "events": [],
                    }
                    return
                cursor = current_revision + 1 if start_revision == 0 else start_revision
                self._watchers[watch_id] = {
                    "cursor": cursor,
                    "progress_requested": False,
                    "cancel_requested": False,
                }
                self._condition.notify_all()
                created = {
                    "header": {"revision": current_revision},
                    "watch_id": watch_id,
                    "created": True,
                    "events": [],
                }

            try:
                yield created
                while True:
                    with self._condition:
                        while True:
                            self._ensure_available()
                            if self.fail_next_watch_after_create:
                                self.fail_next_watch_after_create = False
                                raise ConnectionError("synthetic Watch stream disconnected")
                            self._expire()
                            watcher = self._watchers.get(watch_id)
                            if watcher is None:
                                return
                            cursor = int(watcher["cursor"])
                            if watcher["cancel_requested"]:
                                self._watchers.pop(watch_id, None)
                                response = {
                                    "header": {"revision": self._revision},
                                    "watch_id": watch_id,
                                    "canceled": True,
                                    "cancel_reason": "watch canceled by client",
                                    "events": [],
                                }
                                break
                            if cursor <= self._compact_revision:
                                self._watchers.pop(watch_id, None)
                                response = {
                                    "header": {"revision": self._revision},
                                    "watch_id": watch_id,
                                    "canceled": True,
                                    "compact_revision": self._compact_revision,
                                    "cancel_reason": "watch fell behind compacted history",
                                    "events": [],
                                }
                                break

                            available = [
                                item for item in self._watch_history
                                if int(item["revision"]) >= cursor
                            ]
                            if available:
                                upper = max(int(item["revision"]) for item in available)
                                raw_events = [
                                    item["event"] for item in available
                                    if int(item["revision"]) <= upper
                                    and matches(bytes(item["event"]["kv"]["key"]))
                                ]
                                watcher["cursor"] = upper + 1
                                response = {
                                    "header": {"revision": upper},
                                    "watch_id": watch_id,
                                    "events": [
                                        {
                                            **self._copy_kv(event),
                                            "prev_kv": (
                                                event.get("prev_kv")
                                                if prev_kv else None
                                            ),
                                        }
                                        for event in raw_events
                                    ],
                                }
                                if not raw_events and not progress_notify:
                                    response = None
                                break

                            if watcher["progress_requested"]:
                                watcher["progress_requested"] = False
                                response = {
                                    "header": {"revision": self._revision},
                                    "watch_id": watch_id,
                                    "events": [],
                                }
                                break
                            self._condition.wait()

                    if response is not None:
                        yield response
                    if response is not None and response.get("canceled"):
                        return
            finally:
                with self._condition:
                    self._watchers.pop(watch_id, None)
                    self._condition.notify_all()

        return stream()

    def watch_progress(self, watch_id: int) -> None:
        with self._condition:
            watcher = self._watchers.get(watch_id)
            if watcher is None:
                raise ValueError("watch ID is not active")
            watcher["progress_requested"] = True
            self._condition.notify_all()

    def watch_cancel(self, watch_id: int) -> None:
        with self._condition:
            watcher = self._watchers.get(watch_id)
            if watcher is None:
                return
            watcher["cancel_requested"] = True
            self._condition.notify_all()


def main() -> int:
    print(
        "Coordinator authority store contract: SQLite local adapter and etcd v3 client seam; "
        "no network client or distributed cluster is configured."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
