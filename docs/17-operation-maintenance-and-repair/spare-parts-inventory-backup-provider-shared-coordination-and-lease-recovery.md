# 数控机床备件库存账本备份 Provider 多实例配额、共享限流与租约恢复

**知识ID：** KNOW-000039  
**章节：** CH17 操作、维护与维修  
**状态：** IN_PROGRESS / 同进程多Adapter共享内存模拟  
**适用范围：** 对第二十四轮单Adapter任务调度做补充，定义可替换的共享准入协调器接口，并用共享内存Mock验证多Adapter实例之间的并发配额、租户配额、令牌桶限流和租约过期恢复。

## 1. 设计边界

第二十四轮的公平队列和租户并发上限属于单个Adapter实例。本轮新增 `ProviderAdmissionCoordinator` 抽象，让多个Adapter实例可以把Provider操作域准入请求交给同一个协调器；每次被准入时申请带租户、操作域、所有者、过期时间和单调fencing token的租约。

本轮具体实现 `InMemoryProviderAdmissionCoordinator`，只允许在同一Python进程中由多个Adapter共享同一个对象。它不是跨进程共享内存、数据库、Redis、消息队列、云服务或生产分布式限流器。真实多进程/多主机实现必须替换接口实现为具有原子事务/CAS/脚本能力的共享服务，并验证其故障域、可用性与持久性。

协调器实例应按一个明确的Provider账号/区域/资源范围隔离配置；不能把不同Provider账户的流量错误地聚合到同一策略实例。

## 2. 全局并发和租户配额

协调器对 `read/write/multipart/inventory` 四个操作域分别施加共享并发上限；可对某个tenant ID再设置该操作域的并发上限。未配置的租户使用该操作域全局上限。

所有配额在一个协调器对象的互斥区内原子检查和创建租约。不同Adapter实例共享同一协调器时，不能各自独立超发；某个租户达到配额时，其他租户仍可使用全局剩余槽位。协调器与Adapter本地舱壁同时启用时，本地舱壁先筛选，再申请共享租约。

共享公平队列使用调用方priority（较大整数优先）、等待时间aging及FIFO打破平局。所有实例共用一个协调器队列时，才能在该同进程模拟范围内实现跨Adapter排队公平。Admission等待仍由 `bulkhead_acquire_timeout_seconds` 控制；超时后从等待队列移除。

## 3. 共享令牌桶限流

可选配置 `rate_limits_per_second` 和 `rate_bursts`，对每个Provider操作域施加共享令牌桶。每次Provider尝试在获得并发租约时原子消费一个令牌；失败重试再次申请准入，因此也会消耗令牌。

令牌不足时，协调器计算 `retry_after_seconds` 并抛出 `ProviderRateLimitExceededError`。该错误不是Provider瞬态错误，不会被现有自动重试器悄悄重试；调用方可结合任务deadline、业务优先级和Provider正式限流约定决定是否重新提交。令牌桶速率、burst均没有预填生产建议。

## 4. 租约、租约续期与故障恢复

共享租约包含 `lease_id`、`owner_id`、`tenant_id`、`domain`、`fencing_token` 和 `expires_at`。协调器在租约到期后回收名额；后续新租约获得更大的fencing token。释放、续租、有效性验证都必须同时匹配当前租约身份，旧所有者不能用过期租约释放后来者的槽位。

`renew()` 提供显式租约续期契约；当前同步Adapter调用不启动心跳线程，也不会自动续期。调用方必须将 `coordinator_lease_ttl_seconds` 设为明显大于真实Provider单次调用的硬超时，并由实际Provider adapter实施连接/读写超时。当前Provider Protocol不强制传递fencing token给底层服务，所以本地lease expiry不能证明远端副作用被阻止。

若Provider callback无论正常返回还是抛出异常时共享租约已丢失，Adapter抛出 `ProviderAdmissionLeaseLostError`，其 `outcome_unknown=True`：不得将其解释为操作未发生，也不得自动使用新backup ID重做；应以原对象键/backup ID执行盘点、幂等验证或恢复流程。fencing token只有在下游存储服务也验证并拒绝旧token时，才能成为真正的陈旧写入保护。

## 5. 诊断计数

`coordinator_snapshot()` 可读共享并发上限、各域活动租约、租户占用、等待数、过期租约、发放租约、拒绝配额与限流计数。快照不包含对象正文、密钥或凭据；租户标识属于运营元数据，日志/监控导出前仍应按企业隐私策略审查。

## 6. 自动化测试与验收范围

新增8项专项unittest：
- 两个Adapter共享同一协调器时遵守跨实例域并发上限；
- 租户配额跨Adapter生效，其他租户可使用全局剩余槽位；
- 租约过期后回收名额，旧fencing token不能释放新租约；
- 续租延长有效期，过期租约续租/释放失败；
- 令牌桶在多个Adapter间共享，时间推进后按速率恢复；
- Adapter调用期间租约丢失后不报告成功，返回结果按outcome-unknown处理；
- 全局容量、租户配额、速率、burst和lease TTL配置非法时拒绝启动。

所有测试均在单进程线程与注入时钟上运行，不进行跨进程/跨主机或真实Provider测试。

**生产限制：** 当前协调器没有跨进程共享、持久化、网络故障恢复、主备切换、quorum、时钟漂移治理、租约心跳或下游fencing执行。租约过期只证明本地协调器回收名额；不保证之前的远端请求已停止。生产实现必须选定共享协调服务，定义一致性/可用性取舍、服务宕机时fail-open/fail-closed策略、租约与Provider请求超时关系、fencing落地和观测告警，并经过多进程/断网/进程崩溃/恢复风暴测试。

生产备份仍关闭，`governance_readiness=BLOCKED_PENDING_ENTERPRISE_APPROVAL`，`business_rule_assertions=NOT_EVALUATED`。


## 7. 最终CI验收记录

- 首次代码/测试CI Run 45743739362执行181个测试时，两个直接协调器租约测试因测试模块遗漏导入 `ProviderTaskContext` 发生NameError；其余共享并发、租户配额、令牌桶等测试通过。
- 修复提交 `a77a4b51723fe9f2e01109cca0496cd00d843a37` 补齐import，并加固Provider callback异常退出时的租约有效性检查：如果Provider永久或瞬态异常发生时租约已丢失，统一返回 `ProviderAdmissionLeaseLostError`，防止错误路径继续重试。
- 最终CI：[Run 45743927996](https://github.com/rexyll/cnc-knowledge/actions/runs/45743927996)，Knowledge structure and data quality与CH12 numerical resource tests两个Job均completed/success；全库182个unittest通过，Provider适配器专项54个。
- `knowledge_lint.py --strict` 为PASS（0 errors）；Provider Mock自检PASS；Artifact [ch17-backup-storage-adapter-45743927996](https://github.com/rexyll/cnc-knowledge/actions/runs/45743927996/artifacts/15081984380)，ID 15081984380。
- **严格边界：** 所有多Adapter协调测试共享同一Python进程中的Mock协调器对象。17条矩阵仍PROPOSED_NOT_APPROVED / NOT_RUN；无跨进程/主机、真实Provider、网络分区、主备、quorum、自动心跳、下游fencing或生产容量验证。生产备份仍关闭。
