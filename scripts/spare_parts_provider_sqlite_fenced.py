#!/usr/bin/env python3
"""Same-host SQLite reference Provider with durable package-scoped fencing.

This is a local-file reference implementation. It is not a network service,
multi-host object store, cloud-provider integration, or production approval.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import sqlite3
import sys
import tempfile
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.spare_parts_fencing_attestation import (
    FencingAttestationError, verify_fencing_attestation_signature,
    _load_ed25519_public_key,
)

from scripts.spare_parts_provider_write_freeze_gate import (
    ProviderWriteFreezeCommandError,
    verify_provider_write_freeze_command,
)
from scripts.spare_parts_provider_revocable_grant import (
    ProviderGrantCommandError,
    verify_provider_grant_command,
)

from scripts.spare_parts_backup_storage_adapter import (
    BackupStorageConflict,
    BackupStorageError,
    FencingNotSupportedError,
    FencingTokenConflictError,
    MultipartPart,
    ObjectMetadata,
    ProviderCapabilities,
    ProviderTransientError,
    StaleFencingTokenError,
    StoredObject,
    _json_bytes,
    _safe_key,
    _sha,
)

SCHEMA_VERSION = 5
PBKDF2_ITERATIONS = 210_000
MAX_FENCING_TOKEN = (1 << 63) - 1
DEFAULT_ACTIONS = (
    "object:read",
    "object:write_fenced",
    "object:list_prefix",
    "multipart:read",
    "multipart:write_fenced",
    "multipart:list",
)


class SQLiteProviderAuthorizationError(BackupStorageError):
    """The configured local Provider principal is not allowed to perform an action."""


class FencingAttestationRejectedError(BackupStorageError):
    """A Coordinator signature or scope-bound fencing claim is invalid."""


class FencingAttestationStatusUnavailableError(BackupStorageError):
    """The required online Coordinator lease-status check failed closed."""


class SQLiteProviderWriteFrozenError(BackupStorageError):
    """A persisted Provider-native freeze gate blocks a mutation."""


class SQLiteProviderGrantRejectedError(BackupStorageError):
    """A Provider-native grant is absent, fenced, expired or stale."""


class SQLiteProviderObjectNotFoundError(BackupStorageError):
    """The requested tenant-scoped object does not exist."""


class SQLiteFencedObjectStorageProvider:
    """Durable same-host Provider fixture with transactional downstream fencing.

    A configured bearer secret selects a persisted principal. Prefix/action ACLs,
    tenant identity, package-scope high-water, idempotency receipt and object
    mutation are checked in SQLite. This proves a local reference contract only:
    OS account isolation and SQLite file permissions remain part of the trust
    boundary; the class does not provide network/TLS or remote IAM.
    """

    supports_fencing = True
    requires_fencing_attestation = True

    def __init__(
        self,
        database_path: str | os.PathLike[str],
        *,
        principal_id: str,
        principal_secret: str,
        provider_id: str | None = None,
        trusted_attestation_keys: dict[str, str | bytes] | None = None,
        trusted_ed25519_public_keys: dict[str, Any] | None = None,
        attestation_status_checker: Any | None = None,
        require_online_attestation_status: bool = False,
        require_atomic_online_attestation_status: bool = False,
        leader_status_checker: Any | None = None,
        require_online_leader_status: bool = False,
        require_revocable_grant: bool = False,
        busy_timeout_seconds: float = 5.0,
        fault_hook: Callable[[str], None] | None = None,
    ):
        if not isinstance(database_path, (str, os.PathLike)) or not str(database_path).strip():
            raise BackupStorageError("SQLite fenced Provider database path is required")
        raw_path = Path(database_path).expanduser()
        if raw_path.is_symlink():
            raise BackupStorageError("SQLite fenced Provider database cannot be a symlink")
        self.database_path = raw_path.resolve()
        if not self.database_path.is_file():
            raise BackupStorageError("SQLite fenced Provider database has not been provisioned")
        if not isinstance(principal_id, str) or not principal_id.strip():
            raise BackupStorageError("Provider principal ID is required")
        if not isinstance(principal_secret, str) or len(principal_secret) < 16:
            raise BackupStorageError("Provider principal secret must contain at least 16 characters")
        if not isinstance(busy_timeout_seconds, (int, float)) or isinstance(busy_timeout_seconds, bool):
            raise BackupStorageError("SQLite busy timeout must be numeric")
        if not 0 < busy_timeout_seconds <= 120:
            raise BackupStorageError("SQLite busy timeout must be in (0, 120] seconds")
        self.principal_id = principal_id.strip()
        if provider_id is not None and (
            not isinstance(provider_id, str) or not provider_id.strip() or len(provider_id) > 128
        ):
            raise BackupStorageError("Provider identity is invalid")
        self.provider_id = provider_id.strip() if provider_id is not None else None
        self._principal_secret = principal_secret.encode("utf-8")
        hmac_keys = trusted_attestation_keys or {}
        ed25519_keys = trusted_ed25519_public_keys or {}
        if not isinstance(hmac_keys, dict) or not isinstance(ed25519_keys, dict):
            raise BackupStorageError("Provider trusted attestation key rings must be dictionaries")
        if not hmac_keys and not ed25519_keys:
            raise BackupStorageError("Provider requires at least one trusted HMAC or Ed25519 verification key")
        self._trusted_attestation_keys: dict[str, bytes] = {}
        for key_id, secret in hmac_keys.items():
            if not isinstance(key_id, str) or not re.fullmatch(
                r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", key_id
            ):
                raise BackupStorageError("trusted HMAC attestation key ID is invalid")
            if isinstance(secret, str):
                key_bytes = secret.encode("utf-8")
            elif isinstance(secret, bytes):
                key_bytes = secret
            else:
                raise BackupStorageError("trusted HMAC attestation key must be bytes or text")
            if len(key_bytes) < 32:
                raise BackupStorageError("trusted HMAC attestation keys must contain at least 32 bytes")
            self._trusted_attestation_keys[key_id] = key_bytes
        self._trusted_ed25519_public_keys: dict[str, Any] = {}
        for key_id, public_key in ed25519_keys.items():
            if not isinstance(key_id, str) or not re.fullmatch(
                r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", key_id
            ):
                raise BackupStorageError("trusted Ed25519 attestation key ID is invalid")
            self._trusted_ed25519_public_keys[key_id] = _load_ed25519_public_key(public_key)
        if not isinstance(require_online_attestation_status, bool):
            raise BackupStorageError("require_online_attestation_status must be boolean")
        if not isinstance(require_atomic_online_attestation_status, bool):
            raise BackupStorageError("require_atomic_online_attestation_status must be boolean")
        if require_online_attestation_status and not callable(
            getattr(attestation_status_checker, "is_attestation_active", None)
        ):
            raise BackupStorageError("online attestation status is required but no status checker is configured")
        if require_atomic_online_attestation_status:
            checker_path = getattr(attestation_status_checker, "database_path", None)
            if (
                not require_online_attestation_status
                or not callable(getattr(attestation_status_checker, "is_attestation_active_in_transaction", None))
                or not isinstance(checker_path, (str, os.PathLike))
                or Path(checker_path).expanduser().resolve() != self.database_path
            ):
                raise BackupStorageError(
                    "atomic online status requires an online checker sharing the exact Provider SQLite database"
                )
        if not isinstance(require_online_leader_status, bool):
            raise BackupStorageError("require_online_leader_status must be boolean")
        if require_online_leader_status and not callable(
            getattr(leader_status_checker, "is_leader_active", None)
        ):
            raise BackupStorageError(
                "online Coordinator Leader status is required but no checker is configured"
            )
        if not isinstance(require_revocable_grant, bool):
            raise BackupStorageError("require_revocable_grant must be boolean")
        self.require_revocable_grant = require_revocable_grant
        self.attestation_status_checker = attestation_status_checker
        self.require_online_attestation_status = require_online_attestation_status
        self.require_atomic_online_attestation_status = require_atomic_online_attestation_status
        self.leader_status_checker = leader_status_checker
        self.require_online_leader_status = require_online_leader_status
        self.busy_timeout_seconds = float(busy_timeout_seconds)
        self.fault_hook = fault_hook
        self._ensure_ed25519_registry_schema()
        self._capabilities = ProviderCapabilities(
            provider_kind="SQLITE_LOCAL_FENCED_REFERENCE",
            conditional_create=True,
            object_versioning=False,
            object_lock=False,
            server_side_encryption=None,
            transport_encryption=None,
            consistency_model="SQLITE_WAL_BEGIN_IMMEDIATE_SINGLE_HOST_TRANSACTION",
            identity_authentication="CONFIGURED_BEARER_SECRET_PBKDF2_SESSION_CONTEXT",
            authorization_model="PERSISTED_PRINCIPAL_TENANT_ACTION_AND_PREFIX_ALLOWLIST",
            tenant_isolation=True,
            audit_logging="PERSISTENT_SQLITE_ALLOW_AND_DENY_METADATA",
            multipart_upload=True,
            scoped_inventory=True,
            evidence_scope="SAME_HOST_LOCAL_SQLITE_REFERENCE_NOT_CLOUD_OR_MULTI_HOST",
        )
    def _ensure_ed25519_registry_schema(self) -> None:
        """Additive migration; older HMAC-only Provider DBs remain readable."""
        connection = None
        try:
            connection = sqlite3.connect(
                str(self.database_path), timeout=self.busy_timeout_seconds, isolation_level=None
            )
            connection.execute("PRAGMA busy_timeout = " + str(int(self.busy_timeout_seconds * 1000)))
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """CREATE TABLE IF NOT EXISTS provider_write_freeze_scopes (
                    tenant_id TEXT NOT NULL,
                    fencing_scope TEXT NOT NULL,
                    generation INTEGER NOT NULL CHECK(generation > 0),
                    freeze_id TEXT NOT NULL,
                    state TEXT NOT NULL CHECK(state IN ('FROZEN','OPEN')),
                    command_sha256 TEXT NOT NULL CHECK(length(command_sha256)=64),
                    updated_at REAL NOT NULL,
                    PRIMARY KEY(tenant_id,fencing_scope)
                )"""
            )
            connection.execute(
                """CREATE TABLE IF NOT EXISTS provider_write_freeze_commands (
                    command_sha256 TEXT PRIMARY KEY CHECK(length(command_sha256)=64),
                    issuer_id TEXT NOT NULL,
                    key_id TEXT NOT NULL,
                    provider_id TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    fencing_scope TEXT NOT NULL,
                    action TEXT NOT NULL CHECK(action IN ('FREEZE','UNFREEZE')),
                    freeze_id TEXT NOT NULL,
                    generation INTEGER NOT NULL CHECK(generation > 0),
                    result_state TEXT NOT NULL CHECK(result_state IN ('FROZEN','OPEN')),
                    applied_at REAL NOT NULL
                )"""
            )
            connection.execute(
                """CREATE TABLE IF NOT EXISTS provider_write_freeze_leader_floors (
                    tenant_id TEXT NOT NULL,
                    fencing_scope TEXT NOT NULL,
                    coordinator_namespace TEXT NOT NULL,
                    leader_id TEXT NOT NULL,
                    leader_epoch INTEGER NOT NULL CHECK(leader_epoch > 0),
                    leader_lease_id INTEGER NOT NULL CHECK(leader_lease_id > 0),
                    leader_lease_expires_at REAL NOT NULL,
                    observed_at REAL NOT NULL,
                    PRIMARY KEY(tenant_id,fencing_scope)
                )"""
            )
            connection.execute(
                """CREATE TABLE IF NOT EXISTS provider_write_freeze_command_leaders (
                    command_sha256 TEXT PRIMARY KEY CHECK(length(command_sha256)=64),
                    coordinator_namespace TEXT NOT NULL,
                    leader_id TEXT NOT NULL,
                    leader_epoch INTEGER NOT NULL CHECK(leader_epoch > 0),
                    leader_lease_id INTEGER NOT NULL CHECK(leader_lease_id > 0),
                    leader_lease_expires_at REAL NOT NULL
                )"""
            )
            connection.execute(
                """CREATE TABLE IF NOT EXISTS provider_scope_grants (
                    tenant_id TEXT NOT NULL,
                    fencing_scope TEXT NOT NULL,
                    coordinator_namespace TEXT NOT NULL,
                    leader_id TEXT NOT NULL,
                    leader_epoch INTEGER NOT NULL CHECK(leader_epoch > 0),
                    leader_lease_id INTEGER NOT NULL CHECK(leader_lease_id > 0),
                    leader_lease_expires_at REAL NOT NULL,
                    grant_generation INTEGER NOT NULL CHECK(grant_generation > 0),
                    grant_id TEXT NOT NULL,
                    state TEXT NOT NULL CHECK(state IN ('FENCED','ACTIVE')),
                    grant_expires_at REAL,
                    fence_command_sha256 TEXT NOT NULL CHECK(length(fence_command_sha256)=64),
                    activation_command_sha256 TEXT,
                    updated_at REAL NOT NULL,
                    PRIMARY KEY(tenant_id,fencing_scope)
                )"""
            )
            connection.execute(
                """CREATE TABLE IF NOT EXISTS provider_grant_commands (
                    command_sha256 TEXT PRIMARY KEY CHECK(length(command_sha256)=64),
                    issuer_id TEXT NOT NULL,
                    key_id TEXT NOT NULL,
                    provider_id TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    fencing_scope TEXT NOT NULL,
                    action TEXT NOT NULL CHECK(action IN ('FENCE','ACTIVATE')),
                    grant_id TEXT NOT NULL,
                    generation INTEGER NOT NULL CHECK(generation > 0),
                    coordinator_namespace TEXT NOT NULL,
                    leader_id TEXT NOT NULL,
                    leader_epoch INTEGER NOT NULL CHECK(leader_epoch > 0),
                    leader_lease_id INTEGER NOT NULL CHECK(leader_lease_id > 0),
                    leader_lease_expires_at REAL NOT NULL,
                    fence_command_sha256 TEXT,
                    result_state TEXT NOT NULL CHECK(result_state IN ('FENCED','ACTIVE')),
                    applied_at REAL NOT NULL
                )"""
            )
            connection.execute(
                "UPDATE provider_meta SET value=? WHERE key='schema_version' AND value IN ('2','3','4')",
                (str(SCHEMA_VERSION),),
            )
            version_row = connection.execute(
                "SELECT value FROM provider_meta WHERE key='schema_version'"
            ).fetchone()
            if version_row is None or version_row[0] != str(SCHEMA_VERSION):
                raise BackupStorageError("unsupported SQLite Provider schema version")
            connection.execute(
                """CREATE TABLE IF NOT EXISTS trusted_ed25519_keys (
                    issuer_id TEXT NOT NULL,
                    key_id TEXT NOT NULL,
                    algorithm TEXT NOT NULL CHECK(algorithm='ED25519'),
                    public_key_sha256 TEXT NOT NULL CHECK(length(public_key_sha256)=64),
                    status TEXT NOT NULL CHECK(status IN ('ACTIVE','RETIRING','REVOKED')),
                    not_before REAL NOT NULL,
                    not_after REAL,
                    created_at REAL NOT NULL,
                    PRIMARY KEY(issuer_id,key_id)
                )"""
            )
            connection.commit()
        except sqlite3.Error as exc:
            if connection is not None:
                connection.rollback()
            raise BackupStorageError("cannot migrate Provider Ed25519 trusted key registry") from exc
        finally:
            if connection is not None:
                connection.close()

        self._authenticate_initial_session()
        self._validate_configured_attestation_keys()

    @classmethod
    def admin_register_trusted_attestation_key(
        cls, database_path: str | os.PathLike[str], *, issuer_id: str, key_id: str,
        not_before: float | None = None,
    ) -> dict[str, Any]:
        """Register a verification key using local database-owner privileges.

        This is an offline/local control-plane operation. It stores metadata only;
        the secret must be injected separately into Coordinator and Provider.
        """
        path = Path(database_path).expanduser()
        if path.is_symlink():
            raise BackupStorageError("Provider key registry database cannot be a symlink")
        path = path.resolve()
        if not path.is_file():
            raise BackupStorageError("Provider key registry database does not exist")
        if not isinstance(issuer_id, str) or not issuer_id.strip() or len(issuer_id) > 128:
            raise BackupStorageError("trusted issuer ID is invalid")
        if not isinstance(key_id, str) or not re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", key_id
        ):
            raise BackupStorageError("trusted key ID is invalid")
        boundary = time.time() if not_before is None else not_before
        if (
            not isinstance(boundary, (int, float)) or isinstance(boundary, bool)
            or not 0 <= float(boundary) < float("inf")
        ):
            raise BackupStorageError("trusted key not_before is invalid")
        connection = None
        try:
            connection = sqlite3.connect(str(path), isolation_level=None)
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """INSERT INTO trusted_fencing_keys(
                    issuer_id,key_id,algorithm,status,not_before,not_after,created_at
                ) VALUES(?,?,'HMAC-SHA256','ACTIVE',?,NULL,?)""",
                (issuer_id.strip(), key_id, float(boundary), time.time()),
            )
            connection.commit()
            return {
                "result": "REGISTERED",
                "issuer_id": issuer_id.strip(),
                "key_id": key_id,
                "algorithm": "HMAC-SHA256",
                "status": "ACTIVE",
                "secret_stored": False,
            }
        except sqlite3.IntegrityError as exc:
            if connection is not None:
                connection.rollback()
            raise BackupStorageError("trusted issuer/key ID already exists") from exc
        except sqlite3.Error as exc:
            if connection is not None:
                connection.rollback()
            raise BackupStorageError("cannot register trusted Provider attestation key") from exc
        finally:
            if connection is not None:
                connection.close()

    @classmethod
    def admin_set_trusted_attestation_key_status(
        cls, database_path: str | os.PathLike[str], *, issuer_id: str, key_id: str,
        status: str, not_after: float | None = None,
    ) -> dict[str, Any]:
        """Retire or revoke a key; REVOKED is terminal and immediately fails closed."""
        path = Path(database_path).expanduser()
        if path.is_symlink():
            raise BackupStorageError("Provider key registry database cannot be a symlink")
        path = path.resolve()
        if not path.is_file():
            raise BackupStorageError("Provider key registry database does not exist")
        if status not in {"RETIRING", "REVOKED"}:
            raise BackupStorageError("key status transition must be RETIRING or REVOKED")
        now = time.time()
        boundary = now if status == "REVOKED" else not_after
        if status == "RETIRING" and (
            not isinstance(boundary, (int, float)) or isinstance(boundary, bool)
            or not now < float(boundary) < float("inf")
        ):
            raise BackupStorageError("retiring key requires a future not_after deadline")
        connection = None
        try:
            connection = sqlite3.connect(str(path), isolation_level=None)
            connection.row_factory = sqlite3.Row
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT status FROM trusted_fencing_keys WHERE issuer_id=? AND key_id=?",
                (issuer_id, key_id),
            ).fetchone()
            if row is None:
                raise BackupStorageError("trusted issuer/key ID is not registered")
            if row["status"] == "REVOKED":
                if status != "REVOKED":
                    raise BackupStorageError("revoked attestation keys cannot be reactivated")
                connection.commit()
                return {"result": "UNCHANGED", "issuer_id": issuer_id, "key_id": key_id, "status": "REVOKED"}
            connection.execute(
                "UPDATE trusted_fencing_keys SET status=?,not_after=? WHERE issuer_id=? AND key_id=?",
                (status, float(boundary), issuer_id, key_id),
            )
            connection.commit()
            return {
                "result": "UPDATED", "issuer_id": issuer_id, "key_id": key_id,
                "status": status, "not_after": float(boundary),
            }
        except BackupStorageError:
            if connection is not None:
                connection.rollback()
            raise
        except sqlite3.Error as exc:
            if connection is not None:
                connection.rollback()
            raise BackupStorageError("cannot update trusted Provider attestation key status") from exc
        finally:
            if connection is not None:
                connection.close()

    @staticmethod
    def _ed25519_public_key_fingerprint(public_key: Any) -> str:
        from cryptography.hazmat.primitives import serialization
        raw = public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        return hashlib.sha256(raw).hexdigest()

    @classmethod
    def admin_register_trusted_ed25519_key(
        cls, database_path: str | os.PathLike[str], *, issuer_id: str, key_id: str,
        public_key_sha256: str, not_before: float | None = None,
    ) -> dict[str, Any]:
        path = Path(database_path).expanduser()
        if path.is_symlink():
            raise BackupStorageError("Provider key registry database cannot be a symlink")
        path = path.resolve()
        if not path.is_file():
            raise BackupStorageError("Provider key registry database does not exist")
        if not isinstance(issuer_id, str) or not issuer_id.strip() or len(issuer_id) > 128:
            raise BackupStorageError("trusted issuer ID is invalid")
        if not isinstance(key_id, str) or not re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", key_id
        ):
            raise BackupStorageError("trusted Ed25519 key ID is invalid")
        if not isinstance(public_key_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", public_key_sha256):
            raise BackupStorageError("Ed25519 public key fingerprint is invalid")
        boundary = time.time() if not_before is None else not_before
        if not isinstance(boundary, (int, float)) or isinstance(boundary, bool) or not 0 <= float(boundary) < float("inf"):
            raise BackupStorageError("trusted Ed25519 key not_before is invalid")
        connection = None
        try:
            connection = sqlite3.connect(str(path), isolation_level=None)
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """INSERT INTO trusted_ed25519_keys(
                    issuer_id,key_id,algorithm,public_key_sha256,status,not_before,not_after,created_at
                ) VALUES(?,?,'ED25519',?,'ACTIVE',?,NULL,?)""",
                (issuer_id.strip(), key_id, public_key_sha256, float(boundary), time.time()),
            )
            connection.commit()
            return {
                "result": "REGISTERED", "issuer_id": issuer_id.strip(),
                "key_id": key_id, "algorithm": "ED25519", "status": "ACTIVE",
                "public_key_sha256": public_key_sha256, "private_key_stored": False,
            }
        except sqlite3.IntegrityError as exc:
            if connection is not None:
                connection.rollback()
            raise BackupStorageError("trusted Ed25519 issuer/key ID already exists") from exc
        except sqlite3.Error as exc:
            if connection is not None:
                connection.rollback()
            raise BackupStorageError("cannot register trusted Ed25519 Provider key") from exc
        finally:
            if connection is not None:
                connection.close()

    @classmethod
    def admin_set_trusted_ed25519_key_status(
        cls, database_path: str | os.PathLike[str], *, issuer_id: str, key_id: str,
        status: str, not_after: float | None = None,
    ) -> dict[str, Any]:
        if status not in {"RETIRING", "REVOKED"}:
            raise BackupStorageError("Ed25519 key status transition must be RETIRING or REVOKED")
        now = time.time()
        boundary = now if status == "REVOKED" else not_after
        if status == "RETIRING" and (
            not isinstance(boundary, (int, float)) or isinstance(boundary, bool)
            or not now < float(boundary) < float("inf")
        ):
            raise BackupStorageError("retiring Ed25519 key requires a future not_after deadline")
        path = Path(database_path).expanduser()
        if path.is_symlink() or not path.is_file():
            raise BackupStorageError("Provider key registry database is missing or unsafe")
        connection = None
        try:
            connection = sqlite3.connect(str(path), isolation_level=None)
            connection.row_factory = sqlite3.Row
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT status FROM trusted_ed25519_keys WHERE issuer_id=? AND key_id=?",
                (issuer_id, key_id),
            ).fetchone()
            if row is None:
                raise BackupStorageError("trusted Ed25519 issuer/key ID is not registered")
            if row["status"] == "REVOKED":
                if status != "REVOKED":
                    raise BackupStorageError("revoked Ed25519 keys cannot be reactivated")
                connection.commit()
                return {"result": "UNCHANGED", "status": "REVOKED", "key_id": key_id}
            connection.execute(
                "UPDATE trusted_ed25519_keys SET status=?,not_after=? WHERE issuer_id=? AND key_id=?",
                (status, float(boundary), issuer_id, key_id),
            )
            connection.commit()
            return {
                "result": "UPDATED", "issuer_id": issuer_id, "key_id": key_id,
                "algorithm": "ED25519", "status": status, "not_after": float(boundary),
            }
        except BackupStorageError:
            if connection is not None:
                connection.rollback()
            raise
        except sqlite3.Error as exc:
            if connection is not None:
                connection.rollback()
            raise BackupStorageError("cannot update trusted Ed25519 Provider key status") from exc
        finally:
            if connection is not None:
                connection.close()

    def _validate_configured_attestation_keys(self) -> None:
        try:
            with self._transaction() as c:
                hmac_rows = c.execute(
                    "SELECT key_id FROM trusted_fencing_keys WHERE status IN ('ACTIVE','RETIRING')"
                ).fetchall()
                ed_rows = c.execute(
                    """SELECT key_id,public_key_sha256 FROM trusted_ed25519_keys
                       WHERE status IN ('ACTIVE','RETIRING')"""
                ).fetchall()
                hmac_match = {
                    row["key_id"] for row in hmac_rows
                    if row["key_id"] in self._trusted_attestation_keys
                }
                ed_match = {
                    row["key_id"] for row in ed_rows
                    if row["key_id"] in self._trusted_ed25519_public_keys
                    and self._ed25519_public_key_fingerprint(
                        self._trusted_ed25519_public_keys[row["key_id"]]
                    ) == row["public_key_sha256"]
                }
                if not hmac_match and not ed_match:
                    raise BackupStorageError(
                        "Provider has no matching active runtime key in its trusted Coordinator key registry"
                    )
        except sqlite3.Error as exc:
            raise BackupStorageError("cannot load trusted Coordinator attestation key registry") from exc

    @classmethod
    def provision_database(
        cls,
        database_path: str | os.PathLike[str],
        *,
        principals: list[dict[str, Any]],
        trusted_attestation_keys: list[dict[str, Any]] | None = None,
        trusted_ed25519_keys: list[dict[str, Any]] | None = None,
        minimum_fencing_token: int = 0,
    ) -> dict[str, Any]:
        """Create a new DB and principal verifier records; never overwrites a DB."""
        path = Path(database_path).expanduser()
        if path.is_symlink():
            raise BackupStorageError("Provider database path cannot be a symlink")
        path = path.resolve()
        if path.exists():
            raise BackupStorageError("Provider database already exists; in-place provisioning is prohibited")
        if not isinstance(minimum_fencing_token, int) or isinstance(minimum_fencing_token, bool):
            raise BackupStorageError("minimum fencing token must be an integer")
        if not 0 <= minimum_fencing_token <= MAX_FENCING_TOKEN:
            raise BackupStorageError("minimum fencing token is out of range")
        if not isinstance(principals, list) or not principals:
            raise BackupStorageError("at least one Provider principal is required")
        path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
        connection: sqlite3.Connection | None = None
        try:
            connection = sqlite3.connect(str(path), isolation_level=None)
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA synchronous=FULL")
            connection.execute("PRAGMA foreign_keys=ON")
            connection.executescript(
                """
                CREATE TABLE provider_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE trusted_fencing_keys (
                    issuer_id TEXT NOT NULL,
                    key_id TEXT NOT NULL,
                    algorithm TEXT NOT NULL CHECK(algorithm='HMAC-SHA256'),
                    status TEXT NOT NULL CHECK(status IN ('ACTIVE','RETIRING','REVOKED')),
                    not_before REAL NOT NULL,
                    not_after REAL,
                    created_at REAL NOT NULL,
                    PRIMARY KEY(issuer_id,key_id)
                );
                CREATE TABLE provider_write_freeze_scopes (
                    tenant_id TEXT NOT NULL,
                    fencing_scope TEXT NOT NULL,
                    generation INTEGER NOT NULL CHECK(generation > 0),
                    freeze_id TEXT NOT NULL,
                    state TEXT NOT NULL CHECK(state IN ('FROZEN','OPEN')),
                    command_sha256 TEXT NOT NULL CHECK(length(command_sha256)=64),
                    updated_at REAL NOT NULL,
                    PRIMARY KEY(tenant_id,fencing_scope)
                );
                CREATE TABLE trusted_ed25519_keys (
                    issuer_id TEXT NOT NULL,
                    key_id TEXT NOT NULL,
                    algorithm TEXT NOT NULL CHECK(algorithm='ED25519'),
                    public_key_sha256 TEXT NOT NULL CHECK(length(public_key_sha256)=64),
                    status TEXT NOT NULL CHECK(status IN ('ACTIVE','RETIRING','REVOKED')),
                    not_before REAL NOT NULL,
                    not_after REAL,
                    created_at REAL NOT NULL,
                    PRIMARY KEY(issuer_id,key_id)
                );
                CREATE TABLE provider_principals (
                    principal_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    secret_salt BLOB NOT NULL,
                    secret_hash BLOB NOT NULL,
                    allowed_prefixes_json TEXT NOT NULL,
                    allowed_actions_json TEXT NOT NULL,
                    enabled INTEGER NOT NULL CHECK(enabled IN (0,1)),
                    created_at REAL NOT NULL
                );
                CREATE TABLE fencing_scopes (
                    tenant_id TEXT NOT NULL,
                    fencing_scope TEXT NOT NULL,
                    high_water INTEGER NOT NULL CHECK(high_water >= 0),
                    updated_at REAL NOT NULL,
                    PRIMARY KEY(tenant_id, fencing_scope)
                );
                CREATE TABLE fenced_operations (
                    tenant_id TEXT NOT NULL,
                    fencing_scope TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    operation_sha256 TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    fencing_token INTEGER NOT NULL,
                    created_at REAL NOT NULL,
                    PRIMARY KEY(tenant_id, fencing_scope, idempotency_key)
                );
                CREATE TABLE provider_objects (
                    tenant_id TEXT NOT NULL,
                    object_key TEXT NOT NULL,
                    fencing_scope TEXT NOT NULL,
                    data BLOB NOT NULL,
                    content_sha256 TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    version_id TEXT,
                    fencing_token INTEGER NOT NULL,
                    created_at REAL NOT NULL,
                    PRIMARY KEY(tenant_id, object_key)
                );
                CREATE TABLE multipart_sessions (
                    tenant_id TEXT NOT NULL,
                    object_key TEXT NOT NULL,
                    upload_id TEXT NOT NULL,
                    fencing_scope TEXT NOT NULL,
                    state TEXT NOT NULL CHECK(state IN ('ACTIVE','COMPLETED')),
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    PRIMARY KEY(tenant_id, object_key, upload_id)
                );
                CREATE TABLE multipart_parts (
                    tenant_id TEXT NOT NULL,
                    object_key TEXT NOT NULL,
                    upload_id TEXT NOT NULL,
                    part_number INTEGER NOT NULL CHECK(part_number > 0),
                    data BLOB NOT NULL,
                    content_sha256 TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    fencing_token INTEGER NOT NULL,
                    PRIMARY KEY(tenant_id, object_key, upload_id, part_number),
                    FOREIGN KEY(tenant_id, object_key, upload_id)
                      REFERENCES multipart_sessions(tenant_id, object_key, upload_id)
                );
                CREATE TABLE provider_audit (
                    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    principal_id TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    object_key TEXT NOT NULL,
                    fencing_scope TEXT,
                    fencing_token INTEGER,
                    idempotency_key TEXT,
                    outcome TEXT NOT NULL,
                    created_at REAL NOT NULL
                );
                CREATE INDEX idx_provider_objects_prefix
                    ON provider_objects(tenant_id, object_key);
                CREATE INDEX idx_multipart_sessions_prefix
                    ON multipart_sessions(tenant_id, object_key, state);
                """
            )
            now = time.time()
            connection.execute(
                "INSERT INTO provider_meta(key,value) VALUES('schema_version',?)",
                (str(SCHEMA_VERSION),),
            )
            connection.execute(
                "INSERT INTO provider_meta(key,value) VALUES('minimum_fencing_token',?)",
                (str(minimum_fencing_token),),
            )
            connection.execute(
                "INSERT INTO provider_meta(key,value) VALUES('provisioned_at',?)",
                (str(now),),
            )
            hmac_registry = trusted_attestation_keys or []
            ed25519_registry = trusted_ed25519_keys or []
            if not isinstance(hmac_registry, list) or not isinstance(ed25519_registry, list):
                raise BackupStorageError("trusted attestation key registries must be lists")
            if not hmac_registry and not ed25519_registry:
                raise BackupStorageError("at least one trusted HMAC or Ed25519 Coordinator key is required")
            trusted_seen: set[tuple[str, str]] = set()
            for trusted in hmac_registry:
                if not isinstance(trusted, dict):
                    raise BackupStorageError("trusted attestation key metadata must be objects")
                issuer_id, key_id = trusted.get("issuer_id"), trusted.get("key_id")
                algorithm = trusted.get("algorithm", "HMAC-SHA256")
                status = trusted.get("status", "ACTIVE")
                not_before = trusted.get("not_before", 0.0)
                not_after = trusted.get("not_after")
                if not isinstance(issuer_id, str) or not issuer_id.strip() or len(issuer_id) > 128:
                    raise BackupStorageError("trusted attestation issuer ID is invalid")
                if not isinstance(key_id, str) or not re.fullmatch(
                    r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", key_id
                ):
                    raise BackupStorageError("trusted attestation key ID is invalid")
                if algorithm != "HMAC-SHA256" or status not in {"ACTIVE", "RETIRING"}:
                    raise BackupStorageError("trusted attestation key algorithm or initial status is invalid")
                if (
                    not isinstance(not_before, (int, float)) or isinstance(not_before, bool)
                    or not 0 <= float(not_before) < float("inf")
                ):
                    raise BackupStorageError("trusted attestation not_before is invalid")
                if not_after is not None and (
                    not isinstance(not_after, (int, float)) or isinstance(not_after, bool)
                    or not float(not_before) < float(not_after) < float("inf")
                ):
                    raise BackupStorageError("trusted attestation not_after is invalid")
                identity = (issuer_id.strip(), key_id)
                if identity in trusted_seen:
                    raise BackupStorageError("duplicate trusted attestation issuer/key ID")
                trusted_seen.add(identity)
                connection.execute(
                    """INSERT INTO trusted_fencing_keys(
                        issuer_id,key_id,algorithm,status,not_before,not_after,created_at
                    ) VALUES(?,?,?, ?,?,?,?)""",
                    (identity[0], key_id, algorithm, status, float(not_before),
                     float(not_after) if not_after is not None else None, now),
                )
            ed25519_seen: set[tuple[str, str]] = set()
            for trusted in ed25519_registry:
                if not isinstance(trusted, dict):
                    raise BackupStorageError("trusted Ed25519 key metadata must be objects")
                issuer_id, key_id = trusted.get("issuer_id"), trusted.get("key_id")
                algorithm = trusted.get("algorithm", "ED25519")
                status = trusted.get("status", "ACTIVE")
                fingerprint = trusted.get("public_key_sha256")
                not_before = trusted.get("not_before", 0.0)
                not_after = trusted.get("not_after")
                if not isinstance(issuer_id, str) or not issuer_id.strip() or len(issuer_id) > 128:
                    raise BackupStorageError("trusted Ed25519 issuer ID is invalid")
                if not isinstance(key_id, str) or not re.fullmatch(
                    r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", key_id
                ):
                    raise BackupStorageError("trusted Ed25519 key ID is invalid")
                if algorithm != "ED25519" or status not in {"ACTIVE", "RETIRING"}:
                    raise BackupStorageError("trusted Ed25519 algorithm or initial status is invalid")
                if not isinstance(fingerprint, str) or not re.fullmatch(r"[0-9a-f]{64}", fingerprint):
                    raise BackupStorageError("trusted Ed25519 public key SHA256 fingerprint is invalid")
                if (
                    not isinstance(not_before, (int, float)) or isinstance(not_before, bool)
                    or not 0 <= float(not_before) < float("inf")
                ):
                    raise BackupStorageError("trusted Ed25519 not_before is invalid")
                if not_after is not None and (
                    not isinstance(not_after, (int, float)) or isinstance(not_after, bool)
                    or not float(not_before) < float(not_after) < float("inf")
                ):
                    raise BackupStorageError("trusted Ed25519 not_after is invalid")
                identity = (issuer_id.strip(), key_id)
                if identity in ed25519_seen or identity in trusted_seen:
                    raise BackupStorageError("duplicate trusted issuer/key ID across signature algorithms")
                ed25519_seen.add(identity)
                connection.execute(
                    """INSERT INTO trusted_ed25519_keys(
                        issuer_id,key_id,algorithm,public_key_sha256,status,
                        not_before,not_after,created_at
                    ) VALUES(?,?,?, ?,?,?,?,?)""",
                    (identity[0], key_id, algorithm, fingerprint, status, float(not_before),
                     float(not_after) if not_after is not None else None, now),
                )
            seen: set[str] = set()
            for principal in principals:
                if not isinstance(principal, dict):
                    raise BackupStorageError("principal records must be objects")
                principal_id = principal.get("principal_id")
                tenant_id = principal.get("tenant_id")
                secret = principal.get("principal_secret")
                prefixes = principal.get("allowed_prefixes")
                actions = principal.get("allowed_actions", DEFAULT_ACTIONS)
                if not isinstance(principal_id, str) or not principal_id.strip():
                    raise BackupStorageError("principal ID must be nonblank")
                if principal_id in seen:
                    raise BackupStorageError("duplicate Provider principal ID")
                seen.add(principal_id)
                if not isinstance(tenant_id, str) or not tenant_id.strip():
                    raise BackupStorageError("principal tenant ID must be nonblank")
                if not isinstance(secret, str) or len(secret) < 16:
                    raise BackupStorageError("principal secret must contain at least 16 characters")
                if not isinstance(prefixes, (list, tuple)) or not prefixes:
                    raise BackupStorageError("principal requires at least one allowed prefix")
                normalized_prefixes = sorted({_safe_key(str(item).rstrip("/")) for item in prefixes})
                if not isinstance(actions, (list, tuple)) or not actions:
                    raise BackupStorageError("principal requires at least one allowed action")
                normalized_actions = sorted(set(actions))
                if any(not isinstance(a, str) or a not in DEFAULT_ACTIONS for a in normalized_actions):
                    raise BackupStorageError("principal includes an unsupported Provider action")
                salt = os.urandom(16)
                digest = hashlib.pbkdf2_hmac(
                    "sha256", secret.encode("utf-8"), salt, PBKDF2_ITERATIONS
                )
                connection.execute(
                    """INSERT INTO provider_principals(
                        principal_id,tenant_id,secret_salt,secret_hash,
                        allowed_prefixes_json,allowed_actions_json,enabled,created_at
                    ) VALUES(?,?,?,?,?,?,1,?)""",
                    (
                        principal_id.strip(), tenant_id.strip(), salt, digest,
                        json.dumps(normalized_prefixes, separators=(",", ":")),
                        json.dumps(normalized_actions, separators=(",", ":")), now,
                    ),
                )
            connection.commit()
            connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            connection.close()
            connection = None
            os.chmod(path, 0o600)
            return {
                "result": "PROVISIONED",
                "principal_count": len(seen),
                "schema_version": SCHEMA_VERSION,
                "minimum_fencing_token": minimum_fencing_token,
                "database_sha256": cls._sha256_file(path),
                "file_mode": oct(path.stat().st_mode & 0o777),
                "plaintext_secrets_stored": False,
                "trusted_attestation_key_count": len(trusted_seen),
                "trusted_ed25519_key_count": len(ed25519_seen),
            }
        except Exception:
            if connection is not None:
                connection.close()
            for suffix in ("", "-wal", "-shm"):
                try:
                    Path(str(path) + suffix).unlink()
                except FileNotFoundError:
                    pass
            raise

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._capabilities

    def apply_write_freeze_command(
        self, envelope: dict[str, Any], *, now_unix: float | None = None
    ) -> dict[str, Any]:
        """Atomically apply a signed command and persist its durable receipt.

        Replaying any previously committed envelope returns its historical
        result without reapplying it, even after later generations have run.
        """
        if self.provider_id is None:
            raise BackupStorageError(
                "Provider identity must be configured before applying freeze commands"
            )
        now = time.time() if now_unix is None else now_unix
        try:
            claims, key_id, command_digest = verify_provider_write_freeze_command(
                envelope, self._trusted_ed25519_public_keys,
                expected_provider_id=self.provider_id,
                expected_tenant_id=self.tenant_id, now_unix=now,
            )
        except ProviderWriteFreezeCommandError as exc:
            raise FencingAttestationRejectedError(str(exc)) from exc
        scope = _safe_key(claims["scope"])
        issuer_id = claims["issuer_id"]
        with self._transaction() as c:
            trusted = c.execute(
                """SELECT algorithm,public_key_sha256,status,not_before,not_after
                   FROM trusted_ed25519_keys WHERE issuer_id=? AND key_id=?""",
                (issuer_id, key_id),
            ).fetchone()
            public_key = self._trusted_ed25519_public_keys.get(key_id)
            if (
                trusted is None or trusted["algorithm"] != "ED25519"
                or trusted["status"] not in {"ACTIVE", "RETIRING"}
                or public_key is None
                or self._ed25519_public_key_fingerprint(public_key) != trusted["public_key_sha256"]
                or now < float(trusted["not_before"])
                or (trusted["not_after"] is not None and now >= float(trusted["not_after"]))
                or float(claims["issued_at_unix"]) < float(trusted["not_before"])
                or (trusted["not_after"] is not None and float(claims["issued_at_unix"]) >= float(trusted["not_after"]))
            ):
                raise FencingAttestationRejectedError(
                    "freeze command issuer/key is not trusted for this Provider"
                )

            # Resolve lost responses before checking the current generation.
            receipt = c.execute(
                """SELECT issuer_id,key_id,provider_id,tenant_id,fencing_scope,
                          action,freeze_id,generation,result_state,applied_at
                   FROM provider_write_freeze_commands WHERE command_sha256=?""",
                (command_digest,),
            ).fetchone()
            if receipt is not None:
                expected = (
                    issuer_id, key_id, self.provider_id, self.tenant_id, scope,
                    claims["action"], claims["freeze_id"], int(claims["generation"]),
                )
                observed = (
                    receipt["issuer_id"], receipt["key_id"], receipt["provider_id"],
                    receipt["tenant_id"], receipt["fencing_scope"], receipt["action"],
                    receipt["freeze_id"], int(receipt["generation"]),
                )
                if observed != expected:
                    raise FencingAttestationRejectedError(
                        "freeze command receipt digest conflicts with its signed claims"
                    )
                current = c.execute(
                    """SELECT generation,state FROM provider_write_freeze_scopes
                       WHERE tenant_id=? AND fencing_scope=?""",
                    (self.tenant_id, scope),
                ).fetchone()
                return {
                    "result": "ALREADY_APPLIED", "scope": scope,
                    "generation": int(receipt["generation"]),
                    "state": receipt["result_state"],
                    "applied_at": float(receipt["applied_at"]),
                    "current_generation": int(current["generation"]) if current else None,
                    "current_state": current["state"] if current else None,
                }

            # This is a fresh linearizable etcd snapshot, but it cannot be
            # atomically committed with the following local SQLite transaction.
            # Keep the check fail-closed and document the remaining cross-system
            # check-to-commit race; do not describe it as an atomic Lease guard.
            if self.require_online_leader_status:
                try:
                    active = bool(
                        self.leader_status_checker.is_leader_active(
                            claims, now_unix=now
                        )
                    )
                except Exception as exc:
                    raise FencingAttestationStatusUnavailableError(
                        "Coordinator online Leader status is unavailable; freeze command refused"
                    ) from exc
                if not active:
                    raise FencingAttestationRejectedError(
                        "Coordinator Leader is absent, expired, revoked or does not match the signed command"
                    )

            leader = {
                "coordinator_namespace": claims["coordinator_namespace"],
                "leader_id": claims["leader_id"],
                "leader_epoch": int(claims["leader_epoch"]),
                "leader_lease_id": int(claims["leader_lease_id"]),
                "leader_lease_expires_at": float(claims["leader_lease_expires_at_unix"]),
            }
            floor = c.execute(
                """SELECT coordinator_namespace,leader_id,leader_epoch,leader_lease_id,
                          leader_lease_expires_at
                   FROM provider_write_freeze_leader_floors
                   WHERE tenant_id=? AND fencing_scope=?""",
                (self.tenant_id, scope),
            ).fetchone()
            if floor is not None:
                if leader["coordinator_namespace"] != floor["coordinator_namespace"]:
                    raise FencingAttestationRejectedError(
                        "Coordinator namespace changed for an established Provider scope"
                    )
                if leader["leader_epoch"] < int(floor["leader_epoch"]):
                    raise FencingAttestationRejectedError(
                        "freeze command was issued by a stale Coordinator Leader epoch"
                    )
                if leader["leader_epoch"] == int(floor["leader_epoch"]) and (
                    leader["leader_id"] != floor["leader_id"]
                    or leader["leader_lease_id"] != int(floor["leader_lease_id"])
                ):
                    raise FencingAttestationRejectedError(
                        "Coordinator Leader identity or native Lease changed without an epoch advance"
                    )
                if (
                    leader["leader_epoch"] == int(floor["leader_epoch"])
                    and leader["leader_id"] == floor["leader_id"]
                    and leader["leader_lease_id"] == int(floor["leader_lease_id"])
                    and leader["leader_lease_expires_at"] < float(floor["leader_lease_expires_at"])
                ):
                    raise FencingAttestationRejectedError(
                        "Coordinator Leader Lease expiry regressed within the same epoch"
                    )

            current = c.execute(
                """SELECT generation,freeze_id,state FROM provider_write_freeze_scopes
                   WHERE tenant_id=? AND fencing_scope=?""",
                (self.tenant_id, scope),
            ).fetchone()
            generation = int(claims["generation"])
            action = claims["action"]
            freeze_id = claims["freeze_id"]
            expected_generation = int(current["generation"]) + 1 if current else 1
            if generation != expected_generation:
                raise FencingAttestationRejectedError(
                    "freeze command generation is stale or skips the next generation"
                )
            if action == "FREEZE":
                if current is not None and current["state"] == "FROZEN":
                    raise FencingAttestationRejectedError(
                        "scope is already frozen; unfreeze the current generation first"
                    )
                if current is not None and current["freeze_id"] == freeze_id:
                    raise FencingAttestationRejectedError("a new freeze requires a new freeze ID")
                state = "FROZEN"
            else:
                if current is None or current["state"] != "FROZEN" or current["freeze_id"] != freeze_id:
                    raise FencingAttestationRejectedError(
                        "unfreeze command does not match the active freeze"
                    )
                state = "OPEN"
            c.execute(
                """INSERT INTO provider_write_freeze_scopes(
                    tenant_id,fencing_scope,generation,freeze_id,state,command_sha256,updated_at
                ) VALUES(?,?,?,?,?,?,?)
                ON CONFLICT(tenant_id,fencing_scope) DO UPDATE SET
                    generation=excluded.generation,freeze_id=excluded.freeze_id,
                    state=excluded.state,command_sha256=excluded.command_sha256,
                    updated_at=excluded.updated_at""",
                (self.tenant_id, scope, generation, freeze_id, state, command_digest, now),
            )
            c.execute(
                """INSERT INTO provider_write_freeze_commands(
                    command_sha256,issuer_id,key_id,provider_id,tenant_id,
                    fencing_scope,action,freeze_id,generation,result_state,applied_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    command_digest, issuer_id, key_id, self.provider_id, self.tenant_id,
                    scope, action, freeze_id, generation, state, now,
                ),
            )
            c.execute(
                """INSERT INTO provider_write_freeze_leader_floors(
                    tenant_id,fencing_scope,coordinator_namespace,leader_id,
                    leader_epoch,leader_lease_id,leader_lease_expires_at,observed_at
                ) VALUES(?,?,?,?,?,?,?,?)
                ON CONFLICT(tenant_id,fencing_scope) DO UPDATE SET
                    coordinator_namespace=excluded.coordinator_namespace,
                    leader_id=excluded.leader_id,leader_epoch=excluded.leader_epoch,
                    leader_lease_id=excluded.leader_lease_id,
                    leader_lease_expires_at=excluded.leader_lease_expires_at,
                    observed_at=excluded.observed_at""",
                (
                    self.tenant_id, scope, leader["coordinator_namespace"],
                    leader["leader_id"], leader["leader_epoch"],
                    leader["leader_lease_id"], leader["leader_lease_expires_at"], now,
                ),
            )
            c.execute(
                """INSERT INTO provider_write_freeze_command_leaders(
                    command_sha256,coordinator_namespace,leader_id,leader_epoch,
                    leader_lease_id,leader_lease_expires_at
                ) VALUES(?,?,?,?,?,?)""",
                (
                    command_digest, leader["coordinator_namespace"], leader["leader_id"],
                    leader["leader_epoch"], leader["leader_lease_id"],
                    leader["leader_lease_expires_at"],
                ),
            )
        return {"result": "APPLIED", "scope": scope, "generation": generation, "state": state}

    def apply_provider_grant_command(
        self, envelope: dict[str, Any], *, now_unix: float | None = None
    ) -> dict[str, Any]:
        """Atomically FENCE an old grant or ACTIVATE a grant after its FENCE receipt."""
        if self.provider_id is None:
            raise BackupStorageError("Provider identity must be configured before grant commands")
        now = time.time() if now_unix is None else now_unix
        try:
            claims, key_id, command_digest = verify_provider_grant_command(
                envelope, self._trusted_ed25519_public_keys,
                expected_provider_id=self.provider_id,
                expected_tenant_id=self.tenant_id,
                now_unix=now,
            )
        except ProviderGrantCommandError as exc:
            raise FencingAttestationRejectedError(str(exc)) from exc
        scope = _safe_key(claims["scope"])
        with self._transaction() as c:
            trusted = c.execute(
                """SELECT algorithm,public_key_sha256,status,not_before,not_after
                   FROM trusted_ed25519_keys WHERE issuer_id=? AND key_id=?""",
                (claims["issuer_id"], key_id),
            ).fetchone()
            public_key = self._trusted_ed25519_public_keys.get(key_id)
            if (
                trusted is None or trusted["algorithm"] != "ED25519"
                or trusted["status"] not in {"ACTIVE", "RETIRING"}
                or public_key is None
                or self._ed25519_public_key_fingerprint(public_key) != trusted["public_key_sha256"]
                or now < float(trusted["not_before"])
                or (trusted["not_after"] is not None and now >= float(trusted["not_after"]))
                or float(claims["issued_at_unix"]) < float(trusted["not_before"])
                or (trusted["not_after"] is not None and float(claims["issued_at_unix"]) >= float(trusted["not_after"]))
            ):
                raise FencingAttestationRejectedError(
                    "Provider grant issuer/key is not trusted for this Provider"
                )

            receipt = c.execute(
                """SELECT * FROM provider_grant_commands
                   WHERE command_sha256=? AND provider_id=? AND tenant_id=?""",
                (command_digest, self.provider_id, self.tenant_id),
            ).fetchone()
            if receipt is not None:
                expected = (
                    claims["issuer_id"], key_id, self.provider_id, self.tenant_id,
                    scope, claims["action"], claims["grant_id"], int(claims["generation"]),
                    claims["coordinator_namespace"], claims["leader_id"],
                    int(claims["leader_epoch"]), int(claims["leader_lease_id"]),
                )
                observed = (
                    receipt["issuer_id"], receipt["key_id"], receipt["provider_id"],
                    receipt["tenant_id"], receipt["fencing_scope"], receipt["action"],
                    receipt["grant_id"], int(receipt["generation"]),
                    receipt["coordinator_namespace"], receipt["leader_id"],
                    int(receipt["leader_epoch"]), int(receipt["leader_lease_id"]),
                )
                if observed != expected:
                    raise FencingAttestationRejectedError(
                        "Provider grant receipt conflicts with its signed claims"
                    )
                current = c.execute(
                    """SELECT grant_generation,grant_id,state,grant_expires_at
                       FROM provider_scope_grants WHERE tenant_id=? AND fencing_scope=?""",
                    (self.tenant_id, scope),
                ).fetchone()
                return {
                    "result": "ALREADY_APPLIED", "scope": scope,
                    "generation": int(receipt["generation"]),
                    "state": receipt["result_state"], "command_sha256": command_digest,
                    "current_generation": int(current["grant_generation"]) if current else None,
                    "current_state": current["state"] if current else None,
                }

            if self.require_online_leader_status:
                try:
                    active = bool(self.leader_status_checker.is_leader_active(
                        {
                            "coordinator_namespace": claims["coordinator_namespace"],
                            "leader_id": claims["leader_id"],
                            "leader_epoch": claims["leader_epoch"],
                            "leader_lease_id": claims["leader_lease_id"],
                            "leader_lease_expires_at_unix": claims["leader_lease_expires_at_unix"],
                        },
                        now_unix=now,
                    ))
                except Exception as exc:
                    raise FencingAttestationStatusUnavailableError(
                        "Coordinator online Leader status is unavailable; grant command refused"
                    ) from exc
                if not active:
                    raise FencingAttestationRejectedError(
                        "Coordinator Leader is absent, expired, revoked or does not match the grant command"
                    )

            current = c.execute(
                """SELECT * FROM provider_scope_grants
                   WHERE tenant_id=? AND fencing_scope=?""",
                (self.tenant_id, scope),
            ).fetchone()
            generation = int(claims["generation"])
            expected_generation = int(current["grant_generation"]) + 1 if current else 1
            if generation != expected_generation:
                raise FencingAttestationRejectedError(
                    "Provider grant generation is stale or skips the next generation"
                )
            namespace = claims["coordinator_namespace"]
            leader_id = claims["leader_id"]
            leader_epoch = int(claims["leader_epoch"])
            lease_id = int(claims["leader_lease_id"])
            lease_expires = float(claims["leader_lease_expires_at_unix"])
            grant_id = claims["grant_id"]
            action = claims["action"]
            fence_digest = command_digest if action == "FENCE" else claims["fence_command_sha256"]

            if current is not None and namespace != current["coordinator_namespace"]:
                raise FencingAttestationRejectedError(
                    "Coordinator namespace changed for an established Provider grant scope"
                )

            if action == "FENCE":
                if current is not None:
                    current_epoch = int(current["leader_epoch"])
                    if leader_epoch < current_epoch:
                        raise FencingAttestationRejectedError(
                            "FENCE was issued by a stale Coordinator Leader epoch"
                        )
                    if leader_epoch == current_epoch:
                        same_identity = (
                            leader_id == current["leader_id"]
                            and lease_id == int(current["leader_lease_id"])
                        )
                        if not same_identity:
                            raise FencingAttestationRejectedError(
                                "same-epoch FENCE cannot change Leader or native Lease identity"
                            )
                        if current["state"] == "FENCED":
                            raise SQLiteProviderGrantRejectedError(
                                "scope is already FENCED; activate the pending grant or use a newer epoch"
                            )
                        if lease_expires < float(current["leader_lease_expires_at"]):
                            raise FencingAttestationRejectedError(
                                "same-epoch FENCE Leader Lease expiry regressed"
                            )
                prior_grant = c.execute(
                    """SELECT 1 FROM provider_grant_commands
                       WHERE provider_id=? AND tenant_id=? AND fencing_scope=? AND grant_id=?
                       LIMIT 1""",
                    (self.provider_id, self.tenant_id, scope, grant_id),
                ).fetchone()
                if prior_grant is not None:
                    raise FencingAttestationRejectedError(
                        "Provider grant ID has already been used for this scope"
                    )
                state = "FENCED"
                grant_expires = None
                activation_digest = None
            else:
                if current is None or current["state"] != "FENCED":
                    raise SQLiteProviderGrantRejectedError(
                        "ACTIVATE requires a previously committed Provider FENCE"
                    )
                identity = (
                    namespace, leader_id, leader_epoch, lease_id, lease_expires, grant_id
                )
                fenced_identity = (
                    current["coordinator_namespace"], current["leader_id"],
                    int(current["leader_epoch"]), int(current["leader_lease_id"]),
                    float(current["leader_lease_expires_at"]), current["grant_id"],
                )
                if identity != fenced_identity:
                    raise FencingAttestationRejectedError(
                        "ACTIVATE does not match the pending FENCE Leader, Lease or grant identity"
                    )
                if claims["fence_command_sha256"] != current["fence_command_sha256"]:
                    raise FencingAttestationRejectedError(
                        "ACTIVATE does not reference the exact current FENCE receipt"
                    )
                fence_receipt = c.execute(
                    """SELECT result_state,action,provider_id,tenant_id,fencing_scope,
                              grant_id,generation,coordinator_namespace,leader_id,
                              leader_epoch,leader_lease_id,applied_at
                       FROM provider_grant_commands WHERE command_sha256=?""",
                    (claims["fence_command_sha256"],),
                ).fetchone()
                if (
                    fence_receipt is None or fence_receipt["action"] != "FENCE"
                    or fence_receipt["result_state"] != "FENCED"
                    or fence_receipt["provider_id"] != self.provider_id
                    or fence_receipt["tenant_id"] != self.tenant_id
                    or fence_receipt["fencing_scope"] != scope
                    or fence_receipt["grant_id"] != grant_id
                    or int(fence_receipt["generation"]) + 1 != generation
                    or fence_receipt["coordinator_namespace"] != namespace
                    or fence_receipt["leader_id"] != leader_id
                    or int(fence_receipt["leader_epoch"]) != leader_epoch
                    or int(fence_receipt["leader_lease_id"]) != lease_id
                    or float(claims["issued_at_unix"]) < float(fence_receipt["applied_at"])
                ):
                    raise SQLiteProviderGrantRejectedError(
                        "ACTIVATE is missing an exact durable FENCE receipt"
                    )
                state = "ACTIVE"
                grant_expires = float(claims["expires_at_unix"])
                activation_digest = command_digest

            c.execute(
                """INSERT INTO provider_scope_grants(
                    tenant_id,fencing_scope,coordinator_namespace,leader_id,
                    leader_epoch,leader_lease_id,leader_lease_expires_at,
                    grant_generation,grant_id,state,grant_expires_at,
                    fence_command_sha256,activation_command_sha256,updated_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(tenant_id,fencing_scope) DO UPDATE SET
                    coordinator_namespace=excluded.coordinator_namespace,
                    leader_id=excluded.leader_id,leader_epoch=excluded.leader_epoch,
                    leader_lease_id=excluded.leader_lease_id,
                    leader_lease_expires_at=excluded.leader_lease_expires_at,
                    grant_generation=excluded.grant_generation,
                    grant_id=excluded.grant_id,state=excluded.state,
                    grant_expires_at=excluded.grant_expires_at,
                    fence_command_sha256=excluded.fence_command_sha256,
                    activation_command_sha256=excluded.activation_command_sha256,
                    updated_at=excluded.updated_at""",
                (
                    self.tenant_id, scope, namespace, leader_id, leader_epoch,
                    lease_id, lease_expires, generation, grant_id, state,
                    grant_expires, fence_digest, activation_digest, now,
                ),
            )
            c.execute(
                """INSERT INTO provider_grant_commands(
                    command_sha256,issuer_id,key_id,provider_id,tenant_id,
                    fencing_scope,action,grant_id,generation,coordinator_namespace,
                    leader_id,leader_epoch,leader_lease_id,leader_lease_expires_at,
                    fence_command_sha256,result_state,applied_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    command_digest, claims["issuer_id"], key_id, self.provider_id,
                    self.tenant_id, scope, action, grant_id, generation, namespace,
                    leader_id, leader_epoch, lease_id, lease_expires,
                    claims["fence_command_sha256"], state, now,
                ),
            )
            self._inject("before_provider_grant_commit")
        # This hook simulates a lost response after the durable SQLite commit.
        self._inject("after_provider_grant_commit")
        return {
            "result": "APPLIED", "scope": scope, "generation": generation,
            "state": state, "grant_id": grant_id,
            "command_sha256": command_digest,
        }

    def provider_grant_command_status(self, command_sha256: str) -> dict[str, Any] | None:
        """Read-only recovery lookup for an exact signed FENCE/ACTIVATE envelope."""
        if not isinstance(command_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", command_sha256):
            raise BackupStorageError("Provider grant command digest must be 64 lowercase hexadecimal characters")
        if self.provider_id is None:
            raise BackupStorageError("Provider identity is required for grant receipt lookup")
        with self._read_transaction() as c:
            receipt = c.execute(
                """SELECT * FROM provider_grant_commands
                   WHERE command_sha256=? AND provider_id=? AND tenant_id=?""",
                (command_sha256, self.provider_id, self.tenant_id),
            ).fetchone()
            if receipt is None:
                return None
            result = dict(receipt)
            current = c.execute(
                """SELECT * FROM provider_scope_grants
                   WHERE tenant_id=? AND fencing_scope=?""",
                (self.tenant_id, result["fencing_scope"]),
            ).fetchone()
            result["current_scope_state"] = dict(current) if current is not None else None
            return result

    def provider_grant_state(self, fencing_scope: str) -> dict[str, Any] | None:
        """Read-only current Provider grant state for one scope."""
        scope = _safe_key(fencing_scope)
        with self._read_transaction() as c:
            row = c.execute(
                """SELECT coordinator_namespace,leader_id,leader_epoch,leader_lease_id,
                          leader_lease_expires_at,grant_generation,grant_id,state,
                          grant_expires_at,fence_command_sha256,activation_command_sha256,
                          updated_at
                   FROM provider_scope_grants WHERE tenant_id=? AND fencing_scope=?""",
                (self.tenant_id, scope),
            ).fetchone()
            return dict(row) if row is not None else None

    def write_freeze_command_status(self, command_sha256: str) -> dict[str, Any] | None:
        """Read-only lookup of a historical command receipt and current scope state."""
        if not isinstance(command_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", command_sha256):
            raise BackupStorageError("freeze command digest must be 64 lowercase hexadecimal characters")
        if self.provider_id is None:
            raise BackupStorageError("Provider identity must be configured for freeze receipt lookup")
        with self._read_transaction() as c:
            receipt = c.execute(
                """SELECT c.command_sha256,c.issuer_id,c.key_id,c.provider_id,c.tenant_id,
                          c.fencing_scope,c.action,c.freeze_id,c.generation,c.result_state,c.applied_at,
                          l.coordinator_namespace,l.leader_id,l.leader_epoch,l.leader_lease_id,
                          l.leader_lease_expires_at
                   FROM provider_write_freeze_commands c
                   LEFT JOIN provider_write_freeze_command_leaders l
                     ON l.command_sha256=c.command_sha256
                   WHERE c.command_sha256=? AND c.provider_id=? AND c.tenant_id=?""",
                (command_sha256, self.provider_id, self.tenant_id),
            ).fetchone()
            if receipt is None:
                return None
            result = dict(receipt)
            current = c.execute(
                """SELECT generation,freeze_id,state,updated_at FROM provider_write_freeze_scopes
                   WHERE tenant_id=? AND fencing_scope=?""",
                (result["tenant_id"], result["fencing_scope"]),
            ).fetchone()
            result["current_scope_state"] = dict(current) if current is not None else None
            return result

    def write_freeze_state(self, fencing_scope: str) -> dict[str, Any] | None:
        scope = _safe_key(fencing_scope)
        with self._transaction() as c:
            row = c.execute(
                """SELECT generation,freeze_id,state,command_sha256,updated_at
                   FROM provider_write_freeze_scopes
                   WHERE tenant_id=? AND fencing_scope=?""",
                (self.tenant_id, scope),
            ).fetchone()
            if row is None:
                return None
            result = dict(row)
            leader = c.execute(
                """SELECT coordinator_namespace,leader_id,leader_epoch,leader_lease_id,
                          leader_lease_expires_at,observed_at
                   FROM provider_write_freeze_leader_floors
                   WHERE tenant_id=? AND fencing_scope=?""",
                (self.tenant_id, scope),
            ).fetchone()
            result["leader_floor"] = dict(leader) if leader is not None else None
            return result

    def _connect(self) -> sqlite3.Connection:
        c = sqlite3.connect(
            str(self.database_path),
            timeout=self.busy_timeout_seconds,
            isolation_level=None,
        )
        c.row_factory = sqlite3.Row
        c.execute(f"PRAGMA busy_timeout={int(self.busy_timeout_seconds * 1000)}")
        c.execute("PRAGMA foreign_keys=ON")
        c.execute("PRAGMA synchronous=FULL")
        return c

    @contextmanager
    def _transaction(self):
        c = self._connect()
        try:
            c.execute("BEGIN IMMEDIATE")
            yield c
            c.commit()
        except sqlite3.Error as exc:
            try:
                c.rollback()
            except sqlite3.Error:
                pass
            raise ProviderTransientError(
                "SQLite fenced Provider transaction failed",
                outcome_unknown=True,
            ) from exc
        except Exception:
            try:
                c.rollback()
            except sqlite3.Error:
                pass
            raise
        finally:
            c.close()

    @contextmanager
    def _read_transaction(self):
        """Consistent read snapshot without taking SQLite's RESERVED write lock."""
        c = self._connect()
        try:
            c.execute("BEGIN")
            yield c
            c.commit()
        except sqlite3.Error as exc:
            try:
                c.rollback()
            except sqlite3.Error:
                pass
            raise ProviderTransientError(
                "SQLite fenced Provider read transaction failed",
                outcome_unknown=True,
            ) from exc
        except Exception:
            try:
                c.rollback()
            except sqlite3.Error:
                pass
            raise
        finally:
            c.close()

    @contextmanager
    def _authorized_transaction(
        self, *, action: str, object_key: str, fencing_scope: str | None = None
    ):
        try:
            with self._transaction() as c:
                principal = c.execute(
                    "SELECT * FROM provider_principals WHERE principal_id=?",
                    (self.principal_id,),
                ).fetchone()
                if principal is None or not principal["enabled"]:
                    raise SQLiteProviderAuthorizationError("Provider principal is disabled or unknown")
                prefixes = json.loads(principal["allowed_prefixes_json"])
                actions = json.loads(principal["allowed_actions_json"])
                if action not in actions or not self._within_prefixes(object_key, prefixes):
                    raise SQLiteProviderAuthorizationError("Provider action or object prefix is not authorized")
                if fencing_scope is not None:
                    if not self._scope_contains_key(fencing_scope, object_key):
                        raise SQLiteProviderAuthorizationError(
                            "Provider object key is outside the supplied fencing scope"
                        )
                    if not self._within_prefixes(fencing_scope, prefixes):
                        raise SQLiteProviderAuthorizationError(
                            "Provider fencing scope is outside the principal's allowed prefixes"
                        )
                yield c, principal["tenant_id"]
        except SQLiteProviderAuthorizationError:
            self._record_denial(action, object_key, fencing_scope)
            raise

    @staticmethod
    def _within_prefixes(value: str, prefixes: list[str]) -> bool:
        return any(value == prefix or value.startswith(prefix + "/") for prefix in prefixes)

    @staticmethod
    def _scope_contains_key(scope: str, object_key: str) -> bool:
        return object_key.startswith(scope + "/")

    def _authenticate_initial_session(self) -> None:
        try:
            with self._transaction() as c:
                row = c.execute(
                    "SELECT tenant_id,secret_salt,secret_hash,enabled "
                    "FROM provider_principals WHERE principal_id=?",
                    (self.principal_id,),
                ).fetchone()
                if row is None or not row["enabled"]:
                    raise SQLiteProviderAuthorizationError("Provider principal is disabled or unknown")
                supplied = hashlib.pbkdf2_hmac(
                    "sha256", self._principal_secret, row["secret_salt"], PBKDF2_ITERATIONS
                )
                if not hmac.compare_digest(supplied, row["secret_hash"]):
                    raise SQLiteProviderAuthorizationError("Provider principal secret is invalid")
                self.tenant_id = row["tenant_id"]
        except SQLiteProviderAuthorizationError:
            raise
        except sqlite3.Error as exc:
            raise BackupStorageError("cannot authenticate against SQLite Provider database") from exc

    def _record_denial(self, action: str, object_key: str, fencing_scope: str | None) -> None:
        try:
            with self._transaction() as c:
                principal = c.execute(
                    "SELECT tenant_id FROM provider_principals WHERE principal_id=?",
                    (self.principal_id,),
                ).fetchone()
                tenant_id = principal["tenant_id"] if principal else "UNKNOWN"
                c.execute(
                    """INSERT INTO provider_audit(
                        principal_id,tenant_id,action,object_key,fencing_scope,
                        fencing_token,idempotency_key,outcome,created_at
                    ) VALUES(?,?,?,?,?,NULL,NULL,'DENY',?)""",
                    (self.principal_id, tenant_id, action, object_key, fencing_scope, time.time()),
                )
        except sqlite3.Error:
            # Denial remains fail-closed even if audit persistence is unavailable.
            pass

    def _record_allow(
        self, c: sqlite3.Connection, *, tenant_id: str, action: str,
        object_key: str, fencing_scope: str | None = None,
        fencing_token: int | None = None, idempotency_key: str | None = None,
        outcome: str = "ALLOW",
    ) -> None:
        c.execute(
            """INSERT INTO provider_audit(
                principal_id,tenant_id,action,object_key,fencing_scope,
                fencing_token,idempotency_key,outcome,created_at
            ) VALUES(?,?,?,?,?,?,?,?,?)""",
            (
                self.principal_id, tenant_id, action, object_key, fencing_scope,
                fencing_token, idempotency_key, outcome, time.time(),
            ),
        )

    def _inject(self, phase: str) -> None:
        if self.fault_hook is not None:
            self.fault_hook(phase)

    def _verify_fencing_attestation(
        self, token: str, *, fencing_scope: str, resource_key: str,
        fencing_token: int, operation: str, idempotency_key: str,
    ) -> dict[str, Any]:
        try:
            claims, key_id = verify_fencing_attestation_signature(
                token,
                trusted_keys=self._trusted_attestation_keys,
                trusted_ed25519_public_keys=self._trusted_ed25519_public_keys,
            )
        except FencingAttestationError as exc:
            raise FencingAttestationRejectedError(str(exc)) from exc
        expected_domain = "write" if operation == "object:put_if_absent" else "multipart"
        algorithm = claims.get("alg", "HMAC-SHA256")
        expected_version = 2 if algorithm == "ED25519" else 1
        expected = {
            "v": expected_version, "kid": key_id, "tenant_id": self.tenant_id,
            "fencing_scope": fencing_scope, "resource_key": resource_key,
            "fencing_token": fencing_token, "operation": operation,
            "idempotency_key": idempotency_key, "domain": expected_domain,
        }
        for field, value in expected.items():
            if claims.get(field) != value:
                raise FencingAttestationRejectedError(
                    "fencing attestation claim mismatch: " + field
                )
        if (
            not isinstance(claims.get("iss"), str) or not claims["iss"].strip()
            or not isinstance(claims.get("lease_id"), str) or not claims["lease_id"].strip()
            or not isinstance(claims.get("owner_id"), str) or not claims["owner_id"].strip()
        ):
            raise FencingAttestationRejectedError("fencing attestation lease identity is incomplete")
        now = time.time()
        issued = claims.get("issued_at")
        expires = claims.get("expires_at")
        lease_expires = claims.get("lease_expires_at")
        if any(
            not isinstance(value, (int, float)) or isinstance(value, bool)
            or not 0 <= float(value) < float("inf")
            for value in (issued, expires, lease_expires)
        ):
            raise FencingAttestationRejectedError("fencing attestation time claims are invalid")
        if (
            float(issued) > now + 5.0
            or float(expires) <= now
            or float(expires) <= float(issued)
            or float(expires) > float(lease_expires)
            or float(expires) - float(issued) > 60.0
            or float(lease_expires) <= now
        ):
            raise FencingAttestationRejectedError("fencing attestation is expired or exceeds its lease")
        base_claim_count = 15 if algorithm == "HMAC-SHA256" else 16
        has_freeze_generation = "provider_freeze_generation" in claims
        has_grant_id = "provider_grant_id" in claims
        has_grant_generation = "provider_grant_generation" in claims
        if has_grant_id != has_grant_generation:
            raise FencingAttestationRejectedError("Provider grant claims must be supplied together")
        has_provider_grant = has_grant_id and has_grant_generation
        if (
            algorithm not in {"HMAC-SHA256", "ED25519"}
            or len(claims) != base_claim_count + int(has_freeze_generation) + 2 * int(has_provider_grant)
            or (algorithm == "ED25519" and claims.get("alg") != "ED25519")
        ):
            raise FencingAttestationRejectedError("fencing attestation contains unknown or missing claims")
        if has_freeze_generation and (
            not isinstance(claims["provider_freeze_generation"], int)
            or isinstance(claims["provider_freeze_generation"], bool)
            or claims["provider_freeze_generation"] <= 0
        ):
            raise FencingAttestationRejectedError("provider freeze generation claim is invalid")
        if has_provider_grant and (
            not isinstance(claims["provider_grant_id"], str)
            or not claims["provider_grant_id"].strip()
            or len(claims["provider_grant_id"]) > 128
            or not isinstance(claims["provider_grant_generation"], int)
            or isinstance(claims["provider_grant_generation"], bool)
            or claims["provider_grant_generation"] <= 0
        ):
            raise FencingAttestationRejectedError("Provider grant claims are invalid")
        return claims

    def _authorize_fencing_attestation(
        self, c: sqlite3.Connection, *, claims: dict[str, Any], tenant_id: str
    ) -> None:
        algorithm = claims.get("alg", "HMAC-SHA256")
        if algorithm == "ED25519":
            row = c.execute(
                """SELECT algorithm,public_key_sha256,status,not_before,not_after
                   FROM trusted_ed25519_keys WHERE issuer_id=? AND key_id=?""",
                (claims["iss"], claims["kid"]),
            ).fetchone()
            public_key = self._trusted_ed25519_public_keys.get(claims["kid"])
            fingerprint_matches = bool(
                row is not None and public_key is not None
                and self._ed25519_public_key_fingerprint(public_key) == row["public_key_sha256"]
            )
            algorithm_matches = row is not None and row["algorithm"] == "ED25519"
        else:
            row = c.execute(
                """SELECT algorithm,status,not_before,not_after
                   FROM trusted_fencing_keys WHERE issuer_id=? AND key_id=?""",
                (claims["iss"], claims["kid"]),
            ).fetchone()
            fingerprint_matches = claims["kid"] in self._trusted_attestation_keys
            algorithm_matches = row is not None and row["algorithm"] == "HMAC-SHA256"
        now = time.time()
        if (
            row is None or not algorithm_matches or not fingerprint_matches
            or row["status"] not in {"ACTIVE", "RETIRING"}
            or now < float(row["not_before"])
            or (row["not_after"] is not None and now >= float(row["not_after"]))
            or float(claims["issued_at"]) < float(row["not_before"])
            or (row["not_after"] is not None and float(claims["issued_at"]) >= float(row["not_after"]))
            or claims["tenant_id"] != tenant_id
        ):
            raise FencingAttestationRejectedError(
                "fencing attestation issuer/key is not trusted for this tenant or time window"
            )
        if self.require_online_attestation_status:
            try:
                if self.require_atomic_online_attestation_status:
                    active = bool(
                        self.attestation_status_checker.is_attestation_active_in_transaction(c, claims)
                    )
                    if active:
                        # Test-only synchronization point; no-op unless a fault hook is injected.
                        self._inject("after_atomic_online_attestation_status_check")
                else:
                    active = bool(self.attestation_status_checker.is_attestation_active(claims))
            except Exception as exc:
                raise FencingAttestationStatusUnavailableError(
                    "Coordinator online attestation status is unavailable; Provider write refused"
                ) from exc
            if not active:
                raise FencingAttestationRejectedError(
                    "Coordinator reports the fencing lease is released, expired or unknown"
                )

    def _authorize_provider_write_freeze(
        self, c: sqlite3.Connection, *, tenant_id: str,
        fencing_scope: str, claims: dict[str, Any],
    ) -> None:
        freeze = c.execute(
            """SELECT generation,freeze_id,state FROM provider_write_freeze_scopes
               WHERE tenant_id=? AND fencing_scope=?""",
            (tenant_id, fencing_scope),
        ).fetchone()
        if freeze is None:
            if "provider_freeze_generation" in claims:
                raise FencingAttestationRejectedError(
                    "write proof references a Provider freeze generation that is not installed"
                )
        else:
            if freeze["state"] == "FROZEN":
                raise SQLiteProviderWriteFrozenError(
                    "Provider-native write freeze is active for this fencing scope"
                )
            if claims.get("provider_freeze_generation") != int(freeze["generation"]):
                raise FencingAttestationRejectedError(
                    "write proof is not bound to the current Provider freeze generation"
                )
            self._inject("after_provider_write_freeze_check")

        if self.require_revocable_grant:
            grant = c.execute(
                """SELECT coordinator_namespace,leader_id,leader_epoch,leader_lease_id,
                          grant_generation,grant_id,state,grant_expires_at
                   FROM provider_scope_grants
                   WHERE tenant_id=? AND fencing_scope=?""",
                (tenant_id, fencing_scope),
            ).fetchone()
            if grant is None or grant["state"] != "ACTIVE":
                raise SQLiteProviderGrantRejectedError(
                    "Provider grant is absent or fenced for this scope"
                )
            if (
                claims.get("provider_grant_id") != grant["grant_id"]
                or claims.get("provider_grant_generation") != int(grant["grant_generation"])
            ):
                raise SQLiteProviderGrantRejectedError(
                    "write proof does not match the current Provider grant generation"
                )
            now = time.time()
            if grant["grant_expires_at"] is None or float(grant["grant_expires_at"]) <= now:
                raise SQLiteProviderGrantRejectedError("Provider grant has expired")
            self._inject("after_provider_grant_check")

    @staticmethod
    def _validate_fenced_arguments(
        fencing_token: int, idempotency_key: str
    ) -> None:
        if (
            not isinstance(fencing_token, int) or isinstance(fencing_token, bool)
            or not 1 <= fencing_token <= MAX_FENCING_TOKEN
        ):
            raise BackupStorageError("fencing token must be a positive SQLite-safe integer")
        if (
            not isinstance(idempotency_key, str) or not idempotency_key.strip()
            or len(idempotency_key) > 256
        ):
            raise BackupStorageError("fenced operation idempotency key must contain 1..256 characters")

    def _prepare_fenced_operation(
        self, c: sqlite3.Connection, *, tenant_id: str, fencing_scope: str,
        fencing_token: int, idempotency_key: str, operation: str,
        operation_sha256: str,
    ) -> dict[str, Any] | None:
        meta = c.execute(
            "SELECT value FROM provider_meta WHERE key='minimum_fencing_token'"
        ).fetchone()
        floor = int(meta["value"]) if meta else 0
        row = c.execute(
            "SELECT high_water FROM fencing_scopes WHERE tenant_id=? AND fencing_scope=?",
            (tenant_id, fencing_scope),
        ).fetchone()
        high_water = max(floor, int(row["high_water"]) if row else 0)
        if fencing_token < high_water:
            raise StaleFencingTokenError(
                f"stale fencing token {fencing_token}; package scope high-water is {high_water}"
            )
        prior = c.execute(
            """SELECT operation,operation_sha256,result_json
               FROM fenced_operations
               WHERE tenant_id=? AND fencing_scope=? AND idempotency_key=?""",
            (tenant_id, fencing_scope, idempotency_key),
        ).fetchone()
        if prior is not None:
            if prior["operation"] != operation or prior["operation_sha256"] != operation_sha256:
                raise FencingTokenConflictError(
                    "fenced idempotency key was reused for a different operation or content"
                )
            c.execute(
                """INSERT INTO fencing_scopes(tenant_id,fencing_scope,high_water,updated_at)
                   VALUES(?,?,?,?) ON CONFLICT(tenant_id,fencing_scope)
                   DO UPDATE SET high_water=MAX(high_water,excluded.high_water),
                                 updated_at=excluded.updated_at""",
                (tenant_id, fencing_scope, fencing_token, time.time()),
            )
            return json.loads(prior["result_json"])
        if fencing_token == high_water:
            raise FencingTokenConflictError(
                "current fencing token was reused for a different idempotent operation"
            )
        return None

    def _commit_fenced_operation(
        self, c: sqlite3.Connection, *, tenant_id: str, object_key: str,
        fencing_scope: str, fencing_token: int, idempotency_key: str,
        operation: str, operation_sha256: str, result: dict[str, Any] | None,
    ) -> None:
        now = time.time()
        c.execute(
            """INSERT INTO fencing_scopes(tenant_id,fencing_scope,high_water,updated_at)
               VALUES(?,?,?,?) ON CONFLICT(tenant_id,fencing_scope)
               DO UPDATE SET high_water=MAX(high_water,excluded.high_water),
                             updated_at=excluded.updated_at""",
            (tenant_id, fencing_scope, fencing_token, now),
        )
        c.execute(
            """INSERT INTO fenced_operations(
                tenant_id,fencing_scope,idempotency_key,operation,
                operation_sha256,result_json,fencing_token,created_at
            ) VALUES(?,?,?,?,?,?,?,?)""",
            (
                tenant_id, fencing_scope, idempotency_key, operation,
                operation_sha256, json.dumps(result, sort_keys=True, separators=(",", ":")),
                fencing_token, now,
            ),
        )
        self._record_allow(
            c, tenant_id=tenant_id, action=operation, object_key=object_key,
            fencing_scope=fencing_scope, fencing_token=fencing_token,
            idempotency_key=idempotency_key,
        )
        # Test-only crash point: the object mutation, fence and receipt still share
        # one transaction; raising here must roll all of them back.
        self._inject("before_commit")

    @staticmethod
    def _operation_hash(operation: str, identity: dict[str, Any]) -> str:
        value = {"operation": operation, **identity}
        return _sha(_json_bytes(value))

    def _get_object_row(
        self, c: sqlite3.Connection, tenant_id: str, object_key: str
    ) -> sqlite3.Row | None:
        return c.execute(
            "SELECT * FROM provider_objects WHERE tenant_id=? AND object_key=?",
            (tenant_id, object_key),
        ).fetchone()

    @staticmethod
    def _stored_object(row: sqlite3.Row) -> StoredObject:
        return StoredObject(
            key=row["object_key"], data=bytes(row["data"]),
            content_sha256=row["content_sha256"], size_bytes=int(row["size_bytes"]),
            version_id=row["version_id"],
        )

    def _after_commit(self) -> None:
        # A raised timeout here models a committed operation with a lost response.
        self._inject("after_commit_before_response")

    def put_if_absent_fenced(
        self, key: str, data: bytes, *, fencing_scope: str,
        fencing_token: int, idempotency_key: str, fencing_attestation: str,
    ) -> StoredObject:
        normalized_key = _safe_key(key)
        normalized_scope = _safe_key(fencing_scope)
        self._validate_fenced_arguments(fencing_token, idempotency_key)
        if not isinstance(data, bytes):
            raise BackupStorageError("Provider object payload must be bytes")
        self._validate_fenced_arguments(fencing_token, idempotency_key)
        claims = self._verify_fencing_attestation(
            fencing_attestation, fencing_scope=normalized_scope, resource_key=normalized_key,
            fencing_token=fencing_token, operation="object:put_if_absent", idempotency_key=idempotency_key,
        )
        digest = _sha(data)
        operation = "object:write_fenced"
        operation_hash = self._operation_hash(
            operation, {"key": normalized_key, "scope": normalized_scope,
                       "sha256": digest, "size_bytes": len(data)}
        )
        with self._authorized_transaction(
            action=operation, object_key=normalized_key, fencing_scope=normalized_scope
        ) as (c, tenant_id):
            self._authorize_fencing_attestation(c, claims=claims, tenant_id=tenant_id)
            self._authorize_provider_write_freeze(
                c, tenant_id=tenant_id, fencing_scope=claims["fencing_scope"],
                claims=claims,
            )
            prior = self._prepare_fenced_operation(
                c, tenant_id=tenant_id, fencing_scope=normalized_scope,
                fencing_token=fencing_token, idempotency_key=idempotency_key,
                operation=operation, operation_sha256=operation_hash,
            )
            row = self._get_object_row(c, tenant_id, normalized_key)
            if prior is None:
                if row is not None:
                    if (
                        row["data"] != data
                        or row["fencing_scope"] != normalized_scope
                    ):
                        raise BackupStorageConflict(
                            "immutable object key already contains different bytes or scope"
                        )
                else:
                    c.execute(
                        """INSERT INTO provider_objects(
                            tenant_id,object_key,fencing_scope,data,content_sha256,
                            size_bytes,version_id,fencing_token,created_at
                        ) VALUES(?,?,?,?,?,?,NULL,?,?)""",
                        (
                            tenant_id, normalized_key, normalized_scope, data,
                            digest, len(data), fencing_token, time.time(),
                        ),
                    )
                self._inject("after_object_mutation_before_fence_commit")
                self._commit_fenced_operation(
                    c, tenant_id=tenant_id, object_key=normalized_key,
                    fencing_scope=normalized_scope, fencing_token=fencing_token,
                    idempotency_key=idempotency_key, operation=operation,
                    operation_sha256=operation_hash,
                    result={"object_key": normalized_key, "sha256": digest, "size_bytes": len(data)},
                )
            else:
                self._record_allow(
                    c, tenant_id=tenant_id, action=operation, object_key=normalized_key,
                    fencing_scope=normalized_scope, fencing_token=fencing_token,
                    idempotency_key=idempotency_key, outcome="REPLAY",
                )
            row = self._get_object_row(c, tenant_id, normalized_key)
            if row is None:
                raise BackupStorageError("fenced object operation committed without an object row")
            result = self._stored_object(row)
        self._after_commit()
        return result

    def begin_multipart_upload_fenced(
        self, key: str, upload_id: str, *, fencing_scope: str,
        fencing_token: int, idempotency_key: str, fencing_attestation: str,
    ) -> None:
        normalized_key, scope = _safe_key(key), _safe_key(fencing_scope)
        self._validate_fenced_arguments(fencing_token, idempotency_key)
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", upload_id or ""):
            raise BackupStorageError("multipart upload ID is invalid")
        claims = self._verify_fencing_attestation(
            fencing_attestation, fencing_scope=scope, resource_key=normalized_key,
            fencing_token=fencing_token, operation="multipart:begin", idempotency_key=idempotency_key,
        )
        action = "multipart:write_fenced"
        operation_hash = self._operation_hash(
            "multipart_begin", {"key": normalized_key, "scope": scope, "upload_id": upload_id}
        )
        with self._authorized_transaction(
            action=action, object_key=normalized_key, fencing_scope=scope
        ) as (c, tenant_id):
            self._authorize_fencing_attestation(c, claims=claims, tenant_id=tenant_id)
            self._authorize_provider_write_freeze(
                c, tenant_id=tenant_id, fencing_scope=claims["fencing_scope"],
                claims=claims,
            )
            prior = self._prepare_fenced_operation(
                c, tenant_id=tenant_id, fencing_scope=scope,
                fencing_token=fencing_token, idempotency_key=idempotency_key,
                operation="multipart_begin", operation_sha256=operation_hash,
            )
            if prior is None:
                if self._get_object_row(c, tenant_id, normalized_key) is not None:
                    raise BackupStorageConflict("cannot open a multipart session for a completed object")
                existing = c.execute(
                    """SELECT fencing_scope,state FROM multipart_sessions
                       WHERE tenant_id=? AND object_key=? AND upload_id=?""",
                    (tenant_id, normalized_key, upload_id),
                ).fetchone()
                if existing is not None and (
                    existing["fencing_scope"] != scope or existing["state"] != "ACTIVE"
                ):
                    raise BackupStorageConflict("multipart session ID conflicts with stored session state")
                c.execute(
                    """INSERT OR IGNORE INTO multipart_sessions(
                        tenant_id,object_key,upload_id,fencing_scope,state,created_at,updated_at
                    ) VALUES(?,?,?,?,'ACTIVE',?,?)""",
                    (tenant_id, normalized_key, upload_id, scope, time.time(), time.time()),
                )
                self._commit_fenced_operation(
                    c, tenant_id=tenant_id, object_key=normalized_key,
                    fencing_scope=scope, fencing_token=fencing_token,
                    idempotency_key=idempotency_key, operation="multipart_begin",
                    operation_sha256=operation_hash, result={"upload_id": upload_id},
                )
            else:
                self._record_allow(
                    c, tenant_id=tenant_id, action=action, object_key=normalized_key,
                    fencing_scope=scope, fencing_token=fencing_token,
                    idempotency_key=idempotency_key, outcome="REPLAY",
                )
        self._after_commit()

    def put_multipart_part_fenced(
        self, key: str, upload_id: str, part_number: int, data: bytes,
        expected_sha256: str, *, fencing_scope: str,
        fencing_token: int, idempotency_key: str, fencing_attestation: str,
    ) -> MultipartPart:
        normalized_key, scope = _safe_key(key), _safe_key(fencing_scope)
        self._validate_fenced_arguments(fencing_token, idempotency_key)
        if not isinstance(part_number, int) or isinstance(part_number, bool) or part_number < 1:
            raise BackupStorageError("multipart part number must be a positive integer")
        if not isinstance(data, bytes) or _sha(data) != expected_sha256:
            raise BackupStorageError("multipart part data or checksum is invalid")
        claims = self._verify_fencing_attestation(
            fencing_attestation, fencing_scope=scope, resource_key=normalized_key,
            fencing_token=fencing_token, operation="multipart:put_part", idempotency_key=idempotency_key,
        )
        action = "multipart:write_fenced"
        digest = _sha(data)
        operation_hash = self._operation_hash(
            "multipart_part", {
                "key": normalized_key, "scope": scope, "upload_id": upload_id,
                "part_number": part_number, "sha256": digest, "size_bytes": len(data),
            }
        )
        with self._authorized_transaction(
            action=action, object_key=normalized_key, fencing_scope=scope
        ) as (c, tenant_id):
            self._authorize_fencing_attestation(c, claims=claims, tenant_id=tenant_id)
            self._authorize_provider_write_freeze(
                c, tenant_id=tenant_id, fencing_scope=claims["fencing_scope"],
                claims=claims,
            )
            prior = self._prepare_fenced_operation(
                c, tenant_id=tenant_id, fencing_scope=scope,
                fencing_token=fencing_token, idempotency_key=idempotency_key,
                operation="multipart_part", operation_sha256=operation_hash,
            )
            session = c.execute(
                """SELECT fencing_scope,state FROM multipart_sessions
                   WHERE tenant_id=? AND object_key=? AND upload_id=?""",
                (tenant_id, normalized_key, upload_id),
            ).fetchone()
            if session is None or session["fencing_scope"] != scope or session["state"] != "ACTIVE":
                raise BackupStorageError("multipart session is missing, outside scope, or not active")
            if prior is None:
                existing = c.execute(
                    """SELECT data,content_sha256,size_bytes FROM multipart_parts
                       WHERE tenant_id=? AND object_key=? AND upload_id=? AND part_number=?""",
                    (tenant_id, normalized_key, upload_id, part_number),
                ).fetchone()
                if existing is not None and (
                    existing["data"] != data or existing["content_sha256"] != digest
                ):
                    raise BackupStorageConflict("multipart part number already contains different bytes")
                c.execute(
                    """INSERT OR IGNORE INTO multipart_parts(
                        tenant_id,object_key,upload_id,part_number,data,
                        content_sha256,size_bytes,fencing_token
                    ) VALUES(?,?,?,?,?,?,?,?)""",
                    (tenant_id, normalized_key, upload_id, part_number, data, digest, len(data), fencing_token),
                )
                c.execute(
                    """UPDATE multipart_sessions SET updated_at=?
                       WHERE tenant_id=? AND object_key=? AND upload_id=?""",
                    (time.time(), tenant_id, normalized_key, upload_id),
                )
                self._commit_fenced_operation(
                    c, tenant_id=tenant_id, object_key=normalized_key,
                    fencing_scope=scope, fencing_token=fencing_token,
                    idempotency_key=idempotency_key, operation="multipart_part",
                    operation_sha256=operation_hash,
                    result={"part_number": part_number, "sha256": digest, "size_bytes": len(data)},
                )
            else:
                self._record_allow(
                    c, tenant_id=tenant_id, action=action, object_key=normalized_key,
                    fencing_scope=scope, fencing_token=fencing_token,
                    idempotency_key=idempotency_key, outcome="REPLAY",
                )
            part = c.execute(
                """SELECT content_sha256,size_bytes FROM multipart_parts
                   WHERE tenant_id=? AND object_key=? AND upload_id=? AND part_number=?""",
                (tenant_id, normalized_key, upload_id, part_number),
            ).fetchone()
            if part is None:
                raise BackupStorageError("multipart idempotent receipt has no corresponding part")
            result = MultipartPart(part_number, part["content_sha256"], int(part["size_bytes"]))
        self._after_commit()
        return result

    def complete_multipart_upload_fenced(
        self, key: str, upload_id: str, *, expected_part_count: int,
        expected_size_bytes: int, expected_sha256: str,
        fencing_scope: str, fencing_token: int, idempotency_key: str,
        fencing_attestation: str,
    ) -> StoredObject:
        normalized_key, scope = _safe_key(key), _safe_key(fencing_scope)
        self._validate_fenced_arguments(fencing_token, idempotency_key)
        if (
            not isinstance(expected_part_count, int) or isinstance(expected_part_count, bool)
            or expected_part_count < 1
            or not isinstance(expected_size_bytes, int) or isinstance(expected_size_bytes, bool)
            or expected_size_bytes < 0
            or not isinstance(expected_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_sha256)
        ):
            raise BackupStorageError("multipart completion metadata is invalid")
        claims = self._verify_fencing_attestation(
            fencing_attestation, fencing_scope=scope, resource_key=normalized_key,
            fencing_token=fencing_token, operation="multipart:complete", idempotency_key=idempotency_key,
        )
        action = "multipart:write_fenced"
        operation_hash = self._operation_hash(
            "multipart_complete", {
                "key": normalized_key, "scope": scope, "upload_id": upload_id,
                "part_count": expected_part_count, "size_bytes": expected_size_bytes,
                "sha256": expected_sha256,
            }
        )
        with self._authorized_transaction(
            action=action, object_key=normalized_key, fencing_scope=scope
        ) as (c, tenant_id):
            self._authorize_fencing_attestation(c, claims=claims, tenant_id=tenant_id)
            self._authorize_provider_write_freeze(
                c, tenant_id=tenant_id, fencing_scope=claims["fencing_scope"],
                claims=claims,
            )
            prior = self._prepare_fenced_operation(
                c, tenant_id=tenant_id, fencing_scope=scope,
                fencing_token=fencing_token, idempotency_key=idempotency_key,
                operation="multipart_complete", operation_sha256=operation_hash,
            )
            if prior is None:
                session = c.execute(
                    """SELECT state,fencing_scope FROM multipart_sessions
                       WHERE tenant_id=? AND object_key=? AND upload_id=?""",
                    (tenant_id, normalized_key, upload_id),
                ).fetchone()
                if session is None or session["state"] != "ACTIVE" or session["fencing_scope"] != scope:
                    raise BackupStorageError("multipart session is missing, outside scope, or not active")
                parts = c.execute(
                    """SELECT part_number,data FROM multipart_parts
                       WHERE tenant_id=? AND object_key=? AND upload_id=?
                       ORDER BY part_number""",
                    (tenant_id, normalized_key, upload_id),
                ).fetchall()
                if [int(row["part_number"]) for row in parts] != list(range(1, expected_part_count + 1)):
                    raise BackupStorageError("multipart part set is incomplete or unexpected")
                data = b"".join(bytes(row["data"]) for row in parts)
                if len(data) != expected_size_bytes or _sha(data) != expected_sha256:
                    raise BackupStorageError("multipart completion size or digest mismatch")
                existing = self._get_object_row(c, tenant_id, normalized_key)
                if existing is not None and (
                    existing["data"] != data or existing["fencing_scope"] != scope
                ):
                    raise BackupStorageConflict("completed object key already contains different data or scope")
                if existing is None:
                    c.execute(
                        """INSERT INTO provider_objects(
                            tenant_id,object_key,fencing_scope,data,content_sha256,
                            size_bytes,version_id,fencing_token,created_at
                        ) VALUES(?,?,?,?,?,?,NULL,?,?)""",
                        (tenant_id, normalized_key, scope, data, expected_sha256,
                         expected_size_bytes, fencing_token, time.time()),
                    )
                c.execute(
                    """UPDATE multipart_sessions SET state='COMPLETED',updated_at=?
                       WHERE tenant_id=? AND object_key=? AND upload_id=?""",
                    (time.time(), tenant_id, normalized_key, upload_id),
                )
                self._inject("after_object_mutation_before_fence_commit")
                self._commit_fenced_operation(
                    c, tenant_id=tenant_id, object_key=normalized_key,
                    fencing_scope=scope, fencing_token=fencing_token,
                    idempotency_key=idempotency_key, operation="multipart_complete",
                    operation_sha256=operation_hash,
                    result={"object_key": normalized_key, "sha256": expected_sha256,
                            "size_bytes": expected_size_bytes},
                )
            else:
                self._record_allow(
                    c, tenant_id=tenant_id, action=action, object_key=normalized_key,
                    fencing_scope=scope, fencing_token=fencing_token,
                    idempotency_key=idempotency_key, outcome="REPLAY",
                )
            row = self._get_object_row(c, tenant_id, normalized_key)
            if row is None:
                raise BackupStorageError("multipart completion receipt has no committed object")
            result = self._stored_object(row)
        self._after_commit()
        return result

    def put_if_absent(self, key: str, data: bytes) -> StoredObject:
        raise FencingNotSupportedError("SQLite fenced Provider refuses non-fenced object writes")

    def begin_multipart_upload(self, key: str, upload_id: str) -> None:
        raise FencingNotSupportedError("SQLite fenced Provider requires fenced multipart begin")

    def put_multipart_part(
        self, key: str, upload_id: str, part_number: int, data: bytes, expected_sha256: str
    ) -> MultipartPart:
        raise FencingNotSupportedError("SQLite fenced Provider requires fenced multipart part writes")

    def complete_multipart_upload(
        self, key: str, upload_id: str, *, expected_part_count: int,
        expected_size_bytes: int, expected_sha256: str
    ) -> StoredObject:
        raise FencingNotSupportedError("SQLite fenced Provider requires fenced multipart completion")

    def abort_multipart_upload(self, key: str, upload_id: str) -> None:
        raise FencingNotSupportedError("unfenced multipart abort is disabled")

    def get_object(self, key: str, *, version_id: str | None = None) -> StoredObject:
        normalized = _safe_key(key)
        if version_id is not None:
            raise BackupStorageError("SQLite fenced Provider does not support object version IDs")
        with self._authorized_transaction(action="object:read", object_key=normalized) as (c, tenant_id):
            row = self._get_object_row(c, tenant_id, normalized)
            if row is None:
                raise SQLiteProviderObjectNotFoundError("object does not exist in this tenant namespace")
            result = self._stored_object(row)
            self._record_allow(c, tenant_id=tenant_id, action="object:read", object_key=normalized)
        return result

    def list_multipart_parts(self, key: str, upload_id: str) -> list[MultipartPart]:
        normalized = _safe_key(key)
        with self._authorized_transaction(
            action="multipart:read", object_key=normalized
        ) as (c, tenant_id):
            rows = c.execute(
                """SELECT part_number,content_sha256,size_bytes FROM multipart_parts
                   WHERE tenant_id=? AND object_key=? AND upload_id=? ORDER BY part_number""",
                (tenant_id, normalized, upload_id),
            ).fetchall()
            result = [
                MultipartPart(int(r["part_number"]), r["content_sha256"], int(r["size_bytes"]))
                for r in rows
            ]
            self._record_allow(c, tenant_id=tenant_id, action="multipart:read", object_key=normalized)
        return result

    def list_objects(self, prefix: str) -> list[ObjectMetadata]:
        normalized = _safe_key(prefix.rstrip("/"))
        with self._authorized_transaction(
            action="object:list_prefix", object_key=normalized
        ) as (c, tenant_id):
            rows = c.execute(
                """SELECT object_key,content_sha256,size_bytes,version_id
                   FROM provider_objects WHERE tenant_id=?
                   AND (object_key=? OR object_key LIKE ? ESCAPE '\\')
                   ORDER BY object_key""",
                (tenant_id, normalized, self._like_prefix(normalized)),
            ).fetchall()
            result = [
                ObjectMetadata(r["object_key"], r["content_sha256"], int(r["size_bytes"]), r["version_id"])
                for r in rows
            ]
            self._record_allow(c, tenant_id=tenant_id, action="object:list_prefix", object_key=normalized)
        return result

    @staticmethod
    def _like_prefix(prefix: str) -> str:
        escaped = prefix.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        return escaped + "/%"

    def list_multipart_uploads(self, prefix: str) -> list[dict[str, Any]]:
        normalized = _safe_key(prefix.rstrip("/"))
        with self._authorized_transaction(
            action="multipart:list", object_key=normalized
        ) as (c, tenant_id):
            rows = c.execute(
                """SELECT object_key,upload_id,state,fencing_scope,created_at,updated_at
                   FROM multipart_sessions WHERE tenant_id=? AND state='ACTIVE'
                   AND (object_key=? OR object_key LIKE ? ESCAPE '\\')
                   ORDER BY object_key,upload_id""",
                (tenant_id, normalized, self._like_prefix(normalized)),
            ).fetchall()
            result = [dict(row) for row in rows]
            self._record_allow(c, tenant_id=tenant_id, action="multipart:list", object_key=normalized)
        return result

    def fencing_high_water(self, fencing_scope: str) -> int:
        scope = _safe_key(fencing_scope)
        with self._authorized_transaction(
            action="object:list_prefix", object_key=scope
        ) as (c, tenant_id):
            row = c.execute(
                "SELECT high_water FROM fencing_scopes WHERE tenant_id=? AND fencing_scope=?",
                (tenant_id, scope),
            ).fetchone()
            meta = c.execute(
                "SELECT value FROM provider_meta WHERE key='minimum_fencing_token'"
            ).fetchone()
            return max(int(row["high_water"]) if row else 0, int(meta["value"]) if meta else 0)

    def diagnostics(self) -> dict[str, Any]:
        # Probe using a real allowed prefix instead of a synthetic key outside ACL.
        with self._transaction() as c:
            principal = c.execute(
                "SELECT tenant_id,allowed_prefixes_json,allowed_actions_json,enabled "
                "FROM provider_principals WHERE principal_id=?",
                (self.principal_id,),
            ).fetchone()
            if principal is None or not principal["enabled"]:
                raise SQLiteProviderAuthorizationError("Provider principal is disabled or unknown")
            prefixes = json.loads(principal["allowed_prefixes_json"])
            actions = json.loads(principal["allowed_actions_json"])
            if "object:list_prefix" not in actions or not prefixes:
                raise SQLiteProviderAuthorizationError("Provider diagnostics are not authorized")
            probe_prefix = prefixes[0]
        with self._authorized_transaction(
            action="object:list_prefix", object_key=probe_prefix
        ) as (c, tenant_id):
            scopes = c.execute(
                "SELECT COUNT(*) AS n FROM fencing_scopes WHERE tenant_id=?", (tenant_id,)
            ).fetchone()["n"]
            objects = c.execute(
                "SELECT COUNT(*) AS n FROM provider_objects WHERE tenant_id=?", (tenant_id,)
            ).fetchone()["n"]
            sessions = c.execute(
                "SELECT COUNT(*) AS n FROM multipart_sessions WHERE tenant_id=?", (tenant_id,)
            ).fetchone()["n"]
            meta = c.execute(
                "SELECT value FROM provider_meta WHERE key='minimum_fencing_token'"
            ).fetchone()
            self._record_allow(
                c, tenant_id=tenant_id, action="object:list_prefix", object_key=probe_prefix
            )
            # Diagnostics is intentionally limited to local implementation metrics.
            return {
                "backend": "SQLITE_LOCAL_FENCED_REFERENCE",
                "journal_mode": "WAL",
                "synchronous": "FULL",
                "multi_process_same_host": True,
                "multi_host_supported": False,
                "principal_id": self.principal_id,
                "tenant_id": tenant_id,
                "fencing_scope_count": int(scopes),
                "object_count": int(objects),
                "multipart_session_count": int(sessions),
                "minimum_fencing_token": int(meta["value"]) if meta else 0,
                "supports_fencing": True,
            }

    def backup_to(self, destination_path: str | os.PathLike[str]) -> dict[str, Any]:
        """Create a consistent online snapshot at a new immutable path."""
        destination = Path(destination_path).expanduser().resolve()
        if destination == self.database_path or destination.exists():
            raise BackupStorageError("Provider backup destination must be a new file")
        destination.parent.mkdir(parents=True, exist_ok=True)
        staging = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.staging")
        source = target = None
        try:
            source = sqlite3.connect(str(self.database_path), timeout=self.busy_timeout_seconds)
            source.execute(f"PRAGMA busy_timeout={int(self.busy_timeout_seconds * 1000)}")
            target = sqlite3.connect(str(staging), timeout=self.busy_timeout_seconds)
            source.backup(target, pages=256, sleep=0.05)
            target.commit()
            target.close()
            target = None
            source.close()
            source = None
            report = self.validate_backup(staging)
            os.chmod(staging, 0o600)
            with staging.open("rb") as stream:
                os.fsync(stream.fileno())
            os.link(staging, destination)
            staging.unlink()
            os.chmod(destination, 0o600)
            dir_fd = os.open(destination.parent, os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
            return {**report, "path": str(destination)}
        except BackupStorageError:
            raise
        except (sqlite3.Error, OSError) as exc:
            raise BackupStorageError("SQLite fenced Provider online backup failed") from exc
        finally:
            if target is not None:
                target.close()
            if source is not None:
                source.close()
            try:
                staging.unlink()
            except FileNotFoundError:
                pass

    @classmethod
    def validate_backup(cls, backup_path: str | os.PathLike[str]) -> dict[str, Any]:
        backup = Path(backup_path).expanduser().resolve()
        if not backup.is_file() or backup.is_symlink():
            raise BackupStorageError("Provider backup file is missing or unsafe")
        connection = None
        try:
            uri = "file:" + quote(str(backup), safe="/") + "?mode=ro"
            connection = sqlite3.connect(uri, uri=True)
            connection.row_factory = sqlite3.Row
            integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
            if integrity != "ok":
                raise BackupStorageError("Provider backup SQLite integrity check failed")
            fk = connection.execute("PRAGMA foreign_key_check").fetchall()
            if fk:
                raise BackupStorageError("Provider backup has foreign-key violations")
            meta = dict(connection.execute("SELECT key,value FROM provider_meta").fetchall())
            if meta.get("schema_version") != str(SCHEMA_VERSION):
                raise BackupStorageError("Provider backup schema version is unsupported")
            required = {
                "provider_principals", "trusted_fencing_keys", "fencing_scopes", "fenced_operations",
                "provider_objects", "multipart_sessions", "multipart_parts", "provider_audit",
                "provider_write_freeze_scopes", "provider_write_freeze_commands",
                "provider_write_freeze_leader_floors", "provider_write_freeze_command_leaders",
                "provider_scope_grants", "provider_grant_commands",
            }
            tables = {
                row["name"] for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            if not required.issubset(tables):
                raise BackupStorageError("Provider backup is missing required tables")
            report = {
                "result": "VALID",
                "schema_version": SCHEMA_VERSION,
                "minimum_fencing_token": int(meta.get("minimum_fencing_token", "0")),
                "principal_count": int(connection.execute("SELECT COUNT(*) FROM provider_principals").fetchone()[0]),
                "fencing_scope_count": int(connection.execute("SELECT COUNT(*) FROM fencing_scopes").fetchone()[0]),
                "object_count": int(connection.execute("SELECT COUNT(*) FROM provider_objects").fetchone()[0]),
                "audit_record_count": int(connection.execute("SELECT COUNT(*) FROM provider_audit").fetchone()[0]),
                "integrity_check": integrity,
                "foreign_key_check": "PASS",
                "sha256": cls._sha256_file(backup),
            }
            return report
        except sqlite3.Error as exc:
            raise BackupStorageError("Provider backup cannot be validated") from exc
        finally:
            if connection is not None:
                connection.close()

    def restore_to_new_database(
        self,
        backup_path: str | os.PathLike[str],
        destination_path: str | os.PathLike[str],
        *,
        external_fencing_floor: int,
        fencing_reconciliation_ref: str,
    ) -> dict[str, Any]:
        """Prepare a new DB only; requires independent fencing floor reconciliation."""
        backup = Path(backup_path).expanduser().resolve()
        destination = Path(destination_path).expanduser().resolve()
        if not isinstance(external_fencing_floor, int) or isinstance(external_fencing_floor, bool):
            raise BackupStorageError("external fencing floor must be an integer")
        if not 0 <= external_fencing_floor <= MAX_FENCING_TOKEN:
            raise BackupStorageError("external fencing floor is out of range")
        if (
            not isinstance(fencing_reconciliation_ref, str)
            or not fencing_reconciliation_ref.strip()
            or len(fencing_reconciliation_ref.strip()) > 512
        ):
            raise BackupStorageError("restore requires an independent fencing reconciliation reference")
        if backup in {destination, self.database_path} or destination == self.database_path:
            raise BackupStorageError("restore must target a new Provider DB path")
        if destination.exists():
            raise BackupStorageError("restore destination exists; in-place overwrite is prohibited")
        report = self.validate_backup(backup)
        destination.parent.mkdir(parents=True, exist_ok=True)
        staging = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.restore")
        source = target = None
        invalidated_sessions = 0
        try:
            source = sqlite3.connect(
                "file:" + quote(str(backup), safe="/") + "?mode=ro",
                uri=True, timeout=self.busy_timeout_seconds,
            )
            target = sqlite3.connect(str(staging), timeout=self.busy_timeout_seconds, isolation_level=None)
            source.backup(target, pages=256, sleep=0.05)
            target.execute("PRAGMA foreign_keys=ON")
            target.execute("PRAGMA journal_mode=WAL")
            target.execute("PRAGMA synchronous=FULL")
            target.execute("BEGIN IMMEDIATE")
            rows = target.execute("SELECT COUNT(*) FROM multipart_sessions WHERE state='ACTIVE'").fetchone()[0]
            invalidated_sessions = int(rows)
            target.execute(
                """DELETE FROM multipart_parts WHERE EXISTS(
                    SELECT 1 FROM multipart_sessions s
                    WHERE s.tenant_id=multipart_parts.tenant_id
                      AND s.object_key=multipart_parts.object_key
                      AND s.upload_id=multipart_parts.upload_id
                      AND s.state='ACTIVE'
                )"""
            )
            target.execute("DELETE FROM multipart_sessions WHERE state='ACTIVE'")
            target.execute(
                """UPDATE fencing_scopes SET high_water=MAX(high_water,?),updated_at=?""",
                (external_fencing_floor, time.time()),
            )
            current_floor = int(target.execute(
                "SELECT value FROM provider_meta WHERE key='minimum_fencing_token'"
            ).fetchone()[0])
            seeded_floor = max(current_floor, external_fencing_floor, report["minimum_fencing_token"])
            target.execute(
                "UPDATE provider_meta SET value=? WHERE key='minimum_fencing_token'",
                (str(seeded_floor),),
            )
            target.execute(
                "INSERT OR REPLACE INTO provider_meta(key,value) VALUES('restore_reconciliation_ref',?)",
                (fencing_reconciliation_ref.strip(),),
            )
            target.commit()
            target.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            target.close()
            target = None
            source.close()
            source = None
            validation = self.validate_backup(staging)
            os.chmod(staging, 0o600)
            with staging.open("rb") as stream:
                os.fsync(stream.fileno())
            os.link(staging, destination)
            staging.unlink()
            os.chmod(destination, 0o600)
            dir_fd = os.open(destination.parent, os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
            return {
                "result": "PREPARED_NEW_DATABASE_NOT_CUTOVER",
                "destination": str(destination),
                "external_fencing_floor": external_fencing_floor,
                "seeded_minimum_fencing_token": seeded_floor,
                "invalidated_active_multipart_sessions": invalidated_sessions,
                "reconciliation_ref": fencing_reconciliation_ref.strip(),
                "validation": validation,
                "cutover_performed": False,
                "source_database_modified": False,
            }
        except BackupStorageError:
            raise
        except (sqlite3.Error, OSError) as exc:
            raise BackupStorageError("SQLite fenced Provider restore preparation failed") from exc
        finally:
            if target is not None:
                target.close()
            if source is not None:
                source.close()
            try:
                staging.unlink()
            except FileNotFoundError:
                pass

    @staticmethod
    def _sha256_file(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def self_check() -> dict[str, Any]:
        with tempfile.TemporaryDirectory(prefix="ch17-sqlite-fenced-provider-") as tmp:
            root = Path(tmp)
            database = root / "provider.sqlite"
            secret = "synthetic-ci-secret-do-not-reuse"
            provision = SQLiteFencedObjectStorageProvider.provision_database(
                database,
                principals=[{
                    "principal_id": "ci-writer",
                    "tenant_id": "synthetic-tenant",
                    "principal_secret": secret,
                    "allowed_prefixes": ["cnc/ch17"],
                }],
                trusted_attestation_keys=[{
                    "issuer_id": "ci-coordinator", "key_id": "ci-key",
                    "algorithm": "HMAC-SHA256", "status": "ACTIVE",
                }],
            )
            provider = SQLiteFencedObjectStorageProvider(
                database, principal_id="ci-writer", principal_secret=secret,
                trusted_attestation_keys={"ci-key": "ci-fencing-attestation-key-000000000001"},
            )
            from scripts.spare_parts_fencing_attestation import create_fencing_attestation
            issued = time.time()
            provider.put_if_absent_fenced(
                "cnc/ch17/backup-selfcheck/payload.bin", b"synthetic",
                fencing_scope="cnc/ch17/backup-selfcheck",
                fencing_token=1, idempotency_key="ci-put-1",
                fencing_attestation=create_fencing_attestation({
                    "v": 1, "iss": "ci-coordinator", "kid": "ci-key",
                    "lease_id": "ci-lease-1", "owner_id": "ci-self-check",
                    "tenant_id": "synthetic-tenant", "domain": "write",
                    "fencing_token": 1, "issued_at": issued,
                    "expires_at": issued + 30, "lease_expires_at": issued + 30,
                    "fencing_scope": "cnc/ch17/backup-selfcheck",
                    "resource_key": "cnc/ch17/backup-selfcheck/payload.bin",
                    "operation": "object:put_if_absent", "idempotency_key": "ci-put-1",
                }, key_id="ci-key", secret="ci-fencing-attestation-key-000000000001"),
            )
            rejected = False
            try:
                provider.put_if_absent_fenced(
                    "cnc/ch17/backup-selfcheck/late.bin", b"late",
                    fencing_scope="cnc/ch17/backup-selfcheck",
                    fencing_token=1, idempotency_key="ci-stale-1",
                    fencing_attestation=create_fencing_attestation({
                        "v": 1, "iss": "ci-coordinator", "kid": "ci-key",
                        "lease_id": "ci-lease-2", "owner_id": "ci-self-check",
                        "tenant_id": "synthetic-tenant", "domain": "write",
                        "fencing_token": 1, "issued_at": issued,
                        "expires_at": issued + 30, "lease_expires_at": issued + 30,
                        "fencing_scope": "cnc/ch17/backup-selfcheck",
                        "resource_key": "cnc/ch17/backup-selfcheck/late.bin",
                        "operation": "object:put_if_absent", "idempotency_key": "ci-stale-1",
                    }, key_id="ci-key", secret="ci-fencing-attestation-key-000000000001"),
                )
            except (StaleFencingTokenError, FencingTokenConflictError):
                rejected = True
            if not rejected:
                raise AssertionError("stale/same token writer was not rejected")
            persisted = SQLiteFencedObjectStorageProvider(
                database, principal_id="ci-writer", principal_secret=secret,
                trusted_attestation_keys={"ci-key": "ci-fencing-attestation-key-000000000001"},
            )
            if persisted.fencing_high_water("cnc/ch17/backup-selfcheck") != 1:
                raise AssertionError("fencing high-water did not persist across provider instances")
            return {
                "result": "PASS",
                "provider_kind": "SQLITE_LOCAL_FENCED_REFERENCE",
                "provisioning": "PASS",
                "credential_verifier": "PBKDF2_SHA256_NO_PLAINTEXT_SECRET",
                "tenant_prefix_action_authorization": "PASS",
                "package_scope_high_water_persisted": "PASS",
                "stale_same_package_writer_rejected": "PASS",
                "sqlite_atomic_write_fence_receipt_transaction": "PASS",
                "file_mode": provision["file_mode"],
                "network_access": False,
                "multi_host_supported": False,
                "cloud_provider_integration": False,
                "production_approval": "NOT_APPROVED",
            }

    @classmethod
    def main(cls) -> int:
        parser = argparse.ArgumentParser(
            description="Run the synthetic local SQLite fenced Provider reference self-check."
        )
        parser.add_argument("--self-check", action="store_true")
        parser.add_argument("--report-json", type=Path)
        args = parser.parse_args()
        if not args.self_check:
            parser.error("--self-check is required; ad hoc Provider CRUD is deliberately unavailable")
        report = cls.self_check()
        rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        if args.report_json:
            args.report_json.parent.mkdir(parents=True, exist_ok=True)
            args.report_json.write_text(rendered, encoding="utf-8")
        print(rendered, end="")
        return 0 if report["result"] == "PASS" else 1


def main() -> int:
    return SQLiteFencedObjectStorageProvider.main()


if __name__ == "__main__":
    raise SystemExit(main())
