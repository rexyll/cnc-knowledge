# 数控机床备件库存备份 Provider fencing 契约与 SQLite 安全恢复

**知识ID：** KNOW-000043  
**章节：** CH17 操作、维护与维修  
**状态：** IN_PROGRESS / 契约级合成验证  
**适用范围：** KNOW-000039～KNOW-000042 的 Provider 协调、持久租约与故障恢复补充；只定义陈旧写入防护及本地协调器数据库备份恢复边界。

## 1. 协调器租约不等于下游 fencing

协调器 acquire() 返回的租约包含 fencing token。该 token 只有在**实际副作用接收端**也参与校验时，才能阻止暂停、失联或租约过期后重新运行的旧写入者。

典型时序：写入者 A 获得 token 41 后暂停；其租约到期，写入者 B 获得 token 42 并提交；A 恢复运行并尝试提交旧内容。存储端必须依据同一资源的持久高水位 42 拒绝 token 41。

仅在客户端执行 coordinator.validate(lease) 并不足够：校验与远端写操作之间仍存在竞态窗口，也无法撤销已发送但延迟到达的请求。Provider 必须在提交原子边界内重新检查 token。

## 2. 下游 Provider 必须提供的原子合同

新增 scripts/spare_parts_provider_fencing_contract.py：

- FencingAwareObjectStorageProvider 定义 supports_fencing 声明和 put_if_newer 操作；
- fenced_put() 在能力未明确声明、方法缺失或入参不合法时 fail-closed，不回退调用普通写入；
- SyntheticFencedObjectSink 维护每个资源键的高水位与写入回执，供单元测试模拟原子条件提交。

真正可用的 Provider 实现必须在一个不可分割的事务中完成：读取指定资源键当前的已接受 fencing 高水位；拒绝小于高水位的 token；对相同 token 仅允许相同幂等请求身份和相同内容摘要重放；更新高水位并提交对象数据/提交标记；确保对象更新与高水位更新具有相同的原子可见性和持久性边界。

若 Provider 不能保证上述原子性，不能只靠先写高水位、再单独写对象来宣称 fencing 安全；两步间崩溃可能造成高水位前进但对象未提交。也不能先写对象再另行写高水位，因为旧写者仍可能在竞态窗口中覆盖对象。

资源键必须是稳定、规范化且不因租户别名或路径变换而分裂的逻辑资源身份。高水位应按资源或经批准的资源隔离域持久保存；不得仅存在于客户端内存、单一进程或会随对象版本清理的临时元数据中。

| 请求情形 | 预期 |
|---|---|
| token 大于资源当前高水位 | 在同一原子提交中接受对象与高水位 |
| token 小于资源当前高水位 | 拒绝陈旧写入，不改变对象 |
| token 相同、幂等键相同、内容摘要相同 | 返回原回执，视为幂等重放 |
| token 相同但幂等键或内容不同 | 冲突拒绝，不得覆盖 |
| Provider 未声明 fencing 能力或未实现条件写方法 | fail-closed，不调用普通 PUT |

## 3. 合成测试与适用边界

新增 tests/test_spare_parts_provider_fencing_contract.py，8项测试覆盖更大 token 接受、延迟恢复旧写者拒绝、相同请求重放、同 token 内容/幂等键冲突、能力缺失 fail-closed，以及非法 token 不改变对象。

**重要边界：** SyntheticFencedObjectSink 仅是同进程锁保护的内存测试夹具，不是真实对象存储。当前 BackupStorageAdapter / ObjectStorageProvider 既有接口尚未将 admission lease 的 fencing token 贯穿到每个远端 PUT、multipart part/complete 和 receipt commit。新模块是独立合同原型，并未自动给文件系统、Mock 或任何云 Provider 增加真实 fencing 能力。未通过供应商正式接口、原子条件操作与故障注入证明前，实际 Provider 必须视为不支持 fencing。

## 4. SQLite 在线备份与完整性检查

SQLiteProviderAdmissionCoordinator.backup_to() 使用 SQLite Backup API 创建一致性快照，而不是在 WAL 运行时简单复制主数据库文件。备份落到一个新的、不可覆盖的路径后，validate_backup() 以只读方式执行：

- PRAGMA integrity_check 和 foreign_key_check；
- 必需表、schema version、策略哈希及诊断计数校验；
- next_fencing_token 不得小于已签发租约中的最大 token；
- 汇报快照中的活动租约数、等待请求数及文件 SHA-256。

SHA-256 在这里用于文件一致性/传输校验，不是发布者签名或来源认证；备份仍需独立访问控制、加密、不可变保留及受控存储。SQLite integrity_check 通过也不能证明数据来自可信源或满足企业备份策略。

## 5. 恢复到新数据库：高水位对账是强制门禁

restore_to_new_database() 不是原位覆盖恢复，而是准备一个独立的新数据库文件。其执行前提：

