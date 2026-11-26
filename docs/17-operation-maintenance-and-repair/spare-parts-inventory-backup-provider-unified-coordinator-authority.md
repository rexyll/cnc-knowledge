# 备件库存备份 Unified Coordinator Authority：Leader、Scope Fencing 与 Operation Ledger 统一事务

**知识编号：** KNOW-000055  
**章节：** CH17 操作、维护与维修  
**状态：** Store-backed 统一事务参考实现已通过仓库 CI；尚未替换生产/旧 SQLite Coordinator  
**关联知识：** KNOW-000051、KNOW-000052、KNOW-000053、KNOW-000054  
**关联资源：** ASSET-000086

## 1. 本轮目标与状态边界

第四十轮已把 Provider Admission 的 global/tenant quota、跨 domain wait queue、公平调度、fencing token 和 Lease 生命周期归并到单一 revisioned aggregate，但 Coordinator 的 Leader epoch、每个 tenant scope 的 high-water fencing token、ACTIVATE/REVOKE/PUBLISH 操作账本、publish sequence 和恢复审查状态仍留在原 `SQLiteDurableCoordinatorAuthority`。

本轮新增 `StoreBackedCoordinatorAuthority`，把上述 Coordinator 数据作为第四十轮统一 Admission aggregate 的 `coordinator` 子对象保存。Leader TTL key、Admission 活动 Lease/request 索引、scope 状态及 operation ledger 的写入都使用同一个 `CoordinatorAuthorityStore`。本轮证明的是同一状态机/同一 Txn 的参考路径，不是对旧 SQLite 服务的自动迁移。

## 2. 新模块、schema 和 namespace

- 实现：`scripts/spare_parts_provider_unified_coordinator_authority.py`
- 测试：`tests/test_spare_parts_provider_unified_coordinator_authority.py`
- Coordinator：`StoreBackedCoordinatorAuthority`
- Admission scheduler：`StoreBackedProviderAdmissionCoordinator`
- 共用存储：`CoordinatorAuthorityStore`（SQLite / etcd v3 adapter）

为加入 Coordinator 子状态，统一 Admission Aggregate schema 从 version 1 升到 version 2，并使用新 namespace：

```text
/cnc/admission/unified/v2/scheduler/state
/cnc/admission/unified/v2/leases/<sha256(lease_id)>
/cnc/admission/unified/v2/requests/<sha256(request_id)>
/cnc/admission/unified/v2/coordinator/leader
```

不得把 v1 scheduler aggregate 直接作为 v2 状态读取，也不得把第三十九轮 standalone Lease Authority 的 `/cnc/admission/v1/` 键与本版本合并或双写。没有定义自动数据迁移工具；v1→v2 迁移仍需停写、盘点旧状态、验证外部 Provider fencing floor，再以单一权威进行受控导入。

Aggregate 的新增内容：

```json
{
  "schema_version": 2,
  "coordinator": {
    "leader": null,
    "scopes": {},
    "operations": {}
  }
}
```

其中 Admission 的策略、配额、活动 Lease 和 waiters仍保持在同一个 aggregate 中。

## 3. Leader epoch 与原生 TTL

Coordinator Leader 记录包括 `leader_id`、单调递增 `epoch`、`expires_at` 和 backend lease ID。单独的 Leader KV key附着存储后端原生 TTL Lease，aggregate 中同时保留同一记录的镜像。

### claim

`claim_leadership()`：
1. 读取统一 aggregate、Leader TTL key 和当前 admission 活动状态；
2. 若 Leader TTL key仍存在，拒绝第二个 Leader；
3. 默认 epoch 为 persisted epoch + 1；恢复模式要求外部 epoch floor 严格大于持久 epoch，并提供 reconciliation reference；
4. 取得 backend TTL Lease；
5. 在同一 Txn 比较 aggregate revision 和 Leader key 不存在，再写入新的 TTL key及 aggregate Leader 状态；
6. CAS失败时撤销未附着 TTL Lease并重读；响应丢失时以 Leader key 和 aggregate 双重读回核实，无法核实时 fail-closed。

### renew

`renew_leadership()` 在同一个事务中比较旧 Leader key 精确值、aggregate revision，并将新 TTL Lease附着到同一个 Leader key，同时更新 aggregate 的 expires_at/backend lease ID。事务成功后才 best-effort撤销旧 backend Lease。

续租不改变 epoch；同一 `leader_id + epoch` 在续租前后的句柄仍属于同一 Leader epoch。新的 takeover 必须在原生 TTL key到期消失后取得更高 epoch。缓存的旧 Leader不能越过 takeover后的新 epoch。

## 4. Scope fencing state

