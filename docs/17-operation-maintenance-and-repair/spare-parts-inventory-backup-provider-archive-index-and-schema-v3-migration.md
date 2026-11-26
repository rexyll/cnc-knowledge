# 数控机床备件库存备份 Archive Index 精确幂等查询与 Coordinator Schema v3 迁移/回滚设计

**知识编号：** KNOW-000058  
**章节：** CH17 操作、维护与维修  
**状态：** 精确索引与迁移状态机参考模型及单测已建立；尚未接入生产 Coordinator / etcd / 对象存储  
**关联知识：** KNOW-000055、KNOW-000056、KNOW-000057  
**关联资源：** ASSET-000089

## 1. 本轮目标与边界

第四十三轮定义了 Operation Ledger 的不可变归档协议，但现有参考模型的幂等查询仍需遍历从最新 manifest 到最旧 manifest 的完整链。链越长，旧 idempotency key 的查找读取量越大。本轮增加精确分片索引，同时定义 schema-v2 到 schema-v3 的对象拆分、写入冻结、候选验证、原子切换和回滚约束。

本轮实现仍是纯内存参考模型；不修改 StoreBackedCoordinatorAuthority 当前 schema-v2，不连接真实 etcd、SQLite、云对象存储或生产 Provider。Schema v3 是候选逻辑数据布局，不是已批准的生产 keyspace，也没有启用双写或迁移。

## 2. 精确 Archive Index

### 2.1 两级不可变索引结构

新增 ExactShardedArchiveIndex：使用固定数量的 SHA-256 前缀桶将 operation key 分片；支持16、256、4096桶三种参考配置，默认画像配置为256桶。桶数是可调参数，不是生产容量结论。

索引 operation key 与第四十三轮一致：

\[
K_{\mathrm{op}} = \operatorname{SHA256}(\mathrm{scope}\; ||\; 0x00\; ||\; \mathrm{idempotency\_key})
\]

索引包含两级内容寻址对象：

**Root manifest：**

| 字段 | 含义 |
|---|---|
| scope | 所属tenant scope |
| generation | 对应归档链代际 |
| archive_head_sha256 | 本代际对应的权威归档链head |
| previous_index_sha256 | 上一代索引root的内容摘要 |
| bucket_count | 16 / 256 / 4096 |
| operation_count | 当前scope的累计索引记录数 |
| buckets | bucket ID到不可变shard摘要及记录数的映射 |

**Bucket shard：**

每个桶是按 operation key 升序排列的精确索引数组。条目保存 operation_key、目标 archive batch SHA-256、batch generation、batch内record序号及record canonical SHA-256。索引不依靠概率结构决定最终命中/未命中。

### 2.2 查询路径和复杂度

对一个已知 scope/idempotency key：

1. 读取 Coordinator scope 权威元数据中的 archive head、archive generation、archived operation count 和 index root pointer。
2. 读取并校验 Root manifest，检查 scope、generation、archive head、bucket count 和累计数量与权威指针一致。
3. 根据 operation key前缀定位一个 bucket；如果该bucket没有被登记，只有在root完整性和权威累计数量都通过校验后才可返回 exact-not-found。
4. 若bucket存在，读取对应shard，校验摘要/记录数/排序，执行二分查找。
5. 命中时只读取目标archive batch，并校验batch摘要、generation、record位置、原始idempotency key、scope及record摘要后才返回原始operation。

正常命中最多涉及root、一个shard和一个目标batch三个归档对象读取；不需要从最新manifest遍历所有历史批次。桶不存在的exact miss只需要root对象及权威计数校验。每次查询还要传入从Coordinator scope元数据**独立读取**的 archived_operation_count；若索引自报数量与权威计数不一致，必须fail-closed。

不允许使用Bloom Filter的“可能不存在”结果直接创建新operation。Bloom Filter若未来加入，只可作预筛选；任何negative都必须经过完整性校验的精确索引确认。archive store不可用、root/shard损坏、目标batch缺失、count/generation/head不一致时，均不得将错误转换为not-found。

