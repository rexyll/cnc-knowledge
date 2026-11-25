"""Local synthetic-only generation-based persistence for ledger and snapshots."""
from __future__ import annotations
import argparse, hashlib, json, os, re, shutil, tempfile, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from decimal import Decimal
from scripts.spare_parts_inventory_event_ledger import AppendOnlyEventLedger, LedgerEvent
from scripts.spare_parts_inventory_ledger_integrity import seal, verify_chain, verify_snapshot, IntegrityError
from scripts.spare_parts_multidimensional_inventory import BalanceKey

FORMAT_VERSION=1
GENERATION_RE=re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
class PersistenceError(ValueError): pass

def _json_bytes(value):
    return (json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(",",":"),allow_nan=False)+"\n").encode("utf-8")
def _sha(data): return hashlib.sha256(data).hexdigest()
def _fsync_dir(path):
    if not hasattr(os,"O_DIRECTORY"): return
    fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY)
    try: os.fsync(fd)
    finally: os.close(fd)
def _write_sync(path,data):
    with path.open("xb") as stream:
        stream.write(data); stream.flush(); os.fsync(stream.fileno())
def _safe_generation(value):
    if not isinstance(value,str) or not GENERATION_RE.fullmatch(value) or value in {".",".."}:
        raise PersistenceError("invalid generation identifier")
    return value

def publish_generation(root,ledger,snapshot,generation_id,*,failure_stage=None):
    """Publish immutable generation; CURRENT is the sole atomic commit pointer."""
    root=Path(root)
    if failure_stage not in {None,"after_ledger","after_snapshot","after_generation_rename","before_pointer_replace"}:
        raise PersistenceError("unsupported synthetic fault stage")
    gid=_safe_generation(generation_id)
    root.mkdir(parents=True,exist_ok=True)
    if root.is_symlink(): raise PersistenceError("storage root cannot be a symlink")
    final=root/("generation-"+gid)
    stage=root/(".staging-"+gid)
    if final.exists() or stage.exists(): raise PersistenceError("generation already exists or staging residue requires inspection")
    chain=seal(ledger.records); verify_chain(chain); verify_snapshot(snapshot)
    ledger_bytes=_json_bytes(chain); snapshot_bytes=_json_bytes(snapshot)
    stage.mkdir()
    try:
        _write_sync(stage/"ledger.json",ledger_bytes)
        if failure_stage=="after_ledger": raise PersistenceError("injected interruption after ledger write")
        _write_sync(stage/"snapshot.json",snapshot_bytes)
        if failure_stage=="after_snapshot": raise PersistenceError("injected interruption after snapshot write")
        commit={"format_version":FORMAT_VERSION,"generation_id":gid,"commit_state":"COMMITTED",
          "ledger_sha256":_sha(ledger_bytes),"snapshot_sha256":_sha(snapshot_bytes),
          "ledger_record_count":chain["record_count"],"snapshot_ledger_sequence":snapshot["ledger_sequence"]}
        _write_sync(stage/"COMMIT.json",_json_bytes(commit))
        _fsync_dir(stage)
        os.replace(stage,final)
        _fsync_dir(root)
        if failure_stage=="after_generation_rename": raise PersistenceError("injected interruption after generation publish, before CURRENT")
        pointer_tmp=root/(".CURRENT-"+gid+".tmp")
        _write_sync(pointer_tmp,_json_bytes({"format_version":FORMAT_VERSION,"generation_id":gid}))
        if failure_stage=="before_pointer_replace": raise PersistenceError("injected interruption before CURRENT atomic replace")
        os.replace(pointer_tmp,root/"CURRENT")
        _fsync_dir(root)
        return {"result":"COMMITTED","generation_id":gid,"ledger_record_count":chain["record_count"],
          "ledger_sha256":_sha(ledger_bytes),"snapshot_sha256":_sha(snapshot_bytes)}
    except Exception:
        # Staging remnants are intentionally retained for diagnosis; recovery ignores them.
        raise

def _read_json(path):
    try: return json.loads(path.read_text(encoding="utf-8"))
    except (OSError,UnicodeError,json.JSONDecodeError) as exc:
        raise PersistenceError("missing, unreadable, or malformed persistence file: "+path.name) from exc

