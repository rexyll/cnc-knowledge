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
from typing import Any, Callable, Mapping, Protocol, Sequence, runtime_checkable


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
class AuthorityStoreTxnResult:
    succeeded: bool
    revision: int


@dataclass(frozen=True)
class AuthorityStoreLease:
    lease_id: int
    ttl_seconds: int


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
        success: Sequence[AuthorityStoreMutation],
        failure: Sequence[AuthorityStoreMutation] = (),
    ) -> AuthorityStoreTxnResult: ...

    def lease_grant(self, ttl_seconds: int) -> AuthorityStoreLease: ...

    def lease_keepalive(self, lease_id: int) -> AuthorityStoreLease: ...

    def lease_revoke(self, lease_id: int) -> None: ...


@runtime_checkable
class EtcdV3Client(Protocol):
    """Normalized client-driver port.

    A concrete driver may use etcd's gRPC API or its gRPC-JSON gateway. It must
    return snake_case response fields and bytes for keys/values, use a
    linearizable Range when serializable=False, and expose the transaction and
    Lease RPCs without weakening their consistency semantics.
    """

    def range(self, key: bytes, *, serializable: bool = False) -> Mapping[str, Any]: ...

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


def _validate_mutations(
    success: Sequence[AuthorityStoreMutation],
    failure: Sequence[AuthorityStoreMutation],
) -> None:
    for branch in (success, failure):
        keys: set[bytes] = set()
        for op in branch:
            if not isinstance(op, (AuthorityStorePut, AuthorityStoreDelete)):
                raise ValueError("transaction branch contains an unsupported mutation")
            if op.key in keys:
                raise ValueError("a transaction branch may mutate each key at most once")
            keys.add(op.key)


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
        success: Sequence[AuthorityStoreMutation],
        failure: Sequence[AuthorityStoreMutation] = (),
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
                old_rows = {
                    op.key: c.execute(
                        "SELECT create_revision,version FROM authority_store_kv WHERE key=?",
                        (op.key,),
                    ).fetchone()
                    for op in operations if isinstance(op, AuthorityStorePut)
                }
                changed = self._apply(c, operations)
                if changed:
                    revision = self._bump_revision(c)
                    for op in operations:
                        if isinstance(op, AuthorityStorePut):
                            old = old_rows[op.key]
                            create_revision = revision if old is None else int(old["create_revision"])
                            version = 1 if old is None else int(old["version"]) + 1
                            c.execute(
                                """UPDATE authority_store_kv SET create_revision=?,
                                   mod_revision=?,version=? WHERE key=?""",
                                (create_revision, revision, version, op.key),
                            )
                else:
                    revision = self._revision(c)
                c.commit()
                return AuthorityStoreTxnResult(succeeded=succeeded, revision=revision)
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
    def _mutation_request(operation: AuthorityStoreMutation) -> dict[str, Any]:
        if isinstance(operation, AuthorityStorePut):
            request: dict[str, Any] = {
                "key": operation.key,
                "value": operation.value,
            }
            if operation.lease_id:
                request["lease"] = str(operation.lease_id)
            return {"request_put": request}
        return {"request_delete_range": {"key": operation.key}}

    def transact(
        self,
        compares: Sequence[AuthorityStoreCompare],
        success: Sequence[AuthorityStoreMutation],
        failure: Sequence[AuthorityStoreMutation] = (),
    ) -> AuthorityStoreTxnResult:
        if any(not isinstance(cmp, AuthorityStoreCompare) for cmp in compares):
            raise ValueError("compares must contain AuthorityStoreCompare values")
        _validate_mutations(success, failure)
        try:
            response = self.client.txn(
                compare=[self._compare_request(cmp) for cmp in compares],
                success=[self._mutation_request(op) for op in success],
                failure=[self._mutation_request(op) for op in failure],
            )
            header = response.get("header", {})
            return AuthorityStoreTxnResult(
                succeeded=bool(response.get("succeeded")),
                revision=int(header.get("revision", 0)),
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

    def _apply_requests(self, operations: Sequence[Mapping[str, Any]]) -> bool:
        changed = False
        for item in operations:
            if "request_put" in item:
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
            elif "request_delete_range" in item:
                key = item["request_delete_range"]["key"]
                if key in self._kvs:
                    self._kvs.pop(key, None)
                    changed = True
            else:
                raise ValueError("unsupported etcd transaction operation")
        return changed

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
            changed = self._apply_requests(operations)
            if changed:
                self._revision += 1
                for item in operations:
                    if "request_put" in item:
                        record = self._kvs[item["request_put"]["key"]]
                        record["mod_revision"] = self._revision
                        if record["create_revision"] == self._revision - 1:
                            record["create_revision"] = self._revision
            response = {"header": {"revision": self._revision}, "succeeded": succeeded}
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


def main() -> int:
    print(
        "Coordinator authority store contract: SQLite local adapter and etcd v3 client seam; "
        "no network client or distributed cluster is configured."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
