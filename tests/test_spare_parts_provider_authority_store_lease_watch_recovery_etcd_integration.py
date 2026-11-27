from __future__ import annotations

import json
import os
import queue
import subprocess
import threading
import time
import unittest
from uuid import uuid4

from scripts.spare_parts_provider_authority_store import (
    AuthorityStorePut,
    AuthorityStoreUnavailableError,
    EtcdV3CoordinatorAuthorityStore,
)
from scripts.spare_parts_provider_etcd3gw_driver import Etcd3gwV3Client


@unittest.skipUnless(
    os.environ.get("ETCD_INTEGRATION") == "1",
    "set ETCD_INTEGRATION=1 and ETCD_ENDPOINTS to run against a live etcd v3 cluster",
)
class Etcd3gwLiveLeaseWatchRecoveryTests(unittest.TestCase):
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

    def _next_result(self, stream, timeout: float = 10.0):
        result_queue: queue.Queue = queue.Queue(maxsize=1)

        def read_one():
            try:
                result_queue.put(("response", next(stream)))
            except BaseException as exc:
                result_queue.put(("exception", exc))

        worker = threading.Thread(target=read_one, daemon=True)
        worker.start()
        try:
            result = result_queue.get(timeout=timeout)
        except queue.Empty:
            return "timeout", None
        worker.join(timeout=1.0)
        return result

    def _track_watch_attempts(self, driver: Etcd3gwV3Client) -> list[str]:
        attempts: list[str] = []
        for endpoint, client in zip(self.endpoints, driver._clients):
            original_post = client.session.post

            def tracked_post(url, *args, _endpoint=endpoint, _original=original_post, **kwargs):
                if url.endswith("/v3/watch"):
                    attempts.append(_endpoint)
                return _original(url, *args, **kwargs)

            client.session.post = tracked_post
        return attempts

    def test_lease_revoke_emits_delete_with_previous_lease_bound_kv(self):
        suffix = uuid4().hex
        key = f"/cnc-knowledge-it/lease-watch/{suffix}/leader".encode()
        value = f"leader-{suffix}".encode()
        driver = Etcd3gwV3Client(self.endpoints[1:], timeout=3.0)
        store = EtcdV3CoordinatorAuthorityStore(driver)
        stream = None
        lease_id = None

        try:
            lease = store.lease_grant(60)
            lease_id = lease.lease_id
            created = store.transact([], [AuthorityStorePut(key, value, lease_id)])
            self.assertTrue(created.succeeded)

            before, revision = store.linearizable_get(key)
            self.assertIsNotNone(before)
            self.assertEqual(before.value, value)
            self.assertEqual(before.lease_id, lease_id)
            self.assertEqual(before.mod_revision, created.revision)
            self.assertGreaterEqual(revision, before.mod_revision)

            stream = store.watch(
                key,
                start_revision=revision + 1,
                progress_notify=False,
                prev_kv=True,
            )
            opened = self._next_result(stream)
            self.assertEqual(opened[0], "response", opened[1])
            created_response = opened[1]
            self.assertTrue(created_response.created)
            self.assertGreaterEqual(created_response.header_revision, revision)

            store.lease_revoke(lease_id)
            deleted = self._next_result(stream)
            self.assertEqual(deleted[0], "response", deleted[1])
            response = deleted[1]
            self.assertFalse(response.canceled)
            self.assertEqual(len(response.events), 1)
            event = response.events[0]
            self.assertEqual(event.event_type, "DELETE")
            self.assertEqual(event.key, key)
            self.assertIsNone(event.entry)
            self.assertGreater(event.revision, revision)
            self.assertEqual(response.header_revision, event.revision)
            self.assertIsNotNone(event.previous_entry)
            self.assertEqual(event.previous_entry.key, key)
            self.assertEqual(event.previous_entry.value, value)
            self.assertEqual(event.previous_entry.lease_id, lease_id)
            self.assertEqual(event.previous_entry.mod_revision, before.mod_revision)

            current, read_revision = store.linearizable_get(key)
            self.assertIsNone(current)
            self.assertGreaterEqual(read_revision, event.revision)
            print(
                "LEASE_WATCH_DELETE_OBSERVATION "
                + json.dumps(
                    {
                        "watch_start_revision": revision + 1,
                        "delete_event_revision": event.revision,
                        "delete_header_revision": response.header_revision,
                        "previous_kv_mod_revision": event.previous_entry.mod_revision,
                        "previous_kv_lease_id_matches": event.previous_entry.lease_id == lease_id,
                        "linearizable_read_revision": read_revision,
                        "key_absent_after_revoke": True,
                    },
                    sort_keys=True,
                )
            )
        finally:
            if stream is not None:
                stream.close()
            if lease_id is not None:
                try:
                    current, _ = store.linearizable_get(key)
                    if current is not None and current.lease_id == lease_id:
                        store.lease_revoke(lease_id)
                except Exception:
                    pass
            driver.close()

    def test_watch_disconnect_rebuilds_from_linearizable_snapshot_plus_one(self):
        suffix = uuid4().hex
        key = f"/cnc-knowledge-it/lease-watch-recovery/{suffix}/leader".encode()
        value = f"old-leader-{suffix}".encode()
        next_value = f"new-leader-{suffix}".encode()
        minority_container = self._container_id("etcd1")

        majority_driver = Etcd3gwV3Client(self.endpoints[1:], timeout=3.0)
        majority_store = EtcdV3CoordinatorAuthorityStore(majority_driver)
        watch_driver = Etcd3gwV3Client(self.endpoints, timeout=3.0)
        watch_store = EtcdV3CoordinatorAuthorityStore(watch_driver)
        stream = None
        resumed_stream = None
        stopped = False
        lease_ids: list[int] = []
        attempts: list[str] = []
        disconnect_result = "not-observed"
        delete_revision = None
        snapshot_revision = None

        try:
            # Establish a lease-bound key and a revisioned watch on etcd1.
            lease = majority_store.lease_grant(60)
            lease_ids.append(lease.lease_id)
            initial = majority_store.transact(
                [], [AuthorityStorePut(key, value, lease.lease_id)]
            )
            self.assertTrue(initial.succeeded)
            entry, baseline_revision = majority_store.linearizable_get(key)
            self.assertIsNotNone(entry)
            self.assertEqual(entry.lease_id, lease.lease_id)
            self.assertEqual(entry.mod_revision, initial.revision)

            attempts = self._track_watch_attempts(watch_driver)
            stream = watch_store.watch(
                key,
                start_revision=baseline_revision + 1,
                progress_notify=False,
                prev_kv=True,
            )
            opened = self._next_result(stream)
            self.assertEqual(opened[0], "response", opened[1])
            self.assertTrue(opened[1].created)
            self.assertEqual(attempts, [self.endpoints[0]])

            # Stop only the project/service-label-verified etcd1 container.
            # This closes an already-established HTTP Watch stream.
            self._run(["docker", "stop", "--time", "1", minority_container], timeout=20.0)
            stopped = True

            # Commit the lease revoke through the healthy 2/3 majority while
            # the established Watch connection is down.
            majority_store.lease_revoke(lease.lease_id)
            deleted, delete_revision = majority_store.linearizable_get(key)
            self.assertIsNone(deleted)
            self.assertGreater(delete_revision, baseline_revision)

            termination = self._next_result(stream, timeout=10.0)
            self.assertNotEqual(
                termination[0],
                "timeout",
                "established Watch stream did not report EOF/disconnect after its member stopped",
            )
            if termination[0] == "exception":
                self.assertIsInstance(
                    termination[1],
                    AuthorityStoreUnavailableError,
                    f"unexpected Watch disconnect classification: {type(termination[1]).__name__}",
                )
                disconnect_result = type(termination[1]).__name__
            else:
                # A clean HTTP EOF is also an explicit end of this iterator;
                # it is not an automatic restart or a synthetic Watch event.
                self.assertIsInstance(termination[1], StopIteration)
                disconnect_result = "StopIteration"

            # The Watch must not silently dispatch a second request elsewhere.
            self.assertEqual(attempts, [self.endpoints[0]])

            # Restore the stopped member before reconciliation.
            self._run(["docker", "start", minority_container], timeout=20.0)
            stopped = False
            self._wait_for_quorum()

            # Rebuild state from an authoritative Range and use its revision+1.
            snapshot, snapshot_revision = majority_store.linearizable_get(key)
            self.assertIsNone(snapshot)
            self.assertGreaterEqual(snapshot_revision, delete_revision)

            resumed_stream = majority_store.watch(
                key,
                start_revision=snapshot_revision + 1,
                progress_notify=False,
                prev_kv=True,
            )
            resumed_created = self._next_result(resumed_stream)
            self.assertEqual(resumed_created[0], "response", resumed_created[1])
            self.assertTrue(resumed_created[1].created)

            # A fresh PUT proves the resumed stream is live. The first event
            # after its created frame must not replay the earlier DELETE.
            successor = majority_store.lease_grant(60)
            lease_ids.append(successor.lease_id)
            put = majority_store.transact(
                [], [AuthorityStorePut(key, next_value, successor.lease_id)]
            )
            self.assertTrue(put.succeeded)
            resumed_event = self._next_result(resumed_stream)
            self.assertEqual(resumed_event[0], "response", resumed_event[1])
            events = resumed_event[1].events
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0].event_type, "PUT")
            self.assertEqual(events[0].key, key)
            self.assertEqual(events[0].entry.value, next_value)
            self.assertGreaterEqual(events[0].revision, put.revision)

            print(
                "LEASE_WATCH_RECOVERY_OBSERVATION "
                + json.dumps(
                    {
                        "initial_watch_endpoint_attempts": attempts,
                        "initial_watch_baseline_revision": baseline_revision,
                        "disconnect_result": disconnect_result,
                        "delete_revision_during_disconnect": delete_revision,
                        "snapshot_revision_after_recovery": snapshot_revision,
                        "snapshot_key_absent": True,
                        "resume_start_revision": snapshot_revision + 1,
                        "first_resumed_event": events[0].event_type,
                        "first_resumed_event_revision": events[0].revision,
                        "old_delete_replayed": False,
                        "successor_put_observed": True,
                    },
                    sort_keys=True,
                )
            )
        finally:
            if stream is not None:
                stream.close()
            if resumed_stream is not None:
                resumed_stream.close()
            if stopped:
                self._run(["docker", "start", minority_container], timeout=20.0)
                self._wait_for_quorum()
            try:
                current, _ = majority_store.linearizable_get(key)
                if current is not None and current.lease_id in lease_ids:
                    majority_store.lease_revoke(current.lease_id)
            except Exception:
                pass
            watch_driver.close()
            majority_driver.close()


if __name__ == "__main__":
    unittest.main()
