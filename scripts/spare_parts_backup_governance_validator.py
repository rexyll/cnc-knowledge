#!/usr/bin/env python3
"""Validate CH17 backup governance schemas and approval evidence.

Structure/readiness gate only. It never applies retention, configures
cryptography, provisions remote storage, or enables production backup/restore.
"""
from __future__ import annotations
import argparse
import csv
import json
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

RESOURCE_DIR = Path("resouces/17-operation-maintenance-and-repair")
APPROVAL_STATUSES = {"DRAFT", "PROPOSED_NOT_APPROVED", "APPROVED", "REJECTED", "RETIRED"}
DRILL_CASE_IDS = [f"DRB-{i:03d}" for i in range(1, 11)]
SCHEMAS = {"spare-parts-inventory-backup-retention-policy-template.csv":["policy_id","policy_version","backup_scope","data_domain","data_classification","backup_type","backup_trigger_or_frequency","retention_duration","retention_unit","retention_basis","legal_hold_rule","immutability_requirement","delete_method","delete_approval_role","policy_owner_role","approver_role","approval_status","approval_reference","approved_at","effective_from","review_due","exceptions","notes"],"spare-parts-inventory-backup-rpo-rto-requirements-template.csv":["objective_id","service_id","service_name","business_process","impact_assessment_reference","service_tier","rpo_value","rpo_unit","rpo_measurement_basis","rto_value","rto_unit","rto_measurement_start","rto_measurement_end","dependency_scope","restore_sequence","validation_method","target_owner_role","approver_role","approval_status","approval_reference","approved_at","effective_from","notes"],"spare-parts-inventory-backup-security-key-management-template.csv":["control_id","data_scope","data_classification","encryption_at_rest_requirement","encryption_in_transit_requirement","approved_algorithm_and_mode","key_management_service","key_owner_role","key_custodian_role","key_generation_method","rotation_policy_reference","rotation_interval","backup_key_recovery_method","escrow_or_recovery_authority","break_glass_process","access_review_interval","key_compromise_response_reference","separation_of_duties","approval_status","approver_role","approval_reference","approved_at","notes"],"spare-parts-inventory-backup-offsite-storage-assessment-template.csv":["assessment_id","provider_name","service_name","account_or_tenant_owner","primary_region","secondary_region","jurisdiction","data_residency_requirement","data_classification_allowed","network_path","tls_policy","client_side_encryption","server_side_encryption","immutability_or_object_lock","retention_enforcement","versioning_and_delete_protection","iam_and_mfa","private_connectivity","restore_throughput_evidence","egress_cost_basis","service_sla_reference","provider_evidence_reference","exit_portability","verified_deletion_method","incident_notification_terms","approval_status","approver_role","approval_reference","approved_at","notes"],"spare-parts-inventory-backup-restore-drill-acceptance-matrix-v1.csv":["case_id","domain","scenario","preconditions","procedure_reference","acceptance_criteria_source","required_evidence","synthetic_only","approval_status","execution_status","notes"]}

