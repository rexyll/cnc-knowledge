from __future__ import annotations

import os
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from scripts.spare_parts_provider_authority_store import (
    AuthorityStoreCompare,
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
