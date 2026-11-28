# Provider Freeze 在线 Coordinator Leader / Native Lease 校验

## 1. 目的与范围

第八十七轮将 Provider Freeze 命令签名绑定到 Coordinator namespace、Leader ID、epoch、native Lease ID 与声明到期时间，但签名只证明声明来源，不能证明签名时或验证时 etcd Lease 仍然有效。本轮新增 Provider 侧在线只读校验入口，降低提前撤销旧 Lease 后旧 Leader 命令仍可被接受的风险。

本轮是参考实现和契约测试，不是生产接入证明。没有配置真实 etcd client、真实 Provider 或 KMS/HSM，也没有修改生产授权状态。

## 2. 实现

新增 `scripts/spare_parts_provider_live_leader_status.py`：

- `EtcdCoordinatorLeaderStatusChecker` 接受现有 `CoordinatorAuthorityStore` / etcd adapter 的只读接口。
- 每次验证只调用一次 `linearizable_range(namespace_prefix, range_end=...)`，确保 Scheduler aggregate 与 Coordinator Leader TTL key 来自同一个线性一致 Range revision。
- 必须同时存在 `scheduler/state` 与 `coordinator/leader`；aggregate 中的 `coordinator.leader` 必须与 TTL key JSON 记录一致。
- 比较签名命令中的 Leader ID、epoch、native Lease ID 和 Lease expiry；同时核对 etcd KV 元数据中的 `lease_id` 与签名 Lease ID 完全一致。
- Leader 声明到期时间必须与当前 aggregate 记录一致且晚于本次校验时间。缺少 key、Lease 附着不一致、身份漂移、过期或状态格式错误均返回不活动。
- 线性一致 Range 失败抛出 `CoordinatorLeaderStatusUnavailableError`，由 Provider 以 fail-closed 方式拒绝新命令。

Provider `SQLiteFencedObjectStorageProvider` 增加可选配置：

- `leader_status_checker`：实现 `is_leader_active(claims, now_unix=...)` 的检查器。
- `require_online_leader_status=True`：强制检查器存在；应用新的 FREEZE/UNFREEZE 命令前必须通过在线检查。未启用时维持兼容行为，不得宣称已启用在线验证。

历史命令回执查询仍先于在线检查。已提交命令的精确重放只返回 `ALREADY_APPLIED` 和历史结果，不再次执行状态转换，也不因 Leader 已切换而使回执不可查询。

## 3. 为什么使用 Leader TTL Key，而不是把本地计时器当作 Lease 状态

Coordinator 把 `coordinator/leader` KV key 附着到 etcd 原生 Lease。线性一致 Range 返回的 KV 元数据包含 Lease ID；Lease 被撤销或过期清理后，附着 key 将不再出现在 Range 结果中。因此本轮以“同一线性一致快照中 key 存在 + Lease attachment 匹配 + aggregate 与 key 一致 + expires_at 未过期”作为在线状态条件。

这不是独立的 `LeaseTimeToLive` RPC。TTL RPC 的返回不能代替 Leader key 与 aggregate 的同一 revision 校验；本实现也不把客户端本地定时器或签名声明当作 Lease 仍然存在的证据。

## 4. 关键限制：跨系统 TOCTOU 仍未消除

在线检查发生在 Provider SQLite `BEGIN IMMEDIATE` 写事务内，但 etcd 与 Provider SQLite 没有共同的原子事务。可能出现：

1. Provider 对 etcd 做线性一致 Range，确认 Leader key/Lease 有效；
2. Coordinator 随即撤销 Lease，或新 Leader 建立更高 epoch；
3. Provider 随后提交本地 SQLite Freeze 状态和命令回执。

因此，本轮可以拒绝“在线检查之前已经撤销/过期/切换”的旧 Leader 命令，也能在 etcd 不可用时 fail closed；但无法保证 Lease 在 Provider SQLite commit 的瞬间仍有效。Provider 本地 BEGIN IMMEDIATE 锁只能串行化本地 Provider 写入，不能锁住 etcd 的 Leader 状态。

**禁止将本轮描述为跨系统原子 fencing、实时 TTL 保证或生产 stale-Leader 问题彻底解决。** 要消除该窗口，需要进一步设计由 Provider 端参与的可撤销写入授权/屏障协议，使撤销与 Provider mutation 有共同的线性化顺序；单纯把在线 Range 移入 SQLite 事务仍不够。

## 5. 测试与未完成事项

新增 `tests/test_spare_parts_provider_live_leader_status.py`，覆盖：

- 单次线性一致前缀 Range 的有效 Leader；
- Lease 提前撤销后 Leader key 缺失；
- native Lease attachment 不匹配；
- Leader ID、epoch、Lease ID 不匹配；
- aggregate 与 TTL key 内容漂移；
- Lease 到期与 expiry 声明漂移；
- 非规范 namespace；
- etcd 读取失败。

Provider 专项测试增加配置缺失拒绝、在线状态为 false 时拒绝新命令、在线检查异常时 fail closed，以及精确历史命令回执优先于在线检查的行为。

这些测试使用合成 store / fake checker；不证明真实 etcd 集群、网络分区或真实 Provider 的运行行为。下一阶段应先完成跨系统撤销屏障协议设计，再决定是否开展真实三节点 etcd 与 Provider 联合故障演练。

## 6. 安全状态

- 生产 Unified schema-v2 仍是唯一权威；本轮没有读取或写入生产 namespace。
- 没有连接真实 etcd、Provider、KMS/HSM、云对象存储或 IAM/RBAC。
- 没有执行候选数据导入、应用激活、Provider 生产冻结或 cutover。
- ASSET-000092 继续保持 `PROPOSED_NOT_APPROVED / NOT_RUN`。
