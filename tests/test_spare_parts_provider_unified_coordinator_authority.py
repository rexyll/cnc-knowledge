from __future__ import annotations

import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from scripts.spare_parts_backup_storage_adapter import (
    ProviderTaskContext,
)
from scripts.spare_parts_fencing_attestation import (
    Ed25519PrivateKeySigner,
)
from scripts.spare_parts_provider_authority_store import (
    EtcdV3CoordinatorAuthorityStore,
    InMemoryEtcdV3Client,
    SQLiteCoordinatorAuthorityStore,
)
from scripts.spare_parts_provider_coordinator_authority import (
    CoordinatorAuthorityConflictError,
    CoordinatorAuthorityError,
    CoordinatorAuthorityStaleLeaderError,
    sign_distributed_fencing_proof,
)
from scripts.spare_parts_provider_distributed_fencing import (
    DistributedObjectFencingControlPlane,
    InMemoryConditionalObjectControlStore,
)
from scripts.spare_parts_provider_unified_admission_store import (
    StoreBackedProviderAdmissionCoordinator,
)
from scripts.spare_parts_provider_unified_coordinator_authority import (
    StoreBackedCoordinatorAuthority,
)


class MutableClock:
    def __init__(self, value: float = 10_000.0):
        self.value = value
        self.lock = threading.Lock()

    def __call__(self) -> float:
        with self.lock:
            return self.value

    def advance(self, seconds: float) -> None:
        with self.lock:
            self.value += seconds


