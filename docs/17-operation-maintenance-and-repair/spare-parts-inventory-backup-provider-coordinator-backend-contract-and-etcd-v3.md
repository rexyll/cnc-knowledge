# 数控机床备件库存备份 Coordinator 权威存储后端契约与 etcd v3 适配设计

**知识编号：** KNOW-000051  
**章节：** CH17-T004  
**版本：** 1.0  
**日期：** 2026-11-26  
**关联：** KNOW-000049、KNOW-000050  
**测试资源：** ASSET-000082

## 1. 目标与范围

第三十六轮已建立可持久化的 Coordinator 权威状态机，但其实现 `SQLiteDurableCoordinatorAuthority` 直接使用 SQLite SQL 表与 `BEGIN IMMEDIATE`，只能在同一主机本地 SQLite WAL 边界中运行。

本轮把后端能力拆为两个接口层：

1. **应用服务端口 `DurableCoordinatorAuthorityBackend`：** 描述上层服务必须提供的 Leader、activation、revocation、operation sequence、publish确认和恢复操作。当前 `SQLiteDurableCoordinatorAuthority` 结构化满足该端口。
2. **原子存储端口 `CoordinatorAuthorityStore`：** 描述底层强一致存储必须提供的线性一致读取、条件比较事务、分支写操作及租约生命周期。

新增 `SQLiteCoordinatorAuthorityStore` 本地参考实现和 `EtcdV3CoordinatorAuthorityStore` etcd v3 API 适配器。etcd适配器注入 `EtcdV3Client` driver protocol；真实gRPC/JSON Gateway客户端、网络、证书和IAM凭据由部署侧提供，本轮未配置。

**重要：** 当前SQLite应用服务尚未重构为完全通过 `CoordinatorAuthorityStore` 执行领域状态转换；Etcd v3适配器目前实现的是底层KV/Txn/Lease原子存储端口，而不是一套已连接的远程Coordinator服务。不得把这个接口和测试替身称为已完成etcd生产集成。

## 2. 一致性契约

### 2.1 线性一致读

`linearizable_get(key)`必须返回至少不早于本次读取开始前所有已完成写入的值。涉及Leader所有权、lease状态、token high-water、operation sequence和恢复边界的安全决策必须走线性一致读。

etcd v3的KV Range默认提供线性一致读取；请求设置`serializable=true`时可由本地成员直接返回，可能落后于集群共识状态。权威状态读取不得使用该优化。etcd Watch是异步事件订阅，不提供线性一致性；Watch只能触发重新读取，不能直接作为授权判据。[SRC-000397][SRC-000398]

### 2.2 原子条件事务

`transact(compares, success, failure)`必须在后端原子执行：

- 比较集合中的条件全部成立时，执行success分支；
- 任一条件不成立时，执行failure分支；
- 只执行一个分支，不允许观察到部分更新；
- 多key更新应落在同一事务修订号/原子提交点；
- 比较支持key不存在/版本、create revision、mod revision和值。

etcd v3 Txn提供If/Then/Else结构，比较集合原子求值后执行一个分支；一个Txn中的所有修改共享同一store revision。[SRC-000398]

### 2.3 Lease不是资源互斥的充分条件

Lease Grant/KeepAlive/Revoke用于检测客户端存活及在租约到期或撤销时清理附着key。Leader key需要附着lease。**但仅持有Lease或分布式Lock并不代表旧进程已经停止，也不能保护etcd以外的对象存储资源。**

每次影响Coordinator权威状态的Txn还必须比较Leader key的创建/修改修订号、当前epoch或所有者值；不能只在进程启动时检查一次。下游S3/GCS/Azure Provider仍需验证scope token与条件写，防止过期进程在外部系统完成陈旧写入。[SRC-000399][SRC-000400]

## 3. 应用服务端口与存储端口

### 3.1 应用服务端口

`DurableCoordinatorAuthorityBackend`描述现有业务方法：

- claim/renew leadership；
- prepare/confirm activation；
- prepare/confirm revocation；
- allocate/confirm publish operation sequence；
- authorize proof signing；
- list pending operations；
- reconcile after restore。

该端口用于让Provider orchestration与具体持久化引擎解耦。当前SQLite服务已经通过结构接口测试；未来etcd领域服务必须完整实现相同语义，不可只包装KV方法就宣称完成。

### 3.2 低层原子存储端口

`CoordinatorAuthorityStore`提供以下操作：

| 操作 | 必须保证 | 典型用途 |
|---|---|---|
| `linearizable_get(key)` | 安全用途强一致读并返回revision | 读Leader、token/sequence及pending状态 |
| `transact(compares, success, failure)` | 原子比较与单分支写入 | token/sequence分配、Leader epoch检查、幂等提交 |
| `lease_grant(ttl)` | 服务端租约ID与TTL | Coordinator Leader lease |
| `lease_keepalive(id)` | 仅更新当前有效租约 | 续任；失败即停止签发新操作 |
| `lease_revoke(id)` | 撤销租约并清理附着key | 主动让Leader key失效 |

