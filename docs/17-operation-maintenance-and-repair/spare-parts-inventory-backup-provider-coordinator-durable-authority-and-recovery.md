# 数控机床备件库存备份 Coordinator 持久权威、Leader 切换与故障恢复

**知识编号：** KNOW-000050  
**章节：** CH17-T004  
**版本：** 1.0  
**日期：** 2026-11-26  
**关联：** KNOW-000042、KNOW-000043、KNOW-000048、KNOW-000049  
**参考资源：** ASSET-000081

## 1. 目标与适用边界

KNOW-000049定义了对象存储 Provider 通过单个 per-scope control object CAS 对 lease activation、manifest publish 和 revoke 排序；但单对象 CAS 本身不能保证 Coordinator 的 token 分配端不会回退，也不能替代 Coordinator 对 operation sequence、幂等键、领导者切换与崩溃恢复的持久化。

本专题在既有 SQLite admission Coordinator 之上增加一个持久权威参考层，解决以下本地参考路径：

1. 对租户命名空间内的 fencing scope 持久分配单调 token。
2. 在同一 scope 内持久分配单调 publish operation sequence，并将其绑定到幂等键与 manifest 内容摘要。
3. 将 activation、revocation 与 publish 的 Provider 外部提交结果和 Coordinator 本地状态分为两个可恢复阶段。
4. 对 Leader 身份、epoch 和到期时间做持久校验，阻止已失效进程继续创建状态变更或签署新的 operation proof。
5. 对 Coordinator 进程重启、Provider 响应丢失和数据库恢复提出 fail-closed 流程。

**实现范围是同一主机、同一个本地 SQLite WAL 数据库文件的参考模型。** 它不是多主机分布式共识服务，不应将SQLite WAL放到NFS/SMB等网络文件系统上，也不构成生产级线性一致性保证。

## 2. 标识与单调序列

### 2.1 Admission token 与 scope token 是不同层次

既有 `SQLiteProviderAdmissionCoordinator` 为 admission lease 分配的 `admission_fencing_token` 只服务于本机准入/租约序列。本轮新建的 `coordinator_authority_scopes.high_water_token` 则是对象存储控制对象使用的 per-scope token。两者语义不同，不可互换，也不应假设数值相同。

### 2.2 租户 scope 命名空间

Coordinator要求scope使用规范路径：

```text
tenants/<tenant_id>/<resource-scope...>
```

例如：

```text
tenants/tenant-A/cnc/ch17/spares/pkg-001
```

`tenant_id`必须与当前Admission lease一致。该约束避免不同租户误用相同scope key，进而共享token或operation sequence。路径必须是相对路径，拒绝空段、`.`、`..`、反斜杠和超长字段。

### 2.3 两条单调序列

- **Fencing token：** 在每一个 tenant-qualified scope 内单调递增。新activation在持久事务中分配 `high_water_token + 1`；不能复用旧token。
- **Operation sequence：** 在同一scope内单调递增，代表该scope的publish逻辑操作顺序；不随lease轮换或Coordinator进程重启归零。

同一个 `(scope, idempotency_key)` 重复请求，只有在operation kind和规范化请求摘要一致时才返回原记录；相同幂等键对应不同请求内容必须拒绝。

## 3. 持久化数据模型

模块 `scripts/spare_parts_provider_coordinator_authority.py` 新增四类SQLite记录：

| 表 | 职责 | 关键字段 |
|---|---|---|
| `coordinator_authority_leader` | 当前单一Leader lease | `leader_id`、`epoch`、`expires_at`、`state` |
| `coordinator_authority_scopes` | 每个租户scope的权威高水位及当前lease状态 | `high_water_token`、`latest_operation_sequence`、`lease_state`、`provider_generation` |
| `coordinator_authority_operations` | activation/revoke/publish持久请求与恢复记录 | 幂等键、request SHA-256、token、sequence、lease、manifest、状态 |
| `coordinator_authority_meta` | schema版本 | `schema_version` |

所有修改使用 `BEGIN IMMEDIATE`，在单一SQLite写事务内完成Leader核验、幂等检查、序列分配和状态变更。代码通过 `PRAGMA journal_mode=WAL` 和 `synchronous=FULL`；这仍然是单主机SQLite事务语义，而不是跨主机共识协议。

## 4. Activation：先预留，再以 Provider 读回确认

状态转移：

```text
IDLE / ACTIVE / REVOKED / RECOVERY_REQUIRED
        |
        | prepare_activation：事务内 token = high_water + 1
        v
PENDING_ACTIVATION
        |
        | Leader校验并签发 fencing:activate Ed25519 proof
        | Provider对scope control object执行条件CAS
        | 强一致读回ACTIVE + 完全匹配token/lease_id/generation
        v
ACTIVE
```

