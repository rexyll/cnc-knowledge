# Provider Grant 外部单调 Floor 与 Restore 对账设计

> CH17 / 第九十一轮设计任务（2026-11-28）
>
> 状态：DESIGN_IN_PROGRESS。本文定义下一阶段的外部协调权威与恢复协议；不代表外部 floor adapter 已实现，也不授予生产 Restore 权限。

## 1. 背景与当前 fail-closed 边界

第九十轮已经提供 Provider SQLite 本地 Grant 状态、FENCE/ACTIVATE 签名命令、命令回执及本地 mutation gate。FENCE 与对象/multipart mutation 在同一个 Provider SQLite `BEGIN IMMEDIATE` 写事务域串行化。

但 Provider Grant generation、Leader epoch floor 和命令回执目前都位于同一个 Provider SQLite 文件中。常规备份只能证明该备份内部的回执链完整，不能证明备份就是最新版本。若在 Grant 已经推进后恢复一个较旧备份，SQLite 内的 generation、FENCE receipt 和当前 Grant 可能全部回滚。

现阶段 `restore_to_new_database()` 已采用保护性策略：只要备份包含任意 Provider Grant scope 或命令历史，便拒绝通用 Restore。该拒绝是预期安全行为，不是临时测试问题。它不能被通过传入任意 reconciliation string 绕过。

## 2. 安全目标

恢复协议必须证明以下事项：

1. 对每个 `(provider_id, tenant_id, fencing_scope)`，Provider Grant generation floor 不因 SQLite 文件复制、旧备份恢复、主机重装或本地文件回滚而降低。
2. Coordinator Leader epoch floor 不因 Provider Restore 而降低；恢复后必须拒绝旧 Leader 或旧 native Lease 的命令。
3. FENCE/ACTIVATE 的准备中、已提交、响应丢失和恢复中状态均有独立、持久、可查询的 operation identity / command digest。
4. Provider 不可达、外部 floor authority 不可达、floor 证据缺失或命令结果未知时，恢复出的 Provider 保持不可写。
5. 不允许仅凭调用方提供的数字、文本 reconciliation reference、本地 wall clock 或旧备份内部字段宣称 floor 已对账。

## 3. 外部权威边界

新增独立的 `ProviderGrantFloorAuthority` 存储端口。该权威不得与被恢复的 Provider SQLite 文件共享备份、文件系统快照或同一回滚域。

推荐在现有 Unified schema-v2 Coordinator authority 的强一致存储路径中增加 Provider scope floor 子状态，由同一 etcd transaction/compare revision 管理；如果使用单独服务，则必须提供等价的线性一致 CAS/Txn 与不可回滚持久性证据。当前只定义端口与事务契约，不预先认定某个未验证的实现已经满足要求。

按 `(provider_id, tenant_id, fencing_scope)` 持久化：

- `provider_generation_floor`：单调递增的已分配 Grant generation；
- `coordinator_epoch_floor`：该 scope 已接受的最高 Leader epoch；
- `coordinator_namespace`、`leader_id`、`native_lease_id` 与 Lease expiry；
- `state`：`IDLE`、`FENCE_PENDING`、`FENCED`、`ACTIVATE_PENDING`、`ACTIVE`、`RECOVERY_REQUIRED`；
- `pending_operation_id`、`command_digest`、`provider_receipt_digest`；
- `last_fence_receipt_digest`、`last_activation_receipt_digest`、外部存储 revision；
- 更新时间和审计关联标识。

外部 floor 是单调授权/恢复账本，不替代 Provider 对每一笔实际写入在本地事务内校验 ACTIVE Grant 的要求。

## 4. FENCE / ACTIVATE 的双边提交协议

### 4.1 FENCE

1. Coordinator 通过线性一致读取验证当前 Leader ID/epoch、native Lease attachment 与 Lease 有效性。
2. Coordinator 在外部 authority 单个 CAS/Txn 中预留下一个 `provider_generation_floor`，推进 `coordinator_epoch_floor`，并写入 `FENCE_PENDING`、operation ID 和完整签名 command digest。
3. Coordinator 向 Provider 发送该精确 FENCE envelope。
4. Provider 在本地 SQLite 事务中推进 FENCED 状态并保存 command receipt。
5. Coordinator 若收到成功响应，或通过 Provider 的精确 digest status lookup 确认已经提交，则在外部 authority 中写入回执摘要并转为 `FENCED`。
6. 若 Provider 不可达或结果未知，外部状态保留 `FENCE_PENDING`；不得签发 ACTIVATE，也不得把该 scope 标记为 ACTIVE。

