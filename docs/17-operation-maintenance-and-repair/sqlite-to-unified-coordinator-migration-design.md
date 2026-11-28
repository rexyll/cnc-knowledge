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
| MIG-04 | Unified schema-v2 candidate importer、分批和未知结果恢复 | IN_PROGRESS（候选包、隔离namespace、空空间预检、单Txn只读规划完成；实际写入/恢复未完成） |
| MIG-05 | 映射、fencing、幂等、TTL与故障注入测试 | IN_PROGRESS（分阶段导入内存adapter事务契约与未知结果恢复已部分验证；完整映射/fencing/TTL与真实etcd验证未完成） |
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


## 11. MIG-04：候选导入包生成器（首阶段）

新增脚本：`scripts/spare_parts_sqlite_candidate_importer.py`，专用测试：`tests/test_spare_parts_sqlite_candidate_importer.py`。

### 11.1 本阶段交付边界

本阶段生成**候选导入包**，不直接写入etcd或任何CoordinatorAuthorityStore，也不创建生产namespace。原因是目标store当前使用固定的`/cnc/admission/unified/v2/`前缀，尚无可注入namespace的构造参数；在namespace隔离能力和事务/Lease写入恢复协议落实前，不能把“候选导入”实现成直接KV写入。

候选包中的target namespace保持未设置，要求后续写入器显式选择并验证全新隔离namespace；`production_write_allowed=false`。当前脚本不具备任何生产写入路径。

### 11.2 输入与完整性验证

必须同时提供MIG-03 manifest、records导出和策略JSON：

```bash
python scripts/spare_parts_sqlite_candidate_importer.py \
  --manifest /secure/path/sqlite-migration-inventory.json \
  --records /secure/path/sqlite-migration-records.json \
  --policy /secure/path/admission-policy.json \
  --output /secure/path/unified-candidate-bundle.json
```

策略JSON必须包含且仅包含`global_limits`、`tenant_limits`、`max_waiters`、`aging_interval_seconds`；按目标Unified实现的规范化规则计算policy hash，并与来源Admission meta严格相等。不能从单向hash推导原策略，也不能用默认值覆盖来源策略。

工具逐表重算records行数与规范化SHA-256，并重新计算manifest snapshot digest；检查来源格式、完整性PASS、扫描期间DB/WAL未变化、表集合和必需列。任一输入不匹配均fail closed。

### 11.3 当前支持的候选范围

- 仅接受已排空的来源快照：不存在ACTIVE Admission request、waiter或PENDING_ACTIVATION/REVOKING/PENDING_PUBLISH/RECOVERY_REVIEW operation。
- 拒绝仍标记ACTIVE但已过期的Admission行；必须在批准的冻结/清理流程后重新inventory，工具本身不清理来源。
- 保留全局Admission fencing floor、每scope fencing/operation sequence floor、终态request幂等索引、Coordinator scope/operation历史、Provider generation和manifest引用、策略及可映射计数器。
- 不恢复旧Leader；只输出Leader epoch恢复下限，目标必须重新claim。
- 非IDLE/REVOKED的scope进入`RECOVERY_REQUIRED`，不伪装成空闲。
- 终态request索引需要满足Unified内部record schema中的正backend_lease_id字段；候选包使用保留值1作为**仅终态索引占位符**，明确声明它不是原生Lease ID、不得附着或撤销Lease。活动租约不进入候选state。
- 外部Provider fencing floor无法从SQLite证明，候选包将`external_fencing_reconciliation=REQUIRED`且floor为null；在只读核对并批准前不得激活候选。

### 11.4 当前不支持/后续门禁

MIG-04首阶段不是完整导入器：它不创建目标TTL Lease、不写request/state key、不执行分批事务、不建立目标checkpoint，也不处理写入Txn结果未知的恢复。目标namespace隔离、目标Lease分配和原子事务容量评估必须在后续实现中补齐；候选包不能直接喂给生产Store。MIG-05需补齐状态映射/幂等/高水位/故障注入验证，MIG-06才允许在一次性临时etcd集群演练完整写入与恢复。

