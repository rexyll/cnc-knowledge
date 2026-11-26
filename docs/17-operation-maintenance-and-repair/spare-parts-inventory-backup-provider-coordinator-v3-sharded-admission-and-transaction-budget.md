# 备件库存备份 Coordinator Schema v3：分片准入、配额槽位与 etcd 分布式事务预算

**知识编号：** KNOW-000059  
**章节：** CH17 操作、维护与维修  
**状态：** 分片准入与事务预算参考模型/单元测试完成；生产集成未启动  
**前置知识：** KNOW-000054、KNOW-000055、KNOW-000056、KNOW-000058  
**关联资源：** ASSET-000090

## 1. 目标与现状

第四十轮的 Unified Admission Scheduler 把全局/租户配额、活动Lease、等待队列、fencing counter和request幂等放在一个schema-v2 revisioned aggregate。第四十一轮又将Coordinator Leader、Scope和Operation Ledger纳入同一个aggregate。这样能让同一Txn内的状态保持一致，但所有无关Tenant的Acquire、Renew、Release和Coordinator操作都会比较并改写同一个aggregate revision。

现有 StoreBackedProviderAdmissionCoordinator._load_prepared() 会读取活动Lease集合、逐个验证活动lease key/request key，再把精确Compare追加到当前事务；Compare数至少随活动lease数量线性增长。Acquire还在同一个Aggregate中更新active map、waiter和全局fencing序列。这个基线适合先建立正确性，不是无限扩展的多租户并发模型。

本轮建立候选Schema-v3分片准入参考模型，目标是：
- 准入热写从全局aggregate revision冲突转成独立的capacity slot与tenant/request key；
- 以两个维度的slot claims同时保证全局与租户并发上限；
- 将等待队列拆到tenant路由分区，并采用有界批量调度；
- 以分区Leader和非重叠fencing token区间减少每次发号对单一全局序列键的访问；
- 把每个Txn的Compare、Then/Else操作数和请求字节纳入显式预算。

本轮不是生产改造：不替换schema-v2、不连接真实etcd、不提供生产客户端或真实多实例性能数据。所有参考数字均是代码模型或待测参数。

## 2. V3逻辑keyspace

建议在同一个目标etcd集群内按职责与Tenant逻辑分区；逻辑分片不等于部署多个独立etcd集群，也不会移除etcd集群自身的Raft提交路径。

| Keyspace（示意） | 内容 |
|---|---|
| /cnc/admission/v3/control | schema generation、policy revision、partition-map generation |
| /cnc/admission/v3/global/domain/slots/slot-id | 有界全局并发Permit槽 |
| /cnc/admission/v3/tenant/tenant-hash/domain/slots/slot-id | tenant/domain并发Permit槽 |
| /cnc/admission/v3/leases/lease-hash | 活动Admission lease身份与fencing token |
| /cnc/admission/v3/requests/request-hash | request_id持久幂等记录及终态tombstone |
| /cnc/admission/v3/queue/partition/tenant-hash/domain/waiter-id | Tenant等待请求 |
| /cnc/admission/v3/queue-head/partition/domain | 分区内待调度队列摘要 |
| /cnc/admission/v3/dispatcher/domain | 轮转游标、批次epoch与调度策略版本 |
| /cnc/admission/v3/partitions/id/leader | 分区Leader ID、epoch与TTL |
| /cnc/admission/v3/partitions/id/token-range | 当前Leader已预留的token range状态 |
| /cnc/coordinator/v3/scopes/scope-hash | 单scope lease/fencing high-water/sequence/archive pointer |
| /cnc/coordinator/v3/operations/scope-hash/op-key | scope内operation精确记录 |

tenant-hash采用规范化tenant ID的稳定哈希。映射需绑定partition-map-generation；tenant迁移到另一partition时必须冻结该tenant写入、排空或显式迁移活动状态，并对外部fencing floor做核对，不能让两个partition同时成为同一scope的写入权威。

## 3. 双槽Permit：全局/租户配额不再依赖共享计数器

### 3.1 槽位模型

对每个Admission domain分配固定数量的全局slot，其数量就是该domain的全局并发上限。例如write=128，则全局write slots为128个固定key。对每个Tenant/domain分配最多min(tenant_limit, global_limit)个tenant slots。

一次成功Admission必须同时占用：
1. 一个空闲的global/domain slot；
2. 一个空闲的tenant/domain slot。

因此，对任意时刻：

\[
Active(domain) \le GlobalLimit(domain)
\]

\[
Active(tenant,domain) \le TenantLimit(tenant,domain)
\]