### 4.2 ACTIVATE

1. Coordinator 确认外部状态为 `FENCED`，且其 FENCE receipt digest 与 Provider 持久回执匹配。
2. Coordinator 在外部 authority 中预留下一 generation，写入 `ACTIVATE_PENDING` 和精确 ACTIVATE command digest。
3. Provider 校验 ACTIVATE 引用当前已持久化 FENCE receipt，且 Leader/Lease/grant identity 完全匹配；在本地事务中创建 ACTIVE Grant。
4. Coordinator 根据 Provider receipt 或精确 digest lookup 确认提交后，外部 authority 更新 `ACTIVE` 及最新 receipt digest。
5. ACTIVATE 结果未知时不能生成新的 grant ID 或 generation 猜测重试；只能查询、重放完全相同 envelope，或进入人工恢复审查。

外部预留与 Provider commit 仍然是两个系统，不应宣称跨系统一个事务。此协议的目标是让不确定结果有持久 intent 和可恢复 identity，并让 Provider FENCE 仍然是 mutation 数据面的撤销线性化点。

## 5. Restore 对账算法

专用 Grant-aware Restore 必须与当前通用 Restore 分离，不能增加一个布尔 `force` 参数绕过限制。

1. 验证备份 SQLite integrity、schema、trusted key registry、完整 FENCE/ACTIVATE receipt chain。
2. 对备份中每个 Grant scope 向外部 floor authority 进行线性一致读取，收集 generation floor、Leader epoch floor、当前状态、pending operation 和最近 receipt digest。
3. 任一 scope 无法从外部 authority 得到可信快照时，整个 Restore 中止，不生成可写目标库。
4. 比较备份中的 generation、Leader epoch、command digest 与外部 floor：
   - 若完全一致且无 pending operation，才可继续进入受控恢复阶段；
   - 若外部 floor 高于备份、receipt 不匹配或存在 pending operation，不可恢复备份里的 ACTIVE 状态；
   - 未知或冲突结果进入 `RECOVERY_REQUIRED`，需要当前有效 Coordinator Leader 和新的 FENCE 屏障。
5. 在目标 Provider 数据库中先保持 Grant mutation gate 关闭；恢复/协调过程必须持久化外部 floor 对应的恢复状态和 receipt。不能只把旧备份里的 `provider_scope_grants` 表复制回来就声明完成。
6. 只有新的 FENCE receipt 已被 Provider 和外部 authority 双方确认后，才可允许 ACTIVATE。
7. 最后重新运行 backup/schema/receipt-chain 校验，并生成包含外部 authority revision、scope count、floor digest、pending 状态和 Provider receipt digest 的恢复报告。Restore 仍只准备新数据库；Cutover 是独立审批。

## 6. Pending / Unknown 的恢复规则

| 外部 authority 状态 | Provider 精确 receipt | 处理 |
|---|---|---|
| `FENCE_PENDING` | 存在且匹配 | 回写外部 FENCE receipt，转 `FENCED` |
| `FENCE_PENDING` | 不存在 | 仅可按原 envelope digest 重试；命令已过期时进入 `RECOVERY_REQUIRED` |
| `ACTIVATE_PENDING` | 存在且匹配 | 回写外部 ACTIVATE receipt，转 `ACTIVE` |
| `ACTIVATE_PENDING` | 不存在 | 仅可按原 envelope digest重试；Lease/命令无效时保持不可写并进入恢复审查 |
| 外部 floor 高于备份 | 备份没有对应 receipt | 不采用备份 ACTIVE 状态；执行新的、更高epoch FENCE恢复 |
| 外部 authority 不可达 | 任意 | Restore 中止，Provider 不可写 |

不能把“Provider receipt 不存在”理解为“Provider commit 肯定没有发生”；必须区分不可达、读失败和线性一致查询确实未找到。

## 7. 必需测试矩阵

