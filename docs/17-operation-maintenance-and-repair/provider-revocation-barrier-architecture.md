# Provider 可撤销授权与撤销屏障架构设计

> CH17 / 第八十九轮设计任务（2026-11-28）
>
> 状态：DESIGN_IN_PROGRESS。本文是架构决策与验证计划，不是已实现能力，不构成生产授权或迁移批准。

## 1. 背景与问题定义

第八十八轮已通过一次线性一致 etcd prefix Range，在同一 revision 验证 Scheduler aggregate、Coordinator Leader TTL key、Leader ID/epoch、native Lease ID、KV Lease attachment 和 expiry。该检查能拒绝检查时已经失效的 Leader，但 etcd Range 与 Provider 本地 SQLite commit 没有共同事务。

因此仍存在以下窗口：

1. Provider 读取 etcd，观察到 Leader/Lease 有效；
2. etcd Lease 被撤销、过期或更高 epoch Leader 建立；
3. Provider 在本地事务中提交 Freeze/Unfreeze 控制状态或其他受保护 mutation。

将 Range 移入 SQLite `BEGIN IMMEDIATE` 事务不会改变这一事实：SQLite 锁不能阻止 etcd Lease 在两个系统之间变化。重复读取、缩短超时或增加第二次 Range 只能缩小窗口，不能建立共同线性化点。

## 2. 必须区分的两个问题

- **Coordinator leadership validity：** 某个进程在 etcd 中是否仍是当前 Leader。
- **Provider mutation authorization：** Provider 在其写入提交点是否仍授权该 Leader 执行具体 mutation。

前者不能仅凭一次读取与后者原子绑定。Provider 必须在最终 mutation 的事务边界内执行可撤销授权检查；在线 Coordinator 检查只能作为附加拒绝条件，不能替代 Provider 本地授权状态。

## 3. 架构候选与结论

### A. 单一事务权威

将授权状态与受保护数据写入放在同一个具备事务/CAS语义的权威存储中。授权撤销与业务 mutation 在该存储内竞争同一条线性化顺序。

- 优点：语义最直接，可在同一事务中完成授权检查和 mutation。
- 限制：要求 Provider 的控制状态和实际数据写路径共享事务边界；普通对象存储与独立控制数据库通常不满足。
- 适用：同机 SQLite 参考实现或本身提供条件写/事务控制面的 Provider。

### B. Provider 原生条件写 / fencing

如果远程 Provider 在每个实际写入口支持原子条件写，可把 scope epoch / fencing generation 与对象 mutation 绑定，由 Provider 服务端在提交时拒绝低代次请求。

- 优点：无需把 etcd 事务扩展到对象存储。
- 限制：必须覆盖 PUT、multipart begin/part/complete、删除、复制、批量操作及所有其他 mutation；仅在 API Gateway 前置检查不够。条件检查必须由真正持久化数据的 Provider 执行。
- 适用：提供原生 generation、版本条件或事务性授权钩子的对象存储。

### C. Provider 参与的撤销屏障（推荐作为下一轮参考协议）

把 Provider 自身的授权代次作为 Provider mutation 的最终门禁，并将 Leader handoff 拆成显式屏障：

1. **STOP_ISSUANCE：** Coordinator 停止为旧 epoch 签发新 Provider mutation permit；旧请求仍须经过 Provider 事务内门禁。
2. **FENCE_PROVIDER：** 新 epoch 或独立受信控制主体向 Provider 提交签名 FENCE 命令。Provider 在与所有受保护 mutation 相同的事务边界内，原子推进该 scope 的 Provider epoch floor，并撤销旧 grant。
3. **DURABLE_RECEIPT：** Provider 持久化完整命令 envelope digest、旧/新 epoch、scope、结果及提交时间。超时后只能按原 envelope digest查询；未知结果不得换 generation 猜测。
4. **ACTIVATE_NEW_GRANT：** 只有拿到可验证的 FENCE receipt 后，才可激活新 epoch 的 Provider grant。新 grant 绑定 Coordinator namespace、Leader ID/epoch、native Lease ID、Provider grant generation、scope 和期限。
5. **MUTATION_GATE：** 每个 Provider mutation 在最终提交事务内校验 grant 为 ACTIVE、epoch/generation 精确匹配、grant 未过期、scope 和 operation/idempotency 绑定正确，并执行实际数据写入或条件写。