class StoreBackedCoordinatorAuthorityContract:
    SCOPE = "tenants/tenant-A/cnc/ch17/spares/pkg-001"

    def store(self):
        raise NotImplementedError

    def setUpContract(self):
        raise NotImplementedError

    def task(self, request_id: str, tenant: str = "tenant-A"):
        return ProviderTaskContext(f"task-{request_id}", tenant)

    def acquire(self, request_id: str = "request-1", tenant: str = "tenant-A"):
        return self.scheduler.acquire(
            task=self.task(request_id, tenant),
            domain="write",
            owner_id=f"owner-{tenant}",
            lease_ttl_seconds=120,
            timeout_seconds=0,
            check_task=lambda _: None,
            request_id=request_id,
        )

    def activate(self, lease, idem: str = "activate-1"):
        operation = self.authority.prepare_activation(
            self.leader, lease, scope=self.SCOPE, idempotency_key=idem
        )
        proof = sign_distributed_fencing_proof(
            self.authority,
            self.leader,
            operation,
            lease,
            issuer_id="test-coordinator",
            signer=self.signer,
            clock_fn=self.clock,
        )
        provider_record = self.provider.activate_lease(
            self.SCOPE, fencing_attestation=proof
        )
        generation = self.control_store.read_control(self.SCOPE)[0]
        confirmed = self.authority.confirm_activation(
            self.leader,
            scope=self.SCOPE,
            fencing_token=operation.fencing_token,
            idempotency_key=idem,
            observed_provider_state=provider_record["lease_state"],
            observed_high_water_token=provider_record["high_water_token"],
            observed_lease_id=provider_record["lease_id"],
            provider_generation=generation,
        )
        return confirmed

    def test_end_to_end_activation_publish_and_revocation_use_one_aggregate(self):
        lease = self.acquire()
        activation = self.activate(lease)
        self.assertEqual(activation.state, "ACTIVE")
        self.assertEqual(activation.fencing_token, 1)

        publish = self.authority.allocate_operation_sequence(
            self.leader,
            lease,
            scope=self.SCOPE,
            idempotency_key="publish-1",
            manifest_key=f"{self.SCOPE}/staging/{activation.fencing_token}/manifest.json",
            manifest_sha256="a" * 64,
        )
        self.assertEqual(publish.operation_sequence, 1)
        proof = sign_distributed_fencing_proof(
            self.authority,
            self.leader,
            publish,
            lease,
            issuer_id="test-coordinator",
            signer=self.signer,
            clock_fn=self.clock,
        )
        receipt = self.provider.publish_commit(
            self.SCOPE, fencing_attestation=proof
        )
        generation = self.control_store.read_control(self.SCOPE)[0]
        committed = self.authority.confirm_publish(
            self.leader,
            scope=self.SCOPE,
            idempotency_key="publish-1",
            observed_provider_state="ACTIVE",
            observed_fencing_token=receipt.fencing_token,
            observed_operation_sequence=receipt.operation_sequence,
            observed_idempotency_key=receipt.idempotency_key,
            observed_manifest_key=receipt.manifest_key,
            observed_manifest_sha256=receipt.manifest_sha256,
            provider_generation=generation,
        )
        self.assertEqual(committed.state, "COMMITTED")

        revoke = self.authority.prepare_revocation(
            self.leader,
            lease,
            scope=self.SCOPE,
            fencing_token=activation.fencing_token,
            idempotency_key="revoke-1",
        )
        self.assertEqual(revoke.state, "REVOKING")
        revoke_proof = sign_distributed_fencing_proof(
            self.authority,
            self.leader,
            revoke,
            lease,
            issuer_id="test-coordinator",
            signer=self.signer,
            clock_fn=self.clock,
        )
        revoked_record = self.provider.revoke_lease(
            self.SCOPE, fencing_attestation=revoke_proof
        )
        generation = self.control_store.read_control(self.SCOPE)[0]
        revoked = self.authority.confirm_revocation(
            self.leader,
            scope=self.SCOPE,
            fencing_token=revoke.fencing_token,
            idempotency_key="revoke-1",
            observed_provider_state=revoked_record["lease_state"],
            observed_high_water_token=revoked_record["high_water_token"],
            observed_lease_id=revoked_record["lease_id"],
            provider_generation=generation,
        )
        self.assertEqual(revoked.state, "REVOKED")
        self.assertEqual(self.authority.snapshot(self.SCOPE)["lease_state"], "REVOKED")
        aggregate, _ = self.store().linearizable_get(self.scheduler._STATE_KEY)
        decoded = self.scheduler._decode(aggregate)
        self.assertEqual(decoded["coordinator"]["scopes"][self.SCOPE]["lease_state"], "REVOKED")
        self.assertEqual(len(decoded["coordinator"]["operations"]), 3)

    def test_leader_epoch_ttl_and_old_leader_fencing_share_store(self):
        lease = self.acquire("leader-expiry")
        pending = self.authority.prepare_activation(
            self.leader, lease, scope=self.SCOPE, idempotency_key="pending-before-takeover"
        )
        self.clock.advance(31)
        new_leader = self.authority.claim_leadership("leader-B-instance-2", ttl_seconds=30)
        self.assertEqual(new_leader.epoch, self.leader.epoch + 1)
        with self.assertRaises(CoordinatorAuthorityStaleLeaderError):
            self.authority.authorize_operation_signing(self.leader, pending)
        pending_rows = self.authority.list_pending_operations(new_leader)
        self.assertEqual([row.idempotency_key for row in pending_rows], ["pending-before-takeover"])
        renewed = self.authority.renew_leadership(new_leader, ttl_seconds=45)
        self.assertEqual(renewed.epoch, new_leader.epoch)
        self.assertGreater(renewed.expires_at, new_leader.expires_at)
        # Leader identity is epoch-based: the pre-renewal handle remains valid
        # for this epoch until its new persisted TTL expires or a new epoch wins.
        self.assertEqual(
            self.authority.list_pending_operations(new_leader),
            self.authority.list_pending_operations(renewed),
        )

    def test_activation_idempotency_scope_tenant_isolation_and_lease_validation(self):
        lease = self.acquire("idem-first")
        first = self.authority.prepare_activation(
            self.leader, lease, scope=self.SCOPE, idempotency_key="activate-same"
        )
        replay = self.authority.prepare_activation(
            self.leader, lease, scope=self.SCOPE, idempotency_key="activate-same"
        )
        self.assertEqual(replay, first)
        other_lease = self.acquire("idem-second", tenant="tenant-B")
        with self.assertRaises(CoordinatorAuthorityError):
            self.authority.prepare_activation(
                self.leader,
                other_lease,
                scope=self.SCOPE,
                idempotency_key="activate-same",
            )
        with self.assertRaises(CoordinatorAuthorityError):
            self.authority.prepare_activation(
                self.leader,
                lease,
                scope="tenants/tenant-B/cnc/ch17/spares/pkg-001",
                idempotency_key="cross-tenant",
            )
        self.assertTrue(self.scheduler.release(lease))
        with self.assertRaises(CoordinatorAuthorityConflictError):
            self.authority.prepare_activation(
                self.leader,
                lease,
                scope=self.SCOPE,
                idempotency_key="activation-after-release",
            )

    def test_parallel_operation_sequence_allocations_are_unique_and_idempotent(self):
        lease = self.acquire("parallel-publish")
        activation = self.activate(lease, "activate-parallel")
        manifest_digest = "b" * 64

        def allocate(index: int):
            return self.authority.allocate_operation_sequence(
                self.leader,
                lease,
                scope=self.SCOPE,
                idempotency_key=f"publish-parallel-{index}",
                manifest_key=f"{self.SCOPE}/manifest-{index}.json",
                manifest_sha256=manifest_digest,
            )

        with ThreadPoolExecutor(max_workers=8) as pool:
            operations = list(pool.map(allocate, range(8)))
        sequences = sorted(op.operation_sequence for op in operations)
        self.assertEqual(sequences, list(range(1, 9)))
        repeated = allocate(3)
        self.assertEqual(repeated.operation_sequence, operations[3].operation_sequence)
        self.assertEqual(repeated.fencing_token, activation.fencing_token)
        self.assertEqual(
            self.authority.snapshot(self.SCOPE)["latest_operation_sequence"], 8
        )

    def test_restore_reconciliation_raises_floors_and_requires_review(self):
        lease = self.acquire("restore")
        pending_activation = self.authority.prepare_activation(
            self.leader, lease, scope=self.SCOPE, idempotency_key="activate-restore"
        )
        result = self.authority.reconcile_after_restore(
            self.leader,
            scope=self.SCOPE,
            external_high_water_token=pending_activation.fencing_token + 5,
            external_operation_sequence=7,
            reconciliation_ref="restore-drill-2026-11-26",
        )
        self.assertFalse(result["automatic_cutover"])
        self.assertEqual(result["lease_state"], "RECOVERY_REQUIRED")
        snapshot = self.authority.snapshot(self.SCOPE)
        self.assertEqual(snapshot["high_water_token"], pending_activation.fencing_token + 5)
        self.assertEqual(snapshot["latest_operation_sequence"], 7)
        self.assertEqual(snapshot["lease_state"], "RECOVERY_REQUIRED")
        pending = self.authority.list_pending_operations(self.leader)
        self.assertEqual(pending[0].state, "RECOVERY_REVIEW")
        with self.assertRaises(CoordinatorAuthorityConflictError):
            self.authority.reconcile_after_restore(
                self.leader,
                scope=self.SCOPE,
                external_high_water_token=1,
                external_operation_sequence=7,
                reconciliation_ref="below-floor",
            )

    def test_leadership_recovery_floor_must_exceed_persisted_epoch(self):
        current = self.authority.leader_snapshot()
        self.clock.advance(31)
        with self.assertRaises(CoordinatorAuthorityError):
            self.authority.claim_leadership(
                "recovered-too-low",
                ttl_seconds=30,
                recovery_epoch_floor=current["epoch"],
                reconciliation_ref="bad-floor",
            )
        recovered = self.authority.claim_leadership(
            "recovered-leader",
            ttl_seconds=30,
            recovery_epoch_floor=current["epoch"] + 10,
            reconciliation_ref="approved-external-reconciliation",
        )
        self.assertEqual(recovered.epoch, current["epoch"] + 10)

    def test_coordinator_and_admission_state_share_the_same_txn_store(self):
        lease = self.acquire("shared-state")
        activation = self.authority.prepare_activation(
            self.leader, lease, scope=self.SCOPE, idempotency_key="shared-activation"
        )
        self.assertEqual(activation.fencing_token, 1)
        self.assertTrue(self.scheduler.validate(lease))
        self.assertEqual(self.scheduler.snapshot()["active_by_domain"]["write"], 1)
        state_entry, _ = self.store().linearizable_get(self.scheduler._STATE_KEY)
        state = self.scheduler._decode(state_entry)
        self.assertIn(self.SCOPE, state["coordinator"]["scopes"])
        self.assertIn(
            self.authority._op_key(self.SCOPE, "shared-activation"),
            state["coordinator"]["operations"],
        )
        # Release removes the Admission lease. The same coordinator authority
        # can no longer prepare another operation with the captured lease.
        self.assertTrue(self.scheduler.release(lease))
        with self.assertRaises(CoordinatorAuthorityConflictError):
            self.authority.allocate_operation_sequence(
                self.leader,
                lease,
                scope=self.SCOPE,
                idempotency_key="must-not-allocate",
                manifest_key=f"{self.SCOPE}/manifest.json",
                manifest_sha256="c" * 64,
            )


