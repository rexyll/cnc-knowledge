#!/usr/bin/env python3
"""Read-only online verification of a Provider Freeze command's Coordinator Leader.

The verifier takes one linearizable prefix Range so the Scheduler aggregate and
native Lease-attached Leader key are observed at the same etcd revision. It
does not make that observation atomic with a later Provider SQLite commit.
"""
from __future__ import annotations

import json
import math
from typing import Any


class CoordinatorLeaderStatusUnavailableError(RuntimeError):
    """The Coordinator authority snapshot could not be read reliably."""


class EtcdCoordinatorLeaderStatusChecker:
    """Verify signed Leader claims against one linearizable Coordinator snapshot."""

    def __init__(self, store: Any) -> None:
        if not callable(getattr(store, "linearizable_range", None)):
            raise ValueError("Coordinator store must provide linearizable_range")
        self.store = store

    @staticmethod
    def _range_end(prefix: bytes) -> bytes:
        end = bytearray(prefix)
        for index in range(len(end) - 1, -1, -1):
            if end[index] != 0xFF:
                end[index] += 1
                return bytes(end[: index + 1])
        return b"\\x00"

    def is_leader_active(
        self, claims: dict[str, Any], *, now_unix: float
    ) -> bool:
        """Return False for stale/mismatched authority; raise on unavailable reads."""
        if not isinstance(claims, dict):
            return False
        namespace = claims.get("coordinator_namespace")
        if (
            not isinstance(namespace, str)
            or not namespace.startswith("/")
            or not namespace.endswith("/")
            or "//" in namespace
            or any(part in {"", ".", ".."} for part in namespace.strip("/").split("/"))
            or any(ch.isspace() for ch in namespace)
        ):
            return False
        prefix = namespace.encode("utf-8")
        state_key = prefix + b"scheduler/state"
        leader_key = prefix + b"coordinator/leader"
        try:
            snapshot = self.store.linearizable_range(
                prefix, range_end=self._range_end(prefix)
            )
        except Exception as exc:
            raise CoordinatorLeaderStatusUnavailableError(
                "linearizable Coordinator Leader snapshot is unavailable"
            ) from exc
        entries = {entry.key: entry for entry in snapshot.entries}
        state_entry = entries.get(state_key)
        leader_entry = entries.get(leader_key)
        if state_entry is None or leader_entry is None:
            return False
        try:
            state = json.loads(state_entry.value.decode("utf-8"))
            leader = json.loads(leader_entry.value.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError, AttributeError):
            return False
        if (
            not isinstance(state, dict)
            or state.get("schema_version") != 2
            or not isinstance(state.get("coordinator"), dict)
        ):
            return False
        aggregate_leader = state["coordinator"].get("leader")
        if not isinstance(aggregate_leader, dict) or aggregate_leader != leader:
            return False
        expected = (
            claims.get("leader_id"),
            claims.get("leader_epoch"),
            claims.get("leader_lease_id"),
        )
        observed = (
            leader.get("leader_id"),
            leader.get("epoch"),
            leader.get("backend_lease_id"),
        )
        if expected != observed:
            return False
        if (
            not isinstance(expected[1], int) or isinstance(expected[1], bool)
            or not isinstance(expected[2], int) or isinstance(expected[2], bool)
            or expected[1] <= 0 or expected[2] <= 0
            or leader_entry.lease_id != expected[2]
        ):
            return False
        expires = leader.get("expires_at")
        declared_expires = claims.get("leader_lease_expires_at_unix")
        if any(
            not isinstance(value, (int, float)) or isinstance(value, bool)
            or not math.isfinite(float(value))
            for value in (expires, declared_expires, now_unix)
        ):
            return False
        return (
            float(expires) > float(now_unix)
            and abs(float(expires) - float(declared_expires)) <= 1e-6
        )
