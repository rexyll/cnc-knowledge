from __future__ import annotations

import json
import os
import subprocess
import time
import unittest
from uuid import uuid4

from scripts.spare_parts_provider_authority_store import (
    AuthorityStoreCompare,
    AuthorityStoreLeaseError,
    AuthorityStorePut,
    AuthorityStoreUnavailableError,
    EtcdV3CoordinatorAuthorityStore,
)
from scripts.spare_parts_provider_etcd3gw_driver import Etcd3gwV3Client


@unittest.skipUnless(
    os.environ.get("ETCD_INTEGRATION") == "1",
    "set ETCD_INTEGRATION=1 and ETCD_ENDPOINTS to run against a live etcd v3 cluster",
)
class Etcd3gwLiveLeasePartitionTests(unittest.TestCase):
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
        # etcdctl parses lease IDs as hexadecimal; the normalized client port
        # intentionally exposes them as integers.
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

    def _wait_for_lease_expiry(
        self,
        container_id: str,
        lease_id: int,
        store: EtcdV3CoordinatorAuthorityStore,
        attached_key: bytes,
        timeout: float = 20.0,
    ) -> None:
        deadline = time.monotonic() + timeout
        last_ttl: dict | None = None
        while time.monotonic() < deadline:
            last_ttl = self._lease_ttl(container_id, lease_id)
            ttl_expired = (
                last_ttl is None or int(last_ttl.get("ttl", 0)) <= 0
            )
            if ttl_expired:
                # The TTL endpoint can report -1 before lease-attached key
                # deletion has been applied. Confirm actual linearizable key
                # absence rather than treating the TTL response as sufficient.
                while time.monotonic() < deadline:
                    entry, _ = store.linearizable_get(attached_key)
                    if entry is None:
                        return
                    time.sleep(0.25)
                self.fail(
                    f"lease TTL expired but attached authority key remains: "
                    f"lease_id={lease_id}, last_ttl={last_ttl}"
                )
            time.sleep(0.5)
        self.fail(f"lease {lease_id} did not expire before deadline; last TTL={last_ttl}")

    def _track_lease_keepalive_attempts(
        self, driver: Etcd3gwV3Client
    ) -> list[str]:
        attempts: list[str] = []
        for endpoint, client in zip(self.endpoints[:1], driver._clients):
            original_post = client.post

            def tracked_post(url, *args, _endpoint=endpoint, _original=original_post, **kwargs):
                if url.endswith("/lease/keepalive"):
                    attempts.append(_endpoint)
                return _original(url, *args, **kwargs)

            client.post = tracked_post
        return attempts

    def test_minority_cannot_renew_lease_majority_expires_and_fences_old_epoch(self):
        minority_container = self._container_id("etcd1")
        majority_container = self._container_id("etcd2")
        suffix = uuid4().hex
        leader_key = f"/cnc-knowledge-it/lease-partition/{suffix}/leader".encode()
        epoch_key = f"/cnc-knowledge-it/lease-partition/{suffix}/epoch".encode()
        stale_write_key = f"/cnc-knowledge-it/lease-partition/{suffix}/stale-write".encode()
        new_write_key = f"/cnc-knowledge-it/lease-partition/{suffix}/new-write".encode()
        old_owner = f"old-owner-{suffix}".encode()
        new_owner = f"new-owner-{suffix}".encode()

        majority_driver = Etcd3gwV3Client(self.endpoints[1:], timeout=3.0)
        majority_store = EtcdV3CoordinatorAuthorityStore(majority_driver)
        old_lease = None
        new_lease = None
        disconnected = False
        keepalive_driver = None
        keepalive_attempts: list[str] = []
        keepalive_result = "not-run"
        old_ttl_before = None
        old_ttl_after = None
        stale_succeeded = None
        accepted_succeeded = None

        try:
            # Phase A: establish a lease-bound leader and durable epoch on quorum.
            try:
                old_lease = majority_store.lease_grant(8)
                initial = majority_store.transact(
                    [
                        AuthorityStoreCompare(leader_key, "VERSION", "EQUAL", 0),
                        AuthorityStoreCompare(epoch_key, "VERSION", "EQUAL", 0),
                    ],
                    [
                        AuthorityStorePut(leader_key, old_owner, old_lease.lease_id),
                        AuthorityStorePut(epoch_key, b"1"),
                    ],
                )
                self.assertTrue(initial.succeeded)
                leader, _ = majority_store.linearizable_get(leader_key)
                epoch, _ = majority_store.linearizable_get(epoch_key)
                self.assertIsNotNone(leader)
                self.assertEqual(leader.lease_id, old_lease.lease_id)
                self.assertEqual(epoch.value, b"1")

                old_ttl_before = self._lease_ttl(majority_container, old_lease.lease_id)
                self.assertIsNotNone(
                    old_ttl_before,
                    "initial LeaseTimeToLive must be visible from the majority",
                )
                self.assertGreater(int(old_ttl_before.get("ttl", 0)), 0)

                # Phase B: isolate only etcd1, and pin KeepAlive to that member.
                self._run([
                    "docker", "network", "disconnect", self.network, minority_container
                ])
                disconnected = True
                self.assertNotIn(
                    self.network, self._network_memberships(minority_container)
                )

                keepalive_driver = Etcd3gwV3Client(
                    [self.endpoints[0]], timeout=2.0
                )
                keepalive_attempts = self._track_lease_keepalive_attempts(
                    keepalive_driver
                )
                minority_store = EtcdV3CoordinatorAuthorityStore(keepalive_driver)
                try:
                    renewed = minority_store.lease_keepalive(old_lease.lease_id)
                    keepalive_result = f"unexpected-positive-ttl-{renewed.ttl_seconds}"
                    self.fail(
                        "isolated minority reported a positive KeepAlive TTL; "
                        "leadership must fail closed when quorum cannot be reached"
                    )
                except (AuthorityStoreUnavailableError, AuthorityStoreLeaseError) as exc:
                    keepalive_result = type(exc).__name__
                self.assertEqual(keepalive_attempts, [self.endpoints[0]])

                # Let a measurable interval pass, then compare quorum-side TTL.
                time.sleep(2.0)
                old_ttl_after = self._lease_ttl(
                    majority_container, old_lease.lease_id
                )
                if old_ttl_after is not None:
                    self.assertLess(
                        int(old_ttl_after.get("ttl", 0)),
                        int(old_ttl_before.get("ttl", 0)),
                        "quorum-side TTL did not decrease after minority KeepAlive",
                    )

                # The lease expires naturally. No KeepAlive retry or revoke is
                # used to force expiry; etcd removes the attached authority key.
                self._wait_for_lease_expiry(
                    majority_container, old_lease.lease_id,
                    majority_store, leader_key,
                )
                expired_leader, _ = majority_store.linearizable_get(leader_key)
                persistent_epoch, _ = majority_store.linearizable_get(epoch_key)
                self.assertIsNone(expired_leader)
                self.assertEqual(persistent_epoch.value, b"1")

                # Phase C: a new owner advances the independent fencing epoch.
                new_lease = majority_store.lease_grant(20)
                successor = majority_store.transact(
                    [
                        AuthorityStoreCompare(leader_key, "VERSION", "EQUAL", 0),
                        AuthorityStoreCompare(
                            epoch_key, "VALUE", "EQUAL", b"1"
                        ),
                    ],
                    [
                        AuthorityStorePut(
                            leader_key, new_owner, new_lease.lease_id
                        ),
                        AuthorityStorePut(epoch_key, b"2"),
                    ],
                )
                self.assertTrue(successor.succeeded)
                current_leader, _ = majority_store.linearizable_get(leader_key)
                current_epoch, _ = majority_store.linearizable_get(epoch_key)
                self.assertEqual(current_leader.value, new_owner)
                self.assertEqual(current_leader.lease_id, new_lease.lease_id)
                self.assertEqual(current_epoch.value, b"2")

                # A stale writer with owner/epoch 1 cannot pass the CAS fence.
                stale = majority_store.transact(
                    [
                        AuthorityStoreCompare(
                            leader_key, "VALUE", "EQUAL", old_owner
                        ),
                        AuthorityStoreCompare(epoch_key, "VALUE", "EQUAL", b"1"),
                    ],
                    [AuthorityStorePut(stale_write_key, b"must-be-fenced")],
                )
                stale_succeeded = stale.succeeded
                self.assertFalse(stale.succeeded)
                stale_write, _ = majority_store.linearizable_get(stale_write_key)
                self.assertIsNone(stale_write)

                # The current owner at epoch 2 remains authorized.
                accepted = majority_store.transact(
                    [
                        AuthorityStoreCompare(
                            leader_key, "VALUE", "EQUAL", new_owner
                        ),
                        AuthorityStoreCompare(epoch_key, "VALUE", "EQUAL", b"2"),
                    ],
                    [AuthorityStorePut(new_write_key, b"accepted-by-epoch-2")],
                )
                accepted_succeeded = accepted.succeeded
                self.assertTrue(accepted.succeeded)
                new_write, _ = majority_store.linearizable_get(new_write_key)
                self.assertEqual(new_write.value, b"accepted-by-epoch-2")
            finally:
                if keepalive_driver is not None:
                    keepalive_driver.close()
                if disconnected:
                    memberships = self._network_memberships(minority_container)
                    if self.network not in memberships:
                        self._run([
                            "docker", "network", "connect",
                            self.network, minority_container,
                        ])
                self._wait_for_quorum()

            # Phase D: verify the former minority converged to the fenced state
            # before any test-scoped lease cleanup runs.
            recovered_driver = Etcd3gwV3Client(
                [self.endpoints[0]], timeout=3.0
            )
            try:
                recovered_store = EtcdV3CoordinatorAuthorityStore(recovered_driver)
                recovered_leader, _ = recovered_store.linearizable_get(leader_key)
                recovered_epoch, _ = recovered_store.linearizable_get(epoch_key)
                recovered_stale, _ = recovered_store.linearizable_get(stale_write_key)
                recovered_new_write, _ = recovered_store.linearizable_get(new_write_key)
                self.assertIsNotNone(recovered_leader)
                self.assertEqual(recovered_leader.value, new_owner)
                self.assertEqual(recovered_leader.lease_id, new_lease.lease_id)
                self.assertEqual(recovered_epoch.value, b"2")
                self.assertIsNone(recovered_stale)
                self.assertEqual(recovered_new_write.value, b"accepted-by-epoch-2")
            finally:
                recovered_driver.close()

            print(
                "LEASE_PARTITION_FENCING_OBSERVATION "
                + json.dumps(
                    {
                        "keepalive_result": keepalive_result,
                        "keepalive_endpoint_attempts": keepalive_attempts,
                        "old_ttl_before": old_ttl_before,
                        "old_ttl_after": old_ttl_after,
                        "old_lease_expired_naturally": True,
                        "old_leader_key_deleted": True,
                        "old_epoch": 1,
                        "new_epoch": 2,
                        "stale_write_succeeded": stale_succeeded,
                        "new_epoch_write_succeeded": accepted_succeeded,
                        "recovered_member_observed_epoch": 2,
                    },
                    sort_keys=True,
                )
            )
        finally:
            # Cleanup always occurs after network restoration; no production or
            # external container is touched by this disposable test.
            try:
                if new_lease is not None:
                    majority_store.lease_revoke(new_lease.lease_id)
                if old_lease is not None:
                    majority_store.lease_revoke(old_lease.lease_id)
            except Exception:
                pass
            majority_driver.close()


if __name__ == "__main__":
    unittest.main()
