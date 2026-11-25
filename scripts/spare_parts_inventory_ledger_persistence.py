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

def _verified_generation_payloads(generation, gid):
    generation=Path(generation)
    if generation.is_symlink() or not generation.is_dir():
        raise PersistenceError("backup source generation is missing or unsafe")
    payloads={}
    for name in ("COMMIT.json","ledger.json","snapshot.json"):
        path=generation/name
        if path.is_symlink() or not path.is_file():
            raise PersistenceError("backup source payload is missing or unsafe: "+name)
        try: payloads[name]=path.read_bytes()
        except OSError as exc: raise PersistenceError("backup source payload is unreadable: "+name) from exc
    try:
        commit=json.loads(payloads["COMMIT.json"])
        chain=json.loads(payloads["ledger.json"])
        snapshot=json.loads(payloads["snapshot.json"])
    except (UnicodeError,json.JSONDecodeError) as exc:
        raise PersistenceError("backup source contains malformed JSON") from exc
    if not isinstance(commit,dict) or not isinstance(chain,dict) or not isinstance(snapshot,dict):
        raise PersistenceError("backup source payload roots must be JSON objects")
    if commit.get("format_version")!=FORMAT_VERSION or commit.get("generation_id")!=gid or commit.get("commit_state")!="COMMITTED":
        raise PersistenceError("backup source COMMIT marker is invalid")
    if _sha(payloads["ledger.json"])!=commit.get("ledger_sha256") or _sha(payloads["snapshot.json"])!=commit.get("snapshot_sha256"):
        raise PersistenceError("backup source payload digest mismatch")
    try:
        result=verify_chain(chain)
        verify_snapshot(snapshot)
        if result["record_count"]!=commit.get("ledger_record_count"):
            raise PersistenceError("backup source ledger record count mismatch")
        sequence=snapshot.get("ledger_sequence")
        if sequence!=commit.get("snapshot_ledger_sequence") or sequence>result["record_count"]:
            raise PersistenceError("backup source snapshot sequence mismatch")
        prefix_head="0"*64 if sequence==0 else chain["records"][sequence-1]["chain_hash"]
        prefix={"schema_version":chain["schema_version"],"record_count":sequence,
                "chain_head":prefix_head,"records":chain["records"][:sequence]}
        verify_chain(prefix)
        if snapshot.get("chain_head")!=prefix_head:
            raise PersistenceError("backup source snapshot does not match its ledger prefix")
        ledger=_restore_ledger(chain)
    except IntegrityError as exc:
        raise PersistenceError("backup source integrity validation failed") from exc
    if len(ledger.records)!=result["record_count"]:
        raise PersistenceError("backup source event reconstruction count mismatch")
    return payloads,{"generation_id":gid,"ledger_record_count":result["record_count"],
                     "chain_head":result["chain_head"]}

def _paths_overlap(first,second):
    first=Path(first).resolve()
    second=Path(second).resolve()
    return first==second or first in second.parents or second in first.parents

def create_backup(root, backup_parent, backup_id, *, failure_stage=None,
                  lock_timeout_seconds=5.0):
    """Create a self-contained, checksummed backup outside the ledger store."""
    root=Path(root)
    parent=Path(backup_parent)
    bid=_safe_generation(backup_id)
    if failure_stage not in {None,"after_payloads","before_backup_publish"}:
        raise PersistenceError("unsupported backup fault stage")
    if root.is_symlink() or not root.is_dir():
        raise PersistenceError("ledger store is missing or unsafe")
    if parent.exists() and parent.is_symlink():
        raise PersistenceError("backup parent cannot be a symlink")
    if _paths_overlap(root,parent):
        raise PersistenceError("backup location must be separate from the ledger store")
    parent.mkdir(parents=True,exist_ok=True)
    if parent.is_symlink() or not parent.is_dir():
        raise PersistenceError("backup parent is unsafe")
    final=parent/("backup-"+bid)
    stage=parent/(".backup-staging-"+bid)
    if final.exists() or final.is_symlink() or stage.exists() or stage.is_symlink():
        raise PersistenceConflict("backup already exists or staging residue requires inspection")
    with _gc_coordination_lock(root,shared=True,timeout_seconds=lock_timeout_seconds):
        gid=_read_current_generation(root)
        if gid is None: raise PersistenceError("cannot back up a store without CURRENT")
        payloads,summary=_verified_generation_payloads(root/("generation-"+gid),gid)
        stage.mkdir()
        try:
            entries={}
            for name,data in sorted(payloads.items()):
                _write_sync(stage/name,data)
                entries[name]={"size_bytes":len(data),"sha256":_sha(data)}
            if failure_stage=="after_payloads":
                raise PersistenceError("injected interruption after backup payload copy")
            manifest_base={
                "format_version":FORMAT_VERSION,
                "backup_state":"COMPLETE",
                "backup_id":bid,
                "source_generation_id":gid,
                "created_at_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),
                "payloads":entries,
                "ledger_record_count":summary["ledger_record_count"],
                "chain_head":summary["chain_head"],
            }
            manifest={**manifest_base,"backup_manifest_sha256":_sha(_json_bytes(manifest_base))}
            _write_sync(stage/"BACKUP.json",_json_bytes(manifest))
            _fsync_dir(stage)
            if failure_stage=="before_backup_publish":
                raise PersistenceError("injected interruption before atomic backup publish")
            os.replace(stage,final)
            _fsync_dir(parent)
            return {"result":"BACKUP_CREATED","backup_id":bid,"backup_path":str(final),
                    "source_generation_id":gid,"ledger_record_count":summary["ledger_record_count"],
                    "backup_manifest_sha256":manifest["backup_manifest_sha256"]}
        except Exception:
            if stage.exists() and not stage.is_symlink(): shutil.rmtree(stage)
            raise