### 2.3 回填与增量更新

- **历史回填：** 从当前权威archive head沿manifest链完整向前验证generation和previous pointer，生成每个桶的有序快照，校验全部operation key无重复；最后生成root pointer。回填前后应对照archive manifest链的总记录数和完整精确键集合。
- **后续追加：** 新归档batch必须恰好延伸当前archive head、generation递增。仅重建该批次触及的bucket shard；未触及桶沿用旧不可变对象。所有新shard和root先写入不可变存储并read-back校验，再把新index pointer与archive pointer一起交给Coordinator CAS。
- **CAS冲突：** 新建对象可能成为orphan；不得删除旧root/shard/batch，不得切换到未提交索引。热账本仍是权威，orphan回收要走独立盘点和审批。
- **全链审计：** 定期从manifest链重建预期精确键集合，与所有bucket shard逐项比对，检查遗漏、重复、错scope、generation跳跃、目标batch/record位置和摘要。在线单次查询不代替全链审计。

桶数增加可以降低平均单桶索引体量，但会扩大root映射和回填/增量写放大；桶数减少则减少root复杂度但增加桶内条目数。实际选择须基于真实历史operation数量、idempotency key长度、对象存储请求次数、p95/p99查询延迟、热点scope和bucket size分布测量；当前没有已批准的生产桶数或shard大小阈值。

## 3. Coordinator Schema v3 候选布局

Schema v2将 scheduler、所有active lease、waiter、Coordinator scopes和完整operation ledger编码在一个revisioned aggregate中。Schema v3候选布局把这些职责拆到独立对象/key，使Coordinator操作不必为单个scope操作遍历和比较全局所有active lease。

建议keyspace（示意，不是已批准生产前缀）：

| 对象 | 逻辑职责 |
|---|---|
| schema/control | 当前active schema、控制epoch、migration ID和active manifest摘要 |
| scheduler/core | policy、quota/bulkhead参数、全局序列和计数器 |
| scheduler/active/lease-hash | 单个Admission lease，绑定TTL |
| scheduler/requests/request-hash | 持久request identity/tombstone |
| scheduler/waiters/queue-key | 排队项与公平性序列 |
| coordinator/leader | 当前Coordinator Leader epoch/lease |
| coordinator/scopes/scope-hash | 单scope lease状态、fencing高水位、publish sequence、archive pointers |
| coordinator/hot-operations/scope-hash/op-key | 单operation精确热记录 |
| coordinator/archive-index/scope-hash/head | 精确Archive Index与manifest链权威指针 |

每个operation的关键事务比较应围绕本次scope和operation的精确对象，而不是把全局所有active Admission lease全部加入Compare集合。候选事务至少应校验当前Leader、scope revision、确切Admission lease、对应request记录、operation/idempotency目标和必要的archive index head，再原子更新本次operation与scope高水位。Quota/fairness调度仍需自己的原子计数/队列协议；不能为减少Compare而取消全局/tenant额度正确性。

若一次operation依赖archive index精确未命中，则其创建事务还必须比较读取时的archive pointer revision/value；这样若并发归档在查询后将同一个idempotency key纳入archive，新请求会CAS失败并重新查找，而不能基于过期not-found创建第二个operation。

## 4. v2 → v3 安全迁移协议

迁移采用**单权威、冻结写入、候选对象先建、控制指针原子切换**。不使用跨存储双写来伪造分布式原子性。

