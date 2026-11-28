import base64
import copy
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from scripts.spare_parts_sqlite_provider_fencing_reconciliation import (
    ProviderFencingReconciliationError,
)
from scripts.spare_parts_sqlite_provider_fencing_signed_evidence import (
    SIGNATURE_DOMAIN,
    validate_signed_provider_fencing_reconciliation,
    _canonical,
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
        "observed_at_unix": 990.0,
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


class SignedProviderEvidenceTests(unittest.TestCase):
    def setUp(self):
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
        self.evidence = evidence()
        signature = self.private_key.sign(SIGNATURE_DOMAIN + _canonical(self.evidence))
        self.envelope = {
            "format": "ch17-provider-fencing-signed-evidence-v1",
            "evidence": copy.deepcopy(self.evidence),
            "signature": {
                "algorithm": "Ed25519",
                "key_id": "provider-key-2026-01",
                "value_base64": base64.b64encode(signature).decode("ascii"),
            },
        }

    def verify(self, envelope=None, trust_store=None):
        return validate_signed_provider_fencing_reconciliation(
            candidate(),
            self.envelope if envelope is None else envelope,
            self.trust_store if trust_store is None else trust_store,
            now_unix=1000.0,
        )

    def test_accepts_valid_signature_then_reconciles_all_scopes(self):
        result = self.verify()
        self.assertTrue(result["evidence_signature_verified"])
        self.assertEqual(result["provider_fencing_reconciliation"], "PASS")
        self.assertEqual(result["verified_scope_count"], 2)
        self.assertEqual(result["signer_key_id"], "provider-key-2026-01")
        self.assertFalse(result["application_activation_authorized"])
        self.assertFalse(result["provider_operations_authorized"])

    def test_rejects_tampered_evidence(self):
        changed = copy.deepcopy(self.envelope)
        changed["evidence"]["scopes"]["inventory/parts"]["high_water_token"] = 11
        with self.assertRaisesRegex(ProviderFencingReconciliationError, "signature verification"):
            self.verify(changed)

    def test_rejects_unknown_signing_key(self):
        changed = copy.deepcopy(self.envelope)
        changed["signature"]["key_id"] = "unregistered-key"
        with self.assertRaisesRegex(ProviderFencingReconciliationError, "not trusted"):
            self.verify(changed)

    def test_rejects_wrong_signature_and_algorithm(self):
        changed = copy.deepcopy(self.envelope)
        changed["signature"]["value_base64"] = base64.b64encode(b"x" * 64).decode("ascii")
        with self.assertRaisesRegex(ProviderFencingReconciliationError, "signature verification"):
            self.verify(changed)
        changed = copy.deepcopy(self.envelope)
        changed["signature"]["algorithm"] = "HS256"
        with self.assertRaisesRegex(ProviderFencingReconciliationError, "algorithm"):
            self.verify(changed)

    def test_rejects_malformed_key_and_signature_encoding(self):
        changed_store = copy.deepcopy(self.trust_store)
        changed_store["keys"]["provider-key-2026-01"]["public_key_base64"] = "%%%"
        with self.assertRaisesRegex(ProviderFencingReconciliationError, "base64"):
            self.verify(trust_store=changed_store)
        changed = copy.deepcopy(self.envelope)
        changed["signature"]["value_base64"] = "%%%"
        with self.assertRaisesRegex(ProviderFencingReconciliationError, "base64"):
            self.verify(changed)

    def test_rejects_unknown_envelope_and_trust_store_fields(self):
        changed = copy.deepcopy(self.envelope)
        changed["extra"] = True
        with self.assertRaisesRegex(ProviderFencingReconciliationError, "envelope schema"):
            self.verify(changed)
        changed_store = copy.deepcopy(self.trust_store)
        changed_store["trust_me"] = True
        with self.assertRaisesRegex(ProviderFencingReconciliationError, "trust store schema"):
            self.verify(trust_store=changed_store)

    def test_signature_does_not_bypass_freshness_or_floor_checks(self):
        changed = copy.deepcopy(self.evidence)
        changed["observed_at_unix"] = 600.0
        signature = self.private_key.sign(SIGNATURE_DOMAIN + _canonical(changed))
        envelope = copy.deepcopy(self.envelope)
        envelope["evidence"] = changed
        envelope["signature"]["value_base64"] = base64.b64encode(signature).decode("ascii")
        with self.assertRaisesRegex(ProviderFencingReconciliationError, "stale"):
            self.verify(envelope)
        changed = copy.deepcopy(self.evidence)
        changed["scopes"]["inventory/parts"]["high_water_token"] = 13
        signature = self.private_key.sign(SIGNATURE_DOMAIN + _canonical(changed))
        envelope["evidence"] = changed
        envelope["signature"]["value_base64"] = base64.b64encode(signature).decode("ascii")
        with self.assertRaisesRegex(ProviderFencingReconciliationError, "rebuild candidate"):
            self.verify(envelope)


if __name__ == "__main__":
    unittest.main()