比较原语有`VERSION`、`CREATE`、`MOD`、`VALUE`与`EQUAL/NOT_EQUAL/GREATER/LESS`。事务分支支持PUT和DELETE；每一分支不允许重复写同一个key。

## 4. etcd v3映射

| Coordinator存储概念 | etcd v3原语 | 适配要求 |
|---|---|---|
| 强一致读取 | KV Range | `serializable=false`，禁止安全路径使用serializable本地读 |
| 原子CAS/多key事务 | KV Txn Compare/Success/Failure | 一次Txn提交，检查`succeeded`和顶层revision |
| 领导者租约 | Lease Grant/KeepAlive/Revoke | Leader key附着lease；续租失败立即fail-closed |
| Leader身份 | Election Campaign返回的LeaderKey | 保留key、lease、create revision；所有写事务再验证所有权 |
| fencing/逻辑时钟 | scope内的持久high-water token与Txn mod revision | 应用token在同一条件事务中自增，不能只依赖客户端内存计数 |
| 事件通知 | Watch | 仅作唤醒/增量提示；随后做线性一致Range |

etcd Election API的LeaderKey带有创建修订号和lease信息，可用于在Txn中验证Leader ownership；必须将这个验证放进每次重要写入条件，而不只是使用Campaign结果缓存。[SRC-000399]

### 4.1 建议的key布局

以下为建议命名，不是已创建的集群数据：

```text
/cnc/<environment>/spares/coordinator/leader
/cnc/<environment>/spares/scopes/<tenant>/<scope-hash>/state
/cnc/<environment>/spares/scopes/<tenant>/<scope-hash>/ops/<idempotency-key>
/cnc/<environment>/spares/scopes/<tenant>/<scope-hash>/receipts/<operation-sequence>
```

不要直接把用户提供的物料号、scope或tenant字段未经规范化拼入etcd key。需使用固定前缀、租户命名空间、规范化/哈希路径和RBAC范围隔离。

### 4.2 Activation与operation sequence事务

Activation示例逻辑：

1. 线性一致读取Leader key和scope state。
2. 组装Txn compare：Leader key的create/mod revision、leader ID/epoch、scope state的mod revision与当前high-water。
3. success分支同时写入递增的scope token和`PENDING_ACTIVATION` operation ledger。
4. 事务提交后才签发operation proof，再调用Provider单control-object CAS。
5. Provider状态读回完全匹配token/lease/generation后，以另一条Leader+scope revision条件Txn转为ACTIVE。

Publish sequence同理：在一个Txn中比较当前Leader与scope revision，增加sequence并写入幂等operation记录。相同operation key重放必须返回原分配；同key异内容拒绝。

### 4.3 Leader fencing

Leader lease丢失时，旧进程可能因GC暂停、线程阻塞或网络分区继续运行。每一个prepare、confirm、sequence分配、proof签发授权必须重新对比当前LeaderKey的修订号和epoch。

Leader key被新Leader替换后，旧Leader的Txn compare必须失败。对已经签发但尚未过期的短时proof，Leader key变化不会自动撤销其密码学签名；因此Provider端仍必须检查per-scope high-water token、proof TTL和对象控制记录CAS。

### 4.4 Watch与读取

Watch用于订阅状态变化、更新本地缓存和触发pending operation扫描。Watch事件可能因断线、revision compact或重连而延迟/重放；更关键的是Watch本身不提供线性一致性。不得用“Watcher目前没观察到revoke事件”证明lease仍活动。安全决策必须发起线性一致Range或在Txn中重新验证Leader/scope状态。[SRC-000397]

## 5. 失败语义与网络分区

| 故障 | 应用响应 | 禁止行为 |
|---|---|---|
| Txn请求超时/连接断开 | `OUTCOME_UNKNOWN`，按原幂等键线性一致读取恢复 | 换新idempotency key盲目重试 |
| Leader lease keepalive失败 | 停止新proof签发和状态迁移 | 用本地过期时间继续认为自己是Leader |
| etcd选主期间写请求超时 | 保留pending intent并核对后续状态 | 将超时直接解释为未提交 |
| 无法获得多数派 | Coordinator写入与授权失败关闭 | 降级为节点本地写或serializable读 |
| Watch断线/历史已compact | 从当前revision执行线性一致Range，重新建立Watch | 将本地缓存当作新鲜权威状态 |
| Provider已提交、Coordinator未确认 | 读取control object/receipt并按精确字段收敛 | 盲目生成第二个publish operation |
| 旧Leader恢复连接 | Txn中LeaderKey revision比较失败 | 依赖进程内存Leader flag或租约缓存 |

