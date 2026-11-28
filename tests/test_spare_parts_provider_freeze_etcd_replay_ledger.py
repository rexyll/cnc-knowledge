import json
import threading
import unittest

from scripts.spare_parts_provider_authority_store import (
    AuthorityStorePut,
    EtcdV3CoordinatorAuthorityStore,
    InMemoryEtcdV3Client,
)
from scripts.spare_parts_sqlite_provider_fencing_reconciliation import (
    ProviderFencingReconciliationError,
)
from scripts.spare_parts_provider_freeze_etcd_replay_ledger import (
    EtcdProviderFreezeEvidenceReplayLedger,
    ProviderFreezeAuthorityChangedError,
)


NAMESPACE = b"/cnc/migration/isolated/round84-replay/"


class EtcdProviderFreezeReplayLedgerTests(unittest.TestCase):
    def setUp(self):
        self.clock = [1000.0]
        self.client = InMemoryEtcdV3Client(clock_fn=lambda: self.clock[0])
        self.store = EtcdV3CoordinatorAuthorityStore(self.client)
        self.ledger = EtcdProviderFreezeEvidenceReplayLedger(
            self.store, namespace_prefix=NAMESPACE
        )
        self.scopes = {
            "inventory/parts": {
                "provider_generation": "generation-7",
                "high_water_token": 10,
                "latest_operation_sequence": 4,
            },
            "inventory/tools": {
                "provider_generation": "generation-3",
                "high_water_token": 4,
                "latest_operation_sequence": 1,
            },
        }
        self.lease = self.store.lease_grant(60)
        self.leader = {
            "leader_id": "coordinator-leader-1",
            "epoch": 12,
            "expires_at": 1060.0,
            "backend_lease_id": self.lease.lease_id,
        }
        self.state_key = NAMESPACE + b"scheduler/state"
        self.leader_key = NAMESPACE + b"coordinator/leader"
        self.store.transact(
            [],
            (
                AuthorityStorePut(
                    self.state_key,
                    json.dumps(
                        {"schema_version": 2, "coordinator": {
                            "leader": self.leader, "scopes": self.scopes, "operations": {}
                        }},
                        sort_keys=True, separators=(",", ":"),
                    ).encode("utf-8"),
                ),
                AuthorityStorePut(
                    self.leader_key,
                    json.dumps(
                        self.leader, sort_keys=True, separators=(",", ":")
                    ).encode("utf-8"),
                    self.lease.lease_id,
                ),
            ),
        )
        self.snapshot = {
            "format": "ch17-coordinator-leader-snapshot-v1",
            "observed_at_unix": 999.0,
            "leader_id": self.leader["leader_id"],
            "leader_epoch": self.leader["epoch"],
            "lease_id": self.lease.lease_id,
            "lease_expires_at_unix": self.leader["expires_at"],
            "scopes": self.scopes,
        }
        self.record = {
            "provider_id": "provider-prod-a",
            "evidence_id": "b7e6e47b-e43e-4e0d-90a7-6df2a8a2a001",
            "challenge_nonce_sha256": "a" * 64,
            "claim_sha256": "b" * 64,
            "freeze_id": "freeze-round-84",
            "freeze_generation": 8,
            "leader_id": self.leader["leader_id"],
            "leader_epoch": self.leader["epoch"],
            "lease_id": self.lease.lease_id,
            "consumed_at_unix": 1000.0,
        }

    def consume(self, record=None, snapshot=None):
        return self.ledger.consume_once(
            self.record if record is None else record,
            authority_snapshot=self.snapshot if snapshot is None else snapshot,
        )

    def test_consumes_all_uniqueness_keys_in_one_persistent_namespace(self):
        result = self.consume()
        self.assertEqual(result["status"], "CONSUMED")
        keys = self.ledger._keys(self.record)
        entries = [self.store.linearizable_get(key)[0] for key in keys]
        self.assertEqual(len(entries), 4)
        self.assertTrue(all(entry is not None and entry.lease_id == 0 for entry in entries))
        self.assertTrue(all(entry.value == entries[0].value for entry in entries))
        self.assertTrue(all(key.startswith(NAMESPACE) for key in keys))

    def test_rejects_replay_of_same_evidence_nonce_generation_and_freeze_id(self):
        self.consume()
        with self.assertRaises(ProviderFencingReconciliationError):
            self.consume()

    def test_concurrent_consumers_have_exactly_one_success(self):
        barrier = threading.Barrier(2)
        outcomes = []
        failures = []

        def run():
            try:
                barrier.wait()
                outcomes.append(self.consume()["status"])
            except ProviderFencingReconciliationError as exc:
                failures.append(type(exc).__name__)

        threads = [threading.Thread(target=run) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=5)
        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertEqual(len(outcomes), 1)
        self.assertEqual(len(failures), 1)

    def test_unknown_result_after_commit_is_confirmed_by_exact_readback(self):
        self.client.fail_next_txn_after_commit = True
        result = self.consume()
        self.assertEqual(result["status"], "CONFIRMED_AFTER_UNKNOWN")

    def test_unknown_result_before_commit_retries_exact_txn(self):
        called = [False]

        def fail_once():
            if not called[0]:
                called[0] = True
                self.client.before_txn = None
                raise TimeoutError("synthetic request lost before txn execution")

        self.client.before_txn = fail_once
        result = self.consume()
        self.assertEqual(result["status"], "RETRIED_AFTER_NOT_COMMITTED")
        self.assertEqual(self.consume_record_count(), 4)

    def consume_record_count(self):
        return len([
            key for key in self.client._kvs
            if key.startswith(self.ledger.root)
        ])

    def test_partial_replay_state_is_quarantined(self):
        key = self.ledger._keys(self.record)[0]
        self.store.transact([], (AuthorityStorePut(key, b"partial"),))
        with self.assertRaisesRegex(
            ProviderFencingReconciliationError, "partial or conflicting"
        ):
            self.consume()

    def test_rejects_if_coordinator_state_changes_after_snapshot_read(self):
        fired = [False]

        def mutate_after_ledger_snapshot():
            if fired[0]:
                return
            fired[0] = True
            self.client.before_txn = None
            state, _ = self.store.linearizable_get(self.state_key)
            changed = json.loads(state.value.decode("utf-8"))
            changed["unrelated_revision_marker"] = "concurrent-update"
            value = json.dumps(changed, sort_keys=True, separators=(",", ":")).encode()
            self.store.transact(
                [],
                (AuthorityStorePut(self.state_key, value),),
            )

        self.client.before_txn = mutate_after_ledger_snapshot
        with self.assertRaises(ProviderFreezeAuthorityChangedError):
            self.consume()
        self.assertEqual(self.consume_record_count(), 0)

    def test_rejects_snapshot_scope_drift_before_txn(self):
        changed = dict(self.snapshot)
        changed["scopes"] = dict(self.scopes)
        changed["scopes"]["inventory/parts"] = dict(
            self.scopes["inventory/parts"], high_water_token=11
        )
        with self.assertRaisesRegex(ProviderFreezeAuthorityChangedError, "scope floors changed"):
            self.consume(snapshot=changed)

    def test_refuses_production_or_non_isolated_namespace(self):
        for namespace in (
            b"/cnc/admission/unified/v2/",
            b"/cnc/migration/isolated/",
            b"/cnc/migration/isolated/a/b/",
        ):
            with self.subTest(namespace=namespace):
                with self.assertRaises(ProviderFencingReconciliationError):
                    EtcdProviderFreezeEvidenceReplayLedger(
                        self.store, namespace_prefix=namespace
                    )

    def test_replay_keys_are_permanent_and_not_attached_to_leader_lease(self):
        self.consume()
        for key in self.ledger._keys(self.record):
            entry, _ = self.store.linearizable_get(key)
            self.assertIsNotNone(entry)
            self.assertEqual(entry.lease_id, 0)


if __name__ == "__main__":
    unittest.main()