执行顺序：

1. `prepare_activation()` 校验当前Leader、Admission lease的ACTIVE状态、tenant/owner/domain与过期时间。
2. 同一SQLite事务为该scope分配新token，写入 `PENDING_ACTIVATION` 和幂等请求记录。
3. `sign_distributed_fencing_proof()` 在签名前再次核对持久化Leader epoch及原操作仍处于待处理状态；proof绑定scope、tenant、lease、token、operation和idempotency key。
4. Provider对单个control object执行条件CAS。上传staging payload不代表备份已发布。
5. 只有从受信任的Provider Gateway获得强一致读回，且状态、token、lease_id一致时，调用 `confirm_activation()` 将Coordinator状态改为 `ACTIVE` 并记录Provider generation。

任何步骤异常时均不得提前报告ACTIVE。若Provider CAS已成功但响应丢失，Coordinator保留PENDING状态，由当前Leader强一致读取Provider control object后，再执行匹配的确认；不能凭超时推断成功或失败。

## 5. Publish：先分配sequence，再核验完整回执

1. `allocate_operation_sequence()` 要求scope已经是匹配的 `ACTIVE` lease，原子分配 `latest_operation_sequence + 1`。
2. operation record绑定 `scope`、tenant、fencing token、sequence、idempotency key、manifest key和SHA-256。
3. manifest key必须位于token专属不可变staging前缀，例如 `<scope>/staging/<token>/...`。
4. 当前Leader对待提交操作签发 `fencing:publish` Ed25519 proof；proof绑定operation sequence、manifest key及manifest SHA-256。
5. Provider只在单个control object CAS成功并生成receipt后，才把current manifest pointer推进到新manifest。
6. Coordinator的 `confirm_publish()` 必须核对Provider回执中的token、sequence、idempotency key、manifest key、manifest SHA-256和generation，完全匹配后将operation标为 `COMMITTED`。

若响应丢失，必须使用原幂等键及原operation内容恢复；不能创建一个新幂等键并盲目重放未知结果。Provider receipt超保留窗口或无法强一致读取时，操作保持未知/待人工审查，遵循KNOW-000049的 `OUTCOME_UNKNOWN` 约束。

## 6. Revocation：REVOKING 不等于已撤销

状态转移：

```text
ACTIVE
  |
  | prepare_revocation
  v
REVOKING
  |
  | Provider control object ACTIVE -> REVOKED CAS
  | 强一致读回状态、token、lease_id与generation
  v
REVOKED
```

`prepare_revocation()` 仅允许当前Leader对精确匹配的活动lease发起撤销，并持久化 `REVOKING`。只有Provider read-back确认其control object已从ACTIVE变为REVOKED后，`confirm_revocation()` 才能写入最终REVOKED。

处于REVOKING期间，新的publish sequence分配被拒绝。Coordinator不能仅因本地数据库写入REVOKING就告知调用者撤销已经完成。

## 7. Leader epoch 与旧Leader隔离

Coordinator维护单行Leader lease：

- `claim_leadership()` 只在既有Leader未处于有效租期时允许新的Leader接管，并将epoch提升。
- `renew_leadership()` 要求leader_id和epoch仍与数据库中的当前记录一致。
- 所有prepare、confirm、恢复查询和proof签名都必须校验当前Leader ID、epoch及expires_at。
- proof签发前，`authorize_operation_signing()` 重新读取持久化operation，确保请求仍处于PENDING_ACTIVATION、REVOKING或PENDING_PUBLISH之一，且当前调用者仍是有效Leader。
- 旧进程带着缓存的Leader lease重新上线后，不能继续创建操作、签发新proof或确认状态。

Leader lease基于Unix wall-clock时间与TTL，仍假设主机时间源可靠。已签发但尚未过期的短时proof不会仅因Coordinator Leader epoch变化而自动失效；Provider侧的per-scope token high-water和control-object CAS仍是下游最终防线。生产系统还必须限制proof TTL、保护control object写权限，并设计Leader切换后的Provider强一致读回和token fencing策略。

## 8. 崩溃恢复和数据库恢复

### 8.1 进程崩溃

Coordinator崩溃可能发生在：
- 本地写入PENDING之前；
- 本地PENDING提交后、proof签发前；
- proof签发后、Provider CAS前；
- Provider CAS提交后、Coordinator确认前。

未完成操作保留持久状态。新Leader在取得更高epoch后调用 `list_pending_operations()`，并逐项核对Provider真实control object和receipt。只有读回字段与原请求完全匹配时才允许确认；无法读取Provider时必须fail-closed。

