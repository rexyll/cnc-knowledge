"""Local synthetic-only generation-based persistence for ledger and snapshots."""
from __future__ import annotations
import argparse, hashlib, json, os, re, tempfile, sys, time, fcntl, shutil, stat
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
class PersistenceConflict(PersistenceError): pass
from contextlib import contextmanager
@contextmanager
def _exclusive_store_lock(root, timeout_seconds=5.0):
    fd=os.open(Path(root)/".writer.lock",os.O_CREAT|os.O_RDWR,0o600)
    acquired=False
    deadline=time.monotonic()+timeout_seconds
    try:
        while True:
            try:
                fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB); acquired=True; break
            except BlockingIOError:
                if time.monotonic()>=deadline: raise PersistenceConflict("writer lock timeout")
                time.sleep(0.02)
        yield
    finally:
        if acquired: fcntl.flock(fd,fcntl.LOCK_UN)
        os.close(fd)

@contextmanager
def _gc_coordination_lock(root, *, shared=False, timeout_seconds=5.0):
    """Coordinate readers and generation GC; writers do not need this lock."""
    root=Path(root)
    if root.is_symlink() or not root.is_dir():
        raise PersistenceError("storage root is missing, unsafe, or not a directory")
    flags=os.O_CREAT|os.O_RDWR
    if hasattr(os,"O_NOFOLLOW"): flags|=os.O_NOFOLLOW
    try:
        fd=os.open(root/".gc.lock",flags,0o600)
    except OSError as exc:
        raise PersistenceError("cannot safely open reader/GC coordination lock") from exc
    acquired=False
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise PersistenceError("reader/GC lock is not a regular file")
        operation=fcntl.LOCK_SH if shared else fcntl.LOCK_EX
        deadline=time.monotonic()+timeout_seconds
        while True:
            try:
                fcntl.flock(fd,operation|fcntl.LOCK_NB); acquired=True; break
            except BlockingIOError:
                if time.monotonic()>=deadline:
                    raise PersistenceConflict("reader/GC coordination lock timeout")
                time.sleep(0.02)
        yield
    finally:
        if acquired: fcntl.flock(fd,fcntl.LOCK_UN)
        os.close(fd)

def _read_current_generation(root):
    current=Path(root)/"CURRENT"
    if not current.exists(): return None
    if current.is_symlink() or not current.is_file(): raise PersistenceError("CURRENT pointer is unsafe")
    pointer=_read_json(current)
    if pointer.get("format_version")!=FORMAT_VERSION: raise PersistenceError("unsupported CURRENT pointer version")
    return _safe_generation(pointer.get("generation_id"))

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

def publish_generation(root,ledger,snapshot,generation_id,*,failure_stage=None,
                       expected_current_generation="*",lock_timeout_seconds=5.0):
    """Serialize writers with a kernel lock; CURRENT remains the atomic commit pointer."""
    root=Path(root)
    if failure_stage not in {None,"after_lock","after_ledger","after_snapshot","after_generation_rename","before_pointer_replace"}:
        raise PersistenceError("unsupported synthetic fault stage")
    gid=_safe_generation(generation_id)
    root.mkdir(parents=True,exist_ok=True)
    if root.is_symlink(): raise PersistenceError("storage root cannot be a symlink")
    with _exclusive_store_lock(root,lock_timeout_seconds):
        actual=_read_current_generation(root)
        if expected_current_generation!="*" and actual!=expected_current_generation:
            raise PersistenceConflict("CURRENT generation changed; compare-and-swap rejected")
        final=root/("generation-"+gid); stage=root/(".staging-"+gid)
        if final.exists() or stage.exists(): raise PersistenceError("generation already exists or staging residue requires inspection")
        chain=seal(ledger.records); verify_chain(chain); verify_snapshot(snapshot)
        ledger_bytes=_json_bytes(chain); snapshot_bytes=_json_bytes(snapshot)
        stage.mkdir()
        try:
            if failure_stage=="after_lock": raise PersistenceError("injected interruption while holding writer lock")
            _write_sync(stage/"ledger.json",ledger_bytes)
            if failure_stage=="after_ledger": raise PersistenceError("injected interruption after ledger write")
            _write_sync(stage/"snapshot.json",snapshot_bytes)
            if failure_stage=="after_snapshot": raise PersistenceError("injected interruption after snapshot write")
            commit={"format_version":FORMAT_VERSION,"generation_id":gid,"commit_state":"COMMITTED",
              "ledger_sha256":_sha(ledger_bytes),"snapshot_sha256":_sha(snapshot_bytes),
              "ledger_record_count":chain["record_count"],"snapshot_ledger_sequence":snapshot["ledger_sequence"]}
            _write_sync(stage/"COMMIT.json",_json_bytes(commit)); _fsync_dir(stage)
            os.replace(stage,final); _fsync_dir(root)
            if failure_stage=="after_generation_rename": raise PersistenceError("injected interruption after generation publish, before CURRENT")
            pointer_tmp=root/(".CURRENT-"+gid+".tmp")
            _write_sync(pointer_tmp,_json_bytes({"format_version":FORMAT_VERSION,"generation_id":gid}))
            if failure_stage=="before_pointer_replace": raise PersistenceError("injected interruption before CURRENT atomic replace")
            os.replace(pointer_tmp,root/"CURRENT"); _fsync_dir(root)
            return {"result":"COMMITTED","generation_id":gid,"ledger_record_count":chain["record_count"],
              "ledger_sha256":_sha(ledger_bytes),"snapshot_sha256":_sha(snapshot_bytes),"previous_generation":actual}
        except Exception: raise

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