1. 正常 FENCE/ACTIVATE 双边推进，验证 generation floor 与 receipt digest 单调递增。
2. Provider FENCE 已提交但响应丢失，Coordinator 重启后通过精确 digest lookup 恢复，不重复分配 generation。
3. 外部预留后 Provider 未提交，重试原 envelope；过期后转 RECOVERY_REQUIRED。
4. Restore 使用早于外部 floor 的 Provider 备份，必须拒绝恢复旧 ACTIVE Grant。
5. Restore 期间外部 floor authority 不可达或 revision 不可验证，必须中止。
6. 外部 FENCE_PENDING / ACTIVATE_PENDING 与 Provider 备份状态不一致时，不得激活。
7. 恢复后的旧 Leader epoch、旧 native Lease、旧 Grant ID/generation proof 全部拒绝。
8. 同一个 Provider SQLite 备份换 Provider ID、tenant 或 scope 时拒绝。
9. 外部 floor authority 自身出现 snapshot rollback、重复 operation ID、revision regression 时拒绝继续。
10. 真实 etcd 三节点故障、Coordinator 进程重启与 Provider 独立重启组合测试。

## 8. 当前状态与明确限制

- Provider SQLite 本地 Grant 状态机已在第九十六轮升级至 schema v7；命令回执与 Provider 独立 signed Receipt 分列持久化，FENCE/ACTIVATE同事务生成回执，按 command digest 精确查询，备份校验完整 Provider Receipt 签名链。旧 schema v5 历史回执缺少原始envelope，迁移后仍为不可验证状态。
- 通用 Restore 已明确拒绝含有 Grant 历史的备份；此门禁不得移除，直到本设计的独立 floor authority 与专用 Restore 流程实现并通过测试。
- 本文不实现 ProviderGrantFloorAuthority adapter，不修改 Unified schema-v2 生产 authority，不连接真实 etcd/Provider/KMS/HSM，不修改 IAM/RBAC，不执行生产迁移或 Cutover。
- FENCE/ACTIVATE command 与 ACTIVE Grant 的有效期上限在本地参考实现中为300秒，且不能晚于Coordinator native Lease expiry。提前撤销Lease而Provider未及时收到FENCE时，旧Grant仍可能在剩余有效期内被接受；该残余窗口有上限但非零，不能宣称瞬时撤销。
- 当前无真实多主机、远程对象存储或跨系统联合故障证据；MIG-05 继续 IN_PROGRESS，MIG-06 和 MIG-07 不因此解锁。


## 9. 第九十二轮：独立 Floor 本地参考适配器与状态机

新增 scripts/spare_parts_provider_grant_floor.py，实现 ProviderGrantFloorAuthority 端口基类及 SQLiteProviderGrantFloorAuthority 独立文件参考适配器。该文件必须与 Provider SQLite 数据库及其备份/恢复域分离；它只模拟外部 authority 的事务契约，不是 etcd、quorum 或生产级防回滚存储。

### 9.1 持久化记录

- provider_grant_floor_scopes：按 (provider_id, tenant_id, scope) 保存 generation floor、Leader epoch floor、Coordinator namespace/Leader/native Lease 绑定、当前 Grant ID、pending operation、FENCE/ACTIVATE command digest、Provider receipt digest及scope revision。
- provider_grant_floor_operations：按全局唯一 operation ID 保存精确作用域、动作、Grant ID、generation、命令摘要、FENCE引用、Coordinator/Lease身份、预留revision、Provider回执摘要及PENDING/CONFIRMED状态。
- provider_grant_floor_meta：记录本地schema版本和本地authority revision。该revision只用于本地参考审计，不构成独立防回滚锚点。

### 9.2 状态推进与并发语义

1. FENCE reserve通过 BEGIN IMMEDIATE 对scope revision执行CAS，分配下一个generation并进入 FENCE_PENDING；pending未确认或scope已FENCED时不允许分配下一操作。
2. 新Leader/Lease身份必须使用更高Leader epoch；同一epoch不能改变namespace、Leader ID或native Lease ID。scope namespace一经建立不可改变；同epoch同Lease的expiry不能回退。
3. Provider确认FENCE后，Coordinator必须先持有可认证的Provider精确回执，再将其摘要写入外部状态并推进为 FENCED。
4. ACTIVATE reserve只接受 FENCED scope，必须匹配当前Grant、同一Coordinator/Leader/native Lease身份及最近一次已确认FENCE command digest；它分配下一个generation并进入 ACTIVATE_PENDING。
5. Provider精确ACTIVATE回执被确认后才进入 ACTIVE。相同receipt的确认重放幂等；同一operation ID替换命令或替换已确认receipt均拒绝。
6. Coordinator结果未知时可通过 operation_status(operation_id) 在进程重启后读取原操作状态；必须沿用原operation ID和command digest，不可猜测新generation。