def _load_verified_backup(backup_dir):
    backup=Path(backup_dir)
    if backup.is_symlink() or not backup.is_dir():
        raise PersistenceError("backup directory is missing or unsafe")
    expected={"BACKUP.json","COMMIT.json","ledger.json","snapshot.json"}
    try: children={item.name for item in backup.iterdir()}
    except OSError as exc: raise PersistenceError("backup directory cannot be listed") from exc
    if children!=expected:
        raise PersistenceError("backup directory has missing or unexpected entries")
    raw={}
    for name in sorted(expected):
        path=backup/name
        if path.is_symlink() or not path.is_file():
            raise PersistenceError("backup payload is not a regular file: "+name)
        try: raw[name]=path.read_bytes()
        except OSError as exc: raise PersistenceError("backup payload is unreadable: "+name) from exc
    try: manifest=json.loads(raw["BACKUP.json"])
    except (UnicodeError,json.JSONDecodeError) as exc: raise PersistenceError("backup manifest is malformed") from exc
    if not isinstance(manifest,dict) or manifest.get("format_version")!=FORMAT_VERSION or manifest.get("backup_state")!="COMPLETE":
        raise PersistenceError("backup manifest version or state is invalid")
    digest=manifest.get("backup_manifest_sha256")
    base={key:value for key,value in manifest.items() if key!="backup_manifest_sha256"}
    if not isinstance(digest,str) or _sha(_json_bytes(base))!=digest:
        raise PersistenceError("backup manifest digest mismatch")
    _safe_generation(manifest.get("backup_id"))
    gid=_safe_generation(manifest.get("source_generation_id"))
    entries=manifest.get("payloads")
    if not isinstance(entries,dict) or set(entries)!={"COMMIT.json","ledger.json","snapshot.json"}:
        raise PersistenceError("backup payload manifest is incomplete")
    for name,data in raw.items():
        if name=="BACKUP.json": continue
        entry=entries.get(name)
        if not isinstance(entry,dict) or entry.get("size_bytes")!=len(data) or entry.get("sha256")!=_sha(data):
            raise PersistenceError("backup payload checksum or size mismatch: "+name)
    verified,summary=_verified_generation_payloads_from_bytes(raw,gid)
    if summary["ledger_record_count"]!=manifest.get("ledger_record_count") or summary["chain_head"]!=manifest.get("chain_head"):
        raise PersistenceError("backup manifest metadata mismatch")
    return verified,manifest

