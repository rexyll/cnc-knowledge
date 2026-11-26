# 备件库存备份 Coordinator etcd v3 Watch、Range恢复与多实例故障注入契约

**知识编号：** KNOW-000060  
**章节：** CH17 操作、维护与维修  
**关联知识：** KNOW-000051、KNOW-000052、KNOW-000055、KNOW-000059  
**正式场景矩阵：** ASSET-000091  
**状态：** Watch适配器扩展和共享后端多客户端测试替身完成；真实etcd driver/集群未接入

## 1. 现有能力盘点与本轮边界

项目早已具有CoordinatorAuthorityStore、EtcdV3CoordinatorAuthorityStore和注入式EtcdV3Client：
- linearizable_get通过Range(serializable=false)执行权威单键读；
- transact映射Compare/Success/Failure分支并对可能提交但响应丢失的Txn抛出OUTCOME_UNKNOWN；
- lease_grant、lease_keepalive、lease_revoke覆盖底层租约生命周期；
- InMemoryEtcdV3Client提供单进程原子Txn/Lease测试替身。

既有KNOW-000051已经说明Watch只能用于唤醒和增量提示，不能作为授权判据。本轮不重新创建KV/Txn/Lease端口，而是在现有Etcd adapter上补充可选Watch与线性一致前缀Range能力，并增加compaction/reconnect、多客户端共享后端和Lease故障注入。

**没有创建真实gRPC/JSON Gateway客户端；没有etcd server、Raft quorum、TLS/mTLS、RBAC或多主机运行证据。** 所有新增测试均使用一个进程内共享的确定性fake backend。

## 2. 接口拆分

### 2.1 必须的AuthorityStore与可选Watch能力

SQLite本地适配器无需实现etcd Watch，因此Watch不强制加入基础CoordinatorAuthorityStore，而作为可选CoordinatorAuthorityWatchStore能力单独声明。这样不会让本机SQLite测试实现虚假的远程事件推送。

新增能力：
- AuthorityStoreRangeResult(entries, revision)：表示一次线性一致范围读取结果及统一header revision；
- AuthorityStoreWatchEvent：PUT/DELETE、key、事件revision、当前entry和可选previous entry；
- AuthorityStoreWatchResponse：watch ID、header revision、created/canceled、compact revision、cancel reason、fragment和事件；
- EtcdV3WatchClient：规范化Watch stream及WatchProgress driver extension；
- EtcdV3CoordinatorAuthorityStore.linearizable_range：线性一致前缀/范围Range；
- EtcdV3CoordinatorAuthorityStore.watch和watch_progress：Watch响应归一化。

基础KV/Txn/Lease和可选Watch拆分后，未实现Watch的旧注入式driver仍可使用原有基础能力；调用Watch时必须明确报能力缺失，不得静默退化为普通轮询或旧缓存授权。

## 3. Watch事件及revision cursor

etcd v3.7 WatchCreateRequest的start_revision为**包含式**起点。WatchResponse包含created/canceled/compact_revision/cancel_reason/fragment；历史revision已被compact时，服务端取消Watcher，不能用同一个已compact的起点反复重建。progress notification的header revision表示Watch流进度，后续事件revision高于该header revision。参考SRC-000407。

### 3.1 首次创建

收到created=true只确认Watcher已建立，不代表已经追平历史事件。适配层返回created response，但不据此推进业务缓存cursor；后续必须消费对应事件或progress response。

### 3.2 事件响应

对完整的事件响应：
- PUT携带最新KV；
- 如果请求prev_kv=true，响应可能携带更新前KV；
- DELETE事件描述被删除key及删除revision；previous entry只有显式要求且历史可用时才存在；
- 一个Txn可能对多个key产生同revision的多个事件。应用必须按revision和key处理，不得假定一revision仅一条event。

完整非fragment响应的安全续订起点可使用header_revision + 1。如果响应标记fragment=true，一个revision可能跨多个响应拆分，消费者必须先合并/处理完该revision全部fragment；在最后fragment到达前不得推进cursor。

### 3.3 Progress与断线恢复

progress response不含events，但可提供Watch流已推进的header revision。它仅是订阅流进度提示，不证明当前Leader、Lease、scope或operation仍然有效。

推荐恢复流程：

1. 收到连接断开、stream异常或Watcher取消时，停止使用该Watcher；
2. 对受监控key或prefix执行新的线性一致Range，形成revision为R的权威缓存快照；
3. 使用start_revision=R+1重新创建Watch，避免Range快照和后续事件之间出现遗漏；
4. 收到Watch事件后再线性一致读取或Txn Compare验证任何会影响授权、安全或业务状态的决定。

不能只根据Watch缓存、progress header或“尚未收到revoke事件”证明Leader/Lease仍有效。

### 3.4 Compaction

若Watcher因compact_revision被取消：
- 不得在相同start_revision上重试；
- 不得把本地缓存直接作为新的权威状态；
- 必须线性一致Range重建缓存，再以返回header revision+1创建新Watcher；
- 若Range失败，则保持缓存STALE并fail-closed。

## 4. Linearizable Range

新增linearizable_range(key, range_end=...)返回entries与统一revision。它用于恢复prefix缓存，而不是为了替代Txn条件比较。实现必须调用Range(serializable=false)；禁止以member-local serializable读作为Leader/Lease/scope安全判据。

Range返回的每个entry的mod_revision必须小于或等于顶层header revision。prefix恢复建议使用稳定、明确且不重叠的key区间，避免把非目标namespace混入缓存。

