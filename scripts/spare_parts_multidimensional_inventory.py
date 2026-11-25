#!/usr/bin/env python3
"""Multidimensional, in-memory inventory balance kernel.

This module is a mathematical test utility only. It has no enterprise adapters,
database/API writes, implicit unit conversions, or inferred business policies.
"""
from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable


class InventoryModelError(ValueError):
    """Invalid inventory key, quantity, conversion, snapshot, or event."""


@dataclass(frozen=True, order=True)
class BalanceKey:
    account: str
    item: str
    lot: str
    location: str
    owner: str
    condition: str
    uom: str

    def validate(self) -> None:
        for name, value in self.__dict__.items():
            if not isinstance(value, str) or not value.strip():
                raise InventoryModelError(f"{name} dimension is required; use an explicit N/A token when applicable")


@dataclass(frozen=True)
class UnitConversion:
    conversion_id: str
    source_uom: str
    target_uom: str
    factor: Decimal
    approval_status: str
    approved_by: str = ""
    approval_reference: str = ""

    def validate(self) -> None:
        if not self.conversion_id or not self.source_uom or not self.target_uom:
            raise InventoryModelError("conversion identity and both units are required")
        if not self.factor.is_finite() or self.factor <= 0:
            raise InventoryModelError("conversion factor must be finite and positive")
        if self.approval_status != "APPROVED":
            raise InventoryModelError("unit conversion is not approved")
        if not self.approved_by or not self.approval_reference:
            raise InventoryModelError("approved conversion requires approver and approval reference")


@dataclass(frozen=True)
class InventoryEvent:
    event_id: str
    sequence: int
    source: BalanceKey
    destination: BalanceKey
    quantity: Decimal
    event_type: str


def convert_quantity(quantity: Decimal, conversion: UnitConversion) -> Decimal:
    """Convert only with an explicit, fully approved conversion record."""
    conversion.validate()
    if not quantity.is_finite() or quantity <= 0:
        raise InventoryModelError("quantity must be finite and positive")
    return quantity * conversion.factor


class InventoryLedger:
    """Balances keyed by account + item + lot + location + owner + condition + UOM."""

    def __init__(self, opening_balances: dict[BalanceKey, Decimal] | None = None):
        self._balances: dict[BalanceKey, Decimal] = {}
        for key, quantity in (opening_balances or {}).items():
            key.validate()
            self._validate_quantity(quantity, allow_zero=True)
            if quantity < 0:
                raise InventoryModelError("opening balance cannot be negative")
            self._balances[key] = quantity

    @staticmethod
    def _validate_quantity(quantity: Decimal, *, allow_zero: bool = False) -> None:
        if not isinstance(quantity, Decimal) or not quantity.is_finite():
            raise InventoryModelError("quantity must be a finite Decimal")
        if quantity < 0 or (not allow_zero and quantity == 0):
            raise InventoryModelError("quantity must be positive" if not allow_zero else "quantity cannot be negative")

    @property
    def balances(self) -> dict[BalanceKey, Decimal]:
        return dict(self._balances)

    def total_by_uom(self) -> dict[str, Decimal]:
        totals: dict[str, Decimal] = {}
        for key, quantity in self._balances.items():
            totals[key.uom] = totals.get(key.uom, Decimal("0")) + quantity
        return totals

    def transfer(self, event: InventoryEvent) -> None:
        """Apply a same-dimension, same-unit two-leg transfer atomically."""
        if not event.event_id or not event.event_type:
            raise InventoryModelError("event identity and type are required")
        if event.sequence < 1:
            raise InventoryModelError("event sequence must be a positive integer")
        event.source.validate()
        event.destination.validate()
        if event.source == event.destination:
            raise InventoryModelError("source and destination balance keys must differ")
        if event.source.item != event.destination.item or event.source.lot != event.destination.lot:
            raise InventoryModelError("transfer cannot silently change item or lot identity")
        if event.source.location != event.destination.location:
            raise InventoryModelError("cross-location transfer requires a separately modeled movement")
        if event.source.owner != event.destination.owner:
            raise InventoryModelError("ownership change requires an explicitly modeled event")
        if event.source.uom != event.destination.uom:
            raise InventoryModelError("cross-unit transfer is forbidden; use an approved conversion explicitly")
        self._validate_quantity(event.quantity)
        before = dict(self._balances)
        source_qty = before.get(event.source, Decimal("0"))
        if source_qty < event.quantity:
            raise InventoryModelError("insufficient source balance")
        after = dict(before)
        after[event.source] = source_qty - event.quantity
        after[event.destination] = after.get(event.destination, Decimal("0")) + event.quantity
        if after[event.source] < 0 or sum(after.values(), Decimal("0")) != sum(before.values(), Decimal("0")):
            raise InventoryModelError("transfer violates non-negative balance or same-unit conservation")
        self._balances = after

    def replay(self, events: Iterable[InventoryEvent]) -> dict[str, int]:
        """Replay ordered events; exact duplicate event IDs are rejected, not re-posted."""
        seen: set[str] = set()
        count = 0
        previous_sequence = 0
        for event in events:
            if event.event_id in seen:
                raise InventoryModelError(f"duplicate event_id: {event.event_id}")
            if event.sequence <= previous_sequence:
                raise InventoryModelError("event sequence must be strictly increasing")
            self.transfer(event)
            seen.add(event.event_id)
            previous_sequence = event.sequence
            count += 1
        return {"applied_events": count, "unique_event_ids": len(seen)}


