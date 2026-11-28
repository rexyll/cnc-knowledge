from __future__ import annotations

import hashlib
import tempfile
import threading
import unittest
from pathlib import Path

from scripts.spare_parts_provider_grant_floor import (
    ProviderGrantFloorConflict,
    ProviderGrantFloorRevisionRegression,
    ProviderGrantFloorScopeKey,
    ProviderGrantFloorError,
    SQLiteProviderGrantFloorAuthority,
)


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class SQLiteProviderGrantFloorAuthorityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ch17-provider-grant-floor-")
        self.base = Path(self.temp.name)
        self.database = self.base / "external-floor.sqlite"
        self.authority = SQLiteProviderGrantFloorAuthority(self.database)
        self.key = ProviderGrantFloorScopeKey(
            provider_id="provider-a", tenant_id="tenant-a",
            scope="cnc/ch17/backup-reference-001",
        )
        self.namespace = "/cnc/migration/isolated/provider-grant-test/"
        self.leader_id = "leader-a"
        self.lease_id = 1001
        self.lease_expiry = 2_000_000_000.0

    def tearDown(self):
        self.temp.cleanup()

    def reserve_fence(self, *, operation_id="fence-op-1", expected_revision=0,
                      grant_id="grant-a", command_digest=None, leader_epoch=1,
                      leader_id=None, lease_id=None, lease_expiry=None):
        return self.authority.reserve_fence(
            operation_id=operation_id,
            key=self.key,
            grant_id=grant_id,
            command_digest=command_digest or _digest(operation_id + "-command"),
            coordinator_namespace=self.namespace,
            leader_id=leader_id or self.leader_id,
            leader_epoch=leader_epoch,
            native_lease_id=lease_id or self.lease_id,
            lease_expires_at_unix=(
                self.lease_expiry if lease_expiry is None else lease_expiry
            ),
            expected_revision=expected_revision,
        )

    def confirm_fence(self, reservation):
        return self.authority.confirm_provider_receipt(
            operation_id=reservation.operation_id,
            command_digest=reservation.command_digest,
            provider_receipt_digest=_digest(reservation.operation_id + "-provider-receipt"),
            expected_revision=reservation.reserved_scope_revision,
        )

    def activate(self, *, operation_id="activate-op-1", expected_revision=None,
                 fence_command_digest=None, grant_id="grant-a"):
        snapshot = self.authority.snapshot(self.key)
        return self.authority.reserve_activate(
            operation_id=operation_id,
            key=self.key,
            grant_id=grant_id,
            command_digest=_digest(operation_id + "-command"),
            fence_command_digest=(
                fence_command_digest or snapshot.last_fence_command_digest
            ),
            coordinator_namespace=self.namespace,
            leader_id=self.leader_id,
            leader_epoch=1,
            native_lease_id=self.lease_id,
            lease_expires_at_unix=self.lease_expiry,
            expected_revision=(
                snapshot.revision if expected_revision is None else expected_revision
            ),
        )

    def test_fence_and_activate_advance_generation_and_confirm_exact_receipts(self):
        fence = self.reserve_fence()
        self.assertEqual(fence.generation, 1)
        self.assertEqual(fence.reserved_scope_revision, 1)
        self.assertEqual(self.authority.snapshot(self.key).state, "FENCE_PENDING")

        fenced = self.confirm_fence(fence)
        self.assertEqual(fenced.state, "FENCED")
        self.assertEqual(fenced.provider_generation_floor, 1)
        self.assertEqual(fenced.last_fence_command_digest, fence.command_digest)
        self.assertEqual(fenced.last_fence_receipt_digest, _digest("fence-op-1-provider-receipt"))

        activate = self.activate()
        self.assertEqual(activate.generation, 2)
        self.assertEqual(activate.fence_command_digest, fence.command_digest)
        self.assertEqual(self.authority.snapshot(self.key).state, "ACTIVATE_PENDING")

        active = self.authority.confirm_provider_receipt(
            operation_id=activate.operation_id,
            command_digest=activate.command_digest,
            provider_receipt_digest=_digest("activate-receipt"),
            expected_revision=activate.reserved_scope_revision,
        )
        self.assertEqual(active.state, "ACTIVE")
        self.assertEqual(active.provider_generation_floor, 2)
        self.assertEqual(active.last_activation_command_digest, activate.command_digest)
        self.assertEqual(active.last_activation_receipt_digest, _digest("activate-receipt"))

    def test_reservation_is_idempotent_by_exact_operation_identity(self):
        first = self.reserve_fence()
        replay = self.reserve_fence()
        self.assertEqual(first, replay)
        self.assertEqual(self.authority.snapshot(self.key).provider_generation_floor, 1)
        self.assertEqual(self.authority.operation_status(first.operation_id).state, "PENDING")

    def test_reusing_operation_id_with_different_command_is_rejected(self):
        first = self.reserve_fence()
        with self.assertRaisesRegex(ProviderGrantFloorConflict, "different Grant floor reservation"):
            self.reserve_fence(command_digest=_digest("different-command"))
        self.assertEqual(self.authority.snapshot(self.key).pending_operation_id, first.operation_id)

    def test_pending_operation_blocks_a_second_generation_reservation(self):
        self.reserve_fence()
        with self.assertRaisesRegex(ProviderGrantFloorConflict, "pending or recovery-required"):
            self.reserve_fence(operation_id="fence-op-2", expected_revision=1)
        self.assertEqual(self.authority.snapshot(self.key).provider_generation_floor, 1)

    def test_compare_and_swap_rejects_stale_scope_revision(self):
        self.reserve_fence()
        with self.assertRaisesRegex(ProviderGrantFloorConflict, "revision CAS failed"):
            self.reserve_fence(operation_id="fence-op-stale", expected_revision=0)
        self.assertEqual(self.authority.snapshot(self.key).revision, 1)

    def test_two_concurrent_reservations_with_same_revision_have_one_winner(self):
        barrier = threading.Barrier(2)
        successes = []
        errors = []

        def reserve(operation_id):
            try:
                barrier.wait(timeout=2.0)
                successes.append(self.reserve_fence(
                    operation_id=operation_id, expected_revision=0
                ))
            except Exception as exc:
                errors.append(exc)

        threads = [
            threading.Thread(target=reserve, args=("concurrent-a",)),
            threading.Thread(target=reserve, args=("concurrent-b",)),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=4.0)
        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertEqual(len(successes), 1)
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], ProviderGrantFloorConflict)
        self.assertEqual(self.authority.snapshot(self.key).provider_generation_floor, 1)

    def test_provider_receipt_requires_exact_operation_command_and_revision(self):
        reservation = self.reserve_fence()
        with self.assertRaisesRegex(ProviderGrantFloorConflict, "command digest"):
            self.authority.confirm_provider_receipt(
                operation_id=reservation.operation_id,
                command_digest=_digest("wrong-command"),
                provider_receipt_digest=_digest("receipt"),
                expected_revision=reservation.reserved_scope_revision,
            )
        with self.assertRaisesRegex(ProviderGrantFloorConflict, "revision CAS failed"):
            self.authority.confirm_provider_receipt(
                operation_id=reservation.operation_id,
                command_digest=reservation.command_digest,
                provider_receipt_digest=_digest("receipt"),
                expected_revision=0,
            )
        self.assertEqual(self.authority.snapshot(self.key).state, "FENCE_PENDING")

    def test_confirm_is_idempotent_only_for_the_same_provider_receipt(self):
        reservation = self.reserve_fence()
        receipt = _digest("provider-receipt")
        first = self.authority.confirm_provider_receipt(
            operation_id=reservation.operation_id,
            command_digest=reservation.command_digest,
            provider_receipt_digest=receipt,
            expected_revision=reservation.reserved_scope_revision,
        )
        replay = self.authority.confirm_provider_receipt(
            operation_id=reservation.operation_id,
            command_digest=reservation.command_digest,
            provider_receipt_digest=receipt,
            expected_revision=reservation.reserved_scope_revision,
        )
        self.assertEqual(replay.state, first.state)
        self.assertEqual(replay.revision, first.revision)
        with self.assertRaisesRegex(ProviderGrantFloorConflict, "cannot be replaced"):
            self.authority.confirm_provider_receipt(
                operation_id=reservation.operation_id,
                command_digest=reservation.command_digest,
                provider_receipt_digest=_digest("different-receipt"),
                expected_revision=reservation.reserved_scope_revision,
            )

    def test_unknown_reservation_outcome_is_recovered_by_operation_id_after_restart(self):
        reservation = self.reserve_fence()
        reopened = SQLiteProviderGrantFloorAuthority(self.database)
        status = reopened.operation_status(reservation.operation_id)
        self.assertIsNotNone(status)
        self.assertEqual(status.state, "PENDING")
        self.assertEqual(status.command_digest, reservation.command_digest)
        self.assertEqual(status.generation, reservation.generation)
        self.assertEqual(
            reopened.snapshot(self.key).pending_command_digest,
            reservation.command_digest,
        )

    def test_unknown_provider_commit_is_confirmed_without_allocating_new_generation(self):
        reservation = self.reserve_fence()
        # Simulate a lost Provider response: the exact receipt is looked up later.
        recovered = self.confirm_fence(reservation)
        generation_before_replay = recovered.provider_generation_floor
        self.authority.confirm_provider_receipt(
            operation_id=reservation.operation_id,
            command_digest=reservation.command_digest,
            provider_receipt_digest=_digest(reservation.operation_id + "-provider-receipt"),
            expected_revision=reservation.reserved_scope_revision,
        )
        self.assertEqual(
            self.authority.snapshot(self.key).provider_generation_floor,
            generation_before_replay,
        )

    def test_activate_requires_confirmed_fence_and_exact_fence_digest(self):
        self.reserve_fence()
        with self.assertRaisesRegex(ProviderGrantFloorConflict, "requires a confirmed FENCED"):
            self.activate(operation_id="activate-before-fence")
        fence = self.authority.operation_status("fence-op-1")
        self.assertEqual(fence.state, "PENDING")

        self.confirm_fence(self.reserve_fence())
        with self.assertRaisesRegex(ProviderGrantFloorConflict, "latest confirmed FENCE"):
            self.activate(
                operation_id="activate-wrong-fence",
                fence_command_digest=_digest("not-the-fence"),
            )
        self.assertEqual(self.authority.snapshot(self.key).state, "FENCED")

    def test_leader_epoch_is_monotonic_and_same_epoch_identity_is_immutable(self):
        fence = self.reserve_fence()
        self.confirm_fence(fence)
        activate = self.activate()
        self.authority.confirm_provider_receipt(
            operation_id=activate.operation_id,
            command_digest=activate.command_digest,
            provider_receipt_digest=_digest("activate-receipt"),
            expected_revision=activate.reserved_scope_revision,
        )
        active = self.authority.snapshot(self.key)
        newer_fence = self.reserve_fence(
            operation_id="newer-epoch-fence-for-regression",
            expected_revision=active.revision,
            leader_epoch=2,
            leader_id="leader-b",
            lease_id=2002,
            lease_expiry=self.lease_expiry + 100.0,
        )
        self.confirm_fence(newer_fence)
        fenced = self.authority.snapshot(self.key)
        newer_activate = self.authority.reserve_activate(
            operation_id="newer-epoch-activate",
            key=self.key,
            grant_id="grant-a",
            command_digest=_digest("newer-epoch-activate-command"),
            fence_command_digest=newer_fence.command_digest,
            coordinator_namespace=self.namespace,
            leader_id="leader-b",
            leader_epoch=2,
            native_lease_id=2002,
            lease_expires_at_unix=self.lease_expiry + 100.0,
            expected_revision=fenced.revision,
        )
        self.authority.confirm_provider_receipt(
            operation_id=newer_activate.operation_id,
            command_digest=newer_activate.command_digest,
            provider_receipt_digest=_digest("newer-epoch-activate-receipt"),
            expected_revision=newer_activate.reserved_scope_revision,
        )
        current = self.authority.snapshot(self.key)

        with self.assertRaisesRegex(ProviderGrantFloorConflict, "below the external floor"):
            self.reserve_fence(
                operation_id="old-epoch-fence",
                expected_revision=current.revision,
                leader_epoch=1,
                leader_id="leader-a",
                lease_id=1001,
            )
        with self.assertRaisesRegex(ProviderGrantFloorConflict, "same Leader epoch"):
            self.reserve_fence(
                operation_id="same-epoch-new-leader",
                expected_revision=current.revision,
                leader_epoch=2,
                leader_id="leader-substitute",
                lease_id=2003,
                lease_expiry=self.lease_expiry + 100.0,
            )
        self.assertEqual(self.authority.snapshot(self.key).state, "ACTIVE")

    def test_coordinator_namespace_cannot_change_even_with_a_newer_leader_epoch(self):
        fence = self.reserve_fence()
        self.confirm_fence(fence)
        activate = self.activate()
        active = self.authority.confirm_provider_receipt(
            operation_id=activate.operation_id,
            command_digest=activate.command_digest,
            provider_receipt_digest=_digest("activate-receipt"),
            expected_revision=activate.reserved_scope_revision,
        )
        with self.assertRaisesRegex(ProviderGrantFloorConflict, "namespace is immutable"):
            self.authority.reserve_fence(
                operation_id="namespace-change",
                key=self.key,
                grant_id="grant-a",
                command_digest=_digest("namespace-change-command"),
                coordinator_namespace="/cnc/migration/other-namespace/",
                leader_id="leader-b",
                leader_epoch=2,
                native_lease_id=2002,
                lease_expires_at_unix=self.lease_expiry + 100.0,
                expected_revision=active.revision,
            )

    def test_activate_native_lease_expiry_cannot_regress_below_fence_snapshot(self):
        fence = self.reserve_fence()
        self.confirm_fence(fence)
        snapshot = self.authority.snapshot(self.key)
        with self.assertRaisesRegex(ProviderGrantFloorConflict, "expiry cannot regress"):
            self.authority.reserve_activate(
                operation_id="activate-lease-regression",
                key=self.key,
                grant_id="grant-a",
                command_digest=_digest("activate-lease-regression-command"),
                fence_command_digest=fence.command_digest,
                coordinator_namespace=self.namespace,
                leader_id=self.leader_id,
                leader_epoch=1,
                native_lease_id=self.lease_id,
                lease_expires_at_unix=self.lease_expiry - 1.0,
                expected_revision=snapshot.revision,
            )

    def test_same_leader_native_lease_expiry_cannot_regress_on_fence(self):
        fence = self.reserve_fence()
        self.confirm_fence(fence)
        activate = self.activate()
        self.authority.confirm_provider_receipt(
            operation_id=activate.operation_id,
            command_digest=activate.command_digest,
            provider_receipt_digest=_digest("activate-receipt"),
            expected_revision=activate.reserved_scope_revision,
        )
        active = self.authority.snapshot(self.key)
        with self.assertRaisesRegex(ProviderGrantFloorConflict, "expiry cannot regress"):
            self.reserve_fence(
                operation_id="regressed-lease-fence",
                expected_revision=active.revision,
                lease_expiry=self.lease_expiry - 1.0,
            )

    def test_newer_leader_epoch_can_fence_and_advance_floor(self):
        first = self.reserve_fence()
        self.confirm_fence(first)
        activate = self.activate()
        self.authority.confirm_provider_receipt(
            operation_id=activate.operation_id,
            command_digest=activate.command_digest,
            provider_receipt_digest=_digest("activate-receipt"),
            expected_revision=activate.reserved_scope_revision,
        )
        active = self.authority.snapshot(self.key)
        newer = self.reserve_fence(
            operation_id="new-epoch-fence",
            expected_revision=active.revision,
            leader_epoch=2,
            leader_id="leader-b",
            lease_id=2002,
            lease_expiry=self.lease_expiry + 100.0,
        )
        self.assertEqual(newer.generation, 3)
        self.assertEqual(self.authority.snapshot(self.key).coordinator_epoch_floor, 2)
        self.assertEqual(self.authority.snapshot(self.key).state, "FENCE_PENDING")

    def test_provider_tenant_and_scope_are_independent_floor_keys(self):
        first = self.reserve_fence()
        self.confirm_fence(first)
        other = ProviderGrantScopeKey(
            provider_id="provider-b", tenant_id="tenant-a",
            scope="cnc/ch17/backup-reference-001",
        )
        other_snapshot = self.authority.snapshot(other)
        self.assertEqual(other_snapshot.provider_generation_floor, 0)
        self.assertEqual(other_snapshot.revision, 0)
        tenant_key = ProviderGrantScopeKey(
            provider_id="provider-a", tenant_id="tenant-b",
            scope="cnc/ch17/backup-reference-001",
        )
        self.assertEqual(self.authority.snapshot(tenant_key).state, "IDLE")

    def test_trusted_minimum_revision_detects_a_regressed_snapshot(self):
        reservation = self.reserve_fence()
        self.confirm_fence(reservation)
        with self.assertRaises(ProviderGrantFloorRevisionRegression):
            self.authority.snapshot(self.key, minimum_revision=99)
        self.assertEqual(self.authority.snapshot(self.key, minimum_revision=2).revision, 2)

    def test_database_permissions_are_restricted(self):
        self.assertEqual(self.database.stat().st_mode & 0o777, 0o600)

    def test_invalid_scope_namespace_and_digest_are_rejected(self):
        with self.assertRaises(ProviderGrantFloorError):
            ProviderGrantFloorScopeKey("provider-a", "tenant-a", "cnc/../scope")
        with self.assertRaisesRegex(ProviderGrantFloorError, "namespace"):
            self.authority.reserve_fence(
                operation_id="bad-namespace", key=self.key, grant_id="grant-a",
                command_digest=_digest("bad"), coordinator_namespace="/cnc//bad/",
                leader_id=self.leader_id, leader_epoch=1, native_lease_id=1,
                lease_expires_at_unix=self.lease_expiry, expected_revision=0,
            )
        with self.assertRaisesRegex(ProviderGrantFloorError, "SHA-256"):
            self.authority.reserve_fence(
                operation_id="bad-digest", key=self.key, grant_id="grant-a",
                command_digest="not-a-digest", coordinator_namespace=self.namespace,
                leader_id=self.leader_id, leader_epoch=1, native_lease_id=1,
                lease_expires_at_unix=self.lease_expiry, expected_revision=0,
            )


if __name__ == "__main__":
    unittest.main()
