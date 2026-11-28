from __future__ import annotations

import hashlib
import sqlite3
import tempfile
import threading
import time
import unittest
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from scripts.spare_parts_provider_grant_receipt import (
    CLAIMS_FORMAT as RECEIPT_CLAIMS_FORMAT,
    canonical_receipt_json,
    sign_provider_grant_receipt,
)

from scripts.spare_parts_provider_grant_floor import (
    ProviderGrantFloorConflict,
    ProviderGrantFloorRevisionRegression,
    ProviderGrantScopeKey,
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
        self.receipt_signer = Ed25519PrivateKey.generate()
        self.receipt_public_key = self.receipt_signer.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        )
        self.authority.admin_register_provider_receipt_key(
            provider_id="provider-a",
            key_id="provider-receipt-a",
            public_key=self.receipt_public_key,
            not_before=time.time() - 60.0,
        )
        self._receipt_tick = 0.0
        self.last_receipts = {}
        self.key = ProviderGrantScopeKey(
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


    def receipt_envelope(self, reservation, **overrides):
        self._receipt_tick += 0.25
        issued = time.time() + self._receipt_tick
        claims = {
            "format": RECEIPT_CLAIMS_FORMAT,
            "provider_id": reservation.key.provider_id,
            "tenant_id": reservation.key.tenant_id,
            "scope": reservation.key.scope,
            "action": reservation.action,
            "grant_id": reservation.grant_id,
            "generation": reservation.generation,
            "command_sha256": reservation.command_digest,
            "fence_command_sha256": reservation.fence_command_digest,
            "result_state": "FENCED" if reservation.action == "FENCE" else "ACTIVE",
            "coordinator_namespace": reservation.coordinator_namespace,
            "leader_id": reservation.leader_id,
            "leader_epoch": reservation.leader_epoch,
            "native_lease_id": reservation.native_lease_id,
            "native_lease_expires_at_unix": reservation.lease_expires_at_unix,
            "command_issued_at_unix": issued,
            "command_expires_at_unix": issued + 30.0,
            "applied_at_unix": issued + 0.1,
        }
        claims.update(overrides)
        return sign_provider_grant_receipt(
            claims, key_id="provider-receipt-a", private_key=self.receipt_signer
        )

    def confirm_receipt(self, reservation, receipt_envelope=None, *, expected_revision=None, **overrides):
        envelope = receipt_envelope or self.receipt_envelope(reservation, **overrides)
        self.last_receipts[reservation.operation_id] = envelope
        return self.authority.confirm_provider_receipt(
            operation_id=reservation.operation_id,
            receipt_envelope=envelope,
            expected_revision=(
                reservation.reserved_scope_revision
                if expected_revision is None else expected_revision
            ),
        )

    def confirm_fence(self, reservation):
        return self.confirm_receipt(reservation)

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
        self.assertEqual(
            fenced.last_fence_receipt_digest,
            hashlib.sha256(canonical_receipt_json(self.last_receipts[fence.operation_id])).hexdigest(),
        )

        activate = self.activate()
        self.assertEqual(activate.generation, 2)
        self.assertEqual(activate.fence_command_digest, fence.command_digest)
        self.assertEqual(self.authority.snapshot(self.key).state, "ACTIVATE_PENDING")

        active = self.confirm_receipt(activate)
        self.assertEqual(active.state, "ACTIVE")
        self.assertEqual(active.provider_generation_floor, 2)
        self.assertEqual(active.last_activation_command_digest, activate.command_digest)
        self.assertEqual(
            active.last_activation_receipt_digest,
            hashlib.sha256(canonical_receipt_json(self.last_receipts[activate.operation_id])).hexdigest(),
        )

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
        wrong_command_receipt = self.receipt_envelope(
            reservation, command_sha256=_digest("wrong-command")
        )
        with self.assertRaisesRegex(ProviderGrantFloorConflict, "command digest"):
            self.confirm_receipt(reservation, wrong_command_receipt)
        valid_receipt = self.receipt_envelope(reservation)
        with self.assertRaisesRegex(ProviderGrantFloorConflict, "revision CAS failed"):
            self.confirm_receipt(reservation, valid_receipt, expected_revision=0)
        self.assertEqual(self.authority.snapshot(self.key).state, "FENCE_PENDING")

    def test_confirm_is_idempotent_only_for_the_same_provider_receipt(self):
        reservation = self.reserve_fence()
        receipt = self.receipt_envelope(reservation)
        first = self.confirm_receipt(reservation, receipt)
        replay = self.confirm_receipt(reservation, receipt)
        self.assertEqual(replay.state, first.state)
        self.assertEqual(replay.revision, first.revision)
        different_receipt = self.receipt_envelope(reservation)
        with self.assertRaisesRegex(ProviderGrantFloorConflict, "cannot be replaced"):
            self.confirm_receipt(reservation, different_receipt)

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
        self.confirm_receipt(
            reservation, self.last_receipts[reservation.operation_id]
        )
        self.assertEqual(
            self.authority.snapshot(self.key).provider_generation_floor,
            generation_before_replay,
        )

    def test_activate_requires_confirmed_fence_and_exact_fence_digest(self):
        self.reserve_fence()
        with self.assertRaisesRegex(ProviderGrantFloorConflict, "pending or recovery-required"):
            self.activate(
                operation_id="activate-before-fence",
                fence_command_digest=_digest("unconfirmed-fence"),
            )
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
        self.confirm_receipt(activate)
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
        self.confirm_receipt(newer_activate)
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
        active = self.confirm_receipt(activate)
        with self.assertRaisesRegex(ProviderGrantFloorConflict, "namespace is immutable"):
            self.authority.reserve_fence(
                operation_id="namespace-change",
                key=self.key,
                grant_id="grant-a",
                command_digest=_digest("namespace-change-command"),
                coordinator_namespace="/cnc/migration/isolated/other-namespace/",
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
        self.confirm_receipt(activate)
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
        self.confirm_receipt(activate)
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


    def test_floor_persists_verified_receipt_signer_and_trust_metadata(self):
        reservation = self.reserve_fence()
        receipt = self.receipt_envelope(reservation)
        applied_at = receipt["receipt"]["applied_at_unix"]
        self.confirm_receipt(reservation, receipt)
        operation = self.authority.operation_status(reservation.operation_id)
        self.assertEqual(operation.receipt_signer_key_id, "provider-receipt-a")
        self.assertEqual(
            operation.receipt_key_fingerprint,
            hashlib.sha256(self.receipt_public_key).hexdigest(),
        )
        self.assertEqual(operation.receipt_trust_revision, 1)
        self.assertEqual(operation.provider_applied_at_unix, applied_at)

    def test_unknown_provider_receipt_key_is_rejected_without_advancing_floor(self):
        reservation = self.reserve_fence()
        receipt = self.receipt_envelope(reservation)
        receipt["signature"]["key_id"] = "unknown-provider-key"
        before = self.authority.snapshot(self.key)
        with self.assertRaisesRegex(ProviderGrantFloorConflict, "not trusted"):
            self.confirm_receipt(reservation, receipt)
        after = self.authority.snapshot(self.key)
        self.assertEqual(after.state, "FENCE_PENDING")
        self.assertEqual(after.revision, before.revision)
        self.assertEqual(after.authority_revision, before.authority_revision)

    def test_receipt_claim_provider_identity_mismatch_is_rejected_without_floor_advance(self):
        reservation = self.reserve_fence()
        receipt = self.receipt_envelope(reservation, provider_id="provider-other")
        before = self.authority.snapshot(self.key)
        with self.assertRaisesRegex(ProviderGrantFloorConflict, "signer identity"):
            self.confirm_receipt(reservation, receipt)
        after = self.authority.snapshot(self.key)
        self.assertEqual(after.state, "FENCE_PENDING")
        self.assertEqual(after.revision, before.revision)
        self.assertEqual(after.authority_revision, before.authority_revision)

    def test_retiring_provider_key_accepts_pre_retirement_receipt_but_rejects_new_receipts(self):
        reservation = self.reserve_fence()
        now = time.time()
        old_receipt = self.receipt_envelope(
            reservation,
            command_issued_at_unix=now - 2.0,
            command_expires_at_unix=now + 20.0,
            applied_at_unix=now - 1.0,
        )
        retired = self.authority.admin_set_provider_receipt_key_status(
            provider_id="provider-a", key_id="provider-receipt-a", status="RETIRING"
        )
        self.assertGreater(retired["trust_revision"], 1)
        self.confirm_receipt(reservation, old_receipt)
        self.assertEqual(self.authority.snapshot(self.key).state, "FENCED")

        next_reservation = self.reserve_fence(
            operation_id="retiring-key-new-receipt",
            expected_revision=self.authority.snapshot(self.key).revision,
            leader_epoch=2, leader_id="leader-b", lease_id=2002,
            lease_expiry=self.lease_expiry + 100.0,
        )
        retirement_time = retired["retiring_effective_at"]
        after_retirement = max(time.time(), retirement_time + 0.1)
        new_receipt = self.receipt_envelope(
            next_reservation,
            command_issued_at_unix=after_retirement - 0.2,
            command_expires_at_unix=after_retirement + 30.0,
            applied_at_unix=after_retirement - 0.1,
        )
        with self.assertRaisesRegex(ProviderGrantFloorConflict, "stopped issuing"):
            self.confirm_receipt(next_reservation, new_receipt)
        self.assertEqual(self.authority.snapshot(self.key).state, "FENCE_PENDING")

    def test_revoked_provider_key_rejects_post_revocation_receipt_without_floor_advance(self):
        reservation = self.reserve_fence()
        revoked = self.authority.admin_set_provider_receipt_key_status(
            provider_id="provider-a",
            key_id="provider-receipt-a",
            status="REVOKED",
            revocation_effective_at=time.time() - 1.0,
            revocation_reason="synthetic key compromise test",
        )
        receipt = self.receipt_envelope(
            reservation,
            command_issued_at_unix=revoked["revocation_effective_at"] + 0.1,
            command_expires_at_unix=revoked["revocation_effective_at"] + 30.0,
            applied_at_unix=revoked["revocation_effective_at"] + 0.2,
        )
        with self.assertRaisesRegex(ProviderGrantFloorConflict, "stopped issuing"):
            self.confirm_receipt(reservation, receipt)
        self.assertEqual(self.authority.snapshot(self.key).state, "FENCE_PENDING")

    def test_schema_v1_migration_preserves_unverified_legacy_digest_without_trusting_it(self):
        legacy_path = self.base / "legacy-floor-v1.sqlite"
        connection = sqlite3.connect(legacy_path)
        try:
            connection.executescript(
                """
                CREATE TABLE provider_grant_floor_meta (
                    singleton INTEGER PRIMARY KEY CHECK(singleton=1),
                    schema_version INTEGER NOT NULL,
                    authority_revision INTEGER NOT NULL
                );
                INSERT INTO provider_grant_floor_meta(singleton,schema_version,authority_revision)
                VALUES(1,1,7);
                CREATE TABLE provider_grant_floor_operations (
                    operation_id TEXT PRIMARY KEY,
                    provider_id TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    action TEXT NOT NULL,
                    grant_id TEXT NOT NULL,
                    generation INTEGER NOT NULL,
                    command_digest TEXT NOT NULL,
                    fence_command_digest TEXT,
                    coordinator_namespace TEXT NOT NULL,
                    leader_id TEXT NOT NULL,
                    leader_epoch INTEGER NOT NULL,
                    native_lease_id INTEGER NOT NULL,
                    lease_expires_at_unix REAL NOT NULL,
                    state TEXT NOT NULL,
                    provider_receipt_digest TEXT,
                    reserved_scope_revision INTEGER NOT NULL,
                    confirmed_scope_revision INTEGER,
                    authority_revision INTEGER NOT NULL
                );
                """
            )
            connection.execute(
                """INSERT INTO provider_grant_floor_operations(
                    operation_id,provider_id,tenant_id,scope,action,grant_id,generation,
                    command_digest,fence_command_digest,coordinator_namespace,leader_id,
                    leader_epoch,native_lease_id,lease_expires_at_unix,state,
                    provider_receipt_digest,reserved_scope_revision,confirmed_scope_revision,
                    authority_revision
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    "legacy-confirmed-op","provider-a","tenant-a","cnc/ch17/backup-reference-001",
                    "FENCE","grant-legacy",1,_digest("legacy-command"),None,self.namespace,
                    self.leader_id,1,self.lease_id,self.lease_expiry,"CONFIRMED",
                    _digest("legacy-unverified-receipt"),1,2,7,
                ),
            )
            connection.commit()
        finally:
            connection.close()

        migrated = SQLiteProviderGrantFloorAuthority(legacy_path)
        operation = migrated.operation_status("legacy-confirmed-op")
        self.assertEqual(operation.state, "CONFIRMED")
        self.assertEqual(operation.provider_receipt_digest, _digest("legacy-unverified-receipt"))
        self.assertIsNone(operation.receipt_signer_key_id)
        self.assertIsNone(operation.receipt_key_fingerprint)
        self.assertIsNone(operation.receipt_trust_revision)
        self.assertIsNone(operation.provider_applied_at_unix)
        with sqlite3.connect(legacy_path) as check:
            version = check.execute(
                "SELECT schema_version FROM provider_grant_floor_meta WHERE singleton=1"
            ).fetchone()[0]
            trust_revision = check.execute(
                "SELECT trust_revision FROM provider_grant_floor_meta WHERE singleton=1"
            ).fetchone()[0]
        self.assertEqual(version, 3)
        self.assertEqual(trust_revision, 0)

    def test_database_permissions_are_restricted(self):
        self.assertEqual(self.database.stat().st_mode & 0o777, 0o600)

    def test_invalid_scope_namespace_and_digest_are_rejected(self):
        with self.assertRaises(ProviderGrantFloorError):
            ProviderGrantScopeKey("provider-a", "tenant-a", "cnc/../scope")
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


    def test_namespace_must_be_a_single_isolated_migration_scope(self):
        invalid_namespaces = (
            "/cnc/migration/unified/",
            "/cnc/unified/schema-v2/",
            "/cnc/migration/isolated/",
            "/cnc/migration/isolated/provider-grant-test/extra/",
            "/cnc/migration/isolated/../",
            "/cnc/migration/isolated/%2e%2e/",
            r"/cnc/migration/isolated/provider-grant-test\\",
        )
        for index, namespace in enumerate(invalid_namespaces):
            with self.subTest(namespace=namespace):
                with self.assertRaisesRegex(ProviderGrantFloorError, "isolated"):
                    self.authority.reserve_fence(
                        operation_id=f"bad-isolated-namespace-{index}",
                        key=self.key,
                        grant_id="grant-a",
                        command_digest=_digest(f"bad-isolated-namespace-{index}"),
                        coordinator_namespace=namespace,
                        leader_id=self.leader_id,
                        leader_epoch=1,
                        native_lease_id=self.lease_id,
                        lease_expires_at_unix=self.lease_expiry,
                        expected_revision=0,
                    )
                snapshot = self.authority.snapshot(self.key)
                self.assertEqual(snapshot.state, "IDLE")
                self.assertEqual(snapshot.revision, 0)
                self.assertEqual(snapshot.authority_revision, 0)


if __name__ == "__main__":
    unittest.main()
