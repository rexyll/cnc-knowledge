# 旧 SQLite Coordinator / Admission 到 Unified schema-v2 迁移审计与切换设计

> 状态：代码审计与设计完成；生产数据盘点、迁移实现和切换均未执行。  
> 范围：旧版同机 SQLite Admission / Coordinator 状态迁移至现有 Unified schema-v2；不是 schema-v2→v3 operation archive 迁移。

## 1. 结论

仓库存在两代业务实现，但尚无已验证的SQLite历史数据导出、导入、冻结、回滚和生产cutover流程。

- 来源Admission：scripts/spare_parts_provider_admission_sqlite.py 中的 SQLiteProviderAdmissionCoordinator。
- 来源Coordinator：scripts/spare_parts_provider_coordinator_authority.py 中的 SQLiteDurableCoordinatorAuthority。
- 目标：scripts/spare_parts_provider_unified_admission_store.py 中的 StoreBackedProviderAdmissionCoordinator，以及 scripts/spare_parts_provider_unified_coordinator_authority.py 中的 StoreBackedCoordinatorAuthority。
- 两个目标服务共同使用 /cnc/admission/unified/v2/scheduler/state schema-v2 aggregate，并通过同一个 CoordinatorAuthorityStore 事务维护业务状态。
- 本轮只读仓库代码，不访问生产SQLite，不创建目标生产namespace，不执行任何业务写冻结、迁移或authority切换。

## 2. 来源Schema审计

### 2.1 Admission

SQLiteProviderAdmissionCoordinator 初始化以下对象：

| 表 | 关键字段/语义 | 目标映射 |
|---|---|---|
| coordinator_meta | schema_version、policy_hash、next_fencing_token、issued_leases、expired_leases、rejected_capacity、rejected_queue、attestations_issued等键值 | aggregate策略、计数器、全局fencing floor |
| admission_requests | request_id、lease_id、owner_id、task_id、tenant_id、domain、fencing_token、绝对Unix expires_at、ACTIVE/RELEASED/EXPIRED | active、持久request幂等/终态索引、全局token floor |
| admission_waiters | AUTOINCREMENT sequence、request_id、owner/task/tenant/domain、priority、queued_at、expires_at | 有序waiters，必须保留顺序和过期语义 |

源码中的过期处理会把过期ACTIVE request置为EXPIRED、增加计数，并删除过期waiter。导入不能恢复过期租约，也不能无声丢弃request终态幂等记录。

### 2.2 Coordinator

SQLiteDurableCoordinatorAuthority初始化以下对象：

| 表 | 关键字段/语义 | 目标映射 |
|---|---|---|
| coordinator_authority_meta | schema_version | 检查支持的来源版本 |
| coordinator_authority_leader | singleton、leader_id、epoch、expires_at、UNCLAIMED/ACTIVE/FENCED | aggregate coordinator.leader及TTL Leader key；只迁移epoch floor，不复活旧Leader |
| coordinator_authority_scopes | scope、high_water_token、lease identity/expiry/state、latest_operation_sequence、provider_generation、updated_at | coordinator.scopes |
| coordinator_authority_operations | scope/idempotency_key、kind、request_sha256、token、sequence、lease identity、manifest key/hash、state、Provider generation、时间戳 | coordinator.operations |

Coordinator来源schema当前版本为1。现场迁移前必须对实际数据库执行只读schema探测，确认列、索引、约束、SQLite版本、PRAGMA、WAL状态和文件一致性；本文不能替代现场数据盘点。

## 3. 必须保持的不变量

1. Admission全局next_fencing_token不得低于来源meta值、所有request最大token和外部Provider high-water。
2. 每个scope的high_water_token与latest_operation_sequence分别不得低于来源scope、该scope操作历史和外部Provider/归档索引权威floor。
3. Leader epoch只作为恢复下限导入；目标必须重新claim，epoch严格高于旧epoch和外部reconciliation floor。旧Leader必须被Provider fencing拒绝。
4. 保留request_id、(scope,idempotency_key)、request_sha256及终态记录；相同key不同payload继续冲突。
5. 活动租约保留lease_id、owner/task/tenant/domain/token/绝对expiry；仅剩余TTL为正且目标TTL key成功创建后才可标ACTIVE。
6. waiter保留sequence、priority、queued_at、expires_at和原策略配置，不得重新排序。
7. PENDING_ACTIVATION、REVOKING、PENDING_PUBLISH、RECOVERY_REVIEW等未决状态原样保留并进入reconciliation，不自动确认成功或重放外部副作用。
8. 保留Provider generation、manifest key/hash和外部对象引用；SQLite记录不能单方面证明Provider实际状态。
9. policy_hash必须与批准的目标配置匹配；逐字段保留和对账计数器，不得通过覆盖hash掩盖策略变化。

## 4. TTL转换

固定冻结时刻 Tf，对每个来源租约计算 remaining = expires_at - Tf。

