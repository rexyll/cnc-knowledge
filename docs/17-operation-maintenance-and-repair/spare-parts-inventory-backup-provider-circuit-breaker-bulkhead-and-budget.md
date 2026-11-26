# 数控机床备件库存账本备份 Provider 熔断、半开探测、舱壁与总重试预算

**知识ID：** KNOW-000037  
**章节：** CH17 操作、维护与维修  
**状态：** IN_PROGRESS / 仅本地与Mock并发故障注入  
**适用范围：** 第二十二轮瞬态错误与重试能力之上的 Provider 故障隔离、并发舱壁和顶层任务级重试预算。

## 1. 目标与明确边界

本轮通过本地/Mock验证连续故障时快速拒绝请求、冷却后半开探测、探测失败重新打开、探测成功关闭、按操作域限制并发、跨多个Provider调用累计任务重试预算，以及多个并发备份任务之间的预算隔离。

实现位于 \`scripts/spare_parts_backup_storage_adapter.py\`。控制器在一个 \`BackupStorageAdapter\` 实例内维护。熔断和舱壁状态不跨进程、不跨主机、不跨多个Adapter实例共享；当前不提供分布式熔断协调、全局任务队列或跨集群限流。真实Provider接入前须由部署架构决定这些控制是否需要提升为服务级协调能力。

## 2. 按操作域隔离的熔断器

Adapter为以下四个Provider操作域分别维护独立CircuitBreaker：

- \`read\`：回执和负载对象读取；
- \`write\`：普通对象和最终回执条件创建；
- \`multipart\`：分块会话创建、查询、写入和完成；
- \`inventory\`：指定前缀下的对象/会话元数据盘点。

每个域的状态机是：

\`CLOSED → OPEN → HALF_OPEN → CLOSED\`

连续发生达到阈值的 \`ProviderTransientError\` 时进入OPEN。OPEN期间请求快速失败，抛出 \`ProviderCircuitOpenError\`，不进入底层Provider调用，也不继续消耗重试次数。冷却时间到达后，第一个请求将域切换到HALF_OPEN并申请探测槽位。半开探测成功即关闭熔断、清零连续失败计数；探测再次出现瞬态错误则重新打开并重新计时。

普通的权限、输入、完整性或对象冲突错误不是Provider可用性故障，不累计熔断失败；Provider对请求返回永久错误仍会释放半开探测槽位。熔断以显式瞬态错误为依据，不会把所有异常一律判定为Provider故障。

默认配置：
- \`circuit_failure_threshold=3\`；
- \`circuit_reset_timeout_seconds=30\`；
- \`circuit_half_open_max_probes=1\`。

这些只是当前Mock/代码默认值，不代表推荐生产阈值。生产门限需根据错误率、调用基线、Provider SLA、恢复时间和任务优先级压测后确定。

## 3. 半开探测并发限制

同一个操作域进入HALF_OPEN后，默认只允许一个探测请求在途。探测槽位占用期间，其他同域请求立即收到 \`ProviderCircuitOpenError\`，不会同时打到仍可能故障的Provider。探测结束必须释放槽位；成功关闭电路，失败重新打开。

本轮测试涵盖半开槽位已占用时第二个请求被拒绝、探测失败重新OPEN、等待冷却后探测成功回到CLOSED。冷却时间由注入的单调时钟驱动，测试不依赖真实等待。

## 4. Provider操作域舱壁（Bulkhead）

Adapter为每个操作域配置独立的有界信号量，Provider调用只在真正执行期间占用槽位，退避等待时释放槽位。一个域占满或阻塞不应占住其他域的并发容量。

默认舱壁容量：
- read：4；
- write：2；
- multipart：2；
- inventory：1。

默认 \`bulkhead_acquire_timeout_seconds=0\`，即槽位满时快速返回 \`ProviderBulkheadFullError\`，不无限等待，也不自动排队。每次Provider调用结束或异常都会释放槽位，避免永久占坑。

舱壁仅作用于同一个Adapter实例/进程内的并发调用；多个进程、容器副本或不同Adapter实例之间不共享信号量。生产部署若需要全局并发上限，应在服务层/任务队列/租户配额层另行实施，并避免把本地信号量误当成分布式限流器。

## 5. 顶层备份任务的聚合重试预算

第二十二轮的 \`retry_max_attempts\` 仍限制单次Provider调用的最大尝试次数；本轮新增 \`retry_budget_total\`，限制一个顶层备份/验证/恢复/盘点操作中所有嵌套Provider调用累计消耗的重试次数。

- 每个顶层操作开始时创建独立RetryBudget；
- 同一个操作内部的对象上传、回执提交、读取验证和恢复读操作共享这一预算；
- 预算只统计重试，不统计每个调用的首次尝试；
- 每次瞬态失败准备重试时消耗1个单位；预算不足即抛出 \`RetryBudgetExceededError\`；
- 一个任务结束后预算上下文清理；另一个并发线程/任务创建自己的预算，不与其他任务争用计数；
- 同一任务上下文内嵌套调用复用当前预算，防止函数层级重置预算而绕过上限。

默认 \`retry_budget_total=20\`，这是实现默认而非生产推荐。实际值需要按单次备份对象数、Multipart分块数、重试策略、任务deadline、Provider限流和任务优先级计算。

预算耗尽或熔断打开均不得返回PUBLISHED/VERIFIED/RESTORED。调用方应将任务保留为可诊断的失败/待恢复状态，以原backup ID和原对象键再次盘点或人工恢复；不得通过创建新backup ID掩盖未知提交状态。

## 6. 与第二十二轮重试器的组合顺序

每次Provider调用按以下顺序控制：

1. 获取该任务的RetryBudget上下文；
2. 按操作域申请Bulkhead槽位；槽位不足立即失败；
3. 检查CircuitBreaker状态；OPEN/半开槽位占用时拒绝，不调用Provider；
4. 执行Provider操作；
5. 成功则记录熔断成功；明确瞬态错误才累加失败；
6. 若允许重试，先消耗本次调用尝试预算，再消耗顶层任务总预算；
7. 释放Bulkhead槽位后执行有界指数退避；
8. 重试继续使用同一对象键、backup ID、upload ID、part number和相同字节，保持第二十二轮的幂等语义。

\`ProviderCircuitOpenError\`、\`ProviderBulkheadFullError\` 和 \`RetryBudgetExceededError\` 都是快速失败控制信号，不会被误认成底层瞬态Provider错误并无限重试。

## 7. 并发与资源保护的适用范围

本轮只在单进程Mock环境验证：同域请求的并发槽位、读/写域互不阻塞、槽位在异常后释放、并发线程拥有独立任务级预算、半开只有一个探测请求。它不证明分布式锁、跨进程/跨容器信号量、集群级公平性、租户间资源配额、服务端全局QPS或真实网络时延下的端到端性能。

生产实现还需评估：
- 按Provider账号/租户/区域/服务操作域拆分熔断粒度；
- 熔断失败率窗口、连续失败计数、成功恢复条件和冷却策略；
- 半开探测请求的选择、优先级、超时和成功判据；
- 舱壁等待队列是否存在、排队上限、请求取消与公平性；
- 任务总deadline、单次调用超时、总重试预算和剩余RTO之间的约束；
- 多实例部署时的局部熔断与共享限流如何协同，避免所有副本同时半开探测造成恢复风暴。

## 8. 自动化测试与状态边界

新增9项专项unittest，覆盖熔断阈值和OPEN快速拒绝、半开探测失败重开/成功关闭、半开单探测配额、read/write熔断隔离、同域舱壁占满、异常后槽位释放、嵌套Provider调用共享任务级重试预算、并发任务预算隔离和配置参数校验。全库测试总数由160增至169。

CI代码/测试Run \`45740068529\` 两个Job均completed/success，169个unittest通过；扩展self-check Run \`45740213445\` 应在最终验收记录中确认两个Job和Artifact。自检增加熔断打开/快速拒绝/半开探测恢复与零总预算失败关闭。所有结果均来自本地/Mock。

**严格状态：** 无真实云Provider、真实IAM或网络；未验证跨进程/跨容器/集群级舱壁与熔断；没有真实供应商限流、RTO、生产并发容量和任务优先级测试。生产备份仍关闭，\`governance_readiness=BLOCKED_PENDING_ENTERPRISE_APPROVAL\`，业务断言仍 \`NOT_EVALUATED\`。


### 最终CI验收记录

- 代码及9个新增专项测试：Run `45740068529`，两个Job均completed/success，全库169个unittest通过。
- 熔断/半开/预算增强自检：Run `45740213445`，两个Job均completed/success；self-check `circuit_breaker_open_half_open_probe_and_recovery=PASS`、`aggregate_retry_budget_exhaustion=PASS`；Artifact ID `15081155445`。
- 文档、资源与覆盖率最终同步：Run `45740530720`，两个Job均completed/success；全库169个unittest通过、strict knowledge lint 0 errors；Provider Artifact ID `15080399203`。
- 最终状态：KNOW-000037、ASSET-000068已登记；CH17统计17篇KNOW、67个实体、61项资源。熔断/舱壁/总预算仅单Adapter/进程与任务上下文范围，生产备份仍关闭。
