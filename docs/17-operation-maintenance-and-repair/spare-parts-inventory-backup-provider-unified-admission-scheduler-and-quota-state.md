# 备件库存备份 Unified Admission Scheduler 与配额状态统一事务模型

**知识编号：** KNOW-000054  
**章节：** CH17 操作、维护与维修  
**状态：** 后端无关统一调度参考实现已通过仓库CI；尚未接入生产Admission/Coordinator  
**关联知识：** KNOW-000050、KNOW-000051、KNOW-000052、KNOW-000053  
**关联资源：** ASSET-000085

## 1. 本轮目标

第三十九轮只把Admission lease生命周期抽象到KV/Txn/Lease端口；旧Admission SQLite服务仍在SQL事务中维护等待队列、公平调度、全局/租户配额、策略指纹、幂等和lease签发。若lease迁到一个store、容量计数仍留在旧SQLite，两个写事务之间就可能出现配额超卖或已撤销lease仍占用/释放容量的时序问题。

第四十轮新增 `StoreBackedProviderAdmissionCoordinator`，将Admission scheduler的策略、fencing counter、活动Lease集合、等待队列、waiter序号和调度指标归并为一个revisioned aggregate state，并使用同一 `CoordinatorAuthorityStore` 的Txn与TTL Lease维护活动键、request_id幂等索引。其目标是先提供一个跨SQLite/etcd适配器可运行的一致性参考模型，而不是声称旧Admission Coordinator已迁移。

## 2. 模块与键空间

实现：`scripts/spare_parts_provider_unified_admission_store.py`  
测试：`tests/test_spare_parts_provider_unified_admission_store.py`  
核心类型：`StoreBackedProviderAdmissionCoordinator`

本轮使用独立命名空间 `/cnc/admission/unified/v1/`，避免与第三十九轮独立 `StoreBackedAdmissionLeaseAuthority` 的 `/cnc/admission/v1/` 参考键冲突。两个原型不能对同一个业务Admission范围并行写入，也不构成双写迁移方案。

| 键 | 生命周期 | 内容/职责 |
|---|---|---|
| `/cnc/admission/unified/v1/scheduler/state` | 持久、revision CAS | 全域策略指纹、global/tenant quota、活动lease记录、全局waiter数组、fencing/waiter序号和统计 |
| `/cnc/admission/unified/v1/leases/<sha256(lease_id)>` | Store TTL Lease | 活动lease权威记录；TTL到期时由后端删除 |
| `/cnc/admission/unified/v1/requests/<sha256(request_id)>` | 持久 | request identity、lease、fencing token及ACTIVE/RELEASED/EXPIRED终态索引 |

Scheduler aggregate中每一个活动记录必须与活动Lease键和持久request索引的规范化记录字节相匹配。每次影响容量、等待队列或lease生命周期的事务都比较aggregate的mod_revision，并对当前活动lease/request索引追加精确值比较。这样活动键的TTL到期、release或renew发生在读取和写入之间时，原事务比较会失败，而不能使用陈旧活动集合提交新的配额决策。

## 3. 单aggregate状态模型

Aggregate状态保存：

- 不可变策略指纹 `policy_hash`、全局domain limits、tenant-specific overrides、最大等待队列长度和aging interval；
- 全局单调 `next_fencing_token` 与 `next_waiter_sequence`；
- 全部domain的活动Admission lease map；
- 跨domain的有界waiter数组；
- issued、expired、released、capacity-rejected、queue-rejected计数。

所有scheduler状态更新通过同一个aggregate键序列化。它是本轮选择的“先保证原子语义、再评估分片”的正确性基线：不需要在多个domain计数键、多个队列键和lease表之间维持跨键聚合协议，且SQLite与etcd适配器共用相同的CAS/Txn行为。

**代价：** 所有domain的入队、出队、续租和释放都竞争同一个aggregate键，写入会串行化；每次Txn还需要比较当前活动Lease集合。该设计会限制吞吐量，状态体积及Compare数量随活动Lease与waiter数量增长，不能视为高并发生产调度器。后续分片必须保留全局配额、跨tenant策略和公平队列的原子证明，不能仅把键按domain切开就宣称安全。

