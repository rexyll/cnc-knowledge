from __future__ import annotations

import hashlib
import json
import unittest

from scripts.spare_parts_sqlite_candidate_importer import build_candidate
from scripts.spare_parts_sqlite_migration_inventory import _json_bytes
from scripts.spare_parts_sqlite_staged_import_protocol import (
    UNKNOWN_COMMITTED,
    UNKNOWN_QUARANTINE,
    UNKNOWN_RETRY,
    StagedImportPlanError,
    build_staged_import_plan,
    classify_batch_unknown,
    classify_checkpoint_initialization_unknown,
    classify_publish_unknown,
)
from tests.test_spare_parts_sqlite_candidate_importer import fixture


PREFIX = b"/cnc/migration/isolated/round78-staged/"


def resign(candidate):
    material = dict(candidate)
    material.pop("candidate_digest_sha256", None)
    candidate["candidate_digest_sha256"] = hashlib.sha256(_json_bytes(material)).hexdigest()


def multi_request_candidate(count: int):
    manifest, records, policy = fixture()
    candidate = build_candidate(manifest, records, policy, generated_at=1000.0)
    base = candidate["terminal_request_indexes"][0]["record"]
    indexes = []
    for index in range(count):
        record = dict(base)
        record["request_id"] = f"request-{index:04d}"
        record["lease_id"] = f"legacy-lease-{index:04d}"
        key = "requests/" + hashlib.sha256(record["request_id"].encode()).hexdigest()
        indexes.append({"key": key, "record": record})
    candidate["terminal_request_indexes"] = indexes
    candidate["counts"]["terminal_requests"] = count
    resign(candidate)
    return candidate


