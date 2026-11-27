from __future__ import annotations

import tempfile
import threading
import time
import unittest
from pathlib import Path

from scripts.spare_parts_backup_storage_adapter import (
    BackupStorageError,
    ProviderAdmissionQueueFullError,
    ProviderBulkheadFullError,
    ProviderTaskContext,
)
from scripts.spare_parts_provider_authority_store import (
    AuthorityStorePut,
    EtcdV3CoordinatorAuthorityStore,
    InMemoryEtcdV3Client,
    SQLiteCoordinatorAuthorityStore,
)
from scripts.spare_parts_provider_unified_admission_store import (
    StoreBackedProviderAdmissionCoordinator,
)


class MutableClock:
    def __init__(self, value: float = 1000.0):
        self.value = value

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


class IsolatedNamespaceTests(unittest.TestCase):
    def test_custom_namespaces_are_disjoint_and_default_prefix_is_unchanged(self):
        store = EtcdV3CoordinatorAuthorityStore(InMemoryEtcdV3Client())
        policy = {
            "global_limits": {"read": 2},
            "max_waiters": 0,
            "namespace_prefix": b"/cnc/migration/isolated/drill-a/",
        }
        first = StoreBackedProviderAdmissionCoordinator(store, **policy)
        second = StoreBackedProviderAdmissionCoordinator(
            store, **{**policy, "namespace_prefix": b"/cnc/migration/isolated/drill-b/"}
        )
        self.assertNotEqual(first._STATE_KEY, second._STATE_KEY)
        self.assertEqual(first._PREFIX, b"/cnc/migration/isolated/drill-a/")
        self.assertEqual(second._PREFIX, b"/cnc/migration/isolated/drill-b/")
        self.assertEqual(
            StoreBackedProviderAdmissionCoordinator._PREFIX,
            b"/cnc/admission/unified/v2/",
        )

    def test_custom_namespace_rejects_production_and_ambiguous_prefixes(self):
        store = EtcdV3CoordinatorAuthorityStore(InMemoryEtcdV3Client())
        for prefix in (
            b"/cnc/admission/unified/v2/",
            b"/cnc/migration/isolated/",
            b"/cnc/migration/isolated/a/b/",
            b"/cnc/migration/isolated/../prod/",
            "/cnc/migration/isolated/unicode-测试/".encode(),
        ):
            with self.subTest(prefix=prefix):
                with self.assertRaises(BackupStorageError):
                    StoreBackedProviderAdmissionCoordinator(
                        store, namespace_prefix=prefix
                    )


