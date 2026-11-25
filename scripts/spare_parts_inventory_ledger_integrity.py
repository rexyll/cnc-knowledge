"""Synthetic-only SHA-256 event-chain and inventory snapshot checkpoint."""
import argparse, hashlib, json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from scripts.spare_parts_inventory_event_ledger import AppendOnlyEventLedger
from scripts.spare_parts_multidimensional_inventory import BalanceKey, InventoryEvent, InventoryLedger

VERSION=1
GENESIS="0"*64
class IntegrityError(ValueError): pass

def canon(x):
    return json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(",",":"),allow_nan=False).encode()
def digest(x): return hashlib.sha256(canon(x)).hexdigest()
def timestamp(s):
    try: d=datetime.fromisoformat(s.replace("Z","+00:00"))
    except (AttributeError,ValueError): raise IntegrityError("invalid ISO-8601 timestamp") from None
    if d.tzinfo is None or d.utcoffset() is None: raise IntegrityError("timestamp offset required")
    return d.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00","Z")
def dec(x):
    if not isinstance(x,Decimal) or not x.is_finite(): raise IntegrityError("finite Decimal required")
    x=x.normalize()
    return format(x,"f") if x else "0"
def key(k):
    k.validate()
    return {n:getattr(k,n) for n in ("account","item","lot","location","owner","condition","uom")}
def payload(r):
    e=r.event; e.validate()
    return {"ledger_sequence":r.ledger_sequence,"event":{
      "event_id":e.event_id,"business_event_id":e.business_event_id,"source_system_id":e.source_system_id,
      "idempotency_key":e.idempotency_key,"business_time":timestamp(e.business_time),
      "ingestion_time":timestamp(e.ingestion_time),"event_type":e.event_type,
      "source":key(e.source),"destination":key(e.destination),"quantity":dec(e.quantity),
      "reference_event_id":e.reference_event_id}}
def seal(records):
    rows=[]; prev=GENESIS
    for n,r in enumerate(records,1):
        if r.ledger_sequence!=n: raise IntegrityError("ledger sequence gap")
        p=payload(r); eh=digest(p); ch=hashlib.sha256((prev+eh).encode()).hexdigest()
        rows.append({**p,"event_hash":eh,"previous_chain_hash":prev,"chain_hash":ch}); prev=ch
    return {"schema_version":VERSION,"record_count":len(rows),"chain_head":prev,"records":rows}
def verify_chain(doc):
    if doc.get("schema_version")!=VERSION: raise IntegrityError("unsupported ledger schema")
    rows=doc.get("records")
    if not isinstance(rows,list) or doc.get("record_count")!=len(rows): raise IntegrityError("record count mismatch")
    prev=GENESIS; ids=set(); idems=set()
    for n,r in enumerate(rows,1):
        if r.get("ledger_sequence")!=n: raise IntegrityError("sequence gap or reordering")
        e=r.get("event") or {}; eid=e.get("event_id"); ik=e.get("idempotency_key")
        if not eid or eid in ids or not ik or ik in idems: raise IntegrityError("duplicate or missing event identity")
        ids.add(eid); idems.add(ik); p={"ledger_sequence":n,"event":e}; eh=digest(p)
        if r.get("event_hash")!=eh: raise IntegrityError("event hash mismatch")
        if r.get("previous_chain_hash")!=prev: raise IntegrityError("chain predecessor mismatch")
        ch=hashlib.sha256((prev+eh).encode()).hexdigest()
        if r.get("chain_hash")!=ch: raise IntegrityError("chain hash mismatch")
        prev=ch
    if doc.get("chain_head")!=prev: raise IntegrityError("chain head mismatch")
    return {"result":"PASS","record_count":len(rows),"chain_head":prev}
def rows(b):
    return [{"key":key(k),"quantity":dec(v)} for k,v in sorted(b.items())]
def unrows(rs):
    out={}
    for r in rs:
        try: k=BalanceKey(**r["key"]); v=Decimal(r["quantity"])
        except (KeyError,TypeError,ValueError): raise IntegrityError("invalid balance row") from None
        k.validate()
        if k in out or not v.is_finite() or v<0: raise IntegrityError("duplicate or invalid balance")
        out[k]=v
    return out
def snap_hash(s): return digest({k:v for k,v in s.items() if k!="snapshot_hash"})
def create_snapshot(ledger,opening,business_cutoff,known_at_cutoff=None):
    chain=seal(ledger.records); rebuilt=ledger.rebuild(opening,business_cutoff,known_at_cutoff)
    s={"schema_version":VERSION,"snapshot_type":"SYNTHETIC_TEST_ONLY","ledger_sequence":len(ledger.records),
      "chain_head":chain["chain_head"],"business_cutoff":timestamp(business_cutoff),
      "known_at_cutoff":timestamp(known_at_cutoff) if known_at_cutoff else None,
      "opening_balances":rows(opening),"balances":rows(rebuilt["balances"]),
      "business_rule_assertions":"NOT_EVALUATED","execution_status":"BLOCKED_PENDING_ENTERPRISE_APPROVAL"}
    s["snapshot_hash"]=snap_hash(s); return s
