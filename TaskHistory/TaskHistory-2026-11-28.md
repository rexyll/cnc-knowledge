# Task History — 2026-11-28

## CNC Knowledge Base — Round 79

- Repository: `rexyll/cnc-knowledge`
- Branch: `main` only. No branch was created.
- Scope: MIG-05 staged-import execution contract tests and exact checkpoint-chain recovery.

### Code changes

- Tightened `classify_batch_unknown()` in `scripts/spare_parts_sqlite_staged_import_protocol.py`: the observed checkpoint must byte-match one of the immutable plan's expected successor checkpoints for the current or a later batch. A matching plan digest, request values and a merely advanced counter are insufficient.
- Updated `tests/test_spare_parts_sqlite_staged_import_protocol.py` with explicit expected-successor checkpoint coverage and a forged-progress-digest rejection test.
- Added `tests/test_spare_parts_sqlite_staged_import_execution.py`. The tests drive real `EtcdV3CoordinatorAuthorityStore` request translation into `InMemoryEtcdV3Client` and cover:
  - process/adapter reconstruction after an earlier batch, checkpoint resume, unique request-key creation and final-only Scheduler state publication;
  - lost Txn response after commit and authoritative read-back classification;
  - timeout before commit, exact predecessor-state verification and retry of the identical Txn;
  - a competing writer winning one request key, causing the import CAS to fail without partial batch writes or checkpoint advancement;
  - lost final-publish response resolved through exact Scheduler state, final checkpoint and absent Leader key.
- Representative commits: `6d8b6843a6c4ec1d29b336a332febd0775187e7e` (strict checkpoint chain), `5b33cf3c555f16be443d796cdd190ada5410c725` (execution simulation tests), `3997c2d765dca141b7fd1a328b5316cf7fd070d1` (forged checkpoint test).

### Validation