### 8.2 Coordinator数据库从备份恢复

恢复旧数据库可能让本地token、sequence或Leader epoch回退。因此在恢复数据库对外提供写服务前，必须从独立于该备份的权威记录取得：
- 当前scope的Provider high-water token；
- 当前scope的Provider latest operation sequence；
- 当前Leader epoch的独立恢复下限。

`claim_leadership(recovery_epoch_floor=..., reconciliation_ref=...)` 要求Leader epoch恢复下限高于恢复库中的epoch。`reconcile_after_restore()` 要求外部token/sequence floors不低于恢复库当前值，将scope提升到外部高水位，清除旧lease身份并设置 `RECOVERY_REQUIRED`；未完成操作转为 `RECOVERY_REVIEW`，不会自动重放或自动cutover。

恢复下限中的 `reconciliation_ref` 只是审计引用字符串，本身不是签名证据或外部服务校验。必须由部署Runbook规定如何认证Provider read-back与独立epoch register；缺少可信外部高水位时保持写入阻断。该参考模块不负责执行SQLite备份、备份文件完整性校验、文件系统切换或真实灾备恢复。

## 9. 测试与资源

新增代码：
- `scripts/spare_parts_provider_coordinator_authority.py`
- `tests/test_spare_parts_provider_coordinator_authority.py`

新增资源：
- `resouces/17-operation-maintenance-and-repair/spare-parts-inventory-backup-provider-coordinator-authority-test-matrix-v1.csv`（ASSET-000081，16条合成参考场景，全部 `PROPOSED_NOT_APPROVED / NOT_RUN`）

专项测试覆盖持久token/sequence、幂等与冲突、并发sequence分配、两阶段activation/revoke、Provider receipt绑定、Coordinator重启、Leader过期接管、旧Leader写入与签名拒绝、新Leader恢复待处理激活以及外部恢复高水位门禁。

## 10. CI 验证记录

- **代码提交：** `abb73ebd6e3268d15f149333d904369c5cc1a42d`；[Run 45769331991](https://github.com/rexyll/cnc-knowledge/actions/runs/45769331991)两个必需Job均completed/success。
- **文档同步提交：** `262c7fe71f0a436ec1b95686cbb1c6c7448b2575`；[Run 45769584662](https://github.com/rexyll/cnc-knowledge/actions/runs/45769584662)两个必需Job均completed/success。
- 两次最终验收均为全库283项unittest、CH12 143项数值资源测试通过；strict knowledge lint PASS（0 errors，5 warnings）；知识结构与数据质量PASS（0 errors）。
- 文档同步Run的现有产物包括CH17 SQLite admission Coordinator self-check 15093960081、Provider fenced self-check 15093038669、BackupStorageAdapter self-check 15093925222及备份治理readiness 15093158182。这些是既有模块的自检产物，不是新Coordinator authority的多主机/云服务验收证据。
- 新增15项Coordinator authority unittest通过；ASSET-000081的16条场景仍全部PROPOSED_NOT_APPROVED / NOT_RUN。CI只验证本地SQLite/内存Provider合成测试路径。

## 11. 明确未完成事项

- SQLite WAL实现仅支持同一主机、同一数据库文件及受支持的本地文件系统；不支持NFS/SMB或多主机共享。
- 没有Raft/Paxos/etcd/Consul/Spanner等分布式共识/事务后端，也没有多实例Coordinator远程API。
- 没有HTTP/gRPC远程服务、AWS S3/GCS/Azure SDK或真实对象存储端到端测试。
- 没有真实KMS/HSM签名、云IAM/RBAC部署、Gateway独占写权限策略或密钥轮换运维流程。
- Provider read-back必须来自受信任且强一致的Gateway；不得接受不可信客户端自行提交的状态字符串。
- 16条ASSET-000081验收场景全部尚未获批或执行；仓库单元测试不等于企业验收。
- 生产备份继续关闭：`production_backup_enabled=false`；治理状态为 `BLOCKED_PENDING_ENTERPRISE_APPROVAL`；`business_rule_assertions=NOT_EVALUATED`。

## 12. 参考来源

- SRC-000391：SQLite Transactions官方文档。
- SRC-000392：SQLite Write-Ahead Logging官方文档。WAL的共享内存协调要求决定了它不能被视为NFS/SMB多主机协调服务。

关联的远程Provider单对象CAS约束见 [KNOW-000049](spare-parts-inventory-backup-provider-distributed-fencing.md)。本专题是同机持久Coordinator参考层，并未把SQLite状态表升级为分布式共识服务。
