from __future__ import annotations

import os
import subprocess
import time
import unittest
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
class Etcd3gwLiveMemberOutageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.endpoints = [
            item.strip()
            for item in os.environ.get("ETCD_ENDPOINTS", "").split(",")
            if item.strip()
        ]
        if len(cls.endpoints) < 3:
            raise RuntimeError("three ETCD_ENDPOINTS are required for the member-outage test")
        cls.compose = [
            "docker", "compose",
            "--project-name", "cnc-knowledge-etcd-itest",
            "-f", "scripts/etcd-integration/compose.yaml",
        ]

    def _compose(self, action: str, service: str) -> None:
        subprocess.run(
            [*self.compose, action, service],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )

    def _wait_for_endpoint(self, endpoint: str, *, members: int, timeout: float = 45.0) -> None:
        probe = Etcd3gwV3Client([endpoint], timeout=1.0)
        deadline = time.monotonic() + timeout
        last_error: Exception | None = None
        try:
            while time.monotonic() < deadline:
                try:
                    status = probe.status()
                    leader = status.get("leader", status.get("leaderID", 0))
                    if int(leader or 0) > 0 and len(probe.members()) == members:
                        return
                except Exception as exc:
                    last_error = exc
                time.sleep(0.5)
        finally:
            probe.close()
        raise AssertionError(
            f"etcd endpoint {endpoint} did not recover with {members} members; "
            f"last_error={last_error}"
        )

    def test_single_member_outage_retains_quorum_and_linearizable_writes(self):
        # The Compose file maps etcd1/2/3 to ETCD_ENDPOINTS[0/1/2].
        stopped_endpoint = self.endpoints[0]
        healthy_endpoint = self.endpoints[1]
        key = f"/cnc-knowledge-it/member-outage/{uuid4().hex}".encode()
        value = b"quorum-survived-single-member-outage"

        self._compose("stop", "etcd1")
        try:
            # Read-only Range must fail over from the stopped first member
            # without weakening serializable=false (linearizable semantics).
            read_driver = Etcd3gwV3Client(
                [stopped_endpoint, healthy_endpoint],
                timeout=1.0,
            )
            try:
                range_result = read_driver.range(
                    b"/cnc-knowledge-it/member-outage/",
                    serializable=False,
                )
                self.assertGreaterEqual(range_result["header"]["revision"], 0)
            finally:
                read_driver.close()

            # Wait for a leader to be available on the surviving two-member
            # quorum before issuing the single mutating Txn request.
            self._wait_for_endpoint(healthy_endpoint, members=3)
            write_driver = Etcd3gwV3Client([healthy_endpoint], timeout=2.0)
            try:
                store = EtcdV3CoordinatorAuthorityStore(write_driver)
                transaction = store.transact(
                    [AuthorityStoreCompare(key, "VERSION", "EQUAL", 0)],
                    [AuthorityStorePut(key, value)],
                )
                self.assertTrue(transaction.succeeded)
                entry, revision = store.linearizable_get(key)
                self.assertIsNotNone(entry)
                self.assertEqual(entry.value, value)
                self.assertGreaterEqual(revision, transaction.revision)
            finally:
                write_driver.close()
        finally:
            self._compose("start", "etcd1")
            self._wait_for_endpoint(stopped_endpoint, members=3)


if __name__ == "__main__":
    unittest.main()
