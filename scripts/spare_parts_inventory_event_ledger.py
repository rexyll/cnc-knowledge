#!/usr/bin/env python3
"""Append-only synthetic inventory event ledger and as-of balance reconstruction.

This is an offline mathematical test utility. It has no enterprise adapters,
database/API writes, inferred account policies, or production data access.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Iterable
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.spare_parts_multidimensional_inventory import (
    BalanceKey,
    InventoryEvent,
    InventoryLedger,
    InventoryModelError,
)


class EventLedgerError(ValueError):
    """Invalid ledger identity, idempotency, timestamp, or reversal."""


def _aware_datetime(value: str, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise EventLedgerError(f"{field} is required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise EventLedgerError(f"{field} must be an ISO-8601 timestamp") from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise EventLedgerError(f"{field} must include an explicit UTC offset")
    return parsed


@dataclass(frozen=True)
class LedgerEvent:
    event_id: str
    business_event_id: str
    source_system_id: str
    idempotency_key: str
    business_time: str
    ingestion_time: str
    event_type: str
    source: BalanceKey
    destination: BalanceKey
    quantity: Decimal
    reference_event_id: str = ""

    def validate(self) -> None:
        for field in ("event_id", "business_event_id", "source_system_id",
                      "idempotency_key", "event_type"):
            value = getattr(self, field)
            if not isinstance(value, str) or not value.strip():
                raise EventLedgerError(f"{field} is required")
        _aware_datetime(self.business_time, "business_time")
        _aware_datetime(self.ingestion_time, "ingestion_time")
        if self.event_type not in {"TRANSFER", "REVERSAL"}:
            raise EventLedgerError("only generic TRANSFER and REVERSAL records are supported")
        self.source.validate()
        self.destination.validate()
        if self.source == self.destination:
            raise EventLedgerError("source and destination keys must differ")
        if self.source.item != self.destination.item or self.source.lot != self.destination.lot:
            raise EventLedgerError("ordinary ledger events cannot change item or lot identity")
        if self.source.location != self.destination.location or self.source.owner != self.destination.owner:
            raise EventLedgerError("location and ownership changes require separately approved event semantics")
        if self.source.uom != self.destination.uom:
            raise EventLedgerError("cross-unit ledger events are forbidden")
        if not isinstance(self.quantity, Decimal) or not self.quantity.is_finite() or self.quantity <= 0:
            raise EventLedgerError("quantity must be a finite positive Decimal")
        if self.event_type == "REVERSAL" and not self.reference_event_id:
            raise EventLedgerError("REVERSAL requires reference_event_id")
        if self.event_type == "TRANSFER" and self.reference_event_id:
            raise EventLedgerError("TRANSFER cannot carry reference_event_id")

    def fingerprint(self) -> tuple:
        return (
            self.business_event_id, self.source_system_id, self.business_time,
            self.event_type, self.source, self.destination, str(self.quantity),
            self.reference_event_id,
        )


@dataclass(frozen=True)
class StoredEvent:
    ledger_sequence: int
    event: LedgerEvent


class AppendOnlyEventLedger:
    """In-memory append-only ledger with idempotent delivery and explicit reversals."""

    def __init__(self) -> None:
        self._records: list[StoredEvent] = []
        self._by_event_id: dict[str, StoredEvent] = {}
        self._by_idempotency: dict[str, StoredEvent] = {}
        self._reversed_event_ids: set[str] = set()

    @property
    def records(self) -> tuple[StoredEvent, ...]:
        return tuple(self._records)

    def append(self, event: LedgerEvent) -> dict[str, object]:
        event.validate()
        prior_key = self._by_idempotency.get(event.idempotency_key)
        if prior_key is not None:
            if prior_key.event.fingerprint() != event.fingerprint():
                raise EventLedgerError("idempotency key was reused with a different payload")
            return {
                "accepted": False,
                "duplicate_delivery": True,
                "original_event_id": prior_key.event.event_id,
                "ledger_sequence": prior_key.ledger_sequence,
            }
        if event.event_id in self._by_event_id:
            raise EventLedgerError("event_id already exists under a different idempotency key")
        if event.event_type == "REVERSAL":
            target = self._by_event_id.get(event.reference_event_id)
            if target is None:
                raise EventLedgerError("reversal target must already exist in the append-only ledger")
            original = target.event
            if original.event_type != "TRANSFER":
                raise EventLedgerError("only a TRANSFER can be reversed")
            if event.source != original.destination or event.destination != original.source:
                raise EventLedgerError("reversal must use the exact opposite balance keys")
            if event.quantity != original.quantity:
                raise EventLedgerError("reversal quantity must equal the original event quantity")
            if event.reference_event_id in self._reversed_event_ids:
                raise EventLedgerError("an original transfer can be reversed only once in this model")
            if _aware_datetime(event.business_time, "business_time") < _aware_datetime(original.business_time, "original business_time"):
                raise EventLedgerError("reversal business_time cannot precede the original event")
        sequence = len(self._records) + 1
        stored = StoredEvent(sequence, event)
        self._records.append(stored)
        self._by_event_id[event.event_id] = stored
        self._by_idempotency[event.idempotency_key] = stored
        if event.event_type == "REVERSAL":
            self._reversed_event_ids.add(event.reference_event_id)
        return {
            "accepted": True,
            "duplicate_delivery": False,
            "original_event_id": event.event_id,
            "ledger_sequence": sequence,
        }

    def rebuild(
        self,
        opening_balances: dict[BalanceKey, Decimal],
        business_cutoff: str,
        known_at_cutoff: str | None = None,
    ) -> dict[str, object]:
        """Rebuild balances at business time, optionally bounded by ingestion time.

        Event ordering is business_time then immutable ledger_sequence. Late arrivals
        remain visible in the ledger but only affect a rebuild whose knowledge cutoff
        includes their ingestion_time.
        """
        business_end = _aware_datetime(business_cutoff, "business_cutoff")
        known_end = _aware_datetime(known_at_cutoff, "known_at_cutoff") if known_at_cutoff else None
        selected = []
        for record in self._records:
            event = record.event
            business_time = _aware_datetime(event.business_time, "business_time")
            ingestion_time = _aware_datetime(event.ingestion_time, "ingestion_time")
            if business_time <= business_end and (known_end is None or ingestion_time <= known_end):
                selected.append(record)
        selected.sort(key=lambda item: (
            _aware_datetime(item.event.business_time, "business_time"),
            item.ledger_sequence,
        ))
        by_id = {record.event.event_id: record.event for record in selected}
        ledger = InventoryLedger(opening_balances)
        applied = []
        for record in selected:
            event = record.event
            if event.event_type == "TRANSFER":
                effective = InventoryEvent(
                    event.event_id, record.ledger_sequence, event.source,
                    event.destination, event.quantity, "SYNTHETIC_LEDGER_TRANSFER",
                )
            else:
                target = by_id.get(event.reference_event_id)
                if target is None:
                    raise EventLedgerError(
                        "as-of rebuild includes a reversal but not its referenced transfer; "
                        "check business_time and known_at_cutoff"
                    )
                effective = InventoryEvent(
                    event.event_id, record.ledger_sequence, event.source,
                    event.destination, event.quantity, "SYNTHETIC_LEDGER_REVERSAL",
                )
            ledger.transfer(effective)
            applied.append(event.event_id)
        return {
            "balances": ledger.balances,
            "applied_event_ids": applied,
            "applied_event_count": len(applied),
            "ignored_later_business_events": len(self._records) - len(selected),
            "business_cutoff": business_cutoff,
            "known_at_cutoff": known_at_cutoff,
            "ledger_record_count": len(self._records),
            "global_inventory_total": None,
            "business_rule_assertions": "NOT_EVALUATED",
            "execution_status": "BLOCKED_PENDING_ENTERPRISE_APPROVAL",
        }

    def reconcile(
        self,
        opening_balances: dict[BalanceKey, Decimal],
        business_cutoff: str,
    ) -> dict[str, object]:
        """Compare a replayed projection to a separately supplied synthetic projection."""
        rebuilt = self.rebuild(opening_balances, business_cutoff)
        return {
            "rebuild_result": "PASS",
            "balance_projection": {
                "|".join(key.__dict__.values()): str(value)
                for key, value in sorted(rebuilt["balances"].items())
            },
            "reconciled_event_count": rebuilt["applied_event_count"],
            "global_inventory_total": None,
            "business_rule_assertions": "NOT_EVALUATED",
            "execution_status": "BLOCKED_PENDING_ENTERPRISE_APPROVAL",
        }


def synthetic_self_check() -> dict[str, object]:
    hold = BalanceKey("QUALITY_HOLD", "SYN-PART", "SYN-LOT", "SYN-BIN",
                      "SYN-OWNER", "QUARANTINED", "EA")
    available = BalanceKey("AVAILABLE", "SYN-PART", "SYN-LOT", "SYN-BIN",
                           "SYN-OWNER", "RELEASED", "EA")
    opening = {hold: Decimal("5"), available: Decimal("0")}
    ledger = AppendOnlyEventLedger()
    first = LedgerEvent(
        "SYN-EVT-001", "SYN-BIZ-001", "SYN-SOURCE-A", "SYN-IDEM-001",
        "2026-01-01T09:00:00+08:00", "2026-01-01T09:01:00+08:00",
        "TRANSFER", hold, available, Decimal("2"),
    )
    ledger.append(first)
    duplicate = ledger.append(first)
    rebuilt = ledger.rebuild(opening, "2026-01-01T23:59:59+08:00")
    assert duplicate["duplicate_delivery"] is True
    assert rebuilt["applied_event_count"] == 1
    assert rebuilt["balances"][hold] == Decimal("3")
    return {
        "result": "PASS",
        "model_scope": "synthetic event-ledger mathematical self-check only",
        "stored_records": len(ledger.records),
        "duplicate_delivery": "NO_OP",
        "reconstructed_event_count": rebuilt["applied_event_count"],
        "global_inventory_total": None,
        "external_connections": False,
        "database_or_api_writes": False,
        "business_rule_assertions": "NOT_EVALUATED",
        "execution_status": "BLOCKED_PENDING_ENTERPRISE_APPROVAL",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--report-json", type=Path)
    args = parser.parse_args()
    if not args.self_check:
        parser.error("--self-check is required; enterprise data loading is unsupported")
    report = synthetic_self_check()
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.report_json:
        args.report_json.parent.mkdir(parents=True, exist_ok=True)
        args.report_json.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