1. **Preflight：** 记录v2 schema version、aggregate revision/摘要、Leader epoch、scope count、operation count、active lease/request/waiter数量、每scope high_water_token 与 latest_operation_sequence；验证现有archive manifest链及索引（若存在）。
2. **Acquire barrier：** 由当前Leader持有迁移权，CAS写入migration ID和write-frozen gate；新旧所有v2写路径必须识别该gate并fail-closed。等待在途请求完成或进入可审查状态，不得把pending operation当作已完成。
3. **Freeze snapshot：** 在冻结状态下取得稳定v2 revision快照和source SHA-256；任何source revision变化或Leader epoch变化都终止本次候选。
4. **Build inactive v3：** 在独立的migration generation前缀创建scheduler对象、Leader对象、scope对象、hot operation对象以及已全链验证的archive index pointers。对象先写，不让在线请求读取。
5. **Verify：** 对每个对象做read-back和SHA-256；对照source revision、完整operation key集合、scope数量、active lease/request一致性、waiter、policy/counters、每scope token/sequence floor、archive generation/head/count及索引全链完整性。验证报告必须绑定source digest和candidate root digest。
6. **Cutover CAS：** 控制指针事务比较旧active schema仍为2、migration epoch、v2 source revision、当前Leader epoch和write-frozen状态，然后一次性切为schema 3及candidate root。事务响应丢失时线性一致读取control pointer；只有schema、epoch、migration ID和root digest全部匹配才认定切换成功。
7. **Resume：** 先确认所有服务实例已识别schema generation和V3 keyspace，再解除写冻结。旧v2客户端携带旧generation的写请求必须被拒绝，而不是静默写入旧aggregate。
8. **Observe：** 观察operation lookup、scope CAS冲突、lease校验、队列公平性、对象读写、p95/p99和恢复指标；保留只读v2迁移快照及完整迁移证据，直到企业批准的回滚窗口结束。

迁移过程中archive object/index写入失败、摘要不一致或候选不完整，只允许中止并保留v2权威；不得提前移动active pointer，也不得删除v2数据。

## 5. 回滚规则：区分“未写入回切”和“写入后反向迁移”

### 5.1 V3尚未接受任何mutation

若控制指针已切到v3，但仍保持写冻结、没有任何v3业务mutation，可以在同一迁移控制epoch保护下CAS切回原v2快照。此窗口内v2源没有落后于v3写入，因此允许指针回切。

### 5.2 V3已接受第一笔mutation

一旦v3接收任何业务写入，**禁止直接把active pointer指回迁移前的旧v2快照**。该快照已缺失v3接受的operation、scope高水位或sequence进展，会造成重复idempotency key、token/sequence回退和旧状态复活。

此后只能：
- 优先向前修复v3；
- 或冻结v3、通过完整Archive Index/manifest链重新水合全部历史operation，重建v2 shadow，逐条核对v3已接受operation、每scope fencing/sequence floors、Admission/Leader状态、request tombstones和容量限制，验证目标v2 aggregate完整可表示后，再通过新的控制epoch CAS反向迁移。

如果v2重建状态超过经核实的请求/状态容量，或归档索引不完整、外部floor不可核验，则反向迁移不可行；继续保持冻结并向前修复，不允许降级到过期快照。此规则也适用于v3阶段已经有新的archive batch或新的idempotency tombstone的情况。

## 6. etcd事务和容量边界

etcd v3.7官方文档说明，--max-txn-ops 默认128、--max-request-bytes 默认1,572,864字节，二者均为可配置服务端选项。目标部署必须读取真实服务端参数；不能把默认值写成所有环境固定限制。参考 SRC-000403。

etcd Txn是对key-value store的原子If/Then/Else结构；Compare是多个谓词的合取，Then/Else中的操作按顺序处理。因此schema-v3的控制指针CAS、scope状态和相关operation key必须设计在同一个目标etcd事务边界内；不可把多个独立RPC的先后成功误当作跨对象原子性。参考 SRC-000405。

归档批次会删除对应hot operation key并切换archive/index pointers；批次record数必须同时受实际transaction operation count和serialized request bytes约束。若目标max-txn-ops较小，应缩小每批删除数或设计显式分阶段归档状态机；不得通过假定更大的默认限制规避。大请求可能增加其他etcd请求延迟；请求预算还需计入Compare、Then/Else、key/value和协议封装，而不是只看manifest JSON大小。

