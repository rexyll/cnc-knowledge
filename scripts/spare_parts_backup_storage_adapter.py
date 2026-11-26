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
from typing import Any, Protocol

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


@dataclass(frozen=True)
class ProviderCapabilities:
    provider_kind: str
    conditional_create: bool | None
    object_versioning: bool | None
    object_lock: bool | None
    server_side_encryption: bool | None
    transport_encryption: bool | None
    consistency_model: str
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


class MockObjectStorageProvider:
    """In-memory object store simulator. It never contacts a remote service."""

    def __init__(
        self,
        *,
        object_versioning: bool = False,
        object_lock: bool = False,
        server_side_encryption: bool = False,
        transport_encryption: bool = False,
        fail_after_puts: int | None = None,
    ):
        self._objects: dict[str, StoredObject] = {}
        self.object_versioning = object_versioning
        self.object_lock = object_lock
        self.server_side_encryption = server_side_encryption
        self.transport_encryption = transport_encryption
        self.fail_after_puts = fail_after_puts
        self._successful_puts = 0
        self._capabilities = ProviderCapabilities(
            provider_kind="MOCK_OBJECT_STORAGE",
            conditional_create=True,
            object_versioning=object_versioning,
            object_lock=object_lock,
            server_side_encryption=server_side_encryption,
            transport_encryption=transport_encryption,
            consistency_model="IN_MEMORY_STRONG_READ_AFTER_WRITE_SIMULATION",
            evidence_scope="MOCK_DECLARATION_ONLY_NOT_PROVIDER_EVIDENCE",
        )

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._capabilities

    def put_if_absent(self, key: str, data: bytes) -> StoredObject:
        normalized = _safe_key(key)
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
        return result

    def get_object(self, key: str, *, version_id: str | None = None) -> StoredObject:
        normalized = _safe_key(key)
        try:
            result = self._objects[normalized]
        except KeyError as exc:
            raise BackupStorageError("mock object does not exist") from exc
        if version_id is not None and version_id != result.version_id:
            raise BackupStorageError("requested object version does not match the stored version")
        return result


class BackupStorageAdapter:
    """Publishes verified backup packages and restores only after verification."""

    def __init__(self, provider: ObjectStorageProvider):
        self.provider = provider

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
                record = self.provider.put_if_absent(payload_keys[name], data)
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
            receipt_record = self.provider.put_if_absent(receipt_key, receipt_data)

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
        record = self.provider.get_object(receipt_key)
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
            record = self.provider.get_object(expected_key, version_id=row.get("version_id"))
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
        provider = MockObjectStorageProvider()
        adapter = BackupStorageAdapter(provider)
        published = adapter.publish_backup(Path(local_backup["backup_path"]), prefix="ch17/synthetic")
        verified = adapter.verify_stored_backup(prefix="ch17/synthetic", backup_id="adapter-smoke-001")
        restored = adapter.restore_from_provider(
            prefix="ch17/synthetic", backup_id="adapter-smoke-001", target_root=target
        )
        assert published["result"] == "PUBLISHED"
        assert verified["result"] == "VERIFIED"
        assert restored["result"] == "RESTORED" and restored["ledger_record_count"] == 1
        return {
            "result": "PASS",
            "provider": "MOCK_OBJECT_STORAGE",
            "upload_and_receipt_publish": "PASS",
            "remote_manifest_and_payload_verification": "PASS",
            "isolated_restore_from_provider": "PASS",
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
