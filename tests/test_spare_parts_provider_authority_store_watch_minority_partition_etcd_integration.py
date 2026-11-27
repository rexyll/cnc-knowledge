from __future__ import annotations

import concurrent.futures
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
    AuthorityStoreUnavailableError,
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

    def _create_access_network(
        self, network: str, *, purpose: str = "watch-minority-isolation"
    ) -> None:
        self._run([
            "docker", "network", "create", "--driver", "bridge",
            "--label", f"cnc-knowledge.project={self.project}",
            "--label", f"cnc-knowledge.purpose={purpose}",
            network,
        ])
        details = self._network_details(network)
        labels = details.get("Labels") or {}
        self.assertEqual(labels.get("cnc-knowledge.project"), self.project)
        self.assertEqual(
            labels.get("cnc-knowledge.purpose"), purpose
        )

    def _remove_access_network(
        self, network: str, *, purpose: str = "watch-minority-isolation"
    ) -> None:
        details = self._network_details(network)
        labels = details.get("Labels") or {}
        if (
            labels.get("cnc-knowledge.project") != self.project
            or labels.get("cnc-knowledge.purpose") != purpose
        ):
            self.fail(f"refusing to remove an unowned Docker network: {network!r}")
        self._run(["docker", "network", "rm", network])

    def test_isolated_member_progress_watermark_lags_quorum_and_snapshot_resume_is_safe(self):
        suffix = uuid4().hex
        key = f"/cnc-knowledge-it/watch-minority/{suffix}/leader".encode()
        initial_value = f"leader-before-partition-{suffix}".encode()
        baseline_marker_key = f"/cnc-knowledge-it/watch-minority/{suffix}/baseline".encode()
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
            # Advance the baseline beyond the watched-key PUT with an
            # unrelated key. Then a linearizable read through etcd1 forces
            # that member to apply the baseline revision before watch creation.
            marker_result = majority_store.transact(
                [], [AuthorityStorePut(baseline_marker_key, b"baseline")]
            )
            self.assertTrue(marker_result.succeeded)
            current, majority_baseline_revision = majority_store.linearizable_get(key)
            self.assertIsNotNone(current)
            self.assertEqual(current.value, initial_value)
            local_current, local_baseline_revision = watch_store.linearizable_get(key)
            self.assertIsNotNone(local_current)
            self.assertEqual(local_current.value, initial_value)
            self.assertGreaterEqual(majority_baseline_revision, marker_result.revision)
            self.assertGreaterEqual(local_baseline_revision, marker_result.revision)
            baseline_revision = local_baseline_revision

            partition_stream = watch_store.watch(
                key,
                # Watch start_revision is inclusive. The selected baseline is
                # later than the watched-key PUT and contains only an unrelated
                # marker, so it creates a synced watcher without replaying a
                # watched-key event. This is required for a local progress frame.
                start_revision=baseline_revision,
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
                "watched_key_put_revision": created_result.revision,
                "baseline_marker_revision": marker_result.revision,
                "majority_baseline_revision": majority_baseline_revision,
                "local_baseline_revision": local_baseline_revision,
                "watch_start_revision": baseline_revision,
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
                "docker", "network", "connect", "--ip", "172.29.64.11",
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

            # Membership/status recovery does not imply that the formerly
            # isolated member has already re-established ReadIndex service.
            # Retry only read-only linearizable probes until it serves the
            # quorum snapshot (or the bounded recovery deadline expires).
            local_entry = None
            local_revision = 0
            last_local_read_error: Exception | None = None
            local_read_deadline = time.monotonic() + 30.0
            while time.monotonic() < local_read_deadline:
                try:
                    candidate, candidate_revision = watch_store.linearizable_get(key)
                    if (
                        candidate is not None
                        and candidate.value == snapshot.value
                        and candidate_revision >= snapshot_revision
                    ):
                        local_entry = candidate
                        local_revision = candidate_revision
                        break
                    last_local_read_error = RuntimeError(
                        "reconnected member has not yet reached the quorum snapshot"
                    )
                except Exception as exc:
                    last_local_read_error = exc
                time.sleep(0.5)
            self.assertIsNotNone(
                local_entry,
                f"reconnected member did not serve the quorum snapshot; "
                f"last_error={last_local_read_error}",
            )
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
                        "docker", "network", "connect", "--ip", "172.29.64.11",
                        self.cluster_network, container_id,
                    ])
                self._wait_for_quorum(timeout=60.0)
            finally:
                if majority_store is not None:
                    try:
                        cleanup = []
                        for cleanup_key in (key, baseline_marker_key):
                            current, _ = majority_store.linearizable_get(cleanup_key)
                            if current is not None:
                                cleanup.append(AuthorityStoreDelete(cleanup_key))
                        if cleanup:
                            majority_store.transact([], cleanup)
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


    def test_minority_watch_is_canceled_by_quorum_compaction_then_snapshot_resumes(self):
        suffix = uuid4().hex
        key = f"/cnc-knowledge-it/watch-minority-compaction/{suffix}/leader".encode()
        baseline_marker_key = (
            f"/cnc-knowledge-it/watch-minority-compaction/{suffix}/baseline"
        ).encode()
        compaction_marker_key = (
            f"/cnc-knowledge-it/watch-minority-compaction/{suffix}/compaction-marker"
        ).encode()
        initial_value = f"leader-before-minority-compaction-{suffix}".encode()
        partition_values = [
            f"leader-quorum-update-{index}-{suffix}".encode()
            for index in range(1, 3)
        ]
        resumed_value = f"leader-after-compaction-snapshot-{suffix}".encode()
        access_network = f"{self.project}-watch-compact-{suffix[:12]}"
        etcd1_container = self._container_id("etcd1")
        etcd2_container = self._container_id("etcd2")

        access_network_created = False
        cluster_network_disconnected = False
        access_endpoint = None
        watch_driver = None
        majority_driver = None
        watch_store = None
        majority_store = None
        old_stream = None
        stale_stream = None
        resumed_stream = None
        observations: dict = {}

        try:
            # Keep a host-reachable path to etcd1 for the Watch stream while
            # removing only its peer path to etcd2/etcd3.
            self._create_access_network(
                access_network, purpose="watch-minority-compaction"
            )
            access_network_created = True
            self._run(["docker", "network", "connect", access_network, etcd1_container])

            memberships = self._network_memberships(etcd1_container)
            self.assertIn(self.cluster_network, memberships)
            self.assertIn(access_network, memberships)
            access_ip = memberships[access_network].get("IPAddress")
            self.assertTrue(access_ip, "temporary access network has no etcd1 IPv4 address")
            access_endpoint = f"http://{access_ip}:2379"
            self.assertEqual(
                set(self._network_details(access_network).get("Containers") or {}),
                {etcd1_container},
            )

            cluster_labels = self._network_details(self.cluster_network).get("Labels") or {}
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

            initial = majority_store.transact([], [AuthorityStorePut(key, initial_value)])
            self.assertTrue(initial.succeeded)
            marker = majority_store.transact(
                [], [AuthorityStorePut(baseline_marker_key, b"watch-baseline")]
            )
            self.assertTrue(marker.succeeded)

            majority_entry, majority_baseline_revision = majority_store.linearizable_get(key)
            self.assertIsNotNone(majority_entry)
            self.assertEqual(majority_entry.value, initial_value)
            local_entry, local_baseline_revision = watch_store.linearizable_get(key)
            self.assertIsNotNone(local_entry)
            self.assertEqual(local_entry.value, initial_value)
            self.assertGreaterEqual(majority_baseline_revision, marker.revision)
            self.assertGreaterEqual(local_baseline_revision, marker.revision)
            watch_start_revision = local_baseline_revision

            old_stream = watch_store.watch(
                key,
                start_revision=watch_start_revision,
                progress_notify=True,
                prev_kv=True,
            )
            created_result = self._next_result(old_stream, timeout=8.0)
            self.assertEqual(created_result[0], "response", created_result[1])
            created = created_result[1]
            self.assertTrue(created.created)
            self.assertFalse(created.canceled)
            self.assertEqual(created.events, ())

            # Partition etcd1 after its watcher has synced at the baseline.
            self._run([
                "docker", "network", "disconnect",
                self.cluster_network, etcd1_container,
            ])
            cluster_network_disconnected = True
            memberships = self._network_memberships(etcd1_container)
            self.assertNotIn(self.cluster_network, memberships)
            self.assertIn(access_network, memberships)

            # The remaining two-member majority commits new KV revisions.
            partition_write_revisions = []
            for value in partition_values:
                result = majority_store.transact(
                    [], [AuthorityStorePut(compaction_marker_key, value)]
                )
                self.assertTrue(result.succeeded)
                partition_write_revisions.append(result.revision)
            self.assertEqual(
                partition_write_revisions,
                sorted(partition_write_revisions),
            )
            self.assertGreater(partition_write_revisions[0], watch_start_revision)

            majority_latest, majority_revision = majority_store.linearizable_get(
                compaction_marker_key
            )
            self.assertIsNotNone(majority_latest)
            self.assertEqual(majority_latest.value, partition_values[-1])
            self.assertGreaterEqual(majority_revision, partition_write_revisions[-1])

            # Compact on etcd2, which remains in the quorum. The container must
            # belong to this exact disposable Compose project/service.
            compacted_revision = partition_write_revisions[-1]
            compact_result = self._run([
                "docker", "exec", etcd2_container,
                "/usr/local/bin/etcdctl",
                "--endpoints=http://127.0.0.1:2379",
                "--dial-timeout=2s",
                "--command-timeout=10s",
                "compact", str(compacted_revision),
            ], timeout=15.0)
            self.assertEqual(compact_result.returncode, 0, compact_result.stderr)
            self.assertGreater(compacted_revision, watch_start_revision)

            # Reconnect etcd1 to the exact Compose peer network before
            # beginning recovery. Preserve the statically advertised Raft IP.
            self._run([
                "docker", "network", "connect", "--ip", "172.29.64.11",
                self.cluster_network, etcd1_container,
            ])
            cluster_network_disconnected = False
            rejoined_memberships = self._network_memberships(etcd1_container)
            self.assertIn(self.cluster_network, rejoined_memberships)
            self.assertEqual(
                rejoined_memberships[self.cluster_network].get("IPAddress"),
                "172.29.64.11",
                "reconnected etcd1 did not retain its static Raft peer address",
            )
            self._wait_for_quorum(timeout=60.0)

            # Use a linearizable snapshot from the surviving quorum as the
            # authoritative recovery point. A recently reconnected minority
            # can still be electing/catching up; don't make its ReadIndex
            # readiness a prerequisite for application Watch reconstruction.
            snapshot, snapshot_revision = majority_store.linearizable_get(key)
            self.assertIsNotNone(snapshot)
            self.assertEqual(snapshot.value, initial_value)
            self.assertGreaterEqual(snapshot_revision, compacted_revision)

            old_stream.close()
            stale_stream = majority_store.watch(
                key,
                start_revision=watch_start_revision,
                progress_notify=False,
                prev_kv=True,
            )
            stale_first_result = self._next_result(stale_stream, timeout=8.0)
            self.assertEqual(
                stale_first_result[0], "response", stale_first_result[1]
            )
            stale_first = stale_first_result[1]
            if stale_first.created:
                self.assertFalse(stale_first.canceled)
                self.assertEqual(stale_first.events, ())
                stale_cancel_result = self._next_result(stale_stream, timeout=8.0)
                self.assertEqual(
                    stale_cancel_result[0], "response", stale_cancel_result[1]
                )
                stale_canceled = stale_cancel_result[1]
            else:
                stale_canceled = stale_first
            self.assertTrue(stale_canceled.canceled)
            self.assertFalse(stale_canceled.created)
            self.assertEqual(stale_canceled.compact_revision, compacted_revision)
            self.assertEqual(stale_canceled.events, ())
            self.assertIsNone(stale_canceled.resume_revision)
            self.assertIsInstance(stale_canceled.cancel_reason, str)
            if stale_canceled.cancel_reason:
                self.assertIn("compact", stale_canceled.cancel_reason.lower())
            stale_stream.close()

            # Recreate the stream only from the authoritative snapshot+1 cursor.
            resumed_stream = majority_store.watch(
                key,
                start_revision=snapshot_revision + 1,
                progress_notify=False,
                prev_kv=True,
            )
            resumed_created_result = self._next_result(resumed_stream, timeout=8.0)
            self.assertEqual(
                resumed_created_result[0], "response", resumed_created_result[1]
            )
            resumed_created = resumed_created_result[1]
            self.assertTrue(resumed_created.created)
            self.assertFalse(resumed_created.canceled)
            self.assertEqual(resumed_created.events, ())

            post_snapshot_write = majority_store.transact(
                [], [AuthorityStorePut(key, resumed_value)]
            )
            self.assertTrue(post_snapshot_write.succeeded)
            self.assertGreater(post_snapshot_write.revision, snapshot_revision)
            resumed_result = self._next_result(resumed_stream, timeout=10.0)
            self.assertEqual(resumed_result[0], "response", resumed_result[1])
            resumed_response = resumed_result[1]
            self.assertFalse(resumed_response.canceled)
            self.assertEqual(len(resumed_response.events), 1)
            resumed_event = resumed_response.events[0]
            self.assertEqual(resumed_event.event_type, "PUT")
            self.assertEqual(resumed_event.key, key)
            self.assertEqual(resumed_event.entry.value, resumed_value)
            self.assertIsNotNone(resumed_event.previous_entry)
            self.assertEqual(resumed_event.previous_entry.value, initial_value)
            self.assertEqual(resumed_event.revision, post_snapshot_write.revision)
            self.assertEqual(
                resumed_response.resume_revision, post_snapshot_write.revision + 1
            )

            observations = {
                "watch_endpoint": access_endpoint,
                "watch_start_revision": watch_start_revision,
                "majority_partition_write_revisions": partition_write_revisions,
                "majority_compact_revision": compacted_revision,
                "compact_command_stdout": compact_result.stdout.strip(),
                "majority_linearizable_revision_before_rejoin": majority_revision,
                "original_minority_watch_closed_for_rebuild": True,
                "reconnected_etcd1_static_peer_ip": rejoined_memberships[self.cluster_network].get("IPAddress"),
                "stale_cursor_and_resumed_watch_endpoint": "healthy_quorum",
                "stale_cursor_watch_canceled": stale_canceled.canceled,
                "stale_cursor_cancel_compact_revision": stale_canceled.compact_revision,
                "stale_cursor_cancel_event_count": len(stale_canceled.events),
                "stale_cursor_cancel_resume_revision": stale_canceled.resume_revision,
                "quorum_snapshot_revision": snapshot_revision,
                "resume_start_revision": snapshot_revision + 1,
                "post_snapshot_write_revision": post_snapshot_write.revision,
                "post_snapshot_event_count": len(resumed_response.events),
                "no_compacted_event_replayed_after_snapshot": (
                    resumed_event.revision == post_snapshot_write.revision
                    and resumed_event.revision > snapshot_revision
                ),
                "post_snapshot_event_delivered_once": len(resumed_response.events) == 1,
            }
            print(
                "WATCH_MINORITY_COMPACTION_RECOVERY_OBSERVATION "
                + json.dumps(observations, sort_keys=True)
            )
        finally:
            for stream in (old_stream, stale_stream, resumed_stream):
                if stream is not None:
                    try:
                        stream.close()
                    except Exception:
                        pass

            # Always restore the Compose peer network before cleanup writes.
            try:
                memberships = self._network_memberships(etcd1_container)
                if self.cluster_network not in memberships:
                    self._run([
                        "docker", "network", "connect", "--ip", "172.29.64.11",
                        self.cluster_network, etcd1_container,
                    ])
                self._wait_for_quorum(timeout=60.0)
            finally:
                if majority_store is not None:
                    try:
                        cleanup = []
                        for cleanup_key in (key, baseline_marker_key, compaction_marker_key):
                            current, _ = majority_store.linearizable_get(cleanup_key)
                            if current is not None:
                                cleanup.append(AuthorityStoreDelete(cleanup_key))
                        if cleanup:
                            majority_store.transact([], cleanup)
                    except Exception:
                        pass
                if watch_driver is not None:
                    watch_driver.close()
                if majority_driver is not None:
                    majority_driver.close()

                if access_network_created:
                    memberships = self._network_memberships(etcd1_container)
                    if access_network in memberships:
                        self._run([
                            "docker", "network", "disconnect",
                            access_network, etcd1_container,
                        ])
                    self._remove_access_network(
                        access_network, purpose="watch-minority-compaction"
                    )


    def test_long_running_watch_rebuilds_client_cache_across_periodic_compactions(self):
        suffix = uuid4().hex
        prefix = f"/cnc-knowledge-it/watch-long-running/{suffix}/state/".encode()
        range_end = prefix[:-1] + b"0"
        progress_marker_key = f"/cnc-knowledge-it/watch-long-running/{suffix}/progress-marker".encode()
        keys = [prefix + f"state-{index}".encode() for index in range(4)]
        initial_values = [
            f"initial-{index}-{suffix}".encode() for index in range(len(keys))
        ]
        etcd2_container = self._container_id("etcd2")

        majority_driver = Etcd3gwV3Client(self.endpoints[1:], timeout=3.0)
        majority_store = EtcdV3CoordinatorAuthorityStore(majority_driver)
        watch_driver = Etcd3gwV3Client([self.endpoints[0]], timeout=3.0)
        watch_store = EtcdV3CoordinatorAuthorityStore(watch_driver)
        streams = []
        active_stream = None
        gap_thread = None
        gap_release = threading.Event()
        gap_first_write = threading.Event()
        gap_results: list[int] = []
        gap_errors: list[BaseException] = []
        seen_events: set[tuple[int, bytes, str]] = set()
        event_revisions: list[int] = []
        cache: dict[bytes, bytes] = {}
        snapshot_revisions: list[int] = []
        compact_revisions: list[int] = []
        progress_revisions: list[int] = []

        def take_snapshot() -> tuple[int, dict[bytes, bytes]]:
            result = majority_store.linearizable_range(
                prefix, range_end=range_end
            )
            snapshot_revisions.append(result.revision)
            return result.revision, {
                entry.key: entry.value for entry in result.entries
            }

        def assert_cache_matches_snapshot(
            expected: dict[bytes, bytes], actual: dict[bytes, bytes]
        ) -> None:
            self.assertEqual(actual, expected)

        def open_watch(start_revision: int):
            local_applied = watch_store.linearizable_range(
                prefix, range_end=range_end
            )
            self.assertGreaterEqual(
                local_applied.revision, start_revision - 1,
                "etcd1 has not linearly applied the snapshot before Watch creation",
            )
            stream = watch_store.watch(
                prefix,
                start_revision=start_revision,
                range_end=range_end,
                progress_notify=True,
                prev_kv=True,
            )
            opened = self._next_result(stream, timeout=10.0)
            self.assertEqual(opened[0], "response", opened[1])
            response = opened[1]
            self.assertTrue(response.created)
            self.assertFalse(response.canceled)
            self.assertEqual(response.events, ())
            self.assertIsNone(response.resume_revision)
            streams.append(stream)
            return stream

        def consume_events(stream, expected_count: int) -> list[int]:
            received_revisions: list[int] = []
            last_event_revision = 0
            last_progress_revision = 0
            while len(received_revisions) < expected_count:
                outcome = self._next_result(stream, timeout=12.0)
                self.assertEqual(outcome[0], "response", outcome[1])
                response = outcome[1]
                self.assertFalse(response.canceled)
                self.assertFalse(response.created)
                self.assertFalse(
                    response.fragment,
                    "the client cache must not apply an incomplete fragmented response",
                )
                if response.is_progress:
                    self.assertEqual(response.events, ())
                    self.assertGreaterEqual(
                        response.header_revision, last_progress_revision
                    )
                    last_progress_revision = response.header_revision
                    progress_revisions.append(response.header_revision)
                    continue
                self.assertTrue(response.events)
                self.assertEqual(
                    response.resume_revision, response.header_revision + 1
                )
                for event in response.events:
                    self.assertGreaterEqual(event.revision, last_event_revision)
                    last_event_revision = event.revision
                    self.assertTrue(prefix <= event.key < range_end)
                    identity = (event.revision, event.key, event.event_type)
                    self.assertNotIn(
                        identity, seen_events,
                        "a Watch event was delivered more than once across rebuilds",
                    )
                    seen_events.add(identity)
                    event_revisions.append(event.revision)
                    received_revisions.append(event.revision)

                    previous = event.previous_entry
                    if previous is not None:
                        self.assertEqual(cache.get(event.key), previous.value)
                    if event.event_type == "PUT":
                        self.assertIsNotNone(event.entry)
                        cache[event.key] = event.entry.value
                    elif event.event_type == "DELETE":
                        self.assertIsNone(event.entry)
                        self.assertIsNotNone(previous)
                        self.assertIn(event.key, cache)
                        del cache[event.key]
                    else:
                        self.fail(f"unexpected Watch event type: {event.event_type!r}")
            return received_revisions

        def write_parallel(groups):
            barrier = threading.Barrier(len(groups))

            def write_group(endpoint: str, operations):
                driver = Etcd3gwV3Client([endpoint], timeout=4.0)
                store = EtcdV3CoordinatorAuthorityStore(driver)
                revisions = []
                try:
                    barrier.wait(timeout=8.0)
                    for kind, key, value in operations:
                        operation = (
                            AuthorityStorePut(key, value)
                            if kind == "PUT"
                            else AuthorityStoreDelete(key)
                        )
                        result = store.transact([], [operation])
                        if not result.succeeded:
                            raise AssertionError(
                                f"concurrent {kind} transaction failed for {key!r}"
                            )
                        revisions.append(result.revision)
                    return revisions
                finally:
                    driver.close()

            expected_events = sum(len(operations) for _, operations in groups)
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=len(groups)
            ) as pool:
                futures = [
                    pool.submit(write_group, endpoint, operations)
                    for endpoint, operations in groups
                ]
                received = consume_events(active_stream, expected_events)
                revisions = [
                    revision
                    for future in futures
                    for revision in future.result(timeout=25.0)
                ]
            self.assertEqual(sorted(received), sorted(revisions))
            return revisions

        def compact_at(revision: int) -> str:
            compact_result = self._run(
                [
                    "docker", "exec", etcd2_container,
                    "/usr/local/bin/etcdctl",
                    "--endpoints=http://127.0.0.1:2379",
                    "--dial-timeout=2s",
                    "--command-timeout=10s",
                    "compact", str(revision),
                ],
                timeout=15.0,
            )
            self.assertEqual(compact_result.returncode, 0, compact_result.stderr)
            self.assertIn("compacted revision", compact_result.stdout.lower())
            compact_revisions.append(revision)
            return compact_result.stdout.strip()

        def assert_old_cursor_canceled(start_revision: int, compact_revision: int):
            stale = majority_store.watch(
                prefix,
                start_revision=start_revision,
                range_end=range_end,
                progress_notify=False,
                prev_kv=True,
            )
            try:
                first = self._next_result(stale, timeout=10.0)
                self.assertEqual(first[0], "response", first[1])
                canceled = first[1]
                if canceled.created:
                    self.assertFalse(canceled.canceled)
                    self.assertEqual(canceled.events, ())
                    next_result = self._next_result(stale, timeout=10.0)
                    self.assertEqual(next_result[0], "response", next_result[1])
                    canceled = next_result[1]
                self.assertTrue(canceled.canceled)
                self.assertFalse(canceled.created)
                self.assertGreaterEqual(
                    canceled.compact_revision, compact_revision
                )
                self.assertEqual(canceled.events, ())
                self.assertIsNone(canceled.resume_revision)
            finally:
                stale.close()

        def write_gap_after_snapshot():
            driver = Etcd3gwV3Client([self.endpoints[2]], timeout=4.0)
            store = EtcdV3CoordinatorAuthorityStore(driver)
            try:
                before = store.transact(
                    [], [AuthorityStorePut(keys[0], b"gap-before-snapshot")]
                )
                if not before.succeeded:
                    raise AssertionError("pre-snapshot gap write failed")
                gap_results.append(before.revision)
                gap_first_write.set()
                if not gap_release.wait(timeout=15.0):
                    raise TimeoutError("snapshot did not release the gap writer")
                for key, value in (
                    (keys[1], b"gap-after-snapshot-1"),
                    (keys[2], b"gap-after-snapshot-2"),
                ):
                    result = store.transact([], [AuthorityStorePut(key, value)])
                    if not result.succeeded:
                        raise AssertionError("post-snapshot gap write failed")
                    gap_results.append(result.revision)
            except BaseException as exc:
                gap_errors.append(exc)
                gap_first_write.set()
            finally:
                driver.close()

        try:
            seed = majority_store.transact(
                [],
                [
                    AuthorityStorePut(key, value)
                    for key, value in zip(keys, initial_values)
                ],
            )
            self.assertTrue(seed.succeeded)

            initial_snapshot_revision, cache = take_snapshot()
            self.assertEqual(set(cache), set(keys))
            first_cursor = initial_snapshot_revision + 1
            active_stream = open_watch(first_cursor)

            # Keep the stream open across an idle interval and confirm that a
            # periodic Progress frame is not mistaken for a KV cache mutation.
            time.sleep(1.15)
            progress_marker = majority_store.transact(
                [], [AuthorityStorePut(progress_marker_key, b"progress-trigger")]
            )
            self.assertTrue(progress_marker.succeeded)
            progress = self._next_result(active_stream, timeout=8.0)
            self.assertEqual(progress[0], "response", progress[1])
            self.assertTrue(progress[1].is_progress)
            self.assertEqual(progress[1].events, ())
            progress_revisions.append(progress[1].header_revision)
            cache_before_progress = dict(cache)
            self.assertEqual(cache, cache_before_progress)

            first_writes = write_parallel(
                [
                    (
                        self.endpoints[1],
                        [
                            ("PUT", keys[0], b"cycle-1-a"),
                            ("PUT", keys[1], b"cycle-1-b"),
                        ],
                    ),
                    (
                        self.endpoints[2],
                        [
                            ("PUT", keys[2], b"cycle-1-c"),
                            ("PUT", keys[3], b"cycle-1-d"),
                        ],
                    ),
                ]
            )
            self.assertEqual(len(first_writes), 4)
            first_live_snapshot_revision, first_live_snapshot = take_snapshot()
            assert_cache_matches_snapshot(first_live_snapshot, cache)

            active_stream.close()
            active_stream = None
            first_compact_output = compact_at(first_live_snapshot_revision)
            assert_old_cursor_canceled(first_cursor, first_live_snapshot_revision)

            # A background writer straddles snapshot/re-watch reconstruction:
            # the first update is included in the snapshot; the next two occur
            # after R and must replay from the new watch's inclusive R+1 cursor.
            gap_thread = threading.Thread(
                target=write_gap_after_snapshot, daemon=True
            )
            gap_thread.start()
            self.assertTrue(
                gap_first_write.wait(timeout=10.0),
                "gap writer did not commit its pre-snapshot update",
            )
            if gap_errors:
                raise gap_errors[0]

            second_snapshot_revision, cache = take_snapshot()
            self.assertIn(keys[0], cache)
            self.assertEqual(cache[keys[0]], b"gap-before-snapshot")
            gap_release.set()
            gap_thread.join(timeout=20.0)
            self.assertFalse(gap_thread.is_alive(), "gap writer did not finish")
            if gap_errors:
                raise gap_errors[0]
            self.assertEqual(len(gap_results), 3)
            self.assertLessEqual(gap_results[0], second_snapshot_revision)
            self.assertTrue(
                all(revision > second_snapshot_revision for revision in gap_results[1:])
            )

            second_cursor = second_snapshot_revision + 1
            active_stream = open_watch(second_cursor)
            gap_event_revisions = consume_events(active_stream, 2)
            self.assertEqual(sorted(gap_event_revisions), sorted(gap_results[1:]))
            after_gap_revision, after_gap_snapshot = take_snapshot()
            assert_cache_matches_snapshot(after_gap_snapshot, cache)
            self.assertGreaterEqual(after_gap_revision, gap_results[-1])

            # Continue consuming a live stream while two independent writers
            # update/delete different keys concurrently.
            second_writes = write_parallel(
                [
                    (
                        self.endpoints[1],
                        [
                            ("PUT", keys[0], b"cycle-2-a"),
                            ("DELETE", keys[1], None),
                        ],
                    ),
                    (
                        self.endpoints[2],
                        [
                            ("PUT", keys[2], b"cycle-2-c"),
                            ("PUT", keys[3], b"cycle-2-d"),
                        ],
                    ),
                ]
            )
            self.assertEqual(len(second_writes), 4)
            second_live_revision, second_live_snapshot = take_snapshot()
            assert_cache_matches_snapshot(second_live_snapshot, cache)

            active_stream.close()
            active_stream = None
            second_compact_output = compact_at(second_live_revision)
            assert_old_cursor_canceled(second_cursor, second_live_revision)

            # Replace the entire client cache from a second authoritative
            # snapshot; no old event cursor is carried into the next stream.
            third_snapshot_revision, cache = take_snapshot()
            assert_cache_matches_snapshot(second_live_snapshot, cache)
            third_cursor = third_snapshot_revision + 1
            active_stream = open_watch(third_cursor)

            final_write = majority_store.transact(
                [], [AuthorityStorePut(keys[1], b"after-second-compaction")]
            )
            self.assertTrue(final_write.succeeded)
            final_event_revisions = consume_events(active_stream, 1)
            self.assertEqual(final_event_revisions, [final_write.revision])

            final_snapshot_revision, final_snapshot = take_snapshot()
            assert_cache_matches_snapshot(final_snapshot, cache)
            self.assertGreaterEqual(final_snapshot_revision, final_write.revision)

            observations = {
                "prefix": prefix.decode("utf-8"),
                "snapshot_revisions": snapshot_revisions,
                "compaction_revisions": compact_revisions,
                "first_compaction_output": first_compact_output,
                "second_compaction_output": second_compact_output,
                "old_cursor_cancel_count": len(compact_revisions),
                "resume_cursors": [
                    first_cursor, second_cursor, third_cursor
                ],
                "gap_writer_revisions": gap_results,
                "concurrent_write_revisions": first_writes + second_writes,
                "final_write_revision": final_write.revision,
                "progress_frame_revisions": progress_revisions,
                "progress_trigger_marker_revision": progress_marker.revision,
                "unique_watch_event_count": len(seen_events),
                "watch_event_revisions": event_revisions,
                "final_cache_matches_linearizable_range": True,
                "snapshot_before_watch_gap_replayed_from_r_plus_one": (
                    sorted(gap_event_revisions) == sorted(gap_results[1:])
                ),
                "cache_replaced_after_each_compaction": len(compact_revisions) == 2,
                "duplicate_watch_events": 0,
            }
            print(
                "WATCH_LONG_RUNNING_COMPACTION_CACHE_OBSERVATION "
                + json.dumps(observations, sort_keys=True)
            )
        finally:
            gap_release.set()
            if gap_thread is not None:
                gap_thread.join(timeout=20.0)
            if active_stream is not None:
                try:
                    active_stream.close()
                except Exception:
                    pass
            for stream in streams:
                try:
                    stream.close()
                except Exception:
                    pass
            try:
                remaining = majority_store.linearizable_range(
                    prefix, range_end=range_end
                )
                cleanup_operations = [
                    AuthorityStoreDelete(entry.key) for entry in remaining.entries
                ]
                marker_entry, _ = majority_store.linearizable_get(progress_marker_key)
                if marker_entry is not None:
                    cleanup_operations.append(AuthorityStoreDelete(progress_marker_key))
                if cleanup_operations:
                    majority_store.transact([], cleanup_operations)
            except Exception:
                pass
            watch_driver.close()
            majority_driver.close()


    def test_slow_watch_consumer_drains_backlog_or_rebuilds_after_compaction(self):
        suffix = uuid4().hex
        prefix = f"/cnc-knowledge-it/watch-slow-consumer/{suffix}/state/".encode()
        range_end = prefix[:-1] + b"0"
        seed_key = prefix + b"seed"
        final_key = prefix + b"after-rebuild"
        etcd2_container = self._container_id("etcd2")

        majority_driver = Etcd3gwV3Client(self.endpoints[1:], timeout=4.0)
        majority_store = EtcdV3CoordinatorAuthorityStore(majority_driver)
        watch_driver = Etcd3gwV3Client([self.endpoints[0]], timeout=4.0)
        watch_store = EtcdV3CoordinatorAuthorityStore(watch_driver)

        streams = []
        active_stream = None
        writer_threads: list[threading.Thread] = []
        writer_errors: list[BaseException] = []
        writer_results: dict[str, list[int]] = {}
        writer_done: dict[str, threading.Event] = {}
        applied_identities: set[tuple[int, bytes, str]] = set()
        all_event_revisions: list[int] = []
        response_counts: list[int] = []
        max_events_per_response = 0
        progress_revisions: list[int] = []
        slow_pause_seconds = 0.8
        slow_response_delay_seconds = 0.008

        def take_snapshot() -> tuple[int, dict[bytes, bytes]]:
            result = majority_store.linearizable_range(prefix, range_end=range_end)
            return result.revision, {
                entry.key: entry.value for entry in result.entries
            }

        def open_watch(start_revision: int):
            local_applied = watch_store.linearizable_range(
                prefix, range_end=range_end
            )
            self.assertGreaterEqual(
                local_applied.revision,
                start_revision - 1,
                "etcd1 has not applied the snapshot before opening the slow-consumer Watch",
            )
            stream = watch_store.watch(
                prefix,
                start_revision=start_revision,
                range_end=range_end,
                progress_notify=True,
                prev_kv=True,
            )
            opened = self._next_result(stream, timeout=10.0)
            self.assertEqual(opened[0], "response", opened[1])
            self.assertTrue(opened[1].created)
            self.assertFalse(opened[1].canceled)
            self.assertEqual(opened[1].events, ())
            self.assertIsNone(opened[1].resume_revision)
            streams.append(stream)
            return stream

        def start_writer(name: str, first_index: int, count: int):
            done = threading.Event()
            revisions: list[int] = []
            writer_done[name] = done
            writer_results[name] = revisions

            def write_batch():
                driver = Etcd3gwV3Client([self.endpoints[2]], timeout=4.0)
                store = EtcdV3CoordinatorAuthorityStore(driver)
                try:
                    for index in range(first_index, first_index + count):
                        key = prefix + f"{name}-{index:04d}".encode()
                        value = (
                            f"{name}:{index:04d}:{suffix}:".encode()
                            + (b"x" * 192)
                        )
                        result = store.transact([], [AuthorityStorePut(key, value)])
                        if not result.succeeded:
                            raise AssertionError(
                                f"backlog writer transaction failed at index {index}"
                            )
                        revisions.append(result.revision)
                except BaseException as exc:
                    writer_errors.append(exc)
                finally:
                    driver.close()
                    done.set()

            thread = threading.Thread(target=write_batch, daemon=True)
            writer_threads.append(thread)
            thread.start()

        def wait_writer(name: str):
            self.assertTrue(
                writer_done[name].wait(timeout=30.0),
                f"writer {name!r} did not finish within the bounded test window",
            )
            for thread in writer_threads:
                thread.join(timeout=1.0)
            if writer_errors:
                raise writer_errors[0]
            self.assertTrue(writer_results[name], f"writer {name!r} produced no revisions")
            return list(writer_results[name])

        def apply_response(response, cache: dict[bytes, bytes]) -> int:
            nonlocal max_events_per_response
            self.assertFalse(response.created)
            self.assertFalse(response.canceled)
            self.assertFalse(
                response.fragment,
                "an incomplete fragmented response must not be applied to the cache",
            )
            if response.is_progress:
                self.assertEqual(response.events, ())
                progress_revisions.append(response.header_revision)
                return 0

            self.assertTrue(response.events)
            self.assertEqual(
                response.resume_revision, response.header_revision + 1
            )
            response_counts.append(len(response.events))
            max_events_per_response = max(
                max_events_per_response, len(response.events)
            )
            last_revision = all_event_revisions[-1] if all_event_revisions else 0
            for event in response.events:
                self.assertTrue(prefix <= event.key < range_end)
                self.assertGreaterEqual(event.revision, last_revision)
                last_revision = event.revision
                identity = (event.revision, event.key, event.event_type)
                self.assertNotIn(
                    identity,
                    applied_identities,
                    "a slow-consumer Watch event was applied more than once",
                )
                applied_identities.add(identity)
                all_event_revisions.append(event.revision)

                if event.event_type == "PUT":
                    self.assertIsNotNone(event.entry)
                    if event.previous_entry is not None:
                        self.assertEqual(
                            cache.get(event.key), event.previous_entry.value
                        )
                    cache[event.key] = event.entry.value
                elif event.event_type == "DELETE":
                    self.assertIsNone(event.entry)
                    self.assertIsNotNone(event.previous_entry)
                    self.assertIn(event.key, cache)
                    self.assertEqual(
                        cache[event.key], event.previous_entry.value
                    )
                    del cache[event.key]
                else:
                    self.fail(f"unexpected event type {event.event_type!r}")
            return len(response.events)

        def consume_backlog(
            stream,
            expected_count: int,
            cache: dict[bytes, bytes],
            *,
            cancel_is_allowed: bool,
        ) -> tuple[str, int, int]:
            received = 0
            frames = 0
            while received < expected_count:
                outcome = self._next_result(stream, timeout=12.0)
                self.assertEqual(outcome[0], "response", outcome[1])
                response = outcome[1]
                frames += 1
                if response.canceled:
                    self.assertTrue(cancel_is_allowed)
                    self.assertEqual(response.events, ())
                    self.assertIsNone(response.resume_revision)
                    self.assertGreaterEqual(
                        response.compact_revision,
                        max(writer_results.get("compaction-burst", [0])),
                    )
                    return "canceled", received, frames
                self.assertEqual(apply_response(response, cache), len(response.events))
                received += len(response.events)
                if response.is_progress and received < expected_count:
                    self.assertLess(
                        response.header_revision,
                        max(writer_results.get("compaction-burst", [0])),
                        "Progress passed the committed backlog without delivering its events",
                    )
                if received < expected_count and response.events:
                    time.sleep(slow_response_delay_seconds)
            return "drained", received, frames

        def compact_at(revision: int) -> str:
            result = self._run(
                [
                    "docker", "exec", etcd2_container,
                    "/usr/local/bin/etcdctl",
                    "--endpoints=http://127.0.0.1:2379",
                    "--dial-timeout=2s",
                    "--command-timeout=10s",
                    "compact", str(revision),
                ],
                timeout=15.0,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("compacted revision", result.stdout.lower())
            return result.stdout.strip()

        def assert_old_cursor_canceled(start_revision: int, compact_revision: int):
            stale = majority_store.watch(
                prefix,
                start_revision=start_revision,
                range_end=range_end,
                progress_notify=False,
                prev_kv=True,
            )
            try:
                first = self._next_result(stale, timeout=10.0)
                self.assertEqual(first[0], "response", first[1])
                canceled = first[1]
                if canceled.created:
                    self.assertFalse(canceled.canceled)
                    self.assertEqual(canceled.events, ())
                    next_result = self._next_result(stale, timeout=10.0)
                    self.assertEqual(next_result[0], "response", next_result[1])
                    canceled = next_result[1]
                self.assertTrue(canceled.canceled)
                self.assertGreaterEqual(canceled.compact_revision, compact_revision)
                self.assertEqual(canceled.events, ())
                self.assertIsNone(canceled.resume_revision)
            finally:
                stale.close()

        cache: dict[bytes, bytes] = {}
        observations: dict = {}

        try:
            seed = majority_store.transact(
                [], [AuthorityStorePut(seed_key, f"seed-{suffix}".encode())]
            )
            self.assertTrue(seed.succeeded)
            initial_revision, cache = take_snapshot()
            self.assertEqual(cache, {seed_key: f"seed-{suffix}".encode()})

            # Phase 1: the producer commits a finite burst while the application
            # does not call next(stream); the application then resumes slowly.
            first_cursor = initial_revision + 1
            active_stream = open_watch(first_cursor)
            first_count = 64
            start_writer("slow-burst", 0, first_count)
            first_revisions = wait_writer("slow-burst")
            self.assertEqual(len(first_revisions), first_count)
            time.sleep(slow_pause_seconds)
            slow_mode, slow_received, slow_frames = consume_backlog(
                active_stream,
                first_count,
                cache,
                cancel_is_allowed=False,
            )
            self.assertEqual(slow_mode, "drained")
            self.assertEqual(slow_received, first_count)
            self.assertEqual(sorted(all_event_revisions), sorted(first_revisions))
            slow_snapshot_revision, slow_snapshot = take_snapshot()
            self.assertEqual(cache, slow_snapshot)

            active_stream.close()
            active_stream = None

            # Phase 2: establish a new Watch and deliberately withhold reads
            # while a second finite burst is committed and compacted.
            second_cursor = slow_snapshot_revision + 1
            active_stream = open_watch(second_cursor)
            second_count = 96
            start_writer("compaction-burst", 0, second_count)
            second_revisions = wait_writer("compaction-burst")
            self.assertEqual(len(second_revisions), second_count)
            self.assertEqual(second_revisions, sorted(second_revisions))
            compact_revision = second_revisions[-1]
            compact_output = compact_at(compact_revision)
            time.sleep(slow_pause_seconds)

            race_mode, race_received, race_frames = consume_backlog(
                active_stream,
                second_count,
                cache,
                cancel_is_allowed=True,
            )
            if race_mode == "drained":
                self.assertEqual(race_received, second_count)
                self.assertEqual(
                    sorted(all_event_revisions[-second_count:]),
                    sorted(second_revisions),
                )
                before_rebuild_revision, before_rebuild_snapshot = take_snapshot()
                self.assertGreaterEqual(before_rebuild_revision, compact_revision)
                self.assertEqual(cache, before_rebuild_snapshot)
            else:
                self.assertLess(race_received, second_count)
                race_delivered_revisions = (
                    all_event_revisions[-race_received:] if race_received else []
                )
                self.assertEqual(
                    set(race_delivered_revisions),
                    set(second_revisions[:race_received]),
                )

            active_stream.close()
            active_stream = None
            assert_old_cursor_canceled(second_cursor, compact_revision)

            # Rebuild the whole projection from the surviving quorum whether
            # the old stream drained its backlog or was canceled by compaction.
            recovery_revision, cache = take_snapshot()
            self.assertGreaterEqual(recovery_revision, compact_revision)
            self.assertEqual(
                set(cache),
                {seed_key}
                | {
                    prefix + f"slow-burst-{index:04d}".encode()
                    for index in range(first_count)
                }
                | {
                    prefix + f"compaction-burst-{index:04d}".encode()
                    for index in range(second_count)
                },
            )

            recovery_cursor = recovery_revision + 1
            active_stream = open_watch(recovery_cursor)
            final_value = f"after-slow-consumer-rebuild-{suffix}".encode()
            final_write = majority_store.transact(
                [], [AuthorityStorePut(final_key, final_value)]
            )
            self.assertTrue(final_write.succeeded)
            final_mode, final_received, final_frames = consume_backlog(
                active_stream,
                1,
                cache,
                cancel_is_allowed=False,
            )
            self.assertEqual(final_mode, "drained")
            self.assertEqual(final_received, 1)
            self.assertEqual(all_event_revisions[-1], final_write.revision)

            final_revision, final_snapshot = take_snapshot()
            self.assertGreaterEqual(final_revision, final_write.revision)
            self.assertEqual(cache, final_snapshot)

            observations = {
                "initial_snapshot_revision": initial_revision,
                "first_watch_cursor": first_cursor,
                "slow_consumer_pause_seconds": slow_pause_seconds,
                "slow_consumer_response_delay_seconds": slow_response_delay_seconds,
                "slow_burst_event_count": first_count,
                "slow_burst_mode": slow_mode,
                "slow_burst_received": slow_received,
                "slow_burst_response_count": slow_frames,
                "slow_burst_snapshot_revision": slow_snapshot_revision,
                "compaction_watch_cursor": second_cursor,
                "compaction_burst_event_count": second_count,
                "compaction_revision": compact_revision,
                "compaction_output": compact_output,
                "compaction_race_mode": race_mode,
                "compaction_race_events_before_cancel_or_drain": race_received,
                "compaction_race_response_count": race_frames,
                "recovery_snapshot_revision": recovery_revision,
                "recovery_cursor": recovery_cursor,
                "final_write_revision": final_write.revision,
                "final_watch_response_count": final_frames,
                "final_snapshot_revision": final_revision,
                "unique_applied_event_count": len(applied_identities),
                "duplicate_applied_events": 0,
                "max_events_per_response": max_events_per_response,
                "progress_revisions_seen": progress_revisions,
                "final_cache_matches_linearizable_range": True,
            }
            print(
                "WATCH_SLOW_CONSUMER_COMPACTION_OBSERVATION "
                + json.dumps(observations, sort_keys=True)
            )
        finally:
            for thread in writer_threads:
                thread.join(timeout=20.0)
            if active_stream is not None:
                try:
                    active_stream.close()
                except Exception:
                    pass
            for stream in streams:
                try:
                    stream.close()
                except Exception:
                    pass
            try:
                remaining = majority_store.linearizable_range(
                    prefix, range_end=range_end
                )
                cleanup_operations = [
                    AuthorityStoreDelete(entry.key) for entry in remaining.entries
                ]
                if cleanup_operations:
                    for offset in range(0, len(cleanup_operations), 100):
                        majority_store.transact(
                            [], cleanup_operations[offset:offset + 100]
                        )
            except Exception:
                pass
            watch_driver.close()
            majority_driver.close()


    def test_idle_watch_progress_keeps_stream_alive_and_access_path_loss_is_bounded(self):
        suffix = uuid4().hex
        prefix = f"/cnc-knowledge-it/watch-idle-liveness/{suffix}/state/".encode()
        range_end = prefix[:-1] + b"0"
        seed_key = prefix + b"seed"
        access_network = f"{self.project}-watch-liveness-{suffix[:12]}"
        purpose = "watch-idle-liveness"
        container_id = self._container_id("etcd1")
        read_timeout_seconds = 4.0

        network_created = False
        network_attached = False
        stream = None
        majority_driver = Etcd3gwV3Client(self.endpoints[1:], timeout=3.0)
        majority_store = EtcdV3CoordinatorAuthorityStore(majority_driver)
        watch_driver = None
        watch_store = None
        progress_revisions: list[int] = []
        progress_intervals: list[float] = []
        access_loss_elapsed = None
        disconnect_kind = None

        try:
            self._create_access_network(access_network, purpose=purpose)
            network_created = True
            self._run(["docker", "network", "connect", access_network, container_id])
            network_attached = True

            memberships = self._network_memberships(container_id)
            self.assertIn(self.cluster_network, memberships)
            self.assertIn(access_network, memberships)
            access_ip = memberships[access_network].get("IPAddress")
            self.assertTrue(access_ip, "dedicated Watch access network has no container IPv4")
            access_endpoint = f"http://{access_ip}:2379"

            access_details = self._network_details(access_network)
            self.assertEqual(
                set((access_details.get("Containers") or {}).keys()),
                {container_id},
            )

            seed = majority_store.transact(
                [], [AuthorityStorePut(seed_key, f"seed-{suffix}".encode())]
            )
            self.assertTrue(seed.succeeded)
            baseline = majority_store.linearizable_range(
                prefix, range_end=range_end
            )
            self.assertEqual(
                {entry.key: entry.value for entry in baseline.entries},
                {seed_key: f"seed-{suffix}".encode()},
            )

            # Keep the node in the Raft cluster but route the Watch HTTP stream
            # through a dedicated host-reachable bridge that can be detached.
            watch_driver = Etcd3gwV3Client(
                [access_endpoint],
                timeout=3.0,
                watch_read_timeout=read_timeout_seconds,
            )
            watch_store = EtcdV3CoordinatorAuthorityStore(watch_driver)
            local = watch_store.linearizable_range(prefix, range_end=range_end)
            self.assertGreaterEqual(local.revision, baseline.revision)

            stream = watch_store.watch(
                prefix,
                start_revision=baseline.revision + 1,
                range_end=range_end,
                progress_notify=True,
                prev_kv=True,
            )
            opened = self._next_result(stream, timeout=8.0)
            self.assertEqual(opened[0], "response", opened[1])
            self.assertTrue(opened[1].created)
            self.assertFalse(opened[1].canceled)
            self.assertEqual(opened[1].events, ())

            # There are no mutations in the watched prefix during this idle
            # window. Periodic Progress frames are control-plane liveness, not KV events.
            previous_progress_at = time.monotonic()
            for index in range(2):
                outcome = self._next_result(stream, timeout=read_timeout_seconds + 2.0)
                self.assertEqual(outcome[0], "response", outcome[1])
                progress = outcome[1]
                observed_at = time.monotonic()
                self.assertTrue(progress.is_progress)
                self.assertEqual(progress.events, ())
                self.assertFalse(progress.canceled)
                self.assertGreaterEqual(progress.header_revision, baseline.revision)
                progress_revisions.append(progress.header_revision)
                progress_intervals.append(observed_at - previous_progress_at)
                previous_progress_at = observed_at

            after_idle = majority_store.linearizable_range(
                prefix, range_end=range_end
            )
            self.assertEqual(after_idle.revision, baseline.revision)
            self.assertEqual(
                {entry.key: entry.value for entry in after_idle.entries},
                {seed_key: f"seed-{suffix}".encode()},
            )

            # The member remains running and attached to the Raft network.
            # Only its dedicated client-access network is removed: from the
            # stream consumer's perspective the established socket may remain
            # silent until the configured HTTP read-inactivity timeout fires.
            before_inspect = self._run([
                "docker", "inspect", "--format",
                '{{.State.Status}}', container_id,
            ]).stdout.strip()
            self.assertEqual(before_inspect, "running")
            self._run(["docker", "network", "disconnect", access_network, container_id])
            network_attached = False
            self.assertNotIn(
                access_network, self._network_memberships(container_id)
            )
            self.assertIn(
                self.cluster_network, self._network_memberships(container_id)
            )

            result_queue: queue.Queue = queue.Queue(maxsize=1)
            disconnect_started = time.monotonic()
            drained_progress: list[int] = []

            def wait_for_stream_failure():
                try:
                    while True:
                        response = next(stream)
                        if response.is_progress:
                            drained_progress.append(response.header_revision)
                            continue
                        result_queue.put(("response", response))
                        return
                except BaseException as exc:
                    result_queue.put(("exception", exc))

            worker = threading.Thread(target=wait_for_stream_failure, daemon=True)
            worker.start()
            try:
                termination = result_queue.get(timeout=read_timeout_seconds + 6.0)
            except queue.Empty:
                stream.close()
                worker.join(timeout=1.0)
                self.fail(
                    "Watch remained blocked beyond the configured read inactivity "
                    f"timeout ({read_timeout_seconds}s)"
                )
            worker.join(timeout=1.0)
            access_loss_elapsed = time.monotonic() - disconnect_started
            self.assertEqual(
                termination[0],
                "exception",
                f"unexpected Watch outcome after access path loss: {termination[1]!r}",
            )
            self.assertIsInstance(
                termination[1],
                AuthorityStoreUnavailableError,
                f"unexpected liveness failure classification: {type(termination[1]).__name__}",
            )
            disconnect_kind = type(termination[1]).__name__

            # Confirm etcd1 itself remained alive and healthy in the cluster;
            # only the dedicated client path was removed.
            final_status = self._run([
                "docker", "inspect", "--format",
                '{{.State.Status}}', container_id,
            ]).stdout.strip()
            self.assertEqual(final_status, "running")
            self._wait_for_quorum()

            print(
                "WATCH_IDLE_LIVENESS_OBSERVATION "
                + json.dumps(
                    {
                        "baseline_revision": baseline.revision,
                        "watched_prefix_event_count_during_idle": 0,
                        "progress_revisions": progress_revisions,
                        "progress_intervals_seconds": progress_intervals,
                        "progress_frames_drained_after_access_loss": drained_progress,
                        "watch_read_timeout_seconds": read_timeout_seconds,
                        "access_path_loss_detection_seconds": access_loss_elapsed,
                        "disconnect_error": disconnect_kind,
                        "etcd1_container_remained_running": True,
                        "etcd1_remained_on_raft_network": True,
                        "only_client_access_network_removed": True,
                        "final_quorum_recovered": True,
                    },
                    sort_keys=True,
                )
            )
        finally:
            if stream is not None:
                try:
                    stream.close()
                except Exception:
                    pass
            if watch_driver is not None:
                watch_driver.close()
            if network_created:
                try:
                    memberships = self._network_memberships(container_id)
                    if access_network in memberships:
                        self._run([
                            "docker", "network", "disconnect",
                            access_network, container_id,
                        ])
                    self._remove_access_network(access_network, purpose=purpose)
                except Exception:
                    pass
            try:
                remaining = majority_store.linearizable_range(
                    prefix, range_end=range_end
                )
                if remaining.entries:
                    majority_store.transact(
                        [],
                        [
                            AuthorityStoreDelete(entry.key)
                            for entry in remaining.entries
                        ],
                    )
            except Exception:
                pass
            majority_driver.close()


if __name__ == "__main__":
    unittest.main()
