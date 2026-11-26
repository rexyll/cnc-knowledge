# 远程 Coordinator 与对象存储 Provider 的分布式 fencing 提交协议

**知识ID：** KNOW-000049  
**章节：** CH17 操作、维护与维修  
**任务：** CH17-T004 第三十五轮  
**状态：** IN_PROGRESS / 厂商中立协议参考模型与合成 CAS 测试  
**代码：** scripts/spare_parts_provider_distributed_fencing.py  
**测试：** tests/test_spare_parts_provider_distributed_fencing.py

## 1. 目标与不变量

第三十四轮的同库 SQLite 原子模式只能覆盖同主机、同一个 SQLite 文件。远程 Coordinator 与云对象存储分处不同服务，不能把两个服务的事务拼成一个 SQLite 事务，也不能把“先查 Coordinator lease、再调用对象存储 PUT”当作原子 fencing。

本轮建立一个基于单个 scope control object 的条件提交协议。核心不变量：

1. 每个 fencing scope 只有一个权威控制对象，保存当前单调 fencing high-water、活动 lease、当前已发布 manifest 指针和幂等回执。
2. 大型 payload 先写入带 token / operation ID 的不可变 staging key；staging 对象本身不是已发布备份。
3. 只有成功执行 control object 的条件更新，才允许发布新的 manifest 指针。
4. lease 激活、lease 撤销和 manifest 发布都修改同一个 control object，因此在该对象的条件写入序列上形成全序。
5. 任何读写超时、CAS冲突、Coordinator不可达、控制对象损坏或结果无法确认，都必须 fail-closed 或显式返回 OUTCOME_UNKNOWN；不得退化为无条件覆盖。
6. 客户端不能直接写 control object。只有受信任 Provider Gateway 可以写该对象；读者只相信 control object 当前指向的 commit。

这里的“线性化”严格指**同一个 scope control object 的强一致读取和原子条件替换**。它不是跨多个对象的事务，也不意味着普通对象存储 PUT 自动验证 Ed25519 token。必须由受信任 Gateway 验签、核对状态，并且只把 control object CAS 作为发布提交点。

## 2. 逻辑对象布局

建议每个 tenant + backup scope 使用独立控制键：

- Control object：scope 固定控制键，例如 cnc/ch17/backup-001/CONTROL.json
- Staging payload：scope/staging/{fencing_token}/{operation_sequence}/{content_hash}/...
- Immutable manifest：同一 token / operation sequence 对应的 manifest 对象。
- Current commit：存放在 Control object 内，包含 manifest key、SHA-256、token、lease ID、operation sequence 和 idempotency key。

控制对象的逻辑字段：

| 字段 | 语义 |
|---|---|
| schema_version | 控制记录协议版本 |
| scope | 唯一 fencing scope |
| high_water_token | 已观察并消费的最大 fencing token，永不回退 |
| lease_state | IDLE / ACTIVE / REVOKED |
| lease_id / tenant_id / owner_id | 当前活动 lease 身份 |
| lease_expires_at | Coordinator 签发的 lease 截止时间 |
| latest_operation_sequence | 当前 scope 已提交的最大操作序号 |
| recent_receipts | 有界的近期幂等回执 |
| current_commit | 当前唯一可见的 manifest 指针 |

对象存储返回的 ETag 或 generation 是 CAS 版本号，不是 fencing token。两者不能混为一谈：fencing token 用于区分租约代际，ETag/generation 用于检测控制对象在读到写之间是否被其他请求修改。

## 3. 租约激活协议

Coordinator 必须是每个 scope 的单调 token 权威分配者，底层状态需具备线性一致的事务/CAS；故障切换、备份恢复和重建均不得复用旧 token 或降低 high-water。

流程：

1. Coordinator 对 acquire 请求做身份、租户、配额和幂等检查，分配严格大于已知历史值的 token，状态进入 PENDING_ACTIVATION。
2. Coordinator 签发 Ed25519 activation proof，绑定 issuer、tenant、owner、lease ID、scope、token、过期时间和 activation idempotency key。
3. Provider Gateway 读取 control object，要求新 token 大于 high_water_token。
4. Gateway 使用读取到的 ETag/generation 执行条件替换，将 control object 更新为 ACTIVE、新 token 和 lease 身份。
5. 只有 CAS 成功或通过强一致重读确认同一 activation 已提交后，Coordinator 才能把 lease 对外标记为 ACTIVE。
6. 若响应丢失，使用同一 token、lease ID 和 idempotency key 重读并恢复；不得简单分配另一个 token 再盲目重试。

