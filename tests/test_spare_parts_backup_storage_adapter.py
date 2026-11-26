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
    ProviderTransientError,
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
            receipt = json.loads(record.data)
            receipt["backup_id"] = "tampered-id"
            tampered = json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode("utf-8")
            provider._objects[key] = type(record)(key, tampered, record.content_sha256, len(tampered), record.version_id)
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



    def test_mock_provider_enforces_principal_action_and_prefix_scope(self):
        provider = MockObjectStorageProvider(
            principal_id="writer-a",
            tenant_id="tenant-a",
            allowed_prefixes=("cnc/site-a/",),
            allowed_actions=("object:write",),
        )
        provider.put_if_absent("cnc/site-a/object", b"safe")
        with self.assertRaises(BackupStorageError):
            provider.get_object("cnc/site-a/object")
        with self.assertRaises(BackupStorageError):
            provider.put_if_absent("cnc/site-b/object", b"blocked")
        self.assertEqual(provider.audit_log[-1]["outcome"], "DENY")
        self.assertEqual(provider.audit_log[-1]["principal_id"], "writer-a")
        self.assertEqual(provider.audit_log[-1]["tenant_id"], "tenant-a")
        self.assertNotIn("safe", json.dumps(provider.audit_log))

    def test_mock_provider_tenant_namespaces_are_isolated(self):
        first = MockObjectStorageProvider(tenant_id="tenant-one")
        second = MockObjectStorageProvider(tenant_id="tenant-two")
        first.put_if_absent("cnc/shared/key", b"tenant-one")
        with self.assertRaises(BackupStorageError):
            second.get_object("cnc/shared/key")
        self.assertTrue(first.capabilities.tenant_isolation)
        self.assertEqual(first.capabilities.identity_authentication, "MOCK_PRINCIPAL_ONLY_NO_CREDENTIALS")

    def test_multipart_upload_resumes_from_verified_parts(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            backup = make_backup(base)
            provider = MockObjectStorageProvider(fail_after_parts=2)
            adapter = BackupStorageAdapter(
                provider, multipart_threshold_bytes=1, multipart_part_size_bytes=64
            )
            with self.assertRaises(BackupStorageError):
                adapter.publish_backup(backup, prefix="cnc/ch17")
            self.assertGreaterEqual(len(provider._multipart), 1)
            provider.fail_after_parts = None
            published = adapter.publish_backup(backup, prefix="cnc/ch17")
            self.assertEqual(published["result"], "PUBLISHED")
            self.assertEqual(published["payload_object_count"], 4)
            self.assertEqual(provider._multipart, {})
            self.assertEqual(
                adapter.verify_stored_backup(prefix="cnc/ch17", backup_id="adapter-test-001")["result"],
                "VERIFIED",
            )

    def test_multipart_part_is_idempotent_but_rejects_changed_bytes(self):
        provider = MockObjectStorageProvider()
        provider.begin_multipart_upload("cnc/ch17/object", "session-1")
        from scripts.spare_parts_backup_storage_adapter import _sha
        provider.put_multipart_part("cnc/ch17/object", "session-1", 1, b"part-a", _sha(b"part-a"))
        same = provider.put_multipart_part("cnc/ch17/object", "session-1", 1, b"part-a", _sha(b"part-a"))
        self.assertEqual(same.content_sha256, _sha(b"part-a"))
        with self.assertRaises(BackupStorageConflict):
            provider.put_multipart_part("cnc/ch17/object", "session-1", 1, b"other", _sha(b"other"))

    def test_multipart_checksum_and_sequence_are_enforced(self):
        provider = MockObjectStorageProvider()
        provider.begin_multipart_upload("cnc/ch17/object", "session-2")
        with self.assertRaises(BackupStorageError):
            provider.put_multipart_part("cnc/ch17/object", "session-2", 1, b"part-a", "bad-digest")
        from scripts.spare_parts_backup_storage_adapter import _sha
        provider.put_multipart_part("cnc/ch17/object", "session-2", 2, b"part-b", _sha(b"part-b"))
        with self.assertRaises(BackupStorageError):
            provider.complete_multipart_upload(
                "cnc/ch17/object", "session-2",
                expected_part_count=2, expected_size_bytes=6, expected_sha256=_sha(b"part-b")
            )

    def test_abort_removes_only_unfinished_multipart_staging(self):
        provider = MockObjectStorageProvider()
        existing = provider.put_if_absent("cnc/ch17/complete", b"committed")
        provider.begin_multipart_upload("cnc/ch17/pending", "session-3")
        from scripts.spare_parts_backup_storage_adapter import _sha
        provider.put_multipart_part("cnc/ch17/pending", "session-3", 1, b"temp", _sha(b"temp"))
        provider.abort_multipart_upload("cnc/ch17/pending", "session-3")
        self.assertEqual(provider.get_object("cnc/ch17/complete").data, b"committed")
        self.assertEqual(provider.list_multipart_uploads("cnc/ch17"), [])
        self.assertEqual(existing.data, b"committed")
        self.assertFalse(hasattr(provider, "delete_object"))

    def test_prefix_inventory_classifies_uncommitted_objects_without_deleting(self):
        provider = MockObjectStorageProvider()
        provider.put_if_absent("cnc/ch17/backup-orphan-001/ledger.json", b"partial")
        provider.begin_multipart_upload("cnc/ch17/backup-pending-001/snapshot.json", "upload-pending")
        from scripts.spare_parts_backup_storage_adapter import _sha
        provider.put_multipart_part(
            "cnc/ch17/backup-pending-001/snapshot.json", "upload-pending", 1, b"part", _sha(b"part")
        )
        adapter = BackupStorageAdapter(provider)
        report = adapter.inventory_backup_objects(prefix="cnc/ch17")
        self.assertEqual(report["result"], "INVENTORY_COMPLETE")
        self.assertEqual(report["backups"][0]["status"], "UNCOMMITTED_ORPHAN_CANDIDATE")
        self.assertEqual(len(report["incomplete_multipart_uploads"]), 1)
        self.assertFalse(report["destructive_operations"])
        self.assertFalse(report["automatic_reclamation"])
        self.assertFalse(report["backups"][0]["reclamation_executable"])
        self.assertEqual(report["backups"][0]["approval_status"], "PROPOSED_NOT_APPROVED")
        self.assertFalse(hasattr(provider, "delete_object"))

    def test_inventory_verifies_published_package_and_flags_missing_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            backup = make_backup(base)
            provider = MockObjectStorageProvider()
            adapter = BackupStorageAdapter(provider)
            adapter.publish_backup(backup, prefix="cnc/ch17")
            report = adapter.inventory_backup_objects(prefix="cnc/ch17")
            self.assertEqual(report["backups"][0]["status"], "PUBLISHED_VERIFIED")
            del provider._objects["cnc/ch17/backup-adapter-test-001/snapshot.json"]
            report = adapter.inventory_backup_objects(prefix="cnc/ch17")
            self.assertEqual(
                report["backups"][0]["status"],
                "PUBLISHED_PACKAGE_INCOMPLETE_OR_UNEXPECTED_OBJECTS",
            )

    def test_inventory_is_prefix_scoped_and_requires_list_permission(self):
        provider = MockObjectStorageProvider(allowed_actions=("object:write", "object:read"))
        adapter = BackupStorageAdapter(provider)
        with self.assertRaises(BackupStorageError):
            adapter.inventory_backup_objects(prefix="cnc/ch17")

    def test_filesystem_provider_scoped_inventory_returns_metadata_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            provider = FileSystemStorageProvider(Path(tmp) / "objects")
            provider.put_if_absent("cnc/ch17/object-a", b"alpha")
            provider.put_if_absent("cnc/ch18/object-b", b"beta")
            rows = provider.list_objects("cnc/ch17")
            self.assertEqual([row.key for row in rows], ["cnc/ch17/object-a"])
            self.assertEqual(rows[0].size_bytes, 5)
            self.assertFalse(hasattr(rows[0], "data"))


    def test_retry_uses_bounded_exponential_backoff_for_transient_throttling(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            backup = make_backup(base)
            delays = []
            provider = MockObjectStorageProvider(transient_failures={"get": 2})
            adapter = BackupStorageAdapter(
                provider,
                retry_max_attempts=4,
                retry_base_delay_seconds=0.25,
                retry_max_delay_seconds=0.5,
                sleep_fn=delays.append,
            )
            result = adapter.publish_backup(backup, prefix="cnc/ch17")
            self.assertEqual(result["result"], "PUBLISHED")
            self.assertEqual(delays[:2], [0.25, 0.5])

    def test_put_response_timeout_after_server_commit_is_idempotently_retried(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            backup = make_backup(base)
            provider = MockObjectStorageProvider(timeout_after_put_number=5)
            adapter = BackupStorageAdapter(
                provider, retry_base_delay_seconds=0, sleep_fn=lambda _: None
            )
            result = adapter.publish_backup(backup, prefix="cnc/ch17")
            self.assertEqual(result["result"], "PUBLISHED")
            receipt_key = "cnc/ch17/backup-adapter-test-001/" + RECEIPT_NAME
            self.assertEqual(provider.get_object(receipt_key).data, provider._objects[receipt_key].data)
            self.assertEqual(provider._successful_puts, 5)
            self.assertEqual(adapter.verify_stored_backup(prefix="cnc/ch17", backup_id="adapter-test-001")["result"], "VERIFIED")

    def test_read_after_write_visibility_delay_is_retried(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            backup = make_backup(base)
            provider = MockObjectStorageProvider(visibility_delay_reads=1)
            adapter = BackupStorageAdapter(
                provider, retry_max_attempts=2,
                retry_base_delay_seconds=0, sleep_fn=lambda _: None,
            )
            result = adapter.publish_backup(backup, prefix="cnc/ch17")
            self.assertEqual(result["result"], "PUBLISHED")
            self.assertGreaterEqual(sum(provider._reads_by_key.values()), 5)

    def test_read_after_write_delay_exhaustion_fails_closed_then_can_verify_later(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            backup = make_backup(base)
            provider = MockObjectStorageProvider(visibility_delay_reads=10)
            adapter = BackupStorageAdapter(
                provider, retry_max_attempts=2,
                retry_base_delay_seconds=0, sleep_fn=lambda _: None,
            )
            with self.assertRaises(BackupStorageError):
                adapter.publish_backup(backup, prefix="cnc/ch17")
            receipt_key = "cnc/ch17/backup-adapter-test-001/" + RECEIPT_NAME
            self.assertIn(receipt_key, provider._objects)
            provider.visibility_delay_reads = 0
            self.assertEqual(
                adapter.verify_stored_backup(prefix="cnc/ch17", backup_id="adapter-test-001")["result"],
                "VERIFIED",
            )

    def test_pinned_backup_version_survives_newer_current_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            backup = make_backup(base)
            provider = MockObjectStorageProvider(object_versioning=True)
            adapter = BackupStorageAdapter(provider)
            adapter.publish_backup(backup, prefix="cnc/ch17")
            receipt_key = "cnc/ch17/backup-adapter-test-001/" + RECEIPT_NAME
            receipt = json.loads(provider.get_object(receipt_key).data)
            ledger_row = next(row for row in receipt["payload_objects"] if row["file_name"] == "ledger.json")
            old_version = ledger_row["version_id"]
            provider.inject_new_version_for_test(ledger_row["object_key"], b"external-newer-version")
            current = provider.get_object(ledger_row["object_key"])
            self.assertNotEqual(current.version_id, old_version)
            verified = adapter.verify_stored_backup(prefix="cnc/ch17", backup_id="adapter-test-001")
            self.assertEqual(verified["result"], "VERIFIED")

    def test_missing_pinned_backup_version_is_not_replaced_with_latest(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            backup = make_backup(base)
            provider = MockObjectStorageProvider(object_versioning=True)
            adapter = BackupStorageAdapter(provider)
            adapter.publish_backup(backup, prefix="cnc/ch17")
            receipt_key = "cnc/ch17/backup-adapter-test-001/" + RECEIPT_NAME
            receipt = json.loads(provider.get_object(receipt_key).data)
            ledger_row = next(row for row in receipt["payload_objects"] if row["file_name"] == "ledger.json")
            old_version = ledger_row["version_id"]
            provider.inject_new_version_for_test(ledger_row["object_key"], b"external-newer-version")
            provider.remove_version_for_test(ledger_row["object_key"], old_version)
            with self.assertRaises(BackupStorageError):
                adapter.verify_stored_backup(prefix="cnc/ch17", backup_id="adapter-test-001")

    def test_multipart_part_commit_timeout_retries_same_part(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            backup = make_backup(base)
            provider = MockObjectStorageProvider(timeout_after_part_number=1)
            adapter = BackupStorageAdapter(
                provider,
                multipart_threshold_bytes=1,
                multipart_part_size_bytes=128,
                retry_base_delay_seconds=0,
                sleep_fn=lambda _: None,
            )
            result = adapter.publish_backup(backup, prefix="cnc/ch17")
            self.assertEqual(result["result"], "PUBLISHED")
            self.assertEqual(provider._multipart, {})
            self.assertEqual(adapter.verify_stored_backup(prefix="cnc/ch17", backup_id="adapter-test-001")["result"], "VERIFIED")

    def test_multipart_complete_response_loss_recovers_committed_object(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            backup = make_backup(base)
            provider = MockObjectStorageProvider(timeout_after_complete_commit=True)
            adapter = BackupStorageAdapter(
                provider,
                multipart_threshold_bytes=1,
                multipart_part_size_bytes=128,
                retry_base_delay_seconds=0,
                sleep_fn=lambda _: None,
            )
            result = adapter.publish_backup(backup, prefix="cnc/ch17")
            self.assertEqual(result["result"], "PUBLISHED")
            self.assertEqual(provider._multipart, {})
            self.assertEqual(len(provider._objects), 5)

    def test_permanent_provider_error_is_not_retried(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            backup = make_backup(base)
            delays = []
            provider = MockObjectStorageProvider(fail_after_puts=0)
            adapter = BackupStorageAdapter(
                provider, retry_max_attempts=5,
                retry_base_delay_seconds=1, sleep_fn=delays.append,
            )
            with self.assertRaises(BackupStorageError):
                adapter.publish_backup(backup, prefix="cnc/ch17")
            self.assertEqual(delays, [])
            self.assertEqual(provider._objects, {})


    def test_retry_after_hint_is_respected_but_capped(self):
        class RetryAfterProvider(MockObjectStorageProvider):
            def __init__(self):
                super().__init__()
                self.raise_retry_after = True

            def get_object(self, key, *, version_id=None):
                if self.raise_retry_after:
                    self.raise_retry_after = False
                    raise ProviderTransientError(
                        "mock throttling with Retry-After",
                        retry_after_seconds=10.0,
                    )
                return super().get_object(key, version_id=version_id)

        provider = RetryAfterProvider()
        provider.put_if_absent("cnc/ch17/retry-after-object", b"payload")
        delays = []
        adapter = BackupStorageAdapter(
            provider,
            retry_max_attempts=3,
            retry_base_delay_seconds=0.5,
            retry_max_delay_seconds=2.0,
            sleep_fn=delays.append,
        )
        result = adapter._provider_call(
            "get_object",
            lambda: provider.get_object("cnc/ch17/retry-after-object"),
        )
        self.assertEqual(result.data, b"payload")
        self.assertEqual(delays, [2.0])

if __name__ == "__main__":
    unittest.main()
