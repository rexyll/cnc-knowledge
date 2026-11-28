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
- Extended `scripts/spare_parts_provider_sqlite_fenced.py`: Provider schema v5; additive grant state and durable command receipt tables; changing Leader/Lease identity requires a strictly newer Coordinator Leader epoch, while the exact same Leader/Lease may self-FENCE an ACTIVE grant for renewal/rotation; ACTIVATE requires an exact persisted FENCE receipt and matching namespace/Leader/Lease/grant identity.
- Added optional `require_revocable_grant=True`. When enabled, Provider construction requires Provider ID, an Ed25519 command trust key and an online Coordinator Leader checker; object PUT and multipart begin/part/complete proofs must include signed Grant ID/generation, checked in each actual Provider BEGIN IMMEDIATE mutation transaction. The online check gates FENCE/ACTIVATE commands but remains separate from SQLite commit; inactive/unavailable status fails closed without creating grant state.
- FENCE permits same-epoch self-revocation only when the exact same Leader ID/native Lease remains current and ACTIVE; an identity change still requires a strictly higher epoch. FENCE IDs cannot be reused, FENCED scopes cannot be fenced repeatedly, and same-epoch Lease expiry cannot regress. Added a same-Leader grant rotation test.
- Added receipt chronology enforcement: ACTIVATE `issued_at_unix` must not predate the FENCE Provider receipt's persisted `applied_at`; a pre-signed early ACTIVATE is rejected. Added schema v4→v5 migration coverage and verified the FENCE receipt survives Provider backup/restore.
- Added same-Leader grant rotation, pre-issued ACTIVATE rejection, schema v4 migration, and backup/restore test commits: `bf938e779990de5e76b8d3972d0857cd779ddd31`, `548e350e7d72d68e50d4fe03d1f092365543d118`, `881d79418c6f039a322df09cb41bd2aeef7c4e1a`.
- Added receipt lookup by exact envelope SHA-256, including lost-response recovery without reapplying a generation.
- Extended Provider tests for missing/early FENCE receipt, activation, newer-epoch revocation of the old grant, same-Leader grant rotation, all four mutation entrypoints, post-commit response loss, backup/restore persistence, transaction ordering, and v2/v3/v4 additive schema migration.

### Validation / safety boundary

- Code and test commits: grant command module `705a7a0d82ffa26685eacd32d33f98d668efe385`; Provider state machine `88f72910cc9b4c913a3fb9ebf09e25b1e31277b1`; self-FENCE/rotation hardening `9eec79e452a7ae016ddf510b55f8f4fc129b2ab9`; ACTIVATE-after-FENCE receipt chronology guard `75562bdaa282df997685d8fc6562b84dbc2f479e`; primary tests `5313f5d72abd8e174e534511c3e73e3caac2489c`, schema migration assertions `3358a930c88c7d2b27e1f9920b66387ad1417bff`, multipart gate and FENCE ordering coverage `0fc9ee43b833469eba40fb9d5c97b687b3daf746`, same-Leader rotation `bf938e779990de5e76b8d3972d0857cd779ddd31`, receipt backup/restore and pre-issued activation / v4 migration `881d79418c6f039a322df09cb41bd2aeef7c4e1a`, `548e350e7d72d68e50d4fe03d1f092365543d118`.
- Required main-branch CI results have not yet been retrieved; do not mark Round 90 DONE until the unit suite and Knowledge Quality workflow complete successfully.
- This is a same-host SQLite reference only. No real etcd, remote Provider, KMS/HSM, cloud object store or IAM/RBAC was contacted; no production namespace, candidate import, application activation or cutover occurred.
- MIG-04 remains IN_PROGRESS; MIG-05 remains IN_PROGRESS; MIG-06 TODO; MIG-07 BLOCKED. Production Unified schema-v2 remains the sole authority; ASSET-000092 remains `PROPOSED_NOT_APPROVED / NOT_RUN`.
