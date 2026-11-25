import json, tempfile, unittest
from decimal import Decimal
from pathlib import Path
from scripts.spare_parts_inventory_event_ledger import AppendOnlyEventLedger, LedgerEvent
from scripts.spare_parts_inventory_ledger_integrity import create_snapshot
from scripts.spare_parts_inventory_ledger_persistence import PersistenceError, PersistenceConflict, publish_generation, recover_current, self_check, _exclusive_store_lock, _gc_coordination_lock, garbage_collect_generations
import multiprocessing, os
from scripts.spare_parts_multidimensional_inventory import BalanceKey

def fixture():
 a=BalanceKey("HOLD","SYN-P","SYN-L","SYN-B","SYN-O","HOLD","EA")
 b=BalanceKey("AVAILABLE","SYN-P","SYN-L","SYN-B","SYN-O","RELEASED","EA")
 opening={a:Decimal("5"),b:Decimal("0")}; l=AppendOnlyEventLedger()
 l.append(LedgerEvent("E1","B1","SRC","I1","2026-01-01T09:00:00+08:00","2026-01-01T09:01:00+08:00","TRANSFER",a,b,Decimal("2")))
 return l,create_snapshot(l,opening,"2026-01-01T10:00:00+08:00")
def _race_writer(root,generation,queue):
 l,s=fixture()
 try: publish_generation(root,l,s,generation,expected_current_generation="g1",lock_timeout_seconds=10); queue.put("COMMITTED")
 except PersistenceConflict: queue.put("CONFLICT")
 except Exception as exc: queue.put("ERROR:"+type(exc).__name__)
def _crash_while_locked(root):
 with _exclusive_store_lock(root): os._exit(23)


def _gc_stress_writer(root,start_event,queue):
 try:
  start_event.wait(5)
  expected="base"
  for i in range(12):
   l,s=fixture(); gid=f"stress-{i:02d}"
   publish_generation(root,l,s,gid,expected_current_generation=expected,lock_timeout_seconds=10)
   expected=gid
   time.sleep(0.002)
  queue.put("writer:PASS")
 except Exception as exc: queue.put("writer:ERROR:"+repr(exc))

def _gc_stress_reader(root,start_event,queue):
 try:
  start_event.wait(5)
  for _ in range(45):
   recovered=recover_current(root)
   if recovered["ledger_record_count"]!=1: raise AssertionError("reader observed incomplete generation")
   time.sleep(0.001)
  queue.put("reader:PASS")
 except Exception as exc: queue.put("reader:ERROR:"+repr(exc))