Provider 的 FENCE 与 mutation 必须在同一 Provider 事务/原生条件写域内串行化。若 mutation 先提交，则它在线性化顺序上先于 FENCE；若 FENCE 先提交，旧 epoch mutation 必须失败。FENCE receipt 是 Provider 侧撤销的提交证明，不是 etcd Lease 的反向证明。

**重要语义：** 对 Provider 写操作而言，撤销屏障在 Provider FENCE 成功提交时线性化，而不是在 etcd Lease 过期的物理瞬间线性化。Coordinator 不得在屏障完成前宣称 Provider 侧 handoff 完成或允许新 epoch 执行业务写入。Provider 不可达时必须阻断新 grant/新 epoch 激活；不能绕过屏障降级为在线 Range 后直接写。

### D. 仅在线 Range 后执行 Provider 写入

不接受为完整解决方案。它仍然存在第 1 节的 TOCTOU 窗口；即使 Range 在线性一致快照中验证 Lease attachment，也不能锁定后续 Provider commit。

## 4. 不能隐瞒的分布式边界

如果业务要求“etcd Lease 一经撤销，任何独立 Provider 在同一瞬间都必须拒绝旧 Leader”，而 etcd 与 Provider 没有共同事务、Provider 原生条件写或同步撤销屏障，则该要求不能由一次或多次在线读取实现。

必须明确选择并记录其中一种语义：

- Provider 原生/共享事务权威直接决定 mutation commit 的授权顺序；或
- Provider FENCE receipt 决定 Provider 侧撤销生效点，Coordinator handoff 必须等待该屏障；或
- 接受明确、有上限且依赖时钟假设的 Provider grant TTL 窗口，并将其标记为残余风险，不能宣称零窗口 fencing。

不能把 etcd TTL、签名命令 expiry、客户端本地计时器或异步 Watch 更新单独当作 Provider mutation 的原子撤销证明。

## 5. Provider grant 数据模型草案

按 `(provider_id, tenant_id, fencing_scope)` 唯一标识：

- `coordinator_namespace`
- `leader_id`
- `leader_epoch`（单调不减）
- `provider_grant_generation`（每次授权/撤销单调递增）
- `grant_id` / `grant_digest`
- `state`：`FENCED`、`ACTIVE`、`EXPIRED`
- `issued_at`、`expires_at`
- `last_command_digest`
- `updated_at`

命令收据必须独立保存历史结果，不能只依赖当前 scope 行。相同完整 envelope 重放只返回历史 receipt；不同 envelope 复用 generation、epoch 回退、同 epoch 更换 Leader/Lease、namespace 漂移或 scope 不匹配均拒绝。

Provider 本地时钟是 TTL 方案的额外信任假设：若采用 expiry，必须设计时钟回拨检测、可信时间来源、重启恢复和最大时钟偏差；不允许默认认为系统 wall clock 可靠。若无法证明这些条件，grant expiry 只能作为额外防护，不能替代显式 FENCE。

## 6. 与现有实现的兼容边界

- 第八十五至八十七轮的 Provider-native freeze scope、command receipt、Leader floor 和审计表可作为本地参考实现基础，但它们当前只覆盖 Freeze/Unfreeze 命令，不等于所有对象/multipart mutation 已绑定 Provider grant。
- 第八十八轮的 `EtcdCoordinatorLeaderStatusChecker` 保留为附加在线校验；它不能作为 Provider grant 的最终提交门禁。
- 现有 `require_atomic_online_attestation_status` 只适用于 attestation checker 与 Provider 共用同一个 SQLite 数据库的本地参考模式；不得将其误用为 etcd 与 SQLite 的跨系统原子事务。
- 生产 Provider 必须逐一证明其真实写 API、multipart生命周期、异步任务、后台复制/删除和管理接口都执行同一 fencing 条件；Gateway 层校验不足以证明数据面受保护。

