#!/usr/bin/env python3
"""Durable same-host SQLite-backed Provider admission coordinator."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
import sqlite3
import tempfile
import threading
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable

from scripts.spare_parts_backup_storage_adapter import (
    BackupStorageError, ProviderAdmissionIdempotencyConflictError,
    ProviderAdmissionLease, ProviderAdmissionQueueFullError,
    ProviderAdmissionRequestFinalizedError, ProviderBulkheadFullError,
    ProviderCoordinatorUnavailableError, ProviderTaskContext,
)


class SQLiteProviderAdmissionCoordinator:
    """Persistent leases for processes sharing one SQLite file on the same host.

    Requires SQLite WAL on a supported local filesystem. It is not a multi-host
    service; do not use NFS/SMB. Lease expiry uses Unix wall-clock seconds so it
    survives process restart; system wall-clock adjustments remain an assumption.
    """

    def __init__(
        self, database_path: str | os.PathLike[str], *,
        global_limits: dict[str, int] | None = None,
        tenant_limits: dict[str, dict[str, int]] | None = None,
        max_waiters: int = 256,
        aging_interval_seconds: float = 1.0,
        busy_timeout_seconds: float = 5.0,
        poll_interval_seconds: float = 0.05,
        clock_fn: Callable[[], float] = time.time,
    ):
        if not isinstance(database_path, (str, os.PathLike)) or not str(database_path).strip():
            raise BackupStorageError("SQLite coordinator database path is required")
        if str(database_path) == ":memory:":
            raise BackupStorageError("SQLite coordinator requires a file path, not :memory:")
        if not isinstance(max_waiters, int) or isinstance(max_waiters, bool) or max_waiters < 0:
            raise BackupStorageError("SQLite maximum waiters must be a non-negative integer")
        if not math.isfinite(aging_interval_seconds) or aging_interval_seconds <= 0:
            raise BackupStorageError("SQLite aging interval must be finite and positive")
        if not math.isfinite(busy_timeout_seconds) or busy_timeout_seconds <= 0:
            raise BackupStorageError("SQLite busy timeout must be finite and positive")
        if not math.isfinite(poll_interval_seconds) or poll_interval_seconds <= 0:
            raise BackupStorageError("SQLite poll interval must be finite and positive")
        limits = {"read": 4, "write": 2, "multipart": 2, "inventory": 1}
        if global_limits is not None:
            if set(global_limits) - set(limits) or any(
                not isinstance(v, int) or isinstance(v, bool) or v < 1
                for v in global_limits.values()
            ):
                raise BackupStorageError("SQLite global limits must be positive integers for known domains")
            limits.update(global_limits)
        tenants = {tenant: dict(values) for tenant, values in (tenant_limits or {}).items()}
        for tenant, values in tenants.items():
            if not isinstance(tenant, str) or not tenant.strip():
                raise BackupStorageError("SQLite tenant limits require nonblank tenant IDs")
            if set(values) - set(limits) or any(
                not isinstance(v, int) or isinstance(v, bool) or v < 1
                for v in values.values()
            ):
                raise BackupStorageError("SQLite tenant limits must be positive integers for known domains")
        self.database_path = Path(database_path).expanduser().resolve()
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.global_limits, self.tenant_limits = limits, tenants
        self.max_waiters = max_waiters
        self.aging_interval_seconds = float(aging_interval_seconds)
        self.busy_timeout_seconds = float(busy_timeout_seconds)
        self.poll_interval_seconds = float(poll_interval_seconds)
        self.clock_fn = clock_fn
        self._fault_lock = threading.Lock()
        self._injected_failures: dict[str, int] = {}
        policy = {
            "global_limits": limits, "tenant_limits": tenants,
            "max_waiters": max_waiters,
            "aging_interval_seconds": self.aging_interval_seconds,
        }
        self._policy_hash = hashlib.sha256(
            json.dumps(policy, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        c = sqlite3.connect(str(self.database_path), timeout=self.busy_timeout_seconds, isolation_level=None)
        c.row_factory = sqlite3.Row
        c.execute(f"PRAGMA busy_timeout = {int(self.busy_timeout_seconds * 1000)}")
        c.execute("PRAGMA foreign_keys = ON")
        c.execute("PRAGMA synchronous = FULL")
        return c

    @contextmanager
    def _transaction(self, phase: str):
        try:
            c = self._connect()
        except sqlite3.Error as exc:
            raise ProviderCoordinatorUnavailableError(
                f"SQLite coordinator cannot open database during {phase}", phase=phase
            ) from exc
        try:
            c.execute("BEGIN IMMEDIATE")
            yield c
            c.commit()
        except sqlite3.Error as exc:
            try:
                c.rollback()
            except sqlite3.Error:
                pass
            raise ProviderCoordinatorUnavailableError(
                f"SQLite coordinator database failure during {phase}", phase=phase
            ) from exc
        except Exception:
            try:
                c.rollback()
            except sqlite3.Error:
                pass
            raise
        finally:
            c.close()

    def _initialize(self) -> None:
        try:
            c = self._connect()
            try:
                mode = c.execute("PRAGMA journal_mode=WAL").fetchone()[0]
                if str(mode).lower() != "wal":
                    raise sqlite3.OperationalError("database did not enter WAL mode")
                c.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS coordinator_meta (
                        key TEXT PRIMARY KEY, value TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS admission_requests (
                        request_id TEXT PRIMARY KEY, lease_id TEXT NOT NULL UNIQUE,
                        owner_id TEXT NOT NULL, task_id TEXT NOT NULL,
                        tenant_id TEXT NOT NULL, domain TEXT NOT NULL,
                        fencing_token INTEGER NOT NULL UNIQUE, expires_at REAL NOT NULL,
                        state TEXT NOT NULL CHECK(state IN ('ACTIVE','RELEASED','EXPIRED'))
                    );
                    CREATE INDEX IF NOT EXISTS idx_admission_domain
                        ON admission_requests(state,domain,expires_at);
                    CREATE INDEX IF NOT EXISTS idx_admission_tenant
                        ON admission_requests(state,tenant_id,domain,expires_at);
                    CREATE TABLE IF NOT EXISTS admission_waiters (
                        sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                        request_id TEXT NOT NULL UNIQUE, owner_id TEXT NOT NULL,
                        task_id TEXT NOT NULL, tenant_id TEXT NOT NULL, domain TEXT NOT NULL,
                        priority INTEGER NOT NULL, queued_at REAL NOT NULL, expires_at REAL NOT NULL
                    );
                    CREATE INDEX IF NOT EXISTS idx_waiter_domain ON admission_waiters(domain,sequence);
                    """
                )
                c.execute("BEGIN IMMEDIATE")
                defaults = {
                    "schema_version": "1", "policy_hash": self._policy_hash,
                    "next_fencing_token": "0", "issued_leases": "0",
                    "expired_leases": "0", "rejected_capacity": "0", "rejected_queue": "0",
                }
                for key, value in defaults.items():
                    c.execute("INSERT OR IGNORE INTO coordinator_meta(key,value) VALUES(?,?)", (key, value))
                stored = c.execute(
                    "SELECT value FROM coordinator_meta WHERE key='policy_hash'"
                ).fetchone()["value"]
                if stored != self._policy_hash:
                    raise BackupStorageError("SQLite coordinator policy differs from database-bound policy")
                c.commit()
            finally:
                c.close()
        except BackupStorageError:
            raise
        except sqlite3.Error as exc:
            raise ProviderCoordinatorUnavailableError(
                "SQLite coordinator initialization failed", phase="initialize"
            ) from exc

    def inject_failure(self, phase: str, *, times: int = 1) -> None:
        if phase != "acquire_response":
            raise BackupStorageError("SQLite coordinator only supports acquire_response fault injection")
        if not isinstance(times, int) or isinstance(times, bool) or times < 1:
            raise BackupStorageError("injected failure count must be positive")
        with self._fault_lock:
            self._injected_failures[phase] = self._injected_failures.get(phase, 0) + times

    def _consume_failure(self, phase: str) -> bool:
        with self._fault_lock:
            n = self._injected_failures.get(phase, 0)
            if not n:
                return False
            if n == 1:
                self._injected_failures.pop(phase, None)
            else:
                self._injected_failures[phase] = n - 1
            return True

    @staticmethod
    def _meta_int(c: sqlite3.Connection, key: str) -> int:
        return int(c.execute("SELECT value FROM coordinator_meta WHERE key=?", (key,)).fetchone()["value"])

    @staticmethod
    def _set_meta_int(c: sqlite3.Connection, key: str, value: int) -> None:
        c.execute("UPDATE coordinator_meta SET value=? WHERE key=?", (str(value), key))

    def _expire_locked(self, c: sqlite3.Connection, now: float) -> int:
        result = c.execute(
            "UPDATE admission_requests SET state='EXPIRED' WHERE state='ACTIVE' AND expires_at<=?",
            (now,),
        )
        count = max(result.rowcount, 0)
        if count:
            self._set_meta_int(c, "expired_leases", self._meta_int(c, "expired_leases") + count)
        c.execute("DELETE FROM admission_waiters WHERE expires_at<=?", (now,))
        return count

    def _tenant_limit(self, tenant_id: str, domain: str) -> int:
        return self.tenant_limits.get(tenant_id, {}).get(domain, self.global_limits[domain])

    @staticmethod
    def _same_identity(row: sqlite3.Row, owner_id: str, task: ProviderTaskContext, domain: str) -> bool:
        return (
            row["owner_id"] == owner_id and row["task_id"] == task.task_id
            and row["tenant_id"] == task.tenant_id and row["domain"] == domain
        )

    @staticmethod
    def _as_lease(row: sqlite3.Row) -> ProviderAdmissionLease:
        return ProviderAdmissionLease(
            row["lease_id"], row["owner_id"], row["tenant_id"], row["domain"],
            int(row["fencing_token"]), float(row["expires_at"]),
        )

    def acquire(
        self, *, task: ProviderTaskContext, domain: str, owner_id: str,
        lease_ttl_seconds: float, timeout_seconds: float,
        check_task: Callable[[ProviderTaskContext], None],
        request_id: str | None = None,
    ) -> ProviderAdmissionLease:
        if request_id is None:
            request_id = uuid.uuid4().hex
        if not isinstance(request_id, str) or not request_id.strip():
            raise BackupStorageError("SQLite admission request ID is required")
        request_id = request_id.strip()
        if domain not in self.global_limits:
            raise BackupStorageError("unknown SQLite coordinator domain")
        if not isinstance(owner_id, str) or not owner_id.strip():
            raise BackupStorageError("SQLite coordinator owner ID is required")
        if not math.isfinite(lease_ttl_seconds) or lease_ttl_seconds <= 0:
            raise BackupStorageError("SQLite lease TTL must be finite and positive")
        if not math.isfinite(timeout_seconds) or timeout_seconds < 0:
            raise BackupStorageError("SQLite acquire timeout must be finite and non-negative")
        owner_id = owner_id.strip()
        deadline, wall_deadline = time.monotonic() + timeout_seconds, self.clock_fn() + timeout_seconds
        registered = admitted = False
        try:
            while True:
                check_task(task)
                now, lease = self.clock_fn(), None
                with self._transaction("acquire") as c:
                    self._expire_locked(c, now)
                    existing = c.execute(
                        "SELECT * FROM admission_requests WHERE request_id=?", (request_id,)
                    ).fetchone()
                    if existing is not None:
                        if not self._same_identity(existing, owner_id, task, domain):
                            raise ProviderAdmissionIdempotencyConflictError(
                                "request ID is bound to a different owner/task/tenant/domain"
                            )
                        if existing["state"] == "ACTIVE" and float(existing["expires_at"]) > now:
                            lease, admitted = self._as_lease(existing), True
                        else:
                            raise ProviderAdmissionRequestFinalizedError(
                                "request ID was released or expired; use a new logical request ID"
                            )
                    else:
                        waiter = c.execute(
                            "SELECT * FROM admission_waiters WHERE request_id=?", (request_id,)
                        ).fetchone()
                        if waiter is not None and not self._same_identity(waiter, owner_id, task, domain):
                            raise ProviderAdmissionIdempotencyConflictError(
                                "waiting request ID is bound to a different identity"
                            )
                        if waiter is None:
                            c.execute(
                                "INSERT INTO admission_waiters("
                                "request_id,owner_id,task_id,tenant_id,domain,priority,queued_at,expires_at"
                                ") VALUES(?,?,?,?,?,?,?,?)",
                                (request_id, owner_id, task.task_id, task.tenant_id,
                                 domain, task.priority, now, wall_deadline),
                            )
                            registered = True
                        active = int(c.execute(
                            "SELECT COUNT(*) AS n FROM admission_requests "
                            "WHERE state='ACTIVE' AND domain=? AND expires_at>?",
                            (domain, now),
                        ).fetchone()["n"])
                        tenant_active = int(c.execute(
                            "SELECT COUNT(*) AS n FROM admission_requests "
                            "WHERE state='ACTIVE' AND domain=? AND tenant_id=? AND expires_at>?",
                            (domain, task.tenant_id, now),
                        ).fetchone()["n"])
                        waiters = c.execute(
                            "SELECT sequence,request_id,tenant_id,priority,queued_at "
                            "FROM admission_waiters WHERE domain=?",
                            (domain,),
                        ).fetchall()
                        tenant_counts = {
                            r["tenant_id"]: int(r["n"])
                            for r in c.execute(
                                "SELECT tenant_id,COUNT(*) AS n FROM admission_requests "
                                "WHERE state='ACTIVE' AND domain=? AND expires_at>? GROUP BY tenant_id",
                                (domain, now),
                            ).fetchall()
                        }
                        eligible = [
                            w for w in waiters
                            if tenant_counts.get(w["tenant_id"], 0) < self._tenant_limit(w["tenant_id"], domain)
                        ]
                        selected = None
                        if eligible:
                            selected = max(
                                eligible,
                                key=lambda w: (
                                    int(w["priority"]) + max(0.0, now - float(w["queued_at"]))
                                    / self.aging_interval_seconds,
                                    -int(w["sequence"]),
                                ),
                            )["request_id"]
                        can_admit = (
                            active < self.global_limits[domain]
                            and tenant_active < self._tenant_limit(task.tenant_id, domain)
                            and selected == request_id
                        )
                        queue_count = int(c.execute(
                            "SELECT COUNT(*) AS n FROM admission_waiters"
                        ).fetchone()["n"])
                        if queue_count > self.max_waiters and not can_admit:
                            c.execute("DELETE FROM admission_waiters WHERE request_id=?", (request_id,))
                            self._set_meta_int(
                                c, "rejected_queue", self._meta_int(c, "rejected_queue") + 1
                            )
                            raise ProviderAdmissionQueueFullError(
                                "SQLite shared admission waiting queue is full",
                                scope="sqlite_coordinator",
                            )
                        if can_admit:
                            fence = self._meta_int(c, "next_fencing_token") + 1
                            self._set_meta_int(c, "next_fencing_token", fence)
                            lease_id, expiry = "sqlite-lease-" + uuid.uuid4().hex, now + lease_ttl_seconds
                            c.execute(
                                "INSERT INTO admission_requests("
                                "request_id,lease_id,owner_id,task_id,tenant_id,domain,fencing_token,expires_at,state"
                                ") VALUES(?,?,?,?,?,?,?,?, 'ACTIVE')",
                                (request_id, lease_id, owner_id, task.task_id,
                                 task.tenant_id, domain, fence, expiry),
                            )
                            c.execute("DELETE FROM admission_waiters WHERE request_id=?", (request_id,))
                            self._set_meta_int(c, "issued_leases", self._meta_int(c, "issued_leases") + 1)
                            lease, admitted = ProviderAdmissionLease(
                                lease_id, owner_id, task.tenant_id, domain, fence, expiry
                            ), True
                        else:
                            remaining = deadline - time.monotonic()
                            if remaining <= 0:
                                c.execute("DELETE FROM admission_waiters WHERE request_id=?", (request_id,))
                                self._set_meta_int(
                                    c, "rejected_capacity", self._meta_int(c, "rejected_capacity") + 1
                                )
                                raise ProviderBulkheadFullError(
                                    f"SQLite shared {domain} concurrency or tenant quota is full"
                                )
                if lease is not None:
                    if self._consume_failure("acquire_response"):
                        raise ProviderCoordinatorUnavailableError(
                            "SQLite lease committed but acquire response was lost",
                            phase="acquire_response", reservation_outcome_unknown=True,
                            request_id=request_id,
                        )
                    return lease
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise ProviderBulkheadFullError(
                        f"SQLite shared {domain} concurrency or tenant quota is full"
                    )
                time.sleep(min(self.poll_interval_seconds, remaining))
        finally:
            if registered and not admitted:
                try:
                    with self._transaction("release_waiter") as c:
                        c.execute("DELETE FROM admission_waiters WHERE request_id=?", (request_id,))
                except ProviderCoordinatorUnavailableError:
                    pass

    def renew(self, lease: ProviderAdmissionLease, *, lease_ttl_seconds: float) -> ProviderAdmissionLease | None:
        if not math.isfinite(lease_ttl_seconds) or lease_ttl_seconds <= 0:
            raise BackupStorageError("SQLite lease TTL must be finite and positive")
        now = self.clock_fn()
        with self._transaction("renew") as c:
            self._expire_locked(c, now)
            row = c.execute("SELECT * FROM admission_requests WHERE lease_id=?", (lease.lease_id,)).fetchone()
            if row is None or row["state"] != "ACTIVE" or self._as_lease(row) != lease:
                return None
            renewed = ProviderAdmissionLease(
                lease.lease_id, lease.owner_id, lease.tenant_id, lease.domain,
                lease.fencing_token, now + lease_ttl_seconds,
            )
            c.execute(
                "UPDATE admission_requests SET expires_at=? WHERE lease_id=? AND state='ACTIVE'",
                (renewed.expires_at, lease.lease_id),
            )
            return renewed

    def release(self, lease: ProviderAdmissionLease) -> bool:
        now = self.clock_fn()
        with self._transaction("release") as c:
            self._expire_locked(c, now)
            row = c.execute("SELECT * FROM admission_requests WHERE lease_id=?", (lease.lease_id,)).fetchone()
            if row is None or row["state"] != "ACTIVE" or self._as_lease(row) != lease:
                return False
            c.execute("UPDATE admission_requests SET state='RELEASED' WHERE lease_id=?", (lease.lease_id,))
            return True

    def validate(self, lease: ProviderAdmissionLease) -> bool:
        now = self.clock_fn()
        with self._transaction("validate") as c:
            self._expire_locked(c, now)
            row = c.execute("SELECT * FROM admission_requests WHERE lease_id=?", (lease.lease_id,)).fetchone()
            return bool(
                row is not None and row["state"] == "ACTIVE"
                and float(row["expires_at"]) > now and self._as_lease(row) == lease
            )

    def reclaim_expired(self) -> int:
        with self._transaction("reclaim") as c:
            return self._expire_locked(c, self.clock_fn())

    def snapshot(self) -> dict[str, Any]:
        now = self.clock_fn()
        with self._transaction("snapshot") as c:
            self._expire_locked(c, now)
            active = {
                domain: int(c.execute(
                    "SELECT COUNT(*) AS n FROM admission_requests "
                    "WHERE state='ACTIVE' AND domain=? AND expires_at>?", (domain, now)
                ).fetchone()["n"])
                for domain in self.global_limits
            }
            tenant_rows = c.execute(
                "SELECT tenant_id,domain,COUNT(*) AS n FROM admission_requests "
                "WHERE state='ACTIVE' AND expires_at>? GROUP BY tenant_id,domain", (now,)
            ).fetchall()
            waiting = {
                domain: int(c.execute(
                    "SELECT COUNT(*) AS n FROM admission_waiters WHERE domain=? AND expires_at>?",
                    (domain, now),
                ).fetchone()["n"])
                for domain in self.global_limits
            }
            meta = {
                key: self._meta_int(c, key)
                for key in ("next_fencing_token", "issued_leases", "expired_leases",
                            "rejected_capacity", "rejected_queue")
            }
            return {
                "backend": "SQLITE_LOCAL_FILE", "journal_mode": "WAL",
                "synchronous": "FULL", "multi_process_same_host": True,
                "multi_host_supported": False, "global_limits": dict(self.global_limits),
                "max_waiters": self.max_waiters, "active_by_domain": active,
                "active_by_tenant_domain": {
                    f"{r['tenant_id']}|{r['domain']}": int(r["n"]) for r in tenant_rows
                },
                "waiting_by_domain": waiting, **meta,
            }

    def self_check(self) -> dict[str, Any]:
        task = ProviderTaskContext(task_id="sqlite-self-check", tenant_id="synthetic")
        first = self.acquire(
            task=task, domain="read", owner_id="self-check", lease_ttl_seconds=10,
            timeout_seconds=0, check_task=lambda _: None, request_id="sqlite-self-check-request",
        )
        replay = self.acquire(
            task=task, domain="read", owner_id="self-check", lease_ttl_seconds=10,
            timeout_seconds=0, check_task=lambda _: None, request_id="sqlite-self-check-request",
        )
        if replay != first or not self.validate(first) or not self.release(first):
            raise BackupStorageError("SQLite lease idempotency/validation/release self-check failed")
        second = self.acquire(
            task=ProviderTaskContext(task_id="sqlite-self-check-next", tenant_id="synthetic"),
            domain="read", owner_id="self-check", lease_ttl_seconds=10,
            timeout_seconds=0, check_task=lambda _: None, request_id="sqlite-self-check-next",
        )
        if second.fencing_token <= first.fencing_token:
            raise BackupStorageError("SQLite fencing sequence did not increase")
        self.release(second)
        return {
            "result": "PASS", "backend": "SQLITE_LOCAL_FILE",
            "idempotent_replay": "PASS", "durable_fencing_sequence": "PASS",
            "lease_lifecycle": "PASS", "scope": "same-host local file; not multi-host HA",
            "snapshot": self.snapshot(),
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SQLite Provider admission coordinator self-check")
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--report-json", type=Path)
    args = parser.parse_args(argv)
    if not args.self_check:
        parser.error("--self-check is required")
    with tempfile.TemporaryDirectory(prefix="ch17-provider-admission-") as tmp:
        report = SQLiteProviderAdmissionCoordinator(Path(tmp) / "coordinator.sqlite3").self_check()
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.report_json:
        args.report_json.parent.mkdir(parents=True, exist_ok=True)
        args.report_json.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