def verify_snapshot(s):
    if s.get("schema_version")!=VERSION: raise IntegrityError("unsupported snapshot version")
    if s.get("snapshot_type")!="SYNTHETIC_TEST_ONLY" or s.get("snapshot_hash")!=snap_hash(s):
        raise IntegrityError("snapshot type or digest invalid")
    if not isinstance(s.get("ledger_sequence"),int) or s["ledger_sequence"]<0: raise IntegrityError("invalid snapshot sequence")
    timestamp(s["business_cutoff"])
    if s.get("known_at_cutoff"): timestamp(s["known_at_cutoff"])
    unrows(s["opening_balances"]); unrows(s["balances"])
    if s.get("business_rule_assertions")!="NOT_EVALUATED" or s.get("execution_status")!="BLOCKED_PENDING_ENTERPRISE_APPROVAL":
        raise IntegrityError("approval gate cannot be changed by snapshot")
    return True
def restore_snapshot(s,ledger,new_business_cutoff,new_known_at_cutoff=None):
    verify_snapshot(s); fullchain=seal(ledger.records); seq=s["ledger_sequence"]
    if len(ledger.records)<seq or seal(ledger.records[:seq])["chain_head"]!=s["chain_head"]:
        raise IntegrityError("snapshot ledger prefix mismatch")
    old=datetime.fromisoformat(s["business_cutoff"].replace("Z","+00:00"))
    new=datetime.fromisoformat(timestamp(new_business_cutoff).replace("Z","+00:00"))
    if new<old: raise IntegrityError("business cutoff cannot move backwards")
    known=datetime.fromisoformat(timestamp(new_known_at_cutoff).replace("Z","+00:00")) if new_known_at_cutoff else None
    candidate=InventoryLedger(unrows(s["balances"])); suffix=[]
    for r in ledger.records[seq:]:
        bt=datetime.fromisoformat(timestamp(r.event.business_time).replace("Z","+00:00"))
        it=datetime.fromisoformat(timestamp(r.event.ingestion_time).replace("Z","+00:00"))
        if bt<=new and (known is None or it<=known):
            if bt<=old: raise IntegrityError("back-dated suffix invalidates snapshot; full rebuild required")
            suffix.append(r)
    suffix.sort(key=lambda r:(timestamp(r.event.business_time),r.ledger_sequence))
    for r in suffix:
        e=r.event
        candidate.transfer(InventoryEvent(e.event_id,r.ledger_sequence,e.source,e.destination,e.quantity,"SYNTHETIC_LEDGER_"+e.event_type))
    actual=candidate.balances
    expected=ledger.rebuild(unrows(s["opening_balances"]),new_business_cutoff,new_known_at_cutoff)["balances"]
    if actual!=expected: raise IntegrityError("incremental replay differs from full replay")
    return {"result":"PASS","replayed_suffix_events":len(suffix),"matches_full_replay":True,
      "chain_head":fullchain["chain_head"],"balances":rows(actual),
      "business_rule_assertions":"NOT_EVALUATED","execution_status":"BLOCKED_PENDING_ENTERPRISE_APPROVAL"}
def self_check():
    from scripts.spare_parts_inventory_event_ledger import LedgerEvent
    a=BalanceKey("HOLD","SYN-P","SYN-L","SYN-B","SYN-O","HOLD","EA")
    b=BalanceKey("AVAILABLE","SYN-P","SYN-L","SYN-B","SYN-O","RELEASED","EA")
    opening={a:Decimal("5"),b:Decimal("0")}; l=AppendOnlyEventLedger()
    l.append(LedgerEvent("SYN-E1","SYN-B1","SYN-SRC","SYN-I1","2026-01-01T09:00:00+08:00","2026-01-01T09:01:00+08:00","TRANSFER",a,b,Decimal("2")))
    s=create_snapshot(l,opening,"2026-01-01T10:00:00+08:00")
    l.append(LedgerEvent("SYN-E2","SYN-B2","SYN-SRC","SYN-I2","2026-01-01T11:00:00+08:00","2026-01-01T11:01:00+08:00","TRANSFER",a,b,Decimal("1")))
    r=restore_snapshot(s,l,"2026-01-01T12:00:00+08:00")
    return {"result":"PASS","sealed_records":2,"replayed_suffix_events":r["replayed_suffix_events"],
      "incremental_matches_full_replay":r["matches_full_replay"],"external_connections":False,
      "database_or_api_writes":False,"business_rule_assertions":"NOT_EVALUATED",
      "execution_status":"BLOCKED_PENDING_ENTERPRISE_APPROVAL"}
def main():
    p=argparse.ArgumentParser(); p.add_argument("--self-check",action="store_true"); p.add_argument("--report-json",type=Path); a=p.parse_args()
    if not a.self_check: p.error("--self-check required; enterprise access unsupported")
    out=json.dumps(self_check(),ensure_ascii=False,indent=2)+"\n"
    if a.report_json: a.report_json.parent.mkdir(parents=True,exist_ok=True); a.report_json.write_text(out,encoding="utf-8")
    print(out,end="")
if __name__=="__main__": main()
