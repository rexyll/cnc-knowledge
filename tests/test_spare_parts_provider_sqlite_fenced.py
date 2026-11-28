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
    SQLiteProviderWriteFrozenError,
    SQLiteProviderGrantRejectedError,
)
from scripts.spare_parts_provider_write_freeze_gate import (
    sign_provider_write_freeze_command,
)
from scripts.spare_parts_provider_revocable_grant import (
    CLAIMS_FORMAT as PROVIDER_GRANT_CLAIMS_FORMAT,
    sign_provider_grant_command,
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
    provider_freeze_generation: int | None = None,
    provider_grant_id: str | None = None,
    provider_grant_generation: int | None = None,
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
        **(
            {"provider_freeze_generation": provider_freeze_generation}
            if provider_freeze_generation is not None else {}
        ),
        **(
            {
                "provider_grant_id": provider_grant_id,
                "provider_grant_generation": provider_grant_generation,
            }
            if provider_grant_id is not None and provider_grant_generation is not None else {}
        ),
    }, key_id=key_id, secret=secret)


def _wrap_test_attestations(provider):
    raw = {
        "put": provider.put_if_absent_fenced,
        "begin": provider.begin_multipart_upload_fenced,
        "part": provider.put_multipart_part_fenced,
        "complete": provider.complete_multipart_upload_fenced,
    }
    provider._raw_fenced_methods = raw

    def put(key, data, *, fencing_scope, fencing_token, idempotency_key, fencing_attestation=None,
            provider_grant_id=None, provider_grant_generation=None):
        proof = fencing_attestation or _proof(
            tenant_id=provider.tenant_id, key=key, scope=fencing_scope,
            token=fencing_token, idempotency_key=idempotency_key,
            operation="object:put_if_absent",
            provider_grant_id=provider_grant_id,
            provider_grant_generation=provider_grant_generation,
        )
        return raw["put"](
            key, data, fencing_scope=fencing_scope, fencing_token=fencing_token,
            idempotency_key=idempotency_key, fencing_attestation=proof,
        )

    def begin(key, upload_id, *, fencing_scope, fencing_token, idempotency_key, fencing_attestation=None,
              provider_grant_id=None, provider_grant_generation=None):
        proof = fencing_attestation or _proof(
            tenant_id=provider.tenant_id, key=key, scope=fencing_scope,
            token=fencing_token, idempotency_key=idempotency_key, operation="multipart:begin",
            provider_grant_id=provider_grant_id,
            provider_grant_generation=provider_grant_generation,
        )
        return raw["begin"](
            key, upload_id, fencing_scope=fencing_scope, fencing_token=fencing_token,
            idempotency_key=idempotency_key, fencing_attestation=proof,
        )

    def part(key, upload_id, part_number, data, expected_sha256, *, fencing_scope,
             fencing_token, idempotency_key, fencing_attestation=None,
             provider_grant_id=None, provider_grant_generation=None):
        proof = fencing_attestation or _proof(
            tenant_id=provider.tenant_id, key=key, scope=fencing_scope,
            token=fencing_token, idempotency_key=idempotency_key, operation="multipart:put_part",
            provider_grant_id=provider_grant_id,
            provider_grant_generation=provider_grant_generation,
        )
        return raw["part"](
            key, upload_id, part_number, data, expected_sha256,
            fencing_scope=fencing_scope, fencing_token=fencing_token,
            idempotency_key=idempotency_key, fencing_attestation=proof,
        )

    def complete(key, upload_id, *, expected_part_count, expected_size_bytes,
                 expected_sha256, fencing_scope, fencing_token, idempotency_key,
                 fencing_attestation=None, provider_grant_id=None,
                 provider_grant_generation=None):
        proof = fencing_attestation or _proof(
            tenant_id=provider.tenant_id, key=key, scope=fencing_scope,
            token=fencing_token, idempotency_key=idempotency_key,
            operation="multipart:complete",
            provider_grant_id=provider_grant_id,
            provider_grant_generation=provider_grant_generation,
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
    provider_id=None, leader_status_checker=None, require_online_leader_status=False,
    require_revocable_grant=False,
):
    if require_revocable_grant:
        leader_status_checker = leader_status_checker or MutableLeaderStatusChecker(active=True)
        require_online_leader_status = True
    provider = SQLiteFencedObjectStorageProvider(
        database, principal_id=principal_id, principal_secret=secret,
        provider_id=provider_id,
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
        leader_status_checker=leader_status_checker,
        require_online_leader_status=require_online_leader_status,
        require_revocable_grant=require_revocable_grant,
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


class MutableLeaderStatusChecker:
    def __init__(self, active=True, error=None):
        self.active = active
        self.error = error
        self.calls = []

    def is_leader_active(self, claims, *, now_unix):
        self.calls.append((dict(claims), now_unix))
        if self.error:
            raise self.error
        return self.active


class SQLiteProviderWriteFreezeGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.database = self.base / "provider.sqlite"
        _provision(self.database, include_ed25519=True)
        self.provider = _new_provider(
            self.database,
            provider_id="provider-test-a",
            trusted_ed25519_public_keys={ED_KEY_ID: ED_PUBLIC},
        )

    def tearDown(self):
        self.temp.cleanup()

    def command(self, action, generation, freeze_id, *, now=None, scope=SCOPE):
        issued = time.time() if now is None else now
        claims = {
            "format": "ch17-provider-write-freeze-command-v2",
            "issuer_id": ISSUER_ID,
            "provider_id": "provider-test-a",
            "tenant_id": "tenant-a",
            "scope": scope,
            "action": action,
            "freeze_id": freeze_id,
            "generation": generation,
            "issued_at_unix": issued,
            "expires_at_unix": issued + 30.0,
            "coordinator_namespace": "/cnc/migration/isolated/provider-freeze-test/",
            "leader_id": "coordinator-leader-a",
            "leader_epoch": 1,
            "leader_lease_id": 101,
            "leader_lease_expires_at_unix": issued + 45.0,
        }
        return sign_provider_write_freeze_command(
            claims, key_id=ED_KEY_ID, private_key=ED_PRIVATE
        )

    def proof(
        self, key, token, operation, idempotency_key, generation=None,
        grant_id=None, grant_generation=None,
    ):
        return _proof(
            tenant_id="tenant-a", key=key, scope=SCOPE, token=token,
            idempotency_key=idempotency_key, operation=operation,
            provider_freeze_generation=generation,
            provider_grant_id=grant_id,
            provider_grant_generation=grant_generation,
        )

    def grant_command(
        self, action, generation, grant_id, *, leader_epoch=1,
        leader_id=None, leader_lease_id=None, issued_at=None,
        lease_expires=None, expires=None, fence_digest=None,
    ):
        issued = time.time() if issued_at is None else issued_at
        lease_expiry = issued + 120.0 if lease_expires is None else lease_expires
        grant_expiry = issued + 60.0 if expires is None else expires
        claims = {
            "format": PROVIDER_GRANT_CLAIMS_FORMAT,
            "issuer_id": ISSUER_ID,
            "provider_id": "provider-test-a",
            "tenant_id": "tenant-a",
            "scope": SCOPE,
            "action": action,
            "grant_id": grant_id,
            "generation": generation,
            "issued_at_unix": issued,
            "expires_at_unix": grant_expiry,
            "coordinator_namespace": "/cnc/migration/isolated/provider-grant-test/",
            "leader_id": leader_id or ("coordinator-leader-" + str(leader_epoch)),
            "leader_epoch": leader_epoch,
            "leader_lease_id": leader_lease_id or (100 + leader_epoch),
            "leader_lease_expires_at_unix": lease_expiry,
            "fence_command_sha256": fence_digest,
        }
        return sign_provider_grant_command(
            claims, key_id=ED_KEY_ID, private_key=ED_PRIVATE
        )

    def enable_revocable_grants(self, *, fault_hook=None):
        self.provider = _new_provider(
            self.database, provider_id="provider-test-a",
            trusted_ed25519_public_keys={ED_KEY_ID: ED_PUBLIC},
            require_revocable_grant=True, fault_hook=fault_hook,
        )
        return self.provider

    def test_revocable_grant_mode_requires_provider_identity_ed25519_and_online_leader_checker(self):
        with self.assertRaisesRegex(BackupStorageError, "online Coordinator Leader verification"):
            SQLiteFencedObjectStorageProvider(
                self.database, principal_id="writer-a", principal_secret=SECRET_A,
                provider_id="provider-test-a",
                trusted_attestation_keys={KEY_ID: ATTESTATION_SECRET},
                trusted_ed25519_public_keys={ED_KEY_ID: ED_PUBLIC},
                require_revocable_grant=True,
            )
        checker = MutableLeaderStatusChecker(active=True)
        with self.assertRaisesRegex(BackupStorageError, "Provider identity and an Ed25519"):
            SQLiteFencedObjectStorageProvider(
                self.database, principal_id="writer-a", principal_secret=SECRET_A,
                provider_id="provider-test-a",
                trusted_attestation_keys={KEY_ID: ATTESTATION_SECRET},
                trusted_ed25519_public_keys={},
                leader_status_checker=checker,
                require_online_leader_status=True,
                require_revocable_grant=True,
            )

    def test_revocable_grant_command_fails_closed_when_online_leader_is_inactive(self):
        checker = MutableLeaderStatusChecker(active=False)
        provider = _new_provider(
            self.database, provider_id="provider-test-a",
            trusted_ed25519_public_keys={ED_KEY_ID: ED_PUBLIC},
            leader_status_checker=checker, require_online_leader_status=True,
            require_revocable_grant=True,
        )
        with self.assertRaisesRegex(FencingAttestationRejectedError, "absent, expired, revoked"):
            provider.apply_provider_grant_command(
                self.grant_command("FENCE", 1, "grant-offline-leader")
            )
        self.assertEqual(len(checker.calls), 1)
        self.assertIsNone(provider.provider_grant_state(SCOPE))

    def test_grant_integer_claims_must_fit_sqlite_signed_integer(self):
        claims = {
            "format": PROVIDER_GRANT_CLAIMS_FORMAT,
            "issuer_id": ISSUER_ID,
            "provider_id": "provider-test-a",
            "tenant_id": "tenant-a",
            "scope": SCOPE,
            "action": "FENCE",
            "grant_id": "grant-overflow",
            "generation": 1,
            "issued_at_unix": time.time(),
            "expires_at_unix": time.time() + 30.0,
            "coordinator_namespace": "/cnc/migration/isolated/provider-grant-test/",
            "leader_id": "coordinator-leader-overflow",
            "leader_epoch": 1 << 63,
            "leader_lease_id": 201,
            "leader_lease_expires_at_unix": time.time() + 60.0,
            "fence_command_sha256": None,
        }
        command = sign_provider_grant_command(
            claims, key_id=ED_KEY_ID, private_key=ED_PRIVATE
        )
        provider = self.enable_revocable_grants()
        with self.assertRaisesRegex(FencingAttestationRejectedError, "SQLite-safe integer"):
            provider.apply_provider_grant_command(command)
        self.assertIsNone(provider.provider_grant_state(SCOPE))

    def test_grant_expiring_while_waiting_for_provider_write_lock_is_rejected(self):
        provider = self.enable_revocable_grants()
        acquired = threading.Event()
        release = threading.Event()
        result = []
        errors = []

        def hold_writer_lock():
            connection = sqlite3.connect(
                str(self.database), timeout=5.0, isolation_level=None
            )
            try:
                connection.execute("BEGIN IMMEDIATE")
                acquired.set()
                if not release.wait(timeout=4.0):
                    raise TimeoutError("test did not release SQLite write lock")
                connection.commit()
            finally:
                connection.close()

        def apply_expiring_command():
            try:
                result.append(provider.apply_provider_grant_command(
                    self.grant_command(
                        "FENCE", 1, "grant-lock-expiry",
                        issued_at=time.time(), lease_expires=time.time() + 5.0,
                        expires=time.time() + 0.6,
                    )
                ))
            except Exception as exc:
                errors.append(exc)

        lock_thread = threading.Thread(target=hold_writer_lock)
        lock_thread.start()
        self.assertTrue(acquired.wait(timeout=2.0))
        apply_thread = threading.Thread(target=apply_expiring_command)
        apply_thread.start()
        try:
            time.sleep(0.8)
        finally:
            release.set()
        lock_thread.join(timeout=3.0)
        apply_thread.join(timeout=3.0)
        self.assertFalse(lock_thread.is_alive())
        self.assertFalse(apply_thread.is_alive())
        self.assertEqual(result, [])
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], FencingAttestationRejectedError)
        self.assertIn("expired", str(errors[0]))
        self.assertIsNone(provider.provider_grant_state(SCOPE))

    def test_activated_grant_expires_and_blocks_mutations(self):
        provider = self.enable_revocable_grants()
        now = time.time()
        fence = self.grant_command(
            "FENCE", 1, "grant-short-lived",
            issued_at=now, lease_expires=now + 30.0,
        )
        digest = hashlib.sha256(
            __import__("json").dumps(fence, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        ).hexdigest()
        provider.apply_provider_grant_command(fence)
        fence_receipt = provider.provider_grant_command_status(digest)
        provider.apply_provider_grant_command(self.grant_command(
            "ACTIVATE", 2, "grant-short-lived",
            issued_at=float(fence_receipt["applied_at"]) + 0.01,
            lease_expires=now + 30.0,
            expires=now + 0.8, fence_digest=digest,
        ))
        key = SCOPE + "/grant/expired.bin"
        proof = self.proof(
            key, 60, "object:put_if_absent", "expired-grant-write",
            grant_id="grant-short-lived", grant_generation=2,
        )
        time.sleep(0.9)
        with self.assertRaisesRegex(SQLiteProviderGrantRejectedError, "expired"):
            provider.put_if_absent_fenced(
                key, b"expired", fencing_scope=SCOPE, fencing_token=60,
                idempotency_key="expired-grant-write", fencing_attestation=proof,
            )
        with self.assertRaises(SQLiteProviderObjectNotFoundError):
            provider.get_object(key)

    def test_backup_validation_requires_ed25519_grant_trust_registry(self):
        backup = self.base / "provider-grant-trust-backup.sqlite"
        self.provider.backup_to(backup)
        with sqlite3.connect(backup) as connection:
            connection.execute("DROP TABLE trusted_ed25519_keys")
        with self.assertRaisesRegex(BackupStorageError, "missing required tables"):
            SQLiteFencedObjectStorageProvider.validate_backup(backup)

    def test_provider_grant_requires_durable_fence_receipt_before_activation(self):
        provider = self.enable_revocable_grants()
        now = time.time()
        fence = self.grant_command(
            "FENCE", 1, "grant-a", issued_at=now, lease_expires=now + 120.0
        )
        import json
        fence_digest = hashlib.sha256(
            json.dumps(fence, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        ).hexdigest()
        activation_without_fence = self.grant_command(
            "ACTIVATE", 1, "grant-a", issued_at=now,
            lease_expires=now + 120.0, fence_digest="f" * 64,
        )
        with self.assertRaises(SQLiteProviderGrantRejectedError):
            provider.apply_provider_grant_command(activation_without_fence)

        result = provider.apply_provider_grant_command(fence)
        self.assertEqual(result["state"], "FENCED")
        self.assertEqual(provider.provider_grant_state(SCOPE)["state"], "FENCED")
        with self.assertRaises(SQLiteProviderGrantRejectedError):
            provider.put_if_absent_fenced(
                SCOPE + "/grant/before-activation.bin", b"denied",
                fencing_scope=SCOPE, fencing_token=1,
                idempotency_key="before-activation",
            )

        activate = self.grant_command(
            "ACTIVATE", 2, "grant-a", issued_at=now + 1.0,
            lease_expires=now + 120.0, expires=now + 60.0,
            fence_digest=fence_digest,
        )
        activated = provider.apply_provider_grant_command(activate)
        self.assertEqual(activated["state"], "ACTIVE")
        proof = self.proof(
            SCOPE + "/grant/active.bin", 2, "object:put_if_absent", "grant-active",
            grant_id="grant-a", grant_generation=2,
        )
        stored = provider.put_if_absent_fenced(
            SCOPE + "/grant/active.bin", b"allowed", fencing_scope=SCOPE,
            fencing_token=2, idempotency_key="grant-active", fencing_attestation=proof,
        )
        self.assertEqual(stored.data, b"allowed")

    def test_activation_command_must_be_issued_after_fence_receipt(self):
        provider = self.enable_revocable_grants()
        now = time.time()
        fence = self.grant_command(
            "FENCE", 1, "grant-early-activation",
            issued_at=now, lease_expires=now + 180.0,
        )
        digest = hashlib.sha256(
            __import__("json").dumps(fence, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        ).hexdigest()
        provider.apply_provider_grant_command(fence)
        early_activate = self.grant_command(
            "ACTIVATE", 2, "grant-early-activation",
            issued_at=now - 0.5, lease_expires=now + 180.0,
            expires=now + 60.0, fence_digest=digest,
        )
        with self.assertRaisesRegex(SQLiteProviderGrantRejectedError, "FENCE receipt"):
            provider.apply_provider_grant_command(early_activate)
        self.assertEqual(provider.provider_grant_state(SCOPE)["state"], "FENCED")

    def test_newer_fence_revokes_old_grant_and_old_proofs(self):
        provider = self.enable_revocable_grants()
        now = time.time()
        fence1 = self.grant_command(
            "FENCE", 1, "grant-a", issued_at=now, lease_expires=now + 180.0
        )
        fence1_digest = hashlib.sha256(
            __import__("json").dumps(fence1, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        ).hexdigest()
        provider.apply_provider_grant_command(fence1)
        activate1 = self.grant_command(
            "ACTIVATE", 2, "grant-a", issued_at=now + 1.0,
            lease_expires=now + 180.0, expires=now + 120.0,
            fence_digest=fence1_digest,
        )
        provider.apply_provider_grant_command(activate1)

        old_key = SCOPE + "/grant/old-epoch.bin"
        old_proof = self.proof(
            old_key, 10, "object:put_if_absent", "old-epoch",
            grant_id="grant-a", grant_generation=2,
        )
        new_fence = self.grant_command(
            "FENCE", 3, "grant-b", leader_epoch=2,
            issued_at=now + 2.0, lease_expires=now + 180.0,
        )
        new_fence_digest = hashlib.sha256(
            __import__("json").dumps(new_fence, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        ).hexdigest()
        provider.apply_provider_grant_command(new_fence)
        with self.assertRaises(SQLiteProviderGrantRejectedError):
            provider.put_if_absent_fenced(
                old_key, b"old-leader", fencing_scope=SCOPE,
                fencing_token=10, idempotency_key="old-epoch",
                fencing_attestation=old_proof,
            )

        activate2 = self.grant_command(
            "ACTIVATE", 4, "grant-b", leader_epoch=2,
            issued_at=now + 3.0, lease_expires=now + 180.0,
            expires=now + 120.0, fence_digest=new_fence_digest,
        )
        provider.apply_provider_grant_command(activate2)
        new_proof = self.proof(
            SCOPE + "/grant/new-epoch.bin", 11, "object:put_if_absent",
            "new-epoch", grant_id="grant-b", grant_generation=4,
        )
        stored = provider.put_if_absent_fenced(
            SCOPE + "/grant/new-epoch.bin", b"new-leader",
            fencing_scope=SCOPE, fencing_token=11, idempotency_key="new-epoch",
            fencing_attestation=new_proof,
        )
        self.assertEqual(stored.data, b"new-leader")
        state = provider.provider_grant_state(SCOPE)
        self.assertEqual(state["leader_epoch"], 2)
        self.assertEqual(state["grant_generation"], 4)
        self.assertEqual(state["state"], "ACTIVE")

    def test_revocable_grant_is_required_by_object_and_all_multipart_mutations(self):
        provider = self.enable_revocable_grants()
        now = time.time()
        fence = self.grant_command(
            "FENCE", 1, "grant-all-writes", issued_at=now, lease_expires=now + 180.0
        )
        digest = hashlib.sha256(
            __import__("json").dumps(fence, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        ).hexdigest()
        provider.apply_provider_grant_command(fence)
        provider.apply_provider_grant_command(self.grant_command(
            "ACTIVATE", 2, "grant-all-writes", issued_at=now + 1.0,
            lease_expires=now + 180.0, expires=now + 120.0,
            fence_digest=digest,
        ))

        key = SCOPE + "/grant/multipart.bin"
        provider.begin_multipart_upload_fenced(
            key, "grant-upload-1", fencing_scope=SCOPE,
            fencing_token=40, idempotency_key="grant-multipart-begin",
            provider_grant_id="grant-all-writes", provider_grant_generation=2,
        )
        part = b"grant-controlled-part"
        provider.put_multipart_part_fenced(
            key, "grant-upload-1", 1, part, hashlib.sha256(part).hexdigest(),
            fencing_scope=SCOPE, fencing_token=41,
            idempotency_key="grant-multipart-part",
            provider_grant_id="grant-all-writes", provider_grant_generation=2,
        )

        provider.apply_provider_grant_command(self.grant_command(
            "FENCE", 3, "grant-next-leader", leader_epoch=2,
            issued_at=now + 2.0, lease_expires=now + 180.0,
        ))
        with self.assertRaises(SQLiteProviderGrantRejectedError):
            provider.put_if_absent_fenced(
                SCOPE + "/grant/blocked-object.bin", b"blocked",
                fencing_scope=SCOPE, fencing_token=42,
                idempotency_key="grant-object-after-fence",
            )
        with self.assertRaises(SQLiteProviderGrantRejectedError):
            provider.begin_multipart_upload_fenced(
                SCOPE + "/grant/blocked-multipart.bin", "grant-upload-2",
                fencing_scope=SCOPE, fencing_token=43,
                idempotency_key="grant-begin-after-fence",
            )
        with self.assertRaises(SQLiteProviderGrantRejectedError):
            provider.put_multipart_part_fenced(
                key, "grant-upload-1", 2, b"late",
                hashlib.sha256(b"late").hexdigest(),
                fencing_scope=SCOPE, fencing_token=44,
                idempotency_key="grant-part-after-fence",
            )
        with self.assertRaises(SQLiteProviderGrantRejectedError):
            provider.complete_multipart_upload_fenced(
                key, "grant-upload-1", expected_part_count=1,
                expected_size_bytes=len(part), expected_sha256=hashlib.sha256(part).hexdigest(),
                fencing_scope=SCOPE, fencing_token=45,
                idempotency_key="grant-complete-after-fence",
            )
        self.assertEqual(provider.provider_grant_state(SCOPE)["state"], "FENCED")

    def test_same_leader_can_fence_and_rotate_its_own_grant(self):
        provider = self.enable_revocable_grants()
        now = time.time()
        lease_expiry = now + 180.0
        fence1 = self.grant_command(
            "FENCE", 1, "grant-rotation-a",
            issued_at=now, lease_expires=lease_expiry,
        )
        digest1 = hashlib.sha256(
            __import__("json").dumps(fence1, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        ).hexdigest()
        provider.apply_provider_grant_command(fence1)
        provider.apply_provider_grant_command(self.grant_command(
            "ACTIVATE", 2, "grant-rotation-a",
            issued_at=now + 1.0, lease_expires=lease_expiry,
            expires=now + 120.0, fence_digest=digest1,
        ))

        old_key = SCOPE + "/grant/rotation-old.bin"
        old_proof = self.proof(
            old_key, 50, "object:put_if_absent", "rotation-old",
            grant_id="grant-rotation-a", grant_generation=2,
        )
        fence2 = self.grant_command(
            "FENCE", 3, "grant-rotation-b",
            leader_epoch=1, leader_id="coordinator-leader-1",
            leader_lease_id=101, issued_at=now + 2.0,
            lease_expires=lease_expiry,
        )
        digest2 = hashlib.sha256(
            __import__("json").dumps(fence2, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        ).hexdigest()
        self.assertEqual(provider.apply_provider_grant_command(fence2)["state"], "FENCED")
        with self.assertRaises(SQLiteProviderGrantRejectedError):
            provider.put_if_absent_fenced(
                old_key, b"old-grant", fencing_scope=SCOPE,
                fencing_token=50, idempotency_key="rotation-old",
                fencing_attestation=old_proof,
            )

        provider.apply_provider_grant_command(self.grant_command(
            "ACTIVATE", 4, "grant-rotation-b",
            leader_epoch=1, leader_id="coordinator-leader-1",
            leader_lease_id=101, issued_at=now + 3.0,
            lease_expires=lease_expiry, expires=now + 120.0,
            fence_digest=digest2,
        ))
        new_key = SCOPE + "/grant/rotation-new.bin"
        new_proof = self.proof(
            new_key, 51, "object:put_if_absent", "rotation-new",
            grant_id="grant-rotation-b", grant_generation=4,
        )
        stored = provider.put_if_absent_fenced(
            new_key, b"rotated", fencing_scope=SCOPE,
            fencing_token=51, idempotency_key="rotation-new",
            fencing_attestation=new_proof,
        )
        self.assertEqual(stored.data, b"rotated")
        self.assertEqual(provider.provider_grant_state(SCOPE)["leader_epoch"], 1)
        self.assertEqual(provider.provider_grant_state(SCOPE)["grant_generation"], 4)

    def test_grant_receipt_recovers_lost_fence_response(self):
        import json
        provider = self.enable_revocable_grants()
        command = self.grant_command("FENCE", 1, "grant-lost-response")
        digest = hashlib.sha256(
            json.dumps(command, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        ).hexdigest()

        def lose_response(stage):
            if stage == "after_provider_grant_commit":
                raise RuntimeError("simulated response loss after commit")

        provider = self.enable_revocable_grants(fault_hook=lose_response)
        with self.assertRaisesRegex(RuntimeError, "response loss"):
            provider.apply_provider_grant_command(command)
        receipt = provider.provider_grant_command_status(digest)
        self.assertEqual(receipt["action"], "FENCE")
        self.assertEqual(receipt["result_state"], "FENCED")
        replay = provider.apply_provider_grant_command(command)
        self.assertEqual(replay["result"], "ALREADY_APPLIED")
        self.assertEqual(replay["generation"], 1)
        self.assertEqual(provider.provider_grant_state(SCOPE)["state"], "FENCED")

        backup = self.base / "provider-grant-receipt-backup.sqlite"
        provider.backup_to(backup)
        restored_path = self.base / "provider-grant-receipt-restored.sqlite"
        provider.restore_to_new_database(
            backup, restored_path, external_fencing_floor=0,
            fencing_reconciliation_ref="synthetic-provider-grant-backup",
        )
        restored = _new_provider(
            restored_path, provider_id="provider-test-a",
            trusted_ed25519_public_keys={ED_KEY_ID: ED_PUBLIC},
        )
        restored_receipt = restored.provider_grant_command_status(digest)
        self.assertEqual(restored_receipt["action"], "FENCE")
        self.assertEqual(restored_receipt["result_state"], "FENCED")
        self.assertEqual(restored.provider_grant_state(SCOPE)["state"], "FENCED")

    def test_provider_grant_fence_and_inflight_mutation_share_one_sqlite_order(self):
        checked = threading.Event()
        allow_write_commit = threading.Event()
        fence_finished = threading.Event()
        write_results = []
        fence_results = []
        errors = []
        control = self.enable_revocable_grants()
        now = time.time()
        fence1 = self.grant_command(
            "FENCE", 1, "grant-race-a", issued_at=now, lease_expires=now + 180.0
        )
        digest1 = hashlib.sha256(
            __import__("json").dumps(fence1, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        ).hexdigest()
        control.apply_provider_grant_command(fence1)
        control.apply_provider_grant_command(self.grant_command(
            "ACTIVATE", 2, "grant-race-a", issued_at=now + 1.0,
            lease_expires=now + 180.0, expires=now + 120.0,
            fence_digest=digest1,
        ))

        def hook(stage):
            if stage == "after_provider_grant_check":
                checked.set()
                if not allow_write_commit.wait(timeout=4):
                    raise TimeoutError("test did not release Provider grant mutation")

        writer = _new_provider(
            self.database, provider_id="provider-test-a",
            trusted_ed25519_public_keys={ED_KEY_ID: ED_PUBLIC},
            require_revocable_grant=True, fault_hook=hook,
        )
        key = SCOPE + "/grant/ordered.bin"
        proof = self.proof(
            key, 30, "object:put_if_absent", "grant-race-write",
            grant_id="grant-race-a", grant_generation=2,
        )

        def write():
            try:
                write_results.append(writer.put_if_absent_fenced(
                    key, b"commit-before-fence", fencing_scope=SCOPE,
                    fencing_token=30, idempotency_key="grant-race-write",
                    fencing_attestation=proof,
                ))
            except Exception as exc:
                errors.append(("write", type(exc).__name__, str(exc)))

        def apply_fence():
            try:
                fence_results.append(control.apply_provider_grant_command(
                    self.grant_command(
                        "FENCE", 3, "grant-race-b", leader_epoch=2,
                        issued_at=now + 2.0, lease_expires=now + 180.0,
                    )
                ))
            except Exception as exc:
                errors.append(("fence", type(exc).__name__, str(exc)))
            finally:
                fence_finished.set()

        writer_thread = threading.Thread(target=write)
        writer_thread.start()
        self.assertTrue(checked.wait(timeout=2), "Provider did not reach in-transaction grant check")
        fence_thread = threading.Thread(target=apply_fence)
        fence_thread.start()
        try:
            self.assertFalse(
                fence_finished.wait(timeout=0.15),
                "FENCE must wait for the in-flight Provider mutation transaction",
            )
        finally:
            allow_write_commit.set()
        writer_thread.join(timeout=4)
        fence_thread.join(timeout=4)
        self.assertFalse(writer_thread.is_alive())
        self.assertFalse(fence_thread.is_alive())
        self.assertEqual(errors, [])
        self.assertEqual(write_results[0].data, b"commit-before-fence")
        self.assertEqual(fence_results[0]["state"], "FENCED")
        with self.assertRaises(SQLiteProviderGrantRejectedError):
            control.put_if_absent_fenced(
                SCOPE + "/grant/after-fence.bin", b"old-grant",
                fencing_scope=SCOPE, fencing_token=31,
                idempotency_key="after-fence",
                fencing_attestation=self.proof(
                    SCOPE + "/grant/after-fence.bin", 31, "object:put_if_absent",
                    "after-fence", grant_id="grant-race-a", grant_generation=2,
                ),
            )

    def test_online_leader_status_is_required_and_fail_closed_for_new_commands(self):
        with self.assertRaisesRegex(BackupStorageError, "online Coordinator Leader status"):
            _new_provider(
                self.database, provider_id="provider-test-a",
                trusted_ed25519_public_keys={ED_KEY_ID: ED_PUBLIC},
                require_online_leader_status=True,
            )

        checker = MutableLeaderStatusChecker(active=False)
        self.provider = _new_provider(
            self.database, provider_id="provider-test-a",
            trusted_ed25519_public_keys={ED_KEY_ID: ED_PUBLIC},
            leader_status_checker=checker, require_online_leader_status=True,
        )
        with self.assertRaisesRegex(FencingAttestationRejectedError, "absent, expired, revoked"):
            self.provider.apply_write_freeze_command(self.command("FREEZE", 1, "online-check"))
        self.assertEqual(len(checker.calls), 1)
        self.assertIsNone(self.provider.write_freeze_state(SCOPE))

        checker.active = True
        command = self.command("FREEZE", 1, "online-check")
        self.assertEqual(self.provider.apply_write_freeze_command(command)["state"], "FROZEN")
        checker.active = False
        # Exact historical receipt lookup precedes live-Leader verification.
        self.assertEqual(self.provider.apply_write_freeze_command(command)["result"], "ALREADY_APPLIED")
        self.assertEqual(len(checker.calls), 2)

    def test_online_leader_status_transport_failure_refuses_freeze_command(self):
        checker = MutableLeaderStatusChecker(error=ConnectionError("etcd partition"))
        self.provider = _new_provider(
            self.database, provider_id="provider-test-a",
            trusted_ed25519_public_keys={ED_KEY_ID: ED_PUBLIC},
            leader_status_checker=checker, require_online_leader_status=True,
        )
        with self.assertRaisesRegex(FencingAttestationStatusUnavailableError, "online Leader status is unavailable"):
            self.provider.apply_write_freeze_command(self.command("FREEZE", 1, "online-unavailable"))
        self.assertIsNone(self.provider.write_freeze_state(SCOPE))


    def test_freeze_blocks_object_and_all_multipart_mutation_entrypoints(self):
        key = SCOPE + "/freeze/multipart.bin"
        self.provider.begin_multipart_upload_fenced(
            key, "upload-freeze-1", fencing_scope=SCOPE,
            fencing_token=10, idempotency_key="begin-before-freeze",
        )
        freeze = self.command("FREEZE", 1, "freeze-001")
        result = self.provider.apply_write_freeze_command(freeze)
        self.assertEqual(result["state"], "FROZEN")
        self.assertEqual(result["generation"], 1)

        with self.assertRaises(SQLiteProviderWriteFrozenError):
            self.provider.put_if_absent_fenced(
                SCOPE + "/freeze/object.bin", b"blocked",
                fencing_scope=SCOPE, fencing_token=11,
                idempotency_key="put-while-frozen",
            )
        with self.assertRaises(SQLiteProviderWriteFrozenError):
            self.provider.begin_multipart_upload_fenced(
                SCOPE + "/freeze/new-multipart.bin", "upload-freeze-2",
                fencing_scope=SCOPE, fencing_token=12,
                idempotency_key="begin-while-frozen",
            )
        with self.assertRaises(SQLiteProviderWriteFrozenError):
            self.provider.put_multipart_part_fenced(
                key, "upload-freeze-1", 1, b"part",
                hashlib.sha256(b"part").hexdigest(),
                fencing_scope=SCOPE, fencing_token=13,
                idempotency_key="part-while-frozen",
            )
        with self.assertRaises(SQLiteProviderWriteFrozenError):
            self.provider.complete_multipart_upload_fenced(
                key, "upload-freeze-1", expected_part_count=1,
                expected_size_bytes=4, expected_sha256=hashlib.sha256(b"part").hexdigest(),
                fencing_scope=SCOPE, fencing_token=14,
                idempotency_key="complete-while-frozen",
            )
        self.assertEqual(self.provider.write_freeze_state(SCOPE)["state"], "FROZEN")
        self.assertEqual(self.provider.list_multipart_parts(key, "upload-freeze-1"), [])

    def test_unfreeze_advances_generation_and_rejects_pre_freeze_proofs(self):
        key = SCOPE + "/freeze/after-unfreeze.bin"
        old_proof = self.proof(key, 20, "object:put_if_absent", "old-proof")
        freeze = self.command("FREEZE", 1, "freeze-002")
        unfreeze = self.command("UNFREEZE", 2, "freeze-002")
        self.assertEqual(self.provider.apply_write_freeze_command(freeze)["state"], "FROZEN")
        self.assertEqual(self.provider.apply_write_freeze_command(unfreeze)["state"], "OPEN")

        with self.assertRaisesRegex(
            FencingAttestationRejectedError, "current Provider freeze generation"
        ):
            self.provider.put_if_absent_fenced(
                key, b"old-proof", fencing_scope=SCOPE, fencing_token=20,
                idempotency_key="old-proof", fencing_attestation=old_proof,
            )
        new_proof = self.proof(
            key, 21, "object:put_if_absent", "new-proof", generation=2
        )
        result = self.provider.put_if_absent_fenced(
            key, b"new-proof", fencing_scope=SCOPE, fencing_token=21,
            idempotency_key="new-proof", fencing_attestation=new_proof,
        )
        self.assertEqual(result.data, b"new-proof")
        self.assertEqual(self.provider.write_freeze_state(SCOPE)["generation"], 2)

    def test_freeze_commands_are_signed_monotonic_and_idempotent(self):
        freeze = self.command("FREEZE", 1, "freeze-003")
        self.assertEqual(self.provider.apply_write_freeze_command(freeze)["result"], "APPLIED")
        self.assertEqual(self.provider.apply_write_freeze_command(freeze)["result"], "ALREADY_APPLIED")

        skipped = self.command("UNFREEZE", 3, "freeze-003")
        with self.assertRaisesRegex(FencingAttestationRejectedError, "skips"):
            self.provider.apply_write_freeze_command(skipped)
        wrong_id = self.command("UNFREEZE", 2, "another-freeze")
        with self.assertRaisesRegex(FencingAttestationRejectedError, "does not match"):
            self.provider.apply_write_freeze_command(wrong_id)
        tampered = self.command("UNFREEZE", 2, "freeze-003")
        tampered["command"]["action"] = "FREEZE"
        with self.assertRaises(FencingAttestationRejectedError):
            self.provider.apply_write_freeze_command(tampered)
        wrong_provider = self.command("UNFREEZE", 2, "freeze-003")
        wrong_provider["command"]["provider_id"] = "provider-other"
        with self.assertRaises(FencingAttestationRejectedError):
            self.provider.apply_write_freeze_command(wrong_provider)

    def test_provider_rejects_stale_leader_epoch_after_new_leader_is_observed(self):
        first = self.command("FREEZE", 1, "leader-handoff")
        self.provider.apply_write_freeze_command(first)

        new_leader_claims = dict(self.command("UNFREEZE", 2, "leader-handoff")["command"])
        new_leader_claims.update({
            "leader_id": "coordinator-leader-b",
            "leader_epoch": 2,
            "leader_lease_id": 202,
            "issued_at_unix": time.time(),
            "expires_at_unix": time.time() + 25.0,
            "leader_lease_expires_at_unix": time.time() + 40.0,
        })
        new_leader = sign_provider_write_freeze_command(
            new_leader_claims, key_id=ED_KEY_ID, private_key=ED_PRIVATE
        )
        self.assertEqual(self.provider.apply_write_freeze_command(new_leader)["state"], "OPEN")
        floor = self.provider.write_freeze_state(SCOPE)["leader_floor"]
        self.assertEqual(floor["leader_epoch"], 2)
        self.assertEqual(floor["leader_id"], "coordinator-leader-b")
        self.assertEqual(floor["leader_lease_id"], 202)

        stale_claims = dict(self.command("FREEZE", 3, "stale-leader-freeze")["command"])
        stale_claims.update({
            "leader_id": "coordinator-leader-a",
            "leader_epoch": 1,
            "leader_lease_id": 101,
            "issued_at_unix": time.time(),
            "expires_at_unix": time.time() + 20.0,
            "leader_lease_expires_at_unix": time.time() + 35.0,
        })
        stale = sign_provider_write_freeze_command(
            stale_claims, key_id=ED_KEY_ID, private_key=ED_PRIVATE
        )
        with self.assertRaisesRegex(FencingAttestationRejectedError, "stale Coordinator Leader epoch"):
            self.provider.apply_write_freeze_command(stale)
        self.assertEqual(self.provider.write_freeze_state(SCOPE)["generation"], 2)

    def test_same_leader_epoch_cannot_change_identity_lease_or_namespace(self):
        self.provider.apply_write_freeze_command(self.command("FREEZE", 1, "same-epoch"))
        claims = dict(self.command("UNFREEZE", 2, "same-epoch")["command"])
        claims["leader_lease_id"] = 999
        claims["issued_at_unix"] = time.time()
        claims["expires_at_unix"] = time.time() + 20.0
        claims["leader_lease_expires_at_unix"] = time.time() + 35.0
        forged_handoff = sign_provider_write_freeze_command(
            claims, key_id=ED_KEY_ID, private_key=ED_PRIVATE
        )
        with self.assertRaisesRegex(FencingAttestationRejectedError, "identity or native Lease changed"):
            self.provider.apply_write_freeze_command(forged_handoff)

        claims["leader_lease_id"] = 101
        claims["coordinator_namespace"] = "/cnc/admission/unified/v2/"
        namespace_change = sign_provider_write_freeze_command(
            claims, key_id=ED_KEY_ID, private_key=ED_PRIVATE
        )
        with self.assertRaisesRegex(FencingAttestationRejectedError, "namespace changed"):
            self.provider.apply_write_freeze_command(namespace_change)

    def test_coordinator_namespace_must_be_canonical_absolute_prefix(self):
        claims = dict(self.command("FREEZE", 1, "namespace-canonical")["command"])
        claims["coordinator_namespace"] = "/cnc//migration/../isolated/"
        invalid = sign_provider_write_freeze_command(
            claims, key_id=ED_KEY_ID, private_key=ED_PRIVATE
        )
        with self.assertRaisesRegex(FencingAttestationRejectedError, "canonical absolute prefix"):
            self.provider.apply_write_freeze_command(invalid)

    def test_same_epoch_rejects_regressed_leader_lease_expiry_snapshot(self):
        first = self.command("FREEZE", 1, "lease-expiry-floor", now=1000.0)
        self.assertEqual(
            self.provider.apply_write_freeze_command(first, now_unix=1000.0)["state"],
            "FROZEN",
        )
        claims = dict(self.command("UNFREEZE", 2, "lease-expiry-floor", now=1005.0)["command"])
        claims["leader_lease_expires_at_unix"] = 1040.0
        stale_snapshot = sign_provider_write_freeze_command(
            claims, key_id=ED_KEY_ID, private_key=ED_PRIVATE
        )
        with self.assertRaisesRegex(FencingAttestationRejectedError, "expiry regressed"):
            self.provider.apply_write_freeze_command(stale_snapshot, now_unix=1005.0)
        self.assertEqual(self.provider.write_freeze_state(SCOPE)["generation"], 1)

    def test_command_expiry_cannot_outlive_leader_lease(self):
        claims = dict(self.command("FREEZE", 1, "lease-bound")["command"])
        claims["issued_at_unix"] = time.time()
        claims["expires_at_unix"] = time.time() + 30.0
        claims["leader_lease_expires_at_unix"] = time.time() + 10.0
        invalid = sign_provider_write_freeze_command(
            claims, key_id=ED_KEY_ID, private_key=ED_PRIVATE
        )
        with self.assertRaisesRegex(FencingAttestationRejectedError, "Leader Lease"):
            self.provider.apply_write_freeze_command(invalid)

        claims["expires_at_unix"] = time.time() + 5.0
        claims["leader_lease_expires_at_unix"] = time.time() - 1.0
        expired_lease = sign_provider_write_freeze_command(
            claims, key_id=ED_KEY_ID, private_key=ED_PRIVATE
        )
        with self.assertRaisesRegex(FencingAttestationRejectedError, "Leader Lease"):
            self.provider.apply_write_freeze_command(expired_lease)

    def test_historical_command_replay_after_unfreeze_never_reapplies_old_state(self):
        freeze = self.command("FREEZE", 1, "freeze-history")
        unfreeze = self.command("UNFREEZE", 2, "freeze-history")
        canonical = lambda value: __import__("json").dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
        freeze_digest = hashlib.sha256(canonical(freeze)).hexdigest()

        self.assertEqual(self.provider.apply_write_freeze_command(freeze)["state"], "FROZEN")
        self.assertEqual(self.provider.apply_write_freeze_command(unfreeze)["state"], "OPEN")
        before = self.provider.write_freeze_state(SCOPE)
        self.assertEqual(before["generation"], 2)
        self.assertEqual(before["state"], "OPEN")

        replay = self.provider.apply_write_freeze_command(freeze)
        self.assertEqual(replay["result"], "ALREADY_APPLIED")
        self.assertEqual(replay["generation"], 1)
        self.assertEqual(replay["state"], "FROZEN")
        self.assertEqual(replay["current_generation"], 2)
        self.assertEqual(replay["current_state"], "OPEN")
        after = self.provider.write_freeze_state(SCOPE)
        self.assertEqual(after["generation"], 2)
        self.assertEqual(after["state"], "OPEN")

        receipt = self.provider.write_freeze_command_status(freeze_digest)
        self.assertEqual(receipt["action"], "FREEZE")
        self.assertEqual(receipt["result_state"], "FROZEN")
        self.assertEqual(receipt["generation"], 1)
        self.assertEqual(receipt["current_scope_state"]["state"], "OPEN")
        self.assertIsNone(self.provider.write_freeze_command_status("0" * 64))
        with self.assertRaises(BackupStorageError):
            self.provider.write_freeze_command_status("not-a-digest")

    def test_command_receipt_is_durable_across_restart_and_backup_restore(self):
        freeze = self.command("FREEZE", 1, "freeze-receipt-durable")
        canonical = __import__("json").dumps(
            freeze, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
        digest = hashlib.sha256(canonical).hexdigest()
        self.provider.apply_write_freeze_command(freeze)
        reopened = _new_provider(
            self.database, provider_id="provider-test-a",
            trusted_ed25519_public_keys={ED_KEY_ID: ED_PUBLIC},
        )
        self.assertEqual(
            reopened.write_freeze_command_status(digest)["result_state"], "FROZEN"
        )
        backup = self.base / "provider-command-ledger-backup.sqlite"
        reopened.backup_to(backup)
        restored_path = self.base / "provider-command-ledger-restored.sqlite"
        reopened.restore_to_new_database(
            backup, restored_path, external_fencing_floor=0,
            fencing_reconciliation_ref="synthetic-command-ledger-test",
        )
        restored = _new_provider(
            restored_path, provider_id="provider-test-a",
            trusted_ed25519_public_keys={ED_KEY_ID: ED_PUBLIC},
        )
        restored_receipt = restored.write_freeze_command_status(digest)
        self.assertEqual(restored_receipt["result_state"], "FROZEN")
        self.assertEqual(restored_receipt["leader_epoch"], 1)
        self.assertEqual(restored_receipt["leader_lease_id"], 101)

    def test_freeze_generation_survives_provider_restart_backup_and_restore(self):
        self.provider.apply_write_freeze_command(
            self.command("FREEZE", 1, "freeze-persist")
        )
        self.provider.apply_write_freeze_command(
            self.command("UNFREEZE", 2, "freeze-persist")
        )
        reopened = _new_provider(
            self.database, provider_id="provider-test-a",
            trusted_ed25519_public_keys={ED_KEY_ID: ED_PUBLIC},
        )
        self.assertEqual(reopened.write_freeze_state(SCOPE)["generation"], 2)
        self.assertEqual(reopened.write_freeze_state(SCOPE)["state"], "OPEN")

        backup = self.base / "provider-freeze-backup.sqlite"
        report = reopened.backup_to(backup)
        self.assertEqual(report["schema_version"], 5)
        restored_path = self.base / "provider-freeze-restored.sqlite"
        restore_report = reopened.restore_to_new_database(
            backup, restored_path, external_fencing_floor=0,
            fencing_reconciliation_ref="synthetic-freeze-gate-test",
        )
        self.assertEqual(restore_report["result"], "PREPARED_NEW_DATABASE_NOT_CUTOVER")
        restored = _new_provider(
            restored_path, provider_id="provider-test-a",
            trusted_ed25519_public_keys={ED_KEY_ID: ED_PUBLIC},
        )
        self.assertEqual(restored.write_freeze_state(SCOPE)["generation"], 2)
        self.assertEqual(restored.write_freeze_state(SCOPE)["state"], "OPEN")
        self.assertEqual(
            restored.write_freeze_state(SCOPE)["leader_floor"]["leader_epoch"], 1
        )

    def test_schema_v2_provider_database_is_upgraded_with_freeze_gate_table(self):
        with sqlite3.connect(self.database) as connection:
            connection.execute("DROP TABLE provider_write_freeze_scopes")
            connection.execute(
                "UPDATE provider_meta SET value='2' WHERE key='schema_version'"
            )
        migrated = _new_provider(
            self.database, provider_id="provider-test-a",
            trusted_ed25519_public_keys={ED_KEY_ID: ED_PUBLIC},
        )
        self.assertIsNone(migrated.write_freeze_state(SCOPE))
        with sqlite3.connect(self.database) as connection:
            version = connection.execute(
                "SELECT value FROM provider_meta WHERE key='schema_version'"
            ).fetchone()[0]
            tables = {
                row[0] for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
        self.assertEqual(version, "5")
        self.assertIn("provider_write_freeze_scopes", tables)
        self.assertIn("provider_write_freeze_commands", tables)
        self.assertIn("provider_write_freeze_leader_floors", tables)
        self.assertIn("provider_write_freeze_command_leaders", tables)
        self.assertIn("provider_scope_grants", tables)
        self.assertIn("provider_grant_commands", tables)

    def test_schema_v3_provider_database_adds_leader_epoch_floors(self):
        with sqlite3.connect(self.database) as connection:
            connection.execute("DROP TABLE provider_write_freeze_leader_floors")
            connection.execute("DROP TABLE provider_write_freeze_command_leaders")
            connection.execute(
                "UPDATE provider_meta SET value='3' WHERE key='schema_version'"
            )
        migrated = _new_provider(
            self.database, provider_id="provider-test-a",
            trusted_ed25519_public_keys={ED_KEY_ID: ED_PUBLIC},
        )
        self.assertIsNone(migrated.write_freeze_state(SCOPE))
        with sqlite3.connect(self.database) as connection:
            version = connection.execute(
                "SELECT value FROM provider_meta WHERE key='schema_version'"
            ).fetchone()[0]
            tables = {
                row[0] for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
        self.assertEqual(version, "5")
        self.assertIn("provider_write_freeze_leader_floors", tables)
        self.assertIn("provider_write_freeze_command_leaders", tables)
        self.assertIn("provider_scope_grants", tables)
        self.assertIn("provider_grant_commands", tables)

    def test_schema_v4_provider_database_adds_revocable_grant_tables(self):
        with sqlite3.connect(self.database) as connection:
            connection.execute("DROP TABLE provider_scope_grants")
            connection.execute("DROP TABLE provider_grant_commands")
            connection.execute(
                "UPDATE provider_meta SET value='4' WHERE key='schema_version'"
            )
        migrated = _new_provider(
            self.database, provider_id="provider-test-a",
            trusted_ed25519_public_keys={ED_KEY_ID: ED_PUBLIC},
        )
        self.assertIsNone(migrated.provider_grant_state(SCOPE))
        with sqlite3.connect(self.database) as connection:
            version = connection.execute(
                "SELECT value FROM provider_meta WHERE key='schema_version'"
            ).fetchone()[0]
            tables = {
                row[0] for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
        self.assertEqual(version, "5")
        self.assertIn("provider_scope_grants", tables)
        self.assertIn("provider_grant_commands", tables)

    def test_write_transaction_and_freeze_command_have_one_sqlite_order(self):
        checked = threading.Event()
        allow_write_commit = threading.Event()
        freeze_finished = threading.Event()
        write_results = []
        freeze_results = []
        errors = []

        def hook(stage):
            if stage == "after_provider_write_freeze_check":
                checked.set()
                if not allow_write_commit.wait(timeout=4):
                    raise TimeoutError("test did not release Provider write")

        writer = _new_provider(
            self.database, provider_id="provider-test-a",
            trusted_ed25519_public_keys={ED_KEY_ID: ED_PUBLIC},
            fault_hook=hook,
        )
        control = _new_provider(
            self.database, provider_id="provider-test-a",
            trusted_ed25519_public_keys={ED_KEY_ID: ED_PUBLIC},
        )
        control.apply_write_freeze_command(self.command("FREEZE", 1, "freeze-004"))
        control.apply_write_freeze_command(self.command("UNFREEZE", 2, "freeze-004"))
        key = SCOPE + "/freeze/race.bin"
        proof = self.proof(key, 30, "object:put_if_absent", "race-write", generation=2)

        def write():
            try:
                result = writer.put_if_absent_fenced(
                    key, b"ordered-before-freeze", fencing_scope=SCOPE,
                    fencing_token=30, idempotency_key="race-write",
                    fencing_attestation=proof,
                )
                write_results.append(result)
            except Exception as exc:
                errors.append(("write", type(exc).__name__, str(exc)))

        def freeze():
            try:
                freeze_results.append(
                    control.apply_write_freeze_command(
                        self.command("FREEZE", 3, "freeze-005")
                    )
                )
            except Exception as exc:
                errors.append(("freeze", type(exc).__name__, str(exc)))
            finally:
                freeze_finished.set()

        writer_thread = threading.Thread(target=write)
        writer_thread.start()
        self.assertTrue(checked.wait(timeout=2), "Provider did not reach in-transaction gate check")
        freeze_thread = threading.Thread(target=freeze)
        freeze_thread.start()
        try:
            self.assertFalse(
                freeze_finished.wait(timeout=0.15),
                "freeze command must wait for the in-flight Provider write transaction",
            )
        finally:
            allow_write_commit.set()
        writer_thread.join(timeout=4)
        freeze_thread.join(timeout=4)
        self.assertFalse(writer_thread.is_alive())
        self.assertFalse(freeze_thread.is_alive())
        self.assertEqual(errors, [])
        self.assertEqual(len(write_results), 1)
        self.assertEqual(write_results[0].data, b"ordered-before-freeze")
        self.assertEqual(freeze_results[0]["state"], "FROZEN")
        with self.assertRaises(SQLiteProviderWriteFrozenError):
            control.put_if_absent_fenced(
                SCOPE + "/freeze/after-race.bin", b"blocked",
                fencing_scope=SCOPE, fencing_token=31,
                idempotency_key="after-race",
            )




if __name__ == "__main__":
    unittest.main()