- [Knowledge Quality Run 46092128612](https://github.com/rexyll/cnc-knowledge/actions/runs/46092128612): success.
- Full unittest suite: 600 tests discovered/run, 40 skipped, 560 passed.
- CH12 numerical resource tests: 143 passed.
- Knowledge lint: 0 errors / 5 warnings.
- Knowledge structure and data quality: 0 errors.

### Documentation

- Updated root `TaskPlan.md`, chapter `docs/TaskPlan/17-operation-maintenance-and-repair/TaskPlan.md`, chapter README and `sqlite-to-unified-coordinator-migration-design.md`.
- MIG-05 is now IN_PROGRESS for the subset of in-memory transaction/recovery tests completed here. Broader schema mapping, fencing, idempotency/TTL, Provider fencing and real-etcd fault validation remain outstanding.
- MIG-04 remains IN_PROGRESS; MIG-06 remains TODO; MIG-07 remains BLOCKED.

### Safety boundary

- `InMemoryEtcdV3Client` is a single-process test double. This work does not prove etcd Raft/Quorum behavior, disk durability, real multi-host concurrency, network partition recovery, service-side Txn limits or production RBAC.
- No real etcd Range/Txn/Lease write was performed. No Lease was granted or revoked. No RBAC, application startup or production namespace was changed. No candidate data was imported and no production cutover was performed.
- ASSET-000092 remains `PROPOSED_NOT_APPROVED / NOT_RUN`; production Unified schema-v2 remains the sole authority.


## CNC Knowledge Base — Round 80

- Repository: \`rexyll/cnc-knowledge\`
- Branch: \`main\` only. No branch was created.
- Scope: MIG-05 schema-v2 runtime interoperability, durable Leader epoch-floor preservation, candidate bundle format versioning.

### Design gap identified

The previous candidate bundle carried the legacy Coordinator Leader epoch only in \`recovery_requirements\`, while writing \`state_template.coordinator.leader = None\`. The existing runtime's default \`claim_leadership()\` derives its next epoch from the aggregate's current Leader record. If no caller separately supplies an external recovery floor, that state would permit a new Leader to start from epoch 1, losing the persisted legacy epoch floor. The migration contract now preserves the floor in the runtime aggregate itself.

### Code changes

- \`scripts/spare_parts_sqlite_candidate_importer.py\` now emits a canonical inactive historical marker only when the legacy epoch floor is greater than zero:
  - \`leader_id = "migration-epoch-floor"\`
  - \`epoch = legacy epoch floor\`
  - \`expires_at = 0.0\`
  - \`backend_lease_id = 0\` (no Lease; does not alias a valid cluster Lease ID)
- For a legacy epoch floor of zero, \`coordinator.leader\` remains \`None\`, so the first normal claim remains epoch 1.
- The old Leader identity and native TTL key are not imported. No native Lease is granted for the marker.
- \`scripts/spare_parts_sqlite_candidate_import_plan.py\` accepts only the exact inactive marker, validates all fields and the recovery metadata, and rejects any other Leader payload.
- \`scripts/spare_parts_provider_unified_coordinator_authority.py\` accepts \`backend_lease_id=0\` only for the exact \`migration-epoch-floor\` marker with \`expires_at=0.0\`; all actual Leader records still require a positive native Lease ID.
- Candidate bundle format was bumped from \`ch17-sqlite-unified-candidate-v1\` to \`ch17-sqlite-unified-candidate-v2\`. The planner rejects old v1 bundles; v1 candidate bundles must be rebuilt from a fresh read-only Inventory/Export.
- Runtime interoperability test in \`tests/test_spare_parts_sqlite_staged_import_execution.py\` publishes the candidate in the isolated in-memory namespace, reopens it through standard Unified Admission/Coordinator constructors, checks scope high-water/operation sequence and COMMITTED operation history, verifies terminal request replay is rejected without creating an Admission Lease, and claims a new Leader without passing a recovery floor to verify epoch 8 advances to epoch 9.
- Importer test verifies epoch-zero legacy source state does not create a floor marker. Planner test verifies a stale v1 candidate bundle is rejected.
- Representative commits: \`d2adcff46a6e4d4d30393682bda6b8af2ea8356e\` (zero no-Lease marker in candidate), \`8af2204601248443c127e2bcf4df336fa71b7cb0\` (planner validation), \`264e4ca8cadcba26d149f5e1f6a6388de5ae3325\` (runtime marker validation), \`18f9f6f55d72a227e8ae13ca5e314298ce7bda4c\` (stale-v1 rejection test).

### Validation

- [Knowledge Quality Run 46092944936](https://github.com/rexyll/cnc-knowledge/actions/runs/46092944936): success.
- Full unittest suite: 604 tests discovered/run, 40 skipped, 564 passed.
- CH12 numerical resource tests: 143 passed.
- Knowledge lint: 0 errors / 5 warnings.
- Knowledge structure and data quality: 0 errors.
- The main quality job exercised the Leader-marker runtime interoperability test, epoch-zero mapping and legacy candidate-v1 rejection test.

### Documentation

- Updated root \`TaskPlan.md\`, chapter \`docs/TaskPlan/17-operation-maintenance-and-repair/TaskPlan.md\`, chapter README and \`sqlite-to-unified-coordinator-migration-design.md\`.
- MIG-05 remains IN_PROGRESS: runtime-schema interoperability and epoch floor continuity are now partially verified; external Provider fencing, broader TTL/fencing scenarios and real-etcd tests remain outstanding.
- MIG-04 remains IN_PROGRESS; MIG-06 remains TODO; MIG-07 remains BLOCKED.

### Safety boundary

- All Round80 runtime integration was executed against \`InMemoryEtcdV3Client\`, not a real etcd cluster. The test's new Leader claim uses only a fake in-memory Lease.
- No real etcd Range/Txn/Lease write, real Lease Grant/Revoke, RBAC modification, production namespace access, application startup, candidate data import or production cutover occurred.
- ASSET-000092 remains \`PROPOSED_NOT_APPROVED / NOT_RUN\`; production Unified schema-v2 remains the sole authority.


## CNC Knowledge Base — Round 81

- Repository: \`rexyll/cnc-knowledge\`
- Branch: \`main\` only; no branch created.
- Scope: MIG-05 external Provider fencing floor reconciliation, read-only fail-closed validator.

### Code changes

- Added \`scripts/spare_parts_sqlite_provider_fencing_reconciliation.py\`.
- Added \`tests/test_spare_parts_sqlite_provider_fencing_reconciliation.py\`.
- Validator accepts only candidate format \`ch17-sqlite-unified-candidate-v2\` and a fixed read-only evidence schema.
- Evidence must identify the Provider and include an observation timestamp and an exact scope map matching all candidate scopes.
- Per scope, Provider generation must exactly match the candidate generation. Observed Provider fencing high-water token and operation sequence must each be less than or equal to the corresponding candidate floor.
- If a Provider floor exceeds the candidate floor, validation fails and requires rebuilding the candidate from reconciled source data; it never silently lowers Provider state or mutates the candidate.
- Evidence older than 300 seconds or from the future is rejected by default; malformed fields, unknown fields, missing/extra scopes, generation mismatch and invalid numeric floors fail closed.
- Successful output includes canonical evidence SHA-256 and per-scope comparisons, but both \`application_activation_authorized\` and \`provider_operations_authorized\` remain false.
- Added seven tests covering fresh success, missing scope, higher token floor, higher operation sequence, generation mismatch, stale/future evidence and unknown schema.

### Validation

- [Knowledge Quality Run 46094890151](https://github.com/rexyll/cnc-knowledge/actions/runs/46094890151): success.
- Full unittest suite: 611 tests run, 40 skipped.
- CH12 numerical resource tests: 143 passed.
- Knowledge structure/data checks: 0 errors.
- Fixture lint: 0 errors / 5 warnings.

### Documentation

- Updated root \`TaskPlan.md\`, CH17 TaskPlan, CH17 README and SQLite-to-Unified migration design.
- MIG-05 remains IN_PROGRESS: this validates supplied Provider floor evidence only; evidence authenticity, trusted Provider sampling, continuous freeze, and runtime enforcement are still outstanding.
- MIG-06 remains TODO; MIG-07 remains BLOCKED.

### Safety boundary

- No real Provider was queried; evidence was synthetic unit-test input.
- No Provider control object was written, no generation/fencing floor was changed, no etcd Lease or RBAC was touched, no application access was enabled, and no production cutover occurred.
- The 300-second freshness check is only a timestamp policy; it does not prevent Provider mutation after observation. The result is not a signature, trust attestation or production authorization.
- ASSET-000092 remains \`PROPOSED_NOT_APPROVED / NOT_RUN\`; production Unified schema-v2 remains the sole authority.



## CNC Knowledge Base — Round 82

- Repository: `rexyll/cnc-knowledge`
- Branch: `main` only; no branch created.
- Scope: MIG-05 Ed25519 signature verification for external Provider fencing evidence.

### Code changes

- Added `scripts/spare_parts_sqlite_provider_fencing_signed_evidence.py`.
- Added `tests/test_spare_parts_sqlite_provider_fencing_signed_evidence.py`.
- The signed envelope and trust-store schemas are exact and reject unknown fields.
- Signature verification uses Ed25519 over a domain-separated prefix plus canonical JSON for the complete evidence object.
- Only after signature verification succeeds does the wrapper invoke the existing read-only reconciliation validator; freshness, complete scope coverage, Provider generation and fencing/operation floors remain mandatory.
- The result reports signature verification, signer key ID and trust-store SHA-256. Application activation and Provider operation authorization remain false.
- Tests cover valid signature, tampered evidence, unknown signer, invalid signature/algorithm, malformed Base64, unknown schema, stale evidence and Provider floor above candidate.

### Validation

- CI for the code and documentation commits is pending; do not treat this round as accepted until the required main-branch workflow runs complete successfully.

### Safety boundary

- The trust store is caller-supplied; this verifier does not establish its provenance, approval or secure distribution.
- A signature authenticates a snapshot only. It does not prove continuous Provider freeze or prevent post-sample mutation.
- No durable nonce/evidence replay ledger is implemented; a still-fresh signed snapshot may be replayed.
- No real Provider/KMS was contacted; no Provider control record, etcd Lease, RBAC, application access or production namespace was changed. No candidate was imported and no production cutover occurred.
- ASSET-000092 remains `PROPOSED_NOT_APPROVED / NOT_RUN`; production Unified schema-v2 remains the sole authority.

### Round 82 code validation (documentation synchronization pending final CI)

- [Knowledge Quality Run 46096035428](https://github.com/rexyll/cnc-knowledge/actions/runs/46096035428): success; the run includes both Round82 signed-evidence code and tests.
- Full unittest suite: 618 tests run, 40 skipped (578 passed).
- Both required jobs completed successfully, including CH12 numerical resource tests and Knowledge structure/data quality.
- The run's tested commit predates the final documentation synchronization commits; a final-main validation is being triggered separately.
