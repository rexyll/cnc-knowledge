from __future__ import annotations

import os
import subprocess
import time
import unittest
from uuid import uuid4

from scripts.spare_parts_provider_authority_store import (
    AuthorityStoreCompare,
    AuthorityStoreOutcomeUnknownError,
    AuthorityStorePut,
    AuthorityStoreUnavailableError,
    EtcdV3CoordinatorAuthorityStore,
)
from scripts.spare_parts_provider_etcd3gw_driver import Etcd3gwV3Client


@unittest.skipUnless(
    os.environ.get("ETCD_INTEGRATION") == "1",
    "set ETCD_INTEGRATION=1 and ETCD_ENDPOINTS to run against a live etcd v3 cluster",
)
class Etcd3gwLiveQuorumLossTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.endpoints = [
            item.strip()
            for item in os.environ.get("ETCD_ENDPOINTS", "").split(",")
            if item.strip()
        ]
        if len(cls.endpoints) < 3:
            raise RuntimeError("three ETCD_ENDPOINTS are required for the quorum-loss test")
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

    def _wait_for_quorum(self, endpoint: str, timeout: float = 45.0) -> None:
        probe = Etcd3gwV3Client([endpoint], timeout=1.0)
        deadline = time.monotonic() + timeout
        last_error: Exception | None = None
        try:
            while time.monotonic() < deadline:
                try:
                    status = probe.status()
                    leader = status.get("leader", status.get("leaderID", 0))
                    if int(leader or 0) > 0 and len(probe.members()) == 3:
                        return
                except Exception as exc:
                    last_error = exc
                time.sleep(0.5)
        finally:
            probe.close()
        raise AssertionError(f"three-member quorum did not recover; last_error={last_error}")

    def test_two_member_loss_rejects_linearizable_io_and_recovers(self):
        key = f"/cnc-knowledge-it/quorum-loss/{uuid4().hex}".encode()
        value = b"must-not-commit-without-majority"
        self._compose("stop", "etcd1")
        self._compose("stop", "etcd2")
        try:
            time.sleep(1.5)  # Allow the former leader lease/election window to expire.

            read_driver = Etcd3gwV3Client(self.endpoints, timeout=1.0)
            try:
                read_store = EtcdV3CoordinatorAuthorityStore(read_driver)
                with self.assertRaises(AuthorityStoreUnavailableError):
                    read_store.linearizable_get(key)
            finally:
                read_driver.close()

            # A mutation routed to the sole surviving member must not be
            # reported as committed without a Raft majority.
            write_driver = Etcd3gwV3Client([self.endpoints[2]], timeout=1.5)
            try:
                write_store = EtcdV3CoordinatorAuthorityStore(write_driver)
                with self.assertRaises((
                    AuthorityStoreUnavailableError,
                    AuthorityStoreOutcomeUnknownError,
                )):
                    write_store.transact(
                        [AuthorityStoreCompare(key, "VERSION", "EQUAL", 0)],
                        [AuthorityStorePut(key, value)],
                    )
            finally:
                write_driver.close()
        finally:
            # Bring all members back even when an assertion fails.
            self._compose("start", "etcd1")
            self._compose("start", "etcd2")
            self._wait_for_quorum(self.endpoints[2])

        # After quorum recovery the failed/no-quorum attempt must not have
        # produced an accepted value; a fresh CAS write should now succeed.
        recovered_driver = Etcd3gwV3Client([self.endpoints[2]], timeout=2.0)
        try:
            recovered_store = EtcdV3CoordinatorAuthorityStore(recovered_driver)
            missing, _ = recovered_store.linearizable_get(key)
            self.assertIsNone(missing)
            committed = recovered_store.transact(
                [AuthorityStoreCompare(key, "VERSION", "EQUAL", 0)],
                [AuthorityStorePut(key, value)],
            )
            self.assertTrue(committed.succeeded)
            entry, revision = recovered_store.linearizable_get(key)
            self.assertIsNotNone(entry)
            self.assertEqual(entry.value, value)
            self.assertGreaterEqual(revision, committed.revision)
        finally:
            recovered_driver.close()


if __name__ == "__main__":
    unittest.main()
