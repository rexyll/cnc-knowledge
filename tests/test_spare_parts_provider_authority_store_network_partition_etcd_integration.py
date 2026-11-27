from __future__ import annotations

import json
import os
import subprocess
import time
import unittest
from uuid import uuid4

from scripts.spare_parts_provider_authority_store import (
    AuthorityStoreCompare,
    AuthorityStorePut,
    AuthorityStoreUnavailableError,
    AuthorityStoreOutcomeUnknownError,
    EtcdV3CoordinatorAuthorityStore,
)
from scripts.spare_parts_provider_etcd3gw_driver import Etcd3gwV3Client


@unittest.skipUnless(
    os.environ.get("ETCD_INTEGRATION") == "1",
    "set ETCD_INTEGRATION=1 and ETCD_ENDPOINTS to run against a live etcd v3 cluster",
)
class Etcd3gwLiveNetworkPartitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.endpoints = [
            item.strip()
            for item in os.environ.get("ETCD_ENDPOINTS", "").split(",")
            if item.strip()
        ]
        if len(cls.endpoints) != 3:
            raise RuntimeError("exactly three ETCD_ENDPOINTS are required")
        cls.project = "cnc-knowledge-etcd-itest"
        cls.compose = [
            "docker", "compose", "--project-name", cls.project,
            "-f", "scripts/etcd-integration/compose.yaml",
        ]
        cls.network = f"{cls.project}_default"

    def _run(self, args: list[str], *, check: bool = True, timeout: float = 15.0):
        return subprocess.run(
            args, check=check, capture_output=True, text=True, timeout=timeout
        )

    def _container_id(self) -> str:
        result = self._run([*self.compose, "ps", "-q", "etcd1"])
        container_id = result.stdout.strip()
        if not container_id:
            self.fail("etcd1 container was not found in the disposable Compose project")
        labels = self._run([
            "docker", "inspect", "--format",
            '{{ index .Config.Labels "com.docker.compose.project" }}|{{ index .Config.Labels "com.docker.compose.service" }}',
            container_id,
        ]).stdout.strip()
        if labels != f"{self.project}|etcd1":
            self.fail(f"refusing to isolate unexpected container labels: {labels!r}")
        return container_id

    def _network_memberships(self, container_id: str) -> set[str]:
        raw = self._run([
            "docker", "inspect", "--format",
            '{{json .NetworkSettings.Networks}}', container_id,
        ]).stdout
        return set(json.loads(raw).keys())

    def _wait_for_quorum(self, timeout: float = 60.0) -> None:
        deadline = time.monotonic() + timeout
        last_error: Exception | None = None
        while time.monotonic() < deadline:
            clients = []
            try:
                for endpoint in self.endpoints:
                    client = Etcd3gwV3Client([endpoint], timeout=1.5)
                    clients.append(client)
                    client.status()
                members = clients[0].members()
                if len(members) == 3:
                    return
                last_error = RuntimeError(f"expected 3 members, got {len(members)}")
            except Exception as exc:
                last_error = exc
            finally:
                for client in clients:
                    client.close()
            time.sleep(0.5)
        self.fail(f"three-member cluster did not recover: {last_error}")

    def _etcdctl_local(self, container_id: str, *args: str):
        return self._run([
            "docker", "exec", container_id,
            "etcdctl",
            "--endpoints=http://127.0.0.1:2379",
            "--dial-timeout=2s",
            "--command-timeout=3s",
            *args,
        ], check=False, timeout=8.0)

    def test_minority_partition_fails_closed_and_majority_recovers(self):
        container_id = self._container_id()
        key = f"/cnc-knowledge-it/network-partition/{uuid4().hex}".encode()
        value = b"committed-on-majority-only"
        key_text = key.decode("ascii")
        disconnected = False

        try:
            self._run(["docker", "network", "disconnect", self.network, container_id])
            disconnected = True
            self.assertNotIn(self.network, self._network_memberships(container_id))

            # The isolated member remains alive and can reach its local client
            # listener, but cannot obtain a Raft majority.
            minority_read = self._etcdctl_local(container_id, "get", key_text)
            self.assertNotEqual(
                minority_read.returncode, 0,
                "isolated minority unexpectedly completed a linearizable read",
            )
            minority_write = self._etcdctl_local(
                container_id, "put", key_text, "must-not-commit"
            )
            self.assertNotEqual(
                minority_write.returncode, 0,
                "isolated minority unexpectedly acknowledged a write",
            )

            # The two connected members retain quorum and may commit once.
            majority_driver = Etcd3gwV3Client(self.endpoints[1:], timeout=3.0)
            try:
                majority_store = EtcdV3CoordinatorAuthorityStore(majority_driver)
                missing, _ = majority_store.linearizable_get(key)
                self.assertIsNone(missing)
                result = majority_store.transact(
                    [AuthorityStoreCompare(key, "VERSION", "EQUAL", 0)],
                    [AuthorityStorePut(key, value)],
                )
                self.assertTrue(result.succeeded)
                entry, revision = majority_store.linearizable_get(key)
                self.assertIsNotNone(entry)
                self.assertEqual(entry.value, value)
                self.assertGreaterEqual(revision, result.revision)
            finally:
                majority_driver.close()
        finally:
            if disconnected:
                memberships = self._network_memberships(container_id)
                if self.network not in memberships:
                    self._run(["docker", "network", "connect", self.network, container_id])
            self._wait_for_quorum()

        # Once the network is restored, the isolated member must converge to
        # the single majority-committed value; the failed minority write must
        # not appear as a second or conflicting value.
        recovered_driver = Etcd3gwV3Client([self.endpoints[0]], timeout=3.0)
        try:
            recovered_store = EtcdV3CoordinatorAuthorityStore(recovered_driver)
            entry, _ = recovered_store.linearizable_get(key)
            self.assertIsNotNone(entry)
            self.assertEqual(entry.value, value)
        finally:
            recovered_driver.close()


if __name__ == "__main__":
    unittest.main()