RECORD_IDS = {
 "spare-parts-inventory-backup-retention-policy-template.csv":"policy_id",
 "spare-parts-inventory-backup-rpo-rto-requirements-template.csv":"objective_id",
 "spare-parts-inventory-backup-security-key-management-template.csv":"control_id",
 "spare-parts-inventory-backup-offsite-storage-assessment-template.csv":"assessment_id",
}
APPROVED_REQUIRED = {
 "spare-parts-inventory-backup-retention-policy-template.csv":[
  "backup_scope","data_domain","data_classification","backup_type","backup_trigger_or_frequency",
  "retention_duration","retention_unit","retention_basis","legal_hold_rule","delete_method",
  "delete_approval_role","policy_owner_role"],
 "spare-parts-inventory-backup-rpo-rto-requirements-template.csv":[
  "service_id","service_name","business_process","impact_assessment_reference","rpo_value","rpo_unit",
  "rpo_measurement_basis","rto_value","rto_unit","rto_measurement_start","rto_measurement_end",
  "dependency_scope","restore_sequence","validation_method","target_owner_role"],
 "spare-parts-inventory-backup-security-key-management-template.csv":[
  "data_scope","data_classification","encryption_at_rest_requirement","encryption_in_transit_requirement",
  "approved_algorithm_and_mode","key_management_service","key_owner_role","key_custodian_role",
  "key_generation_method","rotation_policy_reference","backup_key_recovery_method",
  "escrow_or_recovery_authority","break_glass_process","key_compromise_response_reference",
  "separation_of_duties"],
 "spare-parts-inventory-backup-offsite-storage-assessment-template.csv":[
  "provider_name","service_name","account_or_tenant_owner","primary_region","jurisdiction",
  "data_residency_requirement","data_classification_allowed","network_path","tls_policy",
  "client_side_encryption","server_side_encryption","immutability_or_object_lock",
  "retention_enforcement","versioning_and_delete_protection","iam_and_mfa",
  "restore_throughput_evidence","egress_cost_basis","service_sla_reference",
  "provider_evidence_reference","exit_portability","verified_deletion_method",
  "incident_notification_terms"],
}
def _read_table(path: Path, expected: list[str], errors: list[str]) -> tuple[list[dict[str,str]], list[str]]:
 try:
  with path.open("r",encoding="utf-8-sig",newline="") as stream:
   reader=csv.reader(stream); headers=next(reader,None)
   if headers is None:
    errors.append(f"{path}: empty CSV"); return [],[]
   if len(headers)!=len(set(headers)): errors.append(f"{path}: duplicate header names")
   if headers!=expected: errors.append(f"{path}: header mismatch; expected exact ordered schema with {len(expected)} columns")
   rows=[]
   for line,values in enumerate(reader,start=2):
    if not values or all(value=="" for value in values): continue
    if len(values)!=len(headers):
     errors.append(f"{path}: row {line} has {len(values)} columns; expected {len(headers)}"); continue
    rows.append(dict(zip(headers,values)))
   return rows,headers
 except (OSError,UnicodeError,csv.Error) as exc:
  errors.append(f"{path}: unable to read CSV: {exc}"); return [],[]
def _timestamp_ok(value: str) -> bool:
 try:
  parsed=datetime.fromisoformat(value.replace("Z","+00:00"))
  return parsed.tzinfo is not None and parsed.utcoffset() is not None
 except ValueError: return False
def _decimal_ok(value: str,allow_zero: bool=False) -> bool:
 try: number=Decimal(value)
 except (InvalidOperation,ValueError): return False
 if not number.is_finite(): return False
 return number>=0 if allow_zero else number>0
def _check_approved(filename: str,row: dict[str,str],line: int,errors: list[str]) -> None:
 required=APPROVED_REQUIRED[filename]+["approver_role","approval_reference","approved_at"]
 if filename in {"spare-parts-inventory-backup-retention-policy-template.csv","spare-parts-inventory-backup-rpo-rto-requirements-template.csv"}:
  required.append("effective_from")
 missing=[field for field in required if not row.get(field,"").strip()]
 if missing: errors.append(f"{filename}: row {line}: APPROVED record missing fields: {', '.join(missing)}")
 for field in ("approved_at","effective_from"):
  value=row.get(field,"")
  if value and not _timestamp_ok(value):
   errors.append(f"{filename}: row {line}: {field} must include an explicit UTC offset")
 if filename=="spare-parts-inventory-backup-retention-policy-template.csv":
  value=row.get("retention_duration","")
  if value and not _decimal_ok(value): errors.append(f"{filename}: row {line}: retention_duration must be finite and positive")
 if filename=="spare-parts-inventory-backup-rpo-rto-requirements-template.csv":
  rpo=row.get("rpo_value",""); rto=row.get("rto_value","")
  if rpo and not _decimal_ok(rpo,allow_zero=True): errors.append(f"{filename}: row {line}: rpo_value must be finite and non-negative")
  if rto and not _decimal_ok(rto): errors.append(f"{filename}: row {line}: rto_value must be finite and positive")