两项占位必须在同一个etcd事务中完成。不能先扣global counter再扣tenant counter，也不能用两个RPC分别占位。由于global slot池大小本身不超过global quota，而每个tenant slot池不超过tenant quota，所以即使任意数量的服务实例同时执行Acquire，也无法成功占用超过池容量的slot。

### 3.2 Acquire事务

候选流程：

1. 对request_id做线性一致查询；若已有相同identity的ACTIVE lease则返回原记录，若终态则拒绝重用；identity不匹配则幂等冲突。
2. 为Lease申请etcd native Lease TTL。该步骤独立于Txn，若后续Compare失败，撤销未被引用的candidate Lease。
3. 对global slot和tenant slot池做Range，选取可能空闲的slot。请求ID哈希可作为起始偏移，避免所有客户端先竞争slot 0。
4. 提交单Txn Compare：
   - control generation/policy revision未改变；
   - global slot VERSION=0；
   - tenant slot VERSION=0；
   - request idempotency key不存在；
   - 当前tenant partition Leader epoch/lease仍有效。
5. Then写入global slot、tenant slot和Admission lease record，三者附着同一个etcd Lease TTL；同时持久写入request记录为ACTIVE。

**参考事务规模：** 5个Compare + 4个Put，保守模型按9个操作预算。Compare失败意味着slot可能已被其他请求抢占，应重新Range/选择并重试；不得据此降低配额或绕开Tenant限制。

etcd官方API说明Txn是原子的If/Then/Else；所有Compare必须同时成立，Then分支才执行；同一事务中的键修改需遵守唯一键约束（不能重复Put/Delete同一key）。因此，global slot、tenant slot、lease record和request record必须纳入同一目标Txn边界。参考SRC-000405。

### 3.3 为什么slot key也附着同一个TTL Lease

etcd v3.7 Lease语义说明，一个key最多附着一个Lease；Lease过期或撤销时，该Lease关联的所有key都会被删除。可以把global slot、tenant slot与活动Admission lease record附着同一Lease，让三个活动凭证共同失效。request idempotency记录不附着TTL，作为持久tombstone保留。参考SRC-000406。

Lease过期后，request tombstone可能暂时仍显示ACTIVE；请求重放路径必须验证对应lease/global-slot/tenant-slot是否存在且身份一致，再通过CAS把request记录标记为EXPIRED。不能因为request key仍存在就重放过期Lease，也不能因为其slot消失就把同一request_id重新变成新请求。

### 3.4 Release与Renew

- **Release：** 同一Txn比较当前lease、global slot、tenant slot、request record精确值；删除三个活动key并将持久request tombstone写为RELEASED。事务提交后可撤销native Lease清理空Lease。
- **Renew：** 先申请新native Lease；一个Txn比较旧lease/global/tenant slots和request精确值，再把三个活动key改挂到新Lease并更新request expires_at。成功后再撤销旧Lease。响应丢失时必须通过相同request_id和slot/lease read-back确定结果；不可新造request_id重试。
- **Expiration：** native Lease过期删除slot和lease keys，request tombstone保留；重放/后台reconcile标记EXPIRED。reconcile不能重建旧slot，也不能复活已过期fencing token。

### 3.5 代价与限制

slot池消除了“每次Acquire更新同一个全局计数器”的写竞争，但并不免费：
- slot选择需要Range读取候选key，池越大越需要分页、缓存或分块扫描；
- 同一global slot和同一tenant slot仍可能发生Compare冲突，客户端要做有界重试；
- 全局slot池固定容量，配额增长需版本化扩容；配额缩小不能直接截断仍被占用的高slot；
- 若将global/tenant slot key放在不同etcd集群，就不能通过同一Txn保证两者原子占位；
- control和policy改动需要单独版本化，避免读到旧配额后仍成功Acquire。

## 4. Tenant队列分片与公平调度

### 4.1 队列隔离

等待请求按稳定tenant hash路由到partition；Tenant内保留priority和aging。入队只更新本tenant queue及该partition的queue-head摘要，避免所有Tenant请求都更新单一全局Aggregate。

### 4.2 候选公平策略

本轮参考模型采用：
- **跨Tenant：** round-robin，确保有容量时各活跃Tenant轮流获得dispatch机会；
- **Tenant内部：** priority + elapsed/aging_interval作为effective priority；同分按Tenant-local enqueue sequence FIFO；
- **Dispatch：** 有界batch；调度器每个domain维护一个cursor/epoch，对一个batch中的派发进行版本化仲裁。

这与schema-v2目前跨所有waiter统一比较priority+age的严格全局排序**不完全等价**。采用跨Tenant轮转能避免一个Tenant的高优先级洪峰持续压制其他Tenant，但它会把priority限定在Tenant内部。必须经业务owner批准后才能作为V3正式策略；不得静默切换。