外部状态进入 FENCE_PENDING 仅表示Coordinator已预留代次和命令身份，**不代表旧Provider Grant已经撤销**；在Provider实际FENCE命令提交前，旧ACTIVE Grant仍可能在其剩余有效期内通过Provider mutation gate（当前本地参考上限为300秒）。只有Provider FENCE与mutation共享事务域的提交才是Provider数据面的撤销线性化点，不得把外部reserve描述为fencing。

Floor状态先预留、Provider本地事务再提交、最后外部确认，是两个系统间的双边协议而不是分布式原子事务。这里不通过跨机器 issued_at/applied_at 比较决定状态先后；协议顺序由外部revision、operation identity、精确命令摘要和Provider回执摘要表示。Lease expiry仍作为签名/Leader校验材料保存，但当前时刻的Leader/Lease有效性必须由真实Coordinator authority单独线性一致验证。

### 9.3 新增测试与当前限制

新增 tests/test_spare_parts_provider_grant_floor.py，包含20个独立测试方法定义，覆盖正常FENCE→ACTIVATE、generation递增、CAS竞争、相同operation重试、operation ID冲突、pending阻断、精确Provider receipt确认、响应未知后的重启查询、Leader epoch/namespace/Lease expiry单调性、Provider/tenant/scope隔离、trusted minimum revision和文件权限。

**必须保留的限制：**

- 当前SQLite floor只能证明同机单文件事务和CAS参考语义；它不是etcd linearizable KV/Txn，不提供Raft quorum、跨主机线性一致读写或远程故障恢复。
- SQLite文件自身无法识别自己被恢复到旧快照。minimum_revision 只有在调用方持有来自该数据库备份域之外的可信revision checkpoint时，才可检测低于该checkpoint的回滚。
- 适配器只保存Provider receipt digest；调用者仍须通过认证的Provider状态接口核实回执的真实性、Provider身份、scope和command digest，不能把未认证字符串直接确认成有效回执。
- 当前没有连接该适配器与 SQLiteFencedObjectStorageProvider.apply_provider_grant_command()、Coordinator命令签发或Unified schema-v2 authority；没有Grant-aware Restore，也没有解除通用Restore对Grant历史备份的拒绝。
- 本轮测试方法数量只是源代码清单，尚不代表测试已执行或通过。Round 90、Round 92均不得因此标记DONE；生产 Unified schema-v2仍为唯一authority，MIG-04/MIG-05继续IN_PROGRESS，MIG-06 TODO，MIG-07 BLOCKED。

## 10. 第九十三轮：Coordinator Namespace 严格隔离

第九十二轮 SQLite 参考 Floor adapter 不再接受任意绝对路径作为 Coordinator namespace，只接受唯一形状：

`/cnc/migration/isolated/{single-id}/`

其中 `single-id` 是单一标识段，规则与代码中的 `[A-Za-z0-9][A-Za-z0-9._:-]{0,127}` 一致：首字符必须为 ASCII 字母或数字，后续最多127个字符且只允许字母、数字、点、下划线、冒号和连字符。路径必须有且只有四个非空段，必须以斜线开头和结尾；不接受额外层级、重复分隔符、点段、路径穿越、百分号编码、反斜线或空白字符。

校验发生在写事务/修订号推进之前。非法 namespace 必须直接 fail-closed，不创建 scope 记录，不分配 generation，不增加 scope revision 或 authority revision。一个 scope 首次绑定隔离 namespace 后仍不可更换；更换为另一个格式合法的 isolated ID 也必须被既有不可变性门禁拒绝。

这是一项本地合成迁移参考模型的输入限制，不是通用 Coordinator namespace 解析器，也不是生产 Unified schema-v2 namespace 的迁移或授权变更。它不连接真实 etcd 或 Provider；生产 authority 仍须通过独立的权限、租约和 namespace 策略验证。

新增测试覆盖合法隔离 namespace、Unified/生产前缀、隔离根路径、额外层级、空段/点段、百分号编码及反斜线。拒绝路径后同时核对 scope 仍为 IDLE，scope revision 与 authority revision 均未变化。测试还确认在隔离前缀内更换单一 ID 仍违反既有 scope namespace 不可变约束。