每个 scope 使用规范化相对路径，并必须属于 `tenants/<tenant_id>/...` 命名空间。scope record 保存：

| 字段 | 含义 |
|---|---|
| `high_water_token` | 该 scope 单调递增的 Provider fencing token |
| `lease_id / owner_id / tenant_id / domain` | 当前 scope Lease身份 |
| `lease_expires_at` | Admission Lease到期时间 |
| `lease_state` | IDLE / PENDING_ACTIVATION / ACTIVE / REVOKING / REVOKED / FENCED / RECOVERY_REQUIRED |
| `latest_operation_sequence` | scope内单调发布序列 |
| `provider_generation` | Provider 端 read-back generation |

scope token与Admission全局 fencing token是两个不同层级：前者在 scope内控制 Provider 资源写入顺序；后者在 Admission scheduler内保护并发容量与Lease生命周期。Coordinator operation同时绑定这两类身份，不可以互相替代。

## 5. Operation Ledger：两阶段 ACTIVATE / REVOKE / PUBLISH

Operation map由 `sha256(scope + NUL + idempotency_key)` 定位。记录保留完整 scope、kind、idempotency_key、canonical request SHA-256、scope fencing token、可选 operation sequence、Admission Lease身份、manifest binding、state、Provider generation及创建/更新时间。

### ACTIVATE

- `prepare_activation()` 在同一 Txn核实当前 Leader和活动Admission Lease，拒绝 scope已有未解决的 PENDING_ACTIVATION / REVOKING，分配 `high_water_token + 1`，写入 PENDING_ACTIVATION operation并更新 scope。
- 外部 Provider必须执行实际 activate并返回状态、high-water token、lease ID和generation。
- `confirm_activation()` 只在 read-back确认 ACTIVE且 token/lease匹配时，原子地把 operation和scope转为 ACTIVE。
- 同一 idempotency key + 同一 payload返回原 operation；相同key若 kind或请求digest不同则拒绝。

### REVOKE

- `prepare_revocation()` 仅接受 exact current ACTIVE scope Lease及对应 fencing token；同一 Txn写入 REVOKING operation与 scope状态。
- 外部 Provider撤销并read-back确认后，`confirm_revocation()` 将 operation和scope标记 REVOKED。
- 不能把准备撤销等同于已撤销；需要 Provider端读回证据。

### PUBLISH

- `allocate_operation_sequence()` 仅允许 exact ACTIVE scope Lease，为 scope分配 `latest_operation_sequence + 1`，并绑定 fencing token、manifest key与 SHA-256，operation初始为 PENDING_PUBLISH。
- manifest key必须位于 scope下的规范化路径。
- Provider收到签名 proof并执行条件发布后，`confirm_publish()` 校验 Provider receipt中的 fencing token、sequence、idempotency key、manifest key和digest，才将操作置为 COMMITTED。
- 同一 idempotency key + 同一 manifest payload重复请求返回同一 sequence；并发不同请求通过 aggregate revision CAS获得唯一序号。

## 6. Proof signing authorization

`authorize_operation_signing()` 在签名之前重新读取并比较当前 Leader TTL key和aggregate revision，要求：
- caller Leader ID/epoch仍为当前有效Leader；
- operation仍存在于持久 operation map；
- kind、request digest、scope fencing token、Lease ID、owner、tenant、domain、Lease expires_at、pending state、operation sequence和manifest binding均与持久记录一致。

本轮同步调整 `sign_distributed_fencing_proof()` 的后端检查：从限定 `SQLiteDurableCoordinatorAuthority` 改为要求 authority backend提供 `authorize_operation_signing()`。这样 SQLite和 Store-backed Coordinator实现共用签名路径，而不是为测试引入另一套 proof 格式。

新增测试使用Ed25519测试 signer、`InMemoryConditionalObjectControlStore` 和 `DistributedObjectFencingControlPlane` 执行本地合成 end-to-end：
ACTIVATE prepare → signing authorization → Provider activate → read-back confirm → PUBLISH sequence allocation → proof signing → Provider conditional publish → receipt confirm → REVOKE prepare → Provider revoke → read-back confirm。

该测试验证的是本地合成 Provider adapter，不是外部对象存储或真实多主机Provider。

## 7. Restore reconciliation 与 fail-closed

`reconcile_after_restore()` 要求外部 Provider high-water token与 operation sequence floor都不低于恢复出的 Coordinator值。成功后：
- scope token与sequence提升到外部floor；
- 当前scope Lease身份清空，状态变为 RECOVERY_REQUIRED；
- PENDING_ACTIVATION、REVOKING和PENDING_PUBLISH operations转入 RECOVERY_REVIEW；
- 返回 `automatic_cutover=false`。

