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
            self.assertEqual(snapshot.value, initial_value)

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
                        "docker", "network", "connect",
                        self.cluster_network, container_id,
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
                progress_notify=False,
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

            # The old HTTP Watch remains pinned to minority etcd1 while the
            # majority has compacted the range. On rejoin, Raft catch-up may
            # deliver some missing KV events before the compact command is
            # applied locally and the old watcher is canceled. Do not assume
            # either zero or all catch-up events arrive before cancellation.
            self._run([
                "docker", "network", "connect",
                self.cluster_network, etcd1_container,
            ])
            cluster_network_disconnected = False
            memberships = self._network_memberships(etcd1_container)
            self.assertIn(self.cluster_network, memberships)
            self._wait_for_quorum(timeout=60.0)

            old_watch_events = []
            canceled = None
            cancel_deadline = time.monotonic() + 30.0
            while time.monotonic() < cancel_deadline:
                outcome, response = self._next_result(
                    old_stream,
                    timeout=min(10.0, max(0.5, cancel_deadline - time.monotonic())),
                )
                self.assertNotEqual(outcome, "timeout", "old Watch did not receive compaction cancellation")
                self.assertEqual(outcome, "response", response)
                if response.canceled:
                    canceled = response
                    break
                self.assertFalse(response.created)
                # The compacted writes deliberately target a key outside
                # this exact-key Watch, so no catch-up KV events should advance
                # the old watcher's min_revision before Compaction is applied.
                self.assertEqual(response.events, ())
            self.assertIsNotNone(canceled, "old Watch was not canceled after compacted log catch-up")
            self.assertFalse(canceled.created)
            self.assertEqual(canceled.compact_revision, compacted_revision)
            self.assertEqual(canceled.events, ())
            self.assertIsNone(canceled.resume_revision)
            self.assertIsInstance(canceled.cancel_reason, str)
            if canceled.cancel_reason:
                self.assertIn("compact", canceled.cancel_reason.lower())
            old_event_revisions = [item["revision"] for item in old_watch_events]
            self.assertEqual(old_event_revisions, sorted(set(old_event_revisions)))

            # The cancellation invalidates the old cursor even if some
            # catch-up events were delivered immediately before the cancel.
            old_stream.close()
            snapshot, snapshot_revision = majority_store.linearizable_get(key)
            self.assertIsNotNone(snapshot)
            self.assertEqual(snapshot.value, partition_values[-1])
            self.assertGreaterEqual(snapshot_revision, compacted_revision)

            # Do not resume from the old Watch's last event/progress revision.
            # Wait until the recovered member can itself serve the quorum
            # snapshot, using read-only probes only.
            local_snapshot = None
            local_revision = 0
            last_local_error: Exception | None = None
            local_deadline = time.monotonic() + 30.0
            while time.monotonic() < local_deadline:
                try:
                    candidate, candidate_revision = watch_store.linearizable_get(key)
                    if (
                        candidate is not None
                        and candidate.value == snapshot.value
                        and candidate_revision >= snapshot_revision
                    ):
                        local_snapshot = candidate
                        local_revision = candidate_revision
                        break
                    last_local_error = RuntimeError(
                        "recovered member has not reached the compaction snapshot"
                    )
                except Exception as exc:
                    last_local_error = exc
                time.sleep(0.5)
            self.assertIsNotNone(
                local_snapshot,
                f"recovered member did not serve the quorum snapshot: {last_local_error}",
            )
            self.assertEqual(local_snapshot.value, initial_value)
            self.assertGreaterEqual(local_revision, snapshot_revision)

            resumed_stream = watch_store.watch(
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
                "old_watch_event_revisions_before_cancel": old_event_revisions,
                "old_watch_received_no_compaction_marker_events": not old_watch_events,
                "old_watch_canceled": canceled.canceled,
                "old_watch_cancel_compact_revision": canceled.compact_revision,
                "old_watch_cancel_event_count": len(canceled.events),
                "old_watch_cancel_resume_revision": canceled.resume_revision,
                "quorum_snapshot_revision": snapshot_revision,
                "recovered_member_linearizable_revision": local_revision,
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
            for stream in (old_stream, resumed_stream):
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
                        "docker", "network", "connect",
                        self.cluster_network, etcd1_container,
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
                    memberships = self._network_memberships(etcd1_container)
                    if access_network in memberships:
                        self._run([
                            "docker", "network", "disconnect",
                            access_network, etcd1_container,
                        ])
                    self._remove_access_network(
                        access_network, purpose="watch-minority-compaction"
                    )


if __name__ == "__main__":
    unittest.main()