def _verified_generation_payloads_from_bytes(raw,gid):
    try:
        commit=json.loads(raw["COMMIT.json"])
        chain=json.loads(raw["ledger.json"])
        snapshot=json.loads(raw["snapshot.json"])
    except (KeyError,UnicodeError,json.JSONDecodeError) as exc:
        raise PersistenceError("backup payload JSON is malformed") from exc
    if not all(isinstance(x,dict) for x in (commit,chain,snapshot)):
        raise PersistenceError("backup payload roots must be JSON objects")
    if commit.get("format_version")!=FORMAT_VERSION or commit.get("generation_id")!=gid or commit.get("commit_state")!="COMMITTED":
        raise PersistenceError("backup COMMIT marker is invalid")
    if _sha(raw["ledger.json"])!=commit.get("ledger_sha256") or _sha(raw["snapshot.json"])!=commit.get("snapshot_sha256"):
        raise PersistenceError("backup file digest mismatch")
    try:
        result=verify_chain(chain)
        verify_snapshot(snapshot)
        sequence=snapshot.get("ledger_sequence")
        if result["record_count"]!=commit.get("ledger_record_count") or sequence!=commit.get("snapshot_ledger_sequence") or sequence>result["record_count"]:
            raise PersistenceError("backup commit metadata mismatch")
        prefix_head="0"*64 if sequence==0 else chain["records"][sequence-1]["chain_hash"]
        prefix={"schema_version":chain["schema_version"],"record_count":sequence,
                "chain_head":prefix_head,"records":chain["records"][:sequence]}
        verify_chain(prefix)
        if snapshot.get("chain_head")!=prefix_head:
            raise PersistenceError("backup snapshot chain prefix mismatch")
        ledger=_restore_ledger(chain)
    except IntegrityError as exc:
        raise PersistenceError("backup ledger/snapshot integrity validation failed") from exc
    if len(ledger.records)!=result["record_count"]:
        raise PersistenceError("backup event reconstruction count mismatch")
    return {"COMMIT.json":raw["COMMIT.json"],"ledger.json":raw["ledger.json"],"snapshot.json":raw["snapshot.json"]}, {
        "generation_id":gid,"ledger_record_count":result["record_count"],"chain_head":result["chain_head"]}

def verify_backup(backup_dir):
    """Verify backup manifest, per-file digests, commit marker and ledger semantics."""
    payloads,manifest=_load_verified_backup(backup_dir)
    return {"result":"VERIFIED","backup_id":manifest["backup_id"],
            "source_generation_id":manifest["source_generation_id"],
            "ledger_record_count":manifest["ledger_record_count"],
            "chain_head":manifest["chain_head"],
            "payload_files":sorted(payloads),"backup_manifest_sha256":manifest["backup_manifest_sha256"]}

def restore_backup(backup_dir,target_root,*,failure_stage=None,lock_timeout_seconds=5.0):
    """Restore a verified backup into an empty, isolated local store without overwrite."""
    if failure_stage not in {None,"after_generation_rename","before_pointer_replace"}:
        raise PersistenceError("unsupported restore fault stage")
    payloads,manifest=_load_verified_backup(backup_dir)
    source=Path(backup_dir).resolve()
    target=Path(target_root)
    if target.exists() and target.is_symlink():
        raise PersistenceError("restore target cannot be a symlink")
    if _paths_overlap(source,target):
        raise PersistenceError("restore target must be separate from backup source")
    target.mkdir(parents=True,exist_ok=True)
    if not target.is_dir() or any(target.iterdir()):
        raise PersistenceConflict("restore target must be an existing empty directory")
    with _exclusive_store_lock(target,lock_timeout_seconds):
      with _gc_coordination_lock(target,shared=False,timeout_seconds=lock_timeout_seconds):
        entries={item.name for item in target.iterdir()}
        if entries!={".writer.lock",".gc.lock"}:
            raise PersistenceConflict("restore target changed or is not empty")
        gid=manifest["source_generation_id"]
        generation=target/("generation-"+gid)
        stage=target/(".staging-"+gid)
        if generation.exists() or stage.exists():
            raise PersistenceConflict("restore generation already exists or staging residue requires inspection")
        stage.mkdir()
        try:
            for name,data in sorted(payloads.items()):
                _write_sync(stage/name,data)
            _fsync_dir(stage)
            os.replace(stage,generation)
            _fsync_dir(target)
            if failure_stage=="after_generation_rename":
                raise PersistenceError("injected interruption after restored generation publish")
            pointer_tmp=target/(".CURRENT-restore.tmp")
            _write_sync(pointer_tmp,_json_bytes({"format_version":FORMAT_VERSION,"generation_id":gid}))
            if failure_stage=="before_pointer_replace":
                raise PersistenceError("injected interruption before restored CURRENT publish")
            os.replace(pointer_tmp,target/"CURRENT")
            _fsync_dir(target)
        except Exception:
            if stage.exists() and not stage.is_symlink(): shutil.rmtree(stage)
            raise
        recovered=_recover_current_unlocked(target)
        return {"result":"RESTORED","backup_id":manifest["backup_id"],
                "generation_id":recovered["generation_id"],
                "ledger_record_count":recovered["ledger_record_count"],
                "chain_head":recovered["chain_head"],
                "business_rule_assertions":"NOT_EVALUATED",
                "execution_status":"BLOCKED_PENDING_ENTERPRISE_APPROVAL"}

