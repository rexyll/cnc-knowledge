from __future__ import annotations

import csv
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from scripts import spare_parts_multidimensional_inventory as model


def key(account="AVAILABLE", *, item="PART-1", lot="LOT-1", location="BIN-1",
        owner="OWNER-1", condition="RELEASED", uom="EA"):
    return model.BalanceKey(account, item, lot, location, owner, condition, uom)


class MultidimensionalInventoryTests(unittest.TestCase):
    def test_balance_key_contains_all_dimensions(self):
        a = key()
        b = key(location="BIN-2")
        self.assertNotEqual(a, b)
        self.assertEqual(len(a.__dataclass_fields__), 7)

    def test_transfer_conserves_same_uom_across_account_state(self):
        src, dst = key("QUALITY_HOLD", condition="QUARANTINED"), key("AVAILABLE")
        ledger = model.InventoryLedger({src: Decimal("4"), dst: Decimal("0")})
        ledger.transfer(model.InventoryEvent("E1", 1, src, dst, Decimal("3"), "RELEASE"))
        self.assertEqual(ledger.balances[src], Decimal("1"))
        self.assertEqual(ledger.balances[dst], Decimal("3"))
        self.assertEqual(sum(ledger.balances.values()), Decimal("4"))

    def test_location_change_requires_separate_movement(self):
        src, dst = key(), key(location="BIN-2")
        ledger = model.InventoryLedger({src: Decimal("2")})
        with self.assertRaises(model.InventoryModelError):
            ledger.transfer(model.InventoryEvent("E1", 1, src, dst, Decimal("1"), "MOVE"))

    def test_item_lot_and_owner_identity_cannot_change(self):
        variants = [key(item="PART-2"), key(lot="LOT-2"), key(owner="OWNER-2")]
        src = key()
        for dst in variants:
            with self.subTest(dst=dst), self.assertRaises(model.InventoryModelError):
                model.InventoryLedger({src: Decimal("2")}).transfer(
                    model.InventoryEvent("E1", 1, src, dst, Decimal("1"), "TRANSFER"))

    def test_cross_unit_transfer_is_rejected_without_conversion(self):
        src, dst = key(uom="BOX"), key(uom="EA")
        with self.assertRaises(model.InventoryModelError):
            model.InventoryLedger({src: Decimal("2")}).transfer(
                model.InventoryEvent("E1", 1, src, dst, Decimal("1"), "TRANSFER"))

    def test_conversion_requires_approval_and_evidence(self):
        pending = model.UnitConversion("C1", "BOX", "EA", Decimal("10"), "PROPOSED_NOT_APPROVED")
        with self.assertRaises(model.InventoryModelError):
            model.convert_quantity(Decimal("1"), pending)
        approved = model.UnitConversion("C1", "BOX", "EA", Decimal("10"), "APPROVED", "synthetic-approver", "SYN-APPROVAL")
        self.assertEqual(model.convert_quantity(Decimal("2"), approved), Decimal("20"))

    def test_conversion_factor_must_be_positive_and_finite(self):
        for factor in (Decimal("0"), Decimal("-1"), Decimal("NaN"), Decimal("Infinity")):
            conversion = model.UnitConversion("C1", "A", "B", factor, "APPROVED", "x", "y")
            with self.subTest(factor=factor), self.assertRaises(model.InventoryModelError):
                model.convert_quantity(Decimal("1"), conversion)

    def test_negative_or_non_decimal_opening_balance_rejected(self):
        with self.assertRaises(model.InventoryModelError):
            model.InventoryLedger({key(): Decimal("-1")})

    def test_replay_requires_strict_sequence_and_unique_event_ids(self):
        src, dst = key("HOLD"), key()
        ledger = model.InventoryLedger({src: Decimal("3")})
        events = [model.InventoryEvent("E1", 1, src, dst, Decimal("1"), "X"),
                  model.InventoryEvent("E2", 2, src, dst, Decimal("1"), "X")]
        self.assertEqual(ledger.replay(events), {"applied_events": 2, "unique_event_ids": 2})
        with self.assertRaises(model.InventoryModelError):
            model.InventoryLedger({src: Decimal("3")}).replay([events[0], events[0]])
        with self.assertRaises(model.InventoryModelError):
            model.InventoryLedger({src: Decimal("3")}).replay([events[1], events[0]])

    def test_replay_failure_does_not_apply_partial_event(self):
        src, dst = key("HOLD"), key()
        ledger = model.InventoryLedger({src: Decimal("1")})
        before = ledger.balances
        with self.assertRaises(model.InventoryModelError):
            ledger.replay([model.InventoryEvent("E1", 1, src, dst, Decimal("2"), "X")])
        self.assertEqual(ledger.balances, before)

    def test_synthetic_opening_snapshot_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "opening.csv"
            fields = ["snapshot_status", "account_code", "item_id", "lot_id", "location_id",
                      "owner_id", "condition_code", "quantity", "uom", "synthetic_only", "reset_group"]
            with path.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=fields)
                writer.writeheader()
                writer.writerow(dict(snapshot_status="SYNTHETIC_TEST_ONLY", account_code="AVAILABLE",
                    item_id="SYN-PART", lot_id="SYN-LOT", location_id="SYN-BIN", owner_id="SYN-OWNER",
                    condition_code="RELEASED", quantity="12", uom="EA", synthetic_only="TRUE",
                    reset_group="SYN-RESET-1"))
            ledger = model.load_synthetic_opening_snapshot(path)
            self.assertEqual(next(iter(ledger.balances.values())), Decimal("12"))
            text = path.read_text(encoding="utf-8").replace("SYNTHETIC_TEST_ONLY", "APPROVED")
            path.write_text(text, encoding="utf-8")
            with self.assertRaises(model.InventoryModelError):
                model.load_synthetic_opening_snapshot(path)

    def test_duplicate_opening_balance_key_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "opening.csv"
            fields = ["snapshot_status", "account_code", "item_id", "lot_id", "location_id",
                      "owner_id", "condition_code", "quantity", "uom", "synthetic_only", "reset_group"]
            row = dict(snapshot_status="SYNTHETIC_TEST_ONLY", account_code="AVAILABLE",
                item_id="SYN-PART", lot_id="SYN-LOT", location_id="SYN-BIN", owner_id="SYN-OWNER",
                condition_code="RELEASED", quantity="1", uom="EA", synthetic_only="TRUE",
                reset_group="SYN-RESET-1")
            with path.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=fields)
                writer.writeheader()
                writer.writerow(row)
                writer.writerow(row)
            with self.assertRaises(model.InventoryModelError):
                model.load_synthetic_opening_snapshot(path)

    def test_self_check_fails_closed(self):
        report = model.self_check()
        self.assertEqual(report["result"], "PASS")
        self.assertEqual(report["execution_status"], "BLOCKED_PENDING_ENTERPRISE_APPROVAL")
        self.assertFalse(report["enterprise_connections"])


if __name__ == "__main__":
    unittest.main()