token T2 的 activation CAS 成功后，control object 的 high_water_token 已变为 T2。任何仍拿着 T1 的旧 writer，即便它先前读到过旧 ETag，后续 CAS 也会因 ETag/generation 已改变而失败；即便重读最新 control object，也会因 token 不匹配而被拒绝。

## 4. 备份提交协议

1. Gateway 验证 Ed25519 publish proof，确认 issuer/key 状态、tenant、scope、resource、lease ID、token、operation、manifest key、manifest SHA-256 和 operation sequence 全部匹配。
2. payload 和 manifest 以 token-specific immutable key 写入。上传过程可包含 multipart；进行中的分块对象不能成为备份可见性依据。
3. 完成后读取 control object，要求 lease_state=ACTIVE、token 和 lease ID 完全匹配、lease 未到期，且 operation sequence 大于已提交序号。
4. Gateway 生成新的控制对象版本，把 current_commit 指向已验证的 immutable manifest，同时更新 latest_operation_sequence 和 recent_receipts。
5. 使用读取到的 ETag/generation 做单对象条件写入。只有该 CAS 成功，备份才被视为已发布。
6. 读者先读取 control object，再按 manifest 指针读取并校验 SHA-256；不得通过列举 staging 目录或“时间最新对象”推断当前备份。

这样，staging payload 可以分多次上传，但最终可见性只由一个 control object 条件更新决定。旧 writer 可能留下未引用的孤儿 staging 对象，却不能通过旧 token 覆盖已经发布的 manifest 指针。垃圾回收必须另行审批，不能用未经 fencing 的盲删作为恢复手段。

## 5. 撤销协议与线性化点

release 不得只在 Coordinator 数据库中写 RELEASED 就向调用方返回成功。Coordinator 与 Provider 分库仍然会产生 TOCTOU。

推荐流程：

1. Coordinator 将 lease 标记为 REVOKING，停止签发该 lease 的新 mutation proof。
2. Coordinator 签发绑定当前 token/lease/scope 的 revoke proof。
3. Gateway 读取 control object，确认仍是目标 ACTIVE lease，并使用 CAS 把 lease_state 改成 REVOKED；high_water_token 保持不变。
4. Gateway 确认 CAS 成功后，Coordinator 才最终记录 RELEASED 并向调用方报告 release 完成。
5. 如果 CAS 响应丢失，读取 control object：同一 token/lease 已为 REVOKED则完成收敛；仍为 ACTIVE则用同一个 revoke idempotency key 重试；控制服务不可用则报告结果未知，绝不能报告撤销成功。

**真正的线性化点是 control object 从 ACTIVE 条件更新为 REVOKED 的 CAS。**

与撤销并发的 Provider publish 只能有两种顺序：
- publish CAS 先成功：该发布在线性顺序上先于 release；
- revoke CAS 先成功：publish 使用旧 ETag 会失败，重读后看到 REVOKED 并拒绝。

Coordinator 的 PENDING_ACTIVATION、REVOKING 等状态负责崩溃恢复和防止重复分配；对象存储 control object 是 Provider 写入路径最终执行的 fencing 门。

Lease 自然到期还需 Gateway 检查 proof expires_at 和 control object lease_expires_at，并使用受控时钟、时钟偏差预算。到期后的异步清理任务可以把记录推进为 REVOKED，但不能依赖该清理任务及时运行来放行过期 proof。若时钟可信度或状态未知，必须拒绝写入。

## 6. operation sequence 与幂等恢复

token 区分租约代际；operation_sequence 区分同一 lease 内的多个提交操作。Coordinator 必须对每个 scope 单调分配操作序号，并把 sequence、idempotency key、manifest key 与摘要纳入签名 proof。

- 已提交 sequence 且在回执窗口内找到相同 idempotency key / operation hash：返回原回执，不重复发布。
- 相同 sequence 或 idempotency key 对应不同内容：冲突拒绝。
- sequence 小于等于已提交 high-water，但回执已超出保留窗口：返回 OUTCOME_UNKNOWN，不能把它当作新操作重新执行。
- 新 sequence 大于当前提交序号：可参与下一次 CAS；若并发顺序倒置，较旧 sequence 被拒绝，调用方必须先向 Coordinator 做幂等查询/恢复，不能擅自更换 sequence 来掩盖未知结果。

参考模型默认只保留最近128条 receipt；这是可配置的工程参数，不是行业通用值。生产部署要按最大重试周期、备份频度和审计要求设计保留窗口。旧请求超出窗口只能返回未知，不能盲目重放。

## 7. 主流对象存储映射及能力边界