- remaining <= 0：不创建目标TTL Lease；request按过期终态导入。
- remaining > 0：只按剩余时间请求目标Lease，记录Store实际Granted TTL和服务端Lease ID；不得重新授予完整原始TTL。
- 若服务端最小Granted TTL会使实际租约超过来源绝对deadline，必须拒绝该活动租约迁移，或由应用层绝对deadline强制阻断过期操作。不能静默延长租约。
- waiter按同一冻结时刻判断是否仍有效；过期waiter不进入目标队列，但request终态/审计索引按来源语义保留。
- 时钟偏差、回拨或时间源不确定时fail-closed；记录冻结时间及时间源。

## 5. 推荐迁移协议

### Phase A：只读盘点
取得数据库路径/文件系统、SQLite版本、PRAGMA、WAL checkpoint状态、表行数、schema版本、策略配置、进程清单；统计主键/唯一键冲突、孤儿记录、非法状态、过期租约、waiter顺序、最大记录尺寸。只读取得Provider各scope generation、fencing token floor、operation sequence floor和manifest审计。未知schema、外部floor缺失或记录无法解释时停止。

### Phase B：隔离预演
对生产数据库的一致性副本演练，源端只读，不触达Provider写接口。按批准配置计算policy_hash，生成确定性映射和snapshot digest；重复导入两次并比较规范化摘要。注入进程中断、Txn结果未知和重复请求；未知结果必须先读回目标状态，不得盲目重试Lease创建或外部副作用。

### Phase C：冻结与快照
停止Admission新请求、队列消费者和Coordinator workers；阻断所有写入口并撤销/隔离旧进程写凭证；确认无活动事务和写连接。执行一次逻辑过期结算，WAL checkpoint后通过SQLite backup API或等价一致性机制取得快照。禁止只复制正在写入的主数据库而遗漏WAL。记录冻结时间、schema、文件摘要、各表行数/键集合摘要、meta、Provider floors及未决操作。冻结后任何源端写入都使snapshot失效，必须重新冻结和取样。

### Phase D：构建候选目标
使用隔离的全新Unified namespace；Admission与Coordinator作为一个逻辑整体导入同一aggregate事务。Leader只导入epoch floor并保持未claim。活动Lease按剩余TTL创建目标Lease，aggregate记录、request索引和TTL key必须满足目标Store原子Txn边界。若Txn操作数、compare数量或请求体大小不能容纳导入，必须设计显式分批checkpoint；业务写入保持冻结。任何Txn结果未知，先线性一致读回aggregate revision、目标key和checkpoint判断是否提交。

### Phase E：逐项校验
- 表级行数、状态计数、request_id、lease_id、waiter sequence、scope和operation键集合精确对账。
- 幂等重放结果相同，不同payload冲突；终态request记录可查询。
- 全局和逐scope fencing/sequence floors满足来源与外部Provider权威值。
- operation状态、request SHA、manifest hash、Provider generation逐条一致；未决操作为零，或有明确恢复批准、责任人及方案。
- 活动租约目标TTL符合冻结时剩余时间；无幽灵TTL key、意外延长或孤儿索引。
- waiter顺序、配额占用、过期行为及policy_hash匹配。
- 目标通过线性一致读回；目标aggregate digest与迁移manifest一致。
- Provider只读核验所有scope的generation与fencing floor。外部floor不可用即阻断切换。
- 输出完整SHA-256审计报告，由业务、Provider、安全和运维责任人共同批准。

## 6. 单权威切换与回滚

### 6.1 Cutover
保持入口停写；冻结迁移manifest和验证报告；将唯一写入口切到Unified Coordinator；旧SQLite凭证撤销或只读化；新后端重新claim Leader，epoch高于旧epoch与外部reconciliation floor；验证Provider fencing后才开放受控流量。恢复业务前必须负向验证旧进程无法写入。禁止双写或按请求随机路由两个权威。

### 6.2 Rollback
- Unified尚未接受任何业务mutation：在停写状态下撤销目标Leader/TTL Lease，确认Provider没有外部副作用后，可恢复到冻结且未变化的SQLite快照。
- Unified接受第一笔业务mutation后：禁止直接回指旧SQLite快照。必须停写、导出Unified完整状态、对账Provider、保留新增幂等键/操作、提升token/sequence/epoch floors，构建并验证反向迁移候选库；若旧格式无法表达新状态或容量不足，只能向前修复。
- 回滚不得倒退Provider generation、manifest commit、ACTIVATE/REVOKE副作用或已签发fencing proof。数据库恢复不等于外部业务状态恢复。

## 7. 风险与阻塞

| 风险 | 缓解/门禁 |
|---|---|
| 单aggregate导入体积、Txn compare/operation数量、请求体上限 | 先测实际数据规模与etcd限制；必要时单独设计受审查的分批checkpoint，不擅自拆分权威 |
| 永久request/operation幂等历史导致aggregate增长 | 盘点历史量并评估现有archive index；不得丢弃幂等键 |
| SQLite WAL快照不一致 | 冻结、checkpoint、SQLite backup API和文件摘要 |
| TTL Grant大于剩余TTL | 拒绝迁移活动租约或应用绝对deadline兜底 |
| 未决Provider操作 | 人工reconciliation，不自动确认或重放 |
| 外部fencing floor缺失 | Provider只读对账不可用即阻断切换 |
| 双权威/旧进程残留 | 停写、撤销凭证、进程退出与负向验证 |
| Txn结果未知 | 线性一致读回、checkpoint与确定性幂等恢复 |

