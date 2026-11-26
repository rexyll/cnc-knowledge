# 数控机床备件库存账本备份 Provider 准入队列容量保护与恢复

**知识ID：** KNOW-000041  
**章节：** CH17 操作、维护与维修  
**状态：** IN_PROGRESS / 同进程Mock与合成测试  
**适用范围：** 对KNOW-000038～KNOW-000040的本地公平舱壁、共享协调器与故障处理做队列容量和恢复期过载保护补充。

## 1. 为什么需要排队上限

并发租约限制同时进入Provider的请求数，但不限制等待中的请求数。若Provider或协调器持续不可用，调用方持续提交任务，会导致本地Adapter及共享协调器的等待队列增长；服务恢复时，大量等待任务又可能同时争抢准入资源。

因此，活动并发额度与排队额度必须分别治理：并发限制控制在途工作，最大等待数限制排队内存和恢复时的竞争面。队列满时快速拒绝新等待者，不驱逐已经排队的任务。

## 2. 本地与共享队列上限

- `ProviderFairBulkhead` 新增 `max_waiters`，`BackupStorageAdapter` 暴露 `bulkhead_max_waiters`；用于每个Adapter实例、每个操作域的本地等待队列。
- `InMemoryProviderAdmissionCoordinator` 新增独立 `max_waiters`；用于共享协调器对象内各操作域合计等待者数。
- 两类配置当前默认值均为256，属于代码实现基线，不是容量推荐值。必须按并发负载、进程内存、租户公平和请求时限重新测量与审批。
- 配置为0表示不接受等待者，但不禁止可立即取得并发槽位/令牌的请求。
- 等待队列达到上限后抛出 `ProviderAdmissionQueueFullError`，该异常继承 `ProviderBulkheadFullError`，并通过 `scope` 区分 `local_bulkhead` 与 `shared_coordinator`。活动租约和既有等待者不被移除。

## 3. 协调器等待期间失效

共享协调器的 `acquire` 不仅在进入队列前检查可用性，也在每次等待循环醒来后重新检查。若协调器在排队期间转为不可用，当前等待者会收到 `ProviderCoordinatorUnavailableError(phase="acquire")`，并从队列移除；Adapter不得绕过协调器调用Provider，也不得把失败的旧任务静默重放。

服务恢复后，调用方必须按原业务任务ID/备份对象键重新判断任务状态并提交一次新的准入请求。旧等待请求不是恢复队列，也不构成自动重试。

## 4. 恢复期流量策略与观测

- 共享令牌桶的rate/burst可限制协调器正常工作时的Provider尝试速率和瞬时突发；突发额度必须按Provider合同与实测确定。
- 有界队列用于限制恢复时可被缓存的等待任务；队列满时拒绝并计数。上层任务调度器应结合任务deadline、优先级和幂等身份控制重新提交节奏。
- 当前未实现随机jitter、自动启动预热、动态扩容、恢复速率斜坡、跨进程共享或持久任务队列；不得据此声称已经消除了分布式恢复风暴。
- 本地 `bulkhead_snapshot()` 与共享 `coordinator_snapshot()` 新增 `max_waiters` 和 `rejected_queue` 观测字段。监控需区分本地队列满、共享队列满、并发满和令牌限流，避免把不同拒绝原因混为Provider故障。

## 5. 合成测试与限制

本轮新增3项Provider专项unittest：本地队列满时保留既有等待者、共享协调器队列满时保留既有等待者、协调器在排队期间不可用时清理等待者并在恢复后接受新的准入。并补充最大等待数负值/布尔值配置校验。

新增ASSET-000071定义7条纯合成验收场景，全部 `TRUE / PROPOSED_NOT_APPROVED / NOT_RUN`。以上只验证同进程线程和Mock对象，不构成跨进程/主机、真实网络分区、生产容量或恢复风暴测试。

**严格边界：** 协调器仍是同Python进程内共享对象；无持久任务队列、共享服务高可用、自动租约心跳、下游fencing enforcement或真实Provider。生产备份仍关闭，`governance_readiness=BLOCKED_PENDING_ENTERPRISE_APPROVAL`，`business_rule_assertions=NOT_EVALUATED`。

## 6. 验收记录

代码/测试提交 `a691f7eaedafdf96892c9613f3ae304e85f7047c`，分支为 `main`，未创建新分支。

- **最终CI：** [Run 45746342659](https://github.com/rexyll/cnc-knowledge/actions/runs/45746342659)；`Knowledge structure and data quality` 与 `CH12 numerical resource tests` 两个Job均 `completed/success`。
- **测试：** 全库 `unittest` 191项通过；CH12数控资源测试143项通过。Provider适配器测试文件包含64个 `test_` 方法定义（本轮新增3项），并随全库测试集执行。
- **静态校验：** `knowledge_lint.py --strict` 返回 `RESULT: PASS (0 errors)`。
- **Provider自检：** `spare_parts_backup_storage_adapter.py --self-check` 返回PASS；Artifact [ch17-backup-storage-adapter-45746342659](https://github.com/rexyll/cnc-knowledge/actions/runs/45746342659/artifacts/15083925258)，ID 15083925258。新队列回归由全库unittest覆盖，不应将该Artifact解读为单独的队列故障报告。
- **资源：** ASSET-000071的7条合成场景仍为 `TRUE / PROPOSED_NOT_APPROVED / NOT_RUN`；CI通过不改变审批或执行状态。
- **边界：** 仅同进程Mock与合成测试；无真实Provider、跨进程/主机共享、真实网络分区、生产容量或恢复风暴验证。生产备份关闭，`governance_readiness=BLOCKED_PENDING_ENTERPRISE_APPROVAL`，`business_rule_assertions=NOT_EVALUATED`。
