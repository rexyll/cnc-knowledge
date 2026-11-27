from __future__ import annotations

import json
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
                    self._run(["docker", "network", "connect", "--ip", "172.29.64.11", self.network, container_id])
            self._wait_for_quorum()

        # Once the network is restored, the isolated member must converge to
        # the single majority-committed value; the failed minority write must
        # not appear as a second or conflicting value.
        recovered_driver = Etcd3gwV3Client([self.endpoints[0]], timeout=2.0)
        try:
            recovered_store = EtcdV3CoordinatorAuthorityStore(recovered_driver)
            deadline = time.monotonic() + 15.0
            entry = None
            last_error: Exception | None = None
            while time.monotonic() < deadline:
                try:
                    entry, _ = recovered_store.linearizable_get(key)
                    if entry is not None:
                        break
                except Exception as exc:
                    # This is a read-only convergence probe after reconnect;
                    # no write is replayed while the former minority catches up.
                    last_error = exc
                time.sleep(0.5)
            self.assertIsNotNone(
                entry,
                f"reconnected minority did not expose the majority value; last_error={last_error}",
            )
            self.assertEqual(entry.value, value)
        finally:
            recovered_driver.close()


    def _track_driver_attempts(self, driver: Etcd3gwV3Client) -> list[str]:
        attempts: list[str] = []
        for endpoint, client in zip(self.endpoints, driver._clients):
            original_post = client.post

            def tracked_post(url, *args, _endpoint=endpoint, _original=original_post, **kwargs):
                attempts.append(_endpoint)
                return _original(url, *args, **kwargs)

            client.post = tracked_post
        return attempts

    def test_driver_partition_read_failover_and_single_txn_outcome(self):
        container_id = self._container_id()
        read_key = f"/cnc-knowledge-it/partition-driver-read/{uuid4().hex}".encode()
        txn_key = f"/cnc-knowledge-it/partition-driver-txn/{uuid4().hex}".encode()
        txn_value = b"single-attempt-minority-transaction"
        disconnected = False
        read_driver = None
        txn_driver = None
        read_observation = "not-run"
        txn_observation = "not-run"
        read_attempts: list[str] = []
        txn_attempts: list[str] = []

        try:
            self._run(["docker", "network", "disconnect", self.network, container_id])
            disconnected = True
            self.assertNotIn(self.network, self._network_memberships(container_id))

            # The client starts with the isolated endpoint first. A real
            # transport timeout may fail over; a typed Gateway response must
            # remain visible and must not be retried as a transport failure.
            read_driver = Etcd3gwV3Client(self.endpoints, timeout=4.0)
            read_attempts = self._track_driver_attempts(read_driver)
            read_store = EtcdV3CoordinatorAuthorityStore(read_driver)
            try:
                entry, _ = read_store.linearizable_get(read_key)
                self.assertIsNone(entry)
                self.assertGreaterEqual(
                    len(read_attempts), 2,
                    "linearizable Range returned from the isolated member without a majority path",
                )
                read_observation = "linearizable-read-reached-a-healthy-endpoint"
            except AuthorityStoreUnavailableError as exc:
                cause = exc.__cause__
                if isinstance(cause, (TimeoutError, ConnectionError)):
                    self.assertGreaterEqual(
                        len(read_attempts), 2,
                        "transport timeout should advance through configured read endpoints",
                    )
                    read_observation = f"transport-failure-after-{len(read_attempts)}-attempts"
                else:
                    self.assertEqual(
                        len(read_attempts), 1,
                        "non-transport Gateway/protocol errors must not trigger endpoint failover",
                    )
                    read_observation = (
                        f"non-transport-{type(cause).__name__ if cause else type(exc).__name__}"
                    )

            # Mutating Txn uses a single isolated endpoint so the number of
            # network submissions is observable and cannot be mistaken for
            # an automatic replay to a healthy member.
            txn_driver = Etcd3gwV3Client([self.endpoints[0]], timeout=4.0)
            single_endpoint = [self.endpoints[0]]
            txn_attempts = self._track_single_endpoint_attempts(txn_driver, single_endpoint)
            txn_store = EtcdV3CoordinatorAuthorityStore(txn_driver)
            try:
                result = txn_store.transact(
                    [AuthorityStoreCompare(txn_key, "VERSION", "EQUAL", 0)],
                    [AuthorityStorePut(txn_key, txn_value)],
                )
                self.assertFalse(
                    result.succeeded,
                    "isolated minority unexpectedly acknowledged a successful Txn",
                )
                txn_observation = f"known-unsuccessful-revision-{result.revision}"
            except AuthorityStoreOutcomeUnknownError as exc:
                txn_observation = f"OUTCOME_UNKNOWN/{type(exc.__cause__).__name__}"
            except AuthorityStoreUnavailableError as exc:
                txn_observation = (
                    f"unavailable/{type(exc.__cause__).__name__ if exc.__cause__ else type(exc).__name__}"
                )

            self.assertEqual(
                len(txn_attempts), 1,
                "mutating Txn must be submitted exactly once and never fail over",
            )
            print(
                "PARTITION_DRIVER_OBSERVATION "
                + json.dumps(
                    {
                        "read_result": read_observation,
                        "read_endpoint_attempts": read_attempts,
                        "txn_result": txn_observation,
                        "txn_endpoint_attempts": txn_attempts,
                    },
                    sort_keys=True,
                )
            )
        finally:
            for driver in (read_driver, txn_driver):
                if driver is not None:
                    driver.close()
            if disconnected:
                memberships = self._network_memberships(container_id)
                if self.network not in memberships:
                    self._run(["docker", "network", "connect", "--ip", "172.29.64.11", self.network, container_id])
            self._wait_for_quorum()

        # Reconcile the one-shot Txn after quorum returns; never replay it.
        recovered_driver = Etcd3gwV3Client(self.endpoints[1:], timeout=3.0)
        try:
            recovered_store = EtcdV3CoordinatorAuthorityStore(recovered_driver)
            entry, _ = recovered_store.linearizable_get(txn_key)
            if entry is None:
                recovery = "not-committed"
            else:
                self.assertEqual(entry.value, txn_value)
                recovery = "committed-once"
            print(f"PARTITION_DRIVER_TXN_RECOVERY={recovery}")
        finally:
            recovered_driver.close()

    def _track_single_endpoint_attempts(
        self, driver: Etcd3gwV3Client, endpoints: list[str]
    ) -> list[str]:
        attempts: list[str] = []
        for endpoint, client in zip(endpoints, driver._clients):
            original_post = client.post

            def tracked_post(url, *args, _endpoint=endpoint, _original=original_post, **kwargs):
                attempts.append(_endpoint)
                return _original(url, *args, **kwargs)

            client.post = tracked_post
        return attempts


if __name__ == "__main__":
    unittest.main()
