# 数控机床备件库存账本备份 Provider 持久化准入协调器与幂等租约

**知识ID：** KNOW-000042  
**章节：** CH17 操作、维护与维修  
**状态：** IN_PROGRESS / SQLite本地文件原型与自动化测试  
**适用范围：** 对KNOW-000039～KNOW-000041的同进程共享协调与故障恢复模型，增加可持久化后端实现和同主机多进程准入测试。

## 1. 实现定位与边界

新增 `SQLiteProviderAdmissionCoordinator`，作为 `ProviderAdmissionCoordinator` 可替换实现之一。它使用本地SQLite数据库文件、WAL日志模式、`synchronous=FULL` 和写事务 `BEGIN IMMEDIATE`，在数据库事务中完成容量读取、等待队列选择、fencing token递增和租约插入。

该实现适用于**同一主机上多个进程共享一个受支持的本地文件系统数据库**。它不是跨主机协调服务，不应把WAL数据库放在NFS/SMB或未经验证的网络文件系统上；没有主备、复制、quorum、跨区域高可用或数据库文件灾难恢复能力。

## 2. 持久化对象与原子准入

数据库保存以下状态：

- `admission_requests`：request_id、lease_id、owner/task/tenant/domain、fencing token、过期时间和ACTIVE/RELEASED/EXPIRED状态；
- `admission_waiters`：等待队列身份、任务优先级、排队时间与排队截止时间；
- `coordinator_meta`：策略哈希、全局单调fencing token序列和诊断计数。

每次准入使用 `BEGIN IMMEDIATE` 串行化写竞争；全局与租户域内活动租约、共享最大等待数、优先级aging/FIFO选择、租约创建和fencing token递增在同一个写事务内完成。策略哈希将数据库与全局并发/租户配额/等待队列参数绑定；同一个数据库被不同策略配置的进程打开时，拒绝启动，避免配置漂移造成过量准入。

当前SQLite后端实现共享并发、租户配额、等待队列和租约，不实现令牌桶QPS限流。原InMemory协调器的共享令牌桶仅为同进程Mock能力，不能自动推定SQLite后端也具备该能力。

## 3. 请求ID幂等与响应丢失恢复

`acquire(request_id=...)` 将request_id作为准入幂等键：

1. 同一request_id、owner/task/tenant/domain一致且原租约仍ACTIVE时，返回原lease_id和原fencing token，不重复占额；
2. 相同request_id绑定不同身份时，抛 `ProviderAdmissionIdempotencyConflictError`；
3. request_id对应租约已RELEASED或EXPIRED时，抛 `ProviderAdmissionRequestFinalizedError`，不允许把已终结的业务请求ID复用为新租约；
4. 若租约已提交而响应丢失，`ProviderCoordinatorUnavailableError`携带 `request_id` 和 `reservation_outcome_unknown=True`。调用方可以用相同请求身份及request_id重放acquire，取回原租约；不应生成新的request_id去重复占额。

Adapter每次Provider准入尝试生成唯一request_id。对于响应结果未知，异常会向调用方暴露request_id；调用方须依据原任务身份执行协调状态重查，不得把该机制误解为Provider副作用的幂等保证。Provider副作用本身仍需原对象键/backup ID和存储端幂等策略。

## 4. 租约、过期与fencing

SQLite后端把租约到期时间保存为Unix wall-clock秒数，使进程重启后仍可校验租约；InMemory实现使用单调时钟，两个后端的 `expires_at` 不得跨后端比较。系统墙钟跳变会影响SQLite租约期限判断，生产实现须明确NTP/时钟漂移监测与故障处理。

每次新建租约在事务中递增持久化fencing token。续租会更新持久化过期时间；旧lease值不再通过validate。释放后保留请求终态记录，避免同一个request_id被误用。过期租约通过后续准入/validate/snapshot访问惰性回收，并累计过期计数；没有独立清扫服务。

**关键限制：** 本项目Provider接口尚未把fencing token传递给对象存储端并要求存储端拒绝较小token。因此持久化token目前只证明协调器颁发序列单调，不能阻止一个已过期的远端写请求在Provider端继续完成。

## 5. 自动化验证

新增 `tests/test_spare_parts_provider_admission_sqlite.py` 的12项测试，覆盖：

- 同一request_id重复申请返回同一租约、身份冲突拒绝、终态request_id不可复用；
- acquire响应丢失后重新打开数据库并用原request_id恢复租约；
- 协调器对象重建后租约仍可验证、fencing token持续递增；
- 过期租约回收、续租持久化和旧lease值失效；
- 两个独立协调器实例共享配额与等待队列；
- 策略哈希不一致拒绝；
- 使用Python `multiprocessing.spawn` 启动两个独立进程同时竞争同一SQLite文件，验证容量为1时只有一个进程能获得租约；
- InMemory协调器也支持request_id幂等及响应丢失后的相同请求重放。

这些测试证明的是GitHub Actions Linux runner上同一主机本地SQLite文件的测试结果，不是生产部署验收，也不是多主机验证。

## 6. 配置、运行与运维风险

- `database_path` 必须是持久文件路径；不接受 `:memory:`。
- 当前busy timeout默认5秒、轮询间隔默认50ms、max_waiters默认256；均为代码实现基线，不是生产容量建议。
- SQLite文件及WAL/SHM文件的OS访问控制、静态加密、备份、恢复、checkpoint、磁盘满处理和损坏恢复尚未实现。
- request终态记录不做自动压缩/清理；长期运行会持续增长，需要企业定义安全的幂等键保留期与归档/清理协议。
- 无自动租约心跳；Provider同步调用的硬超时必须短于lease TTL，并在下游执行fencing后才能提供陈旧写隔离。
- 当前没有持久QPS令牌桶、跨主机访问、自动主备、故障转移或外部协调服务健康探测。