## 5. 多客户端与故障注入模型

新增InMemoryEtcdV3WatchClient，多个独立EtcdV3CoordinatorAuthorityStore可共享同一fake对象，以模拟不同应用客户端观察同一个后端：
- 共享revision/KV/Lease状态和Compare/Txn互斥；
- Watch PUT/DELETE/prev_kv/progress/compact/cancel；
- Txn提交后响应丢失与提交前超时；
- LeaseGrant、LeaseKeepAlive和LeaseRevoke响应丢失；
- Lease过期时附着key删除并向Watcher发送DELETE。

该测试替身不模拟多个etcd server成员，不模拟Raft复制/选举/quorum，不模拟真实gRPC流、连接池、TLS认证、重连退避或网络分区时钟。多个adapter实例共享一个Python锁不等价于多主机共识。

## 6. 未知操作结果语义

| RPC/操作 | 故障表现 | 调用方要求 |
|---|---|---|
| Linearizable Range | 连接/超时错误 | UNAVAILABLE，不得退化到serializable/local cache |
| Txn | 请求超时或响应丢失 | OUTCOME_UNKNOWN；使用原operation/idempotency key线性一致read-back |
| LeaseGrant | 响应丢失 | OUTCOME_UNKNOWN；可能遗留无key附着的孤儿Lease，不能盲目创建新逻辑操作 |
| LeaseKeepAlive | 响应丢失/连接失败 | 本次续任未确认，Leader授权fail-closed；恢复后只对同一lease ID重新确认 |
| LeaseRevoke | 响应丢失 | OUTCOME_UNKNOWN；读取Lease附着key及Leader状态，不猜测已撤销或未撤销 |
| Watch | stream断开/compacted | Watch能力失效；linearizable Range重建后从R+1订阅 |

Txn read-back必须验证足够的业务身份字段、scope、idempotency key、request digest、Leader epoch和操作状态，而不只是“某个key存在”。当读回不可用时，业务结果仍是未知，不能编造成功或回滚。

## 7. 新增测试

新增tests/test_spare_parts_provider_authority_store_watch.py，共21项测试方法，覆盖：
- 线性一致prefix Range和revision；
- 两个独立adapter实例共享后端时CAS单赢家；
- Txn提交后响应丢失与提交前超时；
- Watch created、PUT/DELETE、prev_kv和progress；
- fragment cursor、start revision包含式和compact取消；
- active watcher落后compact、Range重建、R+1重订阅；
- Watch stream断线与显式close；
- Lease过期/撤销事件；
- LeaseGrant/KeepAlive/Revoke未知响应；
- 旧Leader Lease过期后Txn compare拒绝。

正式矩阵ASSET-000091共30条场景，全部PROPOSED_NOT_APPROVED / NOT_RUN。21项自动化测试是对共享fake backend的契约模拟，不代表30项正式矩阵已执行。

## 8. 生产Driver实施门禁

1. 选定并固定etcd v3.7目标版本和客户端库版本，确认watch stream对created、fragment、progress、cancel和compact字段的真实映射；
2. 验证Range/Txn/Lease/Watch调用的header revision、key/value bytes、lease ID和事件字段不丢失；
3. 为Watch定义有限缓存容量、backpressure、stream重建、cancel/close和进程退出资源释放规则；
4. 验证compaction/断线时Range快照与Watch R+1之间不遗漏事件；
5. 在真实三节点etcd集群执行kill/partition/leader election/quorum loss/slow consumer/compact while watch等故障注入；
6. 验证mTLS、RBAC prefix、证书轮换、endpoint failover和请求重试是否保留unknown-outcome语义；
7. 按Coordinator真实请求形状验证Txn/Lease/Range/Watch负载、p95/p99、watch lag、reconnect time和quorum恢复；
8. 企业批准后再考虑把领域Coordinator状态机从SQLite SQL迁移到该Store port；本轮没有改变这一生产集成前置条件。

当前schema-v2仍是唯一生产权威；etcd driver与watch extension没有连接真实集群；CH17-T004继续IN_PROGRESS。

## 9. 来源

- SRC-000397～SRC-000401：既有Coordinator后端一致性、Txn、Lease、Election和故障语义来源；
- SRC-000407：etcd v3.7 API Reference与Watch API，start_revision、created/canceled/compact_revision、fragment及progress revision语义；
- KNOW-000051：Coordinator authority store基础KV/Txn/Lease端口；
- KNOW-000052：Txn分支内有序Get读批次。


## 10. CI验收记录

- **最终代码head：** `cdaff0dc43834b3250d8803efb0591a8656c363d`（main）。
- **CI：** [GitHub Actions Run 45826709629](https://github.com/rexyll/cnc-knowledge/actions/runs/45826709629)，head SHA与提交一致，两个必需Job均completed/success。
- **测试结果：** 全库484项unittest通过（含本轮21项Watch/多客户端故障注入测试）；CH12 143项数值资源测试通过；strict knowledge lint 0 errors；知识结构与数据质量0 errors。另有5项既有合成fixture审批/执行状态warning。
- **边界：** CI使用单进程共享InMemoryEtcdV3WatchClient及两个独立adapter实例，不连接etcd server，不证明Raft quorum、多主机网络分区、mTLS/RBAC、真实gRPC Watch流或生产吞吐。ASSET-000091的30项正式场景仍PROPOSED_NOT_APPROVED / NOT_RUN。
