from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from scripts.spare_parts_provider_grant_floor import (
    ProviderGrantFloorError,
    ProviderGrantScopeKey,
    SQLiteProviderGrantFloorAuthority,
)
from scripts.spare_parts_provider_grant_floor_checkpoint import (
    CheckpointedSQLiteProviderGrantFloorAuthority,
    InMemoryProviderGrantFloorCheckpointStore,
    ProviderGrantFloorCheckpoint,
    ProviderGrantFloorCheckpointBootstrapDenied,
    ProviderGrantFloorCheckpointMismatch,
    ProviderGrantFloorCheckpointMissing,
    ProviderGrantFloorCheckpointUncertain,
)
from scripts.spare_parts_provider_grant_receipt import (
    CLAIMS_FORMAT as RECEIPT_CLAIMS_FORMAT,
    sign_provider_grant_receipt,
)
from scripts.spare_parts_provider_revocable_grant import (
    CLAIMS_FORMAT as COMMAND_CLAIMS_FORMAT,
    sign_provider_grant_command,
)


def _raw_public_key(private_key: Ed25519PrivateKey) -> bytes:
    return private_key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )


def _command_digest(envelope: dict) -> str:
    encoded = json.dumps(
        envelope, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class _LoseNextCheckpointResponse(InMemoryProviderGrantFloorCheckpointStore):
    def __init__(self) -> None:
        super().__init__()
        self.lose_next_response = False

    def compare_and_set(self, **kwargs) -> ProviderGrantFloorCheckpoint:
        result = super().compare_and_set(**kwargs)
        if self.lose_next_response:
            self.lose_next_response = False
            raise OSError("simulated response loss after checkpoint commit")
        return result


class _FailNextCheckpointWrite(InMemoryProviderGrantFloorCheckpointStore):
    def __init__(self) -> None:
        super().__init__()
        self.fail_next_write = False

    def compare_and_set(self, **kwargs) -> ProviderGrantFloorCheckpoint:
        if self.fail_next_write:
            self.fail_next_write = False
            raise OSError("simulated checkpoint backend outage before commit")
        return super().compare_and_set(**kwargs)


class _ConflictNextCheckpointWrite(InMemoryProviderGrantFloorCheckpointStore):
    def __init__(self) -> None:
        super().__init__()
        self.conflict_next_write = False

    def compare_and_set(self, **kwargs) -> ProviderGrantFloorCheckpoint:
        if self.conflict_next_write:
            self.conflict_next_write = False
            current = self.read_checkpoint()
            if current is None:
                raise OSError("simulated unexpected empty checkpoint")
            self._checkpoint = ProviderGrantFloorCheckpoint(
                sequence=current.sequence + 1,
                authority_revision=current.authority_revision,
                state_sha256="f" * 64,
            )
            raise OSError("simulated competing checkpoint CAS writer")
        return super().compare_and_set(**kwargs)


class _WrongNextCheckpointResponse(InMemoryProviderGrantFloorCheckpointStore):
    def __init__(self) -> None:
        super().__init__()
        self.misreport_next_response = False

    def compare_and_set(self, **kwargs) -> ProviderGrantFloorCheckpoint:
        result = super().compare_and_set(**kwargs)
        if self.misreport_next_response:
            self.misreport_next_response = False
            return ProviderGrantFloorCheckpoint(
                sequence=result.sequence,
                authority_revision=result.authority_revision,
                state_sha256="0" * 64,
            )
        return result


class CheckpointedProviderGrantFloorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="ch17-floor-checkpoint-")
        self.root = Path(self.temp.name)
        self.database = self.root / "floor.sqlite"
        self.authority = SQLiteProviderGrantFloorAuthority(self.database)
        self.store = InMemoryProviderGrantFloorCheckpointStore()
        self.floor = CheckpointedSQLiteProviderGrantFloorAuthority(
            self.authority, self.store
        )
        self.initial = self.floor.bootstrap_empty_floor()
        self.key = ProviderGrantScopeKey(
            provider_id="provider-checkpoint-a",
            tenant_id="tenant-checkpoint-a",
            scope="cnc/ch17/checkpoint-reference",
        )
        self.namespace = "/cnc/migration/isolated/checkpoint-test/"
        self.lease_expiry = time.time() + 600.0
        self.coordinator_signer = Ed25519PrivateKey.generate()
        self.receipt_signer = Ed25519PrivateKey.generate()
        self.coordinator_key_id = "coordinator-checkpoint-key"
        self.receipt_key_id = "provider-checkpoint-receipt-key"
        self.issuer_id = "coordinator-checkpoint"
        self.floor.admin_register_coordinator_command_key(
            issuer_id=self.issuer_id,
            key_id=self.coordinator_key_id,
            public_key=_raw_public_key(self.coordinator_signer),
            not_before=time.time() - 60.0,
        )
        self.floor.admin_register_provider_receipt_key(
            provider_id=self.key.provider_id,
            key_id=self.receipt_key_id,
            public_key=_raw_public_key(self.receipt_signer),
            not_before=time.time() - 60.0,
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _command(
        self,
        action: str,
        generation: int,
        *,
        issued_at: float | None = None,
        fence_digest: str | None = None,
    ) -> dict:
        issued = time.time() - 1.0 if issued_at is None else issued_at
        claims = {
            "format": COMMAND_CLAIMS_FORMAT,
            "issuer_id": self.issuer_id,
            "provider_id": self.key.provider_id,
            "tenant_id": self.key.tenant_id,
            "scope": self.key.scope,
            "action": action,
            "grant_id": "grant-checkpoint-a",
            "generation": generation,
            "issued_at_unix": issued,
            "expires_at_unix": issued + 30.0,
            "coordinator_namespace": self.namespace,
            "leader_id": "leader-checkpoint-a",
            "leader_epoch": 1,
            "leader_lease_id": 321,
            "leader_lease_expires_at_unix": self.lease_expiry,
            "fence_command_sha256": fence_digest,
        }
        return sign_provider_grant_command(
            claims,
            key_id=self.coordinator_key_id,
            private_key=self.coordinator_signer,
        )

    def _receipt(self, reservation, *, applied_at: float):
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
            "command_issued_at_unix": reservation.command_issued_at_unix,
            "command_expires_at_unix": reservation.command_expires_at_unix,
            "applied_at_unix": applied_at,
        }
        return sign_provider_grant_receipt(
            claims, key_id=self.receipt_key_id, private_key=self.receipt_signer
        )

    def test_bootstrap_and_key_registry_changes_advance_external_checkpoint(self):
        first = self.initial
        self.assertEqual(first.sequence, 1)
        self.assertEqual(first.authority_revision, 0)

        # setUp registers two independent trust keys after the explicit
        # bootstrap; each durable trust-registry mutation must advance the
        # external checkpoint even though authority_revision remains zero.
        after_keys = self.floor.verify_checkpoint()
        self.assertEqual(after_keys.sequence, first.sequence + 2)
        self.assertEqual(self.store.read_checkpoint(), after_keys)
        self.assertEqual(after_keys.authority_revision, 0)
        self.assertNotEqual(after_keys.state_sha256, first.state_sha256)

    def test_normal_fence_activate_lifecycle_is_anchored_after_each_write(self):
        fence_issued = time.time() - 2.0
        fence_command = self._command("FENCE", 1, issued_at=fence_issued)
        fence = self.floor.reserve_fence_from_command(
            operation_id="checkpoint-fence-op",
            key=self.key,
            command_envelope=fence_command,
            expected_revision=0,
        )
        fence_applied = fence_issued + 0.25
        fenced = self.floor.confirm_provider_receipt(
            operation_id=fence.operation_id,
            receipt_envelope=self._receipt(fence, applied_at=fence_applied),
            expected_revision=fence.reserved_scope_revision,
        )
        self.assertEqual(fenced.state, "FENCED")
        self.floor.verify_checkpoint()

        activate_issued = fence_applied + 1.0
        activate_command = self._command(
            "ACTIVATE", 2, issued_at=activate_issued,
            fence_digest=fence.command_digest,
        )
        activate = self.floor.reserve_activate_from_command(
            operation_id="checkpoint-activate-op",
            key=self.key,
            command_envelope=activate_command,
            expected_revision=fenced.revision,
        )
        active = self.floor.confirm_provider_receipt(
            operation_id=activate.operation_id,
            receipt_envelope=self._receipt(
                activate, applied_at=activate_issued + 0.25
            ),
            expected_revision=activate.reserved_scope_revision,
        )
        self.assertEqual(active.state, "ACTIVE")
        self.assertEqual(active.provider_generation_floor, 2)
        self.assertEqual(
            self.floor.operation_status(activate.operation_id).state, "CONFIRMED"
        )
        self.floor.verify_checkpoint()

    def test_exact_command_replay_does_not_create_a_new_checkpoint(self):
        command = self._command("FENCE", 1)
        first = self.floor.reserve_fence_from_command(
            operation_id="checkpoint-replay-op", key=self.key,
            command_envelope=command, expected_revision=0,
        )
        checkpoint = self.floor.verify_checkpoint()
        replay = self.floor.reserve_fence_from_command(
            operation_id="checkpoint-replay-op", key=self.key,
            command_envelope=command, expected_revision=0,
        )
        self.assertEqual(first, replay)
        self.assertEqual(self.floor.verify_checkpoint(), checkpoint)

    def test_nonempty_unanchored_floor_cannot_be_bootstrapped(self):
        path = self.root / "unanchored.sqlite"
        raw = SQLiteProviderGrantFloorAuthority(path)
        signer = Ed25519PrivateKey.generate()
        raw.admin_register_coordinator_command_key(
            issuer_id="unanchored-issuer",
            key_id="unanchored-key",
            public_key=_raw_public_key(signer),
            not_before=time.time() - 60.0,
        )
        guard = CheckpointedSQLiteProviderGrantFloorAuthority(
            raw, InMemoryProviderGrantFloorCheckpointStore()
        )
        with self.assertRaises(ProviderGrantFloorCheckpointBootstrapDenied):
            guard.bootstrap_empty_floor()

    def test_absent_checkpoint_fails_closed(self):
        other = SQLiteProviderGrantFloorAuthority(self.root / "missing.sqlite")
        guard = CheckpointedSQLiteProviderGrantFloorAuthority(
            other, InMemoryProviderGrantFloorCheckpointStore()
        )
        with self.assertRaises(ProviderGrantFloorCheckpointMissing):
            guard.snapshot(self.key)

    def test_old_sqlite_snapshot_restore_is_detected(self):
        backup = self.root / "pre-key-registration.sqlite"
        with sqlite3.connect(self.database) as source, sqlite3.connect(backup) as target:
            source.backup(target)
        self.floor.admin_register_coordinator_command_key(
            issuer_id="rollback-issuer",
            key_id="rollback-key",
            public_key=_raw_public_key(Ed25519PrivateKey.generate()),
            not_before=time.time() - 60.0,
        )
        shutil.copy2(backup, self.database)
        os.chmod(self.database, 0o600)
        with self.assertRaises(ProviderGrantFloorCheckpointMismatch):
            self.floor.snapshot(self.key)

    def test_same_authority_revision_content_tamper_is_detected(self):
        before = self.floor.verify_checkpoint()
        self.assertEqual(before.authority_revision, 0)
        with sqlite3.connect(self.database) as connection:
            connection.execute(
                """UPDATE provider_grant_floor_coordinator_keys
                   SET public_key_sha256=? WHERE issuer_id=? AND key_id=?""",
                ("0" * 64, self.issuer_id, self.coordinator_key_id),
            )
        with self.assertRaises(ProviderGrantFloorCheckpointMismatch):
            self.floor.operation_status("no-such-operation")

    def test_failed_floor_validation_does_not_advance_checkpoint(self):
        before = self.floor.verify_checkpoint()
        bad = self._command(
            "FENCE", 1, fence_digest="1" * 64
        )
        with self.assertRaises(ProviderGrantFloorError):
            self.floor.reserve_fence_from_command(
                operation_id="bad-checkpoint-command",
                key=self.key,
                command_envelope=bad,
                expected_revision=0,
            )
        self.assertEqual(self.floor.verify_checkpoint(), before)

    def test_checkpoint_response_loss_is_resolved_only_by_exact_readback(self):
        store = _LoseNextCheckpointResponse()
        raw = SQLiteProviderGrantFloorAuthority(self.root / "lost-response.sqlite")
        guard = CheckpointedSQLiteProviderGrantFloorAuthority(raw, store)
        guard.bootstrap_empty_floor()
        store.lose_next_response = True
        guard.admin_register_coordinator_command_key(
            issuer_id="lost-response-issuer",
            key_id="lost-response-key",
            public_key=_raw_public_key(Ed25519PrivateKey.generate()),
            not_before=time.time() - 60.0,
        )
        self.assertEqual(guard.verify_checkpoint().sequence, 2)

    def test_mismatched_checkpoint_response_requires_and_accepts_exact_readback(self):
        store = _WrongNextCheckpointResponse()
        raw = SQLiteProviderGrantFloorAuthority(self.root / "misreported.sqlite")
        guard = CheckpointedSQLiteProviderGrantFloorAuthority(raw, store)

        store.misreport_next_response = True
        bootstrap = guard.bootstrap_empty_floor()
        self.assertEqual(bootstrap, store.read_checkpoint())

        store.misreport_next_response = True
        guard.admin_register_coordinator_command_key(
            issuer_id="misreported-issuer",
            key_id="misreported-key",
            public_key=_raw_public_key(Ed25519PrivateKey.generate()),
            not_before=time.time() - 60.0,
        )
        self.assertEqual(guard.verify_checkpoint(), store.read_checkpoint())

    def test_unconfirmed_checkpoint_write_leaves_floor_fail_closed(self):
        store = _FailNextCheckpointWrite()
        raw = SQLiteProviderGrantFloorAuthority(self.root / "unconfirmed.sqlite")
        guard = CheckpointedSQLiteProviderGrantFloorAuthority(raw, store)
        guard.bootstrap_empty_floor()
        store.fail_next_write = True
        with self.assertRaises(ProviderGrantFloorCheckpointUncertain):
            guard.admin_register_coordinator_command_key(
                issuer_id="unconfirmed-issuer",
                key_id="unconfirmed-key",
                public_key=_raw_public_key(Ed25519PrivateKey.generate()),
                not_before=time.time() - 60.0,
            )
        with self.assertRaises(ProviderGrantFloorCheckpointMismatch):
            guard.snapshot(self.key)

    def test_checkpoint_cas_conflict_leaves_floor_fail_closed(self):
        store = _ConflictNextCheckpointWrite()
        raw = SQLiteProviderGrantFloorAuthority(self.root / "cas-conflict.sqlite")
        guard = CheckpointedSQLiteProviderGrantFloorAuthority(raw, store)
        guard.bootstrap_empty_floor()
        store.conflict_next_write = True
        with self.assertRaises(ProviderGrantFloorCheckpointUncertain):
            guard.admin_register_coordinator_command_key(
                issuer_id="cas-conflict-issuer",
                key_id="cas-conflict-key",
                public_key=_raw_public_key(Ed25519PrivateKey.generate()),
                not_before=time.time() - 60.0,
            )
        with self.assertRaises(ProviderGrantFloorCheckpointMismatch):
            guard.snapshot(self.key)

    def test_external_checkpoint_rollback_is_detected(self):
        self.floor.verify_checkpoint()
        self.store._checkpoint = self.initial
        with self.assertRaises(ProviderGrantFloorCheckpointMismatch):
            self.floor.snapshot(self.key)

    def test_store_is_independent_from_sqlite_and_database_stays_private(self):
        self.assertFalse(hasattr(self.store, "database_path"))
        self.assertEqual(self.database.stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