def _recover_current_unlocked(root):
    if (root/"CURRENT").is_symlink(): raise PersistenceError("CURRENT pointer cannot be a symlink")
    pointer=_read_json(root/"CURRENT")
    if pointer.get("format_version")!=FORMAT_VERSION: raise PersistenceError("unsupported CURRENT pointer version")
    gid=_safe_generation(pointer.get("generation_id"))
    generation=root/("generation-"+gid)
    if generation.is_symlink() or not generation.is_dir(): raise PersistenceError("committed generation is missing or unsafe")
    commit=_read_json(generation/"COMMIT.json")
    if commit.get("format_version")!=FORMAT_VERSION or commit.get("generation_id")!=gid or commit.get("commit_state")!="COMMITTED":
        raise PersistenceError("commit marker invalid")
    ledger_path=generation/"ledger.json"; snapshot_path=generation/"snapshot.json"
    if ledger_path.is_symlink() or snapshot_path.is_symlink():
        raise PersistenceError("persisted payload cannot be a symlink")
    ledger_bytes=ledger_path.read_bytes()
    snapshot_bytes=snapshot_path.read_bytes()
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

def recover_current(root):
    """Read one complete CURRENT generation while excluding concurrent GC."""
    root=Path(root)
    if root.is_symlink() or not root.is_dir():
        raise PersistenceError("storage root is missing, unsafe, or not a directory")
    with _gc_coordination_lock(root,shared=True):
        return _recover_current_unlocked(root)


def _generation_is_verified_for_gc(root,gid):
    """Only collect complete, digest-consistent committed generations."""
    generation=Path(root)/("generation-"+gid)
    if generation.is_symlink() or not generation.is_dir(): return False
    commit_path=generation/"COMMIT.json"
    ledger_path=generation/"ledger.json"
    snapshot_path=generation/"snapshot.json"
    if any(x.is_symlink() or not x.is_file() for x in (commit_path,ledger_path,snapshot_path)):
        return False
    try:
        commit=_read_json(commit_path)
        ledger_bytes=ledger_path.read_bytes()
        snapshot_bytes=snapshot_path.read_bytes()
    except (OSError,PersistenceError):
        return False
    return (commit.get("format_version")==FORMAT_VERSION
        and commit.get("generation_id")==gid
        and commit.get("commit_state")=="COMMITTED"
        and _sha(ledger_bytes)==commit.get("ledger_sha256")
        and _sha(snapshot_bytes)==commit.get("snapshot_sha256"))