def _restore_ledger(chain):
    verify_chain(chain)
    ledger=AppendOnlyEventLedger()
    for row in chain["records"]:
        e=row["event"]
        try:
            source=BalanceKey(**e["source"]); destination=BalanceKey(**e["destination"])
            event=LedgerEvent(e["event_id"],e["business_event_id"],e["source_system_id"],e["idempotency_key"],
              e["business_time"],e["ingestion_time"],e["event_type"],source,destination,Decimal(e["quantity"]),
              e.get("reference_event_id",""))
            result=ledger.append(event)
        except Exception as exc:
            raise PersistenceError("event reconstruction failed") from exc
        if not result["accepted"] or result["ledger_sequence"]!=row["ledger_sequence"]:
            raise PersistenceError("event sequence reconstruction mismatch")
    return ledger

def recover_current(root):
    root=Path(root)
    if root.is_symlink(): raise PersistenceError("storage root cannot be a symlink")
    pointer=_read_json(root/"CURRENT")
    if pointer.get("format_version")!=FORMAT_VERSION: raise PersistenceError("unsupported CURRENT pointer version")
    gid=_safe_generation(pointer.get("generation_id"))
    generation=root/("generation-"+gid)
    if generation.is_symlink() or not generation.is_dir(): raise PersistenceError("committed generation is missing or unsafe")
    commit=_read_json(generation/"COMMIT.json")
    if commit.get("format_version")!=FORMAT_VERSION or commit.get("generation_id")!=gid or commit.get("commit_state")!="COMMITTED":
        raise PersistenceError("commit marker invalid")
    ledger_bytes=(generation/"ledger.json").read_bytes()
    snapshot_bytes=(generation/"snapshot.json").read_bytes()
    if _sha(ledger_bytes)!=commit.get("ledger_sha256") or _sha(snapshot_bytes)!=commit.get("snapshot_sha256"):
        raise PersistenceError("persisted file digest mismatch")
    try: chain=json.loads(ledger_bytes); snapshot=json.loads(snapshot_bytes)
    except (UnicodeError,json.JSONDecodeError) as exc: raise PersistenceError("persisted payload malformed") from exc
    try:
        result=verify_chain(chain); verify_snapshot(snapshot)
    except IntegrityError as exc: raise PersistenceError("ledger or snapshot integrity verification failed") from exc
    if result["record_count"]!=commit.get("ledger_record_count") or snapshot.get("ledger_sequence")!=commit.get("snapshot_ledger_sequence"):
        raise PersistenceError("commit marker metadata mismatch")
    ledger=_restore_ledger(chain)
    return {"result":"RECOVERED","generation_id":gid,"ledger":ledger,"snapshot":snapshot,
      "ledger_record_count":len(ledger.records),"chain_head":result["chain_head"],
      "business_rule_assertions":"NOT_EVALUATED","execution_status":"BLOCKED_PENDING_ENTERPRISE_APPROVAL"}

def self_check():
    from scripts.spare_parts_inventory_ledger_integrity import create_snapshot
    a=BalanceKey("HOLD","SYN-P","SYN-L","SYN-B","SYN-O","HOLD","EA")
    b=BalanceKey("AVAILABLE","SYN-P","SYN-L","SYN-B","SYN-O","RELEASED","EA")
    opening={a:Decimal("5"),b:Decimal("0")}; ledger=AppendOnlyEventLedger()
    ledger.append(LedgerEvent("SYN-P1","SYN-PB1","SYN-SRC","SYN-PI1","2026-01-01T09:00:00+08:00","2026-01-01T09:01:00+08:00","TRANSFER",a,b,Decimal("2")))
    snapshot=create_snapshot(ledger,opening,"2026-01-01T10:00:00+08:00")
    with tempfile.TemporaryDirectory(prefix="ch17-ledger-persist-") as tmp:
        published=publish_generation(Path(tmp)/"store",ledger,snapshot,"self-check-001")
        recovered=recover_current(Path(tmp)/"store")
        assert recovered["ledger_record_count"]==1 and published["result"]=="COMMITTED"
    return {"result":"PASS","generation_publish":"PASS","committed_recovery":"PASS",
      "restored_event_count":1,"temporary_directory_only":True,"external_connections":False,
      "database_or_api_writes":False,"business_rule_assertions":"NOT_EVALUATED",
      "execution_status":"BLOCKED_PENDING_ENTERPRISE_APPROVAL"}
def main():
    p=argparse.ArgumentParser(); p.add_argument("--self-check",action="store_true"); p.add_argument("--report-json",type=Path); a=p.parse_args()
    if not a.self_check: p.error("--self-check required; production persistence is unsupported")
    out=json.dumps(self_check(),ensure_ascii=False,indent=2)+"\n"
    if a.report_json: a.report_json.parent.mkdir(parents=True,exist_ok=True); a.report_json.write_text(out,encoding="utf-8")
    print(out,end="")
if __name__=="__main__": main()
