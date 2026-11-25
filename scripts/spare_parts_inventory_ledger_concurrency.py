"""Synthetic multiprocess writer race and recovery self-check."""
import argparse,json,tempfile,multiprocessing
from pathlib import Path
from decimal import Decimal
from scripts.spare_parts_inventory_ledger_persistence import publish_generation,recover_current,PersistenceConflict
from scripts.spare_parts_inventory_event_ledger import AppendOnlyEventLedger,LedgerEvent
from scripts.spare_parts_inventory_ledger_integrity import create_snapshot
from scripts.spare_parts_multidimensional_inventory import BalanceKey
def fixture():
 a=BalanceKey("HOLD","SYN-P","SYN-L","SYN-B","SYN-O","HOLD","EA"); b=BalanceKey("AVAILABLE","SYN-P","SYN-L","SYN-B","SYN-O","RELEASED","EA")
 l=AppendOnlyEventLedger(); l.append(LedgerEvent("SYN-C1","SYN-CB1","SYN-SRC","SYN-CI1","2026-01-01T09:00:00+08:00","2026-01-01T09:01:00+08:00","TRANSFER",a,b,Decimal("2")))
 return l,create_snapshot(l,{a:Decimal("5"),b:Decimal("0")},"2026-01-01T10:00:00+08:00")
def writer(root,gid,q):
 l,s=fixture()
 try: publish_generation(root,l,s,gid,expected_current_generation="base",lock_timeout_seconds=10); q.put("COMMITTED")
 except PersistenceConflict: q.put("CONFLICT")
def self_check():
 with tempfile.TemporaryDirectory(prefix="ch17-ledger-concurrency-") as tmp:
  root=Path(tmp)/"store"; l,s=fixture(); publish_generation(root,l,s,"base")
  q=multiprocessing.Queue(); ps=[multiprocessing.Process(target=writer,args=(root,g,q)) for g in ("writer-a","writer-b")]
  [p.start() for p in ps]; [p.join(10) for p in ps]
  if any(p.exitcode!=0 for p in ps): raise RuntimeError("writer process failed or timed out")
  results=[q.get(timeout=2),q.get(timeout=2)]
  if sorted(results)!=["COMMITTED","CONFLICT"]: raise RuntimeError("CAS race did not produce exactly one winner")
  current=recover_current(root)["generation_id"]
  if current not in {"writer-a","writer-b"}: raise RuntimeError("unexpected current generation")
 return {"result":"PASS","multiprocess_writers":2,"commit_winners":1,"stale_writer_conflicts":1,"current_generation_recovered":"PASS","temporary_directory_only":True,"external_connections":False,"database_or_api_writes":False,"business_rule_assertions":"NOT_EVALUATED","execution_status":"BLOCKED_PENDING_ENTERPRISE_APPROVAL"}
def main():
 p=argparse.ArgumentParser(); p.add_argument("--self-check",action="store_true"); p.add_argument("--report-json",type=Path); a=p.parse_args()
 if not a.self_check: p.error("--self-check required")
 out=json.dumps(self_check(),ensure_ascii=False,indent=2)+"\n"
 if a.report_json: a.report_json.parent.mkdir(parents=True,exist_ok=True); a.report_json.write_text(out,encoding="utf-8")
 print(out,end="")
if __name__=="__main__": main()
