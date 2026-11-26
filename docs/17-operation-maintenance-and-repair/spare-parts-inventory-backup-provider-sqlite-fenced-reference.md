# 数控机床备件库存备份 SQLite fenced Provider 参考实现、主体授权与恢复门禁

**知识ID：** KNOW-000045  
**状态：** IN_PROGRESS / 同主机本地参考实现与合成 CI 验证  
**实现：** scripts/spare_parts_provider_sqlite_fenced.py  
**测试：** tests/test_spare_parts_provider_sqlite_fenced.py

## 1. 目标和范围

本轮把 KNOW-000044 的适配器 fencing 调用链落到一个持久化 Provider 参考实现：SQLiteFencedObjectStorageProvider。Provider 数据库负责独立维护 tenant + backup object_prefix 的高水位，并将授权检查、token 比较、对象或分块变更、幂等回执及审计放在同一 SQLite 写事务中。

它是**同主机、本地文件、多进程共享的参考实现**，不是网络对象存储服务、云厂商适配器、多主机分布式存储或生产批准实现。

## 2. 主体认证和授权

provision_database 只能创建新数据库，不覆盖现有文件。主体记录包含 principal_id、tenant_id、允许的 action、allowed_prefixes，以及 PBKDF2 verifier。每个 principal 使用随机16字节 salt，PBKDF2-HMAC-SHA256 210,000次迭代；数据库不保存明文 secret。Provider 初始化会话时验证 bearer secret，此后每次数据事务重新检查主体是否启用，并用数据库内的 tenant/action/prefix ACL 校验请求。

接口形状：

