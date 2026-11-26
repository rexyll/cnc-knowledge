from __future__ import annotations

import concurrent.futures
import threading
import unittest

from scripts.spare_parts_provider_authority_store import (
    AuthorityStoreCompare,
    AuthorityStoreDelete,
    AuthorityStoreOutcomeUnknownError,
    AuthorityStorePut,
    AuthorityStoreUnavailableError,
    EtcdV3CoordinatorAuthorityStore,
    InMemoryEtcdV3WatchClient,
)


class MutableClock:
    def __init__(self, value: float = 10_000.0):
        self.value = value

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


def shared_stores():
    clock = MutableClock()
    client = InMemoryEtcdV3WatchClient(clock_fn=clock)
    return clock, client, (
        EtcdV3CoordinatorAuthorityStore(client),
        EtcdV3CoordinatorAuthorityStore(client),
    )


class EtcdWatchAndMultiClientContractTests(unittest.TestCase):
    def test_linearizable_range_reads_a_prefix_at_one_revision(self):
        _, _, (store_a, store_b) = shared_stores()
        result = store_a.transact([], [
            AuthorityStorePut(b"/cnc/scopes/a", b"A"),
            AuthorityStorePut(b"/cnc/scopes/b", b"B"),
            AuthorityStorePut(b"/cnc/other/c", b"C"),
        ])
        ranged = store_b.linearizable_range(b"/cnc/scopes/", range_end=b"/cnc/scopes0")
        self.assertEqual(ranged.revision, result.revision)
        self.assertEqual([entry.key for entry in ranged.entries], [
            b"/cnc/scopes/a", b"/cnc/scopes/b"
        ])
        self.assertEqual({entry.mod_revision for entry in ranged.entries}, {result.revision})
        self.assertTrue(all(flag is False for flag in store_a.client.serializable_flags))

    def test_two_independent_adapters_have_exactly_one_cas_winner(self):
        _, _, (store_a, store_b) = shared_stores()
        store_a.transact([], [AuthorityStorePut(b"/cnc/counter", b"0")])
        observed, _ = store_a.linearizable_get(b"/cnc/counter")
        barrier = threading.Barrier(2)

        def write(store, value):
            barrier.wait(timeout=5)
            return store.transact(
                [AuthorityStoreCompare(b"/cnc/counter", "MOD", "EQUAL", observed.mod_revision)],
                [AuthorityStorePut(b"/cnc/counter", value)],
            ).succeeded

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            futures = [
                pool.submit(write, store_a, b"A"),
                pool.submit(write, store_b, b"B"),
            ]
            results = [future.result(timeout=5) for future in futures]
        self.assertEqual(results.count(True), 1)
        self.assertEqual(results.count(False), 1)

    def test_lost_txn_response_is_reconciled_by_second_client_readback(self):
        _, client, (store_a, store_b) = shared_stores()
        client.fail_next_txn_after_commit = True
        with self.assertRaises(AuthorityStoreOutcomeUnknownError):
            store_a.transact(
                [AuthorityStoreCompare(b"/cnc/requests/r1", "VERSION", "EQUAL", 0)],
                [AuthorityStorePut(b"/cnc/requests/r1", b"ACTIVE")],
            )
        entry, _ = store_b.linearizable_get(b"/cnc/requests/r1")
        self.assertEqual(entry.value, b"ACTIVE")
        self.assertEqual(client._revision, entry.mod_revision)

    def test_timeout_before_commit_is_still_outcome_unknown_not_known_failure(self):
        _, client, (store_a, store_b) = shared_stores()
        client.fail_next_txn_before_commit = True
        with self.assertRaises(AuthorityStoreOutcomeUnknownError):
            store_a.transact(
                [AuthorityStoreCompare(b"/cnc/requests/r2", "VERSION", "EQUAL", 0)],
                [AuthorityStorePut(b"/cnc/requests/r2", b"ACTIVE")],
            )
        entry, _ = store_b.linearizable_get(b"/cnc/requests/r2")
        self.assertIsNone(entry)

    def test_watch_created_response_does_not_advance_resume_cursor(self):
        _, _, (store, _) = shared_stores()
        watch = store.watch(b"/cnc/events", start_revision=0)
        created = next(watch)
        self.assertTrue(created.created)
        self.assertIsNone(created.resume_revision)
        watch.close()

    def test_watch_delivers_put_with_revision_and_previous_value(self):
        _, _, (store_a, store_b) = shared_stores()
        store_a.transact([], [AuthorityStorePut(b"/cnc/events/key", b"one")])
        first, _ = store_a.linearizable_get(b"/cnc/events/key")
        watch = store_b.watch(b"/cnc/events/key", start_revision=first.mod_revision + 1)
        self.assertTrue(next(watch).created)
        result = store_a.transact(
            [AuthorityStoreCompare(b"/cnc/events/key", "MOD", "EQUAL", first.mod_revision)],
            [AuthorityStorePut(b"/cnc/events/key", b"two")],
        )
        response = next(watch)
        event = response.events[0]
        self.assertEqual(event.event_type, "PUT")
        self.assertEqual(event.entry.value, b"two")
        self.assertEqual(event.previous_entry.value, b"one")
        self.assertEqual(event.revision, result.revision)
        self.assertEqual(response.resume_revision, result.revision + 1)
        watch.close()

    def test_watch_delete_contains_previous_kv_when_requested(self):
        _, _, (store_a, store_b) = shared_stores()
        store_a.transact([], [AuthorityStorePut(b"/cnc/delete-me", b"value")])
        current, _ = store_a.linearizable_get(b"/cnc/delete-me")
        watch = store_b.watch(b"/cnc/delete-me", start_revision=current.mod_revision + 1)
        next(watch)
        store_a.transact(
            [AuthorityStoreCompare(b"/cnc/delete-me", "MOD", "EQUAL", current.mod_revision)],
            [AuthorityStoreDelete(b"/cnc/delete-me")],
        )
        event = next(watch).events[0]
        self.assertEqual(event.event_type, "DELETE")
        self.assertIsNone(event.entry)
        self.assertEqual(event.previous_entry.value, b"value")
        watch.close()

    def test_watch_prev_kv_false_omits_previous_value(self):
        _, _, (store_a, store_b) = shared_stores()
        store_a.transact([], [AuthorityStorePut(b"/cnc/no-prev", b"before")])
        current, _ = store_a.linearizable_get(b"/cnc/no-prev")
        watch = store_b.watch(
            b"/cnc/no-prev", start_revision=current.mod_revision + 1, prev_kv=False
        )
        next(watch)
        store_a.transact([], [AuthorityStorePut(b"/cnc/no-prev", b"after")])
        self.assertIsNone(next(watch).events[0].previous_entry)
        watch.close()

    def test_watch_progress_response_advances_complete_revision_cursor(self):
        _, _, (store_a, _) = shared_stores()
        store_a.transact([], [AuthorityStorePut(b"/cnc/progress", b"x")])
        current, _ = store_a.linearizable_get(b"/cnc/progress")
        watch = store_a.watch(b"/cnc/progress", start_revision=current.mod_revision + 1)
        created = next(watch)
        store_a.watch_progress(created.watch_id)
        progress = next(watch)
        self.assertTrue(progress.is_progress)
        self.assertEqual(progress.resume_revision, progress.header_revision + 1)
        self.assertGreaterEqual(progress.header_revision, current.mod_revision)
        watch.close()

    def test_watch_fragment_does_not_advance_cursor_until_final_fragment(self):
        class FragmentClient(InMemoryEtcdV3WatchClient):
            def watch(self, key, **kwargs):
                def stream():
                    yield {"header": {"revision": 50}, "watch_id": 7, "created": True, "events": []}
                    yield {
                        "header": {"revision": 51}, "watch_id": 7, "fragment": True,
                        "events": [{
                            "type": 0,
                            "kv": {
                                "key": key, "value": b"part-1",
                                "create_revision": 51, "mod_revision": 51,
                                "version": 1, "lease": 0,
                            },
                        }],
                    }
                    yield {"header": {"revision": 51}, "watch_id": 7, "events": []}
                return stream()

        store = EtcdV3CoordinatorAuthorityStore(FragmentClient())
        watch = store.watch(b"/cnc/fragment")
        self.assertTrue(next(watch).created)
        partial = next(watch)
        self.assertTrue(partial.fragment)
        self.assertIsNone(partial.resume_revision)
        self.assertEqual(next(watch).resume_revision, 52)
        watch.close()

    def test_starting_watch_at_compacted_revision_returns_cancel(self):
        _, client, (store, _) = shared_stores()
        store.transact([], [AuthorityStorePut(b"/cnc/compact", b"one")])
        current, _ = store.linearizable_get(b"/cnc/compact")
        client.compact(current.mod_revision)
        watch = store.watch(b"/cnc/compact", start_revision=current.mod_revision)
        canceled = next(watch)
        self.assertTrue(canceled.canceled)
        self.assertEqual(canceled.compact_revision, current.mod_revision)
        self.assertIsNone(canceled.resume_revision)
        with self.assertRaises(StopIteration):
            next(watch)

    def test_active_watch_is_canceled_when_it_falls_behind_compaction(self):
        _, client, (store_a, store_b) = shared_stores()
        store_a.transact([], [AuthorityStorePut(b"/cnc/active-compact", b"v1")])
        first, _ = store_a.linearizable_get(b"/cnc/active-compact")
        watch = store_b.watch(b"/cnc/active-compact", start_revision=first.mod_revision + 1)
        next(watch)
        second = store_a.transact([], [AuthorityStorePut(b"/cnc/unrelated", b"x")])
        client.compact(second.revision)
        canceled = next(watch)
        self.assertTrue(canceled.canceled)
        self.assertIsNone(canceled.resume_revision)

    def test_recovery_after_compaction_requires_fresh_linearizable_range(self):
        _, client, (store_a, store_b) = shared_stores()
        store_a.transact([], [AuthorityStorePut(b"/cnc/state/a", b"one")])
        current, _ = store_a.linearizable_get(b"/cnc/state/a")
        watch = store_b.watch(
            b"/cnc/state/", start_revision=current.mod_revision + 1,
            range_end=b"/cnc/state0",
        )
        next(watch)
        later = store_a.transact([], [AuthorityStorePut(b"/cnc/state/b", b"two")])
        client.compact(later.revision)
        self.assertTrue(next(watch).canceled)
        snapshot = store_b.linearizable_range(b"/cnc/state/", range_end=b"/cnc/state0")
        self.assertEqual(snapshot.revision, later.revision)
        self.assertEqual(
            {entry.key: entry.value for entry in snapshot.entries},
            {b"/cnc/state/a": b"one", b"/cnc/state/b": b"two"},
        )
        restarted = store_b.watch(
            b"/cnc/state/", start_revision=snapshot.revision + 1,
            range_end=b"/cnc/state0",
        )
        self.assertTrue(next(restarted).created)
        restarted.close()

    def test_watch_stream_disconnect_fails_closed(self):
        _, client, (store, _) = shared_stores()
        watch = store.watch(b"/cnc/disconnect")
        self.assertTrue(next(watch).created)
        client.fail_next_watch_after_create = True
        with self.assertRaises(AuthorityStoreUnavailableError):
            next(watch)
        self.assertIsNone(store.linearizable_get(b"/cnc/disconnect")[0])

    def test_watch_cancel_closes_server_side_registration(self):
        _, client, (store, _) = shared_stores()
        watch = store.watch(b"/cnc/cancel")
        created = next(watch)
        self.assertIn(created.watch_id, client._watchers)
        watch.close()
        self.assertNotIn(created.watch_id, client._watchers)

    def test_lease_expiry_emits_delete_event_for_watch_and_removes_key(self):
        clock, _, (store_a, store_b) = shared_stores()
        lease = store_a.lease_grant(5)
        store_a.transact([], [AuthorityStorePut(b"/cnc/leader", b"leader-a", lease.lease_id)])
        leader, _ = store_a.linearizable_get(b"/cnc/leader")
        watch = store_b.watch(b"/cnc/leader", start_revision=leader.mod_revision + 1)
        next(watch)
        clock.advance(6)
        self.assertIsNone(store_b.linearizable_get(b"/cnc/leader")[0])
        event = next(watch).events[0]
        self.assertEqual(event.event_type, "DELETE")
        watch.close()

    def test_lease_grant_lost_response_is_unknown_and_not_blindly_retried(self):
        _, client, (store_a, _) = shared_stores()
        client.fail_next_lease_grant_after_commit = True
        with self.assertRaises(AuthorityStoreOutcomeUnknownError):
            store_a.lease_grant(30)
        self.assertEqual(len(client._leases), 1)
        self.assertEqual(len(client._kvs), 0)

    def test_lease_keepalive_lost_response_fails_closed(self):
        _, client, (store_a, store_b) = shared_stores()
        lease = store_a.lease_grant(30)
        client.fail_next_lease_keepalive_after_commit = True
        with self.assertRaises(AuthorityStoreUnavailableError):
            store_a.lease_keepalive(lease.lease_id)
        self.assertEqual(store_b.lease_keepalive(lease.lease_id).lease_id, lease.lease_id)

    def test_lease_revoke_lost_response_is_reconciled_by_second_client(self):
        _, client, (store_a, store_b) = shared_stores()
        lease = store_a.lease_grant(30)
        store_a.transact([], [AuthorityStorePut(b"/cnc/revoke", b"leader", lease.lease_id)])
        client.fail_next_lease_revoke_after_commit = True
        with self.assertRaises(AuthorityStoreOutcomeUnknownError):
            store_a.lease_revoke(lease.lease_id)
        self.assertIsNone(store_b.linearizable_get(b"/cnc/revoke")[0])

    def test_expired_old_leader_cannot_mutate_after_other_client_observes_expiry(self):
        clock, _, (store_a, store_b) = shared_stores()
        lease = store_a.lease_grant(3)
        store_a.transact([], [AuthorityStorePut(b"/cnc/leader", b"leader-a", lease.lease_id)])
        leader, _ = store_a.linearizable_get(b"/cnc/leader")
        clock.advance(4)
        store_b.linearizable_get(b"/cnc/leader")
        stale = store_a.transact(
            [AuthorityStoreCompare(b"/cnc/leader", "MOD", "EQUAL", leader.mod_revision)],
            [AuthorityStorePut(b"/cnc/proof", b"must-not-exist")],
        )
        self.assertFalse(stale.succeeded)
        self.assertIsNone(store_b.linearizable_get(b"/cnc/proof")[0])

    def test_watch_delete_is_notification_only_authority_requires_linearizable_read(self):
        _, _, (store_a, store_b) = shared_stores()
        store_a.transact([], [AuthorityStorePut(b"/cnc/scope", b"ACTIVE")])
        current, _ = store_a.linearizable_get(b"/cnc/scope")
        watch = store_b.watch(b"/cnc/scope", start_revision=current.mod_revision + 1)
        next(watch)
        store_a.transact([], [AuthorityStoreDelete(b"/cnc/scope")])
        event = next(watch)
        self.assertEqual(event.events[0].event_type, "DELETE")
        after, read_revision = store_b.linearizable_get(b"/cnc/scope")
        self.assertIsNone(after)
        self.assertGreaterEqual(read_revision, event.header_revision)
        watch.close()


if __name__ == "__main__":
    unittest.main()