class StoreBackedAdmissionSchedulerContract:
    def store(self):
        raise NotImplementedError

    def fresh_store(self):
        raise NotImplementedError

    def setUpContract(self):
        self.clock = MutableClock()
        self.policy = {
            "global_limits": {"read": 1, "write": 1, "multipart": 1, "inventory": 1},
            "tenant_limits": {"tenant-A": {"read": 1}},
            "max_waiters": 3,
            "aging_interval_seconds": 1.0,
            "poll_interval_seconds": 0.005,
            "clock_fn": self.clock,
        }
        self.scheduler = StoreBackedProviderAdmissionCoordinator(
            self.store(), **self.policy
        )

    def task(self, task_id="task-1", tenant_id="tenant-A", priority=0):
        return ProviderTaskContext(task_id=task_id, tenant_id=tenant_id, priority=priority)

    def acquire(self, request_id, *, tenant="tenant-A", task_id=None, domain="read",
                timeout=0, priority=0, ttl=30):
        return self.scheduler.acquire(
            task=self.task(task_id or request_id, tenant, priority),
            domain=domain, owner_id="owner-"+tenant,
            lease_ttl_seconds=ttl, timeout_seconds=timeout,
            check_task=lambda _: None, request_id=request_id,
        )

    def test_global_and_tenant_capacity_are_atomic_across_instances(self):
        store = self.fresh_store()
        policy = dict(self.policy)
        policy["global_limits"] = {
            "read": 2, "write": 1, "multipart": 1, "inventory": 1
        }
        a = StoreBackedProviderAdmissionCoordinator(store, **policy)
        b = StoreBackedProviderAdmissionCoordinator(store, **policy)
        first = a.acquire(
            task=self.task("task-1", "tenant-A"), domain="read", owner_id="owner-A",
            lease_ttl_seconds=30, timeout_seconds=0, check_task=lambda _: None,
            request_id="r-1",
        )
        with self.assertRaises(ProviderBulkheadFullError):
            b.acquire(
                task=self.task("task-2", "tenant-A"), domain="read", owner_id="owner-A",
                lease_ttl_seconds=30, timeout_seconds=0, check_task=lambda _: None,
                request_id="r-2",
            )
        second = b.acquire(
            task=self.task("task-3", "tenant-B"), domain="read", owner_id="owner-B",
            lease_ttl_seconds=30, timeout_seconds=0, check_task=lambda _: None,
            request_id="r-3",
        )
        self.assertEqual(first.fencing_token, 1)
        self.assertEqual(second.fencing_token, 2)
        snap = a.snapshot()
        self.assertEqual(snap["active_by_domain"]["read"], 2)
        self.assertEqual(snap["active_by_tenant_domain"]["tenant-A:read"], 1)

    def test_queue_is_bounded_and_fair_by_priority_then_aging(self):
        active = self.acquire("holder")
        results = []
        errors = []

        def wait_for(request_id, priority):
            try:
                results.append(self.acquire(
                    request_id, tenant="tenant-B", timeout=3, priority=priority
                ))
            except Exception as exc:
                errors.append(exc)

        low = threading.Thread(target=wait_for, args=("low", 0), daemon=True)
        high = threading.Thread(target=wait_for, args=("high", 5), daemon=True)
        low.start()
        deadline = time.time() + 2
        while self.scheduler.snapshot()["queue_depth"] != 1 and time.time() < deadline:
            time.sleep(0.005)
        high.start()
        deadline = time.time() + 2
        while self.scheduler.snapshot()["queue_depth"] != 2 and time.time() < deadline:
            time.sleep(0.005)
        self.assertEqual(self.scheduler.snapshot()["queue_depth"], 2)
        self.assertTrue(self.scheduler.release(active))
        deadline = time.time() + 2
        while not results and time.time() < deadline:
            time.sleep(0.005)
        self.assertTrue(results)
        self.assertEqual(results[0].fencing_token, 2)  # high-priority waiter
        self.scheduler.release(results[0])
        low.join(timeout=3)
        high.join(timeout=3)
        self.assertFalse(errors)
        self.assertEqual(len(results), 2)
        for lease in results:
            self.scheduler.release(lease)

    def test_queue_limit_fails_fast_without_leaving_waiter(self):
        store = self.fresh_store()
        policy = dict(self.policy)
        policy["max_waiters"] = 1
        scheduler = StoreBackedProviderAdmissionCoordinator(store, **policy)
        active = scheduler.acquire(
            task=self.task("holder", "tenant-A"), domain="read", owner_id="owner-A",
            lease_ttl_seconds=30, timeout_seconds=0, check_task=lambda _: None,
            request_id="holder",
        )
        acquired = []
        errors = []

        def wait_once():
            try:
                acquired.append(scheduler.acquire(
                    task=self.task("queued-1", "tenant-B"), domain="read",
                    owner_id="owner-B", lease_ttl_seconds=30, timeout_seconds=2,
                    check_task=lambda _: None, request_id="queued-1",
                ))
            except Exception as exc:
                errors.append(exc)

        waiter = threading.Thread(target=wait_once, daemon=True)
        waiter.start()
        deadline = time.time() + 2
        while scheduler.snapshot()["queue_depth"] != 1 and time.time() < deadline:
            time.sleep(0.005)
        self.assertEqual(scheduler.snapshot()["queue_depth"], 1)
        with self.assertRaises(ProviderAdmissionQueueFullError):
            scheduler.acquire(
                task=self.task("queued-2", "tenant-B"), domain="read",
                owner_id="owner-B", lease_ttl_seconds=30, timeout_seconds=1,
                check_task=lambda _: None, request_id="queued-2",
            )
        self.assertEqual(scheduler.snapshot()["queue_depth"], 1)
        self.assertTrue(scheduler.release(active))
        waiter.join(timeout=3)
        self.assertFalse(waiter.is_alive())
        self.assertFalse(errors)
        self.assertEqual(len(acquired), 1)
        self.assertTrue(scheduler.release(acquired[0]))
        self.assertEqual(scheduler.snapshot()["queue_depth"], 0)

    def test_expired_lease_is_reclaimed_before_capacity_decision(self):
        first = self.acquire("short", ttl=2)
        self.clock.advance(3)
        second = self.acquire("after-expiry", tenant="tenant-B")
        self.assertFalse(self.scheduler.validate(first))
        self.assertEqual(second.fencing_token, first.fencing_token + 1)
        self.assertEqual(self.scheduler.snapshot()["counters"]["expired_leases"], 1)

    def test_renew_release_and_authority_guard_share_the_same_store(self):
        lease = self.acquire("guard")
        protected = self.scheduler.transact_with_active_lease(
            lease, [AuthorityStorePut(b"/authority/protected/1", b"ok")]
        )
        self.assertTrue(protected.succeeded)
        renewed = self.scheduler.renew(lease, lease_ttl_seconds=45)
        self.assertIsNotNone(renewed)
        self.assertFalse(self.scheduler.validate(lease))
        self.assertTrue(self.scheduler.validate(renewed))
        old_guard = self.scheduler.active_lease_compares(renewed)
        self.assertTrue(self.scheduler.release(renewed))
        stale = self.store().transact(
            old_guard, [AuthorityStorePut(b"/authority/protected/2", b"must-not-write")]
        )
        self.assertFalse(stale.succeeded)

    def test_same_request_is_idempotent_and_concurrent_acquisitions_do_not_oversubscribe(self):
        store = self.store()
        a = StoreBackedProviderAdmissionCoordinator(store, **self.policy)
        b = StoreBackedProviderAdmissionCoordinator(store, **self.policy)
        args = dict(
            task=self.task("same", "tenant-A"), domain="write", owner_id="owner-A",
            lease_ttl_seconds=20, timeout_seconds=0, check_task=lambda _: None,
            request_id="same-request",
        )
        leases = []
        errors = []

        def run(scheduler):
            try:
                leases.append(scheduler.acquire(**args))
            except Exception as exc:
                errors.append(exc)
        threads = [threading.Thread(target=run, args=(scheduler,)) for scheduler in (a, b)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=5)
        self.assertFalse(errors)
        self.assertEqual(len(leases), 2)
        self.assertEqual(leases[0], leases[1])
        self.assertEqual(leases[0].fencing_token, 1)
        self.assertTrue(a.release(leases[0]))

        # Different request IDs against a one-slot domain must have one winner.
        leases.clear()
        errors.clear()
        barrier = threading.Barrier(3)

        def race(scheduler, request_id):
            barrier.wait()
            try:
                leases.append(scheduler.acquire(
                    task=self.task(request_id, "tenant-A"), domain="write",
                    owner_id="owner-A", lease_ttl_seconds=20, timeout_seconds=0,
                    check_task=lambda _: None, request_id=request_id,
                ))
            except Exception as exc:
                errors.append(exc)
        threads = [
            threading.Thread(target=race, args=(a, "race-A")),
            threading.Thread(target=race, args=(b, "race-B")),
        ]
        for thread in threads:
            thread.start()
        barrier.wait()
        for thread in threads:
            thread.join(timeout=5)
        self.assertEqual(len(leases), 1)
        self.assertEqual(len(errors), 1)
        self.assertTrue(a.release(leases[0]))


