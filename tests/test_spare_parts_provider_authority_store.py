from __future__ import annotations

import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from scripts.spare_parts_provider_authority_store import (
    AuthorityStoreCompare,
    AuthorityStoreDelete,
    AuthorityStoreOutcomeUnknownError,
    AuthorityStorePut,
    AuthorityStoreUnavailableError,
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


class CoordinatorAuthorityStoreContract:
    def store(self):
        raise NotImplementedError

    def test_linearizable_get_and_atomic_multi_key_transaction(self):
        store = self.store()
        missing, initial_revision = store.linearizable_get(b"/authority/scope-A")
        self.assertIsNone(missing)

        created = store.transact(
            [AuthorityStoreCompare(b"/authority/scope-A", "VERSION", "EQUAL", 0)],
            [
                AuthorityStorePut(b"/authority/scope-A", b'{"token":1}'),
                AuthorityStorePut(b"/authority/sequence-A", b"0"),
            ],
        )
        self.assertTrue(created.succeeded)
        self.assertGreater(created.revision, initial_revision)
        first, revision_a = store.linearizable_get(b"/authority/scope-A")
        second, revision_b = store.linearizable_get(b"/authority/sequence-A")
        self.assertEqual(first.value, b'{"token":1}')
        self.assertEqual(second.value, b"0")
        self.assertEqual(first.mod_revision, second.mod_revision)
        self.assertEqual(revision_a, revision_b)

    def test_failed_compare_executes_failure_branch_atomically(self):
        store = self.store()
        store.transact([], [AuthorityStorePut(b"/authority/counter", b"1")])
        entry, _ = store.linearizable_get(b"/authority/counter")
        result = store.transact(
            [AuthorityStoreCompare(b"/authority/counter", "MOD", "EQUAL", 999)],
            [AuthorityStorePut(b"/authority/counter", b"2")],
            [AuthorityStorePut(b"/authority/conflict", b"stale")],
        )
        self.assertFalse(result.succeeded)
        current, _ = store.linearizable_get(b"/authority/counter")
        failure, _ = store.linearizable_get(b"/authority/conflict")
        self.assertEqual(current.value, b"1")
        self.assertEqual(failure.value, b"stale")
        self.assertEqual(current.mod_revision, entry.mod_revision)

    def test_compare_and_swap_has_one_winner_under_concurrency(self):
        store = self.store()
        store.transact([], [AuthorityStorePut(b"/authority/counter", b"0")])
        entry, _ = store.linearizable_get(b"/authority/counter")
        barrier = threading.Barrier(2)

        def contender(value: bytes):
            barrier.wait(timeout=5)
            return store.transact(
                [AuthorityStoreCompare(
                    b"/authority/counter", "MOD", "EQUAL", entry.mod_revision
                )],
                [AuthorityStorePut(b"/authority/counter", value)],
            ).succeeded

        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(contender, (b"A", b"B")))
        self.assertEqual(outcomes.count(True), 1)
        self.assertEqual(outcomes.count(False), 1)

    def test_lease_attaches_expires_and_revokes_keys(self):
        store = self.store()
        clock = self.clock
        lease = store.lease_grant(5)
        store.transact(
            [],
            [AuthorityStorePut(b"/authority/leader", b"leader-A", lease.lease_id)],
        )
        current, _ = store.linearizable_get(b"/authority/leader")
        self.assertEqual(current.lease_id, lease.lease_id)
        clock.advance(3)
        self.assertEqual(store.lease_keepalive(lease.lease_id).ttl_seconds, 5)
        clock.advance(3)
        current, _ = store.linearizable_get(b"/authority/leader")
        self.assertIsNotNone(current)
        clock.advance(6)
        current, _ = store.linearizable_get(b"/authority/leader")
        self.assertIsNone(current)

        lease2 = store.lease_grant(5)
        store.transact([], [AuthorityStorePut(b"/authority/leader", b"leader-B", lease2.lease_id)])
        store.lease_revoke(lease2.lease_id)
        current, _ = store.linearizable_get(b"/authority/leader")
        self.assertIsNone(current)

    def test_delete_is_revisioned_and_missing_delete_is_noop(self):
        store = self.store()
        store.transact([], [AuthorityStorePut(b"/authority/delete-me", b"x")])
        entry, _ = store.linearizable_get(b"/authority/delete-me")
        removed = store.transact(
            [AuthorityStoreCompare(b"/authority/delete-me", "MOD", "EQUAL", entry.mod_revision)],
            [AuthorityStoreDelete(b"/authority/delete-me")],
        )
        self.assertTrue(removed.succeeded)
        current, _ = store.linearizable_get(b"/authority/delete-me")
        self.assertIsNone(current)
        noop = store.transact([], [AuthorityStoreDelete(b"/authority/not-present")])
        self.assertEqual(noop.revision, removed.revision)