def self_check():
    from scripts.spare_parts_inventory_ledger_integrity import create_snapshot
    a=BalanceKey("HOLD","SYN-P","SYN-L","SYN-B","SYN-O","HOLD","EA")
    b=BalanceKey("AVAILABLE","SYN-P","SYN-L","SYN-B","SYN-O","RELEASED","EA")
    opening={a:Decimal("5"),b:Decimal("0")}; ledger=AppendOnlyEventLedger()
    ledger.append(LedgerEvent("SYN-P1","SYN-PB1","SYN-SRC","SYN-PI1","2026-01-01T09:00:00+08:00","2026-01-01T09:01:00+08:00","TRANSFER",a,b,Decimal("2")))
    snapshot=create_snapshot(ledger,opening,"2026-01-01T10:00:00+08:00")
    with tempfile.TemporaryDirectory(prefix="ch17-ledger-persist-") as tmp:
        root=Path(tmp)/"store"
        backup_parent=Path(tmp)/"backups"
        restore_root=Path(tmp)/"restored"
        published=publish_generation(root,ledger,snapshot,"self-check-001")
        recovered=recover_current(root)
        assert recovered["ledger_record_count"]==1 and published["result"]=="COMMITTED"
        backup=create_backup(root,backup_parent,"self-check-backup")
        verified=verify_backup(backup["backup_path"])
        assert verified["result"]=="VERIFIED"
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
        restored=restore_backup(backup["backup_path"],restore_root)
        restored_state=recover_current(restore_root)
        assert restored["result"]=="RESTORED"
        assert restored_state["generation_id"]=="self-check-001"
        assert restored_state["ledger_record_count"]==1
    return {"result":"PASS","generation_publish":"PASS","committed_recovery":"PASS",
      "reader_gc_exclusion":"PASS","dry_run_non_mutating":"PASS","retention_and_recovery":"PASS",
      "backup_manifest_and_payload_verification":"PASS","restore_to_isolated_store":"PASS",
      "backup_survives_source_generation_gc":"PASS","restored_event_count":1,
      "temporary_directory_only":True,"external_connections":False,
      "database_or_api_writes":False,"business_rule_assertions":"NOT_EVALUATED",
      "execution_status":"BLOCKED_PENDING_ENTERPRISE_APPROVAL"}
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--self-check",action="store_true")
    p.add_argument("--report-json",type=Path)
    p.add_argument("--gc-root",type=Path,help="local ledger store directory; defaults to a non-mutating GC plan")
    p.add_argument("--gc-apply",action="store_true",help="explicitly apply the generation retention plan")
    p.add_argument("--keep-last",type=int,default=3)
    p.add_argument("--minimum-age-seconds",type=float,default=604800)
    p.add_argument("--backup-root",type=Path,help="ledger store to back up")
    p.add_argument("--backup-parent",type=Path,help="separate directory in which to create the backup")
    p.add_argument("--backup-id",help="unique backup identifier")
    p.add_argument("--verify-backup",type=Path,help="verify a backup directory")
    p.add_argument("--restore-backup",type=Path,help="restore a verified backup")
    p.add_argument("--restore-target",type=Path,help="empty isolated store directory for restore")
    a=p.parse_args()
    modes=sum(x is not None for x in (a.gc_root,a.backup_root,a.verify_backup,a.restore_backup))+int(a.self_check)
    if modes!=1: p.error("choose exactly one of --self-check, --gc-root, --backup-root, --verify-backup or --restore-backup")
    if a.gc_root is not None:
        if a.gc_apply and a.backup_parent: p.error("incompatible GC options")
        result=garbage_collect_generations(a.gc_root,keep_last=a.keep_last,
            minimum_age_seconds=a.minimum_age_seconds,apply=a.gc_apply)
    elif a.backup_root is not None:
        if a.backup_parent is None or not a.backup_id: p.error("--backup-root requires --backup-parent and --backup-id")
        if a.gc_apply: p.error("--gc-apply cannot be combined with backup")
        result=create_backup(a.backup_root,a.backup_parent,a.backup_id)
    elif a.verify_backup is not None:
        if a.gc_apply or a.backup_parent or a.backup_id: p.error("incompatible backup verification options")
        result=verify_backup(a.verify_backup)
    elif a.restore_backup is not None:
        if a.restore_target is None: p.error("--restore-backup requires --restore-target")
        if a.gc_apply: p.error("--gc-apply cannot be combined with restore")
        result=restore_backup(a.restore_backup,a.restore_target)
    else:
        if a.gc_apply or a.backup_parent or a.backup_id or a.restore_target: p.error("incompatible self-check options")
        result=self_check()
    out=json.dumps(result,ensure_ascii=False,indent=2)+"\n"
    if a.report_json:
        a.report_json.parent.mkdir(parents=True,exist_ok=True)
        a.report_json.write_text(out,encoding="utf-8")
    print(out,end="")
if __name__=="__main__": main()
