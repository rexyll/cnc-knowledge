from __future__ import annotations

import concurrent.futures
import unittest

from scripts.spare_parts_provider_admission_partition_model import (
    AdmissionPartitionCapacityError,
    AdmissionPartitionConflictError,
    AdmissionPartitionPolicyError,
    AdmissionPartitionRequestFinalizedError,
    AdmissionPartitionStaleLeaderError,
    AdmissionPartitionIntegrityError,
    EtcdTransactionBudget,
    PartitionFencingRangeAllocator,
    ShardedProviderAdmissionModel,
    tenant_partition,
)


def make_model(
    *,
    global_limit=4,
    tenant_limit=2,
    partition_count=8,
    block_size=4,
    aging_interval=30,
    tenants=("tenant-A", "tenant-B", "tenant-C", "tenant-D"),
):
    model = ShardedProviderAdmissionModel(
        global_limits={"write": global_limit, "read": 3},
        tenant_limits={
            tenant: {"write": tenant_limit, "read": 2}
            for tenant in tenants
        },
        partition_count=partition_count,
        aging_interval_seconds=aging_interval,
        fencing_block_size=block_size,
    )
    owner = "partition-dispatcher"
    for partition in {
        tenant_partition(tenant, partition_count) for tenant in tenants
    }:
        model.fencing.claim_leader(
            partition,
            owner,
            now=0.0,
            ttl_seconds=10_000,
        )
    return model, owner


def submit(model, request_id, tenant, *, priority=0, queued_at=0, domain="write", timeout=1000):
    return model.submit(
        request_id=request_id,
        tenant_id=tenant,
        owner_id=f"owner-{tenant}",
        task_id=f"task-{request_id}",
        domain=domain,
        priority=priority,
        now=float(queued_at),
        timeout_at=float(timeout),
    )