## 12. MIG-04：隔离命名空间注入（第七十五轮）

Unified Admission Scheduler新增可选构造参数`namespace_prefix`：

- 不传参数时，仍使用既有`/cnc/admission/unified/v2/`，保持现有部署与测试键路径不变。
- 迁移预演自定义值必须位于`/cnc/migration/isolated/{namespace-id}/`，namespace-id只能是一个可打印ASCII路径段；拒绝生产前缀、空ID、多段路径、控制字符及路径穿越。
- Scheduler State、Admission Lease key、Request幂等索引统一从实例prefix派生。
- Unified Coordinator的Leader TTL key改为从传入Scheduler的实例prefix派生，确保Leader与Admission aggregate处于同一隔离键空间。
- 两个不同隔离namespace必须完全分离；默认namespace必须与历史版本兼容。

本轮仅增加键空间路由与输入门禁。它不验证调用者拥有的etcd RBAC是否只允许该namespace，不会自动创建namespace或校验namespace为空，也不写候选状态。后续写入器必须在启动前使用独立临时etcd凭证，并对目标prefix做线性一致空空间检查；不能把“字符串prefix受限”误认为后端权限隔离。

### 12.1 当前未覆盖的写入安全门禁

1. 创建隔离namespace时必须显式提供唯一演练ID，目标前缀不得复用历史数据。
2. 对目标prefix做线性一致Range空空间检查；发现任意键即停止，不覆盖、不清理。
3. 迁移专用凭证应由etcd RBAC限制在目标prefix及必要Lease API；本地参数校验不能代替服务端权限。
4. Admission State、request terminal indexes、Coordinator scopes/operations与Leader epoch floor必须在一个受控导入协议中恢复；旧Leader TTL key不得恢复。
5. 活动Lease目前不在候选bundle范围内；后续若支持活动Lease，必须按冻结剩余TTL逐一创建native Lease，并证明Granted TTL不延长来源deadline。
6. 尚未实现事务容量/分批checkpoint/Txn未知结果恢复。本轮代码不得用于导入任何生产数据。

## 13. MIG-04：隔离目标空空间预检（第七十六轮）

新增`scripts/spare_parts_migration_namespace.py`：

- `validate_isolated_namespace(prefix)`仅允许`/cnc/migration/isolated/{single-id}/`单段ASCII namespace ID；拒绝生产schema-v2前缀、空ID、多段路径、控制字符、空格和路径穿越。
- `preflight_empty_namespace(store, prefix)`调用`EtcdV3CoordinatorAuthorityStore.linearizable_range()`，对prefix对应的完整字节区间做线性一致Range。只要返回至少一个KV，即拒绝继续；Range错误/连接错误不允许被解释成空空间。
- 成功时返回`NamespacePreflight(prefix, revision, existing_key_count=0)`，供后续审计记录使用。

### 13.1 预检的安全边界

空空间预检仅证明在该次线性一致Range的读取revision上没有匹配键。它**不是锁**，不能防止预检完成后其他客户端创建键，也不能证明调用凭证只拥有目标prefix权限。正式迁移写入器必须同时满足：

1. 使用专用、短期、最小权限的etcd凭证，服务端RBAC限制在该演练prefix；
2. 最好使用一次性临时etcd集群，确保不存在其他写入者；
3. 将目标prefix唯一ID、Range revision、集群身份和凭证身份写入演练记录；
4. 写入前后均核验目标范围，任何范围外写入/意外键均中止；
5. 不得将此预检作为生产写入许可或cutover审批。

本轮仅新增只读预检与内存客户端Range语义测试；不创建namespace、不写入KV、不创建Lease、不导入候选包。

## 14. MIG-04：单 Txn 候选导入容量计划（第七十七轮）

新增只读脚本：
`scripts/spare_parts_sqlite_candidate_import_plan.py`。

