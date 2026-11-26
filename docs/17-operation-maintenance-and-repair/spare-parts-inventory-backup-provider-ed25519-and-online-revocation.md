# Provider Ed25519 公钥验签、KMS 签名回调与在线租约状态检查

**知识ID：** KNOW-000047  
**章节：** CH17 操作、维护与维修  
**状态：** IN_PROGRESS / 本地参考实现及合成 CI 验证  
**依赖：** requirements-ch17-security.txt（cryptography==50.0.2）

## 1. 协议版本

本轮在原 HMAC v1 之上新增 Ed25519 v2。两版可在迁移窗口并存：

| 版本 | 签名 | Provider key material | 用途 |
|---|---|---|---|
| v1 | HMAC-SHA256 | 对称 secret | 既有本地参考/迁移兼容 |
| v2 | Ed25519 | 公钥 | 新版 Coordinator 签名和 Provider 公钥验签 |

Ed25519 v2 token 结构为 v2.ed25519.kid.payload.signature。claims 为16项，保留原来的 lease、tenant、domain、token、scope、resource、operation、idempotency 和时间字段，并增加 alg=ED25519。签名输入含协议域分隔符、版本、算法、key ID 和规范化 payload。

## 2. Coordinator 私钥边界和签名回调

新增 FencingAttestationSigner 协议和 CallbackEd25519Signer：
- Coordinator 只依赖 signer.algorithm、signer.key_id 和 sign(signing_input)；
- CallbackEd25519Signer接收一个签名 callback，返回64字节 Ed25519 signature；
- callback可由部署系统连接KMS/HSM远程签名接口；
- Ed25519PrivateKeySigner仅是本地测试/参考实现，支持raw seed或PEM私钥。

Coordinator SQLite 不保存私钥。当前仓库没有云 KMS/HSM SDK、凭据、网络或服务端连接；callback只是可替换接入点，不能宣称已经接入任何云 KMS。生产部署应由KMS/HSM保护私钥并通过受控远程签名接口提供签名，禁止把私钥存入配置文件、Provider数据库或Git仓库。

## 3. Provider 公钥注册与轮换

Provider构造时注入 trusted_ed25519_public_keys。Ed25519-only部署可以不配置HMAC secret。Provider使用公钥验签，trusted_ed25519_keys注册表只保存：
- issuer_id / key_id / algorithm=ED25519；
- public_key_sha256 指纹；
- ACTIVE / RETIRING / REVOKED；
- not_before / not_after / created_at。

新增接口：
- admin_register_trusted_ed25519_key：登记issuer、key ID和公钥SHA-256指纹，不保存公钥私钥材料；
- admin_set_trusted_ed25519_key_status：标记RETIRING并设置截止时间，或设置REVOKED。

Provider运行时公钥必须与数据库登记指纹一致；密钥状态在每次Provider写事务中重查。推荐先登记新公钥指纹并把新公钥注入Provider，再将Coordinator signer切换到新KMS key ID，观察新旧key重叠窗口，最后退役并撤销旧key。HMAC v1与Ed25519 v2可以并存迁移；完成部署切换后应撤销旧HMAC key并从Provider运行时key ring移除。

## 4. 在线 lease 状态查询

新增Coordinator方法 SQLiteProviderAdmissionCoordinator.is_attestation_active(claims)，根据lease_id回查：
- state必须为ACTIVE；
- 数据库expires_at必须晚于Coordinator时钟；
- owner_id、tenant_id、domain、fencing_token必须与已签发claims一致；
- proof expires_at不得超过Coordinator记录的lease expiry；
- issuer必须匹配当前Coordinator身份配置（若有）。

Provider可配置：
- attestation_status_checker：提供is_attestation_active(claims)的状态检查器；
- require_online_attestation_status=True：强制启用在线查询；缺少checker时Provider初始化失败。

Provider先完成签名、claims、租户、scope和key registry验证，再在持有Provider本地写事务期间查询Coordinator状态。查询返回false（lease已释放、已过期、身份不匹配或未知）时拒绝写入。查询异常/Coordinator不可用时包装为FencingAttestationStatusUnavailableError，回滚Provider写事务，不允许降级为仅本地验签。

## 5. 在线撤销的准确边界

当前实现的是“下一次写操作时在线复查lease状态”，而不是由Coordinator向所有Provider主动推送撤销通知。SQLite参考checker访问同机Coordinator数据库；没有实现HTTP/gRPC服务、远程认证、重试隔离或跨主机缓存一致性。

重要竞态：Coordinator status query和Provider对象commit发生在两个独立SQLite数据库/事务中。若Coordinator在检查返回ACTIVE之后、Provider事务提交之前释放lease，写操作仍可能在该小窗口内提交。因此该方法降低已释放proof被重用的风险，但不是线性一致的即时撤销，也不能宣称zero-TOCTOU。要提供严格顺序，需要把lease状态与资源写入置于同一线性化事务/服务中，或使用Provider原生条件写和单调fencing high-water确保所有迟到token被下游拒绝。多主机远程Provider还需要网络化Coordinator、认证、超时、观测、服务降级和故障演练。

当前推荐策略：生产写入在Coordinator状态未知/不可达时一律fail-closed；不得缓存“上次有效”状态后继续写。Coordinator恢复后通过新的lease获取与新proof重试，保持同一逻辑operation的idempotency key。

## 6. CI与测试

[CI Run 45760844653](https://github.com/rexyll/cnc-knowledge/actions/runs/45760844653)：
- 全库252项unittest通过；
- CH12数值资源143项通过；
- strict knowledge lint PASS（0 errors，5 warnings）；
- Provider fenced self-check PASS；
- Provider artifact 15089847421；
- Admission coordinator artifact 15089209106；
- Adapter artifact 15089074481。

新增测试覆盖：
- Ed25519 callback signer签发v2证明；
- Provider只装载公钥、不装载HMAC secret也可验签；
- 公钥SHA-256指纹与Provider注册表一致；
- 当前ACTIVE lease通过在线状态检查；
- lease释放后下一次Provider写入被拒绝；
- Coordinator状态检查失败时Provider fail-closed且对象不落库；
- 原HMAC v1测试继续通过。

新增ASSET-000078包含22条形式化参考场景，全部PROPOSED_NOT_APPROVED / NOT_RUN。CI合成测试不是生产KMS验证、供应商验收、现场试验或多主机测试。

生产备份仍关闭：governance_readiness=BLOCKED_PENDING_ENTERPRISE_APPROVAL，business_rule_assertions=NOT_EVALUATED。