### 4.3 Dispatch事务与热点边界

调度器读取同一revision下的partition queue-head摘要，选择候选Tenant后，在一个事务内比较：
- dispatcher epoch/cursor；
- 被观察的partition-head revision；
- 被选waiter的revision；
- global/tenant slot不存在；
- request tombstone不存在；
- 相关partition Leader epoch有效。

Then完成slot/lease/request写入、waiter删除、partition head更新及dispatcher cursor前移。若任一被观察的queue-head变化，事务失败并重新选取，避免使用过期候选。

这一机制把全局仲裁集中在每个domain的dispatcher batch上，而不是集中在每一次入队、renew和release。dispatcher本身仍可能成为该domain的串行吞吐边界；batch是摊薄固定事务成本的方法，不是无锁或完全去中心化声明。

## 5. Fencing token：分区Leader与非重叠区间预留

单一全局next_fencing_token每次Acquire都加一，会形成写热点。候选方案是保留一个**仅用于区间预留**的global high-water allocator：
1. 每个tenant partition只有一个有效Leader，Leader key通过native Lease与单调epoch保护；
2. partition Leader在当前token block耗尽时，CAS预留一个新的全局唯一区间，例如64个token；
3. 当前Leader在本地原子发号；不为区间内每个token更新global allocator；
4. Leader失效/进程重启后，未使用token区间整体作废，不尝试从旧区间继续；
5. 新Leader必须以更高epoch接管，并在global reserved high-water和外部Provider fencing floor之上申请新区间。

该策略保证：
- 同一个partition内token递增；
- 不同partition预留区间不重叠，因此token全局数值唯一；
- Leader故障后允许token出现空洞，但不复用旧token。

不同partition token的数值大小不代表跨partition的真实发号时间先后。业务下游必须按稳定scope/tenant partition检查fencing token；不允许对不同scope token做全局大小排序。tenant跨partition迁移前冻结旧scope、核对外部high-water，再允许新partition发号。

如果既有API消费者硬性要求“所有Tenant跨partition全局严格按实际发出时间递增”，则区间预留不能保持这一语义；必须保留逐次global sequence CAS或修改下游契约并获批。本模型不隐瞒这个取舍。

## 6. Coordinator业务事务与跨分片边界

普通备份/发布操作应绑定单tenant/scope；scope state、operation record和Admission lease/slot guard在同一etcd集群Txn中提交。候选Compare至少验证control generation、Coordinator Leader epoch、scope revision、operation/idempotency key不存在、Admission lease/global slot/tenant slot仍然匹配；Then原子更新scope和operation。

在同一个etcd集群内，逻辑partition不同不代表Txn不能跨这些key；只要该事务的Compare/Then请求和请求字节未超过目标服务端限制，就可以用一个Txn实现原子提交。反之，如果跨多个独立数据库或外部对象存储，则etcd Txn不能提供跨系统原子性，必须定义Saga/两阶段状态/幂等补偿与恢复审查，不能把多个RPC串行成功宣称成一个原子事务。

跨多个tenant/scope的批量动作优先拆成独立幂等子操作；只有业务要求all-or-nothing且事务预算可证明满足时，才考虑跨scope单Txn。超过预算必须明确拒绝、缩小批次或走经批准的Saga，不得静默拆成若干非原子写入。

## 7. Transaction Compare/Then/Else与请求预算

etcd v3.7官方配置文档列出的--max-txn-ops默认值为128，--max-request-bytes默认值为1,572,864 bytes；二者是可配置server options，不是所有目标集群的固定硬编码值。实施前必须读取目标集群的真实配置和适用版本。参考SRC-000403。

本轮提供EtcdTransactionBudget估算器：
- 保守operation count = Compare数量 + max(success_ops, failure_ops)；
- 请求字节使用canonical JSON reference payload长度；
- 默认分析目标为配置值70%，只是本项目的安全余量，不是etcd硬限制；
- **不等于protobuf/gRPC wire size**，不包括真实协议封装、header、压缩及适配器编码。

候选预算示例（以128、1,572,864 bytes作为文档默认参考、70%模型目标）：

| 事务形状 | Compare | Then Ops | 保守操作数 | 说明 |
|---|---:|---:|---:|---|
| Admission单笔占位 | 5 | 4 | 9 | control、两个slot、request、partition leader |
| 单scope Coordinator提交 | 7 | 2 | 9 | scope、operation及Admission lease/slot guards |
| 16 partitions、4 grants派发批次 | 33 | 25 | 58 | 含partition heads、waiter删除及dispatcher更新 |
| 64 partitions、4 grants派发批次 | 81 | 25 | 106 | 超过70%参考操作预算，应减小partition head fan-in或拆批 |