etcd多数派失效时不能接受新的集群写；Leader故障/选举期间未提交事务可能丢失，客户端也可能收到超时。应用必须对这些请求保留结果未知语义。[SRC-000401]

## 6. 新增模块与验证范围

新增文件：

- `scripts/spare_parts_provider_authority_store.py`
- `tests/test_spare_parts_provider_authority_store.py`

实现：

- `DurableCoordinatorAuthorityBackend`：应用服务端口，当前SQLite领域服务结构化满足。
- `CoordinatorAuthorityStore`：原子存储KV/Txn/Lease端口。
- `SQLiteCoordinatorAuthorityStore`：本机WAL参考实现。
- `EtcdV3CoordinatorAuthorityStore`：适配规范化etcd v3 client driver接口，执行Range(serializable=false)、Compare/Txn、Lease操作。
- `InMemoryEtcdV3Client`：单进程测试替身，注入Txn提交后响应丢失、Leader key变化和租约过期。

测试覆盖SQLite与etcd假客户端的共同存储契约，包括原子多key写、修改修订号CAS单赢家、成功/失败分支、线性一致读参数、租约附着/续约/到期/撤销、旧Leader修订号拒绝和Txn响应丢失OUTCOME_UNKNOWN。

**没有真实etcd server、gRPC/JSON Gateway驱动、mTLS认证、RBAC、网络分区或多主机测试。** `InMemoryEtcdV3Client`只验证适配器映射和确定性语义，不代表Raft共识、quorum或生产故障演练。

## 7. 迁移路径与后续工作

1. 先在专用三节点测试etcd集群完成真实client driver、TLS/mTLS、RBAC前缀权限和线性一致读验证。
2. 将当前SQLite Coordinator的表状态机拆分为领域服务与Store port事务，定义Leader epoch、scope state、operation ledger多key原子写入的完整Txn边界。
3. 实现etcd后端事务映射，所有关键Txn都比较LeaderKey revision、scope mod revision和idempotency记录。
4. 做网络分区、Leader进程暂停/恢复、etcd选主、quorum丢失、Txn响应丢失、Lease续租失败、Watch compact/reconnect与Provider CAS竞争测试。
5. 完成恢复/快照/灾备策略、key namespace/RBAC/mTLS轮换、容量和延迟预算后，再决定生产启用。

## 8. 外部资料

- SRC-000397：etcd API guarantees，线性一致性、Watch保证与未知请求结果。
- SRC-000398：etcd v3 API，KV Txn compare/then/else和Lease API。
- SRC-000399：etcd v3 concurrency API reference，Election/LeaderKey及revision字段。
- SRC-000400：etcd leases与locks使用边界，Lease/Lock本身不构成外部资源互斥，必须在事务中验证revision/lease并使用fencing。
- SRC-000401：etcd failure modes，Leader故障/选举与多数派故障。

**当前生产状态不变：** `production_backup_enabled=false`，`governance_readiness=BLOCKED_PENDING_ENTERPRISE_APPROVAL`，`business_rule_assertions=NOT_EVALUATED`。


## 9. CI验证记录

- **代码提交：** `e274067e7e601c026252ddf3dacb87db5971bd63`；[GitHub Actions Run 45770717942](https://github.com/rexyll/cnc-knowledge/actions/runs/45770717942)，两个必需Job均completed/success。
- **文档同步提交：** `3a83763239ec2ecda8607eca0977139c41dd6df9`；[GitHub Actions Run 45770955018](https://github.com/rexyll/cnc-knowledge/actions/runs/45770955018)，两个必需Job均completed/success。
- 两次最终CI均全库300项unittest、CH12数值资源143项通过；strict knowledge lint PASS（0 errors，5 warnings）；知识结构与数据质量PASS（0 errors）。
- 测试覆盖本机SQLite参考存储与单进程InMemoryEtcdV3Client API替身。CI没有连接etcd server，也没有验证Raft quorum、mTLS/RBAC、多主机网络分区、云Provider或生产灾备。
- ASSET-000082的20条验收场景全部PROPOSED_NOT_APPROVED / NOT_RUN。CI单元测试通过不改变矩阵状态。

## 10. 当前集成与生产边界

- `DurableCoordinatorAuthorityBackend`是应用服务端口，当前SQLite领域服务通过结构化接口测试。
- `CoordinatorAuthorityStore`及etcd v3适配器提供底层KV/Txn/Lease原语，但现有SQLite领域状态机仍直接执行SQL；**尚未完成领域服务向该存储端口的迁移**。
- `EtcdV3Client`只是注入式driver contract；本轮未提供或安装真实gRPC/JSON Gateway客户端，没有真实集群地址、TLS/mTLS证书、认证/RBAC角色或网络连接。
- 生产备份仍关闭：`production_backup_enabled=false`；`governance_readiness=BLOCKED_PENDING_ENTERPRISE_APPROVAL`；`business_rule_assertions=NOT_EVALUATED`。
