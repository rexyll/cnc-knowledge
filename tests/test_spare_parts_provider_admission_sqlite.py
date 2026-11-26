from __future__ import annotations
import multiprocessing
import tempfile
import threading
import time
import unittest
from pathlib import Path

from scripts.spare_parts_backup_storage_adapter import (
    BackupStorageError, InMemoryProviderAdmissionCoordinator,
    ProviderAdmissionIdempotencyConflictError, ProviderAdmissionRequestFinalizedError,
    ProviderBulkheadFullError, ProviderCoordinatorUnavailableError, ProviderTaskContext,
)
from scripts.spare_parts_provider_admission_sqlite import SQLiteProviderAdmissionCoordinator


def _sqlite_process_worker(database_path, barrier, release_event, result_queue, worker_id):
    coordinator = SQLiteProviderAdmissionCoordinator(
        database_path,
        global_limits={"read": 1, "write": 1, "multipart": 1, "inventory": 1},
        tenant_limits={"tenant-A": {"read": 1}},
        max_waiters=8,
    )
    barrier.wait(timeout=10)
    try:
        lease = coordinator.acquire(
            task=ProviderTaskContext(f"process-{worker_id}", f"tenant-{worker_id}"),
            domain="read", owner_id=f"owner-{worker_id}", lease_ttl_seconds=10,
            timeout_seconds=0, check_task=lambda _: None, request_id=f"process-{worker_id}",
        )
    except Exception as exc:
        result_queue.put(("rejected", type(exc).__name__))
        return
    result_queue.put(("acquired", lease.fencing_token))
    release_event.wait(timeout=10)
    coordinator.release(lease)


class SQLiteProviderAdmissionCoordinatorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.database_path = str(Path(self.tmp.name) / "admission.sqlite3")
        self.policy = {
            "global_limits": {"read": 1, "write": 1, "multipart": 1, "inventory": 1},
            "tenant_limits": {"tenant-A": {"read": 1}},
            "max_waiters": 8,
        }
        self.coordinator = SQLiteProviderAdmissionCoordinator(self.database_path, **self.policy)

    def tearDown(self):
        self.tmp.cleanup()

    @staticmethod
    def task(task_id="task-1", tenant_id="tenant-A"):
        return ProviderTaskContext(task_id=task_id, tenant_id=tenant_id)

    def acquire(self, *, request_id="request-1", task=None, coordinator=None, timeout=0):
        return (coordinator or self.coordinator).acquire(
            task=task or self.task(), domain="read", owner_id="owner-1",
            lease_ttl_seconds=30, timeout_seconds=timeout,
            check_task=lambda _: None, request_id=request_id,
        )

    def test_request_idempotency_conflict_and_finalized_key_rejection(self):
        lease = self.acquire()
        self.assertEqual(self.acquire(), lease)
        with self.assertRaises(ProviderAdmissionIdempotencyConflictError):
            self.acquire(task=self.task(task_id="different"))
        self.assertTrue(self.coordinator.release(lease))
        with self.assertRaises(ProviderAdmissionRequestFinalizedError):
            self.acquire()
        self.assertEqual(self.coordinator.snapshot()["active_by_domain"]["read"], 0)

    def test_lost_acquire_response_recovers_same_lease_after_database_reopen(self):
        self.coordinator.inject_failure("acquire_response")
        with self.assertRaises(ProviderCoordinatorUnavailableError) as caught:
            self.acquire(request_id="lost-response")
        self.assertEqual(caught.exception.phase, "acquire_response")
        self.assertTrue(caught.exception.reservation_outcome_unknown)
        self.assertEqual(caught.exception.request_id, "lost-response")
        reopened = SQLiteProviderAdmissionCoordinator(self.database_path, **self.policy)
        recovered = self.acquire(coordinator=reopened, request_id=caught.exception.request_id)
        self.assertEqual(recovered.fencing_token, 1)
        self.assertEqual(reopened.snapshot()["active_by_domain"]["read"], 1)
        self.assertTrue(reopened.release(recovered))

    def test_active_lease_and_fencing_sequence_survive_coordinator_recreation(self):
        first = self.acquire(request_id="persist-1")
        reopened = SQLiteProviderAdmissionCoordinator(self.database_path, **self.policy)
        self.assertTrue(reopened.validate(first))
        self.assertTrue(reopened.release(first))
        second = self.acquire(
            coordinator=reopened, request_id="persist-2", task=self.task("task-2")
        )
        self.assertGreater(second.fencing_token, first.fencing_token)
        self.assertFalse(reopened.validate(first))
        self.assertTrue(reopened.release(second))

    def test_expiry_is_reclaimed_and_fencing_is_monotonic_after_restart(self):
        class FakeClock:
            now = 1000.0
            def __call__(self): return self.now
            def advance(self, seconds): self.now += seconds

        clock = FakeClock()
        expiry_path = str(Path(self.tmp.name) / "expiry.sqlite3")
        first_coordinator = SQLiteProviderAdmissionCoordinator(
            expiry_path, **self.policy, clock_fn=clock
        )
        first = first_coordinator.acquire(
            task=self.task(), domain="read", owner_id="owner-1",
            lease_ttl_seconds=2, timeout_seconds=0, check_task=lambda _: None,
            request_id="expiry-1",
        )
        clock.advance(2.1)
        reopened = SQLiteProviderAdmissionCoordinator(expiry_path, **self.policy, clock_fn=clock)
        self.assertFalse(reopened.validate(first))
        second = reopened.acquire(
            task=self.task("after-expiry"), domain="read", owner_id="owner-2",
            lease_ttl_seconds=2, timeout_seconds=0, check_task=lambda _: None,
            request_id="expiry-2",
        )
        self.assertGreater(second.fencing_token, first.fencing_token)
        self.assertEqual(reopened.snapshot()["expired_leases"], 1)
        self.assertTrue(reopened.release(second))

    def test_two_independent_coordinator_instances_share_capacity(self):
        holder = self.acquire(request_id="holder")
        other = SQLiteProviderAdmissionCoordinator(self.database_path, **self.policy)
        with self.assertRaises(ProviderBulkheadFullError):
            self.acquire(coordinator=other, request_id="blocked", task=self.task("blocked", "tenant-B"))
        self.assertTrue(self.coordinator.release(holder))
        admitted = self.acquire(coordinator=other, request_id="blocked", task=self.task("blocked", "tenant-B"))
        self.assertTrue(other.release(admitted))

    def test_lease_renewal_persists_new_expiry_and_fences_old_lease_value(self):
        class FakeClock:
            now = 2000.0
            def __call__(self):
                return self.now
            def advance(self, seconds):
                self.now += seconds

        clock = FakeClock()
        renewal_path = str(Path(self.tmp.name) / "renewal.sqlite3")
        coordinator = SQLiteProviderAdmissionCoordinator(
            renewal_path, **self.policy, clock_fn=clock
        )
        old = coordinator.acquire(
            task=self.task(), domain="read", owner_id="owner-1",
            lease_ttl_seconds=2, timeout_seconds=0, check_task=lambda _: None,
            request_id="renewal-1",
        )
        renewed = coordinator.renew(old, lease_ttl_seconds=5)
        self.assertIsNotNone(renewed)
        self.assertFalse(coordinator.validate(old))
        reopened = SQLiteProviderAdmissionCoordinator(
            renewal_path, **self.policy, clock_fn=clock
        )
        clock.advance(3)
        self.assertTrue(reopened.validate(renewed))
        self.assertTrue(reopened.release(renewed))

    def test_policy_mismatch_is_rejected_for_same_database(self):
        with self.assertRaises(BackupStorageError):
            SQLiteProviderAdmissionCoordinator(
                self.database_path,
                global_limits={"read": 9, "write": 1, "multipart": 1, "inventory": 1},
                tenant_limits={"tenant-A": {"read": 1}}, max_waiters=8,
            )

    def test_waiter_is_visible_across_instances_and_removed_after_admission(self):
        holder = self.acquire(request_id="queue-holder")
        other = SQLiteProviderAdmissionCoordinator(
            self.database_path, **self.policy, poll_interval_seconds=0.01
        )
        values, errors = [], []

        def waiting():
            try:
                values.append(self.acquire(
                    coordinator=other, request_id="queue-waiter",
                    task=self.task("waiter", "tenant-B"), timeout=2,
                ))
            except Exception as exc:
                errors.append(exc)

        thread = threading.Thread(target=waiting)
        thread.start()
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline and not self.coordinator.snapshot()["waiting_by_domain"]["read"]:
            time.sleep(0.01)
        self.assertEqual(self.coordinator.snapshot()["waiting_by_domain"]["read"], 1)
        self.assertTrue(self.coordinator.release(holder))
        thread.join(timeout=3)
        self.assertFalse(thread.is_alive())
        self.assertEqual(errors, [])
        self.assertEqual(len(values), 1)
        self.assertEqual(self.coordinator.snapshot()["waiting_by_domain"]["read"], 0)
        self.assertTrue(other.release(values[0]))

    def test_multiple_processes_cannot_oversubscribe_the_same_database(self):
        context = multiprocessing.get_context("spawn")
        barrier, release_event, results = context.Barrier(3), context.Event(), context.Queue()
        processes = [
            context.Process(target=_sqlite_process_worker,
                            args=(self.database_path, barrier, release_event, results, idx))
            for idx in range(2)
        ]
        for process in processes:
            process.start()
        barrier.wait(timeout=10)
        outcomes = [results.get(timeout=15) for _ in processes]
        release_event.set()
        for process in processes:
            process.join(timeout=10)
        for process in processes:
            if process.is_alive():
                process.terminate()
                process.join(timeout=2)
        self.assertTrue(all(p.exitcode == 0 for p in processes))
        self.assertEqual(sum(1 for status, _ in outcomes if status == "acquired"), 1)
        self.assertEqual(sum(1 for status, _ in outcomes if status == "rejected"), 1)
        self.assertEqual(self.coordinator.snapshot()["active_by_domain"]["read"], 0)

    def test_in_memory_request_idempotency_and_finalized_key_rejection(self):
        coordinator = InMemoryProviderAdmissionCoordinator(
            global_limits={"read": 1, "write": 1, "multipart": 1, "inventory": 1}
        )
        task = self.task("memory-id")
        lease = coordinator.acquire(
            task=task, domain="read", owner_id="owner", lease_ttl_seconds=20,
            timeout_seconds=0, check_task=lambda _: None, request_id="memory-key",
        )
        replay = coordinator.acquire(
            task=task, domain="read", owner_id="owner", lease_ttl_seconds=20,
            timeout_seconds=0, check_task=lambda _: None, request_id="memory-key",
        )
        self.assertEqual(replay, lease)
        self.assertTrue(coordinator.release(lease))
        with self.assertRaises(ProviderAdmissionRequestFinalizedError):
            coordinator.acquire(
                task=task, domain="read", owner_id="owner", lease_ttl_seconds=20,
                timeout_seconds=0, check_task=lambda _: None, request_id="memory-key",
            )

    def test_in_memory_response_loss_replays_request_id(self):
        coordinator = InMemoryProviderAdmissionCoordinator()
        task = self.task("memory-loss")
        coordinator.inject_failure("acquire_response")
        with self.assertRaises(ProviderCoordinatorUnavailableError) as caught:
            coordinator.acquire(
                task=task, domain="read", owner_id="owner", lease_ttl_seconds=20,
                timeout_seconds=0, check_task=lambda _: None, request_id="memory-loss",
            )
        replay = coordinator.acquire(
            task=task, domain="read", owner_id="owner", lease_ttl_seconds=20,
            timeout_seconds=0, check_task=lambda _: None, request_id=caught.exception.request_id,
        )
        self.assertEqual(replay.fencing_token, 1)
        self.assertTrue(coordinator.release(replay))


if __name__ == "__main__":
    unittest.main()
