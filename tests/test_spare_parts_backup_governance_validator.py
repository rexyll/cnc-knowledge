from __future__ import annotations
import csv, shutil, tempfile, unittest
from pathlib import Path
from scripts import spare_parts_backup_governance_validator as validator
REPO_ROOT=Path(__file__).resolve().parents[1]
class BackupGovernanceValidatorTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name)
  target=self.root/validator.RESOURCE_DIR; target.mkdir(parents=True)
  for filename in validator.SCHEMAS:
   shutil.copy2(REPO_ROOT/validator.RESOURCE_DIR/filename,target/filename)
 def tearDown(self): self.temp.cleanup()
 def write_rows(self,filename,rows):
  path=self.root/validator.RESOURCE_DIR/filename; headers=validator.SCHEMAS[filename]
  with path.open("w",encoding="utf-8",newline="") as stream:
   writer=csv.DictWriter(stream,fieldnames=headers,lineterminator="\n"); writer.writeheader(); writer.writerows(rows)
  return path
 def approved_row(self,filename,record_id):
  row={h:"" for h in validator.SCHEMAS[filename]}
  id_field=validator.RECORD_IDS[filename]; row[id_field]=record_id
  row["approval_status"]="APPROVED"; row["approver_role"]="Inventory Data Owner"
  row["approval_reference"]="SYN-APPROVAL-001"; row["approved_at"]="2026-11-26T09:00:00+08:00"
  if "effective_from" in row: row["effective_from"]="2026-12-01T00:00:00+08:00"
  for field in validator.APPROVED_REQUIRED[filename]: row[field]=row.get(field) or "SYNTHETIC-APPROVED-VALUE"
  if filename=="spare-parts-inventory-backup-retention-policy-template.csv": row["retention_duration"]="30"
  if filename=="spare-parts-inventory-backup-rpo-rto-requirements-template.csv":
   row["rpo_value"]="0"; row["rpo_unit"]="minutes"; row["rto_value"]="60"; row["rto_unit"]="minutes"
  return row
 def test_blank_templates_and_proposed_drills_pass_but_gate_stays_blocked(self):
  report=validator.validate_governance(self.root)
  self.assertEqual(report["result"],"PASS",report["errors"]); self.assertEqual(report["totals"]["template_files"],5)
  self.assertEqual(report["totals"]["drill_cases"],10); self.assertEqual(report["governance_readiness"],"BLOCKED_PENDING_ENTERPRISE_APPROVAL")
  self.assertFalse(report["production_backup_enabled"]); self.assertEqual(report["enterprise_backup_test_status"],"NOT_RUN")
 def test_missing_template_fails(self):
  (self.root/validator.RESOURCE_DIR/next(iter(validator.SCHEMAS))).unlink()
  self.assertEqual(validator.validate_governance(self.root)["result"],"FAIL")
 def test_wrong_header_order_fails(self):
  filename=next(iter(validator.SCHEMAS)); (self.root/validator.RESOURCE_DIR/filename).write_text("wrong,headers\n",encoding="utf-8")
  report=validator.validate_governance(self.root); self.assertTrue(any("header mismatch" in e for e in report["errors"]))
 def test_malformed_row_width_fails(self):
  filename=next(iter(validator.SCHEMAS))
  with (self.root/validator.RESOURCE_DIR/filename).open("a",encoding="utf-8") as stream: stream.write("broken,row\n")
  report=validator.validate_governance(self.root); self.assertTrue(any("has 2 columns" in e for e in report["errors"]))
 def test_duplicate_record_id_fails(self):
  filename="spare-parts-inventory-backup-retention-policy-template.csv"
  row={h:"" for h in validator.SCHEMAS[filename]}; row.update(policy_id="POLICY-001",approval_status="DRAFT")
  self.write_rows(filename,[row,row.copy()]); report=validator.validate_governance(self.root)
  self.assertTrue(any("duplicate policy_id" in e for e in report["errors"]))
 def test_approved_record_requires_approval_evidence(self):
  filename="spare-parts-inventory-backup-retention-policy-template.csv"
  row={h:"" for h in validator.SCHEMAS[filename]}; row.update(policy_id="POLICY-001",approval_status="APPROVED")
  self.write_rows(filename,[row]); report=validator.validate_governance(self.root)
  self.assertTrue(any("APPROVED record missing fields" in e for e in report["errors"]))
 def test_approved_rpo_rto_values_must_be_valid(self):
  filename="spare-parts-inventory-backup-rpo-rto-requirements-template.csv"
  row=self.approved_row(filename,"RTO-001"); row["rpo_value"]="-1"; row["rto_value"]="NaN"
  self.write_rows(filename,[row]); report=validator.validate_governance(self.root)
  self.assertTrue(any("rpo_value must be finite and non-negative" in e for e in report["errors"]))
  self.assertTrue(any("rto_value must be finite and positive" in e for e in report["errors"]))
 def test_approved_timestamp_requires_timezone(self):
  filename="spare-parts-inventory-backup-security-key-management-template.csv"
  row=self.approved_row(filename,"KEY-001"); row["approved_at"]="2026-11-26T09:00:00"
  self.write_rows(filename,[row]); report=validator.validate_governance(self.root)
  self.assertTrue(any("explicit UTC offset" in e for e in report["errors"]))
 def test_drill_matrix_cannot_claim_unexecuted_case_passed(self):
  filename="spare-parts-inventory-backup-restore-drill-acceptance-matrix-v1.csv"
  with (self.root/validator.RESOURCE_DIR/filename).open("r",encoding="utf-8",newline="") as stream: rows=list(csv.DictReader(stream))
  rows[0]["execution_status"]="PASS"; self.write_rows(filename,rows)
  report=validator.validate_governance(self.root); self.assertTrue(any("drill matrix must remain" in e for e in report["errors"]))

 def test_drill_matrix_requires_acceptance_criteria_source_and_evidence(self):
  filename="spare-parts-inventory-backup-restore-drill-acceptance-matrix-v1.csv"
  with (self.root/validator.RESOURCE_DIR/filename).open("r",encoding="utf-8",newline="") as stream: rows=list(csv.DictReader(stream))
  rows[0]["acceptance_criteria_source"]=""
  self.write_rows(filename,rows)
  report=validator.validate_governance(self.root)
  self.assertTrue(any("acceptance criteria source and evidence" in e for e in report["errors"]))
 def test_approved_policy_does_not_unlock_production(self):
  filename="spare-parts-inventory-backup-retention-policy-template.csv"
  self.write_rows(filename,[self.approved_row(filename,"POLICY-001")])
  report=validator.validate_governance(self.root); self.assertEqual(report["result"],"PASS",report["errors"])
  self.assertEqual(report["totals"]["approved_policy_records"],1)
  self.assertEqual(report["governance_readiness"],"BLOCKED_PENDING_ENTERPRISE_APPROVAL")
  self.assertFalse(report["production_backup_enabled"])
if __name__=="__main__": unittest.main()
