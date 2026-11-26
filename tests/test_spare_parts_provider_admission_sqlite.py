from __future__ import annotations
import multiprocessing
import sqlite3
import tempfile
import threading
import time
import unittest

from scripts.spare_parts_fencing_attestation import verify_fencing_attestation_signature
from pathlib import Path

from scripts.spare_parts_backup_storage_adapter import (
    BackupStorageError, InMemoryProviderAdmissionCoordinator,
    ProviderAdmissionIdempotencyConflictError, ProviderAdmissionRequestFinalizedError,
    ProviderAdmissionQueueFullError, ProviderBulkheadFullError,
    ProviderCoordinatorUnavailableError, ProviderTaskContext,
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

    def test_signed_attestation_is_bound_to_active_lease_and_refuses_after_release(self):
        signer_secret = "coordinator-signing-secret-32-bytes-minimum-value"
        coordinator = SQLiteProviderAdmissionCoordinator(
            self.database_path, **self.policy,
            attestation_issuer_id="unit-test-coordinator",
            attestation_key_id="unit-test-kid-v1",
            attestation_secret=signer_secret,
            attestation_ttl_seconds=10,
        )
        task = ProviderTaskContext("attested-task", "tenant-A")
        lease = coordinator.acquire(
            task=task, domain="write", owner_id="attested-owner",
            lease_ttl_seconds=30, timeout_seconds=0,
            check_task=lambda _: None, request_id="attested-request",
        )
        proof = coordinator.issue_fencing_attestation(
            lease, fencing_scope="cnc/ch17/pkg-1",
            resource_key="cnc/ch17/pkg-1/object.bin",
            operation="object:put_if_absent", idempotency_key="attested-idem",
        )
        claims, key_id = verify_fencing_attestation_signature(
            proof, trusted_keys={"unit-test-kid-v1": signer_secret}
        )
        self.assertEqual(key_id, "unit-test-kid-v1")
        self.assertEqual(claims["tenant_id"], "tenant-A")
        self.assertEqual(claims["fencing_scope"], "cnc/ch17/pkg-1")
        self.assertEqual(claims["resource_key"], "cnc/ch17/pkg-1/object.bin")
        self.assertEqual(claims["fencing_token"], lease.fencing_token)
        self.assertEqual(claims["lease_id"], lease.lease_id)
        self.assertLessEqual(claims["expires_at"], lease.expires_at)
        self.assertTrue(coordinator.release(lease))
        with self.assertRaises(BackupStorageError):
            coordinator.issue_fencing_attestation(
                lease, fencing_scope="cnc/ch17/pkg-1",
                resource_key="cnc/ch17/pkg-1/late.bin",
                operation="object:put_if_absent", idempotency_key="late-idem",
            )

    def test_coordinator_refuses_to_sign_a_resource_outside_lease_scope(self):
        signer_secret = "coordinator-signing-secret-32-bytes-minimum-value"
        coordinator = SQLiteProviderAdmissionCoordinator(
            self.database_path, **self.policy,
            attestation_issuer_id="unit-test-coordinator",
            attestation_key_id="unit-test-kid-v1",
            attestation_secret=signer_secret,
        )
        lease = coordinator.acquire(
            task=ProviderTaskContext("attested-task", "tenant-A"),
            domain="write", owner_id="attested-owner",
            lease_ttl_seconds=30, timeout_seconds=0,
            check_task=lambda _: None, request_id="attested-request-scope",
        )
        with self.assertRaises(BackupStorageError):
            coordinator.issue_fencing_attestation(
                lease, fencing_scope="cnc/ch17/pkg-1",
                resource_key="cnc/ch17/pkg-2/escape.bin",
                operation="object:put_if_absent", idempotency_key="escape-idem",
            )
        self.assertTrue(coordinator.release(lease))

    def test_online_attestation_status_tracks_active_and_released_lease(self):
        signer_secret = "online-status-coordinator-signing-secret-32-bytes"
        coordinator = SQLiteProviderAdmissionCoordinator(
            self.database_path, **self.policy,
            attestation_issuer_id="online-status-coordinator",
            attestation_key_id="online-status-key",
            attestation_secret=signer_secret,
        )
        lease = coordinator.acquire(
            task=ProviderTaskContext("online-status-task", "tenant-A"),
            domain="write", owner_id="online-status-owner",
            lease_ttl_seconds=30, timeout_seconds=0,
            check_task=lambda _: None, request_id="online-status-1",
        )
        claims = {
            "iss": "online-status-coordinator", "lease_id": lease.lease_id,
            "owner_id": lease.owner_id, "tenant_id": lease.tenant_id,
            "domain": lease.domain, "fencing_token": lease.fencing_token,
            "issued_at": time.time(), "expires_at": lease.expires_at,
        }
        self.assertTrue(coordinator.is_attestation_active(claims))
        self.assertTrue(coordinator.release(lease))
        self.assertFalse(coordinator.is_attestation_active(claims))

    def test_online_attestation_status_failure_is_explicit(self):
        signer_secret = "online-status-coordinator-signing-secret-32-bytes"
        coordinator = SQLiteProviderAdmissionCoordinator(
            self.database_path, **self.policy,
            attestation_issuer_id="online-status-coordinator",
            attestation_key_id="online-status-key",
            attestation_secret=signer_secret,
        )
        coordinator.inject_failure("attestation_status")
        with self.assertRaises(ProviderCoordinatorUnavailableError):
            coordinator.is_attestation_active({"lease_id": "synthetic-missing"})

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

    def test_queue_overflow_is_fail_fast_and_rejection_counter_persists(self):
        zero_wait_policy = dict(self.policy)
        zero_wait_policy["max_waiters"] = 0
        path = str(Path(self.tmp.name) / "zero-waiters.sqlite3")
        coordinator = SQLiteProviderAdmissionCoordinator(path, **zero_wait_policy)
        holder = coordinator.acquire(
            task=self.task("queue-holder"), domain="read", owner_id="holder",
            lease_ttl_seconds=30, timeout_seconds=0, check_task=lambda _: None,
            request_id="queue-holder",
        )
        with self.assertRaises(ProviderAdmissionQueueFullError):
            coordinator.acquire(
                task=self.task("queue-overflow", "tenant-B"), domain="read",
                owner_id="overflow", lease_ttl_seconds=30, timeout_seconds=0,
                check_task=lambda _: None, request_id="queue-overflow",
            )
        snapshot = coordinator.snapshot()
        self.assertEqual(snapshot["active_by_domain"]["read"], 1)
        self.assertEqual(snapshot["waiting_by_domain"]["read"], 0)
        self.assertEqual(snapshot["rejected_queue"], 1)
        self.assertTrue(coordinator.release(holder))

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



    def test_online_backup_is_consistent_and_validates_active_lease_snapshot(self):
        lease = self.acquire(request_id="backup-active")
        backup = Path(self.tmp.name) / "coordinator-online-backup.sqlite3"
        report = self.coordinator.backup_to(backup)
        self.assertEqual(report["result"], "PASS")
        self.assertEqual(report["integrity_check"], "ok")
        self.assertEqual(report["active_leases"], 1)
        self.assertTrue(report["sha256"])
        self.assertEqual(SQLiteProviderAdmissionCoordinator.validate_backup(backup)["active_leases"], 1)
        self.assertTrue(self.coordinator.release(lease))
        backup_coordinator = SQLiteProviderAdmissionCoordinator(backup, **self.policy)
        self.assertTrue(backup_coordinator.validate(lease))
        self.assertTrue(backup_coordinator.release(lease))

    def test_corrupt_backup_is_rejected(self):
        broken = Path(self.tmp.name) / "corrupt.sqlite3"
        broken.write_bytes(b"not-a-sqlite-database")
        with self.assertRaises(BackupStorageError):
            SQLiteProviderAdmissionCoordinator.validate_backup(broken)

    def test_backup_with_fencing_counter_behind_issued_token_is_rejected(self):
        lease = self.acquire(request_id="counter-integrity")
        backup = Path(self.tmp.name) / "counter-integrity.sqlite3"
        self.coordinator.backup_to(backup)
        with sqlite3.connect(backup) as connection:
            connection.execute(
                "UPDATE coordinator_meta SET value='0' WHERE key='next_fencing_token'"
            )
        with self.assertRaises(BackupStorageError):
            SQLiteProviderAdmissionCoordinator.validate_backup(backup)
        self.assertTrue(self.coordinator.release(lease))

    def test_restore_invalidates_leases_clears_waiters_and_seeds_external_fencing_floor(self):
        holder = self.acquire(request_id="restore-holder")
        waiter_values, waiter_errors = [], []

        def wait_for_capacity():
            try:
                lease = self.acquire(
                    request_id="restore-waiter",
                    task=self.task("restore-waiter", "tenant-B"),
                    timeout=3,
                )
                waiter_values.append(lease)
                self.coordinator.release(lease)
            except Exception as exc:
                waiter_errors.append(exc)

        thread = threading.Thread(target=wait_for_capacity)
        thread.start()
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            if self.coordinator.snapshot()["waiting_by_domain"]["read"] == 1:
                break
            time.sleep(0.01)
        self.assertEqual(self.coordinator.snapshot()["waiting_by_domain"]["read"], 1)
        backup = Path(self.tmp.name) / "restore-source.sqlite3"
        self.coordinator.backup_to(backup)
        self.assertTrue(self.coordinator.release(holder))
        thread.join(timeout=4)
        self.assertFalse(thread.is_alive())
        self.assertEqual(waiter_errors, [])
        self.assertEqual(len(waiter_values), 1)

        destination = Path(self.tmp.name) / "restored-coordinator.sqlite3"
        report = self.coordinator.restore_to_new_database(
            backup, destination,
            external_fencing_floor=90,
            fencing_reconciliation_ref="SYNTHETIC-EXTERNAL-HIGH-WATER-RECORD-001",
        )
        self.assertEqual(report["result"], "PREPARED_NEW_DATABASE")
        self.assertEqual(report["active_leases_invalidated"], 1)
        self.assertEqual(report["waiters_cleared"], 1)
        self.assertFalse(report["cutover_performed"])
        restored = SQLiteProviderAdmissionCoordinator(destination, **self.policy)
        self.assertEqual(restored.snapshot()["active_by_domain"]["read"], 0)
        self.assertEqual(restored.snapshot()["waiting_by_domain"]["read"], 0)
        self.assertFalse(restored.validate(holder))
        with self.assertRaises(ProviderAdmissionRequestFinalizedError):
            self.acquire(
                coordinator=restored, request_id="restore-holder",
                task=self.task("task-1", "tenant-A"),
            )
        next_lease = self.acquire(
            coordinator=restored, request_id="after-restore",
            task=self.task("after-restore", "tenant-A"),
        )
        self.assertGreater(next_lease.fencing_token, 90)
        self.assertTrue(restored.release(next_lease))

    def test_restore_requires_external_reconciliation_and_matching_policy(self):
        backup = Path(self.tmp.name) / "restore-policy-source.sqlite3"
        self.coordinator.backup_to(backup)
        destination = Path(self.tmp.name) / "restore-no-floor.sqlite3"
        with self.assertRaises(BackupStorageError):
            self.coordinator.restore_to_new_database(
                backup, destination, external_fencing_floor=None,
                fencing_reconciliation_ref="SYNTHETIC-REF",
            )
        other_path = Path(self.tmp.name) / "other-policy.sqlite3"
        other = SQLiteProviderAdmissionCoordinator(
            other_path,
            global_limits={"read": 2, "write": 1, "multipart": 1, "inventory": 1},
            tenant_limits={"tenant-A": {"read": 1}}, max_waiters=8,
        )
        with self.assertRaises(BackupStorageError):
            other.restore_to_new_database(
                backup, Path(self.tmp.name) / "policy-mismatch-restore.sqlite3",
                external_fencing_floor=0,
                fencing_reconciliation_ref="SYNTHETIC-REF",
            )

    def test_backup_and_restore_never_overwrite_existing_or_live_database_paths(self):
        with self.assertRaises(BackupStorageError):
            self.coordinator.backup_to(self.database_path)
        backup = Path(self.tmp.name) / "immutable-backup.sqlite3"
        self.coordinator.backup_to(backup)
        with self.assertRaises(BackupStorageError):
            self.coordinator.backup_to(backup)
        with self.assertRaises(BackupStorageError):
            self.coordinator.restore_to_new_database(
                backup, self.database_path,
                external_fencing_floor=0,
                fencing_reconciliation_ref="SYNTHETIC-REF",
            )
        existing = Path(self.tmp.name) / "preexisting.sqlite3"
        existing.write_bytes(b"preexisting")
        with self.assertRaises(BackupStorageError):
            self.coordinator.restore_to_new_database(
                backup, existing,
                external_fencing_floor=0,
                fencing_reconciliation_ref="SYNTHETIC-REF",
            )


if __name__ == "__main__":
    unittest.main()