## 4. Acquire：容量核算和Lease签发一次事务提交

`acquire()` 的过程：

1. 校验request_id、owner、task、tenant和domain；每次轮询均重新调用 `check_task`，检查任务取消/外部准入条件。
2. 线性一致读取aggregate。通过活动lease键和request索引的精确读取识别过期、缺失或不一致记录；将已过期lease转为EXPIRED tombstone，并移除活动集合中的占用。
3. 基于同一个aggregate快照计算该domain活动总数、tenant活动数和等待者集合。未单独配置tenant limit的tenant继承该domain的global limit。
4. 将等待者按 `priority + waiting_age / aging_interval` 排序；分数相同优先较早的waiter sequence。全局max_waiters约束所有domain的等待队列总量。
5. 若容量允许且当前request是被选中的waiter，则分配新fencing token、生成lease identity并申请backend TTL Lease。
6. 一个Txn同时比较aggregate revision、所有现存活动Lease/request索引、目标request索引不存在及新lease键不存在；成功分支写入更新后的aggregate、TTL附着的活动lease键和持久request索引。只有一次Txn成功才算取得准入。
7. CAS失败者重新读取最新aggregate并重算容量，不允许继续使用旧计数或旧token；申请到但未附着的backend TTL Lease会撤销或自行到期。

因此，全局domain capacity与tenant quota不再分别依赖单独的计数器更新，而是在同一个串行化状态快照下计算，并以aggregate revision与所有活动lease精确比较保护其有效性。

## 5. Waiter、公平调度与容量边界

- Waiters存在同一个跨domain数组；因此 `max_waiters` 是全局上限，不会在多个domain各自达到上限后再叠加超出。
- 一个domain容量可用时，只允许该domain按priority与aging排序选出的waiter进入；tenant quota已满的waiter不参与该domain当前eligible集合。
- acquire timeout后，waiter从aggregate中删除；任务检查回调抛错时也会走清理路径。
- 等待者的deadline过期时，后续状态更新会清理过期waiter；`snapshot()` 和 `reclaim_expired()` 可触发过期状态整理。
- timeout=0的请求不进入持久wait队列；若当前没有可用容量则fail-fast。
- request_id只在实际签发Lease时写入永久幂等索引；同request_id的同一身份重放返回相同Lease，已释放/过期的request_id拒绝复用。

## 6. Renew / Release与受保护Authority事务

### Renew

续租在同一个Txn中比较aggregate revision、旧活动Lease精确值及旧request索引，将aggregate里的活动记录、活动Lease键和request索引一起更新为新的expires_at/backend TTL Lease。fencing token保持不变，旧调用方对象由于expires_at改变而失效。新backend TTL lease在事务未能提交时只是未附着的短暂Lease；若Txn结果unknown，组件保留候选TTL以便同lease ID重读恢复，不将潜在已提交的Lease误撤销。

### Release

释放在一个Txn中删除活动Lease键、从aggregate活动集合移除记录并将request索引改成RELEASED tombstone。成功后再撤销backend TTL lease。release与受保护authority写发生竞争时，由同一存储端的Compare决定顺序。

### Authority guard

`active_lease_compares(lease)` 返回活动Lease键及持久request索引的精确值比较；调用方将这两项与Leader epoch、scope revision、operation idempotency等比较一起传给同一个 `CoordinatorAuthorityStore.transact()`。单独validate后再发起独立authority写不是同等保证。`transact_with_active_lease()` 提供快捷调用路径。

## 7. 幂等、过期和OUTCOME_UNKNOWN

- Acquire遇到Txn响应丢失时，按同一request_id线性一致重读request索引、活动Lease键和aggregate活动记录；三者完全匹配才恢复为成功。
- 若读回也不可用，返回 `ProviderCoordinatorUnavailableError(reservation_outcome_unknown=True)`。不能生成新request_id重放。
- Renew结果unknown时，只有活动Lease键和request索引均与候选新值完全匹配才报告续租成功；否则保持unknown。
- Release结果unknown时，以永久request索引中的RELEASED tombstone恢复状态。
- backend TTL过期删除活动键后，后续scheduler写事务使用VERSION==0比较，清除aggregate的过期活动记录并写入EXPIRED request tombstone。若旧活动键已被删除，容量才会在新的CAS事务中释放。
- 若aggregate与lease/request索引无法一致解释，模块fail-closed，不会推断活动Lease有效。

