import copy, unittest
from decimal import Decimal
from scripts.spare_parts_inventory_event_ledger import AppendOnlyEventLedger, LedgerEvent
from scripts.spare_parts_inventory_ledger_integrity import IntegrityError, create_snapshot, restore_snapshot, seal, verify_chain, verify_snapshot, self_check
from scripts.spare_parts_multidimensional_inventory import BalanceKey

def keys():
 return (BalanceKey("HOLD","SYN-P","SYN-L","SYN-B","SYN-O","HOLD","EA"),BalanceKey("AVAILABLE","SYN-P","SYN-L","SYN-B","SYN-O","RELEASED","EA"))
def ev(i,idem,biz,ing,qty="1"):
 a,b=keys(); return LedgerEvent(i,"BIZ-"+i,"SYN-SRC",idem,biz,ing,"TRANSFER",a,b,Decimal(qty))
class Tests(unittest.TestCase):
 def test_decimal_and_timezone_canonicalization(self):
  a=AppendOnlyEventLedger(); b=AppendOnlyEventLedger()
  a.append(ev("E1","I1","2026-01-01T09:00:00+08:00","2026-01-01T09:01:00+08:00","1.00"))
  b.append(ev("E1","I1","2026-01-01T01:00:00Z","2026-01-01T01:01:00Z","1"))
  self.assertEqual(seal(a.records),seal(b.records))
 def test_valid_chain(self):
  l=AppendOnlyEventLedger(); l.append(ev("E1","I1","2026-01-01T09:00:00+08:00","2026-01-01T09:01:00+08:00"))
  self.assertEqual(verify_chain(seal(l.records))["result"],"PASS")
 def test_payload_tampering(self):
  l=AppendOnlyEventLedger(); l.append(ev("E1","I1","2026-01-01T09:00:00+08:00","2026-01-01T09:01:00+08:00"))
  d=seal(l.records); d["records"][0]["event"]["quantity"]="88"
  with self.assertRaises(IntegrityError): verify_chain(d)
 def test_deleted_record_sequence_gap(self):
  l=AppendOnlyEventLedger(); l.append(ev("E1","I1","2026-01-01T09:00:00+08:00","2026-01-01T09:01:00+08:00")); l.append(ev("E2","I2","2026-01-01T10:00:00+08:00","2026-01-01T10:01:00+08:00"))
  d=seal(l.records); d["records"].pop(0)
  with self.assertRaises(IntegrityError): verify_chain(d)
 def test_reordering(self):
  l=AppendOnlyEventLedger(); l.append(ev("E1","I1","2026-01-01T09:00:00+08:00","2026-01-01T09:01:00+08:00")); l.append(ev("E2","I2","2026-01-01T10:00:00+08:00","2026-01-01T10:01:00+08:00"))
  d=seal(l.records); d["records"].reverse()
  with self.assertRaises(IntegrityError): verify_chain(d)
 def test_chain_head_tampering(self):
  l=AppendOnlyEventLedger(); l.append(ev("E1","I1","2026-01-01T09:00:00+08:00","2026-01-01T09:01:00+08:00"))
  d=seal(l.records); d["chain_head"]="f"*64
  with self.assertRaises(IntegrityError): verify_chain(d)
 def test_snapshot_digest_and_balance_tampering(self):
  l=AppendOnlyEventLedger(); a,b=keys(); s=create_snapshot(l,{a:Decimal("5"),b:Decimal("0")},"2026-01-01T10:00:00+08:00")
  self.assertTrue(verify_snapshot(s)); s["balances"][0]["quantity"]="99"
  with self.assertRaises(IntegrityError): verify_snapshot(s)
 def test_unknown_snapshot_version(self):
  l=AppendOnlyEventLedger(); a,b=keys(); s=create_snapshot(l,{a:Decimal("5"),b:Decimal("0")},"2026-01-01T10:00:00+08:00"); s["schema_version"]=8
  with self.assertRaises(IntegrityError): verify_snapshot(s)
 def test_prefix_hash_mismatch(self):
  l=AppendOnlyEventLedger(); a,b=keys(); l.append(ev("E1","I1","2026-01-01T09:00:00+08:00","2026-01-01T09:01:00+08:00"))
  s=create_snapshot(l,{a:Decimal("5"),b:Decimal("0")},"2026-01-01T10:00:00+08:00")
  other=AppendOnlyEventLedger(); other.append(ev("E1","I1","2026-01-01T09:00:00+08:00","2026-01-01T09:01:00+08:00","2"))
  with self.assertRaises(IntegrityError): restore_snapshot(s,other,"2026-01-01T12:00:00+08:00")
 def test_incremental_suffix_matches_full_replay(self):
  l=AppendOnlyEventLedger(); a,b=keys(); opening={a:Decimal("5"),b:Decimal("0")}
  l.append(ev("E1","I1","2026-01-01T09:00:00+08:00","2026-01-01T09:01:00+08:00")); s=create_snapshot(l,opening,"2026-01-01T10:00:00+08:00")
  l.append(ev("E2","I2","2026-01-01T11:00:00+08:00","2026-01-01T11:01:00+08:00"))
  self.assertTrue(restore_snapshot(s,l,"2026-01-01T12:00:00+08:00")["matches_full_replay"])
 def test_backdated_suffix_rejected(self):
  l=AppendOnlyEventLedger(); a,b=keys(); s=create_snapshot(l,{a:Decimal("5"),b:Decimal("0")},"2026-01-01T10:00:00+08:00")
  l.append(ev("LATE","IL","2026-01-01T09:30:00+08:00","2026-01-01T11:00:00+08:00"))
  with self.assertRaises(IntegrityError): restore_snapshot(s,l,"2026-01-01T12:00:00+08:00","2026-01-01T12:00:00+08:00")
 def test_backward_cutoff_rejected(self):
  l=AppendOnlyEventLedger(); a,b=keys(); s=create_snapshot(l,{a:Decimal("5"),b:Decimal("0")},"2026-01-01T10:00:00+08:00")
  with self.assertRaises(IntegrityError): restore_snapshot(s,l,"2026-01-01T09:00:00+08:00")
 def test_gate_remains_blocked(self):
  r=self_check(); self.assertEqual(r["execution_status"],"BLOCKED_PENDING_ENTERPRISE_APPROVAL"); self.assertEqual(r["business_rule_assertions"],"NOT_EVALUATED")
if __name__=="__main__": unittest.main()
