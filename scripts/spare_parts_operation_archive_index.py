#!/usr/bin/env python3
"""Exact sharded idempotency index for immutable Coordinator archive batches.

This is a pure reference model. It uses the existing in-memory immutable
archive store and does not connect to production Coordinator, etcd or object
storage. A missing index entry is authoritative only when the root and target
shard are validated against the committed archive pointer.
"""
from __future__ import annotations

import bisect
import hashlib
import json
from typing import Any

from scripts.spare_parts_operation_ledger_archive import (
    InMemoryImmutableOperationArchiveStore,
    OperationArchiveConflictError,
    OperationArchiveIntegrityError,
    OperationArchivePolicyError,
    OperationArchiveUnavailableError,
    canonical_json_bytes,
    operation_index_key,
)


class ExactArchiveIndexError(RuntimeError):
    """Base exception for exact archive-index operations."""


class ExactArchiveIndexIntegrityError(ExactArchiveIndexError):
    """The root, shard, archive batch or identity does not verify."""


class ExactArchiveIndexConflictError(ExactArchiveIndexError):
    """An archive generation or operation key conflicts with existing data."""


class ExactArchiveIndexPolicyError(ExactArchiveIndexError):
    """An unsupported bucket/index policy was requested."""


class ExactShardedArchiveIndex:
    """Immutable 16/256/4096-bucket exact index over archive manifest batches.

    Each archive generation writes new immutable shard snapshots only for
    buckets touched by that batch, then writes a new small root object.
    Coordinator integration is expected to CAS the returned pointer alongside
    the archive manifest pointer. This class only prepares and verifies that
    pointer; it never switches live Coordinator state.
    """

    _ROOT_FIELDS = {
        "schema_version",
        "scope",
        "generation",
        "archive_head_sha256",
        "previous_index_sha256",
        "bucket_count",
        "operation_count",
        "buckets",
    }
    _SHARD_FIELDS = {"schema_version", "scope", "bucket", "entries"}
    _ENTRY_FIELDS = {
        "operation_key",
        "batch_sha256",
        "batch_generation",
        "record_index",
        "record_sha256",
    }
    _BATCH_FIELDS = {
        "schema_version",
        "scope",
        "generation",
        "previous_batch_sha256",
        "records",
    }

    def __init__(
        self,
        archive_store: InMemoryImmutableOperationArchiveStore,
        *,
        bucket_count: int = 256,
    ) -> None:
        if (
            not isinstance(bucket_count, int)
            or isinstance(bucket_count, bool)
            or bucket_count not in {16, 256, 4096}
        ):
            raise ExactArchiveIndexPolicyError(
                "bucket_count must be one of 16, 256 or 4096"
            )
        self.archive_store = archive_store
        self.bucket_count = bucket_count
        self._bucket_hex_width = {16: 1, 256: 2, 4096: 3}[bucket_count]
        self.last_lookup_object_reads = 0

    def _bucket(self, operation_key: str) -> str:
        return operation_key[: self._bucket_hex_width]

    @staticmethod
    def _sha256(payload: bytes) -> str:
        return hashlib.sha256(payload).hexdigest()

    def _put_verified(self, payload: bytes) -> str:
        digest = self.archive_store.put_immutable(payload)
        if digest != self._sha256(payload):
            raise ExactArchiveIndexIntegrityError(
                "immutable object store returned a mismatched content address"
            )
        readback = self.archive_store.read(digest)
        if readback != payload or self._sha256(readback) != digest:
            raise ExactArchiveIndexIntegrityError(
                "immutable object read-back verification failed"
            )
        return digest

    def _read_json(self, digest: str) -> dict[str, Any]:
        raw = self.archive_store.read(digest)
        if self._sha256(raw) != digest:
            raise ExactArchiveIndexIntegrityError("content-address digest mismatch")
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ExactArchiveIndexIntegrityError("indexed object is invalid JSON") from exc
        if not isinstance(value, dict):
            raise ExactArchiveIndexIntegrityError("indexed object must be a JSON object")
        return value

    def _read_batch(
        self,
        digest: str,
        *,
        expected_scope: str,
        expected_generation: int,
    ) -> dict[str, Any]:
        batch = self._read_json(digest)
        if (
            set(batch) != self._BATCH_FIELDS
            or batch.get("schema_version") != 1
            or batch.get("scope") != expected_scope
            or batch.get("generation") != expected_generation
            or not isinstance(batch.get("records"), list)
        ):
            raise ExactArchiveIndexIntegrityError(
                "archive batch schema, scope or generation mismatch"
            )
        return batch

    def _read_root(self, pointer: dict[str, Any]) -> dict[str, Any]:
        required_pointer = {
            "scope",
            "index_generation",
            "index_head_sha256",
            "archive_generation",
            "archive_head_sha256",
            "operation_count",
            "bucket_count",
        }
        if not isinstance(pointer, dict) or set(pointer) != required_pointer:
            raise ExactArchiveIndexIntegrityError("archive index pointer schema mismatch")
        if (
            pointer["bucket_count"] != self.bucket_count
            or pointer["index_generation"] != pointer["archive_generation"]
            or not isinstance(pointer["operation_count"], int)
            or isinstance(pointer["operation_count"], bool)
            or pointer["operation_count"] < 0
        ):
            raise ExactArchiveIndexIntegrityError("archive index pointer counters mismatch")
        root = self._read_json(pointer["index_head_sha256"])
        if (
            set(root) != self._ROOT_FIELDS
            or root.get("schema_version") != 1
            or root.get("scope") != pointer["scope"]
            or root.get("generation") != pointer["index_generation"]
            or root.get("archive_head_sha256") != pointer["archive_head_sha256"]
            or root.get("bucket_count") != pointer["bucket_count"]
            or root.get("operation_count") != pointer["operation_count"]
            or not isinstance(root.get("buckets"), dict)
        ):
            raise ExactArchiveIndexIntegrityError("archive index root does not match pointer")
        total = 0
        for bucket, metadata in root["buckets"].items():
            if (
                not isinstance(bucket, str)
                or len(bucket) != self._bucket_hex_width
                or any(ch not in "0123456789abcdef" for ch in bucket)
                or not isinstance(metadata, dict)
                or set(metadata) != {"sha256", "count"}
                or not isinstance(metadata.get("sha256"), str)
                or len(metadata["sha256"]) != 64
                or not isinstance(metadata.get("count"), int)
                or isinstance(metadata.get("count"), bool)
                or metadata["count"] < 1
            ):
                raise ExactArchiveIndexIntegrityError("archive root bucket metadata is malformed")
            total += metadata["count"]
        if total != root["operation_count"]:
            raise ExactArchiveIndexIntegrityError(
                "archive root bucket counts do not sum to operation_count"
            )
        if (total == 0) != (not root["buckets"]):
            raise ExactArchiveIndexIntegrityError("empty root bucket map is inconsistent")
        return root

    def _read_shard(
        self,
        digest: str,
        *,
        scope: str,
        bucket: str,
        expected_count: int,
    ) -> dict[str, Any]:
        shard = self._read_json(digest)
        if (
            set(shard) != self._SHARD_FIELDS
            or shard.get("schema_version") != 1
            or shard.get("scope") != scope
            or shard.get("bucket") != bucket
            or not isinstance(shard.get("entries"), list)
            or len(shard["entries"]) != expected_count
        ):
            raise ExactArchiveIndexIntegrityError("archive index shard schema/count mismatch")
        previous = ""
        for entry in shard["entries"]:
            if not isinstance(entry, dict) or set(entry) != self._ENTRY_FIELDS:
                raise ExactArchiveIndexIntegrityError("archive index entry schema mismatch")
            key = entry.get("operation_key")
            if (
                not isinstance(key, str)
                or len(key) != 64
                or any(ch not in "0123456789abcdef" for ch in key)
                or self._bucket(key) != bucket
                or key <= previous
                or not isinstance(entry.get("batch_sha256"), str)
                or len(entry["batch_sha256"]) != 64
                or not isinstance(entry.get("batch_generation"), int)
                or isinstance(entry.get("batch_generation"), bool)
                or entry["batch_generation"] < 1
                or not isinstance(entry.get("record_index"), int)
                or isinstance(entry.get("record_index"), bool)
                or entry["record_index"] < 0
                or not isinstance(entry.get("record_sha256"), str)
                or len(entry["record_sha256"]) != 64
            ):
                raise ExactArchiveIndexIntegrityError(
                    "archive index entries are malformed or unsorted"
                )
            previous = key
        return shard

    def _pointer(
        self,
        *,
        scope: str,
        generation: int,
        root_sha256: str,
        archive_head_sha256: str,
        operation_count: int,
    ) -> dict[str, Any]:
        return {
            "scope": scope,
            "index_generation": generation,
            "index_head_sha256": root_sha256,
            "archive_generation": generation,
            "archive_head_sha256": archive_head_sha256,
            "operation_count": operation_count,
            "bucket_count": self.bucket_count,
        }

    def build_from_chain(
        self,
        *,
        scope: str,
        archive_head_sha256: str,
        archive_generation: int,
        expected_operation_count: int,
    ) -> dict[str, Any]:
        """Backfill the exact index from a complete, verified legacy manifest chain."""
        if (
            not isinstance(archive_generation, int)
            or isinstance(archive_generation, bool)
            or archive_generation < 1
            or not isinstance(expected_operation_count, int)
            or isinstance(expected_operation_count, bool)
            or expected_operation_count < 0
        ):
            raise ExactArchiveIndexPolicyError("invalid archive generation/count")
        manifests: list[tuple[str, dict[str, Any]]] = []
        digest: str | None = archive_head_sha256
        generation = archive_generation
        while digest is not None:
            batch = self._read_batch(
                digest, expected_scope=scope, expected_generation=generation
            )
            manifests.append((digest, batch))
            digest = batch["previous_batch_sha256"]
            if digest is not None and (
                not isinstance(digest, str) or len(digest) != 64
            ):
                raise ExactArchiveIndexIntegrityError("archive chain pointer is malformed")
            generation -= 1
        if generation != 0:
            raise ExactArchiveIndexIntegrityError("archive chain is incomplete")
        manifests.reverse()

        entries_by_bucket: dict[str, list[dict[str, Any]]] = {}
        seen: set[str] = set()
        for batch_digest, batch in manifests:
            for index, row in enumerate(batch["records"]):
                if (
                    not isinstance(row, dict)
                    or set(row) != {"operation_key", "record"}
                    or not isinstance(row["record"], dict)
                    or row["record"].get("scope") != scope
                ):
                    raise ExactArchiveIndexIntegrityError("legacy archive row is malformed")
                key = operation_index_key(scope, row["record"]["idempotency_key"])
                if row["operation_key"] != key or key in seen:
                    raise ExactArchiveIndexIntegrityError(
                        "legacy archive row key is invalid or duplicated"
                    )
                seen.add(key)
                record_digest = self._sha256(canonical_json_bytes(row["record"]))
                bucket = self._bucket(key)
                entries_by_bucket.setdefault(bucket, []).append(
                    {
                        "operation_key": key,
                        "batch_sha256": batch_digest,
                        "batch_generation": int(batch["generation"]),
                        "record_index": index,
                        "record_sha256": record_digest,
                    }
                )
        if len(seen) != expected_operation_count:
            raise ExactArchiveIndexIntegrityError(
                "legacy archive chain count differs from expected_operation_count"
            )

        buckets: dict[str, dict[str, Any]] = {}
        for bucket, entries in sorted(entries_by_bucket.items()):
            entries.sort(key=lambda item: item["operation_key"])
            shard = {
                "schema_version": 1,
                "scope": scope,
                "bucket": bucket,
                "entries": entries,
            }
            raw = canonical_json_bytes(shard)
            buckets[bucket] = {
                "sha256": self._put_verified(raw),
                "count": len(entries),
            }

        root = {
            "schema_version": 1,
            "scope": scope,
            "generation": archive_generation,
            "archive_head_sha256": archive_head_sha256,
            "previous_index_sha256": None,
            "bucket_count": self.bucket_count,
            "operation_count": len(seen),
            "buckets": buckets,
        }
        root_raw = canonical_json_bytes(root)
        root_digest = self._put_verified(root_raw)
        pointer = self._pointer(
            scope=scope,
            generation=archive_generation,
            root_sha256=root_digest,
            archive_head_sha256=archive_head_sha256,
            operation_count=len(seen),
        )
        self._read_root(pointer)
        return pointer

    def append_batch(
        self,
        *,
        previous_pointer: dict[str, Any],
        batch_sha256: str,
    ) -> dict[str, Any]:
        """Prepare a new immutable index root for exactly the next archive batch."""
        root = self._read_root(previous_pointer)
        scope = previous_pointer["scope"]
        next_generation = int(previous_pointer["archive_generation"]) + 1
        batch = self._read_batch(
            batch_sha256, expected_scope=scope, expected_generation=next_generation
        )
        if batch["previous_batch_sha256"] != previous_pointer["archive_head_sha256"]:
            raise ExactArchiveIndexConflictError(
                "archive batch does not extend the indexed archive head"
            )

        changed: dict[str, list[dict[str, Any]]] = {}
        new_keys: set[str] = set()
        for index, row in enumerate(batch["records"]):
            if (
                not isinstance(row, dict)
                or set(row) != {"operation_key", "record"}
                or not isinstance(row["record"], dict)
                or row["record"].get("scope") != scope
            ):
                raise ExactArchiveIndexIntegrityError("new archive batch row is malformed")
            key = operation_index_key(scope, row["record"]["idempotency_key"])
            if row["operation_key"] != key or key in new_keys:
                raise ExactArchiveIndexConflictError("new batch contains duplicate or invalid keys")
            new_keys.add(key)
            bucket = self._bucket(key)
            changed.setdefault(bucket, []).append(
                {
                    "operation_key": key,
                    "batch_sha256": batch_sha256,
                    "batch_generation": next_generation,
                    "record_index": index,
                    "record_sha256": self._sha256(canonical_json_bytes(row["record"])),
                }
            )

        buckets = {
            key: dict(value) for key, value in root["buckets"].items()
        }
        for bucket, fresh_entries in changed.items():
            old_meta = buckets.get(bucket)
            merged = []
            if old_meta is not None:
                old_shard = self._read_shard(
                    old_meta["sha256"],
                    scope=scope,
                    bucket=bucket,
                    expected_count=old_meta["count"],
                )
                merged.extend(old_shard["entries"])
            existing_keys = {item["operation_key"] for item in merged}
            if existing_keys.intersection(item["operation_key"] for item in fresh_entries):
                raise ExactArchiveIndexConflictError(
                    "archive append reuses an existing idempotency index key"
                )
            merged.extend(fresh_entries)
            merged.sort(key=lambda item: item["operation_key"])
            shard = {
                "schema_version": 1,
                "scope": scope,
                "bucket": bucket,
                "entries": merged,
            }
            shard_digest = self._put_verified(canonical_json_bytes(shard))
            buckets[bucket] = {"sha256": shard_digest, "count": len(merged)}

        operation_count = int(root["operation_count"]) + len(new_keys)
        new_root = {
            "schema_version": 1,
            "scope": scope,
            "generation": next_generation,
            "archive_head_sha256": batch_sha256,
            "previous_index_sha256": previous_pointer["index_head_sha256"],
            "bucket_count": self.bucket_count,
            "operation_count": operation_count,
            "buckets": buckets,
        }
        root_digest = self._put_verified(canonical_json_bytes(new_root))
        pointer = self._pointer(
            scope=scope,
            generation=next_generation,
            root_sha256=root_digest,
            archive_head_sha256=batch_sha256,
            operation_count=operation_count,
        )
        self._read_root(pointer)
        return pointer

    def lookup(
        self,
        pointer: dict[str, Any],
        *,
        idempotency_key: str,
        expected_archive_operation_count: int,
    ) -> dict[str, Any] | None:
        """Return an exact archived operation or exact-not-found; never bloom-only.

        expected_archive_operation_count must come from the separately read,
        authoritative Coordinator scope record, not from the index pointer.
        """
        if (
            not isinstance(expected_archive_operation_count, int)
            or isinstance(expected_archive_operation_count, bool)
            or expected_archive_operation_count < 0
            or not isinstance(pointer, dict)
            or pointer.get("operation_count") != expected_archive_operation_count
        ):
            raise ExactArchiveIndexIntegrityError(
                "index count differs from authoritative Coordinator archive count"
            )
        self.last_lookup_object_reads = 0
        root = self._read_root(pointer)
        self.last_lookup_object_reads += 1
        scope = pointer["scope"]
        key = operation_index_key(scope, idempotency_key)
        bucket = self._bucket(key)
        metadata = root["buckets"].get(bucket)
        if metadata is None:
            # Root is authenticated by the authoritative Coordinator pointer;
            # bucket counts must account for the complete indexed population.
            if sum(meta["count"] for meta in root["buckets"].values()) != root["operation_count"]:
                raise ExactArchiveIndexIntegrityError("index root is not complete")
            return None
        shard = self._read_shard(
            metadata["sha256"],
            scope=scope,
            bucket=bucket,
            expected_count=metadata["count"],
        )
        self.last_lookup_object_reads += 1
        keys = [entry["operation_key"] for entry in shard["entries"]]
        position = bisect.bisect_left(keys, key)
        if position >= len(keys) or keys[position] != key:
            return None
        entry = shard["entries"][position]
        batch = self._read_batch(
            entry["batch_sha256"],
            expected_scope=scope,
            expected_generation=entry["batch_generation"],
        )
        self.last_lookup_object_reads += 1
        try:
            row = batch["records"][entry["record_index"]]
        except IndexError as exc:
            raise ExactArchiveIndexIntegrityError(
                "index points outside the archive batch"
            ) from exc
        if (
            not isinstance(row, dict)
            or row.get("operation_key") != key
            or not isinstance(row.get("record"), dict)
            or row["record"].get("scope") != scope
            or row["record"].get("idempotency_key") != idempotency_key
            or self._sha256(canonical_json_bytes(row["record"])) != entry["record_sha256"]
        ):
            raise ExactArchiveIndexIntegrityError(
                "index target does not match the exact requested operation"
            )
        return dict(row["record"])

    def verify_against_chain(
        self,
        pointer: dict[str, Any],
        *,
        expected_archive_count: int,
    ) -> dict[str, Any]:
        """Full backfill/restore audit: compare every exact key to the manifest chain."""
        root = self._read_root(pointer)
        expected: dict[str, tuple[str, int, str]] = {}
        digest: str | None = pointer["archive_head_sha256"]
        generation = int(pointer["archive_generation"])
        chain_count = 0
        while digest is not None:
            batch = self._read_batch(
                digest, expected_scope=pointer["scope"], expected_generation=generation
            )
            for index, row in enumerate(batch["records"]):
                key = operation_index_key(pointer["scope"], row["record"]["idempotency_key"])
                if row["operation_key"] != key or key in expected:
                    raise ExactArchiveIndexIntegrityError("archive chain contains duplicate/invalid keys")
                expected[key] = (
                    digest,
                    generation,
                    self._sha256(canonical_json_bytes(row["record"])),
                )
                chain_count += 1
            digest = batch["previous_batch_sha256"]
            generation -= 1
        if generation != 0 or chain_count != expected_archive_count:
            raise ExactArchiveIndexIntegrityError("archive chain generation/count mismatch")

        observed: dict[str, tuple[str, int, str]] = {}
        for bucket, metadata in root["buckets"].items():
            shard = self._read_shard(
                metadata["sha256"],
                scope=pointer["scope"],
                bucket=bucket,
                expected_count=metadata["count"],
            )
            for entry in shard["entries"]:
                observed[entry["operation_key"]] = (
                    entry["batch_sha256"],
                    entry["batch_generation"],
                    entry["record_sha256"],
                )
        if observed != expected or len(observed) != root["operation_count"]:
            raise ExactArchiveIndexIntegrityError(
                "exact index does not cover the full committed archive chain"
            )
        if root["operation_count"] != expected_archive_count:
            raise ExactArchiveIndexIntegrityError("index operation count mismatch")
        return {
            "scope": pointer["scope"],
            "generation": pointer["index_generation"],
            "operation_count": len(observed),
            "bucket_count": len(root["buckets"]),
            "index_sha256": pointer["index_head_sha256"],
            "verified": True,
        }
