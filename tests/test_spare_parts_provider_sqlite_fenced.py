from __future__ import annotations

import hashlib
import multiprocessing
import os
import sqlite3
import tempfile
import threading
import time
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
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from scripts.spare_parts_provider_admission_sqlite import SQLiteProviderAdmissionCoordinator
from scripts.spare_parts_fencing_attestation import (
    CallbackEd25519Signer, Ed25519PrivateKeySigner,
    create_fencing_attestation, verify_fencing_attestation_signature,
)
from scripts.spare_parts_provider_sqlite_fenced import (
    FencingAttestationRejectedError,
    FencingAttestationStatusUnavailableError,
    SQLiteFencedObjectStorageProvider,
    SQLiteProviderAuthorizationError,
    SQLiteProviderObjectNotFoundError,
)


SECRET_A = "synthetic-writer-secret-0000001"
SECRET_B = "synthetic-other-secret-000002"
SCOPE = "cnc/ch17/backup-reference-001"
ISSUER_ID = "ci-admission-coordinator"
KEY_ID = "ci-key-v2"
OLD_KEY_ID = "ci-key-v1-retiring"
ATTESTATION_SECRET = "synthetic-hmac-attestation-secret-32-bytes-minimum"
OLD_ATTESTATION_SECRET = "synthetic-old-hmac-secret-32-bytes-minimum-value"
ED_KEY_ID = "ci-ed25519-v1"
ED_PRIVATE = Ed25519PrivateKey.from_private_bytes(hashlib.sha256(b"CH17 synthetic Ed25519 signer seed").digest())
ED_SIGNER = Ed25519PrivateKeySigner(key_id=ED_KEY_ID, private_key=ED_PRIVATE)
ED_PUBLIC = ED_SIGNER.public_key_raw()


def _proof(
    *, tenant_id: str, key: str, scope: str, token: int,
    idempotency_key: str, operation: str, key_id: str = KEY_ID,
    secret: str = ATTESTATION_SECRET, ttl_seconds: float = 30.0,
) -> str:
    issued = time.time()
    domain = "write" if operation == "object:put_if_absent" else "multipart"
    return create_fencing_attestation({
        "v": 1, "iss": ISSUER_ID, "kid": key_id,
        "lease_id": f"test-lease-{token}-{idempotency_key[:40]}",
        "owner_id": "synthetic-test-owner", "tenant_id": tenant_id,
        "domain": domain, "fencing_token": token,
        "issued_at": issued, "expires_at": issued + ttl_seconds,
        "lease_expires_at": issued + ttl_seconds,
        "fencing_scope": scope, "resource_key": key,
        "operation": operation, "idempotency_key": idempotency_key,
    }, key_id=key_id, secret=secret)


