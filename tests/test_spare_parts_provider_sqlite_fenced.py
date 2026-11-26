from __future__ import annotations

import hashlib
import multiprocessing
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from scripts.spare_parts_backup_storage_adapter import (
    BackupStorageAdapter,
    BackupStorageConflict,
    BackupStorageError,
    FencingTokenConflictError,
    FencingNotSupportedError,
    ProviderTransientError,
    StaleFencingTokenError,
    _synthetic_ledger,
)
from scripts.spare_parts_inventory_ledger_persistence import create_backup, publish_generation
from scripts.spare_parts_provider_admission_sqlite import SQLiteProviderAdmissionCoordinator
from scripts.spare_parts_provider_sqlite_fenced import (
    SQLiteFencedObjectStorageProvider,
    SQLiteProviderAuthorizationError,
    SQLiteProviderObjectNotFoundError,
)


SECRET_A = "synthetic-writer-secret-0000001"
SECRET_B = "synthetic-other-secret-000002"
SCOPE = "cnc/ch17/backup-reference-001"


def _provision(path: Path, *, two_tenants: bool = False) -> None:
    principals = [{
        "principal_id": "writer-a",
        "tenant_id": "tenant-a",
        "principal_secret": SECRET_A,
        "allowed_prefixes": ["cnc/ch17"],
    }]
    if two_tenants:
        principals.append({
            "principal_id": "writer-b",
            "tenant_id": "tenant-b",
            "principal_secret": SECRET_B,
            "allowed_prefixes": ["cnc/ch17"],
        })
    SQLiteFencedObjectStorageProvider.provision_database(path, principals=principals)


def _process_writer(
    database_path: str,
    principal_id: str,
    secret: str,
    key: str,
    token: int,
    barrier: object,
    result_queue: object,
) -> None:
    try:
        provider = SQLiteFencedObjectStorageProvider(
            database_path, principal_id=principal_id, principal_secret=secret
        )
        barrier.wait(timeout=10)
        provider.put_if_absent_fenced(
            key, f"payload-{token}".encode(),
            fencing_scope=SCOPE, fencing_token=token,
            idempotency_key=f"process-{token}",
        )
        result_queue.put(("ACCEPTED", token))
    except StaleFencingTokenError:
        result_queue.put(("STALE", token))
    except Exception as exc:
        result_queue.put(("ERROR", token, type(exc).__name__, str(exc)))


def _make_backup(base: Path, backup_id: str) -> Path:
    source = base / "source-store"
    backups = base / "local-backups"
    ledger, snapshot = _synthetic_ledger()
    publish_generation(source, ledger, snapshot, "sqlite-fenced-provider-generation")
    result = create_backup(source, backups, backup_id)
    return Path(result["backup_path"])


class SQLiteFencedObjectStorageProviderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ch17-sqlite-fenced-provider-test-")
        self.base = Path(self.temp.name)
        self.database = self.base / "provider.sqlite"
        _provision(self.database)
        self.provider = SQLiteFencedObjectStorageProvider(
            self.database, principal_id="writer-a", principal_secret=SECRET_A
        )

    def tearDown(self):
        self.temp.cleanup()

    def fenced_put(
        self, key: str, data: bytes, token: int, idem: str, scope: str = SCOPE
    ):
        return self.provider.put_if_absent_fenced(
            key, data, fencing_scope=scope, fencing_token=token, idempotency_key=idem
        )

    def test_provision_hashes_secret_and_restricts_database_file_mode(self):
        self.assertEqual(self.database.stat().st_mode & 0o777, 0o600)
        raw = self.database.read_bytes()
        self.assertNotIn(SECRET_A.encode(), raw)
        self.assertNotIn(SECRET_B.encode(), raw)
        self.assertTrue(self.provider.capabilities.tenant_isolation)
        self.assertEqual(self.provider.capabilities.provider_kind, "SQLITE_LOCAL_FENCED_REFERENCE")

    def test_wrong_bearer_secret_is_rejected_before_provider_use(self):
        with self.assertRaises(SQLiteProviderAuthorizationError):
            SQLiteFencedObjectStorageProvider(
                self.database, principal_id="writer-a", principal_secret="wrong-secret-value-000"
            )

    def test_action_and_prefix_denial_is_fail_closed_and_audited(self):
        with self.assertRaises(SQLiteProviderAuthorizationError):
            self.provider.put_if_absent_fenced(
                "cnc/other/forbidden.bin", b"forbidden",
                fencing_scope="cnc/other/package", fencing_token=10,
                idempotency_key="denied-prefix",
            )
        with sqlite3.connect(self.database) as connection:
            rows = connection.execute(
                "SELECT outcome,action,object_key FROM provider_audit WHERE outcome='DENY'"
            ).fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], "DENY")
        self.assertEqual(rows[0][2], "cnc/other/forbidden.bin")
        self.assertEqual(self.provider.fencing_high_water("cnc/ch17/backup-reference-001"), 0)

    def test_scope_must_contain_object_key_and_be_authorized(self):
        with self.assertRaises(SQLiteProviderAuthorizationError):
            self.provider.put_if_absent_fenced(
                "cnc/ch17/backup-a/file.bin", b"data",
                fencing_scope="cnc/ch17/backup-b", fencing_token=1,
                idempotency_key="outside-scope",
            )
        with self.assertRaises(SQLiteProviderAuthorizationError):
            self.provider.put_if_absent_fenced(
                "cnc/elsewhere/file.bin", b"data",
                fencing_scope="cnc/elsewhere", fencing_token=2,
                idempotency_key="outside-acl",
            )

    def test_tenant_namespace_isolation(self):
        database = self.base / "two-tenants.sqlite"
        _provision(database, two_tenants=True)
        writer_a = SQLiteFencedObjectStorageProvider(
            database, principal_id="writer-a", principal_secret=SECRET_A
        )
        writer_b = SQLiteFencedObjectStorageProvider(
            database, principal_id="writer-b", principal_secret=SECRET_B
        )
        writer_a.put_if_absent_fenced(
            "cnc/ch17/shared-key.bin", b"tenant-a",
            fencing_scope="cnc/ch17", fencing_token=11, idempotency_key="tenant-a-write",
        )
        with self.assertRaises(SQLiteProviderObjectNotFoundError):
            writer_b.get_object("cnc/ch17/shared-key.bin")
        writer_b.put_if_absent_fenced(
            "cnc/ch17/shared-key.bin", b"tenant-b",
            fencing_scope="cnc/ch17", fencing_token=4, idempotency_key="tenant-b-write",
        )
        self.assertEqual(writer_a.get_object("cnc/ch17/shared-key.bin").data, b"tenant-a")
        self.assertEqual(writer_b.get_object("cnc/ch17/shared-key.bin").data, b"tenant-b")

    def test_package_high_water_rejects_stale_writer_on_different_object_key(self):
        self.fenced_put("cnc/ch17/backup-reference-001/a.bin", b"first", 100, "write-a")
        with self.assertRaises(StaleFencingTokenError):
            self.fenced_put("cnc/ch17/backup-reference-001/b.bin", b"late", 99, "write-b")
        with self.assertRaises(SQLiteProviderObjectNotFoundError):
            self.provider.get_object("cnc/ch17/backup-reference-001/b.bin")
        self.assertEqual(self.provider.fencing_high_water(SCOPE), 100)

    def test_fencing_high_water_persists_across_provider_instance_recreation(self):
        self.fenced_put("cnc/ch17/backup-reference-001/persist.bin", b"durable", 101, "persist-101")
        reopened = SQLiteFencedObjectStorageProvider(
            self.database, principal_id="writer-a", principal_secret=SECRET_A
        )
        self.assertEqual(reopened.fencing_high_water(SCOPE), 101)
        with self.assertRaises(StaleFencingTokenError):
            reopened.put_if_absent_fenced(
                "cnc/ch17/backup-reference-001/late.bin", b"stale",
                fencing_scope=SCOPE, fencing_token=100, idempotency_key="stale-100",
            )

    def test_idempotent_replay_with_newer_token_returns_original_object(self):
        first = self.fenced_put("cnc/ch17/backup-reference-001/replay.bin", b"same", 110, "replay-key")
        replay = self.fenced_put("cnc/ch17/backup-reference-001/replay.bin", b"same", 111, "replay-key")
        self.assertEqual(first, replay)
        self.assertEqual(self.provider.fencing_high_water(SCOPE), 111)
        with sqlite3.connect(self.database) as connection:
            count = connection.execute(
                "SELECT COUNT(*) FROM fenced_operations WHERE fencing_scope=? AND idempotency_key=?",
                (SCOPE, "replay-key"),
            ).fetchone()[0]
        self.assertEqual(count, 1)

    def test_idempotency_key_reuse_with_different_content_is_rejected(self):
        self.fenced_put("cnc/ch17/backup-reference-001/conflict.bin", b"one", 120, "same-idem")
        with self.assertRaises(FencingTokenConflictError):
            self.fenced_put("cnc/ch17/backup-reference-001/conflict.bin", b"two", 121, "same-idem")
        self.assertEqual(
            self.provider.get_object("cnc/ch17/backup-reference-001/conflict.bin").data, b"one"
        )

    def test_current_token_cannot_be_reused_for_a_different_operation(self):
        self.fenced_put("cnc/ch17/backup-reference-001/first.bin", b"one", 130, "first-130")
        with self.assertRaises(FencingTokenConflictError):
            self.fenced_put("cnc/ch17/backup-reference-001/second.bin", b"two", 130, "second-130")

    def test_object_mutation_and_fencing_metadata_roll_back_in_one_transaction(self):
        state = {"failed": False}
        def fault(phase: str) -> None:
            if phase == "after_object_mutation_before_fence_commit" and not state["failed"]:
                state["failed"] = True
                raise RuntimeError("synthetic crash before fencing metadata commit")
        provider = SQLiteFencedObjectStorageProvider(
            self.database, principal_id="writer-a", principal_secret=SECRET_A, fault_hook=fault
        )
        key = "cnc/ch17/backup-reference-001/rollback.bin"
        with self.assertRaisesRegex(RuntimeError, "synthetic crash"):
            provider.put_if_absent_fenced(
                key, b"rollback", fencing_scope=SCOPE, fencing_token=140,
                idempotency_key="rollback-140",
            )
        self.assertEqual(provider.fencing_high_water(SCOPE), 0)
        with self.assertRaises(SQLiteProviderObjectNotFoundError):
            provider.get_object(key)
        clean = SQLiteFencedObjectStorageProvider(
            self.database, principal_id="writer-a", principal_secret=SECRET_A
        )
        clean.put_if_absent_fenced(
            key, b"rollback", fencing_scope=SCOPE, fencing_token=140,
            idempotency_key="rollback-140",
        )
        self.assertEqual(clean.fencing_high_water(SCOPE), 140)

    def test_multipart_complete_commit_and_lost_response_replay(self):
        key = "cnc/ch17/backup-reference-001/multipart.bin"
        upload_id = "multipart-ref-001"
        self.provider.begin_multipart_upload_fenced(
            key, upload_id, fencing_scope=SCOPE, fencing_token=150,
            idempotency_key="begin-150",
        )
        parts = [b"first-segment", b"second-segment"]
        for number, data in enumerate(parts, 1):
            self.provider.put_multipart_part_fenced(
                key, upload_id, number, data, hashlib.sha256(data).hexdigest(),
                fencing_scope=SCOPE, fencing_token=150 + number,
                idempotency_key=f"part-{number}",
            )
        joined = b"".join(parts)
        state = {"lost": False}
        def lose_response(phase: str) -> None:
            if phase == "after_commit_before_response" and not state["lost"]:
                state["lost"] = True
                raise ProviderTransientError("synthetic committed completion timeout", outcome_unknown=True)
        self.provider.fault_hook = lose_response
        with self.assertRaises(ProviderTransientError):
            self.provider.complete_multipart_upload_fenced(
                key, upload_id, expected_part_count=2, expected_size_bytes=len(joined),
                expected_sha256=hashlib.sha256(joined).hexdigest(),
                fencing_scope=SCOPE, fencing_token=153, idempotency_key="complete-153",
            )
        self.provider.fault_hook = None
        result = self.provider.complete_multipart_upload_fenced(
            key, upload_id, expected_part_count=2, expected_size_bytes=len(joined),
            expected_sha256=hashlib.sha256(joined).hexdigest(),
            fencing_scope=SCOPE, fencing_token=154, idempotency_key="complete-153",
        )
        self.assertEqual(result.data, joined)
        self.assertEqual(self.provider.fencing_high_water(SCOPE), 154)
        self.assertEqual(self.provider.get_object(key).content_sha256, hashlib.sha256(joined).hexdigest())

    def test_multipart_part_uses_same_package_scope_and_rejects_old_token(self):
        key = "cnc/ch17/backup-reference-001/chunked.bin"
        self.provider.begin_multipart_upload_fenced(
            key, "mp-stale", fencing_scope=SCOPE, fencing_token=160, idempotency_key="begin-stale"
        )
        first = b"part-a"
        self.provider.put_multipart_part_fenced(
            key, "mp-stale", 1, first, hashlib.sha256(first).hexdigest(),
            fencing_scope=SCOPE, fencing_token=161, idempotency_key="part-current",
        )
        with self.assertRaises(StaleFencingTokenError):
            self.provider.put_multipart_part_fenced(
                key, "mp-stale", 2, b"part-old", hashlib.sha256(b"part-old").hexdigest(),
                fencing_scope=SCOPE, fencing_token=159, idempotency_key="part-stale",
            )
        self.assertEqual(
            [part.part_number for part in self.provider.list_multipart_parts(key, "mp-stale")],
            [1],
        )

    def test_two_processes_share_one_persistent_package_fence(self):
        context = multiprocessing.get_context("spawn")
        barrier = context.Barrier(2)
        output = context.Queue()
        processes = [
            context.Process(
                target=_process_writer,
                args=(
                    str(self.database), "writer-a", SECRET_A,
                    f"cnc/ch17/backup-reference-001/process-{token}.bin",
                    token, barrier, output,
                ),
            )
            for token in (200, 201)
        ]
        for process in processes:
            process.start()
        results = [output.get(timeout=20) for _ in processes]
        for process in processes:
            process.join(timeout=20)
            self.assertEqual(process.exitcode, 0)
        self.assertTrue(all(item[0] in {"ACCEPTED", "STALE"} for item in results), results)
        self.assertIn(("ACCEPTED", 201), results)
        self.assertEqual(self.provider.fencing_high_water(SCOPE), 201)
        with self.assertRaises(StaleFencingTokenError):
            self.fenced_put("cnc/ch17/backup-reference-001/after-race.bin", b"old", 200, "after-race")
        self.assertEqual(len([r for r in results if r[0] == "ACCEPTED"]), 1 if ("STALE", 200) in results else 2)

    def test_online_backup_validation_and_restore_seed_external_fencing_floor(self):
        self.fenced_put("cnc/ch17/backup-reference-001/restore.bin", b"durable-data", 300, "restore-300")
        backup = self.base / "provider-backup.sqlite"
        snapshot = self.provider.backup_to(backup)
        self.assertEqual(snapshot["result"], "VALID")
        self.assertEqual(snapshot["integrity_check"], "ok")
        prepared_path = self.base / "provider-restored.sqlite"
        prepared = self.provider.restore_to_new_database(
            backup, prepared_path, external_fencing_floor=450,
            fencing_reconciliation_ref="SYNTHETIC-INDEPENDENT-FENCE-RECONCILIATION",
        )
        self.assertEqual(prepared["result"], "PREPARED_NEW_DATABASE_NOT_CUTOVER")
        self.assertFalse(prepared["cutover_performed"])
        restored = SQLiteFencedObjectStorageProvider(
            prepared_path, principal_id="writer-a", principal_secret=SECRET_A
        )
        self.assertEqual(restored.fencing_high_water(SCOPE), 450)
        self.assertEqual(restored.get_object("cnc/ch17/backup-reference-001/restore.bin").data, b"durable-data")
        with self.assertRaises(StaleFencingTokenError):
            restored.put_if_absent_fenced(
                "cnc/ch17/backup-reference-001/rollback-stale.bin", b"stale",
                fencing_scope=SCOPE, fencing_token=449, idempotency_key="restore-stale",
            )
        self.assertEqual(self.provider.fencing_high_water(SCOPE), 300)

    def test_restore_requires_external_fencing_reconciliation_and_never_overwrites(self):
        backup = self.base / "backup.sqlite"
        self.provider.backup_to(backup)
        target = self.base / "existing.sqlite"
        target.write_bytes(b"do-not-overwrite")
        with self.assertRaises(BackupStorageError):
            self.provider.restore_to_new_database(
                backup, target, external_fencing_floor=0,
                fencing_reconciliation_ref="synthetic-ref",
            )
        with self.assertRaises(BackupStorageError):
            self.provider.restore_to_new_database(
                backup, self.base / "missing-ref.sqlite", external_fencing_floor=0,
                fencing_reconciliation_ref="",
            )
        self.assertEqual(target.read_bytes(), b"do-not-overwrite")

    def test_corrupt_backup_is_rejected(self):
        backup = self.base / "corrupt.sqlite"
        backup.write_bytes(b"not-a-sqlite-database")
        with self.assertRaises(BackupStorageError):
            SQLiteFencedObjectStorageProvider.validate_backup(backup)

    def test_adapter_strict_mode_publishes_full_backup_through_sqlite_fenced_provider(self):
        backup = _make_backup(self.base, "adapter-sqlite-fenced-001")
        provider_db = self.base / "adapter-provider.sqlite"
        coordinator_db = self.base / "admission.sqlite"
        _provision(provider_db)
        provider = SQLiteFencedObjectStorageProvider(
            provider_db, principal_id="writer-a", principal_secret=SECRET_A
        )
        coordinator = SQLiteProviderAdmissionCoordinator(coordinator_db)
        adapter = BackupStorageAdapter(
            provider,
            multipart_threshold_bytes=1,
            multipart_part_size_bytes=1024,
            admission_coordinator=coordinator,
            require_provider_fencing=True,
            retry_max_attempts=3,
            retry_base_delay_seconds=0,
            sleep_fn=lambda _: None,
        )
        result = adapter.publish_backup(backup, prefix="cnc/ch17")
        verified = adapter.verify_stored_backup(
            prefix="cnc/ch17", backup_id="adapter-sqlite-fenced-001"
        )
        self.assertEqual(result["result"], "PUBLISHED")
        self.assertEqual(verified["result"], "VERIFIED")
        package_scope = result["object_prefix"]
        self.assertGreater(provider.fencing_high_water(package_scope), 0)
        object_rows = provider.list_objects(package_scope)
        self.assertGreaterEqual(len(object_rows), 5)
        self.assertTrue(any(item.key.endswith("BACKUP-RECEIPT.json") for item in object_rows))

    def test_provider_refuses_legacy_unfenced_write_methods(self):
        with self.assertRaises(FencingNotSupportedError):
            self.provider.put_if_absent("cnc/ch17/legacy.bin", b"legacy")


if __name__ == "__main__":
    unittest.main()
