# Provider Grant Floor 回执来源认证与签名证据设计

- **章节：** CH17 运维、备份与恢复
- **关联任务：** MIG-05；Provider Grant Floor / Grant-aware Restore
- **状态：** 设计稿（Round 94）；尚未实现
- **适用对象：** Provider Grant FENCE / ACTIVATE 的外部 Floor 对账协议
- **重要边界：** 本文定义可验证的回执证据契约，不代表真实 Provider、KMS/HSM、etcd 或生产 Unified authority 已实现或接入

## 1. 问题与设计目标

第九十二轮建立了独立于 Provider SQLite 文件和备份域的 ProviderGrantFloorAuthority 参考端口。FENCE/ACTIVATE 采用外部 reserve → Provider commit → external receipt confirm 的双边流程，外部 authority 按 Provider/tenant/scope 保存 generation floor、Coordinator Leader epoch floor、pending operation、command digest、Provider receipt digest 和 revision。

当前 confirm_provider_receipt() 只接收调用方提供的 provider_receipt_digest 字符串。它可以把该摘要与已预留 operation / command digest 关联，但它不能证明：

1. 摘要是否来自目标 Provider；
2. Provider 是否真的提交了对应 FENCE/ACTIVATE；
3. 回执是否属于相同 Provider、tenant、scope、Grant generation 和 Coordinator Leader/native Lease；
4. 回执的结果状态是否与当前 pending 操作一致；
5. 调用方是否伪造或替换了 receipt digest。

因此，现有 SQLite Floor 模型证明的是“调用方提交了一个格式正确、可重复比较的摘要”，而不是“目标 Provider 对指定命令作出了可认证的持久化提交证明”。

本轮目标是冻结 Provider-native signed receipt envelope、验签信任模型、外部 Floor 对账门禁和故障恢复语义。后续实现必须保证：**未经目标 Provider 信任密钥验签、且没有精确绑定 pending reservation 的回执，不得推进外部 generation/epoch floor 状态。**

## 2. 威胁模型与信任边界

### 2.1 要防御的错误与攻击

- Coordinator 调用方错误地传入随机 SHA-256 字符串或其他 Provider 的 receipt digest。
- 回执在传输、队列、日志或人工处理期间被篡改。
- 将 Provider A、tenant A 或 scope A 的回执重放到 Provider B、tenant B 或 scope B。
- 把 FENCE 回执用作 ACTIVATE 确认，或把旧 generation 的回执绑定到新 operation。
- 对同一 command digest 提交不同的回执内容，试图替换已确认的 applied time 或 result state。
- 未知 Provider signer key、撤销密钥或超出有效期的密钥签发的回执被错误接受。
- Coordinator 在 Provider 提交成功但响应丢失后，错误创建新 operation 或新 command，造成 generation 重复推进。

### 2.2 信任主体

1. **Coordinator command signer：** 签署 FENCE/ACTIVATE 命令。其密钥证明“哪个 Coordinator Leader/Lease 请求执行什么命令”。
2. **Provider receipt signer：** 由 Provider 自身控制的独立 Ed25519 密钥。其密钥证明“哪个 Provider 对该精确命令持久化了什么结果”。
3. **ProviderGrantFloorAuthority：** 保存可信 Provider public-key registry，验证 Provider receipt envelope，并在精确 scope revision CAS 中确认回执。
4. **外部信任配置发布者：** 通过独立、受控的配置/密钥发布通道维护 Provider receipt public key。不能允许普通 Coordinator 调用方自行注册一个密钥，再用该密钥证明自己的 receipt。

Coordinator command key 与 Provider receipt key 必须是两个独立信任域；不能因为二者都使用 Ed25519 就复用同一把私钥。

### 2.3 不在本轮证明的事项

- 不证明 Provider 软件本身没有恶意或漏洞。Provider 私钥可签署虚假状态时，验签无法判断业务事实真假。
- 不证明 Provider 主机、SQLite 文件或私钥在系统被攻陷后仍可信。
- 不证明 etcd Lease 与 Provider 数据库提交跨系统原子。
- 不证明本地 SQLite Floor 数据库自身不可被旧快照覆盖。
- 不把签名 receipt 等同于生产 Provider 的合规审计、不可抵赖或硬件根信任证明。

