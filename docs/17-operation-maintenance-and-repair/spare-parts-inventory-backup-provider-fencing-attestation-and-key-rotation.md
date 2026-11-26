# Coordinator 签发的 scope-bound fencing attestation、Provider 验签与密钥轮换

**知识ID：** KNOW-000046  
**章节：** CH17 操作、维护与维修  
**状态：** IN_PROGRESS / 同主机参考实现及合成 CI 验证  
**实现：** scripts/spare_parts_fencing_attestation.py、scripts/spare_parts_provider_admission_sqlite.py、scripts/spare_parts_backup_storage_adapter.py、scripts/spare_parts_provider_sqlite_fenced.py

## 1. 威胁模型与目标

上一轮 SQLite fenced Provider 已有主体凭据、tenant/action/prefix ACL 和持久包级 high-water，但普通 Provider principal 无法证明送入的 token 来自可信 Coordinator。本轮增加 Coordinator 签名证明：Provider 对每次对象/multipart mutation 验证短期、不可篡改、绑定资源和幂等操作的证明，而不是只信任调用参数中的整数 token。

本轮信任假设：
- 应用调用者可能拥有合法 Provider principal secret，但不能因此获得 Coordinator token 签发能力。
- Coordinator 的 HMAC signing secret 只作为可信服务配置注入，不存入 admission SQLite。
- Provider 另有 trusted key registry，记录 issuer/key_id、算法、状态和有效时间；签名密钥本身不写入 Provider SQLite。
- 未持有 Coordinator signing secret 的调用者不能构造有效证明。
- Provider 仍是本机 Python 参考实现，HMAC verify secret 存在 Provider 进程内存，不防御进程内恶意代码或本机管理员。

## 2. 签发流程

1. BackupStorageAdapter 为一次 Provider mutation 获取 SQLite admission lease。
2. Coordinator 在 BEGIN IMMEDIATE 事务中重新读取该 lease，检查 lease 仍为 ACTIVE、未超时、行记录与传入 lease 的完整字段完全一致。
3. Coordinator 核对 resource key 是 fencing scope 的后代，核对 operation 和 idempotency key 格式。
4. Coordinator 创建短期 claims 并用配置的 HMAC-SHA256 key 签名。
5. Adapter 将 token 和 attestation 一起发给 Provider。
6. Provider 验签，校验 claims 与当前方法参数逐项相等；随后在 Provider 写事务内再查 trusted_fencing_keys 状态/有效期、主体 tenant/action/prefix ACL 和 scope high-water。
7. 同一个事务提交对象或分块、fencing high-water、幂等回执与审计。

Coordinator 默认 attestation TTL 为15秒，签名证明 expires_at = min(lease.expires_at, issued_at + configured TTL)。Coordinator TTL 最大限制60秒；Provider最多接受60秒的证明，且仍须满足实际 expires_at、lease_expires_at 和 key registry 时间边界。

## 3. 签名证明字段

当前 claims 固定为15个字段，拒绝额外或缺失字段：

| 字段 | 约束 |
|---|---|
| v / iss / kid | 协议版本、受信任签发者和 key ID |
| lease_id / owner_id | Coordinator lease 和 owner 身份 |
| tenant_id / domain | 租户与准入域（write/multipart） |
| fencing_token | 正整数 fencing 序列 |
| issued_at / expires_at / lease_expires_at | 签发时间、短证明期限及原 lease 到期时间 |
| fencing_scope | 备份包级 fencing scope |
| resource_key | 精确对象 key |
| operation | object:put_if_absent、multipart:begin、multipart:put_part、multipart:complete |
| idempotency_key | 当前操作的幂等标识 |

规范化 JSON 使用排序字段和紧凑编码；token 格式 v1.kid.payload.signature；签名输入包含协议域分隔符、版本、kid 与 payload，签名比较使用恒定时间 compare_digest。Provider 检查签名、issuer/key ID、tenant、scope、resource key、operation、token、idempotency key、domain 和时间条件。

## 4. 绑定和重放语义

证明同时绑定 tenant + scope + resource_key + token + lease_id + owner_id + domain + operation + idempotency_key。将 proof 用于另一 tenant、scope、object key、operation、token 或幂等键都会被拒绝。

