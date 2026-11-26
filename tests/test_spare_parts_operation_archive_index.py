from __future__ import annotations

import unittest

from scripts.spare_parts_operation_ledger_archive import (
    InMemoryImmutableOperationArchiveStore,
    OperationLedgerArchiveModel,
    make_operation,
)
from scripts.spare_parts_operation_archive_index import (
    ExactArchiveIndexConflictError,
    ExactArchiveIndexIntegrityError,
    ExactArchiveIndexPolicyError,
    ExactShardedArchiveIndex,
)


SCOPE_A = "tenants/tenant-A/cnc/spares/pkg-001"
SCOPE_B = "tenants/tenant-B/cnc/spares/pkg-002"
NOW = 1_900_000_000.0


def operation(idem: str, *, scope: str = SCOPE_A, token: int = 3, seq: int = 10):
    return make_operation(
        scope=scope,
        kind="PUBLISH",
        idempotency_key=idem,
        request_sha256=("a" if scope == SCOPE_A else "b") * 64,
        state="COMMITTED",
        fencing_token=token,
        operation_sequence=seq,
        manifest_key=f"{scope}/manifest-{idem}.json",
        manifest_sha256=("c" if scope == SCOPE_A else "d") * 64,
        provider_generation="provider-gen-1",
        created_at=NOW - 10_000,
        updated_at=NOW - 9_000,
    )


