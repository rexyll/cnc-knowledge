from __future__ import annotations

import unittest
from decimal import Decimal

from scripts.spare_parts_multidimensional_inventory import BalanceKey
from scripts.spare_parts_inventory_event_ledger import (
    AppendOnlyEventLedger,
    EventLedgerError,
    LedgerEvent,
    synthetic_self_check,
)


def keys():
    hold = BalanceKey("QUALITY_HOLD", "SYN-PART", "SYN-LOT", "SYN-BIN",
                      "SYN-OWNER", "QUARANTINED", "EA")
    available = BalanceKey("AVAILABLE", "SYN-PART", "SYN-LOT", "SYN-BIN",
                           "SYN-OWNER", "RELEASED", "EA")
    return hold, available


def event(event_id, idem, *, business="2026-01-01T09:00:00+08:00",
          ingested="2026-01-01T09:01:00+08:00", qty="2", source=None,
          destination=None, event_type="TRANSFER", reference=""):
    hold, available = keys()
    return LedgerEvent(
        event_id, "BIZ-" + event_id, "SYN-SOURCE", idem, business, ingested,
        event_type, source or hold, destination or available, Decimal(qty), reference,
    )


class InventoryEventLedgerTests(unittest.TestCase):
    def test_append_assigns_monotonic_ledger_sequence(self):
        ledger = AppendOnlyEventLedger()
        ledger.append(event("E1", "I1"))
        ledger.append(event("E2", "I2", business="2026-01-01T10:00:00+08:00"))
        self.assertEqual([r.ledger_sequence for r in ledger.records], [1, 2])

    def test_records_are_exposed_as_immutable_tuple(self):
        ledger = AppendOnlyEventLedger()
        ledger.append(event("E1", "I1"))
        self.assertIsInstance(ledger.records, tuple)
        with self.assertRaises(AttributeError):
            ledger.records.append(event("E2", "I2"))

    def test_duplicate_delivery_same_idempotency_payload_is_noop(self):
        ledger = AppendOnlyEventLedger()
        original = event("E1", "I1")
        self.assertTrue(ledger.append(original)["accepted"])
        duplicate = ledger.append(original)
        self.assertTrue(duplicate["duplicate_delivery"])
        self.assertEqual(len(ledger.records), 1)

    def test_idempotency_key_reuse_with_changed_payload_is_rejected(self):
        ledger = AppendOnlyEventLedger()
        ledger.append(event("E1", "I1"))
        with self.assertRaises(EventLedgerError):
            ledger.append(event("E2", "I1", qty="3"))

    def test_event_id_reuse_with_new_idempotency_key_is_rejected(self):
        ledger = AppendOnlyEventLedger()
        ledger.append(event("E1", "I1"))
        with self.assertRaises(EventLedgerError):
            ledger.append(event("E1", "I2"))

    def test_missing_identity_fields_rejected(self):
        e = event("E1", "I1")
        with self.assertRaises(EventLedgerError):
            ledger_event = LedgerEvent("", e.business_event_id, e.source_system_id,
                e.idempotency_key, e.business_time, e.ingestion_time, e.event_type,
                e.source, e.destination, e.quantity)
            AppendOnlyEventLedger().append(ledger_event)

    def test_timestamps_must_have_explicit_timezone(self):
        with self.assertRaises(EventLedgerError):
            AppendOnlyEventLedger().append(event("E1", "I1", business="2026-01-01T09:00:00"))

    def test_late_arrival_is_preserved_and_knowledge_cutoff_controls_visibility(self):
        ledger = AppendOnlyEventLedger()
        late = event("LATE", "I-LATE", business="2026-01-01T09:00:00+08:00",
                     ingested="2026-01-03T10:00:00+08:00")
        ledger.append(late)
        before_known = ledger.rebuild({keys()[0]: Decimal("5")}, "2026-01-02T00:00:00+08:00",
                                      "2026-01-02T00:00:00+08:00")
        after_known = ledger.rebuild({keys()[0]: Decimal("5")}, "2026-01-02T00:00:00+08:00",
                                     "2026-01-04T00:00:00+08:00")
        self.assertEqual(before_known["applied_event_count"], 0)
        self.assertEqual(after_known["applied_event_count"], 1)
        self.assertEqual(len(ledger.records), 1)

    def test_out_of_order_arrival_rebuilds_by_business_time_not_ingestion_order(self):
        ledger = AppendOnlyEventLedger()
        hold, available = keys()
        later = event("E-LATER", "I-LATER", business="2026-01-01T10:00:00+08:00",
                      ingested="2026-01-01T10:01:00+08:00", source=available,
                      destination=hold, qty="1")
        earlier = event("E-EARLIER", "I-EARLIER", business="2026-01-01T09:00:00+08:00",
                        ingested="2026-01-01T10:02:00+08:00", qty="2")
        ledger.append(later)
        ledger.append(earlier)
        rebuilt = ledger.rebuild({hold: Decimal("5"), available: Decimal("0")},
                                 "2026-01-01T23:00:00+08:00")
        self.assertEqual(rebuilt["applied_event_ids"], ["E-EARLIER", "E-LATER"])
        self.assertEqual(rebuilt["balances"][hold], Decimal("4"))

    def test_business_cutoff_excludes_later_events(self):
        ledger = AppendOnlyEventLedger()
        ledger.append(event("E1", "I1", business="2026-01-02T09:00:00+08:00"))
        rebuilt = ledger.rebuild({keys()[0]: Decimal("5")}, "2026-01-01T23:59:59+08:00")
        self.assertEqual(rebuilt["applied_event_count"], 0)

    def test_reversal_is_a_new_immutable_opposite_event(self):
        ledger = AppendOnlyEventLedger()
        hold, available = keys()
        original = event("E1", "I1")
        ledger.append(original)
        reversal = event("R1", "IR1", business="2026-01-01T10:00:00+08:00",
                         ingested="2026-01-01T10:01:00+08:00", source=available,
                         destination=hold, event_type="REVERSAL", reference="E1")
        ledger.append(reversal)
        rebuilt = ledger.rebuild({hold: Decimal("5"), available: Decimal("0")},
                                 "2026-01-01T23:00:00+08:00")
        self.assertEqual(rebuilt["balances"][hold], Decimal("5"))
        self.assertEqual(rebuilt["balances"][available], Decimal("0"))
        self.assertEqual(len(ledger.records), 2)

    def test_reversal_requires_existing_target_and_exact_opposite(self):
        ledger = AppendOnlyEventLedger()
        hold, available = keys()
        reversal = event("R1", "IR1", event_type="REVERSAL", reference="MISSING",
                         source=available, destination=hold)
        with self.assertRaises(EventLedgerError):
            ledger.append(reversal)
        ledger.append(event("E1", "I1"))
        wrong = event("R2", "IR2", event_type="REVERSAL", reference="E1")
        with self.assertRaises(EventLedgerError):
            ledger.append(wrong)

    def test_duplicate_reversal_is_rejected(self):
        ledger = AppendOnlyEventLedger()
        hold, available = keys()
        ledger.append(event("E1", "I1"))
        ledger.append(event("R1", "IR1", business="2026-01-01T10:00:00+08:00",
                            source=available, destination=hold,
                            event_type="REVERSAL", reference="E1"))
        with self.assertRaises(EventLedgerError):
            ledger.append(event("R2", "IR2", business="2026-01-01T11:00:00+08:00",
                                source=available, destination=hold,
                                event_type="REVERSAL", reference="E1"))

    def test_rebuild_detects_reversal_without_visible_target(self):
        ledger = AppendOnlyEventLedger()
        hold, available = keys()
        ledger.append(event("E1", "I1", business="2026-01-01T10:00:00+08:00"))
        ledger.append(event("R1", "IR1", business="2026-01-01T11:00:00+08:00",
                            source=available, destination=hold,
                            event_type="REVERSAL", reference="E1"))
        with self.assertRaises(EventLedgerError):
            ledger.rebuild({hold: Decimal("5"), available: Decimal("0")},
                           "2026-01-01T12:00:00+08:00",
                           "2026-01-01T10:30:00+08:00")

    def test_rebuild_failure_does_not_mutate_event_ledger(self):
        ledger = AppendOnlyEventLedger()
        ledger.append(event("E1", "I1", qty="6"))
        before = ledger.records
        with self.assertRaises(Exception):
            ledger.rebuild({keys()[0]: Decimal("5")}, "2026-01-02T00:00:00+08:00")
        self.assertEqual(ledger.records, before)

    def test_reconcile_report_never_emits_global_total(self):
        ledger = AppendOnlyEventLedger()
        ledger.append(event("E1", "I1"))
        result = ledger.reconcile({keys()[0]: Decimal("5")}, "2026-01-02T00:00:00+08:00")
        self.assertEqual(result["rebuild_result"], "PASS")
        self.assertIsNone(result["global_inventory_total"])
        self.assertEqual(result["business_rule_assertions"], "NOT_EVALUATED")

    def test_self_check_fails_closed(self):
        report = synthetic_self_check()
        self.assertEqual(report["result"], "PASS")
        self.assertEqual(report["execution_status"], "BLOCKED_PENDING_ENTERPRISE_APPROVAL")
        self.assertFalse(report["external_connections"])


if __name__ == "__main__":
    unittest.main()