必须从真实目标数据库盘点的未知量：表行数、最大记录尺寸、request/operation总量、活跃/过期租约数、waiter峰值、scope数、外部Provider floors、WAL大小和可接受停写窗口。不能用单元测试fixture推断。

## 8. 任务状态

| 任务 | 内容 | 状态 |
|---|---|---|
| MIG-01 | 来源schema与目标schema代码审计、字段映射 | DONE（代码审计；现场数据未盘点） |
| MIG-02 | 冻结、TTL、校验、cutover与回滚设计 | DONE（设计；未获生产批准） |
| MIG-03 | 只读SQLite inventory/export及snapshot manifest | DONE（工具、单元测试、Quality CI通过） |
| MIG-04 | Unified schema-v2 candidate importer、分批和未知结果恢复 | TODO |
| MIG-05 | 映射、fencing、幂等、TTL与故障注入测试 | TODO |
| MIG-06 | 临时真实etcd迁移及反向迁移演练 | TODO |
| MIG-07 | 容量、停写窗口、Provider owner及生产审批 | BLOCKED |

## 9. 证据边界

本审计基于仓库中的SQLite Admission、SQLite Coordinator、Unified Admission、Unified Coordinator和CoordinatorAuthorityStore实现。第七十一轮三节点etcd Live仅验证目标业务路径，不覆盖SQLite历史数据导入。本文件是工程设计，不是生产操作授权；现场执行前必须取得变更批准并完成正式矩阵审批。


## 10. MIG-03：只读 Inventory / Logical Export 工具

新增脚本：`scripts/spare_parts_sqlite_migration_inventory.py`。

### 10.1 安全模型

- 不实例化SQLite Admission/Coordinator服务类，因为它们的构造函数会创建目录、切换WAL或初始化schema。
- 使用SQLite URI `mode=ro` 打开现有文件，并设置连接级`PRAGMA query_only=ON`；在单个只读事务中读取schema、表记录、元数据与完整性检查。
- 不调用`_expire_locked()`，不修改ACTIVE/EXPIRED状态，不删除waiter，不写meta，不触达Provider或etcd。
- 扫描前后计算主数据库和WAL文件SHA-256/大小/mtime；若扫描期间文件变化，报告warning并要求在写冻结后重跑。
- 默认仅输出表级摘要和规范化行摘要；显式传入`--records-output`才导出完整业务行。完整records文件采用原子替换并设置0600权限，因其中包含owner/task/tenant/request/manifest等运行标识，必须存放在受控目录。
- snapshot digest由schema、表级行数/行摘要、元数据和Leader持久状态组成，不依赖扫描时刻；它不是SQLite物理备份，也不替代冻结后的SQLite Backup API快照。

### 10.2 检查内容

- 两组来源表及必需列、Admission/Coordinator schema_version。
- SQLite integrity_check、foreign_key_check、journal_mode。
- 每表行数、主键排序、状态分布、关键数值字段min/max与规范化SHA-256。
- Admission活动/已到期但仍标记ACTIVE的行、过期waiter、全局fencing token floor。
- Coordinator scope数、operation孤儿、pending operation数量、request/manifest SHA格式、每scope fencing token与operation sequence高水位。
- source DB/WAL扫描前后指纹变化。

### 10.3 使用方式

只生成摘要清单：

```bash
python scripts/spare_parts_sqlite_migration_inventory.py \
  --database /secure/path/legacy-coordinator.sqlite3 \
  --output resouces/17-operation-maintenance-and-repair/sqlite-migration-inventory.json
```

需要逻辑行级导出时显式增加：

```bash
python scripts/spare_parts_sqlite_migration_inventory.py \
  --database /secure/path/legacy-coordinator.sqlite3 \
  --output resouces/17-operation-maintenance-and-repair/sqlite-migration-inventory.json \
  --records-output resouces/17-operation-maintenance-and-repair/sqlite-migration-records.json
```

退出码0表示未发现工具定义的完整性错误；退出码2表示输入/Schema/完整性错误。即使发现完整性错误，仍会写出可诊断的inventory manifest（若源Schema足以完成扫描）。warning不自动等于安全通过，尤其journal_mode非WAL或扫描期间DB/WAL发生变化时，应由迁移负责人判断并在冻结后复扫。

### 10.4 限制

MIG-03只提供只读逻辑盘点与可选JSON记录导出；不创建SQLite物理备份、不执行写冻结、不探测Provider外部fencing floor、不导入Unified schema-v2，也不证明数据可以安全迁移。records export应视为敏感运维数据，不能提交到Git或公共资源目录。
