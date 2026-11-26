from __future__ import annotations

import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from scripts.spare_parts_backup_storage_adapter import ProviderTaskContext
from scripts.spare_parts_fencing_attestation import (
    Ed25519PrivateKeySigner,
    verify_fencing_attestation_signature,
)
from scripts.spare_parts_provider_admission_sqlite import SQLiteProviderAdmissionCoordinator
from scripts.spare_parts_provider_coordinator_authority import (
    CoordinatorAuthorityConflictError,
    CoordinatorAuthorityStaleLeaderError,
    SQLiteDurableCoordinatorAuthority,
    sign_distributed_fencing_proof,
)
from scripts.spare_parts_provider_distributed_fencing import (
    DistributedObjectFencingControlPlane,
    InMemoryConditionalObjectControlStore,
)


class MutableClock:
    def __init__(self, value: float = 10_000.0):
        self.value = value

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


class SQLiteDurableCoordinatorAuthorityTests(unittest.TestCase):
    SCOPE = "cnc/ch17/spares/pkg-001"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.database_path = str(Path(self.tmp.name) / "coordinator.sqlite3")
        self.clock = MutableClock()
        self.coordinator = SQLiteProviderAdmissionCoordinator(
            self.database_path,
            global_limits={"read": 2, "write": 4, "multipart": 2, "inventory": 1},
            max_waiters=8,
            clock_fn=self.clock,
        )
        self.authority = SQLiteDurableCoordinatorAuthority(
            self.database_path, clock_fn=self.clock
        )
        self.leader = self.authority.claim_leadership("leader-A-instance-1", ttl_seconds=30)
        private_key = Ed25519PrivateKey.generate()
        self.signer = Ed25519PrivateKeySigner(key_id="test-kid-v1", private_key=private_key)
        self.public_key = self.signer.public_key_raw()
        self.store = InMemoryConditionalObjectControlStore()
        self.provider = DistributedObjectFencingControlPlane(
            self.store,
            trusted_ed25519_public_keys={"test-kid-v1": self.public_key},
            trusted_issuers={"test-coordinator"},
            clock_fn=self.clock,
        )

    def tearDown(self):
        self.tmp.cleanup()

    def acquire(self, request_id: str = "request-1"):
        return self.coordinator.acquire(
            task=ProviderTaskContext(f"task-{request_id}", "tenant-A"),
            domain="write",
            owner_id="owner-A",
            lease_ttl_seconds=300,
            timeout_seconds=0,
            check_task=lambda _: None,
            request_id=request_id,
        )

    def activate(self, lease, idem="activate-1"):
        operation = self.authority.prepare_activation(
            self.leader, lease, scope=self.SCOPE, idempotency_key=idem
        )
        proof = sign_distributed_fencing_proof(
            self.authority, self.leader, operation, lease, issuer_id="test-coordinator", signer=self.signer,
            clock_fn=self.clock,
        )
        provider_record = self.provider.activate_lease(
            self.SCOPE, fencing_attestation=proof
        )
        generation = self.store.read_control(self.SCOPE)[0]
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

    def test_end_to_end_activation_publish_and_revocation_use_durable_tokens(self):
        lease = self.acquire()
        activation = self.activate(lease)
        self.assertEqual(activation.state, "ACTIVE")
        self.assertEqual(activation.fencing_token, 1)

        publish = self.authority.allocate_operation_sequence(
            self.leader, lease, scope=self.SCOPE, idempotency_key="publish-1",
            manifest_key=f"{self.SCOPE}/staging/{activation.fencing_token}/manifest.json",
            manifest_sha256="a" * 64,
        )
        self.assertEqual(publish.operation_sequence, 1)
        proof = sign_distributed_fencing_proof(
            self.authority, self.leader, publish, lease, issuer_id="test-coordinator", signer=self.signer,
            clock_fn=self.clock,
        )
        receipt = self.provider.publish_commit(self.SCOPE, fencing_attestation=proof)
        generation = self.store.read_control(self.SCOPE)[0]
        committed = self.authority.confirm_publish(
            self.leader, scope=self.SCOPE, idempotency_key="publish-1",
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
            self.leader, lease, scope=self.SCOPE,
            fencing_token=activation.fencing_token, idempotency_key="revoke-1",
        )
        self.assertEqual(revoke.state, "REVOKING")
        revoke_proof = sign_distributed_fencing_proof(
            self.authority, self.leader, revoke, lease, issuer_id="test-coordinator", signer=self.signer,
            clock_fn=self.clock,
        )
        revoked_record = self.provider.revoke_lease(
            self.SCOPE, fencing_attestation=revoke_proof
        )
        generation = self.store.read_control(self.SCOPE)[0]
        revoked = self.authority.confirm_revocation(
            self.leader, scope=self.SCOPE, fencing_token=revoke.fencing_token,
            idempotency_key="revoke-1",
            observed_provider_state=revoked_record["lease_state"],
            observed_high_water_token=revoked_record["high_water_token"],
            observed_lease_id=revoked_record["lease_id"],
            provider_generation=generation,
        )
        self.assertEqual(revoked.state, "REVOKED")
        self.assertEqual(self.authority.snapshot(self.SCOPE)["lease_state"], "REVOKED")

    def test_token_and_sequence_survive_coordinator_reconstruction(self):
        lease = self.acquire("restart-1")
        first = self.activate(lease, "activate-restart-1")
        operation = self.authority.allocate_operation_sequence(
            self.leader, lease, scope=self.SCOPE, idempotency_key="publish-restart-1",
            manifest_key=f"{self.SCOPE}/manifest-1.json", manifest_sha256="1" * 64,
        )
        reopened = SQLiteDurableCoordinatorAuthority(self.database_path, clock_fn=self.clock)
        self.authority = reopened
        replay = reopened.allocate_operation_sequence(
            self.leader, lease, scope=self.SCOPE, idempotency_key="publish-restart-1",
            manifest_key=f"{self.SCOPE}/manifest-1.json", manifest_sha256="1" * 64,
        )
        self.assertEqual(replay.operation_sequence, operation.operation_sequence)
        self.assertEqual(replay.fencing_token, first.fencing_token)
        self.coordinator.release(lease)
        next_lease = self.acquire("restart-2")
        next_activation = reopened.prepare_activation(
            self.leader, next_lease, scope=self.SCOPE, idempotency_key="activate-restart-2"
        )
        self.assertGreater(next_activation.fencing_token, first.fencing_token)

    def test_activation_is_not_active_until_provider_confirmation(self):
        lease = self.acquire("pending-activation")
        pending = self.authority.prepare_activation(
            self.leader, lease, scope=self.SCOPE, idempotency_key="pending-activation"
        )
        self.assertEqual(self.authority.snapshot(self.SCOPE)["lease_state"], "PENDING_ACTIVATION")
        with self.assertRaises(CoordinatorAuthorityConflictError):
            self.authority.allocate_operation_sequence(
                self.leader, lease, scope=self.SCOPE, idempotency_key="too-early",
                manifest_key=f"{self.SCOPE}/manifest.json", manifest_sha256="2" * 64,
            )
        with self.assertRaises(CoordinatorAuthorityConflictError):
            self.authority.confirm_activation(
                self.leader, scope=self.SCOPE, fencing_token=pending.fencing_token,
                idempotency_key="pending-activation", observed_provider_state="ACTIVE",
                observed_high_water_token=pending.fencing_token + 1,
                observed_lease_id=lease.lease_id, provider_generation="gen-1",
            )
        self.assertEqual(self.authority.snapshot(self.SCOPE)["lease_state"], "PENDING_ACTIVATION")

    def test_activation_idempotency_and_conflicting_reuse(self):
        lease = self.acquire("activation-idem")
        first = self.authority.prepare_activation(
            self.leader, lease, scope=self.SCOPE, idempotency_key="activation-idem"
        )
        replay = self.authority.prepare_activation(
            self.leader, lease, scope=self.SCOPE, idempotency_key="activation-idem"
        )
        self.assertEqual(first.fencing_token, replay.fencing_token)
        self.assertEqual(first.request_sha256, replay.request_sha256)
        other_lease = self.acquire("activation-idem-other")
        with self.assertRaises(CoordinatorAuthorityConflictError):
            self.authority.prepare_activation(
                self.leader, other_lease, scope=self.SCOPE, idempotency_key="activation-idem"
            )

    def test_revocation_stays_revoke_pending_until_provider_readback(self):
        lease = self.acquire("revoke-pending")
        activation = self.activate(lease, "activate-revoke-pending")
        operation = self.authority.prepare_revocation(
            self.leader, lease, scope=self.SCOPE, fencing_token=activation.fencing_token,
            idempotency_key="revoke-pending",
        )
        self.assertEqual(operation.state, "REVOKING")
        self.assertEqual(self.authority.snapshot(self.SCOPE)["lease_state"], "REVOKING")
        with self.assertRaises(CoordinatorAuthorityConflictError):
            self.authority.allocate_operation_sequence(
                self.leader, lease, scope=self.SCOPE, idempotency_key="blocked-publish",
                manifest_key=f"{self.SCOPE}/manifest.json", manifest_sha256="3" * 64,
            )

    def test_operation_sequence_is_monotonic_and_idempotent(self):
        lease = self.acquire("sequence-idem")
        self.activate(lease, "activate-sequence-idem")
        kwargs = {
            "scope": self.SCOPE,
            "idempotency_key": "same-publish",
            "manifest_key": f"{self.SCOPE}/manifest-1.json",
            "manifest_sha256": "4" * 64,
        }
        first = self.authority.allocate_operation_sequence(self.leader, lease, **kwargs)
        replay = self.authority.allocate_operation_sequence(self.leader, lease, **kwargs)
        self.assertEqual(first.operation_sequence, 1)
        self.assertEqual(replay.operation_sequence, 1)
        with self.assertRaises(CoordinatorAuthorityConflictError):
            self.authority.allocate_operation_sequence(
                self.leader, lease, scope=self.SCOPE, idempotency_key="same-publish",
                manifest_key=f"{self.SCOPE}/different.json", manifest_sha256="5" * 64,
            )
        second = self.authority.allocate_operation_sequence(
            self.leader, lease, scope=self.SCOPE, idempotency_key="publish-2",
            manifest_key=f"{self.SCOPE}/manifest-2.json", manifest_sha256="6" * 64,
        )
        self.assertEqual(second.operation_sequence, 2)

    def test_parallel_sequence_allocations_are_unique_in_shared_local_database(self):
        lease = self.acquire("parallel-sequences")
        self.activate(lease, "activate-parallel")
        authorities = [
            SQLiteDurableCoordinatorAuthority(self.database_path, clock_fn=self.clock)
            for _ in range(4)
        ]

        def allocate(index):
            return authorities[index % len(authorities)].allocate_operation_sequence(
                self.leader, lease, scope=self.SCOPE, idempotency_key=f"parallel-{index}",
                manifest_key=f"{self.SCOPE}/manifest-{index}.json",
                manifest_sha256=f"{index + 10:064x}",
            ).operation_sequence

        with ThreadPoolExecutor(max_workers=8) as pool:
            sequences = list(pool.map(allocate, range(12)))
        self.assertEqual(sorted(sequences), list(range(1, 13)))

    def test_new_leader_epoch_fences_old_leader_after_expiry(self):
        lease = self.acquire("leader-failover")
        old_leader = self.leader
        self.clock.advance(31)
        reopened = SQLiteDurableCoordinatorAuthority(self.database_path, clock_fn=self.clock)
        new_leader = reopened.claim_leadership("leader-B-instance-1", ttl_seconds=30)
        self.assertGreater(new_leader.epoch, old_leader.epoch)
        with self.assertRaises(CoordinatorAuthorityStaleLeaderError):
            self.authority.prepare_activation(
                old_leader, lease, scope=self.SCOPE, idempotency_key="old-leader-write"
            )
        current = reopened.prepare_activation(
            new_leader, lease, scope=self.SCOPE, idempotency_key="new-leader-write"
        )
        self.assertGreater(current.fencing_token, 0)

    def test_recovery_lists_pending_activation_without_auto_promoting_it(self):
        lease = self.acquire("crash-before-confirm")
        operation = self.authority.prepare_activation(
            self.leader, lease, scope=self.SCOPE, idempotency_key="crash-before-confirm"
        )
        proof = sign_distributed_fencing_proof(
            self.authority, self.leader, operation, lease, issuer_id="test-coordinator", signer=self.signer,
            clock_fn=self.clock,
        )
        self.provider.activate_lease(self.SCOPE, fencing_attestation=proof)
        self.clock.advance(31)
        reopened = SQLiteDurableCoordinatorAuthority(self.database_path, clock_fn=self.clock)
        new_leader = reopened.claim_leadership("leader-after-crash", ttl_seconds=30)
        pending = reopened.list_pending_operations(new_leader, scope=self.SCOPE)
        self.assertEqual([item.state for item in pending], ["PENDING_ACTIVATION"])
        self.assertEqual(reopened.snapshot(self.SCOPE)["lease_state"], "PENDING_ACTIVATION")
        provider_record = self.provider.snapshot(self.SCOPE)
        generation = self.store.read_control(self.SCOPE)[0]
        confirmed = reopened.confirm_activation(
            new_leader, scope=self.SCOPE, fencing_token=operation.fencing_token,
            idempotency_key="crash-before-confirm",
            observed_provider_state=provider_record["lease_state"],
            observed_high_water_token=provider_record["high_water_token"],
            observed_lease_id=provider_record["lease_id"],
            provider_generation=generation,
        )
        self.assertEqual(confirmed.state, "ACTIVE")

    def test_old_leader_cannot_confirm_after_new_epoch_claim(self):
        lease = self.acquire("old-confirm")
        pending = self.authority.prepare_activation(
            self.leader, lease, scope=self.SCOPE, idempotency_key="old-confirm"
        )
        self.clock.advance(31)
        reopened = SQLiteDurableCoordinatorAuthority(self.database_path, clock_fn=self.clock)
        new_leader = reopened.claim_leadership("replacement-leader", ttl_seconds=30)
        with self.assertRaises(CoordinatorAuthorityStaleLeaderError):
            self.authority.confirm_activation(
                self.leader, scope=self.SCOPE, fencing_token=pending.fencing_token,
                idempotency_key="old-confirm", observed_provider_state="ACTIVE",
                observed_high_water_token=pending.fencing_token,
                observed_lease_id=lease.lease_id, provider_generation="provider-gen",
            )
        with self.assertRaises(CoordinatorAuthorityStaleLeaderError):
            sign_distributed_fencing_proof(
                self.authority, self.leader, pending, lease,
                issuer_id="test-coordinator", signer=self.signer, clock_fn=self.clock,
            )
        recovered_proof = sign_distributed_fencing_proof(
            reopened, new_leader, pending, lease,
            issuer_id="test-coordinator", signer=self.signer, clock_fn=self.clock,
        )
        provider_record = self.provider.activate_lease(
            self.SCOPE, fencing_attestation=recovered_proof
        )
        generation = self.store.read_control(self.SCOPE)[0]
        self.assertEqual(provider_record["lease_state"], "ACTIVE")
        confirmed = reopened.confirm_activation(
            new_leader, scope=self.SCOPE, fencing_token=pending.fencing_token,
            idempotency_key="old-confirm", observed_provider_state="ACTIVE",
            observed_high_water_token=pending.fencing_token,
            observed_lease_id=lease.lease_id, provider_generation=generation,
        )
        self.assertEqual(confirmed.state, "ACTIVE")
        self.assertEqual(new_leader.epoch, self.leader.epoch + 1)

    def test_restore_reconciliation_raises_token_and_sequence_floors_and_blocks_old_lease(self):
        lease = self.acquire("restore-floor")
        activation = self.activate(lease, "activate-restore-floor")
        report = self.authority.reconcile_after_restore(
            self.leader, scope=self.SCOPE, external_high_water_token=40,
            external_operation_sequence=9, reconciliation_ref="EXTERNAL-PROVIDER-READBACK-001",
        )
        self.assertFalse(report["automatic_cutover"])
        self.assertEqual(self.authority.snapshot(self.SCOPE)["lease_state"], "RECOVERY_REQUIRED")
        with self.assertRaises(CoordinatorAuthorityConflictError):
            self.authority.allocate_operation_sequence(
                self.leader, lease, scope=self.SCOPE, idempotency_key="restore-blocked",
                manifest_key=f"{self.SCOPE}/blocked.json", manifest_sha256="7" * 64,
            )
        self.coordinator.release(lease)
        next_lease = self.acquire("restore-new-lease")
        next_activation = self.authority.prepare_activation(
            self.leader, next_lease, scope=self.SCOPE, idempotency_key="activate-after-restore"
        )
        self.assertEqual(next_activation.fencing_token, 41)
        self.assertGreater(next_activation.fencing_token, activation.fencing_token)

    def test_restore_reconciliation_requires_external_floors_not_below_database(self):
        lease = self.acquire("restore-lower-floor")
        self.activate(lease, "activate-restore-lower")
        with self.assertRaises(CoordinatorAuthorityConflictError):
            self.authority.reconcile_after_restore(
                self.leader, scope=self.SCOPE, external_high_water_token=0,
                external_operation_sequence=0, reconciliation_ref="TOO-LOW",
            )
        with self.assertRaises(Exception):
            self.authority.reconcile_after_restore(
                self.leader, scope=self.SCOPE, external_high_water_token=10,
                external_operation_sequence=0, reconciliation_ref="",
            )

    def test_leadership_recovery_from_restored_database_requires_external_epoch_floor(self):
        self.clock.advance(31)
        restored = SQLiteDurableCoordinatorAuthority(self.database_path, clock_fn=self.clock)
        first = restored.claim_leadership("leader-before-backup", ttl_seconds=30)
        self.clock.advance(31)
        stale_backup = SQLiteDurableCoordinatorAuthority(self.database_path, clock_fn=self.clock)
        # The persisted epoch is lower than the externally reconciled recovery floor.
        replacement = stale_backup.claim_leadership(
            "leader-after-restore", ttl_seconds=30,
            recovery_epoch_floor=first.epoch + 5,
            reconciliation_ref="EXTERNAL-LEADER-EPOCH-REGISTER-006",
        )
        self.assertEqual(replacement.epoch, first.epoch + 5)
        with self.assertRaises(CoordinatorAuthorityStaleLeaderError):
            restored.snapshot(self.SCOPE)  # read-only snapshot remains available
            restored.renew_leadership(first, ttl_seconds=20)

    def test_signed_operation_proof_binds_token_sequence_and_manifest(self):
        lease = self.acquire("proof-bindings")
        self.activate(lease, "activate-proof-bindings")
        operation = self.authority.allocate_operation_sequence(
            self.leader, lease, scope=self.SCOPE, idempotency_key="proof-publish",
            manifest_key=f"{self.SCOPE}/manifest-proof.json", manifest_sha256="8" * 64,
        )
        proof = sign_distributed_fencing_proof(
            self.authority, self.leader, operation, lease, issuer_id="test-coordinator", signer=self.signer,
            clock_fn=self.clock,
        )
        claims, key_id = verify_fencing_attestation_signature(
            proof, trusted_ed25519_public_keys={"test-kid-v1": self.public_key}
        )
        self.assertEqual(key_id, "test-kid-v1")
        self.assertEqual(claims["fencing_token"], operation.fencing_token)
        self.assertEqual(claims["operation_sequence"], operation.operation_sequence)
        self.assertEqual(claims["manifest_key"], operation.manifest_key)
        self.assertEqual(claims["manifest_sha256"], operation.manifest_sha256)


if __name__ == "__main__":
    unittest.main()
