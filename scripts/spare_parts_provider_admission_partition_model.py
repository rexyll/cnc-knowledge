#!/usr/bin/env python3
"""Pure reference model for sharded Provider Admission and bounded etcd transactions.

The model demonstrates:
* exact global + tenant quota with two-dimensional expiring permit slots;
* tenant-routed queues and bounded round-robin dispatch batches;
* one active leader per partition and non-overlapping fencing-token ranges;
* explicit etcd transaction operation/byte budgeting.

It is intentionally in-memory. It does not implement an etcd client, network
quorum, production clock, persistent dispatcher, or production cutover.
"""
from __future__ import annotations

import hashlib
import json
import math
import threading
import uuid
from dataclasses import dataclass
from typing import Any, Iterable


class AdmissionPartitionError(RuntimeError):
    """Base error for the partitioned admission reference model."""


class AdmissionPartitionPolicyError(AdmissionPartitionError):
    """An invalid partition, quota, lease or transaction policy was supplied."""


class AdmissionPartitionConflictError(AdmissionPartitionError):
    """A request identity, slot, leader or fencing reservation conflicts."""


class AdmissionPartitionCapacityError(AdmissionPartitionError):
    """The global or tenant permit pool is full."""


class AdmissionPartitionRequestFinalizedError(AdmissionPartitionError):
    """A request ID is already terminal and cannot be reused."""


class AdmissionPartitionStaleLeaderError(AdmissionPartitionError):
    """The caller is not the current leader of its admission partition."""


class AdmissionPartitionIntegrityError(AdmissionPartitionError):
    """The active/request/slot indexes do not describe the same lease set."""


def canonical_json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise AdmissionPartitionIntegrityError(
            "transaction planning object is not canonical JSON"
        ) from exc