class SQLiteCoordinatorAuthorityStoreTests(CoordinatorAuthorityStoreContract, unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.clock = MutableClock()

    def tearDown(self):
        self.tmp.cleanup()

    def store(self):
        return SQLiteCoordinatorAuthorityStore(
            Path(self.tmp.name) / "authority.sqlite3", clock_fn=self.clock
        )


class EtcdV3CoordinatorAuthorityStoreTests(CoordinatorAuthorityStoreContract, unittest.TestCase):
    def setUp(self):
        self.clock = MutableClock()
        self.client = InMemoryEtcdV3Client(clock_fn=self.clock)
        self._store = EtcdV3CoordinatorAuthorityStore(self.client)

    def tearDown(self):
        pass

    @property
    def store_instance(self):
        return self._store

    def store(self):
        return self.store_instance

    def test_etcd_adapter_always_uses_linearizable_range_for_authority_reads(self):
        entry, revision = self.store().linearizable_get(b"/authority/missing")
        self.assertIsNone(entry)
        self.assertEqual(revision, 0)
        self.assertEqual(self.client.serializable_flags, [False])

    def test_unknown_transaction_outcome_is_not_reported_as_success_or_retried(self):
        self.client.fail_next_txn_after_commit = True
        with self.assertRaises(AuthorityStoreOutcomeUnknownError):
            self.store().transact(
                [],
                [AuthorityStorePut(b"/authority/unknown", b"committed-maybe")],
            )
        entry, _ = self.store().linearizable_get(b"/authority/unknown")
        self.assertEqual(entry.value, b"committed-maybe")

    def test_etcd_transaction_encodes_revision_comparison_and_lease_attachment(self):
        lease = self.store().lease_grant(10)
        created = self.store().transact(
            [AuthorityStoreCompare(b"/authority/leased", "VERSION", "EQUAL", 0)],
            [AuthorityStorePut(b"/authority/leased", b"leader", lease.lease_id)],
        )
        self.assertTrue(created.succeeded)
        entry, _ = self.store().linearizable_get(b"/authority/leased")
        self.assertEqual(entry.lease_id, lease.lease_id)
        self.store().lease_revoke(lease.lease_id)
        removed, _ = self.store().linearizable_get(b"/authority/leased")
        self.assertIsNone(removed)

    def test_etcd_connection_error_fails_closed(self):
        self.client.unavailable = True
        with self.assertRaises(AuthorityStoreUnavailableError):
            self.store().linearizable_get(b"/authority/leader")

        with self.assertRaises(AuthorityStoreOutcomeUnknownError):
            self.store().transact(
                [],
                [AuthorityStorePut(b"/authority/new", b"must-not-be-assumed")],
            )

    def test_injected_old_leader_cas_is_rejected_after_epoch_value_changes(self):
        # Leader ownership is enforced by an atomic revision/value comparison,
        # not by a cached process-local lease object.
        store = self.store()
        leader_key = b"/authority/leader"
        epoch_key = b"/authority/leader-epoch"
        store.transact(
            [AuthorityStoreCompare(leader_key, "VERSION", "EQUAL", 0)],
            [
                AuthorityStorePut(leader_key, b"leader-A"),
                AuthorityStorePut(epoch_key, b"1"),
            ],
        )
        leader, _ = store.linearizable_get(leader_key)
        epoch, _ = store.linearizable_get(epoch_key)
        store.transact(
            [AuthorityStoreCompare(leader_key, "MOD", "EQUAL", leader.mod_revision)],
            [
                AuthorityStorePut(leader_key, b"leader-B"),
                AuthorityStorePut(epoch_key, b"2"),
            ],
        )
        stale = store.transact(
            [
                AuthorityStoreCompare(leader_key, "MOD", "EQUAL", leader.mod_revision),
                AuthorityStoreCompare(epoch_key, "VALUE", "EQUAL", b"1"),
            ],
            [AuthorityStorePut(b"/authority/proof-issued-by-old", b"yes")],
        )
        self.assertFalse(stale.succeeded)
        proof, _ = store.linearizable_get(b"/authority/proof-issued-by-old")
        self.assertIsNone(proof)


if __name__ == "__main__":
    unittest.main()
