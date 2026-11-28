import unittest

from scripts.spare_parts_sqlite_provider_fencing_reconciliation import (
    ProviderFencingReconciliationError,
    validate_provider_fencing_reconciliation,
)


def candidate():
    return {
        "format": "ch17-sqlite-unified-candidate-v2",
        "candidate_digest_sha256": "a" * 64,
        "state_template": {
            "coordinator": {
                "scopes": {
                    "inventory/parts": {
                        "provider_generation": "generation-7",
                        "high_water_token": 12,
                        "latest_operation_sequence": 5,
                    },
                    "inventory/tools": {
                        "provider_generation": "generation-3",
                        "high_water_token": 4,
                        "latest_operation_sequence": 2,
                    },
                }
            }
        },
    }


def evidence():
    return {
        "format": "ch17-provider-fencing-readonly-evidence-v1",
        "provider_id": "provider-prod-a",
        "observed_at_unix": 990.0,
        "scopes": {
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
        },
    }


class ProviderFencingReconciliationTests(unittest.TestCase):
    def test_accepts_complete_fresh_provider_floors_below_candidate(self):
        result = validate_provider_fencing_reconciliation(
            candidate(), evidence(), now_unix=1000.0
        )
        self.assertEqual(result["provider_fencing_reconciliation"], "PASS")
        self.assertEqual(result["verified_scope_count"], 2)
        self.assertFalse(result["application_activation_authorized"])
        self.assertFalse(result["provider_operations_authorized"])
        self.assertEqual(len(result["evidence_sha256"]), 64)

    def test_rejects_missing_scope_evidence(self):
        item = evidence()
        del item["scopes"]["inventory/tools"]
        with self.assertRaisesRegex(ProviderFencingReconciliationError, "exactly every"):
            validate_provider_fencing_reconciliation(candidate(), item, now_unix=1000.0)

    def test_rejects_provider_floor_above_candidate_and_requires_rebuild(self):
        item = evidence()
        item["scopes"]["inventory/parts"]["high_water_token"] = 13
        with self.assertRaisesRegex(ProviderFencingReconciliationError, "rebuild candidate"):
            validate_provider_fencing_reconciliation(candidate(), item, now_unix=1000.0)

    def test_rejects_provider_sequence_above_candidate(self):
        item = evidence()
        item["scopes"]["inventory/tools"]["latest_operation_sequence"] = 3
        with self.assertRaisesRegex(ProviderFencingReconciliationError, "rebuild candidate"):
            validate_provider_fencing_reconciliation(candidate(), item, now_unix=1000.0)

    def test_rejects_generation_mismatch(self):
        item = evidence()
        item["scopes"]["inventory/parts"]["provider_generation"] = "generation-8"
        with self.assertRaisesRegex(ProviderFencingReconciliationError, "generation mismatch"):
            validate_provider_fencing_reconciliation(candidate(), item, now_unix=1000.0)

    def test_rejects_stale_or_future_evidence(self):
        for observed_at in (600.0, 1001.0):
            item = evidence()
            item["observed_at_unix"] = observed_at
            with self.subTest(observed_at=observed_at):
                with self.assertRaises(ProviderFencingReconciliationError):
                    validate_provider_fencing_reconciliation(candidate(), item, now_unix=1000.0)

    def test_rejects_unknown_evidence_schema(self):
        item = evidence()
        item["trusted"] = True
        with self.assertRaisesRegex(ProviderFencingReconciliationError, "schema mismatch"):
            validate_provider_fencing_reconciliation(candidate(), item, now_unix=1000.0)


if __name__ == "__main__":
    unittest.main()