def garbage_collect_generations(root, *, keep_last=3, minimum_age_seconds=604800,
                                apply=False, lock_timeout_seconds=5.0):
    """Plan or explicitly apply safe local generation retention.

    The collector serializes against writers, then excludes active readers.
    It keeps CURRENT, the newest keep_last verified generations, and any
    generation younger than minimum_age_seconds. Dry-run is the default.
    """
    root=Path(root)
    if root.is_symlink() or not root.is_dir():
        raise PersistenceError("storage root is missing, unsafe, or not a directory")
    if isinstance(keep_last,bool) or not isinstance(keep_last,int) or keep_last<1:
        raise PersistenceError("keep_last must be an integer greater than or equal to 1")
    if isinstance(minimum_age_seconds,bool) or not isinstance(minimum_age_seconds,(int,float)) or minimum_age_seconds<0:
        raise PersistenceError("minimum_age_seconds must be a non-negative number")
    if not isinstance(apply,bool): raise PersistenceError("apply must be boolean")
    deleted=[]; reaped_trash=[]
    # Lock order is writer first, GC second. Readers only acquire the GC lock.
    with _exclusive_store_lock(root,lock_timeout_seconds):
      with _gc_coordination_lock(root,shared=False,timeout_seconds=lock_timeout_seconds):
        current=_read_current_generation(root)
        now=time.time()
        if apply:
            # A previous process may have crashed after atomically moving a
            # generation into trash but before recursively removing it.
            for item in root.iterdir():
                if item.name.startswith(".gc-trash-") and not item.is_symlink() and item.is_dir():
                    shutil.rmtree(item)
                    reaped_trash.append(item.name)
            if reaped_trash: _fsync_dir(root)
        verified=[]
        skipped=[]
        for item in root.iterdir():
            if not item.name.startswith("generation-"): continue
            gid=item.name[len("generation-"):]
            try: _safe_generation(gid)
            except PersistenceError:
                skipped.append(item.name); continue
            if not _generation_is_verified_for_gc(root,gid):
                skipped.append(item.name); continue
            try: mtime_ns=item.stat(follow_symlinks=False).st_mtime_ns
            except OSError:
                skipped.append(item.name); continue
            verified.append((mtime_ns,gid,item))
        verified.sort(key=lambda row:(row[0],row[1]),reverse=True)
        by_id={gid:(mtime_ns,path) for mtime_ns,gid,path in verified}
        if current is not None and current not in by_id:
            raise PersistenceError("CURRENT does not reference a verified committed generation")
        keep={gid for _,gid,_ in verified[:keep_last]}
        if current is not None: keep.add(current)
        cutoff_ns=int((now-float(minimum_age_seconds))*1_000_000_000)
        candidates=[gid for mtime_ns,gid,_ in verified if gid not in keep and mtime_ns<=cutoff_ns]
        if apply:
            for gid in candidates:
                # Re-read CURRENT immediately before every retirement. The
                # writer lock prevents a concurrent supported writer publish.
                if _read_current_generation(root)==gid: continue
                source=root/("generation-"+gid)
                if not _generation_is_verified_for_gc(root,gid): continue
                trash=root/(f".gc-trash-{gid}-{os.getpid()}-{time.time_ns()}")
                os.replace(source,trash)
                _fsync_dir(root)
                shutil.rmtree(trash)
                _fsync_dir(root)
                deleted.append(gid)
        return {
            "result":"APPLIED" if apply else "DRY_RUN",
            "current_generation":current,
            "verified_generation_count":len(verified),
            "keep_last":keep_last,
            "minimum_age_seconds":minimum_age_seconds,
            "kept_generations":sorted(keep),
            "eligible_generations":candidates,
            "deleted_generations":deleted,
            "reaped_interrupted_cleanup":reaped_trash,
            "skipped_unverified_entries":sorted(skipped),
            "mutated":bool(deleted or reaped_trash),
        }

def self_check():
    from scripts.spare_parts_inventory_ledger_integrity import create_snapshot
    a=BalanceKey("HOLD","SYN-P","SYN-L","SYN-B","SYN-O","HOLD","EA")
    b=BalanceKey("AVAILABLE","SYN-P","SYN-L","SYN-B","SYN-O","RELEASED","EA")
    opening={a:Decimal("5"),b:Decimal("0")}; ledger=AppendOnlyEventLedger()
    ledger.append(LedgerEvent("SYN-P1","SYN-PB1","SYN-SRC","SYN-PI1","2026-01-01T09:00:00+08:00","2026-01-01T09:01:00+08:00","TRANSFER",a,b,Decimal("2")))
    snapshot=create_snapshot(ledger,opening,"2026-01-01T10:00:00+08:00")
    with tempfile.TemporaryDirectory(prefix="ch17-ledger-persist-") as tmp:
        root=Path(tmp)/"store"
        published=publish_generation(root,ledger,snapshot,"self-check-001")
        recovered=recover_current(root)
        assert recovered["ledger_record_count"]==1 and published["result"]=="COMMITTED"
        second=publish_generation(root,ledger,snapshot,"self-check-002",
                                  expected_current_generation="self-check-001")
        os.utime(root/"generation-self-check-001",(1,1))
        dry=garbage_collect_generations(root,keep_last=1,minimum_age_seconds=0)
        assert dry["result"]=="DRY_RUN" and dry["eligible_generations"]==["self-check-001"]
        assert (root/"generation-self-check-001").exists()
        with _gc_coordination_lock(root,shared=True):
            try:
                garbage_collect_generations(root,keep_last=1,minimum_age_seconds=0,
                                            apply=True,lock_timeout_seconds=0.02)
                raise AssertionError("GC must wait for an active reader")
            except PersistenceConflict:
                pass
        collected=garbage_collect_generations(root,keep_last=1,minimum_age_seconds=0,apply=True)
        recovered_after_gc=recover_current(root)
        assert collected["deleted_generations"]==["self-check-001"]
        assert recovered_after_gc["generation_id"]=="self-check-002"
        assert second["result"]=="COMMITTED"
    return {"result":"PASS","generation_publish":"PASS","committed_recovery":"PASS",
      "reader_gc_exclusion":"PASS","dry_run_non_mutating":"PASS","retention_and_recovery":"PASS",
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
