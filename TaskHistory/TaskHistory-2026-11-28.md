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



## CNC Knowledge Base — Round 83

- Repository: \`rexyll/cnc-knowledge\`
- Branch: \`main\` only; no branch created.
- Scope: MIG-05 Provider freeze attestation binding and single-host durable replay prevention reference.

### Code changes

- Added \`scripts/spare_parts_sqlite_provider_freeze_attestation.py\` and its dedicated unittest module.
- Added a reusable Ed25519 signed-payload verifier and retained the existing signed-snapshot validation behavior.
- Freeze claims bind Provider ID, freeze ID/generation, UUID evidence ID, one-time Coordinator challenge nonce, freeze/signature time window, Coordinator Leader ID/epoch/native Lease ID/expiry and the full Provider scope floors.
- Validation compares claims to a fresh caller-supplied Coordinator snapshot (default maximum age 5 seconds), requires exact per-scope floor equality with Coordinator authority, and still enforces the 300-second Provider evidence freshness and candidate floor limits.
- Added \`SQLiteProviderFreezeEvidenceReplayLedger\`: mode-0600 single-host SQLite reference ledger, FULL synchronous durability, BEGIN IMMEDIATE atomic consumption and uniqueness constraints for Provider/evidence ID, challenge nonce and freeze ID/generation. Evidence is consumed only after all validation succeeds.
- Failed validation does not consume evidence IDs. Ledger errors fail closed.
- Explicit output flags remain false for actual Provider write-freeze enforcement, application activation and Provider operations.

### Validation

- [Knowledge Quality Run 46108172706](https://github.com/rexyll/cnc-knowledge/actions/runs/46108172706): success on the complete Round83 implementation and documentation commit.
- Full unittest suite: 628 tests run, 40 skipped (588 passed).
- CH12 numerical resource tests: 143 passed.
- Knowledge lint: 0 errors; fixture lint: 0 errors / 5 warnings.
- Synthetic scenario replay: 30 simulated, 0 failed; external connections and writes were disabled.
- Both required GitHub Actions jobs completed successfully.

### Safety boundary

- The freeze assertion is signed, but this offline tool does not inspect or block the real Provider write paths; it does not prove that all mutation routes honor the asserted native gate.
- The Coordinator snapshot is caller-supplied; real integration must read it from an authenticated, fresh, linearizable Coordinator authority.
- SQLite ledger is single-host only; it provides no multi-host consensus and can be reset by restoring a trusted old database backup. Production must use a shared durable linearizable replay ledger, such as an isolated etcd CAS/Txn design, with nonce issuance and consumption tied to the same authority lifecycle.
- No real Provider/KMS/etcd was contacted, no Provider control object, RBAC, Lease or production namespace was changed, no application access was enabled, and no candidate import/cutover occurred.
- ASSET-000092 remains \`PROPOSED_NOT_APPROVED / NOT_RUN\`; production Unified schema-v2 remains the sole authority.



## CNC Knowledge Base — Round 84

- Repository: `rexyll/cnc-knowledge`
- Branch: `main` only; no branch created.
- Scope: MIG-05 shared etcd CAS/Txn replay ledger candidate integrated with signed Provider freeze attestation.

### Code changes

- Added `scripts/spare_parts_provider_freeze_etcd_replay_ledger.py`.
- Added `tests/test_spare_parts_provider_freeze_etcd_replay_ledger.py`.
- Added `EtcdProviderFreezeEvidenceReplayLedger` using the existing CoordinatorAuthorityStore linearizable Get/Txn interface.
- The ledger accepts only a single-segment isolated migration namespace and rejects the production Unified namespace.
- Each consumption atomically creates four permanent uniqueness keys: Provider evidence UUID, challenge nonce digest, freeze generation and freeze ID.
- The same Txn compares exact VALUE and MOD revision for `scheduler/state` and the native-lease-attached `coordinator/leader` key. The adapter pre-reads and checks Leader ID/epoch/Lease attachment/expiry and exact per-scope floors against the signed snapshot.
- Integrated with `validate_provider_freeze_attestation()`; SQLite replay ledger remains a same-host reference implementation.
- Unknown Txn outcome is resolved only by exact read-back of all four records or retrying the exact same Txn after proving all four keys absent and rechecking authority. Partial/conflicting state is quarantined.
- Tests cover end-to-end signed claim consumption, single-winner concurrent use, unknown commit response, known-not-committed retry, aggregate CAS race, scope drift, partial ledger state and namespace rejection.

### Validation

- An initial negative-test run exposed only an exception normalization mismatch for invalid isolated namespaces; the ledger now wraps `MigrationNamespaceError` as `ProviderFreezeReplayLedgerError`.
- [Knowledge Quality Run 46114881253](https://github.com/rexyll/cnc-knowledge/actions/runs/46114881253): success for the complete Round84 code and documentation state.
- Full unittest suite: 639 tests run, 40 skipped (599 passed).
- CH12 numerical resource tests: 143 passed.
- Knowledge lint: 0 errors; fixture lint: 0 errors / 5 warnings.
- Synthetic scenario replay: 30 simulated, 0 failed; external connections and writes were disabled.
- Both required GitHub Actions jobs completed successfully.

### Safety boundary

- Tests use `EtcdV3CoordinatorAuthorityStore` + `InMemoryEtcdV3Client`; they are not evidence of real etcd cluster consensus, disk durability, multi-host failures or server-side RBAC.
- SQLite replay remains single-host only. The etcd implementation is a candidate over the generic store port, not a connected production service.
- No real etcd, Provider, KMS or external service was contacted; no RBAC/Lease/provider-control state was mutated outside the in-memory fake; no application access, candidate import or production cutover occurred.
- `provider_write_freeze_enforced`, application activation and Provider operations authorization remain false.
- ASSET-000092 remains `PROPOSED_NOT_APPROVED / NOT_RUN`; production Unified schema-v2 remains the sole authority.


## CNC Knowledge Base — Round 85

- Repository: `rexyll/cnc-knowledge`
- Branch: `main` only; no branch created.
- Scope: Provider-native persistent write-freeze gate for the existing SQLite fenced Provider reference.

### Code changes

- Added `scripts/spare_parts_provider_write_freeze_gate.py`, a domain-separated Ed25519 FREEZE/UNFREEZE command envelope bound to issuer, Provider ID, tenant, scope, freeze ID, monotonic generation and short validity window.
- Extended `scripts/spare_parts_provider_sqlite_fenced.py` with optional Provider identity, persistent `provider_write_freeze_scopes`, `apply_write_freeze_command()` and read-only `write_freeze_state()`.
- Provider schema upgraded from v2 to v3. Existing v2 DBs receive an additive migration; backup validation requires the v3 freeze-state table, and backup/restore preparation retains the freeze state.
- Object fenced PUT, multipart begin, part and complete now inspect the gate and write-proof generation inside the same existing `BEGIN IMMEDIATE` transaction.
- FREEZE/UNFREEZE must advance exactly one generation. UNFREEZE must match the active freeze ID. Exact command replay is idempotent; stale, skipped, conflicting, wrong-tenant/provider, wrong-freeze-ID or invalid-signature commands fail closed.
- After unfreeze, all mutation proofs must include the current `provider_freeze_generation`; old proofs cannot resume writes. Read paths remain available; unfenced mutations and unfenced multipart abort remain disabled.
- Added tests for all mutation paths, command signature and monotonicity, stale proof rejection, transaction ordering race, schema v2 migration, Provider restart, and backup/restore persistence.

### Validation

- [Code quality Run 46133032641](https://github.com/rexyll/cnc-knowledge/actions/runs/46133032641): both required jobs succeeded after the test fixture's expected restore-preparation result was corrected.
- [Final documentation quality Run 46133257782](https://github.com/rexyll/cnc-knowledge/actions/runs/46133257782): both required jobs succeeded on the complete code, plan, README, migration-design and TaskHistory state.
- Full unittest suite: 645 tests run, 40 skipped (605 passed).
- CH12 numerical resource tests: 143 passed.
- Knowledge lint: 0 errors; fixture lint: 0 errors / 5 warnings.
- Synthetic scenario replay: 30 simulated, 0 failed; external connections and writes were disabled.
- Provider freeze tests additionally cover all four mutation entrypoints, signed command replay/monotonicity, old proof rejection after unfreeze, SQLite transaction race ordering, v2-to-v3 additive migration, restart, and backup/restore persistence.

### Safety boundary

- This is a same-host SQLite reference gate, not a remote Provider Gateway or cloud object-store enforcement proof.
- No real Provider, KMS/HSM, etcd, cloud object store or IAM/RBAC service was contacted; no production control object or authority was changed.
- The offline freeze attestation verifier still reports `provider_write_freeze_enforced=false`; it does not inspect this local fixture or establish production freeze status.
- No candidate import, application activation or production cutover occurred. ASSET-000092 remains `PROPOSED_NOT_APPROVED / NOT_RUN`; production Unified schema-v2 remains the sole authority.


## CNC Knowledge Base — Round 86

- Repository: rexyll/cnc-knowledge
- Branch: main only; no branch created.
- Scope: Provider-native freeze command durable receipts and lost-response recovery in the same-host SQLite reference.

### Code changes

- Freeze command digest now covers the complete canonical signed envelope, including key ID and signature, rather than claims alone.
- Added provider_write_freeze_commands, keyed by the full-envelope SHA-256 and recording issuer/key, Provider/tenant/scope, action, freeze ID, generation, historical result state and applied timestamp.
- Command receipt insertion and provider_write_freeze_scopes generation/state update occur in the same BEGIN IMMEDIATE transaction.
- apply_write_freeze_command() checks the trusted key registry and then resolves a historical receipt before checking current generation. Replaying any previously committed exact envelope returns ALREADY_APPLIED with its historical result and current scope state; it never re-applies an old FREEZE/UNFREEZE.
- Added read-only write_freeze_command_status() to query historical receipt and current scope state by exact envelope digest. Receipts persist across restart and backup/restore.
- Added tests for FREEZE→UNFREEZE→historical FREEZE replay (current state remains OPEN), history/current-state distinction, unknown and malformed digests, and receipt persistence through restart and backup/restore.

### Validation

- CI validation pending; do not treat this round as accepted until required main-branch workflows complete successfully.

### Safety boundary

- This remains a same-host SQLite reference implementation. A missing local receipt does not prove that an unknown remote network request never committed.
- Production Coordinator recovery still requires an authenticated, linearizable Provider receipt-query endpoint and defined retry/quarantine rules; this change does not provide remote multi-replica consistency.
- No real Provider, KMS/HSM, etcd, cloud object store or IAM/RBAC service was contacted. No production control object, application access, candidate import or cutover was changed. ASSET-000092 remains PROPOSED_NOT_APPROVED / NOT_RUN; production Unified schema-v2 remains the sole authority.

## CNC Knowledge Base — Round 87

- Repository: rexyll/cnc-knowledge
- Branch: main only; no branch created.
- Scope: bind Provider-native freeze commands to signed Coordinator Leader identity, epoch, native Lease ID and Lease expiry.

### Code changes

- Upgraded freeze command envelope/claims/signature domain to v2. Claims strictly require coordinator_namespace, leader_id, positive leader_epoch, positive leader_lease_id, and leader_lease_expires_at_unix.
- Provider rejects expired Leader Lease declarations and commands whose expiry exceeds the declared Leader Lease expiry.
- Upgraded SQLite Provider schema to v4 with additive provider_write_freeze_leader_floors and provider_write_freeze_command_leaders tables.
- Provider persists a per-tenant/scope Coordinator namespace and highest observed Leader epoch. Lower epochs are rejected; same-epoch Leader ID or native Lease changes are rejected; namespace changes are rejected.
- A higher epoch can take over the next freeze generation, including matching UNFREEZE of the active freeze ID.
- Freeze scope update, durable command receipt, Leader epoch floor and command-Leader audit row are written in one BEGIN IMMEDIATE transaction. Rejected commands do not advance floors.
- Exact historical command receipt lookup remains ahead of Leader epoch checks; replay returns the historical result without reapplying the old command.
- Added tests for stale epoch rejection after observing a new Leader, same-epoch identity/Lease mutation, namespace drift, command expiry beyond Lease expiry, already-expired Lease, and v3-to-v4 additive migration. Updated v2 migration and backup/restore expectations.

### Validation

- [Provider code and test quality run 46137931408](https://github.com/rexyll/cnc-knowledge/actions/runs/46137931408): success.
- [Final Round87 documentation/history quality run 46137972275](https://github.com/rexyll/cnc-knowledge/actions/runs/46137972275): both required jobs succeeded.
- Full unittest suite: 653 tests run, 40 skipped (613 passed).
- CH12 numerical resource tests: 143 passed.
- Knowledge lint and repository structure/data checks: 0 errors; fixture lint retains 5 existing warnings.
- The CI run before final history synchronization also exercised the complete Round87 code and migration tests; final history synchronization is validated separately by the run above.

### Safety boundary

- The Provider validates a signed Lease-expiry assertion; it does not query live etcd Lease existence, Leader-key attachment, or early revocation.
- Before the Provider observes a higher epoch, an old Leader can still be accepted within the signed command/Lease validity window if its Lease was revoked early. Production requires a linearizable online Leader/Lease status check at the Provider or an equivalent independently revocable authorization mechanism.
- Same-host SQLite tests do not establish etcd consensus, remote Provider behavior or multi-host consistency. No real etcd, Provider, KMS/HSM, cloud object store or IAM/RBAC service was contacted; no production application access, candidate import or cutover occurred. ASSET-000092 remains PROPOSED_NOT_APPROVED / NOT_RUN; production Unified schema-v2 remains the sole authority.

- Additional hardening: Coordinator namespace must be a canonical absolute prefix; within the same Leader epoch and native Lease ID, a lower Lease-expiry snapshot is rejected. Tests cover both conditions.

- Backup validation now requires all four freeze/receipt/Leader-floor/audit tables; backup/restore tests assert the persisted Leader epoch and native Lease binding survive restore.

## CNC Knowledge Base — Round 88

- Repository: `rexyll/cnc-knowledge`
- Branch: `main` only; no branch created.
- Scope: Provider Freeze online Coordinator Leader/native Lease verification.

### Code changes

- Added `scripts/spare_parts_provider_live_leader_status.py` with `EtcdCoordinatorLeaderStatusChecker`.
- The checker uses one existing `linearizable_range(namespace_prefix)` call to observe Scheduler aggregate and Coordinator Leader TTL key at the same etcd revision.
- It verifies exact aggregate/key agreement, Leader ID, epoch, native Lease ID, etcd KV Lease attachment, and matching non-expired Lease expiry.
- Added Provider opt-in `leader_status_checker` and `require_online_leader_status=True`. New FREEZE/UNFREEZE commands fail closed when the online check reports inactive or unavailable. Missing checker configuration is rejected at Provider construction.
- Exact historical command receipts are still resolved before online status checks; replay returns `ALREADY_APPLIED` without reapplying the historical command.
- Added `tests/test_spare_parts_provider_live_leader_status.py` and Provider command-path tests for missing checker, revoked/unknown status, network failure and historical receipt precedence.
- Added `docs/17-operation-maintenance-and-repair/provider-online-coordinator-leader-verification.md`.

### Validation

- [Final main-branch CI Run 46139767853](https://github.com/rexyll/cnc-knowledge/actions/runs/46139767853): both required jobs succeeded. Full unittest suite: 663 run, 40 skipped (623 passed); CH12 numerical resource tests: 143 passed; knowledge lint: 0 errors / 5 warnings; repository structure/data checks: 0 errors.
- Test doubles are synthetic. No live etcd or remote Provider was contacted.

### Safety boundary and remaining gap

- The linearizable Range proves the Leader key and aggregate matched at the read revision, and verifies the key's native Lease attachment.
- The etcd read and Provider SQLite commit are not one distributed transaction. A Lease can still be revoked after the Range and before the local SQLite commit. This change reduces the stale-command window but does not eliminate cross-system TOCTOU and must not be described as atomic fencing or real-time validity at commit.
- No real etcd, Provider, KMS/HSM, cloud object store or IAM/RBAC was contacted; no production namespace or authority was changed, no candidate data was imported, no application activation or cutover occurred.
- ASSET-000092 remains `PROPOSED_NOT_APPROVED / NOT_RUN`; production Unified schema-v2 remains the sole authority.


## CNC Knowledge Base — Round 89（架构设计进行中）

- Repository: `rexyll/cnc-knowledge`
- Branch: `main` only; no branch created.
- Scope: Provider revocable authorization and revocation-barrier architecture after the Round 88 cross-system TOCTOU finding.

### Changes

- Added `docs/17-operation-maintenance-and-repair/provider-revocation-barrier-architecture.md`.
- Distinguished Coordinator Leader validity from Provider mutation authorization.
- Compared a single transactional authority, Provider-native conditional writes, Provider-participating FENCE barrier, and online Range-only checks.
- Proposed Provider-side grant/epoch floor as the final mutation gate; FENCE and protected mutations must share the Provider transaction or native conditional-write boundary; durable command receipt is required before new-epoch grant activation.
- Explicitly defined Provider FENCE commit as the Provider-side revocation linearization point. It is not atomic with the physical expiry/revocation instant of an independent etcd Lease.
- Synchronized root TaskPlan, CH17 TaskPlan, CH17 README and migration design with the Round 89 architecture decision task.

### Status / validation

- Architecture document and all plan/README/migration-design/history indexes synchronized on main. Latest documentation commit: `f405f1223421c73485feaac8543cf06401c0e9fa`. Branch verification shows `main` only. Combined commit status currently reports no checks; required CI result is not yet available, so Round 89 is not marked DONE.
- This round is design only. No grant/FENCE writer, real etcd/Provider/KMS/HSM integration, RBAC change, production namespace access, candidate import, application activation or cutover occurred.
- MIG-04 remains IN_PROGRESS; MIG-05 remains IN_PROGRESS; MIG-06 TODO; MIG-07 BLOCKED.
- Production Unified schema-v2 remains the sole authority; ASSET-000092 remains `PROPOSED_NOT_APPROVED / NOT_RUN`.


## CNC Knowledge Base — Round 90（Provider grant/FENCE 本地参考实现进行中）

- Repository: `rexyll/cnc-knowledge`
- Branch: `main` only; no branch created.
- Scope: implement a same-host SQLite Provider reference for Provider-native revocable grants and FENCE barrier.

### Code changes

- Added `scripts/spare_parts_provider_revocable_grant.py`: domain-separated Ed25519 FENCE/ACTIVATE command envelope and strict claims validation.
- Extended `scripts/spare_parts_provider_sqlite_fenced.py`: Provider schema v6; additive grant state and durable command receipt tables with canonical signed envelope and signer public key retained; changing Leader/Lease identity requires a strictly newer Coordinator Leader epoch, while the exact same Leader/Lease may self-FENCE an ACTIVE grant for renewal/rotation; ACTIVATE requires an exact persisted FENCE receipt and matching namespace/Leader/Lease/grant identity.
- Added optional `require_revocable_grant=True`. When enabled, Provider construction requires Provider ID, an Ed25519 command trust key and an online Coordinator Leader checker; object PUT and multipart begin/part/complete proofs must include signed Grant ID/generation, checked in each actual Provider BEGIN IMMEDIATE mutation transaction. The online check gates FENCE/ACTIVATE commands but remains separate from SQLite commit; inactive/unavailable status fails closed without creating grant state.
- FENCE permits same-epoch self-revocation only when the exact same Leader ID/native Lease remains current and ACTIVE; an identity change still requires a strictly higher epoch. FENCE IDs cannot be reused, FENCED scopes cannot be fenced repeatedly, and same-epoch Lease expiry cannot regress. Added a same-Leader grant rotation test.
- Grant mode now fails Provider construction unless Provider identity, an Ed25519 command trust key and an online Coordinator Leader checker are all configured. Added tests for missing trust configuration and inactive Leader fail-closed; implementation/test commits `8024b82c6aba3141b2ebf0f0fc3cc36159444881`, `0c634567ca72ed503efd4c69277b2f6069d31a03`, `eb3d84c4f2bf453133fd870e37aa4c3d55acb44e`.
- Added receipt chronology enforcement: ACTIVATE `issued_at_unix` must not predate the FENCE Provider receipt's persisted `applied_at`; a pre-signed early ACTIVATE is rejected. Added schema v4→v6 and v5→v6 migration coverage; schema v6 adds canonical envelope/public-key columns and cryptographically re-verifies every retained FENCE/ACTIVATE signature during backup validation. Legacy v5 receipts without those fields fail closed for mutation and backup validation. Generic restore now refuses any backup containing Provider Grant scope or command history because no independent Grant generation/Leader epoch floor is currently supplied.
- Added same-Leader grant rotation, pre-issued ACTIVATE rejection and schema v4 migration tests: `bf938e779990de5e76b8d3972d0857cd779ddd31`, `548e350e7d72d68e50d4fe03d1f092365543d118`. The early backup/restore test assumption was superseded by the explicit generic Restore block without an external Grant floor.
- Added receipt lookup by exact envelope SHA-256, including lost-response recovery without reapplying a generation.
- Hardened SQLite commit-time validation: Freeze/Unfreeze and Grant command apply APIs no longer accept caller-supplied `now_unix`; signed command and key time windows are revalidated after acquiring `BEGIN IMMEDIATE` and again after online Leader verification. Grant integer claims are bounded to SQLite signed 64-bit values.
- Generic restore hardening commit `8dc762d66837c6a8a12519ca35d43493c7a4a0ce` blocks any backup containing Provider Grant scope or command history until an independent Grant generation/Leader epoch floor is reconciled; test `3e6a5b7bf07754fc506ae56481e86587c118dc15` confirms fail-closed behavior and no destination DB is created.
- Freeze/Unfreeze caller-clock removal and post-lock/online-check expiry revalidation: code `3e01d49feb45a74b641718d8055347247dbcade3`, regression test `443ab80906820e6fb8e59134ab2b17f7e425787f`, Lease expiry floor test update `5c5c3624553607ebffe1966d73054d6ced3b8d91`.
- Bound current Provider grant scope to its FENCE receipt's Provider ID at both ACTIVATE/FENCE transition and actual mutation gate; a different Provider identity cannot reuse the same SQLite scope.
- Backup validation now requires the Ed25519 trust registry and validates every FENCE/ACTIVATE receipt chain and the current scope state against durable receipts. Added tests for caller-clock injection, lock-wait expiry, active-grant expiry, integer overflow, cross-Provider reuse and tampered backup receipt chains.
- Schema v6 receipt integrity commits: original envelope/public-key persistence `d9531f7acaa7dff1b077fcdfd75ef53f56944547`; corrected placement on the Grant receipt table `5e709e696427358f18b83ddf02e52191cf33cee2`; offline Ed25519 backup re-verification `4e9c48144640932f8e98acadd55f7ef7e291b740`; runtime receipt verification at mutation gate `f8314cde81bc6cbbd62c94ade3323ed8bd93fc98`, state/identity consistency `608d236700e0471e2b04194d956f8465cd44a80c`; status payload redaction `dbd3160faab926e27c4d2dad09901c132360a045`.
- Schema v6 test commits: v5 migration `a8a282357a3417000b911e4afae53589a29c8007`; persisted signature tamper at backup `0f8357cd5269686c109e88d25a79b69de1ae5024`; runtime mutation gate signature tamper `dbbf37cfd42e7b6d9c653e52d5e8bb70fd082229`; duplicate test cleanup `4a1ba3471a0dc9dada99908b883cc4742c412607`; v5 legacy receipt fail-closed `156ebc5d4118cb14dbe44d384a9919b603129ffe`.
- Extended Provider tests for missing/early FENCE receipt, activation, newer-epoch revocation of the old grant, same-Leader grant rotation, cross-Provider identity rejection, all four mutation entrypoints, post-commit response loss, backup-chain and Ed25519 signature integrity, runtime rejection of a tampered persisted ACTIVATE receipt, legacy v5 receipt fail-closed migration, generic restore refusal without an external Grant floor, transaction ordering, and v2/v3/v4/v5 additive schema migration.

### Validation / safety boundary

- Additional hardening commits: SQLite-safe signed integer bounds `0bd80b2b79700718dfcd778e96ec8df1bd091652`, provider command time revalidation after lock and online read `1bba4efe6bbec62b4a06d70eab4de0f1c9b6a75e`, required Ed25519 trust table and backup receipt-chain checks `4f6ba70bdf5051844f66d973db27bea9d7e95286`, `a8b82ca21f6fe54f49c2137de8ea92cdf76a0ff4`, plus follow-up validation fixes `1dbe93bdc46e8d9b8832aed1ae5c69ea48a7ef9f`, `1fec83f69d727448b2afb4d400d6ce37838c4e19`.
- Additional tests: caller clock and integer overflow `b6824c8c5a4264c266d2a7e51740f7ed9206f138`, `52cf7e0647baf3f412101687705a2b1a90c346c8`; lock-wait expiry and Provider scope identity `481947fd7393eb32ec9cecfcb8462cc182997fa7`, `8145cb7204da6ae1fe8d4b413c3b722f644386c0`; grant expiry and backup chain/trust registry `b225a4c8764bd5b5e45cdef718605152a5978de4`, `be11f022459927e676f57d3166170f45b62bd7e9`, `86c0c7d91fbcfe314f3918dcc2f7cf81280999fd`; Freeze/Grant API clock removal `deeba02bcc9815c04834402b3fd7602992ca7670`, `3e01d49feb45a74b641718d8055347247dbcade3`, regression tests `5c5c3624553607ebffe1966d73054d6ced3b8d91`, `443ab80906820e6fb8e59134ab2b17f7e425787f`.
- Repository readback shows 68 test method definitions in `tests/test_spare_parts_provider_sqlite_fenced.py`; this is a source inventory only, not an execution result.
- Grant command/ACTIVE grant validity cap reduced from 24 hours to 300 seconds; this bounds, but does not eliminate, the residual old-Grant window when an etcd Lease is revoked early and Provider FENCE delivery is delayed. Added over-five-minute rejection test. Implementation `5d315ffd11dd469344ff0906652014620ca9b5e0`; test `79c4074dd47a11f5b8c5f46fa4127b5517c37e03`.
- Schema v6 hardening commits: canonical envelope/public-key persistence `d9531f7acaa7dff1b077fcdfd75ef53f56944547`; DDL correction `5e709e696427358f18b83ddf02e52191cf33cee2`; backup Ed25519 re-verification `4e9c48144640932f8e98acadd55f7ef7e291b740`; runtime gate receipt verification `f8314cde81bc6cbbd62c94ade3323ed8bd93fc98`, chain consistency `608d236700e0471e2b04194d956f8465cd44a80c`; schema v5 migration `a8a282357a3417000b911e4afae53589a29c8007`; backup-signature tampering and runtime-signature tampering tests `0f8357cd5269686c109e88d25a79b69de1ae5024`, `dbbf37cfd42e7b6d9c653e52d5e8bb70fd082229`; legacy v5 receipt fail-closed test `156ebc5d4118cb14dbe44d384a9919b603129ffe`. The working container cannot resolve `github.com`, so no local checkout/test execution was possible. `get_commit_combined_status` returned no status entries and the available commit-workflow lookup exposes PR-triggered runs only; no push-run result was obtained. Do not mark Round 90 DONE until the unit suite and Knowledge Quality workflow complete successfully.
- This is a same-host SQLite reference only. No real etcd, remote Provider, KMS/HSM, cloud object store or IAM/RBAC was contacted; no production namespace, candidate import, application activation or cutover occurred.
- MIG-04 remains IN_PROGRESS; MIG-05 remains IN_PROGRESS; MIG-06 TODO; MIG-07 BLOCKED. Production Unified schema-v2 remains the sole authority; ASSET-000092 remains `PROPOSED_NOT_APPROVED / NOT_RUN`.


## CNC Knowledge Base — Round 91（Provider Grant 外部 Floor / Restore 对账设计中）

- Added docs/17-operation-maintenance-and-repair/provider-grant-external-floor-and-restore-reconciliation-design.md.
- Captured the Grant backup rollback gap: a valid SQLite backup can still be stale because Provider grant generation, Leader epoch and receipt history currently live only inside that backup domain.
- Designed the ProviderGrantFloorAuthority contract, per-provider/tenant/scope monotonic floors, FENCE/ACTIVATE external reservation and receipt-confirmation protocol, and a dedicated fail-closed Grant-aware Restore algorithm.
- Explicitly retained the Round90 generic Restore block for any backup containing Provider Grant scope or command history. A text reconciliation reference or object fencing token floor is not sufficient Grant floor evidence.
- Synchronized root TaskPlan, CH17 TaskPlan, README and migration design. This is architecture-only; no external floor adapter, production authority change, real etcd/Provider integration or Restore/Cutover occurred.


## CNC Knowledge Base — Round 92（Provider Grant 外部 Floor 本地参考实现进行中）

- Repository: rexyll/cnc-knowledge
- Branch: main only; no branch created.
- New module: scripts/spare_parts_provider_grant_floor.py
  - Added ProviderGrantFloorAuthority port base and immutable scope/snapshot/reservation/operation records.
  - Added separate-file SQLiteProviderGrantFloorAuthority schema v1. The adapter persists per Provider/tenant/scope generation and Leader epoch floors, Leader/native Lease identity, pending operation, exact command digest, Provider receipt digest and scope revision.
  - FENCE and ACTIVATE use BEGIN IMMEDIATE + scope-revision CAS. Pending operations prevent another generation reservation. ACTIVATE requires a confirmed FENCE and binds the latest FENCE command digest.
  - Exact operation ID replay returns the original reservation; operation ID reuse with a different command/scope/identity is rejected. Exact Provider receipt confirmation is idempotent; receipt replacement is rejected.
  - Leader epoch cannot regress; same epoch cannot change Leader/native Lease identity; Coordinator namespace is immutable after first use; same native Lease expiry cannot regress.
  - snapshot(minimum_revision=...) can detect a floor below a trusted external checkpoint. The SQLite authority cannot detect rollback of its own database snapshot.
- New tests: tests/test_spare_parts_provider_grant_floor.py, 20 test method definitions covering the state machine, CAS concurrency, unknown-operation restart lookup, exact receipt confirmation, epoch/namespace/Lease monotonicity, scope isolation, revision floor and file permissions. These definitions are a source inventory only; no claim of execution or pass result.
- Commits:
  - Initial adapter: f7c520ac6f1f2950b2e40a611f4b79d5627ca85f
  - Initial tests: 1c3943080ffed1a0279bdf095230336118477778
- Follow-up test-path correction: the pending-FENCE ACTIVATE rejection test now supplies a syntactically valid, unconfirmed FENCE digest so it reaches the intended state-machine branch. Commit: d2c7e7a6081a410bf1c38df01440898ffaf3ad8c.
- Clarified the critical state boundary: external FENCE_PENDING is only a reservation; the prior ACTIVE Grant can remain accepted until Provider FENCE actually commits. Provider-side FENCE remains the mutation revocation linearization point.
  - Namespace and Lease-expiry monotonicity hardening: 5311c20232af022cd36bb932a06001e2bde655b8
  - Additional regression tests: 3e848b2c1ffe66c41c033d6c78961b5ce4832c0a
- Documentation synchronized in root TaskPlan.md, CH17 TaskPlan, CH17 README, migration design and this history.
- Validation: get_commit_combined_status returned no status entries; the available commit-workflow lookup returned no workflow runs for the test commit. No local checkout/test execution was performed. Do not mark Round 92 or Round 90 DONE from source inventory.
- Safety boundary: this is a single-host SQLite reference, not etcd linearizable/quorum authority or production integration. The adapter stores Provider receipt digests but does not authenticate the receipt; a future Coordinator must verify an authenticated Provider status response. No Provider command path, Unified schema-v2 authority, real etcd/Provider/KMS/HSM, IAM/RBAC, production namespace, Restore, candidate import, application activation or Cutover was touched.
- Status: MIG-04 IN_PROGRESS; MIG-05 IN_PROGRESS; MIG-06 TODO; MIG-07 BLOCKED. Production Unified schema-v2 remains the sole authority; ASSET-000092 remains PROPOSED_NOT_APPROVED / NOT_RUN.

## CNC Knowledge Base — Round 93（Provider Grant Floor namespace 收敛与CI验收完成）

- Repository: `rexyll/cnc-knowledge`
- Branch: `main` only; no branch created.
- Scope: Restrict the local Provider Grant Floor reference adapter to isolated Coordinator namespaces and close the remaining test/receipt-validation defects found during full-suite CI.

### Code and test changes

- Restricted `SQLiteProviderGrantFloorAuthority._namespace()` to exactly `/cnc/migration/isolated/{single-id}/`; the single ID segment follows `[A-Za-z0-9][A-Za-z0-9._:-]{0,127}`. Validation occurs before a write transaction, scope creation, generation reservation or revision change.
- Added negative tests for Unified/production namespace prefixes, the isolated root without an ID, additional path levels, dot traversal, percent-encoded traversal and backslashes. Rejected inputs leave the scope IDLE and both scope/authority revisions unchanged.
- Updated namespace immutability coverage to use a second syntactically valid isolated ID; the established scope still rejects namespace replacement.
- Corrected the Floor test module import to the actual `ProviderGrantScopeKey` class. The pending-FENCE ACTIVATE case now asserts that pending operation state blocks a second reservation before confirmation.
- Fixed Provider ACTIVATE receipt lookup to select its durable command digest. Aligned persisted receipt and backup validation with the verifier's bounded five-second command clock-skew allowance while retaining signed-expiry enforcement.
- Adjusted the synthetic test command helper so its default grant expiry never exceeds the Coordinator native Lease expiry. The receipt-chain corruption test now removes the referenced FENCE receipt instead of editing a field covered by the ACTIVATE signature.

### Documentation and plans

- Added Round 93 namespace and receipt-validation details to `provider-grant-external-floor-and-restore-reconciliation-design.md`.
- Indexed the design document, adapter module and focused tests in CH17 README.
- Updated root TaskPlan and CH17 TaskPlan with Round 93 completion and Round 94 receipt-authentication design tasks.
- Added this Round 93 result record.

### Validation

- [GitHub Actions Knowledge Quality Run 46152883043](https://github.com/rexyll/cnc-knowledge/actions/runs/46152883043): both required jobs succeeded.
- Full repository unittest: 707 tests run, 40 skipped by environment guards; all non-skipped tests passed.
- CH12 numerical resource tests: 143 passed.
- Repository knowledge lint: 0 errors / 5 warnings; additional repository structure/data checks: 0 errors.

### Safety boundary / remaining gaps

- The SQLite adapter remains a same-host reference, not etcd linearizable KV/Txn, Raft quorum, multi-host HA or rollback-resistant storage. It cannot detect rollback of its own SQLite snapshot without a trusted checkpoint outside that database/backup domain.
- The adapter stores a Provider receipt digest but does not yet authenticate the receipt's origin. Round 94 will design a signed Provider receipt evidence contract and verifier trust model.
- FENCE_PENDING is only an external reservation; the Provider Grant remains usable until the Provider-native FENCE transaction commits. The Provider FENCE remains the mutation revocation linearization point.
- No real etcd, remote Provider, KMS/HSM, cloud object storage or IAM/RBAC was contacted; no production authority/namespace, candidate import, restore, application activation or Cutover was changed or executed. Generic Restore for any Provider Grant history remains fail-closed.
- MIG-04 IN_PROGRESS; MIG-05 IN_PROGRESS; MIG-06 TODO; MIG-07 BLOCKED. Production Unified schema-v2 remains the sole authority.


## CNC Knowledge Base — Round 94（Provider Grant 回执来源认证与签名证据设计完成）

- Repository: \`rexyll/cnc-knowledge\`
- Branch: \`main\` only; no branch created.
- Scope: Define a verifiable Provider-native signed receipt contract for external Provider Grant Floor FENCE/ACTIVATE reconciliation. This round is design-only; no runtime signer/verifier or production integration was implemented.

### Design deliverable

- Added \`docs/17-operation-maintenance-and-repair/provider-grant-receipt-authentication-design.md\` and indexed it in CH17 README and both TaskPlans.
- Defined a versioned Provider receipt envelope with strict claims for Provider ID, tenant, scope, FENCE/ACTIVATE action, Grant ID/generation, exact Coordinator command digest, result state, isolated namespace, Leader ID/epoch, native Lease ID/expiry, command issue/expiry and Provider applied time.
- FENCE receipt binds \`fence_command_sha256=null\`; ACTIVATE receipt must bind the exact latest confirmed FENCE command digest.
- Separated Coordinator command signing trust from Provider receipt signing trust. Proposed a Provider-controlled independent Ed25519 receipt key and an externally managed Provider/key trust registry with ACTIVE/RETIRING/REVOKED lifecycle, validity windows, fingerprint binding and trust revision.
- Specified domain-separated signature input and RFC 8785 JSON Canonicalization Scheme (JCS) for the new receipt envelope. The existing Coordinator command digest must continue to use the exact versioned canonicalization bytes that its current signature verifier accepts; implementations must not silently reserialize signed commands under a different canonicalizer.
- Defined receipt digest as SHA-256 of the complete verified canonical receipt envelope including signature. Naked caller-supplied digest must not be sufficient to promote a production Floor reservation.
- Described Provider same-transaction persistence of grant state, command receipt and signed receipt; remote KMS/HSM signing may use a durable RECEIPT_SIGNING_PENDING state, but unsigned success is never externally confirmable.
- Defined exact command-digest receipt lookup for lost-response recovery, immutable historical receipts, duplicate confirmation rules, FENCE/ACTIVATE state and chronology checks, fail-closed key revocation behavior, and the required receipt tamper/replay/cross-identity test matrix.
- Explicitly retained generic Restore fail-closed for any Provider Grant scope or command history. Receipt authentication alone is necessary but not sufficient for Grant-aware Restore.

### Validation

- [GitHub Actions Knowledge Quality Run 46153427280](https://github.com/rexyll/cnc-knowledge/actions/runs/46153427280): both required jobs succeeded on the design/plan commit \`8431d434f485a60ba2c94c25f617173930d96b10\`.
- Full repository unittest: 707 tests run, 40 skipped by environment guards; all non-skipped tests passed.
- CH12 numerical resource tests: 143 passed.
- Repository knowledge lint: 0 errors / 5 warnings.
- Additional structure/data checks: 0 errors.
- This CI validates repository consistency and existing code/tests; it does not execute a Provider receipt signer or verifier, since those remain unimplemented.

### Safety boundary / next work

- No real etcd, remote Provider, KMS/HSM, cloud object storage or IAM/RBAC was contacted. No production Unified schema-v2 authority, namespace, candidate import, Restore, application activation or Cutover was modified or executed.
- The proposed receipt signature proves that a trusted Provider key signed the receipt claims; it does not prove that the Provider implementation is correct or that the signing host/key is uncompromised.
- Provider receipt authenticity, external Floor consistency and Provider mutation atomicity remain separate guarantees and must be implemented/validated independently.
- SQLite Floor snapshot rollback protection still requires an independently trusted checkpoint outside that backup domain.
- MIG-04 IN_PROGRESS; MIG-05 IN_PROGRESS; MIG-06 TODO; MIG-07 BLOCKED. Production Unified schema-v2 remains the sole authority.
- **Status:** DONE for the Round 94 protocol/design deliverable only. A separate implementation round is required before any claim of authenticated Provider receipt functionality.

## CNC Knowledge Base — Round 95（Provider Receipt 签名协议与 Floor schema v4 验签门禁）

- Repository: \`rexyll/cnc-knowledge\`
- Branch: \`main\` only; no new branch created.
- Scope: Implement a local Provider receipt protocol module and move the external Provider Grant Floor from naked caller-supplied receipt digests to signed-envelope verification. Provider mutation transaction integration remains a separate Round96 task.

### Implementation

- Added \`scripts/spare_parts_provider_grant_receipt.py\`: RFC 8785 JCS canonicalization, Provider-owned Ed25519 domain-separated signing/verifying, strict JSON envelope parsing, duplicate-key rejection, claims validation, key lifecycle checks and immutable Verified Receipt output.
- Pinned \`rfc8785==0.1.4\` in \`requirements-ch17-security.txt\`.
- Upgraded \`SQLiteProviderGrantFloorAuthority\` to schema v4 with \`provider_grant_floor_receipt_keys\` trust registry. Explicit local owner APIs register key material and advance ACTIVE→RETIRING/REVOKED lifecycle; retirement and revocation timestamps constrain historical receipt verification. A retiring key may not issue receipts after the retirement boundary; a revoked key may not validate receipts at/after revocation.
- Changed \`confirm_provider_receipt\` to accept signed envelope only. It verifies Provider/key identity, fingerprint, claims and reservation binding inside the existing BEGIN IMMEDIATE / scope-revision CAS transaction, recomputes SHA-256 over the complete JCS envelope including signature, stores signer/key/trust/applied metadata, and rejects receipt replacement.
- Persisted the original Coordinator command issue/expiry timestamps in Floor Reservation. Signed receipt claims must match these exact values; command expiry cannot exceed the native Lease expiry. ACTIVATE applied time cannot predate the confirmed FENCE receipt.
- Schema migrations are sequential v1→v4. Historical naked digests remain unchanged with null signer/fingerprint/trust/applied/command-time metadata; legacy operations are not forged or silently promoted. Legacy pending reservations without authenticated command time fail closed on new confirmation.
- Added protocol test suite \`tests/test_spare_parts_provider_grant_receipt.py\` and extended \`tests/test_spare_parts_provider_grant_floor.py\` with synthetic Provider signers.

### Validation

- [GitHub Actions Knowledge Quality Run 46155354641](https://github.com/rexyll/cnc-knowledge/actions/runs/46155354641): both required jobs succeeded.
- Full repository unittest: 737 tests run, 40 skipped by environment guards; all remaining tests passed.
- CH12 numerical resource tests: 143 passed.
- This run validates code and focused tests. The implementation/plan documentation and TaskHistory synchronization commits are being followed by a fresh main-branch Knowledge Quality run.

### Safety boundary / remaining work

- Provider SQLite FENCE/ACTIVATE mutation path does not yet create and persist the signed receipt inside the same database transaction. Floor tests use synthetic Provider Ed25519 keys; this is not yet an end-to-end Provider→Floor proof.
- Local Floor owner key-management methods are not a production authenticated management plane. The Floor does not independently verify the Coordinator command signature; it binds the Provider receipt to the command digest and issue/expiry fields recorded in the reservation.
- Signed \`applied_at_unix\` is a Provider assertion, not an independent trusted timestamp. A compromised key can backdate claims; production requires additional immutable audit/time evidence.
- No actual etcd, Provider, KMS/HSM, object storage, IAM/RBAC or production authority integration occurred. No candidate import, Restore, application activation or Cutover occurred. Generic Restore with Provider Grant history stays fail-closed.
- MIG-04 IN_PROGRESS; MIG-05 IN_PROGRESS; MIG-06 TODO; MIG-07 BLOCKED. Production Unified schema-v2 remains the sole authority.
- **Status:** DONE for the local protocol module and external Floor verification gate only. Round96 is required for Provider durable receipt emission.


## CNC Knowledge Base — Round 95（Provider Grant Receipt 协议模块与外部 Floor 验签门禁）

- Repository: `rexyll/cnc-knowledge`
- Branch: `main` only; no branch created.
- Scope: Implement local Provider-native signed Receipt verification and migrate the separate SQLite Floor reference from naked digest confirmation to authenticated evidence. No Provider mutation integration or production external service integration.

### Implementation

- Added `scripts/spare_parts_provider_grant_receipt.py` and `tests/test_spare_parts_provider_grant_receipt.py`.
  - RFC 8785 JCS canonical UTF-8 encoding for new Receipt claims and envelopes.
  - Independent domain-separated Ed25519 Provider receipt signing/verifying; Coordinator command signing key is not reused.
  - Strict envelope/claims/signature schema, duplicate JSON-key rejection, unknown-field rejection, strict Base64 and 64-byte signature validation, type/range/time/digest/isolated-namespace/action-result checks.
  - `VerifiedProviderGrantReceipt` carries a complete canonical-envelope digest, signer key/fingerprint, trust revision and bound receipt claims.
- Upgraded `scripts/spare_parts_provider_grant_floor.py` to SQLite schema v4.
  - Added an explicit Provider receipt public-key trust registry keyed by Provider ID + key ID, including SHA-256 fingerprint, validity window, ACTIVE/RETIRING/REVOKED lifecycle, retirement/revocation effective timestamps and trust revision.
  - Added local database-owner management methods for key registration, retirement and revocation. Receipt-supplied public keys never auto-register or establish trust.
  - FENCE/ACTIVATE reservations now persist Coordinator command `issued_at` and `expires_at`; command expiry must be positive and no later than the native Lease expiry. Exact operation replay includes exact command time fields.
  - `confirm_provider_receipt()` now accepts only a signed Receipt envelope. Signature verification, trust-key lookup, Provider/tenant/scope/action/Grant/generation/command/FENCE digest/isolated namespace/Leader/native Lease/command time/result binding, ACTIVATE chronology, scope revision CAS and Floor state advancement occur under the same `BEGIN IMMEDIATE` transaction.
  - Floor computes the full canonical-envelope SHA-256 itself and stores signer key ID, key fingerprint, trust revision and Provider applied time. Confirmed Receipt replacement with a different digest is rejected; exact replay is idempotent.
  - Schema migration is sequential v1→v2→v3→v4. Historical naked digests and operations remain present, but new signer/fingerprint/trust/applied-time/command-time fields remain NULL for legacy rows; they are not forged or automatically upgraded to authenticated evidence. Legacy PENDING rows with no pinned command times cannot use the new confirmation path.
- Updated `requirements-ch17-security.txt` with pinned `rfc8785==0.1.4`.
- Updated CH17 README and the Round 95 section of root/CH17 TaskPlans to describe the actual schema v4 behavior and the distinction between local receipt verification and Provider data-plane integration.

### Tests and validation

- Current code implementation validation: [Knowledge Quality Run 46155354641](https://github.com/rexyll/cnc-knowledge/actions/runs/46155354641), both required jobs succeeded.
- Full repository unittest: 737 tests run, 40 skipped by environment guards; all non-skipped tests passed.
- CH12 numerical resource tests: 143 passed.
- Knowledge lint: 0 errors / 5 warnings; additional structure/data checks: 0 errors.
- The 737-test suite includes the Receipt protocol, Floor trust lifecycle, v1→v4 migration, naked-digest rejection, exact reservation claims, command-time/Lease bounds, FENCE/ACTIVATE chronology, idempotency/replacement and no-revision-advance-on-invalid-receipt tests.
- Final complete-main documentation synchronization: [Knowledge Quality Run 46155719334](https://github.com/rexyll/cnc-knowledge/actions/runs/46155719334) completed successfully on commit `b96831952e5e0e8148870f3d46637252a848394f`; both required jobs succeeded, including Knowledge structure/data quality and CH12 numerical resource tests. Root TaskPlan, CH17 TaskPlan, README, this TaskHistory record, design document, and implementation code are all covered by the final successful main-branch CI.

### Safety boundary / remaining work

- Receipt signing in the current tests uses synthetic Provider Ed25519 keys. The real `spare_parts_provider_sqlite_fenced.py` FENCE/ACTIVATE transaction still does not atomically persist the grant state, command receipt and signed Receipt envelope together; no durable signed-receipt lookup API by command digest exists yet.
- The Floor does not independently verify the Coordinator command signature in this round. The pinned command digest/claims in each reservation are supplied by the upstream Coordinator call path; production integration must authenticate that source and prevent callers from manufacturing reservation claims.
- The local key registry management methods are not a production key-management plane. No real Provider, KMS/HSM, etcd, object storage, IAM/RBAC or production trust-registry control plane was contacted.
- Provider receipt authenticity, external Floor consistency and Provider mutation atomicity remain separate guarantees. SQLite Floor/trust registry snapshot rollback still requires an independently trusted checkpoint outside its own backup domain.
- No Grant-aware Restore, candidate import, application activation or Cutover was implemented or executed. Generic Restore for any Provider Grant history remains fail-closed.
- MIG-04 IN_PROGRESS; MIG-05 IN_PROGRESS; MIG-06 TODO; MIG-07 BLOCKED. Production Unified schema-v2 remains the sole authority.
- **Status:** DONE for the Round 95 local Receipt protocol and external Floor verification reference implementation only; Provider data-plane signed Receipt persistence and production integration remain separate work.


## CNC Knowledge Base — Round 96（Provider SQLite FENCE/ACTIVATE 同事务 Signed Receipt）

- Repository: `rexyll/cnc-knowledge`
- Branch: `main` only; no branch created.
- Scope: Extend the local SQLite Provider reference so Provider-native signed FENCE/ACTIVATE Receipts are created and persisted atomically with Grant state and the original Coordinator command receipt, then consumed by the Round95 external Floor verifier.

### Implementation

- Upgraded `scripts/spare_parts_provider_sqlite_fenced.py` Provider schema to v7. Kept the existing `envelope_json` and `signer_public_key_base64` fields dedicated to the Coordinator-signed command; added separate Provider Receipt envelope, digest, signer key ID and public-key copy columns.
- Added dependency injection for an independent Provider Ed25519 private key and key ID plus strict signed-receipt mode. The private key stays in process memory only. Provider refuses a receipt signer key ID or public key that duplicates a configured Coordinator command signer.
- Persisted `provider_grant_receipt_signing_required` in Provider metadata. Once strict mode is enabled, a later Provider instance cannot silently downgrade the database to unsigned mode. Historical command rows lacking Provider Receipt evidence are not backfilled or elevated to trusted current grants.
- FENCE/ACTIVATE processing now signs and stores the Provider Receipt inside the same Provider `BEGIN IMMEDIATE` transaction as the Provider Grant state and original Coordinator command receipt. Claims bind Provider/tenant/scope/action/Grant/generation/command digest/FENCE digest/Coordinator namespace/Leader/native Lease/command issue-expiry/Provider applied time. Any failure before transaction commit rolls back all three durable records.
- Added `get_provider_grant_receipt(provider_id, tenant_id, command_sha256)` for exact lookup. It revalidates the Coordinator command, Provider signature, canonical full-envelope digest and claim-to-row bindings. Exact command replay verifies and returns the original immutable receipt; post-commit response loss can be recovered by the original command digest.
- Strict-mode protected object/multipart mutations now require both the current FENCE and ACTIVATE Provider Receipts to exist and pass verification. Provider backup validation checks Provider Receipt canonical bytes/digest, independent Provider signer signature, binding to the original Coordinator signed command and the FENCE/ACTIVATE chain. A recomputed digest with a forged signature is still rejected.
- Added Provider→Floor end-to-end integration coverage: the local Provider produces real signed FENCE and ACTIVATE envelopes, which are then independently checked by the Round95 Floor Provider-key registry and advance the Floor to FENCED/ACTIVE.
- Added tests for pre-commit full rollback, exact Provider/Tenant/command lookup, response-loss and restart replay, strict policy no-downgrade, schema v6→v7 migration, separate Coordinator/Provider signers, Receipt digest tamper, forged signature with recomputed digest, and backup validation rejection.
- Updated Round96 sections in root and CH17 TaskPlans; added Round97 plan for independent Coordinator command signature verification at the Floor reservation boundary. Updated CH17 README and Receipt authentication design.

### Validation

- [GitHub Actions Knowledge Quality Run 46157250066](https://github.com/rexyll/cnc-knowledge/actions/runs/46157250066): both required jobs succeeded.
- Full repository unittest: 745 tests run, 40 skipped by environment guards; all non-skipped tests passed.
- CH12 numerical resource tests: 143 passed.
- Repository knowledge lint: 0 errors / 5 warnings.
- Additional repository structure/data checks: 0 errors.

### Safety boundary / remaining work

- This proves the same-host SQLite Provider reference only, using an in-memory synthetic Ed25519 Provider key. No real remote Provider, object storage, KMS/HSM, etcd, IAM/RBAC or production key-management plane was connected.
- The public-key copy stored beside each Provider Receipt supports local self-consistency verification, not independent trust. The external Floor Provider key registry remains the Provider signer trust anchor.
- Critical remaining gap: external Floor reservation still accepts caller-supplied Coordinator command digest/claims and does not independently verify the original Coordinator signed Grant command. Round97 will make the Floor accept and validate the signed command envelope against an independent Coordinator key registry.
- Provider and Floor SQLite databases/trust registries are not rollback-resistant against their own old snapshots without independently trusted checkpoints outside their backup domains.
- Grant-aware Restore remains unimplemented. Generic Restore for any Provider Grant history remains fail-closed. No candidate import, Restore, application activation or Cutover was performed.
- MIG-04 IN_PROGRESS; MIG-05 IN_PROGRESS; MIG-06 TODO; MIG-07 BLOCKED. Production Unified schema-v2 remains the sole authority.
- **Status:** DONE for the Round96 local Provider SQLite reference integration and its end-to-end tests.


## CNC Knowledge Base — Round 97（外部 Floor Coordinator Grant Command 来源认证）

- Repository: `rexyll/cnc-knowledge`
- Branch: `main` only; no branch created.
- Scope: Close the Coordinator command source-authentication gap in the local external Grant Floor reference. The Floor now accepts original Coordinator-signed FENCE/ACTIVATE envelopes and independently verifies them before reserving a generation.

### Implementation

- Upgraded `scripts/spare_parts_provider_grant_floor.py` external Floor schema from v4 to v5.
  - Added `provider_grant_floor_coordinator_keys`, keyed by issuer ID + key ID, containing Ed25519 public-key material/fingerprint, ACTIVE/RETIRING/REVOKED, validity window, retirement/revocation effective timestamps and reason, and trust revision.
  - Added persistent `coordinator_command_auth_required` policy. New Floor databases default to strict command authentication; v1-v4 migrations also default to strict.
  - Added Coordinator signer key ID, fingerprint and trust revision columns to operation history. Historical operations are not retroactively assigned a signer or fabricated trust evidence.
- Added local owner management APIs `admin_register_coordinator_command_key()` and `admin_set_coordinator_command_key_status()`. Coordinator command envelopes cannot auto-register their own public keys. Key rotation registers a new key ID/material; retired/revoked keys cannot create new reservations. Exact previously accepted operation identity is retained for historical audit/idempotency.
- Added strict signed-command APIs:
  - `reserve_fence_from_command(operation_id, key, command_envelope, expected_revision)`
  - `reserve_activate_from_command(operation_id, key, command_envelope, expected_revision)`
- Both APIs require an explicit expected `ProviderGrantScopeKey` selected by the caller. The Floor compares signed Provider/Tenant/scope claims with that target context, so a valid command cannot choose a different Floor scope by self-declaration.
- The Floor parses original Coordinator signed envelopes, rejects duplicate JSON object keys and non-finite JSON constants, recomputes the canonical full-envelope command digest, loads the Coordinator public key from its own trust registry, and verifies the Ed25519 signature. It checks issuer/key/fingerprint/lifecycle/time, Provider/Tenant/scope, action, Grant ID/generation, namespace, Leader epoch/native Lease, command issued/expiry and FENCE digest.
- Coordinator signature verification, claims binding, next-generation calculation, scope state validation, scope revision CAS and pending operation creation occur inside the same SQLite `BEGIN IMMEDIATE` transaction. The signed command generation must equal the exact next Floor generation; ACTIVATE must reference the latest confirmed FENCE. Invalid signature, unknown/revoked key, identity mismatch, time/Lease violation, generation mismatch or CAS failure does not advance scope or authority revision.
- Strict mode rejects caller-supplied digest/claims through the legacy `reserve_fence()` / `reserve_activate()` methods. `allow_legacy_unsigned_reservations=True` is an explicit local test/compatibility option for a newly created non-strict database only; strict Floor databases cannot be downgraded.
- In strict mode, legacy migrated PENDING operations that lack Coordinator signer ID/fingerprint/trust revision cannot be upgraded merely by presenting a Provider signed Receipt. Previously confirmed history remains unaltered and is not relabeled as authenticated Coordinator command evidence.
- Updated Provider→Floor integration to register independent Coordinator command and Provider Receipt public keys, pass the actual signed Coordinator command envelope through the strict Floor API, then confirm with the actual Provider-signed Receipt.
- Added tests covering valid FENCE/ACTIVATE, signed-command tamper, duplicate JSON keys, unknown/retired/revoked keys, key rotation, cross-Provider/Tenant/scope, wrong generation, Lease/time bounds, exact FENCE chain, strict-default/no-downgrade, v1→v5 migration, legacy PENDING fail-closed and no-revision-advance on invalid commands.
- Updated Round97 root and CH17 TaskPlans, CH17 README, and the external Floor/Restore reconciliation design document.

### Validation

- Code/test validation: [Knowledge Quality Run 46159157703](https://github.com/rexyll/cnc-knowledge/actions/runs/46159157703), both required jobs succeeded.
- Full repository unittest: 757 tests run, 40 skipped by environment guards; all non-skipped tests passed.
- CH12 numerical resource tests: 143 passed.
- Knowledge lint: 0 errors / 5 warnings.
- Additional structure/data checks: 0 errors.
- The run above validates the Floor schema v5 Coordinator trust implementation and regression suite. Final complete documentation synchronization is validated by the subsequent main-branch CI run after this TaskHistory update.

### Safety boundary / remaining work

- This is a same-host SQLite Floor reference with synthetic Coordinator/Provider Ed25519 keys; it is not a production Coordinator/etcd trust plane, quorum authority, or multi-host linearizable service.
- The Coordinator key registry is managed through local database-owner APIs, not a production approval workflow or KMS/HSM integration. Floor SQLite and its trust registry remain vulnerable to rollback of their own database snapshots unless an independently trusted checkpoint is stored outside that backup domain.
- No real Coordinator, etcd, remote Provider, object storage, KMS/HSM, IAM/RBAC or production trust control plane was connected. Production Unified schema-v2 remains the sole authority.
- Grant-aware Restore remains unimplemented. Generic Restore for any Provider Grant history remains fail-closed. No candidate import, Restore, application activation or Cutover was performed.
- MIG-04 IN_PROGRESS; MIG-05 IN_PROGRESS; MIG-06 TODO; MIG-07 BLOCKED.
- Final expanded code/test validation: [Knowledge Quality Run 46159590900](https://github.com/rexyll/cnc-knowledge/actions/runs/46159590900) succeeded on both required jobs; 762 repository tests ran with 40 environment-guarded skips, CH12 numerical resource tests passed 143, knowledge lint had 0 errors / 5 warnings, and structure/data checks had 0 errors. Additional tests cover explicit Provider/Tenant/scope target binding, command expiry beyond native Lease, exact signed-operation replay, and preventing legacy unsigned PENDING operations from being confirmed after strict migration.
- **Status:** Round97 implementation and expanded code/test suite passed; final documentation synchronization CI pending.
