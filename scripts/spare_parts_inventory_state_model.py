#!/usr/bin/env python3
"""Independent double-entry inventory transition kernel; no enterprise rules are assumed.

The kernel accepts explicit, approved two-leg transfer contracts only. It has no
database/API adapter and does not interpret fixture-declared bucket deltas as postings.
"""
from __future__ import annotations

import argparse
import csv
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

DEFAULT_CONTRACT = Path("resouces/17-operation-maintenance-and-repair/spare-parts-inventory-state-transition-contract-v1.csv")
HEADERS = ["event_type", "source_account", "destination_account", "quantity_field", "unit_field",
           "conservation_scope", "approval_status", "approved_by", "approval_reference", "notes"]


class StateModelError(ValueError):
    """Invalid or unapproved state transition."""


def apply_transfer(
    balances: dict[str, Decimal],
    *,
    source_account: str,
    destination_account: str,
    quantity: Decimal,
    unit: str,
) -> dict[str, Decimal]:
    """Apply one atomic two-leg transfer to a copy; total quantity is conserved."""
    if not source_account or not destination_account:
        raise StateModelError("both source and destination accounts are required")
    if source_account == destination_account:
        raise StateModelError("source and destination accounts must differ")
    if not unit:
        raise StateModelError("unit is required")
    if not quantity.is_finite() or quantity <= 0:
        raise StateModelError("quantity must be finite and greater than zero")
    next_balances = dict(balances)
    source_before = next_balances.get(source_account, Decimal("0"))
    if source_before < quantity:
        raise StateModelError(f"insufficient balance in {source_account}: {source_before} < {quantity}")
    total_before = sum(next_balances.values(), Decimal("0"))
    next_balances[source_account] = source_before - quantity
    next_balances[destination_account] = next_balances.get(destination_account, Decimal("0")) + quantity
    total_after = sum(next_balances.values(), Decimal("0"))
    if total_before != total_after:
        raise StateModelError("two-leg transfer violated quantity conservation")
    if any(value < 0 for value in next_balances.values()):
        raise StateModelError("negative account balance is not allowed")
    return next_balances


def load_contracts(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != HEADERS:
            raise StateModelError(f"contract header mismatch: {reader.fieldnames!r}")
        rows = list(reader)
    if len({row["event_type"] for row in rows}) != len(rows):
        raise StateModelError("duplicate event_type contract")
    for index, row in enumerate(rows, start=2):
        if not row.get("event_type") or row.get("approval_status") not in {"NOT_APPROVED", "APPROVED"}:
            raise StateModelError(f"invalid event contract at row {index}")
        if row["approval_status"] == "APPROVED":
            required = ("source_account", "destination_account", "unit_field", "approved_by", "approval_reference")
            missing = [name for name in required if not row.get(name)]
            if missing:
                raise StateModelError(f"approved contract {row['event_type']} missing {missing}")
    return rows


def assess_contract_readiness(rows: list[dict[str, str]]) -> dict[str, Any]:
    pending = [row["event_type"] for row in rows if row["approval_status"] != "APPROVED"]
    approved = [row["event_type"] for row in rows if row["approval_status"] == "APPROVED"]
    return {
        "contract_count": len(rows),
        "approved_count": len(approved),
        "not_approved_count": len(pending),
        "execution_status": "READY" if not pending else "BLOCKED",
        "business_rule_assertions": "NOT_EVALUATED",
        "pending_event_types": pending,
        "external_connections": False,
        "database_or_api_writes": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--contract-csv", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--report-json", type=Path)
    args = parser.parse_args()
    rows = load_contracts(args.root / args.contract_csv)
    report = assess_contract_readiness(rows)
    report["result"] = "PASS" if rows else "FAIL"
    report["checks"] = [
        {"name": "unique_event_contracts", "status": "PASS", "count": len(rows)},
        {"name": "approval_gate_fail_closed", "status": "PASS", "detail": report["execution_status"]},
        {"name": "no_external_side_effects", "status": "PASS"},
    ]
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.report_json:
        output = args.report_json if args.report_json.is_absolute() else args.root / args.report_json
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
