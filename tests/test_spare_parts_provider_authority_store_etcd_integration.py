from __future__ import annotations

import os
import queue
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from scripts.spare_parts_provider_authority_store import (
    AuthorityStoreCompare,
    AuthorityStoreDelete,
    AuthorityStorePut,
    EtcdV3CoordinatorAuthorityStore,
)
from scripts.spare_parts_provider_etcd3gw_driver import Etcd3gwV3Client


@unittest.skipUnless(
    os.environ.get("ETCD_INTEGRATION") == "1",
    "set ETCD_INTEGRATION=1 and ETCD_ENDPOINTS to run against a live etcd v3 cluster",
)
class Etcd3gwLiveClusterIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.endpoints = [
            item.strip()
            for item in os.environ.get("ETCD_ENDPOINTS", "").split(",")
            if item.strip()
        ]
        if not cls.endpoints:
            raise RuntimeError("ETCD_ENDPOINTS must provide one or more etcd HTTP gateway endpoints")
        cls.namespace = f"/cnc-knowledge-it/{uuid4().hex}/"
        cls.driver_a = Etcd3gwV3Client(cls.endpoints, timeout=2.0)
        cls.driver_b = Etcd3gwV3Client(cls.endpoints, timeout=2.0)
        cls.store_a = EtcdV3CoordinatorAuthorityStore(cls.driver_a)
        cls.store_b = EtcdV3CoordinatorAuthorityStore(cls.driver_b)

    @classmethod
    def tearDownClass(cls):
        for driver in (getattr(cls, "driver_a", None), getattr(cls, "driver_b", None)):
            if driver is not None:
                driver.close()

    def test_cluster_membership_reports_three_members(self):
        self.assertEqual(len(self.driver_a.members()), 3)

    def test_binary_range_and_compare_transaction_round_trip(self):
        key = (self.namespace + "binary").encode()
        payload = b"\x00etcd-v3\xff\x80payload"
        tx = self.store_a.transact(
            [AuthorityStoreCompare(key, "VERSION", "EQUAL", 0)],
            [AuthorityStorePut(key, payload)],
        )
        self.assertTrue(tx.succeeded)
        entry, revision = self.store_b.linearizable_get(key)
        self.assertEqual(entry.value, payload)
        self.assertGreaterEqual(revision, tx.revision)

    def test_two_independent_clients_have_exactly_one_cas_winner(self):
        key = (self.namespace + "cas").encode()
        barrier = threading.Barrier(2)

        def attempt(store, value):
            barrier.wait(timeout=5)
            result = store.transact(
                [AuthorityStoreCompare(key, "VERSION", "EQUAL", 0)],
                [AuthorityStorePut(key, value)],
            )
            return result.succeeded

        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(attempt, self.store_a, b"client-a")
            second = pool.submit(attempt, self.store_b, b"client-b")
            winners = [first.result(timeout=10), second.result(timeout=10)]
        self.assertEqual(sum(winners), 1)

    def test_lease_attached_key_survives_keepalive_and_disappears_on_revoke(self):
        key = (self.namespace + "lease").encode()
        lease = self.store_a.lease_grant(30)
        self.store_a.transact([], [AuthorityStorePut(key, b"leased", lease.lease_id)])
        refreshed = self.store_b.lease_keepalive(lease.lease_id)
        self.assertGreater(refreshed.ttl_seconds, 0)
        entry, _ = self.store_b.linearizable_get(key)
        self.assertIsNotNone(entry)
        self.store_a.lease_revoke(lease.lease_id)
        deleted, _ = self.store_b.linearizable_get(key)
        self.assertIsNone(deleted)

    def test_watch_preserves_created_put_delete_and_previous_kv(self):
        key = (self.namespace + "watch").encode()
        value = b"gateway-watch-value"

        stream = self.store_a.watch(
            key,
            start_revision=0,
            progress_notify=True,
            prev_kv=True,
        )

        def next_with_timeout(timeout=8.0):
            outcome = queue.Queue(maxsize=1)

            def read_one():
                try:
                    outcome.put((True, next(stream)))
                except BaseException as exc:
                    outcome.put((False, exc))

            worker = threading.Thread(target=read_one, daemon=True)
            worker.start()
            try:
                succeeded, result = outcome.get(timeout=timeout)
            except queue.Empty:
                stream.close()
                worker.join(timeout=2.0)
                self.fail(f"etcd Watch did not produce a response within {timeout}s")
            if not succeeded:
                raise result
            return result

        try:
            created = next_with_timeout()
            self.assertTrue(created.created)
            self.assertGreaterEqual(created.header_revision, 0)
            self.assertGreaterEqual(created.watch_id, 0)

            put = self.store_b.transact([], [AuthorityStorePut(key, value)])
            self.assertTrue(put.succeeded)
            put_response = next_with_timeout()
            self.assertFalse(put_response.canceled)
            self.assertEqual(len(put_response.events), 1)
            self.assertEqual(put_response.events[0].event_type, "PUT")
            self.assertEqual(put_response.events[0].key, key)
            self.assertEqual(put_response.events[0].entry.value, value)
            self.assertEqual(put_response.events[0].revision, put.revision)

            delete = self.store_b.transact([], [AuthorityStoreDelete(key)])
            self.assertTrue(delete.succeeded)
            delete_response = next_with_timeout()
            self.assertFalse(delete_response.canceled)
            self.assertEqual(len(delete_response.events), 1)
            self.assertEqual(delete_response.events[0].event_type, "DELETE")
            self.assertEqual(delete_response.events[0].key, key)
            self.assertEqual(delete_response.events[0].previous_entry.value, value)
            self.assertEqual(delete_response.events[0].revision, delete.revision)
        finally:
            stream.close()

    def test_linearizable_range_fails_over_from_an_unavailable_first_endpoint(self):
        fallback = self.endpoints[0]
        failover = Etcd3gwV3Client(
            ["http://127.0.0.1:1", fallback],
            timeout=0.5,
        )
        try:
            result = failover.range(self.namespace.encode(), serializable=False)
        finally:
            failover.close()
        self.assertGreaterEqual(result["header"]["revision"], 0)


if __name__ == "__main__":
    unittest.main()