class SQLiteUnifiedCoordinatorAuthorityTests(StoreBackedCoordinatorAuthorityContract, unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.clock = MutableClock()
        self._store = SQLiteCoordinatorAuthorityStore(
            Path(self.tmp.name) / "unified-coordinator.sqlite3",
            clock_fn=self.clock,
        )
        self.scheduler = StoreBackedProviderAdmissionCoordinator(
            self._store,
            global_limits={"read": 2, "write": 4, "multipart": 2, "inventory": 1},
            max_waiters=8,
            clock_fn=self.clock,
        )
        self.authority = StoreBackedCoordinatorAuthority(
            self.scheduler, clock_fn=self.clock
        )
        self.leader = self.authority.claim_leadership(
            "leader-A-instance-1", ttl_seconds=30
        )
        private_key = Ed25519PrivateKey.generate()
        self.signer = Ed25519PrivateKeySigner(
            key_id="test-kid-v1", private_key=private_key
        )
        self.control_store = InMemoryConditionalObjectControlStore()
        self.provider = DistributedObjectFencingControlPlane(
            self.control_store,
            trusted_ed25519_public_keys={"test-kid-v1": self.signer.public_key_raw()},
            trusted_issuers={"test-coordinator"},
            clock_fn=self.clock,
        )

    def store(self):
        return self._store

    def tearDown(self):
        self.tmp.cleanup()


class EtcdUnifiedCoordinatorAuthorityTests(StoreBackedCoordinatorAuthorityContract, unittest.TestCase):
    def setUp(self):
        self.clock = MutableClock()
        self._client = InMemoryEtcdV3Client(clock_fn=self.clock)
        self._store = EtcdV3CoordinatorAuthorityStore(self._client)
        self.scheduler = StoreBackedProviderAdmissionCoordinator(
            self._store,
            global_limits={"read": 2, "write": 4, "multipart": 2, "inventory": 1},
            max_waiters=8,
            clock_fn=self.clock,
        )
        self.authority = StoreBackedCoordinatorAuthority(
            self.scheduler, clock_fn=self.clock
        )
        self.leader = self.authority.claim_leadership(
            "leader-A-instance-1", ttl_seconds=30
        )
        private_key = Ed25519PrivateKey.generate()
        self.signer = Ed25519PrivateKeySigner(
            key_id="test-kid-v1", private_key=private_key
        )
        self.control_store = InMemoryConditionalObjectControlStore()
        self.provider = DistributedObjectFencingControlPlane(
            self.control_store,
            trusted_ed25519_public_keys={"test-kid-v1": self.signer.public_key_raw()},
            trusted_issuers={"test-coordinator"},
            clock_fn=self.clock,
        )

    def store(self):
        return self._store

    def tearDown(self):
        pass
