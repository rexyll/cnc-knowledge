from __future__ import annotations

import unittest

from scripts.spare_parts_provider_fencing_contract import (
    FencingNotSupportedError,
    FencingTokenConflictError,
    StaleFencingTokenError,
    SyntheticFencedObjectSink,
    fenced_put,
)


class FencingContractTests(unittest.TestCase):
    def setUp(self):
        self.provider = SyntheticFencedObjectSink()

    def test_accepts_newer_token_and_atomically_updates_object_and_high_water(self):
        result = fenced_put(
            self.provider, "backup/ledger", b"version-1",
            fencing_token=1, idempotency_key="write-1",
        )
        self.assertFalse(result.replayed)
        self.assertEqual(self.provider.get("backup/ledger"), b"version-1")
        self.assertEqual(self.provider.high_water("backup/ledger"), 1)
        newer = fenced_put(
            self.provider, "backup/ledger", b"version-2",
            fencing_token=2, idempotency_key="write-2",
        )
        self.assertFalse(newer.replayed)
        self.assertEqual(self.provider.get("backup/ledger"), b"version-2")
        self.assertEqual(self.provider.high_water("backup/ledger"), 2)

    def test_rejects_paused_old_writer_after_newer_writer_commits(self):
        fenced_put(
            self.provider, "backup/ledger", b"new-owner",
            fencing_token=42, idempotency_key="new-owner-write",
        )
        with self.assertRaises(StaleFencingTokenError):
            fenced_put(
                self.provider, "backup/ledger", b"stale-owner",
                fencing_token=41, idempotency_key="late-old-write",
            )
        self.assertEqual(self.provider.get("backup/ledger"), b"new-owner")
        self.assertEqual(self.provider.high_water("backup/ledger"), 42)

    def test_same_token_and_same_request_and_payload_is_idempotent(self):
        first = fenced_put(
            self.provider, "backup/ledger", b"payload",
            fencing_token=7, idempotency_key="operation-7",
        )
        replay = fenced_put(
            self.provider, "backup/ledger", b"payload",
            fencing_token=7, idempotency_key="operation-7",
        )
        self.assertFalse(first.replayed)
        self.assertTrue(replay.replayed)
        self.assertEqual(first.content_sha256, replay.content_sha256)

    def test_same_token_with_changed_payload_is_rejected(self):
        fenced_put(
            self.provider, "backup/ledger", b"original",
            fencing_token=9, idempotency_key="operation-9",
        )
        with self.assertRaises(FencingTokenConflictError):
            fenced_put(
                self.provider, "backup/ledger", b"changed",
                fencing_token=9, idempotency_key="operation-9",
            )
        self.assertEqual(self.provider.get("backup/ledger"), b"original")

    def test_same_token_with_different_operation_id_is_rejected(self):
        fenced_put(
            self.provider, "backup/ledger", b"original",
            fencing_token=10, idempotency_key="operation-A",
        )
        with self.assertRaises(FencingTokenConflictError):
            fenced_put(
                self.provider, "backup/ledger", b"original",
                fencing_token=10, idempotency_key="operation-B",
            )

    def test_provider_without_fencing_capability_fails_closed(self):
        class LegacyProvider:
            supports_fencing = False

            def put_if_absent(self, key, data):
                raise AssertionError("legacy write must never be invoked")

        with self.assertRaises(FencingNotSupportedError):
            fenced_put(
                LegacyProvider(), "backup/ledger", b"payload",
                fencing_token=1, idempotency_key="operation",
            )

    def test_provider_claim_without_atomic_fencing_operation_fails_closed(self):
        class IncompleteProvider:
            supports_fencing = True

        with self.assertRaises(FencingNotSupportedError):
            fenced_put(
                IncompleteProvider(), "backup/ledger", b"payload",
                fencing_token=1, idempotency_key="operation",
            )

    def test_invalid_tokens_are_rejected_without_mutation(self):
        for token in (0, -1, True, 1.5):
            with self.subTest(token=token), self.assertRaises(Exception):
                fenced_put(
                    self.provider, "backup/ledger", b"payload",
                    fencing_token=token, idempotency_key="operation",
                )
        self.assertIsNone(self.provider.get("backup/ledger"))
        self.assertEqual(self.provider.high_water("backup/ledger"), 0)


if __name__ == "__main__":
    unittest.main()