class ShardedProviderAdmissionTests(unittest.TestCase):
    def test_tenant_partition_mapping_is_stable(self):
        first = tenant_partition("tenant-A", 32)
        self.assertEqual(first, tenant_partition("tenant-A", 32))
        self.assertGreaterEqual(first, 0)
        self.assertLess(first, 32)

    def test_partition_count_is_validated(self):
        with self.assertRaises(AdmissionPartitionPolicyError):
            tenant_partition("tenant-A", 0)

    def test_one_active_lease_claims_both_global_and_tenant_slots(self):
        model, owner = make_model(global_limit=3, tenant_limit=1)
        submit(model, "a1", "tenant-A")
        lease = model.dispatch_one(
            "write", dispatcher_id=owner, now=1, lease_ttl_seconds=60
        )
        self.assertIsNotNone(lease)
        snap = model.snapshot()
        self.assertEqual(snap["active_by_domain"]["write"], 1)
        self.assertEqual(sum(x is not None for x in snap["global_slots"]["write"]), 1)
        self.assertEqual(
            sum(x is not None for x in snap["tenant_slots"]["tenant-A/write"]), 1
        )
        self.assertTrue(model.verify_invariants()["consistent"])

    def test_global_quota_is_enforced_across_tenants(self):
        model, owner = make_model(global_limit=2, tenant_limit=2)
        for index, tenant in enumerate(("tenant-A", "tenant-B", "tenant-C")):
            submit(model, f"request-{index}", tenant)
        granted = model.dispatch_batch(
            "write", dispatcher_id=owner, now=1, lease_ttl_seconds=60, max_grants=10
        )
        self.assertEqual(len(granted), 2)
        self.assertEqual(model.snapshot()["active_by_domain"]["write"], 2)
        self.assertIsNone(
            model.dispatch_one(
                "write", dispatcher_id=owner, now=1, lease_ttl_seconds=60
            )
        )
        self.assertTrue(model.verify_invariants()["consistent"])

    def test_tenant_quota_is_enforced_while_global_capacity_remains(self):
        model, owner = make_model(global_limit=4, tenant_limit=1)
        submit(model, "a1", "tenant-A")
        submit(model, "a2", "tenant-A")
        submit(model, "b1", "tenant-B")
        granted = model.dispatch_batch(
            "write", dispatcher_id=owner, now=1, lease_ttl_seconds=60, max_grants=10
        )
        self.assertEqual(len(granted), 2)
        self.assertEqual(
            model.snapshot()["active_by_tenant_domain"]["tenant-A/write"], 1
        )
        self.assertEqual(
            model.snapshot()["active_by_tenant_domain"]["tenant-B/write"], 1
        )

    def test_round_robin_dispatch_fairness_across_tenants(self):
        model, owner = make_model(global_limit=4, tenant_limit=3)
        for request_id, tenant in (
            ("a1", "tenant-A"),
            ("a2", "tenant-A"),
            ("b1", "tenant-B"),
            ("b2", "tenant-B"),
            ("c1", "tenant-C"),
        ):
            submit(model, request_id, tenant)
        granted = model.dispatch_batch(
            "write", dispatcher_id=owner, now=1, lease_ttl_seconds=60, max_grants=5
        )
        first_three = [record.tenant_id for record in granted[:3]]
        self.assertEqual(first_three, ["tenant-A", "tenant-B", "tenant-C"])

    def test_priority_is_ordered_within_tenant_queue(self):
        model, owner = make_model(global_limit=2, tenant_limit=2)
        submit(model, "low", "tenant-A", priority=0, queued_at=0)
        submit(model, "high", "tenant-A", priority=3, queued_at=0)
        lease = model.dispatch_one(
            "write", dispatcher_id=owner, now=1, lease_ttl_seconds=60
        )
        self.assertEqual(lease.request_id, "high")

    def test_queue_aging_can_promote_an_older_request_within_tenant(self):
        model, owner = make_model(global_limit=2, tenant_limit=2, aging_interval=30)
        submit(model, "old-low", "tenant-A", priority=0, queued_at=0)
        submit(model, "new-high", "tenant-A", priority=1, queued_at=100)
        lease = model.dispatch_one(
            "write", dispatcher_id=owner, now=1000, lease_ttl_seconds=60
        )
        self.assertEqual(lease.request_id, "old-low")

    def test_new_immediate_request_cannot_bypass_an_older_other_tenant_waiter(self):
        model, owner = make_model(global_limit=4, tenant_limit=2)
        submit(model, "a-waiting", "tenant-A")
        result = model.acquire_immediate(
            request_id="b-later",
            tenant_id="tenant-B",
            owner_id="owner-tenant-B",
            task_id="task-b-later",
            domain="write",
            now=1,
            lease_ttl_seconds=60,
            dispatcher_id=owner,
        )
        self.assertIsNone(result)
        self.assertEqual(model.snapshot()["waiting_count"], 2)

    def test_request_id_replay_does_not_duplicate_waiter(self):
        model, _ = make_model()
        submit(model, "same-id", "tenant-A")
        replay = submit(model, "same-id", "tenant-A", priority=99)
        self.assertEqual(replay["request_id"], "same-id")
        self.assertEqual(model.snapshot()["waiting_count"], 1)

    def test_request_id_reuse_for_another_tenant_is_rejected(self):
        model, _ = make_model()
        submit(model, "same-id", "tenant-A")
        with self.assertRaises(AdmissionPartitionConflictError):
            submit(model, "same-id", "tenant-B")

    def test_terminal_request_id_cannot_be_reused(self):
        model, owner = make_model(global_limit=1, tenant_limit=1)
        submit(model, "terminal-id", "tenant-A")
        lease = model.dispatch_one(
            "write", dispatcher_id=owner, now=1, lease_ttl_seconds=60
        )
        self.assertTrue(model.release(lease.lease_id))
        with self.assertRaises(AdmissionPartitionRequestFinalizedError):
            submit(model, "terminal-id", "tenant-A", queued_at=2)

    def test_release_atomically_frees_global_and_tenant_slots(self):
        model, owner = make_model(global_limit=1, tenant_limit=1)
        submit(model, "a1", "tenant-A")
        lease = model.dispatch_one(
            "write", dispatcher_id=owner, now=1, lease_ttl_seconds=60
        )
        self.assertTrue(model.release(lease.lease_id))
        self.assertEqual(model.snapshot()["active_count"], 0)
        self.assertTrue(model.verify_invariants()["consistent"])
        submit(model, "a2", "tenant-A", queued_at=2, timeout=100)
        next_lease = model.dispatch_one(
            "write", dispatcher_id=owner, now=2, lease_ttl_seconds=60
        )
        self.assertIsNotNone(next_lease)

    def test_expiry_frees_both_capacity_slots(self):
        model, owner = make_model(global_limit=1, tenant_limit=1)
        submit(model, "expires", "tenant-A")
        lease = model.dispatch_one(
            "write", dispatcher_id=owner, now=1, lease_ttl_seconds=5
        )
        self.assertEqual(model.expire(now=6), [lease.lease_id])
        self.assertEqual(model.snapshot()["active_count"], 0)
        self.assertEqual(model._requests["expires"]["state"], "EXPIRED")
        self.assertTrue(model.verify_invariants()["consistent"])

    def test_waiter_timeout_keeps_terminal_request_tombstone(self):
        model, _ = make_model()
        submit(model, "wait-timeout", "tenant-A", queued_at=0, timeout=10)
        self.assertEqual(model.expire_waiters(now=10), ["wait-timeout"])
        self.assertEqual(model.snapshot()["waiting_count"], 0)
        with self.assertRaises(AdmissionPartitionRequestFinalizedError):
            submit(model, "wait-timeout", "tenant-A", queued_at=11, timeout=20)

    def test_renew_preserves_permit_slots_and_fencing_token(self):
        model, owner = make_model(global_limit=2, tenant_limit=2)
        submit(model, "renew", "tenant-A")
        lease = model.dispatch_one(
            "write", dispatcher_id=owner, now=1, lease_ttl_seconds=5
        )
        renewed = model.renew(lease.lease_id, now=3, ttl_seconds=100)
        self.assertEqual(renewed.fencing_token, lease.fencing_token)
        self.assertEqual(renewed.global_slot, lease.global_slot)
        self.assertEqual(renewed.tenant_slot, lease.tenant_slot)
        self.assertEqual(model.snapshot()["active_count"], 1)

    def test_read_and_write_domains_have_independent_global_permits(self):
        model, owner = make_model(global_limit=1, tenant_limit=1)
        submit(model, "write-id", "tenant-A", domain="write")
        submit(model, "read-id", "tenant-A", domain="read")
        write_lease = model.dispatch_one(
            "write", dispatcher_id=owner, now=1, lease_ttl_seconds=60
        )
        read_lease = model.dispatch_one(
            "read", dispatcher_id=owner, now=1, lease_ttl_seconds=60
        )
        self.assertIsNotNone(write_lease)
        self.assertIsNotNone(read_lease)
        self.assertEqual(model.snapshot()["active_count"], 2)

    def test_cancel_waiter_removes_only_waiting_request(self):
        model, _ = make_model()
        submit(model, "cancel-me", "tenant-A")
        self.assertTrue(model.cancel_waiter("cancel-me"))
        self.assertFalse(model.cancel_waiter("cancel-me"))
        self.assertEqual(model._requests["cancel-me"]["state"], "CANCELLED")
        self.assertEqual(model.snapshot()["waiting_count"], 0)

    def test_dispatch_batch_is_bounded_by_requested_grants(self):
        model, owner = make_model(global_limit=6, tenant_limit=3)
        for index, tenant in enumerate(("tenant-A", "tenant-B", "tenant-C", "tenant-D")):
            submit(model, f"batch-{index}", tenant)
        records = model.dispatch_batch(
            "write", dispatcher_id=owner, now=1, lease_ttl_seconds=60, max_grants=2
        )
        self.assertEqual(len(records), 2)

    def test_partition_fencing_tokens_are_unique_across_partitions(self):
        allocator = PartitionFencingRangeAllocator(block_size=4)
        allocator.claim_leader(0, "p0", now=0, ttl_seconds=10)
        allocator.claim_leader(1, "p1", now=0, ttl_seconds=10)
        p0 = allocator.next_token(0, "p0", 1, now=1)
        p1 = allocator.next_token(1, "p1", 1, now=1)
        self.assertNotEqual(p0, p1)

    def test_partition_fencing_tokens_are_monotonic_within_partition(self):
        allocator = PartitionFencingRangeAllocator(block_size=3)
        allocator.claim_leader(0, "p0", now=0, ttl_seconds=100)
        tokens = [
            allocator.next_token(0, "p0", 1, now=1),
            allocator.next_token(0, "p0", 1, now=1),
            allocator.next_token(0, "p0", 1, now=1),
            allocator.next_token(0, "p0", 1, now=1),
        ]
        self.assertEqual(tokens, sorted(tokens))
        self.assertEqual(len(tokens), len(set(tokens)))

    def test_leader_failover_discards_unused_range_and_does_not_reuse_tokens(self):
        allocator = PartitionFencingRangeAllocator(block_size=8)
        allocator.claim_leader(3, "old", now=0, ttl_seconds=5)
        first = allocator.next_token(3, "old", 1, now=1)
        allocator.claim_leader(3, "new", now=10, ttl_seconds=5)
        second = allocator.next_token(3, "new", 2, now=11)
        self.assertEqual(first, 1)
        self.assertGreater(second, first)
        self.assertGreaterEqual(second, 9)

    def test_external_fencing_floor_is_honored_before_range_reservation(self):
        allocator = PartitionFencingRangeAllocator(block_size=4)
        allocator.claim_leader(
            1, "owner", now=0, ttl_seconds=10, external_high_water_floor=500
        )
        self.assertEqual(
            allocator.next_token(1, "owner", 1, now=1),
            501,
        )

    def test_same_leader_discards_unconsumed_range_when_external_floor_advances(self):
        allocator = PartitionFencingRangeAllocator(block_size=8)
        allocator.claim_leader(2, "owner", now=0, ttl_seconds=100)
        first = allocator.next_token(2, "owner", 1, now=1)
        self.assertEqual(first, 1)
        allocator.claim_leader(
            2, "owner", now=2, ttl_seconds=100,
            external_high_water_floor=500,
        )
        next_token = allocator.next_token(2, "owner", 1, now=3)
        self.assertEqual(next_token, 501)

    def test_expired_leader_cannot_issue_tokens(self):
        allocator = PartitionFencingRangeAllocator(block_size=4)
        allocator.claim_leader(1, "owner", now=0, ttl_seconds=2)
        with self.assertRaises(AdmissionPartitionStaleLeaderError):
            allocator.next_token(1, "owner", 1, now=3)

    def test_live_partition_cannot_be_claimed_by_another_leader(self):
        allocator = PartitionFencingRangeAllocator()
        allocator.claim_leader(1, "owner-a", now=0, ttl_seconds=10)
        with self.assertRaises(AdmissionPartitionConflictError):
            allocator.claim_leader(1, "owner-b", now=1, ttl_seconds=10)

    def test_fencing_allocator_reserves_new_non_overlapping_block_after_exhaustion(self):
        allocator = PartitionFencingRangeAllocator(block_size=2)
        allocator.claim_leader(0, "p0", now=0, ttl_seconds=100)
        values = [allocator.next_token(0, "p0", 1, now=1) for _ in range(5)]
        self.assertEqual(values, [1, 2, 3, 4, 5])

    def test_global_capacity_is_not_oversold_under_concurrent_dispatch(self):
        model, owner = make_model(
            global_limit=7,
            tenant_limit=2,
            partition_count=16,
            tenants=tuple(f"tenant-{i:02d}" for i in range(20)),
        )
        for index in range(80):
            tenant = f"tenant-{index % 20:02d}"
            submit(model, f"concurrent-{index}", tenant)
        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
            futures = [
                pool.submit(
                    model.dispatch_one,
                    "write",
                    dispatcher_id=owner,
                    now=1,
                    lease_ttl_seconds=60,
                )
                for _ in range(40)
            ]
            results = [future.result() for future in futures]
        granted = [item for item in results if item is not None]
        self.assertEqual(len(granted), 7)
        self.assertLessEqual(model.snapshot()["active_by_domain"]["write"], 7)
        self.assertTrue(model.verify_invariants()["consistent"])

    def test_tenant_capacity_is_not_oversold_under_concurrent_dispatch(self):
        model, owner = make_model(global_limit=20, tenant_limit=2)
        for index in range(20):
            submit(model, f"same-tenant-{index}", "tenant-A")
        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
            futures = [
                pool.submit(
                    model.dispatch_one,
                    "write",
                    dispatcher_id=owner,
                    now=1,
                    lease_ttl_seconds=60,
                )
                for _ in range(20)
            ]
            results = [future.result() for future in futures]
        self.assertEqual(sum(item is not None for item in results), 2)
        self.assertEqual(
            model.snapshot()["active_by_tenant_domain"]["tenant-A/write"], 2
        )
        self.assertTrue(model.verify_invariants()["consistent"])

    def test_transaction_estimate_fits_admission_fast_path_budget(self):
        budget = EtcdTransactionBudget(
            max_txn_ops=128, max_request_bytes=1_572_864, utilization_target=0.70
        )
        report = budget.admission_grant_shape(key_prefix="/cnc/v3", request_id="r1")
        self.assertEqual(report.compare_count, 5)
        self.assertEqual(report.success_operation_count, 4)
        self.assertEqual(report.worst_case_operation_count, 9)
        budget.require_fit(report)

    def test_transaction_estimate_fits_coordinator_scope_commit(self):
        budget = EtcdTransactionBudget()
        report = budget.coordinator_scope_commit_shape(
            key_prefix="/cnc/v3", scope_id="scope-1", operation_id="op-1"
        )
        self.assertEqual(report.compare_count, 7)
        self.assertEqual(report.worst_case_operation_count, 9)
        budget.require_fit(report)

    def test_dispatch_batch_budget_fits_for_sixteen_partitions_and_four_grants(self):
        budget = EtcdTransactionBudget(
            max_txn_ops=128,
            max_request_bytes=1_572_864,
            utilization_target=0.70,
        )
        report = budget.dispatch_batch_shape(
            partition_count=16,
            batch_size=4,
            key_prefix="/cnc/v3",
        )
        self.assertEqual(report.worst_case_operation_count, 58)
        budget.require_fit(report)

    def test_dispatch_batch_budget_rejects_too_many_partition_heads(self):
        budget = EtcdTransactionBudget(
            max_txn_ops=128,
            max_request_bytes=1_572_864,
            utilization_target=0.70,
        )
        report = budget.dispatch_batch_shape(
            partition_count=64,
            batch_size=4,
            key_prefix="/cnc/v3",
        )
        self.assertFalse(report.within_operation_budget)
        with self.assertRaises(AdmissionPartitionPolicyError):
            budget.require_fit(report)

    def test_transaction_operation_budget_is_enforced(self):
        budget = EtcdTransactionBudget(
            max_txn_ops=16,
            max_request_bytes=100_000,
            utilization_target=0.50,
        )
        report = budget.estimate(
            compares=[{"key": f"k{i}"} for i in range(8)],
            success_ops=[{"key": f"p{i}"} for i in range(4)],
        )
        self.assertFalse(report.within_operation_budget)
        with self.assertRaises(AdmissionPartitionPolicyError):
            budget.require_fit(report)

    def test_transaction_request_byte_budget_is_enforced(self):
        budget = EtcdTransactionBudget(
            max_txn_ops=128,
            max_request_bytes=512,
            utilization_target=0.5,
        )
        report = budget.estimate(
            compares=[{"key": "a", "expected": "x" * 1000}],
            success_ops=[{"key": "b", "value": "y" * 1000}],
        )
        self.assertFalse(report.within_byte_budget)
        with self.assertRaises(AdmissionPartitionPolicyError):
            budget.require_fit(report)

    def test_transaction_model_reports_that_wire_size_is_not_measured(self):
        budget = EtcdTransactionBudget()
        report = budget.admission_grant_shape(key_prefix="/cnc/v3", request_id="r")
        self.assertTrue(report.model_only)
        self.assertGreater(report.request_model_bytes, 0)

    def test_invariant_check_detects_slot_index_corruption(self):
        model, owner = make_model(global_limit=2, tenant_limit=2)
        submit(model, "integrity", "tenant-A")
        lease = model.dispatch_one(
            "write", dispatcher_id=owner, now=1, lease_ttl_seconds=60
        )
        model._global_slots["write"][lease.global_slot] = "corrupted"
        with self.assertRaises(AdmissionPartitionIntegrityError):
            model.verify_invariants()


if __name__ == "__main__":
    unittest.main()
