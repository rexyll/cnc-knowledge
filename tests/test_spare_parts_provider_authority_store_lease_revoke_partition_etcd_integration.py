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
    EtcdV3CoordinatorAuthorityStore,
)
from scripts.spare_parts_provider_etcd3gw_driver import Etcd3gwV3Client


@unittest.skipUnless(
    os.environ.get("ETCD_INTEGRATION") == "1",
    "set ETCD_INTEGRATION=1 and ETCD_ENDPOINTS to run against a live etcd v3 cluster",
)
class Etcd3gwLiveLeaseRevokePartitionTests(unittest.TestCase):
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

    def _container_id(self, service: str) -> str:
        result = self._run([*self.compose, "ps", "-q", service])
        container_id = result.stdout.strip()
        if not container_id:
            self.fail(f"{service} container was not found in the disposable Compose project")
        labels = self._run([
            "docker", "inspect", "--format",
            '{{ index .Config.Labels "com.docker.compose.project" }}|{{ index .Config.Labels "com.docker.compose.service" }}',
            container_id,
        ]).stdout.strip()
        if labels != f"{self.project}|{service}":
            self.fail(f"refusing to operate on unexpected container labels: {labels!r}")
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

    def _lease_ttl(self, container_id: str, lease_id: int) -> dict | None:
        lease_hex = format(lease_id, "x")
        result = self._etcdctl_local(
            container_id, "lease", "timetolive", lease_hex,
            "--write-out=json", "--keys",
        )
        if result.returncode != 0:
            return None
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            self.fail(f"etcdctl returned invalid LeaseTimeToLive JSON: {exc}")
        if not isinstance(payload, dict):
            self.fail("etcdctl LeaseTimeToLive response must be a JSON object")
        return payload

    def _track_revoke_attempts(self, driver: Etcd3gwV3Client) -> list[str]:
        attempts: list[str] = []
        for endpoint, client in zip(self.endpoints, driver._clients):
            original_post = client.post

            def tracked_post(url, *args, _endpoint=endpoint, _original=original_post, **kwargs):
                if url.endswith("/kv/lease/revoke"):
                    attempts.append(_endpoint)
                return _original(url, *args, **kwargs)

            client.post = tracked_post
        return attempts

    def test_minority_lease_revoke_is_single_dispatch_and_reconciled_after_recovery(self):
        minority_container = self._container_id("etcd1")
        majority_container = self._container_id("etcd2")
        suffix = uuid4().hex
        authority_key = f"/cnc-knowledge-it/lease-revoke-partition/{suffix}/leader".encode()
        authority_value = f"leader-{suffix}".encode()

        majority_driver = Etcd3gwV3Client(self.endpoints[1:], timeout=3.0)
        majority_store = EtcdV3CoordinatorAuthorityStore(majority_driver)
        revoke_driver = None
        revoke_attempts: list[str] = []
        revoke_result = "not-dispatched"
        lease = None
        disconnected = False
        ttl_before = None
        ttl_after = None
        key_revision_before = None
        key_revision_after = None
        recovered_state = "not-reconciled"
        cleanup_action = "not-needed"

        try:
            # Establish the lease and its authority key through the healthy majority.
            lease = majority_store.lease_grant(60)
            created = majority_store.transact(
                [AuthorityStoreCompare(authority_key, "VERSION", "EQUAL", 0)],
                [AuthorityStorePut(authority_key, authority_value, lease.lease_id)],
            )
            self.assertTrue(created.succeeded)
            attached, _ = majority_store.linearizable_get(authority_key)
            self.assertIsNotNone(attached)
            self.assertEqual(attached.lease_id, lease.lease_id)
            self.assertEqual(attached.value, authority_value)
            key_revision_before = attached.mod_revision
            ttl_before = self._lease_ttl(majority_container, lease.lease_id)
            self.assertIsNotNone(ttl_before)
            self.assertGreater(int(ttl_before.get("ttl", 0)), 0)

            # Partition only the project-owned etcd1 service container.
            self._run([
                "docker", "network", "disconnect", self.network, minority_container
            ])
            disconnected = True
            self.assertNotIn(
                self.network, self._network_memberships(minority_container)
            )

            # The first and only revoke request is pinned to isolated etcd1 by
            # endpoint order. Its result class is recorded rather than assumed.
            revoke_driver = Etcd3gwV3Client(self.endpoints, timeout=2.0)
            revoke_attempts = self._track_revoke_attempts(revoke_driver)
            revoke_store = EtcdV3CoordinatorAuthorityStore(revoke_driver)
            try:
                revoke_store.lease_revoke(lease.lease_id)
                revoke_result = "success"
            except Exception as exc:
                revoke_result = type(exc).__name__
            finally:
                revoke_driver.close()
                revoke_driver = None

            self.assertEqual(revoke_attempts, [self.endpoints[0]])

            # Restore the network before inspecting state or doing any cleanup.
            memberships = self._network_memberships(minority_container)
            if self.network not in memberships:
                self._run([
                    "docker", "network", "connect", "--ip", "172.29.64.11",
                    self.network, minority_container,
                ])
            disconnected = False
            self._wait_for_quorum()

            # Reconcile from the majority. Do not replay the first Revoke.
            deadline = time.monotonic() + 12.0
            ttl_after = None
            recovered_entry = None
            while time.monotonic() < deadline:
                ttl_after = self._lease_ttl(majority_container, lease.lease_id)
                recovered_entry, _ = majority_store.linearizable_get(authority_key)
                lease_absent = (
                    ttl_after is None or int(ttl_after.get("ttl", -1)) <= 0
                )
                if recovered_entry is None and lease_absent:
                    recovered_state = "revoke-committed-or-already-absent"
                    break
                if (
                    recovered_entry is not None
                    and ttl_after is not None
                    and int(ttl_after.get("ttl", 0)) > 0
                ):
                    recovered_state = "revoke-not-committed"
                    break
                # TTL=-1 can precede deletion of lease-attached KV entries.
                time.sleep(0.25)

            self.assertIn(
                recovered_state,
                {"revoke-committed-or-already-absent", "revoke-not-committed"},
                f"could not reconcile LeaseRevoke outcome: ttl={ttl_after}",
            )

            if recovered_state == "revoke-committed-or-already-absent":
                self.assertIsNone(recovered_entry)
                self.assertGreater(
                    majority_store.linearizable_get(authority_key)[1],
                    key_revision_before,
                    "a committed revoke should remove the lease-bound key at a later revision",
                )
            else:
                self.assertIsNotNone(recovered_entry)
                self.assertEqual(recovered_entry.value, authority_value)
                self.assertEqual(recovered_entry.lease_id, lease.lease_id)
                self.assertEqual(recovered_entry.mod_revision, key_revision_before)
                self.assertGreater(int(ttl_after.get("ttl", 0)), 0)

                # This is a new, explicit cleanup action after the first result
                # has been reconciled; it is not an automatic retry of that call.
                cleanup_action = "one-explicit-revoke-through-healthy-majority"
                majority_store.lease_revoke(lease.lease_id)
                cleanup_deadline = time.monotonic() + 10.0
                cleanup_entry = recovered_entry
                cleanup_ttl = ttl_after
                while time.monotonic() < cleanup_deadline:
                    cleanup_ttl = self._lease_ttl(majority_container, lease.lease_id)
                    cleanup_entry, _ = majority_store.linearizable_get(authority_key)
                    if cleanup_entry is None and (
                        cleanup_ttl is None or int(cleanup_ttl.get("ttl", -1)) <= 0
                    ):
                        break
                    time.sleep(0.25)
                self.assertIsNone(cleanup_entry)
                self.assertTrue(
                    cleanup_ttl is None or int(cleanup_ttl.get("ttl", -1)) <= 0
                )
                ttl_after = cleanup_ttl
                key_revision_after = majority_store.linearizable_get(authority_key)[1]
            if key_revision_after is None:
                key_revision_after = majority_store.linearizable_get(authority_key)[1]

            self.assertIn(
                revoke_result,
                {
                    "success",
                    "AuthorityStoreOutcomeUnknownError",
                    "AuthorityStoreUnavailableError",
                },
                f"unexpected Store result classification: {revoke_result}",
            )

            print(
                "LEASE_REVOKE_PARTITION_OBSERVATION "
                + json.dumps(
                    {
                        "revoke_endpoint_attempts": revoke_attempts,
                        "revoke_result": revoke_result,
                        "lease_id": lease.lease_id,
                        "ttl_before": ttl_before,
                        "ttl_after_reconciliation": ttl_after,
                        "authority_key_revision_before": key_revision_before,
                        "authority_key_revision_after": key_revision_after,
                        "recovered_state": recovered_state,
                        "cleanup_action": cleanup_action,
                    },
                    sort_keys=True,
                )
            )
        finally:
            if revoke_driver is not None:
                revoke_driver.close()
            if disconnected:
                memberships = self._network_memberships(minority_container)
                if self.network not in memberships:
                    self._run([
                        "docker", "network", "connect", "--ip", "172.29.64.11",
                        self.network, minority_container,
                    ])
                self._wait_for_quorum()
            # Never issue a duplicate cleanup revoke if the key is already gone.
            if lease is not None:
                remaining, _ = majority_store.linearizable_get(authority_key)
                if remaining is not None and remaining.lease_id == lease.lease_id:
                    majority_store.lease_revoke(lease.lease_id)
            majority_driver.close()


if __name__ == "__main__":
    unittest.main()