### 14.1 目标键与原子写入集合

对于隔离前缀 `P=/cnc/migration/isolated/{id}/`，当前schema-v2实现的导入写集合为：

- Aggregate：`P + scheduler/state`，包含Admission策略、全局fencing floor、计数器，以及Coordinator Leader（保持null）、scopes与operations。
- 终态request幂等索引：每条候选记录写入 `P + requests/{SHA256(request_id)}`。键派生规则与Scheduler实例方法一致。
- Leader TTL key：`P + coordinator/leader`只参与`VERSION=0`比较，不写入。旧Leader不恢复；导入完成后必须由新Coordinator重新claim并创建原生Lease。
- 当前候选不包含活动Admission Lease与waiter，因此导入阶段原生Lease Grant数量为0。终态request中的`backend_lease_id=1`只是schema兼容哨兵，不能附着或撤销。

规划器先验证候选摘要、schema-v2 aggregate结构、终态request record schema、request key派生、scope fencing/sequence floors、恢复门禁与记录数量。它为Aggregate、全部终态request key和Leader key生成`VERSION=0`比较条件；在**同一个Txn**中Put Aggregate及所有终态request索引。任何目标键已存在时，整个Txn失败，不覆盖已有值。

### 14.2 容量预算

CLI要求调用者明确提供`--max-txn-ops`和`--max-txn-bytes`，不会猜测或自动读取目标etcd服务端配置：

```bash
python scripts/spare_parts_sqlite_candidate_import_plan.py \
  --candidate /secure/path/unified-candidate-bundle.json \
  --namespace /cnc/migration/isolated/rehearsal-unique-id/ \
  --max-txn-ops 100 \
  --max-txn-bytes 1048576 \
  --wire-safety-margin-bytes 4096 \
  --output /secure/path/unified-import-plan.json
```

- `compare_count`、`put_count`和`compare+put`保守计数分别报告；配置的`max_txn_ops`按比较数与成功分支Put数之和执行应用层预算，避免低估事务复杂度。
- 字节估算按etcd HTTP Gateway Txn JSON请求形状，将KV二进制key/value编码为Base64后计算规范化紧凑JSON字节，并额外加调用者指定的安全余量。它是规划估算，不是从etcd读取到的运行时限制；正式演练仍须确认目标集群的实际`max-txn-ops`、`max-request-bytes`及代理限制。
- 只要操作预算或字节预算任一超出，计划会标记`CAPACITY_EXCEEDED`并以退出码3结束，不输出可执行结论；不得自动拆成多个事务或丢弃终态索引。
- 规划器不连接etcd，不执行Range/Txn/Lease/RBAC操作。它生成的write-set摘要可用于后续写入前后核对。

### 14.3 原子导入门禁与未解决问题

单Txn只有在目标数据完整装入且全部目的键从未存在时才具有本设计要求的原子可见性。写入前仍必须复做线性一致空prefix检查，并用一次性临时集群或服务端RBAC封闭竞态。应用身份在导入与读回验证完成前必须不能访问目标prefix；仅靠“state key暂不存在”不足以阻止Scheduler构造函数创建空aggregate。

若候选超出单Txn预算，当前规划器只会阻断，不会提供分批写入。下一阶段必须先设计并验证staging/checkpoint、未知Txn结果读回、应用启动隔离/权限屏障及最终发布协议，再考虑批处理；不能把一个业务aggregate拆开后提前暴露给应用。外部Provider fencing floor仍须独立对账批准，不能因KV导入成功而自动开放Provider操作。

第七十七轮只新增只读容量规划与单元测试；没有创建目标KV、原生Lease、etcd凭证或RBAC，也没有执行迁移、生产写入或cutover。

### 14.4 第七十七轮验证记录