### 10.1 与本轮共同完成的 Provider 回执校验修复

主分支 Quality Run 同时暴露并修复了第九十轮 Provider 参考实现中的几处验收缺陷：

- ACTIVATE mutation gate 查询现在显式读取 ACTIVATE receipt 的 `command_sha256`，使后续持久化签名验证使用真实回执摘要，不再访问缺失的查询列。
- 命令验证本身允许签发时间最多领先 Provider 当前时间5秒；运行时回执验证和备份验证现统一允许 Provider 应用时间相对签发时间最多早5秒，但仍要求应用时间不得晚于签名命令到期时间。超出该偏差范围仍 fail-closed。
- 测试命令的默认到期时间不得超过 Coordinator native Lease expiry。
- 备份断链测试改为删除被 ACTIVATE 引用的 FENCE 回执，以验证确切的 FENCE/ACTIVATE 缺失链拒绝，而不是通过改写已签名字段提前触发通用签名声明不匹配错误。
- Floor 单元测试的 namespace 不可变场景改用另一个语法合法的 isolated ID；pending FENCE 阶段发起 ACTIVATE 的断言明确验证 pending operation 阻断。

这些变化修正了本地参考实现/测试的内部一致性，不构成真实 Provider、etcd 或跨系统事务验收。

### 10.2 验证记录

