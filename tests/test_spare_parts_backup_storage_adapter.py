from __future__ import annotations

import json
import tempfile
import threading
import time
import unittest
from pathlib import Path

from scripts.spare_parts_backup_storage_adapter import (
    BackupStorageAdapter,
    BackupStorageConflict,
    BackupStorageError,
    FileSystemStorageProvider,
    MockObjectStorageProvider,
    ProviderTransientError,
    ProviderCircuitBreaker,
    ProviderCircuitOpenError,
    ProviderBulkheadFullError,
    ProviderAdmissionLeaseLostError,
    InMemoryProviderAdmissionCoordinator,
    ProviderRateLimitExceededError,
    ProviderTaskCancelledError,
    ProviderTaskDeadlineExceededError,
    RetryBudgetExceededError,
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


    def test_circuit_opens_after_consecutive_transient_failures_and_fails_fast(self):
        class FakeClock:
            now = 100.0
            def __call__(self):
                return self.now
            def advance(self, seconds):
                self.now += seconds

        provider = MockObjectStorageProvider()
        provider.put_if_absent("cnc/ch17/circuit-read", b"readable")
        clock = FakeClock()
        adapter = BackupStorageAdapter(
            provider,
            retry_max_attempts=1,
            circuit_failure_threshold=2,
            circuit_reset_timeout_seconds=5,
            clock_fn=clock,
        )
        provider._transient_failures["get"] = 2
        for _ in range(2):
            with self.assertRaises(ProviderTransientError):
                adapter._provider_call(
                    "get_payload", lambda: provider.get_object("cnc/ch17/circuit-read")
                )
        self.assertEqual(adapter.circuit_snapshot("read")["state"], "OPEN")
        with self.assertRaises(ProviderCircuitOpenError):
            adapter._provider_call(
                "get_payload", lambda: provider.get_object("cnc/ch17/circuit-read")
            )
        self.assertEqual(adapter._provider_call(
            "put_if_absent",
            lambda: provider.put_if_absent("cnc/ch17/circuit-write", b"write-ok"),
        ).data, b"write-ok")
        self.assertEqual(adapter.circuit_snapshot("write")["state"], "CLOSED")

    def test_half_open_probe_failure_reopens_then_success_closes_circuit(self):
        class FakeClock:
            now = 0.0
            def __call__(self):
                return self.now
            def advance(self, seconds):
                self.now += seconds

        clock = FakeClock()
        breaker = ProviderCircuitBreaker(
            failure_threshold=1,
            reset_timeout_seconds=10,
            half_open_max_probes=1,
            clock_fn=clock,
        )
        probe = breaker.acquire()
        self.assertFalse(probe)
        breaker.record_failure(probe)
        self.assertEqual(breaker.snapshot()["state"], "OPEN")
        with self.assertRaises(ProviderCircuitOpenError):
            breaker.acquire()
        clock.advance(10)
        half_open_probe = breaker.acquire()
        self.assertTrue(half_open_probe)
        breaker.record_failure(half_open_probe)
        self.assertEqual(breaker.snapshot()["state"], "OPEN")
        clock.advance(10)
        half_open_probe = breaker.acquire()
        breaker.record_success(half_open_probe)
        self.assertEqual(breaker.snapshot()["state"], "CLOSED")
        self.assertEqual(breaker.snapshot()["consecutive_failures"], 0)

    def test_half_open_circuit_allows_only_one_concurrent_probe(self):
        class FakeClock:
            def __call__(self):
                return 50.0

        breaker = ProviderCircuitBreaker(
            failure_threshold=1, reset_timeout_seconds=0,
            half_open_max_probes=1, clock_fn=FakeClock(),
        )
        breaker.record_failure(breaker.acquire())
        first_probe = breaker.acquire()
        self.assertTrue(first_probe)
        with self.assertRaises(ProviderCircuitOpenError):
            breaker.acquire()
        breaker.record_success(first_probe)
        self.assertEqual(breaker.snapshot()["state"], "CLOSED")

    def test_circuit_breakers_are_isolated_by_operation_domain(self):
        provider = MockObjectStorageProvider()
        provider.put_if_absent("cnc/ch17/read-object", b"read")
        adapter = BackupStorageAdapter(
            provider, retry_max_attempts=1, circuit_failure_threshold=1
        )
        provider._transient_failures["get"] = 1
        with self.assertRaises(ProviderTransientError):
            adapter._provider_call(
                "get_payload", lambda: provider.get_object("cnc/ch17/read-object")
            )
        self.assertEqual(adapter.circuit_snapshot("read")["state"], "OPEN")
        self.assertEqual(
            adapter._provider_call(
                "put_if_absent",
                lambda: provider.put_if_absent("cnc/ch17/write-object", b"write"),
            ).data,
            b"write",
        )
        self.assertEqual(adapter.circuit_snapshot("write")["state"], "CLOSED")

    def test_bulkhead_blocks_same_domain_but_does_not_block_other_domains(self):
        provider = MockObjectStorageProvider()
        provider.put_if_absent("cnc/ch17/read-object", b"read")
        adapter = BackupStorageAdapter(
            provider,
            bulkhead_limits={"read": 1, "write": 1, "multipart": 1, "inventory": 1},
            bulkhead_acquire_timeout_seconds=0,
        )
        entered = threading.Event()
        release = threading.Event()
        worker_errors = []

        def blocking_read():
            entered.set()
            if not release.wait(timeout=2):
                raise AssertionError("test read was not released")
            return "read-complete"

        def worker():
            try:
                adapter._provider_call("get_payload", blocking_read)
            except Exception as exc:
                worker_errors.append(exc)

        thread = threading.Thread(target=worker)
        thread.start()
        self.assertTrue(entered.wait(timeout=2))
        try:
            with self.assertRaises(ProviderBulkheadFullError):
                adapter._provider_call("get_payload", lambda: "second-read")
            self.assertEqual(
                adapter._provider_call("put_if_absent", lambda: "independent-write"),
                "independent-write",
            )
        finally:
            release.set()
            thread.join(timeout=2)
        self.assertFalse(thread.is_alive())
        self.assertEqual(worker_errors, [])

    def test_bulkhead_slot_is_released_after_provider_error(self):
        adapter = BackupStorageAdapter(
            MockObjectStorageProvider(),
            bulkhead_limits={"read": 1, "write": 1, "multipart": 1, "inventory": 1},
        )
        with self.assertRaises(BackupStorageError):
            adapter._provider_call(
                "get_payload", lambda: (_ for _ in ()).throw(BackupStorageError("permanent"))
            )
        self.assertEqual(
            adapter._provider_call("get_payload", lambda: "slot-released"),
            "slot-released",
        )

    def test_total_retry_budget_is_shared_across_nested_provider_calls(self):
        adapter = BackupStorageAdapter(
            MockObjectStorageProvider(),
            retry_max_attempts=4,
            retry_budget_total=2,
            retry_base_delay_seconds=0,
            sleep_fn=lambda _: None,
        )

        def succeeds_after_one_failure(value):
            calls = {"count": 0}
            def callback():
                calls["count"] += 1
                if calls["count"] == 1:
                    raise ProviderTransientError("temporary")
                return value
            return callback

        with adapter.retry_operation() as budget:
            self.assertEqual(adapter._provider_call(
                "put_if_absent", succeeds_after_one_failure("write")
            ), "write")
            with adapter.retry_operation() as nested:
                self.assertIs(nested, budget)
                self.assertEqual(adapter._provider_call(
                    "get_payload", succeeds_after_one_failure("read")
                ), "read")
            self.assertEqual(budget.used, 2)
            self.assertEqual(budget.remaining, 0)
            with self.assertRaises(RetryBudgetExceededError):
                adapter._provider_call(
                    "get_payload",
                    lambda: (_ for _ in ()).throw(ProviderTransientError("budget exhausted")),
                )
            self.assertEqual(budget.used, 2)

        # A later top-level operation receives a fresh task budget.
        with adapter.retry_operation() as fresh:
            self.assertEqual(fresh.used, 0)
            self.assertEqual(adapter._provider_call("get_payload", lambda: "new-task"), "new-task")

    def test_retry_budgets_are_isolated_between_concurrent_tasks(self):
        adapter = BackupStorageAdapter(
            MockObjectStorageProvider(),
            retry_max_attempts=2,
            retry_budget_total=1,
            retry_base_delay_seconds=0,
            sleep_fn=lambda _: None,
        )
        barrier = threading.Barrier(2)
        results = []
        errors = []

        def task(value):
            calls = {"count": 0}
            def callback():
                calls["count"] += 1
                if calls["count"] == 1:
                    barrier.wait(timeout=2)
                    raise ProviderTransientError("one retry per task")
                return value
            try:
                with adapter.retry_operation() as budget:
                    result = adapter._provider_call("get_payload", callback)
                    results.append((result, budget.used, budget.remaining))
            except Exception as exc:
                errors.append(exc)

        threads = [
            threading.Thread(target=task, args=("task-a",)),
            threading.Thread(target=task, args=("task-b",)),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=3)
        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertEqual(errors, [])
        self.assertCountEqual(results, [("task-a", 1, 0), ("task-b", 1, 0)])

    def test_circuit_and_bulkhead_configuration_is_validated(self):
        with self.assertRaises(BackupStorageError):
            BackupStorageAdapter(MockObjectStorageProvider(), circuit_failure_threshold=0)
        with self.assertRaises(BackupStorageError):
            BackupStorageAdapter(MockObjectStorageProvider(), retry_budget_total=-1)
        with self.assertRaises(BackupStorageError):
            BackupStorageAdapter(MockObjectStorageProvider(), bulkhead_limits={"read": 0})
        with self.assertRaises(BackupStorageError):
            BackupStorageAdapter(MockObjectStorageProvider(), bulkhead_limits={"unknown": 1})
        with self.assertRaises(BackupStorageError):
            BackupStorageAdapter(MockObjectStorageProvider(), tenant_bulkhead_limits={"": 1})
        with self.assertRaises(BackupStorageError):
            BackupStorageAdapter(MockObjectStorageProvider(), priority_aging_interval_seconds=0)


    def _wait_for_bulkhead_queue(self, adapter, expected, domain="read"):
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            if adapter.bulkhead_snapshot(domain)["waiting_count"] >= expected:
                return
            time.sleep(0.005)
        self.fail(f"expected {expected} queued provider task(s)")

    def test_priority_waiter_runs_before_normal_waiter(self):
        adapter = BackupStorageAdapter(
            MockObjectStorageProvider(),
            bulkhead_limits={"read": 1, "write": 1, "multipart": 1, "inventory": 1},
            bulkhead_acquire_timeout_seconds=2,
        )
        entered, release = threading.Event(), threading.Event()
        order, errors = [], []

        def blocker():
            entered.set()
            if not release.wait(timeout=2):
                raise AssertionError("blocking task was not released")
            return "holder"

        def holder():
            try:
                with adapter.task_context(task_id="holder", tenant_id="holder"):
                    adapter._provider_call("get_payload", blocker)
            except Exception as exc:
                errors.append(exc)

        def queued(task_id, priority):
            try:
                with adapter.task_context(task_id=task_id, tenant_id=task_id, priority=priority):
                    adapter._provider_call("get_payload", lambda: order.append(task_id))
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=holder)]
        threads[0].start()
        self.assertTrue(entered.wait(timeout=2))
        normal = threading.Thread(target=queued, args=("normal", 0))
        urgent = threading.Thread(target=queued, args=("urgent", 10))
        normal.start()
        self._wait_for_bulkhead_queue(adapter, 1)
        urgent.start()
        self._wait_for_bulkhead_queue(adapter, 2)
        release.set()
        for thread in (threads[0], normal, urgent):
            thread.join(timeout=3)
        self.assertTrue(all(not thread.is_alive() for thread in (threads[0], normal, urgent)))
        self.assertEqual(errors, [])
        self.assertEqual(order, ["urgent", "normal"])

    def test_priority_aging_prevents_a_queued_task_from_starving(self):
        class FakeClock:
            now = 100.0
            def __call__(self):
                return self.now
            def advance(self, seconds):
                self.now += seconds

        clock = FakeClock()
        adapter = BackupStorageAdapter(
            MockObjectStorageProvider(),
            bulkhead_limits={"read": 1, "write": 1, "multipart": 1, "inventory": 1},
            bulkhead_acquire_timeout_seconds=2,
            priority_aging_interval_seconds=1,
            clock_fn=clock,
        )
        entered, release = threading.Event(), threading.Event()
        order, errors = [], []

        def blocker():
            entered.set()
            if not release.wait(timeout=2):
                raise AssertionError("blocking task was not released")
            return "holder"

        def holder():
            try:
                adapter._provider_call("get_payload", blocker)
            except Exception as exc:
                errors.append(exc)

        def run_task(task_id, priority):
            try:
                with adapter.task_context(task_id=task_id, tenant_id=task_id, priority=priority):
                    adapter._provider_call("get_payload", lambda: order.append(task_id))
            except Exception as exc:
                errors.append(exc)

        hold_thread = threading.Thread(target=holder)
        hold_thread.start()
        self.assertTrue(entered.wait(timeout=2))
        older = threading.Thread(target=run_task, args=("older-low", 0))
        older.start()
        self._wait_for_bulkhead_queue(adapter, 1)
        clock.advance(10)
        newer = threading.Thread(target=run_task, args=("newer-high", 5))
        newer.start()
        self._wait_for_bulkhead_queue(adapter, 2)
        release.set()
        for thread in (hold_thread, older, newer):
            thread.join(timeout=3)
        self.assertTrue(all(not thread.is_alive() for thread in (hold_thread, older, newer)))
        self.assertEqual(errors, [])
        self.assertEqual(order, ["older-low", "newer-high"])

    def test_tenant_bulkhead_quota_isolated_from_other_tenants(self):
        adapter = BackupStorageAdapter(
            MockObjectStorageProvider(),
            bulkhead_limits={"read": 2, "write": 1, "multipart": 1, "inventory": 1},
            tenant_bulkhead_limits={"tenant-A": 1},
            bulkhead_acquire_timeout_seconds=0,
        )
        entered, release = threading.Event(), threading.Event()
        errors = []

        def blocker():
            entered.set()
            if not release.wait(timeout=2):
                raise AssertionError("tenant A task was not released")
            return "A"

        def tenant_a_holder():
            try:
                with adapter.task_context(task_id="A-holder", tenant_id="tenant-A"):
                    adapter._provider_call("get_payload", blocker)
            except Exception as exc:
                errors.append(exc)

        thread = threading.Thread(target=tenant_a_holder)
        thread.start()
        self.assertTrue(entered.wait(timeout=2))
        try:
            with adapter.task_context(task_id="A-second", tenant_id="tenant-A"):
                with self.assertRaises(ProviderBulkheadFullError):
                    adapter._provider_call("get_payload", lambda: "must-not-run")
            with adapter.task_context(task_id="B", tenant_id="tenant-B"):
                self.assertEqual(adapter._provider_call("get_payload", lambda: "tenant-B"), "tenant-B")
        finally:
            release.set()
            thread.join(timeout=2)
        self.assertFalse(thread.is_alive())
        self.assertEqual(errors, [])

    def test_task_cancellation_removes_waiter_without_calling_provider(self):
        adapter = BackupStorageAdapter(
            MockObjectStorageProvider(),
            bulkhead_limits={"read": 1, "write": 1, "multipart": 1, "inventory": 1},
            bulkhead_acquire_timeout_seconds=2,
        )
        entered, release, cancelled = threading.Event(), threading.Event(), threading.Event()
        errors, callback_calls = [], []

        def blocker():
            entered.set()
            if not release.wait(timeout=2):
                raise AssertionError("blocking task was not released")
            return "holder"

        def holder():
            with adapter.task_context(task_id="holder", tenant_id="holder"):
                adapter._provider_call("get_payload", blocker)

        def waiting_task():
            try:
                with adapter.task_context(
                    task_id="cancel-me", tenant_id="tenant-C", cancellation_event=cancelled
                ):
                    adapter._provider_call("get_payload", lambda: callback_calls.append("called"))
            except Exception as exc:
                errors.append(exc)

        holder_thread = threading.Thread(target=holder)
        waiter_thread = threading.Thread(target=waiting_task)
        holder_thread.start()
        self.assertTrue(entered.wait(timeout=2))
        waiter_thread.start()
        self._wait_for_bulkhead_queue(adapter, 1)
        cancelled.set()
        waiter_thread.join(timeout=2)
        release.set()
        holder_thread.join(timeout=2)
        self.assertFalse(waiter_thread.is_alive())
        self.assertFalse(holder_thread.is_alive())
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], ProviderTaskCancelledError)
        self.assertEqual(callback_calls, [])
        self.assertEqual(adapter.bulkhead_snapshot("read")["waiting_count"], 0)

    def test_task_deadline_expiring_during_backoff_prevents_next_attempt(self):
        class FakeClock:
            now = 0.0
            def __call__(self):
                return self.now
            def advance(self, seconds):
                self.now += seconds

        clock = FakeClock()
        calls = []
        adapter = BackupStorageAdapter(
            MockObjectStorageProvider(),
            retry_max_attempts=3,
            retry_base_delay_seconds=0.1,
            sleep_fn=lambda delay: clock.advance(2),
            clock_fn=clock,
        )

        def transient():
            calls.append("attempt")
            raise ProviderTransientError("synthetic timeout")

        with adapter.task_context(task_id="deadline-task", tenant_id="tenant-D", timeout_seconds=1):
            with self.assertRaises(ProviderTaskDeadlineExceededError):
                adapter._provider_call("get_payload", transient)
        self.assertEqual(calls, ["attempt"])



    def test_shared_coordinator_enforces_global_capacity_across_adapters(self):
        coordinator = InMemoryProviderAdmissionCoordinator(
            global_limits={"read": 1, "write": 1, "multipart": 1, "inventory": 1}
        )
        provider_a, provider_b = MockObjectStorageProvider(), MockObjectStorageProvider()
        adapter_a = BackupStorageAdapter(provider_a, admission_coordinator=coordinator)
        adapter_b = BackupStorageAdapter(provider_b, admission_coordinator=coordinator)
        entered, release = threading.Event(), threading.Event()
        errors = []

        def blocking():
            entered.set()
            if not release.wait(timeout=2):
                raise AssertionError("shared admission holder was not released")
            return "held"

        def holder():
            try:
                with adapter_a.task_context(task_id="shared-a", tenant_id="tenant-A"):
                    adapter_a._provider_call("get_payload", blocking)
            except Exception as exc:
                errors.append(exc)

        thread = threading.Thread(target=holder)
        thread.start()
        self.assertTrue(entered.wait(timeout=2))
        try:
            with adapter_b.task_context(task_id="shared-b", tenant_id="tenant-B"):
                with self.assertRaises(ProviderBulkheadFullError):
                    adapter_b._provider_call("get_payload", lambda: "must-not-run")
            self.assertEqual(coordinator.snapshot()["active_by_domain"]["read"], 1)
        finally:
            release.set()
            thread.join(timeout=2)
        self.assertFalse(thread.is_alive())
        self.assertEqual(errors, [])
        with adapter_b.task_context(task_id="shared-b-after", tenant_id="tenant-B"):
            self.assertEqual(adapter_b._provider_call("get_payload", lambda: "admitted"), "admitted")
        self.assertEqual(coordinator.snapshot()["active_by_domain"]["read"], 0)

    def test_shared_tenant_quota_applies_across_adapters_but_other_tenant_can_use_capacity(self):
        coordinator = InMemoryProviderAdmissionCoordinator(
            global_limits={"read": 2, "write": 1, "multipart": 1, "inventory": 1},
            tenant_limits={"tenant-A": {"read": 1}},
        )
        adapter_a = BackupStorageAdapter(MockObjectStorageProvider(), admission_coordinator=coordinator)
        adapter_b = BackupStorageAdapter(MockObjectStorageProvider(), admission_coordinator=coordinator)
        entered, release = threading.Event(), threading.Event()
        errors = []

        def blocking():
            entered.set()
            if not release.wait(timeout=2):
                raise AssertionError("tenant quota holder was not released")
            return "held"

        def holder():
            try:
                with adapter_a.task_context(task_id="A-1", tenant_id="tenant-A"):
                    adapter_a._provider_call("get_payload", blocking)
            except Exception as exc:
                errors.append(exc)

        thread = threading.Thread(target=holder)
        thread.start()
        self.assertTrue(entered.wait(timeout=2))
        try:
            with adapter_b.task_context(task_id="A-2", tenant_id="tenant-A"):
                with self.assertRaises(ProviderBulkheadFullError):
                    adapter_b._provider_call("get_payload", lambda: "same-tenant-blocked")
            with adapter_b.task_context(task_id="B-1", tenant_id="tenant-B"):
                self.assertEqual(adapter_b._provider_call("get_payload", lambda: "other-tenant-admitted"), "other-tenant-admitted")
        finally:
            release.set()
            thread.join(timeout=2)
        self.assertFalse(thread.is_alive())
        self.assertEqual(errors, [])

    def test_expired_shared_lease_is_reclaimed_and_stale_release_is_fenced(self):
        class FakeClock:
            now = 10.0
            def __call__(self):
                return self.now
            def advance(self, seconds):
                self.now += seconds

        clock = FakeClock()
        coordinator = InMemoryProviderAdmissionCoordinator(
            global_limits={"read": 1, "write": 1, "multipart": 1, "inventory": 1},
            clock_fn=clock,
        )
        check = lambda _: None
        task = ProviderTaskContext(task_id="lease-a", tenant_id="tenant-A")
        old = coordinator.acquire(
            task=task, domain="read", owner_id="adapter-a",
            lease_ttl_seconds=5, timeout_seconds=0, check_task=check,
        )
        clock.advance(5.1)
        new = coordinator.acquire(
            task=ProviderTaskContext(task_id="lease-b", tenant_id="tenant-B"),
            domain="read", owner_id="adapter-b", lease_ttl_seconds=5,
            timeout_seconds=0, check_task=check,
        )
        self.assertGreater(new.fencing_token, old.fencing_token)
        self.assertFalse(coordinator.validate(old))
        self.assertFalse(coordinator.release(old))
        self.assertTrue(coordinator.validate(new))
        self.assertEqual(coordinator.snapshot()["expired_leases"], 1)
        self.assertTrue(coordinator.release(new))

    def test_shared_lease_renewal_extends_expiry_and_requires_current_fence(self):
        class FakeClock:
            now = 0.0
            def __call__(self):
                return self.now
            def advance(self, seconds):
                self.now += seconds

        clock = FakeClock()
        coordinator = InMemoryProviderAdmissionCoordinator(clock_fn=clock)
        lease = coordinator.acquire(
            task=ProviderTaskContext(task_id="renew", tenant_id="tenant-A"),
            domain="read", owner_id="adapter-a", lease_ttl_seconds=2,
            timeout_seconds=0, check_task=lambda _: None,
        )
        clock.advance(1.5)
        renewed = coordinator.renew(lease, lease_ttl_seconds=4)
        self.assertIsNotNone(renewed)
        clock.advance(3)
        self.assertTrue(coordinator.validate(renewed))
        self.assertTrue(coordinator.release(renewed))
        self.assertFalse(coordinator.release(lease))

    def test_shared_rate_limit_is_atomic_across_adapters_and_refills(self):
        class FakeClock:
            now = 0.0
            def __call__(self):
                return self.now
            def advance(self, seconds):
                self.now += seconds

        clock = FakeClock()
        coordinator = InMemoryProviderAdmissionCoordinator(
            global_limits={"read": 2, "write": 1, "multipart": 1, "inventory": 1},
            rate_limits_per_second={"read": 1.0},
            rate_bursts={"read": 1},
            clock_fn=clock,
        )
        adapter_a = BackupStorageAdapter(MockObjectStorageProvider(), admission_coordinator=coordinator, clock_fn=clock)
        adapter_b = BackupStorageAdapter(MockObjectStorageProvider(), admission_coordinator=coordinator, clock_fn=clock)
        with adapter_a.task_context(task_id="rate-a", tenant_id="tenant-A"):
            self.assertEqual(adapter_a._provider_call("get_payload", lambda: "first"), "first")
        with adapter_b.task_context(task_id="rate-b", tenant_id="tenant-B"):
            with self.assertRaises(ProviderRateLimitExceededError) as caught:
                adapter_b._provider_call("get_payload", lambda: "must-wait")
        self.assertAlmostEqual(caught.exception.retry_after_seconds, 1.0)
        clock.advance(1.0)
        with adapter_b.task_context(task_id="rate-b2", tenant_id="tenant-B"):
            self.assertEqual(adapter_b._provider_call("get_payload", lambda: "after-refill"), "after-refill")

    def test_adapter_fails_closed_if_shared_lease_expires_inside_provider_call(self):
        class FakeClock:
            now = 0.0
            def __call__(self):
                return self.now
            def advance(self, seconds):
                self.now += seconds

        clock = FakeClock()
        coordinator = InMemoryProviderAdmissionCoordinator(
            global_limits={"read": 1, "write": 1, "multipart": 1, "inventory": 1},
            clock_fn=clock,
        )
        adapter = BackupStorageAdapter(
            MockObjectStorageProvider(), admission_coordinator=coordinator,
            coordinator_lease_ttl_seconds=2, clock_fn=clock,
        )

        def expires_while_running():
            clock.advance(2.1)
            return "provider-may-have-completed"

        with adapter.task_context(task_id="lease-loss", tenant_id="tenant-A"):
            with self.assertRaises(ProviderAdmissionLeaseLostError) as caught:
                adapter._provider_call("get_payload", expires_while_running)
        self.assertTrue(caught.exception.outcome_unknown)
        self.assertEqual(coordinator.snapshot()["active_by_domain"]["read"], 0)

    def test_shared_coordinator_rejects_invalid_policy_configuration(self):
        with self.assertRaises(BackupStorageError):
            InMemoryProviderAdmissionCoordinator(global_limits={"read": 0})
        with self.assertRaises(BackupStorageError):
            InMemoryProviderAdmissionCoordinator(tenant_limits={"tenant-A": {"unknown": 1}})
        with self.assertRaises(BackupStorageError):
            InMemoryProviderAdmissionCoordinator(rate_limits_per_second={"read": 0})
        with self.assertRaises(BackupStorageError):
            InMemoryProviderAdmissionCoordinator(rate_bursts={"read": 2})
        with self.assertRaises(BackupStorageError):
            BackupStorageAdapter(MockObjectStorageProvider(), coordinator_lease_ttl_seconds=0)


if __name__ == "__main__":
    unittest.main()
