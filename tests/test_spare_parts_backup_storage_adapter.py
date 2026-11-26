from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.spare_parts_backup_storage_adapter import (
    BackupStorageAdapter,
    BackupStorageConflict,
    BackupStorageError,
    FileSystemStorageProvider,
    MockObjectStorageProvider,
    RECEIPT_NAME,
    PAYLOAD_FILES,
    _synthetic_ledger,
)
from scripts.spare_parts_inventory_ledger_persistence import create_backup, publish_generation, recover_current


def make_backup(base: Path, backup_id: str = "adapter-test-001") -> Path:
    source = base / "source"
    ledger, snapshot = _synthetic_ledger()
    publish_generation(source, ledger, snapshot, "adapter-generation-001")
    result = create_backup(source, base / "backups", backup_id)
    return Path(result["backup_path"])


class BackupStorageAdapterTests(unittest.TestCase):
    def test_mock_provider_publish_verify_and_restore(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            backup = make_backup(base)
            provider = MockObjectStorageProvider()
            adapter = BackupStorageAdapter(provider)
            published = adapter.publish_backup(backup, prefix="cnc/ch17")
            self.assertEqual(published["result"], "PUBLISHED")
            self.assertEqual(published["payload_object_count"], 4)
            verified = adapter.verify_stored_backup(prefix="cnc/ch17", backup_id="adapter-test-001")
            self.assertEqual(verified["result"], "VERIFIED")
            target = base / "restored"
            restored = adapter.restore_from_provider(prefix="cnc/ch17", backup_id="adapter-test-001", target_root=target)
            self.assertEqual(restored["result"], "RESTORED")
            self.assertEqual(recover_current(target)["ledger_record_count"], 1)

    def test_publish_is_idempotent_for_identical_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            backup = make_backup(base)
            adapter = BackupStorageAdapter(MockObjectStorageProvider())
            first = adapter.publish_backup(backup, prefix="cnc/ch17")
            second = adapter.publish_backup(backup, prefix="cnc/ch17")
            self.assertEqual(first["receipt_sha256"], second["receipt_sha256"])
            self.assertEqual(second["result"], "PUBLISHED")

    def test_immutable_key_rejects_different_content(self):
        provider = MockObjectStorageProvider()
        provider.put_if_absent("cnc/object", b"first")
        with self.assertRaises(BackupStorageConflict):
            provider.put_if_absent("cnc/object", b"second")

    def test_partial_upload_has_no_receipt_and_can_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            backup = make_backup(base)
            provider = MockObjectStorageProvider(fail_after_puts=2)
            adapter = BackupStorageAdapter(provider)
            with self.assertRaises(BackupStorageError):
                adapter.publish_backup(backup, prefix="cnc/ch17")
            receipt_key = "cnc/ch17/backup-adapter-test-001/" + RECEIPT_NAME
            with self.assertRaises(BackupStorageError):
                provider.get_object(receipt_key)
            self.assertEqual(len(provider._objects), 2)
            provider.fail_after_puts = None
            result = adapter.publish_backup(backup, prefix="cnc/ch17")
            self.assertEqual(result["result"], "PUBLISHED")
            self.assertEqual(adapter.verify_stored_backup(prefix="cnc/ch17", backup_id="adapter-test-001")["result"], "VERIFIED")

    def test_changed_payload_under_existing_backup_id_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            backup = make_backup(base)
            adapter = BackupStorageAdapter(MockObjectStorageProvider())
            adapter.publish_backup(backup, prefix="cnc/ch17")
            with self.assertRaises(BackupStorageConflict):
                adapter.provider.put_if_absent("cnc/ch17/backup-adapter-test-001/ledger.json", b"tampered")

    def test_corrupt_remote_payload_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            backup = make_backup(base)
            provider = MockObjectStorageProvider()
            adapter = BackupStorageAdapter(provider)
            adapter.publish_backup(backup, prefix="cnc/ch17")
            key = "cnc/ch17/backup-adapter-test-001/ledger.json"
            record = provider._objects[key]
            provider._objects[key] = type(record)(key, record.data + b"X", record.content_sha256, record.size_bytes, record.version_id)
            with self.assertRaises(BackupStorageError):
                adapter.verify_stored_backup(prefix="cnc/ch17", backup_id="adapter-test-001")

    def test_missing_payload_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            backup = make_backup(base)
            provider = MockObjectStorageProvider()
            adapter = BackupStorageAdapter(provider)
            adapter.publish_backup(backup, prefix="cnc/ch17")
            del provider._objects["cnc/ch17/backup-adapter-test-001/snapshot.json"]
            with self.assertRaises(BackupStorageError):
                adapter.verify_stored_backup(prefix="cnc/ch17", backup_id="adapter-test-001")

    def test_receipt_corruption_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            backup = make_backup(base)
            provider = MockObjectStorageProvider()
            adapter = BackupStorageAdapter(provider)
            adapter.publish_backup(backup, prefix="cnc/ch17")
            key = "cnc/ch17/backup-adapter-test-001/" + RECEIPT_NAME
            record = provider._objects[key]
            provider._objects[key] = type(record)(key, record.data + b" ", record.content_sha256, record.size_bytes, record.version_id)
            with self.assertRaises(BackupStorageError):
                adapter.verify_stored_backup(prefix="cnc/ch17", backup_id="adapter-test-001")

    def test_restore_refuses_nonempty_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            backup = make_backup(base)
            adapter = BackupStorageAdapter(MockObjectStorageProvider())
            adapter.publish_backup(backup, prefix="cnc/ch17")
            target = base / "nonempty"
            target.mkdir()
            sentinel = target / "keep.txt"
            sentinel.write_text("unchanged")
            with self.assertRaises(Exception):
                adapter.restore_from_provider(prefix="cnc/ch17", backup_id="adapter-test-001", target_root=target)
            self.assertEqual(sentinel.read_text(), "unchanged")

    def test_filesystem_provider_is_write_once_and_reports_unclaimed_security(self):
        with tempfile.TemporaryDirectory() as tmp:
            provider = FileSystemStorageProvider(Path(tmp) / "objects")
            first = provider.put_if_absent("a/b/object.bin", b"payload")
            same = provider.put_if_absent("a/b/object.bin", b"payload")
            self.assertEqual(first.content_sha256, same.content_sha256)
            self.assertFalse(provider.capabilities.object_versioning)
            self.assertFalse(provider.capabilities.object_lock)
            self.assertIsNone(provider.capabilities.server_side_encryption)
            self.assertIsNone(provider.capabilities.transport_encryption)
            with self.assertRaises(BackupStorageConflict):
                provider.put_if_absent("a/b/object.bin", b"changed")

    def test_path_traversal_and_symlink_objects_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            provider = FileSystemStorageProvider(Path(tmp) / "objects")
            for key in ("../escape", "/absolute", "a//b", "a/./b", "a\\b"):
                with self.subTest(key=key), self.assertRaises(BackupStorageError):
                    provider.put_if_absent(key, b"x")
            outside = Path(tmp) / "outside"
            outside.write_bytes(b"external")
            link = provider.root / "linked"
            link.symlink_to(outside)
            with self.assertRaises(BackupStorageError):
                provider.get_object("linked")

    def test_version_id_is_pinned_when_mock_provider_declares_versioning(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            backup = make_backup(base)
            provider = MockObjectStorageProvider(object_versioning=True, object_lock=True)
            adapter = BackupStorageAdapter(provider)
            result = adapter.publish_backup(backup, prefix="cnc/ch17")
            self.assertTrue(result["provider_capabilities"]["object_versioning"])
            receipt_key = "cnc/ch17/backup-adapter-test-001/" + RECEIPT_NAME
            receipt = json.loads(provider.get_object(receipt_key).data)
            self.assertTrue(all(row["version_id"] for row in receipt["payload_objects"]))
            self.assertEqual(adapter.verify_stored_backup(prefix="cnc/ch17", backup_id="adapter-test-001")["result"], "VERIFIED")

    def test_self_check_is_mock_only_and_keeps_enterprise_gate_blocked(self):
        from scripts.spare_parts_backup_storage_adapter import self_check
        result = self_check()
        self.assertEqual(result["result"], "PASS")
        self.assertFalse(result["external_connections"])
        self.assertFalse(result["credentials_or_keys_used"])
        self.assertEqual(result["execution_status"], "BLOCKED_PENDING_ENTERPRISE_APPROVAL")


if __name__ == "__main__":
    unittest.main()