## 8. 适配器测试和CI

新增六个跨适配器测试方法，在SQLite `SQLiteCoordinatorAuthorityStore` 和 `EtcdV3CoordinatorAuthorityStore`（使用单进程 `InMemoryEtcdV3Client` 测试替身）上各运行一次，共12次适配器测试执行。覆盖：

1. 多实例global/tenant capacity原子约束；
2. priority + aging公平排队；
3. 全局waiter上限及队列清理；
4. 过期Lease清理后容量恢复；
5. renew/release与同Txn authority guard；
6. 同request_id幂等并发及不同request_id竞争不超卖。

代码最终提交 `34023050272f41c725396d1737ea4b394c22cf3d`；[GitHub Actions Run 45778008494](https://github.com/rexyll/cnc-knowledge/actions/runs/45778008494)两个必需Job均completed/success。全库328项unittest、CH12数值资源143项测试通过；strict knowledge lint 0 errors；知识结构与数据质量0 errors。该CI证明仓库合成适配器路径，不证明真实etcd集群、生产容量或企业场景通过。

ASSET-000085定义24条统一scheduler场景，全部 `PROPOSED_NOT_APPROVED / NOT_RUN`。

## 9. 与旧Admission系统及第四十轮以后迁移的边界

本轮组件使用独立 `/cnc/admission/unified/v1/` 命名空间，不能与第三十九轮 `StoreBackedAdmissionLeaseAuthority` 原型或旧 `SQLiteProviderAdmissionCoordinator` 对同一业务范围并行写入。它是候选统一状态模型，不是线上自动切换器。

尚未完成：

- 旧SQLite scheduler的真实数据导入、活动lease/waiter恢复、policy hash校验和一次性cutover；
- `SQLiteDurableCoordinatorAuthority` 的Leader epoch、scope token、operation ledger及其状态迁移，尚未同此scheduler状态写入同一Txn；
- 远程etcd gRPC/JSON Gateway、mTLS/RBAC、租约keepalive监控、quorum/网络分区/多主机故障演练；
- Provider proof签发/撤销/对象提交的真实端到端集成；
- 单aggregate热点的吞吐测试、状态尺寸/Txn compare上限测试、分片与全局配额保持策略。

切换时必须停掉旧、新两边的写入口，执行带外部fencing high-water校验的受控迁移，再启用单一权威写入路径。禁止在两个scheduler间双写以“保证一致”。

## 10. 生产治理状态

本轮没有启用生产备份或改变企业业务规则状态：

```text
production_backup_enabled = false
governance_readiness = BLOCKED_PENDING_ENTERPRISE_APPROVAL
business_rule_assertions = NOT_EVALUATED
```

## 11. 来源

- SRC-000391、SRC-000392：SQLite事务及WAL参考。
- SRC-000397、SRC-000398：etcd v3线性一致Range、KV Txn和Lease API。


### 文档同步CI验收

文档同步提交 `87d749147d2c32da547ce23ed56db69725271a00`；[GitHub Actions Run 45778328441](https://github.com/rexyll/cnc-knowledge/actions/runs/45778328441)两个必需Job均completed/success。全库328项unittest、CH12 143项数值资源测试通过；strict knowledge lint 0 errors；知识结构与数据质量0 errors（报告包含5条非阻断warning）。该结果不改变ASSET-000085的24条场景 `PROPOSED_NOT_APPROVED / NOT_RUN` 状态，也不构成真实etcd或企业Admission验收。


### 第四十轮最终文档同步说明

文档同步提交 `87d749147d2c32da547ce23ed56db69725271a00`；[GitHub Actions Run 45778328441](https://github.com/rexyll/cnc-knowledge/actions/runs/45778328441)两个必需Job均completed/success。全库328项unittest、CH12 143项数值资源测试通过；strict knowledge lint 0 errors；知识结构与数据质量0 errors（报告包含5条非阻断warning）。ASSET-000085的24条场景继续保持 `PROPOSED_NOT_APPROVED / NOT_RUN`。
