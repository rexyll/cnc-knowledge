import base64
import os
import tempfile
import unittest
import uuid
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from scripts.spare_parts_sqlite_provider_fencing_reconciliation import (
    ProviderFencingReconciliationError,
    _canonical,
)
from scripts.spare_parts_sqlite_provider_fencing_signed_evidence import (
    SIGNATURE_DOMAIN,
)
from scripts.spare_parts_sqlite_provider_freeze_attestation import (
    FREEZE_SIGNATURE_DOMAIN,
    FREEZE_ENVELOPE_FORMAT,
    FREEZE_CLAIMS_FORMAT,
    COORDINATOR_SNAPSHOT_FORMAT,
    ProviderFreezeReplayError,
    SQLiteProviderFreezeEvidenceReplayLedger,
    validate_provider_freeze_attestation,
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
        "observed_at_unix": 997.0,
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


class ProviderFreezeAttestationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.ledger_path = Path(self.temp_dir.name) / "freeze-replay.sqlite3"
        self.ledger = SQLiteProviderFreezeEvidenceReplayLedger(self.ledger_path)
        self.private_key = Ed25519PrivateKey.generate()
        public_bytes = self.private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        self.trust_store = {
            "format": "ch17-provider-fencing-trust-store-v1",
            "keys": {
                "provider-key-2026-01": {
                    "algorithm": "Ed25519",
                    "public_key_base64": base64.b64encode(public_bytes).decode("ascii"),
                }
            },
        }
        self.nonce = "a" * 64
        self.coordinator = {
            "leader_id": "coordinator-leader-1",
            "leader_epoch": 12,
            "lease_id": 991,
            "lease_expires_at_unix": 1100.0,
        }
        self.snapshot = {
            "format": COORDINATOR_SNAPSHOT_FORMAT,
            "observed_at_unix": 999.0,
            **self.coordinator,
            "scopes": evidence()["scopes"],
        }
        self.claims = {
            "format": FREEZE_CLAIMS_FORMAT,
            "provider_id": "provider-prod-a",
            "freeze_id": "freeze-window-20261128-001",
            "freeze_generation": 7,
            "frozen": True,
            "freeze_mode": "provider-native-write-gate",
            "evidence_id": str(uuid.uuid4()),
            "challenge_nonce": self.nonce,
            "freeze_started_at_unix": 996.0,
            "freeze_expires_at_unix": 1060.0,
            "issued_at_unix": 998.0,
            "expires_at_unix": 1030.0,
            "coordinator": self.coordinator,
            "evidence": evidence(),
        }
        self.envelope = self.sign_claims(self.claims)

    def sign_claims(self, claims):
        signature = self.private_key.sign(
            FREEZE_SIGNATURE_DOMAIN + _canonical(claims)
        )
        return {
            "format": FREEZE_ENVELOPE_FORMAT,
            "evidence": claims,
            "signature": {
                "algorithm": "Ed25519",
                "key_id": "provider-key-2026-01",
                "value_base64": base64.b64encode(signature).decode("ascii"),
            },
        }

    def verify(self, envelope=None, snapshot=None, expected_nonce=None, ledger=None, now=1000.0):
        return validate_provider_freeze_attestation(
            candidate(),
            self.envelope if envelope is None else envelope,
            self.trust_store,
            self.snapshot if snapshot is None else snapshot,
            self.ledger if ledger is None else ledger,
            expected_challenge_nonce=self.nonce if expected_nonce is None else expected_nonce,
            now_unix=now,
        )

    def test_valid_freeze_attestation_is_consumed_and_bound_to_leader(self):
        result = self.verify()
        self.assertTrue(result["freeze_attestation_signature_verified"])
        self.assertTrue(result["freeze_evidence_replay_consumed"])
        self.assertEqual(result["coordinator_leader_epoch"], 12)
        self.assertEqual(result["coordinator_lease_id"], 991)
        self.assertEqual(result["provider_fencing_reconciliation"], "PASS")
        self.assertFalse(result["provider_write_freeze_enforced"])
        self.assertFalse(result["application_activation_authorized"])
        self.assertFalse(result["provider_operations_authorized"])
        self.assertEqual(os.stat(self.ledger_path).st_mode & 0o777, 0o600)

    def test_rejects_replay_of_same_evidence_id(self):
        self.verify()
        with self.assertRaises(ProviderFreezeReplayError):
            self.verify()

    def test_rejects_reuse_of_nonce_or_freeze_generation_with_new_evidence_id(self):
        self.verify()
        claims = dict(self.claims)
        claims["evidence_id"] = str(uuid.uuid4())
        envelope = self.sign_claims(claims)
        with self.assertRaises(ProviderFreezeReplayError):
            self.verify(envelope)

    def test_rejects_wrong_challenge_nonce(self):
        with self.assertRaisesRegex(ProviderFencingReconciliationError, "nonce mismatch"):
            self.verify(expected_nonce="b" * 64)

    def test_rejects_stale_or_mismatched_coordinator_snapshot(self):
        stale = dict(self.snapshot)
        stale["observed_at_unix"] = 990.0
        with self.assertRaisesRegex(ProviderFencingReconciliationError, "snapshot is stale"):
            self.verify(snapshot=stale)
        mismatched = dict(self.snapshot)
        mismatched["leader_epoch"] = 13
        with self.assertRaisesRegex(ProviderFencingReconciliationError, "leader_epoch mismatch"):
            self.verify(snapshot=mismatched)

    def test_rejects_changed_scope_floor_and_expired_lease(self):
        changed = dict(self.snapshot)
        changed["scopes"] = dict(self.snapshot["scopes"])
        changed["scopes"]["inventory/parts"] = dict(self.snapshot["scopes"]["inventory/parts"])
        changed["scopes"]["inventory/parts"]["high_water_token"] = 11
        with self.assertRaisesRegex(ProviderFencingReconciliationError, "differs from Coordinator"):
            self.verify(snapshot=changed)
        expired = dict(self.snapshot)
        expired["lease_expires_at_unix"] = 999.0
        with self.assertRaisesRegex(ProviderFencingReconciliationError, "Lease expires"):
            self.verify(snapshot=expired)

    def test_rejects_invalid_freeze_window_and_unsigned_frozen_assertion(self):
        claims = dict(self.claims)
        claims["expires_at_unix"] = 1065.0
        with self.assertRaisesRegex(ProviderFencingReconciliationError, "time window"):
            self.verify(self.sign_claims(claims))
        claims = dict(self.claims)
        claims["frozen"] = False
        with self.assertRaisesRegex(ProviderFencingReconciliationError, "not attested"):
            self.verify(self.sign_claims(claims))

    def test_failed_validation_does_not_consume_replay_identifier(self):
        claims = dict(self.claims)
        claims["coordinator"] = dict(self.coordinator, leader_epoch=13)
        envelope = self.sign_claims(claims)
        with self.assertRaises(ProviderFencingReconciliationError):
            self.verify(envelope)
        self.verify()

    def test_durable_ledger_rejects_duplicate_freeze_generation(self):
        self.verify()
        claims = dict(self.claims)
        claims["evidence_id"] = str(uuid.uuid4())
        claims["challenge_nonce"] = "b" * 64
        envelope = self.sign_claims(claims)
        with self.assertRaises(ProviderFreezeReplayError):
            self.verify(envelope, expected_nonce="b" * 64)

    def test_replay_ledger_requires_private_regular_file(self):
        path = Path(self.temp_dir.name) / "unsafe.sqlite3"
        path.write_text("not a database", encoding="utf-8")
        os.chmod(path, 0o644)
        ledger = SQLiteProviderFreezeEvidenceReplayLedger(path)
        with self.assertRaisesRegex(ProviderFencingReconciliationError, "mode 0600"):
            self.verify(ledger=ledger)


if __name__ == "__main__":
    unittest.main()
