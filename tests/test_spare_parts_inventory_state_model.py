from __future__ import annotations

import csv
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from scripts import spare_parts_inventory_state_model as model


class InventoryStateModelTests(unittest.TestCase):
    def test_internal_transfer_conserves_quantity(self) -> None:
        before = {"QUARANTINE": Decimal("4"), "AVAILABLE": Decimal("0")}
        after = model.apply_transfer(before, source_account="QUARANTINE",
            destination_account="AVAILABLE", quantity=Decimal("3"), unit="EA")
        self.assertEqual(after["QUARANTINE"], Decimal("1"))
        self.assertEqual(after["AVAILABLE"], Decimal("3"))
        self.assertEqual(sum(before.values()), sum(after.values()))

    def test_transfer_does_not_mutate_input(self) -> None:
        before = {"A": Decimal("5")}
        model.apply_transfer(before, source_account="A", destination_account="B",
            quantity=Decimal("2"), unit="EA")
        self.assertEqual(before, {"A": Decimal("5")})

    def test_insufficient_source_balance_is_rejected(self) -> None:
        with self.assertRaises(model.StateModelError):
            model.apply_transfer({"A": Decimal("1")}, source_account="A",
                destination_account="B", quantity=Decimal("2"), unit="EA")

    def test_negative_zero_or_non_finite_quantity_is_rejected(self) -> None:
        for value in (Decimal("-1"), Decimal("0"), Decimal("NaN"), Decimal("Infinity")):
            with self.subTest(value=value), self.assertRaises(model.StateModelError):
                model.apply_transfer({"A": Decimal("5")}, source_account="A",
                    destination_account="B", quantity=value, unit="EA")

    def test_missing_or_same_account_is_rejected(self) -> None:
        for source, destination in (("", "B"), ("A", ""), ("A", "A")):
            with self.subTest(source=source, destination=destination), self.assertRaises(model.StateModelError):
                model.apply_transfer({"A": Decimal("5")}, source_account=source,
                    destination_account=destination, quantity=Decimal("1"), unit="EA")

    def test_unit_is_required(self) -> None:
        with self.assertRaises(model.StateModelError):
            model.apply_transfer({"A": Decimal("5")}, source_account="A",
                destination_account="B", quantity=Decimal("1"), unit="")

    def test_failed_transfer_is_atomic(self) -> None:
        before = {"A": Decimal("1"), "B": Decimal("9")}
        with self.assertRaises(model.StateModelError):
            model.apply_transfer(before, source_account="A", destination_account="B",
                quantity=Decimal("2"), unit="EA")
        self.assertEqual(before, {"A": Decimal("1"), "B": Decimal("9")})

    def test_current_22_event_contracts_remain_blocked_pending_approval(self) -> None:
        path = Path(__file__).resolve().parents[1] / model.DEFAULT_CONTRACT
        rows = model.load_contracts(path)
        status = model.assess_contract_readiness(rows)
        self.assertEqual(status["contract_count"], 22)
        self.assertEqual(status["approved_count"], 0)
        self.assertEqual(status["execution_status"], "BLOCKED")
        self.assertEqual(status["business_rule_assertions"], "NOT_EVALUATED")

    def test_approved_contract_requires_two_accounts_and_approval_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "contracts.csv"
            with path.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=model.HEADERS)
                writer.writeheader()
                writer.writerow({
                    "event_type": "TEST", "source_account": "A", "destination_account": "",
                    "quantity_field": "qty", "unit_field": "unit", "conservation_scope": "ITEM",
                    "approval_status": "APPROVED", "approved_by": "", "approval_reference": "", "notes": "",
                })
            with self.assertRaises(model.StateModelError):
                model.load_contracts(path)


if __name__ == "__main__":
    unittest.main()
