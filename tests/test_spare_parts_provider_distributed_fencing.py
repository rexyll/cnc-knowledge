from __future__ import annotations

import hashlib
import threading
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from scripts.spare_parts_fencing_attestation import (
    Ed25519PrivateKeySigner,
    create_fencing_attestation_ed25519,
)
from scripts.spare_parts_provider_distributed_fencing import (
    ConditionalControlStoreUnavailableError,
    DistributedFencingConflictError,
    DistributedFencingOutcomeUnknownError,
    DistributedFencingStaleTokenError,
    DistributedFencingUnavailableError,
    DistributedObjectFencingControlPlane,
    InMemoryConditionalObjectControlStore,
)


ISSUER = "synthetic-distributed-coordinator"
KEY_ID = "synthetic-distributed-v1"
TENANT = "tenant-synthetic"
OWNER = "owner-synthetic"
SCOPE = "cnc/ch17/backup-reference-distributed"
NOW = 1_900_000_000.0
PRIVATE = Ed25519PrivateKey.from_private_bytes(
    hashlib.sha256(b"CH17 distributed fencing synthetic key").digest()
)
SIGNER = Ed25519PrivateKeySigner(key_id=KEY_ID, private_key=PRIVATE)
PUBLIC = SIGNER.public_key_raw()