def tenant_partition(tenant_id: str, partition_count: int) -> int:
    if not isinstance(tenant_id, str) or not tenant_id.strip():
        raise AdmissionPartitionPolicyError("tenant_id is required")
    if (
        not isinstance(partition_count, int)
        or isinstance(partition_count, bool)
        or partition_count < 1
        or partition_count > 4096
    ):
        raise AdmissionPartitionPolicyError(
            "partition_count must be in [1, 4096]"
        )
    digest = hashlib.sha256(tenant_id.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % partition_count


@dataclass(frozen=True)
class AdmissionLeaseRecord:
    lease_id: str
    request_id: str
    tenant_id: str
    owner_id: str
    task_id: str
    domain: str
    partition_id: int
    fencing_token: int
    expires_at: float
    global_slot: int
    tenant_slot: int
    state: str = "ACTIVE"


class PartitionFencingRangeAllocator:
    """Block allocator with partition leader fencing and non-reusable ranges.

    A partition has at most one active leader. A leader reserves a durable
    non-overlapping token interval from a single global allocator only when
    its local interval is exhausted. Tokens are monotonic within a partition;
    numeric order across independent partitions is not a wall-clock order.
    """

    def __init__(self, *, block_size: int = 64) -> None:
        if (
            not isinstance(block_size, int)
            or isinstance(block_size, bool)
            or block_size < 2
            or block_size > 1_000_000
        ):
            raise AdmissionPartitionPolicyError("block_size must be in [2, 1000000]")
        self.block_size = block_size
        self._global_high_water = 0
        self._leaders: dict[int, dict[str, Any]] = {}
        self._ranges: dict[int, dict[str, Any]] = {}
        self._lock = threading.RLock()

    def claim_leader(
        self,
        partition_id: int,
        owner_id: str,
        *,
        now: float,
        ttl_seconds: float,
        external_high_water_floor: int = 0,
    ) -> int:
        self._validate_partition(partition_id)
        owner = self._required_text(owner_id, "owner_id")
        self._finite(now, "now")
        ttl = self._finite(ttl_seconds, "ttl_seconds")
        if ttl < 1:
            raise AdmissionPartitionPolicyError("partition leader TTL must be >= 1")
        floor = self._nonnegative_int(external_high_water_floor, "external floor")
        with self._lock:
            current = self._leaders.get(partition_id)
            if current is not None and float(current["expires_at"]) > now:
                if current["owner_id"] != owner:
                    raise AdmissionPartitionConflictError(
                        "partition already has a live leader"
                    )
                if floor > self._global_high_water:
                    self._global_high_water = floor
                interval = self._ranges.get(partition_id)
                if interval is not None and floor >= int(interval["next"]):
                    # A newly observed external floor can invalidate the
                    # unconsumed suffix even while the same process still
                    # owns the partition. Abandon the remainder; the next
                    # token is reserved above global_high_water.
                    self._ranges.pop(partition_id, None)
                current["expires_at"] = now + ttl
                return int(current["epoch"])
            if floor > self._global_high_water:
                self._global_high_water = floor
            epoch = 1 if current is None else int(current["epoch"]) + 1
            self._leaders[partition_id] = {
                "owner_id": owner,
                "epoch": epoch,
                "expires_at": now + ttl,
            }
            # A failover never resumes an old partially used range. Its unused
            # tokens become permanent gaps; the new owner reserves above the
            # maximum reserved/external floor.
            self._ranges.pop(partition_id, None)
            return epoch

    def renew_leader(
        self, partition_id: int, owner_id: str, epoch: int, *, now: float, ttl_seconds: float
    ) -> None:
        with self._lock:
            leader = self._require_leader(partition_id, owner_id, epoch, now)
            ttl = self._finite(ttl_seconds, "ttl_seconds")
            if ttl < 1:
                raise AdmissionPartitionPolicyError("partition leader TTL must be >= 1")
            leader["expires_at"] = now + ttl

    def next_token(
        self,
        partition_id: int,
        owner_id: str,
        epoch: int,
        *,
        now: float,
    ) -> int:
        with self._lock:
            self._require_leader(partition_id, owner_id, epoch, now)
            interval = self._ranges.get(partition_id)
            if interval is None or int(interval["next"]) > int(interval["end"]):
                start = self._global_high_water + 1
                end = self._global_high_water + self.block_size
                if end > (2**63 - 1):
                    raise AdmissionPartitionPolicyError("fencing token space exhausted")
                self._global_high_water = end
                interval = {
                    "start": start,
                    "end": end,
                    "next": start,
                    "owner_id": owner_id,
                    "epoch": epoch,
                }
                self._ranges[partition_id] = interval
            if interval["owner_id"] != owner_id or int(interval["epoch"]) != epoch:
                raise AdmissionPartitionStaleLeaderError(
                    "token range belongs to another partition leader"
                )
            token = int(interval["next"])
            interval["next"] = token + 1
            return token

    @staticmethod
    def _required_text(value: str, label: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise AdmissionPartitionPolicyError(f"{label} is required")
        return value.strip()

    @staticmethod
    def _finite(value: float, label: str) -> float:
        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(float(value))
        ):
            raise AdmissionPartitionPolicyError(f"{label} must be finite")
        return float(value)

    @staticmethod
    def _nonnegative_int(value: int, label: str) -> int:
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise AdmissionPartitionPolicyError(f"{label} must be non-negative")
        return value

    @staticmethod
    def _validate_partition(partition_id: int) -> None:
        if not isinstance(partition_id, int) or isinstance(partition_id, bool) or partition_id < 0:
            raise AdmissionPartitionPolicyError("partition_id must be non-negative")

    def _require_leader(
        self, partition_id: int, owner_id: str, epoch: int, now: float
    ) -> dict[str, Any]:
        self._validate_partition(partition_id)
        self._finite(now, "now")
        self._nonnegative_int(epoch, "leader epoch")
        leader = self._leaders.get(partition_id)
        if (
            leader is None
            or leader["owner_id"] != owner_id
            or int(leader["epoch"]) != epoch
            or float(leader["expires_at"]) <= now
        ):
            raise AdmissionPartitionStaleLeaderError(
                "caller does not hold the active partition leadership lease"
            )
        return leader

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "global_reserved_high_water": self._global_high_water,
                "leaders": {k: dict(v) for k, v in self._leaders.items()},
                "ranges": {k: dict(v) for k, v in self._ranges.items()},
            }


