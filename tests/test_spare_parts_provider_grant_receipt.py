from __future__ import annotations

import hashlib
import json
import time
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from scripts.spare_parts_provider_grant_receipt import (
    CLAIMS_FORMAT,
    ProviderGrantReceiptError,
    ProviderReceiptTrustKey,
    canonical_receipt_json,
    sign_provider_grant_receipt,
    verify_provider_grant_receipt,
)


class ProviderGrantReceiptProtocolTests(unittest.TestCase):
    def setUp(self):
        self.signer = Ed25519PrivateKey.generate()
        self.public_key = self.signer.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        )
        self.fingerprint = hashlib.sha256(self.public_key).hexdigest()
        self.key_id = "provider-receipt-test-a"
        self.now = time.time()
        self.trust_key = ProviderReceiptTrustKey(
            provider_id="provider-test-a",
            key_id=self.key_id,
            public_key=self.public_key,
            public_key_sha256=self.fingerprint,
            status="ACTIVE",
            not_before=self.now - 3600.0,
            not_after=None,
            revocation_effective_at=None,
            trust_revision=4,
        )

    def claims(self, **changes):
        issued = self.now - 1.0
        result = {
            "format": CLAIMS_FORMAT,
            "provider_id": "provider-test-a",
            "tenant_id": "tenant-a",
            "scope": "cnc/ch17/backup-reference-001",
            "action": "FENCE",
            "grant_id": "grant-001",
            "generation": 11,
            "command_sha256": "1" * 64,
            "fence_command_sha256": None,
            "result_state": "FENCED",
            "coordinator_namespace": "/cnc/migration/isolated/provider-grant-test/",
            "leader_id": "coordinator-leader-a",
            "leader_epoch": 7,
            "native_lease_id": 701,
            "native_lease_expires_at_unix": self.now + 120.0,
            "command_issued_at_unix": issued,
            "command_expires_at_unix": self.now + 30.0,
            "applied_at_unix": self.now - 0.5,
        }
        result.update(changes)
        return result

    def sign(self, **changes):
        return sign_provider_grant_receipt(
            self.claims(**changes),
            key_id=self.key_id,
            private_key=self.signer,
        )

    def verify(self, envelope, trust_key=None, **expected):
        return verify_provider_grant_receipt(
            envelope,
            self.trust_key if trust_key is None else trust_key,
            expected_claims=expected or {
                "provider_id": "provider-test-a",
                "tenant_id": "tenant-a",
                "scope": "cnc/ch17/backup-reference-001",
            },
            now_unix=self.now,
        )

    def test_rfc8785_canonicalization_sorts_keys_and_emits_compact_utf8(self):
        self.assertEqual(
            canonical_receipt_json({"z": 1, "a": "机床"}),
            '{"a":"机床","z":1}'.encode("utf-8"),
        )

    def test_valid_fence_receipt_verifies_and_hashes_entire_envelope(self):
        envelope = self.sign()
        verified = self.verify(envelope)
        expected_digest = hashlib.sha256(canonical_receipt_json(envelope)).hexdigest()
        self.assertEqual(verified.receipt_digest, expected_digest)
        self.assertEqual(verified.action, "FENCE")
        self.assertEqual(verified.result_state, "FENCED")
        self.assertIsNone(verified.fence_command_sha256)
        self.assertEqual(verified.signer_key_id, self.key_id)
        self.assertEqual(verified.signer_public_key_sha256, self.fingerprint)
        self.assertEqual(verified.trust_revision, 4)

    def test_valid_activate_receipt_requires_exact_prior_fence_digest(self):
        fence_digest = "2" * 64
        envelope = self.sign(
            action="ACTIVATE",
            generation=12,
            command_sha256="3" * 64,
            fence_command_sha256=fence_digest,
            result_state="ACTIVE",
        )
        verified = self.verify(
            envelope,
            action="ACTIVATE",
            generation=12,
            command_sha256="3" * 64,
            fence_command_sha256=fence_digest,
            result_state="ACTIVE",
        )
        self.assertEqual(verified.fence_command_sha256, fence_digest)

    def test_signature_tampering_is_rejected(self):
        envelope = self.sign()
        signature = envelope["signature"]["value_base64"]
        envelope["signature"]["value_base64"] = ("A" if signature[0] != "A" else "B") + signature[1:]
        with self.assertRaisesRegex(ProviderGrantReceiptError, "signature verification failed"):
            self.verify(envelope)

    def test_receipt_claim_tampering_is_rejected(self):
        envelope = self.sign()
        envelope["receipt"]["grant_id"] = "grant-substituted"
        with self.assertRaisesRegex(ProviderGrantReceiptError, "signature verification failed"):
            self.verify(envelope)

    def test_expected_reservation_binding_is_exact(self):
        envelope = self.sign()
        with self.assertRaisesRegex(ProviderGrantReceiptError, "does not match reservation"):
            self.verify(envelope, command_sha256="f" * 64)

    def test_provider_identity_must_match_the_registered_signer(self):
        envelope = self.sign()
        wrong_key = ProviderReceiptTrustKey(
            provider_id="provider-other",
            key_id=self.key_id,
            public_key=self.public_key,
            public_key_sha256=self.fingerprint,
            status="ACTIVE",
            not_before=self.now - 3600.0,
            not_after=None,
            revocation_effective_at=None,
            trust_revision=4,
        )
        with self.assertRaisesRegex(ProviderGrantReceiptError, "signer identity"):
            self.verify(envelope, trust_key=wrong_key)

    def test_public_key_fingerprint_mismatch_is_rejected(self):
        envelope = self.sign()
        wrong_key = ProviderReceiptTrustKey(
            provider_id="provider-test-a",
            key_id=self.key_id,
            public_key=self.public_key,
            public_key_sha256="0" * 64,
            status="ACTIVE",
            not_before=self.now - 3600.0,
            not_after=None,
            revocation_effective_at=None,
            trust_revision=4,
        )
        with self.assertRaisesRegex(ProviderGrantReceiptError, "fingerprint mismatch"):
            self.verify(envelope, trust_key=wrong_key)

    def test_key_validity_window_is_enforced_at_provider_applied_time(self):
        envelope = self.sign()
        expired_key = ProviderReceiptTrustKey(
            provider_id="provider-test-a",
            key_id=self.key_id,
            public_key=self.public_key,
            public_key_sha256=self.fingerprint,
            status="ACTIVE",
            not_before=self.now + 10.0,
            not_after=self.now + 20.0,
            revocation_effective_at=None,
            trust_revision=5,
        )
        with self.assertRaisesRegex(ProviderGrantReceiptError, "before the key validity window"):
            self.verify(envelope, trust_key=expired_key)

    def test_retiring_key_can_verify_receipts_created_inside_its_validity_window(self):
        envelope = self.sign()
        retiring = ProviderReceiptTrustKey(
            provider_id="provider-test-a",
            key_id=self.key_id,
            public_key=self.public_key,
            public_key_sha256=self.fingerprint,
            status="RETIRING",
            not_before=self.now - 3600.0,
            not_after=self.now + 10.0,
            revocation_effective_at=None,
            trust_revision=5,
        )
        self.assertEqual(self.verify(envelope, trust_key=retiring).signer_key_id, self.key_id)

    def test_revoked_key_rejects_receipts_at_or_after_effective_time(self):
        envelope = self.sign()
        revoked = ProviderReceiptTrustKey(
            provider_id="provider-test-a",
            key_id=self.key_id,
            public_key=self.public_key,
            public_key_sha256=self.fingerprint,
            status="REVOKED",
            not_before=self.now - 3600.0,
            not_after=None,
            revocation_effective_at=self.now - 1.0,
            trust_revision=6,
        )
        with self.assertRaisesRegex(ProviderGrantReceiptError, "was revoked"):
            self.verify(envelope, trust_key=revoked)

    def test_revoked_key_can_verify_receipt_applied_before_revocation_boundary(self):
        old_claims = self.claims(
            command_issued_at_unix=self.now - 20.0,
            command_expires_at_unix=self.now + 20.0,
            applied_at_unix=self.now - 10.0,
        )
        envelope = sign_provider_grant_receipt(
            old_claims, key_id=self.key_id, private_key=self.signer
        )
        revoked = ProviderReceiptTrustKey(
            provider_id="provider-test-a",
            key_id=self.key_id,
            public_key=self.public_key,
            public_key_sha256=self.fingerprint,
            status="REVOKED",
            not_before=self.now - 3600.0,
            not_after=None,
            revocation_effective_at=self.now - 5.0,
            trust_revision=6,
        )
        self.assertEqual(self.verify(envelope, trust_key=revoked).action, "FENCE")

    def test_future_applied_time_beyond_clock_skew_is_rejected(self):
        envelope = self.sign(
            command_issued_at_unix=self.now + 10.0,
            command_expires_at_unix=self.now + 60.0,
            applied_at_unix=self.now + 11.0,
        )
        with self.assertRaisesRegex(ProviderGrantReceiptError, "in the future"):
            self.verify(envelope)

    def test_applied_time_after_signed_command_expiry_is_rejected(self):
        with self.assertRaisesRegex(ProviderGrantReceiptError, "outside the signed command window"):
            self.sign(
                command_issued_at_unix=self.now - 10.0,
                command_expires_at_unix=self.now - 5.0,
                applied_at_unix=self.now - 1.0,
            )

    def test_fence_cannot_claim_activate_result_or_prior_fence(self):
        with self.assertRaisesRegex(ProviderGrantReceiptError, "result state"):
            self.sign(result_state="ACTIVE")
        with self.assertRaisesRegex(ProviderGrantReceiptError, "must not reference"):
            self.sign(fence_command_sha256="2" * 64)

    def test_activate_requires_a_canonical_fence_command_digest(self):
        with self.assertRaisesRegex(ProviderGrantReceiptError, "lowercase SHA-256"):
            self.sign(
                action="ACTIVATE",
                result_state="ACTIVE",
                fence_command_sha256="NOT-A-DIGEST",
            )

    def test_duplicate_json_keys_are_rejected_before_signature_verification(self):
        with self.assertRaisesRegex(ProviderGrantReceiptError, "duplicate object key"):
            self.verify(b'{"format":"cnc-provider-grant-receipt-envelope-v1","format":"x"}')

    def test_unknown_fields_and_boolean_integer_claims_are_rejected(self):
        envelope = self.sign()
        envelope["receipt"]["unexpected"] = "not allowed"
        with self.assertRaisesRegex(ProviderGrantReceiptError, "claims schema"):
            self.verify(envelope)
        with self.assertRaisesRegex(ProviderGrantReceiptError, "SQLite-safe positive integer"):
            self.sign(generation=True)


if __name__ == "__main__":
    unittest.main()