恢复流程不自动把operation升级为 ACTIVE/COMMITTED，也不会自动重新绑定旧Admission Lease。外部floor低于持久状态时拒绝恢复；必须人工审查Provider read-back与 reconciliation证据。完成floor核对后，调用方可显式发起新的ACTIVATE请求，scope token从外部floor+1开始，仍先处于PENDING_ACTIVATION，只有新的Provider read-back才能确认ACTIVE。此显式调用不等同于自动恢复或自动cutover。

## 8. 同一 Txn 边界

每次 Coordinator写入通过 scheduler的 `_load_prepared()`读取同一 aggregate revision及当前Admission活动Lease/request精确值，并追加当前 Leader TTL key的精确值Compare。成功分支将更新后的完整aggregate一次写回。因此：

- Leader takeover/TTL expiry与Coordinator写入竞争时，旧事务的Leader Compare失败；
- Admission Lease release/renew/TTL expiry与prepare operation竞争时，活动Lease/request Compare失败；
- scope high-water token与operation记录在同一aggregate中更新；
- PUBLISH sequence分配和幂等索引同一revision CAS，不会从并发调用中重复分配；
- 没有独立 Coordinator SQLite表与Admission KV表之间的双写窗口。

注意：这些比较保护的是当前Store backend承诺的线性一致性与Txn原子性。真实etcd quorum、网络分区和多主机故障语义仍待真实集群验证。

## 9. 测试与 CI

新增8个契约测试方法，在SQLite `SQLiteCoordinatorAuthorityStore` 与 `EtcdV3CoordinatorAuthorityStore`（由单进程 `InMemoryEtcdV3Client` 提供测试替身）上分别执行，共16次新增适配器测试执行，覆盖：

1. ACTIVATE → PUBLISH → REVOKE完整本地Provider合成流程；
2. Leader TTL到期、epoch takeover和旧Leader fencing；
3. 活跃Leader互斥及renew不改变epoch；
4. tenant scope隔离、request idempotency和Admission Lease有效性；
5. 多线程并发PUBLISH sequence唯一性与重放；
6. restore外部高水位/sequence floor与RECOVERY_REVIEW；
7. Admission与Coordinator状态确实驻留在同一Aggregate；
8. proof signing拒绝伪造/篡改的operation owner等身份字段。

最终代码提交 `3d79149c1112550b4fb25efbe02b5f536b08cacd`；[GitHub Actions Run 45810737444](https://github.com/rexyll/cnc-knowledge/actions/runs/45810737444)两个必需Job均completed/success。全库344项unittest、CH12数值资源143项测试通过；strict knowledge lint 0 errors；知识结构与数据质量0 errors。恢复场景另验证外部floor之后显式新ACTIVATE取得floor+1 token并保持PENDING_ACTIVATION。CI只验证仓库内合成适配器路径。

ASSET-000086定义30条 Coordinator统一事务场景，全部 `PROPOSED_NOT_APPROVED / NOT_RUN`。

## 10. 尚未完成的生产迁移边界

本轮没有替换 `SQLiteDurableCoordinatorAuthority` 或旧 `SQLiteProviderAdmissionCoordinator`。尚未完成：

- 旧SQLite Leader/scope/operation表与旧Admission lease/waiter的迁移工具及可回滚 cutover；
- v1 unified aggregate到v2 schema的生产数据迁移；
- 真实etcd Gateway/gRPC、mTLS/RBAC、quorum、网络分区、keepalive丢失和多主机故障注入；
- 真实对象存储Provider的proof验证、conditional write、回执和generation集成；
- 单aggregate热点、operation ledger无界增长、Txn请求体与Compare数量的容量/性能上限测量；
- operation ledger保留/归档策略以及恢复演练的企业审批。

v2 aggregate仍然是全局串行写入点。Coordinator operations与scopes在aggregate内持续增长，不能无限扩展；后续需要设计有证明的operation归档、scope分片/全局epoch和容量约束，而不是简单把数据拆成多个键。

## 11. 生产治理状态

```text
production_backup_enabled = false
governance_readiness = BLOCKED_PENDING_ENTERPRISE_APPROVAL
business_rule_assertions = NOT_EVALUATED
```

## 12. 来源

- SRC-000391、SRC-000392：SQLite事务及WAL参考。
- SRC-000397、SRC-000398：etcd v3线性一致Range、KV Txn与Lease API。
- KNOW-000051、KNOW-000052：原 Coordinator authority store及事务读写接口。
- KNOW-000054：统一Admission scheduler aggregate及配额状态参考。