def validate_governance(root: Path) -> dict[str,Any]:
 root=root.resolve(); errors=[]; warnings=[]; checks=[]
 totals={"template_files":0,"policy_records":0,"approved_policy_records":0,"drill_cases":0}
 files=[]
 def check(name,ok,detail):
  checks.append({"name":name,"status":"PASS" if ok else "FAIL","detail":detail})
  if not ok: errors.append(f"{name}: {detail}")
 for filename,expected in SCHEMAS.items():
  rows,headers=_read_table(root/RESOURCE_DIR/filename,expected,errors)
  totals["template_files"]+=1
  files.append({"path":(RESOURCE_DIR/filename).as_posix(),"columns":len(headers),"data_rows":len(rows)})
  check("schema:"+filename,headers==expected,"exact ordered schema and unique columns" if headers==expected else "schema mismatch")
  if filename=="spare-parts-inventory-backup-restore-drill-acceptance-matrix-v1.csv":
   totals["drill_cases"]=len(rows)
   ids=[row.get("case_id","") for row in rows]
   check("restore_drill_case_set",ids==DRILL_CASE_IDS,"exactly DRB-001..DRB-010 in canonical order" if ids==DRILL_CASE_IDS else "duplicate, missing, extra or reordered drill IDs")
   states=all(row.get("synthetic_only")=="TRUE" and row.get("approval_status")=="PROPOSED_NOT_APPROVED" and row.get("execution_status")=="NOT_RUN" for row in rows)
   check("restore_drill_status_gate",states,"all drill specifications are synthetic, unapproved and NOT_RUN" if states else "drill matrix must remain TRUE / PROPOSED_NOT_APPROVED / NOT_RUN")
   continue
  id_field=RECORD_IDS[filename]; seen=set()
  for line,row in enumerate(rows,start=2):
   totals["policy_records"]+=1
   record_id=row.get(id_field,"").strip()
   if not record_id: errors.append(f"{filename}: row {line}: blank {id_field}")
   elif record_id in seen: errors.append(f"{filename}: duplicate {id_field} {record_id}")
   seen.add(record_id)
   status=row.get("approval_status","").strip()
   if status not in APPROVAL_STATUSES:
    errors.append(f"{filename}: row {line}: unsupported approval_status {status!r}")
   elif status=="APPROVED":
    totals["approved_policy_records"]+=1; _check_approved(filename,row,line,errors)
   elif status=="PROPOSED_NOT_APPROVED":
    warnings.append(f"{filename}: {record_id or 'unnamed row'} awaits enterprise approval")
 return {
  "result":"PASS" if not errors else "FAIL",
  "governance_readiness":"BLOCKED_PENDING_ENTERPRISE_APPROVAL",
  "production_backup_enabled":False,
  "scope":"schema and approval-evidence validation only; no encryption, key, network, provider or backup operation",
  "totals":totals,"files":files,"checks":checks,"errors":errors,"warnings":warnings,
  "business_rule_assertions":"NOT_EVALUATED","enterprise_backup_test_status":"NOT_RUN"
}
def main() -> int:
 parser=argparse.ArgumentParser(description="Validate CH17 backup governance templates and approval gates.")
 parser.add_argument("--root",type=Path,default=Path(".")); parser.add_argument("--report-json",type=Path)
 args=parser.parse_args(); report=validate_governance(args.root)
 output=json.dumps(report,ensure_ascii=False,indent=2)+"\n"
 if args.report_json:
  args.report_json.parent.mkdir(parents=True,exist_ok=True)
  args.report_json.write_text(output,encoding="utf-8")
 print(output,end="")
 return 0 if report["result"]=="PASS" else 1
if __name__=="__main__": raise SystemExit(main())
