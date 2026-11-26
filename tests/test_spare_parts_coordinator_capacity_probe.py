from __future__ import annotations

import copy
import csv
import unittest
from pathlib import Path

from scripts.spare_parts_coordinator_capacity_probe import (
    DEFAULT_ETCD_MAX_REQUEST_BYTES,
    DEFAULT_MATRIX,
    build_synthetic_state,
    inspect_aggregate,
    run_matrix,
)
from scripts.spare_parts_provider_unified_admission_store import (
    StoreBackedProviderAdmissionCoordinator,
)


class UnifiedCoordinatorCapacityProbeTests(unittest.TestCase):
    def test_aggregate_bytes_match_canonical_scheduler_encoding(self):
        state = build_synthetic_state(
            scope_count=2,
            operations_per_scope=3,
            active_lease_count=2,
            waiter_count=4,
        )
        report = inspect_aggregate(state)
        expected = StoreBackedProviderAdmissionCoordinator._encode(state)
        self.assertEqual(report["aggregate_value_bytes"], len(expected))
        self.assertEqual(
            report["coordinator_subtree_bytes"],
            len(StoreBackedProviderAdmissionCoordinator._encode(state["coordinator"])),
        )

    def test_operation_index_size_grows_monotonically(self):
        sizes = []
        for count in (0, 10, 50, 100):
            state = build_synthetic_state(
                scope_count=1,
                operations_per_scope=count,
            )
            sizes.append(inspect_aggregate(state)["operation_index_bytes"])
        self.assertEqual(sizes, sorted(sizes))
        self.assertGreater(sizes[-1], sizes[0])

    def test_scope_index_size_grows_monotonically(self):
        sizes = []
        for count in (0, 1, 10, 50):
            state = build_synthetic_state(
                scope_count=count,
                operations_per_scope=0,
            )
            sizes.append(inspect_aggregate(state)["scope_index_bytes"])
        self.assertEqual(sizes, sorted(sizes))
        self.assertGreater(sizes[-1], sizes[0])

    def test_active_lease_compare_estimate_has_two_entries_per_lease(self):
        for active in (0, 1, 10, 50):
            state = build_synthetic_state(
                scope_count=1,
                operations_per_scope=0,
                active_lease_count=active,
            )
            report = inspect_aggregate(state)
            self.assertEqual(
                report["coordinator_compare_count_estimate"],
                2 + 2 * active,
            )

    def test_waiter_count_is_reported_without_mutating_state(self):
        state = build_synthetic_state(
            scope_count=2,
            operations_per_scope=1,
            waiter_count=12,
        )
        before = copy.deepcopy(state)
        report = inspect_aggregate(state)
        self.assertEqual(report["waiter_count"], 12)
        self.assertEqual(state, before)

    def test_target_budget_is_a_report_threshold_not_a_server_limit(self):
        state = build_synthetic_state(scope_count=1, operations_per_scope=0)
        measured = inspect_aggregate(
            state,
            max_request_bytes=1_000,
            target_utilization=0.5,
        )
        self.assertEqual(measured["aggregate_target_budget_bytes"], 500)
        self.assertFalse(measured["within_target_budget"])
        self.assertGreater(measured["request_value_to_reference_limit_ratio"], 0)
        self.assertIn("lower bound", measured["measurement_boundary"])

    def test_reference_request_limit_is_the_documented_default(self):
        self.assertEqual(DEFAULT_ETCD_MAX_REQUEST_BYTES, 1_572_864)

    def test_zero_scopes_cannot_carry_coordinator_operations(self):
        with self.assertRaises(ValueError):
            build_synthetic_state(scope_count=0, operations_per_scope=1)

    def test_negative_or_boolean_counts_are_rejected(self):
        with self.assertRaises(ValueError):
            build_synthetic_state(scope_count=-1, operations_per_scope=0)
        with self.assertRaises(ValueError):
            build_synthetic_state(
                scope_count=1,
                operations_per_scope=0,
                active_lease_count=True,
            )

    def test_invalid_measurement_budgets_are_rejected(self):
        state = build_synthetic_state(scope_count=1, operations_per_scope=0)
        with self.assertRaises(ValueError):
            inspect_aggregate(state, max_request_bytes=0)
        with self.assertRaises(ValueError):
            inspect_aggregate(state, target_utilization=0)
        with self.assertRaises(ValueError):
            inspect_aggregate(state, target_utilization=1.01)

    def test_matrix_profiles_are_unique_and_monotonic(self):
        profiles = run_matrix(DEFAULT_MATRIX)
        self.assertEqual(len(profiles), 14)
        ids = [item["scenario_id"] for item in profiles]
        self.assertEqual(len(ids), len(set(ids)))
        by_id = {item["scenario_id"]: item for item in profiles}
        self.assertLess(
            by_id["CAP-004"]["aggregate_value_bytes"],
            by_id["CAP-005"]["aggregate_value_bytes"],
        )
        self.assertLess(
            by_id["CAP-006"]["aggregate_value_bytes"],
            by_id["CAP-009"]["aggregate_value_bytes"],
        )
        self.assertTrue(all(item["synthetic_only"] for item in profiles))

    def test_matrix_rejects_duplicate_scenario_ids(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            matrix = Path(tmp) / "duplicate.csv"
            with matrix.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "scenario_id",
                        "purpose",
                        "scope_count",
                        "operations_per_scope",
                        "active_lease_count",
                        "waiter_count",
                    ],
                )
                writer.writeheader()
                row = {
                    "scenario_id": "DUP",
                    "purpose": "duplicate id validation",
                    "scope_count": 1,
                    "operations_per_scope": 0,
                    "active_lease_count": 0,
                    "waiter_count": 0,
                }
                writer.writerow(row)
                writer.writerow(row)
            with self.assertRaises(ValueError):
                run_matrix(matrix)


if __name__ == "__main__":
    unittest.main()