证明不是一次性 nonce：同一操作在响应丢失后允许使用相同 idempotency key 重放，以取回原始操作结果。Adapter 的每次重试会重新申请 lease 并签发新 proof，但逻辑 idempotency key 不变。重放内容不同或幂等键复用到另一操作仍由 Provider 的 operation hash 冲突保护。

## 5. Key registry 与轮换操作

Provider 表 trusted_fencing_keys 只保存 issuer_id、key_id、algorithm、status、not_before、not_after、created_at，不存 HMAC secret。Provider 构造时需从外部受控配置加载 key ring；每次 fenced mutation 事务重新查询 key registry，允许 ACTIVE 和 RETIRING key，REVOKED 或过期 key立即拒绝。

本地管理员 API：
- admin_register_trusted_attestation_key：登记新 issuer/key_id 的 ACTIVE 元数据，不写密钥本身；
- admin_set_trusted_attestation_key_status(status=RETIRING, not_after=...)：保留旧 key 的有限兼容窗口；
- admin_set_trusted_attestation_key_status(status=REVOKED)：立刻撤销，REVOKED 状态不可恢复。

推荐轮换顺序：
1. 通过受控本机管理员流程将新 key_id 登记为 ACTIVE。
2. 把新 key 的 secret 分别注入 Coordinator signer 和 Provider key ring，保留旧 key。
3. 将 Coordinator signer 切换到新 key_id，并用新 key 生成 proof。
4. 将旧 key 标记 RETIRING，设置 not_after 大于短期 proof 最大有效期限和允许的时钟偏差。
5. 确认旧 key proof 已过期后将旧 key 标记 REVOKED，并从 Provider 运行时 key ring 移除。

这些 admin_* 接口只依赖本机数据库文件所有者权限，没有独立管理员认证/远程管理 API。必须通过 OS 账户、目录权限、备份加密及部署流程控制。若调用主体能直接修改 Provider SQLite 文件，就处于数据库管理员信任域内。

## 6. 有界撤销延迟与 HMAC 参考实现限制

Coordinator 在 proof 签发时验证 lease ACTIVE，但 Provider 不对每次 mutation 远程回查 Coordinator；在 proof 签发后立即 release/取消 lease，不会同步撤销已经签发的 proof。该 proof 最多仍可使用至 expires_at（默认不超过15秒）。在此窗口内，后续较高 token 推进 scope high-water 后，旧 token 会被挡住；若要求 lease release 立即阻止已签 proof，则还需要 Provider 在线查 Coordinator 或使用共享的原子撤销状态。本轮没有实现网络撤销服务。

HMAC 是本地参考算法：Coordinator 与 Provider 都注入同一对称秘密；Provider 进程持有 verify secret，因此不应把该 Python Provider 暴露给不可信租户代码，也不能声称实现了“仅有公钥的服务端验签”。生产远端 Provider 应优先采用非对称签名（例如 Coordinator/KMS 持有 Ed25519 私钥，Provider 只持公钥），并实现密钥版本、撤销、时钟同步与审计服务。当前没有 KMS/HSM、TLS、远程身份、密钥托管或多主机网络验证。

## 7. CI 验收

[CI Run 45758028329](https://github.com/rexyll/cnc-knowledge/actions/runs/45758028329) 对代码提交 f4c26e61f0136b2d487ec009ae9f8259af090314 完成：
- 全库248项 unittest 通过；
- CH12 数值资源测试143项通过；
- strict knowledge lint：PASS（0 errors，5 warnings）；
- Provider fenced CLI self-check：PASS；
- Provider fenced artifact ID 15087973420；
- Admission coordinator artifact ID 15087604559；
- Provider adapter artifact ID 15087868629。

新增 Coordinator/Provider 专项测试覆盖活动 lease 签发、释放后拒绝、resource scope 越界、签名篡改、tenant/scope/resource/operation/idempotency 绑定、过期 proof、ACTIVE/RETIRING/REVOKED key 轮换，以及 Strict Adapter 对 payload/multipart/receipt 的证明透传。以上均为本地合成软件测试，非供应商或现场验收。

生产备份仍关闭：governance_readiness=BLOCKED_PENDING_ENTERPRISE_APPROVAL，business_rule_assertions=NOT_EVALUATED。