class ShardedProviderAdmissionModel:
    """Logical tenant sharding plus exact global/tenant permit-slot claims.

    The same request claims one global slot and one tenant/domain slot. Both
    are created and deleted atomically in this model; in a real etcd adapter
    they belong in the same bounded Txn and share the same native Lease TTL.
    """

    def __init__(
        self,
        *,
        global_limits: dict[str, int],
        tenant_limits: dict[str, dict[str, int]] | None = None,
        partition_count: int = 16,
        aging_interval_seconds: float = 30.0,
        fencing_block_size: int = 64,
    ) -> None:
        if not isinstance(global_limits, dict) or not global_limits:
            raise AdmissionPartitionPolicyError("global_limits must be a non-empty mapping")
        self.global_limits = {
            self._required_text(k, "domain"): self._positive_int(v, f"global limit {k}")
            for k, v in global_limits.items()
        }
        if (
            not isinstance(partition_count, int)
            or isinstance(partition_count, bool)
            or not 1 <= partition_count <= 4096
        ):
            raise AdmissionPartitionPolicyError("partition_count must be in [1, 4096]")
        self.partition_count = partition_count
        self.aging_interval_seconds = self._finite(aging_interval_seconds, "aging interval")
        if self.aging_interval_seconds <= 0:
            raise AdmissionPartitionPolicyError("aging interval must be positive")
        self.tenant_limits: dict[str, dict[str, int]] = {}
        for tenant, limits in (tenant_limits or {}).items():
            self.tenant_limits[self._required_text(tenant, "tenant")] = {
                domain: self._positive_int(value, f"tenant limit {tenant}/{domain}")
                for domain, value in limits.items()
                if domain in self.global_limits
            }
        self.fencing = PartitionFencingRangeAllocator(block_size=fencing_block_size)
        self._global_slots = {
            domain: [None for _ in range(limit)]
            for domain, limit in self.global_limits.items()
        }
        self._tenant_slots: dict[tuple[str, str], list[str | None]] = {}
        self._active: dict[str, AdmissionLeaseRecord] = {}
        self._requests: dict[str, dict[str, Any]] = {}
        self._waiters: dict[tuple[str, str], list[dict[str, Any]]] = {}
        self._tenant_rr_cursor: dict[str, str | None] = {
            domain: None for domain in self.global_limits
        }
        self._local_waiter_sequence: dict[tuple[str, str], int] = {}
        self._lock = threading.RLock()

    def _tenant_limit(self, tenant_id: str, domain: str) -> int:
        return min(
            self.global_limits[domain],
            self.tenant_limits.get(tenant_id, {}).get(domain, self.global_limits[domain]),
        )

    def _tenant_slot_pool(self, tenant_id: str, domain: str) -> list[str | None]:
        key = (tenant_id, domain)
        if key not in self._tenant_slots:
            self._tenant_slots[key] = [None for _ in range(self._tenant_limit(tenant_id, domain))]
        expected = self._tenant_limit(tenant_id, domain)
        if len(self._tenant_slots[key]) != expected:
            raise AdmissionPartitionIntegrityError(
                "tenant quota changed without an explicit versioned capacity migration"
            )
        return self._tenant_slots[key]

    def submit(
        self,
        *,
        request_id: str,
        tenant_id: str,
        owner_id: str,
        task_id: str,
        domain: str,
        priority: int,
        now: float,
        timeout_at: float,
    ) -> dict[str, Any]:
        request_id = self._required_text(request_id, "request_id")
        tenant_id = self._required_text(tenant_id, "tenant_id")
        owner_id = self._required_text(owner_id, "owner_id")
        task_id = self._required_text(task_id, "task_id")
        domain = self._required_text(domain, "domain")
        if domain not in self.global_limits:
            raise AdmissionPartitionPolicyError("unknown Admission domain")
        if not isinstance(priority, int) or isinstance(priority, bool):
            raise AdmissionPartitionPolicyError("priority must be an integer")
        now = self._finite(now, "now")
        timeout_at = self._finite(timeout_at, "timeout_at")
        if timeout_at <= now:
            raise AdmissionPartitionPolicyError("timeout_at must be after enqueue time")
        partition_id = tenant_partition(tenant_id, self.partition_count)
        identity = {
            "request_id": request_id,
            "tenant_id": tenant_id,
            "owner_id": owner_id,
            "task_id": task_id,
            "domain": domain,
            "partition_id": partition_id,
        }
        with self._lock:
            previous = self._requests.get(request_id)
            if previous is not None:
                if any(previous.get(k) != v for k, v in identity.items()):
                    raise AdmissionPartitionConflictError(
                        "request ID is bound to another tenant/owner/task/domain"
                    )
                if previous["state"] in {"RELEASED", "EXPIRED", "CANCELLED"}:
                    raise AdmissionPartitionRequestFinalizedError(
                        "terminal request ID cannot be reused"
                    )
                return dict(previous)

            key = (tenant_id, domain)
            queue_key = (tenant_id, domain)
            sequence = self._local_waiter_sequence.get(queue_key, 0) + 1
            self._local_waiter_sequence[queue_key] = sequence
            waiter = {
                **identity,
                "priority": priority,
                "enqueue_sequence": sequence,
                "queued_at": now,
                "timeout_at": timeout_at,
                "state": "WAITING",
            }
            self._waiters.setdefault(key, []).append(waiter)
            self._requests[request_id] = dict(waiter)
            return dict(waiter)

    def _select_tenant(self, domain: str, now: float) -> tuple[str, dict[str, Any]] | None:
        tenants = sorted(
            tenant
            for (tenant, queue_domain), queue in self._waiters.items()
            if queue_domain == domain and queue
        )
        if not tenants:
            return None
        cursor = self._tenant_rr_cursor.get(domain)
        start_index = 0
        if cursor in tenants:
            start_index = (tenants.index(cursor) + 1) % len(tenants)
        ordered = tenants[start_index:] + tenants[:start_index]
        global_free = self._first_free(self._global_slots[domain])
        if global_free is None:
            return None

        for tenant in ordered:
            pool = self._tenant_slot_pool(tenant, domain)
            if self._first_free(pool) is None:
                continue
            queue = self._waiters[(tenant, domain)]
            # Priority applies within a tenant queue. Aging increases the
            # effective priority; cross-tenant fairness is round-robin.
            candidate = max(
                queue,
                key=lambda item: (
                    int(item["priority"])
                    + max(0.0, now - float(item["queued_at"])) / self.aging_interval_seconds,
                    -int(item["enqueue_sequence"]),
                ),
            )
            return tenant, candidate
        return None

    def dispatch_one(
        self,
        domain: str,
        *,
        dispatcher_id: str,
        now: float,
        lease_ttl_seconds: float,
    ) -> AdmissionLeaseRecord | None:
        domain = self._required_text(domain, "domain")
        if domain not in self.global_limits:
            raise AdmissionPartitionPolicyError("unknown Admission domain")
        dispatcher = self._required_text(dispatcher_id, "dispatcher_id")
        now = self._finite(now, "now")
        ttl = self._finite(lease_ttl_seconds, "lease_ttl_seconds")
        if ttl < 1:
            raise AdmissionPartitionPolicyError("lease TTL must be at least one second")
        with self._lock:
            selected = self._select_tenant(domain, now)
            if selected is None:
                return None
            tenant_id, waiter = selected
            partition_id = int(waiter["partition_id"])
            # The tenant partition must have an active writer. In production
            # this is guarded by a partition leader lease/epoch in the same Txn.
            leader = self.fencing._leaders.get(partition_id)
            if (
                leader is None
                or leader["owner_id"] != dispatcher
                or float(leader["expires_at"]) <= now
            ):
                raise AdmissionPartitionStaleLeaderError(
                    "dispatcher does not own the selected tenant partition"
                )
            epoch = int(leader["epoch"])
            global_slot = self._first_free(
                self._global_slots[domain], seed=waiter["request_id"]
            )
            tenant_pool = self._tenant_slot_pool(tenant_id, domain)
            tenant_slot = self._first_free(
                tenant_pool, seed=waiter["request_id"]
            )
            if global_slot is None or tenant_slot is None:
                return None

            token = self.fencing.next_token(
                partition_id, dispatcher, epoch, now=now
            )
            lease_id = "admission-" + uuid.uuid4().hex
            record = AdmissionLeaseRecord(
                lease_id=lease_id,
                request_id=waiter["request_id"],
                tenant_id=tenant_id,
                owner_id=waiter["owner_id"],
                task_id=waiter["task_id"],
                domain=domain,
                partition_id=partition_id,
                fencing_token=token,
                expires_at=now + ttl,
                global_slot=global_slot,
                tenant_slot=tenant_slot,
            )
            # One lock models the one etcd Txn that must claim both permit
            # slots, write the active lease and advance the request index.
            if (
                self._global_slots[domain][global_slot] is not None
                or tenant_pool[tenant_slot] is not None
                or waiter["request_id"] not in self._requests
                or self._requests[waiter["request_id"]]["state"] != "WAITING"
            ):
                raise AdmissionPartitionConflictError(
                    "slot or request changed before atomic dispatch"
                )
            self._global_slots[domain][global_slot] = lease_id
            tenant_pool[tenant_slot] = lease_id
            self._active[lease_id] = record
            request = self._requests[waiter["request_id"]]
            request.update(
                {
                    "state": "ACTIVE",
                    "lease_id": lease_id,
                    "fencing_token": token,
                    "expires_at": record.expires_at,
                    "global_slot": global_slot,
                    "tenant_slot": tenant_slot,
                }
            )
            queue = self._waiters[(tenant_id, domain)]
            queue.remove(waiter)
            if not queue:
                del self._waiters[(tenant_id, domain)]
            self._tenant_rr_cursor[domain] = tenant_id
            return record

    def dispatch_batch(
        self,
        domain: str,
        *,
        dispatcher_id: str,
        now: float,
        lease_ttl_seconds: float,
        max_grants: int,
    ) -> list[AdmissionLeaseRecord]:
        if not isinstance(max_grants, int) or isinstance(max_grants, bool) or max_grants < 1:
            raise AdmissionPartitionPolicyError("max_grants must be positive")
        records = []
        for _ in range(max_grants):
            record = self.dispatch_one(
                domain,
                dispatcher_id=dispatcher_id,
                now=now,
                lease_ttl_seconds=lease_ttl_seconds,
            )
            if record is None:
                break
            records.append(record)
        return records

    def acquire_immediate(
        self,
        *,
        request_id: str,
        tenant_id: str,
        owner_id: str,
        task_id: str,
        domain: str,
        now: float,
        lease_ttl_seconds: float,
        dispatcher_id: str,
    ) -> AdmissionLeaseRecord | None:
        with self._lock:
            previous = self.submit(
                request_id=request_id,
                tenant_id=tenant_id,
                owner_id=owner_id,
                task_id=task_id,
                domain=domain,
                priority=0,
                now=now,
                timeout_at=now + lease_ttl_seconds,
            )
            if previous.get("state") == "ACTIVE":
                return self._active.get(previous.get("lease_id"))
            selected = self._select_tenant(domain, now)
            if selected is None or selected[1]["request_id"] != request_id:
                return None
            return self.dispatch_one(
                domain,
                dispatcher_id=dispatcher_id,
                now=now,
                lease_ttl_seconds=lease_ttl_seconds,
            )

    def _free_lease(
        self, lease_id: str, terminal_state: str, *, terminal_at: float | None = None
    ) -> bool:
        record = self._active.pop(lease_id, None)
        if record is None:
            return False
        global_slots = self._global_slots[record.domain]
        tenant_slots = self._tenant_slot_pool(record.tenant_id, record.domain)
        if (
            global_slots[record.global_slot] != lease_id
            or tenant_slots[record.tenant_slot] != lease_id
        ):
            raise AdmissionPartitionIntegrityError(
                "lease index and global/tenant permit slots diverged"
            )
        global_slots[record.global_slot] = None
        tenant_slots[record.tenant_slot] = None
        request = self._requests.get(record.request_id)
        if request is None or request.get("lease_id") != lease_id:
            raise AdmissionPartitionIntegrityError("active lease has no request index")
        request["state"] = terminal_state
        request["terminal_at"] = terminal_at if terminal_state == "EXPIRED" else None
        return True

    def release(self, lease_id: str) -> bool:
        with self._lock:
            return self._free_lease(lease_id, "RELEASED")

    def expire(self, *, now: float) -> list[str]:
        now = self._finite(now, "now")
        with self._lock:
            expired = [
                lease_id for lease_id, record in self._active.items()
                if record.expires_at <= now
            ]
            for lease_id in expired:
                self._free_lease(lease_id, "EXPIRED", terminal_at=now)
            return expired

    def expire_waiters(self, *, now: float) -> list[str]:
        now = self._finite(now, "now")
        with self._lock:
            expired = []
            for key, queue in list(self._waiters.items()):
                keep = []
                for waiter in queue:
                    if float(waiter["timeout_at"]) <= now:
                        request = self._requests[waiter["request_id"]]
                        request["state"] = "EXPIRED"
                        request["terminal_at"] = now
                        expired.append(waiter["request_id"])
                    else:
                        keep.append(waiter)
                if keep:
                    self._waiters[key] = keep
                else:
                    self._waiters.pop(key, None)
            return expired

    def renew(self, lease_id: str, *, now: float, ttl_seconds: float) -> AdmissionLeaseRecord | None:
        now = self._finite(now, "now")
        ttl = self._finite(ttl_seconds, "ttl_seconds")
        if ttl < 1:
            raise AdmissionPartitionPolicyError("lease TTL must be at least one second")
        with self._lock:
            record = self._active.get(lease_id)
            if record is None or record.expires_at <= now:
                return None
            renewed = AdmissionLeaseRecord(
                lease_id=record.lease_id,
                request_id=record.request_id,
                tenant_id=record.tenant_id,
                owner_id=record.owner_id,
                task_id=record.task_id,
                domain=record.domain,
                partition_id=record.partition_id,
                fencing_token=record.fencing_token,
                expires_at=now + ttl,
                global_slot=record.global_slot,
                tenant_slot=record.tenant_slot,
            )
            self._active[lease_id] = renewed
            self._requests[record.request_id]["expires_at"] = renewed.expires_at
            return renewed

    def cancel_waiter(self, request_id: str) -> bool:
        request_id = self._required_text(request_id, "request_id")
        with self._lock:
            request = self._requests.get(request_id)
            if request is None:
                return False
            if request["state"] != "WAITING":
                return False
            key = (request["tenant_id"], request["domain"])
            queue = self._waiters.get(key, [])
            self._waiters[key] = [w for w in queue if w["request_id"] != request_id]
            if not self._waiters[key]:
                self._waiters.pop(key, None)
            request["state"] = "CANCELLED"
            return True

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "partition_count": self.partition_count,
                "active_count": len(self._active),
                "active_by_domain": {
                    domain: sum(1 for r in self._active.values() if r.domain == domain)
                    for domain in self.global_limits
                },
                "active_by_tenant_domain": {
                    f"{tenant}/{domain}": sum(
                        1 for r in self._active.values()
                        if r.tenant_id == tenant and r.domain == domain
                    )
                    for tenant, domain in self._tenant_slots
                },
                "global_slots": {
                    domain: [None if value is None else value for value in slots]
                    for domain, slots in self._global_slots.items()
                },
                "tenant_slots": {
                    f"{tenant}/{domain}": list(slots)
                    for (tenant, domain), slots in self._tenant_slots.items()
                },
                "waiting_count": sum(len(queue) for queue in self._waiters.values()),
                "rr_cursor": dict(self._tenant_rr_cursor),
            }

    def verify_invariants(self) -> dict[str, Any]:
        with self._lock:
            active_ids = set(self._active)
            global_claims: set[str] = set()
            tenant_claims: set[str] = set()
            global_claim_count = 0
            tenant_claim_count = 0
            for domain, slots in self._global_slots.items():
                occupied = [value for value in slots if value is not None]
                if len(occupied) > self.global_limits[domain] or len(occupied) != len(set(occupied)):
                    raise AdmissionPartitionIntegrityError("global domain permit slots exceed quota or duplicate")
                global_claims.update(occupied)
                global_claim_count += len(occupied)
            for (tenant, domain), slots in self._tenant_slots.items():
                occupied = [value for value in slots if value is not None]
                cap = self._tenant_limit(tenant, domain)
                if len(occupied) > cap or len(occupied) != len(set(occupied)):
                    raise AdmissionPartitionIntegrityError("tenant permit slots exceed quota or duplicate")
                tenant_claims.update(occupied)
                tenant_claim_count += len(occupied)
            if (
                active_ids != global_claims
                or active_ids != tenant_claims
                or global_claim_count != len(active_ids)
                or tenant_claim_count != len(active_ids)
            ):
                raise AdmissionPartitionIntegrityError(
                    "every active lease must own exactly one global and one tenant slot"
                )
            for lease_id, record in self._active.items():
                request = self._requests.get(record.request_id)
                if (
                    request is None
                    or request.get("state") != "ACTIVE"
                    or request.get("lease_id") != lease_id
                    or self._global_slots[record.domain][record.global_slot] != lease_id
                    or self._tenant_slot_pool(record.tenant_id, record.domain)[record.tenant_slot] != lease_id
                ):
                    raise AdmissionPartitionIntegrityError(
                        "lease, request and permit slots are inconsistent"
                    )
            return {
                "active_count": len(active_ids),
                "global_domain_count": {
                    domain: sum(1 for r in self._active.values() if r.domain == domain)
                    for domain in self.global_limits
                },
                "tenant_count": {
                    f"{tenant}/{domain}": sum(
                        1 for r in self._active.values()
                        if r.tenant_id == tenant and r.domain == domain
                    )
                    for tenant, domain in self._tenant_slots
                },
                "unique_active_lease_count": len(active_ids),
                "consistent": True,
            }

    @staticmethod
    def _first_free(
        slots: list[str | None], *, seed: str | None = None
    ) -> int | None:
        if not slots:
            return None
        start = 0
        if seed is not None:
            start = int.from_bytes(
                hashlib.sha256(seed.encode("utf-8")).digest()[:4], "big"
            ) % len(slots)
        for offset in range(len(slots)):
            index = (start + offset) % len(slots)
            if slots[index] is None:
                return index
        return None

    @staticmethod
    def _required_text(value: str, label: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise AdmissionPartitionPolicyError(f"{label} is required")
        return value.strip()

    @staticmethod
    def _positive_int(value: int, label: str) -> int:
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise AdmissionPartitionPolicyError(f"{label} must be a positive integer")
        return value

    @staticmethod
    def _finite(value: float, label: str) -> float:
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)):
            raise AdmissionPartitionPolicyError(f"{label} must be finite")
        return float(value)