## 3. 规范化 Receipt Envelope

### 3.1 Envelope 形状

建议采用独立于 Coordinator command envelope 的 Provider receipt envelope。以下为合成结构示例：

    {
      "format": "cnc-provider-grant-receipt-envelope-v1",
      "receipt": {
        "format": "cnc-provider-grant-receipt-v1",
        "provider_id": "provider-test-a",
        "tenant_id": "tenant-a",
        "scope": "cnc/ch17/backup-reference-001",
        "action": "FENCE",
        "grant_id": "grant-001",
        "generation": 11,
        "command_sha256": "<64 lowercase hex>",
        "result_state": "FENCED",
        "coordinator_namespace": "/cnc/migration/isolated/provider-grant-test/",
        "leader_id": "coordinator-leader-a",
        "leader_epoch": 7,
        "native_lease_id": 701,
        "native_lease_expires_at_unix": 1800000120.0,
        "command_issued_at_unix": 1800000000.0,
        "command_expires_at_unix": 1800000060.0,
        "applied_at_unix": 1800000001.25
      },
      "signature": {
        "algorithm": "Ed25519",
        "key_id": "provider-receipt-ed25519-v1",
        "value_base64": "<base64 signature>"
      }
    }

以上标识和时间均为合成值，不代表实际 Provider 数据。

### 3.2 Receipt claims 的强制绑定字段

| 字段 | 含义与验证要求 |
|---|---|
| format | 严格版本标识；不接受未知版本或未知字段 |
| provider_id | 与外部 Floor 的 ProviderGrantScopeKey.provider_id 精确一致 |
| tenant_id | 与 reservation tenant 精确一致 |
| scope | 与 reservation fencing scope 精确一致 |
| action | 只能是 FENCE 或 ACTIVATE |
| grant_id | 与 reservation grant ID 精确一致 |
| generation | 与 reservation generation 精确一致，正的 SQLite-safe 整数 |
| command_sha256 | 目标 Provider 实际应用的原始 Coordinator signed command envelope 的 SHA-256；必须与 pending reservation 的 command digest 一致 |
| fence_command_sha256 | FENCE 必须为 null；ACTIVATE 必须绑定外部 Floor 最近一次已确认的 FENCE command digest |
| result_state | FENCE 必须为 FENCED；ACTIVATE 必须为 ACTIVE |
| coordinator_namespace | 与已签名 command claims / reservation 精确一致，继续受 isolated namespace 策略约束 |
| leader_id、leader_epoch | 与已签名 command claims 精确一致 |
| native_lease_id、native_lease_expires_at_unix | 与已签名 command claims 精确一致；expiry 不得在同一 Leader/Lease 代次中回退 |
| command_issued_at_unix、command_expires_at_unix | 与 Provider 验证过的原 command claims 精确一致 |
| applied_at_unix | Provider 持久化提交该状态转换时采集的时间；有限、非负，并处于命令允许的有效时间窗内 |

Receipt 不需要独立接收调用方提供的 operation ID。Floor reservation 已将 operation ID 与唯一 command digest 持久绑定；Provider receipt 以该精确 command digest 作为跨系统相关键，Floor 在确认时再核对 operation ID 对应的 reservation。这样避免 Provider 命令协议与某一类外部 Floor 数据库的内部 operation ID 形成不必要的耦合。

### 3.3 Canonical serialization 与摘要

