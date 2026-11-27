from __future__ import annotations

import copy
import unittest

from scripts.spare_parts_sqlite_candidate_importer import build_candidate
from scripts.spare_parts_sqlite_candidate_import_plan import (
    ImportPlanError,
    build_import_plan,
)
from tests.test_spare_parts_sqlite_candidate_importer import fixture


PREFIX = b"/cnc/migration/isolated/round77-plan/"


class CandidateImportPlanTests(unittest.TestCase):
    def candidate(self):
        manifest, records, policy = fixture()
        return build_candidate(manifest, records, policy, generated_at=1000.0)

    def test_builds_atomic_single_transaction_plan(self):
        candidate = self.candidate()
        plan = build_import_plan(
            candidate, PREFIX, max_txn_ops=100, max_txn_bytes=1_000_000
        )
        self.assertTrue(plan["limits"]["fits"])
        self.assertEqual(plan["atomicity"]["transaction_count"], 1)
        self.assertEqual(plan["atomicity"]["compare_count"], 3)
        self.assertEqual(plan["atomicity"]["put_count"], 2)
        self.assertTrue(plan["atomicity"]["all_destination_keys_compared_as_version_zero"])
        self.assertTrue(plan["atomicity"]["state_and_terminal_indexes_commit_together"])
        self.assertEqual(plan["atomicity"]["native_lease_grants_required_for_import"], 0)
        self.assertFalse(plan["atomicity"]["legacy_leader_ttl_key_imported"])
        self.assertTrue(plan["target"]["leader_key_must_remain_absent_until_new_claim"])
        self.assertEqual(plan["payload_estimate"]["terminal_request_count"], 1)
        self.assertTrue(plan["not_performed"])

    def test_rejects_production_namespace(self):
        with self.assertRaises(Exception):
            build_import_plan(
                self.candidate(), b"/cnc/admission/unified/v2/",
                max_txn_ops=100, max_txn_bytes=1_000_000,
            )

    def test_rejects_modified_candidate_digest(self):
        candidate = self.candidate()
        candidate["state_template"]["next_fencing_token"] += 1
        with self.assertRaisesRegex(ImportPlanError, "digest"):
            build_import_plan(candidate, PREFIX, max_txn_ops=100, max_txn_bytes=1_000_000)

    def test_rejects_request_index_key_mismatch(self):
        candidate = self.candidate()
        candidate["terminal_request_indexes"][0]["key"] = "requests/" + "0" * 64
        # Re-signing here ensures key derivation, rather than digest checking, is tested.
        from scripts.spare_parts_sqlite_migration_inventory import _json_bytes
        import hashlib
        material = dict(candidate)
        material.pop("candidate_digest_sha256")
        candidate["candidate_digest_sha256"] = hashlib.sha256(_json_bytes(material)).hexdigest()
        with self.assertRaisesRegex(ImportPlanError, "key"):
            build_import_plan(candidate, PREFIX, max_txn_ops=100, max_txn_bytes=1_000_000)

    def test_rejects_live_or_nonterminal_request_record(self):
        candidate = self.candidate()
        candidate["terminal_request_indexes"][0]["record"]["state"] = "ACTIVE"
        from scripts.spare_parts_sqlite_migration_inventory import _json_bytes
        import hashlib
        material = dict(candidate)
        material.pop("candidate_digest_sha256")
        candidate["candidate_digest_sha256"] = hashlib.sha256(_json_bytes(material)).hexdigest()
        with self.assertRaises(ImportPlanError):
            build_import_plan(candidate, PREFIX, max_txn_ops=100, max_txn_bytes=1_000_000)

    def test_reports_operation_budget_exceeded_without_claiming_ready(self):
        plan = build_import_plan(
            self.candidate(), PREFIX, max_txn_ops=1, max_txn_bytes=1_000_000
        )
        self.assertFalse(plan["limits"]["fits"])
        self.assertIn("compare+put", plan["limits"]["reasons"][0])

    def test_reports_byte_budget_exceeded(self):
        plan = build_import_plan(
            self.candidate(), PREFIX, max_txn_ops=100, max_txn_bytes=1
        )
        self.assertFalse(plan["limits"]["fits"])
        self.assertTrue(any("bytes" in reason for reason in plan["limits"]["reasons"]))

    def test_rejects_scope_identity_that_could_restore_live_lease(self):
        candidate = self.candidate()
        scope = next(iter(candidate["state_template"]["coordinator"]["scopes"].values()))
        scope["lease_id"] = "legacy-live-lease"
        from scripts.spare_parts_sqlite_migration_inventory import _json_bytes
        import hashlib
        material = dict(candidate)
        material.pop("candidate_digest_sha256")
        candidate["candidate_digest_sha256"] = hashlib.sha256(_json_bytes(material)).hexdigest()
        with self.assertRaisesRegex(ImportPlanError, "live lease"):
            build_import_plan(candidate, PREFIX, max_txn_ops=100, max_txn_bytes=1_000_000)


if __name__ == "__main__":
    unittest.main()