class DistributedFencingContractTests(unittest.TestCase):
    def setUp(self):
        self.store = InMemoryConditionalObjectControlStore()
        self.plane = DistributedObjectFencingControlPlane(
            self.store,
            trusted_ed25519_public_keys={KEY_ID: PUBLIC},
            trusted_issuers={ISSUER},
            clock_fn=lambda: NOW,
            receipt_history=2,
        )

    def proof(
        self, operation: str, *, token: int = 1, lease_id: str | None = None,
        idem: str | None = None, sequence: int | None = None,
        manifest_key: str | None = None, manifest_sha256: str | None = None,
        tenant_id: str = TENANT, expires_at: float = NOW + 60,
        lease_expires_at: float = NOW + 120, issuer: str = ISSUER,
    ) -> str:
        identity = lease_id or f"lease-{token}"
        operation_id = idem or f"{operation}-{token}-{sequence or 0}"
        claims = {
            "v": 2, "alg": "ED25519", "iss": issuer, "kid": KEY_ID,
            "lease_id": identity, "owner_id": OWNER, "tenant_id": tenant_id,
            "domain": "write", "fencing_token": token,
            "issued_at": NOW - 1, "expires_at": expires_at,
            "lease_expires_at": lease_expires_at,
            "fencing_scope": SCOPE, "resource_key": SCOPE,
            "operation": operation, "idempotency_key": operation_id,
        }
        if sequence is not None:
            claims["operation_sequence"] = sequence
        if manifest_key is not None:
            claims["manifest_key"] = manifest_key
        if manifest_sha256 is not None:
            claims["manifest_sha256"] = manifest_sha256
        return create_fencing_attestation_ed25519(claims, signer=SIGNER)

    def activate(self, token: int = 1, *, lease_id: str | None = None):
        return self.plane.activate_lease(
            SCOPE,
            fencing_attestation=self.proof(
                "fencing:activate", token=token, lease_id=lease_id,
                idem=f"activate-{token}",
            ),
        )

    def publish(self, token: int, sequence: int, *, idem: str | None = None, digest: str | None = None):
        object_key = f"{SCOPE}/staging/{token}/manifest-{sequence}.json"
        sha = digest or hashlib.sha256(f"manifest-{sequence}".encode()).hexdigest()
        return self.plane.publish_commit(
            SCOPE,
            fencing_attestation=self.proof(
                "fencing:publish", token=token, idem=idem or f"publish-{sequence}",
                sequence=sequence, manifest_key=object_key, manifest_sha256=sha,
            ),
        )

    def test_activation_advances_persistent_control_record_high_water(self):
        result = self.activate(1)
        self.assertEqual(result["high_water_token"], 1)
        self.assertEqual(result["lease_state"], "ACTIVE")
        self.activate(2)
        current = self.plane.snapshot(SCOPE)
        self.assertEqual(current["high_water_token"], 2)
        self.assertEqual(current["lease_id"], "lease-2")

    def test_old_writer_is_rejected_after_new_epoch_activation(self):
        self.activate(1)
        self.activate(2)
        with self.assertRaises(DistributedFencingStaleTokenError):
            self.publish(1, 1)
        current = self.plane.snapshot(SCOPE)
        self.assertIsNone(current["current_commit"])
        self.assertEqual(current["high_water_token"], 2)

    def test_revoke_is_linearized_by_control_object_cas(self):
        self.activate(1)
        revoked = self.plane.revoke_lease(
            SCOPE,
            fencing_attestation=self.proof(
                "fencing:revoke", token=1, idem="release-1",
            ),
        )
        self.assertEqual(revoked["lease_state"], "REVOKED")
        with self.assertRaises(DistributedFencingStaleTokenError):
            self.publish(1, 1)

    def test_publish_changes_only_the_authoritative_manifest_pointer(self):
        self.activate(1)
        result = self.publish(1, 1)
        self.assertFalse(result.replayed)
        current = self.plane.snapshot(SCOPE)
        self.assertEqual(current["current_commit"]["manifest_key"], result.manifest_key)
        self.assertEqual(current["current_commit"]["manifest_sha256"], result.manifest_sha256)
        self.assertEqual(current["latest_operation_sequence"], 1)

    def test_same_operation_replay_is_idempotent(self):
        self.activate(1)
        first = self.publish(1, 1, idem="same-logical-operation")
        second = self.publish(1, 1, idem="same-logical-operation")
        self.assertFalse(first.replayed)
        self.assertTrue(second.replayed)
        self.assertEqual(first.manifest_sha256, second.manifest_sha256)
        self.assertEqual(len(self.plane.snapshot(SCOPE)["recent_receipts"]), 1)

    def test_same_sequence_with_different_manifest_is_rejected(self):
        self.activate(1)
        self.publish(1, 1, idem="same-operation")
        with self.assertRaises(DistributedFencingConflictError):
            self.publish(1, 1, idem="same-operation", digest="f" * 64)

    def test_old_operation_outside_receipt_window_returns_unknown_not_replay(self):
        self.activate(1)
        self.publish(1, 1)
        self.publish(1, 2)
        self.publish(1, 3)
        with self.assertRaises(DistributedFencingOutcomeUnknownError):
            self.publish(1, 1)

    def test_out_of_order_operation_sequence_is_rejected(self):
        self.activate(1)
        self.publish(1, 2)
        with self.assertRaises(DistributedFencingOutcomeUnknownError):
            self.publish(1, 1)

    def test_lost_cas_response_is_resolved_by_strong_read(self):
        self.activate(1)
        self.store.lose_next_response_after_commit()
        result = self.publish(1, 1)
        self.assertEqual(result.operation_sequence, 1)
        self.assertEqual(self.plane.snapshot(SCOPE)["latest_operation_sequence"], 1)

    def test_untrusted_issuer_is_rejected(self):
        proof = self.proof("fencing:activate", token=1, issuer="unknown-issuer")
        with self.assertRaises(DistributedFencingError):
            self.plane.activate_lease(SCOPE, fencing_attestation=proof)

    def test_expired_proof_is_rejected(self):
        proof = self.proof("fencing:activate", token=1, expires_at=NOW - 0.1)
        with self.assertRaises(DistributedFencingError):
            self.plane.activate_lease(SCOPE, fencing_attestation=proof)

    def test_hmac_legacy_profile_is_not_accepted_for_remote_fencing(self):
        from scripts.spare_parts_fencing_attestation import create_fencing_attestation
        claims = {
            "v": 1, "iss": ISSUER, "kid": "legacy",
            "lease_id": "lease-1", "owner_id": OWNER, "tenant_id": TENANT,
            "domain": "write", "fencing_token": 1, "issued_at": NOW - 1,
            "expires_at": NOW + 60, "lease_expires_at": NOW + 120,
            "fencing_scope": SCOPE, "resource_key": SCOPE,
            "operation": "fencing:activate", "idempotency_key": "legacy-activate",
        }
        proof = create_fencing_attestation(
            claims, key_id="legacy", secret="synthetic-legacy-hmac-secret-over-32-bytes"
        )
        with self.assertRaises(DistributedFencingError):
            self.plane.activate_lease(SCOPE, fencing_attestation=proof)

    def test_control_store_outage_fails_closed(self):
        self.activate(1)
        self.store.set_available(False)
        with self.assertRaises(DistributedFencingUnavailableError):
            self.publish(1, 1)

    def test_stale_writer_cannot_publish_after_concurrent_epoch_switch(self):
        self.activate(1)
        reached_cas = threading.Event()
        release_cas = threading.Event()
        writer_errors = []

        def pause_old_writer(control_key: str, expected_etag: str | None, payload: bytes):
            if threading.current_thread().name == "old-epoch-writer":
                reached_cas.set()
                if not release_cas.wait(timeout=3):
                    raise RuntimeError("test timed out waiting to release stale CAS")

        self.store.before_compare_and_swap = pause_old_writer

        def old_writer():
            try:
                self.publish(1, 1)
            except Exception as exc:
                writer_errors.append(exc)

        worker = threading.Thread(target=old_writer, name="old-epoch-writer")
        worker.start()
        self.assertTrue(reached_cas.wait(timeout=2))
        self.store.before_compare_and_swap = None
        self.activate(2)
        release_cas.set()
        worker.join(timeout=4)
        self.assertFalse(worker.is_alive())
        self.assertEqual(len(writer_errors), 1)
        self.assertIsInstance(writer_errors[0], DistributedFencingStaleTokenError)
        current = self.plane.snapshot(SCOPE)
        self.assertEqual(current["high_water_token"], 2)
        self.assertEqual(current["lease_state"], "ACTIVE")
        self.assertIsNone(current["current_commit"])


from scripts.spare_parts_provider_distributed_fencing import (
    DistributedFencingError,
)


if __name__ == "__main__":
    unittest.main()