- Receipt claims 与 envelope 使用 RFC 8785 JSON Canonicalization Scheme（JCS），以避免不同语言对键排序、Unicode 和数字表示产生不同签名字节。实现必须通过 JCS 一致性向量，不能仅把某语言的普通 JSON stringify 当作跨语言标准。
- 禁止 NaN、Infinity、重复键、未知字段、无效 Unicode 和非规范数字表示。
- 整数身份字段必须使用 JSON integer，不能把 bool 当作整数；generation / epoch / Lease ID 限定在 SQLite signed 64-bit 正整数范围。
- 浮点时间必须有限、非负；比较时不将其转换为本地时区字符串。
- receipt_digest 由完整 canonical envelope（含 signature）直接计算：SHA-256(canonical_json(envelope))。
- command_sha256 必须使用生成原 Coordinator command 时对应版本的 canonical envelope 字节计算，并与 Provider command verifier 实际接受的字节规则一致；不能对已签名 command 重新序列化后换一种 canonicalizer 再计算。当前 command verifier 的 canonicalization 规则应在实现时作为独立版本固定并纳入一致性测试。
- 不接受调用方同时传入一个 claims 对象和一个独立摘要，再由服务器默认相信两者一致；摘要只能在 envelope schema、签名、绑定和时间验证全部通过后由 verifier 重算。

## 4. Ed25519 签名协议

建议定义固定签名域：

    SIGNING_DOMAIN = b"cnc-provider-grant-receipt-v1\x00"
    signing_input = SIGNING_DOMAIN || key_id_ascii || b"." || canonical_json(receipt)

验证必须满足：

1. Envelope 顶层字段集合严格等于 {format, receipt, signature}。
2. format、receipt format、signature 字段集合及算法严格匹配版本定义。
3. key_id 使用受限 ASCII 标识格式；base64 必须采用严格解码，Ed25519 signature 长度必须为64字节。
4. provider_id + key_id 必须在外部 Floor 的可信 Provider receipt key registry 中存在，且 public key 与其指纹一致。
5. Ed25519 验签成功后，重算 canonical envelope SHA-256，并继续执行第6节的 reservation/state/time binding 检查。
6. 即使签名有效，任何 provider/tenant/scope/action/grant/generation/command/leader/Lease 不一致仍必须拒绝。

Receipt signature 是针对 Provider 的 durable command receipt，不得用 Coordinator 命令签名密钥代签。Provider receipt key 的私钥不得写入外部 Floor SQLite 数据库、备份文件或普通日志。

## 5. Provider 如何生成可验证的提交回执

### 5.1 与 Provider mutation 的事务关系

Receipt 必须证明 Provider 已经完成目标状态转换。因此 Provider 不能在状态转换之前就把“即将提交”当成成功回执对外发布。

推荐 Provider 内部流程：

1. 验证 Coordinator signed command、Provider/tenant binding、Leader/Lease 约束和本地 grant generation 规则。
2. 在同一 Provider 写事务内更新 grant state、command receipt 和不可变 receipt claims（包含实际 applied_at_unix）。
3. 使用 Provider receipt signing key 对规范化 receipt claims 签名，并将完整 envelope、签名 key ID 与其 digest 一并写入同一事务。
4. 提交 Provider 事务后，receipt lookup API 才能按 exact command_sha256 返回该 envelope。
5. 若事务回滚，不得留下可被 Floor 接受的成功 receipt。
6. 若响应丢失，按原 command digest 查询同一条 durable receipt；不得重新执行 generation 推进。

本地私钥可以在事务内完成签名。若真实部署通过远程 KMS/HSM 签名，不能为了避免持有写锁而提前返回 unsigned success。可选择在 Provider 中持久化不可变的 RECEIPT_SIGNING_PENDING 记录，在签名完成并二次持久化前不向外部 Floor 提供成功证明；其间外部 reservation 继续 PENDING，任何下一代 FENCE/ACTIVATE 都必须被阻断。HSM 超时或结果未知时，仅允许对相同的不可变 receipt payload / digest 查询或重试签名，不得创建不同 claims。

### 5.2 Receipt 查询 API

Provider 应提供只读、按原始 command_sha256 精确查询的接口，例如：

get_provider_grant_receipt(provider_id, tenant_id, command_sha256)

契约要求：