- GitHub Actions Knowledge Quality Run 46152883043：两个必需 Job 均成功。
- 全库 unittest：707项运行，40项按环境条件跳过，其余667项通过。
- CH12 numerical resource tests：143项通过。
- repository knowledge lint：0 errors、5 warnings；附加结构/数据检查结果为0 errors。
- 测试运行链接：[Knowledge Quality Run 46152883043](https://github.com/rexyll/cnc-knowledge/actions/runs/46152883043)。

本地 SQLite Floor 依然不能识别自身数据库被恢复到旧快照；`minimum_revision` 只有在调用者持有该数据库备份域外的可信 revision checkpoint 时才有回滚检测意义。Provider 回执仍仅以摘要存入 Floor adapter，adapter 本身尚未验证回执签名或来源。该缺口列入下一轮设计任务。


## 11. 第九十七轮：Floor Coordinator Signed Command 来源认证（schema v5）

第九十七轮将 Coordinator command authentication 加入外部 Floor 本地参考模型。此前 Round95/96已能验证 Provider 独立签名 Receipt，但 Floor 的 reservation仍接受调用方直接提供command digest与claims，因此Provider Receipt虽可证明Provider签署了某组claim，却不能证明Floor预留的claim本身来自受信Coordinator。

### 11.1 Coordinator trust registry

Floor schema从v4升级至v5，新增 `provider_grant_floor_coordinator_keys` 表，以 (`issuer_id`, `key_id`) 为主键保存：

- Ed25519 public key 的 Base64副本及SHA-256 fingerprint；
- ACTIVE / RETIRING / REVOKED；
- not_before / not_after；
- retiring_effective_at / revocation_effective_at / revocation_reason；
- trust_revision与created_at。

新增本地数据库owner管理API `admin_register_coordinator_command_key()` 与 `admin_set_coordinator_command_key_status()`。Coordinator command envelope中携带的任何公钥都不会自动加入trust registry。撤销和退役状态只能向前推进，不能重新激活；轮换通过注册新key ID/public key完成。

当前策略对新reservation只接受ACTIVE且当前时间与command签发时间均符合key有效期的key；RETIRING/REVOKED key不能创建新operation。此前已经成功认证并持久化的operation会保存signer key ID、fingerprint和trust revision，作为该reservation当时的认证审计材料；exact operation replay只返回既有operation，不重新分配generation或推进revision。

### 11.2 Signed command reservation API

Floor新增：

- `reserve_fence_from_command(operation_id, key, command_envelope, expected_revision)`
- `reserve_activate_from_command(operation_id, key, command_envelope, expected_revision)`

其中调用方必须传入预期目标 `ProviderGrantScopeKey`。Floor不会仅从命令自报的Provider/Tenant/scope来决定写入哪个scope；它将已验签claims与调用方选择的目标key逐字段比较，防止一个在Coordinator trust registry中有效的命令被调用方用来申请另一个Provider/Tenant/scope的Floor状态。

新API接受Coordinator原始signed envelope（object、UTF-8 bytes或JSON text），JSON text parser拒绝重复object key和非有限数值。Floor使用Coordinator命令签名模块相同的canonical JSON规则重算完整envelope SHA-256，再从issuer/key ID查询独立Coordinator key registry并执行Ed25519验签。验证内容包括：

- issuer、key ID、key fingerprint、algorithm、status及有效期；
- Provider ID、Tenant ID、scope与明确传入的目标ProviderGrantScopeKey；
- FENCE/ACTIVATE action、Grant ID、generation；
- Coordinator namespace、Leader ID/epoch、native Lease ID与Lease expiry；
- command issued_at/expires_at、native Lease上限及精确FENCE command digest；
- canonical signed-envelope digest与reservation command digest必须一致。

ACTIVATE除了验证签名和claims，还必须匹配Floor当前FENCED scope的Grant、Leader/native Lease identity及最近一次已确认FENCE command digest。命令中的generation必须恰好等于Floor状态机计算的下一generation，调用方不能选择或跳过代次。

### 11.3 同事务验证与Strict migration

Coordinator key lookup、签名验证、claims binding、当前scope状态/CAS和pending operation创建均在同一个SQLite `BEGIN IMMEDIATE` 事务内完成。所有校验成功之前，不会创建scope记录、不占用operation ID、不推进scope revision或authority revision。

Floor metadata增加 `coordinator_command_auth_required`：
- 新Floor默认strict=1；
- v1–v4旧库依序迁移至v5，并默认strict=1；
- 只有显式创建的本地兼容/测试库才能用 `allow_legacy_unsigned_reservations=True` 开启legacy API；
- 已经strict的Floor数据库不能被重新打开为legacy模式；
- legacy raw `reserve_fence()` / `reserve_activate()` 在strict模式下拒绝调用方直接提交digest/claims。

Operation表新增Coordinator signer key ID、key fingerprint、trust revision字段。迁移历史操作保留原记录，但不补造Coordinator签名来源。strict mode下，迁移进来的旧PENDING operation如果缺少这些Coordinator认证元数据，`confirm_provider_receipt()` 不能只凭一个Provider签名Receipt将其追认为已认证reservation；已经CONFIRMED的历史operation只保留原有历史结果，不自动升级来源等级。

### 11.4 测试与验收

Floor测试使用独立合成Coordinator Ed25519 key，覆盖：

- 正常FENCE/ACTIVATE signed-envelope reservation与Provider Receipt确认；
- 命令签名篡改、未知issuer/key、wrong key/fingerprint和重复JSON key；
- Provider/Tenant/scope错配，generation不等于Floor下一代；
- native Lease/command validity边界及FENCE digest错误；
- ACTIVE、RETIRING、REVOKED与key rotation；
- exact operation replay与signer audit metadata；
- strict默认拒绝裸digest/claims、strict不能降级；
- v1→v5迁移、旧历史不补造签名来源、旧PENDING operation不能通过新确认路径；
- 失败时scope revision与authority revision不推进；
- Provider真实本地FENCE/ACTIVATE签名回执与Floor双信任域端到端集成。

[Knowledge Quality Run 46159157703](https://github.com/rexyll/cnc-knowledge/actions/runs/46159157703) 在代码测试提交上两个必需Job均success：全库757项测试运行、40项环境跳过；CH12数值资源143项通过；knowledge lint 0 errors / 5 warnings；结构/数据检查0 errors。最终完整文档同步仍以对应文档提交的CI为准。

### 11.5 保留的生产边界

此实现仍是单机SQLite参考模型，不是etcd linearizable KV/Txn、Raft quorum、多主机authority或生产Coordinator trust plane。Coordinator key registry由本地数据库owner API管理，不含生产审批、多节点安全发布、KMS/HSM或硬件密钥隔离。Floor文件及其trust registry仍不能识别自身旧快照回滚，必须依赖Floor备份域外可信checkpoint。

没有连接真实Coordinator/etcd/Provider/object storage/KMS/HSM/IAM/RBAC，没有修改Unified schema-v2 production authority。Provider receipt authentication、Coordinator command source authentication和跨系统mutation atomicity仍是不同保证，当前参考代码不把其中任何一个夸大为生产分布式原子授权。Grant-aware Restore仍未实现，所有包含Provider Grant历史的通用Restore继续fail-closed；不执行候选导入、Restore、应用激活或Cutover。

