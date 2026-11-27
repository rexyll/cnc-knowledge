"""Fail-closed helpers for isolated SQLite-to-Unified migration namespaces.

This module only performs read-only preflight checks. It never creates keys,
leases, namespaces, or etcd credentials.
"""
from __future__ import annotations

from dataclasses import dataclass

from scripts.spare_parts_provider_authority_store import (
    AuthorityStoreError,
    AuthorityStoreRangeResult,
    EtcdV3CoordinatorAuthorityStore,
)

ISOLATED_ROOT = b"/cnc/migration/isolated/"


class MigrationNamespaceError(RuntimeError):
    """Raised when an isolated migration namespace is unsafe to use."""


@dataclass(frozen=True)
class NamespacePreflight:
    prefix: bytes
    revision: int
    existing_key_count: int


def validate_isolated_namespace(prefix: bytes) -> bytes:
    if (
        not isinstance(prefix, bytes)
        or not prefix.startswith(ISOLATED_ROOT)
        or not prefix.endswith(b"/")
        or b".." in prefix
        or any(byte < 0x21 or byte > 0x7E for byte in prefix)
    ):
        raise MigrationNamespaceError(
            "namespace must be a printable ASCII path under "
            "/cnc/migration/isolated/{single-id}/"
        )
    namespace_id = prefix[len(ISOLATED_ROOT):-1]
    if not namespace_id or b"/" in namespace_id:
        raise MigrationNamespaceError(
            "isolated migration namespace must contain exactly one identifier segment"
        )
    return prefix


def _prefix_range_end(prefix: bytes) -> bytes:
    end = bytearray(prefix)
    for index in range(len(end) - 1, -1, -1):
        if end[index] != 0xFF:
            end[index] += 1
            return bytes(end[: index + 1])
    return b"\x00"


def preflight_empty_namespace(
    store: EtcdV3CoordinatorAuthorityStore, prefix: bytes
) -> NamespacePreflight:
    """Linearizably verify that the complete prefix contains no keys.

    This is a point-in-time check, not a lock. The caller must additionally
    use an isolated cluster or server-side RBAC preventing concurrent writers.
    """
    validate_isolated_namespace(prefix)
    try:
        result: AuthorityStoreRangeResult = store.linearizable_range(
            prefix, range_end=_prefix_range_end(prefix)
        )
    except AuthorityStoreError:
        raise
    except Exception as exc:
        raise MigrationNamespaceError("namespace preflight failed closed") from exc
    if result.entries:
        sample = ", ".join(
            entry.key.decode("ascii", errors="backslashreplace")
            for entry in result.entries[:5]
        )
        raise MigrationNamespaceError(
            f"namespace is not empty ({len(result.entries)} keys); sample: {sample}"
        )
    return NamespacePreflight(
        prefix=prefix, revision=result.revision, existing_key_count=0
    )