- 精确 Provider、tenant 和 command digest 三元组，不接受模糊查询或“当前 grant 状态”替代历史 receipt。
- 如果 command 已提交，返回同一条 canonical signed receipt；重复读取必须保持 digest 不变。
- 如果命令不存在或未提交，返回明确的 NOT_FOUND / NOT_COMMITTED 结果；不得制造成功 receipt。
- 如果 Provider 已提交但签名还在 pending，返回显式待签名状态，不能降级为普通字符串 digest。
- 对已提交 receipt 的原始 envelope 不可覆写；密钥轮换不能修改历史 receipt 的签名或 claims。

## 6. 外部 Floor 的验签与确认门禁

### 6.1 确认输入

将现有“裸摘要确认”收敛为强类型 Evidence 路径。设计上可提供：

- ProviderGrantReceiptEnvelope：未验证的解析结果，仅表示字节/JSON 输入；
- VerifiedProviderGrantReceipt：只有经过 verifier 完整验签和 binding 后才可构造的内部对象；
- ProviderGrantReceiptVerifier：按 Provider trust registry 验证 envelope 的端口；
- confirm_provider_receipt(operation_id, receipt_evidence, expected_revision)：接收 envelope 或内部 verified object，并在 authority 内重新核对 pending operation。

不应保留一个可被业务调用方使用的、只凭任意 provider_receipt_digest 就能推进状态的生产路径。测试辅助 API 可以显式注入 synthetic verifier，但默认必须 fail-closed。

### 6.2 FENCE 确认

仅当同时满足以下条件时，外部 Floor 才可将 FENCE_PENDING 推进为 FENCED：

- operation ID 精确存在且 action 为 FENCE；
- 当前 scope revision 与 reservation 中的 revision 完全相同，CAS 成功；
- Provider receipt 的签名者属于该 Provider 的受信 key registry；
- Provider、tenant、scope、grant ID、generation 与 reservation 完全一致；
- receipt command_sha256 等于 reservation 的 exact command digest；
- result_state == FENCED；
- namespace、Leader ID/epoch、native Lease ID/expiry 与已签名命令一致；
- applied_at_unix 满足签名命令 expiry 与允许的时钟偏差约束；
- 当前 scope 不存在其他未决或 RECOVERY_REQUIRED operation。

通过后，Floor 保存由 envelope 重算的 receipt digest、signer key ID、验证时使用的 trust revision、Provider applied time，并推进 scope revision。调用方提交的任意摘要不得覆盖 verifier 计算结果。

### 6.3 ACTIVATE 确认

除第6.2节的通用验证外，还必须满足：

- scope 当前确实为已确认的 FENCED；
- ACTIVATE reservation 绑定最近一次已确认 FENCE command digest；
- ACTIVATE receipt command_sha256 等于当前 ACTIVATE reservation；
- receipt fence_command_sha256 精确等于已确认 FENCE command digest；
- result_state == ACTIVE；
- Provider applied time 不早于已确认 FENCE receipt 的 applied time；
- FENCE 与 ACTIVATE receipt 的 Provider、tenant、scope、Grant、generation、Coordinator Leader/native Lease 身份一致，并满足 generation 的既定推进规则。

任何一项不一致，都不得将外部 Floor 标为 ACTIVE。

### 6.4 幂等与替换

- 同一 operation、同一 command digest、同一 verified receipt digest 的重放可返回既有结果，不得再次推进 generation 或 revision。
- 同一 operation / command digest 若出现不同 receipt digest、不同 signer identity 或不同 claims，必须拒绝替换，并将 scope 标记为需要人工/恢复流程处理的状态（具体状态由实现轮次冻结）。
- 不允许仅因签名 key 轮换就改写已确认 receipt digest；历史证据保持不可变。
- operation ID 被重复用于不同 scope/action/command 时，继续按 Round 92 的唯一性约束拒绝。

## 7. Provider receipt key 生命周期

### 7.1 独立 trust registry

外部 Floor 必须维护独立的 Provider receipt signer registry，至少记录：

- provider_id、key_id、算法和 raw public key / SHA-256 fingerprint；
- not_before、not_after、status；
- revocation_effective_at 与撤销原因/审批记录；
- registry trust revision / 配置版本；
- key 加入、轮换、退役和撤销的审计事件。

