# SQLite 同库原子 lease 撤销与 Provider 写入顺序

**知识ID：** KNOW-000048  
**章节：** CH17 操作、维护与维修  
**任务：** CH17-T004 第三十四轮  
**状态：** IN_PROGRESS / 本机 SQLite 原子参考模式；CI 与部署验收以记录为准  
**依赖：** Python sqlite3；沿用本章 fencing attestation v1/v2 验签与准入 lease 数据模型

## 1. 本轮目标与问题边界

第三十三轮已能由 Provider 在每次写入前在线查询 Coordinator，检查 lease 是否仍为 ACTIVE；Coordinator 不可用时 fail-closed。但当 Coordinator 与 Provider 使用不同数据库/事务时，状态读取与对象提交之间存在 TOCTOU 窗口：状态查询返回 ACTIVE 后，Coordinator 可能先完成 RELEASED，Provider 随后仍提交对象。

本轮增加一个可选的**同一 SQLite 数据库、同一写事务**参考模式。它不是把两个独立数据库做分布式事务，也不改变既有分库兼容模式；它通过强制相同数据库路径和复用 Provider 已持有的事务连接，让 lease 状态检查、对象或 multipart 变更、fencing high-water、幂等回执及审计写入共享一个 SQLite 写事务。

## 2. SQLite 并发语义基础

SQLite 同时允许多个读事务，但同一数据库文件同一时刻只有一个写事务。BEGIN IMMEDIATE 会立即开始写事务；若另一写事务已占用写锁，新的写事务会等待或返回 SQLITE_BUSY，具体取决于 busy timeout。

WAL 模式支持同一主机上的多进程协作，但需要共享内存 wal-index，不适用于网络文件系统。WAL 文件同一时间也只有一个 writer。因此本实现的互斥顺序只适用于**同一主机、同一真实 SQLite 文件、受支持的本地文件系统**。

依据：
- SRC-000391：SQLite 官方 Transaction 文档，BEGIN IMMEDIATE 与读写事务互斥语义。
- SRC-000392：SQLite 官方 Write-Ahead Logging 文档，同机限制及 WAL writer 互斥语义。

## 3. 实现接口与启用门槛

### 3.1 Coordinator

SQLiteProviderAdmissionCoordinator.is_attestation_active_in_transaction(connection, claims) 接收 Provider 已开启的 SQLite connection：
- 要求 connection 是 sqlite3.Connection 且事务已经打开；
- 使用 PRAGMA database_list 检查 main 数据库路径与 Coordinator 自身路径相同；
- 在当前 connection 上核验 issuer、lease_id、owner、tenant、domain、fencing token、ACTIVE 状态及时间窗口；
- 复用当前事务，不再另开连接或嵌套 BEGIN。

普通 is_attestation_active(claims) 仍保留，继续支持分库在线检查模式。

### 3.2 Provider

新增可选构造参数：
- require_online_attestation_status=True：启用在线状态检查；
- require_atomic_online_attestation_status=True：进一步要求原子同库模式。

严格原子模式必须同时满足：
1. 在线状态检查已启用；
2. checker 实现 is_attestation_active_in_transaction；
3. checker 的 database_path 与 Provider 解析后的数据库路径相同。

任一条件不满足，Provider 初始化失败，不静默退化为分库模式。未启用原子模式时，旧的 is_attestation_active 路径保持兼容，但仍存在第三十三轮记录的跨事务 TOCTOU 边界。

## 4. 原子顺序与线性化点

Provider 写入路径先在自身数据库执行 BEGIN IMMEDIATE，然后在该连接内验证签名/密钥和 lease 状态。对象写入（或 multipart session/part/complete）、scope high-water、幂等 receipt、审计记录在同一事务中提交。

两种竞争顺序如下：

**Provider 先获得写事务：**
1. Provider 获得 SQLite 写锁；
2. 同事务读取 lease=ACTIVE；
3. 完成对象或 multipart 变更及 fencing/receipt/audit；
4. Provider COMMIT；
5. Coordinator 的 release 才能取得写锁并提交 RELEASED。

因此本次写入在 lease release 之前线性化；release 不可能插入到 status check 和 Provider commit 之间。

**Coordinator release 先获得写事务：**
1. Coordinator 获得 SQLite 写锁；
2. 将 lease 状态提交为 RELEASED；
3. Provider 随后获得写锁；
4. Provider 在同一事务连接中读到 RELEASED，拒绝请求并回滚，不写入对象。

这里的“原子”是针对共享 SQLite 文件上遵守同一事务协议的 Coordinator/Provider 写路径而言。它不是网络分布式线性一致性保证，也不防止数据库管理员直接绕过应用逻辑修改表。

## 5. 错误处理与审计原则

- 原子检查异常或 Coordinator 状态不可用时，Provider fail-closed，拒绝写入。
- lease 非 ACTIVE、过期、issuer/owner/tenant/domain/token 不匹配时，拒绝写入。
- Provider 对象、fencing high-water、幂等回执与 audit 继续共用 Provider 事务；异常退出应整体回滚。
- 相同逻辑重试继续使用稳定 idempotency key；重新取得 lease 时使用新的 fencing token 和 proof。
- 原子路径不能混入另一个 Coordinator 数据库，也不能由 Provider 检查后再访问网络状态服务。

## 6. 测试与资源

新增代码与测试：
- scripts/spare_parts_provider_admission_sqlite.py：事务内状态查询接口；
- scripts/spare_parts_provider_sqlite_fenced.py：原子模式启用门槛与同连接检查；
- tests/test_spare_parts_provider_sqlite_fenced.py：路径不一致拒绝、要求在线模式、Provider 持有写事务期间 Coordinator release 被串行阻塞、release 提交后旧 proof 重放拒绝。

资源：
- ASSET-000079：12条原子 lease 撤销参考验收场景矩阵，初始均为 PROPOSED_NOT_APPROVED / NOT_RUN。

本地单元测试或CI通过只证明代码路径和合成并发模型按预期工作；不等于企业级业务规则批准、真实KMS、真实云Provider、生产多主机、对象存储条件写或灾备验收。

## 7. 适用限制与生产方向

本实现要求 Coordinator admission 表与 Provider 对象表共置于一个 SQLite 文件，这会扩大数据库的安全与备份边界，并由 SQLite 单写事务限制并发写吞吐。数据库必须位于同一主机的受支持本地文件系统；不要把 WAL 数据库放在 NFS、SMB 或未经验证的网络盘。进程权限、文件权限、时钟、busy timeout、WAL checkpoint、磁盘满与数据库恢复仍是运行前置条件。

若生产架构必须将 Coordinator 与 Provider 拆为不同主机/数据库，应重新选取单一权威线性化点，例如支持事务租约与资源变更的集中服务，或由目标对象存储提供并经验证的条件写/fencing机制；不能将本地同库实现直接宣称为远程部署安全保证。

**生产状态不变：** 未连接真实云 KMS/HSM、远程 Coordinator 或云对象存储；未执行企业批准的备份/恢复演练；production_backup_enabled=false，治理门禁仍为 BLOCKED_PENDING_ENTERPRISE_APPROVAL。
