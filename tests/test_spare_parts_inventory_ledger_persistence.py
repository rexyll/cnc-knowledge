import json, tempfile, unittest
from decimal import Decimal
from pathlib import Path
from scripts.spare_parts_inventory_event_ledger import AppendOnlyEventLedger, LedgerEvent
from scripts.spare_parts_inventory_ledger_integrity import create_snapshot
from scripts.spare_parts_inventory_ledger_persistence import PersistenceError, publish_generation, recover_current, self_check
from scripts.spare_parts_multidimensional_inventory import BalanceKey

def fixture():
 a=BalanceKey("HOLD","SYN-P","SYN-L","SYN-B","SYN-O","HOLD","EA")
 b=BalanceKey("AVAILABLE","SYN-P","SYN-L","SYN-B","SYN-O","RELEASED","EA")
 opening={a:Decimal("5"),b:Decimal("0")}; l=AppendOnlyEventLedger()
 l.append(LedgerEvent("E1","B1","SRC","I1","2026-01-01T09:00:00+08:00","2026-01-01T09:01:00+08:00","TRANSFER",a,b,Decimal("2")))
 return l,create_snapshot(l,opening,"2026-01-01T10:00:00+08:00")
class PersistenceTests(unittest.TestCase):
 def test_publish_and_recover_round_trip(self):
  with tempfile.TemporaryDirectory() as t:
   l,s=fixture(); out=publish_generation(Path(t)/"store",l,s,"g1"); got=recover_current(Path(t)/"store")
   self.assertEqual(out["result"],"COMMITTED"); self.assertEqual(got["ledger_record_count"],1)
   self.assertEqual(got["ledger"].records[0].event.event_id,"E1")
 def test_interruption_after_ledger_does_not_publish(self):
  with tempfile.TemporaryDirectory() as t:
   l,s=fixture(); root=Path(t)/"store"
   with self.assertRaises(PersistenceError): publish_generation(root,l,s,"g1",failure_stage="after_ledger")
   self.assertFalse((root/"CURRENT").exists())
   with self.assertRaises(PersistenceError): recover_current(root)
 def test_interruption_after_snapshot_does_not_publish(self):
  with tempfile.TemporaryDirectory() as t:
   l,s=fixture(); root=Path(t)/"store"
   with self.assertRaises(PersistenceError): publish_generation(root,l,s,"g1",failure_stage="after_snapshot")
   self.assertFalse((root/"CURRENT").exists())
 def test_orphan_generation_after_rename_is_not_current(self):
  with tempfile.TemporaryDirectory() as t:
   l,s=fixture(); root=Path(t)/"store"
   with self.assertRaises(PersistenceError): publish_generation(root,l,s,"g1",failure_stage="after_generation_rename")
   self.assertTrue((root/"generation-g1"/"COMMIT.json").exists())
   with self.assertRaises(PersistenceError): recover_current(root)
 def test_existing_current_survives_failed_next_publish(self):
  with tempfile.TemporaryDirectory() as t:
   l,s=fixture(); root=Path(t)/"store"; publish_generation(root,l,s,"g1")
   with self.assertRaises(PersistenceError): publish_generation(root,l,s,"g2",failure_stage="before_pointer_replace")
   self.assertEqual(recover_current(root)["generation_id"],"g1")
 def test_payload_corruption_rejected(self):
  with tempfile.TemporaryDirectory() as t:
   l,s=fixture(); root=Path(t)/"store"; publish_generation(root,l,s,"g1")
   p=root/"generation-g1"/"ledger.json"; p.write_text(p.read_text().replace('"quantity":"2"','"quantity":"9"'))
   with self.assertRaises(PersistenceError): recover_current(root)
 def test_missing_commit_marker_rejected(self):
  with tempfile.TemporaryDirectory() as t:
   l,s=fixture(); root=Path(t)/"store"; publish_generation(root,l,s,"g1")
   (root/"generation-g1"/"COMMIT.json").unlink()
   with self.assertRaises(PersistenceError): recover_current(root)
 def test_path_traversal_generation_rejected(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t)/"store"; root.mkdir(); (root/"CURRENT").write_text(json.dumps({"format_version":1,"generation_id":"../escape"}))
   with self.assertRaises(PersistenceError): recover_current(root)
 def test_unknown_pointer_version_rejected(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t)/"store"; root.mkdir(); (root/"CURRENT").write_text(json.dumps({"format_version":99,"generation_id":"g1"}))
   with self.assertRaises(PersistenceError): recover_current(root)
 def test_duplicate_generation_rejected(self):
  with tempfile.TemporaryDirectory() as t:
   l,s=fixture(); root=Path(t)/"store"; publish_generation(root,l,s,"g1")
   with self.assertRaises(PersistenceError): publish_generation(root,l,s,"g1")
 def test_gate_stays_blocked(self):
  r=self_check(); self.assertEqual(r["execution_status"],"BLOCKED_PENDING_ENTERPRISE_APPROVAL")
  self.assertEqual(r["business_rule_assertions"],"NOT_EVALUATED")
if __name__=="__main__": unittest.main()