## 7. 下一轮验证要求

第九十轮实现前，先冻结本设计中的授权语义和状态机；随后至少验证：

1. 旧 epoch mutation 与 FENCE 并发：只能出现“旧 mutation 先提交”或“FENCE 先提交、旧 mutation 被拒绝”两种结果。
2. FENCE 提交后响应丢失：原 envelope digest 查询到唯一历史 receipt，不重复推进 generation。
3. FENCE 未提交且无 receipt：只允许按完全相同 envelope 重试；冲突或未知持续时隔离。
4. 新 grant 在 FENCE receipt 缺失、损坏或与scope/epoch不匹配时不得激活。
5. 旧 grant 在 FENCE 后被重放、旧 epoch 回退、同 epoch identity/Lease mutation 均拒绝。
6. Provider restart / backup / restore 不得回退 epoch floor、grant generation 或 command receipt。
7. 实际对象与 multipart mutation 必须与 FENCE 共用同一事务/原生条件写边界；若做不到，必须标记为不支持强 fencing。
8. Provider 不可达、Coordinator 不可达、时钟回拨和未知事务结果均 fail closed。

## 8. 本轮状态与安全声明

本文仅完成问题分解和候选架构，不代表已实现 Provider grant、FENCE 命令、撤销屏障或生产级强 fencing。尚未连接真实 etcd、Provider、KMS/HSM、对象存储或 IAM/RBAC；未改变生产 authority、未导入候选数据、未激活应用、未执行 cutover。生产 Unified schema-v2 仍为唯一权威，ASSET-000092 仍为 `PROPOSED_NOT_APPROVED / NOT_RUN`。


## 9. 第九十轮本地参考实现映射

第九十轮已开始将本设计映射到同机SQLite Provider：

- 新增独立Ed25519 `FENCE` / `ACTIVATE` command envelope；ACTIVATE必须引用精确FENCE receipt digest。
- Provider新增scope grant状态表和命令receipt表；FENCE推进到FENCED。更换Leader/Lease身份要求epoch严格增加；同epoch仅允许完全相同Leader/Lease身份主动撤销当前ACTIVE grant；ACTIVATE只有在FENCE receipt存在且全部identity绑定一致时才能开启新grant。
- 可选`require_revocable_grant`在初始化时强制要求Provider ID、Ed25519命令信任公钥和在线Coordinator Leader checker；checker返回inactive/异常时拒绝FENCE/ACTIVATE且不推进状态。对象PUT及multipart begin/part/complete在各自Provider写事务中检查Grant ID/generation、ACTIVE状态和expiry，并JOIN当前FENCE receipt确认Provider ID，拒绝跨Provider身份复用。Freeze/Unfreeze与Grant命令不能注入调用方时间；写锁等待和在线Leader查询后均重新校验命令expiry及Key有效时间窗。在线检查仅是命令前置门禁，仍不能原子绑定Provider commit。
- FENCE与mutation使用同一Provider SQLite BEGIN IMMEDIATE事务，形成单机数据库内的可验证串行化边界。
- 命令提交后响应丢失通过原始envelope digest读回receipt，不生成新代次；ACTIVATE签发时间必须不早于FENCE的Provider持久化回执时间，且receipt经backup/restore后仍可查询。

**状态：** 已提交代码与专用测试初版，待必需CI完成后确认。该实现仍不是远程Provider/对象存储、跨主机或生产级证明；FENCE线性化点仍仅是Provider本地数据库提交，不与etcd Lease物理撤销瞬间原子同步。
