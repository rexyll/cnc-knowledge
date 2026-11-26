#!/usr/bin/env python3
"""Synthetic downstream fencing contract; no real cloud-provider integration."""
from __future__ import annotations

import hashlib
import threading
from dataclasses import dataclass
from typing import Protocol

from scripts.spare_parts_backup_storage_adapter import BackupStorageError


from scripts.spare_parts_backup_storage_adapter import (
    BackupStorageError, FencingContractError, FencingNotSupportedError,
    StaleFencingTokenError, FencingTokenConflictError,
)


@dataclass(frozen=True)
class FencedWriteReceipt:
    resource_key: str
    fencing_token: int
    idempotency_key: str
    content_sha256: str
    replayed: bool


class FencingAwareObjectStorageProvider(Protocol):
    """A target must atomically compare token, update high-water and commit bytes."""

    @property
    def supports_fencing(self) -> bool: ...

    def put_if_newer(
        self, resource_key: str, data: bytes, *,
        fencing_token: int, idempotency_key: str,
    ) -> FencedWriteReceipt: ...


def fenced_put(
    provider: object,
    resource_key: str,
    data: bytes,
    *,
    fencing_token: int,
    idempotency_key: str,
) -> FencedWriteReceipt:
    """Fail closed unless the provider explicitly implements the fenced-write API."""
    if not isinstance(resource_key, str) or not resource_key.strip():
        raise BackupStorageError("fenced resource key is required")
    if not isinstance(data, bytes):
        raise BackupStorageError("fenced write payload must be bytes")
    if not isinstance(fencing_token, int) or isinstance(fencing_token, bool) or fencing_token < 1:
        raise BackupStorageError("fencing token must be a positive integer")
    if not isinstance(idempotency_key, str) or not idempotency_key.strip():
        raise BackupStorageError("fenced write idempotency key is required")
    if getattr(provider, "supports_fencing", False) is not True:
        raise FencingNotSupportedError("provider has not declared downstream fencing support")
    operation = getattr(provider, "put_if_newer", None)
    if not callable(operation):
        raise FencingNotSupportedError("provider declares fencing but has no put_if_newer operation")
    return operation(
        resource_key.strip(), data,
        fencing_token=fencing_token,
        idempotency_key=idempotency_key.strip(),
    )


class SyntheticFencedObjectSink:
    """Thread-safe in-memory contract fixture; never represents a production provider."""

    supports_fencing = True

    def __init__(self):
        self._lock = threading.RLock()
        self._high_water: dict[str, int] = {}
        self._receipts: dict[tuple[str, int], tuple[str, str]] = {}
        self._objects: dict[str, bytes] = {}

    def put_if_newer(
        self, resource_key: str, data: bytes, *,
        fencing_token: int, idempotency_key: str,
    ) -> FencedWriteReceipt:
        if not isinstance(resource_key, str) or not resource_key.strip():
            raise BackupStorageError("fenced resource key is required")
        if not isinstance(data, bytes):
            raise BackupStorageError("fenced write payload must be bytes")
        if not isinstance(fencing_token, int) or isinstance(fencing_token, bool) or fencing_token < 1:
            raise BackupStorageError("fencing token must be a positive integer")
        if not isinstance(idempotency_key, str) or not idempotency_key.strip():
            raise BackupStorageError("fenced write idempotency key is required")
        key = resource_key.strip()
        request = idempotency_key.strip()
        digest = hashlib.sha256(data).hexdigest()
        with self._lock:
            high_water = self._high_water.get(key, 0)
            if fencing_token < high_water:
                raise StaleFencingTokenError(
                    f"stale fencing token {fencing_token}; resource high-water is {high_water}"
                )
            if fencing_token == high_water:
                prior = self._receipts.get((key, fencing_token))
                if prior == (request, digest):
                    return FencedWriteReceipt(key, fencing_token, request, digest, True)
                raise FencingTokenConflictError(
                    "equal fencing token was reused for a different operation or payload"
                )
            # The comparison, durable high-water update and object mutation are one
            # lock-protected fixture operation. A remote Provider must guarantee the
            # equivalent in one atomic conditional transaction.
            self._high_water[key] = fencing_token
            self._receipts[(key, fencing_token)] = (request, digest)
            self._objects[key] = data
            return FencedWriteReceipt(key, fencing_token, request, digest, False)

    def get(self, resource_key: str) -> bytes | None:
        with self._lock:
            return self._objects.get(resource_key)

    def high_water(self, resource_key: str) -> int:
        with self._lock:
            return self._high_water.get(resource_key, 0)