def load_synthetic_opening_snapshot(path: Path) -> InventoryLedger:
    """Load only explicitly synthetic, test-only rows; production data is rejected."""
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        required = {"snapshot_status", "account_code", "item_id", "lot_id", "location_id",
                    "owner_id", "condition_code", "quantity", "uom", "synthetic_only", "reset_group"}
        if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
            raise InventoryModelError("opening snapshot is missing required columns")
        rows = list(reader)
    balances: dict[BalanceKey, Decimal] = {}
    for row_number, row in enumerate(rows, start=2):
        if row.get("synthetic_only") != "TRUE" or row.get("snapshot_status") != "SYNTHETIC_TEST_ONLY":
            raise InventoryModelError(f"row {row_number}: only SYNTHETIC_TEST_ONLY snapshots are loadable")
        if not row.get("reset_group"):
            raise InventoryModelError(f"row {row_number}: reset_group is required")
        key = BalanceKey(row["account_code"], row["item_id"], row["lot_id"] or "N/A",
                         row["location_id"], row["owner_id"] or "N/A",
                         row["condition_code"], row["uom"])
        key.validate()
        try:
            quantity = Decimal(row["quantity"])
        except (InvalidOperation, TypeError):
            raise InventoryModelError(f"row {row_number}: invalid quantity") from None
        InventoryLedger._validate_quantity(quantity, allow_zero=True)
        if key in balances:
            raise InventoryModelError(f"row {row_number}: duplicate balance key; aggregate explicitly first")
        balances[key] = quantity
    return InventoryLedger(balances)


def self_check() -> dict:
    available = BalanceKey("AVAILABLE", "SYN-PART-001", "SYN-LOT-01", "SYN-BIN-01",
                           "SYN-OWNER", "RELEASED", "EA")
    hold = BalanceKey("QUALITY_HOLD", "SYN-PART-001", "SYN-LOT-01", "SYN-BIN-01",
                      "SYN-OWNER", "QUARANTINED", "EA")
    ledger = InventoryLedger({hold: Decimal("4"), available: Decimal("0")})
    ledger.transfer(InventoryEvent("SYN-EVT-001", 1, hold, available, Decimal("3"), "SYNTHETIC_TRANSFER"))
    assert ledger.balances[hold] == Decimal("1")
    assert ledger.balances[available] == Decimal("3")
    return {
        "result": "PASS",
        "model_scope": "synthetic mathematical self-check only",
        "multidimensional_key_fields": ["account", "item", "lot", "location", "owner", "condition", "uom"],
        "self_check_events": 1,
        "same_uom_conservation": "PASS",
        "implicit_unit_conversion": False,
        "enterprise_connections": False,
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
        parser.error("--self-check is required; this utility does not load enterprise data")
    report = self_check()
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.report_json:
        args.report_json.parent.mkdir(parents=True, exist_ok=True)
        args.report_json.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