Quality Run [46027837959](https://github.com/rexyll/cnc-knowledge/actions/runs/46027837959) success：全库582 unittest（40 skipped）、CH12 143项通过、knowledge lint 0 errors/5 warnings、结构检查0 errors。本结果仅验证规划器与仓库质量门禁，不包含任何真实etcd导入或生产变更。

## 15. MIG-04：分阶段索引导入、checkpoint与最终发布协议（第七十八轮）

新增只读协议模型：
`scripts/spare_parts_sqlite_staged_import_protocol.py`，测试位于
`tests/test_spare_parts_sqlite_staged_import_protocol.py`。

### 15.1 分阶段写入顺序

当前Unified schema-v2的Scheduler构造函数会在`scheduler/state`不存在时初始化一个空aggregate。因此，不能先启动应用再逐批导入request索引；这会导致应用抢先创建空state并破坏迁移目标。协议按以下顺序运行：

1. **初始化checkpoint：** 在同一个Txn中比较checkpoint、`scheduler/state`、`coordinator/leader`均不存在，写入初始checkpoint。任何键已存在即停止。
2. **分批写终态request索引：** 按稳定的key顺序将`requests/{SHA256(request_id)}`分成多个batch。每批Txn比较该批所有request key均`VERSION=0`、checkpoint等于精确前驱值、Scheduler state和Leader key仍不存在；同一Txn Put全部request记录及下一版checkpoint。
3. **最终发布aggregate：** 只有所有批次提交、所有终态request key线性一致读回且摘要匹配后，才执行最后Txn。该Txn比较checkpoint精确值、state不存在、Leader key不存在，然后只Put完整`scheduler/state`。state是当前运行时的发布门，不会在前序批次提前出现。

Checkpoint key位于`{prefix}/staging/sqlite-import/{candidate_digest}/checkpoint`。checkpoint内包含plan digest、下一个batch序号、已完成request数量、最近batch digest和累积`progress_sha256`。每次批次事务同时推进request索引和checkpoint，因此不会出现“索引写入成功但进度未记录”或相反的有效Txn状态。

### 15.2 预算与不可分割对象

在compare/put保守计数口径下：

- 初始化Txn：3 compares + 1 put。
- 含N条request的batch：N个request不存在性compare，加checkpoint前驱值compare及state/Leader不存在性compare；Put N条request及1条checkpoint，即compare+put为`2N+4`。
- 最终发布Txn：3 compares + 1 put。

每个Txn均独立计算紧凑Gateway JSON请求体字节数并加入调用者配置的安全余量。批次按操作数和字节预算贪心分段；单条request也无法放入batch时直接拒绝。Scheduler aggregate仍然是**单个不可拆分KV值**：若它无法放入最终发布Txn，协议在任何staging写入前拒绝，必须先对schema/runtime实施分片设计，不能把部分aggregate暴露给应用。

本阶段候选只含终态request，因此不产生Admission Lease Grant。旧Leader TTL key始终只比较不存在，不导入；重新claim Leader发生在应用访问开启之后。

### 15.3 未知Txn结果恢复

网络超时/响应丢失时禁止盲目重发或假定失败，必须进行线性一致读回：

- **Checkpoint初始化未知：** checkpoint精确等于初始值且state/Leader/request目标均未出现时判定COMMITTED；checkpoint和目标键均不存在时可重试相同Txn；其他状态隔离。
- **Batch Txn未知：** 读回checkpoint及本批每个request值。checkpoint仍等于前驱且全部目标key不存在时判定NOT_COMMITTED，可重试完全相同的Txn；checkpoint属于相同plan且已推进到该批或更后、同时本批所有记录值逐字节匹配时判定COMMITTED；其余情况QUARANTINE。
- **最终发布Txn未知：** state字节与候选完全一致、checkpoint处于最终状态且Leader key不存在时判定COMMITTED；state不存在但最终checkpoint一致且Leader key不存在时可重试相同发布Txn；任何冲突状态均QUARANTINE。
- etcd Txn本身具有原子性，若线性一致读回看到本批只有部分key存在，则不能把它解释成合法的Txn部分提交，必须隔离调查。

状态分类值分别为`COMMITTED`、`NOT_COMMITTED_RETRY_SAME_TXN`和`INCONSISTENT_QUARANTINE`。本轮只实现分类函数和计划模型，不执行真实Range、Txn或自动恢复。

### 15.4 应用隔离和最终启用屏障

- 迁移身份在演练期间拥有目标隔离namespace所需权限；应用身份在staging期间必须无权访问目标namespace。
- 应用身份即使需要后续访问，也只能获得`scheduler/state`、`requests/`、`leases/`和`coordinator/leader`对应的最小键范围；不得授权`staging/`。
- 所有request索引和最终checkpoint完成线性一致读回后，才发布`scheduler/state`；发布后先读回state与Leader key，再撤销/禁用迁移写身份，最后才开放应用身份并启动单一新Leader claim。
- Provider操作仍需独立核验外部fencing floor、generation与scope recovery；KV导入成功不自动开放Provider控制面。
- checkpoint和摘要证据至少保留至迁移验收完成；不得在成功返回后立即删除审计证据。

**状态边界：** 本轮新增纯只读协议模型和分类测试；没有连接etcd、写入KV、创建Lease、调整RBAC、启动应用或触碰生产数据。真实批次写入器、checkpoint续跑执行器和一次性临时etcd故障注入演练仍未实现。

### 15.5 第七十八轮验证记录

Quality Run [46029534619](https://github.com/rexyll/cnc-knowledge/actions/runs/46029534619) success：全库594 unittest（40 skipped）、CH12数值资源143项通过、knowledge lint 0 errors/5 warnings、结构检查0 errors。该结果仅验证只读协议模型、恢复分类和仓库质量门禁，不构成真实etcd写入、故障注入或生产迁移证据。

### 15.6 第七十九轮：精确checkpoint链与内存事务执行验证

第七十八轮的batch未知结果分类曾允许根据plan digest、完成数量下限和当前batch request值匹配来认定COMMITTED。此判据不足以证明读回checkpoint确实由该计划生成：具有相同plan digest但被伪造或损坏的游标/progress digest，可能被误认为合法的后续checkpoint。

现要求调用方提供该批次及其所有后续批次由不可变计划生成的精确checkpoint字节值集合。只有线性一致读回值逐字节命中该集合、checkpoint结构字段有效、完成数量覆盖目标批次且目标request值全部逐字节匹配，才允许分类COMMITTED。仍处于精确前驱checkpoint且本批所有key均不存在时，才允许分类NOT_COMMITTED_RETRY_SAME_TXN；其他情况一律QUARANTINE。此规则同时允许进程在后续批次已经完成后，恢复判定先前批次的响应丢失。

新增 `tests/test_spare_parts_sqlite_staged_import_execution.py`，通过 `EtcdV3CoordinatorAuthorityStore` 和 `InMemoryEtcdV3Client` 执行实际的adapter Txn请求映射。测试覆盖：

- 模拟进程在首批完成后退出，新的store adapter读取checkpoint并从下一批继续；所有request索引仅创建一次，`scheduler/state`直到所有批次完成后才出现。
- Txn提交后模拟丢失响应，线性一致读回checkpoint与本批值后判定COMMITTED，不盲目重放。
- Txn提交前模拟连接中断，读回精确前驱checkpoint且所有目标值不存在后，允许重试完全相同Txn。
- 竞争writer在导入Txn评估比较前先写入一个目标request key；导入CAS失败，其他request目标保持不存在，checkpoint不推进，并进入QUARANTINE。
- 最终发布Txn提交后响应丢失，通过精确state、最终checkpoint与Leader key读回判定COMMITTED。

新增的严格判据单元测试还证明：即使plan digest和request值匹配，只要progress digest被篡改、checkpoint不属于本计划的预期后继链，就不能判定COMMITTED。

**证据边界：** `InMemoryEtcdV3Client`是单进程测试替身，不提供Raft、Quorum、磁盘耐久性、真正多客户端网络并发、节点故障或服务端配置约束。新store adapter重建只模拟进程对象重建，并不等同真实OS进程重启后的服务器持久性验证。本轮没有etcd真实Range/Txn/Lease写入、RBAC修改、应用启停、生产namespace访问或cutover。真实临时三节点etcd故障注入仍属于MIG-06后续门禁。

### 15.7 第七十九轮验证记录

Quality Run [46092128612](https://github.com/rexyll/cnc-knowledge/actions/runs/46092128612) success：全库600 unittest（40 skipped，560 passed）、CH12数值资源测试143项通过、knowledge lint 0 errors/5 warnings、结构/data检查0 errors。新增执行测试走现有Etcd adapter与InMemory fake，覆盖批次原子性、checkpoint未知结果恢复、竞争writer CAS冲突、重启续跑和最终state发布。MIG-05因此进入IN_PROGRESS，但只完成本轮涉及的一部分事务恢复测试；完整状态映射、fencing、幂等/TTL、外部Provider fencing和真实etcd故障注入仍未完成。

本轮没有连接真实etcd、执行Lease Grant/Revoke、修改RBAC、启动应用、写生产namespace或进行生产cutover。MIG-04仍IN_PROGRESS，MIG-06 TODO，MIG-07 BLOCKED。

### 15.8 第八十轮：Leader epoch floor持久化及Unified runtime互操作

此前候选映射只把旧Leader epoch作为顶层恢复说明，而 \`state_template.coordinator.leader\` 置为 \`None\`。现有标准 \`claim_leadership()\` 的默认计算以aggregate当前Leader epoch为基准；若导入后忘记显式传入外部reconciliation floor，标准claim会从epoch 1开始，导致历史epoch floor未被运行时强制保留。这是迁移连续性缺口。

现将旧epoch floor持久化为Unified schema-v2 aggregate内部的固定失效历史marker（仅旧epoch大于0时）：
- \`leader_id = "migration-epoch-floor"\`
- \`epoch = legacy leader epoch\`
- \`expires_at = 0.0\`
- \`backend_lease_id = 0\`（etcd no-Lease sentinel，不引用任何cluster-global真实Lease ID）

此marker不代表旧Leader，不包含旧leader_id，不具备有效TTL，也没有对应的 \`coordinator/leader\` TTL key；导入时不创建原生Lease。它只承载单调epoch下限。标准 \`leader_snapshot()\` 应将其识别为inactive；标准 \`claim_leadership()\` 随后会生成epoch \`legacy floor + 1\` 的全新Leader，并为其正常申请正数Lease。旧epoch为0时不写marker，保持 \`leader=None\`，新claim的首个epoch仍为1。

为避免该特殊值扩大到普通Leader记录，Planner只允许字段和值全部精确匹配的marker；Coordinator runtime只对 \`leader_id="migration-epoch-floor"\` 且 \`expires_at=0.0\` 的记录接受 \`backend_lease_id=0\`。其他真实Leader仍要求正数Lease ID。旧Leader身份、非零backend Lease哨兵、非零过期时间或其他非规范记录均不得通过导入校验。

候选bundle的数据语义发生了不兼容变化，因此格式从 \`ch17-sqlite-unified-candidate-v1\` 升级为 \`ch17-sqlite-unified-candidate-v2\`。旧v1候选包必须拒绝；需从新的只读Inventory/Export重新构建manifest、records、policy与candidate。Planner单独有测试确认v1不再被接受。

新增的内存互操作测试在模拟完成分批request导入及最终state publish后，使用标准Admission/Coordinator runtime重新构造对象，验证scope high-water/operation sequence、COMMITTED operation、终态request拒绝重放，以及旧epoch 8后的新Leader epoch 9。另验证epoch-zero来源不生成marker。该测试只说明候选aggregate与当前客户端运行时结构契约兼容；不等价于真实etcd导入演练、Lease TTL验证、Provider外部fencing验收或生产cutover。MIG-05仍为IN_PROGRESS，MIG-06仍为TODO。