| 平台 | 单对象条件更新能力 | 协议映射与注意点 |
|---|---|---|
| Amazon S3 | PutObject / CompleteMultipartUpload 等支持 If-Match、If-None-Match | Control object 用 If-Match 做 CAS；staging 使用唯一 key；CreateMultipartUpload / UploadPart 本身不接受同样的条件头，不能把它们视为最终提交 |
| Google Cloud Storage | ifGenerationMatch / generation precondition | 把读取到的 generation 作为 control object 更新前置条件；412 表示 generation 已变化 |
| Azure Blob Storage | ETag + If-Match；也提供 Blob Lease | Control blob 用 ETag 条件更新；Blob Lease 是对象级锁，不构成多个 Blob 的事务 |

官方依据：
- SRC-000393：Amazon S3 Conditional Writes。
- SRC-000394：Google Cloud Storage Request Preconditions。
- SRC-000395：Azure Blob Storage Manage Concurrency。
- SRC-000396：Azure Architecture Center 对 Blob 多对象事务边界的说明。

这几种能力都不能直接提供跨 control object 与多个 payload object 的事务。因此本协议把不可变 payload 与最终 control pointer 分开，只要求 control pointer 的更新具有强一致单对象 CAS。真实 SDK 适配前，必须逐项核对所选区域、桶类型、版本控制、API 操作、策略条件和错误语义。

## 8. 安全部署约束

- 控制对象必须有独立 IAM/RBAC 边界；只有 Gateway 的服务身份能写 control key。
- 客户端不能持有可绕过 Gateway 的 control key 写权限或可覆盖当前指针的长期凭据。
- Staging key 使用 token / operation ID / content digest 构造，避免不同租约覆盖同一 payload key。
- 读取 control object 必须强一致；ETag/generation 必须是可用于条件更新的服务端版本标识，不能用本地缓存值替代。
- 条件更新必须是 fail-closed；平台不支持目标操作的条件头、版本条件或错误确认时，不得宣称支持严格 fencing。
- 409、412、超时和连接中断必须区分“条件冲突”“明确失败”和“提交结果未知”；未知结果先重读并通过 receipt 对账。
- 所有备份读者只认 control pointer，不得直接读取未提交 staging key。
- 生产 Coordinator 自身也必须有线性一致的 token/operation sequence 分配和崩溃恢复机制；若权威 token 状态回滚，单靠对象存储 CAS 无法补救错误的 token 分配者。

## 9. 本轮参考实现和验证边界

新增 scripts/spare_parts_provider_distributed_fencing.py：
- 定义单控制对象 read + compare_and_swap 协议。
- 用 Ed25519 v2 proof 验证 issuer、scope、lease、token、operation 和 expiry。
- 实现 ACTIVE 激活、REVOKED 撤销、manifest 指针发布、operation sequence 与有限回执。
- CAS 响应丢失后强一致重读并按幂等记录恢复。
- 对回执超窗的旧操作返回 OUTCOME_UNKNOWN，禁止盲目重复执行。
- InMemoryConditionalObjectControlStore 只用于单进程合成测试，不能作为远程或多主机实现。

新增资源 ASSET-000080：20条分布式 fencing 参考验收场景，初始全部 PROPOSED_NOT_APPROVED / NOT_RUN。

本轮没有实现 AWS / Azure / Google Cloud SDK、远程 HTTP/gRPC Coordinator、真实 KMS/HSM、生产 IAM policy 或云对象存储测试。合成 CAS 测试只验证状态机与竞态模型，不代表厂商验收或生产线性一致性证明。

**生产备份继续关闭：** governance_readiness=BLOCKED_PENDING_ENTERPRISE_APPROVAL，production_backup_enabled=false，business_rule_assertions=NOT_EVALUATED。

## 10. 本轮 CI 验证记录

- 代码与测试CI：[Run 45767324560](https://github.com/rexyll/cnc-knowledge/actions/runs/45767324560)，两个必需Job success；全库268项unittest、CH12数值资源143项通过；strict lint 0 errors / 5 warnings；知识结构和数据质量0 errors。
- 最终文档同步CI：[Run 45767658789](https://github.com/rexyll/cnc-knowledge/actions/runs/45767658789)，两个必需Job success；全库268项、CH12 143项通过；strict lint 0 errors / 5 warnings；知识结构与数据质量0 errors。
- CH12 S-curve artifact：15091879973。现有BackupStorageAdapter、Admission和SQLite Provider自检仍成功，但这些报告不是本轮分布式CAS模型的云服务验收证据。

本轮14项分布式CAS单元测试是本地合成状态机测试。ASSET-000080的20条参考场景全部PROPOSED_NOT_APPROVED / NOT_RUN；真实S3/GCS/Azure SDK、远程Coordinator、KMS/HSM、IAM和多主机测试均未完成。
