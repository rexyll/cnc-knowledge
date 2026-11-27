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
    AuthorityStoreDelete,
    AuthorityStorePut,
    EtcdV3CoordinatorAuthorityStore,
)
from scripts.spare_parts_provider_etcd3gw_driver import Etcd3gwV3Client


@unittest.skipUnless(
    os.environ.get("ETCD_INTEGRATION") == "1",
    "set ETCD_INTEGRATION=1 and ETCD_ENDPOINTS to run against a live etcd v3 cluster",
)
class Etcd3gwLiveMinorityWatchProgressTests(unittest.TestCase):
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
        cls.cluster_network = f"{cls.project}_default"

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

    def _network_memberships(self, container_id: str) -> dict[str, dict]:
        raw = self._run([
            "docker", "inspect", "--format",
            '{{json .NetworkSettings.Networks}}', container_id,
        ]).stdout
        return json.loads(raw)

    def _network_details(self, network: str) -> dict:
        raw = self._run(["docker", "network", "inspect", network]).stdout
        details = json.loads(raw)
        if len(details) != 1:
            self.fail(f"expected exactly one inspected network for {network!r}")
        return details[0]

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

    def _create_access_network(self, network: str) -> None:
        self._run([
            "docker", "network", "create", "--driver", "bridge",
            "--label", f"cnc-knowledge.project={self.project}",
            "--label", "cnc-knowledge.purpose=watch-minority-isolation",
            network,
        ])
        details = self._network_details(network)
        labels = details.get("Labels") or {}
        self.assertEqual(labels.get("cnc-knowledge.project"), self.project)
        self.assertEqual(
            labels.get("cnc-knowledge.purpose"), "watch-minority-isolation"
        )

    def _remove_access_network(self, network: str) -> None:
        details = self._network_details(network)
        labels = details.get("Labels") or {}
        if (
            labels.get("cnc-knowledge.project") != self.project
            or labels.get("cnc-knowledge.purpose") != "watch-minority-isolation"
        ):
            self.fail(f"refusing to remove an unowned Docker network: {network!r}")
        self._run(["docker", "network", "rm", network])

    def test_isolated_member_progress_watermark_lags_quorum_and_snapshot_resume_is_safe(self):
        suffix = uuid4().hex
        key = f"/cnc-knowledge-it/watch-minority/{suffix}/leader".encode()
        initial_value = f"leader-before-partition-{suffix}".encode()
        partition_values = [
            f"leader-majority-update-{index}-{suffix}".encode()
            for index in range(1, 4)
        ]
        recovered_value = f"leader-after-snapshot-{suffix}".encode()
        access_network = f"{self.project}-watch-access-{suffix[:12]}"
        container_id = self._container_id("etcd1")

        access_network_created = False
        access_network_attached = False
        cluster_network_disconnected = False
        access_endpoint = None
        watch_driver = None
        majority_driver = None
        watch_store = None
        majority_store = None
        partition_stream = None
        resumed_stream = None
        observations: dict = {}

        try:
            # Give the isolated member a dedicated host-reachable control
            # network before removing its only peer network. This keeps the
            # server-stream connection alive without giving it a path to etcd2/3.
            self._create_access_network(access_network)
            access_network_created = True
            self._run(["docker", "network", "connect", access_network, container_id])
            access_network_attached = True

            memberships = self._network_memberships(container_id)
            self.assertIn(self.cluster_network, memberships)
            self.assertIn(access_network, memberships)
            access_ip = memberships[access_network].get("IPAddress")
            self.assertTrue(access_ip, "temporary access network has no container IPv4 address")
            access_endpoint = f"http://{access_ip}:2379"

            access_details = self._network_details(access_network)
            attached_containers = access_details.get("Containers") or {}
            self.assertEqual(set(attached_containers), {container_id})

            # Confirm the Compose network is the expected project network before
            # disconnecting etcd1 from it.
            cluster_details = self._network_details(self.cluster_network)
            cluster_labels = cluster_details.get("Labels") or {}
            self.assertEqual(
                cluster_labels.get("com.docker.compose.project"), self.project
            )
            self.assertEqual(
                cluster_labels.get("com.docker.compose.network"), "default"
            )

            majority_driver = Etcd3gwV3Client(self.endpoints[1:], timeout=3.0)
            majority_store = EtcdV3CoordinatorAuthorityStore(majority_driver)
            watch_driver = Etcd3gwV3Client([access_endpoint], timeout=3.0)
            watch_store = EtcdV3CoordinatorAuthorityStore(watch_driver)

            created_result = majority_store.transact(
                [], [AuthorityStorePut(key, initial_value)]
            )
            self.assertTrue(created_result.succeeded)
            current, baseline_revision = majority_store.linearizable_get(key)
            self.assertIsNotNone(current)
            self.assertEqual(current.value, initial_value)
            self.assertGreaterEqual(baseline_revision, created_result.revision)

            partition_stream = watch_store.watch(
                key,
                start_revision=baseline_revision + 1,
                progress_notify=True,
                prev_kv=True,
            )
            opened = self._next_result(partition_stream, timeout=8.0)
            self.assertEqual(opened[0], "response", opened[1])
            created = opened[1]
            self.assertTrue(created.created)
            self.assertFalse(created.canceled)
            self.assertEqual(created.events, ())

            # Isolate etcd1 from the two-member Raft majority while retaining
            # the stream over the dedicated single-member access network.
            self._run([
                "docker", "network", "disconnect",
                self.cluster_network, container_id,
            ])
            cluster_network_disconnected = True
            memberships = self._network_memberships(container_id)
            self.assertNotIn(self.cluster_network, memberships)
            self.assertIn(access_network, memberships)

            # The majority commits several revisions to the watched key. The
            # disconnected member must not apply them or emit their KV events.
            partition_results = []
            for value in partition_values:
                result = majority_store.transact([], [AuthorityStorePut(key, value)])
                self.assertTrue(result.succeeded)
                partition_results.append(result.revision)

            majority_entry, majority_revision = majority_store.linearizable_get(key)
            self.assertIsNotNone(majority_entry)
            self.assertEqual(majority_entry.value, partition_values[-1])
            self.assertGreater(majority_revision, created.header_revision)
            self.assertGreater(partition_results[-1], baseline_revision)

            progress_result = self._next_result(partition_stream, timeout=8.0)
            self.assertEqual(progress_result[0], "response", progress_result[1])
            progress = progress_result[1]
            self.assertTrue(progress.is_progress)
            self.assertEqual(progress.watch_id, created.watch_id)
            self.assertEqual(progress.events, ())
            self.assertFalse(progress.canceled)
            self.assertLess(
                progress.header_revision,
                majority_revision,
                "the isolated member's progress watermark unexpectedly reached the quorum revision",
            )
            self.assertEqual(progress.resume_revision, progress.header_revision + 1)

            # Require another periodic progress frame while the partition is
            # still active; it must remain a local watermark, not catch up.
            time.sleep(1.2)
            second_progress_result = self._next_result(partition_stream, timeout=5.0)
            self.assertEqual(
                second_progress_result[0], "response", second_progress_result[1]
            )
            second_progress = second_progress_result[1]
            self.assertTrue(second_progress.is_progress)
            self.assertEqual(second_progress.events, ())
            self.assertEqual(second_progress.watch_id, created.watch_id)
            self.assertLess(second_progress.header_revision, majority_revision)
            observations = {
                "watch_endpoint": access_endpoint,
                "created_watch_id": created.watch_id,
                "baseline_revision": baseline_revision,
                "majority_partition_revisions": partition_results,
                "majority_linearizable_revision": majority_revision,
                "isolated_progress_revision": progress.header_revision,
                "isolated_second_progress_revision": second_progress.header_revision,
                "isolated_progress_event_count": len(progress.events),
                "quorum_revision_exceeds_isolated_progress": (
                    majority_revision > progress.header_revision
                ),
                "quorum_value_after_partition": majority_entry.value.decode("utf-8"),
            }
            print(
                "WATCH_MINORITY_PROGRESS_OBSERVATION "
                + json.dumps(observations, sort_keys=True)
            )

            # Close the stale stream. Its progress cursor is not a snapshot
            # and must not be used to resume the application cache.
            partition_stream.close()
            partition_stream = None

            # Rejoin etcd1 to the exact Compose network; no host firewall or
            # unrelated container/network is modified.
            self._run([
                "docker", "network", "connect",
                self.cluster_network, container_id,
            ])
            cluster_network_disconnected = False
            memberships = self._network_memberships(container_id)
            self.assertIn(self.cluster_network, memberships)
            self._wait_for_quorum()

            # Rebuild from a quorum linearizable snapshot, then wait for etcd1
            # to be able to serve at least that applied revision.
            snapshot, snapshot_revision = majority_store.linearizable_get(key)
            self.assertIsNotNone(snapshot)
            self.assertEqual(snapshot.value, partition_values[-1])
            local_entry, local_revision = watch_store.linearizable_get(key)
            self.assertIsNotNone(local_entry)
            self.assertEqual(local_entry.value, snapshot.value)
            self.assertGreaterEqual(local_revision, snapshot_revision)

            resumed_stream = watch_store.watch(
                key,
                start_revision=snapshot_revision + 1,
                progress_notify=True,
                prev_kv=True,
            )
            resumed_created_result = self._next_result(resumed_stream, timeout=8.0)
            self.assertEqual(
                resumed_created_result[0], "response", resumed_created_result[1]
            )
            resumed_created = resumed_created_result[1]
            self.assertTrue(resumed_created.created)
            self.assertEqual(resumed_created.events, ())

            resumed_write = majority_store.transact(
                [], [AuthorityStorePut(key, recovered_value)]
            )
            self.assertTrue(resumed_write.succeeded)
            resumed_event_result = self._next_result(resumed_stream, timeout=8.0)
            self.assertEqual(
                resumed_event_result[0], "response", resumed_event_result[1]
            )
            resumed_response = resumed_event_result[1]
            self.assertFalse(resumed_response.canceled)
            self.assertEqual(len(resumed_response.events), 1)
            event = resumed_response.events[0]
            self.assertEqual(event.event_type, "PUT")
            self.assertEqual(event.key, key)
            self.assertIsNotNone(event.entry)
            self.assertEqual(event.entry.value, recovered_value)
            self.assertIsNotNone(event.previous_entry)
            self.assertEqual(event.previous_entry.value, partition_values[-1])
            self.assertEqual(event.revision, resumed_write.revision)
            self.assertGreater(event.revision, snapshot_revision)
            self.assertEqual(
                resumed_response.resume_revision, event.revision + 1
            )

            # The next response should be an event-free progress watermark:
            # none of the three already snapshotted partition writes may replay.
            post_event_result = self._next_result(resumed_stream, timeout=8.0)
            self.assertEqual(post_event_result[0], "response", post_event_result[1])
            post_event = post_event_result[1]
            self.assertTrue(post_event.is_progress)
            self.assertEqual(post_event.events, ())
            observations.update({
                "quorum_snapshot_revision": snapshot_revision,
                "recovered_member_linearizable_revision": local_revision,
                "resume_start_revision": snapshot_revision + 1,
                "post_recovery_write_revision": resumed_write.revision,
                "post_recovery_event_count": len(resumed_response.events),
                "post_recovery_event_value": event.entry.value.decode("utf-8"),
                "no_partition_write_replayed": True,
                "next_response_after_single_recovery_event_is_empty_progress": True,
            })
            print(
                "WATCH_MINORITY_RECOVERY_OBSERVATION "
                + json.dumps(observations, sort_keys=True)
            )
        finally:
            for stream in (partition_stream, resumed_stream):
                if stream is not None:
                    try:
                        stream.close()
                    except Exception:
                        pass

            # Restore the Compose peer network before any cleanup writes.
            try:
                memberships = self._network_memberships(container_id)
                if self.cluster_network not in memberships:
                    self._run([
                        "docker", "network", "connect",
                        self.cluster_network, container_id,
                    ])
                self._wait_for_quorum(timeout=60.0)
            finally:
                if majority_store is not None:
                    try:
                        current, _ = majority_store.linearizable_get(key)
                        if current is not None:
                            majority_store.transact([], [AuthorityStoreDelete(key)])
                    except Exception:
                        pass
                if watch_driver is not None:
                    watch_driver.close()
                if majority_driver is not None:
                    majority_driver.close()

                if access_network_created:
                    memberships = self._network_memberships(container_id)
                    if access_network in memberships:
                        self._run([
                            "docker", "network", "disconnect",
                            access_network, container_id,
                        ])
                    self._remove_access_network(access_network)


if __name__ == "__main__":
    unittest.main()