- 备份结构和完整性校验通过，且策略哈希与当前协调器策略一致；
- 操作方必须提供非负 external_fencing_floor，以及可追溯的 fencing_reconciliation_ref；
- 外部高水位必须来自协调器数据库之外的可信证据，例如实际下游资源端已接受 token 的审计/状态汇总；不能仅从被恢复的旧备份推导；
- 恢复程序将旧快照中的全部 ACTIVE 租约置为 EXPIRED，清空等待者，并将下一 token 设置为不小于外部高水位、备份原序列及已签发最大 token 的值；
- 新库完整性复核通过后写入新文件；返回 PREPARED_NEW_DATABASE，明确 cutover_performed=false。

此流程不会覆盖运行中的原数据库，不负责服务停机、客户端重新连接、DNS/配置切换、并发写入屏障或恢复后的业务核对。真正切换前，必须先停止或隔离旧协调器实例，完成下游高水位盘点并确保旧写者无法再绕过 Provider fencing；否则即使新库 token 较大，旧实例仍可能继续向不支持 fencing 的目标写入。

**不能取得外部高水位时，禁止恢复后直接重新启用写入。** 当下游高水位不可枚举、审计不完整、存在多个存储域却只有部分数据、或 Provider 没有原子 fencing 能力时，恢复状态必须保持 BLOCKED；先人工处置旧协调器/旧写者和存储对象冲突，并形成经企业批准的恢复决策。不能用时间戳、旧备份中的最大 token、进程重启或 lease TTL 单独替代下游 fencing 高水位证据。

## 6. CI 证据及未覆盖风险

代码提交 1307ef462b920d9bf745ffb5ff5606e859f3a669 对应 [GitHub Actions Run 45751336613](https://github.com/rexyll/cnc-knowledge/actions/runs/45751336613)：全库217项 unittest 通过；CH12数值资源测试143项通过；knowledge_lint.py --strict 为 PASS（0 errors，5 warnings）；SQLite协调器CLI自检包含在线备份完整性与外部fencing高水位恢复验证，返回PASS；Artifact ID 15084844535。

本轮SQLite专项新增6项测试，SQLite协调器测试共18项；独立下游 fencing 合同新增8项测试。全部是GitHub Actions Linux runner上的本地/内存合成验证，不是多主机、真实云存储、供应商接口、断电、磁盘损坏或企业灾备演练。

未覆盖项仍包括：WAL/SHM与磁盘故障策略、加密和签名、访问控制、备份介质耐久性、保留/清理、旧数据库隔离、跨主机协调、自动心跳、持久QPS限流、真实 Provider 的条件事务、multipart 与 receipt 的 fencing 集成、下游高水位全量盘点和恢复切换演练。

生产备份继续关闭，governance_readiness=BLOCKED_PENDING_ENTERPRISE_APPROVAL，business_rule_assertions=NOT_EVALUATED。ASSET-000073～ASSET-000074的16个场景全部为 PROPOSED_NOT_APPROVED / NOT_RUN，不得视作已审批或已执行。


## 第三十轮补充：适配器层 token 贯穿与备份包 scope fencing

- 新增显式 BackupStorageAdapter(require_provider_fencing=True) 严格模式。缺少 admission coordinator、Provider supports_fencing 声明或必需 fenced 方法时启动失败，不回退到普通 PUT。默认值为False以兼容既有Provider；默认模式不得声称下游fencing开启。
- _bulkhead_slot()现在向内部调用者交付当前admission lease；_provider_call()把该lease的fencing_token传递给fenced callback。每个实际写操作独立获得租约；重试使用新token，但保留稳定idempotency key。
- 同一个备份包使用 object_prefix 作为统一 fencing_scope，覆盖payload PUT、multipart begin/part/complete和最后的 BACKUP-RECEIPT.json。scope高水位推进后，同包其他object key上更小token的迟到写入也应被拒绝。
- 新增 FencedMockObjectStorageProvider 作为合成夹具；不是生产Provider。严格模式测试覆盖：门禁、token传递、跨key stale writer、multipart part stale token、receipt以及complete响应丢失后的幂等重放。
- **代码CI：** [Run 45753519142](https://github.com/rexyll/cnc-knowledge/actions/runs/45753519142) 两个必需Job均completed/success；全库221项unittest、CH12数值资源143项通过；strict lint 0 errors（5 warnings）。Provider self-check中的 downstream_fencing_token_propagation_payload_multipart_receipt 为PASS；Artifact [15086063425](https://github.com/rexyll/cnc-knowledge/actions/runs/45753519142/artifacts/15086063425)。
- **生产边界：** 当前只有FencedMock内存夹具支持该合同。真实Provider仍需实现认证主体与授权scope绑定、持久scope高水位、对象/分块/完成/回执同事务原子提交及网络竞态故障验证；不能只根据supports_fencing布尔值认定供应商能力已通过审查。生产备份保持关闭。
