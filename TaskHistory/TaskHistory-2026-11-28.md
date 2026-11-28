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
