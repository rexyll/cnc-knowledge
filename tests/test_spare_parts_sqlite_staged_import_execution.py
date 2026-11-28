from __future__ import annotations

import json
import unittest

from scripts.spare_parts_provider_authority_store import (
    AuthorityStoreCompare,
    AuthorityStoreOutcomeUnknownError,
    AuthorityStorePut,
    EtcdV3CoordinatorAuthorityStore,
    InMemoryEtcdV3Client,
)
from scripts.spare_parts_provider_unified_admission_store import (
    ProviderAdmissionIdempotencyConflictError,
    ProviderAdmissionRequestFinalizedError,
    ProviderTaskContext,
    StoreBackedProviderAdmissionCoordinator,
)
from scripts.spare_parts_provider_unified_coordinator_authority import (
    StoreBackedCoordinatorAuthority,
)
from scripts.spare_parts_sqlite_staged_import_protocol import (
    UNKNOWN_COMMITTED,
    UNKNOWN_QUARANTINE,
    UNKNOWN_RETRY,
    build_staged_import_plan,
    classify_batch_unknown,
    classify_publish_unknown,
)
from tests.test_spare_parts_sqlite_staged_import_protocol import multi_request_candidate


PREFIX = b"/cnc/migration/isolated/round79-sim/"


def canonical(value) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


