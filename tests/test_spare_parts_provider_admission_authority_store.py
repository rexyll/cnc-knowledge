from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.spare_parts_backup_storage_adapter import ProviderAdmissionLease, ProviderTaskContext
from scripts.spare_parts_provider_admission_authority_store import (
    AdmissionLeaseConflictError,
    AdmissionLeaseFinalizedError,
    AdmissionLeaseUnknownOutcomeError,
    StoreBackedAdmissionLeaseAuthority,
)
from scripts.spare_parts_provider_authority_store import (
    AuthorityStoreCompare,
    AuthorityStorePut,
    EtcdV3CoordinatorAuthorityStore,
    InMemoryEtcdV3Client,
    SQLiteCoordinatorAuthorityStore,
)


class MutableClock:
    def __init__(self, value: float = 1000.0):
        self.value = value

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


class StoreBackedAdmissionLeaseContract:
    def store(self):
        raise NotImplementedError

    def test_create_uses_global_monotonic_token_and_request_id_is_idempotent(self):
        authority = StoreBackedAdmissionLeaseAuthority(self.store(), clock_fn=self.clock)
        task = ProviderTaskContext("task-1", "tenant-A")
        first = authority.acquire(
            task=task, domain="write", owner_id="owner-A",
            request_id="request-A", lease_ttl_seconds=20,
        )
        replay = authority.acquire(
            task=task, domain="write", owner_id="owner-A",
            request_id="request-A", lease_ttl_seconds=20,
        )
        second = authority.acquire(
            task=ProviderTaskContext("task-2", "tenant-B"), domain="read",
            owner_id="owner-B", request_id="request-B", lease_ttl_seconds=20,
        )
        self.assertEqual(first, replay)
        self.assertEqual(first.fencing_token, 1)
        self.assertEqual(second.fencing_token, 2)
        self.assertTrue(authority.validate(first))
        self.assertTrue(authority.validate(second))

    def test_request_id_cannot_be_reused_for_another_identity_or_after_release(self):
        authority = StoreBackedAdmissionLeaseAuthority(self.store(), clock_fn=self.clock)
        task = ProviderTaskContext("task-1", "tenant-A")
        lease = authority.acquire(
            task=task, domain="write", owner_id="owner-A",
            request_id="request-A", lease_ttl_seconds=20,
        )
        with self.assertRaises(AdmissionLeaseConflictError):
            authority.acquire(
                task=task, domain="write", owner_id="owner-B",
                request_id="request-A", lease_ttl_seconds=20,
            )
        self.assertTrue(authority.release(lease))
        with self.assertRaises(AdmissionLeaseFinalizedError):
            authority.acquire(
                task=task, domain="write", owner_id="owner-A",
                request_id="request-A", lease_ttl_seconds=20,
            )

    def test_renew_moves_key_to_new_backend_lease_and_fences_old_value(self):
        authority = StoreBackedAdmissionLeaseAuthority(self.store(), clock_fn=self.clock)
        lease = authority.acquire(
            task=ProviderTaskContext("task-1", "tenant-A"), domain="write",
            owner_id="owner-A", request_id="request-A", lease_ttl_seconds=20,
        )
        renewed = authority.renew(lease, lease_ttl_seconds=40)
        self.assertIsNotNone(renewed)
        self.assertEqual(renewed.lease_id, lease.lease_id)
        self.assertEqual(renewed.fencing_token, lease.fencing_token)
        self.assertGreater(renewed.expires_at, lease.expires_at)
        self.assertFalse(authority.validate(lease))
        self.assertTrue(authority.validate(renewed))
        self.assertFalse(authority.release(lease))
        self.assertTrue(authority.release(renewed))

    def test_release_and_ttl_expiry_invalidate_same_transaction_guard(self):
        store = self.store()
        authority = StoreBackedAdmissionLeaseAuthority(store, clock_fn=self.clock)
        lease = authority.acquire(
            task=ProviderTaskContext("task-1", "tenant-A"), domain="write",
            owner_id="owner-A", request_id="request-A", lease_ttl_seconds=20,
        )
        guard = authority.active_lease_compares(lease)
        self.assertTrue(
            store.transact(
                guard,
                [AuthorityStorePut(b"/authority/protected/A", b"committed")],
            ).succeeded
        )
        self.assertTrue(authority.release(lease))
        stale = store.transact(
            guard,
            [AuthorityStorePut(b"/authority/protected/B", b"must-not-commit")],
        )
        self.assertFalse(stale.succeeded)
        entry, _ = store.linearizable_get(b"/authority/protected/B")
        self.assertIsNone(entry)

        second = authority.acquire(
            task=ProviderTaskContext("task-2", "tenant-A"), domain="write",
            owner_id="owner-A", request_id="request-B", lease_ttl_seconds=3,
        )
        expiry_guard = authority.active_lease_compares(second)
        self.clock.advance(4)
        expired_write = store.transact(
            expiry_guard,
            [AuthorityStorePut(b"/authority/protected/expired", b"must-not-commit")],
        )
        self.assertFalse(expired_write.succeeded)
        self.assertFalse(authority.validate(second))

    def test_lost_create_response_recovers_same_request_without_new_token(self):
        store = self.store()
        if self.fake_etcd_client is not None:
            self.fake_etcd_client.fail_next_txn_after_commit = True
            authority_store = store
        else:
            from scripts.spare_parts_provider_authority_store import AuthorityStoreOutcomeUnknownError

            class LostResponseProxy:
                def __init__(self, inner):
                    self.inner = inner
                    self.fail_after_commit = True

                def __getattr__(self, name):
                    return getattr(self.inner, name)

                def transact(self, compares, success, failure=()):
                    result = self.inner.transact(compares, success, failure)
                    if self.fail_after_commit:
                        self.fail_after_commit = False
                        raise AuthorityStoreOutcomeUnknownError(
                            "synthetic lost response after SQLite commit"
                        )
                    return result

            authority_store = LostResponseProxy(store)
        authority = StoreBackedAdmissionLeaseAuthority(authority_store, clock_fn=self.clock)
        lease = authority.acquire(
            task=ProviderTaskContext("task-1", "tenant-A"), domain="read",
            owner_id="owner-A", request_id="request-unknown", lease_ttl_seconds=20,
        )
        replay = authority.acquire(
            task=ProviderTaskContext("task-1", "tenant-A"), domain="read",
            owner_id="owner-A", request_id="request-unknown", lease_ttl_seconds=20,
        )
        self.assertEqual(lease, replay)
        self.assertEqual(lease.fencing_token, 1)

    def test_same_request_concurrent_writers_have_single_durable_lease(self):
        from concurrent.futures import ThreadPoolExecutor
        store = self.store()
        authority_a = StoreBackedAdmissionLeaseAuthority(store, clock_fn=self.clock)
        authority_b = StoreBackedAdmissionLeaseAuthority(store, clock_fn=self.clock)
        task = ProviderTaskContext("task-1", "tenant-A")
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [
                pool.submit(
                    auth.acquire, task=task, domain="write", owner_id="owner-A",
                    request_id="request-race", lease_ttl_seconds=20,
                )
                for auth in (authority_a, authority_b)
            ]
            leases = [f.result(timeout=5) for f in futures]
        self.assertEqual(leases[0], leases[1])
        self.assertEqual(leases[0].fencing_token, 1)


class SQLiteAdmissionLeaseAuthorityTests(StoreBackedAdmissionLeaseContract, unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.clock = MutableClock()
        self.fake_etcd_client = None

    def tearDown(self):
        self.tmp.cleanup()

    def store(self):
        return SQLiteCoordinatorAuthorityStore(
            Path(self.tmp.name) / "authority.sqlite3", clock_fn=self.clock
        )


class EtcdAdmissionLeaseAuthorityTests(StoreBackedAdmissionLeaseContract, unittest.TestCase):
    def setUp(self):
        self.clock = MutableClock()
        self.fake_etcd_client = InMemoryEtcdV3Client(clock_fn=self.clock)
        self._store = EtcdV3CoordinatorAuthorityStore(self.fake_etcd_client)

    def tearDown(self):
        pass

    def store(self):
        return self._store