Registry 不得仅从待验签 receipt 自身下载 public key 并自动信任。密钥注册/替换须通过独立管理通道、审批和审计完成；Provider 数据库备份不应成为唯一 trust anchor。

### 7.2 轮换与撤销策略

建议状态：

| 状态 | 新回执签发 | 历史回执验证 |
|---|---|---|
| ACTIVE | 允许 | 允许（必须在 key validity window 内） |
| RETIRING | 禁止新签发；Provider 应切换到新 ACTIVE key | 允许历史回执 |
| REVOKED | 禁止 | 根据 revocation_effective_at 和撤销原因决定；默认按 fail-closed 策略处理 |

- 正常轮换：旧 key 转为 RETIRING，新 key ACTIVE；历史 receipt 在旧 key 有效时间窗内仍可验证。
- 密钥泄露/疑似泄露：撤销生效时间应回溯至最早可能受影响时间；该时间之后签出的 receipt 不得被接受。
- 若无法确定泄露起始时间，不能擅自假设历史 receipt 安全；需要人工恢复、重签或重新 FENCE。
- 未知 key、无可信公钥、fingerprint mismatch、trust registry 不可用或 revision 低于受信 checkpoint 时均 fail-closed。

## 8. 时钟、有效期与持久化语义

- Coordinator command 的 issued_at_unix、expires_at_unix、native Lease expiry 必须作为原签名 claims 保留在 receipt 中，并与数据库 command receipt 一致。
- Provider applied_at_unix 由实际执行 Provider 状态转换的一侧生成，不能接受 Coordinator 在 confirm 请求中注入的时间。
- applied time 必须在 command 已签发与 command expiry 的允许窗口中；具体最大正/负偏差必须作为协议常量写入代码和测试，不能由调用方逐请求放宽。
- Receipt 的时间声明只证明 Provider 签署的时间事实，不证明系统时钟准确；生产部署仍需时钟同步/监控和合理的漂移假设。
- Provider 状态、command receipt、receipt claims 和可查询 receipt 的持久化必须共享明确的事务边界。签名服务暂不可用时，不得把 unsigned receipt 当作已确认提交证据。
- Floor revision 与 Provider receipt applied_at 是不同维度：前者用于 authority CAS，后者用于 Provider 回执 chronology，不能互相替代。

## 9. 未知结果、重启与 Restore

### 9.1 Provider commit 后响应丢失

1. Coordinator 保留原 Floor operation ID、command digest 和 PENDING reservation。
2. Coordinator 按相同 command_sha256 查询 Provider receipt API。
3. 若返回 signed receipt，重新验签并确认相同 operation/revision。
4. 若明确 NOT_FOUND / NOT_COMMITTED，按照同一命令 identity 的恢复协议决定原命令是否可以重试；不得提前分配下一代。
5. Provider 返回 RECEIPT_SIGNING_PENDING 或查询超时，外部 Floor 仍保持 PENDING/RECOVERY_REQUIRED；不得把摘要猜测为成功。

### 9.2 Restore

- 这套 receipt evidence 是 Grant-aware Restore 的必要输入之一，但不是充分条件。
- Restore 还必须从独立外部 authority 读取线性一致 floor，核对 Provider generation/Leader epoch floor、pending operation、receipt chain 和 trusted minimum revision。
- Restore 目标数据库在历史 Grant scope 全部对账并完成新的 Provider FENCE receipt 前保持不可写。
- 任何缺失/撤销/验签失败的 receipt、回执链不完整、revision 回退、未知 Provider 结果或外部 authority 不可达，都应中止 Restore。
- 当前通用 Restore 对含任意 Provider Grant scope 或 command history 的备份继续 fail-closed；不能因新增 receipt 设计稿或本地签名测试而解除门禁。

## 10. 验收测试矩阵

实现轮次至少覆盖：