@dataclass(frozen=True)
class TransactionBudgetReport:
    compare_count: int
    success_operation_count: int
    failure_operation_count: int
    worst_case_operation_count: int
    request_model_bytes: int
    operation_budget: int
    request_byte_budget: int
    within_operation_budget: bool
    within_byte_budget: bool
    utilization_target: float
    model_only: bool


class EtcdTransactionBudget:
    """Conservative transaction request budget calculator.

    The operation count uses compares + the larger mutually-exclusive branch.
    Bytes are canonical JSON model bytes, not protobuf/gRPC wire bytes.
    The configured limits are caller-supplied and MUST be checked against the
    target etcd server. The official v3.7 defaults are references, not policy.
    """

    def __init__(
        self,
        *,
        max_txn_ops: int = 128,
        max_request_bytes: int = 1_572_864,
        utilization_target: float = 0.70,
    ) -> None:
        self.max_txn_ops = self._positive_int(max_txn_ops, "max_txn_ops")
        self.max_request_bytes = self._positive_int(
            max_request_bytes, "max_request_bytes"
        )
        self.utilization_target = self._finite(utilization_target, "utilization_target")
        if not 0 < self.utilization_target <= 1:
            raise AdmissionPartitionPolicyError("utilization_target must be in (0, 1]")

    def estimate(
        self,
        *,
        compares: Iterable[dict[str, Any]],
        success_ops: Iterable[dict[str, Any]],
        failure_ops: Iterable[dict[str, Any]] = (),
    ) -> TransactionBudgetReport:
        compare_rows = list(compares)
        success_rows = list(success_ops)
        failure_rows = list(failure_ops)
        payload = {
            "compare": compare_rows,
            "success": success_rows,
            "failure": failure_rows,
        }
        request_bytes = len(canonical_json_bytes(payload))
        # Both branches are mutually exclusive; budget the larger branch and
        # include every compare for a deliberately conservative estimate.
        worst = len(compare_rows) + max(len(success_rows), len(failure_rows))
        operation_budget = max(1, int(self.max_txn_ops * self.utilization_target))
        byte_budget = max(1, int(self.max_request_bytes * self.utilization_target))
        return TransactionBudgetReport(
            compare_count=len(compare_rows),
            success_operation_count=len(success_rows),
            failure_operation_count=len(failure_rows),
            worst_case_operation_count=worst,
            request_model_bytes=request_bytes,
            operation_budget=operation_budget,
            request_byte_budget=byte_budget,
            within_operation_budget=worst <= operation_budget,
            within_byte_budget=request_bytes <= byte_budget,
            utilization_target=self.utilization_target,
            model_only=True,
        )

    def require_fit(self, report: TransactionBudgetReport) -> None:
        if not report.within_operation_budget:
            raise AdmissionPartitionPolicyError(
                "transaction operation estimate exceeds the configured safety budget"
            )
        if not report.within_byte_budget:
            raise AdmissionPartitionPolicyError(
                "transaction request model bytes exceed the configured safety budget"
            )

    def admission_grant_shape(self, *, key_prefix: str, request_id: str) -> TransactionBudgetReport:
        compares = [
            {"target": "VALUE_OR_REVISION", "key": f"{key_prefix}/control"},
            {"target": "VERSION=0", "key": f"{key_prefix}/global-slots/0"},
            {"target": "VERSION=0", "key": f"{key_prefix}/tenant-slots/t0/0"},
            {"target": "VERSION=0", "key": f"{key_prefix}/requests/{request_id}"},
            {"target": "VALUE_OR_REVISION", "key": f"{key_prefix}/partitions/p0/leader"},
        ]
        success_ops = [
            {"type": "PUT_WITH_TTL", "key": f"{key_prefix}/global-slots/0", "value": "slot"},
            {"type": "PUT_WITH_TTL", "key": f"{key_prefix}/tenant-slots/t0/0", "value": "slot"},
            {"type": "PUT_WITH_TTL", "key": f"{key_prefix}/leases/{request_id}", "value": "lease"},
            {"type": "PUT", "key": f"{key_prefix}/requests/{request_id}", "value": "ACTIVE"},
        ]
        return self.estimate(compares=compares, success_ops=success_ops)

    def coordinator_scope_commit_shape(
        self, *, key_prefix: str, scope_id: str, operation_id: str
    ) -> TransactionBudgetReport:
        compares = [
            {"target": "VALUE_OR_REVISION", "key": f"{key_prefix}/control"},
            {"target": "VALUE_OR_REVISION", "key": f"{key_prefix}/leader"},
            {"target": "VALUE_OR_REVISION", "key": f"{key_prefix}/scope/{scope_id}"},
            {"target": "VALUE_OR_REVISION", "key": f"{key_prefix}/admission/lease/{scope_id}"},
            {"target": "VALUE_OR_REVISION", "key": f"{key_prefix}/admission/global-slot/{scope_id}"},
            {"target": "VALUE_OR_REVISION", "key": f"{key_prefix}/admission/tenant-slot/{scope_id}"},
            {"target": "VERSION=0", "key": f"{key_prefix}/operation/{operation_id}"},
        ]
        success_ops = [
            {"type": "PUT", "key": f"{key_prefix}/scope/{scope_id}", "value": "next-scope"},
            {"type": "PUT", "key": f"{key_prefix}/operation/{operation_id}", "value": "operation"},
        ]
        return self.estimate(compares=compares, success_ops=success_ops)

    def dispatch_batch_shape(
        self,
        *,
        partition_count: int,
        batch_size: int,
        key_prefix: str,
    ) -> TransactionBudgetReport:
        partitions = self._positive_int(partition_count, "partition_count")
        batch = self._positive_int(batch_size, "batch_size")
        prefix = str(key_prefix).rstrip("/")
        if not prefix:
            raise AdmissionPartitionPolicyError("key_prefix is required")
        # Guard every partition summary observed by the dispatcher, then guard
        # each grant's two capacity slots, request tombstone and selected
        # waiter. The success branch writes four permit/request records,
        # deletes each waiter, updates at most one head per touched partition,
        # and advances the domain arbiter.
        compares = [
            {"target": "VALUE_OR_REVISION", "key": f"{prefix}/domain-arbiter"}
        ]
        compares.extend(
            {"target": "VALUE_OR_REVISION_OR_ABSENT", "key": f"{prefix}/partition-head/{p}"}
            for p in range(partitions)
        )
        for index in range(batch):
            compares.extend(
                [
                    {"target": "VERSION=0", "key": f"{prefix}/global-slot/{index}"},
                    {"target": "VERSION=0", "key": f"{prefix}/tenant-slot/{index}"},
                    {"target": "VERSION=0", "key": f"{prefix}/request/{index}"},
                    {"target": "VALUE_OR_REVISION", "key": f"{prefix}/waiter/{index}"},
                ]
            )
        success_ops = []
        for index in range(batch):
            success_ops.extend(
                [
                    {"type": "PUT_WITH_TTL", "key": f"{prefix}/global-slot/{index}", "value": "slot"},
                    {"type": "PUT_WITH_TTL", "key": f"{prefix}/tenant-slot/{index}", "value": "slot"},
                    {"type": "PUT_WITH_TTL", "key": f"{prefix}/lease/{index}", "value": "lease"},
                    {"type": "PUT", "key": f"{prefix}/request/{index}", "value": "ACTIVE"},
                    {"type": "DELETE", "key": f"{prefix}/waiter/{index}"},
                ]
            )
        touched_heads = min(partitions, batch)
        for index in range(touched_heads):
            success_ops.append(
                {"type": "PUT", "key": f"{prefix}/partition-head/{index}", "value": "next-head"}
            )
        success_ops.append(
            {"type": "PUT", "key": f"{prefix}/domain-arbiter", "value": "next-cursor"}
        )
        return self.estimate(compares=compares, success_ops=success_ops)

    @staticmethod
    def _positive_int(value: int, label: str) -> int:
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise AdmissionPartitionPolicyError(f"{label} must be a positive integer")
        return value

    @staticmethod
    def _finite(value: float, label: str) -> float:
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)):
            raise AdmissionPartitionPolicyError(f"{label} must be finite")
        return float(value)