第三行、第四行只是本轮模型的预算样例；生产配置必须基于真实Txn请求构造、目标版本和服务端参数做集成验收。官方API还要求同一Txn中请求的key修改集合保持唯一；批量dispatch更新同一个partition head时必须先合并为一次写入。参考SRC-000405。

## 8. 参考模型、验证与观察指标

新增：
- scripts/spare_parts_provider_admission_partition_model.py：固定global/tenant slot、tenant队列、跨tenant轮转、tenant内部priority/aging、lease renew/release/expiry、partition leader和token block allocator、Txn budget。
- tests/test_spare_parts_provider_admission_partition_model.py：并发不超卖、请求幂等、slot一致性、释放/过期、Leader failover、token不复用、事务操作与字节预算等合成测试。
- ASSET-000090：正式准入分片/分布式事务场景矩阵，待批准/未执行。
- SRC-000406：etcd v3.7 Lease key expiry/revoke语义；复用SRC-000403/405作为配置/事务来源。

推荐真实系统监控：
- global/tenant slot active、空闲和分布偏斜；
- slot候选冲突率、Compare失败重试率；
- 每partition queue depth、最老waiter age、每Tenant grant share；
- dispatcher batch size、head revision冲突及批次延迟；
- fencing range refill次数、未使用range gaps、partition Leader epoch切换；
- 每笔Txn Compare数量、Then/Else操作数、真实protobuf bytes、p95/p99 latency；
- native Lease TTL过期数、request tombstone reconcile延迟和unknown outcome数量。

当前参考模型使用Python锁模拟一次原子Txn，不模拟真实etcd并发提交、Lease server时钟、watch断线、Raft quorum或网络分区；因此模型单测通过只能验证状态机和预算公式，不等于真实多实例一致性或吞吐验收。

## 9. 生产集成门禁

1. 企业批准V3跨Tenant round-robin与Tenant内priority-aging的公平性语义，明确与V2旧策略差异及可接受的最大等待时间。
2. 通过真实负载确定global slot/tenant slot粒度、候选slot Range读取策略、slot冲突重试和配额动态变更流程。
3. 确定partition数量、tenant hash version、Leader归属、迁移/重分区协议和fencing range block size。
4. 验证单租户/单scope所有写入均由单一partition authority保护；partition failover要检查外部Provider high-water。
5. 在真实etcd集群上对比：v2单aggregate、v3分区slot、不同partition count、不同batch grants；测实际gRPC protobuf请求字节与Txn Compare/Then/Else计数。
6. 演练Txn lost response、Lease过期、Leader split-brain/epoch takeover、Slot索引不一致、policy resize、active tenant churn、queue-head revision冲突、fencing block部分耗用、重分区中断和恢复。
7. 确认全局quota、tenant quota、公平调度、request幂等和Coordinator scope commit在故障/恢复时仍保持同一权威；无企业批准前不执行schema-v2→v3切换。

当前schema-v2仍是唯一生产权威；V3分片模型和ASSET-000090均未获企业批准。CH17-T004继续IN_PROGRESS。

## 10. 来源

- SRC-000403：etcd v3.7 Configuration options，Txn操作数和请求大小的默认值/可配置性。
- SRC-000405：etcd v3.7 API，Txn Compare/Then/Else和同Txn原子修改约束。
- SRC-000406：etcd v3.7 API Lease，Lease过期/撤销会删除附着key。
- KNOW-000058：Archive Index与Coordinator Schema v3迁移/回滚设计。


## 11. CI验收记录

- **最终代码head：** \`a035cdf1f82e6ea9274195b2872953e9f12e83ba\`（main）。
- **CI：** [GitHub Actions Run 45823628905](https://github.com/rexyll/cnc-knowledge/actions/runs/45823628905)，head SHA与代码提交一致，两个必需Job均completed/success。
- **测试结果：** 全库462项unittest通过（含本轮36项分片准入与事务预算参考模型测试）；CH12 143项数值资源测试通过；strict knowledge lint 0 errors；知识结构与数据质量0 errors。另有5项既有合成fixture审批/执行状态warning，非本轮测试失败。
- **验收边界：** 只验证内存状态机、并发模型和预算公式；不代表真实etcd事务、native Lease时序、多主机Dispatcher、Raft quorum或生产性能通过。ASSET-000090的54项正式场景仍PROPOSED_NOT_APPROVED / NOT_RUN；V3跨Tenant round-robin与V2全局priority-aging语义差异必须先经企业批准。