1. 合法 FENCE receipt 与合法 ACTIVATE receipt 完整推进外部 Floor。
2. receipt claims 单字段篡改、signature 字节篡改、非规范 JSON、重复 JSON key、未知字段和错误 envelope format 拒绝。
3. 错 Provider、tenant、scope、action、Grant ID、generation、command digest、result state 拒绝。
4. namespace、Leader ID/epoch、native Lease ID/expiry 与签名 Coordinator command 不一致时拒绝。
5. Provider public key 未注册、key fingerprint 错误、错误 Provider key、key 不在有效期、REVOKED key 生效时间之后的回执拒绝。
6. RETIRING key 的有效历史 receipt 按既定时间窗验证；轮换不改变已确认 digest。
7. ACTIVATE receipt 引用错误或不存在的 FENCE command digest 时拒绝。
8. Provider commit 成功但响应丢失：按原 command digest 查询同一 receipt，重复确认不推进 generation。
9. RECEIPT_SIGNING_PENDING、签名服务故障、Provider 查询不可达和外部 Floor 不可达时均 fail-closed。
10. 相同 receipt 的幂等重放成功；同一 operation 的不同 receipt 替换失败。
11. 跨 Provider/tenant/scope 和不同 operation 的 receipt 重放失败。
12. 所有验签/绑定失败后 scope state、generation floor、scope revision 与 authority revision 不变，或进入明确的 RECOVERY_REQUIRED 状态；不得出现部分成功。

## 11. 实施顺序建议

1. 先实现纯协议模块：receipt claims schema、canonical JSON、domain-separated Ed25519 signer/verifier、trusted key data model。
2. 再为本地 Provider SQLite 参考实现增加 durable receipt claims/envelope，确保与 FENCE/ACTIVATE 状态转换同事务提交；补充精确 command digest 查询 API。
3. 再在独立 Floor adapter 中增加 Provider receipt trust registry 与 Verified Evidence 确认门禁；默认拒绝裸 digest 确认。
4. 添加故障注入、签名 key rotation/revocation、响应丢失、receipt replacement 与数据库备份回滚前提测试。
5. 只有本地参考测试和 Knowledge Quality CI 通过后，才进入真实 Provider API/密钥托管方案评估；生产接入需单独架构评审和授权。

## 12. 未解决问题与生产接入前提

- Provider receipt private key 的生成、保护、备份/恢复、轮换和灾备由谁负责；是否使用 KMS/HSM 或硬件安全模块。
- Provider 集群多实例是否共享逻辑 receipt signing identity，还是各自签署并由 registry 记录实例身份；同一 logical provider 的 failover 如何验证。
- Provider 的 receipt signing key 是否可在同一写事务中调用；外部 HSM 调用超时后如何持久化待签名证据而不阻断安全恢复。
- Trust registry 如何通过独立管理平面进行配置发布、审批、审计和 revision checkpoint；如何防止 trust registry 自身回滚。
- Provider native FENCE receipt 是否能覆盖所有被保护的写入口，包括 object PUT、multipart begin/part/complete、delete/overwrite、metadata、ACL、lifecycle 和后台异步写。
- 真实对象存储若不支持事务内条件写或不可变 receipt 记录，是否有等价的 Provider 原子机制。单纯在应用层签名一个“已完成”文本不足以作为 fencing 证明。
- Provider restore/灾备切换后如何证明旧实例不能继续对外写；Receipt signature 不替代 Provider fencing token/epoch floor enforcement。

## 13. 明确结论

1. 当前裸 provider_receipt_digest API 不具备回执来源认证能力，不可作为生产 Grant-aware Restore 或生产 FENCE/ACTIVATE 的完整对账证据。
2. 推荐使用独立 Provider Ed25519 receipt key 对规范化回执签名，并将签名 claims 与 Provider grant state/command receipt 的持久化提交绑定。
3. 外部 Floor 必须验签并逐字段匹配当前 reservation 后，才能确认 FENCE/ACTIVATE；回执摘要必须由验证后的 canonical envelope 重算。
4. Provider receipt authenticity、external Floor consistency 和 Provider mutation atomicity 是三个不同保证，必须分别验证，不能互相代替。
5. 本设计不会解除现有 Restore 门禁，不代表生产 authority/Provider/KMS/HSM/etcd 已接入。