生产备份仍关闭，`governance_readiness=BLOCKED_PENDING_ENTERPRISE_APPROVAL`，`business_rule_assertions=NOT_EVALUATED`。

## 7. 验收记录

**最终代码与CI验收（2026-11-26）：**

- 实现提交 3867b6c2ad3a3ab8832cf518b1c3b27db056bd6f 对应 [Run 45748405672](https://github.com/rexyll/cnc-knowledge/actions/runs/45748405672)，两个必需Job成功，全库201项unittest、CH12资源测试143项通过。
- 文档/续租测试/CI自检提交 8f7211c213131f4ceb972fcbb3228daa2b6b21f4 的Run 45748616308中全库202项测试通过，但SQLite CLI自检因脚本直接执行时仓库根目录没有加入sys.path而失败。
- 修复提交 8d2a36b6240f20b1968a7e2ef148dcc02e745f88 为SQLite CLI显式增加仓库根目录导入路径。最终 [Run 45748707053](https://github.com/rexyll/cnc-knowledge/actions/runs/45748707053) 两个必需Job均completed/success；全库202项unittest通过，CH12资源测试143项通过，knowledge_lint.py --strict返回RESULT: PASS (0 errors)。
- SQLite持久化自检PASS，Artifact [ch17-provider-admission-sqlite-45748707053](https://github.com/rexyll/cnc-knowledge/actions/runs/45748707053/artifacts/15084821221)，ID 15084821221；Provider Mock self-check PASS，Artifact ID 15084277008。

**未覆盖边界：** 所有SQLite用例仍是GitHub runner同主机本地文件的合成技术测试，不改变ASSET-000072中11条场景的批准/执行状态。未验证多主机/NFS/SMB/HA、数据库文件损坏/备份还原、静态加密、自动心跳、持久QPS令牌桶、下游fencing enforcement或生产容量。完整测试通过不能作为生产Provider、企业安全评审或灾备恢复验收。


### 第二十八轮附加回归：队列拒绝计数的事务边界

最终CI自检接入后的代码复核发现，队列满分支在准入事务中先更新rejected_queue再抛出异常，事务回滚会同时撤销该诊断计数。该问题不影响请求被拒绝或活动租约安全，但会使快照少报拒绝次数。现已将计数写入独立事务，并增加SAQQ-011对应的SQLite单元测试：队列满时拒绝新请求、保留活动租约、队列无残留，且rejected_queue持久增加。该测试仍属于本机SQLite合成验证。


### SQLite队列拒绝计数附加回归与最终验收

- 队列满分支原先在准入事务内更新rejected_queue并抛异常，事务回滚会使计数丢失。现改为准入事务回滚后使用独立事务提交拒绝计数；新增测试验证拒绝新请求、保留原活动租约、清除等待者并持久增加rejected_queue。
- 首轮补充测试Run 45749038281中新增测试因漏导入ProviderAdmissionQueueFullError产生NameError；修复提交b4dcebb5249546954090a50a1c7dff809796345c。
- **最终CI：** [Run 45749107843](https://github.com/rexyll/cnc-knowledge/actions/runs/45749107843)，两个必需Job均completed/success；全库203项unittest、CH12资源143项通过，knowledge_lint.py --strict为PASS（0 errors）。
- SQLite自检Artifact [15083979275](https://github.com/rexyll/cnc-knowledge/actions/runs/45749107843/artifacts/15083979275)；Provider Mock self-check Artifact ID 15084203674。
- 当前SQLite协调器专项unittest 12项；ASSET-000072共11条场景，全部PROPOSED_NOT_APPROVED / NOT_RUN。


## 第二十九轮补充：在线备份与外部 fencing 高水位恢复

- 新增 backup_to()：调用 SQLite Backup API 创建在线一致性快照，目标必须是新路径且不能覆盖现有文件；备份通过只读 integrity_check / foreign_key_check、schema / policy hash / 计数器校验，并输出 SHA-256。
- 新增 validate_backup()：检查 fencing 计数器不低于所有已签发记录的最大 token；报告活动租约、等待请求和备份摘要。
- 新增 restore_to_new_database()：恢复到独立新库，强制要求来自数据库之外的 external_fencing_floor 和 fencing_reconciliation_ref；恢复会使旧ACTIVE租约失效并清空等待者，将下一token推进到外部高水位及备份序列的最大值；不覆盖原库、不执行客户端切换。
- 新增6项SQLite测试：在线备份/活动租约快照、损坏备份拒绝、计数器倒退拒绝、恢复租约和等待者清理、外部高水位/策略门禁及禁止覆盖路径。SQLite协调器专项测试现18项。
- 该恢复API仅准备新库；服务切换、旧实例隔离、下游高水位全量盘点、恢复后业务一致性核对仍由受控运维流程负责。缺少可信外部高水位或下游不具备原子fencing时，不得恢复写入。
- **代码CI：** [Run 45751336613](https://github.com/rexyll/cnc-knowledge/actions/runs/45751336613) 两个必需Job均completed/success；全库217项unittest通过、CH12资源143项通过，strict lint 0 errors（5 warnings）。SQLite CLI自检PASS，Artifact [15084844535](https://github.com/rexyll/cnc-knowledge/actions/runs/45751336613/artifacts/15084844535)。
- 未覆盖：WAL/SHM磁盘故障、加密/签名、访问控制、异地介质、真实灾备演练、多主机协调和生产切换。
