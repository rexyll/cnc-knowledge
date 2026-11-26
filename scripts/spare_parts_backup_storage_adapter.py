#!/usr/bin/env python3
"""Provider-neutral, synthetic-only backup storage adapter contract.

The module ships a local filesystem provider and an in-memory mock object
provider. It intentionally has no delete, credential, KMS, encryption or
network client API. A receipt object is published last as the commit marker.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
import time
import sys
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Protocol

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.spare_parts_inventory_ledger_persistence import (
    PersistenceError,
    create_backup,
    restore_backup,
    verify_backup,
)

PAYLOAD_FILES = ("BACKUP.json", "COMMIT.json", "ledger.json", "snapshot.json")
RECEIPT_NAME = "BACKUP-RECEIPT.json"
RECEIPT_SCHEMA_VERSION = 1


class BackupStorageError(ValueError):
    """Provider or backup-object contract failure."""


class BackupStorageConflict(BackupStorageError):
    """An immutable object key already contains different content."""


class ProviderTransientError(BackupStorageError):
    """Retryable provider error; outcome_unknown means the server may have committed."""

    def __init__(self, message: str, *, retry_after_seconds: float | None = None,
                 outcome_unknown: bool = False):
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds
        self.outcome_unknown = outcome_unknown


@dataclass(frozen=True)
class ProviderCapabilities:
    provider_kind: str
    conditional_create: bool | None
    object_versioning: bool | None
    object_lock: bool | None
    server_side_encryption: bool | None
    transport_encryption: bool | None
    consistency_model: str
    identity_authentication: str
    authorization_model: str
    tenant_isolation: bool | None
    audit_logging: str
    multipart_upload: bool | None
    scoped_inventory: bool | None
    evidence_scope: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class StoredObject:
    key: str
    data: bytes
    content_sha256: str
    size_bytes: int
    version_id: str | None = None


@dataclass(frozen=True)
class ObjectMetadata:
    key: str
    content_sha256: str
    size_bytes: int
    version_id: str | None = None


@dataclass(frozen=True)
class MultipartPart:
    part_number: int
    content_sha256: str
    size_bytes: int


class MultipartObjectStorageProvider(Protocol):
    """Optional resumable multipart contract; list/abort are session-scoped only."""

    def begin_multipart_upload(self, key: str, upload_id: str) -> None: ...

    def put_multipart_part(
        self, key: str, upload_id: str, part_number: int, data: bytes, expected_sha256: str
    ) -> MultipartPart: ...

    def list_multipart_parts(self, key: str, upload_id: str) -> list[MultipartPart]: ...

    def complete_multipart_upload(
        self, key: str, upload_id: str, *, expected_part_count: int,
        expected_size_bytes: int, expected_sha256: str
    ) -> StoredObject: ...

    def abort_multipart_upload(self, key: str, upload_id: str) -> None: ...


class ScopedInventoryProvider(Protocol):
    """Read-only, prefix-scoped object and incomplete-upload inventory."""

    def list_objects(self, prefix: str) -> list[ObjectMetadata]: ...

    def list_multipart_uploads(self, prefix: str) -> list[dict[str, Any]]: ...


class ObjectStorageProvider(Protocol):
    """Minimal write-once/read interface; deliberately excludes delete/list."""

    @property
    def capabilities(self) -> ProviderCapabilities: ...

    def put_if_absent(self, key: str, data: bytes) -> StoredObject: ...

    def get_object(self, key: str, *, version_id: str | None = None) -> StoredObject: ...


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_bytes(value: dict[str, Any]) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _safe_key(key: str) -> str:
    if not isinstance(key, str) or not key or "\\" in key or "\x00" in key:
        raise BackupStorageError("object key is blank or contains an unsafe character")
    if key.startswith("/") or re.match(r"^[A-Za-z]:", key):
        raise BackupStorageError("absolute object keys are not allowed")
    parsed = PurePosixPath(key)
    parts = key.split("/")
    if parsed.is_absolute() or any(part in {"", ".", ".."} for part in parts):
        raise BackupStorageError("object key must be a normalized relative POSIX path")
    if any(part.startswith(".") for part in parts):
        raise BackupStorageError("dot-prefixed object-key components are not allowed")
    return parsed.as_posix()


def _safe_prefix(prefix: str) -> str:
    if not isinstance(prefix, str) or not prefix:
        raise BackupStorageError("object prefix is required")
    return _safe_key(prefix.rstrip("/"))


def _record(key: str, data: bytes, version_id: str | None = None) -> StoredObject:
    return StoredObject(key=key, data=data, content_sha256=_sha(data), size_bytes=len(data), version_id=version_id)


class FileSystemStorageProvider:
    """Local write-once object namespace for temporary-directory tests only."""

    def __init__(self, root: Path):
        self.root = Path(root)
        if self.root.exists() and self.root.is_symlink():
            raise BackupStorageError("provider root cannot be a symlink")
        self.root.mkdir(parents=True, exist_ok=True)
        if self.root.is_symlink() or not self.root.is_dir():
            raise BackupStorageError("provider root is not a safe directory")
        self._capabilities = ProviderCapabilities(
            provider_kind="LOCAL_FILESYSTEM",
            conditional_create=True,
            object_versioning=False,
            object_lock=False,
            server_side_encryption=None,
            transport_encryption=None,
            consistency_model="LOCAL_FILESYSTEM_ATOMIC_HARDLINK_CREATE; FSYNC_DEPENDENT",
            identity_authentication="LOCAL_PROCESS_IDENTITY_ONLY",
            authorization_model="HOST_FILESYSTEM_PERMISSIONS",
            tenant_isolation=None,
            audit_logging="HOST_OS_AUDIT_NOT_CONFIGURED",
            multipart_upload=False,
            scoped_inventory=True,
            evidence_scope="LOCAL_TEMPORARY_FILESYSTEM_TEST_ONLY",
        )

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._capabilities

    def _path(self, key: str, *, create_parents: bool) -> Path:
        normalized = _safe_key(key)
        path = self.root
        parts = normalized.split("/")
        for part in parts[:-1]:
            path = path / part
            if path.is_symlink():
                raise BackupStorageError("object-key parent is a symlink")
            if path.exists():
                if not path.is_dir():
                    raise BackupStorageError("object-key parent is not a safe directory")
            elif create_parents:
                path.mkdir()
            else:
                raise BackupStorageError("object-key parent does not exist")
        target = path / parts[-1]
        if target.is_symlink():
            raise BackupStorageError("object path cannot be a symlink")
        return target

    def put_if_absent(self, key: str, data: bytes) -> StoredObject:
        if not isinstance(data, bytes):
            raise BackupStorageError("object payload must be bytes")
        target = self._path(key, create_parents=True)
        if target.exists():
            if not target.is_file():
                raise BackupStorageError("existing object key is not a regular file")
            existing = target.read_bytes()
            if existing != data:
                raise BackupStorageConflict("immutable object key already contains different bytes")
            return _record(_safe_key(key), existing)
        staging_fd, staging_name = tempfile.mkstemp(prefix=".object-staging-", dir=target.parent)
        staging = Path(staging_name)
        try:
            with os.fdopen(staging_fd, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            try:
                os.link(staging, target)
            except FileExistsError:
                existing = target.read_bytes()
                if existing != data:
                    raise BackupStorageConflict("immutable object key was concurrently created with different bytes")
                return _record(_safe_key(key), existing)
            directory_fd = os.open(target.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
            return _record(_safe_key(key), data)
        finally:
            try:
                staging.unlink()
            except FileNotFoundError:
                pass

    def get_object(self, key: str, *, version_id: str | None = None) -> StoredObject:
        if version_id is not None:
            raise BackupStorageError("local filesystem provider does not support version IDs")
        target = self._path(key, create_parents=False)
        if target.is_symlink() or not target.is_file():
            raise BackupStorageError("object is missing or not a regular file")
        data = target.read_bytes()
        return _record(_safe_key(key), data)

    def list_objects(self, prefix: str) -> list[ObjectMetadata]:
        normalized = _safe_prefix(prefix) + "/"
        results = []
        for item in self.root.rglob("*"):
            if item.is_symlink() or not item.is_file():
                continue
            key = item.relative_to(self.root).as_posix()
            if not key.startswith(normalized):
                continue
            data = item.read_bytes()
            results.append(ObjectMetadata(key, _sha(data), len(data), None))
        return sorted(results, key=lambda item: item.key)

    def list_multipart_uploads(self, prefix: str) -> list[dict[str, Any]]:
        _safe_prefix(prefix)
        return []


class MockObjectStorageProvider:
    """In-memory object store with synthetic ACL, multipart and fault injection."""

    def __init__(
        self,
        *,
        object_versioning: bool = False,
        object_lock: bool = False,
        server_side_encryption: bool = False,
        transport_encryption: bool = False,
        fail_after_puts: int | None = None,
        fail_after_parts: int | None = None,
        timeout_after_put_number: int | None = None,
        timeout_after_part_number: int | None = None,
        timeout_after_complete_commit: bool = False,
        visibility_delay_reads: int = 0,
        transient_failures: dict[str, int] | None = None,
        principal_id: str = "mock-backup-writer",
        tenant_id: str = "synthetic-tenant",
        allowed_prefixes: tuple[str, ...] = ("cnc/", "ch17/"),
        allowed_actions: tuple[str, ...] = (
            "object:write", "object:read", "object:list_prefix", "multipart:write"
        ),
    ):
        self._objects: dict[str, StoredObject] = {}
        self._multipart: dict[tuple[str, str], dict[int, bytes]] = {}
        self.object_versioning = object_versioning
        self.object_lock = object_lock
        self.server_side_encryption = server_side_encryption
        self.transport_encryption = transport_encryption
        self.fail_after_puts = fail_after_puts
        self.fail_after_parts = fail_after_parts
        self.timeout_after_put_number = timeout_after_put_number
        self.timeout_after_part_number = timeout_after_part_number
        self.timeout_after_complete_commit = timeout_after_complete_commit
        self.visibility_delay_reads = visibility_delay_reads
        self._successful_puts = 0
        self._successful_parts = 0
        self._timeout_after_put_emitted = False
        self._timeout_after_part_emitted = False
        self._timeout_after_complete_emitted = False
        self._reads_by_key: dict[str, int] = {}
        self._versions: dict[str, dict[str, StoredObject]] = {}
        self._transient_failures = dict(transient_failures or {})
        if visibility_delay_reads < 0:
            raise BackupStorageError("visibility delay cannot be negative")
        if any(not isinstance(value, int) or value < 0 for value in self._transient_failures.values()):
            raise BackupStorageError("transient failure counts must be non-negative integers")
        self.principal_id = principal_id
        self.tenant_id = tenant_id
        self.allowed_prefixes = tuple(allowed_prefixes)
        self.allowed_actions = frozenset(allowed_actions)
        self.audit_log: list[dict[str, str]] = []
        if not self.principal_id or not self.tenant_id:
            raise BackupStorageError("mock principal and tenant identifiers are required")
        if not self.allowed_prefixes:
            raise BackupStorageError("mock provider requires at least one allowed prefix")
        self._capabilities = ProviderCapabilities(
            provider_kind="MOCK_OBJECT_STORAGE",
            conditional_create=True,
            object_versioning=object_versioning,
            object_lock=object_lock,
            server_side_encryption=server_side_encryption,
            transport_encryption=transport_encryption,
            consistency_model="IN_MEMORY_STRONG_READ_AFTER_WRITE_SIMULATION",
            identity_authentication="MOCK_PRINCIPAL_ONLY_NO_CREDENTIALS",
            authorization_model="PRINCIPAL_ACTION_AND_PREFIX_ALLOWLIST_SIMULATION",
            tenant_isolation=True,
            audit_logging="IN_MEMORY_METADATA_ONLY_AUDIT_TRACE",
            multipart_upload=True,
            scoped_inventory=True,
            evidence_scope="MOCK_DECLARATION_ONLY_NOT_PROVIDER_EVIDENCE",
        )

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._capabilities

    def _authorize(self, action: str, key: str) -> str:
        normalized = _safe_key(key)
        allowed_prefix = any(normalized.startswith(prefix) for prefix in self.allowed_prefixes)
        allowed = action in self.allowed_actions and allowed_prefix
        self.audit_log.append({
            "principal_id": self.principal_id,
            "tenant_id": self.tenant_id,
            "action": action,
            "object_key": normalized,
            "outcome": "ALLOW" if allowed else "DENY",
        })
        if not allowed:
            raise BackupStorageError("mock provider authorization denied")
        return normalized

    def _maybe_transient(self, operation: str) -> None:
        remaining = self._transient_failures.get(operation, 0)
        if remaining > 0:
            self._transient_failures[operation] = remaining - 1
            raise ProviderTransientError(
                f"injected transient provider failure during {operation}",
                retry_after_seconds=0.0,
                outcome_unknown=False,
            )

    def put_if_absent(self, key: str, data: bytes) -> StoredObject:
        normalized = self._authorize("object:write", key)
        self._maybe_transient("put")
        if not isinstance(data, bytes):
            raise BackupStorageError("object payload must be bytes")
        if self.fail_after_puts is not None and self._successful_puts >= self.fail_after_puts:
            raise BackupStorageError("injected mock provider interruption")
        if normalized in self._objects:
            existing = self._objects[normalized]
            if existing.data != data:
                raise BackupStorageConflict("immutable object key already contains different bytes")
            return existing
        self._successful_puts += 1
        version = f"mock-v{self._successful_puts:08d}" if self.object_versioning else None
        result = _record(normalized, data, version)
        self._objects[normalized] = result
        if version is not None:
            self._versions.setdefault(normalized, {})[version] = result
        if (self.timeout_after_put_number is not None
                and self._successful_puts == self.timeout_after_put_number
                and not self._timeout_after_put_emitted):
            self._timeout_after_put_emitted = True
            raise ProviderTransientError("mock write committed but response timed out",
                                         outcome_unknown=True)
        return result

    def get_object(self, key: str, *, version_id: str | None = None) -> StoredObject:
        normalized = self._authorize("object:read", key)
        self._maybe_transient("get")
        try:
            current = self._objects[normalized]
        except KeyError as exc:
            raise BackupStorageError("mock object does not exist") from exc
        reads = self._reads_by_key.get(normalized, 0)
        if reads < self.visibility_delay_reads:
            self._reads_by_key[normalized] = reads + 1
            raise ProviderTransientError("mock object is committed but not yet visible to reads",
                                         retry_after_seconds=0.0)
        if version_id is not None:
            if not self.object_versioning:
                raise BackupStorageError("provider does not support version-specific reads")
            result = self._versions.get(normalized, {}).get(version_id)
            if result is None:
                raise BackupStorageError("requested object version is unavailable")
            return result
        return current

    def inject_new_version_for_test(self, key: str, data: bytes) -> StoredObject:
        normalized = _safe_key(key)
        if not self.object_versioning:
            raise BackupStorageError("test version switch requires object versioning")
        self._successful_puts += 1
        version = f"mock-external-v{self._successful_puts:08d}"
        result = _record(normalized, data, version)
        self._versions.setdefault(normalized, {})[version] = result
        self._objects[normalized] = result
        return result

    def remove_version_for_test(self, key: str, version_id: str) -> None:
        normalized = _safe_key(key)
        self._versions.get(normalized, {}).pop(version_id, None)
        current = self._objects.get(normalized)
        if current is not None and current.version_id == version_id:
            remaining = self._versions.get(normalized, {})
            if remaining:
                self._objects[normalized] = list(remaining.values())[-1]
            else:
                self._objects.pop(normalized, None)

    def begin_multipart_upload(self, key: str, upload_id: str) -> None:
        normalized = self._authorize("multipart:write", key)
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", upload_id or ""):
            raise BackupStorageError("multipart upload ID is invalid")
        if normalized in self._objects:
            raise BackupStorageConflict("cannot open a multipart session for a completed object")
        session = self._multipart.setdefault((normalized, upload_id), {})
        if not isinstance(session, dict):
            raise BackupStorageError("multipart session metadata is corrupt")

    def put_multipart_part(
        self, key: str, upload_id: str, part_number: int, data: bytes, expected_sha256: str
    ) -> MultipartPart:
        normalized = self._authorize("multipart:write", key)
        self._maybe_transient("put_part")
        session_key = (normalized, upload_id)
        if session_key not in self._multipart:
            raise BackupStorageError("multipart upload session does not exist")
        if not isinstance(part_number, int) or part_number < 1:
            raise BackupStorageError("multipart part number must be a positive integer")
        if not isinstance(data, bytes):
            raise BackupStorageError("multipart payload must be bytes")
        digest = _sha(data)
        if digest != expected_sha256:
            raise BackupStorageError("multipart part checksum mismatch")
        existing = self._multipart[session_key].get(part_number)
        if existing is not None:
            if existing != data:
                raise BackupStorageConflict("multipart part number already contains different bytes")
            return MultipartPart(part_number, digest, len(data))
        if self.fail_after_parts is not None and self._successful_parts >= self.fail_after_parts:
            raise BackupStorageError("injected mock multipart interruption")
        self._multipart[session_key][part_number] = data
        self._successful_parts += 1
        if (self.timeout_after_part_number is not None
                and self._successful_parts == self.timeout_after_part_number
                and not self._timeout_after_part_emitted):
            self._timeout_after_part_emitted = True
            raise ProviderTransientError("mock multipart part committed but response timed out",
                                         outcome_unknown=True)
        return MultipartPart(part_number, digest, len(data))

    def list_multipart_parts(self, key: str, upload_id: str) -> list[MultipartPart]:
        normalized = self._authorize("multipart:write", key)
        session_key = (normalized, upload_id)
        if session_key not in self._multipart:
            raise BackupStorageError("multipart upload session does not exist")
        return [
            MultipartPart(number, _sha(data), len(data))
            for number, data in sorted(self._multipart[session_key].items())
        ]

    def complete_multipart_upload(
        self, key: str, upload_id: str, *, expected_part_count: int,
        expected_size_bytes: int, expected_sha256: str
    ) -> StoredObject:
        normalized = self._authorize("multipart:write", key)
        self._maybe_transient("complete")
        session_key = (normalized, upload_id)
        try:
            parts = self._multipart[session_key]
        except KeyError as exc:
            raise BackupStorageError("multipart upload session does not exist") from exc
        if set(parts) != set(range(1, expected_part_count + 1)):
            raise BackupStorageError("multipart upload part sequence is incomplete or out of order")
        assembled = b"".join(parts[index] for index in range(1, expected_part_count + 1))
        if len(assembled) != expected_size_bytes or _sha(assembled) != expected_sha256:
            raise BackupStorageError("assembled multipart object size or digest mismatch")
        result = self.put_if_absent(normalized, assembled)
        if self.timeout_after_complete_commit and not self._timeout_after_complete_emitted:
            self._timeout_after_complete_emitted = True
            raise ProviderTransientError("mock multipart completion committed but response timed out",
                                         outcome_unknown=True)
        del self._multipart[session_key]
        return result

    def abort_multipart_upload(self, key: str, upload_id: str) -> None:
        normalized = self._authorize("multipart:write", key)
        # This only discards uncommitted multipart staging; it cannot delete objects.
        self._multipart.pop((normalized, upload_id), None)

    def list_objects(self, prefix: str) -> list[ObjectMetadata]:
        normalized_prefix = _safe_prefix(prefix) + "/"
        # Prefix-list permission applies to the requested namespace, not the bucket root.
        self._authorize("object:list_prefix", normalized_prefix + "_inventory_probe")
        return [
            ObjectMetadata(key, value.content_sha256, value.size_bytes, value.version_id)
            for key, value in sorted(self._objects.items())
            if key.startswith(normalized_prefix)
        ]

    def list_multipart_uploads(self, prefix: str) -> list[dict[str, Any]]:
        normalized_prefix = _safe_prefix(prefix) + "/"
        self._authorize("object:list_prefix", normalized_prefix + "_inventory_probe")
        return [
            {"object_key": key, "upload_id": upload_id, "part_count": len(parts)}
            for (key, upload_id), parts in sorted(self._multipart.items())
            if key.startswith(normalized_prefix)
        ]


class BackupStorageAdapter:
    """Publishes verified backup packages and restores only after verification."""

    def __init__(
        self,
        provider: ObjectStorageProvider,
        *,
        multipart_threshold_bytes: int = 1024 * 1024,
        multipart_part_size_bytes: int = 256 * 1024,
        retry_max_attempts: int = 4,
        retry_base_delay_seconds: float = 0.1,
        retry_max_delay_seconds: float = 2.0,
        sleep_fn: Callable[[float], None] = time.sleep,
    ):
        if multipart_threshold_bytes < 1 or multipart_part_size_bytes < 1:
            raise BackupStorageError("multipart thresholds and part sizes must be positive")
        if retry_max_attempts < 1 or retry_base_delay_seconds < 0 or retry_max_delay_seconds < 0:
            raise BackupStorageError("retry attempts must be positive and delays cannot be negative")
        self.provider = provider
        self.multipart_threshold_bytes = multipart_threshold_bytes
        self.multipart_part_size_bytes = multipart_part_size_bytes
        self.retry_max_attempts = retry_max_attempts
        self.retry_base_delay_seconds = retry_base_delay_seconds
        self.retry_max_delay_seconds = retry_max_delay_seconds
        self.sleep_fn = sleep_fn

    def _provider_call(self, operation: str, callback: Callable[[], Any]) -> Any:
        for attempt in range(self.retry_max_attempts):
            try:
                return callback()
            except ProviderTransientError as exc:
                if attempt + 1 >= self.retry_max_attempts:
                    raise
                delay = min(self.retry_max_delay_seconds,
                            self.retry_base_delay_seconds * (2 ** attempt))
                if exc.retry_after_seconds is not None:
                    delay = min(self.retry_max_delay_seconds,
                                max(delay, exc.retry_after_seconds))
                self.sleep_fn(delay)
        raise AssertionError(f"unreachable retry loop for {operation}")

    def _upload_payload(self, key: str, data: bytes) -> StoredObject:
        capabilities = self.provider.capabilities
        multipart_methods = (
            "begin_multipart_upload", "put_multipart_part", "list_multipart_parts",
            "complete_multipart_upload", "abort_multipart_upload",
        )
        if len(data) < self.multipart_threshold_bytes:
            return self._provider_call("put_if_absent",
                                        lambda: self.provider.put_if_absent(key, data))
        if capabilities.multipart_upload is not True:
            return self._provider_call("put_if_absent",
                                       lambda: self.provider.put_if_absent(key, data))
        if any(not callable(getattr(self.provider, name, None)) for name in multipart_methods):
            raise BackupStorageError("provider declares multipart support but omits required multipart methods")

        upload_id = "mp-" + _sha((key + ":" + _sha(data)).encode("utf-8"))[:28]
        self._provider_call("begin_multipart_upload",
                            lambda: self.provider.begin_multipart_upload(key, upload_id))
        part_size = self.multipart_part_size_bytes
        parts = [
            data[offset:offset + part_size]
            for offset in range(0, len(data), part_size)
        ]
        existing = {
            item.part_number: item
            for item in self._provider_call(
                "list_multipart_parts",
                lambda: self.provider.list_multipart_parts(key, upload_id),
            )
        }
        if set(existing) - set(range(1, len(parts) + 1)):
            raise BackupStorageConflict("multipart session contains unexpected part numbers")
        for number, part in enumerate(parts, start=1):
            digest = _sha(part)
            prior = existing.get(number)
            if prior is not None:
                if prior.content_sha256 != digest or prior.size_bytes != len(part):
                    raise BackupStorageConflict("resumed multipart part differs from source content")
                continue
            self._provider_call(
                "put_multipart_part",
                lambda: self.provider.put_multipart_part(key, upload_id, number, part, digest),
            )
        result = self._provider_call(
            "complete_multipart_upload",
            lambda: self.provider.complete_multipart_upload(
                key, upload_id, expected_part_count=len(parts),
                expected_size_bytes=len(data), expected_sha256=_sha(data),
            ),
        )
        if result.content_sha256 != _sha(data) or result.size_bytes != len(data):
            raise BackupStorageError("completed multipart object metadata mismatch")
        return result

    def inventory_backup_objects(self, *, prefix: str) -> dict[str, Any]:
        list_objects = getattr(self.provider, "list_objects", None)
        list_uploads = getattr(self.provider, "list_multipart_uploads", None)
        if not callable(list_objects) or not callable(list_uploads):
            raise BackupStorageError("provider does not support prefix-scoped read-only inventory")
        normalized = _safe_prefix(prefix)
        objects = self._provider_call("list_objects", lambda: list_objects(normalized))
        grouped: dict[str, list[ObjectMetadata]] = {}
        unclassified: list[str] = []
        marker = normalized + "/backup-"
        for item in objects:
            if not item.key.startswith(marker):
                unclassified.append(item.key)
                continue
            remainder = item.key[len(marker):]
            if "/" not in remainder:
                unclassified.append(item.key)
                continue
            backup_id, _ = remainder.split("/", 1)
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", backup_id):
                unclassified.append(item.key)
                continue
            grouped.setdefault(backup_id, []).append(item)

        backup_reports = []
        for backup_id, entries in sorted(grouped.items()):
            keys = {item.key for item in entries}
            object_prefix, payload_keys, receipt_key = self._keys(normalized, backup_id)
            expected = set(payload_keys.values()) | {receipt_key}
            unexpected = sorted(keys - expected)
            missing = sorted(expected - keys)
            if receipt_key not in keys:
                status = "UNCOMMITTED_ORPHAN_CANDIDATE"
            elif unexpected or missing:
                status = "PUBLISHED_PACKAGE_INCOMPLETE_OR_UNEXPECTED_OBJECTS"
            else:
                try:
                    verified = self.verify_stored_backup(prefix=normalized, backup_id=backup_id)
                    status = "PUBLISHED_VERIFIED"
                except BackupStorageError:
                    status = "PUBLISHED_INVALID"
                    verified = None
            backup_reports.append({
                "backup_id": backup_id,
                "object_prefix": object_prefix,
                "status": status,
                "object_count": len(entries),
                "total_size_bytes": sum(item.size_bytes for item in entries),
                "object_keys": sorted(keys),
                "missing_expected_keys": missing,
                "unexpected_keys": unexpected,
                "reclamation_recommendation": (
                    "MANUAL_REVIEW_REQUIRED" if status == "UNCOMMITTED_ORPHAN_CANDIDATE"
                    else "DO_NOT_RECLAIM_AUTOMATICALLY"
                ),
                "approval_status": "PROPOSED_NOT_APPROVED",
                "reclamation_executable": False,
            })
        multipart = self._provider_call("list_multipart_uploads", lambda: list_uploads(normalized))
        return {
            "result": "INVENTORY_COMPLETE",
            "prefix": normalized,
            "object_count": len(objects),
            "backup_count": len(backup_reports),
            "backups": backup_reports,
            "unclassified_object_keys": sorted(unclassified),
            "incomplete_multipart_uploads": multipart,
            "destructive_operations": False,
            "automatic_reclamation": False,
            "approval_status": "PROPOSED_NOT_APPROVED",
        }

    def _keys(self, prefix: str, backup_id: str) -> tuple[str, dict[str, str], str]:
        prefix = _safe_prefix(prefix)
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", backup_id or ""):
            raise BackupStorageError("backup_id must use 1-64 safe identifier characters")
        object_prefix = f"{prefix}/backup-{backup_id}"
        payload_keys = {name: f"{object_prefix}/{name}" for name in PAYLOAD_FILES}
        return object_prefix, payload_keys, f"{object_prefix}/{RECEIPT_NAME}"

    def publish_backup(self, backup_dir: Path, *, prefix: str) -> dict[str, Any]:
        backup_dir = Path(backup_dir)
        if backup_dir.is_symlink() or not backup_dir.is_dir():
            raise BackupStorageError("local backup package is missing or unsafe")
        expected_names = set(PAYLOAD_FILES)
        try:
            if {item.name for item in backup_dir.iterdir()} != expected_names:
                raise BackupStorageError("local backup package has missing or unexpected entries")
        except OSError as exc:
            raise BackupStorageError("local backup package cannot be listed") from exc

        # Snapshot bytes once, then validate that exact snapshot before publishing.
        with tempfile.TemporaryDirectory(prefix="ch17-backup-provider-stage-") as tmp:
            staged = Path(tmp) / "backup"
            staged.mkdir()
            payload_data: dict[str, bytes] = {}
            for name in PAYLOAD_FILES:
                source = backup_dir / name
                if source.is_symlink() or not source.is_file():
                    raise BackupStorageError("local backup payload is not a regular file: " + name)
                data = source.read_bytes()
                payload_data[name] = data
                (staged / name).write_bytes(data)
            try:
                verified = verify_backup(staged)
            except PersistenceError as exc:
                raise BackupStorageError("local backup package failed integrity verification") from exc

            backup_id = verified["backup_id"]
            object_prefix, payload_keys, receipt_key = self._keys(prefix, backup_id)
            payload_rows = []
            for name in PAYLOAD_FILES:
                data = payload_data[name]
                record = self._upload_payload(payload_keys[name], data)
                payload_rows.append({
                    "file_name": name,
                    "object_key": payload_keys[name],
                    "size_bytes": record.size_bytes,
                    "sha256": record.content_sha256,
                    "version_id": record.version_id,
                })
            receipt_base = {
                "schema_version": RECEIPT_SCHEMA_VERSION,
                "receipt_state": "PUBLISHED",
                "backup_id": backup_id,
                "object_prefix": object_prefix,
                "backup_manifest_sha256": verified["backup_manifest_sha256"],
                "payload_objects": payload_rows,
                "provider_kind": self.provider.capabilities.provider_kind,
            }
            receipt = {**receipt_base, "receipt_sha256": _sha(_json_bytes(receipt_base))}
            receipt_data = _json_bytes(receipt)
            receipt_record = self._provider_call(
                "put_receipt", lambda: self.provider.put_if_absent(receipt_key, receipt_data)
            )

        checked = self.verify_stored_backup(prefix=prefix, backup_id=backup_id)
        return {
            "result": "PUBLISHED",
            "backup_id": backup_id,
            "object_prefix": object_prefix,
            "receipt_key": receipt_key,
            "receipt_sha256": receipt["receipt_sha256"],
            "receipt_object_sha256": receipt_record.content_sha256,
            "payload_object_count": len(payload_rows),
            "provider_capabilities": self.provider.capabilities.to_dict(),
            "verification": checked["result"],
        }

    def _read_receipt(self, receipt_key: str) -> dict[str, Any]:
        record = self._provider_call("get_receipt", lambda: self.provider.get_object(receipt_key))
        try:
            receipt = json.loads(record.data)
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise BackupStorageError("backup receipt is malformed") from exc
        if not isinstance(receipt, dict):
            raise BackupStorageError("backup receipt root must be an object")
        digest = receipt.get("receipt_sha256")
        base = {key: value for key, value in receipt.items() if key != "receipt_sha256"}
        if not isinstance(digest, str) or _sha(_json_bytes(base)) != digest:
            raise BackupStorageError("backup receipt digest mismatch")
        return receipt

    def _download_verified(self, *, prefix: str, backup_id: str, target_dir: Path) -> dict[str, Any]:
        object_prefix, payload_keys, receipt_key = self._keys(prefix, backup_id)
        receipt = self._read_receipt(receipt_key)
        if (
            receipt.get("schema_version") != RECEIPT_SCHEMA_VERSION
            or receipt.get("receipt_state") != "PUBLISHED"
            or receipt.get("backup_id") != backup_id
            or receipt.get("object_prefix") != object_prefix
            or receipt.get("provider_kind") != self.provider.capabilities.provider_kind
        ):
            raise BackupStorageError("backup receipt identity or state mismatch")
        rows = receipt.get("payload_objects")
        if not isinstance(rows, list) or {row.get("file_name") for row in rows if isinstance(row, dict)} != set(PAYLOAD_FILES) or len(rows) != len(PAYLOAD_FILES):
            raise BackupStorageError("backup receipt payload object set is incomplete")
        target_dir.mkdir(parents=True, exist_ok=False)
        observed = {}
        for row in rows:
            name = row["file_name"]
            expected_key = payload_keys[name]
            if row.get("object_key") != expected_key:
                raise BackupStorageError("backup receipt object key does not match expected prefix")
            record = self._provider_call(
                "get_payload",
                lambda: self.provider.get_object(expected_key, version_id=row.get("version_id")),
            )
            if record.size_bytes != row.get("size_bytes") or record.content_sha256 != row.get("sha256"):
                raise BackupStorageError("stored object size or digest differs from receipt")
            (target_dir / name).write_bytes(record.data)
            observed[name] = record
        try:
            verified = verify_backup(target_dir)
        except PersistenceError as exc:
            raise BackupStorageError("downloaded backup failed package integrity verification") from exc
        if (
            verified["backup_id"] != backup_id
            or verified["backup_manifest_sha256"] != receipt.get("backup_manifest_sha256")
        ):
            raise BackupStorageError("downloaded backup manifest differs from published receipt")
        return {
            "receipt": receipt,
            "verified": verified,
            "observed_objects": observed,
        }

    def verify_stored_backup(self, *, prefix: str, backup_id: str) -> dict[str, Any]:
        with tempfile.TemporaryDirectory(prefix="ch17-backup-provider-verify-") as tmp:
            result = self._download_verified(prefix=prefix, backup_id=backup_id, target_dir=Path(tmp) / "backup")
        return {
            "result": "VERIFIED",
            "backup_id": backup_id,
            "manifest_sha256": result["verified"]["backup_manifest_sha256"],
            "payload_object_count": len(result["observed_objects"]),
            "provider_capabilities": self.provider.capabilities.to_dict(),
            "provider_evidence_scope": self.provider.capabilities.evidence_scope,
        }

    def restore_from_provider(
        self,
        *,
        prefix: str,
        backup_id: str,
        target_root: Path,
    ) -> dict[str, Any]:
        with tempfile.TemporaryDirectory(prefix="ch17-backup-provider-restore-") as tmp:
            staged_backup = Path(tmp) / "backup"
            self._download_verified(prefix=prefix, backup_id=backup_id, target_dir=staged_backup)
            restored = restore_backup(staged_backup, target_root)
        return {
            "result": "RESTORED",
            "backup_id": backup_id,
            "generation_id": restored["generation_id"],
            "ledger_record_count": restored["ledger_record_count"],
            "provider_capabilities": self.provider.capabilities.to_dict(),
            "business_rule_assertions": "NOT_EVALUATED",
            "execution_status": "BLOCKED_PENDING_ENTERPRISE_APPROVAL",
        }


def _synthetic_ledger():
    from decimal import Decimal
    from scripts.spare_parts_inventory_event_ledger import AppendOnlyEventLedger, LedgerEvent
    from scripts.spare_parts_inventory_ledger_integrity import create_snapshot
    from scripts.spare_parts_multidimensional_inventory import BalanceKey

    source = BalanceKey("HOLD", "SYN-P", "SYN-L", "SYN-B", "SYN-O", "HOLD", "EA")
    destination = BalanceKey("AVAILABLE", "SYN-P", "SYN-L", "SYN-B", "SYN-O", "RELEASED", "EA")
    ledger = AppendOnlyEventLedger()
    ledger.append(LedgerEvent(
        "SYN-BK-E1", "SYN-BK-BE1", "SYN-BK-SRC", "SYN-BK-I1",
        "2026-01-01T09:00:00+08:00", "2026-01-01T09:01:00+08:00",
        "TRANSFER", source, destination, Decimal("2")
    ))
    snapshot = create_snapshot(
        ledger, {source: Decimal("5"), destination: Decimal("0")},
        "2026-01-01T10:00:00+08:00"
    )
    return ledger, snapshot


def self_check() -> dict[str, Any]:
    from scripts.spare_parts_inventory_ledger_persistence import publish_generation

    with tempfile.TemporaryDirectory(prefix="ch17-backup-adapter-") as tmp:
        base = Path(tmp)
        source_root = base / "source-store"
        backup_parent = base / "local-backups"
        target = base / "restore-target"
        ledger, snapshot = _synthetic_ledger()
        publish_generation(source_root, ledger, snapshot, "adapter-synthetic-001")
        local_backup = create_backup(source_root, backup_parent, "adapter-smoke-001")
        provider = MockObjectStorageProvider(
            object_versioning=True,
            timeout_after_put_number=5,
            visibility_delay_reads=1,
            transient_failures={"get": 1},
        )
        adapter = BackupStorageAdapter(
            provider,
            retry_max_attempts=4,
            retry_base_delay_seconds=0,
            sleep_fn=lambda _: None,
        )
        published = adapter.publish_backup(Path(local_backup["backup_path"]), prefix="ch17/synthetic")
        verified = adapter.verify_stored_backup(prefix="ch17/synthetic", backup_id="adapter-smoke-001")
        receipt_key = "ch17/synthetic/backup-adapter-smoke-001/" + RECEIPT_NAME
        receipt = json.loads(provider.get_object(receipt_key).data)
        ledger_row = next(row for row in receipt["payload_objects"] if row["file_name"] == "ledger.json")
        provider.inject_new_version_for_test(ledger_row["object_key"], b"newer-external-version")
        pinned_after_version_switch = adapter.verify_stored_backup(
            prefix="ch17/synthetic", backup_id="adapter-smoke-001"
        )
        restored = adapter.restore_from_provider(
            prefix="ch17/synthetic", backup_id="adapter-smoke-001", target_root=target
        )
        assert published["result"] == "PUBLISHED"
        assert verified["result"] == "VERIFIED"
        assert pinned_after_version_switch["result"] == "VERIFIED"
        assert restored["result"] == "RESTORED" and restored["ledger_record_count"] == 1
        return {
            "result": "PASS",
            "provider": "MOCK_OBJECT_STORAGE",
            "upload_and_receipt_publish": "PASS",
            "remote_manifest_and_payload_verification": "PASS",
            "isolated_restore_from_provider": "PASS",
            "ambiguous_put_commit_timeout_recovered": "PASS",
            "read_after_write_and_transient_get_retried": "PASS",
            "historical_version_pinned_after_current_version_switch": "PASS",
            "retry_policy": "BOUNDED_EXPONENTIAL_NO_RANDOM_JITTER_IN_SYNTHETIC_TEST",
            "payload_object_count": published["payload_object_count"],
            "external_connections": False,
            "credentials_or_keys_used": False,
            "network_access": False,
            "delete_operations": False,
            "business_rule_assertions": "NOT_EVALUATED",
            "execution_status": "BLOCKED_PENDING_ENTERPRISE_APPROVAL",
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the synthetic backup storage adapter contract self-check.")
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--report-json", type=Path)
    args = parser.parse_args()
    if not args.self_check:
        parser.error("--self-check is required; provider CRUD is deliberately not exposed as an ad hoc CLI")
    report = self_check()
    output = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.report_json:
        args.report_json.parent.mkdir(parents=True, exist_ok=True)
        args.report_json.write_text(output, encoding="utf-8")
    print(output, end="")
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