def _gc_stress_collector(root,start_event,queue):
 try:
  start_event.wait(5)
  for _ in range(16):
   garbage_collect_generations(root,keep_last=2,minimum_age_seconds=0,apply=True,lock_timeout_seconds=10)
   time.sleep(0.002)
  queue.put("collector:PASS")
 except Exception as exc: queue.put("collector:ERROR:"+repr(exc))

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

 def test_concurrent_writers_compare_and_swap_one_wins(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t)/"store"; l,s=fixture(); publish_generation(root,l,s,"g1")
   q=multiprocessing.Queue()
   p1=multiprocessing.Process(target=_race_writer,args=(root,"g2a",q)); p2=multiprocessing.Process(target=_race_writer,args=(root,"g2b",q))
   p1.start(); p2.start(); p1.join(10); p2.join(10)
   self.assertEqual(p1.exitcode,0); self.assertEqual(p2.exitcode,0)
   results=[q.get(timeout=2),q.get(timeout=2)]
   self.assertEqual(results.count("COMMITTED"),1); self.assertEqual(results.count("CONFLICT"),1)
   self.assertIn(recover_current(root)["generation_id"],{"g2a","g2b"})
 def test_kernel_releases_lock_after_process_crash(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t)/"store"; root.mkdir()
   p=multiprocessing.Process(target=_crash_while_locked,args=(root,)); p.start(); p.join(5)
   self.assertEqual(p.exitcode,23)
   l,s=fixture(); self.assertEqual(publish_generation(root,l,s,"after-crash",lock_timeout_seconds=1)["result"],"COMMITTED")
 def test_compare_and_swap_rejects_stale_writer(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t)/"store"; l,s=fixture(); publish_generation(root,l,s,"g1")
   publish_generation(root,l,s,"g2",expected_current_generation="g1")
   with self.assertRaises(PersistenceConflict): publish_generation(root,l,s,"g3",expected_current_generation="g1")
   self.assertEqual(recover_current(root)["generation_id"],"g2")
 def test_writer_lock_timeout(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t)/"store"; root.mkdir()
   with _exclusive_store_lock(root):
    l,s=fixture()
    with self.assertRaises(PersistenceConflict): publish_generation(root,l,s,"g1",lock_timeout_seconds=0.02)
 def test_interrupted_writer_releases_lock(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t)/"store"; l,s=fixture()
   with self.assertRaises(PersistenceError): publish_generation(root,l,s,"g1",failure_stage="after_lock")
   self.assertEqual(publish_generation(root,l,s,"g2",lock_timeout_seconds=1)["result"],"COMMITTED")


 def test_gc_dry_run_and_retention_policy(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t)/"store"; l,s=fixture()
   publish_generation(root,l,s,"g1")
   publish_generation(root,l,s,"g2",expected_current_generation="g1")
   publish_generation(root,l,s,"g3",expected_current_generation="g2")
   os.utime(root/"generation-g1",(1,1))
   plan=garbage_collect_generations(root,keep_last=2,minimum_age_seconds=0)
   self.assertEqual(plan["result"],"DRY_RUN")
   self.assertEqual(plan["eligible_generations"],["g1"])
   self.assertTrue((root/"generation-g1").exists())
   done=garbage_collect_generations(root,keep_last=2,minimum_age_seconds=0,apply=True)
   self.assertEqual(done["deleted_generations"],["g1"])
   self.assertFalse((root/"generation-g1").exists())
   self.assertTrue((root/"generation-g2").exists())
   self.assertEqual(recover_current(root)["generation_id"],"g3")

 def test_gc_respects_minimum_age(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t)/"store"; l,s=fixture()
   publish_generation(root,l,s,"g1")
   publish_generation(root,l,s,"g2",expected_current_generation="g1")
   os.utime(root/"generation-g1",(1,1))
   plan=garbage_collect_generations(root,keep_last=1,minimum_age_seconds=10**12)
   self.assertEqual(plan["eligible_generations"],[])
   self.assertTrue((root/"generation-g1").exists())

 def test_active_reader_excludes_generation_gc(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t)/"store"; l,s=fixture(); publish_generation(root,l,s,"g1")
   os.utime(root/"generation-g1",(1,1))
   with _gc_coordination_lock(root,shared=True):
    with self.assertRaises(PersistenceConflict):
     garbage_collect_generations(root,keep_last=1,minimum_age_seconds=0,
                                 apply=True,lock_timeout_seconds=0.03)
    self.assertTrue((root/"generation-g1").exists())
   self.assertEqual(recover_current(root)["generation_id"],"g1")

 def test_gc_recovers_interrupted_trash_cleanup(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t)/"store"; l,s=fixture(); publish_generation(root,l,s,"current")
   trash=root/".gc-trash-old-123"; trash.mkdir(); (trash/"partial").write_text("synthetic")
   result=garbage_collect_generations(root,apply=True)
   self.assertIn(".gc-trash-old-123",result["reaped_interrupted_cleanup"])
   self.assertFalse(trash.exists())
   self.assertEqual(recover_current(root)["generation_id"],"current")

 def test_unverified_generation_is_never_collected(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t)/"store"; l,s=fixture(); publish_generation(root,l,s,"current")
   bad=root/"generation-unverified"; bad.mkdir(); (bad/"COMMIT.json").write_text("{}")
   result=garbage_collect_generations(root,keep_last=1,minimum_age_seconds=0,apply=True)
   self.assertIn("generation-unverified",result["skipped_unverified_entries"])
   self.assertTrue(bad.exists())

 def test_concurrent_reader_writer_and_gc_stress(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t)/"store"; l,s=fixture(); publish_generation(root,l,s,"base")
   start=multiprocessing.Event(); q=multiprocessing.Queue()
   ps=[
    multiprocessing.Process(target=_gc_stress_writer,args=(root,start,q)),
    multiprocessing.Process(target=_gc_stress_reader,args=(root,start,q)),
    multiprocessing.Process(target=_gc_stress_collector,args=(root,start,q)),
   ]
   [p.start() for p in ps]; start.set(); [p.join(20) for p in ps]
   self.assertTrue(all(p.exitcode==0 for p in ps),[p.exitcode for p in ps])
   results=[q.get(timeout=3) for _ in ps]
   self.assertEqual(sorted(results),["collector:PASS","reader:PASS","writer:PASS"])
   self.assertEqual(recover_current(root)["generation_id"],"stress-11")

 def test_gate_stays_blocked(self):
  r=self_check(); self.assertEqual(r["execution_status"],"BLOCKED_PENDING_ENTERPRISE_APPROVAL")
  self.assertEqual(r["business_rule_assertions"],"NOT_EVALUATED")
if __name__=="__main__": unittest.main()
