from __future__ import annotations

import json
import os
import queue
import subprocess
import threading
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
class Etcd3gwLiveWatchCompactionTests(unittest.TestCase):
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

    def test_compacted_watch_is_canceled_then_snapshot_plus_one_resumes(self):
        suffix = uuid4().hex
        key = f"/cnc-knowledge-it/watch-compaction/{suffix}/leader".encode()
        first_value = f"leader-before-compaction-{suffix}".encode()
        second_value = f"leader-at-compaction-{suffix}".encode()
        resumed_value = f"leader-after-snapshot-{suffix}".encode()

        driver = Etcd3gwV3Client(self.endpoints, timeout=3.0)
        store = EtcdV3CoordinatorAuthorityStore(driver)
        old_stream = None
        resumed_stream = None
        compact_container = self._container_id("etcd1")
        compacted_revision = None

        try:
            initial = store.transact([], [AuthorityStorePut(key, first_value)])
            self.assertTrue(initial.succeeded)
            initial_entry, initial_read_revision = store.linearizable_get(key)
            self.assertIsNotNone(initial_entry)
            old_revision = initial_entry.mod_revision
            self.assertEqual(old_revision, initial.revision)
            self.assertGreaterEqual(initial_read_revision, old_revision)

            # Advance the global revision beyond the cursor that will be compacted.
            advanced = store.transact([], [AuthorityStorePut(key, second_value)])
            self.assertTrue(advanced.succeeded)
            latest_entry, latest_read_revision = store.linearizable_get(key)
            self.assertIsNotNone(latest_entry)
            self.assertEqual(latest_entry.value, second_value)
            self.assertEqual(latest_entry.mod_revision, advanced.revision)
            self.assertGreater(advanced.revision, old_revision)
            self.assertGreaterEqual(latest_read_revision, advanced.revision)

            # The container identity is verified by Compose project/service labels.
            # Compaction is scoped to this disposable three-member test cluster.
            compact = self._run([
                "docker", "exec", compact_container,
                "/usr/local/bin/etcdctl",
                "--endpoints=http://127.0.0.1:2379",
                "--dial-timeout=2s",
                "--command-timeout=10s",
                "compact", str(old_revision),
            ], timeout=15.0)
            self.assertEqual(compact.returncode, 0, compact.stderr)
            compacted_revision = old_revision

            old_stream = store.watch(
                key,
                start_revision=old_revision,
                progress_notify=False,
                prev_kv=True,
            )
            canceled_result = self._next_result(old_stream)
            self.assertEqual(canceled_result[0], "response", canceled_result[1])
            canceled = canceled_result[1]
            self.assertTrue(canceled.canceled)
            self.assertFalse(canceled.created)
            self.assertEqual(canceled.compact_revision, compacted_revision)
            self.assertIn("compact", canceled.cancel_reason.lower())
            self.assertEqual(canceled.events, ())
            self.assertIsNone(canceled.resume_revision)

            ended = self._next_result(old_stream)
            self.assertEqual(ended[0], "exception", ended[1])
            self.assertIsInstance(ended[1], StopIteration)

            # A canceled cursor is never resumed. Reconcile from a linearizable snapshot.
            snapshot, snapshot_revision = store.linearizable_get(key)
            self.assertIsNotNone(snapshot)
            self.assertEqual(snapshot.value, second_value)
            self.assertEqual(snapshot.mod_revision, advanced.revision)
            self.assertGreaterEqual(snapshot_revision, compacted_revision)

            resumed_stream = store.watch(
                key,
                start_revision=snapshot_revision + 1,
                progress_notify=False,
                prev_kv=True,
            )
            created_result = self._next_result(resumed_stream)
            self.assertEqual(created_result[0], "response", created_result[1])
            self.assertTrue(created_result[1].created)

            resumed = store.transact([], [AuthorityStorePut(key, resumed_value)])
            self.assertTrue(resumed.succeeded)
            event_result = self._next_result(resumed_stream)
            self.assertEqual(event_result[0], "response", event_result[1])
            response = event_result[1]
            self.assertFalse(response.canceled)
            self.assertEqual(len(response.events), 1)
            event = response.events[0]
            self.assertEqual(event.event_type, "PUT")
            self.assertEqual(event.key, key)
            self.assertEqual(event.entry.value, resumed_value)
            self.assertIsNotNone(event.previous_entry)
            self.assertEqual(event.previous_entry.value, second_value)
            self.assertEqual(event.revision, resumed.revision)
            self.assertGreater(event.revision, snapshot_revision)
            self.assertEqual(response.resume_revision, event.revision + 1)

            print(
                "WATCH_COMPACTION_RECOVERY_OBSERVATION "
                + json.dumps(
                    {
                        "old_watch_start_revision": old_revision,
                        "compacted_revision": compacted_revision,
                        "canceled": True,
                        "cancel_reason": canceled.cancel_reason,
                        "canceled_watch_event_count": len(canceled.events),
                        "canceled_resume_revision": canceled.resume_revision,
                        "snapshot_revision": snapshot_revision,
                        "snapshot_value_matches_latest": snapshot.value == second_value,
                        "snapshot_mod_revision": snapshot.mod_revision,
                        "resume_start_revision": snapshot_revision + 1,
                        "first_resumed_event": event.event_type,
                        "first_resumed_event_revision": event.revision,
                        "previous_value_matches_snapshot": event.previous_entry.value == snapshot.value,
                        "old_events_replayed": False,
                    },
                    sort_keys=True,
                )
            )
        finally:
            if old_stream is not None:
                old_stream.close()
            if resumed_stream is not None:
                resumed_stream.close()
            try:
                current, _ = store.linearizable_get(key)
                if current is not None:
                    store.transact([], [AuthorityStoreDelete(key)])
            except Exception:
                pass
            driver.close()


if __name__ == "__main__":
    unittest.main()