class SQLiteUnifiedAdmissionTests(StoreBackedAdmissionSchedulerContract, unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self._store = None
        self.clock = MutableClock()
        self.policy = {
            "global_limits": {"read": 1, "write": 1, "multipart": 1, "inventory": 1},
            "tenant_limits": {"tenant-A": {"read": 1}},
            "max_waiters": 3,
            "aging_interval_seconds": 1.0,
            "poll_interval_seconds": 0.005,
            "clock_fn": self.clock,
        }
        self._store = SQLiteCoordinatorAuthorityStore(
            Path(self.tmp.name) / "unified.sqlite3", clock_fn=self.clock
        )
        self.scheduler = StoreBackedProviderAdmissionCoordinator(self._store, **self.policy)

    def tearDown(self):
        self.tmp.cleanup()

    def store(self):
        return self._store

    def fresh_store(self):
        return SQLiteCoordinatorAuthorityStore(
            Path(self.tmp.name) / "variant.sqlite3", clock_fn=self.clock
        )


class EtcdUnifiedAdmissionTests(StoreBackedAdmissionSchedulerContract, unittest.TestCase):
    def setUp(self):
        self.clock = MutableClock()
        self._client = InMemoryEtcdV3Client(clock_fn=self.clock)
        self._store = EtcdV3CoordinatorAuthorityStore(self._client)
        self.policy = {
            "global_limits": {"read": 1, "write": 1, "multipart": 1, "inventory": 1},
            "tenant_limits": {"tenant-A": {"read": 1}},
            "max_waiters": 3,
            "aging_interval_seconds": 1.0,
            "poll_interval_seconds": 0.005,
            "clock_fn": self.clock,
        }
        self.scheduler = StoreBackedProviderAdmissionCoordinator(self._store, **self.policy)

    def tearDown(self):
        pass

    def store(self):
        return self._store

    def fresh_store(self):
        client = InMemoryEtcdV3Client(clock_fn=self.clock)
        return EtcdV3CoordinatorAuthorityStore(client)