class ExactShardedArchiveIndexTests(unittest.TestCase):
    def setUp(self):
        self.store = InMemoryImmutableOperationArchiveStore()
        self.archive = OperationLedgerArchiveModel(self.store)
        self.archive.create_scope(
            SCOPE_A,
            high_water_token=3,
            latest_operation_sequence=10,
            lease_state="REVOKED",
            lease_id="lease-3",
        )
        self.archive.create_scope(
            SCOPE_B,
            high_water_token=1,
            latest_operation_sequence=2,
            lease_state="REVOKED",
            lease_id="lease-B",
        )
        self.index = ExactShardedArchiveIndex(self.store, bucket_count=256)

    def _make_batch(self, keys, *, scope=SCOPE_A):
        for item in keys:
            self.archive.insert_or_replay(operation(item, scope=scope))
        return self.archive.archive_scope(
            scope,
            now=NOW,
            minimum_age_seconds=0,
            max_records=100,
            max_batch_bytes=1_000_000,
        )

    def _lookup(self, pointer, idempotency_key, expected_count=None):
        authoritative_count = (
            self.archive.snapshot(SCOPE_A)["archived_operation_count"]
            if expected_count is None else expected_count
        )
        return self.index.lookup(
            pointer,
            idempotency_key=idempotency_key,
            expected_archive_operation_count=authoritative_count,
        )

    def _build(self, keys):
        result = self._make_batch(keys)
        pointer = self.index.build_from_chain(
            scope=SCOPE_A,
            archive_head_sha256=result["manifest_sha256"],
            archive_generation=result["archive_generation"],
            expected_operation_count=result["archived"],
        )
        return result, pointer

    def test_build_backfill_creates_exact_root_and_bucket_shards(self):
        result, pointer = self._build(["a", "b", "c"])
        self.assertEqual(pointer["operation_count"], 3)
        verified = self.index.verify_against_chain(
            pointer, expected_archive_count=result["archived"]
        )
        self.assertTrue(verified["verified"])
        self.assertEqual(verified["operation_count"], 3)

    def test_exact_lookup_returns_original_operation(self):
        self._build(["lookup-1"])
        pointer = self.index.build_from_chain(
            scope=SCOPE_A,
            archive_head_sha256=self.archive.snapshot(SCOPE_A)["archive_head_sha256"],
            archive_generation=1,
            expected_operation_count=1,
        )
        found = self._lookup(pointer, "lookup-1")
        self.assertEqual(found["idempotency_key"], "lookup-1")
        self.assertEqual(found["operation_sequence"], 10)

    def test_exact_not_found_does_not_scan_all_manifest_batches(self):
        _, pointer = self._build(["present"])
        result = self._lookup(pointer, "absent")
        self.assertIsNone(result)
        self.assertLessEqual(self.index.last_lookup_object_reads, 2)

    def test_hit_reads_only_root_shard_and_target_batch(self):
        _, pointer = self._build(["hot-hit"])
        self._lookup(pointer, "hot-hit")
        self.assertLessEqual(self.index.last_lookup_object_reads, 3)

    def test_incremental_append_updates_index_generation(self):
        _, pointer = self._build(["first"])
        self.archive.insert_or_replay(operation("second", seq=11))
        second_batch = self.archive.archive_scope(
            SCOPE_A,
            now=NOW,
            minimum_age_seconds=0,
            max_records=100,
            max_batch_bytes=1_000_000,
        )
        next_pointer = self.index.append_batch(
            previous_pointer=pointer,
            batch_sha256=second_batch["manifest_sha256"],
        )
        self.assertEqual(next_pointer["index_generation"], 2)
        self.assertEqual(next_pointer["operation_count"], 2)
        self.assertEqual(
            self._lookup(next_pointer, "first")["idempotency_key"],
            "first",
        )
        self.assertEqual(
            self._lookup(next_pointer, "second")["idempotency_key"],
            "second",
        )

    def test_previous_pointer_remains_immutable_after_append(self):
        _, first_pointer = self._build(["first"])
        self.archive.insert_or_replay(operation("second", seq=11))
        second_batch = self.archive.archive_scope(
            SCOPE_A,
            now=NOW,
            minimum_age_seconds=0,
            max_records=100,
            max_batch_bytes=1_000_000,
        )
        second_pointer = self.index.append_batch(
            previous_pointer=first_pointer,
            batch_sha256=second_batch["manifest_sha256"],
        )
        self.assertIsNone(
            self._lookup(first_pointer, "second", expected_count=1)
        )
        self.assertIsNotNone(
            self._lookup(second_pointer, "second", expected_count=2)
        )

    def test_wrong_previous_archive_head_is_rejected(self):
        _, pointer = self._build(["first"])
        fake_pointer = dict(pointer)
        fake_pointer["archive_head_sha256"] = "f" * 64
        with self.assertRaises(ExactArchiveIndexIntegrityError):
            self.index.append_batch(
                previous_pointer=fake_pointer,
                batch_sha256="e" * 64,
            )

    def test_previous_generation_batch_cannot_be_appended_twice(self):
        _, pointer = self._build(["first"])
        with self.assertRaises(ExactArchiveIndexIntegrityError):
            self.index.append_batch(
                previous_pointer=pointer,
                batch_sha256=pointer["archive_head_sha256"],
            )

    def test_duplicate_archive_key_is_rejected_on_incremental_append(self):
        import json
        from scripts.spare_parts_operation_ledger_archive import canonical_json_bytes

        first_result, pointer = self._build(["first"])
        first_batch = self.store.read(first_result["manifest_sha256"])
        source_batch = json.loads(first_batch.decode("utf-8"))
        duplicate_batch = {
            "schema_version": 1,
            "scope": SCOPE_A,
            "generation": 2,
            "previous_batch_sha256": first_result["manifest_sha256"],
            "records": source_batch["records"],
        }
        duplicate_sha = self.store.put_immutable(canonical_json_bytes(duplicate_batch))
        with self.assertRaises(ExactArchiveIndexConflictError):
            self.index.append_batch(
                previous_pointer=pointer,
                batch_sha256=duplicate_sha,
            )

    def test_corrupt_root_is_rejected(self):
        _, pointer = self._build(["root-corrupt"])
        self.store.corrupt_for_test(pointer["index_head_sha256"], b"{}")
        with self.assertRaises(ExactArchiveIndexIntegrityError):
            self._lookup(pointer, "root-corrupt")

    def test_corrupt_bucket_shard_is_rejected(self):
        _, pointer = self._build(["shard-corrupt"])
        root = self.index._read_root(pointer)
        key = next(iter(root["buckets"]))
        self.store.corrupt_for_test(root["buckets"][key]["sha256"], b"{}")
        with self.assertRaises(ExactArchiveIndexIntegrityError):
            self._lookup(pointer, "shard-corrupt")

    def test_corrupt_target_archive_batch_is_rejected(self):
        _, pointer = self._build(["batch-corrupt"])
        root = self.index._read_root(pointer)
        key = next(iter(root["buckets"]))
        shard = self.index._read_shard(
            root["buckets"][key]["sha256"],
            scope=SCOPE_A,
            bucket=key,
            expected_count=root["buckets"][key]["count"],
        )
        batch_sha = shard["entries"][0]["batch_sha256"]
        self.store.corrupt_for_test(batch_sha, b"{}")
        with self.assertRaises(ExactArchiveIndexIntegrityError):
            self._lookup(pointer, "batch-corrupt")

    def test_pointer_scope_mismatch_is_rejected(self):
        _, pointer = self._build(["scope-bound"])
        bad = dict(pointer)
        bad["scope"] = SCOPE_B
        with self.assertRaises(ExactArchiveIndexIntegrityError):
            self._lookup(bad, "scope-bound")

    def test_authoritative_scope_archive_count_mismatch_fails_closed(self):
        _, pointer = self._build(["count-bound"])
        with self.assertRaises(ExactArchiveIndexIntegrityError):
            self.index.lookup(
                pointer,
                idempotency_key="not-present",
                expected_archive_operation_count=0,
            )

    def test_pointer_archive_generation_mismatch_is_rejected(self):
        _, pointer = self._build(["generation-bound"])
        bad = dict(pointer)
        bad["archive_generation"] = 2
        with self.assertRaises(ExactArchiveIndexIntegrityError):
            self._lookup(bad, "generation-bound")

    def test_wrong_bucket_count_policy_is_rejected(self):
        with self.assertRaises(ExactArchiveIndexPolicyError):
            ExactShardedArchiveIndex(self.store, bucket_count=64)

    def test_all_supported_bucket_counts_build_valid_indexes(self):
        for bucket_count in (16, 256, 4096):
            store = InMemoryImmutableOperationArchiveStore()
            archive = OperationLedgerArchiveModel(store)
            archive.create_scope(SCOPE_A, high_water_token=3, latest_operation_sequence=10)
            archive.insert_or_replay(operation(f"b{bucket_count}"))
            result = archive.archive_scope(
                SCOPE_A, now=NOW, minimum_age_seconds=0,
                max_records=100, max_batch_bytes=1_000_000,
            )
            index = ExactShardedArchiveIndex(store, bucket_count=bucket_count)
            pointer = index.build_from_chain(
                scope=SCOPE_A,
                archive_head_sha256=result["manifest_sha256"],
                archive_generation=result["archive_generation"],
                expected_operation_count=result["archived"],
            )
            self.assertEqual(
                index.lookup(
                    pointer,
                    idempotency_key=f"b{bucket_count}",
                    expected_archive_operation_count=result["archived"],
                )["idempotency_key"],
                f"b{bucket_count}",
            )

    def test_full_chain_audit_detects_missing_index_entries(self):
        _, pointer = self._build(["one", "two"])
        root = self.index._read_root(pointer)
        bucket = next(iter(root["buckets"]))
        shard = self.index._read_shard(
            root["buckets"][bucket]["sha256"],
            scope=SCOPE_A,
            bucket=bucket,
            expected_count=root["buckets"][bucket]["count"],
        )
        shard["entries"].pop()
        raw = __import__("scripts.spare_parts_operation_ledger_archive", fromlist=["canonical_json_bytes"]).canonical_json_bytes(shard)
        digest = self.store.put_immutable(raw)
        altered_root = dict(root)
        altered_root["buckets"] = dict(root["buckets"])
        altered_root["buckets"][bucket] = {
            "sha256": digest,
            "count": len(shard["entries"]),
        }
        altered_root["operation_count"] = sum(
            item["count"] for item in altered_root["buckets"].values()
        )
        root_digest = self.store.put_immutable(
            __import__("scripts.spare_parts_operation_ledger_archive", fromlist=["canonical_json_bytes"]).canonical_json_bytes(altered_root)
        )
        bad_pointer = dict(pointer)
        bad_pointer["index_head_sha256"] = root_digest
        bad_pointer["operation_count"] = altered_root["operation_count"]
        with self.assertRaises(ExactArchiveIndexIntegrityError):
            self.index.verify_against_chain(
                bad_pointer,
                expected_archive_count=2,
            )

    def test_negative_lookup_with_absent_bucket_is_exact(self):
        _, pointer = self._build(["present"])
        # The absent key is hashed and bucketed exactly; no probabilistic
        # filter is involved in the not-found decision.
        self.assertIsNone(self._lookup(pointer, "no-such-key"))

    def test_index_pointer_requires_exact_field_set(self):
        _, pointer = self._build(["pointer-schema"])
        bad = dict(pointer)
        bad["bloom_filter_maybe"] = True
        with self.assertRaises(ExactArchiveIndexIntegrityError):
            self._lookup(bad, "pointer-schema")

    def test_full_index_audit_matches_all_manifest_records(self):
        result, pointer = self._build(["audit-a", "audit-b", "audit-c"])
        report = self.index.verify_against_chain(
            pointer, expected_archive_count=result["archived"]
        )
        self.assertEqual(report["operation_count"], 3)
        self.assertEqual(report["generation"], 1)


if __name__ == "__main__":
    unittest.main()