etcd MVCC compaction只清理被后续版本取代的历史版本，不替应用维护业务Operation Ledger。参考 SRC-000404。

## 7. 参考实现与验证边界

新增：
- scripts/spare_parts_operation_archive_index.py：16/256/4096桶精确分片索引、旧manifest链回填、逐批增量更新、精确hit/miss、目标batch回读校验和全链审计。
- scripts/spare_parts_coordinator_schema_migration.py：schema-v2写冻结、source digest、schema-v3逻辑对象候选、完整对象校验、Leader/source revision/外部floor保护、cutover、写入前指针回切和写入后重建式反向迁移。
- 对应两份测试文件，当前合计46个测试方法。
- ASSET-000089定义独立于参考模型单测的正式迁移/索引场景矩阵，全部 PROPOSED_NOT_APPROVED / NOT_RUN。

参考模型不执行真实etcd Compare/Txn、不接入对象存储、不实现生产认证/权限/密钥管理、不保证网络分区下的多实例行为，也不替代真实p95/p99、吞吐、quorum、恢复时间和保留策略验收。单元测试通过只验证代码模型，不表示Schema v3已获准实施。

## 8. 生产实施前置条件

1. 固定目标etcd版本、集群规模、真实max-txn-ops、max-request-bytes、backend quota和auto-compaction配置。
2. 通过容量画像与真实负载决定bucket数量、单bucket shard大小、archive batch records/bytes和回填速率。
3. 明确Coordinator schema-control key的权限、Leader epoch保护和旧客户端generation拒绝规则。
4. 证明Admission quotas/fairness在V3分键后仍可原子更新，不依靠全局active lease扫描来维持正确性。
5. 在隔离真实etcd集群演练：长时间网络分区、Leader失效/切换、archive store不可用、CAS冲突、lost response、索引损坏、迁移中断、cutover后立即回滚、v3写入后reverse rehydrate及恢复校验。
6. 企业批准迁移窗口、写冻结最长时间、RPO/RTO、保留/法律保留、对象锁/备份副本、回滚可行性和生产切换门禁。

当前CH17-T004继续IN_PROGRESS；生产归档仍关闭；schema-v2仍是唯一生产权威；未发生迁移、cutover或历史数据删除。

## 9. 来源

- SRC-000403：etcd v3.7 Configuration options，Txn操作数与请求大小的默认值/可配置性。
- SRC-000404：etcd v3.7 Data model，MVCC revision/compaction语义。
- SRC-000405：etcd v3.7 API，Txn Compare/Then/Else原子语义。
- KNOW-000057：Coordinator Operation Ledger生命周期与安全归档协议。


## 10. CI验收记录

- **最终代码/测试head：** `2b66224909d2bcd9b326c1cffcf220bef5d14b7f`（main）。首个实现提交为 `b3eaf4807028783681a424228ffed76b3a8a4245`；随后修正了历史archive pointer测试中的权威计数夹具，以及reverse-migration容量测试的状态机前置步骤。
- **CI：** [GitHub Actions Run 45819520749](https://github.com/rexyll/cnc-knowledge/actions/runs/45819520749)，head SHA与最终代码提交一致，两个必需Job均completed/success。
- **测试结果：** 全库426项unittest通过（含本轮21项Archive Index测试及25项Schema migration测试）；CH12 143项数值资源测试通过；strict knowledge lint 0 errors；知识结构与数据质量0 errors。另有5项既有合成fixture审批/执行状态warning，非本轮测试失败。
- **验收边界：** 只验证内存精确索引及迁移状态机模型；不表示真实对象存储/etcd事务、真实多主机Leader/Coordinator、schema-v3生产keyspace或生产迁移回滚通过。ASSET-000089的47项正式场景仍PROPOSED_NOT_APPROVED / NOT_RUN。
