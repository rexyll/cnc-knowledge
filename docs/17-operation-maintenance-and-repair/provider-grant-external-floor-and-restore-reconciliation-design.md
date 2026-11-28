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

- 当前 Provider SQLite schema v6 本地 Grant 状态机已实现；命令回执持久化规范化完整签名envelope与签名公钥材料，备份校验重算digest并重新验证Ed25519签名。schema v5历史回执缺少原始envelope，迁移后仍为不可验证状态。
- 通用 Restore 已明确拒绝含有 Grant 历史的备份；此门禁不得移除，直到本设计的独立 floor authority 与专用 Restore 流程实现并通过测试。
- 本文不实现 ProviderGrantFloorAuthority adapter，不修改 Unified schema-v2 生产 authority，不连接真实 etcd/Provider/KMS/HSM，不修改 IAM/RBAC，不执行生产迁移或 Cutover。
- FENCE/ACTIVATE command 与 ACTIVE Grant 的有效期上限在本地参考实现中为300秒，且不能晚于Coordinator native Lease expiry。提前撤销Lease而Provider未及时收到FENCE时，旧Grant仍可能在剩余有效期内被接受；该残余窗口有上限但非零，不能宣称瞬时撤销。
- 当前无真实多主机、远程对象存储或跨系统联合故障证据；MIG-05 继续 IN_PROGRESS，MIG-06 和 MIG-07 不因此解锁。