class StagedImportInMemoryExecutionTests(unittest.TestCase):
    """Exercise the planned Txn chain through the real etcd-store adapter.

    The backend is a process-local fake. These tests validate compare/Txn wiring,
    crash/re-entry behavior and outcome classification, not etcd consensus,
    durability, transport timing or production deployment behavior.
    """

    def setUp(self):
        self.candidate = multi_request_candidate(5)
        self.plan = build_staged_import_plan(
            self.candidate,
            PREFIX,
            max_txn_ops=8,
            max_txn_bytes=1_000_000,
            wire_safety_margin_bytes=0,
        )
        self.client = InMemoryEtcdV3Client()
        self.store = EtcdV3CoordinatorAuthorityStore(self.client)
        self.checkpoint_key = self.plan["target"]["checkpoint_key"].encode("ascii")
        self.state_key = self.plan["target"]["scheduler_state_key"].encode("ascii")
        self.leader_key = self.plan["target"]["leader_key_compare_only"].encode("ascii")
        self.request_values = {
            PREFIX + item["key"].encode("ascii"): canonical(item["record"])
            for item in self.candidate["terminal_request_indexes"]
        }

    def _initialize(self, store=None):
        store = store or self.store
        checkpoint = self.plan["transactions"]["initialize_checkpoint"]["checkpoint_value"]
        result = store.transact(
            [
                AuthorityStoreCompare(self.checkpoint_key, "VERSION", "EQUAL", 0),
                AuthorityStoreCompare(self.state_key, "VERSION", "EQUAL", 0),
                AuthorityStoreCompare(self.leader_key, "VERSION", "EQUAL", 0),
            ],
            [AuthorityStorePut(self.checkpoint_key, canonical(checkpoint))],
        )
        self.assertTrue(result.succeeded)
        return canonical(checkpoint)

    def _batch_values(self, batch):
        return {
            key.encode("ascii"): self.request_values[key.encode("ascii")]
            for key in batch["request_keys"]
        }

    def _execute_batch(self, store, batch_index, previous_checkpoint_value):
        batch = self.plan["transactions"]["request_batches"][batch_index]
        values = self._batch_values(batch)
        compares = [
            *(
                AuthorityStoreCompare(key, "VERSION", "EQUAL", 0)
                for key in values
            ),
            AuthorityStoreCompare(
                self.checkpoint_key, "VALUE", "EQUAL", previous_checkpoint_value
            ),
            AuthorityStoreCompare(self.state_key, "VERSION", "EQUAL", 0),
            AuthorityStoreCompare(self.leader_key, "VERSION", "EQUAL", 0),
        ]
        puts = [
            *(AuthorityStorePut(key, value) for key, value in values.items()),
            AuthorityStorePut(
                self.checkpoint_key, canonical(batch["checkpoint_after"])
            ),
        ]
        return store.transact(compares, puts)

    def _observe_batch(self, store, batch):
        observed_values = {}
        for key in self._batch_values(batch):
            entry, _ = store.linearizable_get(key)
            observed_values[key] = None if entry is None else entry.value
        checkpoint, _ = store.linearizable_get(self.checkpoint_key)
        state, _ = store.linearizable_get(self.state_key)
        leader, _ = store.linearizable_get(self.leader_key)
        return {
            "checkpoint": None if checkpoint is None else checkpoint.value,
            "request_values": observed_values,
            "state_exists": state is not None,
            "leader_exists": leader is not None,
        }

    def _classify_batch(self, store, batch_index, previous_checkpoint_value):
        batch = self.plan["transactions"]["request_batches"][batch_index]
        observed = self._observe_batch(store, batch)
        expected_values = self._batch_values(batch)
        successors = [
            canonical(item["checkpoint_after"])
            for item in self.plan["transactions"]["request_batches"][batch_index:]
        ]
        return classify_batch_unknown(
            plan_sha256=self.plan["plan_sha256"],
            expected_previous_checkpoint=previous_checkpoint_value,
            observed_checkpoint=observed["checkpoint"],
            expected_completed_request_count=batch["checkpoint_after"][
                "completed_request_count"
            ],
            expected_successor_checkpoints=successors,
            observed_request_values=observed["request_values"],
            expected_request_values=expected_values,
            observed_state_exists=observed["state_exists"],
            observed_leader_exists=observed["leader_exists"],
        )

    def _publish(self, store):
        batches = self.plan["transactions"]["request_batches"]
        final_checkpoint = (
            batches[-1]["checkpoint_after"]
            if batches
            else self.plan["transactions"]["initialize_checkpoint"]["checkpoint_value"]
        )
        final_checkpoint_value = canonical(final_checkpoint)
        state_value = canonical(self.candidate["state_template"])
        return store.transact(
            [
                AuthorityStoreCompare(
                    self.checkpoint_key, "VALUE", "EQUAL", final_checkpoint_value
                ),
                AuthorityStoreCompare(self.state_key, "VERSION", "EQUAL", 0),
                AuthorityStoreCompare(self.leader_key, "VERSION", "EQUAL", 0),
            ],
            [AuthorityStorePut(self.state_key, state_value)],
        )

    def _finish_all_batches(self, store):
        checkpoint_entry, _ = store.linearizable_get(self.checkpoint_key)
        if checkpoint_entry is None:
            raise AssertionError("checkpoint was not initialized")
        checkpoint_value = checkpoint_entry.value
        checkpoint = json.loads(checkpoint_value.decode("utf-8"))
        next_index = checkpoint["next_batch_index"]
        for batch_index in range(next_index, len(self.plan["transactions"]["request_batches"])):
            result = self._execute_batch(store, batch_index, checkpoint_value)
            self.assertTrue(result.succeeded)
            checkpoint_value = canonical(
                self.plan["transactions"]["request_batches"][batch_index]["checkpoint_after"]
            )
        return checkpoint_value

    def test_restart_resumes_from_checkpoint_and_publishes_state_only_at_the_end(self):
        initial_checkpoint = self._initialize()
        batches = self.plan["transactions"]["request_batches"]
        self.assertEqual(len(batches), 3)

        first = self._execute_batch(self.store, 0, initial_checkpoint)
        self.assertTrue(first.succeeded)

        # Simulate process loss after batch 0 and reconstruction with a new adapter.
        restarted_store = EtcdV3CoordinatorAuthorityStore(self.client)
        checkpoint_entry, _ = restarted_store.linearizable_get(self.checkpoint_key)
        self.assertIsNotNone(checkpoint_entry)
        checkpoint = json.loads(checkpoint_entry.value.decode("utf-8"))
        self.assertEqual(checkpoint["next_batch_index"], 1)
        state, _ = restarted_store.linearizable_get(self.state_key)
        self.assertIsNone(state)

        self._finish_all_batches(restarted_store)
        for key, expected in self.request_values.items():
            entry, _ = restarted_store.linearizable_get(key)
            self.assertIsNotNone(entry)
            self.assertEqual(entry.value, expected)
            self.assertEqual(entry.version, 1)

        state, _ = restarted_store.linearizable_get(self.state_key)
        leader, _ = restarted_store.linearizable_get(self.leader_key)
        self.assertIsNone(state)
        self.assertIsNone(leader)

        published = self._publish(restarted_store)
        self.assertTrue(published.succeeded)
        state, _ = restarted_store.linearizable_get(self.state_key)
        self.assertIsNotNone(state)
        self.assertEqual(state.value, canonical(self.candidate["state_template"]))
        leader, _ = restarted_store.linearizable_get(self.leader_key)
        self.assertIsNone(leader)

        # Initialization + three batches + final publication: one revision each.
        self.assertEqual(self.client._revision, 5)

    def test_lost_batch_response_after_commit_is_classified_committed(self):
        previous = self._initialize()
        batch = self.plan["transactions"]["request_batches"][0]
        self.client.fail_next_txn_after_commit = True

        with self.assertRaises(AuthorityStoreOutcomeUnknownError):
            self._execute_batch(self.store, 0, previous)

        self.assertEqual(
            self._classify_batch(self.store, 0, previous), UNKNOWN_COMMITTED
        )
        observed = self._observe_batch(self.store, batch)
        self.assertEqual(
            observed["checkpoint"], canonical(batch["checkpoint_after"])
        )
        for key in self._batch_values(batch):
            entry, _ = self.store.linearizable_get(key)
            self.assertEqual(entry.version, 1)

    def test_lost_batch_response_before_commit_allows_retry_of_identical_txn(self):
        previous = self._initialize()

        def disconnect_before_commit():
            self.client.before_txn = None
            raise TimeoutError("synthetic request did not reach the transaction commit")

        self.client.before_txn = disconnect_before_commit
        with self.assertRaises(AuthorityStoreOutcomeUnknownError):
            self._execute_batch(self.store, 0, previous)

        self.assertEqual(
            self._classify_batch(self.store, 0, previous), UNKNOWN_RETRY
        )
        result = self._execute_batch(self.store, 0, previous)
        self.assertTrue(result.succeeded)
        self.assertEqual(
            self._classify_batch(self.store, 0, previous), UNKNOWN_COMMITTED
        )

    def test_competing_writer_prevents_partial_batch_and_forces_quarantine(self):
        previous = self._initialize()
        batch = self.plan["transactions"]["request_batches"][0]
        request_key = batch["request_keys"][0].encode("ascii")

        def concurrent_writer():
            # A distinct writer wins one request key after planning but before
            # the migration Txn's compare is evaluated.
            self.client.before_txn = None
            self.client.txn(
                compare=[],
                success=[{
                    "request_put": {"key": request_key, "value": b"foreign-writer"}
                }],
                failure=[],
            )

        self.client.before_txn = concurrent_writer
        result = self._execute_batch(self.store, 0, previous)
        self.assertFalse(result.succeeded)

        checkpoint, _ = self.store.linearizable_get(self.checkpoint_key)
        self.assertEqual(checkpoint.value, previous)
        self.assertEqual(
            self._classify_batch(self.store, 0, previous), UNKNOWN_QUARANTINE
        )
        for key in self._batch_values(batch):
            entry, _ = self.store.linearizable_get(key)
            if key == request_key:
                self.assertEqual(entry.value, b"foreign-writer")
            else:
                self.assertIsNone(entry)

        state, _ = self.store.linearizable_get(self.state_key)
        leader, _ = self.store.linearizable_get(self.leader_key)
        self.assertIsNone(state)
        self.assertIsNone(leader)

    def test_published_candidate_is_readable_by_unified_runtime_and_preserves_leader_epoch_floor(self):
        self._initialize()
        self._finish_all_batches(self.store)
        self.assertTrue(self._publish(self.store).succeeded)

        state_template = self.candidate["state_template"]
        scheduler = StoreBackedProviderAdmissionCoordinator(
            self.store,
            global_limits=state_template["global_limits"],
            tenant_limits=state_template["tenant_limits"],
            max_waiters=state_template["max_waiters"],
            aging_interval_seconds=state_template["aging_interval_seconds"],
            clock_fn=lambda: 1000.0,
            namespace_prefix=PREFIX,
        )
        authority = StoreBackedCoordinatorAuthority(
            scheduler, clock_fn=lambda: 1000.0
        )

        # The legacy leader identity and TTL key are not restored. Only an
        # expired sentinel record remains so the runtime's normal claim path
        # cannot reset the epoch to one after import.
        before = authority.leader_snapshot()
        self.assertEqual(before["leader_id"], "migration-epoch-floor")
        self.assertEqual(before["epoch"], 8)
        self.assertFalse(before["active"])
        self.assertIsNone(self.store.linearizable_get(self.leader_key)[0])
        self.assertEqual(self.client._leases, {})

        scope_name = "tenants/tenant-A/cnc/ch17/spares/pkg-001"
        scope = authority.snapshot(scope_name)
        self.assertEqual(scope["high_water_token"], 9)
        self.assertEqual(scope["latest_operation_sequence"], 3)
        self.assertEqual(scope["lease_state"], "IDLE")

        operation_key = authority._op_key(scope_name, "publish-1")
        state_entry, _ = self.store.linearizable_get(self.state_key)
        imported_state = scheduler._decode(state_entry)
        operation = imported_state["coordinator"]["operations"][operation_key]
        self.assertEqual(operation["state"], "COMMITTED")
        self.assertEqual(operation["manifest_sha256"], "b" * 64)

        request_id = self.candidate["terminal_request_indexes"][0]["record"]["request_id"]
        identity = {
            "task": ProviderTaskContext(task_id="task-A", tenant_id="tenant-A"),
            "domain": "read",
            "lease_ttl_seconds": 30,
            "timeout_seconds": 0,
            "check_task": lambda _: None,
            "request_id": request_id,
        }
        lease_count_before_replay = len(self.client._leases)
        with self.assertRaises(ProviderAdmissionRequestFinalizedError):
            scheduler.acquire(owner_id="owner-A", **identity)
        with self.assertRaises(ProviderAdmissionIdempotencyConflictError):
            scheduler.acquire(owner_id="different-owner", **identity)
        self.assertEqual(len(self.client._leases), lease_count_before_replay)

        # The standard runtime claim path uses the imported historical floor.
        claimed = authority.claim_leadership("new-leader-after-import", ttl_seconds=30)
        self.assertEqual(claimed.epoch, 9)
        after = authority.leader_snapshot()
        self.assertEqual(after["leader_id"], "new-leader-after-import")
        self.assertEqual(after["epoch"], 9)
        self.assertTrue(after["active"])

    def test_lost_publish_response_is_resolved_by_exact_state_and_checkpoint(self):
        self._initialize()
        self._finish_all_batches(self.store)
        final_checkpoint = canonical(
            self.plan["transactions"]["request_batches"][-1]["checkpoint_after"]
        )
        expected_state = canonical(self.candidate["state_template"])
        self.client.fail_next_txn_after_commit = True

        with self.assertRaises(AuthorityStoreOutcomeUnknownError):
            self._publish(self.store)

        checkpoint, _ = self.store.linearizable_get(self.checkpoint_key)
        state, _ = self.store.linearizable_get(self.state_key)
        leader, _ = self.store.linearizable_get(self.leader_key)
        self.assertEqual(
            classify_publish_unknown(
                observed_checkpoint=checkpoint.value,
                expected_final_checkpoint=final_checkpoint,
                observed_state=state.value,
                expected_state=expected_state,
                observed_leader_exists=leader is not None,
            ),
            UNKNOWN_COMMITTED,
        )


if __name__ == "__main__":
    unittest.main()