def _wrap_test_attestations(provider):
    raw = {
        "put": provider.put_if_absent_fenced,
        "begin": provider.begin_multipart_upload_fenced,
        "part": provider.put_multipart_part_fenced,
        "complete": provider.complete_multipart_upload_fenced,
    }
    provider._raw_fenced_methods = raw

    def put(key, data, *, fencing_scope, fencing_token, idempotency_key, fencing_attestation=None):
        proof = fencing_attestation or _proof(
            tenant_id=provider.tenant_id, key=key, scope=fencing_scope,
            token=fencing_token, idempotency_key=idempotency_key,
            operation="object:put_if_absent",
        )
        return raw["put"](
            key, data, fencing_scope=fencing_scope, fencing_token=fencing_token,
            idempotency_key=idempotency_key, fencing_attestation=proof,
        )

    def begin(key, upload_id, *, fencing_scope, fencing_token, idempotency_key, fencing_attestation=None):
        proof = fencing_attestation or _proof(
            tenant_id=provider.tenant_id, key=key, scope=fencing_scope,
            token=fencing_token, idempotency_key=idempotency_key, operation="multipart:begin",
        )
        return raw["begin"](
            key, upload_id, fencing_scope=fencing_scope, fencing_token=fencing_token,
            idempotency_key=idempotency_key, fencing_attestation=proof,
        )

    def part(key, upload_id, part_number, data, expected_sha256, *, fencing_scope,
             fencing_token, idempotency_key, fencing_attestation=None):
        proof = fencing_attestation or _proof(
            tenant_id=provider.tenant_id, key=key, scope=fencing_scope,
            token=fencing_token, idempotency_key=idempotency_key, operation="multipart:put_part",
        )
        return raw["part"](
            key, upload_id, part_number, data, expected_sha256,
            fencing_scope=fencing_scope, fencing_token=fencing_token,
            idempotency_key=idempotency_key, fencing_attestation=proof,
        )

    def complete(key, upload_id, *, expected_part_count, expected_size_bytes,
                 expected_sha256, fencing_scope, fencing_token, idempotency_key,
                 fencing_attestation=None):
        proof = fencing_attestation or _proof(
            tenant_id=provider.tenant_id, key=key, scope=fencing_scope,
            token=fencing_token, idempotency_key=idempotency_key,
            operation="multipart:complete",
        )
        return raw["complete"](
            key, upload_id, expected_part_count=expected_part_count,
            expected_size_bytes=expected_size_bytes, expected_sha256=expected_sha256,
            fencing_scope=fencing_scope, fencing_token=fencing_token,
            idempotency_key=idempotency_key, fencing_attestation=proof,
        )

    provider.put_if_absent_fenced = put
    provider.begin_multipart_upload_fenced = begin
    provider.put_multipart_part_fenced = part
    provider.complete_multipart_upload_fenced = complete
    return provider


def _new_provider(
    database: Path, *, principal_id: str = "writer-a", secret: str = SECRET_A,
    fault_hook=None, trusted_ed25519_public_keys=None,
    attestation_status_checker=None, require_online_attestation_status=False,
    require_atomic_online_attestation_status=False, trusted_hmac_keys=None,
):
    provider = SQLiteFencedObjectStorageProvider(
        database, principal_id=principal_id, principal_secret=secret,
        trusted_attestation_keys=(
            trusted_hmac_keys if trusted_hmac_keys is not None else {
                KEY_ID: ATTESTATION_SECRET,
                OLD_KEY_ID: OLD_ATTESTATION_SECRET,
            }
        ),
        trusted_ed25519_public_keys=trusted_ed25519_public_keys,
        attestation_status_checker=attestation_status_checker,
        require_online_attestation_status=require_online_attestation_status,
        require_atomic_online_attestation_status=require_atomic_online_attestation_status,
        fault_hook=fault_hook,
    )
    return _wrap_test_attestations(provider)