class StagedImportProtocolTests(unittest.TestCase):
    def build(self, candidate=None, *, max_ops=8, max_bytes=1_000_000):
        return build_staged_import_plan(
            candidate or multi_request_candidate(5),
            PREFIX,
            max_txn_ops=max_ops,
            max_txn_bytes=max_bytes,
            wire_safety_margin_bytes=0,
        )

    def test_splits_request_indexes_into_atomic_checkpointed_batches(self):
        plan = self.build()
        txns = plan["transactions"]
        batches = txns["request_batches"]
        self.assertEqual(len(batches), 3)
        self.assertEqual([b["request_count"] for b in batches], [2, 2, 1])
        self.assertEqual(txns["total_transaction_count"], 5)
        for batch in batches:
            self.assertTrue(batch["budget"]["fits"])
            self.assertEqual(batch["budget"]["conservative_compare_plus_put_count"], 2 * batch["request_count"] + 4)
            self.assertEqual(batch["checkpoint_after"]["next_batch_index"], batch["batch_index"] + 1)
        self.assertTrue(plan["strategy"]["scheduler_state_is_written_only_in_final_publish_txn"])
        self.assertEqual(plan["transactions"]["publish_scheduler_state"]["budget"]["put_count"], 1)

    def test_checkpoint_and_request_index_are_committed_in_same_txn(self):
        plan = self.build()
        for batch in plan["transactions"]["request_batches"]:
            self.assertEqual(batch["budget"]["put_count"], batch["request_count"] + 1)
            self.assertEqual(batch["budget"]["compare_count"], batch["request_count"] + 3)
            self.assertNotIn(plan["target"]["scheduler_state_key"], batch["request_keys"])

    def test_state_is_last_and_checkpoint_is_outside_application_key_ranges(self):
        plan = self.build()
        self.assertTrue(plan["target"]["application_access_must_remain_disabled_until_publish_verified"])
        self.assertIn("/staging/sqlite-import/", plan["target"]["checkpoint_key"])
        self.assertTrue(any("exclude staging/" in item for item in plan["activation_barrier"]))
        self.assertEqual(plan["transactions"]["publish_scheduler_state"]["budget"]["put_count"], 1)

    def test_zero_request_candidate_still_initializes_checkpoint_and_publishes_state(self):
        plan = self.build(multi_request_candidate(0))
        self.assertEqual(plan["transactions"]["request_batches"], [])
        self.assertEqual(plan["transactions"]["total_transaction_count"], 2)

    def test_rejects_production_namespace(self):
        with self.assertRaises(StagedImportPlanError):
            build_staged_import_plan(
                multi_request_candidate(1),
                b"/cnc/admission/unified/v2/",
                max_txn_ops=100,
                max_txn_bytes=1_000_000,
                wire_safety_margin_bytes=0,
            )

    def test_rejects_budget_that_cannot_fit_one_request_and_checkpoint(self):
        with self.assertRaisesRegex(StagedImportPlanError, "one terminal request"):
            self.build(max_ops=5)

    def test_rejects_single_scheduler_aggregate_that_cannot_fit_final_txn(self):
        with self.assertRaisesRegex(StagedImportPlanError, "scheduler aggregate"):
            self.build(max_bytes=1)

    def test_initial_checkpoint_unknown_outcome_classification(self):
        plan = self.build(multi_request_candidate(0))
        import json
        checkpoint = json.dumps(
            plan["transactions"]["initialize_checkpoint"]["checkpoint_value"],
            sort_keys=True, separators=(",", ":"),
        ).encode()
        self.assertEqual(classify_checkpoint_initialization_unknown(
            observed_checkpoint=checkpoint,
            observed_state_exists=False,
            observed_leader_exists=False,
            observed_request_key_count=0,
            expected_initial_checkpoint=checkpoint,
        ), UNKNOWN_COMMITTED)
        self.assertEqual(classify_checkpoint_initialization_unknown(
            observed_checkpoint=None,
            observed_state_exists=False,
            observed_leader_exists=False,
            observed_request_key_count=0,
            expected_initial_checkpoint=checkpoint,
        ), UNKNOWN_RETRY)
        self.assertEqual(classify_checkpoint_initialization_unknown(
            observed_checkpoint=None,
            observed_state_exists=True,
            observed_leader_exists=False,
            observed_request_key_count=0,
            expected_initial_checkpoint=checkpoint,
        ), UNKNOWN_QUARANTINE)

    def test_batch_unknown_outcome_committed_retry_or_quarantine(self):
        candidate = multi_request_candidate(2)
        plan = self.build(candidate)
        batch = plan["transactions"]["request_batches"][0]
        previous = plan["transactions"]["initialize_checkpoint"]["checkpoint_value"]
        previous_bytes = json.dumps(previous, sort_keys=True, separators=(",", ":")).encode()
        after_bytes = json.dumps(batch["checkpoint_after"], sort_keys=True, separators=(",", ":")).encode()
        expected_values = {}
        for index in candidate["terminal_request_indexes"]:
            key = PREFIX + index["key"].encode()
            expected_values[key] = json.dumps(index["record"], sort_keys=True, separators=(",", ":")).encode()
        observed = {k: expected_values[k] for k in expected_values}
        self.assertEqual(classify_batch_unknown(
            plan_sha256=plan["plan_sha256"],
            expected_previous_checkpoint=previous_bytes,
            observed_checkpoint=after_bytes,
            expected_completed_request_count=2,
            expected_successor_checkpoints=[after_bytes],
            observed_request_values=observed,
            expected_request_values=expected_values,
            observed_state_exists=False,
            observed_leader_exists=False,
        ), UNKNOWN_COMMITTED)
        self.assertEqual(classify_batch_unknown(
            plan_sha256=plan["plan_sha256"],
            expected_previous_checkpoint=previous_bytes,
            observed_checkpoint=previous_bytes,
            expected_completed_request_count=2,
            expected_successor_checkpoints=[after_bytes],
            observed_request_values={k: None for k in expected_values},
            expected_request_values=expected_values,
            observed_state_exists=False,
            observed_leader_exists=False,
        ), UNKNOWN_RETRY)
        corrupt = dict(observed)
        corrupt[next(iter(corrupt))] = b"foreign-value"
        self.assertEqual(classify_batch_unknown(
            plan_sha256=plan["plan_sha256"],
            expected_previous_checkpoint=previous_bytes,
            observed_checkpoint=after_bytes,
            expected_completed_request_count=2,
            expected_successor_checkpoints=[after_bytes],
            observed_request_values=corrupt,
            expected_request_values=expected_values,
            observed_state_exists=False,
            observed_leader_exists=False,
        ), UNKNOWN_QUARANTINE)

    def test_advanced_checkpoint_proves_earlier_batch_only_with_exact_values(self):
        candidate = multi_request_candidate(5)
        plan = self.build(candidate)
        batches = plan["transactions"]["request_batches"]
        first = batches[0]
        final_checkpoint = batches[-1]["checkpoint_after"]
        first_keys = [
            PREFIX + item["key"].encode()
            for item in candidate["terminal_request_indexes"][:first["request_count"]]
        ]
        first_values = {
            PREFIX + item["key"].encode(): json.dumps(
                item["record"], sort_keys=True, separators=(",", ":")
            ).encode()
            for item in candidate["terminal_request_indexes"][:first["request_count"]]
        }
        initial = plan["transactions"]["initialize_checkpoint"]["checkpoint_value"]
        previous_bytes = json.dumps(initial, sort_keys=True, separators=(",", ":")).encode()
        final_bytes = json.dumps(final_checkpoint, sort_keys=True, separators=(",", ":")).encode()
        successor_checkpoints = [
            json.dumps(batch["checkpoint_after"], sort_keys=True, separators=(",", ":")).encode()
            for batch in batches
        ]
        self.assertEqual(classify_batch_unknown(
            plan_sha256=plan["plan_sha256"],
            expected_previous_checkpoint=previous_bytes,
            observed_checkpoint=final_bytes,
            expected_completed_request_count=first["request_count"],
            expected_successor_checkpoints=successor_checkpoints,
            observed_request_values=first_values,
            expected_request_values=first_values,
            observed_state_exists=False,
            observed_leader_exists=False,
        ), UNKNOWN_COMMITTED)

    def test_batch_unknown_rejects_checkpoint_not_in_plan_chain(self):
        candidate = multi_request_candidate(2)
        plan = self.build(candidate)
        batch = plan["transactions"]["request_batches"][0]
        previous = plan["transactions"]["initialize_checkpoint"]["checkpoint_value"]
        previous_bytes = json.dumps(
            previous, sort_keys=True, separators=(",", ":")
        ).encode()
        expected_checkpoint = json.dumps(
            batch["checkpoint_after"], sort_keys=True, separators=(",", ":")
        ).encode()
        forged = dict(batch["checkpoint_after"])
        forged["progress_sha256"] = "f" * 64
        forged_bytes = json.dumps(
            forged, sort_keys=True, separators=(",", ":")
        ).encode()
        expected_values = {
            PREFIX + item["key"].encode(): json.dumps(
                item["record"], sort_keys=True, separators=(",", ":")
            ).encode()
            for item in candidate["terminal_request_indexes"]
        }
        self.assertEqual(classify_batch_unknown(
            plan_sha256=plan["plan_sha256"],
            expected_previous_checkpoint=previous_bytes,
            observed_checkpoint=forged_bytes,
            expected_completed_request_count=2,
            expected_successor_checkpoints=[expected_checkpoint],
            observed_request_values=expected_values,
            expected_request_values=expected_values,
            observed_state_exists=False,
            observed_leader_exists=False,
        ), UNKNOWN_QUARANTINE)

    def test_publish_unknown_conflicting_state_is_quarantined(self):
        candidate = multi_request_candidate(0)
        plan = self.build(candidate)
        checkpoint = json.dumps(
            plan["transactions"]["initialize_checkpoint"]["checkpoint_value"],
            sort_keys=True, separators=(",", ":"),
        ).encode()
        expected_state = json.dumps(
            candidate["state_template"], sort_keys=True, separators=(",", ":")
        ).encode()
        self.assertEqual(classify_publish_unknown(
            observed_checkpoint=checkpoint,
            expected_final_checkpoint=checkpoint,
            observed_state=b"foreign-state",
            expected_state=expected_state,
            observed_leader_exists=False,
        ), UNKNOWN_QUARANTINE)

    def test_publish_unknown_outcome_requires_exact_state_and_complete_checkpoint(self):
        candidate = multi_request_candidate(0)
        plan = self.build(candidate)
        init = plan["transactions"]["initialize_checkpoint"]
        state = candidate["state_template"]
        expected_state = json.dumps(state, sort_keys=True, separators=(",", ":")).encode()
        checkpoint = json.dumps(
            init["checkpoint_value"], sort_keys=True, separators=(",", ":")
        ).encode()
        self.assertEqual(classify_publish_unknown(
            observed_checkpoint=checkpoint,
            expected_final_checkpoint=checkpoint,
            observed_state=expected_state,
            expected_state=expected_state,
            observed_leader_exists=False,
        ), UNKNOWN_COMMITTED)
        self.assertEqual(classify_publish_unknown(
            observed_checkpoint=checkpoint,
            expected_final_checkpoint=checkpoint,
            observed_state=None,
            expected_state=expected_state,
            observed_leader_exists=False,
        ), UNKNOWN_RETRY)
        self.assertEqual(classify_publish_unknown(
            observed_checkpoint=checkpoint,
            expected_final_checkpoint=checkpoint,
            observed_state=None,
            expected_state=expected_state,
            observed_leader_exists=True,
        ), UNKNOWN_QUARANTINE)


if __name__ == "__main__":
    unittest.main()