\`\`\`python
SQLiteFencedObjectStorageProvider.provision_database(
    provider_db,
    principals=[{
        "principal_id": "backup-writer",
        "tenant_id": "site-a",
        "principal_secret": secret_from_secret_store,
        "allowed_prefixes": ["cnc/ch17"],
    }],
)
provider = SQLiteFencedObjectStorageProvider(
    provider_db, principal_id="backup-writer",
    principal_secret=secret_from_secret_store,
)
\`\`\`

示例 secret 仅来自受控运行时/secret store，不得写入仓库或日志。当前没有 principal 创建、禁用、轮换的管理 API；数据库主文件权限设置为0600，但目录权限、WAL/SHM、备份介质和运行账户仍需操作系统层加固。该方案不是 TLS 网络 IAM。

拒绝操作会 fail-closed，并尝试写入独立 DENY 审计记录；若数据库本身不可写，DENY 日志可能不能持久化，但操作仍然被拒绝。成功和重放事件在业务事务中留有审计元数据。

## 3. 服务端原子 fencing

SQLite 使用 WAL、synchronous=FULL 和 BEGIN IMMEDIATE。关键表包括：

- fencing_scopes：按 tenant_id + fencing_scope 存储单调 high_water；
- fenced_operations：按 scope + idempotency_key 存储操作类型、内容哈希和原结果；
- provider_objects：不可变对象字节、SHA-256、scope 与 token；
- multipart_sessions / multipart_parts：会话、状态、分块和摘要；
- provider_principals / provider_audit：主体 ACL 与审计数据。

每个 fenced 写入在同一事务中执行：检查主体和授权范围；读取 scope high-water 以及恢复底线；小于 high-water 的 token 直接拒绝；幂等键若对应不同操作或内容则拒绝；提交对象/part/session、更新 high-water、写幂等结果和审计。事务任一步失败就整体回滚，避免对象已写入但 fence 未更新的半状态。

同一个备份包的 payload、multipart begin/part/complete 和 receipt-last 继续共用 object_prefix scope。因此，一个 object key 上的较新 token 推进高水位后，同包其他 key 上的旧 token 也会被拒绝。

## 4. 仍需解决的 token 来源认证问题

**当前 Provider 尚未验证 fencing token 是否确实由可信 admission coordinator 签发。** 它验证主体凭据、ACL、token 值、scope 和单调高水位，但没有 scope-bound HMAC/signature attestation。持有有效 Provider principal secret 的本地应用进程如果能直接调用 fenced 方法，仍可能提交一个异常大的 token，导致该 scope 后续合法写入被拒绝。

因此本实现只能由受信任备份服务进程在本地调用，不能暴露给租户终端、不可信插件或一般客户端。生产化前必须增加由 coordinator 签发、按 tenant + scope + token + lease 身份绑定的 HMAC/签名证明，Provider 必须验证证明并在事务内比较 high-water。Provider principal secret 不是 token 签名密钥。

## 5. 对象和 multipart 合同

- put_if_absent_fenced：不可变对象条件创建；相同内容可幂等重放，不同内容冲突。
- begin_multipart_upload_fenced：会话创建也受 scope fence 保护。
- put_multipart_part_fenced：每个分块核验 part number、SHA-256 并与 fence 一同提交。
- complete_multipart_upload_fenced：完整检查分块序列、总字节数和摘要，原子提交对象、会话完成态、fence 和幂等回执。
- 非 fenced 的 PUT、multipart begin/part/complete 与 unfenced abort 明确拒绝；读取、prefix inventory、multipart read/list 仍可用。

响应丢失时，重试必须使用同一 idempotency key 和更新的 coordinator token，Provider 返回原结果并推进 high-water，不重复创建另一份对象。

## 6. SQLite online backup 和新库恢复准备

backup_to 使用 SQLite online backup API 生成新文件，并运行 integrity_check、foreign_key_check、schema/table 检查与 SHA-256 计算。目标路径必须不存在。

restore_to_new_database 要求 operator 提供独立取得的 external_fencing_floor 和 fencing_reconciliation_ref，只准备一个新数据库，不覆盖源库、不执行客户端 cutover。准备步骤会将已有 scope high-water 提升到 external floor，将全局 minimum_fencing_token 设为 floor，清理恢复快照中的未完成 multipart sessions/parts，并保留已提交对象和幂等记录。

该恢复 API 仅校验 floor 类型/范围及 reconciliation reference 非空，不会验证证据的真实性或自行从 coordinator 取 floor。必须由受控恢复流程提供独立可信 floor，并进行人工/企业审批后再切换。不能用过期备份加一个占位引用替代真实核验。

## 7. CI 及限制

[CI Run 45755448153](https://github.com/rexyll/cnc-knowledge/actions/runs/45755448153)：
- 全库241项 unittest 通过；
- CH12 数值资源测试143项通过；
- knowledge_lint.py --strict：PASS（0 errors，5 warnings）；
- SQLite fenced Provider CLI self-check：PASS；
- Provider self-check Artifact ID 15087184041；
- SQLite admission Artifact ID 15087452634；Provider adapter Artifact ID 15087507413。

新增20项专项 unittest 覆盖主体凭据、ACL、租户隔离、跨 key stale token、幂等/冲突、事务回滚、响应丢失重放、multipart、多进程竞争、online backup/restore、external fencing floor 和 strict adapter 端到端发布。ASSET-000076定义22条正式参考验收场景，均为 PROPOSED_NOT_APPROVED / NOT_RUN。CI 合成测试不等于供应商、现场或企业验收。

**尚未完成：** scope-bound coordinator token attestation；主体 secret 生命周期管理；加密静态数据；跨主机/网络服务；多主机事务；幂等记录保留/压缩；真实云/本地生产 Provider 验收；生产恢复切换演练。生产备份仍关闭，governance_readiness=BLOCKED_PENDING_ENTERPRISE_APPROVAL，business_rule_assertions=NOT_EVALUATED。


## 8. 第三十二轮 Coordinator scope-bound attestation 补充

Provider 已从“只校验 token 整数”升级为要求 fencing_attestation。Coordinator 仅对数据库中 ACTIVE 且字段完全匹配的 lease 签发15秒默认TTL HMAC-SHA256证明；证明绑定issuer/key ID、lease/owner、tenant、domain、token、scope、resource key、operation和idempotency key。Adapter每次mutation（payload、multipart begin/part/complete、receipt-last）按当前lease获取新证明。

Provider在SQLite事务内重查trusted_fencing_keys，支持ACTIVE/RETIRING/REVOKED状态。新增本地admin注册、退役和撤销接口；密钥本身不入库。新增KNOW-000046和ASSET-000077，定义20条attestation/rotation场景。见 [Coordinator attestation与key rotation](spare-parts-inventory-backup-provider-fencing-attestation-and-key-rotation.md)。

**验收：** CI Run 45758028329两个必需Job均success；全库248项unittest、CH12 143项测试通过；strict lint 0 errors/5 warnings；Provider CLI self-check PASS（Artifact 15087973420）。

**保留限制：** HMAC秘密同时注入Coordinator及Provider本地进程，不是公钥验签；已签proof在lease release后仍可使用到expires_at，默认最多15秒。生产远端Provider应采用Coordinator/KMS私钥+Provider公钥的非对称签名，并实现在线撤销、时钟同步及KMS/HSM；本地SQLite仍不支持多主机。生产备份关闭。