def _provision(
    path: Path, *, two_tenants: bool = False, include_hmac: bool = True,
    include_ed25519: bool = False,
) -> None:
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
    ed_registry = []
    if include_ed25519:
        ed_registry.append({
            "issuer_id": ISSUER_ID, "key_id": ED_KEY_ID,
            "algorithm": "ED25519", "status": "ACTIVE",
            "public_key_sha256": hashlib.sha256(ED_PUBLIC).hexdigest(),
        })
    SQLiteFencedObjectStorageProvider.provision_database(
        path,
        principals=principals,
        trusted_attestation_keys=(
            [{"issuer_id": ISSUER_ID, "key_id": KEY_ID, "algorithm": "HMAC-SHA256", "status": "ACTIVE"}]
            if include_hmac else []
        ),
        trusted_ed25519_keys=ed_registry,
    )


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
        provider = _new_provider(Path(database_path), principal_id=principal_id, secret=secret)
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
        self.provider = _new_provider(self.database)

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

    def test_diagnostics_uses_authorized_prefix_and_reports_local_only_scope(self):
        report = self.provider.diagnostics()
        self.assertEqual(report["backend"], "SQLITE_LOCAL_FENCED_REFERENCE")
        self.assertTrue(report["multi_process_same_host"])
        self.assertFalse(report["multi_host_supported"])
        self.assertEqual(report["tenant_id"], "tenant-a")

    def test_unsigned_fenced_write_is_rejected(self):
        with self.assertRaises(TypeError):
            self.provider._raw_fenced_methods["put"](
                "cnc/ch17/backup-reference-001/unsigned.bin", b"unsigned",
                fencing_scope=SCOPE, fencing_token=1, idempotency_key="unsigned-write",
            )

    def test_tampered_signature_is_rejected(self):
        proof = _proof(
            tenant_id="tenant-a", key="cnc/ch17/backup-reference-001/tampered.bin",
            scope=SCOPE, token=1, idempotency_key="tampered-write",
            operation="object:put_if_absent",
        )
        signed_prefix, signature = proof.rsplit(".", 1)
        tampered_signature = ("A" if signature[0] != "A" else "B") + signature[1:]
        tampered = signed_prefix + "." + tampered_signature
        with self.assertRaises(BackupStorageError):
            self.provider._raw_fenced_methods["put"](
                "cnc/ch17/backup-reference-001/tampered.bin", b"tampered",
                fencing_scope=SCOPE, fencing_token=1, idempotency_key="tampered-write",
                fencing_attestation=tampered,
            )

    def test_attestation_is_bound_to_tenant_scope_resource_operation_and_idempotency(self):
        key = "cnc/ch17/backup-reference-001/bound.bin"
        proof = _proof(
            tenant_id="tenant-a", key=key, scope=SCOPE, token=1,
            idempotency_key="bound-idem", operation="object:put_if_absent",
        )
        raw = self.provider._raw_fenced_methods["put"]
        for kwargs in (
            {"fencing_scope": "cnc/ch17/other-package"},
            {"idempotency_key": "different-idem"},
        ):
            args = {"fencing_scope": SCOPE, "fencing_token": 1, "idempotency_key": "bound-idem"}
            args.update(kwargs)
            with self.subTest(kwargs=kwargs), self.assertRaises(BackupStorageError):
                raw(
                    key, b"payload", **args, fencing_attestation=proof
                )
        wrong_tenant = _proof(
            tenant_id="tenant-b", key=key, scope=SCOPE, token=1,
            idempotency_key="bound-idem", operation="object:put_if_absent",
        )
        with self.assertRaises(BackupStorageError):
            raw(
                key, b"payload", fencing_scope=SCOPE, fencing_token=1,
                idempotency_key="bound-idem", fencing_attestation=wrong_tenant,
            )

    def test_expired_attestation_is_rejected(self):
        key = "cnc/ch17/backup-reference-001/expired.bin"
        proof = _proof(
            tenant_id="tenant-a", key=key, scope=SCOPE, token=1,
            idempotency_key="expired-proof", operation="object:put_if_absent",
            ttl_seconds=-1,
        )
        with self.assertRaises(BackupStorageError):
            self.provider._raw_fenced_methods["put"](
                key, b"expired", fencing_scope=SCOPE, fencing_token=1,
                idempotency_key="expired-proof", fencing_attestation=proof,
            )

    def test_key_rotation_accepts_retiring_and_active_keys_then_revocation_rejects(self):
        registered = SQLiteFencedObjectStorageProvider.admin_register_trusted_attestation_key(
            self.database, issuer_id=ISSUER_ID, key_id=OLD_KEY_ID,
        )
        self.assertEqual(registered["result"], "REGISTERED")
        retired = SQLiteFencedObjectStorageProvider.admin_set_trusted_attestation_key_status(
            self.database, issuer_id=ISSUER_ID, key_id=OLD_KEY_ID,
            status="RETIRING", not_after=time.time() + 60,
        )
        self.assertEqual(retired["status"], "RETIRING")
        self.provider = _new_provider(self.database)
        old_key = "cnc/ch17/backup-reference-001/old-key.bin"
        old_proof = _proof(
            tenant_id="tenant-a", key=old_key, scope=SCOPE, token=5,
            idempotency_key="old-key-write", operation="object:put_if_absent",
            key_id=OLD_KEY_ID, secret=OLD_ATTESTATION_SECRET,
        )
        self.provider._raw_fenced_methods["put"](
            old_key, b"old-key", fencing_scope=SCOPE, fencing_token=5,
            idempotency_key="old-key-write", fencing_attestation=old_proof,
        )
        new_key = "cnc/ch17/backup-reference-001/new-key.bin"
        new_proof = _proof(
            tenant_id="tenant-a", key=new_key, scope=SCOPE, token=6,
            idempotency_key="new-key-write", operation="object:put_if_absent",
            key_id=KEY_ID, secret=ATTESTATION_SECRET,
        )
        self.provider._raw_fenced_methods["put"](
            new_key, b"new-key", fencing_scope=SCOPE, fencing_token=6,
            idempotency_key="new-key-write", fencing_attestation=new_proof,
        )
        revoked_status = SQLiteFencedObjectStorageProvider.admin_set_trusted_attestation_key_status(
            self.database, issuer_id=ISSUER_ID, key_id=OLD_KEY_ID, status="REVOKED",
        )
        self.assertEqual(revoked_status["status"], "REVOKED")
        revoked_key = "cnc/ch17/backup-reference-001/revoked-key.bin"
        revoked_proof = _proof(
            tenant_id="tenant-a", key=revoked_key, scope=SCOPE, token=7,
            idempotency_key="revoked-key-write", operation="object:put_if_absent",
            key_id=OLD_KEY_ID, secret=OLD_ATTESTATION_SECRET,
        )
        with self.assertRaises(BackupStorageError):
            self.provider._raw_fenced_methods["put"](
                revoked_key, b"revoked", fencing_scope=SCOPE, fencing_token=7,
                idempotency_key="revoked-key-write", fencing_attestation=revoked_proof,
            )

    def test_wrong_bearer_secret_is_rejected_before_provider_use(self):
        with self.assertRaises(SQLiteProviderAuthorizationError):
            SQLiteFencedObjectStorageProvider(
                self.database, principal_id="writer-a", principal_secret="wrong-secret-value-000",
                trusted_attestation_keys={KEY_ID: ATTESTATION_SECRET},
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
        writer_a = _new_provider(database, principal_id="writer-a", secret=SECRET_A)
        writer_b = _new_provider(database, principal_id="writer-b", secret=SECRET_B)
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
        reopened = _new_provider(self.database)
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
        provider = _new_provider(self.database, fault_hook=fault)
        key = "cnc/ch17/backup-reference-001/rollback.bin"
        with self.assertRaisesRegex(RuntimeError, "synthetic crash"):
            provider.put_if_absent_fenced(
                key, b"rollback", fencing_scope=SCOPE, fencing_token=140,
                idempotency_key="rollback-140",
            )
        self.assertEqual(provider.fencing_high_water(SCOPE), 0)
        with self.assertRaises(SQLiteProviderObjectNotFoundError):
            provider.get_object(key)
        clean = _new_provider(self.database)
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
        pending_key = "cnc/ch17/backup-reference-001/pending.bin"
        self.provider.begin_multipart_upload_fenced(
            pending_key, "pending-restore-session", fencing_scope=SCOPE,
            fencing_token=301, idempotency_key="pending-restore-begin",
        )
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
        restored = _new_provider(prepared_path)
        self.assertEqual(restored.fencing_high_water(SCOPE), 450)
        self.assertEqual(restored.get_object("cnc/ch17/backup-reference-001/restore.bin").data, b"durable-data")
        self.assertEqual(restored.list_multipart_uploads("cnc/ch17/backup-reference-001"), [])
        self.assertEqual(prepared["invalidated_active_multipart_sessions"], 1)
        with self.assertRaises(StaleFencingTokenError):
            restored.put_if_absent_fenced(
                "cnc/ch17/backup-reference-001/rollback-stale.bin", b"stale",
                fencing_scope=SCOPE, fencing_token=449, idempotency_key="restore-stale",
            )
        self.assertEqual(self.provider.fencing_high_water(SCOPE), 301)

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
        coordinator = SQLiteProviderAdmissionCoordinator(
            coordinator_db, attestation_issuer_id=ISSUER_ID,
            attestation_key_id=KEY_ID, attestation_secret=ATTESTATION_SECRET,
        )
        provider = _new_provider(
            provider_db, attestation_status_checker=coordinator,
            require_online_attestation_status=True,
        )
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
        with adapter.task_context(task_id="sqlite-fenced-integration", tenant_id="tenant-a"):
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

    def test_ed25519_coordinator_signer_and_public_key_only_provider(self):
        database = self.base / "ed25519-provider.sqlite"
        _provision(database, include_hmac=False, include_ed25519=True)
        provider = _new_provider(
            database, trusted_hmac_keys={},
            trusted_ed25519_public_keys={ED_KEY_ID: ED_PUBLIC},
        )
        coordinator = SQLiteProviderAdmissionCoordinator(
            self.base / "ed25519-admission.sqlite",
            attestation_issuer_id=ISSUER_ID,
            attestation_signer=CallbackEd25519Signer(
                key_id=ED_KEY_ID, signing_callback=ED_PRIVATE.sign,
            ),
        )
        task = __import__(
            "scripts.spare_parts_backup_storage_adapter", fromlist=["ProviderTaskContext"]
        ).ProviderTaskContext("ed25519-task", "tenant-a")
        lease = coordinator.acquire(
            task=task, domain="write", owner_id="ed25519-owner",
            lease_ttl_seconds=30, timeout_seconds=0,
            check_task=lambda _: None, request_id="ed25519-request",
        )
        key = "cnc/ch17/backup-reference-001/ed25519.bin"
        proof = coordinator.issue_fencing_attestation(
            lease, fencing_scope=SCOPE, resource_key=key,
            operation="object:put_if_absent", idempotency_key="ed25519-put",
        )
        claims, key_id = verify_fencing_attestation_signature(
            proof, trusted_ed25519_public_keys={ED_KEY_ID: ED_PUBLIC}
        )
        self.assertEqual(key_id, ED_KEY_ID)
        self.assertEqual(claims["v"], 2)
        self.assertEqual(claims["alg"], "ED25519")
        self.assertEqual(claims["lease_id"], lease.lease_id)
        stored = provider.put_if_absent_fenced(
            key, b"asymmetric proof", fencing_scope=SCOPE,
            fencing_token=lease.fencing_token, idempotency_key="ed25519-put",
            fencing_attestation=proof,
        )
        self.assertEqual(stored.data, b"asymmetric proof")
        self.assertEqual(provider._trusted_attestation_keys, {})
        with sqlite3.connect(database) as connection:
            fingerprint = connection.execute(
                "SELECT public_key_sha256 FROM trusted_ed25519_keys WHERE key_id=?",
                (ED_KEY_ID,),
            ).fetchone()[0]
        self.assertEqual(fingerprint, hashlib.sha256(ED_PUBLIC).hexdigest())
        self.assertNotIn(ED_PRIVATE.private_bytes_raw(), database.read_bytes())

    def test_online_status_check_rejects_released_lease_and_fails_closed_on_outage(self):
        database = self.base / "online-provider.sqlite"
        _provision(database)
        coordinator = SQLiteProviderAdmissionCoordinator(
            self.base / "online-admission.sqlite",
            attestation_issuer_id=ISSUER_ID,
            attestation_key_id=KEY_ID, attestation_secret=ATTESTATION_SECRET,
        )
        provider = _new_provider(
            database, attestation_status_checker=coordinator,
            require_online_attestation_status=True,
        )
        task = __import__(
            "scripts.spare_parts_backup_storage_adapter", fromlist=["ProviderTaskContext"]
        ).ProviderTaskContext("online-check-task", "tenant-a")
        lease = coordinator.acquire(
            task=task, domain="write", owner_id="online-check-owner",
            lease_ttl_seconds=30, timeout_seconds=0,
            check_task=lambda _: None, request_id="online-check-released",
        )
        released_key = "cnc/ch17/backup-reference-001/released.bin"
        released_proof = coordinator.issue_fencing_attestation(
            lease, fencing_scope=SCOPE, resource_key=released_key,
            operation="object:put_if_absent", idempotency_key="released-proof",
        )
        self.assertTrue(coordinator.release(lease))
        with self.assertRaises(FencingAttestationRejectedError):
            provider.put_if_absent_fenced(
                released_key, b"released", fencing_scope=SCOPE,
                fencing_token=lease.fencing_token, idempotency_key="released-proof",
                fencing_attestation=released_proof,
            )
        with self.assertRaises(SQLiteProviderObjectNotFoundError):
            provider.get_object(released_key)

        active = coordinator.acquire(
            task=task, domain="write", owner_id="online-check-owner",
            lease_ttl_seconds=30, timeout_seconds=0,
            check_task=lambda _: None, request_id="online-check-outage",
        )
        outage_key = "cnc/ch17/backup-reference-001/outage.bin"
        outage_proof = coordinator.issue_fencing_attestation(
            active, fencing_scope=SCOPE, resource_key=outage_key,
            operation="object:put_if_absent", idempotency_key="outage-proof",
        )
        coordinator.inject_failure("attestation_status")
        with self.assertRaises(FencingAttestationStatusUnavailableError):
            provider.put_if_absent_fenced(
                outage_key, b"outage", fencing_scope=SCOPE,
                fencing_token=active.fencing_token, idempotency_key="outage-proof",
                fencing_attestation=outage_proof,
            )
        with self.assertRaises(SQLiteProviderObjectNotFoundError):
            provider.get_object(outage_key)

    def test_atomic_online_status_requires_same_database_and_online_mode(self):
        provider_db = self.base / "atomic-provider.sqlite"
        coordinator_db = self.base / "separate-coordinator.sqlite"
        _provision(provider_db)
        coordinator = SQLiteProviderAdmissionCoordinator(
            coordinator_db,
            attestation_issuer_id=ISSUER_ID,
            attestation_key_id=KEY_ID,
            attestation_secret=ATTESTATION_SECRET,
        )
        with self.assertRaisesRegex(BackupStorageError, "sharing the exact Provider SQLite database"):
            _new_provider(
                provider_db,
                attestation_status_checker=coordinator,
                require_online_attestation_status=True,
                require_atomic_online_attestation_status=True,
            )
        same_db_coordinator = SQLiteProviderAdmissionCoordinator(
            provider_db,
            attestation_issuer_id=ISSUER_ID,
            attestation_key_id=KEY_ID,
            attestation_secret=ATTESTATION_SECRET,
        )
        with self.assertRaisesRegex(BackupStorageError, "sharing the exact Provider SQLite database"):
            _new_provider(
                provider_db,
                attestation_status_checker=same_db_coordinator,
                require_online_attestation_status=False,
                require_atomic_online_attestation_status=True,
            )

    def test_atomic_online_status_serializes_provider_commit_before_lease_release(self):
        database = self.base / "atomic-shared.sqlite"
        _provision(database)
        coordinator = SQLiteProviderAdmissionCoordinator(
            database,
            attestation_issuer_id=ISSUER_ID,
            attestation_key_id=KEY_ID,
            attestation_secret=ATTESTATION_SECRET,
        )
        task = __import__(
            "scripts.spare_parts_backup_storage_adapter", fromlist=["ProviderTaskContext"]
        ).ProviderTaskContext("atomic-online-task", "tenant-a")
        lease = coordinator.acquire(
            task=task, domain="write", owner_id="atomic-online-owner",
            lease_ttl_seconds=30, timeout_seconds=0,
            check_task=lambda _: None, request_id="atomic-online-request",
        )
        key = "cnc/ch17/backup-reference-001/atomic-online.bin"
        proof = coordinator.issue_fencing_attestation(
            lease, fencing_scope=SCOPE, resource_key=key,
            operation="object:put_if_absent", idempotency_key="atomic-online-put",
        )

        status_checked = threading.Event()
        allow_provider_commit = threading.Event()
        release_connection_opened = threading.Event()
        release_done = threading.Event()
        hook_state = {"paused": False}
        release_results = []
        write_results = []
        write_errors = []

        def pause_after_atomic_status(phase: str) -> None:
            if phase == "after_atomic_online_attestation_status_check" and not hook_state["paused"]:
                hook_state["paused"] = True
                status_checked.set()
                if not allow_provider_commit.wait(timeout=4):
                    raise RuntimeError("timed out waiting to finish the atomic Provider transaction")

        provider = _new_provider(
            database,
            attestation_status_checker=coordinator,
            require_online_attestation_status=True,
            require_atomic_online_attestation_status=True,
            fault_hook=pause_after_atomic_status,
        )
        original_connect = coordinator._connect

        def observe_release_connection():
            if threading.current_thread().name == "coordinator-release":
                release_connection_opened.set()
            return original_connect()

        coordinator._connect = observe_release_connection

        def write_object():
            try:
                write_results.append(provider.put_if_absent_fenced(
                    key, b"atomic-commit-before-release",
                    fencing_scope=SCOPE, fencing_token=lease.fencing_token,
                    idempotency_key="atomic-online-put", fencing_attestation=proof,
                ))
            except Exception as exc:
                write_errors.append(exc)

        def release_lease():
            try:
                release_results.append(coordinator.release(lease))
            except Exception as exc:
                release_results.append(exc)
            finally:
                release_done.set()

        writer = threading.Thread(target=write_object, name="provider-writer")
        writer.start()
        self.assertTrue(status_checked.wait(timeout=2), "Provider did not reach its in-transaction status check")
        releaser = threading.Thread(target=release_lease, name="coordinator-release")
        releaser.start()
        try:
            self.assertTrue(release_connection_opened.wait(timeout=2), "release did not open its SQLite connection")
            self.assertFalse(
                release_done.wait(timeout=0.15),
                "lease release must wait while the Provider holds the shared write transaction",
            )
        finally:
            allow_provider_commit.set()
        writer.join(timeout=4)
        releaser.join(timeout=4)
        self.assertFalse(writer.is_alive(), "Provider writer thread did not finish")
        self.assertFalse(releaser.is_alive(), "Coordinator release thread did not finish")
        self.assertEqual(write_errors, [])
        self.assertEqual(len(write_results), 1)
        self.assertEqual(write_results[0].data, b"atomic-commit-before-release")
        self.assertEqual(release_results, [True])
        self.assertTrue(release_done.is_set())

        with self.assertRaises(FencingAttestationRejectedError):
            provider.put_if_absent_fenced(
                key, b"must-not-replay-after-release",
                fencing_scope=SCOPE, fencing_token=lease.fencing_token,
                idempotency_key="atomic-online-put", fencing_attestation=proof,
            )
        self.assertEqual(provider.get_object(key).data, b"atomic-commit-before-release")

    def test_provider_refuses_legacy_unfenced_write_methods(self):
        with self.assertRaises(FencingNotSupportedError):
            self.provider.put_if_absent("cnc/ch17/legacy.bin", b"legacy")


if __name__ == "__main__":
    unittest.main()
